"""Tests unitaires de l'ossature DCF déterministe (Sprint 132)."""
from __future__ import annotations

import math

import pytest

from app.services.valuation_calculations import (
    _ERP_MATURE,
    _RF_DEFAULT,
    capm_cost_of_equity,
    dcf_sensitivity_matrix,
    dcf_value_per_share,
    poids_capital,
    wacc_cmpc,
)


class TestCapm:
    def test_capm_valeur_connue(self):
        """Re = Rf + β × ERP = 0.0375 + 1.0 × 0.0423 = 0.0798."""
        re = capm_cost_of_equity(_RF_DEFAULT, 1.0, _ERP_MATURE)
        assert re == pytest.approx(0.0798)

    def test_capm_beta_eleve(self):
        re = capm_cost_of_equity(0.04, 1.5, 0.05)
        assert re == pytest.approx(0.04 + 1.5 * 0.05)

    @pytest.mark.parametrize("rf,beta,erp", [(None, 1.0, 0.04), (0.04, None, 0.04), (0.04, 1.0, None)])
    def test_capm_parametre_manquant(self, rf, beta, erp):
        assert capm_cost_of_equity(rf, beta, erp) is None


class TestWaccCmpc:
    def test_wacc_100pct_equity(self):
        """Sans dette, WACC = coût des capitaux propres."""
        wacc = wacc_cmpc(
            cost_equity=0.09, cost_debt=0.05, tax_rate=0.265, equity_weight=1.0, debt_weight=0.0
        )
        assert wacc == pytest.approx(0.09)

    def test_wacc_avec_dette(self):
        """WACC = 0.6×0.10 + 0.4×0.05×(1−0.265) = 0.06 + 0.0147 = 0.0747."""
        wacc = wacc_cmpc(
            cost_equity=0.10, cost_debt=0.05, tax_rate=0.265, equity_weight=0.6, debt_weight=0.4
        )
        assert wacc == pytest.approx(0.06 + 0.4 * 0.05 * 0.735)

    def test_wacc_cost_equity_manquant(self):
        assert (
            wacc_cmpc(
                cost_equity=None, cost_debt=0.05, tax_rate=0.265, equity_weight=0.6, debt_weight=0.4
            )
            is None
        )

    def test_wacc_dette_sans_cout(self):
        """Dette non nulle mais coût de dette manquant → None."""
        assert (
            wacc_cmpc(
                cost_equity=0.10, cost_debt=None, tax_rate=0.265, equity_weight=0.6, debt_weight=0.4
            )
            is None
        )


class TestPoidsCapital:
    def test_aucune_dette(self):
        assert poids_capital(0.0) == (1.0, 0.0)
        assert poids_capital(None) == (1.0, 0.0)

    def test_de_unitaire(self):
        """D/E = 1 → E/V = D/V = 0.5."""
        e_w, d_w = poids_capital(1.0)
        assert e_w == pytest.approx(0.5)
        assert d_w == pytest.approx(0.5)

    def test_de_eleve(self):
        e_w, d_w = poids_capital(0.5)
        assert d_w == pytest.approx(0.5 / 1.5)
        assert e_w == pytest.approx(1.0 / 1.5)


class TestDcfValuePerShare:
    def test_dcf_valeur_calculee_a_la_main(self):
        """
        FCF=10 (plat, g_high=0), 2 ans, WACC=10%, g=2%, 1000M actions, dette nette 0.
        PV explicite = 10/1.1 + 10/1.21 = 17.3554
        VT = 10×1.02 / (0.10−0.02) = 127.5 ; PV(VT) = 127.5 / 1.21 = 105.3719
        VE = 122.7273 ; par action = 122.7273 / 1.0 = 122.73
        """
        valeur = dcf_value_per_share(
            fcf_initial_bn=10.0,
            growth_high=0.0,
            years=2,
            wacc=0.10,
            terminal_growth=0.02,
            shares_outstanding_m=1000.0,
            net_debt_bn=0.0,
        )
        attendu = (10 / 1.1 + 10 / 1.21) + (10 * 1.02 / 0.08) / 1.21
        assert valeur == pytest.approx(attendu)
        assert valeur == pytest.approx(122.73, abs=0.01)

    def test_dcf_dette_nette_reduit_valeur(self):
        sans_dette = dcf_value_per_share(
            fcf_initial_bn=10.0, growth_high=0.0, years=2, wacc=0.10,
            terminal_growth=0.02, shares_outstanding_m=1000.0, net_debt_bn=0.0,
        )
        avec_dette = dcf_value_per_share(
            fcf_initial_bn=10.0, growth_high=0.0, years=2, wacc=0.10,
            terminal_growth=0.02, shares_outstanding_m=1000.0, net_debt_bn=20.0,
        )
        # 20 Md de dette / 1 Md d'actions = 20 $ de moins par action.
        assert sans_dette - avec_dette == pytest.approx(20.0)

    def test_dcf_wacc_inferieur_a_g_none(self):
        """WACC ≤ croissance terminale → Gordon diverge → None."""
        assert (
            dcf_value_per_share(
                fcf_initial_bn=10.0, growth_high=0.05, years=10, wacc=0.02,
                terminal_growth=0.03, shares_outstanding_m=1000.0,
            )
            is None
        )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"fcf_initial_bn": None},
            {"shares_outstanding_m": None},
            {"shares_outstanding_m": 0.0},
            {"fcf_initial_bn": -5.0},
            {"wacc": 0.0},
            {"growth_high": None},
            {"terminal_growth": None},
        ],
    )
    def test_dcf_donnee_manquante_ou_invalide_none(self, kwargs):
        base = dict(
            fcf_initial_bn=10.0, growth_high=0.05, years=10, wacc=0.09,
            terminal_growth=0.025, shares_outstanding_m=1000.0,
        )
        base.update(kwargs)
        assert dcf_value_per_share(**base) is None

    def test_dcf_valeur_finie(self):
        valeur = dcf_value_per_share(
            fcf_initial_bn=5.0, growth_high=0.08, years=10, wacc=0.09,
            terminal_growth=0.025, shares_outstanding_m=2000.0, net_debt_bn=3.0,
        )
        assert valeur is not None and math.isfinite(valeur)


class TestSensitivityMatrix:
    def test_matrice_dimensions_5x5(self):
        result = dcf_sensitivity_matrix(
            fcf_initial_bn=5.0, growth_high=0.08, years=10, shares_outstanding_m=2000.0,
        )
        assert result is not None
        wacc_range, growth_range, values = result
        assert len(wacc_range) == 5
        assert len(growth_range) == 5
        assert len(values) == 5
        for row in values:
            assert len(row) == 5
            for cell in row:
                assert isinstance(cell, float) and math.isfinite(cell)

    def test_matrice_monotone_wacc(self):
        """À g constant, une hausse de WACC réduit la valeur DCF (actualisation plus forte)."""
        _, _, values = dcf_sensitivity_matrix(
            fcf_initial_bn=5.0, growth_high=0.08, years=10, shares_outstanding_m=2000.0,
        )
        colonne_g_centrale = [ligne[2] for ligne in values]  # g = 2.5 %
        assert colonne_g_centrale == sorted(colonne_g_centrale, reverse=True)

    def test_matrice_monotone_croissance(self):
        """À WACC constant, une hausse de g terminale augmente la valeur DCF."""
        _, _, values = dcf_sensitivity_matrix(
            fcf_initial_bn=5.0, growth_high=0.08, years=10, shares_outstanding_m=2000.0,
        )
        ligne_wacc_centrale = values[2]  # WACC = 9 %
        assert ligne_wacc_centrale == sorted(ligne_wacc_centrale)

    def test_matrice_none_si_fcf_manquant(self):
        assert (
            dcf_sensitivity_matrix(
                fcf_initial_bn=None, growth_high=0.08, years=10, shares_outstanding_m=2000.0
            )
            is None
        )
