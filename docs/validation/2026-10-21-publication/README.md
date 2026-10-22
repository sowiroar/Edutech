# Comprobación local para publicación — 21 de octubre de 2026

Preparación sobre `feature/avatar-web-delivery`, base local `90e05a0`. Esta
validación no crea commits ni acredita un push, CI remoto o despliegue.

## Resultados

| Comprobación | Resultado |
|---|---|
| Pruebas del frontend | 35 aprobadas con los tres modelos privados instalados |
| Copia de código sin assets privados | 32 aprobadas, 3 omitidas explícitamente; cero fallos |
| TypeScript, `tsc --noEmit` | Correcto, ejecutado por separado del build |
| Lint frontend | Correcto, sin errores ni advertencias |
| Compilación Next.js | Correcta; 9 páginas generadas |
| Pruebas Python de scripts | 27 aprobadas; 1 omitida en Windows (política de ramas de shell) |
| Pruebas del agente | 48 aprobadas en contenedor temporal sin red |
| Ruff agente | Lint correcto; 24 archivos con formato correcto |
| Pruebas del bridge conservado | 50 aprobadas en contenedor temporal sin red |
| Ruff scripts y bridge | Imports/errores estáticos de scripts y reglas del bridge correctos; formato correcto en 29 y 17 archivos |
| Diferencias Git | `git diff --check` correcto |
| Configuración Compose | Validación silenciosa correcta, sin iniciar servicios |
| Modelos activos | Un GLB por personaje; SHA-256 y tamaño coincidentes con manifiestos |
| Paquete privado | ZIP de 11.998.689 bytes; sus nueve archivos de runtime coinciden con los instalados |

Total: **160 pruebas aprobadas y 1 omitida**. La política de ramas de shell se
ejecuta en CI Linux; la rama local usa el prefijo `feature/` admitido. El build
de Next omite sus comprobaciones internas de tipos/lint por la configuración
existente: ambas se ejecutaron por separado, como figura arriba.
El escenario adicional de código sin modelos no se suma a ese total: repite
la suite web en una carpeta aislada, copiando únicamente los archivos candidatos
a Git y usando las dependencias ya instaladas. Resultado en
[code-only-tests.json](code-only-tests.json).

Los fallos iniciales de temporales del sandbox no se ocultaron cambiando tests:
la suite de scripts pasó en la ejecución local autorizada. Las comprobaciones
de Ruff usaron montaje de solo lectura y caché desactivada. El primer chequeo
de formato detectó un test Python sin formatear; se corrigió. El lint ampliado
detectó diez props extraídas sin uso en TileLayout; se retiraron de la extracción
conservando su contrato público. Las comprobaciones finales pasan. No se iniciaron
llamadas nuevas a Gemini, bases de pruebas sobre producción ni servicios Unreal.

## Limpieza y alcance

Se actualizaron los README, el índice técnico y la entrega para incluir la
recuperación del arranque de LIRA, la piel mate de NEXO y el ajuste de latencia.
La instalación apunta al paquete nexo-repair vigente. AGENTS conserva el estado
actual y CLAUDE remite a él; las notas superadas permanecen bajo docs/history.
Se ordenaron imports y formato de Python sin cambiar voces, RAG ni modelos.
La web usa npm de forma coherente con su lockfile, Docker y CI; dispone de npm test.
El lint incluye ahora el arranque de sesión y los componentes de presentación.
CI ejecutará también los contratos del bridge. No se afirma que CI remoto ya pasó.

Las pruebas de los rigs instalados indican explícitamente una omisión si faltan
los GLB privados; no se cuentan como aprobadas sin ejecutar sus aserciones.
Los tests sintéticos del rig y del catálogo siguen disponibles sin esos archivos.

Las 11 exportaciones retiradas en la primera limpieza permanecen respaldadas
en data/local-avatar/publication-20261021/retired-models. En la revisión final
se trasladaron otras siete versiones históricas a retired-models-cleanup, en
esa misma carpeta privada: 36.695.536 bytes (35,00 MiB), verificados por SHA-256
después del traslado. Queda un GLB por personaje en public/avatars. No se
eliminaron los originales Unreal ni los modelos descartados.

Los tres modelos activos y sus fondos conservan sus hashes y coinciden con
el paquete viva-web-avatars-20261021-nexo-repair.zip. El ZIP mide 11.998.689 bytes
(11,44 MiB). Las imágenes Docker construidas antes del traslado no cambian;
la siguiente construcción copiará solo las versiones que quedan en public/.

El índice Git deja de incluir data/knowledge.db; su archivo local de 5.787.648
bytes se conserva. Los GLB/fondos, secretos, datos y respaldos locales están
excluidos. Manifiestos, código, documentación y evidencia seleccionada sí son
versionables. La procedencia del cabello se conserva en THIRD_PARTY_AVATARS.md.

La revisión de publicación comprueba enlaces locales de los documentos actuales,
archivos grandes y coincidencias con secretos configurados localmente o tokens
JWT/llaves privadas. No es un análisis de todo el historial Git ni garantiza
detectar credenciales desconocidas. Resultado detallado en
[prepublication-check.json](prepublication-check.json). El informe previo de
dos avatares se conserva en [prepublication-check-initial.json](prepublication-check-initial.json).

Las pruebas de voz y las mediciones de RAM/GPU son las de
[LIRA y transferencia a NEXO](../2026-10-21-lira-web/README.md) y
[recursos](../2026-10-21-avatar-resources/README.md), con las verificaciones
posteriores de [latencia](../2026-10-21-nexo-latency/README.md) y
[arranque de LIRA](../2026-10-21-lira-startup/README.md). No se presenta esta limpieza
como nueva aceptación artística, fonética, de concurrencia o de UAM.

Publicación y descripción propuesta del PR:
[ENTREGA_WEB_2026-10-21.md](../../mvp/ENTREGA_WEB_2026-10-21.md).
