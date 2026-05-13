"""Tests unitaires pour app/utils/ticker_sanitizer.py"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.utils.ticker_sanitizer import sanitize_ticker


@pytest.mark.parametrize("raw,expected", [
    ("BNS", "BNS"),
    ("bns", "BNS"),           # normalisation majuscules
    (" BNS ", "BNS"),         # strip espaces
    ("BNS.TO", "BNS.TO"),     # suffixe canadien (2 lettres)
    ("BRK.B", "BRK.B"),       # suffixe lettre unique
    ("AAPL", "AAPL"),         # ticker US standard
    ("XEQT", "XEQT"),         # ETF canadien
    ("A", "A"),               # 1 caractère — valide
    ("A1B2C3", "A1B2C3"),     # 6 caractères alphanumériques
    ("VFV.TO", "VFV.TO"),     # ETF TSX
    (" brk.b ", "BRK.B"),     # strip + normalisation
])
def test_valid_tickers(raw: str, expected: str) -> None:
    assert sanitize_ticker(raw) == expected


@pytest.mark.parametrize("invalid", [
    "",                   # vide
    "   ",                # espaces seulement
    "DROP TABLE",         # injection SQL
    "BNS;rm",             # injection shell
    "123456789",          # trop long
    "B.NS.TO",            # double suffixe
    "TOOLONG7",           # 8 chars — trop long
    "../etc/passwd",      # path traversal
    "BNS.TOO",            # suffixe trop long (3 lettres)
    "BNS.",               # point sans suffixe
    ".BNS",               # point en position invalide
    "BNS TO",             # espace interne
    "BNS\nTO",            # newline
    "<script>",           # XSS
])
def test_invalid_tickers_raise_422(invalid: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        sanitize_ticker(invalid)
    assert exc_info.value.status_code == 422
    assert "Ticker invalide" in exc_info.value.detail


def test_detail_message_contient_valeur_originale() -> None:
    """Le message d'erreur expose la valeur brute pour le débogage."""
    with pytest.raises(HTTPException) as exc_info:
        sanitize_ticker("drop table")
    assert "drop table" in exc_info.value.detail


def test_strip_ne_change_pas_ticker_valide() -> None:
    """Les espaces en bordure sont ignorés — le ticker sous-jacent reste valide."""
    assert sanitize_ticker("  AAPL  ") == "AAPL"


def test_normalisation_minuscules() -> None:
    assert sanitize_ticker("bnsto") == "BNSTO"
