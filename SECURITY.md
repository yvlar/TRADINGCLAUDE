# Politique de sécurité / Security Policy

## Versions supportées / Supported versions

Seule la dernière version sur la branche `master` reçoit des correctifs de sécurité.

| Version | Support |
|---|---|
| `master` (latest) | ✅ Supportée |
| Versions antérieures | ❌ Non supportées |

---

## Signaler une vulnérabilité / Reporting a vulnerability

**Ne pas ouvrir une issue publique pour des rapports de sécurité.**

Pour divulguer de façon responsable une vulnérabilité :

1. Envoyer un e-mail à **ivess49@gmail.com** avec :
   - Description de la vulnérabilité
   - Étapes de reproduction
   - Impact potentiel estimé
   - Version ou commit affecté

2. Un accusé de réception sera envoyé sous **72 heures**.

3. Un correctif sera déployé dans les **14 jours** pour les vulnérabilités critiques.

4. Le rapport sera crédité dans le changelog (sauf demande d'anonymat).

---

## Périmètre / Scope

Ce projet est un **outil d'analyse personnel** — il ne traite pas de données financières réelles
d'utilisateurs tiers ni de transactions. Les risques prioritaires sont :

- Exposition de clés API (Anthropic, etc.) via logs ou endpoints
- Injection dans les prompts Claude
- Accès non autorisé aux endpoints `/admin`

---

## Bonnes pratiques intégrées

- Clés API exclusivement via variables d'environnement (`.env` non commité)
- `.env.example` fourni avec valeurs factices
- Authentification Bearer token sur les endpoints sensibles
- Pas de valeurs sensibles dans les traces Langfuse ni les messages d'erreur HTTP
