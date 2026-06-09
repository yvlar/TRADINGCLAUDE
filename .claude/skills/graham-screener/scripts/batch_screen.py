#!/usr/bin/env python3
"""
batch_screen.py — Screening Graham en lot sur un univers complet (ex. S&P 500),
avec checkpoint/reprise, limitation de débit, et export des candidats au format
JSONL prêt pour l'ingestion Qdrant de TradingClaude.

Usage :
    # Univers S&P 500 récupéré en direct (Wikipedia), screening complet
    python batch_screen.py --universe sp500 --min-score 5

    # Univers depuis un fichier, reprise après interruption
    python batch_screen.py --universe-file mes_tickers.txt --resume

    # Test hors-ligne sur les données démo
    python batch_screen.py --universe demo

Sorties :
    output/batch_results.csv        — tous les titres, tous les scores
    output/candidates.jsonl         — documents d'ingestion (score >= min-score)
    output/checkpoint.json          — état de progression (reprise possible)

Conventions : identifiants en anglais, commentaires en français.
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

# Réutilise le moteur de screening du script principal
sys.path.insert(0, str(Path(__file__).parent))
from graham_screener import (
    DEFAULT_THRESHOLDS, evaluate_criteria,
    fetch_fundamentals_yf, fetch_fundamentals_demo, save_csv,
)

WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def load_universe(args) -> list:
    """Construit la liste de tickers selon la source demandée."""
    if args.universe == "demo":
        demo_path = Path(__file__).parent.parent / "assets" / "sample_data.json"
        return list(json.loads(demo_path.read_text()).keys())

    if args.universe_file:
        return [t.strip().upper() for t in
                Path(args.universe_file).read_text().splitlines() if t.strip()]

    if args.universe == "sp500":
        # Récupération en direct des constituants depuis Wikipedia (pandas.read_html)
        try:
            import pandas as pd
            tables = pd.read_html(WIKI_SP500_URL)
            tickers = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
            print(f"Univers S&P 500 : {len(tickers)} tickers récupérés")
            return tickers
        except Exception as e:
            # Repli sur la liste statique embarquée si le réseau échoue
            print(f"Récupération Wikipedia échouée ({e}); repli sur la liste statique")
            fallback = Path(__file__).parent.parent / "assets" / "universes.json"
            return json.loads(fallback.read_text())["sp500_fallback"]

    raise ValueError("Univers inconnu : utiliser sp500, demo, ou --universe-file")


def result_to_document(r, as_of: str) -> dict:
    """Transforme un ScreenResult en document JSONL pour l'ingestion Qdrant.

    Le champ `text` est le résumé en français destiné à l'embedding
    (text-embedding-3-small, comme le corpus investment_knowledge); le champ
    `payload` contient les métadonnées structurées pour le filtrage. Les champs
    `source_file` et `skill_id` alignent le payload sur celui lu par
    RagClient.search (app/rag/client.py).
    """
    failed = [c.name for c in r.criteria if c.passed is False]
    passed = [c.name for c in r.criteria if c.passed is True]
    details = "; ".join(f"{c.name}: {c.value}" for c in r.criteria)

    mos_txt = (f"{r.margin_of_safety*100:+.1f} %"
               if r.margin_of_safety is not None else "non calculable")
    text = (
        f"Screening Graham du {as_of} — {r.ticker} : score {r.score}/{r.evaluated}. "
        f"Prix {r.price} $, Graham Number {round(r.graham_number, 2) if r.graham_number else 'N/A'} $, "
        f"marge de sécurité {mos_txt}. "
        f"Critères réussis : {', '.join(passed) or 'aucun'}. "
        f"Critères échoués : {', '.join(failed) or 'aucun'}. "
        f"Détail : {details}. "
        + ("Évaluation sur données partielles (fenêtre < 10 ans). " if r.partial_data else "")
        + "Rappel : filtre quantitatif d'élimination, pas une recommandation d'achat."
    )

    return {
        "id": f"graham-{as_of}-{r.ticker}",
        "text": text,
        "payload": {
            "skill_id": "graham_screener",
            "source_file": f"graham-screener/{as_of}/{r.ticker}",
            "source": "graham-screener",
            "doc_type": "screening_result",
            "ticker": r.ticker,
            "as_of": as_of,
            "score": r.score,
            "evaluated": r.evaluated,
            "price": r.price,
            "graham_number": round(r.graham_number, 2) if r.graham_number else None,
            "margin_of_safety": round(r.margin_of_safety, 4) if r.margin_of_safety is not None else None,
            "partial_data": r.partial_data,
            "failed_criteria": failed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Screening Graham en lot + export Qdrant")
    parser.add_argument("--universe", default="sp500", choices=["sp500", "demo"],
                        help="Univers prédéfini (défaut : sp500)")
    parser.add_argument("--universe-file", help="Fichier texte, un ticker par ligne")
    parser.add_argument("--min-score", type=int, default=5,
                        help="Score minimal pour figurer dans candidates.jsonl (défaut : 5)")
    parser.add_argument("--output-dir", default="output", help="Répertoire de sortie")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Pause entre requêtes yfinance en secondes (défaut : 0.5)")
    parser.add_argument("--resume", action="store_true",
                        help="Reprendre depuis le checkpoint existant")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out / "checkpoint.json"
    as_of = date.today().isoformat()

    tickers = load_universe(args)
    demo_path = (Path(__file__).parent.parent / "assets" / "sample_data.json"
                 if args.universe == "demo" and not args.universe_file else None)

    # --- Reprise depuis checkpoint : on saute les tickers déjà traités ---
    done: dict = {}
    if args.resume and checkpoint_path.exists():
        done = json.loads(checkpoint_path.read_text())
        print(f"Reprise : {len(done)} tickers déjà traités")

    results = []
    for i, t in enumerate(tickers, 1):
        t = t.strip().upper()
        if t in done:
            continue
        try:
            f = (fetch_fundamentals_demo(t, demo_path) if demo_path
                 else fetch_fundamentals_yf(t))
            f["_ticker"] = t
            r = evaluate_criteria(f, DEFAULT_THRESHOLDS)
        except Exception as e:
            from graham_screener import ScreenResult
            r = ScreenResult(ticker=t, error=str(e))
        results.append(r)
        done[t] = {"score": r.score, "error": r.error}

        # Checkpoint tous les 25 titres : interruption sans perte de travail
        if i % 25 == 0:
            checkpoint_path.write_text(json.dumps(done))
            print(f"  [{i}/{len(tickers)}] checkpoint sauvegardé")
        if not demo_path and args.delay:
            time.sleep(args.delay)  # Courtoisie envers l'API gratuite

    checkpoint_path.write_text(json.dumps(done))

    # --- Tri et exports ---
    results.sort(key=lambda r: (-r.score, -(r.margin_of_safety or -9)))
    save_csv(results, str(out / "batch_results.csv"))

    candidates = [r for r in results if not r.error and r.score >= args.min_score]
    jsonl_path = out / "candidates.jsonl"
    with open(jsonl_path, "w") as fh:
        for r in candidates:
            fh.write(json.dumps(result_to_document(r, as_of), ensure_ascii=False) + "\n")

    errors = sum(1 for r in results if r.error)
    print(f"\nScreening terminé : {len(results)} titres, {errors} erreurs.")
    print(f"Candidats >= {args.min_score}/7 : {len(candidates)} -> {jsonl_path}")
    print("Prochaine étape : python .claude/skills/graham-screener/scripts/ingest_qdrant.py "
          f"--input {jsonl_path} --collection graham_screening")


if __name__ == "__main__":
    main()
