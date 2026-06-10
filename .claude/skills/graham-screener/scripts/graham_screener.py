#!/usr/bin/env python3
"""
graham_screener.py — Screening systématique des 7 critères de Benjamin Graham
(chapitre 14, The Intelligent Investor, éd. 1973) sur un univers de titres.

Usage :
    python graham_screener.py --tickers AAPL,BMY,KO --output results.csv
    python graham_screener.py --demo            # données d'exemple, sans réseau
    python graham_screener.py --tickers-file universe.txt --min-score 5

Dépendances : yfinance (mode réseau seulement), pandas.
Conventions : identifiants en anglais, commentaires en français.
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# --- Seuils configurables (adaptations modernes des seuils de 1973) ---
DEFAULT_THRESHOLDS = {
    "min_revenue": 2_000_000_000,   # Critère 1 : taille adéquate (2 G$, ajusté inflation)
    "min_current_ratio": 2.0,       # Critère 2a : ratio de liquidité générale
    "min_earnings_years": 4,        # Critère 3 : minimum d'années de données exigé
    "min_eps_cagr": 0.03,           # Critère 5 : ~équivalent annuel du +33 % sur 10 ans
    "max_pe": 15.0,                 # Critère 6 : P/E plafond (bénéfices moyens 3 ans)
    "max_pb": 1.5,                  # Critère 7a : P/B plafond
    "max_pe_pb_product": 22.5,      # Critère 7b : produit P/E × P/B (règle alternative)
}


@dataclass
class CriterionResult:
    """Résultat d'un critère individuel : verdict + valeur observée + note."""
    name: str
    passed: Optional[bool]          # None = données insuffisantes (N/A)
    value: str
    partial_data: bool = False      # True si évalué sur fenêtre plus courte que prévu par Graham


@dataclass
class ScreenResult:
    """Résultat complet d'un titre : 7 critères, score, Graham Number, marge."""
    ticker: str
    price: Optional[float] = None
    criteria: list = field(default_factory=list)
    score: int = 0
    evaluated: int = 0              # Nombre de critères évaluables (≠ N/A)
    graham_number: Optional[float] = None
    margin_of_safety: Optional[float] = None
    partial_data: bool = False
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Extraction de données — deux fournisseurs : yfinance (réseau) ou JSON (démo)
# ---------------------------------------------------------------------------

def fetch_fundamentals_yf(ticker: str) -> dict:
    """Récupère les fondamentaux via yfinance et les normalise au format interne.

    Format interne (toutes les listes sont du plus récent au plus ancien) :
    {price, revenue, current_assets, current_liabilities, long_term_debt,
     book_value_per_share, eps_history: [...], dividend_years: [...],
     eps_ttm, shares_outstanding}
    """
    import yfinance as yf  # Import local : absent en mode démo

    tk = yf.Ticker(ticker)
    info = tk.info or {}
    bs = tk.balance_sheet          # Bilan annuel (~4 ans)
    fin = tk.income_stmt           # État des résultats annuel (~4 ans)

    def latest(df, row):
        """Valeur la plus récente d'une ligne du DataFrame, sinon None."""
        try:
            if row in df.index:
                series = df.loc[row].dropna()
                return float(series.iloc[0]) if len(series) else None
        except Exception:
            pass
        return None

    def history(df, row):
        """Historique complet d'une ligne (du plus récent au plus ancien)."""
        try:
            if row in df.index:
                return [float(v) for v in df.loc[row].dropna().tolist()]
        except Exception:
            pass
        return []

    # Historique du BPA : dilué de préférence, sinon de base
    eps_history = history(fin, "Diluted EPS") or history(fin, "Basic EPS")

    # Années de versement de dividendes (approximation via l'historique yfinance)
    dividend_years = []
    try:
        divs = tk.dividends
        if divs is not None and len(divs):
            dividend_years = sorted({d.year for d in divs.index}, reverse=True)
    except Exception:
        pass

    return {
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "revenue": latest(fin, "Total Revenue"),
        "current_assets": latest(bs, "Current Assets"),
        "current_liabilities": latest(bs, "Current Liabilities"),
        "long_term_debt": latest(bs, "Long Term Debt"),
        "book_value_per_share": info.get("bookValue"),
        "eps_history": eps_history,
        "dividend_years": dividend_years,
        "eps_ttm": info.get("trailingEps"),
    }


def fetch_fundamentals_demo(ticker: str, demo_path: Path) -> dict:
    """Charge les fondamentaux depuis le fichier de données d'exemple (mode hors-ligne)."""
    data = json.loads(demo_path.read_text())
    if ticker not in data:
        raise KeyError(f"Ticker {ticker} absent des données démo")
    return data[ticker]


# ---------------------------------------------------------------------------
# Les 7 critères de Graham
# ---------------------------------------------------------------------------

def evaluate_criteria(f: dict, th: dict) -> ScreenResult:
    """Applique les 7 critères à un jeu de fondamentaux normalisés."""
    r = ScreenResult(ticker=f.get("_ticker", "?"), price=f.get("price"))
    c = []

    # --- Critère 1 : taille adéquate (revenus) ---
    rev = f.get("revenue")
    c.append(CriterionResult(
        "1. Taille adéquate",
        None if rev is None else rev >= th["min_revenue"],
        f"Revenus {rev/1e9:.1f} G$" if rev else "N/A",
    ))

    # --- Critère 2 : solidité financière (current ratio + dette LT vs fonds de roulement) ---
    ca, cl, ltd = f.get("current_assets"), f.get("current_liabilities"), f.get("long_term_debt")
    if ca and cl:
        current_ratio = ca / cl
        working_capital = ca - cl
        # Dette LT absente du bilan = 0 (conservateur seulement si la donnée existe vraiment)
        debt_ok = (ltd if ltd is not None else 0) <= working_capital
        passed = current_ratio >= th["min_current_ratio"] and debt_ok
        c.append(CriterionResult(
            "2. Solidité financière", passed,
            f"CR {current_ratio:.2f}, dette LT {'≤' if debt_ok else '>'} fonds de roulement",
        ))
    else:
        c.append(CriterionResult("2. Solidité financière", None, "N/A"))

    # --- Critère 3 : stabilité des bénéfices (positifs chaque année disponible) ---
    eps_hist = f.get("eps_history") or []
    if len(eps_hist) >= th["min_earnings_years"]:
        all_positive = all(e > 0 for e in eps_hist)
        c.append(CriterionResult(
            "3. Stabilité bénéfices", all_positive,
            f"{sum(1 for e in eps_hist if e > 0)}/{len(eps_hist)} années positives",
            partial_data=len(eps_hist) < 10,  # Graham exige 10 ans
        ))
    else:
        c.append(CriterionResult("3. Stabilité bénéfices", None,
                                 f"Seulement {len(eps_hist)} années de données"))

    # --- Critère 4 : dividendes ininterrompus ---
    div_years = f.get("dividend_years") or []
    if div_years:
        # Vérifie la continuité : aucune année manquante dans la fenêtre observée
        span = max(div_years) - min(div_years) + 1
        uninterrupted = span == len(div_years)
        c.append(CriterionResult(
            "4. Dividendes continus", uninterrupted,
            f"{len(div_years)} années, {'sans' if uninterrupted else 'AVEC'} interruption",
            partial_data=len(div_years) < 20,  # Graham exige 20 ans
        ))
    else:
        c.append(CriterionResult("4. Dividendes continus", False, "Aucun dividende"))

    # --- Critère 5 : croissance des bénéfices (CAGR du BPA) ---
    if len(eps_hist) >= th["min_earnings_years"] and eps_hist[-1] > 0 and eps_hist[0] > 0:
        years = len(eps_hist) - 1
        # eps_history est du plus récent au plus ancien
        cagr = (eps_hist[0] / eps_hist[-1]) ** (1 / years) - 1
        c.append(CriterionResult(
            "5. Croissance BPA", cagr >= th["min_eps_cagr"],
            f"CAGR {cagr*100:+.1f} %/an sur {years} ans",
            partial_data=years < 10,
        ))
    else:
        c.append(CriterionResult("5. Croissance BPA", None, "Données insuffisantes"))

    # --- Critère 6 : P/E ≤ 15 (sur bénéfices moyens 3 ans si disponibles) ---
    price = f.get("price")
    eps_basis = None
    if len(eps_hist) >= 3:
        eps_basis = sum(eps_hist[:3]) / 3   # Moyenne des 3 dernières années (lisse le cycle)
    elif f.get("eps_ttm"):
        eps_basis = f["eps_ttm"]
    pe = None
    # Garde-fou : un BPA moyen quasi nul produirait un P/E absurde
    if eps_basis is not None and abs(eps_basis) < 0.01:
        eps_basis = None
    if price and eps_basis and eps_basis > 0:
        pe = price / eps_basis
        c.append(CriterionResult("6. P/E ≤ 15", pe <= th["max_pe"],
                                 f"P/E {pe:.1f} (BPA moyen 3 ans)"))
    else:
        c.append(CriterionResult("6. P/E ≤ 15", None, "BPA négatif ou absent"))

    # --- Critère 7 : P/B ≤ 1,5 OU P/E × P/B ≤ 22,5 ---
    bvps = f.get("book_value_per_share")
    if price and bvps and bvps > 0:
        pb = price / bvps
        product_ok = pe is not None and (pe * pb) <= th["max_pe_pb_product"]
        passed = pb <= th["max_pb"] or product_ok
        detail = f"P/B {pb:.2f}" + (f", P/E×P/B {pe*pb:.1f}" if pe else "")
        c.append(CriterionResult("7. P/B modéré", passed, detail))
    else:
        c.append(CriterionResult("7. P/B modéré", None, "Valeur comptable négative ou absente"))

    # --- Score composite, Graham Number, marge de sécurité ---
    r.criteria = c
    r.score = sum(1 for x in c if x.passed is True)
    r.evaluated = sum(1 for x in c if x.passed is not None)
    r.partial_data = any(x.partial_data for x in c)

    eps_for_gn = f.get("eps_ttm") or (eps_hist[0] if eps_hist else None)
    if eps_for_gn and bvps and eps_for_gn > 0 and bvps > 0:
        r.graham_number = math.sqrt(22.5 * eps_for_gn * bvps)
        if price:
            r.margin_of_safety = (r.graham_number - price) / r.graham_number
    return r


# ---------------------------------------------------------------------------
# Orchestration et sortie
# ---------------------------------------------------------------------------

def run_screen(tickers: list, demo_path: Optional[Path], thresholds: dict) -> list:
    """Boucle de screening sur l'univers; tolère les erreurs ticker par ticker."""
    results = []
    for t in tickers:
        t = t.strip().upper()
        if not t:
            continue
        try:
            f = (fetch_fundamentals_demo(t, demo_path) if demo_path
                 else fetch_fundamentals_yf(t))
            f["_ticker"] = t
            results.append(evaluate_criteria(f, thresholds))
        except Exception as e:
            results.append(ScreenResult(ticker=t, error=str(e)))
    # Classement : score décroissant, puis marge de sécurité décroissante
    results.sort(key=lambda r: (-r.score, -(r.margin_of_safety or -9)))
    return results


def print_report(results: list) -> None:
    """Affiche le rapport console : tableau synthèse puis détail par titre."""
    print(f"\n{'='*78}\nGRAHAM SCREENER — {len(results)} titres analysés\n{'='*78}")
    print(f"{'Ticker':<8}{'Score':<10}{'Prix':<10}{'Graham №':<12}{'Marge séc.':<12}{'Données'}")
    print("-" * 78)
    for r in results:
        if r.error:
            print(f"{r.ticker:<8}ERREUR : {r.error[:55]}")
            continue
        gn = f"{r.graham_number:.2f}" if r.graham_number else "—"
        mos = f"{r.margin_of_safety*100:+.1f} %" if r.margin_of_safety is not None else "—"
        flag = "partielles" if r.partial_data else "ok"
        print(f"{r.ticker:<10}{str(r.score)+'/'+str(r.evaluated):<8}{r.price or '—':<10}{gn:<12}{mos:<12}{flag}")

    print(f"\n{'='*78}\nDÉTAIL PAR CRITÈRE\n{'='*78}")
    for r in results:
        if r.error:
            continue
        print(f"\n--- {r.ticker} (score {r.score}/{r.evaluated}) ---")
        for cr in r.criteria:
            verdict = "PASS" if cr.passed else ("FAIL" if cr.passed is False else "N/A ")
            partial = " [fenêtre courte]" if cr.partial_data else ""
            print(f"  [{verdict}] {cr.name:<26} {cr.value}{partial}")
    print("\nRappel : un score élevé = mérite une analyse qualitative (moat, thèse),")
    print("jamais un signal d'achat. Vérifier les chiffres aux états financiers.\n")


def save_csv(results: list, path: str) -> None:
    """Exporte les résultats en CSV pour intégration TradingClaude."""
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "score", "evaluated", "price", "graham_number",
                    "margin_of_safety", "partial_data", "failed_criteria", "error"])
        for r in results:
            failed = "; ".join(c.name for c in r.criteria if c.passed is False)
            w.writerow([r.ticker, r.score, r.evaluated, r.price,
                        round(r.graham_number, 2) if r.graham_number else "",
                        round(r.margin_of_safety, 4) if r.margin_of_safety is not None else "",
                        r.partial_data, failed, r.error or ""])
    print(f"Résultats exportés : {path}")


def main():
    parser = argparse.ArgumentParser(description="Screening des 7 critères de Graham")
    parser.add_argument("--tickers", help="Liste de tickers séparés par des virgules")
    parser.add_argument("--tickers-file", help="Fichier texte, un ticker par ligne")
    parser.add_argument("--demo", action="store_true",
                        help="Mode hors-ligne avec données d'exemple embarquées")
    parser.add_argument("--output", help="Chemin du CSV de sortie")
    parser.add_argument("--min-score", type=int, default=0,
                        help="N'afficher que les titres avec score ≥ N")
    args = parser.parse_args()

    demo_path = None
    if args.demo:
        demo_path = Path(__file__).parent.parent / "assets" / "sample_data.json"
        tickers = list(json.loads(demo_path.read_text()).keys())
    elif args.tickers:
        tickers = args.tickers.split(",")
    elif args.tickers_file:
        tickers = Path(args.tickers_file).read_text().splitlines()
    else:
        parser.error("Fournir --tickers, --tickers-file ou --demo")

    results = run_screen(tickers, demo_path, DEFAULT_THRESHOLDS)
    if args.min_score:
        results = [r for r in results if r.score >= args.min_score or r.error]
    print_report(results)
    if args.output:
        save_csv(results, args.output)


if __name__ == "__main__":
    main()
