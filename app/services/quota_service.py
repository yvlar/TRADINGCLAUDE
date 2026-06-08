"""Quotas par plan — borne DURE de consommation par tenant (E4-S2).

Au contraire du metering `usage_events` (Sprint 166, best-effort : un échec n'avorte jamais
l'analyse), un quota est une **borne dure** : au dépassement, la requête est refusée (`429`).

Deux bornes appliquées ce sprint :
- **analyses/mois** — compteur mensuel Redis (`quota:{tenant}:{YYYY-MM}`), calqué sur
  `RateLimitMiddleware` (incr/expire). Choix Redis (et non agrégation `usage_events`) :
  l'application d'un quota doit être rapide sur le chemin chaud `/analyze`, et `usage_events`
  est **par skill** (pas par analyse) — en compter les analyses exigerait un COUNT DISTINCT
  coûteux. `usage_events` reste la **source de vérité durable** de la facturation (E4-S5) ; le
  compteur Redis n'est qu'un dispositif d'application **dans la fenêtre**, volontairement
  éphémère (la clé expire au basculement de mois).
- **taille screener** — borne `max_screener_tickers` du plan, en plus du plafond technique
  (max 20) ; rejet synchrone si la liste dépasse la borne du plan.

Politique de panne — **fail-open documenté** : si Redis est indisponible, la requête est
**autorisée** (log d'avertissement), cohérent avec `RateLimitMiddleware`. Justification : une
panne d'infra de quota ne doit pas bloquer un client payant, et la consommation réelle reste
enregistrée durablement dans `usage_events` pour réconciliation/facturation. La borne dure
s'applique dès que Redis est rétabli. (L'alternative fail-closed `503` est rejetée : elle
transformerait une panne Redis en interruption de service facturable.)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
import redis.asyncio as aioredis

from app.db.tenant_context import resolve_tenant

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanLimits:
    """Bornes de consommation résolues pour le plan d'un tenant."""

    plan: str
    max_analyses_per_month: int
    max_screener_tickers: int
    retention_days: int


@dataclass(frozen=True)
class QuotaStatus:
    """État de quota mensuel d'un tenant — lecture seule (E5-S6).

    `limit`/`remaining` valent `None` quand le plan n'a pas pu être résolu (fail-open) : on
    ne fabrique pas une borne factice, le client affiche alors le plan sans compteur.
    """

    plan: str
    used: int
    limit: int | None
    remaining: int | None
    reset_at: datetime


class QuotaExceededError(Exception):
    """Dépassement d'une borne de plan — mappé en `429` au niveau endpoint.

    `retry_after_s` : secondes avant remise à zéro (None pour la borne screener, qui ne
    dépend pas du temps mais de la taille de la requête).
    """

    def __init__(
        self, message: str, *, plan: str, used: int, limit: int, retry_after_s: int | None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.plan = plan
        self.used = used
        self.limit = limit
        self.retry_after_s = retry_after_s


class QuotaService:
    """Applique les bornes de plan (analyses/mois + taille screener) au tenant courant."""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: aioredis.Redis) -> None:
        self._db = db_pool
        self._redis = redis_client

    async def _resolve_limits(self, tenant: UUID) -> PlanLimits | None:
        """Résout les bornes du plan du tenant (None si tenant/plan absent → fail-open)."""
        row = await self._db.fetchrow(
            """
            SELECT pl.plan, pl.max_analyses_per_month, pl.max_screener_tickers, pl.retention_days
            FROM tenants t
            JOIN plan_limits pl ON pl.plan = t.plan
            WHERE t.id = $1::uuid
            """,
            str(tenant),
        )
        if row is None:
            # Tenant inconnu ou plan non référencé : aucune borne applicable (fail-open).
            logger.warning("Aucune borne de plan résolue pour le tenant %s — quota non appliqué", tenant)
            return None
        return PlanLimits(
            plan=row["plan"],
            max_analyses_per_month=row["max_analyses_per_month"],
            max_screener_tickers=row["max_screener_tickers"],
            retention_days=row["retention_days"],
        )

    async def _current_count(self, key: str) -> int:
        """Compteur mensuel courant ; 0 si absent ou Redis indisponible (fail-open)."""
        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.warning("Redis indisponible pour la lecture du quota — requête autorisée")
            return 0
        return int(raw) if raw else 0

    async def check(self, tenant_id: UUID | None = None) -> None:
        """Lève `QuotaExceededError` si le quota mensuel d'analyses est atteint (lecture seule)."""
        tenant = resolve_tenant(tenant_id)
        limits = await self._resolve_limits(tenant)
        if limits is None:
            return
        now = datetime.now(timezone.utc)
        used = await self._current_count(_month_key(tenant, now))
        if used >= limits.max_analyses_per_month:
            retry_after = _seconds_until_month_end(now)
            raise QuotaExceededError(
                f"Quota mensuel atteint (plan {limits.plan} : "
                f"{used}/{limits.max_analyses_per_month} analyses). "
                "Réessayez le mois prochain ou passez à un plan supérieur.",
                plan=limits.plan,
                used=used,
                limit=limits.max_analyses_per_month,
                retry_after_s=retry_after,
            )

    async def increment(self, tenant_id: UUID | None = None) -> None:
        """Incrémente le compteur mensuel (best-effort sur Redis — fail-open documenté)."""
        tenant = resolve_tenant(tenant_id)
        now = datetime.now(timezone.utc)
        key = _month_key(tenant, now)
        try:
            count = await self._redis.incr(key)
            # Pose le TTL uniquement à la création de la clé (premier incr du mois) : la fenêtre
            # expire au basculement de mois sans jamais être prolongée par les incréments suivants.
            if count == 1:
                await self._redis.expire(key, _seconds_until_month_end(now))
        except Exception:
            logger.warning("Redis indisponible pour l'incrément du quota — non comptabilisé")

    async def check_and_increment(self, tenant_id: UUID | None = None) -> None:
        """Vérifie puis incrémente — appelants SANS exemption de cache hit uniquement.

        Les endpoints `/analyze`/`/screen` n'utilisent PAS ce raccourci : ils scindent
        `check()` (avant le travail) et `increment()` (après, seulement si `cost_usd>0`) pour
        ne pas consommer sur un cache hit. Ne l'utiliser que si la consommation est
        inconditionnelle, sous peine de sur-compter.
        """
        await self.check(tenant_id)
        await self.increment(tenant_id)

    async def read_status(self, tenant_id: UUID | None = None) -> QuotaStatus:
        """État du quota mensuel du tenant — LECTURE SEULE (n'incrémente jamais le compteur).

        Réutilise `_resolve_limits` (plan + borne) et `_current_count` (compteur Redis). Fail-open
        cohérent : plan non résolu → `limit`/`remaining` à `None` ; Redis indisponible → `used=0`
        (déjà géré par `_current_count`). Ne casse jamais le header appelant.
        """
        tenant = resolve_tenant(tenant_id)
        now = datetime.now(timezone.utc)
        reset_at = _next_month_start(now)
        try:
            limits = await self._resolve_limits(tenant)
        except Exception:
            # Lecture pour un affichage de header : une panne DB ne doit jamais lever un 500
            # (fail-open au même titre que Redis dans `_current_count`).
            logger.warning("Résolution du plan indisponible pour read_status — quota neutre (fail-open)")
            limits = None
        if limits is None:
            return QuotaStatus(plan="unknown", used=0, limit=None, remaining=None, reset_at=reset_at)
        used = await self._current_count(_month_key(tenant, now))
        limit = limits.max_analyses_per_month
        return QuotaStatus(
            plan=limits.plan,
            used=used,
            limit=limit,
            remaining=max(0, limit - used),
            reset_at=reset_at,
        )

    async def check_screener_size(self, num_tickers: int, tenant_id: UUID | None = None) -> None:
        """Lève `QuotaExceededError` si la liste dépasse `max_screener_tickers` du plan."""
        tenant = resolve_tenant(tenant_id)
        limits = await self._resolve_limits(tenant)
        if limits is None:
            return
        if num_tickers > limits.max_screener_tickers:
            raise QuotaExceededError(
                f"Liste de {num_tickers} tickers au-delà de la borne du plan "
                f"{limits.plan} (max {limits.max_screener_tickers}). "
                "Réduisez la liste ou passez à un plan supérieur.",
                plan=limits.plan,
                used=num_tickers,
                limit=limits.max_screener_tickers,
                retry_after_s=None,
            )


def _month_key(tenant: UUID, now: datetime) -> str:
    """Clé Redis du compteur mensuel — fenêtre calendaire UTC par tenant."""
    return f"quota:{tenant}:{now:%Y-%m}"


def _next_month_start(now: datetime) -> datetime:
    """1er du mois suivant à 00:00 UTC — bascule de la fenêtre mensuelle du compteur."""
    if now.month == 12:
        return now.replace(
            year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _seconds_until_month_end(now: datetime) -> int:
    """Secondes jusqu'au 1er du mois suivant (UTC) — TTL de la clé et `Retry-After`."""
    return max(1, int((_next_month_start(now) - now).total_seconds()))
