"""
Tests d'évaluation Graham — appels Claude RÉELS sur le golden dataset.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Exécution : EVAL_API_URL=http://localhost:8000 pytest tests/evals/ -m evals --no-header -v
Prérequis : ANTHROPIC_API_KEY dans l'environnement, API copilote en cours d'exécution.
            tests/evals/fixtures/graham_golden.json rempli par Yves.

Note rate limit : la variable EVAL_RATE_DELAY_S (défaut 7) espace les requêtes
pour rester sous la limite de 10 req/min du middleware.
"""
from __future__ import annotations

import asyncio
import os

import pytest

from tests.evals.fixtures import load_graham_golden

_RATE_DELAY_S = float(os.environ.get("EVAL_RATE_DELAY_S", "7"))


@pytest.mark.evals
@pytest.mark.parametrize("case", load_graham_golden())
async def test_graham_eval(case, eval_client):
    """Appel Claude RÉEL — ne jamais patcher call_claude_with_retry ici."""
    if os.environ.get("EVAL_API_URL"):
        await asyncio.sleep(_RATE_DELAY_S)

    response = await eval_client.post("/analyze", json={
        "ticker": case["ticker"],
        "ratios": case["inputs"],
    })
    assert response.status_code == 200, (
        f"[{case['id']}] HTTP {response.status_code} pour {case['ticker']}: {response.text[:200]}"
    )
    data = response.json()
    graham = data["graham"]
    exp = case["expected"]

    assert graham["defensive_verdict"] == exp["defensive_verdict"], (
        f"[{case['id']}] {case['ticker']} — verdict attendu={exp['defensive_verdict']!r}, "
        f"obtenu={graham['defensive_verdict']!r} (score={graham['defensive_score']})"
    )

    if "defensive_score_range" in exp:
        lo, hi = exp["defensive_score_range"]
        assert lo <= graham["defensive_score"] <= hi, (
            f"[{case['id']}] {case['ticker']} — score {graham['defensive_score']} "
            f"hors plage [{lo}, {hi}]"
        )

    if exp.get("must_pass_criteria"):
        passed_nums = {c["numero"] for c in graham["criteria_defensif"] if c["passe"]}
        for num in exp["must_pass_criteria"]:
            assert num in passed_nums, (
                f"[{case['id']}] {case['ticker']} — critère {num} doit être PASSE "
                f"(passés: {sorted(passed_nums)})"
            )

    if exp.get("must_red_flag"):
        flags_text = " ".join(graham.get("drapeaux_rouges", [])).lower()
        for keyword in exp["must_red_flag"]:
            assert keyword.lower() in flags_text, (
                f"[{case['id']}] {case['ticker']} — drapeau '{keyword}' attendu "
                f"dans: {graham.get('drapeaux_rouges', [])}"
            )
