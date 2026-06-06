"""Tests du garde-fou d'identifiants PostgreSQL par défaut (E1-S2)."""
from __future__ import annotations

import pytest

from app.utils.security_config import require_secure_db_url

_DEFAULT_URL = "postgresql://copilote:copilote@postgres:5432/copilote"
_SECURE_URL = "postgresql://copilote:s3cr3t-genere-aleatoire@db.interne:5432/copilote"


def test_prod_refuse_identifiants_par_defaut(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        require_secure_db_url(_DEFAULT_URL)


def test_prod_absent_app_env_refuse(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(RuntimeError):
        require_secure_db_url(_DEFAULT_URL)


def test_prod_accepte_secret_genere(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    require_secure_db_url(_SECURE_URL)  # ne doit pas lever


def test_dev_tolere_identifiants_par_defaut(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    require_secure_db_url(_DEFAULT_URL)  # ne doit pas lever
