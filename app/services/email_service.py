from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailService:
    """Envoie des emails avec pièce jointe PDF — SMTP stdlib ou SendGrid."""

    def __init__(self) -> None:
        self._sendgrid_key: str | None = os.environ.get("SENDGRID_API_KEY")
        self._smtp_host: str | None = os.environ.get("SMTP_HOST")
        self._smtp_port: int = int(os.environ.get("SMTP_PORT", "587"))
        self._smtp_user: str | None = os.environ.get("SMTP_USER")
        self._smtp_password: str | None = os.environ.get("SMTP_PASSWORD")

        if self._sendgrid_key:
            self._enabled = True
            self._mode = "sendgrid"
        elif self._smtp_host and self._smtp_user and self._smtp_password:
            self._enabled = True
            self._mode = "smtp"
        else:
            self._enabled = False
            self._mode = "none"

    async def send_report(
        self,
        subject: str,
        body_text: str,
        pdf_bytes: bytes,
        filename: str,
        to: str,
    ) -> bool:
        """
        Envoie un email avec le PDF en pièce jointe.
        Si désactivé → log WARNING, retourne False.
        Retourne True si envoi réussi, False sinon.
        """
        if not self._enabled:
            logger.warning("Email désactivé — aucune configuration SMTP/SendGrid trouvée")
            return False
        try:
            if self._mode == "sendgrid":
                return await asyncio.to_thread(
                    self._send_sendgrid, subject, body_text, pdf_bytes, filename, to
                )
            return await asyncio.to_thread(
                self._send_smtp, subject, body_text, pdf_bytes, filename, to
            )
        except Exception:
            logger.exception("Échec d'envoi d'email vers %s", to)
            return False

    def _send_smtp(
        self,
        subject: str,
        body_text: str,
        pdf_bytes: bytes,
        filename: str,
        to: str,
    ) -> bool:
        # invariant : appelé seulement si _mode == "smtp", donc host/user/password sont définis
        assert self._smtp_host is not None and self._smtp_user is not None
        assert self._smtp_password is not None

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = self._smtp_user
        msg["To"] = to
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(pdf_part)

        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.starttls()
            server.login(self._smtp_user, self._smtp_password)
            server.send_message(msg)
        return True

    def _send_sendgrid(
        self,
        subject: str,
        body_text: str,
        pdf_bytes: bytes,
        filename: str,
        to: str,
    ) -> bool:
        import base64

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import (
            Attachment,
            Disposition,
            FileContent,
            FileName,
            FileType,
            Mail,
        )

        mail = Mail(
            from_email=self._smtp_user or "noreply@copilote.ai",
            to_emails=to,
            subject=subject,
            plain_text_content=body_text,
        )
        encoded = base64.b64encode(pdf_bytes).decode()
        attachment = Attachment(
            FileContent(encoded),
            FileName(filename),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        mail.attachment = attachment

        sg = SendGridAPIClient(self._sendgrid_key)
        response = sg.send(mail)
        return response.status_code in (200, 202)
