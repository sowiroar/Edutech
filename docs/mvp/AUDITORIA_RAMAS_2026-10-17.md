# Auditoría y limpieza de ramas del 17 de octubre de 2026

## Resultado

Retiradas 14 ramas remotas de Edutech y 7 de Avatar, todas con sus commits
alcanzables desde una base conservada. No se eliminaron commits, assets, datos,
worktrees ni archivos locales. No hubo despliegue UAM ni cambios de arquitectura.
Las eliminaciones se aplicaron de forma atómica por repo, comprobando el SHA
previo de cada referencia y sin habilitar actualizaciones forzadas. Un cambio
concurrente en cualquiera de las ramas habría rechazado la operación completa.

La base funcional Edutech revisada es `43d42d9` (PR #9 integrado; CI 39091125838
aprobado). Avatar main es `a204705`. La documentación de esta auditoría se integra
por un PR adicional; no cambia el comportamiento de la demo.

## Ramas que siguen disponibles

| Repo | Rama | Uso |
|---|---|---|
| Edutech | backp-fase1 | Base compartida actual del MVP |
| Edutech | feature/avatar-presentation | Trabajo activo de Santiago |
| Edutech | feature/voice-validation | Pruebas y ajustes de Jacobo |
| Edutech | main, develop | Bases anteriores conservadas; no contienen por sí solas la telemetría actual |
| Edutech | backup-fase-2 | Antecedente de voz de Jacobo |
| Edutech | feature/gemini-live-api+MVP | Histórico de integración Gemini conservado |
| Edutech | release/1.0.0 | Release histórica conservada |
| Avatar | main | Base compartida de los seis diseños |
| Avatar | feature/avatar-presentation | Trabajo activo de assets de Santiago |
| Avatar | backp-fase1 | Respaldo histórico conservado |

Solo se encontró **una** rama remota llamada backup-fase-2. Esta y Gemini MVP
apuntan ambas a `5e5abc3`; se conservaron las dos por petición del usuario.
No se creó una segunda rama backup inexistente. Total objetivo tras retirar
la rama temporal de esta documentación: **8 ramas en Edutech y 3 en Avatar**.
Las features activas se conservan para separar trabajo paralelo de las bases.

Las ramas de Santiago y Jacobo partían de `73ec96d`, sin commits propios publicados.
Se adelantan a la base compartida actual al cerrar la limpieza, validando el SHA
anterior. Sus cambios locales en otros equipos no son visibles desde aquí;
para incorporarlos, seguir FLUJO.md y no hacer reset/force-push.

## Referencias retiradas

Cada SHA siguiente sigue en la historia de la base indicada. La eliminación
retira el nombre de rama, no el trabajo ni los PRs.

### Edutech

| Rama retirada | SHA | Base que conserva los commits |
|---|---|---|
| bugfix/local-rag-bootstrap | `d99b28075999f8ea39b0ee0934784bca7d2b0c6a` | origin/backp-fase1 |
| checkpoint/pre-mvp-fase1-20261017 | `f1ccd3cf7decea6e7d5ea735c808a0083bad0cf7` | origin/backp-fase1 |
| chore/local-config-cleanup | `f058bfcfe848891db75f2aedc508bd2237513f86` | origin/backp-fase1 |
| chore/mvp-shared-base | `476f13d5a8c5a17d487525ac576692eb15e04c20` | origin/backp-fase1 |
| feature/avatar-family-sync | `09694cb317c814db4f74e3e6d5f1122b279aaf7e` | origin/backp-fase1 |
| feature/document-host-ollama | `001dc50aab1da80ab3516a36af993b652b93c0cd` | origin/backp-fase1 |
| feature/gemini-live-api | `739ee1e5c0855a796f252e53bd05d85f6c690aa9` | origin/backp-fase1 |
| feature/gitflow-ci-autodeploy | `d67ebfe218a5a8c1a2d7189d38c7fc3f3de50697` | origin/backp-fase1 |
| feature/knowledge-sources | `fa27986e9fc0740b2a133be9277dd0399559f92d` | origin/backp-fase1 |
| feature/local-stt-nemotron | `14aea88980f8711a463f5fde453cd7127fd3810a` | origin/backp-fase1 |
| feature/local-stt-whisper | `a15280fb419d8763db0ed941b8336bf77a4ade55` | origin/backp-fase1 |
| feature/multi-agent-orchestrator | `5542ac77e8dd01b10d8dbde02934427a42852fdf` | origin/backp-fase1 |
| feature/telemetry | `e92354c2dd04f527d20b2cebeb50a2a160cc52d7` | origin/backp-fase1 |
| feature/telemetry-field-clarity | `8250f4d59ce07e93c69fd9ab18ccec1314d8f779` | origin/backp-fase1 |

### Avatar

| Rama retirada | SHA | Base que conserva los commits |
|---|---|---|
| chore/family-handoff | `24154c2d55d30168a9a85a632ab66061ededc2c1` | origin/main |
| feature/avatar-family | `4b7107687ae2e834346739f8be5155ae9388b465` | origin/main |
| feature/elian-design | `418f7e839ec12b930a3cfcce0f02d7ce2b0efdda` | origin/main |
| feature/family-memory | `81e0e3eefbbc438a76a488b27352af736868734f` | origin/main |
| feature/lira-render | `7a83ccf8edc3ba8bc71ac32cf3e94facacf31656` | origin/main |
| feature/nexo-nova-finish | `e0e92de4f3c821cbf97a0a9fe933d46e74182009` | origin/main |
| feature/noa-design | `2cbe5654cbf4a0f37bb38ab7f21e2b32724a1e6d` | origin/main |

## Respaldos y excepciones locales

Antes de limpiar se generaron y verificaron bundles Git completos y un inventario
de referencias, guardados localmente en `../archive/branch-audit-20261017/` desde
Edutech. También se respaldó el diff de la guía editada por el usuario; se conserva
su actualización al PR #9 y se corrigen dos errores de escritura. Los bundles no
contienen los binarios LFS ni los archivos ignorados; no se eliminaron sus cachés,
objetos ni copias existentes. No se subieron secretos ni bundles a GitHub.

En Avatar, tres referencias con commits no integrados se conservaron como tags
**locales**, bajo `archive/2026-10-17/`: checkpoint/local-integration-20261008,
feature/edutech-integration y feature/noa-design. No se perdieron esos commits
al retirar las ramas locales. El checkpoint de Noa no es una mejora pendiente:
es el guardado previo a la optimización aprobada.

Edutech conserva una excepción local: feature/avatar-bridge, con ocho commits
históricos no integrados, usada por el worktree archive/Edutech-legacy. No se
publicó esa rama ni se borró el worktree: contiene el bridge de las demos WAV.
No confundirlo con el puente Gemini ni volver a fusionarlo automáticamente.

Para recuperar una rama remota retirada, desde un clon actualizado:

```sh
git fetch origin
git branch recuperacion/nombre SHA_DE_LA_TABLA
# Revisar antes de publicar; restaurar una rama no despliega servicios.
```

Los objetos están en las bases retenidas. El bundle local también permite
recuperar referencias si se necesitara restaurar el estado anterior. Los tags
locales de Avatar no están disponibles automáticamente en otro ordenador.

## Cómo continuar

La estructura de carpetas que se compartió con el equipo es correcta. La rama
se escribe exactamente `backp-fase1`, sin espacios. Primero conservar cambios,
fetch/prune y actualizar la feature de Santiago como explica [FLUJO.md](FLUJO.md).
En Avatar, cerrar Unreal antes de cambiar rama y actualizar desde origin/main;
coordinar mapas/Blueprints y locks LFS. No cambiar el pin de Avatar en Edutech
sin una entrega publicada y validada.

La voz/telemetría ya pueden probarse; la aceptación humana en UAM, integración
visual y concurrencia siguen pendientes. Esta limpieza no acredita esas pruebas.
