# Synthèse d'audit & vérification des hypothèses

> **Système multi-agents d'audit.** Quatre agents auditeurs (`audit-investissement`, `audit-architecture`, `audit-code`, `audit-uiux`, définis dans `.claude/agents/`) ont analysé le projet et émis des hypothèses falsifiables. Un cinquième agent, `verificateur-hypotheses`, les a **confirmées ou infirmées contre le code réel**. Ce document consolide les verdicts et les conclusions transverses.

## 1. Méthode

```
4 agents auditeurs  ──émettent──▶  hypothèses falsifiables (fichier:ligne présumé)
                                          │
                                          ▼
                          agent verificateur-hypotheses
                          (Grep/Read, contexte, règles .claude/)
                                          │
                                          ▼
            verdict CONFIRMÉE / INFIRMÉE / PARTIELLE + preuve fichier:ligne
                                          │
                                          ▼
              correction des rapports de dimension (faux positifs retirés)
```

Chaque rapport de dimension (`01`→`04`) a été **corrigé** après vérification : les constats infirmés sont barrés, les sévérités révisées, les faux positifs retirés des listes d'améliorations.

## 2. Tableau des verdicts (15 hypothèses)

| ID | Dimension | Assertion (résumée) | Verdict | Preuve `fichier:ligne` | Note |
|----|-----------|---------------------|---------|------------------------|------|
| H-A | Invest. | Aucun contrôle de fraîcheur (`ratios_fetched_at` jamais comparé à `now()`) | **CONFIRMÉE** | `yahoo_finance.py:298,443,506` (écriture seule) ; aucun `now()−fetched_at` | `now()` ne sert qu'à horodater |
| H-B | Invest. | `sedar_plus.extract()` retourne toujours `None` même si HTTP 200 | **CONFIRMÉE** | `sedar_plus.py:55` `return None` après `status_code==200` | Stub assumé/documenté (`:36-37`) |
| H-C | Invest. | Croissance EPS Graham sur ~4 ans, pas 10 | **PARTIELLE** | `yahoo_finance.py:52` horizon **dynamique** `len(values)-1`, pas une constante | Code plus honnête que l'assertion ; trace `eps_growth_years` |
| H-D | Invest. | Nombre de Graham = `None` si EPS≤0 ou BVPS≤0 | **CONFIRMÉE** | `financial_calculations.py:226` | Intentionnel (formule indéfinie) |
| H-G | Archi. | Service `qdrant` sans `healthcheck` Docker | **CONFIRMÉE** | `docker-compose.yml` (qdrant sans bloc ; postgres a `pg_isready`) ; `depends_on: service_started` | Factuel |
| H-H | Archi. | Erreurs Langfuse loggées en DEBUG (silencieux) | **CONFIRMÉE** | `observability.py:99-102` `except: logger.debug(...)` | Le `except` externe `:140-145` est en `logger.exception` |
| H-K | Archi. | `APP_DATABASE_URL`→`DATABASE_URL` : repli **silencieux** cassant la RLS | **INFIRMÉE** | `security_config.py:29-38` repli **dev-only** ; hors dev → `raise RuntimeError` | **Faux positif** : invariant de sécurité, pas un défaut |
| H-L | Code | `tests/db/` quasi vide, **aucun** test d'isolation cross-tenant | **INFIRMÉE** | `tests/integration/test_rls_isolation.py:126` `test_matrice_isolation_cross_tenant` (6 tables) + ~15 `*_rls.py` | **Faux positif** : couverture explicite présente |
| H-M | Code | mypy `strict=false` + `disable_error_code` + `ignore_errors=true` | **CONFIRMÉE** | `pyproject.toml:27,30` + override `ignore_errors=true` (11 modules) | Type-check non bloquant |
| H-N | Code | `price_alert_service.py` : `except Exception` qui **avale** l'erreur | **PARTIELLE** | `price_alert_service.py:71-72` `logger.exception(...)` (ERROR + stacktrace) | N'avale pas ; seul manque le correlation ID (absent côté workers) |
| H-O | Code | `costs.py` : repli silencieux sur tarif sonnet pour modèle inconnu | **CONFIRMÉE** | `costs.py:29` `PRICING.get(model, PRICING["claude-sonnet-4-6"])` | Aucun log sur modèle inconnu |
| H-Q | UI/UX | Overflow des tables incohérent (certaines oui, d'autres non) | **INFIRMÉE** | `ui/table.tsx:6` `overflow-auto` partagé ; 3 tables via `<Table>` | **Faux positif** : overflow uniforme |
| H-R | UI/UX | `ScreenerPage.tsx` utilise `alert()` pour les erreurs d'export | **CONFIRMÉE** | `ScreenerPage.tsx:49,65` | Factuel |
| H-S | UI/UX | `CommandPalette` sans `aria-modal` ni focus trap | **CONFIRMÉE** | `CommandPalette.tsx:99` overlay `fixed inset-0` sans rôle ; seul Escape géré `:115` | Factuel |
| H-T | UI/UX | Aucun `aria-sort` sur les en-têtes de `ScreenerTable` | **INFIRMÉE** | `ScreenerTable.tsx:158` `<TableHead aria-sort={ariaSort}>` | **Faux positif** : déjà présent |

## 3. Compteurs

| Verdict | Nombre | IDs |
|---------|--------|-----|
| ✅ CONFIRMÉE | **9** | H-A, H-B, H-D, H-G, H-H, H-M, H-O, H-R, H-S |
| ❌ INFIRMÉE | **4** | H-K, H-L, H-Q, H-T |
| 🟡 PARTIELLE | **2** | H-C, H-N |

**Taux de faux positifs des auditeurs : 4/15 (27 %)** — ce qui justifie à lui seul l'étape de vérification adverse : sans elle, deux *forces de sécurité* (RLS bien testée, repli DB fail-closed) auraient été présentées comme des risques, et deux constats UI/UX inexistants auraient généré du travail inutile.

## 4. Conclusions transverses (après vérification)

### Vraies priorités confirmées

| Priorité | Dimension | Action | Source |
|----------|-----------|--------|--------|
| **P1** | Invest. | Validation de fraîcheur des ratios (avert. >30 j, flag/blocage >90 j) | H-A |
| **P1** | Code | Activer `mypy strict` graduellement (retirer les `ignore_errors`) | H-M |
| **P2** | Code | `ValueError` sur modèle Claude inconnu (au lieu du repli tarif silencieux) | H-O |
| **P2** | Archi. | `healthcheck` Qdrant + Langfuse en WARNING | H-G, H-H |
| **P2** | UI/UX | Focus trap/`aria-modal` sur `CommandPalette` ; remplacer `alert()` par inline | H-S, H-R |
| **P3** | Invest. | SEDAR+ : implémenter une vraie source ou documenter le retrait du stub | H-B |

### Faux positifs écartés (à NE PAS corriger)

1. **Isolation RLS cross-tenant** (H-L) — déjà couverte par `test_matrice_isolation_cross_tenant` (6 tables) et ~15 tests `*_rls.py`. La sécurité multi-tenant est **testée**, pas trouée.
2. **Repli DSN runtime** (H-K) — `APP_DATABASE_URL`→`DATABASE_URL` est **dev-only et fail-closed en prod** (`RuntimeError`). C'est un garde-fou, pas une faille.
3. **Overflow des tables** (H-Q) et **`aria-sort`** (H-T) — déjà gérés (composant `ui/table.tsx` partagé ; `aria-sort` présent).

### Constats à requalifier (vrais faits, mais pas des « bugs »)

- H-B (stub SEDAR+), H-O (repli tarif), H-H (DEBUG Langfuse) : **faits réels mais choix de conception/dette assumée** — à traiter comme amélioration, pas comme défaut bloquant.
- H-C, H-N : **exagérés à l'émission** — le code est plus robuste que l'hypothèse (horizon EPS tracé ; erreurs loggées en ERROR).

## 5. Verdict global du système

TradingClaude est un projet **mature et bien construit** sur les quatre dimensions. La vérification adverse confirme que **les invariants de sécurité les plus coûteux (isolation multi-tenant, fail-closed DB) sont solides et testés**. Les améliorations réelles sont ciblées et à faible/moyen effort, dominées par deux thèmes : la **fraîcheur/provenance des données financières** (H-A, H-B) et le **durcissement du typage et des replis silencieux** (H-M, H-O). Aucun défaut critique non couvert n'a survécu à la vérification.

---

*Rapports de dimension : [`01-investissement.md`](01-investissement.md) · [`02-architecture.md`](02-architecture.md) · [`03-code.md`](03-code.md) · [`04-uiux.md`](04-uiux.md). Agents réutilisables : `.claude/agents/`.*
