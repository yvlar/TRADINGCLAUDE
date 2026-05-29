-- Sprint 125 — tags sur les annotations (filtrage sémantique léger de l'historique)
-- À appliquer sur une DB existante où la table `annotations` est déjà présente
-- (créée par le bootstrap du lifespan FastAPI, cf. app/api/main.py).
--
-- Type retenu : TEXT[] (tableau natif Postgres) plutôt que JSONB.
--   - asyncpg mappe list[str] <-> text[] sans encodage JSON intermédiaire
--   - le filtre /history?tags= utilise l'opérateur de confinement `@>` (match de TOUS
--     les tags demandés) — index GIN via la classe d'opérateurs par défaut array_ops
ALTER TABLE annotations
    ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_annotations_tags ON annotations USING GIN (tags);
