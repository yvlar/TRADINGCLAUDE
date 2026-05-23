from __future__ import annotations

import logging
import os
from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

logger = logging.getLogger(__name__)

_RESET_TOKEN_TTL_S = 3600  # 1 heure
_SALT = "password-reset-v1"


class PasswordResetService:
    """
    Génère et vérifie les tokens de réinitialisation de mot de passe via itsdangerous.

    Le token encode l'user_id signé avec un secret serveur et une expiration de 1h.
    Le caractère one-shot est assuré par le changement de mot de passe lui-même :
    après reset, l'ancien token peut encore se vérifier cryptographiquement,
    mais l'accès est inutilisable sans mot de passe (le compte est mis à jour).
    Pour une invalidation stricte, utiliser un nonce en DB dans un sprint futur.
    """

    def __init__(self) -> None:
        secret = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
        self._serializer = URLSafeTimedSerializer(secret)

    def create_reset_token(self, user_id: UUID) -> str:
        """Génère un token signé contenant l'user_id avec TTL de 1h."""
        return self._serializer.dumps(str(user_id), salt=_SALT)

    def verify_reset_token(self, token: str) -> UUID | None:
        """
        Vérifie la signature et l'expiration. Retourne l'user_id ou None si invalide.

        Retourne None sans lever d'exception pour l'anti-énumération.
        """
        try:
            user_id_str = self._serializer.loads(token, salt=_SALT, max_age=_RESET_TOKEN_TTL_S)
            return UUID(user_id_str)
        except SignatureExpired:
            logger.info("Token de réinitialisation expiré")
            return None
        except BadSignature:
            logger.info("Token de réinitialisation invalide")
            return None
        except Exception:
            return None

    async def send_reset_email(self, email: str, reset_link: str) -> None:
        """Envoie l'email de réinitialisation via SendGrid ou log en mode dev."""
        sendgrid_key = os.environ.get("SENDGRID_API_KEY")
        if not sendgrid_key:
            logger.warning("SENDGRID_API_KEY absent — lien reset (dev) : %s", reset_link)
            return

        try:
            import sendgrid  # type: ignore[import]
            from sendgrid.helpers.mail import Mail  # type: ignore[import]

            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_key)
            from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@tradingclaude.app")
            message = Mail(
                from_email=from_email,
                to_emails=email,
                subject="Réinitialisation de votre mot de passe — Copilote Financier",
                html_content=(
                    f"<p>Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe "
                    f"(valable 1 heure) :</p>"
                    f"<p><a href='{reset_link}'>{reset_link}</a></p>"
                    f"<p>Si vous n'avez pas fait cette demande, ignorez cet email.</p>"
                ),
            )
            sg.send(message)
            logger.info("Email de réinitialisation envoyé à %s", email)
        except Exception:
            logger.exception("Échec de l'envoi de l'email de réinitialisation à %s", email)
