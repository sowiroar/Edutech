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

## Decisión final del usuario

Tras la primera limpieza, el usuario pidió consolidar **main como principal**,
retirar las features activas y Gemini MVP, y conservar el respaldo de Jacobo.
La entrega final deja:

| Repo | Rama | Uso |
|---|---|---|
| Edutech | main | Única base actual para crear tareas y recibir PRs |
| Edutech | backp-fase1 | Referencia alineada con main al cierre; sin sincronía automática |
| Edutech | backup-fase-2 | Respaldo de Jacobo sin modificar, 5e5abc3 |
| Avatar | main | Única base de los seis diseños |

Solo se encontró una rama backup-fase-2. Gemini MVP apunta al mismo 5e5abc3 y ya
está contenido en la base; se retira el nombre sin perder cambios. develop y
release/1.0.0 también estaban integradas y se retiran como ramas; no se borran tags.

Santiago, Juan y Jacobo empiezan nuevas features desde origin/main y las eliminan
después del PR. Las antiguas ramas avatar-presentation y voice-validation no tenían
commits propios publicados. Los cambios locales en PCs ajenos no son visibles desde
aquí: conservarlos y seguir FLUJO.md, nunca reset ni borrado forzado.

main anterior se incorporó a la rama de entrega sin conflictos ni cambios de árbol;
la integración conserva ambas historias. El PR de esta auditoría se dirige a main.
La política CI admite feature/bugfix/chore hacia main, y el workflow de releases
ya no intenta abrir back-merge hacia develop. No hay despliegue remoto en estos
workflows; los hooks locales se desactivan mediante EDUTECH_SKIP_DEPLOY=1.

Total final: **3 ramas remotas en Edutech y 1 en Avatar**. backp-fase1 se adelanta
al merge final de main; backup-fase-2 conserva exactamente su SHA original.

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

### Retiradas adicionales tras la decisión final

| Repo | Rama | SHA anterior |
|---|---|---|
| Edutech | develop | 68cc63451268dddf4624bab6dff1c2bf2188b889 |
| Edutech | release/1.0.0 | 8562ab4998d99bea1cd6c17eeca0a264ae16ffeb |
| Edutech | feature/gemini-live-api+MVP | 5e5abc3f08185b48482d185e268120c30a78bc70 |
| Edutech | feature/avatar-presentation | 73ec96d9f3619babad463ce1353ce30f034e32dc |
| Edutech | feature/voice-validation | 73ec96d9f3619babad463ce1353ce30f034e32dc |
| Avatar | backp-fase1 | 156d2d8190bedb2e58fa66671bf6a31d161e192c |
| Avatar | feature/avatar-presentation | a204705fca64f012b5c66c605ea34dc11ee3de43 |

También se retira chore/branch-cleanup después de integrar el PR #10. Su contenido
queda en main; el PR conserva el SHA y la revisión completa. Las eliminaciones
adicionales vuelven a comprobar ascendencia y el SHA previo de cada rama.

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

Los ocho commits históricos no integrados de Edutech feature/avatar-bridge se
conservan en el tag local archive/2026-10-17/feature/avatar-bridge. El worktree
archive/Edutech-legacy queda en el mismo ac68409, con HEAD separado de una rama,
sin cambios de archivos. Se retira el nombre de rama; se conserva el bridge WAV.
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

La estructura de carpetas compartida con el equipo sigue siendo correcta. La
instrucción actualizada es comenzar desde **main** en ambos repositorios, en una
feature nueva por tarea; [FLUJO.md](FLUJO.md) contiene comandos para Santiago.
Conservar trabajo local, cerrar Unreal al cambiar ramas y coordinar locks LFS.
No cambiar el pin de Avatar en Edutech sin entrega publicada y validada.

Voz/telemetría disponibles para pruebas; aceptación humana en UAM, integración
visual y concurrencia siguen pendientes. Esta limpieza no acredita esas pruebas.
