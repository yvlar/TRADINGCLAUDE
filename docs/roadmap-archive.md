# ROADMAP — Archive historique des sprints

> Historique complet déplacé hors de `ROADMAP.md` (hygiène 2026-05-28) pour réduire le coût d'amorçage des sessions Claude Code.
> `ROADMAP.md` ne conserve que l'état courant + les ~4 derniers sprints. **Ce fichier n'est pas lu à l'amorçage d'un sprint.**

---

## Phases complétées

### Phase 0 — Bootstrap ✅
API FastAPI + graham_analysis + PostgreSQL + prompt caching.

### Sprint 125 — Durcissement sécurité auth & fail-safe (P0) ✅

**Objectif :** Éliminer quatre faiblesses de sécurité de la couche auth/middleware relevées par la revue expert FinTech (`docs/revue-expert-fintech.md` §5), sans changer le comportement fonctionnel pour un déploiement correctement configuré. Sprint backend pur — aucune migration DB, aucun changement de prompt de skill (evals non concernées).

**Livrables :**
- `app/utils/jwt_secret.py` — `resolve_jwt_secret()` : **fail-fast** par défaut. Si `JWT_SECRET_KEY` absent, lève `RuntimeError` sauf si `APP_ENV ∈ {dev, development, test, testing}` (repli secret de dev toléré). `APP_ENV` absent = traité comme production (refus). Chaîne vide traitée comme absente. Câblé dans `auth_token_service.py` ET `password_reset_service.py` (qui partageaient le même secret de repli codé en dur — trou fermé partout)
- `app/services/auth_token_service.py` — `is_jti_blacklisted` **fail-closed** : appel Redis enveloppé dans `try/except` → panne Redis = token considéré révoqué (`True`). Les deux appelants (`middleware/auth.py:99`, `endpoints/auth.py:105`) rejettent en 401. Contraire au rate-limiting fail-open, par choix de sécurité
- `app/utils/error_sanitization.py` — `log_internal_error()` (log serveur-side + `correlation_id`) + `sanitized_http_500()` (HTTPException 500 au body générique). Appliqué au global exception handler (`main.py`), au `/analyze`, et à **tous les endpoints à chemin 500** (report, screen, screener_report, monthly_report, ticker_report, compare, extract, annotations, export) + au flux SSE `analyze_stream.py` — `str(exc)` ne sort plus jamais dans un body HTTP/SSE (anti-énumération d'utilisateurs)
- `app/api/main.py` — CORS durci : `allow_methods` explicite (`GET/POST/PUT/DELETE/OPTIONS`) ; origines lues depuis `CORS_ORIGINS` (CSV) avec repli localhost en dev
- `.env.example` — `APP_ENV=dev` + `CORS_ORIGINS` documentés
- `tests/conftest.py` — `os.environ.setdefault("APP_ENV", "test")` pour que le lifespan réel exercé en test tolère le repli secret
- Tests : unitaire `tests/services/test_jwt_secret.py` (8) + `test_auth_token_service.py` (fail-fast init + fail-closed blacklist, 5) ; intégration `tests/api/test_exception_sanitization.py` (global handler + `/analyze` + `/screen` n'exposent pas `str(exc)`, 3) — aucune régression des tests auth existants

**Version** : 10.13.0
**Tests** : 1 478 backend collectés (1 474 passés, 3 skipped, 1 xfailed — +16) ; 406 Vitest verts (inchangé, sprint backend pur) ; ruff `All checks passed`

**Note d'environnement :** session web — stack Docker (Postgres/Redis/Qdrant) non démarrée : le fail-closed Redis et le fail-fast au boot lifespan sont validés sur mocks (`AsyncMock` levant une exception, `monkeypatch` sur `APP_ENV`/`JWT_SECRET_KEY`), pas live. CORS vérifié observablement (parsing CSV + méthodes explicites via introspection du middleware). Pas de test navigateur live. Sprint sans changement de prompt → evals non concernées.

### Sprint 124 — Persistance des préférences Screener côté serveur ✅

**Objectif :** Migrer le tri + les filtres du Screener du `localStorage` (Sprint 109) vers une table `user_preferences` PostgreSQL liée au compte authentifié, pour offrir une continuité multi-appareils. Le `localStorage` reste un fallback hors-ligne / anti-flash.

**Livrables :**
- `infra/postgres/migration_sprint124.sql` + bootstrap lifespan (`app/api/main.py`) + `init.sql` — table `user_preferences (user_id UUID, key TEXT, value JSONB, updated_at, PRIMARY KEY (user_id, key))` ; FK `REFERENCES users(id) ON DELETE CASCADE` posée par le lifespan + la migration (la table `users` n'existe pas dans le schéma Phase 0 `init.sql`)
- `app/services/user_preferences_service.py` — `get_preference` / `upsert_preference` (asyncpg, `INSERT ... ON CONFLICT (user_id, key) DO UPDATE`) ; `_decode_jsonb` gère JSONB renvoyé en `str` (aucun codec) ou déjà décodé
- `app/api/endpoints/preferences.py` — `GET`/`PUT /preferences/screener`, auth-scopés via `_get_current_user` (cookie JWT) plutôt que `request.state.user_id` (jamais posé en mode dev/test où l'auth est bypassée) ; GET tolère une préférence corrompue (→ `ScreenerPreferences()` au lieu d'un 500) ; schemas Pydantic v2 dédiés (`app/models/preferences.py`)
- `frontend/src/api/preferences.ts` — client typé `getScreenerPreferences`/`putScreenerPreferences` (CSRF/cookies, échec silencieux → `null`)
- `frontend/src/types/index.ts` — types `ScreenerSortKey`/`ScreenerSortState`/`ScreenerPreferences` (source canonique ; `screenerView.ts` réexporte `SortKey`/`SortState`, suppression du doublon)
- `frontend/src/components/ScreenerTable.tsx` — hydratation serveur au montage (fallback localStorage si 401 / réseau KO / champ null), persistance serveur + miroir localStorage à chaque changement de tri/filtre
- Tests : intégration `tests/api/test_preferences_endpoints.py` (401, round-trip, upsert idempotent, 422 clé invalide, JSONB str, valeur corrompue) ; unitaire `tests/services/test_user_preferences_service.py` ; composant `frontend/src/__tests__/ScreenerTablePreferences.test.tsx` (hydratation, filtre serveur, fallback localStorage, persistance)

**Version** : 10.11.0
**Tests** : 1 448 backend collectés (1 444 passés, 3 skipped, 1 xfailed — +6 Sprint 124) ; 400 Vitest verts (+4 Sprint 124) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — stack Docker (Postgres/Redis/Qdrant) non démarrée : la migration SQL n'est pas exécutée live (syntaxe validée + tests d'intégration sur pool stateful mocké). Pas de test navigateur live. Sprint sans changement de prompt de skill → evals non concernées.

### Sprint 123 — Code-splitting des routes + lazy-load recharts ✅

**Objectif :** Accélérer le Time-To-Interactive de la première vue en isolant chaque page et la librairie recharts (lourde) du bundle d'entrée. Avant ce sprint, toutes les pages étaient importées statiquement dans le routeur — le navigateur téléchargeait tout le code (recharts compris) avant le premier rendu.

**Livrables :**
- `frontend/src/App.tsx` — conversion des 14 imports de pages statiques en `React.lazy(() => import('./pages/...'))` (Analyse, Screener, Historique, Dashboard, Watchlist, Comparer, ESG, Recherche, Alertes, Admin + 4 pages auth) ; `<Routes>` enveloppé dans un unique `<Suspense fallback={<RouteFallback />}>` placé sous le shell (header, palette, nav restent eager)
- `frontend/src/components/RouteFallback.tsx` — squelette de chargement de chunk réutilisant la primitive `ui/skeleton` ; respecte `max-w-shell` + tokens de design ; `role="status"` / `aria-busy` / texte `sr-only` pour l'accessibilité
- `frontend/src/__tests__/RouteFallback.test.tsx` — 2 tests Vitest (rend sans erreur + conteneur status `aria-busy` ; respect de `max-w-shell`)
- `frontend/src/__tests__/LazyRouting.test.tsx` — 1 test Vitest déterministe (promesse de chunk contrôlée) : le fallback skeleton apparaît, puis la page lazy le remplace après résolution
- **Découpage vérifié via `vite build`** : un chunk séparé par page (`AnalyzePage`, `DashboardPage`, `ScreenerPage`, … les 14) ; recharts isolé dans des chunks dédiés (`colors`, `YAxis`) chargés uniquement par les pages graphiques (Dashboard/ESG/Watchlist/Comparer) — le bundle d'entrée ne référence que le nom de fichier du chunk, aucun code recharts (0 marqueur interne)

**Version** : 10.10.0
**Tests** : 1 432 backend verts (3 skipped, 1 xfailed — inchangé, sprint frontend pur) ; 396 Vitest verts (+3 Sprint 123) ; tsc 0 erreur ; ESLint 0 ; ruff `All checks passed`

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0), Vitest composant (+3), la vérification du `vite build` (chunks séparés + recharts hors entrée), et la suite backend complète (1 432 verts, ruff clean).

### Sprint 121 — Refonte UI Fisher + Damodaran + Marks + Pabrai + Fiscalité ✅

**Objectif :** Clôturer la refonte UI démarrée aux Sprints 118-120 sur les cinq derniers skills encore affichés en JSON brut générique (`SkillSection`) — créer des composants React structurés typés depuis les schemas Pydantic backend, puis retirer le composant générique devenu inutile.

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `FisherPoint`, `FisherOutput`, `DamodaranOutput`, `MarksOutput`, `DhandhoPrincipe`, `PabraiOutput`, `CanadianTaxOutput` ; `AnalyzeResponse.fisher`, `.damodaran`, `.marks`, `.pabrai` et `.canadian_tax` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/FisherSection.tsx` — en-tête avec badge qualité de direction (libellé FR : exceptionnelle/bonne/adéquate/médiocre) + verdict badge (ACHAT_FORT/ACHAT/CONSERVER/EVITER) ; score Fisher /30 ; liste des 15 points (titre + commentaire + score /2 coloré) ; recommandations
- `frontend/src/components/DamodaranSection.tsx` — en-tête avec badge cohérence + verdict badge (NARRATIVE_FORTE/ACCEPTABLE/FAIBLE/INCOHERENTE) ; échelle possible→plausible→probable (niveau atteint mis en évidence, état incohérent en rouge) ; solidité de la narrative /10 ; ERP implicite en % (masqué si null) ; divergences en badges ; recommandations
- `frontend/src/components/MarksSection.tsx` — en-tête avec badge position de cycle (libellé FR : pessimisme excessif/pessimisme/neutre/optimisme/euphorie) + badge timing (ACHETER_AGRESSIF/ACHETER_PRUDEMMENT/ATTENDRE/REDUIRE/VENDRE) ; jauge du pendule −5→+5 avec marqueur et score coloré selon la logique contrariante ; second-level thinking ; recommandations
- `frontend/src/components/PabraiSection.tsx` — en-tête avec verdict badge (DHANDHO_FORT/DHANDHO_MOYEN/PAS_DHANDHO) ; asymétrie upside/downside (×, colorée) ; Kelly fractionnel en % (N/A si null) ; score heads-I-win /9 ; grille des 9 principes Dhandho (✓/✗ + commentaire) ; recommandations
- `frontend/src/components/CanadianTaxSection.tsx` — en-tête avec badge compte recommandé (libellé FR + sigle EN : CELI (TFSA)/REER (RRSP)/CELIAPP (FHSA)/non-enregistré) ; justification fiscale ; taux d'inclusion du gain en capital en % ; badge Smith Manœuvre si applicable ; retenue à la source US (masquée si null) ; recommandations
- `frontend/src/components/AnalysisResult.tsx` — branchement sur les cinq nouveaux composants ; **retrait du composant `SkillSection` générique et de l'import `SkillOutput`** (plus aucun skill en JSON brut)
- `frontend/src/__tests__/FisherSection.test.tsx`, `DamodaranSection.test.tsx`, `MarksSection.test.tsx`, `PabraiSection.test.tsx`, `CanadianTaxSection.test.tsx` — 6 tests Vitest chacun (30 au total)

**Version** : 10.8.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 391 Vitest verts (+30 Sprint 121) ; tsc 0 erreur ; ESLint 0 ; ruff clean

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant (+30), et la suite backend complète (1 423 verts, ruff `All checks passed`).

---

### Sprint 120 — Refonte UI Lynch + Greenblatt + Munger + Klarman ✅

**Objectif :** Poursuivre le pattern des Sprints 118/119 sur le dernier lot de skills encore affichés en JSON brut générique (`SkillSection`) — créer des composants React structurés typés depuis les schemas Pydantic backend pour les quatre frameworks identifiés comme prioritaires : Lynch (catégorie + PEG), Greenblatt (rang ROC + earnings yield), Munger (biais cognitifs détectés), Klarman (marge de sécurité + downside).

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `LynchCategoriesOutput`, `GreenblattOutput`, `BiaisCognitif`, `MungerOutput`, `KlarmanOutput` ; `AnalyzeResponse.lynch`, `.greenblatt`, `.munger` et `.klarman` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/LynchCategoriesSection.tsx` — en-tête avec badge catégorie (libellé FR des 6 archétypes : croissance lente/pilier/croissance rapide/cyclique/redressement/jeu d'actifs) + verdict badge (EXCELLENT/BON/MOYEN/EVITER) ; ratio PEG mis en évidence et coloré (< 1 bull, 1-2 neutral, > 2 bear, N/A si null) ; badge tenbagger potentiel ; score de qualité de croissance /5 ; recommandations
- `frontend/src/components/GreenblattSection.tsx` — en-tête avec verdict badge (TOP_DECILE/BON/MOYEN/EVITER) ; ROC et rendement des bénéfices affichés en % avec couleur seuillée ; situations spéciales en badges ; recommandations
- `frontend/src/components/MungerSection.tsx` — en-tête avec verdict comportemental badge (CONFIANCE_JUSTIFIEE/BIAIS_DETECTE/ALERTE_ROUGE) + badge lollapalooza si risque ; grille des biais cognitifs détectés (nom + badge d'impact MINEUR/MODERE/MAJEUR + description) ou message si aucun ; analyse par inversion ; recommandations
- `frontend/src/components/KlarmanSection.tsx` — en-tête avec badge type de situation qualifié (libellé FR : net-net/actifs cachés/en détresse/situation spéciale/valeur classique) + verdict badge (OPPORTUNITE_FORTE/OPPORTUNITE_MODEREE/ATTENDRE/PASSER) ; décote vs valeur intrinsèque en % (colorée selon le signe) ; barres scores marge de sécurité + préservation du capital /10 ; recommandations
- `frontend/src/components/AnalysisResult.tsx` — branchement sur `LynchCategoriesSection`, `GreenblattSection`, `MungerSection` et `KlarmanSection` (plus `SkillSection` générique pour ces quatre skills)
- `frontend/src/__tests__/LynchCategoriesSection.test.tsx` — 6 tests Vitest (catégorie + verdict + toggle fermé, PEG ouvert, PEG null → N/A, badge tenbagger présent, badge tenbagger masqué, score + recommandations)
- `frontend/src/__tests__/GreenblattSection.test.tsx` — 6 tests Vitest (verdict + toggle, ROC %, earnings yield %, situations spéciales, situations vides masquées, recommandations)
- `frontend/src/__tests__/MungerSection.test.tsx` — 6 tests Vitest (verdict + toggle, badge lollapalooza présent, badge lollapalooza masqué, biais détectés, message si aucun biais, inversion + recommandations)
- `frontend/src/__tests__/KlarmanSection.test.tsx` — 6 tests Vitest (situation + verdict + toggle, décote %, décote null masquée, deux scores /10, recommandations, libellé situation NET_NET)

**Version** : 10.7.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 361 Vitest verts (+24 Sprint 120) ; tsc 0 erreur ; ESLint 0 ; ruff clean

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant (+24), et la suite backend complète (1 423 verts, ruff `All checks passed`).

---

### Sprint 119 — Refonte UI Dorsey Moat + Buffett Quality + Valorisation ✅

**Objectif :** Appliquer le pattern Sprint 118 aux trois skills fréquemment utilisés dans `value_graham` et `compounder_buffett` qui restaient affichés en JSON brut — créer des composants React structurés typés depuis les schemas Pydantic backend.

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `MoatSource`, `DorseyMoatOutput`, `BuffettFiltre`, `BuffettQualityOutput`, `ValuationMethod`, `SensitivityMatrix`, `StockValuationOutput` ; `AnalyzeResponse.dorsey`, `.buffett` et `.valuation` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/DorseyMoatSection.tsx` — en-tête avec badge type de moat (WIDE/NARROW/NONE) + barre de confiance ; durabilité ROIC ; grille des 5 sources d'avantage concurrentiel (intangibles, coûts de transfert, effets de réseau, avantages de coûts, échelle efficiente) avec présence ✓/✗, badge d'intensité (FORTE/MODÉRÉE/FAIBLE/ABSENTE) et justification ; red flags ; recommandations
- `frontend/src/components/BuffettQualitySection.tsx` — en-tête avec verdict badge (COMPOUNDER/QUALITE_CORRECTE/REJETER) + quality score /4 + barre de confiance ; owner earnings par action mis en évidence ; 4 filtres séquentiels ✓/✗ avec score et justification ; red flags ; recommandations
- `frontend/src/components/ValuationSection.tsx` — en-tête avec verdict badge (SOUS_EVALUE/JUSTE_VALEUR/SUREVALUE) + marge de sécurité composite ± % ; fourchette basse/centrale/haute (3 colonnes, centrale mise en évidence) ; 3 méthodes de triangulation (DCF/comparables/sectoriel) avec valeur + hypothèses ; matrice de sensibilité WACC × croissance terminale ; recommandations
- `frontend/src/components/AnalysisResult.tsx` — branchement sur `DorseyMoatSection`, `BuffettQualitySection` et `ValuationSection` (plus `SkillSection` générique pour ces trois skills)
- `frontend/src/__tests__/DorseyMoatSection.test.tsx` — 6 tests Vitest (toggle, 5 sources, durabilité ROIC, drapeaux rouges, recommandations, masquage drapeaux vides)
- `frontend/src/__tests__/BuffettQualitySection.test.tsx` — 6 tests Vitest (toggle + score, 4 filtres, owner earnings, owner earnings null → N/A, drapeaux + recommandations, verdict REJETER)
- `frontend/src/__tests__/ValuationSection.test.tsx` — 6 tests Vitest (toggle + marge, fourchette, 3 méthodes, matrice de sensibilité, recommandations, marge négative SUREVALUE)

**Version** : 10.6.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 337 Vitest verts (+18 Sprint 119) ; tsc 0 erreur ; ESLint 0 ; ruff 0

---

### Sprint 118 — Refonte UI Earnings Quality + Thèse d'investissement ✅

**Objectif :** Remplacer l'affichage JSON brut des deux skills les plus riches (Earnings Quality et Investment Thesis Builder) par des composants React structurés et visuellement exploitables.

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `MScoreDetail`, `ZScoreDetail`, `FScoreCriterion`, `FScoreDetail`, `CScoreSignal`, `CScoreDetail`, `SloanDetail`, `EarningsQualityOutput`, `ThesisScenario`, `ThesisBuilderOutput` ; `AnalyzeResponse.earnings_quality` et `.thesis` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/EarningsQualitySection.tsx` — composant dédié : en-tête avec verdict badge + barre de confiance (% des 5 cadres calculables) ; grille 2 colonnes des 5 frameworks : F-Score Piotroski (9 critères ✓/✗ avec détail), C-Score Montier (6 signaux ⚠/✓ avec détail), M-Score Beneish (8 ratios + seuil -1.78), Z-Score Altman (variante + seuil 2.99/1.81), Sloan accruals (ratio % + seuil ±5%) ; red flags en badges danger ; recommandations prochaine étape ; note contextuelle institutions financières
- `frontend/src/components/ThesisSection.tsx` — composant dédié : en-tête avec verdict_final badge + position size % ; 3 cartes scénarios côte à côte (bull/base/bear) avec barres de probabilité colorées, rendement cible ±%, hypothèses clés ; kill criteria en liste ✗ ; devil's advocate en box mise en évidence ; synthèse narrative découpée en paragraphes
- `frontend/src/components/AnalysisResult.tsx` — branchement sur `EarningsQualitySection` et `ThesisSection` (plus `SkillSection` générique pour ces deux skills)
- `frontend/src/__tests__/EarningsQualitySection.test.tsx` — 6 tests Vitest (toggle fermé/ouvert, F-Score, C-Score, M-Score, Z-Score, drapeaux rouges, recommandations, M-Score null → N/A)
- `frontend/src/__tests__/ThesisSection.test.tsx` — 6 tests Vitest (toggle fermé/ouvert, 3 scénarios, rendements formatés, kill criteria, devil's advocate ciblé avec `within`, narrative paragraphes)

**Version** : 10.5.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 319 Vitest verts (+12 Sprint 118) ; tsc 0 erreur ; ESLint 0 ; ruff non modifié

---

### Sprint 117 — Repo public-ready (gouvernance + README + CHANGELOG) ✅

**Objectif :** Rendre le dépôt GitHub public de façon sécuritaire et professionnelle — audit complet, fichiers de gouvernance open source, durcissement CI/CD.

**Livrables :**
- `README.md` — mis à jour vers v10.3.0 : version badge, tests counts (1 423 CI / 307 Vitest), SearchPage `/recherche`, palette ⌘K dans les fonctionnalités, Node 22, `GET /semantic-search` et `GET /metrics/skill-analyses` dans les endpoints
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1 bilingue (FR/EN), contact ivess49@gmail.com
- `CHANGELOG.md` — historique structuré Keep a Changelog depuis v1.0.0 (Phase 0) jusqu'à v10.3.0 (Sprint 116), groupé par version mineure avec sprint de référence
- `.github/workflows/ci.yml` — `permissions: contents: read` au niveau workflow + sur chaque job (principe de moindre privilège)
- `.gitignore` — ajout des patterns manquants : `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*.cer` (certificats), `*~$*`, `*.tmp` (artefacts OneDrive), `backend_data/`, `data_export/` (dumps données)
- `.github/CODEOWNERS` — `* @yvlar` (code review obligatoire par le mainteneur sur toute PR)

**Version** : 10.4.0
**Tests** : 1 423 CI verts (inchangé — sprint documentation/infrastructure) ; 307 Vitest verts (inchangé)

---

### Sprint 116 — Palette de commandes ⌘K ✅

**Objectif :** Ajouter une command palette (`cmdk`) déclenchée par Ctrl+K / ⌘K permettant de naviguer entre les pages, d'analyser un ticker en un raccourci, d'accéder aux analyses récentes, et de consulter la base de connaissances RAG directement depuis le clavier.

**Livrables :**
- `frontend/src/components/CommandPalette.tsx` — composant `CommandPalette` : rendu via `createPortal` dans `document.body` ; groupes **Actions rapides** (Analyser / Comparer, visibles dès saisie), **Analyses récentes** (depuis `loadRecentAnalyses()`, affichées à l'ouverture vide), **Pages** (10 routes filtrées par query), **Base de connaissances** (résultats RAG `fetchSemanticSearch` debounce 400 ms, activé si ≥ 3 caractères) ; fermeture sur Escape / clic backdrop / sélection d'un item ; légende raccourcis (↵ ↑↓ ESC) en pied de palette
- `frontend/src/App.tsx` — import `CommandPalette` + state `paletteOpen` dans `AppShell` ; `useEffect` global `keydown` sur `Ctrl+K` / `⌘K` (`e.preventDefault()`) ; bouton déclencheur dans l'en-tête (`data-testid="command-palette-trigger"`) avec hint clavier visible sur ≥ md
- `frontend/src/components/AnalyzeForm.tsx` — prop optionnelle `initialTicker?: string` ; état `ticker` initialisé avec `initialTicker ?? ''`
- `frontend/src/pages/AnalyzePage.tsx` — `useSearchParams` pour lire `?ticker=` (pré-rempli depuis la palette) ; `useEffect` pour nettoyer l'URL après lecture (`setSearchParams({}, { replace: true })`) ; `key={prefillTicker}` sur `<AnalyzeForm>` pour forcer le re-mont lors d'un nouveau ticker
- `frontend/src/setupTests.ts` — polyfill `ResizeObserver` pour `cmdk` en jsdom
- `frontend/src/__tests__/CommandPalette.test.tsx` — 8 tests Vitest (mock `cmdk` + `useNavigate` + `loadRecentAnalyses` + `fetchSemanticSearch`) : palette fermée/ouverte, pages navigation affichées, fermeture backdrop, analyses récentes, Analyser → `/?ticker=`, filtre pages par saisie, clic nav item
- `frontend/src/__tests__/AnalyzePage.test.tsx` + `CacheIndicator.test.tsx` — ajout `MemoryRouter` dans le wrapper (requis par `useSearchParams`)
- `frontend/package.json` — dépendance `cmdk@1.1.1` ajoutée

**Version** : 10.3.0
**Tests** : 1423 CI verts (inchangé — sprint frontend pur) ; 307 Vitest verts (+8 Sprint 116) ; tsc 0 erreur ; ESLint 0 ; ruff non modifié

---

### Sprint 115 — Layout pleine largeur + grille Dashboard 12 colonnes ✅

**Objectif :** Exploiter les grands écrans façon plateforme financière en remplaçant le conteneur étroit `max-w-5xl` (frein n°1 à la densité d'information identifié à l'audit UX) par un shell fluide large, et en transformant le Dashboard d'une pile verticale de sections en une grille responsive 12 colonnes.

**Livrables :**
- `frontend/src/index.css` — nouveau token de thème `--container-shell: 96rem` dans `@theme inline` (génère l'utilitaire `max-w-shell`) : point de réglage unique de la largeur du shell applicatif (Tailwind 4 a retiré `max-w-screen-*` ; un token `--container-*` est l'équivalent idiomatique et configurable)
- `frontend/src/App.tsx` — `<main>` passe de `max-w-5xl` à `max-w-shell mx-auto w-full` (full-width shell, `data-testid="app-main"`) ; en-tête sticky restructuré : la barre `bg-card border-b` reste pleine largeur (full-bleed) mais son contenu interne (logo + nav + déconnexion) est enveloppé dans un conteneur `max-w-shell mx-auto w-full` pour aligner son bord gauche sur celui du contenu principal
- `frontend/src/pages/DashboardPage.tsx` — la pile verticale `space-y-6` des sections devient une grille `grid grid-cols-1 lg:grid-cols-12 gap-6 items-start` (`data-testid="dashboard-grid"`) : `MetricsDashboard` et `DetailedMetricsSection` en `lg:col-span-12` (conservent leurs grilles internes), `CompositeChartSection` / `ComparisonSection` / `EvalDriftSection` / `QualitySection` en `lg:col-span-6` (deux par rangée sur grand écran) ; `items-start` évite l'étirement des cartes voisines à hauteur égale
- `frontend/src/__tests__/App.test.tsx` — 2 tests Vitest (le `<main>` porte `max-w-shell` + `mx-auto` et plus `max-w-5xl` ; titre de l'application rendu ; `../api/auth` mocké)
- `frontend/src/__tests__/DashboardPage.test.tsx` — +1 test Vitest (la grille `dashboard-grid` porte `lg:grid-cols-12`)

**Version** : 10.2.0
**Tests** : 1423 CI verts (inchangé — sprint frontend pur) ; 299 Vitest verts (+3 Sprint 115) ; tsc 0 erreur ; ESLint 0 ; ruff clean

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant, et la suite backend complète (1423 verts, ruff `All checks passed`).

---

### Sprint 114 — Quick wins UX/UI (tokens sémantiques, skeletons, accessibilité, progression) ✅

**Objectif :** Lot de quick wins issus d'un audit UX/UI senior — combler quatre lacunes transverses sans changer la structure des pages : (A1) tokeniser les couleurs financières positif/négatif/neutre et supprimer toute couleur en dur (utilities Tailwind + hex recharts) ; (A2) corriger la barre de progression du streaming qui affichait un pourcentage trompeur ; (A3) uniformiser les états de chargement (squelettes partout, fin des « Chargement… » texte) ; (A4) accessibilité de base (mouvement réduit + tri de tableau au clavier).

**Livrables :**
- **A1 — Tokens sémantiques** : `frontend/src/index.css` — variables `--bull` / `--bear` / `--neutral` (`:root`) + mappage `--color-bull/bear/neutral` dans `@theme inline` (génère `text-bull`, `bg-bull/15`, `border-bear/40`, etc.). Nouveau module `frontend/src/lib/colors.ts` — `CHART` (bull/bear/neutral + grid/axis/tooltip/cursor) et `SERIES` (palette catégorielle) : source unique des couleurs recharts (les attributs SVG ne résolvent pas `var()`). Remplacement de **~80 hex** et **~43 utilities** `text-green-400`/`#4ade80`/… par les tokens dans badge, ScreenerTable, HistoryTable, WatchlistTable, AnalysisResult, ConflictsList, StreamingProgress, MetricsDashboard, AnalyzeForm, DashboardPage, ComparePage, AdminPage, RegisterPage et les 10 composants de graphiques recharts
- **A2 — Progression fidèle** : `app/orchestrator/core.py` — méthode `Orchestrator._planned_skill_ids()` (liste ordonnée des skills qui s'exécuteront réellement, mêmes conditions que l'exécution) + nouvel event SSE `plan` (`{"skills": [...]}`) émis au début de `stream_company_analysis`. Frontend : type `SSEPlan` + branche `plan` dans `AnalyzePage`, `StreamingProgress` utilise désormais la liste planifiée comme dénominateur (`done/total` correct) et affiche les skills **en attente** (pastille creuse) en plus de terminés (✓) et actif (ping)
- **A3 — Squelettes partout** : remplacement des 11 placeholders texte « Chargement… » par `Skeleton`/`SkeletonTable` (testids préservés) dans `CompositeScoreChart`, `EsgHistoryChart`, `TickerComparisonChart`, `SkillCostPieChart`, `TopTickersChart`, `CacheByWorkflowChart`, `DailyCostTrendChart`, `AlertsTimelineChart`, `CompositeScoreHistory`, `SkillAnalysesDrilldown`
- **A4 — Accessibilité** : `index.css` — bloc `@media (prefers-reduced-motion: reduce)` neutralisant animations/transitions (WCAG 2.3.3) ; `ScreenerTable` — en-têtes de tri refondus en `<button>` focusables + `aria-sort` sur le `<th>`, icônes de tri `aria-hidden`
- **Tests** : `tests/orchestrator/test_planned_skills.py` (5 tests — workflow/flags/dépendance munger↔thesis/esg hors workflow/workflow inconnu) ; `frontend/src/__tests__/StreamingProgress.test.tsx` (2 tests — dénominateur planifié + repli) ; 3 tests chart adaptés (assertion texte → testid skeleton) + `ComparePage.test` (highlight `bg-primary`)

**Version** : 10.1.0
**Tests** : 1423 CI verts (+5 backend) ; 296 Vitest verts (+2) ; tsc 0 erreur ; ESLint 0 ; ruff clean

---

### Sprint 113 — Global Micro-UX Refresh ✅

**Objectif :** Doter les 11 pages de l'interface React d'un système cohérent d'animations, de micro-interactions et de squelettes de chargement, sans modifier la palette ni la structure des pages. Chaque action répond désormais avec un retour physique (press, pulsation) et chaque attente réseau est représentée par un squelette shimmer correspondant au layout réel.

**Livrables :**
- `frontend/src/index.css` — 5 `@keyframes` CSS (`shimmer`, `fade-in-up`, `scale-in`, `slide-in-right`, `count-pulse`) + 5 entrées `--animate-*` dans `@theme inline` (disponibles comme classes Tailwind) + classe `@layer components .skeleton-shimmer` (gradient 200 % animé)
- `frontend/src/components/ui/skeleton.tsx` — 6 composants : `Skeleton` (rect shimmer aria-hidden), `SkeletonRow` (ligne de tableau N colonnes), `SkeletonCard` (3 rects), `SkeletonCardGrid` (grille de N cartes), `SkeletonChart` (bloc graphique), `SkeletonTable` (tableau complet N×N)
- `frontend/src/components/ui/animated-number.tsx` — `AnimatedNumber` : count-up `requestAnimationFrame` cubic-out vers la valeur cible + pulsation CSS à l'arrivée
- `frontend/src/components/PageTransition.tsx` — `PageTransition` (fade-in-up au montage) + `StaggerItem` (délai proportionnel à l'index, plafonné 400 ms)
- `frontend/src/components/ui/button.tsx` — `active:scale-95` press feedback
- `frontend/src/components/ui/badge.tsx` — `animate-scale-in` à chaque montage
- `frontend/src/components/ui/card.tsx` — hover : `border-primary/30` + glow box-shadow subtil (`transition-[border-color,box-shadow]`)
- `frontend/src/components/StreamingProgress.tsx` — barre de progression globale (done/total), `animate-ping` sur l'indicateur actif, stagger 40 ms par skill
- `frontend/src/App.tsx` — indicateur de navigation animé (`animate-scale-in` sur l'underline actif) + hover `border-primary/30`
- `frontend/src/components/MetricsDashboard.tsx` — `AnimatedNumber` sur les 5 métriques WebSocket, `SkeletonCardGrid` pendant le chargement initial
- **11 pages** — `PageTransition` wrapper + `SkeletonTable`/`SkeletonCard` sur les états de chargement : `AnalyzePage`, `DashboardPage`, `HistoryPage`, `ScreenerPage`, `WatchlistPage`, `EsgPage`, `AlertsPage`, `SearchPage` (squelettes + `StaggerItem` sur résultats), `ComparePage`
- `frontend/src/__tests__/Skeleton.test.tsx` — 9 tests (dimensions, colonnes, aria-hidden, classe shimmer)
- `frontend/src/__tests__/AnimatedNumber.test.tsx` — 5 tests (valeur initiale, className, formatter, nodeName, tabular-nums)
- `frontend/src/__tests__/PageTransition.test.tsx` — 8 tests (rendu, animate-fade-in-up, className supplémentaire, StaggerItem délai croissant, plafond 400 ms)

**Version** : 10.0.0
**Tests** : 1418 CI verts (inchangé — sprint frontend pur) ; 294 Vitest verts (+22 tests Sprint 113)

---

### Sprint 112 — Coût par skill : drill-down et tendance ✅

**Objectif :** Prolonger le Dashboard v2 (Sprint 107) avec un drill-down sur le camembert « coût par skill » (clic → liste des analyses ayant utilisé ce skill sur la période) et une mini-tendance du coût total par jour. Les deux fonctions aident à piloter le budget API Claude : voir *où* part le coût (quels tickers/analyses par framework) et *comment il évolue* dans le temps.

**Livrables :**
- `app/orchestrator/core.py` — `MetricsResponse.daily_cost: dict[str, float] = {}` (coût USD total par jour, clé `YYYY-MM-DD`, défaut `{}` → rétrocompatible) ; `get_metrics()` ajoute une 4e requête `daily_rows` (`GROUP BY to_char(date_trunc('day', created_at), 'YYYY-MM-DD')`) ; nouveaux schemas `SkillAnalysisEntry` (analysis_id / ticker / workflow_name / cost_usd / created_at) + `SkillAnalysesResponse` (skill / period_days / entries) ; méthode `get_skill_analyses(skill, days=30, limit=100)` filtrant `skills_used @> $2::jsonb` (`json.dumps([skill])`), tri `created_at DESC`
- `app/api/main.py` — endpoint `GET /metrics/skill-analyses?skill=&days=30` (`skill` requis via `Query(..., min_length=1)` → 422 si absent ; `days` borné 1-365 → 422) ; import `SkillAnalysesResponse`
- `frontend/src/types/index.ts` — `daily_cost: Record<string, number>` ajouté à `MetricsResponse` ; interfaces `SkillAnalysisEntry` + `SkillAnalysesResponse` (snake_case, miroir JSON FastAPI)
- `frontend/src/api/metrics.ts` — `fetchSkillAnalyses(skill, days=30)` via `apiClient.request`
- `frontend/src/components/DailyCostTrendChart.tsx` — `LineChart` recharts (coût total par jour, série triée par date asc, axe Y formaté `$`), états loading/error/empty
- `frontend/src/components/SkillAnalysesDrilldown.tsx` — React Query `['skill-analyses', skill, days]` → tableau (Date / Ticker / Workflow / Coût), bouton « Fermer », états loading/error/empty
- `frontend/src/components/SkillCostPieChart.tsx` — prop optionnelle `onSkillClick?: (skill: string) => void` ; `onClick` sur le `Pie` lit le skill via `slice.payload.skill` (type `PieSectorDataItem`), curseur pointeur quand cliquable
- `frontend/src/pages/DashboardPage.tsx` — `DetailedMetricsSection` : state `selectedSkill`, `onSkillClick={setSelectedSkill}` sur le camembert, `DailyCostTrendChart` ajouté en pleine largeur (`lg:col-span-2`) dans la grille, `SkillAnalysesDrilldown` rendu sous la grille quand un skill est sélectionné (bouton Fermer → `setSelectedSkill(null)`)
- `tests/orchestrator/test_metrics_v2.py` — +3 tests CI : `daily_cost` construit, `get_skill_analyses` mappe les entrées (+ vérifie le filtre jsonb sérialisé), `get_skill_analyses` vide ; helper `_build_orchestrator` étendu d'un 4e fetch `daily_rows`
- `tests/orchestrator/test_integration_sync.py` — +2 tests CI : `/metrics/skill-analyses` retourne les analyses, 422 si `skill` absent
- `frontend/src/__tests__/DailyCostTrendChart.test.tsx` — 4 tests Vitest (rendu avec données, vide, chargement, erreur ; recharts mocké)
- `frontend/src/__tests__/SkillAnalysesDrilldown.test.tsx` — 5 tests Vitest (appel `fetchSkillAnalyses` avec skill+days, tableau, vide, erreur, bouton Fermer ; QueryClientProvider)
- `frontend/src/__tests__/SkillCostPieChart.test.tsx` — +1 test Vitest (clic sur tranche → `onSkillClick` avec le skill ; mock `Pie` expose `onClick({payload})`)
- `frontend/src/__tests__/DashboardPage.test.tsx` — mock `../api/metrics` complété (`daily_cost: {}` + `fetchSkillAnalyses`)

**Version** : 9.9.0
**Tests** : 1418 CI verts (hors e2e et evals) — +5 tests Sprint 112 ; 272 Vitest verts — +10 tests Sprint 112

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant (recharts mocké) + helpers, et tests d'intégration backend (ruff `All checks passed`).

### Sprint 109 — Screener v2 : filtres avancés et tri persistant ✅

**Objectif :** Améliorer la page Screener avec un tri persistant entre sessions (localStorage), des filtres inline par label composite, un indicateur de fraîcheur des données (date de la dernière analyse par ticker), et un export CSV des résultats filtrés tel qu'affichés. Le screener est l'outil le plus utilisé après l'analyse individuelle ; ces améliorations de navigation ont un impact direct sur l'efficacité du flux d'investissement.

**Livrables :**
- `app/api/endpoints/screen.py` — `ScreenEntry.analyzed_at: str | None = None` (date ISO 8601 de l'analyse sous-jacente, défaut None → rétrocompatible ; None pour les tickers en échec)
- `app/services/screener.py` — `analyzed_at` peuplé depuis `cached.created_at` (hit de cache) et `response.created_at` (analyse fraîche) ; chemin d'erreur laisse None
- `frontend/src/types/index.ts` — champ `analyzed_at: string | null` ajouté à l'interface `ScreenEntry`
- `frontend/src/lib/screenerView.ts` — helpers purs testables : `loadSortState`/`saveSortState` + `loadLabelFilter`/`saveLabelFilter` (persistance localStorage, clés `copilote_screener_sort` et `copilote_screener_label_filter`), `availableLabels()` (labels distincts dans l'ordre d'apparition), `formatFreshness()` (date relative FR + flag `stale` au-delà de 24h, seuil aligné sur le cache composite), `buildScreenerCsv()` (CSV échappé, 9 colonnes)
- `frontend/src/components/ScreenerTable.tsx` — tri persistant sur 5 colonnes (ticker/score/composite/fraîcheur/coût), barre de filtres par label composite (chips dérivées des données + bouton « Réinitialiser »), colonne « Fraîcheur » (`FreshnessCell` : vert si frais, jaune si périmé), bouton `data-testid="export-filtered-csv"` (export client-side des résultats filtrés/triés avec BOM UTF-8)
- `tests/api/test_screener.py` — +3 tests CI : `analyzed_at` reflète `created_at` (analyse fraîche), propagé depuis le cache, None si échec
- `frontend/src/__tests__/screenerView.test.ts` — 14 tests Vitest : `formatFreshness` (null/instant/heures/périmé/date invalide), `availableLabels`, persistance tri + filtre (défaut, round-trip, clé invalide), `buildScreenerCsv` (en-tête + lignes, échappement virgules, cache oui/non + date)
- `frontend/src/__tests__/ScreenerTable.test.tsx` — +7 tests Vitest (colonne Fraîcheur, chips de filtre, filtrage au clic, réinitialisation, persistance + restauration du tri, présence bouton export) ; `localStorage.clear()` en `beforeEach`
- `frontend/src/__tests__/{ScreenerPage,ScreenerPdfExport}.test.tsx` — fixtures `ScreenResult` enrichies de `analyzed_at`

**Version** : 9.8.0
**Tests** : 1413 CI verts (hors e2e et evals) — +3 tests Sprint 109 ; 262 Vitest verts — +21 tests Sprint 109

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant + helpers purs, et tests d'intégration backend (ruff `All checks passed`).

### Sprint 107 — Dashboard v2 : métriques détaillées ✅

**Objectif :** Enrichir `DashboardPage` avec les métriques jusqu'ici manquantes — top tickers analysés, coût par skill, taux de cache par workflow, et évolution du nombre d'alertes dans le temps. Les données proviennent de `GET /metrics` (enrichi côté backend) et `GET /alerts` (Sprint 99), surfacées via 4 graphiques recharts dans une section dédiée.

**Livrables :**
- `app/orchestrator/core.py` — `MetricsResponse` étendu avec `skills_cost: dict[str, float] = {}` (coût USD de chaque analyse réparti également entre ses skills via `cost_usd / NULLIF(jsonb_array_length(skills_used), 0)`) et `cache_by_workflow: dict[str, float] = {}` (taux de cache moyen `GROUP BY workflow_name`) ; `get_metrics()` fusionne le coût dans la requête `skill_rows` existante et ajoute une 3e requête `workflow_rows` ; défauts `{}` → rétrocompatibilité totale des constructions `MetricsResponse` existantes
- `frontend/src/types/index.ts` — interfaces `TickerMetrics` et `MetricsResponse` en snake_case (miroir exact de la réponse JSON FastAPI, comme `AlertEntry`)
- `frontend/src/api/metrics.ts` — `fetchMetrics(days=30)` via `apiClient.request`
- `frontend/src/components/TopTickersChart.tsx` — `BarChart` recharts horizontal (top N par nombre d'analyses), états loading/error/empty
- `frontend/src/components/SkillCostPieChart.tsx` — `PieChart` recharts (coût USD par skill, slices triées DESC, filtre les coûts nuls), états loading/error/empty
- `frontend/src/components/CacheByWorkflowChart.tsx` — `BarChart` recharts horizontal (taux de cache en %, domaine 0-100), états loading/error/empty
- `frontend/src/components/AlertsTimelineChart.tsx` — `BarChart` recharts (alertes regroupées par jour `YYYY-MM-DD`, triées asc), helper `bucketByDay()`, états loading/error/empty
- `frontend/src/pages/DashboardPage.tsx` — nouvelle section `DetailedMetricsSection` : sélecteur de période `data-testid="metrics-period-select"` (7/30/90 j), React Query `['metrics', days]` + `['alerts', 'timeline']`, grille 2 colonnes des 4 graphiques ; insérée entre `MetricsDashboard` et `CompositeChartSection`
- `tests/orchestrator/test_metrics_v2.py` — 3 tests CI : `get_metrics` construit `skills_cost`, construit `cache_by_workflow` (arrondi 4 décimales), dicts vides par défaut sans données
- `tests/orchestrator/test_integration_sync.py` — +1 test CI : `/metrics` sérialise `skills_cost` et `cache_by_workflow` dans la réponse
- `frontend/src/__tests__/{TopTickersChart,SkillCostPieChart,CacheByWorkflowChart,AlertsTimelineChart}.test.tsx` — 18 tests Vitest (recharts mocké) : rendu avec données, états vide/chargement/erreur ; `AlertsTimelineChart` vérifie le regroupement par jour + tri
- `frontend/src/__tests__/DashboardPage.test.tsx` — mocks `../api/metrics` et `../api/alerts` ajoutés (tests existants déterministes)

**Version** : 9.7.0
**Tests** : 1410 CI verts (hors e2e et evals) — +4 tests Sprint 107 ; 241 Vitest verts — +18 tests Sprint 107

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur), Vitest composant (recharts mocké) et tests d'intégration backend.

### Sprint 106 — Recherche sémantique RAG dans le frontend ✅

**Objectif :** Exposer le RAG Qdrant (collection `investment_knowledge`) directement dans le frontend via une nouvelle page `/recherche` : champ de recherche en langage naturel qui retourne les passages de référence (formules, seuils, frameworks) avec leur source et score de similarité. Le corpus RAG (~67 documents) était jusqu'ici alimenté et interrogé uniquement côté backend (par les skills), jamais surfacé à l'utilisateur.

**Livrables :**
- `app/api/endpoints/semantic_search.py` — `GET /semantic-search?q=&k=5` : `SemanticSearchResponse(query, rag_enabled, results: list[Citation])` ; lit `request.app.state.rag_service` (None si `OPENAI_API_KEY` absente) → `rag_enabled=false` + `results=[]` sans erreur ; `q` requis (`min_length=2`, `max_length=500` → 422), `k` borné (`ge=1, le=20`)
- `app/api/main.py` — `app.state.rag_service = rag_service` exposé dans le lifespan (jusque-là injecté uniquement dans les constructeurs de skills) ; import + `include_router(semantic_search_router)`
- `frontend/src/types/index.ts` — interfaces `SemanticSearchResult` (source / extrait / score) et `SemanticSearchResponse` (query / rag_enabled / results)
- `frontend/src/api/search.ts` — `fetchSemanticSearch(query, k=5)` via `apiClient.request`
- `frontend/src/pages/SearchPage.tsx` — formulaire de recherche (Input + Button, soumission via state `query`, React Query `['semantic-search', query]` activé si ≥ 2 caractères) ; résultats en `Card` (source nettoyée + badge score coloré selon seuil 0.8/0.6 + extrait) ; états `search-idle` / `search-spinner` / `search-error` / `search-rag-disabled` / `search-empty` / `search-results`
- `frontend/src/App.tsx` — route `/recherche` (ProtectedRoute) + NavItem "Recherche"
- `frontend/vite.config.ts` — proxy `/semantic-search` → `http://localhost:8000`
- `tests/api/test_semantic_search.py` — 5 tests CI : 200 + résultats mappés (rag_enabled=true), rag désactivé (rag_service None), paramètre `k` propagé, 422 query absente, 422 query trop courte
- `frontend/src/__tests__/SearchPage.test.tsx` — 6 tests Vitest : rendu formulaire + état initial, `fetchSemanticSearch` appelé avec la requête, affichage des passages, état vide, avertissement RAG désactivé, message d'erreur API

**Version** : 9.6.0
**Tests** : 1406 CI verts (hors e2e et evals) — +5 tests Sprint 106 ; 223 Vitest verts — +6 tests Sprint 106

---

### Sprint 101 — Nettoyage `.claude/skills/` (clôture dette technique Sprint 100) ✅

**Objectif :** Résoudre les deux points en suspens signalés en fin de Sprint 100 — le dépôt git imbriqué `.claude/skills/.git` (gitlink cassé sans `.gitmodules`) et le dossier orphelin `.claude/skills/investment/` — afin qu'un `git clone` du dépôt public ne récupère pas un submodule cassé.

**Constat :** Vérification du dépôt distant — les deux points étaient **déjà résolus** par les commits intermédiaires `3ec7548` (« intégrer SKILL.md dans le repo principal — retire gitlink cassé ») et `d81c5dc`. C'étaient des artefacts purement locaux (synchronisation OneDrive de la machine de Yves), jamais présents sur le distant ni dans l'historique versionné.

**Livrables :**
- Vérification : 158 fichiers trackés sous `.claude/skills/` (dont les 16 SKILL.md), `.claude/skills` est un arbre normal (mode `040000`) et non un gitlink (mode `160000`) ; aucun `.git` imbriqué, aucun `.gitmodules`, aucun dossier `investment/` orphelin
- `ROADMAP.md` — note de fin de Sprint 100 mise à jour pour pointer vers cette résolution ; état courant passé à v9.5.1 ; Sprint actif → 102
- `prompt-mise-a-jour-roadmap.md` — réécrit pour le Sprint 102, retrait des avertissements périmés sur le `.git` imbriqué et le dossier orphelin

**Version** : 9.5.1
**Tests** : 1401 CI verts + 217 Vitest verts (inchangé — sprint de vérification et documentation, aucun changement de code applicatif)

---

### Sprint 96 — Estimation rapide total_count via pg_class ✅

**Objectif :** Ajouter un paramètre optionnel `?fast_count=true` à `GET /history-paged` qui remplace le `SELECT COUNT(*)` exact par une estimation rapide via `pg_class.reltuples`. Sans filtre, évite un goulot d'étranglement quand `analysis_history` dépasse 100k lignes.

**Livrables :**
- `app/orchestrator/core.py` — `Orchestrator.get_history_paged()` accepte `fast_count: bool = False` ; quand True et sans filtre (ticker/q/from_dt/to_dt tous None), `_fetch_count()` appelle `SELECT reltuples::bigint FROM pg_class WHERE relname = 'analysis_history'` au lieu de `SELECT COUNT(*)` ; retombe sur COUNT(*) exact dès qu'un filtre est présent
- `app/api/main.py` — endpoint `GET /history-paged` accepte `fast_count: bool = False` comme query parameter, passé à `orchestrator.get_history_paged()`
- `tests/test_history_paged_fast_count.py` — 3 tests CI : `fast_count=False` appelle COUNT(*), `fast_count=True` sans filtre appelle pg_class (pas COUNT*), `fast_count=True` avec ticker retombe sur COUNT(*)

**Version** : 8.9.0
**Tests** : 1385 tests au total (1383 CI verts hors e2e et evals) — +3 tests Sprint 96 ; 200 Vitest verts (inchangé)

---

### Sprint 95 — Suppression des analyses obsolètes (DELETE /history) ✅

**Objectif :** Permettre à Yves de supprimer des analyses individuelles de l'historique directement depuis l'interface React, via un bouton "Supprimer" dans `HistoryPage` avec confirmation modale et un endpoint admin `DELETE /history/{analysis_id}`.

**Livrables :**
- `app/orchestrator/core.py` — méthode `Orchestrator.delete_analysis(analysis_id: str) -> bool` : supprime l'annotation orpheline (pas de FK cascade sur `annotations`) puis `DELETE FROM analysis_history WHERE id = $1::uuid` ; retourne True si 1 ligne supprimée, False sinon ; gère `asyncpg.exceptions.InvalidTextRepresentationError` pour UUID invalide
- `app/api/main.py` — endpoint `DELETE /history/{analysis_id}` (admin only, `Depends(_require_admin)`) ; `analysis_id: UUID` → FastAPI valide le format (422 auto) ; 204 si supprimée, 404 si introuvable ; imports ajoutés : `UUID`, `Depends`, `Response`, `_require_admin`
- `frontend/src/api/analyze.ts` — `deleteAnalysis(analysis_id: string): Promise<void>` via `apiClient.requestEmpty` avec méthode DELETE
- `frontend/src/components/HistoryTable.tsx` — prop `onDeleteAnalysis?: (analysisId: string) => void` + colonne "Supprimer" + bouton icône 🗑 `data-testid="delete-analysis-{analysis_id}"`
- `frontend/src/pages/HistoryPage.tsx` — state `deletedIds: Set<string>` + filtre entrées supprimées + `handleDeleteAnalysis` (window.confirm → deleteAnalysis → setDeletedIds + notification 3s) + passage `onDeleteAnalysis` à HistoryTable
- `tests/test_delete_history.py` — 3 tests CI : True si DELETE 1, False si DELETE 0, endpoint 204 confirmé
- `frontend/src/__tests__/DeleteAnalysis.test.tsx` — 3 tests Vitest : bouton présent, deleteAnalysis appelé avec bon id, entrée retirée du tableau

**Version** : 8.8.0
**Tests** : 1382 CI verts — +3 tests Sprint 95 ; 200 Vitest verts — +3 tests Sprint 95

---

### Sprint 94 — Alerte ESG sur dégradation historique ✅

**Objectif :** Détecter automatiquement une dégradation du score ESG d'un ticker de la watchlist et déclencher une alerte Slack/webhook quand la baisse dépasse le seuil `esg_alert_threshold`. Ferme la boucle "détection → alerte" déjà en place pour le composite_score (Sprint 57).

**Livrables :**
- `app/services/esg_history_service.py` — méthode `get_latest_previous(ticker: str) -> float | None` : SELECT OFFSET 1 ORDER BY recorded_at DESC — retourne le 2e score le plus récent, None si < 2 entrées
- `app/services/watchlist_service.py` — méthode statique `check_esg_degradation(entry, previous_score) -> bool` : True si `(previous_score - last_esg_score) > esg_alert_threshold`
- `app/workers/tasks.py` — `_execute_esg_degradation_check()` + tâche Celery `run_esg_degradation_check()` : itère la watchlist, appelle `get_latest_previous()`, déclenche `webhook_service.send_esg_alert()` + `slack_service.send_esg_alert()` si dégradation détectée ; retourne `{"nb_alertes": N}`
- `app/workers/celery_app.py` — beat schedule `run-esg-degradation-check` : chaque dimanche à 12h00 UTC (après le screener 11h00)
- `app/api/endpoints/watchlist.py` — endpoint `POST /watchlist/check-esg-degradation` (admin only, `Depends(_require_admin)`) ; retourne `{"triggered": N}` alertes déclenchées
- `tests/test_esg_degradation.py` — 5 tests CI : `get_latest_previous` None < 2 entrées, `get_latest_previous` 2e score correct, `check_esg_degradation` False si baisse < seuil, True si baisse > seuil, endpoint 200 `{"triggered": 1}`
- `tests/test_celery_composite_alert.py` — mise à jour du test count beat schedule (6 → 7 tâches)

**Version** : 8.7.0
**Tests** : 1379 CI verts — +5 tests Sprint 94 (+1 mis à jour) ; 197 Vitest verts (inchangé)

---

### Sprint 93 — Streaming SSE dans ComparePage (opt-in) ✅

**Objectif :** Ajouter un toggle "Streaming en direct" dans `ComparePage` qui utilise `POST /analyze-stream` (SSE) au lieu de `POST /analyze`, affichant le skill en cours skill par skill pendant l'analyse. Mode non-streaming conservé comme défaut (opt-in sans changement de comportement par défaut).

**Livrables :**
- `frontend/src/pages/ComparePage.tsx` — import `streamAnalyze` ; états `streamingEnabled` (bool, défaut false) + `tickerStreamSkill` (Record ticker→skill_id) ; toggle checkbox `data-testid="streaming-toggle"` dans la barre de saisie ; `handleAnalyze()` bifurque selon `streamingEnabled` — branche streaming itère `for await` sur `streamAnalyze()` avec `Promise.race 60s`, met à jour `tickerStreamSkill` sur `skill_start`/`skill_result`, lève une erreur sur `error` ; branche non-streaming identique à Sprint 87 ; affichage du skill courant avec `data-testid="stream-skill-{ticker}"` sous le bouton Analyser quand streaming actif
- `frontend/src/__tests__/CompareStreaming.test.tsx` — 5 tests : toggle présent/désactivé, toggle actif → `streamAnalyze` appelé (pas `postAnalyze`), toggle inactif → `postAnalyze` appelé (rétrocompat), `skill_start` affiché progressivement, erreur SSE affichée inline
- `frontend/src/__tests__/ComparePage.test.tsx` — mock `../api/analyze` complété avec `streamAnalyze: vi.fn()`

**Version** : 8.6.0
**Tests** : 1374 CI verts (inchangé) ; 197 Vitest verts — +5 tests Sprint 93

---

### Sprint 92 — Annotations dans l'export Excel watchlist ✅

**Objectif :** Inclure la dernière annotation par ticker dans `GET /watchlist/export.xlsx` en enrichissant `get_all_with_composite()` avec un second LEFT JOIN LATERAL sur la table `annotations` (via `analysis_history`). Ferme l'incohérence entre l'export annotations (Sprint 85) et l'export watchlist (Sprint 83).

**Livrables :**
- `app/services/watchlist_service.py` — second LEFT JOIN LATERAL dans `get_all_with_composite()` : joint `annotations` via `analysis_history` pour récupérer `note` de la dernière annotation par ticker (ORDER BY created_at DESC LIMIT 1) ; alias SQL `derniere_annotation` (COALESCE → '' si absent)
- `app/api/endpoints/watchlist.py` — colonne "Annotation" ajoutée en fin de `_XLSX_HEADERS` (position 9) + `_XLSX_COL_WIDTHS` (largeur 40) + `_generate_watchlist_xlsx()` écrit `row.get("derniere_annotation", "")`
- `tests/test_watchlist_xlsx_annotation.py` — 3 tests CI (SQL contient `derniere_annotation`, en-tête XLSX contient "Annotation", valeur présente vs cellule vide)

**Version** : 8.5.0
**Tests** : 1374 tests au total (1372 CI verts hors e2e et evals) — +3 tests Sprint 92 ; 192 Vitest verts (inchangé)

---

### Sprint 91 — Seuil de prix configurable par ticker ✅

**Objectif :** Permettre à Yves de modifier le seuil d'alerte de prix (`price_alert_threshold_pct`) par ticker directement depuis l'interface React, via une colonne "Seuil Prix (%)" avec édition inline dans `WatchlistTable` et l'endpoint `PATCH /watchlist/{id}/price-threshold`. Pattern identique au Sprint 84 (seuil ESG).

**Livrables :**
- `app/services/watchlist_service.py` — méthode `update_price_threshold(entry_id, threshold)` (UPDATE SQL sur `price_alert_threshold_pct`)
- `app/api/endpoints/watchlist.py` — schema Pydantic `PriceThresholdUpdate(threshold: float)` + endpoint `PATCH /watchlist/{entry_id}/price-threshold` (422 si ≤ 0 ou > 100, 404 si introuvable, division par 100 avant stockage décimal)
- `frontend/src/api/watchlist.ts` — `patchPriceThreshold(id, threshold)` couche HTTP PATCH
- `frontend/src/components/WatchlistTable.tsx` — nouvelle colonne "Seuil Prix (%)" : mode display (`price_alert_threshold_pct * 100`) + mode edit inline (Input 0-100 + Sauvegarder/Annuler + erreur inline) ; états `priceEditingId`/`priceEditValue`/`priceEditError`/`priceSaving` indépendants du seuil ESG
- `tests/test_watchlist_price_threshold.py` — 3 tests CI (SQL params corrects, 200 + valeur à jour, 404 id inexistant)
- `frontend/src/__tests__/WatchlistPriceThreshold.test.tsx` — 5 tests Vitest (affichage %, ouverture input, sauvegarde API, annuler sans appel, erreur affichée)
- **Bonus** : correction corruption OneDrive `frontend/src/types/index.ts` (garbage lignes 463-487) + `frontend/src/pages/HistoryPage.tsx` (accents perdus sur "Télécharger PDF") + mise à jour mock `getHistoryPaged` dans `PdfDownload.test.tsx`

**Version** : 8.4.0
**Tests** : 1371 CI verts (hors e2e et evals) — +3 tests Sprint 91 ; 192 Vitest verts — +5 tests Sprint 91 (+4 bonus PdfDownload restaurés)

---

### Sprint 97 — Score composite historique dans WatchlistPage ✅

**Objectif :** Ajouter un mini-graphique sparkline dans `WatchlistTable` pour chaque ticker, montrant l'évolution du `composite_score` sur 30 jours. Données déjà disponibles via `GET /composite-history/{ticker}?limit=30` (Sprint 57/60) — rendues visibles directement dans la watchlist sans naviguer vers le Dashboard.

**Livrables :**
- `frontend/src/components/CompositeSparkline.tsx` — composant Sparkline : props `ticker: string`, `height?: number` (défaut 40) ; React Query `['composite-history', ticker]` vers `getCompositeHistory(ticker, 30)` ; `LineChart` recharts 120px × hauteur configurable sans axes/tooltip/légende ; Loading : div `animate-pulse` ; Error/Vide : dash `—`
- `frontend/src/components/WatchlistTable.tsx` — colonne "Tendance" ajoutée après "Score composite" (avant "ESG") avec `<CompositeSparkline ticker={entry.ticker} />`
- `frontend/src/__tests__/CompositeSparkline.test.tsx` — 5 tests Vitest : loading, erreur API, 0 points, données présentes (LineChart), prop height
- `frontend/src/__tests__/Watchlist*.test.tsx` (×4) — mock `CompositeSparkline` ajouté pour conserver la compatibilité sans QueryClientProvider

**Version** : 9.0.0
**Tests** : 1383 CI verts (inchangé) ; 205 Vitest verts — +5 tests Sprint 97

---

### Sprint 98 — Professionnalisation GitHub ✅

**Objectif :** Rendre le dépôt GitHub public professionnel et prêt pour des contributeurs : linting/formatage automatique dans le CI, type-checking, templates GitHub, fichiers de gouvernance (LICENSE, CONTRIBUTING, SECURITY).

**Livrables :**
- `LICENSE` — MIT (2026, Yves Larivière)
- `CONTRIBUTING.md` — setup local Docker+npm, conventions bilingues FR/EN, pyramide 5 niveaux, workflow sprint, commandes essentielles
- `SECURITY.md` — politique de divulgation responsable, contact ivess49@gmail.com
- `.github/ISSUE_TEMPLATE/bug_report.yml` + `feature_request.yml` — templates structurés (version, étapes, comportement attendu/observé, composant)
- `.github/pull_request_template.md` — checklist PR (tests, types stricts, CLAUDE.md, `.env.example`, pas de secret)
- `pyproject.toml` — configuration `ruff` (line-length 100, select E/W/F/I/N, ignores E402/E741/E741/F821) + `mypy` (python_version 3.11, ignore_missing_imports, strict=false)
- `frontend/.eslintrc.cjs` — config ESLint (`eslint:recommended` + `@typescript-eslint/recommended` + `react-hooks/recommended`, `no-explicit-any: error`)
- `frontend/package.json` — scripts `"lint": "eslint src --ext .ts,.tsx"` + `"typecheck": "tsc --noEmit"` ; devDependencies ESLint ajoutées
- `.github/workflows/ci.yml` — 4 jobs : `test-backend` (pytest), `test-frontend` (vitest), `lint` (ruff + eslint), `typecheck` (mypy + tsc)
- `.github/dependabot.yml` — mises à jour automatiques pip + npm (weekly, lundi, cible master)
- **Bonus** : auto-fix 197 erreurs ruff (92 imports non triés + 105 imports inutilisés) ; correction bug `F601` clé `"MODERE"` dupliquée dans `app/services/export.py` ; correction typecheck tests (`esg: null` manquant dans 2 mocks, `global.URL` → `window.URL` dans 2 fichiers de test)

**Version** : 9.1.0
**Tests** : 1383 CI verts (inchangé) ; 205 Vitest verts (inchangé) — sprint infrastructure uniquement

---

### Sprint Login — Authentification complète (cookie JWT + CSRF) — parallèle ✅

**Objectif :** Implémenter un système d'authentification complet avec inscription, connexion par cookies httpOnly, rotation de refresh tokens, CSRF double-submit, rate limiting, réinitialisation de mot de passe par email, et les pages React correspondantes. Sprint développé en parallèle du processus principal.

**Livrables :**
- `app/models/auth.py` — `RegisterRequest` (force mdp : 12+ cars, maj, min, chiffre, spécial), `LoginRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`, `UserPublic`, `AuthResponse`
- `app/services/user_service.py` — `UserService` : `create_user`, `authenticate` (argon2 timing-safe, toujours vérifié), `get_by_id`, `update_last_login`, `update_password` ; `EmailAlreadyExistsError` ; argon2 `time_cost=2, memory_cost=65536, parallelism=2`
- `app/services/auth_token_service.py` — JWT HS256 TTL 15 min + jti blacklist Redis `SETEX` ; refresh tokens UUID hachés SHA-256 en DB, rotation par famille (vol → invalidation totale) ; 6 méthodes async
- `app/services/password_reset_service.py` — tokens `URLSafeTimedSerializer` itsdangerous TTL 1h, salt fixe `password-reset-v1` ; `send_reset_email` via SendGrid ou log dev
- `app/middleware/csrf.py` — `CSRFMiddleware` : double-submit cookie ; exempt pré-auth (`/auth/login`, `/auth/register`, etc.) + Bearer + dev mode (`API_KEY` vide) ; 403 si csrf_cookie ≠ X-CSRF-Token
- `app/middleware/auth.py` — extension `BearerTokenMiddleware` : Path 2 cookie `access_token` → AuthTokenService JWT ; rétrocompatibilité Bearer API key complète
- `app/api/endpoints/auth.py` — router `/auth` : 9 endpoints (register/login/logout/refresh/me/forgot-password/reset-password/mfa-setup-stub/mfa-verify-stub) ; `_set_auth_cookies()` (SameSite=lax, Secure=env) ; `_clear_auth_cookies()`
- `app/api/main.py` — tables `users` + `refresh_tokens` (idempotentes lifespan) ; instanciation UserService/AuthTokenService/PasswordResetService/CSRFMiddleware ; CORS `allow_credentials=True` + `X-CSRF-Token` ; proxy `/auth` ajouté
- `.env.example` — `JWT_SECRET_KEY`, `SENDGRID_FROM_EMAIL`, `FRONTEND_URL`, `SECURE_COOKIES`
- `requirements.txt` — `python-jose[cryptography]>=3.3.0`, `argon2-cffi>=23.1.0`, `itsdangerous>=2.2.0`, `email-validator>=2.1.0`
- `frontend/src/api/auth.ts` — `authRegister/authLogin/authLogout/authMe/authRefresh/authForgotPassword/authResetPassword` ; `getCsrfToken()` via `document.cookie` ; `AuthApiError`
- `frontend/src/api/client.ts` — `credentials: 'include'` + `X-CSRF-Token` sur mutations ; Bearer localStorage toujours rétrocompat
- `frontend/src/contexts/AuthContext.tsx` — `authMe()` au montage → restaure session cookie ; `isLoading` state (true jusqu'à résolution)
- `frontend/src/components/ProtectedRoute.tsx` — attend `isLoading` avant de rediriger (évite flash de /login)
- `frontend/src/pages/LoginPage.tsx` — réécriture : remember me, visibilité mdp, liens register/forgot-password
- `frontend/src/pages/RegisterPage.tsx` — indicateur force mdp 4 niveaux (Tailwind) ; redirige vers /login
- `frontend/src/pages/ForgotPasswordPage.tsx` — succès sans révéler si email connu
- `frontend/src/pages/ResetPasswordPage.tsx` — lit `?token=` URL, redirige /login après 2s
- `frontend/vite.config.ts` — proxy `/auth` + 12 autres routes avec `changeOrigin: true`
- `frontend/src/setupTests.ts` — mock global `fetch` pour `/auth/me` → 401 (isLoading résolu dans tests)
- `tests/test_auth_endpoints.py` — 13 tests CI : register (succès/dupliqué/faible), login (succès/mauvais mdp/rate limit), logout, me (sans cookie/avec cookie), forgot-password (connu/inconnu), reset-password (valide/invalide)
- `frontend/src/__tests__/RegisterPage.test.tsx` — 6 tests Vitest : rendu, erreur vide, indicateur force, appel authRegister + redirect, erreur API, lien login
- `frontend/src/__tests__/LoginPage.test.tsx` — 6 tests Vitest réécrits : rendu, erreur vide, appel authLogin + redirect, erreur API, lien register, lien forgot-password

**Version** : 9.3.0 (9.2.0 = migration Vite 8 + Tailwind 4 en parallèle — cf. commit cf5a7a36)
**Tests** : 1396 CI verts (hors e2e et evals) — +13 tests Sprint Login ; 212 Vitest verts — +7 tests (6 RegisterPage + 1 LoginPage net)

---

### Sprint 100 — Nettoyage structure repo (publishable GitHub) ✅

**Objectif :** Rendre la racine du dépôt propre et compréhensible pour un visiteur GitHub : déplacer les fichiers internes Claude Code, supprimer les artefacts résiduels, protéger les analyses personnelles, réorganiser les 80+ tests à plat en sous-dossiers thématiques.

**Livrables :**
- `.claude/prompts/archive/` — 4 anciens prompts sprint (sprint-1 à sprint-4) déplacés depuis la racine
- `.claude/prompts/` — 5 prompts actifs déplacés (prompt-bootstrap-webapp.md, prompt-frontend-catchup.md, prompt-sprint-ci-dependabot.md, prompt-create-login-sprint.md, prompt-rag-bootstrap.md)
- `.claude/docs/revue-projet-rag.md` — revue interne déplacée
- `docs/architecture/architecture-copilote-financier.md` — doc d'architecture déplacée dans docs/
- Supprimés : `test_write.txt` (résidu OneDrive), `=2.0.0` (artefact pip)
- `.gitignore` — `analyses/` + `.claude/settings.local.json` ajoutés ; `analyses/BNS-2026-05.md` et `.claude/settings.local.json` désindexés (git rm --cached)
- `tests/skills/` (20 fichiers) — tests skills tier1/tier2
- `tests/api/` (26 fichiers) — tests endpoints FastAPI
- `tests/services/` (24 fichiers) — tests couche services
- `tests/workers/` (3 fichiers) — tests tâches Celery
- `tests/orchestrator/` (5 fichiers) — tests orchestrateur + intégration
- `tests/load/test_load_smoke.py` — déplacé dans load/ existant

**Note :** `.claude/skills/.git` (dépôt git imbriqué sans .gitmodules) — signalé à l'utilisateur pour décision ; `.claude/skills/investment/` — dossier orphelin, idem. → Résolus depuis : voir Sprint 101 ci-dessous.

**Version** : 9.5.0
**Tests** : 1401 CI verts (inchangé — réorganisation structurelle uniquement) ; 217 Vitest verts (inchangé)

---

### Sprint 99 — Tableau de bord alertes (AlertsPage) ✅

**Objectif :** Nouvelle page `/alerts` listant les alertes récentes générées par Celery (ESG + composite + prix) avec horodatage, ticker, type d'alerte et valeur. Persistance dans une nouvelle table `alert_history`.

**Livrables :**
- `app/services/alert_history_service.py` — `AlertHistoryService` : `record(ticker, type, valeur, seuil, message)` INSERT + retourne id, `get_recent(limit=50)` SELECT ORDER BY created_at DESC
- `app/api/main.py` — migration idempotente `CREATE TABLE IF NOT EXISTS alert_history (id BIGSERIAL PRIMARY KEY, ticker TEXT, type TEXT, valeur DOUBLE PRECISION, seuil DOUBLE PRECISION, message TEXT, created_at TIMESTAMPTZ DEFAULT NOW())` + index `idx_alert_history_ticker_created` ; service instancié + `app.state.alert_history_service` ; endpoint `GET /alerts?limit=50`
- `infra/postgres/init.sql` — table + index ajoutés pour les nouveaux volumes PG
- `app/workers/tasks.py` — persistance best-effort (try/except + logger.warning) dans `_execute_esg_degradation_check()` (type `ESG_DEGRADATION`) et `_execute_scheduled_screener()` (type `SCREENER_FORT`)
- `frontend/src/types/index.ts` — interfaces `AlertEntry` + `AlertsResponse`
- `frontend/src/api/alerts.ts` — `fetchAlerts(limit=50): Promise<AlertsResponse>`
- `frontend/src/pages/AlertsPage.tsx` — React Query `['alerts']`, tableau Horodatage/Ticker/Type badge coloré/Valeur/Seuil/Message, états vide/chargement/erreur, `data-testid="alerts-table"`
- `frontend/src/App.tsx` — route `/alerts` + lien "Alertes" dans la nav
- `tests/test_alert_history_service.py` — 3 tests CI : `record()` params SQL, `get_recent()` tri + limit, endpoint 200 + liste
- `frontend/src/__tests__/AlertsPage.test.tsx` — 5 tests Vitest : rendu vide, 2 alertes, badge type, spinner chargement, erreur API

**Version** : 9.4.0
**Tests** : 1401 CI verts (hors e2e et evals) — +3 tests Sprint 99 ; 217 Vitest verts — +5 tests Sprint 99

---

### Sprint 90 — Pagination avancée historique ✅

**Objectif :** Remplacer la pagination cursor (`before=ISO8601`) par une pagination offset/limit avec `total_count`. Interface paginée numérotée dans `HistoryPage.tsx` avec boutons Précédent/Suivant et label "Page X sur Y", plus sélecteur de taille de page (10/25/50).

**Livrables :**
- `app/orchestrator/core.py` — modèle `PagedHistoryResponse(ticker, q, entries, page, page_size, total_count, total_pages)` ; méthode `Orchestrator.get_history_paged()` exécutant `SELECT ... LIMIT $5 OFFSET $6` et `SELECT COUNT(*)` en parallèle via `asyncio.gather` ; `get_history()` (cursor) préservé pour rétrocompat
- `app/api/main.py` — nouvel endpoint `GET /history-paged?ticker=&q=&page=1&page_size=10&from_dt=&to_dt=` avec validation `page >= 1` et `1 <= page_size <= 50` (sinon 422) ; `GET /history` (cursor) inchangé
- `frontend/src/types/index.ts` — interface `PagedHistoryResponse`
- `frontend/src/api/analyze.ts` — `getHistoryPaged(filters, page, pageSize)` + interface `HistoryPagedFilters`
- `frontend/src/pages/HistoryPage.tsx` — refonte : `currentPage`/`pageSize` (states) au lieu de `nextBefore` ; boutons `data-testid="history-pagination-prev"` / `history-pagination-next` (désactivés aux extrémités) ; label `data-testid="history-page-label"` ("Page X sur Y") ; sélecteur `data-testid="history-page-size"` (10/25/50) ; `useEffect` reset `currentPage=1` quand filtre/pageSize change
- `tests/test_history_paged_orchestrator.py` — 3 tests CI (LIMIT/OFFSET attendus, COUNT(*) propagé, page=2 offset=10)
- `tests/test_history_paged_endpoint.py` — 4 tests CI (200 page+page_size, 422 page<1, 422 page_size>50, total_pages correct)
- `frontend/src/__tests__/HistoryPagination.test.tsx` — 4 tests Vitest (rendu prev/next/label, clic Suivant → page=2, clic Précédent → page=1, changement filtre reset page=1)
- `frontend/src/__tests__/HistoryPage.test.tsx`, `HistorySearch.test.tsx`, `HistoryDateFilter.test.tsx` — mocks `getHistory` migrés vers `getHistoryPaged`

**Version** : 8.3.0
**Tests** : 1368 CI verts (hors e2e et evals) — +7 tests Sprint 90, 6 tests Sprint 89 préservés ; +4 Vitest (total 187+)

**Note opérationnelle :** OneDrive a tronqué de façon répétée `app/orchestrator/core.py`, `app/api/main.py`, `frontend/src/types/index.ts`, `frontend/src/api/analyze.ts` et les 3 tests Vitest existants à mi-édition. Restauration par appends Python en chunks de ~600 bytes (sous le seuil de troncation OneDrive observé), avec vérification `wc -l` + balance braces/parens après chaque écriture. Une duplication SQL préexistante dans `get_history()` (héritée du Sprint 89) a été détectée et tronquée via `re.search` + `os.fsync` avant ré-écriture propre.

---

### Sprint 89 — Historique des scores ESG ✅

**Objectif :** Persister un historique des scores ESG dans une nouvelle table `esg_score_history` alimentée à chaque analyse ESG, exposer un endpoint `GET /esg-history/{ticker}` et afficher un graphique recharts dans `EsgPage.tsx` pour visualiser l'évolution dans le temps. Pattern identique à `composite_score_history` + `CompositeHistoryService` (Sprint 57).

**Livrables :**
- `app/services/esg_history_service.py` — `EsgHistoryService` avec `record(ticker, score)` (calcule le verdict via `esg_verdict()` puis INSERT) et `get_history(ticker, limit=100)` (SELECT ORDER BY recorded_at DESC)
- `app/api/endpoints/esg_history.py` — `GET /esg-history/{ticker}?limit=100` retourne `{ticker, points: [{id, ticker, score, verdict, recorded_at}]}`, 404 si aucun point
- `app/api/main.py` — migration idempotente `CREATE TABLE IF NOT EXISTS esg_score_history (id BIGSERIAL PRIMARY KEY, ticker TEXT, score DOUBLE PRECISION, verdict TEXT, recorded_at TIMESTAMPTZ DEFAULT NOW())` + index `idx_esg_hist_ticker_recorded ON (ticker, recorded_at DESC)` ; instanciation `EsgHistoryService(db_pool)` exposée dans `app.state.esg_history_service` ; routeur enregistré ; service passé à `orchestrator.run_company_analysis()`
- `infra/postgres/init.sql` — table `esg_score_history` + index ajoutés en bootstrap pour les nouveaux volumes PG
- `app/orchestrator/core.py` — `run_company_analysis()` et `stream_company_analysis()` acceptent `esg_history_service` kwarg ; après l'appel à `EsgSimplifiedSkill`, `await esg_history_service.record(ticker, esg_output.esg_score)` en best-effort (try/except + `logger.warning` sans interrompre l'analyse)
- `app/api/endpoints/analyze_stream.py` — `_sse_generator` propage `esg_history_service`
- `frontend/src/types/index.ts` — interfaces `EsgHistoryPoint` et `EsgHistoryResponse`
- `frontend/src/api/esg.ts` — `fetchEsgHistory(ticker, limit=100)` via `apiClient.request`
- `frontend/src/components/EsgHistoryChart.tsx` — `LineChart` recharts (X-axis date / Y-axis 0-15), `ReferenceLine` aux seuils 10 (FORT) et 5 (MODÉRÉ), `Tooltip` coloré par verdict, palette cohérente avec `CompositeScoreChart`
- `frontend/src/pages/EsgPage.tsx` — clic sur un ticker du tableau → `setSelectedTicker` → query `['esg-history', ticker]` (enabled si sélectionné) → rendu de `EsgHistoryChart` en bas de page avec titre "Évolution ESG — {ticker}"
- `tests/test_esg_history_service.py` — 3 tests CI (`record()` calcule FORT/MODERE/FAIBLE via `esg_verdict()`, `record()` insère avec bons params, `get_history()` tri DESC + limit)
- `tests/test_esg_history_endpoint.py` — 3 tests CI (200 avec points, 404 si vide, format réponse + paramètre `limit` propagé)
- `frontend/src/__tests__/EsgHistoryChart.test.tsx` — 4 tests Vitest (empty, rendu avec 3 points, loading, error)

**Version** : 8.2.0
**Tests** : 1361 CI verts (hors e2e et evals) — +6 tests Sprint 89, 9 tests Sprint 88 préservés ; +4 Vitest

**Note opérationnelle :** lors de l'exécution du sprint, la synchronisation OneDrive a tronqué `app/api/main.py` (629→596 lignes) et `app/orchestrator/core.py` (1745→1708 lignes) à mi-édition. Les fichiers ont été restaurés en concaténant la queue manquante via un script Python en bash (les Edits intermédiaires étaient présents, seule la queue avait été perdue). `app/api/endpoints/watchlist.py` et `app/workers/tasks.py` ont été vérifiés intacts avant et après les modifications (aucun octet nul, syntaxe Python OK).

---

### Sprint 88 — Rapport PDF mensuel : section ESG ✅

**Objectif :** Enrichir le `MonthlyReportService` pour ajouter une section ESG en fin de PDF mensuel si au moins un ticker de la watchlist a un `last_esg_score` non-null. Aucun changement frontend — le PDF enrichi est servi par `GET /monthly-report` existant.

**Livrables :**
- `app/utils/esg_utils.py` — extraction du helper `esg_verdict()` (>=10 → ESG_FORT, >=5 → ESG_MODERE, sinon ESG_FAIBLE, None → N/A) pour éviter l'import circulaire `services → api/endpoints`
- `app/api/endpoints/watchlist.py` — `_esg_verdict` devient un alias rétro-compatible pointant vers `app.utils.esg_utils.esg_verdict`
- `app/services/monthly_report_service.py` — nouveau kwarg optionnel `watchlist_service: WatchlistService | None`, méthodes `_build_esg_section_pdf()` (mini-PDF reportlab avec table 4 colonnes : Ticker / Score ESG / Verdict ESG / Seuil alerte, tri scores non-null DESC puis null) et `_append_esg_section()` (concaténation pypdf, fallback silencieux si PDF non parseable) ; section ajoutée uniquement si au moins un score non-null
- `app/api/endpoints/monthly_report.py` — `watchlist_service` récupéré depuis `request.app.state` et passé à `generate()`
- `app/workers/tasks.py` — `_execute_monthly_report()` instancie `WatchlistService(db_pool)` et le passe à `generate()`
- `requirements.txt` — ajout `pypdf>=3.0.0` (concaténation de PDF)
- `tests/test_monthly_report_service.py` — 3 nouveaux tests : `test_monthly_report_pdf_contient_esg_quand_score_present` (extraction texte pypdf), `test_monthly_report_pdf_sans_esg_quand_aucun_score` (PDF identique au mock watchlist), `test_esg_verdict_helper_importable` (verdict + alias `_esg_verdict is esg_verdict`)

**Version** : 8.1.0
**Tests** : 1355 CI verts (hors e2e et evals) — +3 tests Sprint 88, 6 tests Sprint 81 préservés

---

### Sprint 87 — Comparaison avec analyse Claude live (opt-in) ✅

**Objectif :** Enrichir la page `/compare` avec un bouton "Analyser" opt-in sur les colonnes dont le ticker n'a pas encore d'analyse dans l'historique (`analysis_id = null`). Quand l'utilisateur clique, une analyse fraîche est lancée via `POST /analyze` et le tableau se rafraîchit automatiquement.

**Livrables :**
- Backend : aucun changement requis — `analysis_id: str | None` déjà présent dans `TickerComparison` (backend + frontend types) depuis Sprint 80
- `frontend/src/pages/ComparePage.tsx` — import `postAnalyze` + `useRef` ; states `analyzingTickers: Set<string>` + `tickerErrors: Record<string, string>` ; `handleAnalyze()` : `Promise.race` avec timeout 60s, refresh via `postCompare(result.tickers)`, message d'erreur inline avec disparition après 5s ; bouton "Analyser" (`data-testid="analyze-btn-{ticker}"`) visible uniquement si `analysis_id === null`, désactivé pendant l'appel
- `frontend/src/__tests__/ComparePage.test.tsx` — 5 nouveaux tests (bouton visible si null, absent si défini, appel `postAnalyze` avec bon ticker, refresh `postCompare` après succès, message d'erreur inline)

**Version** : 8.0.0
**Tests** : 1340 CI verts (hors e2e et evals) + 179 Vitest verts (0 CI ajouté, +5 Vitest)

---

### Sprint 86 — Alertes Slack / email ✅

**Objectif :** Ajouter un canal de notification Slack (Incoming Webhook) en complément du webhook HTTP générique existant. Les alertes ESG, le screener hebdomadaire et le rapport mensuel peuvent désormais être envoyés sur Slack via `SLACK_WEBHOOK_URL` — optionnel, retourne False silencieusement si absent.

**Livrables :**
- `app/services/slack_service.py` — `SlackService` (4 méthodes async : `send_text`, `send_esg_alert`, `send_screener_summary`, `send_monthly_report_summary`) ; `httpx.AsyncClient` avec 1 retry, no-op si `SLACK_WEBHOOK_URL` absent
- `app/services/webhook_service.py` — `WebhookService.__init__` instancie `SlackService` ; `send_esg_alert()` appelle aussi `self._slack.send_esg_alert()` en complément
- `app/workers/tasks.py` — import `SlackService` ; `_execute_scheduled_screener()` appelle `send_screener_summary()` en fin de tâche ; `_execute_monthly_report()` supprime le guard WEBHOOK_URL-only (supporte SLACK_WEBHOOK_URL seul) et appelle `send_monthly_report_summary()` après envoi webhook
- `app/api/main.py` — import + instanciation `SlackService()` dans lifespan + `app.state.slack_service`
- `.env.example` — `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/VOTRE_WEBHOOK_ICI`
- `tests/test_slack_service.py` — 3 tests CI : `send_text` False sans URL, payload JSON correct avec URL, `send_esg_alert` False sans URL

**Version** : 7.9.0
**Tests** : 1340 CI verts (hors e2e et evals) + 174 Vitest verts

---

### Sprint 85 — Export annotations CSV/Excel ✅

**Objectif :** Permettre à Yves d'exporter toutes ses annotations en CSV et Excel (avec le ticker du JOIN `analysis_history`), via deux boutons dans HistoryPage et deux endpoints dédiés.

**Livrables :**
- `app/services/annotation_service.py` — `get_all_with_ticker()` : requête SQL avec `LEFT JOIN analysis_history` ordonnée par `updated_at DESC`
- `app/api/endpoints/annotations.py` — `GET /annotations/export.csv` (utf-8-sig BOM, 5 colonnes) et `GET /annotations/export.xlsx` (openpyxl, en-têtes gras gris) ; routes statiques placées avant `/{analysis_id}` pour éviter le conflit de routage
- `frontend/src/api/annotations.ts` — `downloadAnnotationsCsv()` et `downloadAnnotationsXlsx()` via `apiClient.requestBlob()`
- `frontend/src/pages/HistoryPage.tsx` — boutons "Exporter CSV" (`data-testid="export-annotations-csv-btn"`) et "Exporter Excel" (`data-testid="export-annotations-xlsx-btn"`) avec états loading/erreur ; message `data-testid="export-annotations-error"` en cas d'échec
- `tests/test_annotations_export.py` — 3 tests CI : get_all_with_ticker() retourne le ticker, CSV 200 + content-type + colonnes, XLSX 200 + content-type
- `frontend/src/__tests__/AnnotationsExport.test.tsx` — 5 tests Vitest : présence des 2 boutons, clic CSV appelle downloadAnnotationsCsv, clic Excel appelle downloadAnnotationsXlsx, erreur API affiche message

**Version** : 7.8.0
**Tests** : 1337 CI verts (hors e2e et evals) + 174 Vitest verts

---

### Sprint 84 — Seuil ESG configurable par ticker (UI) ✅

**Objectif :** Permettre à Yves de modifier le seuil d'alerte ESG (`esg_alert_threshold`) pour chaque ticker de la watchlist directement depuis l'interface React, via un bouton inline dans `WatchlistTable` et l'endpoint `PATCH /watchlist/{id}/esg-threshold`.

**Livrables :**
- `app/services/watchlist_service.py` — `update_esg_threshold(entry_id, threshold)` : UPDATE SQL sur le champ existant
- `app/api/endpoints/watchlist.py` — `EsgThresholdUpdate` Pydantic + `PATCH /{entry_id}/esg-threshold` : get_entry → update → get_entry → return
- `frontend/src/api/watchlist.ts` — `patchEsgThreshold(id, threshold)` couche HTTP PATCH
- `frontend/src/components/WatchlistTable.tsx` — colonne "Seuil ESG" avec édition inline (display mode : valeur + bouton ✎ ; edit mode : Input + Sauvegarder + Annuler + message d'erreur), appel `patchEsgThreshold()` + `onRefresh()`
- `frontend/src/pages/WatchlistPage.tsx` — prop `onRefresh` passée à `WatchlistTable` (invalide la query `['watchlist']`)
- `tests/test_watchlist_esg_threshold.py` — 3 tests CI : service SQL params corrects, PATCH 200 avec nouveau seuil, PATCH 404 id inexistant
- `frontend/src/__tests__/WatchlistEsgThreshold.test.tsx` — 5 tests Vitest : affichage seuil, ouverture input, sauvegarde API, annuler sans appel, erreur API
- `frontend/src/__tests__/PdfDownload.test.tsx` — correction `makeEntry` (champs `esg_alert_threshold` + `last_esg_score` manquants depuis Sprint 77)

**Version** : 7.7.0
**Tests** : 1334 CI verts (hors e2e et evals) + 169 Vitest verts

---

### Sprint 83 — Export watchlist Excel enrichi (ESG) ✅

**Objectif :** Enrichir `GET /watchlist/export.xlsx` avec deux nouvelles colonnes : `Score ESG` (valeur numérique arrondie à 1 décimale) et `Verdict ESG` (ESG_FORT / ESG_MODERE / ESG_FAIBLE / N/A), alimentées depuis `last_esg_score` déjà persisté (Sprint 77).

**Livrables :**
- `app/api/endpoints/watchlist.py` — helper `_esg_verdict(score)`, constantes `_XLSX_HEADERS` / `_XLSX_COL_WIDTHS` étendues, boucle `_generate_watchlist_xlsx()` enrichie
- `app/services/watchlist_service.py` — `get_all_with_composite()` : SELECT étendu avec `w.last_esg_score` et `w.esg_alert_threshold`
- `tests/test_watchlist_xlsx_esg.py` — 8 tests unitaires (`_esg_verdict` indépendant, headers, score 7.5, verdict ESG_MODERE, score None, verdict N/A, rétrocompatibilité 7 colonnes)
- Aucun changement frontend requis — les nouvelles colonnes apparaissent automatiquement dans le fichier téléchargé

**Version** : 7.6.0
**Tests** : 1331 CI verts (hors e2e et evals) + 164 Vitest verts

---

### Sprint 82 — Page ESG dans le frontend ✅

**Objectif :** Créer une page dédiée `/esg` affichant les scores ESG de tous les tickers de la watchlist depuis le champ `last_esg_score` persisté (Sprint 77). Tableau tritable par colonne, badge verdict coloré, lien vers analyse.

**Livrables :**
- `app/api/endpoints/watchlist.py` — schemas Pydantic `WatchlistEsgEntry` / `WatchlistEsgResponse` + `GET /watchlist/esg-scores` (tri DESC nulls last, utilise `WatchlistService.list_entries()`)
- `frontend/src/types/index.ts` — interfaces `WatchlistEsgEntry` / `WatchlistEsgResponse` (snake_case, cohérent avec le reste du projet)
- `frontend/src/api/watchlist.ts` — `fetchWatchlistEsgScores()` 
- `frontend/src/pages/EsgPage.tsx` — tableau tritable (Score ESG + Ticker), badges ESG_FORT/ESG_MODERE/ESG_FAIBLE, score null → "--", loading state, lien "Analyser"
- `frontend/src/App.tsx` — route `/esg` + NavItem "ESG" dans la barre de navigation
- `tests/test_esg_scores_endpoint.py` — 3 tests CI (200 champs, liste vide, tri DESC nulls last)
- `frontend/src/__tests__/EsgPage.test.tsx` — 5 tests Vitest (badge FORT/MODERE/FAIBLE, score null "--", tri colonne)

**Version** : 7.5.0
**Tests** : 1323 CI verts (hors e2e et evals) + 164 Vitest verts

---

### Sprint 81 — Rapport PDF mensuel automatisé ✅

**Objectif :** Ajouter une tâche Celery mensuelle (1er du mois à 08h00 UTC) qui génère automatiquement un rapport PDF consolidé (watchlist + screener des tickers FORT) et l'envoie par webhook multipart.

**Livrables :**
- `app/services/monthly_report_service.py` — `MonthlyReportService.generate()`, requête `composite_score_history` DISTINCT ON pour tickers FORT, `ScreenResult` synthétique sans appel Claude
- `app/api/endpoints/monthly_report.py` — `GET /monthly-report`, déclenchement manuel, 404 si watchlist vide
- `app/api/main.py` — `MonthlyReportService` instancié dans lifespan + `app.state.monthly_report_service` + `monthly_report_router` enregistré
- `app/services/webhook_service.py` — `send_monthly_report(watchlist_pdf, screener_pdf)`, multipart 2 fichiers, pattern identique à `send_screener_pdf_report()`
- `app/workers/tasks.py` — `_execute_monthly_report()` + `run_monthly_report` Celery task, skip si `WEBHOOK_URL` absent
- `app/workers/celery_app.py` — `beat_schedule` entrée `run-monthly-report`, `crontab(hour=8, minute=0, day_of_month=1)`
- `tests/test_monthly_report_service.py` — 6 tests unitaires (init, tuple bytes, PDF watchlist, PDF screener, ValueError vide, aucun FORT)
- `tests/test_monthly_report_endpoint.py` — 4 tests intégration (200, media_type, Content-Disposition, 404 vide)

**Version** : 7.4.0
**Tests** : 1320 CI verts (hors e2e et evals) + 159 Vitest verts

---

### Sprint 80 — Mode comparaison tickers ✅

**Objectif :** Ajouter une page `/compare` affichant un tableau multi-skills côte à côte pour 2 à 5 tickers. Données historiques uniquement — aucun appel Claude.

**Livrables :**
- `app/services/compare_service.py` — `CompareService.compare()`, requête SQL `DISTINCT ON (ticker)` + `LEFT JOIN LATERAL composite_score_history`, extraction JSONB graham/buffett/dorsey
- `app/api/endpoints/compare.py` — `POST /compare`, `CompareRequest` (validation 2-5 tickers), `CompareResponse`
- `app/api/main.py` — `CompareService` instancié dans lifespan + `app.state.compare_service` + `compare_router` enregistré
- `frontend/src/types/index.ts` — `TickerComparison` + `CompareResponse` interfaces
- `frontend/src/api/compare.ts` — `postCompare()` couche HTTP
- `frontend/src/pages/ComparePage.tsx` — tableau 7 lignes × N colonnes, highlight jaune du meilleur composite_score, badges colorés par verdict, gestion ticker absent `--`
- `frontend/src/App.tsx` — route `/compare` + lien nav "Comparer"
- `tests/test_compare_service.py` — 4 tests unitaires (2 tickers, ticker absent, ordre, champs optionnels null)
- `tests/test_compare_endpoint.py` — 6 tests intégration (200 avec 2/5 tickers, 422 si 1/6/0, ticker absent null)
- `frontend/src/__tests__/ComparePage.test.tsx` — 5 tests Vitest (rendu, soumission, highlight, ticker absent, erreur validation)

**Version** : 7.3.0
**Tests** : 1310 CI verts (hors e2e et evals) + 159 Vitest verts

---

### Sprint 79 — Filtre dates dans l'historique ✅

**Objectif :** Ajouter un filtre par plage de dates ISO 8601 dans `GET /history` et les sélecteurs date correspondants dans `HistoryPage`.

**Livrables :**
- `app/orchestrator/core.py` — `get_history()` étendu avec `from_dt` et `to_dt` (`datetime | None`), clauses SQL `created_at >= $5` / `created_at <= $6`
- `app/api/main.py` — paramètres query `from_dt` et `to_dt` sur `GET /history`, validation `datetime.fromisoformat()`, 422 si format invalide
- `frontend/src/api/analyze.ts` — `getHistory()` étendu avec `fromDt?` et `toDt?`, ajoutés aux URLSearchParams
- `frontend/src/pages/HistoryPage.tsx` — deux `<Input type="date">` "Du" / "Au" (`data-testid` normalisés), validation UI from>to, passés dans query + loadMore
- `tests/test_history_filter_dates.py` — 5 tests CI (from_dt seul, to_dt seul, les deux passés à l'orchestrateur, formats invalides 422)
- `frontend/src/__tests__/HistoryDateFilter.test.tsx` — 5 tests Vitest (rendu champs, soumission from+to, validation from>to, fromDt seul)
- `frontend/src/__tests__/HistorySearch.test.tsx` + `HistoryPage.test.tsx` — signatures mises à jour (6 args)

**Version** : 7.2.0
**Tests** : 1300 CI verts (hors e2e et evals) + 154 Vitest verts

---

### Sprint 78 — Annotations d'analyses ✅

**Objectif :** Permettre à Yves d'annoter chaque analyse avec des notes libres, persistées en PostgreSQL et consultables depuis l'historique.

**Livrables :**
- `app/models/annotation.py` — `Annotation` + `AnnotationCreate` (Pydantic v2, `min_length=1`)
- `app/services/annotation_service.py` — `AnnotationService.upsert()` + `get()` — INSERT ON CONFLICT DO UPDATE
- `app/api/endpoints/annotations.py` — `POST /annotations` (201, upsert idempotent) + `GET /annotations/{analysis_id}` (200/404)
- `app/api/main.py` — migration `CREATE TABLE IF NOT EXISTS annotations` + instanciation `AnnotationService` dans lifespan + router enregistré
- `frontend/src/types/index.ts` — `Annotation` + `AnnotationCreate` interfaces
- `frontend/src/api/annotations.ts` — `getAnnotation()` + `upsertAnnotation()`
- `frontend/src/components/AnnotationSection.tsx` — composant accordéon (toggle, affichage note existante, édition en place, `data-testid` normalisés)
- `frontend/src/components/HistoryTable.tsx` — colonne "Notes" avec `AnnotationSection` par ligne
- `tests/test_annotation_service.py` — 5 tests unitaires (upsert, get, get absent, exception DB)
- `tests/test_annotations_endpoint.py` — 5 tests intégration (201 create, 422 note vide, 200 get, 404 absent, idempotent)
- `frontend/src/__tests__/AnnotationSection.test.tsx` — 5 tests Vitest (toggle fermé, vide, note existante, sauvegarde, édition)

**Version** : 7.1.0
**Tests** : 1294 CI verts (hors e2e et evals) + 149 Vitest verts

---

### Sprint 76 — Export PDF watchlist depuis l'interface ✅

**Objectif :** Ajouter un bouton "Exporter PDF" dans WatchlistPage appelant `GET /watchlist/export.pdf`. Le rapport couvre toutes les positions surveillées avec composite_score, label, alerte, date de dernière analyse et section Top Picks.

**Livrables :**
- `app/services/watchlist_pdf_service.py` — `WatchlistPdfService.generate_watchlist_pdf()`, requête SQL enrichie (JOIN LATERAL composite_score_history + analysis_history), styles reportlab cohérents avec ScreenerPdfService
- `GET /watchlist/export.pdf` dans `app/api/endpoints/watchlist.py` — `application/pdf`, `Content-Disposition` daté, 404 si vide
- `app/api/main.py` — `WatchlistPdfService` instancié dans lifespan et exposé dans `app.state`
- `downloadWatchlistPdf()` dans `frontend/src/api/analyze.ts` — pattern requestBlob
- Bouton "Exporter PDF" dans WatchlistPage (`data-testid="export-pdf-watchlist"`, état loading, gestion 404)
- `tests/test_watchlist_pdf_service.py` — 8 tests unitaires (signature PDF, tickers, ValueError vide, top picks, score absent)
- `tests/test_watchlist_export_pdf.py` — 5 tests intégration (200, Content-Disposition, 404, appel pool/composite_history_service)
- `frontend/src/__tests__/WatchlistPdfExport.test.tsx` — 5 tests Vitest (rendu bouton, click, loading, 404, erreur 500)

**Version** : 7.0.0
**Tests** : 1284 CI verts (hors e2e et evals) + 144 Vitest verts

---

### Sprint 75 — ESG SKILL.md + references/ — dette technique ✅

**Objectif :** Créer le dossier `.claude/skills/esg-simplified/` avec `SKILL.md` et 5 fichiers `references/`, fermant la dette technique ouverte lors du Sprint 74. Le skill `esg_simplified` est en production depuis Sprint 70 sans corpus conceptuel dans `.claude/skills/`.

**Livrables :**
- `.claude/skills/esg-simplified/SKILL.md` — logique, workflow, 15 critères ESG 5E+5S+5G, guard-rails
- `.claude/skills/esg-simplified/references/esg-proxies-rationale.md` — justification de l'approche proxy, limites fondamentales, comparaison MSCI/Sustainalytics
- `.claude/skills/esg-simplified/references/criteres-dimension-E.md` — 5 critères E avec formules, seuils, ajustements sectoriels
- `.claude/skills/esg-simplified/references/criteres-dimension-S.md` — 5 critères S
- `.claude/skills/esg-simplified/references/criteres-dimension-G.md` — 5 critères G
- `.claude/skills/esg-simplified/references/scoring-verdicts.md` — barème 0-15, verdicts, 3 exemples chiffrés (banque / tech / industriel)
- `base-connaissances-skills.md` mis à jour : flag ⚠️ retiré, compteur 15→16 SKILL.md

**Version** : 6.8.0

---

### Sprint 74 — Refactor CLAUDE.md → `.claude/rules/` path-scoped ✅

**Objectif :** Éclater le CLAUDE.md monolithique (490 lignes) en un système modulaire `.claude/rules/` avec scoping par chemin de fichier, sans perdre une seule directive opérationnelle.

**Livrables :**
- `CLAUDE.md` réduit à 100 lignes (index + table de pointeurs)
- 16 fichiers `.claude/rules/*.md` — chacun avec `paths:` ciblant les contextes pertinents
- `docs/cheatsheet.md` — toutes les commandes opérationnelles (201 lignes)
- `.gitignore` créé à la racine (manquait depuis la Phase 0)
- Incohérences résolues : catalogue 15→16 skills tier2, `compounder_buffett` documenté comme workflow, compteur pages frontend corrigé à 7

**Version** : 6.7.0

---

### Phase 1 — Infrastructure RAG ✅ (Sprints 1–4)
- **Sprint 1** : `SkillBase` extrait dans `app/skills/base.py`, `UsageDetail` propagé, tokens persistés, `@model_validator` critères Graham, `/healthz` enrichi
- **Sprint 2** : `scripts/ingest_rag.py`, collection Qdrant `investment_knowledge`, `RagService`, `get_citations()`, logging structuré JSON
- **Sprint 3** : `earnings_quality` skill + context enrichment (`GrahamContext`), `GET /history`
- **Sprint 4** : `LangfuseTracer`, `GET /metrics`, timeout `CLAUDE_TIMEOUT_S`, retry backoff exponentiel

---

## Phase 2 — Skills restants (mois 1–2)

**Objectif :** Implémenter 3 skills Tier 2 + extracteurs automatiques de ratios.
**Workflow cible :**
```
graham_analysis → earnings_quality → dorsey_moat → buffett_quality → stock_valuation_triangulation
```

---

### Sprint 5 — dorsey_moat ✅

**Objectif :** Qualifier la durabilité de l'avantage concurrentiel selon Pat Dorsey.

#### Fichiers à créer
```
app/skills/tier2/dorsey_moat/__init__.py
app/skills/tier2/dorsey_moat/schemas.py
app/skills/tier2/dorsey_moat/skill.py
app/skills/tier2/dorsey_moat/prompts/system.md
tests/test_dorsey_moat.py
```

#### Spécifications
- Hériter de `SkillBase` (`app/skills/base.py`)
- Input : `DorseyMoatInput(ticker, ratios: DorseyRatios, earnings_context: EarningsContext | None)`
- `EarningsContext` = verdict + z_score + m_score depuis `EarningsQualityOutput` (context enrichment)
- Output : `DorseyMoatOutput` avec :
  - `moat_type` : `WIDE | NARROW | NONE`
  - `sources_identifiees` : list[MoatSource] (5 sources : intangibles, switching_costs, network_effects, cost_advantages, efficient_scale)
  - `roic_durability` : `FORTE | MODÉRÉE | FAIBLE` (basé sur ROIC fourni ou inféré)
  - `verdict_detail` : str
  - `recommandation_prochaine_etape` : list[str]
  - `citations` : list[Citation]
  - `cost_usd` intégré dans UsageDetail
- Source de vérité du prompt : `.claude/skills/dorsey-moat-analysis/SKILL.md` + `references/*.md`
- System prompt > 1 024 tokens (obligatoire pour prompt caching)

#### Intégration orchestrateur
- Ajouter `DorseyMoatSkill` dans `Orchestrator.__init__`
- Appeler après `earnings_quality` si `earnings_output` présent
- Ajouter `dorsey` dans `AnalyzeResponse`

#### Tests à écrire (`tests/test_dorsey_moat.py`)
```python
# Unitaires (pas d'appel réseau)
test_dorsey_ratios_validation_ok()          # DorseyRatios valide
test_dorsey_ratios_roic_negatif_accepte()   # ROIC négatif = pas d'erreur
test_dorsey_output_moat_type_enum()         # moat_type in {WIDE, NARROW, NONE}
test_dorsey_output_sources_count()          # len(sources_identifiees) == 5
test_dorsey_skill_build_user_message()      # message contient ticker + ratios
test_dorsey_execute_mock_claude()           # mock client.messages.create → GrahamAnalysisOutput valide
test_dorsey_get_citations_rag_absent()      # rag_service=None → citations == []

# Intégration orchestrateur
test_orchestrator_avec_dorsey()             # run_company_analysis avec earnings_ratios → dorsey présent dans response
test_orchestrator_sans_dorsey()             # sans earnings_ratios → dorsey absent
```

#### Critère de succès
```bash
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"BNS",
    "ratios":{"pe":11.0,"pb":1.3,"current_ratio":null,"debt_equity":0.45,
              "eps_growth_10y":0.27,"price":80,"book_value":61.5,
              "eps_ttm":7.25,"revenue_bn":38,"dividend_years":190},
    "earnings_ratios":{...},
    "dorsey_ratios":{...}
  }'
# → JSON avec "dorsey": {"moat_type": "WIDE|NARROW|NONE", ...}
```

---

### Sprint 6 — buffett_quality ✅

**Objectif :** Appliquer les 4 filtres Buffett + calcul des owner earnings.

#### Fichiers à créer
```
app/skills/tier2/buffett_quality/__init__.py
app/skills/tier2/buffett_quality/schemas.py
app/skills/tier2/buffett_quality/skill.py
app/skills/tier2/buffett_quality/prompts/system.md
tests/test_buffett_quality.py
```

#### Spécifications
- Input : `BuffettQualityInput(ticker, ratios: BuffettRatios, dorsey_context: DorseyContext | None)`
- `DorseyContext` = moat_type + sources depuis `DorseyMoatOutput`
- Output : `BuffettQualityOutput` avec :
  - `filtres` : list[BuffettFiltre] — les 4 filtres ("compréhensible", "economics favorables", "management", "prix attractif")
  - `owner_earnings` : float | None — BPA + amortissement - capex maintenance
  - `quality_score` : int (0–4, nombre de filtres passés)
  - `verdict` : `COMPOUNDER | QUALITE_CORRECTE | REJETER`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`
- Source du prompt : `.claude/skills/buffett-quality-investing/SKILL.md` + références

#### Tests à écrire (`tests/test_buffett_quality.py`)
```python
test_buffett_ratios_validation_ok()
test_buffett_output_filtres_count()          # len(filtres) == 4
test_buffett_output_quality_score_range()    # 0 <= quality_score <= 4
test_buffett_owner_earnings_calcul()         # owner_earnings = eps + d&a - maintenance_capex
test_buffett_execute_mock_claude()
test_buffett_get_citations_rag_absent()
test_orchestrator_avec_buffett()
```

#### Critère de succès
```bash
# → JSON avec "buffett": {"quality_score": 3, "owner_earnings": 8.50, ...}
```

---

### Sprint 7 — stock_valuation_triangulation ✅

**Objectif :** Valorisation par 3 méthodes indépendantes avec matrice de sensibilité.

#### Fichiers à créer
```
app/skills/tier2/stock_valuation/__init__.py
app/skills/tier2/stock_valuation/schemas.py
app/skills/tier2/stock_valuation/skill.py
app/skills/tier2/stock_valuation/prompts/system.md
tests/test_stock_valuation.py
```

#### Spécifications
- Input : `StockValuationInput(ticker, ratios, graham_context, earnings_context, dorsey_context, buffett_context)`
- Output : `StockValuationOutput` avec :
  - `valeur_dcf` : float | None
  - `valeur_comparables` : float | None
  - `valeur_sectorielle` : float | None
  - `fourchette_basse` / `fourchette_centrale` / `fourchette_haute` : float
  - `marge_securite_composite` : float (fraction)
  - `matrice_sensibilite` : list[list[float]] (WACC × taux_croissance)
  - `verdict` : `SOUS_EVALUE | JUSTE_VALEUR |_SUREVALUE`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`
- Source du prompt : `.claude/skills/stock-valuation-triangulation/SKILL.md` + références

#### Tests à écrire
```python
test_valuation_fourchette_coherente()        # basse < centrale < haute
test_valuation_marge_securite_calcul()       # (centrale - price) / centrale
test_valuation_matrice_sensibilite_shape()   # 5×5 ou 4×4
test_valuation_execute_mock_claude()
test_orchestrator_workflow_complet_phase2()  # tous les skills enchaînés
```

#### Critère de succès
```bash
# → JSON avec "valuation": {"fourchette_centrale": 92.50, "marge_securite_composite": 0.14, ...}
```

---

### Sprint 8 — Extracteurs Tier 1 ✅

**Objectif :** Calculer les ratios automatiquement depuis les sources publiques (fin de la saisie manuelle).

#### Fichiers à créer
```
app/skills/tier1/__init__.py
app/skills/tier1/yahoo_finance.py        # YahooFinanceExtractor
app/skills/tier1/sedar_plus.py           # SedarPlusExtractor (SEDAR+ Canada)
app/api/endpoints/extract.py             # GET /extract?ticker=BNS
tests/test_yahoo_finance.py
tests/test_sedar_plus.py
```

#### Spécifications
- `YahooFinanceExtractor.extract(ticker: str) -> GrahamRatios` (async, via `httpx` + `yfinance`)
- `SedarPlusExtractor.extract(ticker: str) -> GrahamRatios | None` (TSX seulement, best-effort)
- Nouveau endpoint : `GET /extract?ticker=BNS` → `GrahamRatios` JSON
- Nouveau workflow automatique : `POST /analyze-auto?ticker=BNS` → extraction + analyse
- Timeout 10s sur les extracteurs, erreur explicite si source indisponible

#### Tests à écrire
```python
test_yahoo_finance_mock_response()        # httpx mock → GrahamRatios valide
test_yahoo_finance_ticker_inconnu()       # → HTTPException 404
test_yahoo_finance_valeur_none_toleree()  # current_ratio=None pour banques
test_sedar_plus_tsx_seulement()          # ticker NYSE → None, pas d'erreur
test_extract_endpoint_integration()       # GET /extract?ticker=BNS avec mock Yahoo
```

---

## Phase 3 — Pipeline de synthèse (mois 2–3)

**Objectif :** Workflow d'analyse complet Phase 3 + robustesse production.

**Workflow cible Phase 3 :**
```
[Tier 1] extraction automatique
  → graham → earnings_quality → dorsey_moat → buffett_quality
  → stock_valuation → munger_mental_models
  → investment_thesis_builder → canadian_tax_considerations
```

---

### Sprint 9 — investment_thesis_builder ✅

**Objectif :** Skill de synthèse finale — consolide tous les résultats en une thèse formelle.

#### Fichiers à créer
```
app/skills/tier2/thesis_builder/__init__.py
app/skills/tier2/thesis_builder/schemas.py
app/skills/tier2/thesis_builder/skill.py
app/skills/tier2/thesis_builder/prompts/system.md
tests/test_thesis_builder.py
```

#### Spécifications
- Input : `ThesisBuilderInput(ticker, all_contexts: AllSkillContexts)` — agrège tous les outputs précédents
- Output : `ThesisBuilderOutput` avec :
  - `scenario_bull` / `scenario_base` / `scenario_bear` : ThesisScenario (prob, rendement_cible, hypotheses)
  - `kill_criteria` : list[str] — conditions qui invalident la thèse
  - `devils_advocate` : str — argument le plus fort contre la thèse
  - `position_size_pct` : float (0–10) — allocation recommandée en % du portefeuille
  - `verdict_final` : `ACHETER | ACCUMULER | CONSERVER | VENDRE`
  - `synthese_narrative` : str — 3-5 paragraphes de thèse formelle
  - `citations`

#### Tests à écrire
```python
test_thesis_scenarios_probabilites_somme_100()    # bull + base + bear = 100 %
test_thesis_position_size_range()                 # 0 <= position_size_pct <= 10
test_thesis_kill_criteria_non_vide()
test_thesis_execute_mock_claude()
```

---

### Sprint 10 — Comportemental (munger + canadian_tax) ✅

**Objectif :** Passe comportementale + optimisation fiscale québécoise.

#### Fichiers à créer
```
app/skills/tier2/munger_mental/__init__.py
app/skills/tier2/munger_mental/schemas.py
app/skills/tier2/munger_mental/skill.py
app/skills/tier2/munger_mental/prompts/system.md
app/skills/tier2/canadian_tax/__init__.py
app/skills/tier2/canadian_tax/schemas.py
app/skills/tier2/canadian_tax/skill.py
app/skills/tier2/canadian_tax/prompts/system.md
tests/test_munger.py
tests/test_canadian_tax.py
```

#### Spécifications munger_mental
- Input : `MungerInput(ticker, thesis_context: ThesisContext)` — nourri par thesis_builder
- Output : `MungerOutput` avec :
  - `biais_detectes` : list[BiaisCognitif] (nom, description, impact_sur_these)
  - `inversion_analysis` : str — "qu'est-ce qui pourrait faire échouer cette thèse ?"
  - `lollapalooza_risk` : bool — convergence de plusieurs biais amplificateurs
  - `verdict_comportemental` : `CONFIANCE_JUSTIFIEE | BIAIS_DETECTE | ALERTE_ROUGE`

#### Spécifications canadian_tax
- Input : `CanadianTaxInput(ticker, position_size_pct, verdict_final, province: str = "QC")`
- Output : `CanadianTaxOutput` avec :
  - `compte_recommande` : `CELI | REER | CELIAPP | NON_ENREGISTRE`
  - `justification_fiscale` : str
  - `impact_retenue_us` : str | None (si dividende US)
  - `strategie_smith_manoeuvre` : bool — applicable si marge HELOC disponible

#### Tests à écrire
```python
test_munger_biais_non_vide()
test_munger_inversion_non_vide()
test_tax_compte_celi_priorite()           # action croissance → CELI recommandé
test_tax_dividende_us_retenue()           # ticker US avec dividende → retenue mentionnée
test_tax_province_validation()            # province invalide → ValidationError
```

---

### Sprint 11 — Robustesse production ✅

**Objectif :** Analyse async longue durée + Redis cache + sécurité minimale.

#### Fichiers à créer / modifier
```
app/api/endpoints/jobs.py                # POST /jobs + GET /jobs/{id}
app/workers/celery_app.py               # Worker Celery
app/workers/tasks.py                    # task: run_full_analysis
app/middleware/auth.py                   # API key middleware (Bearer token)
app/middleware/rate_limit.py             # Rate limiting via Redis
```

#### Spécifications
- `POST /analyze-async` → `{"job_id": "uuid"}` (réponse immédiate)
- `GET /jobs/{job_id}` → `{"status": "pending|running|done|failed", "result": ...}`
- Résultats stockés dans Redis 24h, puis dans PostgreSQL
- Authentification : Bearer token depuis `API_KEY` env var
- Rate limiting : 10 requêtes / minute par IP (via Redis)

#### Tests à écrire
```python
test_analyze_async_retourne_job_id()
test_job_status_pending_puis_done()       # mock Celery task
test_auth_missing_token_401()
test_auth_invalid_token_401()
test_rate_limit_depasse_429()
```

---

## Décisions d'architecture

| Décision | Choix retenu | Décidé lors de | Raison |
|----------|-------------|---------------|--------|
| **Modèle d'embedding** | `text-embedding-3-small` (OpenAI) | Sprint 12 | Coût négligeable (~$0.00002/1k tokens), pas de GPU local requis, simplicité d'infrastructure vs `nomic-embed-text` |
| **Chunking RAG** | Sections h2/h3 (actuel) | Sprint 2 | Découpage sémantique aligné avec la structure des SKILL.md |
| **Authentification** | Bearer token simple (`API_KEY` env) | Sprint 11 | Outil interne — OAuth2 inutilement complexe à ce stade |
| **Celery broker** | Redis | Sprint 11 | Redis déjà en stack, RabbitMQ = surcharge inutile pour volumes modérés |

---

---

### Sprint 12 — CLI + décision embedding ✅

**Objectif :** Interface CLI pour analyses manuelles + décisions d'architecture closes.

#### Fichiers créés
```
scripts/analyze_cli.py        # CLI principal — wrapping de POST /analyze
scripts/cli/__init__.py       # Package (vide)
scripts/cli/formatter.py      # Formatage AnalyzeResponse → Markdown
```

#### Spécifications `analyze_cli.py`
- Ticker en argument positionnel
- `--ratios-file FILE` : JSON complet (GrahamRatios plat ou corps `/analyze` complet)
- Ratios Graham inline : `--pe`, `--pb`, `--price`, `--eps`, `--book-value`, `--debt-equity`, `--eps-growth-10y`
  - `book_value` et `eps_ttm` dérivés automatiquement si absents (`price/pb`, `price/pe`)
- `--thesis` / `--munger` pour activer les skills optionnels
- `--api-url`, `--api-key` (ou var `API_KEY`), `--output-dir`
- `--stdout` pour afficher sans sauvegarder
- Rapport sauvegardé dans `analyses/{TICKER}-{YYYY-MM}.md`
- Messages d'erreur explicites : 401 / 422 / 429 / timeout / connexion refusée

#### Usage rapide
```bash
# Ratios inline (Graham seulement)
python scripts/analyze_cli.py BNS \
    --pe 11.0 --pb 1.3 --price 80.0 \
    --debt-equity 0.45 --eps-growth-10y 0.27

# Fichier JSON complet + thèse
python scripts/analyze_cli.py BNS \
    --ratios-file data/bns_full.json --thesis --munger

# Stdout (redirection possible)
python scripts/analyze_cli.py BNS --ratios-file data/bns.json --stdout > rapport.md
```

#### Décision embedding (Sprint 12)
- **Retenu : `text-embedding-3-small`** (OpenAI)
- **Chunking : sections h2/h3** (inchangé depuis Sprint 2)
- Voir section "Décisions d'architecture" ci-dessus pour le détail

#### Critère de succès
```bash
python scripts/analyze_cli.py BNS \
    --pe 11 --pb 1.3 --price 80 --debt-equity 0.45 --eps-growth-10y 0.27
# → analyses/BNS-2026-05.md généré avec sections Graham + résumé exécutif
```

---

### Sprint 13 — Tests d'intégration end-to-end ✅

**Objectif :** Suite pytest complète validant workflow sync + async sous Docker Compose, avant d'ajouter de nouveaux skills.

#### Fichiers à créer
```
tests/conftest.py                    # Fixtures : TestClient, mock Claude, cleanup DB
tests/test_schemas.py                # Validation Pydantic des 10 schemas (critères, ordres, plages)
tests/test_integration_sync.py       # POST /analyze, /history, /metrics, /healthz, /extract
tests/test_integration_async.py      # POST /analyze-async → poll /jobs/{id} → done
tests/test_middleware.py             # Auth 401, rate limit 429, EXEMPT_PATHS
requirements-dev.txt                 # pytest, pytest-asyncio, httpx[test], respx
```

#### Spécifications
- `conftest.py` :
  - `mock_claude` : fixture qui patch `anthropic.AsyncAnthropic.messages.create` → JSON minimal valide par skill
  - `app_client` : `httpx.AsyncClient(app=app, base_url="http://test")` (pas de docker nécessaire)
  - `db_cleanup` : `DELETE FROM analysis_history WHERE ticker = 'TEST'` après chaque test d'intégration
- `test_schemas.py` (unitaires, 0 appel réseau) :
  - Graham : exactement 8 `criteria_defensif`, 5 `criteria_entreprenant`, `defensive_score` in [0,8]
  - Earnings : exactement 9 `f_score.criteria`, 6 `c_score.signaux`
  - Valuation : `fourchette_basse <= fourchette_centrale <= fourchette_haute`
  - Thesis : `bull.probabilite + base.probabilite + bear.probabilite == 1.0` (± 0.01)
  - Munger : `impact_sur_these` in {"MINEUR", "MODERE", "MAJEUR"}
  - Tax : `compte_recommande` in {"CELI", "REER", "CELIAPP", "NON_ENREGISTRE"}
- `test_integration_sync.py` :
  - `test_healthz_200` : GET /healthz → {"status": "ok"}
  - `test_analyze_graham_seulement` : POST /analyze minimal → 200 + `graham.defensive_score` in [0,8]
  - `test_analyze_ratios_invalides_422` : POST /analyze sans `pe` → 422
  - `test_analyze_coute_non_nul` : `cost_usd > 0`
  - `test_history_pagination` : 2 analyses puis GET /history → `entries` non vide
  - `test_metrics_period_valide` : GET /metrics?days=30 → `total_analyses >= 0`
  - `test_extract_endpoint` : GET /extract?ticker=TEST → 200 ou 404 (mock Yahoo)
- `test_integration_async.py` :
  - `test_analyze_async_retourne_job_id` : POST /analyze-async → `{"job_id": "..."}` (UUID)
  - `test_job_status_progression` : mock Celery task → GET /jobs/{id} → status "done"
  - `test_job_inconnu_404` : GET /jobs/uuid-inconnu → 404
- `test_middleware.py` :
  - `test_auth_absent_401` (si `API_KEY` env non vide)
  - `test_auth_invalide_401`
  - `test_auth_valide_passe`
  - `test_rate_limit_429` : 11 requêtes rapides → 429 sur la 11e
  - `test_healthz_exempt_auth` : GET /healthz sans token → 200 (EXEMPT_PATH)

#### Critère de succès
```bash
pytest tests/ -v --tb=short
# → 0 failures, 0 errors sur les tests unitaires
# → Tests intégration passent avec mock Claude (pas de vraie clé API requise)
```

---

### Sprint 14 — Skills Lynch + Fisher + Klarman ✅

**Objectif :** 3 skills manquants pour les workflows croissance, analyse qualitative et situations spéciales.

#### Fichiers à créer
```
app/skills/tier2/lynch_categories/__init__.py
app/skills/tier2/lynch_categories/schemas.py
app/skills/tier2/lynch_categories/skill.py
app/skills/tier2/lynch_categories/prompts/system.md
app/skills/tier2/fisher_scuttlebutt/__init__.py
app/skills/tier2/fisher_scuttlebutt/schemas.py
app/skills/tier2/fisher_scuttlebutt/skill.py
app/skills/tier2/fisher_scuttlebutt/prompts/system.md
app/skills/tier2/klarman_margin/__init__.py
app/skills/tier2/klarman_margin/schemas.py
app/skills/tier2/klarman_margin/skill.py
app/skills/tier2/klarman_margin/prompts/system.md
tests/test_lynch_categories.py
tests/test_fisher_scuttlebutt.py
tests/test_klarman_margin.py
```

#### Spécifications `lynch_categories`
- Source de vérité : `.claude/skills/lynch-categories-and-tenbaggers/SKILL.md` + `references/`
- Input : `LynchRatios(pe, eps_growth_5y, revenue_growth_5y, net_margin, debt_equity, fcf_yield, dividend_yield | None, capex_intensity | None)`
- Output : `LynchOutput`
  - `categorie` : `"SLOW_GROWER" | "STALWART" | "FAST_GROWER" | "CYCLICAL" | "TURNAROUND" | "ASSET_PLAY"`
  - `peg_ratio` : `float | None` — pe / (eps_growth_5y × 100), null si eps_growth_5y ≤ 0
  - `tenbagger_potential` : `bool` — FAST_GROWER avec PEG < 1.0
  - `score_croissance` : `int` (0-5)
  - `verdict` : `"EXCELLENT" | "BON" | "MOYEN" | "EVITER"`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`

#### Spécifications `fisher_scuttlebutt`
- Source de vérité : `.claude/skills/fisher-scuttlebutt/SKILL.md` + `references/`
- Input : `FisherInput(ticker, fisher_answers: list[FisherAnswer], contexte_qualitatif: str | None)`
  - `FisherAnswer(point: int, score: int, commentaire: str)` — 15 points cotés 0/1/2
- Output : `FisherOutput`
  - `fisher_score` : `int` (0-30)
  - `points_evalues` : `list[FisherPoint]` — exactement 15 éléments
  - `management_quality` : `"EXCEPTIONNEL" | "BON" | "ADEQUAT" | "MEDIOCRE"`
  - `verdict` : `"ACHAT_FORT" | "ACHAT" | "CONSERVER" | "EVITER"`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`
- Validation : `len(points_evalues) == 15`, `0 <= fisher_score <= 30`

#### Spécifications `klarman_margin_of_safety`
- Source de vérité : `.claude/skills/klarman-margin-of-safety/SKILL.md` + `references/`
- Input : `KlarmanInput(ticker, situation_type: str, klarman_ratios: KlarmanRatios)`
  - `KlarmanRatios(nav_per_share: float | None, price: float, liquidation_value: float | None, debt_equity: float | None, revenue_bn: float | None, catalyst: str | None)`
- Output : `KlarmanOutput`
  - `situation_type_qualifie` : `"NET_NET" | "ACTIFS_CACHES" | "DISTRESSED" | "SPECIAL_SITUATION" | "VALEUR_CLASSIQUE"`
  - `marge_securite_score` : `int` (0-10)
  - `preservation_capital_score` : `int` (0-10)
  - `discount_to_intrinsic` : `float | None`
  - `verdict` : `"OPPORTUNITE_FORTE" | "OPPORTUNITE_MODEREE" | "ATTENDRE" | "PASSER"`
  - `verdict_detail`, `recommandation_prochaine_etape`, `citations`

#### Intégration orchestrateur
- Ajouter `lynch_ratios: LynchRatios | None`, `fisher_input: FisherInput | None`, `klarman_input: KlarmanInput | None` dans `AnalyzeRequest`
- Étapes 9, 10, 11 dans `run_company_analysis` — pattern identique aux étapes 1-8
- Champs correspondants dans `AnalyzeResponse`

#### Critère de succès
```bash
curl -X POST localhost:8000/analyze \
  -d '{"ticker":"BNS","ratios":{...},"lynch_ratios":{"pe":11,"eps_growth_5y":0.05,...}}'
# → JSON avec "lynch": {"categorie": "STALWART", "peg_ratio": 2.2, ...}
```

---

### Sprint 15 — Skills Greenblatt + Damodaran + Marks + Pabrai ✅

**Objectif :** Compléter les 15 skills de l'architecture — 4 derniers skills (screening systématique, valorisation growth, cycles marché, position sizing).

#### Fichiers à créer
```
app/skills/tier2/greenblatt/__init__.py
app/skills/tier2/greenblatt/schemas.py
app/skills/tier2/greenblatt/skill.py
app/skills/tier2/greenblatt/prompts/system.md
app/skills/tier2/damodaran_narrative/__init__.py
app/skills/tier2/damodaran_narrative/schemas.py
app/skills/tier2/damodaran_narrative/skill.py
app/skills/tier2/damodaran_narrative/prompts/system.md
app/skills/tier2/marks_cycles/__init__.py
app/skills/tier2/marks_cycles/schemas.py
app/skills/tier2/marks_cycles/skill.py
app/skills/tier2/marks_cycles/prompts/system.md
app/skills/tier2/pabrai_dhandho/__init__.py
app/skills/tier2/pabrai_dhandho/schemas.py
app/skills/tier2/pabrai_dhandho/skill.py
app/skills/tier2/pabrai_dhandho/prompts/system.md
tests/test_greenblatt.py
tests/test_damodaran.py
tests/test_marks_cycles.py
tests/test_pabrai_dhandho.py
```

#### Spécifications `greenblatt_magic_formula`
- Source : `.claude/skills/greenblatt-magic-formula/SKILL.md`
- Input : `GreenblattRatios(ebit: float, enterprise_value: float, net_working_capital: float, net_fixed_assets: float, sector: str | None)`
- Output : `GreenblattOutput`
  - `roc` : `float` — EBIT / (NWC + NFA)
  - `earnings_yield` : `float` — EBIT / EV
  - `verdict` : `"TOP_DECILE" | "BON" | "MOYEN" | "EVITER"`
  - `situations_speciales` : `list[str]` — spinoffs, arbitrage, restructuring identifiés
  - `verdict_detail`, `citations`

#### Spécifications `damodaran_narrative`
- Source : `.claude/skills/damodaran-narrative-and-numbers/SKILL.md`
- Input : `DamodararInput(ticker, narrative_text: str, damodaran_ratios: DamodararRatios)`
  - `DamodararRatios(revenue_bn, revenue_growth_5y, net_margin, roic, tam_bn: float | None, market_share_pct: float | None, sector: str | None)`
- Output : `DamodararOutput`
  - `test_coherence` : `"POSSIBLE" | "PLAUSIBLE" | "PROBABLE" | "INCOHERENT"`
  - `erp_implied` : `float | None`
  - `narrative_strength` : `int` (0-10)
  - `divergences_detectees` : `list[str]`
  - `verdict` : `"NARRATIVE_FORTE" | "NARRATIVE_ACCEPTABLE" | "NARRATIVE_FAIBLE" | "NARRATIVE_INCOHERENTE"`
  - `verdict_detail`, `citations`

#### Spécifications `marks_cycles_risk`
- Source : `.claude/skills/marks-cycles-and-risk/SKILL.md`
- Input : `MarksInput(market_context: str, marks_ratios: MarksRatios)`
  - `MarksRatios(pe_market: float | None, vix: float | None, credit_spreads_bps: float | None, insider_net_buying: float | None, bullish_sentiment_pct: float | None)`
- Output : `MarksOutput`
  - `position_cycle` : `"PESSIMISME_EXCESSIF" | "PESSIMISME" | "NEUTRE" | "OPTIMISME" | "EUPHORIE"`
  - `pendule_score` : `int` (-5 à +5, négatif = opportunité contrariante)
  - `second_level_insight` : `str`
  - `recommandation_timing` : `"ACHETER_AGRESSIF" | "ACHETER_PRUDEMMENT" | "ATTENDRE" | "REDUIRE" | "VENDRE"`
  - `verdict_detail`, `citations`
- Validation : `pendule_score` in [-5, 5]

#### Spécifications `pabrai_dhandho`
- Source : `.claude/skills/pabrai-dhandho-and-cloning/SKILL.md`
- Input : `PabraiInput(ticker, pabrai_ratios: PabraiRatios, cloning_source: str | None)`
  - `PabraiRatios(price, intrinsic_value_low, intrinsic_value_high, downside_pct, upside_pct, debt_equity, fcf_yield, business_quality_score: int)`
- Output : `PabraiOutput`
  - `principes_dhandho` : `list[DhandhoPrincipe]` — exactement 9 (nom, satisfait: bool, commentaire)
  - `heads_i_win_score` : `int` (0-9)
  - `asymetrie` : `float` — upside / abs(downside)
  - `kelly_fractionnel` : `float | None` — Kelly / 4
  - `verdict` : `"DHANDHO_FORT" | "DHANDHO_MOYEN" | "PAS_DHANDHO"`
  - `verdict_detail`, `citations`
- Validation : `len(principes_dhandho) == 9`, `asymetrie >= 0`

#### Critère de succès
Tous les 15 skills de l'architecture opérationnels. POST /analyze avec le payload complet retourne les 15 sections.

---

### Sprint 17 — Screener multi-tickers + Cache Redis ✅

**Objectif :** `POST /screen` (analyse parallèle avec asyncio.gather + Semaphore) + cache Redis sur `POST /analyze`.

#### Fichiers créés
```
app/services/__init__.py
app/services/analysis_cache.py    # AnalysisCacheService — clé analysis:{ticker}:{workflow}:{hash}
app/services/screener.py          # ScreenerService — asyncio.gather + Semaphore + timeout
app/api/endpoints/screen.py       # POST /screen + DELETE /cache/{ticker}
tests/test_analysis_cache.py      # 8 tests (get/set/invalidate/TTL/orchestrateur)
tests/test_screener.py            # 12 tests (validation, tri, déduplication, endpoint)
```

#### Fichiers modifiés
```
app/orchestrator/core.py          # AnalyzeRequest.workflow + run_company_analysis(cache=) + cache store
app/api/main.py                   # screen router + AnalysisCacheService + ScreenerService + version 2.0.0
tests/conftest.py                 # mocks analysis_cache + screener dans fixture client
tests/test_api.py                 # version 1.0.0 → 2.0.0
tests/test_orchestrator.py        # workflow "company_analysis" → "value_graham" (défaut Sprint 17)
```

#### Note architecture
Sprint 16 (WorkflowRouter + WebSocket) a été sauté — les fichiers `app/orchestrator/router.py`
et `app/api/endpoints/ws_metrics.py` ne sont pas encore implémentés. Le champ `workflow`
dans `AnalyzeRequest` prépare l'intégration future du WorkflowRouter sans le bloquer.

#### Critère de succès
```bash
pytest tests/test_screener.py tests/test_analysis_cache.py -v  # 20 tests verts
pytest tests/ -v -q                                             # 733 passed, 1 xfail
```

---

### Sprint 18 — Observabilité avancée ✅

**Objectif :** Dashboard Langfuse structuré : traces par skill avec coût et latence, alertes coût > seuil, endpoint `/telemetry` pour visualiser les métriques clés.

#### Fichiers à créer
```
app/services/observability.py        # ObservabilityService — traces Langfuse + compteurs Redis
app/api/endpoints/telemetry.py       # GET /telemetry/summary, /costs, /cache, /latency
tests/test_observability.py          # ~10 tests ObservabilityService
tests/test_telemetry.py              # ~8 tests endpoints /telemetry
```

#### Fichiers à modifier
```
app/orchestrator/core.py             # record_skill_execution après chaque skill (asyncio.create_task)
app/api/main.py                      # Inclure telemetry router + injecter ObservabilityService
```

#### Spécifications — `ObservabilityService`

```python
@dataclass
class SkillTrace:
    skill_id: str
    ticker: str
    cost_usd: float
    latency_ms: int
    cache_hit: bool
    tokens_input: int
    tokens_output: int
    created_at: datetime

class ObservabilityService:
    def __init__(self, langfuse_client: Langfuse | None, redis_client: Redis) -> None: ...

    async def record_skill_execution(self, trace: SkillTrace) -> None:
        # 1. Si Langfuse dispo → span avec metadata structurée (cost_usd, latency_ms, cache_hit)
        # 2. Redis INCRBYFLOAT obs:cost:{YYYY-MM-DD} cost_usd
        # 3. Redis INCR obs:cache:hits si cache_hit, sinon obs:cache:misses
        # 4. Redis ZADD skill_traces:{skill_id} score=timestamp value=latency_ms

    async def get_cost_summary(self, days: int = 30) -> CostSummary:
        """Coût total + breakdown par jour depuis Redis obs:cost:{date}."""

    async def get_cache_stats(self) -> CacheStats:
        """hits / (hits + misses) depuis Redis."""

    async def get_latency_p95(self, skill_id: str | None = None) -> float | None:
        """P95 latence via ZRANGE sur sorted set (skill_id précis ou tous les skills)."""

    async def check_cost_alert(self, daily_threshold_usd: float = 1.0) -> bool:
        """Coût du jour > seuil ? (lecture obs:cost:{today})"""
```

#### Spécifications — endpoints `/telemetry`

```python
GET /telemetry/summary?days=30
# → TelemetrySummary(cost_total_usd, cache_hit_ratio, analyses_count, latency_p95_ms, top_tickers)

GET /telemetry/costs?days=30
# → list[DailyCost(date, cost_usd)]

GET /telemetry/cache
# → CacheStats(hits, misses, hit_ratio, keys_count)

GET /telemetry/latency?skill_id=graham_analysis
# → LatencyStats(skill_id, p50_ms, p95_ms, p99_ms, sample_count)
```

- Endpoints **exemptés d'auth** (lecture seule, monitoring interne)
- `ObservabilityService` injecté via `app.state.observability` dans le lifespan
- Si Langfuse non configuré (`LANGFUSE_SECRET_KEY` absent), le service tourne en mode Redis-only sans erreur

#### Intégration orchestrateur

```python
# Dans run_company_analysis, après chaque skill exécuté avec succès :
asyncio.create_task(
    observability.record_skill_execution(SkillTrace(
        skill_id="graham_analysis",
        ticker=request.ticker,
        cost_usd=output.cost_usd,
        latency_ms=elapsed_ms,
        cache_hit=was_cached,
        tokens_input=output.usage.input_tokens,
        tokens_output=output.usage.output_tokens,
        created_at=datetime.utcnow(),
    ))
)
# asyncio.create_task → non-bloquant, ne ralentit pas l'analyse
```

#### Tests à écrire

**`tests/test_observability.py`**
```python
test_record_sans_langfuse_ok()               # langfuse=None → pas d'erreur
test_record_avec_langfuse_mock()             # span créé avec bons metadata
test_get_cost_summary_vide()                 # 0 enregistrements → cost_total=0.0
test_get_cost_summary_cumul_correct()        # 3 appels → somme exacte
test_get_cache_stats_hit_ratio()             # 3 hits + 1 miss → 0.75
test_get_latency_p95_calcul()               # 100 valeurs → p95 dans range attendu
test_check_cost_alert_depasse()              # coût > seuil → True
test_check_cost_alert_ok()                   # coût < seuil → False
test_record_cache_hit_incremente_hits()      # cache_hit=True → obs:cache:hits +1
test_record_cache_miss_incremente_misses()   # cache_hit=False → obs:cache:misses +1
```

**`tests/test_telemetry.py`**
```python
test_telemetry_summary_200()                 # GET /telemetry/summary → 200 + TelemetrySummary
test_telemetry_costs_200()                   # GET /telemetry/costs?days=7 → 200 + list[DailyCost]
test_telemetry_cache_200()                   # GET /telemetry/cache → 200 + CacheStats
test_telemetry_latency_200()                 # GET /telemetry/latency → 200 + LatencyStats
test_telemetry_latency_skill_filtre()        # ?skill_id=graham → résultat filtré
test_telemetry_sans_auth_200()              # endpoints /telemetry/* exemptés d'auth
test_telemetry_hit_ratio_entre_0_et_1()     # 0 <= hit_ratio <= 1.0
test_telemetry_cost_total_positif()          # cost_total_usd >= 0
```

#### Critère de succès
```bash
pytest tests/test_observability.py tests/test_telemetry.py -v  # tous verts
pytest tests/ -v -q                                             # 0 failures (751+ passed)

curl localhost:8000/telemetry/summary?days=7
# → {"cost_total_usd": 0.42, "cache_hit_ratio": 0.73, "analyses_count": 18, "latency_p95_ms": 3200}

curl localhost:8000/telemetry/cache
# → {"hits": 54, "misses": 20, "hit_ratio": 0.73, "keys_count": 12}
```

---

---

### Sprint 19 — Tests de charge ✅

**Objectif :** Valider la capacité de l'API sous charge réaliste — mesurer le débit de `/screen` et `/analyze` à 10/50 req/min, identifier les goulots d'étranglement avant tout déploiement.

#### Fichiers à créer
```
tests/load/locustfile.py             # Scénarios Locust : /analyze, /screen, /telemetry
tests/load/k6_basic.js               # Scénario k6 pour /analyze seul (alternative)
tests/load/README.md                 # Instructions d'exécution des tests de charge
```

#### Spécifications
- **Outil principal :** `locust` (Python, s'intègre bien avec FastAPI)
- **Scénarios :**
  - `AnalyzeUser` : POST /analyze avec ratios Graham (poids 70 %)
  - `ScreenUser` : POST /screen avec 5 tickers (poids 20 %)
  - `TelemetryUser` : GET /telemetry/summary (poids 10 %)
- **Niveaux testés :** 10, 25, 50 utilisateurs concurrents
- **Durée :** 2 minutes par palier
- **Métriques collectées :** p50, p95, p99 latence, débit (req/s), taux d'erreur
- **Critère de succès :** p95 < 5s à 10 utilisateurs avec cache Redis activé

#### Variables d'environnement pour les tests de charge
```bash
LOCUST_HOST=http://localhost:8000
LOCUST_USERS=50
LOCUST_SPAWN_RATE=5
LOCUST_RUN_TIME=2m
```

#### Tests à écrire
```python
# locustfile.py
class AnalyzeUser(HttpUser): ...      # POST /analyze avec payload Graham complet
class ScreenUser(HttpUser): ...       # POST /screen avec 5 tickers + ratios_map
class TelemetryUser(HttpUser): ...    # GET /telemetry/summary polling
```

#### Critère de succès
```bash
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 -u 10 -r 2 --run-time 2m
# → p95 < 5000ms, taux erreur < 1%

locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 -u 50 -r 5 --run-time 2m
# → p95 < 10000ms, taux erreur < 5%
```

---

### Sprint 20 — Rapport PDF automatique ✅

**Objectif :** Générer un PDF structuré depuis `AnalyzeResponse` via `reportlab`.
Exposer `POST /report` qui déclenche une analyse et retourne un PDF téléchargeable.

#### Fichiers à créer
```
app/services/report.py               # ReportService — génère PDF depuis AnalyzeResponse
app/api/endpoints/report.py          # POST /report, GET /report/{analysis_id}
tests/test_report.py                 # 10 tests (service + endpoint)
```

#### Fichiers à modifier
```
app/api/main.py                      # Inclure report_router
requirements.txt                     # Ajouter reportlab>=4.0.0
README.md                            # Ajouter section "Rapports PDF"
```

#### Critère de succès
```bash
pytest tests/test_report.py -v  # 10 tests verts

curl -X POST localhost:8000/report \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS","ratios":{"pe":11.0,"pb":1.3,"current_ratio":null,
       "debt_equity":0.45,"eps_growth_10y":0.27,"price":80.0,"book_value":61.5}}' \
  --output BNS-rapport.pdf
# → BNS-rapport.pdf créé, lisible dans un lecteur PDF
```

---

### Sprint 21 — Workflows alternatifs + WebSocket dashboard ✅

**Objectif :** Implémenter le `WorkflowRouter` avec 5 workflows spécialisés + un dashboard WebSocket temps réel.
Ce sprint intègre le contenu prévu initialement en Sprint 16 (précédemment sauté).

#### Fichiers à créer
```
app/orchestrator/router.py           # WorkflowRouter — dispatch vers la bonne séquence de skills
app/api/endpoints/ws_metrics.py      # WebSocket /ws/metrics (Redis pub/sub)
tests/test_workflow_router.py        # Tests WorkflowRouter + workflows alternatifs
```

#### Fichiers à modifier
```
app/orchestrator/core.py             # Intégrer WorkflowRouter dans run_company_analysis
app/api/main.py                      # Inclure ws_metrics router, version 2.1.0
```

#### 5 workflows (section 3.3 de l'architecture)

| Workflow | Séquence de skills |
|----------|--------------------|
| `value_graham` | graham → earnings → valuation → thesis → tax *(existant, défaut)* |
| `compounder_buffett` | graham → earnings → dorsey → buffett → fisher → valuation → thesis → munger → tax |
| `fast_grower_lynch` | lynch → damodaran → valuation → thesis → munger → tax |
| `special_situation` | graham → klarman → greenblatt → thesis → tax |
| `distressed_pabrai` | pabrai → klarman → earnings → thesis → tax |

#### Spécifications `WorkflowRouter`
- `AnalyzeRequest` : le champ `workflow: str = "value_graham"` est **déjà présent** — ne pas le re-créer
- `WorkflowRouter.route(workflow: str) -> list[SkillStep]` : retourne la séquence ordonnée
- `SkillStep(skill_id: str, optional: bool = False)` — les skills sans ratios fournis sont sautés (pas d'erreur)
- `run_company_analysis` utilise `WorkflowRouter.route(workflow)` pour déterminer les étapes à exécuter

#### WebSocket `/ws/metrics`
- Connexion : `GET /ws/metrics` → WebSocket upgrade
- Push JSON toutes les 5 secondes :
  ```json
  {
    "jobs_en_cours": 2,
    "jobs_echoues_1h": 0,
    "cout_total_1h_usd": 0.042,
    "cache_hit_ratio": 0.73,
    "analyses_24h": 15,
    "timestamp": "2026-05-09T14:32:00Z"
  }
  ```
- Source : Redis `KEYS job:*:status` + compteurs observabilité existants (`obs:cost:*`, `obs:cache:*`)
- Fermeture propre si client déconnecté (`WebSocketDisconnect`)
- Pas d'auth requise (lecture seule, monitoring interne)

#### Version
- Passer `_VERSION = "2.1.0"` dans `app/api/main.py`

#### Tests à écrire (`tests/test_workflow_router.py`)
```python
test_workflow_value_graham_steps()         # défaut → 5 steps attendus
test_workflow_compounder_buffett_steps()   # 9 steps
test_workflow_fast_grower_lynch_steps()    # 6 steps
test_workflow_special_situation_steps()    # 4 steps
test_workflow_distressed_pabrai_steps()    # 5 steps
test_workflow_inconnu_raise_value_error()  # "foo" → ValueError
test_orchestrator_workflow_non_defaut()    # fast_grower_lynch → lynch présent, graham absent
test_ws_metrics_connect_disconnect()       # mock WebSocket → connect + data + disconnect propre
test_ws_metrics_payload_structure()        # JSON valide avec tous les champs attendus
```

#### Fichiers créés
```
app/orchestrator/router.py           # WorkflowRouter + WORKFLOWS dict (5 workflows)
app/api/endpoints/ws_metrics.py      # WebSocket /ws/metrics — push JSON toutes les 5s
tests/test_workflow_router.py        # 9 tests (7 router + 2 WebSocket)
```

#### Fichiers modifiés
```
app/orchestrator/core.py             # WorkflowRouter intégré, graham/ratios optionnels, _persist corrigé
app/api/main.py                      # ws_metrics_router inclus, version 2.1.0
app/middleware/auth.py               # /ws ajouté à EXEMPT_PREFIXES
```

#### Critère de succès
```bash
# Workflow Lynch
curl -X POST localhost:8000/analyze \
  -d '{"ticker":"NVDA","workflow":"fast_grower_lynch","lynch_ratios":{...},...}'
# → JSON avec sections lynch + damodaran + valuation + thesis (pas de graham)

# WebSocket
wscat -c ws://localhost:8000/ws/metrics
# → Push JSON toutes les 5s avec jobs_en_cours, cout_total_1h_usd, cache_hit_ratio

pytest tests/test_workflow_router.py -v   # 9 tests verts
pytest tests/ -v -q                        # 776+ passed, 1 xfail
```

---

### Sprint 22 — Interface web professionnelle ✅

**Objectif :** Dashboard React professionnel dans `frontend/` pour accéder au copilote sans CLI.

#### Fichiers créés
```
frontend/package.json                        # React 18, Vite 5, TS strict, shadcn/ui, Tanstack Query v5, React Router v6
frontend/vite.config.ts                      # Proxy API → localhost:8000, WebSocket ws:// proxy, Vitest jsdom
frontend/tsconfig.json                       # strict: true, jsx: react-jsx, types: [vitest/globals, jest-dom]
frontend/index.html                          # Entrée Vite
frontend/src/vite-env.d.ts                  # /// <reference types="vite/client" />
frontend/src/setupTests.ts                   # Polyfills Radix UI (hasPointerCapture, scrollIntoView)
frontend/src/types/index.ts                  # GrahamRatios, AnalyzeRequest/Response, ScreenEntry, MetricsPayload, WORKFLOWS
frontend/src/api/client.ts                   # fetch wrapper + ApiError (status, message, name)
frontend/src/api/analyze.ts                  # postAnalyze, postScreen, getHistory, postReport, getHealthz
frontend/src/api/ws.ts                       # useMetrics() — WebSocket /ws/metrics + auto-reconnect 3s
frontend/src/App.tsx                         # BrowserRouter + NavLink (/, /screener, /historique, /dashboard)
frontend/src/components/ui/button.tsx        # cva variants: default, destructive, outline, secondary, ghost, link
frontend/src/components/ui/badge.tsx         # cva variants: default, secondary, destructive, success, warning, danger
frontend/src/components/ui/select.tsx        # Radix @radix-ui/react-select wrapper stylé
frontend/src/components/ui/card.tsx          # Card, CardHeader, CardTitle, CardContent
frontend/src/components/ui/input.tsx         # Input stylé
frontend/src/components/ui/table.tsx         # Table, Thead, Tbody, Tr, Th, Td
frontend/src/components/WorkflowSelector.tsx # Dropdown 5 workflows avec description
frontend/src/components/AnalyzeForm.tsx      # Formulaire ticker + workflow + 10 ratios Graham + options
frontend/src/components/AnalysisResult.tsx   # Affichage 15 sections skills + score + verdict + coût
frontend/src/components/ScreenerTable.tsx    # Tableau trié par score, badges verdict colorés, badge cache
frontend/src/components/HistoryTable.tsx     # Historique paginé, bouton PDF par ligne
frontend/src/components/MetricsDashboard.tsx # 5 cards métriques temps réel via useMetrics
frontend/src/pages/AnalyzePage.tsx           # useMutation postAnalyze + PDF blob download
frontend/src/pages/ScreenerPage.tsx          # Textarea multi-tickers + WorkflowSelector + ScreenerTable
frontend/src/pages/HistoryPage.tsx           # useQuery initial + useMutation load-more cursor pagination
frontend/src/pages/DashboardPage.tsx         # Wrapper MetricsDashboard
frontend/src/__tests__/AnalyzeForm.test.tsx  # 6 tests (submit, uppercase ticker, ratios Graham, loading, munger)
frontend/src/__tests__/ScreenerTable.test.tsx # 6 tests (tickers, tri score, EXEMPLAIRE, REJETER, cache, tri ticker)
frontend/src/__tests__/WorkflowSelector.test.tsx # 5 tests (combobox, 5 workflows, valeurs, label/desc, aria-label)
frontend/src/__tests__/useMetrics.test.ts    # 5 tests (init, onopen, message, JSON invalide, onclose)
frontend/src/__tests__/api.test.ts           # 6 tests (BASE_URL, ApiError, fetch URL, headers, ApiError 422)
```

#### Résultat des tests
```bash
cd frontend && npm test
# ✓ api.test.ts             6 tests
# ✓ ScreenerTable.test.tsx  6 tests
# ✓ WorkflowSelector.test.tsx 5 tests
# ✓ useMetrics.test.ts      5 tests
# ✓ AnalyzeForm.test.tsx    6 tests
# → 5 fichiers, 28 tests — tous verts
```

#### Build
```bash
cd frontend && npm run build
# → vite v5.4.21 ✓ built in ~2s, dist/ généré sans erreurs TypeScript
```

#### Critère de succès
```bash
cd frontend && npm run dev   # http://localhost:5173 accessible
cd frontend && npm run build # dist/ sans erreur TS
cd frontend && npm test      # 28 tests verts
```

---

### Sprint 23 — Watchlist persistante ✅

**Objectif :** Sauvegarder une liste de tickers + workflow + alertes → re-analyse hebdomadaire via Celery beat.

#### Fichiers créés
```
app/models/__init__.py
app/models/watchlist.py                  # WatchlistEntry, WatchlistCreate (Pydantic)
app/services/watchlist_service.py        # WatchlistService — CRUD PostgreSQL
app/api/endpoints/watchlist.py           # POST/GET/DELETE /watchlist + POST /{id}/analyze
tests/test_watchlist.py                  # 7 tests verts
```

#### Fichiers modifiés
```
infra/postgres/init.sql                  # Table watchlist ajoutée
app/workers/tasks.py                     # run_watchlist_analysis + _execute_watchlist_analysis
app/workers/celery_app.py                # beat_schedule — dimanche 07h00 UTC
app/api/main.py                          # watchlist_router + WatchlistService + version 2.3.0
```

---

### Sprint 24 — Alertes prix ✅

**Objectif :** Surveiller le prix courant de chaque entrée watchlist et déclencher une re-analyse si l'écart vs `valeur_intrinseque_ajustee` dépasse ±10 %.

#### Fichiers créés
```
app/services/price_alert_service.py  # PriceAlertService.check_price_alerts()
tests/test_price_alert.py            # 7 tests verts
```

#### Fichiers modifiés
```
app/models/watchlist.py              # +3 champs : last_intrinsic_value, last_price_checked, price_alert_threshold_pct
infra/postgres/init.sql              # colonnes Sprint 24 + migration ALTER TABLE commentée
app/services/watchlist_service.py    # requêtes mises à jour, update_last_analyzed(intrinsic_value), update_price_checked
app/workers/tasks.py                 # _execute_watchlist_analysis → last_intrinsic_value ; _execute_price_alert_check + run_price_alert_check
app/workers/celery_app.py            # beat quotidien run_price_alert_check (08h00 UTC)
app/api/endpoints/watchlist.py       # GET /watchlist/{id}/price-status
```

#### Critère de succès
```bash
pytest tests/test_price_alert.py -v  # 7 tests verts
curl localhost:8000/watchlist/{id}/price-status
# → {"ticker": "BNS", "current_price": 72.50, "intrinsic_value": 80.00, "ecart_pct": -0.094, "alerte": false}
```

---

### Sprint 25 — Export hebdomadaire automatique ✅

**Objectif :** Générer chaque dimanche un rapport PDF synthétisant les positions de la watchlist et l'envoyer par email.

#### Fichiers créés
```
app/services/email_service.py        # EmailService — SMTP stdlib ou SendGrid (import conditionnel)
tests/test_email_service.py          # 4 tests (smtp_ok, sans_config, pdf_attache, sendgrid_priorite)
tests/test_weekly_report.py          # 3 tests (genere_pdf, envoie_email, watchlist_vide)
```

#### Fichiers modifiés
```
app/services/report.py               # +generate_watchlist_summary_pdf(entries) — tableau récapitulatif
app/workers/tasks.py                 # +_execute_weekly_watchlist_report + run_weekly_watchlist_report
app/workers/celery_app.py            # beat_schedule — dimanche 09h00 UTC
```

#### Version milestone : 2.5.0

---

### Sprint 26 — Déploiement homelab ✅

**Objectif :** Passer à un service accessible hors du réseau local avec TLS automatique, backup PostgreSQL journalier, et monitoring Uptime Kuma.

#### Fichiers créés
```
infra/caddy/Caddyfile                        # Reverse proxy Caddy — TLS automatique Let's Encrypt
infra/backup/backup_postgres.sh              # pg_dump + rotation 7 jours
infra/backup/README.md                       # Instructions cron système
infra/monitoring/docker-compose.monitoring.yml # Uptime Kuma service séparé
docker-compose.prod.yml                      # Override production (Caddy + ports internes)
tests/test_healthz_prod.py                   # 2 tests healthz (status ok + version)
```

#### Décisions d'architecture
- **Reverse proxy** : Caddy 2 (Alpine) — TLS Let's Encrypt automatique via variables `{env.DOMAIN}` et `{env.CADDY_EMAIL}`
- **Port isolation** : `copilote:8000` non exposé hors du réseau Docker en production
- **Backup** : cron système (pas Celery), rotation 7 jours via `find -mtime +7`
- **Monitoring** : Uptime Kuma dans compose séparé (`docker-compose.monitoring.yml`) — surveille `/healthz` toutes les 60s sur `:3001`

#### Nouvelles variables d'environnement (`.env`)
```
DOMAIN=copilote.example.com
CADDY_EMAIL=yves@example.com
BACKUP_DIR=/backups
```

#### Critère de succès
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
curl https://{DOMAIN}/healthz  # → {"status": "ok", "version": "2.5.0"}
bash infra/backup/backup_postgres.sh  # → copilote_YYYYMMDD_HHMMSS.sql.gz créé
```

---

### Sprint 27 — Watchlist dans le frontend ✅

**Objectif :** Exposer la watchlist persistante (backend Sprint 23-24) dans une page React dédiée.

#### Fichiers créés
```
frontend/src/api/watchlist.ts                  # getWatchlist, addToWatchlist, removeFromWatchlist, triggerWatchlistAnalysis, getWatchlistPriceStatus
frontend/src/pages/WatchlistPage.tsx           # Page principale — formulaire ajout + tableau + mutations
frontend/src/components/WatchlistTable.tsx     # Tableau shadcn/ui + badges Alerte/OK calculés depuis entry
frontend/src/__tests__/WatchlistPage.test.tsx  # 6 tests Vitest verts
```

#### Fichiers modifiés
```
frontend/src/types/index.ts    # +WatchlistEntry, +WatchlistCreate, +PriceStatus
frontend/src/App.tsx           # route /watchlist + NavLink "Watchlist"
frontend/src/api/client.ts     # +requestEmpty() pour DELETE 204 No Content
```

#### Décisions
- `WatchlistEntry.id` est `string` (UUID) côté frontend — backend renvoie des UUIDs
- Badge Alerte calculé localement depuis `last_price_checked` / `last_intrinsic_value` (pas d'appel /price-status par ligne)
- `requestEmpty` ajouté à `apiClient` pour gérer les réponses 204 sans body JSON

#### Critère de succès
```bash
cd frontend && npm test  # → 34 tests verts (28 existants + 6 WatchlistPage)
cd frontend && npm run build  # → dist/ sans erreur TS
```

---

### Sprint 16 — Workflows alternatifs + WebSocket dashboard

> **Note :** Ce sprint a été sauté lors de la séquence originale et est désormais implémenté comme **Sprint 21**.

---

### Sprint 29 — Fix WorkflowRouter ✅

**Objectif :** Corriger les 24 tests en échec dans `tests/test_workflow_router.py`.

**Cause :** Lors du Sprint 21, `dorsey_moat` et `buffett_quality` avaient été exclus du
workflow `value_graham`, alors que les tests supposaient leur présence.

**Correction apportée :** Ajout de `dorsey_moat` et `buffett_quality` dans la séquence
`value_graham` du `WorkflowRouter`. Rétrocompatibilité préservée — 806 tests verts.

---

### Sprint 30 — Tests E2E Frontend → Backend (Claude mocké) ✅

**Objectif :** Couvrir toutes les fonctionnalités par des tests end-to-end traversant
le vrai frontend React jusqu'au vrai backend FastAPI, en mockant uniquement
`call_claude_with_retry`. Aucun token Anthropic réel consommé.

#### Fichiers à créer
```
tests/e2e/__init__.py
tests/e2e/conftest.py                 # uvicorn thread + mock Claude + Playwright browser
tests/e2e/fixtures/__init__.py
tests/e2e/fixtures/claude_stubs.py   # JSON stubs par skill (déterministes)
tests/e2e/test_e2e_auth.py           # login / logout / redirect (4 tests)
tests/e2e/test_e2e_analyze.py        # analyse Graham complète + bug fixes (5 tests)
tests/e2e/test_e2e_screener.py       # screener multi-tickers (3 tests)
tests/e2e/test_e2e_watchlist.py      # CRUD watchlist (4 tests)
```

#### Fichiers à modifier
```
requirements-dev.txt          # +playwright>=1.44, +pytest-playwright>=0.5
frontend/src/components/      # +data-testid sur AnalysisResult, ScreenerTable, WatchlistTable
frontend/src/pages/AnalyzePage.tsx   # bug fix : setResult(null) avant mutation
frontend/src/components/AnalyzeForm.tsx  # bug fix : earnings_ratios vide → sous-formulaire ou désactivation
```

#### Architecture
```
Playwright (Chromium headless)
  │  HTTP via Vite proxy (port 5173 → 8000)
  ▼
FastAPI (port 8000, thread uvicorn, Claude patché)
  │  call_claude_with_retry() → claude_stubs.py (0 token réel)
  ▼
fixtures déterministes JSON
```

#### Scénarios couverts
| Fichier | Tests | Fonctionnalité |
|---------|-------|---------------|
| `test_e2e_auth.py` | 4 | Redirect /login, login, bouton désactivé, logout |
| `test_e2e_analyze.py` | 5 | Analyse BNS, reset ticker, workflow Lynch, earnings 422, ratios invalides |
| `test_e2e_screener.py` | 3 | 3 tickers, badges, majuscules |
| `test_e2e_watchlist.py` | 4 | Ajout, suppression, doublon refusé, liste vide |

#### Critère de succès
```bash
# Vite dev server actif sur port 5173
cd frontend && npm run dev &

API_KEY=test-key pytest tests/e2e/ -v -m e2e
# → 16 tests verts, 0 appel api.anthropic.com

pytest tests/ -v -q --ignore=tests/e2e
# → 806+ passed, 1 xfail, 0 failures
```

---

### Sprint 31 — CI/CD GitHub Actions ✅

**Objectif :** Pipeline automatisé qui exécute la suite de tests complète à chaque push et pull request.
Aucun service Docker requis — PostgreSQL, Redis et Claude sont tous mockés.

#### Fichiers à créer
```
.github/workflows/ci.yml    # 2 jobs en parallèle : backend + frontend
```

#### Fichiers à modifier
```
README.md                   # Badge CI en haut de page
```

#### Spécifications `.github/workflows/ci.yml`

2 jobs indépendants (parallèles) :

| Job | Environnement | Commande |
|-----|--------------|----------|
| `backend` | ubuntu-latest, Python 3.11 | `pytest tests/ --ignore=tests/e2e -q --tb=short` |
| `frontend` | ubuntu-latest, Node 20 | `cd frontend && npm ci && npm test` |

Variables d'environnement (aucun secret GitHub requis) :
```
ANTHROPIC_API_KEY: sk-ant-ci-dummy-key   # factice — tests mockent Claude
API_KEY: ci-test-key                      # factice — tests mockent auth
DATABASE_URL: postgresql://unused:5432/unused
REDIS_URL: redis://localhost:6379/0
QDRANT_URL: http://localhost:6333
```

#### Critère de succès
```bash
# Push sur master → GitHub Actions
# → job:backend : 806+ passed, 1 xfail, 0 failures
# → job:frontend : 39 passed
# → Badge CI vert dans README.md
```

---

### Sprint 32 — Extraction auto Yahoo Finance (frontend) ✅

**Objectif :** Bouton "Auto-fill" sur `AnalyzeForm` qui appelle `GET /extract?ticker=BNS`
et pré-remplit les 10 champs Graham — élimine la saisie manuelle des ratios.

#### Fichiers à créer
```
(aucun — uniquement des modifications)
```

#### Fichiers à modifier
```
frontend/src/api/analyze.ts               # +getExtract(ticker: string) → GrahamRatios
frontend/src/components/AnalyzeForm.tsx   # bouton "Auto-fill" + loading + erreur
frontend/src/__tests__/AnalyzeForm.test.tsx  # 3 nouveaux tests (bouton, pré-remplissage, erreur 404)
```

#### Spécifications

- Bouton "Auto-fill" à côté du champ ticker (désactivé si ticker vide)
- Au clic : `GET /extract?ticker={ticker}` (endpoint déjà implémenté en Sprint 8)
- Si 200 : pré-remplit les champs `pe`, `pb`, `price`, `book_value`, `eps_ttm`, `revenue_bn`,
  `debt_equity`, `eps_growth_10y`, `dividend_years` — `current_ratio` peut être `null`
- Si 404 : toast/message "Ticker introuvable — vérifiez le symbole"
- Pendant la requête : bouton désactivé avec spinner (état `loading`)
- Les valeurs pré-remplies restent éditables

#### Tests à ajouter (`frontend/src/__tests__/AnalyzeForm.test.tsx`)
```tsx
test_autofill_button_renders()          // bouton "Auto-fill" visible dans le formulaire
test_autofill_prefills_ratios()         // mock GET /extract → champs pré-remplis correctement
test_autofill_error_404_affiche_msg()   // GET /extract 404 → message d'erreur visible
```

#### Critère de succès
```bash
cd frontend && npm test
# → 42 tests verts (39 existants + 3 nouveaux)

cd frontend && npm run build
# → dist/ sans erreur TypeScript
```

---

### Sprint 33 — Qualité bénéfices fonctionnelle ✅

**Objectif :** Activer la checkbox "Qualité bénéfices" dans `AnalyzeForm` : Auto-fill alimente `EarningsQualityRatios` depuis `GET /extract` (états financiers Yahoo Finance), checkbox active uniquement si les données sont disponibles.

#### Fichiers modifiés
```
app/skills/tier1/yahoo_finance.py          # +_fetch_earnings_data() +extract_earnings_quality() → EarningsQualityRatios | None
app/api/endpoints/extract.py               # ExtractResponse (graham + earnings_quality) — breaking change GET /extract
frontend/src/types/index.ts                # +EarningsQualityRatios +ExtractResponse ; earnings_ratios typé
frontend/src/api/analyze.ts                # getExtract() → Promise<ExtractResponse>
frontend/src/components/AnalyzeForm.tsx    # earningsRatios state, checkbox activée post-Auto-fill, payload earnings_ratios
requirements.txt                           # +pandas>=2.0.0
```

#### Tests ajoutés
```
tests/test_yahoo_finance.py                # +TestYahooFinanceExtractEarningsQuality (5 tests) + 2 tests ExtractEndpoint mis à jour
frontend/src/__tests__/AnalyzeForm.test.tsx # +3 tests Sprint 33 (checkbox désactivée, activation, payload)
```

#### Résultats
```bash
pytest tests/test_yahoo_finance.py -v   # 22 passed
cd frontend && npm test                  # 45 passed (42 existants + 3 nouveaux)
```

#### Logique UX
- Checkbox "Qualité bénéfices" désactivée par défaut (`disabled`)
- Après Auto-fill réussi avec `earnings_quality != null` → checkbox active + badge "✓ chargé (Yahoo Finance)"
- Si Yahoo Finance ne retourne pas les états financiers détaillés → checkbox reste désactivée, message "(Auto-fill requis)"
- `earnings_ratios` inclus dans `POST /analyze` uniquement si checkbox cochée et données disponibles

#### Critère de succès
```bash
# Auto-fill BNS → checkbox active → analyse avec earnings_quality
curl GET /extract?ticker=BNS
# → {"graham": {...}, "earnings_quality": {"sales_t": 38e9, ...} ou null}

curl POST /analyze -d '{"ticker":"BNS","ratios":{...},"earnings_ratios":{...}}'
# → JSON avec "earnings_quality": {"verdict": "AUCUN_SIGNAL|ATTENTION|...", ...}
```

---

### Sprint 34 — Tests E2E Sprint 33 ✅

**Objectif :** Couvrir le flux Sprint 33 (Auto-fill + checkbox Qualité bénéfices → analyse) par des tests Playwright.

#### Fichiers créés
```
tests/e2e/test_e2e_sprint33.py    # 3 tests E2E (autofill champs, checkbox active, analyse complète)
```

#### Fichiers modifiés
```
tests/e2e/conftest.py             # _make_yahoo_mock() : +extract_earnings_quality mocqué
```

#### Tests ajoutés
- `test_autofill_remplit_champs_graham` — bouton désactivé sans ticker, Auto-fill → P/E=11, P/B=1.3
- `test_autofill_active_checkbox_earnings` — après Auto-fill, checkbox activée + badge "✓ chargé"
- `test_autofill_earnings_inclus_dans_analyse` — Auto-fill + cocher earnings + Analyser → résultat BNS

#### Résultats
```bash
API_KEY=test-key pytest tests/e2e/test_e2e_sprint33.py -v -m e2e
# → 3 tests verts, 0 appel api.anthropic.com
pytest tests/e2e/ -v -m e2e   # → 19 tests verts (16 existants + 3 nouveaux)
```

---

### Sprint 35 — SSE Streaming ✅

**Objectif :** Afficher chaque skill au fur et à mesure via Server-Sent Events — éliminer les 15-30s d'écran blanc lors d'une analyse multi-skills.

#### Fichiers créés
```
app/api/endpoints/analyze_stream.py      # POST /analyze-stream — StreamingResponse SSE
frontend/src/components/StreamingProgress.tsx  # Composant skill-par-skill (active/done/verdict)
frontend/src/__tests__/AnalyzePage.test.tsx    # 5 tests Vitest streaming (form, progress, résultat, erreur, payload)
tests/test_analyze_stream.py             # 8 tests d'intégration SSE
```

#### Fichiers modifiés
```
app/orchestrator/core.py       # +stream_company_analysis() async generator (skill_start/skill_result/complete/cached/error)
app/api/main.py                # +analyze_stream_router, version 3.0.0
frontend/src/types/index.ts    # +SSEEvent discriminated union (skill_start, skill_result, complete, error, cached)
frontend/src/api/analyze.ts    # +streamAnalyze() — fetch POST + ReadableStream + SSE parsing manuel
frontend/src/pages/AnalyzePage.tsx  # Refactorisé : for-await SSE + partialResult + activeSkill + completedSkills
```

#### Architecture SSE
- **Pourquoi POST et non EventSource :** `EventSource` ne supporte que GET ; le payload JSON + Bearer token impose `fetch()` + `ReadableStream` manuel
- **Parsing SSE** : buffer accumulé, split `\n`, tracking `event:` et `data:` cross-chunk, `currentEventType` réinitialisé après chaque data
- **Events émis** : `skill_start` → `skill_result` (×N) → `complete` ; `cached` si cache hit ; `error` si exception dans le générateur
- **State React** : `isStreaming`, `partialResult`, `activeSkill`, `completedSkills` mis à jour event-par-event

#### Tests
```python
# Backend (8 tests — tests/test_analyze_stream.py)
test_stream_content_type_sse()               # Content-Type: text/event-stream
test_stream_contient_skill_start()           # event skill_start présent
test_stream_skill_start_contient_skill_id()  # skill_id == "graham_analysis"
test_stream_skill_result_contient_result()   # skill_id + result présents
test_stream_complete_contient_analyze_response()  # analysis_id, ticker, cost_usd
test_stream_ordre_events()                   # start < result < complete (ordre garanti)
test_stream_cache_hit_retourne_cached()      # event cached, pas de skill_start
test_stream_erreur_skill_retourne_event_error()   # exception → event error {message}

# Frontend (5 tests — frontend/src/__tests__/AnalyzePage.test.tsx)
test_affiche_formulaire_et_titre()           # rendu initial
test_affiche_StreamingProgress_pendant_streaming()  # streaming-progress testid visible
test_affiche_resultat_final_apres_complete() # result-ticker = "BNS"
test_affiche_message_erreur_quand_rejet()    # error-message testid avec message
test_appelle_streamAnalyze_avec_ticker()     # payload {ticker: 'BNS'}
```

#### Critère de succès
```bash
pytest tests/test_analyze_stream.py -v         # 8 tests verts
cd frontend && npm test                         # 50 tests Vitest verts
```

---

### Sprint 36 — Eval framework qualité IA + Sanitisation ticker ✅

**Objectif :** Mesurer la qualité des sorties Claude via un dataset golden de 20 tickers calibrés,
détecter les dérives de verdict après chaque changement de prompt, et sécuriser les entrées ticker
avec validation et normalisation systématique.

#### Fichiers créés

```
app/utils/ticker_sanitizer.py                   # sanitize_ticker() — regex + HTTP 422
tests/test_ticker_sanitizer.py                   # 28 tests (11 valides + 14 invalides + 3 standalone)
tests/evals/__init__.py                          # Package evals
tests/evals/conftest.py                          # eval_client — AsyncClient réel, JAMAIS de mock Claude
tests/evals/fixtures/__init__.py                 # load_graham_golden() → list[dict]
tests/evals/eval_runner.py                       # EvalResult, EvalReport, EvalRunner.run_all()
tests/evals/fixtures/graham_golden.template.json # 20 tickers (PASSE×8, BORDERLINE×6, REJETER×6)
```

#### Fichiers modifiés

```
app/skills/tier2/graham_analysis/schemas.py  # defensive_verdict @computed_field + pe: float | None
tests/test_schemas.py                         # test_pe_null_accepte + test_pe_negatif_accepte (remplacement test_pe_manquant)
tests/test_api.py                             # test_body_sans_pb_retourne_422 (pb = champ requis restant)
tests/test_integration_sync.py               # BODY_SANS_PB (pe optionnel, pb requis)
tests/test_report.py                          # payload invalides → pb manquant (pas pe)
```

#### Décisions d'architecture prises

| Décision | Choix retenu | Raison |
|----------|-------------|--------|
| **`defensive_verdict`** | `@computed_field` dérivé de `defensive_score` (PASSE≥6, BORDERLINE 4-5, REJETER≤3) | Cible stable pour les evals — jamais générée par Claude, toujours déterministe |
| **`pe: float \| None`** | Nullable, défaut `None` | Sociétés déficitaires (NKLA, RIVN, AMC) — critère PE échoue automatiquement si `None` |
| **Format golden dataset** | Clé `inputs` (pas `ratios`), `defensive_score_range: [min, max]` | Distingue les entrées API des sorties attendues ; plage plutôt que valeur exacte pour tolérer la variabilité Claude |
| **`@pytest.mark.evals`** | `call_claude_with_retry` **JAMAIS patché** dans `tests/evals/` | Les evals mesurent le vrai comportement Claude — mocker Claude annulerait leur utilité |

#### Progression

| Livrable | Statut |
|----------|--------|
| `sanitize_ticker()` + 28 tests | ✅ Complété |
| `defensive_verdict` computed_field | ✅ Complété |
| `pe: float \| None` + 4 tests mis à jour | ✅ Complété |
| EvalRunner + conftest + fixtures infra | ✅ Complété |
| `graham_golden.template.json` (20 tickers) | ✅ Complété |
| Intégrer `sanitize_ticker()` dans 3 endpoints | ✅ Complété — core.py + screen.py + watchlist.py |
| `graham_golden.json` (données réelles Yahoo) | ✅ Complété — 20 cas calibrés par Yves |
| `tests/evals/test_graham_evals.py` | ✅ Complété |
| `pytest tests/evals/ -m evals` ≥ 18/20 | ✅ **20/20 PASS (100 %)** |

#### Intégration `sanitize_ticker()` restante

```python
# app/orchestrator/core.py — @field_validator sur AnalyzeRequest.ticker
@field_validator("ticker")
@classmethod
def validate_ticker(cls, v: str) -> str:
    return sanitize_ticker(v)

# app/api/endpoints/screen.py — avant ScreenerService.screen()
# app/api/endpoints/watchlist.py — avant PostgreSQL insert
```

#### Tests evals — structure attendue (`tests/evals/test_graham_evals.py`)

```python
@pytest.mark.evals
async def test_graham_golden_dataset(eval_client, graham_golden):
    """Exécute tous les cas du golden dataset contre l'API réelle."""
    runner = EvalRunner(client=eval_client)
    report = await runner.run_all(graham_golden)

    assert report.pass_rate >= 0.90, f"Taux de réussite {report.pass_rate:.0%} < 90%"
    assert report.verdict_drift_rate <= 0.10
    report.print_summary()
```

Note : le payload mappe `inputs → ratios` lors de l'appel `POST /analyze`.

#### Critères de succès

- [x] `pytest tests/test_ticker_sanitizer.py -v` → 28 tests verts
- [x] `pytest tests/ -v -q --ignore=tests/evals` → 817+ passés (pas de régression)
- [x] `graham_golden.json` rempli avec vrais ratios Yahoo Finance
- [x] `pytest tests/evals/ -m evals` → **20/20 (100 %)** — appels Claude réels ✅

---

### Sprint 37 — Validation anti-hallucination ✅

**Objectif :** Sanity checks financiers avant appel Claude + détection contradictions inter-skills +
extension du `confidence_score` déterministe aux skills Buffett, Earnings et Dorsey.

#### Livrables

| Livrable | Statut |
|----------|--------|
| `@model_validator` sur `GrahamRatios` : pe<0, pb<0, eps_growth_10y>5, triangle pe/price/eps_ttm | ✅ |
| `confidence_score` Graham (`@computed_field` valeur_observee) | ✅ |
| `confidence_score` Buffett (champ régulier, calculé dans execute() depuis ratios non-None) | ✅ |
| `confidence_score` EarningsQuality (`@computed_field` depuis cadres M/Z/F/C/Sloan) | ✅ |
| `confidence_score` Dorsey (champ régulier, calculé dans execute() depuis ratios non-None) | ✅ |
| `_detect_inter_skill_conflicts()` + `inter_skill_conflicts: list[str]` dans `AnalyzeResponse` | ✅ |
| 27 nouveaux tests (validators + confidence × 4 skills + inter-skill conflicts) | ✅ |

#### Critères de succès

- [x] `pytest tests/evals/ -m evals` → 20/20 toujours verts après ajout validateurs
- [x] `inter_skill_conflicts` détecté pour Buffett=COMPOUNDER + Graham=REJETER
- [x] `confidence_score` calculé de façon déterministe sur 4 skills (Graham, Buffett, Earnings, Dorsey)
- [x] `pytest -m "not e2e and not evals"` → 851 tests CI verts (pas de régression, 25 échecs pré-existants)

#### Décisions d'architecture
- **GrahamRatios validators** : WARNING log uniquement, jamais HTTP 422 — les données imparfaites passent
- **confidence_score stratégie** : `@computed_field` quand l'output encode la complétude (valeur_observee / None-able), champ régulier sinon (calculé dans execute() depuis les inputs)
- **inter_skill_conflicts** : `list[str]` dans AnalyzeResponse (pas `bool`) — messages explicites pour revue manuelle

---

### Sprint 38 — Scoring composite unifié ✅

**Objectif :** Calculer un score global 0-100 agrégeant les 6 skills principaux avec pondération fixe et confidence_score.

#### Livrables livrés

| Skill | Pondération | Champ source | Mapping verdict → score brut |
|-------|------------|-------------|------------------------------|
| `graham_analysis` | 20 % | `defensive_verdict` | PASSE=1.0, BORDERLINE=0.5, REJETER=0.0 |
| `buffett_quality` | 20 % | `verdict` | COMPOUNDER=1.0, QUALITE_CORRECTE=0.75, REJETER=0.0 |
| `stock_valuation` | 20 % | `verdict` | SOUS_EVALUE=1.0, JUSTE_VALEUR=0.5, SUREVALUE=0.0 |
| `dorsey_moat` | 15 % | `moat_type` | WIDE=1.0, NARROW=0.5, NONE=0.0 |
| `earnings_quality` | 15 % | `verdict` | AUCUN_SIGNAL=1.0, ATTENTION=0.75, WATCHLIST=0.5, REJETER=0.0 |
| `marks_cycles` | 10 % | `recommandation_timing` | ACHETER*→1.0, ATTENDRE→0.5, sinon→0.0 |

**Formule :** `Σ(raw_i × poids_i × confidence_i) / Σ(poids_i × confidence_i) × 100`

#### Fichiers créés/modifiés
- `app/services/composite_score.py` — `CompositeScore` dataclass + `compute_composite_score()` + mappings bi-dialectes (test/schéma réel)
- `app/orchestrator/core.py` — `composite_score: CompositeScore | None` dans `AnalyzeResponse` + calcul dans `run_company_analysis()` et `stream_company_analysis()`
- `tests/test_composite_score.py` — 23 tests unitaires (mappings, labels, poids, schémas réels)

#### Critères de succès
- [x] `pytest tests/test_composite_score.py -v` → **23/23 verts**
- [x] `composite_score` présent dans `AnalyzeResponse` (champ Pydantic + dataclass)
- [x] Score varie selon les verdicts (ex. score=37.5 pour graham=REJETER + earnings=AUCUN_SIGNAL)
- [x] Skills absents n'influencent pas le dénominateur
- [x] `pytest -m "not e2e and not evals"` → **874 tests CI verts** (+23 nouveaux, 25 pré-existants inchangés)

#### Décisions d'architecture
- **composite_score** : `CompositeScore` Python dataclass (pas Pydantic) — Pydantic v2 sérialise nativement
- **marks mapping** : `recommandation_timing` (schéma réel) — "ACHETER" check covers both "ACHETER_AGRESSIF" and "ACHETER_PRUDEMMENT"
- **stock_valuation confidence** : `getattr(..., "confidence_score", 0.0)` — StockValuationOutput n'a pas encore confidence_score → toujours exclu du dénominateur pour l'instant

---

### Sprint 39 — Performance tracking ✅

**Objectif :** Enregistrer le cours au moment de l'analyse et exposer un endpoint `GET /performance/{ticker}` calculant le rendement rétrospectif.

#### Livrables livrés
- `infra/postgres/migration_sprint39.sql` — colonne `price_at_analysis FLOAT` dans `analysis_history`
- `app/orchestrator/core.py` — `_persist()` persiste `price_at_analysis` depuis `request.ratios.price`
- `app/skills/tier1/yahoo_finance.py` — `get_price()` — cours actuel sans lever d'exception
- `app/api/endpoints/performance.py` — `GET /performance/{ticker}` → `PerformanceResponse` avec `rendement_pct`
- `tests/test_performance.py` — 19 tests (7 unitaires `_compute_rendement` + 4 `_extract_composite_score` + 8 intégration endpoint)

#### Critères de succès
- [x] `infra/postgres/migration_sprint39.sql` — `price_at_analysis FLOAT` ajouté (fichier séparé, `init.sql` inchangé)
- [x] `_persist()` enregistre `price_at_analysis` depuis `request.ratios.price`
- [x] `GET /performance/{ticker}` retourne `PerformanceResponse` avec `rendement_pct`
- [x] `rendement_pct = None` si `price_at_analysis` ou `price_current` est absent
- [x] `pytest tests/test_performance.py -v` → **19/19 verts**
- [x] `pytest -m "not e2e and not evals"` → **893 tests CI verts** (+19 nouveaux, 25 pré-existants inchangés)

#### Décisions d'architecture
- **price_at_analysis** : `float | None` — persisté depuis `request.ratios.price` si GrahamRatios fournis, `None` sinon — jamais bloquant
- **get_price()** : méthode légère sur `YahooFinanceExtractor` — retourne `None` sur toute exception, ne lève jamais d'erreur
- **composite_score dans PerformanceEntry** : extrait du JSONB `result["composite_score"]["score"]` si présent — `None` pour les analyses antérieures au Sprint 39
- **Migration** : fichier `migration_sprint39.sql` séparé — `init.sql` inchangé pour les environnements existants
- **Ticker validation** : `sanitize_ticker()` — HTTP 422 si ticker invalide (même pattern que les autres endpoints)

---

### Sprint 40 — Tests E2E SSE ✅

**Objectif :** Couvrir le endpoint `POST /analyze-stream` avec des tests Playwright — vérifier la progression skill-par-skill, les états d'erreur et l'événement `complete`.

#### Livrables livrés
- `tests/e2e/test_e2e_stream.py` — 4 tests Playwright E2E streaming SSE
- `frontend/src/types/index.ts` — `CompositeScore` + `inter_skill_conflicts` ajoutés à `AnalyzeResponse`
- `frontend/src/components/AnalysisResult.tsx` — `data-testid="composite-score"` + `CompositeBadge` component

#### Critères de succès
- [x] Test : `streaming-progress` visible dans le DOM (skill_start traités via MutationObserver)
- [x] Test : `skill-done-*` éléments accumulés progressivement (≥ 2 skill_result events)
- [x] Test : `complete` event déclenche `result-ticker` + `composite-score`
- [x] Test : ticker invalide → HTTP 422 → `error-message` visible
- [x] `pytest -m "not e2e and not evals"` → 914 tests CI verts (pas de régression)

#### Décisions d'architecture Sprint 40
- **composite_score frontend** : `CompositeScore` interface dans `types/index.ts`, `data-testid="composite-score"` dans `AnalysisResult.tsx` — `CompositeBadge` composant dédié
- **MutationObserver pattern** : stratégie E2E pour capter les états SSE transitoiress (streaming-progress, skill-done-*) avant que React les démonte — réutilisable pour futurs tests streaming
- **Ticker invalide E2E** : `ABCDEFGH` (8 chars) → dépasse regex `^[A-Z0-9]{1,6}` → 422 backend → `ApiError` → `setStreamError` → `error-message` DOM

---

### Sprint 41 — Dashboard métriques qualité IA ✅

**Objectif :** Afficher `composite_score` et `inter_skill_conflicts` dans le frontend React — permettre à Yves de visualiser la qualité du signal IA en un coup d'oeil.

#### Livrables livrés
- `frontend/src/pages/DashboardPage.tsx` — page `/dashboard` étendue (MetricsDashboard + section qualité IA)
- `frontend/src/components/CompositeScoreHistory.tsx` — historique composite_score par ticker (GET /performance/{ticker})
- `frontend/src/components/ConflictsList.tsx` — liste des inter_skill_conflicts
- `frontend/src/lib/recentAnalyses.ts` — localStorage save/load (RECENT_ANALYSES_KEY, max 10 entrées)
- `frontend/src/pages/AnalyzePage.tsx` — saveRecentAnalysis() au `complete`/`cached` event
- `frontend/src/api/analyze.ts` — getPerformance(ticker)
- `frontend/src/types/index.ts` — PerformanceEntry, PerformanceResponse, RecentAnalysis

#### Critères de succès
- [x] Route `/dashboard` dans `App.tsx` (déjà présente)
- [x] Navigation vers `/dashboard` depuis la nav principale (déjà présente)
- [x] `CompositeScoreHistory` affiche score + label pour le dernier ticker analysé
- [x] `ConflictsList` affiche les conflits si présents (liste vide sinon)
- [x] Tests Vitest : `ConflictsList` (4), `CompositeScoreHistory` (7), `DashboardPage` (7) — 18 nouveaux
- [x] `pytest -m "not e2e and not evals"` → 914+ tests CI verts (backend inchangé)
- [x] `npm run build` frontend sans erreur TypeScript — 68 tests Vitest verts (vs 50 avant)

### Sprint 42 — Tool Use pilote ✅

**Objectif :** Migrer `graham_analysis` et `earnings_quality` de `_parse_claude_json(response.content[0].text)`
vers **Tool Use** (Anthropic SDK `tools` parameter) — élimine les hallucinations de format JSON texte.

#### Livrables livrés
- `app/utils/tool_schema.py` — `build_tool_schema()` : schéma dérivé de `model_json_schema()`, filtre computed_fields
- `app/skills/tier2/graham_analysis/skill.py` — Tool Use via `graham_output` tool, `tool_choice` forcé, `_parse_claude_json` retiré
- `app/skills/tier2/earnings_quality/skill.py` — Tool Use via `earnings_quality_output` tool, `_parse_claude_json` retiré
- `tests/test_graham_tool_use.py` — 9 tests unitaires (schéma, extraction, ValueError, tools/tool_choice params)
- `tests/conftest.py` — 3 fixtures mises à jour (tool_use blocks au lieu de text blocks)
- `tests/test_skill.py` — nettoyé (`_parse_claude_json` tests retirés, mocks mis à jour)
- `tests/test_earnings_quality.py` — 5 tests mises à jour (mocks tool_use)

#### Critères de succès
- [x] `graham_analysis` retourne le résultat via Tool Use
- [x] `earnings_quality` retourne le résultat via Tool Use
- [x] `_parse_claude_json` retiré des 2 skills
- [x] `pytest -m "not e2e and not evals"` → **915 tests CI verts** (914+ atteint)
- [x] `app/utils/tool_schema.py` — schéma dérivé de Pydantic, jamais écrit manuellement

---

### Sprint 43 — Tool Use complet (13 skills restants) ✅

**Objectif :** Migrer les 13 skills restants vers Tool Use en suivant le pattern établi au Sprint 42.
Chaque skill reçoit son propre `_SKILL_TOOL_SCHEMA = build_tool_schema(SkillOutput, exclude={computed_fields})`.

**Dépendance dure :** Sprint 42 ≥ 20/20 evals (baseline Tool Use établie).

#### Livrables livrés
- 13 `skill.py` migrés : `dorsey_moat`, `buffett_quality`, `stock_valuation`, `thesis_builder`, `munger_mental`, `canadian_tax`, `lynch_categories`, `fisher_scuttlebutt`, `klarman_margin`, `greenblatt`, `damodaran_narrative`, `marks_cycles`, `pabrai_dhandho`
- `tests/test_tool_use_skills.py` — 26 tests (13 × schéma + 13 × ValueError) — 0 appel Claude réel
- Mocks Tool Use corrigés dans 13 fichiers de tests existants (pattern `tool_use` block)
- Correction deprecation Pydantic V2.11 : `model_fields` accédé via `type()` plutôt que instance

#### Critères de succès
- [x] 13 skills migrés vers Tool Use
- [x] `_parse_claude_json` retiré de tous les skills
- [x] `pytest -m "not e2e and not evals"` → **942 tests CI verts**
- [x] `build_tool_schema()` utilisé partout — aucun schéma écrit manuellement

---

### Sprint 44 — Multi-model routing ✅

**Objectif :** Router les skills mécaniques/quantitatifs vers Haiku, conserver Sonnet pour les skills qualitatifs. Réduction de coût ~40-60 % sur les appels aux skills formulaiques.

**Livrables :**
- `app/api/main.py` : variable `haiku_model` lue depuis `CLAUDE_HAIKU_MODEL` env var
- `earnings_quality`, `greenblatt`, `lynch_categories` → `haiku_model` (`claude-haiku-4-5-20251001`)
- Tous les autres skills → `model` (Sonnet, `claude-sonnet-4-6`)
- `tests/test_model_routing.py` : 9 tests (8 unitaires + 1 intégration lifespan)
- `.env.example` : ajout `CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001`
- **951 tests CI verts** (vs 942 au Sprint 43)

**Version :** 3.8.0

### Sprint 45 — Evals earnings_quality ✅

**Objectif :** Golden dataset 20 cas pour `EarningsQualitySkill` + framework de détection de drift post-migration Haiku.

**Livrables :**
- `tests/evals/fixtures/earnings_golden.json` : 20 cas réels (MSFT, AAPL, JNJ, PG, KO, BNS, TD, JPM, TSLA, AMZN, UBER, LYFT, NFLX, GME, BBBY, AMC, GE, BA, COIN, MRO)
- `tests/evals/test_earnings_evals.py` : 6 tests `@pytest.mark.evals` (verdict, F-Score, Z-Score, M-Score, drapeaux_rouges, taux concordance global)
- `tests/test_earnings_golden_schema.py` : 10 tests de validation schema (CI standard)
- `tests/evals/fixtures/__init__.py` : ajout `load_earnings_golden()`
- **961 tests CI verts** (vs 951 au Sprint 44)

**Version :** 3.9.0

### Sprint 46 — Screener composite ✅

**Objectif :** Exposer `composite_score` et `composite_label` dans `ScreenEntry`/`ScreenResult`, trier les résultats par `composite_score` décroissant (fallback `defensive_score`).

**Livrables :**
- `app/api/endpoints/screen.py` : `ScreenEntry` + `composite_score: float | None` + `composite_label: str | None`
- `app/services/screener.py` : extraction `response.composite_score`, tri composite-first, support cache hit
- `tests/test_screener.py` : +4 tests composite_score (expose, tri, fallback, label)
- **965 tests CI verts** (vs 961 au Sprint 45)

**Version :** 4.0.0

### Sprint 47 — Export CSV/Excel ✅

**Objectif :** Endpoint `POST /export/screen` qui lance le screener et retourne un fichier CSV ou Excel téléchargeable.

**Livrables :**
- `app/services/export.py` : `export_to_csv()` (csv stdlib) + `export_to_excel()` (openpyxl)
- `app/api/endpoints/export.py` : `POST /export/screen?format=csv|xlsx`
- `app/api/main.py` : router export enregistré
- `requirements.txt` : ajout `openpyxl>=3.1.0`
- `tests/test_export.py` : 13 tests passés (3 Excel skippés si openpyxl absent, activés dans Docker)
- **978 tests CI verts** (vs 965 au Sprint 46)

**Version :** 4.1.0

### Sprint 48 — Watchlist alertes composite ✅

**Objectif :** Alertes de dérive du score composite sur les entrées watchlist.

#### Livrables
- `infra/postgres/migration_sprint48.sql` — colonnes `last_composite_score + composite_alert_threshold`
- `app/models/watchlist.py` — deux nouveaux champs Pydantic
- `app/services/watchlist_service.py` — `update_composite_score()` + SELECT étendu
- `app/services/composite_alert.py` — `CompositeAlertService.check_composite_alerts()` + email
- `tests/test_composite_alert.py` — 13 tests (comparaison, alerte, email, exception isolation)
- **991 tests CI verts** (vs 978 au Sprint 47)

---

### Sprint 49 — Evals multi-skills ✅

**Objectif :** Golden datasets pour 3 skills qualitatifs critiques + frameworks eval.

#### Livrables
- `tests/evals/fixtures/dorsey_golden.json` — 15 cas (5 WIDE, 5 NARROW, 3 NONE, 2 institutions)
- `tests/evals/fixtures/buffett_golden.json` — 15 cas (5 COMPOUNDER, 5 QUALITE_CORRECTE, 3 REJETER, 2 frontier)
- `tests/evals/fixtures/damodaran_golden.json` — 15 cas (5 story, 5 number, 3 rupture, 2 dark horse)
- `tests/evals/fixtures/__init__.py` — `load_dorsey_golden()`, `load_buffett_golden()`, `load_damodaran_golden()`
- `tests/evals/test_dorsey_evals.py` — 5 tests eval (`@pytest.mark.evals`)
- `tests/evals/test_buffett_evals.py` — 5 tests eval (`@pytest.mark.evals`)
- `tests/evals/test_damodaran_evals.py` — 5 tests eval (`@pytest.mark.evals`)
- `tests/test_evals_golden_schema.py` — 25 tests CI standard (validation schema JSON)
- **1016 tests CI verts** (vs 991 au Sprint 48)

---

### Sprint 50 — Backtesting composite ✅

**Objectif :** Simulation retrospective du signal composite vs benchmark.

#### Livrables
- `app/models/backtest.py` — `BacktestRequest`, `BacktestResult`, `BucketResult` (Pydantic)
- `app/services/backtest.py` — `BacktestService.run_backtest()` : classifieur + yfinance + agregation
- `app/api/endpoints/backtest.py` — `GET /backtest/composite` (max 30 tickers, start_date >= 2023)
- `app/api/main.py` — inclusion du router backtest
- `tests/test_backtest.py` — 22 tests (classifieur, modeles, service, endpoint)
- **1038 tests CI verts** (vs 1016 au Sprint 49)

---

### Sprint 51 — Dashboard evals ✅

**Objectif :** Dashboard de suivi des evals avec historique Redis.

#### Livrables
- `app/models/evals.py` — `EvalSkillInfo`, `EvalsSummary`, `EvalRunRecord` (Pydantic)
- `app/services/evals_dashboard.py` — `EvalsDashboardService` : summary + record + history
- `app/api/endpoints/evals.py` — `GET /evals/summary`, `POST /evals/record`, `GET /evals/history`
- `app/api/main.py` — inclusion du router evals
- `tests/conftest.py` — ajout `lpush`, `ltrim`, `lrange` au mock redis_pool
- `tests/test_evals_dashboard.py` — 15 tests (service + endpoints)
- **1053 tests CI verts** (vs 1038 au Sprint 50)

---

### Sprint 52 — Alertes Celery schedulées ✅

**Objectif :** Automatiser la surveillance composite_score watchlist via Celery Beat.

#### Livrables
- `app/workers/tasks.py` — `_execute_composite_alert_check()` + `run_composite_alert_check` task
- `app/workers/celery_app.py` — entrée `run-composite-alert-check-daily` (10h00 UTC) dans beat_schedule
- `tests/test_celery_composite_alert.py` — 10 tests (beat schedule + logique execution + email config)
- **1063 tests CI verts** (vs 1053 au Sprint 51)

---

### Sprint 53 — Rapport PDF watchlist enrichi ✅

**Objectif :** Enrichir le PDF hebdomadaire watchlist avec composite_score, label et alerte composite.

#### Livrables
- `app/services/report.py` — 3 nouvelles colonnes dans `generate_watchlist_summary_pdf()` : Score composite, Label, Alerte composite
- `app/services/report.py` — helpers `_composite_label()` et `_composite_alerte()` (testables isolément)
- `tests/test_report.py` — 3 nouveaux tests Sprint 53 (label, none, alerte)
- **1066 tests CI verts** (vs 1063 au Sprint 52)

---

### Sprint 54 — Evals screening ✅

#### Livrables
- `tests/evals/golden_screener_dataset.json` — 10 tickers avec ratios + expected (score_min, verdict_allowed, composite_label_allowed)
- `tests/evals/fixtures/__init__.py` — `load_screener_golden()` ajoutée
- `tests/evals/test_screener_evals.py` — 5 tests `@pytest.mark.evals` (mocks configurés depuis le dataset)
- `tests/test_screener_golden.py` — 12 tests CI standard (structure dataset + logique tri + seuils composite)
- **1078 tests CI verts** (vs 1066 au Sprint 53)

---

### Sprint 55 — Multi-modèle eval ✅

#### Livrables
- `tests/evals/fixtures/multi_model_golden.json` — 6 cas (2 par skill Haiku : earnings_quality, greenblatt_magic_formula, lynch_categories)
- `tests/evals/fixtures/__init__.py` — `load_multi_model_golden()` ajoutée
- `tests/evals/test_multi_model_evals.py` — 7 tests `@pytest.mark.evals` (schema valide + concordance verdict + taux global)
- `tests/test_multi_model_golden.py` — 14 tests CI standard (structure, Pydantic, logique contrastante)
- **1092 tests CI verts** (vs 1078 au Sprint 54)

---

### Sprint 56 — Notifications webhook ✅

#### Livrables
- `app/services/webhook_service.py` — `WebhookService` avec 3 méthodes async (`send_price_alert`, `send_composite_alert`, `send_watchlist_summary`), httpx, retry 1x, tracking `nb_erreurs` + `derniere_notification`
- `app/workers/tasks.py` — WebhookService intégré dans `run_price_alert_check`, `run_composite_alert_check`, `run_weekly_watchlist_report` (skip silencieux si `WEBHOOK_URL` absent)
- `app/api/endpoints/telemetry.py` — `GET /telemetry/webhook` (`WebhookStatus` : url_configuree, derniere_notification, nb_erreurs)
- `app/api/main.py` — `webhook_service` ajouté à `app.state`
- `.env.example` — `WEBHOOK_URL` + `WEBHOOK_SECRET` documentés
- `tests/test_webhook_service.py` — 12 tests CI standard (mocks httpx, retry, payload, secret header)
- **1104 tests CI verts** (vs 1092 au Sprint 55)

---

### Sprint 57 — Historique composite_score ✅

#### Livrables
- `infra/postgres/init.sql` — table `composite_score_history` (id UUID, ticker, score, label, workflow, recorded_at) + index `idx_csh_ticker_recorded`
- `app/services/composite_history_service.py` — `CompositeHistoryService` avec `record()` + `get_history()` async, `CompositeHistoryPoint` Pydantic
- `app/api/endpoints/composite_history.py` — `GET /composite-history/{ticker}` (limit 1-365, défaut 90), sanitise ticker
- `app/orchestrator/core.py` — paramètre `composite_history_service` optionnel dans `run_company_analysis` et `stream_company_analysis`, appel `record()` protégé par try/except après `compute_composite_score()`
- `app/api/endpoints/analyze_stream.py` — passage `composite_history_service` au générateur SSE
- `app/api/main.py` — `CompositeHistoryService(db_pool)` + `app.state.composite_history_service` + router enregistré
- `tests/test_composite_history_service.py` — 10 tests CI standard (schéma Pydantic, record(), get_history(), limites, ticker invalide, 3 tests endpoint intégration)
- **1114 tests CI verts** (vs 1104 au Sprint 56)

---

### Sprint Frontend Catchup — Synchronisation types + bugs + features ✅

#### Livrables
- `frontend/src/types/index.ts` — ajout `CompositeHistoryPoint`, champs `composite_score`/`composite_label` dans `ScreenEntry`, champs `last_composite_score`/`composite_alert_threshold`/`score_alerte_min` dans `WatchlistEntry`
- `frontend/src/api/analyze.ts` — ajout `getCompositeHistory()` (GET /composite-history/{ticker}) et `exportScreen()` (POST /export/screen)
- `frontend/src/components/CompositeScoreHistory.tsx` — correction endpoint (`getPerformance` → `getCompositeHistory`), adaptation affichage à `CompositeHistoryPoint`
- `frontend/src/pages/HistoryPage.tsx` — soumission vide interdite (return early si ticker vide, suppression fallback 'ALL')
- `frontend/src/components/ScreenerTable.tsx` — colonne "Composite" (score + label coloré) entre Verdict et Coût
- `frontend/src/components/WatchlistTable.tsx` — colonne "Score composite" avec badge coloré FORT/MODÉRÉ/FAIBLE
- `frontend/src/pages/ScreenerPage.tsx` — boutons "Exporter CSV" et "Exporter Excel" après résultat screener
- `frontend/src/__tests__/CompositeScoreHistory.test.tsx` — réécriture complète pour `getCompositeHistory` (7 tests)
- `frontend/src/__tests__/ScreenerTable.test.tsx` — mise à jour fixtures + 2 nouveaux tests colonne composite (8 tests)
- `frontend/src/__tests__/WatchlistTable.test.tsx` — nouveau fichier, 4 tests colonne last_composite_score
- `frontend/src/__tests__/HistoryPage.test.tsx` — nouveau fichier, 4 tests soumission vide interdite
- `frontend/src/__tests__/ScreenerPage.test.tsx` — nouveau fichier, 4 tests boutons export CSV/Excel
- `frontend/src/__tests__/WatchlistPage.test.tsx` — mise à jour makeEntry() avec nouveaux champs WatchlistEntry
- **83 tests Vitest verts, 0 failing** (vs 1 failing, 67 passing avant)
- `npm run build` sans erreur TypeScript

---

### Sprint 58 — Screener avancé ✅

---

### Sprint 61 — Eval drift detection ✅

**Objectif :** Détecter automatiquement les régressions de qualité IA après une mise à jour de modèle Claude, sans intervention manuelle.

**Livrables :**
- `app/services/eval_drift_service.py` — `EvalDriftService` avec `EvalDriftResult` (Pydantic), `run_eval()`, `get_last_result()`, `record_result()`. Clé Redis `eval_drift:{dataset}`, TTL 30 jours, seuil configurable via `EVAL_DRIFT_THRESHOLD` (défaut 0.85)
- `app/api/endpoints/telemetry.py` — `GET /telemetry/eval-drift?dataset={dataset}` (lecture seule Redis, 503 si service absent, 400 si dataset invalide)
- `app/workers/tasks.py` — tâche Celery `run_eval_drift_check(dataset="graham")` déclenchable manuellement ou en cron
- `app/api/main.py` — `EvalDriftService` initialisé dans le lifespan, disponible via `app.state.eval_drift_service`
- `tests/test_eval_drift_service.py` — 19 tests CI standard (schéma, Redis, run_eval avec mock, endpoint)
- Datasets supportés : `graham`, `earnings`, `dorsey`, `buffett`, `damodaran`
- `_check_case()` patchable pour les tests CI (aucun appel Claude réel)
- **1171 tests CI verts** — version 5.4.0

---

### Sprint 60 — Dashboard composite trends ✅

**Objectif :** Graphique d'évolution du composite_score dans le frontend React, consommant `GET /composite-history/{ticker}` (Sprint 57).

**Livrables :**
- `frontend/package.json` — recharts 3.8.1 ajouté aux dépendances
- `frontend/src/components/CompositeScoreChart.tsx` — composant présentationnel recharts : LineChart, axes X/Y (0-100), zones de référence FORT (70) / MODÉRÉ (45), dots colorés par label (vert/orange/rouge), tooltip score+label+date+workflow, états loading/erreur/vide
- `frontend/src/pages/DashboardPage.tsx` — section "Évolution composite score" : input ticker + bouton "Charger", `useQuery` getCompositeHistory(), `CompositeScoreChart` intégré
- `frontend/src/__tests__/CompositeScoreChart.test.tsx` — 7 tests Vitest (mock recharts complet, états vide/loading/erreur/données)
- `tests/test_composite_history_endpoint.py` — 5 nouveaux tests CI endpoint
- **1152 tests CI verts** — version 5.3.0

---

### Sprint 59 — Export Excel watchlist ✅

**Objectif :** `GET /watchlist/export.xlsx` — fichier Excel téléchargeable avec toutes les positions de la watchlist.

**Livrables :**
- `app/services/watchlist_service.py` — `get_all_with_composite()` : JOIN LATERAL sur `composite_score_history` pour obtenir le dernier score par ticker
- `app/api/endpoints/watchlist.py` — `_generate_watchlist_xlsx()` + `GET /watchlist/export.xlsx`
- Colonnes : Ticker, Nom, Date ajout, Composite Score, Label, Alerte, Notes
- En-têtes en gras, fond gris clair (#D3D3D3), largeurs de colonnes adaptées
- `tests/test_export_xlsx.py` — 15 tests CI (10 unitaires + 5 endpoint)
- **1147 tests CI verts** — version 5.2.0

---

### Sprint 64 — Screener planifié (cron) ✅

**Objectif :** Tâche Celery hebdomadaire qui screene toute la watchlist, filtre les opportunités FORT, et notifie par webhook.

**Livrables :**
- `app/services/webhook_service.py` — `send_screener_report()` méthode async (payload type="screener", nb_tickers_screenes, nb_opportunites, tickers_fort)
- `app/workers/tasks.py` — `_execute_scheduled_screener()` + `run_scheduled_screener` tâche Celery. Récupère tous les tickers watchlist, screene par batches de 20, filtre composite_label="FORT" OU defensive_score >= 5, envoie webhook si opportunités trouvées. Tolérant aux erreurs par batch.
- `app/workers/celery_app.py` — entrée `run-scheduled-screener` (dimanche 11h00 UTC) dans beat_schedule. Total : 5 tâches planifiées.
- `tests/test_scheduled_screener.py` — 14 tests CI standard (import, watchlist vide, FORT composite, FORT defensive_score, webhook appelé, webhook non appelé, tolérance erreur, ticker erreur ignoré, beat_schedule, WebhookService)
- `tests/test_celery_composite_alert.py` — test mis à jour : 4 → 5 tâches planifiées
- **1210 tests CI verts** (vs 1196 au Sprint 63) — version 5.7.0

---


---
## Journal des sprints (une ligne par sprint — dédupliqué, ordre d'origine)

*Sprint 73 complété : Recherche full-text dans l'historique — GET /history?q= (ticker partiel ILIKE, workflow ILIKE, verdicts JSONB ILIKE) + ticker optionnel + HistoryResponse.ticker nullable + index GIN pg_trgm (ticker + workflow_name) + HistoryPage champ Recherche + notice cross-ticker + 9 tests CI + 5 tests Vitest HistorySearch.test.tsx — 1259 tests CI verts — 133 tests Vitest verts — version 6.6.0*
*Sprint 72 complété : Comparaison multi-tickers Dashboard — TickerComparisonChart recharts (multi-lignes 2-5 tickers, palette 5 couleurs, ReferenceLine FORT/MODÉRÉ, CustomTooltip) + ComparisonSection DashboardPage (saisie CSV, Promise.all parallèle, validation 2-5 tickers) + 6 tests TickerComparisonChart + 4 tests ComparisonSection — 128 tests Vitest verts — version 6.5.0*
*Sprint 71 complété : Rapport screener PDF — ScreenerPdfService.generate() reportlab + GET /screener-report + WebhookService.send_screener_pdf_report() multipart + Celery scheduled_screener + downloadScreenerPdf() + bouton "Exporter PDF" ScreenerPage (data-testid="export-pdf") + 13 tests CI + 6 tests Vitest — 1250 tests CI verts — 118 tests Vitest verts — version 6.4.0*
*Sprint 70 complété : Notation ESG simplifiée — EsgSimplifiedSkill (15 critères 5E+5S+5G) + EsgInput/EsgOutput/EsgCritere schemas Pydantic + Tool Use forcé + prompt >1024 tokens + esg dans AnalyzeRequest/Response — 17 tests CI verts — 1236 tests verts — version 6.3.0*
*Sprint 69 complété : Badge "depuis cache" dans AnalyzePage — état depuisCache + Badge shadcn/ui "Score depuis cache (<24h)" + reset au lancement d'une nouvelle analyse + 5 tests Vitest CacheIndicator.test.tsx — 112 tests Vitest verts — version 6.2.0*
*Sprint 68 complété : Lien PDF dans l'interface — downloadTickerPdf() api/analyze.ts + bouton "Télécharger PDF" HistoryPage (loading + gestion 404) + bouton "PDF" par ticker WatchlistTable (data-testid + gestion 404) + 6 tests PdfDownload.test.tsx verts — 107 tests Vitest verts — version 6.1.0*
*Sprint 67 complété : Page admin frontend — ApiKey/ApiKeyCreate interfaces TS + api/admin.ts (listApiKeys/createApiKey/revokeApiKey) + AdminPage.tsx (création + liste + révocation + gestion 403) + route /admin App.tsx + 6 tests Vitest AdminPage.test.tsx — 101 tests Vitest (100 verts) — version 6.0.0*
*Sprint 66 complété : Dashboard eval drift frontend — EvalDriftResult interface TS + fetchEvalDrift() api/analyze.ts + EvalDriftSection DashboardPage (progress bar + badges OK/DRIFT) + 5 tests Vitest EvalDriftSection.test.tsx — 95 tests Vitest verts — version 5.9.0*
*Sprint 65 complété : Cache composite_score automatique — CompositeHistoryService.get_recent() + circuit court Étape 0b dans run_company_analysis()/stream_company_analysis() + AnalyzeResponse.depuis_cache_composite + types TS synchronisés + 10 tests CI — 1220 tests CI verts — version 5.8.0*
*Sprint 64 complété : Screener planifié (cron) — run_scheduled_screener Celery dimanche 11h00 UTC + WebhookService.send_screener_report() + filtrage FORT (composite_label OU defensive_score >= 5) + 14 tests CI — 1210 tests CI verts — version 5.7.0*
*Sprint 63 complété : Rapport PDF par ticker — PdfReportService.generate_ticker_report() 3 pages (score actuel, historique, skills) + GET /ticker-report/{ticker}?days=90 + 13 tests CI — 1196 tests CI verts — version 5.6.0*
*Sprint 62 complété : API publique multi-utilisateurs — table api_keys PostgreSQL + ApiKeyService (validate/create/list/revoke/record_usage) + BearerTokenMiddleware fallback rétrocompatible + POST/GET/DELETE /admin/keys + 12 tests CI — 1183 tests CI verts — version 5.5.0*
*Sprint 61 complété : Eval drift detection — EvalDriftService + EvalDriftResult + GET /telemetry/eval-drift + run_eval_drift_check Celery + 19 tests CI — 1171 tests CI verts — version 5.4.0*
*Sprint 60 complété : Dashboard composite trends — recharts LineChart + CompositeScoreChart.tsx + DashboardPage section Évolution + 7 tests Vitest + 5 tests CI endpoint — 1152 tests CI verts — version 5.3.0*
*Sprint 59 complété : Export Excel watchlist — GET /watchlist/export.xlsx + get_all_with_composite() JOIN LATERAL + _generate_watchlist_xlsx() + 15 tests CI — 1147 tests CI verts — version 5.2.0*
*Sprint 58 complété : Screener avancé — 3 filtres POST /screen (composite_label, min_composite_score, filter_workflow) + logique AND + tickers en échec toujours inclus + 15 tests CI — 1129 tests CI verts — version 5.1.0*
*Sprint Frontend Catchup complété : Synchronisation types TS + 5 bugs corrigés + 3 features ajoutées + 5 nouveaux fichiers de tests — 83 tests Vitest verts, 0 failing — build propre — 2026-05-14*
*Sprint 57 complété : Historique composite_score — table composite_score_history + CompositeHistoryService record()/get_history() + GET /composite-history/{ticker} + 10 tests CI, 1114 tests CI verts — version 5.0.0*
*Utiliser `prompt-mise-a-jour-roadmap.md` pour guider Claude lors des mises à jour.*
*Sprint 24 complété : Alertes prix — PriceAlertService + run_price_alert_check + GET /price-status + 7 tests verts — version 2.4.0*
*Sprint 25 complété : Export hebdomadaire automatique — EmailService + generate_watchlist_summary_pdf + run_weekly_watchlist_report + 7 tests verts — version 2.5.0*
*Sprint 26 complété : Déploiement homelab — Caddy + TLS Let's Encrypt + backup PostgreSQL + Uptime Kuma + docker-compose.prod.yml + 2 tests healthz — version 2.5.0*
*Sprint 27 complété : Watchlist dans le frontend — WatchlistPage React + WatchlistTable + api/watchlist.ts + requestEmpty() + 6 tests Vitest — total frontend 34 tests verts — version 2.5.0*
*Sprint 28 complété : Authentification frontend — AuthContext + ProtectedRoute + LoginPage + token localStorage + 5 tests Vitest — total frontend 39 tests verts — version 2.5.0*
*Sprint 29 complété : Fix WorkflowRouter — 24 échecs corrigés (dorsey_moat + buffett_quality dans value_graham) — total backend 806 passés — version 2.5.0*
*Sprint 30 complété : Tests E2E Frontend → Backend — 16 tests Playwright (auth×4, analyze×5, screener×3, watchlist×4) — InMemoryWatchlistService + stubs JSON 15 skills + mocks middleware — version 2.6.0*
*Sprint 31 complété : CI/CD GitHub Actions — .github/workflows/ci.yml — 2 jobs parallèles (backend pytest + frontend vitest) — badge CI README.md — version 2.6.0*
*Sprint 32 complété : Extraction auto Yahoo Finance (frontend) — bouton Auto-fill AnalyzeForm → GET /extract → ratios pré-remplis — 3 tests Vitest + fix LoginPage validation — total frontend 42 tests verts — version 2.7.0*
*Sprint 33 complété : Qualité bénéfices fonctionnelle — extract_earnings_quality() + ExtractResponse + checkbox AnalyzeForm + 5 tests backend + 3 tests frontend — 45 tests Vitest verts — version 2.8.0*
*Sprint 34 complété : Tests E2E Sprint 33 — 3 tests Playwright (autofill Graham, checkbox earnings active, analyse complète) + fix mock extract_earnings_quality dans conftest E2E — 19 tests E2E verts — version 2.9.0*
*Sprint 35 complété : SSE Streaming — POST /analyze-stream + stream_company_analysis() + StreamingProgress React + streamAnalyze() fetch/ReadableStream + 8 tests backend + 5 tests frontend — 50 tests Vitest verts — version 3.0.0*
*Sprint 36 complété : Eval framework qualité IA + Sanitisation ticker — defensive_verdict computed_field + defensive_score computed_field + pe nullable + sanitize_ticker() intégré dans 3 endpoints + EvalRunner + graham_golden.json 20 cas + test_graham_evals.py **20/20 PASS** — 817 tests CI verts*
*Sprint 37 complété : Validation anti-hallucination — @model_validator GrahamRatios (pe<0, pb<0, eps_growth>5, triangle pe/price/eps_ttm) + confidence_score sur 4 skills (Graham @computed_field, Buffett/Dorsey champ régulier, Earnings @computed_field) + _detect_inter_skill_conflicts() + inter_skill_conflicts dans AnalyzeResponse — 27 nouveaux tests — 851 tests CI verts — version 3.1.0*
*Sprint 38 complété : Scoring composite unifié — CompositeScore dataclass + compute_composite_score() 6 skills pondérés (verdict × poids × confidence) + composite_score dans AnalyzeResponse + run_company_analysis() + stream_company_analysis() — 23 nouveaux tests (+ 8 schémas réels) — 874 tests CI verts — version 3.2.0*
*Sprint 39 complété : Performance tracking — migration_sprint39.sql (price_at_analysis FLOAT) + _persist() + get_price() YahooFinanceExtractor + GET /performance/{ticker} (PerformanceResponse, rendement_pct, composite_score si disponible) + 19 tests (7 unitaires + 4 extracteur + 8 intégration) — 893 tests CI verts — version 3.3.0*
*Sprint 40 complété : Tests E2E SSE — test_e2e_stream.py (4 tests Playwright : skill_start MutationObserver, progression skill-done-*, complete+composite_score, ticker invalide 422) + CompositeScore dans types/index.ts + data-testid="composite-score" dans AnalysisResult.tsx — 914 tests CI verts — version 3.4.0*
*Sprint 41 complété : Dashboard métriques qualité IA — DashboardPage étendue + CompositeScoreHistory (GET /performance/{ticker}) + ConflictsList + lib/recentAnalyses.ts (localStorage) + saveRecentAnalysis() dans AnalyzePage + getPerformance() API + PerformanceEntry/RecentAnalysis types — 68 tests Vitest verts (+18 nouveaux) — version 3.5.0*
*Sprint 42 complété : Tool Use pilote — graham_analysis + earnings_quality migrés vers Anthropic Tool Use (tool_choice forcé) + build_tool_schema() dérivé de Pydantic + _parse_claude_json retiré des 2 skills + 9 nouveaux tests unitaires — 915 tests CI verts — version 3.6.0*
