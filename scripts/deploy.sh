#!/usr/bin/env sh
# Construye y (re)levanta el stack de Docker Compose con el código actual.
# Lo invocan los hooks de git tras `git pull` / `git checkout`, o se ejecuta a mano.
# Variables:
#   EDUTECH_SKIP_DEPLOY=1  -> no hace nada (útil para pulls rápidos sin Docker)
set -eu

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

log() { printf '\033[36m[edutech-deploy]\033[0m %s\n' "$*"; }

if [ "${EDUTECH_SKIP_DEPLOY:-0}" = "1" ]; then
  log "Omitido (EDUTECH_SKIP_DEPLOY=1)."
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  log "Docker no está instalado; no se actualizan los contenedores."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  log "Docker no está corriendo. Arráncalo y ejecuta: sh scripts/deploy.sh"
  exit 0
fi

if [ ! -f .env ]; then
  cp .env.example .env
  log "Se creó .env a partir de .env.example."
fi

if grep -Eq '^LIVEKIT_(URL|API_KEY|API_SECRET)=(|.*<.*>.*)$' .env; then
  log "Faltan credenciales de LiveKit en .env (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)."
  log "Complétalas y ejecuta: sh scripts/deploy.sh"
  exit 0
fi

log "Construyendo imágenes y actualizando contenedores (docker compose up -d --build)..."
docker compose up -d --build --remove-orphans
docker compose ps
log "Stack actualizado. Frontend: http://localhost:3000"
