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
  cost_usd: number
  created_at: string
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
}

// ---- Screener ----
export interface ScreenEntry {
  ticker: string
  defensive_score: number | null
  verdict: string | null
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
  ticker: string
  entries: HistoryEntry[]
  next_before: string | null
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
