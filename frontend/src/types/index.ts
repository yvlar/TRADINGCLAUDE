// ---- Ratios Qualité bénéfices (Beneish M-Score, Altman Z-Score, Piotroski F-Score) ----
export interface EarningsQualityRatios {
  // Compte de résultat (T = exercice courant, T-1 = exercice précédent)
  sales_t: number
  sales_t1: number
  cogs_t: number
  cogs_t1: number
  net_income_t: number
  cfo_t: number
  ebit_t?: number | null
  sga_t?: number | null
  sga_t1?: number | null
  depreciation_t?: number | null
  depreciation_t1?: number | null
  // Bilan T
  receivables_t: number
  current_assets_t: number
  current_liabilities_t: number
  total_assets_t: number
  inventory_t?: number | null
  ppe_net_t?: number | null
  ppe_gross_t?: number | null
  ltd_t?: number | null
  retained_earnings_t?: number | null
  total_liabilities_t?: number | null
  market_cap_t?: number | null
  book_equity_t?: number | null
  // Bilan T-1
  receivables_t1: number
  total_assets_t1: number
  current_assets_t1?: number | null
  current_liabilities_t1?: number | null
  inventory_t1?: number | null
  ppe_net_t1?: number | null
  ppe_gross_t1?: number | null
  ltd_t1?: number | null
  shares_issued_net?: boolean | null
}

// ---- Réponse extraction automatique ----
export interface ExtractResponse {
  graham: GrahamRatios
  earnings_quality: EarningsQualityRatios | null
}

// ---- Ratios Graham ----
export interface GrahamRatios {
  pe: number | null
  pb: number | null
  current_ratio: number | null
  debt_equity: number | null
  eps_growth_10y: number | null
  price: number | null
  book_value: number | null
  eps_ttm?: number | null
  revenue_bn?: number | null
  dividend_years?: number | null
  no_deficit_years?: number | null
}

// ---- Critères Graham ----
export interface GrahamCriterion {
  numero: number
  nom: string
  passe: boolean
  valeur_observee: string
  seuil: string
  commentaire: string
}

export interface GrahamAnalysisOutput {
  ticker: string
  profil_applique: string
  defensive_score: number
  enterprising_score: number
  criteria_defensif: GrahamCriterion[]
  criteria_entreprenant: GrahamCriterion[]
  valeur_intrinseque_simple: number | null
  valeur_intrinseque_ajustee: number | null
  marge_securite: number | null
  drapeaux_rouges: string[]
  verdict: string
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd?: number
}

// ---- Autres outputs skills (structure générique pour affichage) ----
export interface SkillOutput {
  verdict?: string
  verdict_detail?: string
  [key: string]: unknown
}

// ---- Score composite pondéré (Sprint 38) ----
export interface CompositeScore {
  score: number
  label: string
  skills_inclus: string[]
  skills_exclus: string[]
  detail: Record<string, number>
}

// ---- ESG Simplifié (Sprint 70) ----
export interface EsgInput {
  ticker: string
  sector?: string | null
  revenue_bn?: number | null
  roe?: number | null
  debt_equity?: number | null
  dividend_years?: number | null
  eps_growth_10y?: number | null
}

export interface EsgCritere {
  dimension: 'E' | 'S' | 'G'
  nom: string
  passe: boolean
  observation: string
  proxy_utilise: string
}

export interface EsgOutput {
  ticker: string
  esg_score: number
  e_score: number
  s_score: number
  g_score: number
  criteres: EsgCritere[]
  verdict: 'ESG_FORT' | 'ESG_MODERE' | 'ESG_FAIBLE'
  verdict_detail: string
  limites: string[]
  citations: unknown[]
  cost_usd?: number
}

// ---- AnalyzeResponse ----
export interface AnalyzeResponse {
  analysis_id: string
  ticker: string
  workflow: string
  skills_applied: string[]
  graham: GrahamAnalysisOutput | null
  earnings_quality: SkillOutput | null
  dorsey: SkillOutput | null
  buffett: SkillOutput | null
  valuation: SkillOutput | null
  thesis: SkillOutput | null
  munger: SkillOutput | null
  canadian_tax: SkillOutput | null
  lynch: SkillOutput | null
  fisher: SkillOutput | null
  klarman: SkillOutput | null
  greenblatt: SkillOutput | null
  damodaran: SkillOutput | null
  marks: SkillOutput | null
  pabrai: SkillOutput | null
  esg: SkillOutput | null
  cost_usd: number
  created_at: string
  inter_skill_conflicts: string[]
  composite_score: CompositeScore | null
  depuis_cache_composite?: boolean
}

// ---- AnalyzeRequest ----
export interface AnalyzeRequest {
  ticker: string
  ratios: GrahamRatios | null
  workflow: string
  thesis_ratios?: boolean
  munger_ratios?: boolean
  earnings_ratios?: EarningsQualityRatios | null
  dorsey_ratios?: Record<string, unknown> | null
  buffett_ratios?: Record<string, unknown> | null
  valuation_ratios?: Record<string, unknown> | null
  tax_input?: Record<string, unknown> | null
  lynch_ratios?: Record<string, unknown> | null
  klarman_input?: Record<string, unknown> | null
  greenblatt_input?: Record<string, unknown> | null
  damodaran_input?: Record<string, unknown> | null
  marks_input?: Record<string, unknown> | null
  pabrai_input?: Record<string, unknown> | null
  fisher_input?: Record<string, unknown> | null
  esg_input?: EsgInput | null
}

// ---- Historique composite_score (Sprint 57) ----
export interface CompositeHistoryPoint {
  id: string
  ticker: string
  score: number
  label: string  // "FORT" | "MODERE" | "FAIBLE"
  workflow: string
  recorded_at: string  // ISO 8601
}

// ---- Historique ESG (Sprint 89) ----
export interface EsgHistoryPoint {
  id: string
  ticker: string
  score: number
  verdict: string  // "ESG_FORT" | "ESG_MODERE" | "ESG_FAIBLE" | "N/A"
  recorded_at: string  // ISO 8601
}

export interface EsgHistoryResponse {
  ticker: string
  points: EsgHistoryPoint[]
}

// ---- Screener ----
export interface ScreenEntry {
  ticker: string
  defensive_score: number | null
  verdict: string | null
  composite_score: number | null
  composite_label: string | null
  workflow_utilise: string
  cost_usd: number
  depuis_cache: boolean
  erreur: string | null
}

export interface ScreenResult {
  tickers_analyses: number
  tickers_echec: number
  tickers_depuis_cache: number
  cout_total_usd: number
  resultats: ScreenEntry[]
  workflow: string
  duration_ms: number
}

export interface ScreenRequest {
  tickers: string[]
  workflow: string
  ratios_map?: Record<string, GrahamRatios> | null
  max_parallel?: number
}

// ---- History ----
export interface HistoryEntry {
  analysis_id: string
  ticker: string
  workflow: string
  skills_applied: string[]
  cost_usd: number
  defensive_score: number | null
  earnings_verdict: string | null
  graham_verdict: string | null
  created_at: string
}

export interface HistoryResponse {
  ticker: string | null
  entries: HistoryEntry[]
  next_before: string | null
}

// Sprint 90 — pagination offset/limit
export interface PagedHistoryResponse {
  ticker: string | null
  q: string | null
  entries: HistoryEntry[]
  page: number
  page_size: number
  total_count: number
  total_pages: number
}

// ---- Performance rétrospective (Sprint 39) ----
export interface PerformanceEntry {
  analysis_id: string
  created_at: string
  price_at_analysis: number | null
  price_current: number | null
  rendement_pct: number | null
  composite_score: number | null
  workflow: string
}

export interface PerformanceResponse {
  ticker: string
  entries: PerformanceEntry[]
}

// ---- Analyses récentes (localStorage Dashboard Sprint 41) ----
export interface RecentAnalysis {
  ticker: string
  composite_score: CompositeScore | null
  inter_skill_conflicts: string[]
  workflow: string
  created_at: string
}

// ---- WebSocket métriques ----
export interface MetricsPayload {
  jobs_en_cours: number
  jobs_echoues_1h: number
  cout_total_1h_usd: number
  cache_hit_ratio: number
  analyses_24h: number
  timestamp: string
}

// ---- Watchlist ----
export interface WatchlistEntry {
  id: string
  ticker: string
  workflow: string
  last_analyzed_at: string | null
  last_score: number | null
  last_intrinsic_value: number | null
  last_price_checked: number | null
  price_alert_threshold_pct: number
  created_at: string
  last_composite_score: number | null
  composite_alert_threshold: number
  score_alerte_min: number | null
  esg_alert_threshold: number
  last_esg_score: number | null
}

export interface WatchlistCreate {
  ticker: string
  workflow?: string
  price_alert_threshold_pct?: number
}

export interface PriceStatus {
  ticker: string
  current_price: number | null
  intrinsic_value: number | null
  ecart_pct: number | null
  alerte: boolean
}

// ---- SSE Streaming ----
export type SSEEventType = 'skill_start' | 'skill_result' | 'complete' | 'error' | 'cached'

export interface SSESkillStart {
  skill_id: string
}

export interface SSESkillResult {
  skill_id: string
  result: Record<string, unknown>
}

export type SSEEvent =
  | { type: 'skill_start'; data: SSESkillStart }
  | { type: 'skill_result'; data: SSESkillResult }
  | { type: 'complete'; data: AnalyzeResponse }
  | { type: 'error'; data: { message: string } }
  | { type: 'cached'; data: AnalyzeResponse }

// ---- Eval Drift (Sprint 61 backend, Sprint 66 frontend) ----
export interface EvalDriftResult {
  dataset: string
  concordance_rate: number  // 0.0 à 1.0
  threshold: number
  alert: boolean
  cases_total: number
  cases_pass: number
  recorded_at: string  // ISO 8601
}

// ---- Admin API Keys (Sprint 67) ----
export interface ApiKey {
  id: string
  name: string
  role: string        // "admin" | "user"
  created_at: string  // ISO 8601
  last_used_at: string | null
  is_active: boolean
}

export interface ApiKeyCreate {
  name: string
  role?: string  // défaut "user"
}

// ---- Annotations (Sprint 78) ----
export interface Annotation {
  annotation_id: string
  analysis_id: string
  note: string
  created_at: string
  updated_at: string
}

export interface AnnotationCreate {
  analysis_id: string
  note: string
}

// ---- ESG Watchlist scores (Sprint 82) ----
export interface WatchlistEsgEntry {
  ticker: string
  last_esg_score: number | null
  esg_alert_threshold: number
  last_analyzed_at: string | null
}

export interface WatchlistEsgResponse {
  entries: WatchlistEsgEntry[]
}

// ---- Comparaison tickers (Sprint 80) ----
export interface TickerComparison {
  ticker: string
  analysis_id: string | null
  graham_verdict: string | null
  graham_score: number | null
  buffett_verdict: string | null
  dorsey_moat_type: string | null
  composite_score: number | null
  composite_label: string | null
  created_at: string | null
}

export interface CompareResponse {
  tickers: string[]
  comparisons: TickerComparison[]
}

// ---- Workflow ----
export interface WorkflowOption {
  value: string
  label: string
  description: string
}

export const WORKFLOWS: WorkflowOption[] = [
  {
    value: 'value_graham',
    label: 'Value Graham',
    description: 'Graham + Earnings + Valorisation + Thèse fiscalité',
  },
  {
    value: 'compounder_buffett',
    label: 'Compounder Buffett',
    description: '4 filtres Buffett + Moat Dorsey + Fisher + Valorisation',
  },
  {
    value: 'fast_grower_lynch',
    label: 'Fast Grower Lynch',
    description: 'PEG Lynch + Narrative Damodaran + Valorisation',
  },
  {
    value: 'special_situation',
    label: 'Situation Spéciale',
    description: 'Graham + Marge sécurité Klarman + Greenblatt',
  },
  {
    value: 'distressed_pabrai',
    label: 'Distressed Pabrai',
    description: 'Dhandho Pabrai + Klarman + Earnings Quality',
  },
]
