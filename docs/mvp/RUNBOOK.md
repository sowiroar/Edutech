# Arranque local, Windows y revisión UAM

## Preparar el checkout

Git y Git LFS para Avatar; Python 3 y uv para agente; Node 24 para frontend.
Docker/Compose con motor activo para servicios. Cerrar Unreal antes de cambiar
su rama. Leer FLUJO.md y conservar cambios locales. No ejecutar setup/deploy
históricos como arranque de esta demo: inician también servicios CUDA.

```sh
# Desde Edutech. En Windows usar python en lugar de python3.
python3 scripts/voice_demo.py init
# Editar .env.voice localmente: GOOGLE_API_KEY y GEMINI_LIVE_MODEL.
python3 scripts/voice_demo.py doctor
python3 scripts/voice_demo.py config
python3 scripts/voice_demo.py up
python3 scripts/voice_demo.py ps
```

Abrir http://localhost:3500 en el mismo equipo, conceder micrófono y comenzar.
`up` construye imágenes y puede tardar; el agente/RAG/Mem0 consumen API Google.
El modelo debe ser el ID habilitado de Jacobo/UAM o uno verificado para esta cuenta;
no se considera válido un default solo porque figure en el repositorio.
Gemini Live incluye audio; no necesita la GPU NVIDIA local para inferencia.
La primera indexación/RAG puede tardar; revisar antes de mostrar la demo.

El proyecto Compose `edutech-voice-local` tiene volúmenes propios. No comparte los
volúmenes `azimutai_*` de UAM. Puertos 3500,7880,7881,7882 ligados a loopback;
no es un despliegue público ni configuración para móviles en otra red.
`infra` inicia solo LiveKit/Qdrant; `web` añade frontend para probar carga/token,
sin agente ni llamadas Google. No demuestra conversación. `down` conserva datos:

```sh
python3 scripts/voice_demo.py down
```

Si un puerto está ocupado, detener solo la prueba propia o ajustar puertos/URLs
coordinadamente. No parar otros contenedores. No publicar .env.voice ni respuestas
con participantToken. El Compose histórico sigue disponible para revisión UAM.

## Pruebas locales sin credenciales

```sh
python3 -m unittest discover -s scripts/tests -v
uv sync --locked --project agent-starter-python
cd agent-starter-python
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
cd ../agent-starter-react
npm ci --legacy-peer-deps
npm run build
```

No se ejecutan escenarios con LLM/proveedor por un cambio documental. Verificar
que las pruebas usadas son unitarias y mocks; los ensayos reales se registran aparte.
Para frontend nativo, copiar su .env.example a .env.local y usar LIVEKIT_URL local,
devkey/secret (credenciales públicas de modo desarrollo), AGENT_NAME=nexus;
`npm run dev`. No ejecutar simultáneamente dos frontends en el mismo puerto.

## Avatar en Mac / equipo de Santiago

Desde Avatar:

```sh
git lfs pull
python3 scripts/validate_avatar_catalog.py
python3 -m unittest discover -s scripts/tests -v
./scripts/editor_mac.command check --avatar lira --profile efficient
# Abrir solo si se va a editar:
./scripts/editor_mac.command open --avatar lira --profile efficient
```

Windows PowerShell, UE 5.8.2 y Visual Studio/SDK compatibles instalados:

```powershell
git lfs pull
python scripts/validate_avatar_catalog.py
.\scripts\editor_windows.ps1 -Action check -Avatar nexo-design
.\scripts\editor_windows.ps1 -Action open -Avatar nexo-design
```

Escoger nexo-design/lira/elian-design/noa-design/nova-design/atlas-design.
No ejecutar scripts de autoría para arrancar escenas. El paquete Mac histórico
`PRESENTAR_FAMILIA_MAC.command` es WAV local de tres candidatas; necesita el bridge
histórico indicado por VIVA_BRIDGE_DIR. No sustituirlo por avatar-bridge de Gemini.
No demuestra sesión Gemini. El paquete actual no contiene las seis escenas.

## UAM: prueba remota, no despliegue automático

1. Conectar FortiClient al perfil UAM existente; luego Windows App/RDP al host
   autorizado. Credenciales solo en el gestor local, nunca documentación/Git.
2. En el host identificar OS real de los servicios: Windows/WSL/Linux, directorio,
   rama, `git status`, commits y procesos/puertos. RDP no prueba SSH disponible.
3. Preservar trabajo no publicado de Jacobo en su rama, publicar o guardar un
   respaldo verificable; registrar SHA antes de actualizar. Conservar .env/datos.
4. Checkout de ensayo separado desde backp-fase1, EDUTECH_SKIP_DEPLOY=1. Revisar
   configuración original antes de iniciar nuevos contenedores; este runbook
   local no asigna puertos automáticamente para un segundo stack UAM.
5. Abrir navegador dentro de RDP usa localhost del servidor. Para probar desde
   Mac se necesita URL accesible, HTTPS/WSS para micrófono fuera de localhost y
   puertos WebRTC/red permitidos. VPN sola no resuelve esas URLs ni ICE.
6. Jacobo valida voz; Santiago render/NVIDIA; Juan telemetría. Registrar versión
   y evidencia, aprobar el candidato funcional y conservar el anterior para retorno.

El acceso por RDP no da por sí mismo una terminal remota a Codex. El flujo inicial
es Git + comandos ejecutados en esa sesión. SSH/runner se configura solo después
de comprobar disponibilidad y alcance, no se presupone ni se abre a Internet.
