"""Tests de l'expurgation des secrets dans les logs + masquage traceback hors dev (E1-S3)."""
from __future__ import annotations

import logging
import sys

import pytest

from app.logging_config import JsonFormatter, RedactingTextFormatter
from app.utils.log_sanitization import redact


class TestRedact:
    @pytest.mark.parametrize(
        "secret",
        [
            "sk-ant-api03-XYZ_secret-value",
            "sk-proj-1234567890abcdefghij",
            "pk-lf-publicLangfuseKey99",
            "SG.sendgridkey1234567890",
            "eyJhbGci.eyJzdWIiOiIx.sigPART",
        ],
    )
    def test_cles_et_tokens_expurges(self, secret: str):
        out = redact(f"valeur={secret} fin")
        assert secret not in out
        assert "[REDACTED]" in out

    def test_bearer_garde_le_prefixe(self):
        assert redact("Authorization: Bearer xyzTOKEN42") == "Authorization: Bearer [REDACTED]"

    def test_email_expurge(self):
        out = redact("contact yves@example.com ok")
        assert "yves@example.com" not in out
        assert "[EMAIL]" in out

    def test_texte_sans_secret_inchange(self):
        assert redact("analyse BNS.TO score 7/10") == "analyse BNS.TO score 7/10"


def _record_with_exc() -> logging.LogRecord:
    try:
        raise ValueError("erreur portant une clé sk-ant-LEAK123456")
    except ValueError:
        return logging.LogRecord(
            "n", logging.ERROR, "p", 1, "message normal", None, sys.exc_info()
        )


class TestJsonFormatter:
    def test_redige_message(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "production")
        rec = logging.LogRecord(
            "n", logging.INFO, "p", 1, "user yves@x.com clé sk-ant-LEAK999999", None, None
        )
        out = JsonFormatter().format(rec)
        assert "sk-ant-LEAK999999" not in out
        assert "yves@x.com" not in out

    def test_omet_traceback_en_prod(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "production")
        out = JsonFormatter().format(_record_with_exc())
        assert '"exc"' not in out

    def test_inclut_mais_redige_traceback_en_dev(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "dev")
        out = JsonFormatter().format(_record_with_exc())
        assert '"exc"' in out
        assert "sk-ant-LEAK123456" not in out  # traceback présent mais expurgé


class TestRedactingTextFormatter:
    def test_redige_message(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "dev")
        rec = logging.LogRecord("n", logging.INFO, "p", 1, "Bearer SECRETTOKEN42", None, None)
        out = RedactingTextFormatter("%(message)s").format(rec)
        assert "SECRETTOKEN42" not in out

    def test_masque_traceback_en_prod(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "production")
        out = RedactingTextFormatter("%(message)s").format(_record_with_exc())
        assert "traceback masqué" in out
        assert "Traceback" not in out
        assert "sk-ant-LEAK123456" not in out
