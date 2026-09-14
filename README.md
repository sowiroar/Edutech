# Edutech · Asistente de voz multiagente

Asistente de voz en español con tres agentes que se transfieren la llamada:

| Agente | Voz (Kokoro) | Rol |
|---|---|---|
| **Lira** | `ef_dora` | Recepción: saluda y enruta |
| **Nexus** | `em_alex` | Tutor de IA, Machine Learning y visión por computadora |
| **Elian** | `em_santa` | Asesor de la Universidad Autónoma de Manizales |

## Arquitectura

| Servicio | Tecnología | Puerto |
|---|---|---|
| `ollama` + `ollama-init` | LLM local; el modelo `nexus` se crea desde [`agent-starter-python/Modelfile`](agent-starter-python/Modelfile) | 11435 |
| `whisper-stt` | Faster-Whisper (voz a texto), GPU | 8000 |
| `kokoro-tts` | Kokoro (texto a voz), GPU | 8880 |
| `voice-agent` | LiveKit Agents (Python) — [`src/agent.py`](agent-starter-python/src/agent.py) | — |
| `frontend` | Next.js | 3000 |

La sala WebRTC, el detector de turno y la cancelación de ruido usan **LiveKit Cloud**.

## Requisitos

- Docker Desktop con soporte de GPU NVIDIA (virtualización activada en la BIOS)
- Git (en Windows, Git for Windows)
- Un proyecto en [LiveKit Cloud](https://cloud.livekit.io) → Settings → API Keys

## Primer uso (una vez por clon)

```bash
git clone https://github.com/sowiroar/Edutech.git
cd Edutech
sh scripts/setup.sh          # Windows PowerShell: .\scripts\setup.ps1
```

`setup` activa los hooks de git, crea `.env` desde [`.env.example`](.env.example) y levanta el stack.
Completa las credenciales de LiveKit en `.env` y vuelve a ejecutar `sh scripts/deploy.sh`.
Luego abre http://localhost:3000.

## Actualizar: solo `git pull`

Con los hooks activos, cada `git pull` (merge o rebase) y cada `git checkout`/`git switch` de rama
revisan qué cambió. Si tocó `docker-compose.yml`, `.env.example`, `agent-starter-python/`,
`agent-starter-react/` o `whisper-service/`, se ejecuta `docker compose up -d --build --remove-orphans`:
se reconstruye lo que cambió y se recrean solo los contenedores afectados.

- Cambiar el modelo base en el `Modelfile` basta para que `ollama-init` lo descargue y recree `nexus`.
- `EDUTECH_SKIP_DEPLOY=1 git pull` baja cambios sin tocar Docker.
- `sh scripts/deploy.sh` fuerza la actualización a mano (por ejemplo, si Docker estaba apagado durante el pull).

## Flujo de trabajo (Gitflow)

| Rama | Sale de | Se fusiona en | Uso |
|---|---|---|---|
| `main` | — | — | Producción; solo recibe `release/*` y `hotfix/*` |
| `develop` | `main` | — | Integración del trabajo en curso |
| `feature/<nombre>` | `develop` | `develop` | Nuevas funcionalidades |
| `bugfix/<nombre>` | `develop` | `develop` | Correcciones antes de release |
| `release/X.Y.Z` | `develop` | `main` y `develop` | Preparar versión |
| `hotfix/X.Y.Z` | `main` | `main` y `develop` | Corrección urgente en producción |

```bash
git switch develop && git pull
git switch -c feature/rag-material-curso
# ...commits...
git push -u origin feature/rag-material-curso   # abrir PR hacia develop
```

Todo cambio entra por Pull Request. Nombres de rama en minúsculas; versiones con [SemVer](https://semver.org/lang/es/).

## GitHub Actions

| Workflow | Cuándo | Qué hace |
|---|---|---|
| [CI](.github/workflows/ci.yml) | push a ramas gitflow y PR a `main`/`develop` | `ruff` + `pytest` del agente, build de Next.js, validación de compose y build de imágenes |
| [Gitflow](.github/workflows/gitflow.yml) | PR a `main`/`develop` | Rechaza PRs cuya rama origen no respeta la tabla anterior |
| [Release](.github/workflows/release.yml) | merge de `release/X.Y.Z` o `hotfix/X.Y.Z` en `main` | Crea el tag `vX.Y.Z`, la GitHub Release y el PR de back-merge a `develop` |

Para que las reglas sean obligatorias, un administrador del repositorio debe proteger `main` y `develop`
(Settings → Branches): exigir PR y exigir los checks **CI** y **Gitflow**.

## Desarrollo local

```bash
cd agent-starter-python
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Logs del stack: `docker compose logs -f voice-agent`.
