"""Helpers pour charger les golden datasets des evals."""
from __future__ import annotations

import json
from pathlib import Path

_FIXTURES_DIR = Path(__file__).parent


def load_graham_golden() -> list[dict]:
    """Charge tests/evals/fixtures/graham_golden.json."""
    path = _FIXTURES_DIR / "graham_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
