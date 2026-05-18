-- Migration Sprint 48 -- Watchlist alertes composite
-- Ajoute le score composite de reference pour les alertes de derive.
-- A executer sur les environnements existants (init.sql reste inchange).

ALTER TABLE watchlist
    ADD COLUMN IF NOT EXISTS last_composite_score FLOAT,
    ADD COLUMN IF NOT EXISTS composite_alert_threshold FLOAT DEFAULT 15.0;
