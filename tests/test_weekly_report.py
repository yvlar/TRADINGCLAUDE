"""Tests pour la tâche Celery run_weekly_watchlist_report."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.watchlist import WatchlistEntry


def _make_entry(ticker: str, score: int = 5, verdict: str = "ACCEPTABLE") -> WatchlistEntry:
    """Crée une WatchlistEntry de test."""
    return WatchlistEntry(
        id="550e8400-e29b-41d4-a716-446655440001",
        ticker=ticker,
        workflow="value_graham",
        ratios=None,
        score_alerte_min=None,
        created_at=datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc),
        last_analyzed_at=datetime(2026, 5, 9, 7, 5, tzinfo=timezone.utc),
        last_score=score,
        last_verdict=verdict,
        last_intrinsic_value=85.50,
        last_price_checked=72.50,
        price_alert_threshold_pct=0.10,
    )


@pytest.mark.asyncio
async def test_weekly_report_genere_pdf(monkeypatch):
    """_execute_weekly_watchlist_report → ReportService.generate_watchlist_summary_pdf appelé."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://copilote:copilote@localhost:5432/copilote")
    monkeypatch.setenv("REPORT_EMAIL_TO", "yves@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    entries = [_make_entry("BNS"), _make_entry("TD", score=4, verdict="ACCEPTABLE")]

    mock_pool = AsyncMock()
    mock_wl_service = AsyncMock()
    mock_wl_service.list_entries.return_value = entries

    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool, \
         patch("app.workers.tasks.WatchlistService", return_value=mock_wl_service), \
         patch("app.workers.tasks.ReportService") as mock_report_cls, \
         patch("app.workers.tasks.EmailService") as mock_email_cls:

        mock_create_pool.return_value = mock_pool
        mock_report = MagicMock()
        mock_report.generate_watchlist_summary_pdf.return_value = b"%PDF-1.4 test"
        mock_report_cls.return_value = mock_report

        mock_email = AsyncMock()
        mock_email.send_report.return_value = True
        mock_email_cls.return_value = mock_email

        from app.workers.tasks import _execute_weekly_watchlist_report
        await _execute_weekly_watchlist_report()

    mock_report.generate_watchlist_summary_pdf.assert_called_once_with(entries)


@pytest.mark.asyncio
async def test_weekly_report_envoie_email(monkeypatch):
    """_execute_weekly_watchlist_report → EmailService.send_report appelé avec pdf_bytes non vide."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://copilote:copilote@localhost:5432/copilote")
    monkeypatch.setenv("REPORT_EMAIL_TO", "yves@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    entries = [_make_entry("BNS"), _make_entry("MSFT", score=2, verdict="REJETER")]
    fake_pdf = b"%PDF-1.4 watchlist-summary"

    mock_pool = AsyncMock()
    mock_wl_service = AsyncMock()
    mock_wl_service.list_entries.return_value = entries

    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool, \
         patch("app.workers.tasks.WatchlistService", return_value=mock_wl_service), \
         patch("app.workers.tasks.ReportService") as mock_report_cls, \
         patch("app.workers.tasks.EmailService") as mock_email_cls:

        mock_create_pool.return_value = mock_pool
        mock_report = MagicMock()
        mock_report.generate_watchlist_summary_pdf.return_value = fake_pdf
        mock_report_cls.return_value = mock_report

        mock_email = AsyncMock()
        mock_email.send_report.return_value = True
        mock_email_cls.return_value = mock_email

        from app.workers.tasks import _execute_weekly_watchlist_report
        await _execute_weekly_watchlist_report()

    mock_email.send_report.assert_called_once()
    call_kwargs = mock_email.send_report.call_args
    # pdf_bytes doit être non vide
    assert call_kwargs.kwargs.get("pdf_bytes") == fake_pdf or call_kwargs.args[2] == fake_pdf
    # destinataire correct
    to_arg = call_kwargs.kwargs.get("to") or call_kwargs.args[4]
    assert to_arg == "yves@example.com"


@pytest.mark.asyncio
async def test_weekly_report_watchlist_vide(monkeypatch):
    """0 entrées watchlist → EmailService.send_report non appelé."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://copilote:copilote@localhost:5432/copilote")
    monkeypatch.setenv("REPORT_EMAIL_TO", "yves@example.com")

    mock_pool = AsyncMock()
    mock_wl_service = AsyncMock()
    mock_wl_service.list_entries.return_value = []

    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool, \
         patch("app.workers.tasks.WatchlistService", return_value=mock_wl_service), \
         patch("app.workers.tasks.ReportService") as mock_report_cls, \
         patch("app.workers.tasks.EmailService") as mock_email_cls:

        mock_create_pool.return_value = mock_pool
        mock_report = MagicMock()
        mock_report_cls.return_value = mock_report

        mock_email = AsyncMock()
        mock_email_cls.return_value = mock_email

        from app.workers.tasks import _execute_weekly_watchlist_report
        await _execute_weekly_watchlist_report()

    mock_email.send_report.assert_not_called()
    mock_report.generate_watchlist_summary_pdf.assert_not_called()
