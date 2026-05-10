"""Formate une AnalyzeResponse JSON en rapport Markdown investissement."""
from __future__ import annotations

from datetime import date
from typing import Any

_MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def format_analyse_markdown(data: dict[str, Any]) -> str:
    """Point d'entrée — convertit une AnalyzeResponse dict en Markdown complet."""
    ticker = data.get("ticker", "N/A").upper()
    today = date.today()
    skills_applied: list[str] = data.get("skills_applied", [])
    cost_usd: float = data.get("cost_usd", 0.0)
    created_at: str = data.get("created_at", "")
    analysis_id: str = data.get("analysis_id", "N/A")

    graham = data.get("graham") or {}
    earnings = data.get("earnings_quality")
    dorsey = data.get("dorsey")
    buffett = data.get("buffett")
    valuation = data.get("valuation")
    thesis = data.get("thesis")
    munger = data.get("munger")
    tax = data.get("canadian_tax")

    verdict_final = thesis.get("verdict_final") if thesis else None
    position_size = thesis.get("position_size_pct") if thesis else None

    parts: list[str] = [
        _header(ticker, today, verdict_final, position_size),
        _toc(data),
        _resume_executif(ticker, data),
        _section_graham(graham),
    ]
    if earnings:
        parts.append(_section_earnings(earnings))
    if dorsey:
        parts.append(_section_dorsey(dorsey))
    if buffett:
        parts.append(_section_buffett(buffett))
    if valuation:
        parts.append(_section_valuation(valuation))
    if thesis:
        parts.append(_section_thesis(thesis))
    if munger:
        parts.append(_section_munger(munger))
    if tax:
        parts.append(_section_tax(tax))

    parts.append(_footer(ticker, skills_applied, cost_usd, analysis_id, created_at))

    return "\n\n---\n\n".join(parts)


# ─── Utilitaires ──────────────────────────────────────────────────────────────

def _pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f} %"


def _val(value: float | None, fmt: str = ".2f") -> str:
    if value is None:
        return "N/A"
    return f"{value:{fmt}}"


def _date_fr(d: date) -> str:
    return f"{d.day} {_MONTHS_FR[d.month]} {d.year}"


# ─── En-tête ──────────────────────────────────────────────────────────────────

def _header(
    ticker: str,
    today: date,
    verdict_final: str | None,
    position_size: float | None,
) -> str:
    lines = [
        f"# Analyse d'Investissement — {ticker}",
        f"**Date d'analyse : {_date_fr(today)} | Analyste : Claude (multi-skill)**",
        "",
    ]
    if verdict_final and position_size is not None:
        lines.append(
            f"> **Verdict final : {verdict_final} "
            f"| Position recommandée : {position_size:.1f} % du portefeuille**"
        )
    elif verdict_final:
        lines.append(f"> **Verdict final : {verdict_final}**")
    return "\n".join(lines)


# ─── Table des matières ───────────────────────────────────────────────────────

def _toc(data: dict[str, Any]) -> str:
    lines = ["## Table des matières", ""]
    idx = 1
    items = [
        ("Résumé exécutif", "#résumé-exécutif", True),
        ("Analyse Graham", "#analyse-graham", True),
        ("Qualité des bénéfices (Earnings Quality)", "#qualité-des-bénéfices", bool(data.get("earnings_quality"))),
        ("Analyse du Moat (Dorsey)", "#analyse-du-moat-dorsey", bool(data.get("dorsey"))),
        ("Qualité Buffett", "#qualité-buffett", bool(data.get("buffett"))),
        ("Valorisation par triangulation", "#valorisation-par-triangulation", bool(data.get("valuation"))),
        ("Thèse d'investissement", "#thèse-dinvestissement", bool(data.get("thesis"))),
        ("Analyse comportementale (Munger)", "#analyse-comportementale-munger", bool(data.get("munger"))),
        ("Fiscalité canadienne", "#fiscalité-canadienne", bool(data.get("canadian_tax"))),
    ]
    for label, anchor, active in items:
        if active:
            lines.append(f"{idx}. [{label}]({anchor})")
            idx += 1
    return "\n".join(lines)


# ─── Résumé exécutif ──────────────────────────────────────────────────────────

def _resume_executif(ticker: str, data: dict[str, Any]) -> str:
    graham = data.get("graham") or {}
    thesis = data.get("thesis")
    dorsey = data.get("dorsey")
    earnings = data.get("earnings_quality")
    valuation = data.get("valuation")
    buffett = data.get("buffett")
    tax = data.get("canadian_tax")

    lines = ["## Résumé exécutif", "", "| Dimension | Résultat |", "|-----------|---------|"]

    g_verdict = graham.get("verdict", "N/A")
    g_score = graham.get("defensive_score", "N/A")
    lines.append(f"| **Graham** | {g_verdict} ({g_score}/8 défensif) |")

    marge = graham.get("marge_securite")
    if marge is not None:
        lines.append(f"| Marge de sécurité | {_pct(marge)} |")

    if earnings:
        lines.append(f"| **Earnings Quality** | {earnings.get('verdict', 'N/A')} |")
        f_score_val = (earnings.get("f_score") or {}).get("f_score")
        if f_score_val is not None:
            lines.append(f"| F-Score Piotroski | {f_score_val}/9 |")

    if dorsey:
        lines.append(
            f"| **Moat** | {dorsey.get('moat_type', 'N/A')} "
            f"— durabilité ROIC {dorsey.get('roic_durability', 'N/A')} |"
        )

    if buffett:
        b_score = buffett.get("quality_score", "N/A")
        lines.append(f"| **Buffett Quality** | {buffett.get('verdict', 'N/A')} ({b_score}/4) |")

    if valuation:
        f_basse = _val(valuation.get("fourchette_basse"))
        f_haute = _val(valuation.get("fourchette_haute"))
        lines.append(f"| **Valorisation** | {valuation.get('verdict', 'N/A')} — fourchette {f_basse}–{f_haute} |")
        lines.append(f"| Marge sécurité composite | {_pct(valuation.get('marge_securite_composite'))} |")

    if thesis:
        ev = _calc_expected_value(thesis)
        lines.append(f"| **Verdict final** | {thesis.get('verdict_final', 'N/A')} |")
        pos = thesis.get("position_size_pct")
        lines.append(f"| Position recommandée | {_val(pos, '.1f')} % du portefeuille |")
        if ev is not None:
            lines.append(f"| Espérance pondérée | {ev:+.1f} % |")

    if tax:
        lines.append(f"| **Compte recommandé** | {tax.get('compte_recommande', 'N/A')} |")

    return "\n".join(lines)


def _calc_expected_value(thesis: dict[str, Any]) -> float | None:
    try:
        ev = (
            thesis["scenario_bull"]["probabilite"] * thesis["scenario_bull"]["rendement_cible"]
            + thesis["scenario_base"]["probabilite"] * thesis["scenario_base"]["rendement_cible"]
            + thesis["scenario_bear"]["probabilite"] * thesis["scenario_bear"]["rendement_cible"]
        )
        return ev * 100
    except (KeyError, TypeError):
        return None


# ─── Graham ───────────────────────────────────────────────────────────────────

def _section_graham(graham: dict[str, Any]) -> str:
    d_score = graham.get("defensive_score", "?")
    e_score = graham.get("enterprising_score", "?")
    verdict = graham.get("verdict", "N/A")
    verdict_detail = graham.get("verdict_detail", "")
    drapeaux = graham.get("drapeaux_rouges", [])
    vi_simple = graham.get("valeur_intrinseque_simple")
    vi_ajustee = graham.get("valeur_intrinseque_ajustee")
    marge = graham.get("marge_securite")
    criteria_def = graham.get("criteria_defensif", [])
    criteria_ent = graham.get("criteria_entreprenant", [])

    lines = [
        "## Analyse Graham",
        "",
        f"**Verdict : {verdict}** | Score défensif : {d_score}/8 | Score entreprenant : {e_score}/5",
        "",
        verdict_detail,
        "",
        "### Critères défensifs (chapitre 14)",
        "",
        "| # | Critère | Valeur observée | Seuil | ✓ |",
        "|---|---------|----------------|-------|---|",
    ]
    for c in criteria_def:
        icon = "✅" if c.get("passe") else "❌"
        lines.append(
            f"| {c.get('numero', '')} | {c.get('nom', '')} "
            f"| {c.get('valeur_observee', '')} | {c.get('seuil', '')} | {icon} |"
        )

    if criteria_ent:
        lines += [
            "",
            "### Critères entrepreneuriaux (chapitre 15)",
            "",
            "| # | Critère | Valeur observée | Seuil | ✓ |",
            "|---|---------|----------------|-------|---|",
        ]
        for c in criteria_ent:
            icon = "✅" if c.get("passe") else "❌"
            lines.append(
                f"| {c.get('numero', '')} | {c.get('nom', '')} "
                f"| {c.get('valeur_observee', '')} | {c.get('seuil', '')} | {icon} |"
            )

    lines += ["", "### Valeur intrinsèque"]
    if vi_simple is not None:
        lines.append(f"- Formule simple (V = EPS × (8.5 + 2g)) : **{vi_simple:.2f}**")
    if vi_ajustee is not None:
        lines.append(f"- Formule ajustée : **{vi_ajustee:.2f}**")
    if marge is not None:
        lines.append(f"- Marge de sécurité : **{_pct(marge)}**")

    if drapeaux:
        lines += ["", "### Drapeaux rouges"]
        for d in drapeaux:
            lines.append(f"- ⚠️ {d}")

    prochaines = graham.get("recommandation_prochaine_etape", [])
    if prochaines:
        lines += ["", "### Prochaines étapes recommandées"]
        for r in prochaines:
            lines.append(f"- {r}")

    return "\n".join(lines)


# ─── Earnings Quality ─────────────────────────────────────────────────────────

def _section_earnings(earnings: dict[str, Any]) -> str:
    verdict = earnings.get("verdict", "N/A")
    verdict_detail = earnings.get("verdict_detail", "")
    is_financial = earnings.get("is_financial", False)
    drapeaux = earnings.get("drapeaux_rouges", [])

    m_score_d = earnings.get("m_score") or {}
    z_score_d = earnings.get("z_score") or {}
    f_score_d = earnings.get("f_score") or {}
    c_score_d = earnings.get("c_score") or {}
    sloan_d = earnings.get("sloan") or {}

    financial_note = " *(institution financière — M-Score/Z-Score inapplicables)*" if is_financial else ""
    lines = [
        "## Qualité des bénéfices",
        "",
        f"**Verdict : {verdict}**{financial_note}",
        "",
        verdict_detail,
        "",
        "### Cadres d'analyse",
        "",
        "| Cadre | Score | Interprétation |",
        "|-------|-------|---------------|",
        f"| M-Score (Beneish) | {_val(m_score_d.get('m_score'), '.2f')} | {m_score_d.get('interpretation', 'N/A')} |",
        f"| Z-Score Altman ({z_score_d.get('variante', '')}) | {_val(z_score_d.get('z_score'), '.2f')} | {z_score_d.get('interpretation', 'N/A')} |",
        f"| F-Score (Piotroski) | {f_score_d.get('f_score', 'N/A')}/9 | {f_score_d.get('interpretation', 'N/A')} |",
        f"| C-Score (Montier) | {c_score_d.get('c_score', 'N/A')}/6 | {c_score_d.get('interpretation', 'N/A')} |",
        f"| Accruals (Sloan) | {_val(sloan_d.get('accrual_ratio'), '.3f')} | {sloan_d.get('interpretation', 'N/A')} |",
    ]

    f_criteria = f_score_d.get("criteria", [])
    if f_criteria:
        lines += [
            "",
            "### F-Score — détail des 9 critères",
            "",
            "| Critère | Résultat |",
            "|---------|---------|",
        ]
        for c in f_criteria:
            icon = "✅" if c.get("passe") else "❌"
            lines.append(f"| {c.get('nom', '')} | {icon} {c.get('detail', '')} |")

    if drapeaux:
        lines += ["", "### Drapeaux rouges"]
        for d in drapeaux:
            lines.append(f"- ⚠️ {d}")

    return "\n".join(lines)


# ─── Dorsey Moat ──────────────────────────────────────────────────────────────

def _section_dorsey(dorsey: dict[str, Any]) -> str:
    moat_type = dorsey.get("moat_type", "N/A")
    roic_durability = dorsey.get("roic_durability", "N/A")
    verdict_detail = dorsey.get("verdict_detail", "")
    sources = dorsey.get("sources_identifiees", [])
    drapeaux = dorsey.get("drapeaux_rouges", [])

    lines = [
        "## Analyse du Moat (Dorsey)",
        "",
        f"**Moat : {moat_type}** | Durabilité ROIC : {roic_durability}",
        "",
        verdict_detail,
        "",
        "### Cinq sources de moat",
        "",
        "| Source | Présent | Intensité | Justification |",
        "|--------|:-------:|-----------|--------------|",
    ]
    for s in sources:
        icon = "✅" if s.get("present") else "❌"
        lines.append(
            f"| {s.get('source', '')} | {icon} | {s.get('intensite', '')} | {s.get('justification', '')} |"
        )

    if drapeaux:
        lines += ["", "### Drapeaux rouges"]
        for d in drapeaux:
            lines.append(f"- ⚠️ {d}")

    prochaines = dorsey.get("recommandation_prochaine_etape", [])
    if prochaines:
        lines += ["", "### Prochaines étapes"]
        for r in prochaines:
            lines.append(f"- {r}")

    return "\n".join(lines)


# ─── Buffett Quality ──────────────────────────────────────────────────────────

def _section_buffett(buffett: dict[str, Any]) -> str:
    verdict = buffett.get("verdict", "N/A")
    quality_score = buffett.get("quality_score", "N/A")
    owner_earnings = buffett.get("owner_earnings")
    verdict_detail = buffett.get("verdict_detail", "")
    filtres = buffett.get("filtres", [])
    drapeaux = buffett.get("drapeaux_rouges", [])

    lines = [
        "## Qualité Buffett",
        "",
        f"**Verdict : {verdict}** | Score qualité : {quality_score}/4",
        "",
        verdict_detail,
    ]
    if owner_earnings is not None:
        lines += ["", f"**Owner Earnings :** {owner_earnings:.2f}"]

    lines += [
        "",
        "### Les 4 filtres Buffett",
        "",
        "| Filtre | Score | Justification |",
        "|--------|:-----:|--------------|",
    ]
    for f in filtres:
        icon = "✅" if f.get("passe") else "❌"
        lines.append(
            f"| {f.get('filtre', '')} | {icon} {f.get('score', '')}/1 | {f.get('justification', '')} |"
        )

    if drapeaux:
        lines += ["", "### Drapeaux rouges"]
        for d in drapeaux:
            lines.append(f"- ⚠️ {d}")

    return "\n".join(lines)


# ─── Stock Valuation ──────────────────────────────────────────────────────────

def _section_valuation(valuation: dict[str, Any]) -> str:
    verdict = valuation.get("verdict", "N/A")
    verdict_detail = valuation.get("verdict_detail", "")
    methodes = valuation.get("methodes", [])
    f_basse = valuation.get("fourchette_basse")
    f_centrale = valuation.get("fourchette_centrale")
    f_haute = valuation.get("fourchette_haute")
    marge = valuation.get("marge_securite_composite")
    matrice = valuation.get("matrice_sensibilite") or {}

    lines = [
        "## Valorisation par triangulation",
        "",
        f"**Verdict : {verdict}**",
        "",
        verdict_detail,
        "",
        "### Méthodes de valorisation",
        "",
        "| Méthode | Valeur estimée | Hypothèses |",
        "|---------|---------------|-----------|",
    ]
    for m in methodes:
        lines.append(
            f"| {m.get('methode', '').upper()} | {_val(m.get('valeur'))} | {m.get('hypotheses', '')} |"
        )

    lines += [
        "",
        "### Fourchette de valeur intrinsèque",
        "",
        "| Basse | Centrale | Haute | Marge de sécurité composite |",
        "|-------|---------|-------|----------------------------|",
        f"| {_val(f_basse)} | {_val(f_centrale)} | {_val(f_haute)} | {_pct(marge)} |",
    ]

    wacc_range = matrice.get("wacc_range", [])
    growth_range = matrice.get("growth_range", [])
    values = matrice.get("values", [])
    if wacc_range and growth_range and values:
        lines += ["", "### Matrice de sensibilité (WACC × taux de croissance)", ""]
        header = "| WACC / g |" + "".join(f" {g * 100:.1f}% |" for g in growth_range)
        separator = "|---------|" + "".join("-------|" for _ in growth_range)
        lines += [header, separator]
        for i, row in enumerate(values):
            wacc_label = f"{wacc_range[i] * 100:.1f}%" if i < len(wacc_range) else "?"
            row_str = f"| {wacc_label} |" + "".join(f" {_val(v)} |" for v in row)
            lines.append(row_str)

    return "\n".join(lines)


# ─── Investment Thesis Builder ────────────────────────────────────────────────

def _section_thesis(thesis: dict[str, Any]) -> str:
    verdict_final = thesis.get("verdict_final", "N/A")
    position_size = thesis.get("position_size_pct")
    synthese = thesis.get("synthese_narrative", "")
    kill_criteria = thesis.get("kill_criteria", [])
    devils_advocate = thesis.get("devils_advocate", "")
    scenario_bull = thesis.get("scenario_bull") or {}
    scenario_base = thesis.get("scenario_base") or {}
    scenario_bear = thesis.get("scenario_bear") or {}

    ev = _calc_expected_value(thesis)

    lines = [
        "## Thèse d'investissement",
        "",
        f"**Verdict final : {verdict_final}** | Position recommandée : {_val(position_size, '.1f')} %",
        "",
        synthese,
        "",
        "### Scénarios pondérés",
        "",
        "| Scénario | Probabilité | Rendement cible | Hypothèses clés |",
        "|----------|:-----------:|:--------------:|----------------|",
    ]

    for label, scenario in [
        ("🐂 Bull", scenario_bull),
        ("📊 Base", scenario_base),
        ("🐻 Bear", scenario_bear),
    ]:
        prob = scenario.get("probabilite", 0)
        rendement = scenario.get("rendement_cible", 0)
        hypotheses = " / ".join(h for h in scenario.get("hypotheses", [])[:2])
        lines.append(f"| {label} | {_pct(prob, 0)} | {_pct(rendement, 0)} | {hypotheses} |")

    if ev is not None:
        lines += ["", f"**Espérance pondérée : {ev:+.1f} %**"]

    if kill_criteria:
        lines += ["", "### Kill Criteria — déclencheurs de sortie"]
        for k in kill_criteria:
            lines.append(f"- 🚨 {k}")

    if devils_advocate:
        lines += ["", "### Devil's Advocate", "", f"> {devils_advocate}"]

    return "\n".join(lines)


# ─── Munger Mental Models ─────────────────────────────────────────────────────

def _section_munger(munger: dict[str, Any]) -> str:
    verdict_comportemental = munger.get("verdict_comportemental", "N/A")
    verdict_detail = munger.get("verdict_detail", "")
    lollapalooza = munger.get("lollapalooza_risk", False)
    inversion = munger.get("inversion_analysis", "")
    biais = munger.get("biais_detectes", [])

    lolla_icon = "⚠️ OUI" if lollapalooza else "✅ NON"
    lines = [
        "## Analyse comportementale (Munger)",
        "",
        f"**Verdict comportemental : {verdict_comportemental}** | Risque lollapalooza : {lolla_icon}",
        "",
        verdict_detail,
    ]

    if biais:
        lines += [
            "",
            "### Biais cognitifs détectés",
            "",
            "| Biais | Impact | Manifestation |",
            "|-------|:------:|--------------|",
        ]
        _icons = {"MAJEUR": "🔴", "MODERE": "🟠", "MINEUR": "🟡"}
        for b in biais:
            impact = b.get("impact_sur_these", "N/A")
            icon = _icons.get(impact, "⚪")
            lines.append(f"| {b.get('nom', '')} | {icon} {impact} | {b.get('description', '')} |")

    if inversion:
        lines += ["", "### Analyse par inversion (« Invert, always invert »)", "", inversion]

    return "\n".join(lines)


# ─── Canadian Tax ─────────────────────────────────────────────────────────────

def _section_tax(tax: dict[str, Any]) -> str:
    compte = tax.get("compte_recommande", "N/A")
    justification = tax.get("justification_fiscale", "")
    retenue_us = tax.get("impact_retenue_us")
    smith = tax.get("strategie_smith_manoeuvre", False)
    taux_inclusion = tax.get("taux_inclusion_gain_capital")
    prochaines = tax.get("recommandation_prochaine_etape", [])

    lines = [
        "## Fiscalité canadienne",
        "",
        f"**Compte recommandé : {compte}**",
        "",
        justification,
        "",
        "| Paramètre | Valeur |",
        "|-----------|--------|",
        f"| Compte optimal | **{compte}** |",
        f"| Smith Manœuvre applicable | {'✅ Oui' if smith else '❌ Non'} |",
    ]
    if taux_inclusion is not None:
        lines.append(f"| Taux inclusion gains en capital | {_pct(taux_inclusion)} |")

    if retenue_us:
        lines += ["", f"**Retenue à la source US :** {retenue_us}"]

    if prochaines:
        lines += ["", "### Recommandations fiscales"]
        for r in prochaines:
            lines.append(f"- {r}")

    return "\n".join(lines)


# ─── Pied de page ─────────────────────────────────────────────────────────────

def _footer(
    ticker: str,
    skills_applied: list[str],
    cost_usd: float,
    analysis_id: str,
    created_at: str,
) -> str:
    skills_str = " · ".join(f"`{s}`" for s in skills_applied)
    date_str = created_at[:10] if created_at else "N/A"
    lines = [
        "## Informations sur l'analyse",
        "",
        "| Champ | Valeur |",
        "|-------|--------|",
        f"| Ticker | {ticker} |",
        f"| ID analyse | `{analysis_id}` |",
        f"| Date | {date_str} |",
        f"| Coût API | ${cost_usd:.4f} USD |",
        f"| Skills | {', '.join(skills_applied)} |",
        "",
        f"*Skills appliqués : {skills_str}*",
        "",
        "*Ce document est à titre informatif uniquement. "
        "Pas un conseil financier ou fiscal personnalisé.*",
    ]
    return "\n".join(lines)
