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


def load_earnings_golden() -> list[dict]:
    """Charge tests/evals/fixtures/earnings_golden.json."""
    path = _FIXTURES_DIR / "earnings_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_dorsey_golden() -> list[dict]:
    """Charge tests/evals/fixtures/dorsey_golden.json."""
    path = _FIXTURES_DIR / "dorsey_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_buffett_golden() -> list[dict]:
    """Charge tests/evals/fixtures/buffett_golden.json."""
    path = _FIXTURES_DIR / "buffett_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_damodaran_golden() -> list[dict]:
    """Charge tests/evals/fixtures/damodaran_golden.json."""
    path = _FIXTURES_DIR / "damodaran_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_screener_golden() -> list[dict]:
    """Charge tests/evals/golden_screener_dataset.json."""
    path = _FIXTURES_DIR.parent / "golden_screener_dataset.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_multi_model_golden() -> list[dict]:
    """Charge tests/evals/fixtures/multi_model_golden.json."""
    path = _FIXTURES_DIR / "multi_model_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_valuation_golden() -> list[dict]:
    """Charge tests/evals/fixtures/valuation_golden.json."""
    path = _FIXTURES_DIR / "valuation_golden.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
