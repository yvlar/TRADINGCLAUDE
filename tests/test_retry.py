"""Tests unitaires de app/utils/retry.py — aucun appel réseau réel."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

from app.utils.retry import call_claude_with_retry


class TestCallClaudeWithRetry:

    @pytest.mark.asyncio
    async def test_succes_premier_appel(self):
        """Retourne directement la réponse si pas d'erreur."""
        mock_response = MagicMock()
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        result = await call_claude_with_retry(
            mock_client, model="claude-sonnet-4-6", messages=[], max_tokens=100
        )

        assert result is mock_response
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_passe_a_messages_create(self):
        """Le paramètre timeout_s est transmis à messages.create."""
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = MagicMock()

        await call_claude_with_retry(
            mock_client, timeout_s=42.0, model="test", messages=[], max_tokens=10
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["timeout"] == 42.0

    @pytest.mark.asyncio
    async def test_retry_sur_erreur_529(self):
        """Retente sur APIStatusError 529, réussit au 2e essai."""
        mock_response = MagicMock()
        err_529 = anthropic.APIStatusError(
            "overloaded", response=MagicMock(status_code=529), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [err_529, mock_response]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await call_claude_with_retry(
                mock_client,
                timeout_s=5.0,
                max_retries=2,
                model="test",
                messages=[],
                max_tokens=10,
            )

        assert result is mock_response
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_epuise_les_retries_et_propage(self):
        """Après max_retries, propage l'erreur 529."""
        err_529 = anthropic.APIStatusError(
            "overloaded", response=MagicMock(status_code=529), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = err_529

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(anthropic.APIStatusError):
                await call_claude_with_retry(
                    mock_client,
                    timeout_s=5.0,
                    max_retries=2,
                    model="test",
                    messages=[],
                    max_tokens=10,
                )

        assert mock_client.messages.create.call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_pas_de_retry_sur_erreur_400(self):
        """Les erreurs autres que 529 ne sont pas retriées."""
        err_400 = anthropic.APIStatusError(
            "bad request", response=MagicMock(status_code=400), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = err_400

        with pytest.raises(anthropic.APIStatusError):
            await call_claude_with_retry(
                mock_client,
                timeout_s=5.0,
                max_retries=3,
                model="test",
                messages=[],
                max_tokens=10,
            )

        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_erreur_pas_retriee(self):
        """APITimeoutError est propagée immédiatement sans retry."""
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = anthropic.APITimeoutError(
            request=MagicMock()
        )

        with pytest.raises(anthropic.APITimeoutError):
            await call_claude_with_retry(
                mock_client,
                timeout_s=1.0,
                max_retries=3,
                model="test",
                messages=[],
                max_tokens=10,
            )

        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sleep_appele_entre_retries(self):
        """asyncio.sleep est appelé entre chaque tentative."""
        err_529 = anthropic.APIStatusError(
            "overloaded", response=MagicMock(status_code=529), body={}
        )
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [err_529, err_529, MagicMock()]

        with patch("app.utils.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await call_claude_with_retry(
                mock_client,
                timeout_s=5.0,
                max_retries=3,
                model="test",
                messages=[],
                max_tokens=10,
            )

        assert mock_sleep.call_count == 2  # 2 retries = 2 sleeps
