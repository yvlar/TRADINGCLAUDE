-- Sprint 125 — annotations enrichies : colonne tags + index GIN
-- À appliquer sur une DB existante où la table `annotations` est déjà présente
-- (créée par le bootstrap du lifespan FastAPI, cf. app/api/main.py).
--
-- Choix du type : JSONB + opérateur de containment `@>` (sémantique ET — une
-- annotation matche si elle contient TOUS les tags demandés). JSONB plutôt que
-- TEXT[] pour rester cohérent avec le reste du schéma (user_preferences,
-- analysis_history.result) et réutiliser le décodage `_decode_jsonb`.

ALTER TABLE annotations ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Index GIN avec classe d'opérateurs jsonb_path_ops : optimal pour `@>` (containment).
CREATE INDEX IF NOT EXISTS idx_annotations_tags ON annotations USING GIN (tags jsonb_path_ops);
