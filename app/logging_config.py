from __future__ import annotations

import json
import logging
import os


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
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def configure_logging() -> None:
    """Configure le logging JSON si LOG_FORMAT=json, sinon garde le format texte."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "text").lower()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
        )

    logging.basicConfig(level=log_level, handlers=[handler], force=True)
