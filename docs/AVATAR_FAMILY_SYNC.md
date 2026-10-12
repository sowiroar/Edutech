# Revisión de la familia de avatares

12 de octubre de 2026. Esta entrega se prepara sobre la integración de Jacobo
`feature/gemini-live-api+MVP`, base
`f1ccd3cf7decea6e7d5ea735c808a0083bad0cf7`.

El objetivo es incorporar el proyecto Unreal con Nexo de Santiago y la nueva
escena de Lira mediante el submódulo existente `Avatar`. La organización,
respaldos y comandos completos se describen en la
[guía del repositorio Avatar](../Avatar/docs/SINCRONIZACION_REPOSITORIOS.md).
Ese enlace requiere descargar el submódulo en una revisión que incluya la guía.

## Alcance del cambio

El diff de esta entrega debe contener únicamente el gitlink `Avatar` y este
documento. No cambia `docker-compose.yml`, Gemini, el backend, el frontend,
prompts, roles de agentes ni contratos de audio. Tampoco fusiona el recorrido
histórico de `feature/avatar-bridge` con la integración actual.

El pin de partida es `156d2d8190bedb2e58fa66671bf6a31d161e192c`, la versión de
Santiago con familia VIVA y selección de personaje. La rama de diseño conserva
ese commit como ancestro; no elimina sus avances. La revisión candidata es **30a29f7836053bb466ca6d8a1f4058acccb8d3bf**; el
gitlink solo se actualiza después de confirmar que existe en el remoto Avatar. No usar el nombre de una rama móvil para identificar una entrega.

Para revisar el pin sin descargar los assets:

```sh
git ls-tree HEAD Avatar
git diff --submodule=log origin/feature/gemini-live-api+MVP...HEAD -- Avatar
git diff --name-only origin/feature/gemini-live-api+MVP...HEAD
```

Antes del commit, revisar además `git diff --cached --submodule=log -- Avatar`.
Un SHA todavía exclusivo del equipo de desarrollo no se puede entregar:
primero debe estar publicado con sus objetos Git LFS en el remoto de Avatar.

## Escenas incluidas

| ID del catálogo | Mapa | Uso |
| --- | --- | --- |
| `nexo` | `/Game/UniversityVirtualAssistant/NEXO_New/NewMap_NEXO_Lite` | Nexo vigente de Santiago; se conserva su diseño y escena |
| `lira-santiago` | `/Game/UniversityVirtualAssistant/FamiliaVIVA/LIRA/NewMap_LIRA_Studio` | Variante de Santiago preservada e integrada en Nexo Lite |
| `atlas`, `elian`, `noa` | Mapas Studio en `FamiliaVIVA` | Familia de Santiago preservada |
| `lira` | `/Game/VIVA/Avatars/Lira/Maps/L_Lira` | Diseño propio de Lira, todavía en revisión estética |
| `nova` | `/Game/UniversityVirtualAssistant/NewMap2` | Entrega femenina original preservada |
| `nexo-legacy` | `/Game/UniversityVirtualAssistant/NewMap` | Demo histórica conservada para referencia |

`Avatar/avatars.json` es la fuente del catálogo. Seleccionar un personaje no
implica cargar todos a la vez ni renombrar agentes del backend. La variante de cabello adaptado no sustituye los actores LIRA/ELIAN del mapa
compartido ni conecta automáticamente su aspecto a Gemini. La escena propia de
Lira usa `BP_Lira`, actor `LIRA` y Live Link `VivaLira`; migrar únicamente su
Blueprint puede dejar fuera accesorios o actores del mapa. El submódulo
versiona el proyecto completo y sus dependencias.

## Descargar y abrir para revisión

Cerrar Unreal y comprobar primero que el checkout y el submódulo no tienen
cambios sin conservar. Los hooks opcionales de Edutech pueden desplegar Docker
tras un cambio de rama o pull. Para una revisión de código sin reiniciar
servicios, establecer antes:

```sh
# Mac/Linux: válido para esta terminal.
export EDUTECH_SKIP_DEPLOY=1
```

```powershell
# Windows PowerShell: válido para esta terminal.
$env:EDUTECH_SKIP_DEPLOY = '1'
```

Desde la revisión acordada de Edutech, con Git LFS instalado:

```sh
git submodule sync --recursive
git submodule update --init --recursive
git -C Avatar lfs install --local
git -C Avatar lfs pull
git -C Avatar lfs fsck
git submodule status --recursive
git -C Avatar rev-parse HEAD
```

No usar `submodule update --remote`: se debe recuperar el SHA fijado en este
repo. Que el submódulo esté en `detached HEAD` es normal. No copiar allí el
directorio Unreal antiguo ni binarios de otra plataforma.

Mac, desde `Avatar/`, con Unreal 5.8.2 y Xcode completo:

```sh
python3 scripts/validate_avatar_catalog.py
./scripts/editor_mac.command check --avatar lira
./scripts/editor_mac.command open --avatar lira
```

Windows, desde `Avatar/`, con Unreal 5.8.2, Visual Studio C++ y Windows SDK:

```powershell
python scripts/validate_avatar_catalog.py
.\scripts\editor_windows.ps1 -Action check -Avatar lira
.\scripts\editor_windows.ps1 -Action open -Avatar lira
```

Cambiar `lira` por `nexo` para la regresión de Santiago. Abrir una sola instancia
del proyecto. Los lanzadores compilan Editor para el sistema local; no generan
por sí solos una aplicación empaquetada ni arrancan el agente.

## Evidencia y aceptación pendiente

Consultar las [pruebas de Avatar](../Avatar/docs/validation/2026-10-12-lira/haircards/README.md)
para conocer qué revisión de cada malla y material se probó. La evidencia
existente acredita compilación Editor Mac, reproducción local de WAV, curvas
faciales variables y retorno a reposo; también hay cancelación local probada.
Un WAV y curvas activas no demuestran por sí solos la sincronía audiovisual
percibida ni la conversación Gemini del servidor.

La comprobación nativa Windows/NVIDIA, la versión desplegada en UAM y el
recorrido de conversación/navegador de esta combinación siguen pendientes.
Esta actualización del pin no debe describirse como integración final de Lira
en producción. Las instrucciones históricas de `avatar-bridge/README.md`
sobre componentes ausentes deben contrastarse con el proyecto nuevo antes de
añadir otro receptor: evitar dos consumidores o voces duplicadas.

Antes de aceptar la combinación en UAM:

1. Registrar SHA Edutech, SHA Avatar, Unreal y plataforma; verificar assets LFS
   completos y compilar Editor en el propio Windows.
2. Abrir Nexo y Lira por separado; comprobar cámara, ropa, rostro y persistencia
   al cerrar/reabrir. Distinguir aceptación estética de funcionamiento técnico.
3. Con el puente actual de Jacobo, verificar un receptor de audio por avatar,
   su identidad y sujeto Live Link, audio sin duplicación, labios, interrupción
   y retorno a reposo durante una conversación real.
4. Probar cambios de agente/avatar y recepción audiovisual del navegador,
   anotando problemas de selección, reconexión o latencia. No inferir este
   resultado a partir de la demo WAV ni de una conexión MCP correcta.
5. Conservar logs y capturas sin secretos y el par de SHA con el resultado.
   Coordinar el despliegue por separado con quien opera el servidor.

El PR se revisa contra `feature/gemini-live-api+MVP`; no sustituye las revisiones
posteriores de esa rama ni activa servicios. El merge y la validación del
servidor deben quedar registrados explícitamente.

## Validación de esta propuesta (12 de octubre)

Avatar incorpora main 156d2d8 por merge b73784b. El receptor C++ de selección de
personaje coincide con upstream; se conserva la escena compartida de Jacobo.
El Editor combinado compiló en Mac. Prueba WAV de Lira: 801910 muestras,
curvas variables y reposo; capturas tras merge en el informe de Avatar.
Pasaron 20 pruebas locales de selección del receptor y pelo; catálogo y
Git LFS fsck se comprobaron por separado.
Se ejecutaron 35 pruebas del bridge de esta base Edutech con Unreal simulado
(protocolo, transporte y selección). No se arrancaron Docker, Gemini ni UAM.

Una actualización del submódulo incorpora assets, no un paquete cocinado.
El despliegue de `avatar-render` puede seguir usando un paquete antiguo fuera
de Git: reconstruir para la plataforma final, registrar su SHA fuente y
validar con el operador antes de sustituirlo. `lira` todavía no reemplaza a
la Lira de Santiago en el mapa compartido; revisar el diseño antes de integrarlo.

La revisión 92869b3 añade cabello Ellie Hair adaptado, límites de textura 1K–2K
y perfil Mac studio. La licencia del recurso está en `Avatar/THIRD_PARTY.md`.
Dos ciclos WAV completos y cancelación pasaron tras el ajuste. En el Editor Mac,
la comparación final registró 9585,30 MB standard y 9035,35 MB studio; el pico no
se redujo. Esto no mide el servidor ni hace definitiva la candidata estética.

## Actualización autorizada de main y base compartida

Avatar PR #1 ya se fusionó en main, revisión `30a29f7`; este pin incluye también
CI de PRs, 25 pruebas y flujo de nuevas features desde main. Los nuevos
workflows de Avatar no despliegan UAM. Protección main requiere al propietario.
Continuar agentes/frontend sobre `feature/gemini-live-api+MVP`; ver
[SINCRONIZAR_TRABAJO_UAM.md](SINCRONIZAR_TRABAJO_UAM.md) para conservar primero
los cambios que Jacobo reportó solo en el servidor. El CI del agente tiene
fallos preexistentes documentados allí; este pin no los corrige ni los oculta.
