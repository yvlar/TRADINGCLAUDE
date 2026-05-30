"""Tests unitaires des calculs financiers déterministes (Sprint 128).

Chaque vecteur attendu est calculé à la main depuis les formules/seuils des
références .claude/skills/earnings-quality-fraud-detection/references/.
"""
from __future__ import annotations

import pytest

from app.services.financial_calculations import (
    altman_z_score,
    beneish_m_score,
    graham_number,
    montier_c_score,
    piotroski_f_score,
    sloan_accrual_ratio,
)

# --- Beneish : entreprise « stable » (T == T-1, NI == CFO) ---
# Les 8 indices valent 1.0 et TATA = 0, donc M = somme des coefficients + constante.
_BENEISH_STABLE = dict(
    receivables_t=50, receivables_t1=50,
    sales_t=1000, sales_t1=1000,
    cogs_t=600, cogs_t1=600,
    current_assets_t=400, current_assets_t1=400,
    ppe_net_t=300, ppe_net_t1=300,
    total_assets_t=1000, total_assets_t1=1000,
    depreciation_t=50, depreciation_t1=50,
    sga_t=100, sga_t1=100,
    net_income_t=80, cfo_t=80,
    ltd_t=200, ltd_t1=200,
    current_liabilities_t=150, current_liabilities_t1=150,
)


class TestGrahamNumber:
    def test_valeur_connue(self):
        # √(22.5 × 10 × 20) = √4500 = 67.0820...
        assert graham_number(10.0, 20.0) == pytest.approx(67.08203932, rel=1e-6)

    def test_eps_none(self):
        assert graham_number(None, 20.0) is None

    def test_bvps_none(self):
        assert graham_number(10.0, None) is None

    def test_eps_negatif(self):
        # racine d'un produit négatif → None (pas d'exception)
        assert graham_number(-5.0, 20.0) is None

    def test_bvps_zero(self):
        assert graham_number(10.0, 0.0) is None


class TestAltmanZScore:
    def _vecteur(self, **overrides):
        base = dict(
            current_assets=100, current_liabilities=50, retained_earnings=40,
            ebit=30, total_assets=200, total_liabilities=150, sales=260,
            market_value_equity=300, book_value_equity=180,
        )
        base.update(overrides)
        return base

    def test_original_valeur_connue(self):
        # X1=0.25 X2=0.20 X3=0.15 X4=2.0 X5=1.3
        # Z = 1.2·0.25 + 1.4·0.20 + 3.3·0.15 + 0.6·2.0 + 1.0·1.3 = 3.575
        assert altman_z_score(**self._vecteur()) == pytest.approx(3.575, rel=1e-9)

    def test_private_variante(self):
        # X4 = book/TL = 180/150 = 1.2 ; Z' = 0.717·0.25 + 0.847·0.20 + 3.107·0.15 + 0.420·1.2 + 0.998·1.3
        attendu = 0.717 * 0.25 + 0.847 * 0.20 + 3.107 * 0.15 + 0.420 * 1.2 + 0.998 * 1.3
        assert altman_z_score(**self._vecteur(), variant="private") == pytest.approx(attendu, rel=1e-9)

    def test_service_variante_exclut_x5(self):
        attendu = 6.56 * 0.25 + 3.26 * 0.20 + 6.72 * 0.15 + 1.05 * 1.2
        assert altman_z_score(**self._vecteur(), variant="service") == pytest.approx(attendu, rel=1e-9)

    def test_societe_peu_endettee_depasse_50(self):
        # X4 = capitalisation / passifs très grand → Z légitimement > 50 (Sprint 128) :
        # le calcul ne plafonne pas ; la borne de plausibilité du schéma est élargie en conséquence.
        z = altman_z_score(**self._vecteur(market_value_equity=120_000, total_liabilities=1_000))
        assert z is not None and z > 50

    def test_banque_retourne_none(self):
        assert altman_z_score(**self._vecteur(), is_financial=True) is None

    def test_total_assets_zero_retourne_none(self):
        assert altman_z_score(**self._vecteur(total_assets=0)) is None

    def test_composante_manquante_retourne_none(self):
        assert altman_z_score(**self._vecteur(retained_earnings=None)) is None

    def test_original_market_value_manquant_none(self):
        assert altman_z_score(**self._vecteur(market_value_equity=None)) is None


class TestBeneishMScore:
    def test_entreprise_stable(self):
        # Tous indices = 1, TATA = 0 → M = -4.84 + 0.92 + 0.528 + 0.404 + 0.892 + 0.115 - 0.172 - 0.327
        assert beneish_m_score(**_BENEISH_STABLE) == pytest.approx(-2.48, abs=1e-9)

    def test_manipulateur_depasse_seuil(self):
        # DSRI et SGI gonflés (créances et ventes en forte hausse) → M franchit -1.78
        m = beneish_m_score(
            **{**_BENEISH_STABLE, "receivables_t": 150, "sales_t": 2000, "net_income_t": 200, "cfo_t": 50}
        )
        assert m is not None
        assert m > -1.78

    def test_banque_retourne_none(self):
        assert beneish_m_score(**{**_BENEISH_STABLE, "is_financial": True}) is None

    def test_donnee_manquante_retourne_none(self):
        assert beneish_m_score(**{**_BENEISH_STABLE, "sales_t1": None}) is None

    def test_division_par_zero_retourne_none(self):
        assert beneish_m_score(**{**_BENEISH_STABLE, "sales_t1": 0}) is None


class TestPiotroskiFScore:
    def _vecteur(self, **overrides):
        base = dict(
            net_income_t=100, total_assets_t=1000, total_assets_t1=900, net_income_t1=80,
            cfo_t=120, ltd_t=150, ltd_t1=200,
            current_assets_t=500, current_liabilities_t=250,
            current_assets_t1=400, current_liabilities_t1=250,
            sales_t=1000, sales_t1=900, cogs_t=600, cogs_t1=560,
            shares_issued_net=False,
        )
        base.update(overrides)
        return base

    def test_score_huit_sur_neuf(self):
        # 8 critères satisfaits, asset turnover stable (1.0 == 1.0) échoue le 9e
        assert piotroski_f_score(**self._vecteur()) == 8

    def test_banque_retourne_none(self):
        assert piotroski_f_score(**self._vecteur(is_financial=True)) is None

    def test_donnee_profitabilite_manquante_none(self):
        assert piotroski_f_score(**self._vecteur(net_income_t=None)) is None

    def test_critere_comparatif_manquant_non_accorde(self):
        # net_income_t1 absent → critère 3 (ROA en hausse) non accordé : 7 au lieu de 8
        assert piotroski_f_score(**self._vecteur(net_income_t1=None)) == 7


class TestMontierCScore:
    def _stable(self, **overrides):
        base = dict(
            net_income_t=80, cfo_t=80, net_income_t1=80, cfo_t1=80,
            receivables_t=50, receivables_t1=50, sales_t=1000, sales_t1=1000,
            inventory_t=100, inventory_t1=100, cogs_t=600, cogs_t1=600,
            depreciation_t=50, depreciation_t1=50, ppe_gross_t=400, ppe_gross_t1=400,
            total_assets_t=1000, total_assets_t1=1000,
        )
        base.update(overrides)
        return base

    def test_entreprise_propre_score_zero(self):
        assert montier_c_score(**self._stable()) == 0

    def test_croissance_actifs_declenche_signal(self):
        # TA +20 % > 10 % → signal 6 coché
        assert montier_c_score(**self._stable(total_assets_t=1200)) == 1

    def test_base_actifs_manquante_none(self):
        assert montier_c_score(**self._stable(total_assets_t1=None)) is None


class TestSloanAccrualRatio:
    def test_valeur_connue_actifs_moyens(self):
        # (100 - 60) / ((1000 + 900)/2) = 40 / 950 = 0.0421...
        assert sloan_accrual_ratio(
            net_income_t=100, cfo_t=60, total_assets_t=1000, total_assets_t1=900
        ) == pytest.approx(40 / 950, rel=1e-9)

    def test_sans_actifs_precedents_utilise_ta_courant(self):
        assert sloan_accrual_ratio(
            net_income_t=100, cfo_t=60, total_assets_t=1000
        ) == pytest.approx(0.04, rel=1e-9)

    def test_donnee_manquante_none(self):
        assert sloan_accrual_ratio(net_income_t=None, cfo_t=60, total_assets_t=1000) is None

    def test_actifs_nuls_none(self):
        assert sloan_accrual_ratio(
            net_income_t=100, cfo_t=60, total_assets_t=0, total_assets_t1=0
        ) is None
