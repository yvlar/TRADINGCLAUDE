from __future__ import annotations

import re

from fastapi import HTTPException

_TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,6}(\.[A-Z]{1,2})?$")


def sanitize_ticker(raw: str) -> str:
    """
    Normalise et valide un ticker boursier.
    Lève HTTP 422 si invalide — jamais de rejet silencieux.
    Exemples valides : BNS, BNS.TO, AAPL, BRK.B, XEQT
    Exemples invalides : '', 'DROP TABLE', 'BNS; rm -rf', 'B.NS.TO'
    """
    ticker = raw.strip().upper()
    if not _TICKER_PATTERN.match(ticker):
        raise HTTPException(status_code=422, detail=f"Ticker invalide : {raw!r}")
    return ticker
