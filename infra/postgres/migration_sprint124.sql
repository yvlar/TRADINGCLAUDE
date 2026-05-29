-- Sprint 124 — préférences utilisateur côté serveur (continuité multi-appareils)
-- À appliquer sur une DB existante où la table `users` est déjà présente
-- (créée par le bootstrap du lifespan FastAPI, cf. app/api/main.py).
-- Le type de `user_id` (UUID) suit `users.id` (UUID PRIMARY KEY gen_random_uuid()).

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key        TEXT        NOT NULL,
    value      JSONB       NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, key)
);
