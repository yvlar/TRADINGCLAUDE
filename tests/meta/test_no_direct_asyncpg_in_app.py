"""Meta-test anti-contournement du chokepoint `create_runtime_pool` — tout `app/` (Sprint 205).

S200 a posé ce scan AST sur le seul `app/workers/`. Mais n'importe quel endpoint ou service
de `app/` pouvait encore fabriquer une connexion asyncpg directe (`asyncpg.create_pool`,
`asyncpg.connect`), contournant silencieusement le garde insecure-creds (`require_secure_db_url`)
ET le hook tenant RLS — les deux câblés par `create_runtime_pool` (`app/db/pool.py`). Ce sprint
généralise le scan à tout `app/**/*.py`, avec une allowlist explicite des deux seuls usages
légitimes (cf. `_ALLOWLIST`). Comme `app/workers/` est inclus dans `app/`, ce scan subsume
l'invariant worker de S200 (renforcé : plus seulement les workers).

Scan par AST (pas un grep du source) : insensible aux commentaires et docstrings, et sans faux
positif sur les type hints (`asyncpg.Pool`/`Record`/`Connection`) ni les exceptions
(`asyncpg.UniqueViolationError`, `asyncpg.exceptions.…`) — seules les fabriques `create_pool`/
`connect` comptent. Couvre les formes dérivées : alias de module (`import asyncpg as pg`),
sous-modules (`asyncpg.pool.create_pool`), chaînes d'attributs et `from asyncpg import *`.
Garde-fou anti-régression, pas un sandbox anti-obfuscation : `getattr`/`importlib` restent hors
périmètre (plausibilité quasi nulle, complexité non justifiée).

Aucun mock, aucune I/O réseau, aucune DB : lecture du système de fichiers local uniquement.
"""
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _REPO_ROOT / "app"
_WORKERS_TASKS_PATH = _APP_DIR / "workers" / "tasks.py"

# Constructeurs de connexion asyncpg dont l'appel direct contournerait le chokepoint.
_FORBIDDEN_FACTORIES = frozenset({"create_pool", "connect"})

# Allowlist : les DEUX seuls fichiers de `app/` autorisés à fabriquer une connexion asyncpg
# directe. Load-bearing (prouvé par `test_allowlist_est_load_bearing`), jamais décorative —
# le WHY de chaque exemption est obligatoire :
#   - app/db/pool.py : LE chokepoint `create_runtime_pool` (résolution DSN runtime + garde
#     insecure-creds + hook tenant RLS, décisions indissociables). Tout autre pool runtime
#     DOIT passer par lui ; c'est précisément ce que ce scan protège.
#   - app/db/provision_app_runtime.py : provisioning du mot de passe du rôle `app_runtime`
#     au boot, exécuté sous le superuser de `DATABASE_URL`, volontairement HORS RLS (il pose
#     le secret AVANT que le runtime NOSUPERUSER ne puisse se connecter — antérieur au pool).
_ALLOWLIST = frozenset(
    {
        _APP_DIR / "db" / "pool.py",
        _APP_DIR / "db" / "provision_app_runtime.py",
    }
)


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
    `create_pool`/`connect` sur ces noms n'a pas d'usage légitime applicatif."""
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


def _modules_app_hors_allowlist() -> list[Path]:
    """Tous les `.py` de `app/` sauf l'allowlist, triés (déterminisme du rapport d'erreur)."""
    return sorted(p for p in _APP_DIR.rglob("*.py") if p not in _ALLOWLIST)


def test_aucun_asyncpg_create_pool_ni_connect_direct_dans_app() -> None:
    """Aucun module de `app/` hors allowlist ne fabrique de connexion DB hors du chokepoint."""
    # Garde : l'allowlist doit pointer sur des fichiers réels — un chemin périmé (fichier
    # renommé/supprimé) exempterait dans le vide et masquerait une régression future.
    for chemin in _ALLOWLIST:
        assert chemin.is_file(), f"Fichier allowlisté introuvable : {chemin} — _ALLOWLIST périmée"

    fichiers_scannes = _modules_app_hors_allowlist()
    assert _WORKERS_TASKS_PATH in fichiers_scannes, (
        "app/workers/tasks.py introuvable dans le scan — la couverture worker de S200 a régressé"
    )

    violations = [
        f"{path.relative_to(_REPO_ROOT)} {violation}"
        for path in fichiers_scannes
        for violation in _scan_violations(_parse_module(path))
    ]

    assert violations == [], (
        "Connexion asyncpg directe dans app/ (hors allowlist) — tout pool runtime doit passer "
        "par app.db.pool.create_runtime_pool (garde insecure-creds + hook tenant RLS) ; un "
        f"provisioning admin légitime doit être ajouté à _ALLOWLIST avec son WHY : {violations}"
    )


def test_allowlist_est_load_bearing() -> None:
    """Anti-vacuité : chaque fichier allowlisté contient bien une fabrique asyncpg directe.

    Sans cette assertion, l'allowlist pourrait lister des fichiers anodins (exemption
    décorative) : le scan resterait vert même vidé de sa substance. Ici on prouve que retirer
    l'un de ces fichiers de `_ALLOWLIST` le ramènerait dans le scan AVEC des violations — donc
    l'exemption est load-bearing, chaque entrée protège un usage réel et justifié."""
    for chemin in _ALLOWLIST:
        violations = _scan_violations(_parse_module(chemin))
        assert violations, (
            f"{chemin.relative_to(_REPO_ROOT)} est allowlisté mais ne contient aucune fabrique "
            "asyncpg directe — exemption injustifiée, à retirer de _ALLOWLIST"
        )


def test_le_scanner_detecte_chaque_forme_de_fabrique_directe() -> None:
    """Anti-régression du scanner : chaque forme de contournement connue est bien détectée."""
    sources_interdites = {
        "attribut direct create_pool": "import asyncpg\nasyncpg.create_pool(dsn)\n",
        "attribut direct connect": "import asyncpg\nasyncpg.connect(dsn)\n",
        "alias de module": "import asyncpg as pg\npg.create_pool(dsn)\n",
        "sous-module chaîné": "import asyncpg.pool\nasyncpg.pool.create_pool(dsn)\n",
        "import nommé": "from asyncpg import create_pool\ncreate_pool(dsn)\n",
        "import nommé via sous-module": "from asyncpg.pool import create_pool\ncreate_pool(dsn)\n",
        "wildcard": "from asyncpg import *\n",
    }
    for libelle, src in sources_interdites.items():
        assert _scan_violations(ast.parse(src)), f"Forme de contournement non détectée : {libelle}"


def test_le_scanner_ignore_les_usages_legitimes() -> None:
    """Pas de faux positif : type hints, exceptions, commentaires et docstrings sont immunisés."""
    sources_legitimes = {
        "type hints": "import asyncpg\n\n\ndef f(p: asyncpg.Pool) -> asyncpg.Record:\n    return p\n",
        "classe d'exception": "import asyncpg\n\ntry:\n    pass\nexcept asyncpg.UniqueViolationError:\n    pass\n",
        "exception via sous-module": (
            "import asyncpg\n\ntry:\n    pass\n"
            "except asyncpg.exceptions.InvalidTextRepresentationError:\n    pass\n"
        ),
        "mention en docstring": '"""Mention asyncpg.create_pool dans un docstring."""\nimport asyncpg\n',
        "mention en commentaire": "# asyncpg.connect en commentaire\nimport asyncpg\n",
    }
    for libelle, src in sources_legitimes.items():
        assert _scan_violations(ast.parse(src)) == [], f"Faux positif sur usage légitime : {libelle}"


def test_chokepoint_create_runtime_pool_utilise_par_les_workers() -> None:
    """Anti-vacuité : les workers passent réellement par le chokepoint.

    Sans cette assertion, le scan resterait vert sur un `tasks.py` vidé de ses accès
    DB — l'invariant serait trivialement satisfait sans plus rien protéger. L'import
    épingle aussi la provenance (`app.db.pool`) : un homonyme local définissant son
    propre `create_runtime_pool` passerait un simple comptage d'appels."""
    tree = _parse_module(_WORKERS_TASKS_PATH)

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
