"""Tests du garde-fou d'identifiants PostgreSQL par défaut (E1-S2) + résolution APP_DATABASE_URL (S182)."""
from __future__ import annotations

import pytest

from app.utils.security_config import require_secure_db_url, resolve_app_database_url

_DEFAULT_URL = "postgresql://copilote:copilote@postgres:5432/copilote"
_SECURE_URL = "postgresql://copilote:s3cr3t-genere-aleatoire@db.interne:5432/copilote"
_APP_URL = "postgresql://app_runtime:s3cr3t@db.interne:5432/copilote"


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


def test_resolve_app_url_priorise_app_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DATABASE_URL", _APP_URL)
    monkeypatch.setenv("DATABASE_URL", _SECURE_URL)
    assert resolve_app_database_url() == _APP_URL


def test_resolve_app_url_repli_database_url_en_dev(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", _DEFAULT_URL)
    assert resolve_app_database_url() == _DEFAULT_URL


def test_resolve_app_url_absente_hors_dev_fail_fast(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", _SECURE_URL)
    with pytest.raises(RuntimeError, match="APP_DATABASE_URL"):
        resolve_app_database_url()


def test_resolve_app_url_absente_app_env_vide_fail_fast(monkeypatch: pytest.MonkeyPatch):
    # APP_ENV absent = production (défaut sûr) → fail-closed même sans APP_DATABASE_URL.
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        resolve_app_database_url()
