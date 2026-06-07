"""Purge de rétention par plan — applique `plan_limits.retention_days` (E4-S6).

Transforme `retention_days` (colonne dormante depuis E4-S2, `0007_plan_limits.py`) en
**politique réelle** : pour un tenant donné et **sous son contexte RLS**, supprime les lignes
des tables historiques plus vieilles que la fenêtre de rétention de son plan
(free = 30 j, pro = 365 j).

Périmètre des tables purgées — décision tranchée ce sprint :
- **PURGÉES** (données historiques auto-générées, croissance non bornée, sémantique « analyse ») :
  `analysis_history` (`created_at`), `composite_score_history` (`recorded_at`),
  `esg_score_history` (`recorded_at`), `alert_history` (`created_at`).
- **NON PURGÉES** (exclusion justifiée) :
  * `usage_events` — **rétention FACTURATION ≠ rétention analyse** (`0006_usage_events.py` :
    « un événement de conso doit survivre à la purge de son analyse »). Purger la source de
    vérité de facturation détruirait les données de réconciliation ; une borne distincte
    (plus longue) est déférée à l'intégration Stripe (E4-S7).
  * `watchlist` — positions **activement surveillées** (état/config, pas un historique) ;
    `created_at` = date d'ajout au suivi, pas l'horodatage d'un événement périssable.
  * `annotations` — notes **rédigées par l'utilisateur** (contenu personnel, non auto-généré) ;
    leur rétention relève d'une décision produit distincte de l'hygiène des données d'analyse.

Sécurité :
- Le DELETE est **doublement scopé** : par l'âge (`created_at`/`recorded_at`) ET par le contexte
  tenant (RLS) — jamais de `DELETE FROM table` sans clause. L'appelant DOIT avoir posé
  `set_current_tenant(tenant_id)` (le GUC RLS en dérive) pour ne purger que les lignes du tenant.
- **Fail-safe** : `retention_days` `NULL`/absent → aucune purge (un plan mal configuré ne doit
  jamais tout supprimer).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

import asyncpg

from app.db.tenant_context import resolve_tenant

logger = logging.getLogger(__name__)

# Table historique → colonne d'horodatage portant la fenêtre de rétention. `composite_score_history`
# et `esg_score_history` horodatent via `recorded_at` ; les autres via `created_at`
# (cf. `0001_baseline_schema.py`). Constante figée — aucune entrée ne provient d'une saisie
# externe, donc l'interpolation du nom de table dans le DELETE est sûre (asyncpg ne paramètre
# pas les identifiants).
_PURGEABLE_TABLES: tuple[tuple[str, str], ...] = (
    ("analysis_history", "created_at"),
    ("composite_score_history", "recorded_at"),
    ("esg_score_history", "recorded_at"),
    ("alert_history", "created_at"),
)


@dataclass(frozen=True)
class PurgeResult:
    """Comptes de lignes supprimées par table pour un tenant (logs/agrégation worker)."""

    tenant_id: UUID
    plan: str
    retention_days: int
    deleted_by_table: dict[str, int]

    @property
    def total_deleted(self) -> int:
        return sum(self.deleted_by_table.values())


class RetentionService:
    """Purge les tables historiques au-delà de la rétention du plan, un tenant à la fois."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def _resolve_retention(self, tenant: UUID) -> tuple[str, int] | None:
        """Résout `(plan, retention_days)` du tenant ; `None` si tenant/plan/borne absent (fail-safe)."""
        row = await self._db.fetchrow(
            """
            SELECT t.plan, pl.retention_days
            FROM tenants t
            JOIN plan_limits pl ON pl.plan = t.plan
            WHERE t.id = $1::uuid
            """,
            str(tenant),
        )
        if row is None or row["retention_days"] is None:
            return None
        return row["plan"], row["retention_days"]

    async def purge_tenant(self, tenant_id: UUID | None = None) -> PurgeResult | None:
        """Purge les tables historiques du tenant **sous son contexte RLS** ; `None` si pas de borne.

        Invariant : l'appelant doit avoir posé `set_current_tenant(tenant_id)` — chaque DELETE
        tourne sous le GUC du tenant et ne touche donc que ses lignes (fail-closed si GUC absent).
        """
        tenant = resolve_tenant(tenant_id)
        resolved = await self._resolve_retention(tenant)
        if resolved is None:
            logger.warning(
                "Rétention non résolue pour le tenant %s (plan/retention_days absent) — purge ignorée",
                tenant,
            )
            return None
        plan, retention_days = resolved

        deleted_by_table: dict[str, int] = {}
        for table, ts_column in _PURGEABLE_TABLES:
            # Borne temporelle liée en str → interval (patron `get_metrics`/`aggregate`). DELETE
            # doublement scopé : par l'âge (`ts_column`) ET par la RLS (contexte tenant courant).
            status = await self._db.execute(
                f"DELETE FROM {table} "
                f"WHERE {ts_column} < NOW() - ($1 || ' days')::interval",
                str(retention_days),
            )
            deleted_by_table[table] = _parse_delete_count(status)

        return PurgeResult(
            tenant_id=tenant,
            plan=plan,
            retention_days=retention_days,
            deleted_by_table=deleted_by_table,
        )


def _parse_delete_count(status: str) -> int:
    """Extrait le nombre de lignes du tag de commande asyncpg (`'DELETE <n>'`)."""
    parts = status.split()
    return int(parts[-1]) if parts and parts[-1].isdigit() else 0
