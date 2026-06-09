"""Source unique du harnais d'intégration RLS partagé par les tests sous le rôle réel `app_runtime`.

Centralise (1) l'inventaire des 7 tables RLS et (2) le harnais de skip `APP_DATABASE_URL`
(`pytest.mark.integration` + `skipif`), jusqu'ici dupliqués entre plusieurs fichiers (2 définitions
de l'ensemble des tables + 1 import croisé, harnais de skip recopié verbatim). Une migration ajoutant
une 8ᵉ table RLS ne se répercute désormais qu'ici — plus de divergence silencieuse possible.

Module utilitaire (préfixe `_`, hors `test_*.py`) → non collecté par pytest, seulement importé.

Note de périmètre : `test_rls_isolation.py` partage l'inventaire de tables mais garde son propre garde
de skip sur `RLS_TEST_DATABASE_URL` (rôle `rls_tester` provisionné à la main par le workflow CI) —
sémantique de skip distincte de `APP_DATABASE_URL` (rôle réel `app_runtime` provisionné par migration),
donc volontairement non centralisée ici.
"""
from __future__ import annotations

import os

import pytest

# Inventaire unique des 7 tables RLS (ENABLE+FORCE RLS, policy tenant standard) — sous-ensemble de
# `0011._RW_TABLES`. Toute table RLS ajoutée par migration doit l'être ICI (source de vérité unique).
RLS_TABLES: tuple[str, ...] = (
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "alert_history",
    "annotations",
    "usage_events",
)

# Harnais de skip partagé : les tests sous le rôle réel `app_runtime` exigent `APP_DATABASE_URL`
# (PG migré). Hors PG migré (conteneur web) → skip ; en CI sous `app_runtime` → exécutés.
APP_DB_URL = os.environ.get("APP_DATABASE_URL")

app_runtime_pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not APP_DB_URL,
        reason="APP_DATABASE_URL non défini (PG migré + rôle app_runtime requis)",
    ),
]

# S197 — helper de connexion simple non extrait (décision clos) :
# Re-mesure : 7 sites `asyncpg.connect(_APP_DB_URL)` / `try/finally close` sur 3 fichiers
# (test_revoke_public_rls×4, test_force_rls×1, test_app_runtime_rls×2).
# S193 avait déjà tranché sur ce même périmètre : le `try/finally close` est idiomatique
# Python, les tests restent auto-portants, gain marginal < coût d'une couche d'abstraction.
# La famille `_RLS_DB_URL` (create_pool + apply_tenant_context) reste distincte et non foldée.
