from __future__ import annotations

import re

_REDACTED = "[REDACTED]"
_EMAIL = "[EMAIL]"

# Motifs de secrets à expurger des logs — du plus spécifique au plus large.
# But : aucun token, clé API, JWT ni email (PII Loi 25) ne doit atteindre les logs.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE), f"Bearer {_REDACTED}"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9._\-]+"), _REDACTED),          # Anthropic
    (re.compile(r"\b(?:pk|sk)-lf-[A-Za-z0-9._\-]+"), _REDACTED),    # Langfuse
    (re.compile(r"\bsk-[A-Za-z0-9._\-]{16,}"), _REDACTED),          # OpenAI/générique
    (re.compile(r"\bSG\.[A-Za-z0-9._\-]{10,}"), _REDACTED),         # SendGrid
    (re.compile(r"\beyJ[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+"), _REDACTED),  # JWT
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), _EMAIL),
)


def redact(text: str) -> str:
    """Expurge tokens, clés API, JWT et emails d'une chaîne destinée aux logs."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
