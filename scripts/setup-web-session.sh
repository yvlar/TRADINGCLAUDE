#!/usr/bin/env bash
# Prépare l'environnement d'une session Claude Code sur le web : le conteneur
# éphémère Debian est cloné à neuf (venv backend absent, binaire natif rollup
# manquant dans node_modules). Idempotent et best-effort : ne fait rien si tout
# est déjà prêt, et ne fait JAMAIS échouer la session (exit 0 systématique).
set -u
cd "$(dirname "$0")/.." || exit 0

# Hors Linux (poste local Windows/macOS), l'étape web ne s'applique pas.
if [ "$(uname -s)" != "Linux" ]; then
  echo "[setup] OS non-Linux — préparation session web ignorée."
  exit 0
fi

# Backend : venv avec accès aux paquets système — la version Debian de
# cryptography casse un pip install global, d'où --system-site-packages.
if [ ! -d .venv ]; then
  echo "[setup] Création du venv backend (.venv)…"
  if python -m venv .venv --system-site-packages \
     && .venv/bin/pip install -q -r requirements-ci.txt ruff; then
    echo "[setup] venv backend prêt."
  else
    echo "[setup] venv/pip a échoué (réseau ?) — relancer scripts/setup-web-session.sh."
  fi
else
  echo "[setup] .venv déjà présent — ok."
fi

# Frontend : le binaire natif rollup-linux-x64-gnu n'est pas dans le node_modules
# cloné ; son absence casse le démarrage de Vitest et de vite build.
if [ -d frontend/node_modules ] && [ ! -d frontend/node_modules/@rollup/rollup-linux-x64-gnu ]; then
  echo "[setup] Installation du binaire natif rollup…"
  if ( cd frontend && npm install @rollup/rollup-linux-x64-gnu --no-save ); then
    echo "[setup] binaire rollup installé."
  else
    echo "[setup] npm install rollup a échoué (réseau ?) — relancer scripts/setup-web-session.sh."
  fi
else
  echo "[setup] binaire rollup présent ou node_modules absent — rien à faire."
fi

exit 0
