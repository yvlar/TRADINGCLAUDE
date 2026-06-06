from __future__ import annotations

import json
import logging
import os

from app.utils.env import is_dev_environment
from app.utils.log_sanitization import redact


def _emit_traceback() -> bool:
    """Les tracebacks complets ne sont émis qu'en dev (fuite de données hors dev)."""
    return is_dev_environment()


class JsonFormatter(logging.Formatter):
    """Formatter qui émet chaque enregistrement de log comme une ligne JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            "ts":     self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        for key in (
            "skill_id", "ticker", "latency_ms", "cost_usd",
            "cache_hit_ratio", "tokens_input", "tokens_output",
            "tokens_cache_read", "tokens_cache_creation", "model",
        ):
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)
        if record.exc_info and _emit_traceback():
            log_obj["exc"] = self.formatException(record.exc_info)
        return redact(json.dumps(log_obj, ensure_ascii=False))


class RedactingTextFormatter(logging.Formatter):
    """Formatter texte qui expurge les secrets et masque les tracebacks hors dev."""

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))

    def formatException(self, ei) -> str:
        if _emit_traceback():
            return super().formatException(ei)
        return "[traceback masqué hors développement]"


def configure_logging() -> None:
    """Configure le logging JSON si LOG_FORMAT=json, sinon garde le format texte.

    Dans les deux cas, les secrets (tokens/clés/JWT/emails) sont expurgés et les
    tracebacks complets ne sont émis qu'en dev (confidentialité — E1-S3).
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "text").lower()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            RedactingTextFormatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
        )

    logging.basicConfig(level=log_level, handlers=[handler], force=True)
