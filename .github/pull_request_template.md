## Description

<!-- Résumer les changements apportés et le problème résolu -->

## Type de changement

- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Refactoring (aucun changement de comportement)
- [ ] Infrastructure / CI
- [ ] Documentation

## Sprint associé

Sprint #<!-- numéro --> — <!-- nom du sprint -->

---

## Checklist

- [ ] Les tests CI passent (`pytest tests/ --ignore=tests/e2e --ignore=tests/evals`)
- [ ] Les tests Vitest passent (`cd frontend && npm test`)
- [ ] Le typecheck passe (`cd frontend && npm run typecheck`)
- [ ] Zéro `any` TypeScript — types stricts dans `frontend/src/types/index.ts`
- [ ] Type hints Python sur toutes les nouvelles signatures
- [ ] `CLAUDE.md` mis à jour si des conventions ont changé
- [ ] `.env.example` mis à jour si de nouvelles variables ont été ajoutées
- [ ] Aucun secret / clé API dans le code ou les logs
- [ ] `ROADMAP.md` mis à jour (sprint complété → ✅, version incrémentée)
