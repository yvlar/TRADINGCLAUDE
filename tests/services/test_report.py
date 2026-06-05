"""Tests Sprint 20 — ReportService + endpoint /report."""
from __future__ import annotations

import uuid

from app.orchestrator.core import AnalyzeResponse
from app.services.report import ReportService

# ---------------------------------------------------------------------------
# Helpers — construction d'AnalyzeResponse de test
# ---------------------------------------------------------------------------


def _make_minimal_response(graham_output) -> AnalyzeResponse:
    """AnalyzeResponse minimale : seulement graham, pas de skills optionnels."""
    return AnalyzeResponse(
        analysis_id=str(uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")),
        ticker="BNS",
        workflow="value_graham",
        skills_applied=["graham_analysis"],
        graham=graham_output,
        cost_usd=0.0012,
        created_at="2026-05-09T10:00:00+00:00",
    )


def _make_full_response(graham_output, earnings_output) -> AnalyzeResponse:
    """AnalyzeResponse avec graham + earnings — les autres sont None."""
    return AnalyzeResponse(
        analysis_id=str(uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")),
        ticker="MSFT",
        workflow="value_graham",
        skills_applied=["graham_analysis", "earnings_quality"],
        graham=graham_output,
        earnings_quality=earnings_output,
        cost_usd=0.0034,
        created_at="2026-05-09T11:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Tests unitaires — ReportService (pas d'appel réseau, pas de DB)
# ---------------------------------------------------------------------------


def test_generate_pdf_retourne_bytes(graham_output_msft):
    """generate_pdf() retourne un objet bytes non vide."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_minimal_response(graham_output_msft)

    result = service.generate_pdf(response)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_commence_par_pdf_header(graham_output_msft):
    """Le PDF généré commence bien par le magic number %PDF."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_minimal_response(graham_output_msft)

    result = service.generate_pdf(response)

    assert result[:4] == b"%PDF"


def test_generate_pdf_graham_seulement(graham_output_msft):
    """AnalyzeResponse sans skills optionnels → PDF valide non vide."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_minimal_response(graham_output_msft)

    result = service.generate_pdf(response)

    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_pdf_avec_earnings(graham_output_msft, earnings_output_msft):
    """AnalyzeResponse avec graham + earnings → PDF valide."""
    service = ReportService(output_dir="/tmp/reports_test")
    response = _make_full_response(graham_output_msft, earnings_output_msft)

    result = service.generate_pdf(response)

    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_save_pdf_cree_fichier(tmp_path, graham_output_msft):
    """save_pdf() crée un fichier .pdf sur le disque."""
    service = ReportService(output_dir=str(tmp_path))
    response = _make_minimal_response(graham_output_msft)

    path = service.save_pdf(response)

    assert path.exists()
    assert path.suffix == ".pdf"
    assert path.stat().st_size > 0


def test_save_pdf_nom_correct(tmp_path, graham_output_msft):
    """save_pdf() nomme le fichier {ticker}-{analysis_id[:8]}.pdf."""
    service = ReportService(output_dir=str(tmp_path))
    response = _make_minimal_response(graham_output_msft)

    path = service.save_pdf(response)

    expected_name = f"{response.ticker}-{response.analysis_id[:8]}.pdf"
    assert path.name == expected_name


# ---------------------------------------------------------------------------
# Tests endpoint — client mocké de conftest.py
# ---------------------------------------------------------------------------


async def test_post_report_200(client) -> None:
    """POST /report avec payload valide → 200 + Content-Type application/pdf."""
    payload = {
        "ticker": "BNS",
        "ratios": {
            "pe": 11.0,
            "pb": 1.3,
            "current_ratio": None,
            "debt_equity": 0.45,
            "eps_growth_total": 0.27,
            "price": 80.0,
            "book_value": 61.5,
        },
        "workflow": "value_graham",
    }
    response = await client.post("/report", json=payload)

    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")


async def test_post_report_content_disposition(client) -> None:
    """POST /report → header Content-Disposition présent avec filename .pdf."""
    payload = {
        "ticker": "BNS",
        "ratios": {
            "pe": 11.0,
            "pb": 1.3,
            "current_ratio": None,
            "debt_equity": 0.45,
            "eps_growth_total": 0.27,
            "price": 80.0,
            "book_value": 61.5,
        },
    }
    response = await client.post("/report", json=payload)

    assert response.status_code == 200
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert ".pdf" in disposition


async def test_post_report_ratios_invalides_422(client) -> None:
    """POST /report sans le champ price obligatoire → 422 Unprocessable Entity."""
    payload = {
        "ticker": "BNS",
        "ratios": {
            # price manquant — doit déclencher une erreur de validation Pydantic
            # Note : pe/pb optionnels (Sprint 36 / Sprint 135 — float | None) ; price reste requis
            "pe": 11.0,
            "pb": 1.3,
            "debt_equity": 0.45,
            "eps_growth_total": 0.27,
            "book_value": 61.5,
        },
    }
    response = await client.post("/report", json=payload)

    assert response.status_code == 422


async def test_get_report_analysis_inconnu_404(client) -> None:
    """GET /report/{uuid-inexistant} → 404 Not Found."""
    from unittest.mock import AsyncMock

    from app.api.main import app

    # fetchrow retourne None pour simuler un analysis_id introuvable en DB
    app.state.db_pool.fetchrow = AsyncMock(return_value=None)

    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await client.get(f"/report/{fake_id}")

    assert response.status_code == 404


async def test_get_report_200_pdf_reconstruit_depuis_historique(
    client, graham_output_msft, earnings_output_msft
) -> None:
    """GET /report/{id} reconstruit l'analyse (cœur consolidé Sprint 147) et renvoie un PDF.

    Couvre le chemin 200 de bout en bout (DB mockée → reconstruct(require_graham=True) →
    PDF multi-skills), jusqu'ici couvert seulement au niveau unité (_reconstruct_response).
    Réutilise `_make_result_row` (helper des tests de reconstruction Sprint 147).
    """
    from unittest.mock import AsyncMock

    from app.api.main import app

    row = _make_result_row(
        {
            "graham": graham_output_msft.model_dump(),
            "earnings_quality": earnings_output_msft.model_dump(),
        }
    )
    app.state.db_pool.fetchrow = AsyncMock(return_value=row)

    response = await client.get(f"/report/{row['id']}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    # Le PDF a réellement été produit depuis l'analyse reconstruite (magic number %PDF).
    assert response.content[:4] == b"%PDF"
    assert len(response.content) > 0


async def test_get_report_graham_absent_du_result_500(client, earnings_output_msft) -> None:
    """Contrat require_graham=True au niveau endpoint : `result` sans clé graham → 500 assaini.

    Le cœur consolidé lève ValueError (graham obligatoire) ; l'endpoint l'assainit en 500.
    Verrouille la validation au niveau endpoint (le test unité Sprint 147 ne couvre que la fonction).
    """
    from unittest.mock import AsyncMock

    from app.api.main import app

    row = _make_result_row({"earnings_quality": earnings_output_msft.model_dump()})
    app.state.db_pool.fetchrow = AsyncMock(return_value=row)

    response = await client.get(f"/report/{row['id']}")

    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Tests Sprint 53 — generate_watchlist_summary_pdf() avec composite_score
# ---------------------------------------------------------------------------


def _make_watchlist_entry(**kwargs):
    """Crée une WatchlistEntry minimale pour les tests PDF watchlist."""
    from datetime import datetime, timezone

    from app.models.watchlist import WatchlistEntry

    defaults = {
        "id": str(uuid.uuid4()),
        "ticker": "BNS",
        "created_at": datetime.now(timezone.utc),
        "last_composite_score": None,
        "composite_alert_threshold": 15.0,
        "last_score": None,
        "last_verdict": None,
        "last_intrinsic_value": None,
        "last_price_checked": None,
        "price_alert_threshold_pct": 0.10,
    }
    defaults.update(kwargs)
    return WatchlistEntry(**defaults)


def test_pdf_contient_composite_score():
    """PDF watchlist valide + _composite_label retourne FORT pour score >= 70."""
    from app.services.report import _composite_label

    service = ReportService(output_dir="/tmp/reports_test")
    entry = _make_watchlist_entry(ticker="RY", last_composite_score=75.0)

    pdf_bytes = service.generate_watchlist_summary_pdf([entry])

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert _composite_label(75.0) == "FORT"
    assert _composite_label(55.0) == "MODERE"
    assert _composite_label(30.0) == "FAIBLE"
    assert _composite_label(None) == "—"


def test_pdf_gere_composite_score_none():
    """Le PDF watchlist se génère sans erreur quand last_composite_score est None."""
    service = ReportService(output_dir="/tmp/reports_test")
    entry = _make_watchlist_entry(ticker="TD", last_composite_score=None)

    pdf_bytes = service.generate_watchlist_summary_pdf([entry])

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 0


def test_pdf_alerte_active_marquee():
    """_composite_alerte retourne OUI quand score < threshold, NON sinon."""
    from app.services.report import _composite_alerte

    service = ReportService(output_dir="/tmp/reports_test")
    entry = _make_watchlist_entry(
        ticker="XIU",
        last_composite_score=10.0,
        composite_alert_threshold=15.0,
    )

    pdf_bytes = service.generate_watchlist_summary_pdf([entry])

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    # Vérification de la logique d'alerte
    assert _composite_alerte(10.0, 15.0) == "OUI"   # score < threshold → alerte
    assert _composite_alerte(20.0, 15.0) == "NON"   # score >= threshold → pas d'alerte
    assert _composite_alerte(None, 15.0) == "—"      # score absent → neutre


# ---------------------------------------------------------------------------
# Sprint 139 — reconstruction de la traçabilité depuis l'historique
# ---------------------------------------------------------------------------


def _make_history_row(graham_output, *, input_data: dict | None) -> dict:
    """Ligne analysis_history simulée (dict indexable comme asyncpg.Record)."""
    import json
    from datetime import datetime, timezone

    return {
        "id": uuid.UUID("cccccccc-0000-0000-0000-000000000003"),
        "ticker": "MSFT",
        "workflow_name": "value_graham",
        "skills_used": json.dumps(["graham"]),
        "input_data": json.dumps(input_data) if input_data is not None else None,
        "result": json.dumps({"graham": graham_output.model_dump()}),
        "cost_usd": 0.0021,
        "created_at": datetime(2026, 5, 20, 10, 0, 0, tzinfo=timezone.utc),
    }


def test_reconstruct_response_reconstruit_tracabilite(graham_output_msft):
    """input_data avec source+date → AnalyzeResponse rechargée porte la traçabilité."""
    from app.api.endpoints.report import _reconstruct_response

    row = _make_history_row(
        graham_output_msft,
        input_data={
            "eps_growth_total": 0.27,
            "price": 245.0,
            "ratios_fetched_at": "2026-05-20T09:00:00+00:00",
            "ratios_source": "Yahoo Finance",
        },
    )
    resp = _reconstruct_response(row)
    assert resp.ratios_source == "Yahoo Finance"
    assert resp.ratios_fetched_at is not None
    assert resp.ratios_fetched_at.startswith("2026-05-20")


def test_reconstruct_response_sans_horodatage_donne_none(graham_output_msft):
    """input_data sans horodatage (analyse ancienne) → champs None, pas de crash."""
    from app.api.endpoints.report import _reconstruct_response

    row = _make_history_row(
        graham_output_msft,
        input_data={"eps_growth_total": 0.27, "price": 245.0},
    )
    resp = _reconstruct_response(row)
    assert resp.ratios_fetched_at is None
    assert resp.ratios_source is None


def test_reconstruct_response_input_data_absent_donne_none(graham_output_msft):
    """input_data NULL (très ancienne analyse) → champs None, pas de crash."""
    from app.api.endpoints.report import _reconstruct_response

    row = _make_history_row(graham_output_msft, input_data=None)
    resp = _reconstruct_response(row)
    assert resp.ratios_fetched_at is None
    assert resp.ratios_source is None


def test_reconstruct_response_reconstruit_earnings_valuation(
    graham_output_msft, ratios_earnings_msft
):
    """Sous-clés earnings_ratios/valuation_ratios horodatées → traçabilité des trois skills rechargée."""
    from datetime import datetime, timezone

    from app.api.endpoints.report import _reconstruct_response
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    earnings = ratios_earnings_msft.model_copy(
        update={
            "ratios_fetched_at": datetime(2026, 5, 21, 9, 0, 0, tzinfo=timezone.utc),
            "ratios_source": "Yahoo Finance",
        }
    )
    valuation = ValuationRatios(
        pe=34.2,
        ratios_fetched_at=datetime(2026, 5, 22, 9, 0, 0, tzinfo=timezone.utc),
        ratios_source="Yahoo Finance",
    )
    row = _make_history_row(
        graham_output_msft,
        input_data={
            "eps_growth_total": 0.27,
            "price": 245.0,
            "ratios_fetched_at": "2026-05-20T09:00:00+00:00",
            "ratios_source": "Yahoo Finance",
            "earnings_ratios": earnings.model_dump(mode="json"),
            "valuation_ratios": valuation.model_dump(mode="json"),
        },
    )
    resp = _reconstruct_response(row)
    assert resp.ratios_fetched_at is not None and resp.ratios_fetched_at.startswith("2026-05-20")
    assert resp.earnings_ratios_source == "Yahoo Finance"
    assert resp.earnings_ratios_fetched_at is not None
    assert resp.earnings_ratios_fetched_at.startswith("2026-05-21")
    assert resp.valuation_ratios_source == "Yahoo Finance"
    assert resp.valuation_ratios_fetched_at is not None
    assert resp.valuation_ratios_fetched_at.startswith("2026-05-22")


def test_reconstruct_response_sous_cles_absentes_earnings_valuation_none(graham_output_msft):
    """Ligne plate (Graham seul, sans sous-clés) → earnings/valuation None, pas de crash."""
    from app.api.endpoints.report import _reconstruct_response

    row = _make_history_row(graham_output_msft, input_data={"eps_growth_total": 0.27})
    resp = _reconstruct_response(row)
    assert resp.earnings_ratios_fetched_at is None
    assert resp.earnings_ratios_source is None
    assert resp.valuation_ratios_fetched_at is None
    assert resp.valuation_ratios_source is None


# ---------------------------------------------------------------------------
# Sprint 147 — cœur de reconstruction partagé (/report vs /ticker-report)
# ---------------------------------------------------------------------------


def _make_esg_output_dict() -> dict:
    """Dict EsgOutput valide minimal (5E + 5S + 5G, tous passés → ESG_FORT)."""
    criteres = [
        {
            "dimension": dim,
            "nom": f"{dim}{i}",
            "passe": True,
            "observation": "obs proxy",
            "proxy_utilise": "roe",
        }
        for dim, count in (("E", 5), ("S", 5), ("G", 5))
        for i in range(count)
    ]
    return {
        "ticker": "MSFT",
        "esg_score": 15,
        "e_score": 5,
        "s_score": 5,
        "g_score": 5,
        "criteres": criteres,
        "verdict": "ESG_FORT",
        "verdict_detail": "Tous les proxies passent.",
        "limites": ["Proxies imparfaits."],
        "citations": [],
        "cost_usd": 0.0,
    }


def _make_result_row(result: dict) -> dict:
    """Ligne analysis_history simulée portant un `result` arbitraire (sans input_data)."""
    import json
    from datetime import datetime, timezone

    return {
        "id": uuid.UUID("dddddddd-0000-0000-0000-000000000004"),
        "ticker": "MSFT",
        "workflow_name": "value_graham",
        "skills_used": json.dumps(list(result.keys())),
        "input_data": None,
        "result": json.dumps(result),
        "cost_usd": 0.0021,
        "created_at": datetime(2026, 5, 20, 10, 0, 0, tzinfo=timezone.utc),
    }


def test_reconstruct_response_reconstruit_esg(graham_output_msft):
    """Régression du bug latent : /report reconstruit désormais `esg` (manquant avant Sprint 147)."""
    from app.api.endpoints.report import _reconstruct_response

    row = _make_result_row(
        {"graham": graham_output_msft.model_dump(), "esg_simplified": _make_esg_output_dict()}
    )
    resp = _reconstruct_response(row)
    assert resp.esg is not None
    assert resp.esg.verdict == "ESG_FORT"


def test_reconstruct_response_reconstruit_ratios_provenance(graham_output_msft):
    """Sprint 150 : reconstruct(require_graham=True) reconstruit ratios_provenance depuis input_data.

    Verrou de bout en bout (ligne → AnalyzeResponse.ratios_provenance) : jusqu'ici seul le helper
    reconstruct_ratios_traces était testé directement ; ce test exerce le chemin endpoint complet.
    """
    import json

    from app.api.endpoints.report import _reconstruct_response

    row = _make_result_row({"graham": graham_output_msft.model_dump()})
    row["input_data"] = json.dumps(
        {"eps_growth_total": 0.27, "price": 245.0, "ratios_provenance": {"pb": "priceToBookRatio"}}
    )
    resp = _reconstruct_response(row)
    assert resp.ratios_provenance == {"pb": "priceToBookRatio"}


def test_reconstruct_response_graham_absent_leve_valueerror():
    """Contrat /report préservé : graham absent → ValueError."""
    import pytest

    from app.api.endpoints.report import _reconstruct_response

    row = _make_result_row({"esg_simplified": _make_esg_output_dict()})
    with pytest.raises(ValueError):
        _reconstruct_response(row)


def test_reconstruct_analyze_response_result_illisible_donne_none():
    """Contrat /ticker-report préservé : result illisible → None (jamais d'exception)."""
    from app.api.endpoints.ticker_report import _reconstruct_analyze_response

    row = _make_result_row({"graham": {}})
    row["result"] = "{ ceci n'est pas du JSON"
    assert _reconstruct_analyze_response(row) is None


def test_reconstruct_analyze_response_graham_absent_tolere(earnings_output_msft):
    """Contrat /ticker-report préservé : graham absent toléré (champ None, pas d'échec)."""
    from app.api.endpoints.ticker_report import _reconstruct_analyze_response

    row = _make_result_row({"earnings_quality": earnings_output_msft.model_dump()})
    resp = _reconstruct_analyze_response(row)
    assert resp is not None
    assert resp.graham is None
    assert resp.earnings_quality is not None


def test_skill_map_parite_des_deux_reconstructeurs(graham_output_msft, earnings_output_msft):
    """Parité : /report et /ticker-report reconstruisent les mêmes skills (esg + optionnel non-graham)."""
    from app.api.endpoints.report import _reconstruct_response
    from app.api.endpoints.ticker_report import _reconstruct_analyze_response

    row = _make_result_row(
        {
            "graham": graham_output_msft.model_dump(),
            "earnings_quality": earnings_output_msft.model_dump(),
            "esg_simplified": _make_esg_output_dict(),
        }
    )
    resp_a = _reconstruct_response(row)
    resp_b = _reconstruct_analyze_response(row)
    assert resp_b is not None
    assert resp_a.earnings_quality is not None and resp_b.earnings_quality is not None
    assert resp_a.esg is not None and resp_b.esg is not None


def test_reconstruct_response_result_illisible_propage():
    """Contrat /report : un result illisible propage (ne renvoie jamais None, à l'inverse de /ticker-report)."""
    import pytest

    from app.api.endpoints.report import _reconstruct_response

    row = _make_result_row({"graham": {}})
    row["result"] = "{ ceci n'est pas du JSON"
    with pytest.raises((ValueError, TypeError)):
        _reconstruct_response(row)


def test_reconstruct_response_graham_invalide_leve(graham_output_msft):
    """Contrat /report : graham présent mais malformé est validé strictement → lève (pas d'avalement)."""
    import pytest

    from app.api.endpoints.report import _reconstruct_response

    # graham présent mais non conforme au schéma (un optionnel invalide serait avalé, pas graham).
    row = _make_result_row(
        {"graham": {"champ_invalide": 1}, "esg_simplified": _make_esg_output_dict()}
    )
    with pytest.raises(ValueError):
        _reconstruct_response(row)
