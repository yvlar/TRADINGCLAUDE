# Revue OWASP — policy Row-Level Security multi-tenant (E3-S5)

**Date** : 2026-06-06 · **Périmètre** : isolation tenant des 6 tables métier sous PostgreSQL RLS
(migration `alembic/versions/0005_business_rls.py`, threading `app/db/tenant_context.py`).
**Méthode** : revue de la policy au crible des vecteurs de contournement RLS connus, croisée
avec l'état runtime observé (`pg_policies`, `pg_class.relrowsecurity/relforcerowsecurity`,
`pg_roles`) sur un PostgreSQL 16 migré à `head`.

La matrice rouge→vert (`tests/integration/test_rls_isolation.py`) prouve l'isolation sur les
6 tables sous rôle NOSUPERUSER ; cette note documente ce que la policy **garantit** et les
**risques résiduels** hors de sa portée.

---

## 1. État vérifié de la policy

Sur les 6 tables métier (`analysis_history`, `watchlist`, `composite_score_history`,
`esg_score_history`, `alert_history`, `annotations`), observé en runtime :

| Contrôle | État | Vérifié par |
|---|---|---|
| `ROW LEVEL SECURITY` activée (`ENABLE`) | ✅ les 6 | `pg_class.relrowsecurity = t` |
| `FORCE ROW LEVEL SECURITY` (propriétaire soumis) | ✅ les 6 | `pg_class.relforcerowsecurity = t` |
| Exactement 1 policy `ALL` par table | ✅ les 6 | `pg_policies` |
| `USING` ET `WITH CHECK` = même prédicat tenant | ✅ les 6 | `pg_policies.qual` == `with_check` |
| Prédicat fail-closed | ✅ | `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid` |

Prédicat : `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`.

---

## 2. Vecteurs de contournement examinés

### 2.1 Injection via le GUC `app.tenant_id` — **non exploitable**
Le GUC n'est jamais construit par concaténation de chaîne. Il est posé via
`set_config($1, $2, false)` en **paramètres liés** (`app/db/tenant_context.py:73`), et la valeur
provient de `get_current_tenant()` qui retourne toujours un `uuid.UUID` validé : `set_current_tenant`
parse l'entrée en `UUID(...)` et **retombe sur le tenant legacy** en cas de valeur absente/malformée
(`app/db/tenant_context.py:38-54`). Une chaîne arbitraire ne peut donc atteindre ni le `set_config`
ni le `::uuid` de la policy. Côté policy, `current_setting(..., true)` + `NULLIF(...,'')::uuid`
neutralise aussi la chaîne vide (qui lèverait sinon `22P02`).

### 2.2 Fonctions `SECURITY DEFINER` — **aucune**
`grep -rin "SECURITY DEFINER" app/ alembic/ infra/` ne renvoie **aucune** définition. Aucune
fonction n'exécute donc de requête sur les tables métier avec les privilèges du créateur (qui
contournerait la RLS de l'appelant). À réévaluer si une telle fonction est introduite.

### 2.3 `FORCE RLS` vs propriétaire de table — **couvert**
Sans `FORCE`, le **propriétaire** d'une table contourne sa propre RLS. Les 6 tables portent
`FORCE` (vérifié), et la matrice tourne sous un rôle **NOSUPERUSER non-propriétaire** : si `FORCE`
manquait sur une table, la matrice échouerait sur la lecture isolée.

### 2.4 `BYPASSRLS` / superuser — **RISQUE RÉSIDUEL #1 (déploiement)**
`FORCE` ne neutralise **pas** un rôle `BYPASSRLS` ni un `SUPERUSER` : ces attributs court-circuitent
toute policy. Sur l'instance observée, le rôle `copilote` (propriétaire, utilisé par les migrations
et par défaut dans `.env.example:21`) est **`SUPERUSER` + `BYPASSRLS`**. **Si le runtime applicatif
se connecte avec ce rôle, l'isolation RLS est nulle.**

> **Exigence de déploiement (à porter en prod)** : le rôle de **connexion applicative** (pools API
> + workers) doit être **`NOSUPERUSER`, `NOBYPASSRLS`, et non-propriétaire** des tables. Le rôle
> `copilote` superuser reste réservé aux migrations Alembic. Cette séparation n'est pas un livrable
> de code de ce sprint (pas de table/endpoint) — c'est une consigne d'infrastructure, à matérialiser
> dans un sprint d'ops (provisioning du rôle `app_runtime`).

---

## 3. Risques résiduels documentés

### 3.1 Chemin de lecture `/report` auth-exempté — **résiduel, décision prise**
`/report` est dans `BearerTokenMiddleware.EXEMPT_PREFIXES` (`app/middleware/auth.py:46`) : aucune
auth ⇒ `TenantContextMiddleware` ne résout aucun tenant ⇒ le GUC reste au **défaut legacy**.
`app/api/endpoints/report.py:88-95` lit `analysis_history WHERE id = $1` sous la RLS. Conséquences
une fois de **vrais** tenants émis :
- une analyse d'un tenant **non-legacy** devient **invisible** au rapport → **404 parasite** ;
- les lignes **legacy** restent lisibles par **quiconque détient l'UUID** (le lien de rapport n'est
  pas scopé au tenant).

**Décision (ce sprint)** : **documenter `/report` comme legacy-only** et le traiter comme risque
résiduel suivi, **sans** modifier l'auth ici. Justification : scoper le token de rapport au tenant
(ou threader le tenant dans l'auth de rapport) est un changement d'authentification **structurant**
— format du lien, signature, révocation — qui dépasse le périmètre « preuve d'isolation + revue »
de l'E3-S5 et mérite son propre sprint. **Action de suivi** : sprint dédié « token de rapport scopé
tenant » (lien signé portant le `tenant_id`, résolu hors du chemin auth-exempté). Tant qu'il n'est
pas livré, `/report` n'est sûr que pour des données legacy.

### 3.2 `tenants` et `users` hors RLS — **par conception, à surveiller**
`tenants` (dimension parente) et `users` n'ont **pas** de RLS (vérifié : `relrowsecurity = f`).
`users` porte pourtant `tenant_id`. L'accès `users` est filtré **au niveau applicatif** (auth par
`id`/`email`, jamais d'énumération cross-tenant exposée), mais il n'y a **pas** d'isolation DB sur
la liste des utilisateurs d'un tenant. Acceptable tant qu'aucun endpoint ne liste les users par
tenant ; à reconsidérer (RLS sur `users`) si une console d'admin multi-tenant est introduite.

### 3.3 Clés API et workers → tenant legacy — **connu, suite E4**
Le chemin Bearer (`api_keys`) et les workers Celery ne posent pas de tenant réel → legacy (cf.
sprints suggérés E4-S3 « clés API rattachées au tenant »). Hors périmètre E3.

---

## 4. Conclusion

La policy RLS est **saine et fail-closed** sur les 6 tables : isolation lecture (`USING`), refus
d'écriture cross-tenant (`WITH CHECK`), et 0 ligne sans contexte — prouvé table par table en
rouge→vert sous rôle NOSUPERUSER. Aucun vecteur de contournement *applicatif* (injection GUC,
`SECURITY DEFINER`, propriétaire via `FORCE`) n'est ouvert.

Deux conditions **hors code** restent à porter avant d'exposer la multi-tenance en production :
1. **rôle runtime `NOSUPERUSER`/`NOBYPASSRLS`/non-propriétaire** (§2.4) — sinon la RLS est inerte ;
2. **scoper `/report` au tenant** (§3.1) — sinon fuite de lecture côté rapport.

L'épic E3 (isolation au niveau base) est clos côté **mécanisme et preuve** ; ces deux points sont
des risques résiduels **suivis**, non des régressions du présent sprint.
