# Trabajo paralelo desde main

## Bases compartidas

**main es la única base de desarrollo en ambos repositorios.** Cada tarea nace
del último origin/main y vuelve mediante PR a main. No editar todos directamente
sobre la misma rama ni reutilizar una feature que ya fue cerrada.

| Repositorio | Ramas que se conservan | Uso |
|---|---|---|
| sowiroar/Edutech | main | Voz, telemetría, frontend e integración actuales |
| sowiroar/Edutech | backp-fase1 | Referencia de compatibilidad, alineada con main al cierre de la limpieza |
| sowiroar/Edutech | backup-fase-2 | Respaldo intacto de la voz de Jacobo en 5e5abc3 |
| SantiagoGarcia205/Avatar | main | Base actual de los seis diseños |

backp-fase1 no se sincroniza automáticamente ni recibe features: la fuente actual
es main. Gemini MVP ya está integrado y se retira su nombre de rama; también
se retiran develop, release/1.0.0 y las features terminadas. Sus commits permanecen.
[Auditoría y recuperación](AUDITORIA_RAMAS_2026-10-17.md).

## Santiago empieza una rama nueva

En Edutech, desde un checkout sin cambios pendientes:

```sh
export EDUTECH_SKIP_DEPLOY=1
git status --short
git fetch --prune origin
git switch main
git merge --ff-only origin/main
git switch -c feature/avatar-presentation
```

PowerShell: usar `$env:EDUTECH_SKIP_DEPLOY='1'` antes de los comandos Git.
Si main no existe localmente: `git switch --track origin/main`.
Si la feature antigua todavía existe en su PC, no reemplazarla: revisar sus commits
con `git log origin/main..feature/avatar-presentation --oneline` y conservar cambios
sin publicar. Puede comenzar con otro nombre, por ejemplo feature/avatar-video,
y trasladar solo los commits necesarios tras revisarlos. No usar reset/clean/stash
ni borrado forzado para sincronizar. `fetch --prune` no borra ramas locales.

En Avatar, cerrar Unreal y usar el mismo flujo desde origin/main. Las ramas de
ambos repositorios son independientes. Compartir nombre no sincroniza cambios.

Juan crea su próxima tarea como feature/telemetry-turns; Jacobo puede usar
feature/voice-validation. Son ejemplos para ramas nuevas, no ramas permanentes
que todos deben mantener. Las nuevas tareas pueden trabajar en paralelo.

## Publicar y cerrar una tarea

1. Publicar la feature y abrir PR a main con pruebas y límites explícitos.
2. Revisar CI y conflictos. Integrar mediante merge, sin reescribir historia.
3. Comprobar que el tip de la rama quedó contenido en main y eliminar la feature.
4. Para otra tarea, crear una rama nueva desde origin/main actualizado.

CI de Edutech admite feature/bugfix/chore y release/hotfix versionados hacia main.
La publicación de una release versionada conserva tags/notas, sin crear develop
ni desplegar UAM. Los checks no equivalen a protección de rama: la cuenta tiene
WRITE, no ADMIN. No se ha configurado una protección administrativa nueva.

## Responsabilidades y coordinación

- Juan: telemetría, identidad/correlación, costos y panel privado.
- Santiago: selector, medios, puente, render, escenas y calidad audiovisual.
- Jacobo: aceptación de voz, entorno UAM, RAG/memoria y revisión.

Compartir el contrato de telemetría y sesión. Coordinar cambios en
app/api/token/route.ts; no duplicar tablas ni contabilizadores por presentación.
Mantener roles, prompts y arquitectura; una falla de renderer no debe tumbar voz.

Unreal: una persona por mapa/Blueprint, locks LFS y assets por PR a Avatar main.
Subir LFS antes del SHA. Lira/Elian/Noa aceptadas no se rediseñan; Noa conserva
SK_Noa_AlternateFace. El pin de Edutech/Avatar avanza en otro PR tras validar
la entrega nativa. No copiar Content ni ejecutables a Edutech.

## Pruebas y servidor UAM

Seguir [RUNBOOK.md](RUNBOOK.md). Antes de actualizar UAM, identificar rama,
commits/procesos y trabajo local de Jacobo; conservar .env y datos. No ejecutar
hooks de despliegue por cambiar de rama. EDUTECH_SKIP_DEPLOY=1 en operaciones Git.
Los cambios del servidor que no estén publicados no se recuperan con fetch.
Esta limpieza no certifica aceptación en UAM ni concurrencia audiovisual.

## Workspace para el equipo

Clonar Edutech y Avatar como carpetas hermanas. Desde la carpeta padre:

```sh
cp Edutech/docs/mvp/workspace/AGENTS.md AGENTS.md
cp Edutech/docs/mvp/workspace/CLAUDE.md CLAUDE.md
cp Edutech/docs/mvp/workspace/README.md README.md
```

No copiar archive, cachés o secretos del PC de Juan. Los respaldos históricos
locales no son requisitos para arrancar la voz actual.
