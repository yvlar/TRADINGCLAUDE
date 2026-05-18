-- Migration Sprint 39 — Performance tracking
-- Ajoute le cours de l'action au moment de chaque analyse.
-- À exécuter sur les environnements existants (init.sql reste inchangé).

ALTER TABLE analysis_history
    ADD COLUMN IF NOT EXISTS price_at_analysis FLOAT;
