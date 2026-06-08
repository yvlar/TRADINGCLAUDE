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
  // Traçabilité source+date (Sprint 138) — miroir du payload backend, parité avec GrahamRatios
  ratios_fetched_at?: string | null
  ratios_source?: string | null
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
  eps_growth_total: number | null
  eps_growth_years?: number | null
  price: number | null
  book_value: number | null
  eps_ttm?: number | null
  revenue_bn?: number | null
  dividend_years?: number | null
  no_deficit_years?: number | null
  ratios_fetched_at?: string | null
  ratios_source?: string | null
  ratios_provenance?: Record<string, string> | null
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
  graham_number: number | null
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

// ---- Earnings Quality Output (Sprint 118) ----
export interface MScoreDetail {
  dsri: number | null
  gmi: number | null
  aqi: number | null
  sgi: number | null
  depi: number | null
  sgai: number | null
  tata: number | null
  lvgi: number | null
  m_score: number | null
  interpretation: string
}

export interface ZScoreDetail {
  variante: string
  // Termes X1-X5 calculés en Python et persistés (Sprint 131) ; null pour banques (is_financial)
  x1: number | null
  x2: number | null
  x3: number | null
  x4: number | null
  x5: number | null
  z_score: number | null
  interpretation: string
}

export interface FScoreCriterion {
  nom: string
  passe: boolean
  detail: string
}

export interface FScoreDetail {
  criteria: FScoreCriterion[]
  f_score: number
  interpretation: string
}

export interface CScoreSignal {
  nom: string
  present: boolean
  detail: string
}

export interface CScoreDetail {
  signaux: CScoreSignal[]
  c_score: number
  interpretation: string
}

export interface SloanDetail {
  accrual_ratio: number | null
  interpretation: string
}

export interface EarningsQualityOutput {
  ticker: string
  is_financial: boolean
  m_score: MScoreDetail
  z_score: ZScoreDetail
  f_score: FScoreDetail
  c_score: CScoreDetail
  sloan: SloanDetail
  drapeaux_rouges: string[]
  verdict: string
  verdict_detail: string
  confidence_score: number
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Investment Thesis Builder Output (Sprint 118) ----
export interface ThesisScenario {
  probabilite: number
  rendement_cible: number
  hypotheses: string[]
}

export interface ThesisBuilderOutput {
  ticker: string
  scenario_bull: ThesisScenario
  scenario_base: ThesisScenario
  scenario_bear: ThesisScenario
  kill_criteria: string[]
  devils_advocate: string
  position_size_pct: number
  verdict_final: string
  synthese_narrative: string
  citations: unknown[]
  cost_usd: number
}

// ---- Dorsey Moat Output (Sprint 119) ----
export interface MoatSource {
  source: string // "intangibles" | "switching_costs" | "network_effects" | "cost_advantages" | "efficient_scale"
  present: boolean
  intensite: string // "FORTE" | "MODÉRÉE" | "FAIBLE" | "ABSENTE"
  justification: string
}

export interface DorseyMoatOutput {
  ticker: string
  moat_type: string // "WIDE" | "NARROW" | "NONE"
  sources_identifiees: MoatSource[]
  roic_durability: string // "FORTE" | "MODÉRÉE" | "FAIBLE"
  verdict_detail: string
  drapeaux_rouges: string[]
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
  confidence_score: number
}

// ---- Buffett Quality Output (Sprint 119) ----
export interface BuffettFiltre {
  filtre: string
  passe: boolean
  score: number
  justification: string
}

export interface BuffettQualityOutput {
  ticker: string
  filtres: BuffettFiltre[]
  owner_earnings: number | null // par action (comme l'EPS)
  quality_score: number // 0-4
  verdict: string // "COMPOUNDER" | "QUALITE_CORRECTE" | "REJETER"
  verdict_detail: string
  drapeaux_rouges: string[]
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
  confidence_score: number
}

// ---- Stock Valuation Output (Sprint 119) ----
export interface ValuationMethod {
  methode: string // "dcf" | "comparables" | "sectoriel"
  valeur: number | null
  hypotheses: string
}

export interface SensitivityMatrix {
  wacc_range: number[]
  growth_range: number[]
  values: number[][]
}

export interface StockValuationOutput {
  ticker: string
  methodes: ValuationMethod[]
  fourchette_basse: number
  fourchette_centrale: number
  fourchette_haute: number
  marge_securite_composite: number // fraction : positif = sous-évalué
  matrice_sensibilite: SensitivityMatrix
  verdict: string // "SOUS_EVALUE" | "JUSTE_VALEUR" | "SUREVALUE"
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Lynch Categories Output (Sprint 120) ----
export interface LynchCategoriesOutput {
  ticker: string
  categorie: string // SLOW_GROWER|STALWART|FAST_GROWER|CYCLICAL|TURNAROUND|ASSET_PLAY
  peg_ratio: number | null // pe / (eps_growth_5y * 100), null si croissance <= 0
  tenbagger_potential: boolean
  score_croissance: number // 0-5
  verdict: string // EXCELLENT|BON|MOYEN|EVITER
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Greenblatt Magic Formula Output (Sprint 120) ----
export interface GreenblattOutput {
  ticker: string
  roc: number // EBIT / (NWC + NFA), fraction
  earnings_yield: number // EBIT / EV, fraction
  verdict: string // TOP_DECILE|BON|MOYEN|EVITER
  situations_speciales: string[]
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Munger Mental Models Output (Sprint 120) ----
export interface BiaisCognitif {
  nom: string
  description: string
  impact_sur_these: string // MINEUR | MODERE | MAJEUR
}

export interface MungerOutput {
  ticker: string
  biais_detectes: BiaisCognitif[]
  inversion_analysis: string
  lollapalooza_risk: boolean
  verdict_comportemental: string // CONFIANCE_JUSTIFIEE | BIAIS_DETECTE | ALERTE_ROUGE
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Klarman Margin of Safety Output (Sprint 120) ----
export interface KlarmanOutput {
  ticker: string
  situation_type_qualifie: string // NET_NET|ACTIFS_CACHES|DISTRESSED|SPECIAL_SITUATION|VALEUR_CLASSIQUE
  marge_securite_score: number // 0-10
  preservation_capital_score: number // 0-10
  discount_to_intrinsic: number | null // fraction : positif = décote sous la valeur intrinsèque
  verdict: string // OPPORTUNITE_FORTE|OPPORTUNITE_MODEREE|ATTENDRE|PASSER
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Fisher Scuttlebutt Output (Sprint 121) ----
export interface FisherPoint {
  point: number // 1-15
  titre: string
  score: number // 0-2
  commentaire: string
}

export interface FisherOutput {
  ticker: string
  fisher_score: number // 0-30 (somme des 15 points)
  points_evalues: FisherPoint[] // exactement 15
  management_quality: string // EXCEPTIONNEL|BON|ADEQUAT|MEDIOCRE
  verdict: string // ACHAT_FORT|ACHAT|CONSERVER|EVITER
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Damodaran Narrative & Numbers Output (Sprint 121) ----
export interface DamodaranOutput {
  ticker: string
  test_coherence: string // POSSIBLE|PLAUSIBLE|PROBABLE|INCOHERENT
  erp_implied: number | null // prime de risque actions implicite
  narrative_strength: number // 0-10
  divergences_detectees: string[]
  verdict: string // NARRATIVE_FORTE|NARRATIVE_ACCEPTABLE|NARRATIVE_FAIBLE|NARRATIVE_INCOHERENTE
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Marks Cycles & Risk Output (Sprint 121) ----
export interface MarksOutput {
  position_cycle: string // PESSIMISME_EXCESSIF|PESSIMISME|NEUTRE|OPTIMISME|EUPHORIE
  pendule_score: number // -5 à +5 ; négatif = opportunité contrariante
  second_level_insight: string
  recommandation_timing: string // ACHETER_AGRESSIF|ACHETER_PRUDEMMENT|ATTENDRE|REDUIRE|VENDRE
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Pabrai Dhandho Output (Sprint 121) ----
export interface DhandhoPrincipe {
  nom: string
  satisfait: boolean
  commentaire: string
}

export interface PabraiOutput {
  ticker: string
  principes_dhandho: DhandhoPrincipe[] // exactement 9
  heads_i_win_score: number // 0-9 (principes satisfaits)
  asymetrie: number // upside / abs(downside), >= 0
  kelly_fractionnel: number | null // Kelly / 4, ou null si non calculable
  verdict: string // DHANDHO_FORT|DHANDHO_MOYEN|PAS_DHANDHO
  verdict_detail: string
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
}

// ---- Canadian Tax Output (Sprint 121) ----
export interface CanadianTaxOutput {
  ticker: string
  compte_recommande: string // CELI | REER | CELIAPP | NON_ENREGISTRE
  justification_fiscale: string
  impact_retenue_us: string | null // retenue à la source US si applicable
  strategie_smith_manoeuvre: boolean
  taux_inclusion_gain_capital: number // 0.50 = 50% inclusion
  recommandation_prochaine_etape: string[]
  citations: unknown[]
  cost_usd: number
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
  earnings_quality: EarningsQualityOutput | null
  dorsey: DorseyMoatOutput | null
  buffett: BuffettQualityOutput | null
  valuation: StockValuationOutput | null
  thesis: ThesisBuilderOutput | null
  munger: MungerOutput | null
  canadian_tax: CanadianTaxOutput | null
  lynch: LynchCategoriesOutput | null
  fisher: FisherOutput | null
  klarman: KlarmanOutput | null
  greenblatt: GreenblattOutput | null
  damodaran: DamodaranOutput | null
  marks: MarksOutput | null
  pabrai: PabraiOutput | null
  esg: SkillOutput | null
  cost_usd: number
  created_at: string
  inter_skill_conflicts: string[]
  composite_score: CompositeScore | null
  depuis_cache_composite?: boolean
  ratios_fetched_at?: string | null
  ratios_source?: string | null
  earnings_ratios_fetched_at?: string | null
  earnings_ratios_source?: string | null
  valuation_ratios_fetched_at?: string | null
  valuation_ratios_source?: string | null
  // Provenance par ratio Graham (clé yfinance de repli) — signal-only sur l'analyse rendue (Sprint 150)
  ratios_provenance?: Record<string, string> | null
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
  analyzed_at: string | null
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

// ---- Préférences Screener (Sprint 124 — persistance serveur) ----
export type ScreenerSortKey = 'score' | 'ticker' | 'cost' | 'composite' | 'freshness'

export interface ScreenerSortState {
  key: ScreenerSortKey
  asc: boolean
}

export interface ScreenerPreferences {
  sort: ScreenerSortState | null
  filter: string[] | null
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
  tags: string[]
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
export type SSEEventType = 'plan' | 'skill_start' | 'skill_result' | 'complete' | 'error' | 'cached'

export interface SSEPlan {
  skills: string[]
}

export interface SSESkillStart {
  skill_id: string
}

export interface SSESkillResult {
  skill_id: string
  result: Record<string, unknown>
}

export type SSEEvent =
  | { type: 'plan'; data: SSEPlan }
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

// ---- Journal d'audit (Sprint 180 — miroir de AuditLogEntry Pydantic) ----
export interface AuditLogEntry {
  id: string
  tenant_id: string | null  // UUID
  user_id: string | null    // UUID
  action: string
  cible_type: string
  cible_id: string | null
  metadata: Record<string, unknown>
  created_at: string        // ISO 8601
}

// ---- Annotations (Sprint 78) ----
export interface Annotation {
  annotation_id: string
  analysis_id: string
  note: string
  tags: string[]
  created_at: string
  updated_at: string
}

export interface AnnotationCreate {
  analysis_id: string
  note: string
  tags: string[]
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

// ---- Auth utilisateurs (Sprint login) ----
export interface User {
  id: string
  email: string
  role: string
  tenant_id: string
  tenant_name: string
  // plan tarifaire du tenant (`free`/`pro`) exposé au Sprint 173 — pilote le CTA Facturation
  plan: string
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
  remember_me?: boolean
}

export interface RegisterRequest {
  email: string
  password: string
}

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}

export interface AuthResponse {
  user: User
  message: string
}

// ---- Alertes Celery (Sprint 99) ----
export interface AlertEntry {
  id: number
  ticker: string
  type: string
  valeur: number | null
  seuil: number | null
  message: string | null
  created_at: string
}

export interface AlertsResponse {
  alerts: AlertEntry[]
}

// ---- Métriques agrégées /metrics (Dashboard v2 — Sprint 107) ----
// Champs en snake_case : ils reflètent la réponse JSON FastAPI (pas d'alias camelCase côté API)
export interface TickerMetrics {
  ticker: string
  analyses: number
  cost_usd: number
}

export interface MetricsResponse {
  period_days: number
  total_analyses: number
  total_cost_usd: number
  avg_cost_per_analysis: number
  cache_hit_ratio_avg: number
  top_tickers: TickerMetrics[]
  skills_usage: Record<string, number>
  skills_cost: Record<string, number>
  cache_by_workflow: Record<string, number>
  // coût USD total par jour (clé YYYY-MM-DD) — tendance quotidienne (Sprint 112)
  daily_cost: Record<string, number>
}

// ---- Drill-down coût par skill /metrics/skill-analyses (Sprint 112) ----
export interface SkillAnalysisEntry {
  analysis_id: string
  ticker: string
  workflow_name: string
  cost_usd: number
  created_at: string
}

export interface SkillAnalysesResponse {
  skill: string
  period_days: number
  entries: SkillAnalysisEntry[]
}

// ---- Consommation agrégée /usage (E4-S5, Sprint 170) — miroir de UsageResponse/UsageBySkill ----
// Champs en snake_case : reflètent la réponse JSON FastAPI (pas d'alias camelCase côté API)
export interface UsageBySkill {
  skill: string
  cost_usd: number
  tokens_input: number
  tokens_output: number
  events: number
}

export interface UsageResponse {
  period_days: number
  total_cost_usd: number
  total_tokens_input: number
  total_tokens_output: number
  by_skill: UsageBySkill[]
  // coût USD total par jour (clé YYYY-MM-DD), même forme que MetricsResponse.daily_cost
  daily_cost: Record<string, number>
}

// ---- État du report d'usage vers Stripe /usage/reporting (E5-S2) — miroir de UsageReportingResponse ----
export interface UsageReporting {
  // ISO 8601 ; null = jamais rapporté (ou pas d'abonnement) → pending couvre tout l'historique
  reported_through: string | null
  pending_events: number
}

// ---- État du quota mensuel /quota (E5-S6) — miroir de QuotaStatusResponse ----
export interface QuotaStatus {
  plan: string
  used: number
  // null = plan non résolu côté serveur (fail-open) → le client n'affiche pas de borne
  limit: number | null
  remaining: number | null
  reset_at: string // ISO 8601 — bascule du compteur mensuel (1er du mois suivant UTC)
}

// ---- Corps structuré du 429 quota (E5-S8) — miroir du detail de quota_exceeded_http ----
export interface QuotaErrorDetail {
  message: string
  plan: string
  used: number
  limit: number
  remaining: number
}

// ---- Recherche sémantique RAG (Sprint 106) ----
export interface SemanticSearchResult {
  source: string
  extrait: string
  score: number
}

export interface SemanticSearchResponse {
  query: string
  rag_enabled: boolean
  results: SemanticSearchResult[]
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
