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
    price_at_analysis     NUMERIC(12,4),
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

-- Historique du composite_score — Sprint 57
CREATE TABLE IF NOT EXISTS composite_score_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker      TEXT NOT NULL,
    score       FLOAT NOT NULL,
    label       TEXT NOT NULL,
    workflow    TEXT NOT NULL DEFAULT 'value_graham',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_csh_ticker_recorded ON composite_score_history(ticker, recorded_at DESC);

-- Historique des scores ESG — Sprint 89
CREATE TABLE IF NOT EXISTS esg_score_history (
    id          BIGSERIAL    PRIMARY KEY,
    ticker      TEXT         NOT NULL,
    score       DOUBLE PRECISION NOT NULL,
    verdict     TEXT         NOT NULL,
    recorded_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_esg_hist_ticker_recorded ON esg_score_history (ticker, recorded_at DESC);

-- Migration Sprint 24 (DB existante) :
-- ALTER TABLE watchlist
--     ADD COLUMN IF NOT EXISTS last_intrinsic_value      NUMERIC(10,4),
--     ADD COLUMN IF NOT EXISTS last_price_checked        NUMERIC(10,4),
--     ADD COLUMN IF NOT EXISTS price_alert_threshold_pct NUMERIC(5,4) NOT NULL DEFAULT 0.10;

-- Clés API multi-utilisateurs — Sprint 62
CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT          NOT NULL,
    key_hash     TEXT          NOT NULL UNIQUE,  -- SHA-256 du token Bearer
    role         TEXT          NOT NULL DEFAULT 'reader',  -- 'admin' | 'reader'
    active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ   -- NULL = pas d'expiration
);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active   ON api_keys (active);

-- Recherche full-text dans l'historique — Sprint 73
-- pg_trgm permet les index GIN pour les requêtes ILIKE '%term%'
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_history_gin_ticker    ON analysis_history USING GIN(ticker gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_history_gin_workflow  ON analysis_history USING GIN(workflow_name gin_trgm_ops);

-- Migration Sprint 73 (DB existante) :
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE INDEX IF NOT EXISTS idx_history_gin_ticker   ON analysis_history USING GIN(ticker gin_trgm_ops);
-- CREATE INDEX IF NOT EXISTS idx_history_gin_workflow ON analysis_history USING GIN(workflow_name gin_trgm_ops);
