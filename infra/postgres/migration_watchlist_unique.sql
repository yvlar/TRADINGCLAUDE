-- Migration — unicité (ticker, workflow) sur la table watchlist
-- Ferme BUG-005 : la garde applicative (SELECT puis INSERT) était sujette à une
-- course TOCTOU sans contrainte DB. Cet index unique garantit l'invariant.
--
-- Étape 1 (optionnelle) : dédupliquer les éventuels doublons préexistants en
-- conservant l'entrée la plus récente par (ticker, workflow). À exécuter avant
-- la création de l'index si la base contient déjà des doublons.
DELETE FROM watchlist a
USING watchlist b
WHERE a.ticker = b.ticker
  AND a.workflow = b.workflow
  AND a.created_at < b.created_at;

-- Étape 2 : verrou d'unicité.
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_ticker_workflow
    ON watchlist (ticker, workflow);
