"""Tests unitaires de check_ratios_age — validation de fraîcheur des ratios (0 appel réseau)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.utils.ratios_freshness import (
    SEUIL_AVERTISSEMENT_J,
    SEUIL_FORT_J,
    check_ratios_age,
)


def _il_y_a(jours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=jours)


class TestCheckRatiosAge:
    def test_none_retourne_none(self):
        """fetched_at absent → aucun avertissement (honnêteté None, pas de faux positif)."""
        assert check_ratios_age(None, label="Ratios Graham") is None

    def test_recent_moins_de_30j_retourne_none(self):
        assert check_ratios_age(_il_y_a(10), label="Ratios Graham") is None

    def test_seuil_avertissement_exact_30j_retourne_none(self):
        """Exactement 30 j n'est pas > 30 j → pas encore d'avertissement."""
        assert check_ratios_age(_il_y_a(SEUIL_AVERTISSEMENT_J), label="Ratios Graham") is None

    def test_entre_30_et_90j_retourne_avertissement(self):
        message = check_ratios_age(_il_y_a(45), label="Ratios Graham")
        assert message is not None
        assert "Ratios Graham" in message
        assert f">{SEUIL_AVERTISSEMENT_J} j" in message
        assert f">{SEUIL_FORT_J} j" not in message

    def test_plus_de_90j_retourne_flag_fort(self):
        message = check_ratios_age(_il_y_a(120), label="Ratios Valorisation")
        assert message is not None
        assert "Ratios Valorisation" in message
        assert f">{SEUIL_FORT_J} j" in message
        assert "fiabilité réduite" in message

    def test_datetime_naif_traite_comme_utc(self):
        """Une date naïve (saisie manuelle) ne lève pas — alignée sur UTC avant comparaison."""
        naif = (datetime.now(timezone.utc) - timedelta(days=100)).replace(tzinfo=None)
        message = check_ratios_age(naif, label="Ratios Graham")
        assert message is not None
        assert f">{SEUIL_FORT_J} j" in message
