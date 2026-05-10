-- Schéma Phase 0 — section 7.3 de l'architecture
-- Historique de toutes les analyses exécutées via le workflow company_analysis

CREATE TABLE analysis_history (
    id                    UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker                VARCHAR(20)   NOT NULL,
    workflow_name         VARCHAR(100)  NOT NULL DEFAULT 'company_analysis',
    skills_used           JSONB         NOT NULL DEFAULT '[]',
    input_data            JSONB         NOT NULL,
    result                JSONB         NOT NULL,
    cost_usd              NUMERIC(10,6) NOT NULL DEFAULT 0,
    tokens_input          INTEGER       NOT NULL DEFAULT 0,
    tokens_output         INTEGER       NOT NULL DEFAULT 0,
    tokens_cache_read     INTEGER       NOT NULL DEFAULT 0,
    tokens_cache_creation INTEGER       NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_history_ticker     ON analysis_history (ticker);
CREATE INDEX idx_history_workflow   ON analysis_history (workflow_name);
CREATE INDEX idx_history_created_at ON analysis_history (created_at DESC);

-- Watchlist persistante — Sprint 23 + Sprint 24
CREATE TABLE watchlist (
    id                           UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker                       VARCHAR(20)    NOT NULL,
    workflow                     VARCHAR(100)   NOT NULL DEFAULT 'value_graham',
    ratios                       JSONB,
    score_alerte_min             INTEGER,
    created_at                   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    last_analyzed_at             TIMESTAMPTZ,
    last_score                   INTEGER,
    last_verdict                 VARCHAR(50),
    -- Sprint 24 : alertes prix
    last_intrinsic_value         NUMERIC(10,4),
    last_price_checked           NUMERIC(10,4),
    price_alert_threshold_pct    NUMERIC(5,4)   NOT NULL DEFAULT 0.10
);

CREATE INDEX idx_watchlist_ticker ON watchlist (ticker);

-- Migration Sprint 24 (DB existante) :
-- ALTER TABLE watchlist
--     ADD COLUMN IF NOT EXISTS last_intrinsic_value      NUMERIC(10,4),
--     ADD COLUMN IF NOT EXISTS last_price_checked        NUMERIC(10,4),
--     ADD COLUMN IF NOT EXISTS price_alert_threshold_pct NUMERIC(5,4) NOT NULL DEFAULT 0.10;
