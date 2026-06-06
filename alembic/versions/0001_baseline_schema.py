"""baseline : schéma courant (init.sql + DDL inline du lifespan)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-06

Capture fidèle du schéma tel qu'il existe avant l'introduction d'Alembic :
`infra/postgres/init.sql` (Docker) complété par les CREATE/ALTER idempotents du
lifespan (`app/api/main.py`). Migration de référence — aucune nouvelle structure.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_BASELINE_DDL = """
CREATE TABLE IF NOT EXISTS analysis_history (
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
CREATE INDEX IF NOT EXISTS idx_history_ticker     ON analysis_history (ticker);
CREATE INDEX IF NOT EXISTS idx_history_workflow   ON analysis_history (workflow_name);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON analysis_history (created_at DESC);

CREATE TABLE IF NOT EXISTS watchlist (
    id                           UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker                       VARCHAR(20)    NOT NULL,
    workflow                     VARCHAR(100)   NOT NULL DEFAULT 'value_graham',
    ratios                       JSONB,
    score_alerte_min             INTEGER,
    created_at                   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    last_analyzed_at             TIMESTAMPTZ,
    last_score                   INTEGER,
    last_verdict                 VARCHAR(50),
    last_intrinsic_value         NUMERIC(10,4),
    last_price_checked           NUMERIC(10,4),
    price_alert_threshold_pct    NUMERIC(5,4)   NOT NULL DEFAULT 0.10
);
CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON watchlist (ticker);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_ticker_workflow ON watchlist (ticker, workflow);
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS last_composite_score FLOAT DEFAULT NULL;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS composite_alert_threshold FLOAT DEFAULT 15.0;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS esg_alert_threshold FLOAT DEFAULT 5.0;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS last_esg_score FLOAT DEFAULT NULL;

CREATE TABLE IF NOT EXISTS composite_score_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker      TEXT NOT NULL,
    score       FLOAT NOT NULL,
    label       TEXT NOT NULL,
    workflow    TEXT NOT NULL DEFAULT 'value_graham',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_csh_ticker_recorded ON composite_score_history(ticker, recorded_at DESC);

CREATE TABLE IF NOT EXISTS esg_score_history (
    id          BIGSERIAL    PRIMARY KEY,
    ticker      TEXT         NOT NULL,
    score       DOUBLE PRECISION NOT NULL,
    verdict     TEXT         NOT NULL,
    recorded_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_esg_hist_ticker_recorded ON esg_score_history (ticker, recorded_at DESC);

CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT          NOT NULL,
    key_hash     TEXT          NOT NULL UNIQUE,
    role         TEXT          NOT NULL DEFAULT 'reader',
    active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active   ON api_keys (active);

CREATE TABLE IF NOT EXISTS alert_history (
    id         BIGSERIAL    PRIMARY KEY,
    ticker     TEXT         NOT NULL,
    type       TEXT         NOT NULL,
    valeur     DOUBLE PRECISION,
    seuil      DOUBLE PRECISION,
    message    TEXT,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alert_history_ticker_created ON alert_history (ticker, created_at DESC);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_history_gin_ticker   ON analysis_history USING GIN(ticker gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_history_gin_workflow ON analysis_history USING GIN(workflow_name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id   UUID NOT NULL UNIQUE,
    note          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE annotations ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_annotations_tags ON annotations USING GIN (tags);

CREATE TABLE IF NOT EXISTS users (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT        NOT NULL,
    hashed_password   TEXT        NOT NULL,
    role              TEXT        NOT NULL DEFAULT 'reader',
    is_active         BOOLEAN     NOT NULL DEFAULT TRUE,
    is_email_verified BOOLEAN     NOT NULL DEFAULT FALSE,
    mfa_secret        TEXT,
    mfa_enabled       BOOLEAN     NOT NULL DEFAULT FALSE,
    oauth_provider    TEXT,
    oauth_id          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at     TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (LOWER(email));

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT        NOT NULL UNIQUE,
    family      UUID        NOT NULL,
    used        BOOLEAN     NOT NULL DEFAULT FALSE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON refresh_tokens (family);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id    UUID        NOT NULL,
    key        TEXT        NOT NULL,
    value      JSONB       NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, key)
);
"""

# Ordre de DROP inverse des dépendances FK (refresh_tokens → users).
_DROP_DDL = """
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS annotations CASCADE;
DROP TABLE IF EXISTS alert_history CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS esg_score_history CASCADE;
DROP TABLE IF EXISTS composite_score_history CASCADE;
DROP TABLE IF EXISTS watchlist CASCADE;
DROP TABLE IF EXISTS analysis_history CASCADE;
DROP EXTENSION IF EXISTS pg_trgm;
"""


def _execute_each(ddl: str) -> None:
    """Exécute chaque instruction séparément.

    asyncpg (protocole de requête étendu) n'autorise qu'une instruction par
    exécution — contrairement à psycopg2. On découpe donc sur `;`. Le DDL de ce
    fichier ne contient aucun `;` littéral (pas de corps de fonction), le découpage
    est donc sûr.
    """
    for statement in ddl.split(";"):
        stripped = statement.strip()
        if stripped:
            op.execute(stripped)


def upgrade() -> None:
    _execute_each(_BASELINE_DDL)


def downgrade() -> None:
    _execute_each(_DROP_DDL)
