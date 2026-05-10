#!/usr/bin/env python3
"""
CLI d'analyse financière — wrapping de POST /analyze, rapport Markdown automatique.

Usage :
    # Fichier JSON complet (recommandé pour analyses multi-skills)
    python scripts/analyze_cli.py BNS --ratios-file data/bns_full.json

    # Ratios Graham inline (analyse rapide)
    python scripts/analyze_cli.py BNS \\
        --pe 11.0 --pb 1.3 --price 80.0 --eps 7.25 \\
        --book-value 61.5 --debt-equity 0.45 --eps-growth-10y 0.27

    # Activer la thèse et l'analyse Munger
    python scripts/analyze_cli.py BNS --ratios-file data/bns_full.json --thesis --munger

    # Afficher sur stdout sans sauvegarder (utile pour redirection)
    python scripts/analyze_cli.py BNS --ratios-file data/bns.json --stdout > rapport.md

Format du fichier JSON (--ratios-file) :
    Forme minimale — GrahamRatios seulement :
        {"pe": 11.0, "pb": 1.3, "price": 80.0, ...}

    Forme complète — tous les skills :
        {
            "ratios": {"pe": 11.0, ...},
            "earnings_ratios": {...},
            "dorsey_ratios": {...},
            "buffett_ratios": {...},
            "valuation_ratios": {...},
            "thesis_ratios": true,
            "munger_ratios": true,
            "tax_input": {"ticker": "BNS", "position_size_pct": 5.0, ...}
        }
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Ajoute scripts/ au sys.path pour l'import de cli.formatter
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402 (après le sys.path)

from cli.formatter import format_analyse_markdown  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_DEFAULT_API_URL = "http://localhost:8000"
_DEFAULT_OUTPUT_DIR = Path("analyses")
_REQUEST_TIMEOUT = 120.0  # 2 min — pipeline complet peut prendre 40-80s


# ─── Argument parser ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Copilote financier IA — analyse et rapport Markdown automatique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("ticker", help="Symbole boursier (ex : BNS, AAPL, BNS.TO)")

    src = p.add_argument_group("Source des ratios (--ratios-file OU ratios inline)")
    src.add_argument(
        "--ratios-file", "-f",
        type=Path,
        metavar="FILE",
        help="JSON contenant les ratios. Forme minimale (GrahamRatios plat) ou complète avec clé 'ratios'.",
    )
    # Ratios Graham inline
    src.add_argument("--pe", type=float, help="Price/Earnings")
    src.add_argument("--pb", type=float, help="Price/Book")
    src.add_argument("--price", type=float, help="Prix actuel de l'action")
    src.add_argument("--eps", type=float, help="BPA TTM (trailing 12 months)")
    src.add_argument("--book-value", type=float, help="Valeur comptable par action (calculée depuis price/pb si absente)")
    src.add_argument("--debt-equity", type=float, help="Dette totale / Capitaux propres")
    src.add_argument("--eps-growth-10y", type=float, help="Croissance BPA 10 ans (fraction : 0.85 = 85%%)")
    src.add_argument("--current-ratio", type=float, default=None, help="Actif/Passif circulant (omettre pour les banques)")
    src.add_argument("--revenue-bn", type=float, default=None, help="Revenus annuels en milliards")
    src.add_argument("--dividend-years", type=int, default=None, help="Années de dividendes consécutifs")

    opt = p.add_argument_group("Skills optionnels")
    opt.add_argument("--thesis", action="store_true", help="Activer investment_thesis_builder")
    opt.add_argument(
        "--munger",
        action="store_true",
        help="Activer munger_mental_models (requiert --thesis)",
    )

    out = p.add_argument_group("Sortie")
    out.add_argument(
        "--api-url",
        default=_DEFAULT_API_URL,
        help=f"URL de l'API FastAPI (défaut : {_DEFAULT_API_URL})",
    )
    out.add_argument(
        "--api-key",
        default=None,
        help="Bearer token (ou variable d'environnement API_KEY)",
    )
    out.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Répertoire de sauvegarde du rapport (défaut : {_DEFAULT_OUTPUT_DIR}/)",
    )
    out.add_argument(
        "--stdout",
        action="store_true",
        help="Afficher le Markdown sur stdout uniquement (pas de fichier)",
    )
    out.add_argument("--verbose", "-v", action="store_true", help="Logs détaillés (DEBUG)")

    return p


# ─── Construction du payload ──────────────────────────────────────────────────

_INLINE_REQUIRED = ["pe", "pb", "price", "debt_equity", "eps_growth_10y"]


def _build_request_body(args: argparse.Namespace) -> dict:
    """Construit le payload JSON pour POST /analyze depuis les arguments CLI."""
    if args.ratios_file:
        if not args.ratios_file.exists():
            raise SystemExit(f"Fichier introuvable : {args.ratios_file}")
        raw: dict = json.loads(args.ratios_file.read_text(encoding="utf-8"))
        # JSON plat (juste GrahamRatios) → encapsuler dans "ratios"
        body: dict = {"ticker": args.ticker}
        if "ratios" in raw:
            body.update(raw)
        else:
            body["ratios"] = raw
        # Les flags CLI --thesis et --munger peuvent surcharger le fichier
        if args.thesis:
            body["thesis_ratios"] = True
        if args.munger:
            body["munger_ratios"] = True
        return body

    # Mode inline — valider les champs obligatoires
    missing = [
        f"--{field.replace('_', '-')}"
        for field in _INLINE_REQUIRED
        if getattr(args, field, None) is None
    ]
    if missing:
        raise SystemExit(
            f"Sans --ratios-file, les arguments suivants sont obligatoires : {', '.join(missing)}\n"
            "Exemple minimal :\n"
            "  python scripts/analyze_cli.py BNS \\\n"
            "    --pe 11 --pb 1.3 --price 80 --debt-equity 0.45 --eps-growth-10y 0.27"
        )

    ratios: dict = {
        "pe": args.pe,
        "pb": args.pb,
        "price": args.price,
        "debt_equity": args.debt_equity,
        "eps_growth_10y": args.eps_growth_10y,
    }

    # book_value dérivé depuis price/pb si absent (évite un 422 de l'API)
    if args.book_value is not None:
        ratios["book_value"] = args.book_value
    elif args.price and args.pb:
        ratios["book_value"] = round(args.price / args.pb, 4)

    # eps_ttm dérivé depuis price/pe si absent
    if args.eps is not None:
        ratios["eps_ttm"] = args.eps
    elif args.price and args.pe:
        ratios["eps_ttm"] = round(args.price / args.pe, 4)

    if args.current_ratio is not None:
        ratios["current_ratio"] = args.current_ratio
    if args.revenue_bn is not None:
        ratios["revenue_bn"] = args.revenue_bn
    if args.dividend_years is not None:
        ratios["dividend_years"] = args.dividend_years

    return {
        "ticker": args.ticker,
        "ratios": ratios,
        "thesis_ratios": args.thesis,
        "munger_ratios": args.munger,
    }


# ─── Chemin de sortie ─────────────────────────────────────────────────────────

def _output_path(ticker: str, output_dir: Path) -> Path:
    """Génère : analyses/BNS-2026-05.md (ou BNS-TO-2026-05.md)"""
    today = date.today()
    safe_ticker = ticker.upper().replace(".", "-")
    filename = f"{safe_ticker}-{today.year:04d}-{today.month:02d}.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


# ─── Point d'entrée ───────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.ratios_file and args.pe is None:
        parser.error(
            "Fournir --ratios-file OU les ratios inline (--pe, --pb, --price, "
            "--debt-equity, --eps-growth-10y au minimum)."
        )

    api_key = args.api_key or os.environ.get("API_KEY", "")

    try:
        body = _build_request_body(args)
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Erreur lecture fichier : {exc}") from exc

    logger.info("Analyse de %s via %s", args.ticker.upper(), args.api_url)
    logger.debug("Payload : %s", json.dumps(body, indent=2, ensure_ascii=False))

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{args.api_url}/analyze",
                json=body,
                headers=headers,
            )
    except httpx.ConnectError as exc:
        raise SystemExit(
            f"Connexion refusée à {args.api_url}.\n"
            "Vérifiez que l'infrastructure est démarrée : docker-compose up -d"
        ) from exc
    except httpx.TimeoutException as exc:
        raise SystemExit(
            f"Timeout ({_REQUEST_TIMEOUT}s dépassés).\n"
            "Le pipeline complet peut prendre 40-80s selon les skills activés.\n"
            "Pour les analyses longues, utilisez POST /analyze-async."
        ) from exc

    if response.status_code == 401:
        raise SystemExit("Erreur 401 — clé API invalide ou absente (--api-key ou variable API_KEY).")
    if response.status_code == 422:
        try:
            detail = response.json().get("detail", response.text[:300])
        except Exception:
            detail = response.text[:300]
        raise SystemExit(f"Erreur 422 — ratios invalides :\n{detail}")
    if response.status_code == 429:
        raise SystemExit("Erreur 429 — rate limit atteint (10 req/min). Réessayez dans 60 secondes.")
    if response.status_code != 200:
        raise SystemExit(f"Erreur API {response.status_code} :\n{response.text[:500]}")

    result = response.json()
    skills = result.get("skills_applied", [])
    cost = result.get("cost_usd", 0.0)
    logger.info("Succès — %d skill(s) | coût : $%.4f USD", len(skills), cost)

    markdown = format_analyse_markdown(result)

    if args.stdout:
        print(markdown)
        return

    out_path = _output_path(args.ticker, args.output_dir)
    out_path.write_text(markdown, encoding="utf-8")

    print(f"\nRapport généré    : {out_path}")
    print(f"Skills appliqués  : {', '.join(skills)}")
    print(f"Coût API          : ${cost:.4f} USD")
    print(f"ID analyse        : {result.get('analysis_id', 'N/A')}")


if __name__ == "__main__":
    main()
