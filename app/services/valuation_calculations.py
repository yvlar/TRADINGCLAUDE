from __future__ import annotations

# Ossature DCF déterministe — valeur intrinsèque et matrice de sensibilité autrefois
# produites par le LLM, désormais calculées en Python pour fiabilité numérique et
# auditabilité (Sprint 132). Domaine distinct des scores de fraude/faillite de
# financial_calculations.py — d'où un module séparé (cohésion).
#
# Formules et hypothèses par défaut RECOPIÉES depuis
# .claude/skills/stock-valuation-triangulation/references/dcf.md — ne jamais les inventer.
# Chaque fonction est pure (calcul CPU, sans I/O), typée, et retourne None plutôt que de
# lever une exception sur donnée manquante / division par zéro (cf. donnees-financieres.md).

# --- Hypothèses par défaut (references/dcf.md) ---
_ERP_MATURE = 0.0423  # prime de risque actions Damodaran, mature market 2026
_RF_DEFAULT = 0.0375  # taux sans risque : obligation Canada/US 10 ans ~3.5-4.5 % → médian
_TAX_DEFAULT = 0.265  # taux d'imposition combiné fédéral + Québec
_BETA_DEFAULT = 1.0  # bêta de marché, faute de bêta propre à l'action
_RD_DEFAULT = 0.05  # coût de la dette : proxy IG corporate, faute de yield d'émission
_PROJECTION_YEARS = 10  # horizon de projection des FCF (references : 5-10 ans)
_G_TERMINAL_DEFAULT = 0.025  # croissance perpétuelle Gordon (references : 2-3 %)
_G_HIGH_MAX = 0.15  # plafond de croissance phase 1 (au-delà : wishful thinking selon Damodaran)
_WACC_DEFAULT = 0.09  # WACC mature par défaut si la CMPC n'est pas calculable

# Plages de la matrice de sensibilité (points de pourcentage) — grille de référence 5×5.
# WACC min (7 %) > g max (3.5 %) garantit Gordon fini sur chaque cellule.
_WACC_RANGE_PCT: tuple[float, ...] = (7.0, 8.0, 9.0, 10.0, 11.0)
_G_RANGE_PCT: tuple[float, ...] = (1.5, 2.0, 2.5, 3.0, 3.5)


def capm_cost_of_equity(
    rf: float | None, beta: float | None, erp: float | None
) -> float | None:
    """Coût des capitaux propres (CAPM) : Re = Rf + β × (Rm − Rf). None si un paramètre manque."""
    if rf is None or beta is None or erp is None:
        return None
    return rf + beta * erp


def wacc_cmpc(
    *,
    cost_equity: float | None,
    cost_debt: float | None,
    tax_rate: float | None,
    equity_weight: float | None,
    debt_weight: float | None,
) -> float | None:
    """
    Coût moyen pondéré du capital : WACC = (E/V)·Re + (D/V)·Rd·(1−T).
    None si la composante capitaux propres manque, ou si une dette non nulle manque ses
    paramètres (coût ou taux d'imposition).
    """
    if cost_equity is None or equity_weight is None:
        return None
    terme_equity = equity_weight * cost_equity
    terme_dette = 0.0
    if debt_weight is not None and debt_weight > 0:
        if cost_debt is None or tax_rate is None:
            return None
        terme_dette = debt_weight * cost_debt * (1 - tax_rate)
    return terme_equity + terme_dette


def poids_capital(debt_equity: float | None) -> tuple[float, float]:
    """
    Pondérations (E/V, D/V) dérivées du ratio dette/capitaux propres.
    Proxy comptable faute de valeurs de marché ; 100 % capitaux propres si D/E inconnu ou ≤ 0.
    """
    if debt_equity is None or debt_equity <= 0:
        return 1.0, 0.0
    d_v = debt_equity / (1 + debt_equity)
    return 1 - d_v, d_v


def dcf_value_per_share(
    *,
    fcf_initial_bn: float | None,
    growth_high: float | None,
    years: int,
    wacc: float | None,
    terminal_growth: float | None,
    shares_outstanding_m: float | None,
    net_debt_bn: float | None = 0.0,
) -> float | None:
    """
    Valeur intrinsèque DCF par action (Gordon à deux temps), montants en milliards.
    FCF de départ projeté à `growth_high` sur `years` ans et actualisé au WACC, valeur
    terminale Gordon actualisée, − dette nette, ÷ actions diluées. None si non calculable.
    Requiert WACC > croissance terminale (sinon la valeur terminale diverge).
    """
    if (
        fcf_initial_bn is None
        or growth_high is None
        or wacc is None
        or terminal_growth is None
        or shares_outstanding_m is None
    ):
        return None
    if shares_outstanding_m <= 0 or wacc <= 0 or wacc <= terminal_growth or fcf_initial_bn <= 0:
        return None

    pv_explicit = 0.0
    for t in range(1, years + 1):
        fcf_t = fcf_initial_bn * (1 + growth_high) ** t
        pv_explicit += fcf_t / (1 + wacc) ** t

    fcf_terminal = fcf_initial_bn * (1 + growth_high) ** years * (1 + terminal_growth)
    valeur_terminale = fcf_terminal / (wacc - terminal_growth)
    pv_terminale = valeur_terminale / (1 + wacc) ** years

    valeur_entreprise_bn = pv_explicit + pv_terminale
    valeur_capitaux_propres_bn = valeur_entreprise_bn - (net_debt_bn or 0.0)
    actions_bn = shares_outstanding_m / 1_000.0
    return valeur_capitaux_propres_bn / actions_bn


def dcf_sensitivity_matrix(
    *,
    fcf_initial_bn: float | None,
    growth_high: float | None,
    years: int,
    shares_outstanding_m: float | None,
    net_debt_bn: float | None = 0.0,
    wacc_range_pct: tuple[float, ...] = _WACC_RANGE_PCT,
    growth_range_pct: tuple[float, ...] = _G_RANGE_PCT,
) -> tuple[list[float], list[float], list[list[float]]] | None:
    """
    Matrice de sensibilité WACC × croissance terminale — chaque cellule = valeur DCF par
    action. Retourne (wacc_range, growth_range, values) en points de pourcentage, ou None
    si l'ossature DCF n'est pas calculable. Chaque cellule est un float fini (les plages
    de référence maintiennent WACC > g).
    """
    values: list[list[float]] = []
    for wacc_pct in wacc_range_pct:
        row: list[float] = []
        for g_pct in growth_range_pct:
            valeur = dcf_value_per_share(
                fcf_initial_bn=fcf_initial_bn,
                growth_high=growth_high,
                years=years,
                wacc=wacc_pct / 100.0,
                terminal_growth=g_pct / 100.0,
                shares_outstanding_m=shares_outstanding_m,
                net_debt_bn=net_debt_bn,
            )
            if valeur is None:
                return None
            row.append(round(valeur, 2))
        values.append(row)
    return list(wacc_range_pct), list(growth_range_pct), values
