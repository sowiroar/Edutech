#!/usr/bin/env sh
# Configuración inicial, una sola vez por clon:
#   1. activa los hooks versionados en .githooks (auto-deploy al bajar cambios)
#   2. crea .env desde .env.example si no existe
#   3. construye y levanta el stack
set -eu

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

git config core.hooksPath .githooks
echo "[edutech-setup] Hooks de git activados (core.hooksPath=.githooks)."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[edutech-setup] Se creó .env: completa LIVEKIT_URL, LIVEKIT_API_KEY y LIVEKIT_API_SECRET."
fi

sh scripts/deploy.sh
