from __future__ import annotations

from dataclasses import dataclass

# Calculs financiers déterministes — scores autrefois produits par le LLM, désormais
# calculés en Python pour fiabilité numérique et auditabilité (Sprint 128).
#
# Coefficients et seuils RECOPIÉS depuis .claude/skills/earnings-quality-fraud-detection/
# references/ — ne jamais les inventer. Chaque fonction est pure (calcul CPU, sans I/O),
# typée, et retourne None plutôt que de lever une exception sur donnée manquante ou
# division par zéro (cf. .claude/rules/donnees-financieres.md).

# --- Coefficients Altman (altman-z-score.md) ---
# Z original (industriel coté) : Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
_Z_ORIGINAL = (1.2, 1.4, 3.3, 0.6, 1.0)
# Z' (industriel privé) : X4 = book value of equity / total liabilities
_Z_PRIVATE = (0.717, 0.847, 3.107, 0.420, 0.998)
# Z'' (service / non-industriel) : exclut X5
_Z_SERVICE = (6.56, 3.26, 6.72, 1.05)

# --- Coefficients Beneish M-Score (beneish-m-score.md) ---
_M_CONST = -4.84
_M_DSRI = 0.92
_M_GMI = 0.528
_M_AQI = 0.404
_M_SGI = 0.892
_M_DEPI = 0.115
_M_SGAI = -0.172
_M_TATA = 4.679
_M_LVGI = -0.327


def _ratio(numerateur: float | None, denominateur: float | None) -> float | None:
    """Division sûre — None si un opérande manque ou si le dénominateur est nul."""
    if numerateur is None or denominateur is None or denominateur == 0:
        return None
    return numerateur / denominateur


def _diff(a: float | None, b: float | None) -> float | None:
    """Soustraction sûre — None si un opérande manque."""
    return a - b if a is not None and b is not None else None


def _somme(a: float | None, b: float | None) -> float | None:
    """Addition sûre — None si un opérande manque."""
    return a + b if a is not None and b is not None else None


def _part_non_courante(
    current_assets: float | None, ppe: float | None, total_assets: float | None
) -> float | None:
    """Part des actifs « non tangibles » (AQI Beneish) : 1 - (CA + PPE) / TA. Securities = 0."""
    if current_assets is None or ppe is None or total_assets is None or total_assets == 0:
        return None
    return 1 - (current_assets + ppe) / total_assets


# Étiquettes de variante exposées dans l'output persisté (auditabilité Sprint 131).
_Z_VARIANTE_LABELS = {"original": "Z_original", "private": "Z_prime", "service": "Z_double_prime"}

# Seuils (bas, haut) par variante Altman — recopiés de altman-z-score.md (cf. system.md).
# z > haut → zone_sure | bas ≤ z ≤ haut → zone_grise | z < bas → zone_detresse.
_Z_SEUILS = {
    "original": (1.81, 2.99),
    "private": (1.23, 2.90),
    "service": (1.10, 2.60),
}


def _altman_interpretation(
    z_score: float | None, variant: str, is_financial: bool
) -> str:
    """Libellé canonique du Z-Score — déterministe (Sprint courant).

    `non_applicable` prime : Altman exclut banques/assureurs/REIT. `DONNEES_MANQUANTES`
    (ASCII) si le score n'a pu être calculé (donnée d'entrée absente).
    """
    if is_financial:
        return "non_applicable"
    if z_score is None:
        return "DONNEES_MANQUANTES"
    bas, haut = _Z_SEUILS.get(variant, _Z_SEUILS["original"])
    if z_score > haut:
        return "zone_sure"
    if z_score >= bas:
        return "zone_grise"
    return "zone_detresse"


def _beneish_interpretation(m_score: float | None, is_financial: bool) -> str:
    """Libellé canonique du M-Score — déterministe (Sprint courant).

    Seuils Beneish : M ≤ −2.22 → non_manipulateur | −2.22 < M ≤ −1.78 → zone_grise |
    M > −1.78 → manipulateur. `non_applicable` pour les financières (hors échantillon).
    """
    if is_financial:
        return "non_applicable"
    if m_score is None:
        return "DONNEES_MANQUANTES"
    if m_score <= -2.22:
        return "non_manipulateur"
    if m_score <= -1.78:
        return "zone_grise"
    return "manipulateur"


@dataclass(frozen=True)
class BeneishComponents:
    """Les 8 indices intermédiaires du M-Score de Beneish + le score agrégé (Sprint 131).

    Chaque indice peut valoir None indépendamment du score : une sous-composante
    calculable est persistée même si une autre manque (auditabilité partielle).
    """

    dsri: float | None
    gmi: float | None
    aqi: float | None
    sgi: float | None
    depi: float | None
    sgai: float | None
    tata: float | None
    lvgi: float | None
    m_score: float | None
    interpretation: str = "DONNEES_MANQUANTES"


@dataclass(frozen=True)
class AltmanComponents:
    """Les 5 termes X1-X5 du Z-Score d'Altman + variante et score agrégé (Sprint 131).

    X5 vaut None pour la variante service (Z'' exclut Sales/TA).
    """

    x1: float | None
    x2: float | None
    x3: float | None
    x4: float | None
    x5: float | None
    variante: str
    z_score: float | None
    interpretation: str = "DONNEES_MANQUANTES"


@dataclass(frozen=True)
class CritereBinaire:
    """Un critère/signal binaire déterministe : libellé, booléen accordé, détail chiffré."""

    nom: str
    valeur: bool
    detail: str


@dataclass(frozen=True)
class PiotroskiComponents:
    """Les 9 critères de Piotroski + le F-Score agrégé (Sprint 142).

    `criteres` est vide quand le score n'est pas calculable (financière ou donnée de
    base manquante) — l'appelant conserve alors la sortie LLM. Sinon, par construction,
    `sum(c.valeur for c in criteres) == f_score`.
    """

    criteres: list[CritereBinaire]
    f_score: int | None


@dataclass(frozen=True)
class MontierComponents:
    """Les 6 signaux de Montier + le C-Score agrégé (Sprint 142).

    `signaux` est vide quand le score n'est pas calculable (base d'actifs manquante).
    Sinon, par construction, `sum(s.valeur for s in signaux) == c_score`.
    """

    signaux: list[CritereBinaire]
    c_score: int | None


def _pct(valeur: float | None) -> str:
    """Formate une fraction en pourcentage pour les détails d'audit — « n/d » si None."""
    return f"{valeur:.1%}" if valeur is not None else "n/d"


def _detail_comparatif(libelle: str, t: float | None, t1: float | None, fmt: str = ".1%") -> str:
    """Détail « libellé T vs T-1 » — « libellé : donnée manquante » si une valeur manque."""
    if t is None or t1 is None:
        return f"{libelle} : donnée manquante"
    return f"{libelle} {t:{fmt}} vs T-1 {t1:{fmt}}"


def graham_number(eps: float | None, bvps: float | None) -> float | None:
    """
    Nombre de Graham : √(22.5 × EPS × BVPS) (variables-financieres.md).
    None si EPS ou BVPS manquant ou ≤ 0 — la racine d'un produit négatif n'est pas définie
    et un BPA/valeur comptable négatif rend la borne Graham dénuée de sens.
    """
    if eps is None or bvps is None or eps <= 0 or bvps <= 0:
        return None
    return (22.5 * eps * bvps) ** 0.5


def altman_z_score_detail(
    *,
    current_assets: float | None,
    current_liabilities: float | None,
    retained_earnings: float | None,
    ebit: float | None,
    total_assets: float | None,
    total_liabilities: float | None,
    sales: float | None,
    market_value_equity: float | None = None,
    book_value_equity: float | None = None,
    variant: str = "original",
    is_financial: bool = False,
) -> AltmanComponents:
    """
    Détail du Z-Score d'Altman (1968) — termes X1-X5 + score agrégé. `variant` ∈
    {original, private, service}. Banques/assureurs/REIT → tous les termes None
    (modèle inapplicable). Un terme calculable est exposé même si le score agrégé
    est None (auditabilité, Sprint 131). Jamais d'exception.
    """
    variante = _Z_VARIANTE_LABELS.get(variant, variant)
    if is_financial or total_assets is None or total_assets == 0:
        return AltmanComponents(
            None, None, None, None, None, variante, None,
            _altman_interpretation(None, variant, is_financial),
        )

    working_capital = (
        current_assets - current_liabilities
        if current_assets is not None and current_liabilities is not None
        else None
    )
    x1 = _ratio(working_capital, total_assets)
    x2 = _ratio(retained_earnings, total_assets)
    x3 = _ratio(ebit, total_assets)
    # X4 = market value of equity / TL (original) ou book equity / TL (private, service)
    equity = market_value_equity if variant == "original" else book_value_equity
    x4 = _ratio(equity, total_liabilities)
    # X5 = Sales / TA — exclu de la variante service (Z'')
    x5 = None if variant == "service" else _ratio(sales, total_assets)

    if variant == "service":
        if x1 is None or x2 is None or x3 is None or x4 is None:
            z = None
        else:
            a, b, c, d = _Z_SERVICE
            z = a * x1 + b * x2 + c * x3 + d * x4
    else:
        if x1 is None or x2 is None or x3 is None or x4 is None or x5 is None:
            z = None
        else:
            a, b, c, d, e = _Z_PRIVATE if variant == "private" else _Z_ORIGINAL
            z = a * x1 + b * x2 + c * x3 + d * x4 + e * x5
    return AltmanComponents(
        x1, x2, x3, x4, x5, variante, z,
        _altman_interpretation(z, variant, is_financial),
    )


def altman_z_score(
    *,
    current_assets: float | None,
    current_liabilities: float | None,
    retained_earnings: float | None,
    ebit: float | None,
    total_assets: float | None,
    total_liabilities: float | None,
    sales: float | None,
    market_value_equity: float | None = None,
    book_value_equity: float | None = None,
    variant: str = "original",
    is_financial: bool = False,
) -> float | None:
    """Z-Score agrégé d'Altman — voir `altman_z_score_detail` pour les termes X1-X5."""
    return altman_z_score_detail(
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        retained_earnings=retained_earnings,
        ebit=ebit,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        sales=sales,
        market_value_equity=market_value_equity,
        book_value_equity=book_value_equity,
        variant=variant,
        is_financial=is_financial,
    ).z_score


def beneish_m_score_detail(
    *,
    receivables_t: float | None,
    receivables_t1: float | None,
    sales_t: float | None,
    sales_t1: float | None,
    cogs_t: float | None,
    cogs_t1: float | None,
    current_assets_t: float | None,
    current_assets_t1: float | None,
    ppe_net_t: float | None,
    ppe_net_t1: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None,
    depreciation_t: float | None,
    depreciation_t1: float | None,
    sga_t: float | None,
    sga_t1: float | None,
    net_income_t: float | None,
    cfo_t: float | None,
    ltd_t: float | None,
    ltd_t1: float | None,
    current_liabilities_t: float | None,
    current_liabilities_t1: float | None,
    is_financial: bool = False,
) -> BeneishComponents:
    """
    Détail du M-Score de Beneish (1999) — 8 indices T/T-1 + score agrégé.
    Banques/assureurs/REIT → tous les indices None (exclus de l'échantillon d'origine).
    Un indice calculable est exposé même si le score agrégé est None (auditabilité,
    Sprint 131). AQI : « titres » (securities) supposés nuls (champ absent du contrat).
    """
    if is_financial:
        return BeneishComponents(
            None, None, None, None, None, None, None, None, None,
            _beneish_interpretation(None, is_financial),
        )

    # DSRI = (Recv_t / Sales_t) / (Recv_{t-1} / Sales_{t-1})
    dsri = _ratio(_ratio(receivables_t, sales_t), _ratio(receivables_t1, sales_t1))

    # GMI = marge brute_{t-1} / marge brute_t
    gm_t = _ratio(_diff(sales_t, cogs_t), sales_t)
    gm_t1 = _ratio(_diff(sales_t1, cogs_t1), sales_t1)
    gmi = _ratio(gm_t1, gm_t)

    # AQI = (1 - (CA_t + PPE_t)/TA_t) / (1 - (CA_{t-1} + PPE_{t-1})/TA_{t-1})  [securities = 0]
    aqi_t = _part_non_courante(current_assets_t, ppe_net_t, total_assets_t)
    aqi_t1 = _part_non_courante(current_assets_t1, ppe_net_t1, total_assets_t1)
    aqi = _ratio(aqi_t, aqi_t1)

    # SGI = Sales_t / Sales_{t-1}
    sgi = _ratio(sales_t, sales_t1)

    # DEPI = (Dep_{t-1}/(Dep_{t-1}+PPE_{t-1})) / (Dep_t/(Dep_t+PPE_t))
    depi_t = _ratio(depreciation_t, _somme(depreciation_t, ppe_net_t))
    depi_t1 = _ratio(depreciation_t1, _somme(depreciation_t1, ppe_net_t1))
    depi = _ratio(depi_t1, depi_t)

    # SGAI = (SGA_t/Sales_t) / (SGA_{t-1}/Sales_{t-1})
    sgai = _ratio(_ratio(sga_t, sales_t), _ratio(sga_t1, sales_t1))

    # TATA = (Net Income_t - CFO_t) / TA_t
    tata = _ratio(_diff(net_income_t, cfo_t), total_assets_t)

    # LVGI = ((LTD_t + CL_t)/TA_t) / ((LTD_{t-1} + CL_{t-1})/TA_{t-1})
    lev_t = _ratio(_somme(ltd_t, current_liabilities_t), total_assets_t)
    lev_t1 = _ratio(_somme(ltd_t1, current_liabilities_t1), total_assets_t1)
    lvgi = _ratio(lev_t, lev_t1)

    if (
        dsri is None
        or gmi is None
        or aqi is None
        or sgi is None
        or depi is None
        or sgai is None
        or tata is None
        or lvgi is None
    ):
        m_score = None
    else:
        m_score = (
            _M_CONST
            + _M_DSRI * dsri
            + _M_GMI * gmi
            + _M_AQI * aqi
            + _M_SGI * sgi
            + _M_DEPI * depi
            + _M_SGAI * sgai
            + _M_TATA * tata
            + _M_LVGI * lvgi
        )
    return BeneishComponents(
        dsri, gmi, aqi, sgi, depi, sgai, tata, lvgi, m_score,
        _beneish_interpretation(m_score, is_financial),
    )


def beneish_m_score(
    *,
    receivables_t: float | None,
    receivables_t1: float | None,
    sales_t: float | None,
    sales_t1: float | None,
    cogs_t: float | None,
    cogs_t1: float | None,
    current_assets_t: float | None,
    current_assets_t1: float | None,
    ppe_net_t: float | None,
    ppe_net_t1: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None,
    depreciation_t: float | None,
    depreciation_t1: float | None,
    sga_t: float | None,
    sga_t1: float | None,
    net_income_t: float | None,
    cfo_t: float | None,
    ltd_t: float | None,
    ltd_t1: float | None,
    current_liabilities_t: float | None,
    current_liabilities_t1: float | None,
    is_financial: bool = False,
) -> float | None:
    """M-Score agrégé de Beneish — voir `beneish_m_score_detail` pour les 8 indices."""
    return beneish_m_score_detail(
        receivables_t=receivables_t,
        receivables_t1=receivables_t1,
        sales_t=sales_t,
        sales_t1=sales_t1,
        cogs_t=cogs_t,
        cogs_t1=cogs_t1,
        current_assets_t=current_assets_t,
        current_assets_t1=current_assets_t1,
        ppe_net_t=ppe_net_t,
        ppe_net_t1=ppe_net_t1,
        total_assets_t=total_assets_t,
        total_assets_t1=total_assets_t1,
        depreciation_t=depreciation_t,
        depreciation_t1=depreciation_t1,
        sga_t=sga_t,
        sga_t1=sga_t1,
        net_income_t=net_income_t,
        cfo_t=cfo_t,
        ltd_t=ltd_t,
        ltd_t1=ltd_t1,
        current_liabilities_t=current_liabilities_t,
        current_liabilities_t1=current_liabilities_t1,
        is_financial=is_financial,
    ).m_score


def piotroski_f_score_detail(
    *,
    net_income_t: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None,
    net_income_t1: float | None,
    cfo_t: float | None,
    ltd_t: float | None,
    ltd_t1: float | None,
    current_assets_t: float | None,
    current_liabilities_t: float | None,
    current_assets_t1: float | None,
    current_liabilities_t1: float | None,
    sales_t: float | None,
    sales_t1: float | None,
    cogs_t: float | None,
    cogs_t1: float | None,
    shares_issued_net: bool | None,
    is_financial: bool = False,
) -> PiotroskiComponents:
    """
    Détail du F-Score de Piotroski (2000) — 9 critères binaires + score agrégé (Sprint 142).
    Financières → score None et `criteres` vide (marges/rotation d'actifs non comparables).
    None aussi si la donnée de profitabilité de base manque (NI_t, TA_t, CFO_t). Un critère
    dont la donnée comparative manque n'est pas accordé (False) — le score reste un entier
    déterministe et `sum(c.valeur) == f_score` par construction.
    """
    if is_financial:
        return PiotroskiComponents([], None)
    if net_income_t is None or total_assets_t is None or total_assets_t == 0 or cfo_t is None:
        return PiotroskiComponents([], None)

    roa_t = net_income_t / total_assets_t
    roa_t1 = _ratio(net_income_t1, total_assets_t1)
    ltd_ta_t = _ratio(ltd_t, total_assets_t)
    ltd_ta_t1 = _ratio(ltd_t1, total_assets_t1)
    cr_t = _ratio(current_assets_t, current_liabilities_t)
    cr_t1 = _ratio(current_assets_t1, current_liabilities_t1)
    gm_t = _ratio(_diff(sales_t, cogs_t), sales_t)
    gm_t1 = _ratio(_diff(sales_t1, cogs_t1), sales_t1)
    turnover_t = _ratio(sales_t, total_assets_t)
    turnover_t1 = _ratio(sales_t1, total_assets_t1)

    criteres = [
        CritereBinaire("ROA positif", roa_t > 0, f"ROA = {_pct(roa_t)}"),
        CritereBinaire("CFO positif", cfo_t > 0, f"CFO = {cfo_t:,.0f}"),
        CritereBinaire(
            "ROA en hausse",
            roa_t1 is not None and roa_t > roa_t1,
            _detail_comparatif("ROA", roa_t, roa_t1),
        ),
        CritereBinaire(
            "CFO > résultat net (accruals)",
            cfo_t > net_income_t,
            f"CFO {cfo_t:,.0f} vs RN {net_income_t:,.0f}",
        ),
        CritereBinaire(
            "Levier long terme en baisse",
            ltd_ta_t is not None and ltd_ta_t1 is not None and ltd_ta_t < ltd_ta_t1,
            _detail_comparatif("LTD/actifs", ltd_ta_t, ltd_ta_t1),
        ),
        CritereBinaire(
            "Ratio de liquidité en hausse",
            cr_t is not None and cr_t1 is not None and cr_t > cr_t1,
            _detail_comparatif("liquidité", cr_t, cr_t1, fmt=".2f"),
        ),
        CritereBinaire(
            "Pas d'émission nette d'actions",
            shares_issued_net is False,
            "aucune émission nette d'actions"
            if shares_issued_net is False
            else (
                "émission nette d'actions sur l'exercice"
                if shares_issued_net is True
                else "information sur l'émission d'actions manquante"
            ),
        ),
        CritereBinaire(
            "Marge brute en hausse",
            gm_t is not None and gm_t1 is not None and gm_t > gm_t1,
            _detail_comparatif("marge brute", gm_t, gm_t1),
        ),
        CritereBinaire(
            "Rotation des actifs en hausse",
            turnover_t is not None and turnover_t1 is not None and turnover_t > turnover_t1,
            _detail_comparatif("rotation", turnover_t, turnover_t1, fmt=".2f"),
        ),
    ]
    return PiotroskiComponents(criteres, sum(1 for c in criteres if c.valeur))


def piotroski_f_score(
    *,
    net_income_t: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None,
    net_income_t1: float | None,
    cfo_t: float | None,
    ltd_t: float | None,
    ltd_t1: float | None,
    current_assets_t: float | None,
    current_liabilities_t: float | None,
    current_assets_t1: float | None,
    current_liabilities_t1: float | None,
    sales_t: float | None,
    sales_t1: float | None,
    cogs_t: float | None,
    cogs_t1: float | None,
    shares_issued_net: bool | None,
    is_financial: bool = False,
) -> int | None:
    """F-Score agrégé de Piotroski — voir `piotroski_f_score_detail` pour les 9 critères."""
    return piotroski_f_score_detail(
        net_income_t=net_income_t,
        total_assets_t=total_assets_t,
        total_assets_t1=total_assets_t1,
        net_income_t1=net_income_t1,
        cfo_t=cfo_t,
        ltd_t=ltd_t,
        ltd_t1=ltd_t1,
        current_assets_t=current_assets_t,
        current_liabilities_t=current_liabilities_t,
        current_assets_t1=current_assets_t1,
        current_liabilities_t1=current_liabilities_t1,
        sales_t=sales_t,
        sales_t1=sales_t1,
        cogs_t=cogs_t,
        cogs_t1=cogs_t1,
        shares_issued_net=shares_issued_net,
        is_financial=is_financial,
    ).f_score


def montier_c_score_detail(
    *,
    net_income_t: float | None,
    cfo_t: float | None,
    net_income_t1: float | None,
    cfo_t1: float | None,
    receivables_t: float | None,
    receivables_t1: float | None,
    sales_t: float | None,
    sales_t1: float | None,
    inventory_t: float | None,
    inventory_t1: float | None,
    cogs_t: float | None,
    cogs_t1: float | None,
    depreciation_t: float | None,
    depreciation_t1: float | None,
    ppe_gross_t: float | None,
    ppe_gross_t1: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None,
) -> MontierComponents:
    """
    Détail du C-Score de Montier (« Cooking the books ») — 6 signaux binaires + score
    agrégé (Sprint 142). Score None et `signaux` vide si la base de croissance des actifs
    manque (TA_t, TA_{t-1}). Signal #1 approximé sur T vs T-1 (la version d'origine couvre
    4 ans glissants) ; signal #4 (« autres actifs courants ») non calculable depuis le
    contrat de données → jamais coché. Un signal dont la donnée manque n'est pas coché ;
    `sum(s.valeur) == c_score` par construction.
    """
    if total_assets_t is None or total_assets_t1 is None or total_assets_t1 == 0:
        return MontierComponents([], None)

    gap_t = _diff(net_income_t, cfo_t)
    gap_t1 = _diff(net_income_t1, cfo_t1)
    dso_index = _ratio(_ratio(receivables_t, sales_t), _ratio(receivables_t1, sales_t1))
    dio_index = _ratio(_ratio(inventory_t, cogs_t), _ratio(inventory_t1, cogs_t1))
    dep_index = _ratio(_ratio(depreciation_t, ppe_gross_t), _ratio(depreciation_t1, ppe_gross_t1))
    croissance_actifs = total_assets_t / total_assets_t1 - 1

    signaux = [
        CritereBinaire(
            "Divergence résultat net / CFO qui se creuse",
            gap_t is not None and gap_t1 is not None and gap_t > gap_t1,
            _detail_comparatif("écart RN-CFO", gap_t, gap_t1, fmt=",.0f"),
        ),
        CritereBinaire(
            "Jours de créances (DSO) en forte hausse",
            dso_index is not None and dso_index > 1.10,
            f"indice DSO = {dso_index:.2f}"
            if dso_index is not None
            else "indice DSO indéterminé (donnée manquante)",
        ),
        CritereBinaire(
            "Jours de stocks (DIO) en forte hausse",
            dio_index is not None and dio_index > 1.10,
            f"indice DIO = {dio_index:.2f}"
            if dio_index is not None
            else "indice DIO indéterminé (donnée manquante)",
        ),
        # Signal #4 d'origine — « autres actifs courants » non disponible dans le contrat
        # de données → jamais coché (cohérent avec le score agrégé qui l'ignore).
        CritereBinaire(
            "Autres actifs courants / ventes en hausse",
            False,
            "non calculable depuis le contrat de données",
        ),
        CritereBinaire(
            "Taux de dépréciation en baisse",
            dep_index is not None and dep_index < 0.95,
            f"indice dépréciation/PPE = {dep_index:.2f}"
            if dep_index is not None
            else "indice dépréciation/PPE indéterminé (donnée manquante)",
        ),
        CritereBinaire(
            "Croissance des actifs > 10 %",
            croissance_actifs > 0.10,
            f"croissance des actifs = {_pct(croissance_actifs)}",
        ),
    ]
    return MontierComponents(signaux, sum(1 for s in signaux if s.valeur))


def montier_c_score(
    *,
    net_income_t: float | None,
    cfo_t: float | None,
    net_income_t1: float | None,
    cfo_t1: float | None,
    receivables_t: float | None,
    receivables_t1: float | None,
    sales_t: float | None,
    sales_t1: float | None,
    inventory_t: float | None,
    inventory_t1: float | None,
    cogs_t: float | None,
    cogs_t1: float | None,
    depreciation_t: float | None,
    depreciation_t1: float | None,
    ppe_gross_t: float | None,
    ppe_gross_t1: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None,
) -> int | None:
    """C-Score agrégé de Montier — voir `montier_c_score_detail` pour les 6 signaux."""
    return montier_c_score_detail(
        net_income_t=net_income_t,
        cfo_t=cfo_t,
        net_income_t1=net_income_t1,
        cfo_t1=cfo_t1,
        receivables_t=receivables_t,
        receivables_t1=receivables_t1,
        sales_t=sales_t,
        sales_t1=sales_t1,
        inventory_t=inventory_t,
        inventory_t1=inventory_t1,
        cogs_t=cogs_t,
        cogs_t1=cogs_t1,
        depreciation_t=depreciation_t,
        depreciation_t1=depreciation_t1,
        ppe_gross_t=ppe_gross_t,
        ppe_gross_t1=ppe_gross_t1,
        total_assets_t=total_assets_t,
        total_assets_t1=total_assets_t1,
    ).c_score


def sloan_accrual_ratio(
    *,
    net_income_t: float | None,
    cfo_t: float | None,
    total_assets_t: float | None,
    total_assets_t1: float | None = None,
) -> float | None:
    """
    Ratio d'accruals de Sloan (1996), version totaux : (NI - CFO) / actifs moyens.
    Actifs moyens = (TA_t + TA_{t-1})/2 si TA_{t-1} fourni, sinon TA_t.
    None si NI, CFO ou TA_t manque, ou si le dénominateur est nul.
    """
    if net_income_t is None or cfo_t is None or total_assets_t is None:
        return None
    actifs_moyens = (
        (total_assets_t + total_assets_t1) / 2 if total_assets_t1 is not None else total_assets_t
    )
    return _ratio(net_income_t - cfo_t, actifs_moyens)
