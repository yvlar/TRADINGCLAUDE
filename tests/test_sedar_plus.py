"""Tests unitaires pour SedarPlusExtractor."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.skills.tier1.sedar_plus import SedarPlusExtractor


class TestSedarPlusDetectionTSX:
    def test_tsx_detecte_avec_suffixe_to(self):
        """BNS.TO → _is_tsx_ticker retourne True."""
        extractor = SedarPlusExtractor()
        assert extractor._is_tsx_ticker("BNS.TO") is True

    def test_tsx_detecte_avec_suffixe_v(self):
        """CSU.V → _is_tsx_ticker retourne True."""
        extractor = SedarPlusExtractor()
        assert extractor._is_tsx_ticker("CSU.V") is True

    def test_tsx_detecte_majuscule_insensible(self):
        """bns.to → _is_tsx_ticker retourne True (insensible à la casse)."""
        extractor = SedarPlusExtractor()
        assert extractor._is_tsx_ticker("bns.to") is True

    def test_ticker_nyse_retourne_false(self):
        """MSFT (NYSE) → _is_tsx_ticker retourne False."""
        extractor = SedarPlusExtractor()
        assert extractor._is_tsx_ticker("MSFT") is False

    def test_ticker_nasdaq_retourne_false(self):
        """AAPL (Nasdaq) → _is_tsx_ticker retourne False."""
        extractor = SedarPlusExtractor()
        assert extractor._is_tsx_ticker("AAPL") is False

    def test_ticker_us_avec_suffixe_autre(self):
        """BRK.B (NYSE) → _is_tsx_ticker retourne False."""
        extractor = SedarPlusExtractor()
        assert extractor._is_tsx_ticker("BRK.B") is False


class TestSedarPlusExtract:
    @pytest.mark.asyncio
    async def test_ticker_nyse_retourne_none_sans_appel_http(self):
        """MSFT → extract retourne None sans appel HTTP (heuristique)."""
        extractor = SedarPlusExtractor()
        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            result = await extractor.extract("MSFT")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_ticker_nasdaq_retourne_none_sans_appel_http(self):
        """AAPL → extract retourne None sans appel HTTP."""
        extractor = SedarPlusExtractor()
        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            result = await extractor.extract("AAPL")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_erreur_http_retourne_none(self):
        """mock httpx → ConnectError → extract retourne None (pas d'exception levée)."""
        extractor = SedarPlusExtractor()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await extractor.extract("BNS.TO")

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_retourne_none(self):
        """mock httpx → TimeoutException → extract retourne None (pas d'exception levée)."""
        extractor = SedarPlusExtractor()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await extractor.extract("BNS.TO")

        assert result is None

    @pytest.mark.asyncio
    async def test_404_retourne_none(self):
        """mock httpx → status 404 → extract retourne None."""
        extractor = SedarPlusExtractor()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await extractor.extract("BNS.TO")

        assert result is None

    @pytest.mark.asyncio
    async def test_erreur_generique_retourne_none(self):
        """Toute exception non anticipée → extract retourne None (jamais ne lève)."""
        extractor = SedarPlusExtractor()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await extractor.extract("BNS.TO")

        assert result is None

    @pytest.mark.asyncio
    async def test_reponse_200_retourne_none_sedar_pas_de_ratios(self):
        """SEDAR+ répond 200 mais ne fournit pas de ratios structurés → None."""
        extractor = SedarPlusExtractor()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.skills.tier1.sedar_plus.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await extractor.extract("BNS.TO")

        assert result is None
