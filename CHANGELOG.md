# Changelog

All notable changes to TradingClaude are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — Semantic Versioning ([semver](https://semver.org/)).

---

## [10.3.0] — 2026-05-27 · Sprint 116

### Added
- **Command palette ⌘K** — `CommandPalette` component (cmdk 1.1.1) triggered by Ctrl+K / ⌘K from any page
- 4 groups: Quick actions (Analyze / Compare), Recent analyses (localStorage), Pages (10 routes), Knowledge base (RAG semantic search, debounce 400 ms, ≥ 3 chars)
- Header trigger button with keyboard hint (`data-testid="command-palette-trigger"`)
- `AnalyzeForm` accepts optional `initialTicker` prop; `AnalyzePage` reads `?ticker=` URL param (cleaned after use)
- `ResizeObserver` polyfill in `setupTests.ts` for cmdk in jsdom

### Tests
- +8 Vitest — `CommandPalette.test.tsx` (308 → 307 Vitest total after CI reorganization)

---

## [10.2.0] — 2026-05-20 · Sprint 115

### Changed
- **Full-width shell** — `max-w-5xl` replaced by `max-w-shell` CSS token (`--container-shell: 96rem`) in `App.tsx`
- Header sticky bar now full-bleed with inner content aligned to shell width
- **Dashboard 12-column grid** — `lg:grid-cols-12` responsive layout (`DashboardPage`); metrics sections span 12 cols, others span 6

---

## [10.1.0] — 2026-05-17 · Sprint 114

### Added
- **Semantic color tokens** — `--bull` / `--bear` / `--neutral` CSS variables + `@theme inline` mapping; `frontend/src/lib/colors.ts` for recharts (`CHART`, `SERIES`)
- Replaced ~80 hex colors and ~43 hardcoded Tailwind utilities across all components and charts
- **Accurate streaming progress** — `Orchestrator._planned_skill_ids()` emits SSE `plan` event; `StreamingProgress` uses planned list as denominator
- **Skeletons everywhere** — 11 chart/section components use `Skeleton`/`SkeletonTable` instead of text placeholders
- **Accessibility** — `prefers-reduced-motion` block; sortable `ScreenerTable` headers as focusable `<button>` with `aria-sort`

### Tests
- +5 CI (planned skills) · +2 Vitest (StreamingProgress)

---

## [10.0.0] — 2026-05-12 · Sprint 113

### Added
- **Global Micro-UX Refresh** — 5 CSS keyframes (`shimmer`, `fade-in-up`, `scale-in`, `slide-in-right`, `count-pulse`) + Tailwind tokens
- `Skeleton` / `SkeletonRow` / `SkeletonCard` / `SkeletonTable` components
- `AnimatedNumber` (count-up `requestAnimationFrame` cubic-out) on WebSocket metrics
- `PageTransition` + `StaggerItem` wrappers on all 11 pages
- Press feedback on buttons (`active:scale-95`), hover glow on cards, `animate-scale-in` on badges
- `StreamingProgress` bar with `animate-ping` on active skill indicator

### Tests
- +22 Vitest (Skeleton, AnimatedNumber, PageTransition)

---

## [9.9.0] — 2026-05-05 · Sprint 112

### Added
- `GET /metrics/skill-analyses?skill=&days=30` — drill-down: analyses that used a given skill
- `MetricsResponse.daily_cost` — daily USD cost by date key (`YYYY-MM-DD`)
- `DailyCostTrendChart` (recharts LineChart) in Dashboard
- `SkillAnalysesDrilldown` — detail table when clicking a pie slice
- `SkillCostPieChart` is now clickable — `onSkillClick` callback

### Tests
- +5 CI · +10 Vitest

---

## [9.8.0] — 2026-04-28 · Sprint 109

### Added
- **Screener v2** — persistent sort (5 columns, localStorage), composite label filters (chips), freshness column (relative date + stale badge > 24h), filtered CSV export (BOM UTF-8)
- `ScreenEntry.analyzed_at` — ISO date of underlying analysis (cache or fresh)
- `frontend/src/lib/screenerView.ts` — pure helper functions (sort/filter persistence, freshness formatting, CSV builder)

### Tests
- +3 CI · +21 Vitest

---

## [9.7.0] — 2026-04-21 · Sprint 107

### Added
- **Dashboard v2 — detailed metrics** — 4 recharts charts: top tickers (bar), cost per skill (pie), cache hit rate by workflow (bar), alerts timeline (bar)
- `MetricsResponse` extended: `skills_cost`, `cache_by_workflow`
- Period selector (7/30/90 days) driving `GET /metrics` + `GET /alerts`

### Tests
- +4 CI · +18 Vitest

---

## [9.6.0] — 2026-04-14 · Sprint 106

### Added
- **Semantic search page** (`/recherche`) — natural language queries on RAG corpus (`investment_knowledge`)
- `GET /semantic-search?q=&k=5` — `rag_enabled=false` + empty results if `OPENAI_API_KEY` absent
- `app.state.rag_service` exposed in FastAPI lifespan

### Tests
- +5 CI · +6 Vitest

---

## [9.5.0] — 2026-04-07 · Sprint 100

### Changed
- Repo structure cleanup for public GitHub: 9 prompts → `.claude/prompts/`, tests flat → 5 subdirectories (`api/`, `services/`, `skills/`, `workers/`, `orchestrator/`)
- `.gitignore` — `analyses/` + `.claude/settings.local.json` added; both untracked

---

## [9.4.0] — 2026-03-31 · Sprint 99

### Added
- **Alerts page** (`/alerts`) — Celery alert history table (ESG · composite · price) with badge-colored type column
- `alert_history` table + `AlertHistoryService.record()` + `GET /alerts?limit=50`

### Tests
- +3 CI · +5 Vitest

---

## [9.3.0] — 2026-03-24 · Sprint Login

### Added
- **Full auth system** — httpOnly JWT cookies (15 min) + refresh token rotation + CSRF double-submit + argon2 + rate limiting (5/15 min Redis)
- 9 `/auth/*` endpoints: register, login, logout, refresh, me, forgot-password, reset-password, mfa-setup-stub, mfa-verify-stub
- 4 React pages: `/login`, `/register`, `/forgot-password`, `/reset-password`
- `AuthContext` + `ProtectedRoute` — session restored from cookie on mount

### Tests
- +13 CI · +7 Vitest

---

## [9.1.0] — 2026-03-17 · Sprint 98

### Added
- `LICENSE` (MIT 2026), `CONTRIBUTING.md`, `SECURITY.md`
- `.github/` — issue templates (bug/feature), PR template
- `pyproject.toml` — ruff + mypy configuration
- `frontend/.eslintrc.cjs` — ESLint + @typescript-eslint + react-hooks
- `.github/workflows/ci.yml` — 4 jobs: test-backend, test-frontend, lint, typecheck
- `.github/dependabot.yml` — pip + npm weekly

---

## [9.0.0] — 2026-03-10 · Sprint 97

### Added
- `CompositeSparkline` recharts component in `WatchlistTable` — 30-day trend per ticker

### Tests
- +5 Vitest

---

## [8.7.0] — 2026-02-24 · Sprint 94

### Added
- `run_esg_degradation_check` Celery task (Sunday 12:00 UTC) — detects ESG score drop vs previous
- `POST /watchlist/check-esg-degradation` (admin)
- `EsgHistoryService.get_latest_previous()` — OFFSET 1 query

### Tests
- +5 CI

---

## [8.6.0] — 2026-02-17 · Sprint 93

### Added
- Streaming SSE toggle in `ComparePage` — `streamAnalyze` opt-in, skill-by-skill display, `Promise.race` 60s timeout

### Tests
- +5 Vitest

---

## [8.5.0] — 2026-02-10 · Sprint 92

### Added
- `GET /watchlist/export.xlsx` now includes latest annotation per ticker (second `LEFT JOIN LATERAL`)

### Tests
- +3 CI

---

## [8.4.0] — 2026-02-03 · Sprint 91

### Added
- `PATCH /watchlist/{id}/price-threshold` — configurable price alert threshold per ticker
- Inline edit column "Seuil Prix (%)" in `WatchlistTable`

### Tests
- +3 CI · +5 Vitest

---

## [8.3.0] — 2026-01-27 · Sprint 90

### Changed
- History pagination migrated from cursor (`before=ISO8601`) to offset/limit (`GET /history-paged`) with `total_count` and numbered UI controls

### Tests
- +7 CI · +4 Vitest

---

## [8.2.0] — 2026-01-20 · Sprint 89

### Added
- `esg_score_history` table + `EsgHistoryService` + `GET /esg-history/{ticker}`
- `EsgHistoryChart` recharts LineChart with reference lines at 10 (FORT) and 5 (MODÉRÉ) in `EsgPage`

### Tests
- +6 CI · +4 Vitest

---

## [8.1.0] — 2026-01-13 · Sprint 88

### Added
- Monthly PDF report now includes ESG section (Ticker / Score ESG / Verdict / Seuil) when at least one ticker has a score
- `esg_utils.py` extracted helper `esg_verdict()` to avoid circular import

### Tests
- +3 CI

---

## [8.0.0] — 2026-01-06 · Sprint 87

### Added
- "Analyser" opt-in button in `ComparePage` for tickers with `analysis_id === null`
- `Promise.race` 60s timeout; inline error with 5s auto-dismiss

### Tests
- +5 Vitest

---

## [7.9.0] — 2025-12-30 · Sprint 86

### Added
- `SlackService` (4 async methods, httpx retry) — no-op if `SLACK_WEBHOOK_URL` absent
- Celery tasks `run_scheduled_screener` and `run_monthly_report` send Slack summaries
- `.env.example` — `SLACK_WEBHOOK_URL`

### Tests
- +3 CI

---

## [7.7.0] — 2025-12-15 · Sprint 84

### Added
- `PATCH /watchlist/{id}/esg-threshold` — per-ticker ESG alert threshold
- Inline edit column "Seuil ESG" in `WatchlistTable`

### Tests
- +3 CI · +5 Vitest

---

## [7.5.0] — 2025-12-01 · Sprint 82

### Added
- **ESG page** (`/esg`) — sortable table with ESG scores and badges (FORT / MODÉRÉ / FAIBLE) for all watchlist tickers
- `GET /watchlist/esg-scores`

### Tests
- +3 CI · +5 Vitest

---

## [7.4.0] — 2025-11-17 · Sprint 81

### Added
- **Monthly PDF report** — `MonthlyReportService` (ReportLab), `GET /monthly-report`, `run_monthly_report` Celery task (1st of month, 08:00 UTC)

### Tests
- +10 CI

---

## [7.3.0] — 2025-11-03 · Sprint 80

### Added
- **Compare page** (`/compare`) — multi-skill side-by-side comparison for 2–5 tickers (historical data only)
- `POST /compare` + `CompareService`

### Tests
- +10 CI · +5 Vitest

---

## [7.2.0] — 2025-10-20 · Sprint 79

### Added
- Date range filter on history — `GET /history?from_dt=&to_dt=` + "Du" / "Au" fields in `HistoryPage` with from > to validation

### Tests
- +5 CI · +5 Vitest

---

## [7.1.0] — 2025-10-06 · Sprint 78

### Added
- Annotations on analyses — `annotations` table, `POST/GET /annotations`, `AnnotationSection` accordion in `HistoryTable`

### Tests
- +10 CI · +5 Vitest

---

## [7.0.0] — 2025-09-22 · Sprint 77

### Added
- ESG watchlist alerts — `esg_alert_threshold`, `last_esg_score` on `WatchlistEntry`; `send_esg_alert()` in `WebhookService`; ESG badge in `WatchlistTable`

### Tests
- +13 CI · +6 Vitest

---

## [6.9.0] — 2025-09-08 · Sprint 76

### Added
- `GET /watchlist/export.pdf` — watchlist PDF report (composite scores + verdicts + top picks)
- "Exporter PDF" button in `WatchlistPage`

### Tests
- +13 CI · +5 Vitest

---

## [6.8.0] — 2025-08-25 · Sprint 75

### Added
- `esg-simplified` SKILL.md + 5 references — all 16 tier2 skills now documented in `.claude/skills/`
- RAG corpus complete (~67 reference documents)

---

## [6.3.0] — 2025-07-14 · Sprint 70

### Added
- **ESG skill** (`esg_simplified`) — 15 criteria (5E + 5S + 5G), proxy-based scoring, `esg_input`/`esg` in `AnalyzeRequest`/`AnalyzeResponse`

### Tests
- +17 CI

---

## [6.2.0] — 2025-07-07 · Sprint 69

### Added
- "Score depuis cache" badge in `AnalyzePage` when `depuis_cache_composite=True`

### Tests
- +5 Vitest

---

## [6.1.0] — 2025-06-30 · Sprint 68

### Added
- "Télécharger PDF" button in `HistoryPage` + per-ticker PDF button in `WatchlistTable`

### Tests
- +6 Vitest

---

## [6.0.0] — 2025-06-23 · Sprint 67

### Added
- **Admin page** (`/admin`) — API key management (create / list / revoke), route `/admin`, `403` error handling

### Tests
- +6 Vitest

---

## [5.9.0] — 2025-06-09 · Sprint 66

### Added
- `EvalDriftSection` in `DashboardPage` — progress bar + badges from `GET /telemetry/eval-drift`

### Tests
- +5 Vitest

---

## [5.8.0] — 2025-05-26 · Sprint 65

### Added
- Circuit breaker: composite_score cached < 24h triggers early exit (`depuis_cache_composite`) — skips re-analysis

### Tests
- +10 CI

---

## [5.7.0] — 2025-05-12 · Sprint 64

### Added
- `run_scheduled_screener` Celery beat task (Sunday 11:00 UTC) — watchlist screener + webhook PDF if FORT results

### Tests
- +14 CI

---

## [5.6.0] — 2025-04-28 · Sprint 63

### Added
- Per-ticker PDF report — `PdfReportService` (3 pages ReportLab), `GET /ticker-report/{ticker}?days=90`

### Tests
- +13 CI

---

## [5.5.0] — 2025-04-14 · Sprint 62

### Added
- Multi-user API keys — `api_keys` table, `ApiKeyService`, `BearerTokenMiddleware` (backward-compatible), `POST/GET/DELETE /admin/keys`

### Tests
- +12 CI

---

## [5.4.0] — 2025-03-31 · Sprint 61

### Added
- `EvalDriftService` — detects regression against golden eval dataset; `run_eval_drift_check` Celery task; `GET /telemetry/eval-drift`

### Tests
- +19 CI

---

## [5.3.0] — 2025-03-17 · Sprint 60

### Added
- `CompositeScoreChart` recharts `LineChart` in `DashboardPage` — 30-day composite score evolution per ticker

### Tests
- +7 Vitest · +5 CI

---

## [5.2.0] — 2025-03-03 · Sprint 59

### Added
- `GET /watchlist/export.xlsx` — Excel export (openpyxl) with composite score, verdicts, ESG, price

### Tests
- +15 CI

---

## [5.1.0] — 2025-02-17 · Sprint 58

### Added
- 3 POST `/screen` filters: `composite_label`, `min_composite_score`, `filter_workflow`

### Tests
- +15 CI

---

## [5.0.0] — 2025-02-03 · Sprint 57

### Added
- `composite_score_history` table + `CompositeHistoryService.record()`/`get_history()` + `GET /composite-history/{ticker}`

### Tests
- +10 CI

---

## [4.9.0] — 2025-01-20 · Sprint 56

### Added
- `WebhookService` (3 async methods, httpx retry, `X-Webhook-Secret` header) + `GET /telemetry/webhook`
- `.env.example` — `WEBHOOK_URL`, `WEBHOOK_SECRET`

### Tests
- +12 CI

---

## [4.8.0] — 2025-01-06 · Sprint 55

### Added
- Multi-model eval suite — `multi_model_golden.json` (6 Haiku cases) + 7 evals + 14 CI tests

### Tests
- +14 CI

---

## [4.7.0] — 2024-12-23 · Sprint 54

### Added
- Screener golden dataset — `golden_screener_dataset.json` (10 tickers) + 5 evals + 12 CI tests

### Tests
- +12 CI

---

## [4.6.0] — 2024-12-09 · Sprint 52 (autonomous session)

### Added
- Haiku routing for lightweight skills, screener, CSV/Excel export, watchlist alerts, backtesting, dashboard, Celery scheduler

### Tests
- 1 063 CI total

---

## [3.7.0] — 2024-10-14 · Sprint 43

### Added (milestone)
- **Tool Use migration complete** — all 15 skills migrated from legacy JSON schema to Anthropic Tool Use
- 942 CI tests total

---

## [1.0.0] — 2024-06-01 · Phase 0

### Added (initial release)
- FastAPI API + `graham_analysis` skill + PostgreSQL
- Basic analysis endpoint `POST /analyze`
- Prompt caching enabled

---

*For the complete sprint-by-sprint history, see [`ROADMAP.md`](ROADMAP.md).*
