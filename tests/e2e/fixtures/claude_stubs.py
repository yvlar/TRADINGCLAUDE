"""Réponses Claude stubbées pour les tests E2E — aucun token Anthropic consommé."""
from __future__ import annotations

import json
from types import SimpleNamespace


def _resp(data: dict) -> SimpleNamespace:
    # Les skills lisent désormais un bloc tool_use (`b.type == "tool_use"`, `b.input`) ;
    # on expose aussi `.text` pour rester compatible avec un éventuel skill encore en
    # mode parsing JSON texte.
    block = SimpleNamespace(
        type="tool_use",
        name="output",
        input=data,
        text=json.dumps(data),
    )
    return SimpleNamespace(
        content=[block],
        usage=SimpleNamespace(
            input_tokens=50,
            output_tokens=100,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=100,
        ),
        stop_reason="tool_use",
    )


async def graham_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "profil_applique": "LES_DEUX",
        "defensive_score": 6,
        "enterprising_score": 4,
        "criteria_defensif": [
            {"numero": i + 1, "nom": f"Critère défensif {i + 1}", "passe": True,
             "valeur_observee": "ok", "seuil": "seuil", "commentaire": "test"}
            for i in range(8)
        ],
        "criteria_entreprenant": [
            {"numero": i + 1, "nom": f"Critère entreprenant {i + 1}", "passe": True,
             "valeur_observee": "ok", "seuil": "seuil", "commentaire": "test"}
            for i in range(5)
        ],
        "valeur_intrinseque_simple": 90.0,
        "valeur_intrinseque_ajustee": 85.0,
        "marge_securite": 0.0625,
        "drapeaux_rouges": [],
        "verdict": "CANDIDAT_SOLIDE",
        "verdict_detail": "Score 6/8 — candidat valeur à surveiller.",
        "recommandation_prochaine_etape": ["earnings_quality"],
        "citations": [],
        "cost_usd": 0.0,
    })


async def earnings_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "is_financial": False,
        "m_score": {
            "dsri": None, "gmi": None, "aqi": None, "sgi": 1.07,
            "depi": None, "sgai": None, "tata": -0.028, "lvgi": None,
            "m_score": None, "interpretation": "DONNÉES_MANQUANTES",
        },
        "z_score": {"variante": "Z_original", "z_score": 4.12, "interpretation": "zone_sure"},
        "f_score": {
            "criteria": [
                {"nom": f"Critère F{i + 1}", "passe": True, "detail": "ok"}
                for i in range(9)
            ],
            "f_score": 9,
            "interpretation": "forte_qualite",
        },
        "c_score": {
            "signaux": [
                {"nom": f"Signal C{i + 1}", "present": False, "detail": "ok"}
                for i in range(6)
            ],
            "c_score": 0,
            "interpretation": "propre",
        },
        "sloan": {"accrual_ratio": -0.029, "interpretation": "qualite_elevee"},
        "drapeaux_rouges": [],
        "verdict": "AUCUN_SIGNAL",
        "verdict_detail": "Aucun signal détecté.",
        "recommandation_prochaine_etape": [],
    })


async def dorsey_stub(*args, **kwargs) -> SimpleNamespace:
    sources = [
        {"source": s, "present": False, "intensite": "ABSENTE", "justification": "non évalué"}
        for s in ["intangibles", "switching_costs", "network_effects", "cost_advantages", "efficient_scale"]
    ]
    return _resp({
        "ticker": "TEST",
        "moat_type": "NARROW",
        "sources_identifiees": sources,
        "roic_durability": "MODÉRÉE",
        "verdict_detail": "Moat étroit.",
        "drapeaux_rouges": [],
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def buffett_stub(*args, **kwargs) -> SimpleNamespace:
    filtres = [
        {"filtre": f"Filtre {i + 1}", "passe": True, "score": 1, "justification": "ok"}
        for i in range(4)
    ]
    return _resp({
        "ticker": "TEST",
        "filtres": filtres,
        "owner_earnings": 5.0,
        "quality_score": 3,
        "verdict": "BON",
        "verdict_detail": "Qualité satisfaisante.",
        "drapeaux_rouges": [],
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def valuation_stub(*args, **kwargs) -> SimpleNamespace:
    methodes = [
        {"methode": m, "valeur": 90.0, "hypotheses": "hypothèses test"}
        for m in ["dcf", "comparables", "sectoriel"]
    ]
    return _resp({
        "ticker": "TEST",
        "methodes": methodes,
        "fourchette_basse": 75.0,
        "fourchette_centrale": 90.0,
        "fourchette_haute": 105.0,
        "marge_securite_composite": 0.125,
        "matrice_sensibilite": {
            "wacc_range": [0.07, 0.09, 0.11],
            "growth_range": [0.02, 0.03, 0.04],
            "values": [[80.0, 90.0, 100.0]] * 3,
        },
        "verdict": "SOUS_EVALUE",
        "verdict_detail": "Sous-évalué selon les 3 méthodes.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def thesis_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "scenario_bull": {"probabilite": 0.30, "rendement_cible": 0.50, "hypotheses": ["h1"]},
        "scenario_base": {"probabilite": 0.50, "rendement_cible": 0.15, "hypotheses": ["h2"]},
        "scenario_bear": {"probabilite": 0.20, "rendement_cible": -0.20, "hypotheses": ["h3"]},
        "kill_criteria": ["Dividende coupé", "Dette explose", "Perte parts de marché"],
        "devils_advocate": "Concurrence accrue.",
        "position_size_pct": 3.0,
        "verdict_final": "ACCUMULER",
        "synthese_narrative": "Thèse de test robuste.",
        "citations": [],
        "cost_usd": 0.0,
    })


async def munger_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "biais_detectes": [],
        "inversion_analysis": "Aucun biais majeur détecté.",
        "lollapalooza_risk": False,
        "verdict_comportemental": "CONFIANCE_JUSTIFIEE",
        "verdict_detail": "Analyse comportementale saine.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def canadian_tax_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "compte_recommande": "CELI",
        "justification_fiscale": "Croissance libre d'impôt optimale.",
        "impact_retenue_us": None,
        "strategie_smith_manoeuvre": False,
        "taux_inclusion_gain_capital": 0.50,
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def lynch_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "categorie": "STALWART",
        "peg_ratio": 1.5,
        "tenbagger_potential": False,
        "score_croissance": 3,
        "verdict": "BON",
        "verdict_detail": "STALWART établi — croissance régulière.",
        "recommandation_prochaine_etape": ["damodaran_narrative"],
        "citations": [],
        "cost_usd": 0.0,
    })


async def fisher_stub(*args, **kwargs) -> SimpleNamespace:
    points = [
        {"point": i + 1, "titre": f"Point Fisher {i + 1}", "score": 1, "commentaire": "ok"}
        for i in range(15)
    ]
    return _resp({
        "ticker": "TEST",
        "fisher_score": 15,
        "points_evalues": points,
        "management_quality": "BON",
        "verdict": "ACHAT",
        "verdict_detail": "Score Fisher satisfaisant.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def klarman_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "situation_type_qualifie": "VALEUR_CLASSIQUE",
        "marge_securite_score": 7,
        "preservation_capital_score": 7,
        "discount_to_intrinsic": 0.15,
        "verdict": "OPPORTUNITE_MODEREE",
        "verdict_detail": "Marge de sécurité présente.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def greenblatt_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "roc": 0.18,
        "earnings_yield": 0.09,
        "verdict": "BON",
        "situations_speciales": [],
        "verdict_detail": "ROC et earnings yield satisfaisants.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def damodaran_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "ticker": "TEST",
        "test_coherence": "PLAUSIBLE",
        "erp_implied": 0.055,
        "narrative_strength": 7,
        "divergences_detectees": [],
        "verdict": "NARRATIVE_ACCEPTABLE",
        "verdict_detail": "Narrative cohérente avec les chiffres.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def marks_stub(*args, **kwargs) -> SimpleNamespace:
    return _resp({
        "position_cycle": "NEUTRE",
        "pendule_score": 0,
        "second_level_insight": "Marché neutre — valorisation raisonnable.",
        "recommandation_timing": "ATTENDRE",
        "verdict_detail": "Cycle neutre, pas d'opportunité contrariante marquée.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })


async def pabrai_stub(*args, **kwargs) -> SimpleNamespace:
    principes = [
        {"nom": f"Principe Dhandho {i + 1}", "satisfait": True, "commentaire": "ok"}
        for i in range(9)
    ]
    return _resp({
        "ticker": "TEST",
        "principes_dhandho": principes,
        "heads_i_win_score": 9,
        "asymetrie": 5.0,
        "kelly_fractionnel": 0.05,
        "verdict": "DHANDHO_FORT",
        "verdict_detail": "Tous les principes Dhandho satisfaits.",
        "recommandation_prochaine_etape": [],
        "citations": [],
        "cost_usd": 0.0,
    })
