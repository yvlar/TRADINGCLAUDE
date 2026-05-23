"""Tests pour EmailService — SMTP stdlib et SendGrid."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_email_env(monkeypatch):
    """Nettoie les variables d'environnement email avant chaque test."""
    for var in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SENDGRID_API_KEY", "REPORT_EMAIL_TO"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.asyncio
async def test_email_service_smtp_ok(monkeypatch):
    """SMTP_HOST configuré + mock smtplib.SMTP → True retourné."""
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from app.services.email_service import EmailService

        service = EmailService()
        result = await service.send_report(
            subject="Rapport hebdomadaire",
            body_text="Corps du message",
            pdf_bytes=b"%PDF-1.4 test",
            filename="watchlist-2026-05-11.pdf",
            to="destinataire@example.com",
        )

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user@example.com", "secret")
    mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_email_service_sans_config():
    """SMTP_HOST absent + SENDGRID absent → False retourné, WARNING loggué."""
    from app.services.email_service import EmailService

    with patch("app.services.email_service.logger") as mock_logger:
        service = EmailService()
        result = await service.send_report(
            subject="Test",
            body_text="corps",
            pdf_bytes=b"pdf",
            filename="rapport.pdf",
            to="dest@example.com",
        )

    assert result is False
    mock_logger.warning.assert_called_once()
    assert service._enabled is False
    assert service._mode == "none"


@pytest.mark.asyncio
async def test_email_service_pdf_attache(monkeypatch):
    """send_report → message MIME contient une pièce jointe avec Content-Disposition: attachment."""
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    sent_messages: list = []

    def capture_send_message(msg):
        sent_messages.append(msg)

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = capture_send_message
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from app.services.email_service import EmailService

        service = EmailService()
        await service.send_report(
            subject="Rapport watchlist",
            body_text="Voir la pièce jointe.",
            pdf_bytes=b"%PDF-1.4 watchlist",
            filename="watchlist-2026-05-11.pdf",
            to="yves@example.com",
        )

    assert len(sent_messages) == 1
    payloads = sent_messages[0].get_payload()
    # La deuxième partie doit être la pièce jointe PDF
    attachments = [
        p for p in payloads
        if "attachment" in p.get("Content-Disposition", "")
    ]
    assert len(attachments) == 1
    assert "watchlist-2026-05-11.pdf" in attachments[0].get("Content-Disposition", "")


def test_email_service_sendgrid_priorite(monkeypatch):
    """SENDGRID_API_KEY présent + SMTP configuré → mode sendgrid sélectionné en priorité."""
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test-api-key")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    from app.services.email_service import EmailService

    service = EmailService()
    assert service._enabled is True
    assert service._mode == "sendgrid"

    # Vérifier que send_report appelle _send_sendgrid et non _send_smtp
    with patch.object(service, "_send_sendgrid", return_value=True) as mock_sg, \
         patch.object(service, "_send_smtp", return_value=True) as mock_smtp:
        import asyncio
        result = asyncio.run(service.send_report(
            subject="Test",
            body_text="corps",
            pdf_bytes=b"pdf",
            filename="rapport.pdf",
            to="dest@example.com",
        ))

    assert result is True
    mock_sg.assert_called_once()
    mock_smtp.assert_not_called()
