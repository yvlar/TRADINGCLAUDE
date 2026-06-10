"""Meta-test anti-contournement du chokepoint `create_runtime_pool` (Sprint 200).

S192/S196/S199 prouvent que le garde `require_secure_db_url` verrouille les chemins
pool/worker/API à condition que tout pool runtime passe par `create_runtime_pool`
(`app/db/pool.py`) — qui câble aussi le hook tenant RLS. Rien n'empêchait un futur
worker d'appeler `asyncpg.create_pool`/`asyncpg.connect` en direct, contournant
silencieusement le garde ET l'isolation multi-tenant. Ce scan statique rend ce
contournement impossible à introduire sans casser le CI.

Scan par AST (pas un grep du source) : insensible aux commentaires et docstrings —
une mention `asyncpg.create_pool` dans un commentaire ne déclenche pas de faux positif,
seul du vrai code l'atteint. Couvre tout le package `app/workers/` (l'invariant dit
« aucun worker », pas « tasks.py seul ») et les formes dérivées : alias de module,
sous-modules (`asyncpg.pool`), chaînes d'attributs et `from asyncpg import *`.
Garde-fou anti-régression, pas un sandbox anti-obfuscation : `getattr`/`importlib`
restent hors périmètre (plausibilité quasi nulle, complexité non justifiée).

Aucun mock, aucune I/O réseau, aucune DB : lecture du système de fichiers local uniquement.
"""
from __future__ import annotations

import ast
from pathlib import Path

_WORKERS_DIR = Path(__file__).resolve().parents[2] / "app" / "workers"
_TASKS_PATH = _WORKERS_DIR / "tasks.py"

# Constructeurs de connexion asyncpg dont l'appel direct contournerait le chokepoint.
_FORBIDDEN_FACTORIES = frozenset({"create_pool", "connect"})


def _is_asyncpg_module(name: str) -> bool:
    """Le nom désigne asyncpg ou un de ses sous-modules (`asyncpg.pool`…)."""
    return name == "asyncpg" or name.startswith("asyncpg.")


def _parse_module(path: Path) -> ast.Module:
    """Parse un module depuis la racine du dépôt — indépendant du cwd de pytest."""
    return ast.parse(path.read_text(encoding="utf-8"))


def _local_names_of_asyncpg(tree: ast.Module) -> set[str]:
    """Noms locaux désignant asyncpg, un de ses sous-modules ou attributs.

    Un alias d'import (`import asyncpg as pg`, `import asyncpg.pool as ap`) suffirait
    à esquiver un scan limité au littéral `asyncpg` — on résout donc les alias avant
    de chercher les accès d'attribut. `from asyncpg import pool` lie aussi un nom
    (`pool.create_pool(...)` contournerait sinon, vérifié) : tout nom importé depuis
    asyncpg est suivi — sur-approximation sans faux positif, un accès
    `create_pool`/`connect` sur ces noms n'a pas d'usage légitime en worker."""
    noms = {"asyncpg"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_asyncpg_module(alias.name):
                    noms.add(alias.asname or alias.name.split(".")[0])
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and _is_asyncpg_module(node.module)
        ):
            for alias in node.names:
                if alias.name != "*":
                    noms.add(alias.asname or alias.name)
    return noms


def _dotted_name(node: ast.Attribute) -> str | None:
    """Reconstruit le nom pointé d'une chaîne d'attributs (`asyncpg.pool.create_pool`).

    Nécessaire car `asyncpg.pool.create_pool` n'est PAS un `Attribute` sur un `Name` :
    sa valeur est elle-même un `Attribute` — un test `isinstance(value, ast.Name)` le
    manquerait (faux négatif vérifié). Racine non-Name (appel chaîné…) → None."""
    parts: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(cur.id)
    return ".".join(reversed(parts))


def _scan_violations(tree: ast.Module) -> list[str]:
    """Occurrences de fabrication directe de connexion asyncpg dans un module.

    Trois formes détectées : accès d'attribut depuis un nom liant asyncpg (alias et
    chaînes de sous-modules compris), `from asyncpg[.x] import create_pool/connect`,
    et `from asyncpg[.x] import *` (rend les fabriques accessibles sans préfixe —
    indétectable ensuite, donc interdit à la source)."""
    noms_asyncpg = _local_names_of_asyncpg(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_FACTORIES:
            dotted = _dotted_name(node)
            if dotted is not None and dotted.split(".")[0] in noms_asyncpg:
                violations.append(f"ligne {node.lineno} : {dotted}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and _is_asyncpg_module(node.module)
        ):
            for alias in node.names:
                if alias.name in _FORBIDDEN_FACTORIES or alias.name == "*":
                    violations.append(
                        f"ligne {node.lineno} : from {node.module} import {alias.name}"
                    )
    return violations


def test_aucun_asyncpg_create_pool_ni_connect_direct_dans_workers() -> None:
    """Aucun module worker ne fabrique de connexion DB hors du chokepoint gardé."""
    fichiers_scannes = sorted(_WORKERS_DIR.rglob("*.py"))
    assert _TASKS_PATH in fichiers_scannes, (
        "app/workers/tasks.py introuvable — le scan ne couvre plus le module visé"
    )

    violations = [
        f"{path.name} {violation}"
        for path in fichiers_scannes
        for violation in _scan_violations(_parse_module(path))
    ]

    assert violations == [], (
        "Connexion asyncpg directe dans app/workers/ — tout pool runtime doit passer "
        "par app.db.pool.create_runtime_pool (garde insecure-creds + hook tenant "
        f"RLS) : {violations}"
    )


def test_chokepoint_create_runtime_pool_utilise_par_les_workers() -> None:
    """Anti-vacuité : les workers passent réellement par le chokepoint.

    Sans cette assertion, le scan resterait vert sur un `tasks.py` vidé de ses accès
    DB — l'invariant serait trivialement satisfait sans plus rien protéger. L'import
    épingle aussi la provenance (`app.db.pool`) : un homonyme local définissant son
    propre `create_runtime_pool` passerait un simple comptage d'appels."""
    tree = _parse_module(_TASKS_PATH)

    importe_chokepoint = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app.db.pool"
        and any(alias.name == "create_runtime_pool" for alias in node.names)
        for node in ast.walk(tree)
    )
    nb_appels = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "create_runtime_pool"
    )

    assert importe_chokepoint, (
        "app/workers/tasks.py n'importe plus create_runtime_pool depuis app.db.pool — "
        "le meta-test ne protège plus rien"
    )
    assert nb_appels >= 1, (
        "Aucun appel create_runtime_pool dans app/workers/tasks.py — le meta-test "
        "serait vacueux"
    )
