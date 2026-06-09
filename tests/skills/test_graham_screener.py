"""
Tests d'intégration — skill graham-screener (scripts batch, mode démo hors-ligne).

Ces tests vérifient :
  - Le moteur de screening classe correctement l'univers démo (VALUECO 7/7 premier)
  - Le Graham Number et la marge de sécurité sont calculés correctement
  - Le document JSONL d'ingestion porte le payload aligné sur RagClient.search
  - Le flux complet batch_screen → ingest_qdrant fonctionne sans réseau
    (Qdrant :memory: + embedder dummy)

Aucun appel réseau ni appel Claude — scripts purement mécaniques.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_SKILL_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / "graham-screener"
_SCRIPTS_DIR = _SKILL_DIR / "scripts"


def _load_module(name: str):
    """Charge un script du skill comme module (les scripts ne sont pas un package)."""
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def screener():
    return _load_module("graham_screener")


@pytest.fixture(scope="module")
def batch():
    return _load_module("batch_screen")


@pytest.fixture(scope="module")
def demo_results(screener):
    """Screening complet de l'univers démo, classé."""
    demo_path = _SKILL_DIR / "assets" / "sample_data.json"
    tickers = list(json.loads(demo_path.read_text()).keys())
    return screener.run_screen(tickers, demo_path, screener.DEFAULT_THRESHOLDS)


def test_demo_ranking_valueco_first(demo_results):
    """VALUECO passe les 7 critères et arrive en tête du classement."""
    top = demo_results[0]
    assert top.ticker == "VALUECO"
    assert top.score == 7
    assert top.evaluated == 7
    assert all(c.passed is True for c in top.criteria)


def test_demo_valueco_margin_of_safety(demo_results):
    """Graham Number ≈ 59.60 $ et marge de sécurité ≈ +29.5 % pour VALUECO."""
    top = demo_results[0]
    assert top.graham_number == pytest.approx(59.60, abs=0.01)
    assert top.margin_of_safety == pytest.approx(0.295, abs=0.001)


def test_demo_trapco_eliminated(demo_results):
    """TRAPCO (value trap) arrive dernier avec un score ≤ 2."""
    last = demo_results[-1]
    assert last.ticker == "TRAPCO"
    assert last.score <= 2
    # Le critère 6 doit être N/A (BPA moyen quasi nul), pas un P/E absurde
    crit6 = next(c for c in last.criteria if c.name.startswith("6."))
    assert crit6.passed is None


def test_demo_partial_data_flagged(demo_results):
    """Les critères 3/4/5 évalués sur fenêtre < 10-20 ans portent le drapeau partial_data."""
    for r in demo_results:
        assert r.partial_data is True


def test_result_to_document_payload(batch, demo_results):
    """Le document JSONL porte les champs requis + ceux lus par RagClient.search."""
    doc = batch.result_to_document(demo_results[0], "2026-06-09")
    assert doc["id"] == "graham-2026-06-09-VALUECO"
    assert "recommandation d'achat" in doc["text"]  # rappel filtre ≠ recommandation
    payload = doc["payload"]
    for required in ("source", "doc_type", "ticker", "as_of", "score",
                     "margin_of_safety", "failed_criteria",
                     "skill_id", "source_file"):
        assert required in payload, f"champ manquant : {required}"
    assert payload["ticker"] == "VALUECO"
    assert payload["failed_criteria"] == []


def test_e2e_batch_then_ingest_memory(tmp_path):
    """Flux complet hors-ligne : batch_screen démo → ingest_qdrant :memory: + dummy."""
    py = sys.executable
    out_dir = tmp_path / "graham"

    screen = subprocess.run(
        [py, str(_SCRIPTS_DIR / "batch_screen.py"),
         "--universe", "demo", "--output-dir", str(out_dir)],
        capture_output=True, text=True, timeout=120,
    )
    assert screen.returncode == 0, screen.stderr
    candidates = out_dir / "candidates.jsonl"
    assert candidates.exists()
    lines = [json.loads(l) for l in candidates.read_text().splitlines() if l.strip()]
    assert len(lines) == 1 and lines[0]["payload"]["ticker"] == "VALUECO"

    ingest = subprocess.run(
        [py, str(_SCRIPTS_DIR / "ingest_qdrant.py"),
         "--input", str(candidates), "--url", ":memory:", "--embedder", "dummy"],
        capture_output=True, text=True, timeout=120,
    )
    assert ingest.returncode == 0, ingest.stderr
    assert "Ingestion terminée : 1 candidats" in ingest.stdout
    assert "VALUECO" in ingest.stdout  # la requête de similarité le retrouve
