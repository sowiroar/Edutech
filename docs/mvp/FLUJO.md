# Trabajo paralelo y trazabilidad

## Repositorios

- `sowiroar/Edutech`: base compartida **backp-fase1** (ortografía exacta).
- `SantiagoGarcia205/Avatar`: base compartida **main**, Git LFS para assets.
- `backup-fase-2` se conserva como antecedente de la voz; no duplicar desarrollo allí.
- Ramas históricas permanecen. No hacer reset, force-push ni clean para sincronizar.

| Responsable | Repo / rama | Propiedad principal |
|---|---|---|
| Juan | Edutech `feature/telemetry` | Contrato, agente instrumentado, persistencia, API y panel |
| Santiago | Edutech `feature/avatar-presentation` | Selector, medios, puente, render y calidad audiovisual |
| Santiago | Avatar `feature/avatar-presentation` | Adaptación nativa de seis escenas, build y métricas NVIDIA |
| Jacobo | Edutech `feature/voice-validation` | Voz, entorno UAM, RAG/memoria, revisión y pruebas |

Cada rama nace después de integrar la preparación en la base, no de backups viejos.
Un nombre igual en dos repositorios no sincroniza sus commits automáticamente.

## Crear o actualizar una rama

Desde Edutech, shell Bash/Git Bash:

```sh
export EDUTECH_SKIP_DEPLOY=1
git status --short
git fetch origin
git switch backp-fase1
git merge --ff-only origin/backp-fase1
# Si ya existe publicada, usar git switch --track origin/feature/telemetry.
git switch -c feature/telemetry
```

PowerShell: primero `$env:EDUTECH_SKIP_DEPLOY='1'`, luego los mismos comandos Git.
Si hay cambios locales, conservarlos en su rama antes de cambiar; nunca stash automático.
Si la rama de trabajo ya existe, `git switch feature/telemetry` y fusionar
`origin/backp-fase1` en ella. No usar `pull` ambiguo entre distintas bases.

PR de feature/bugfix/chore/hotfix hacia `backp-fase1`. CI cubre esa base.
No desplegar por cambiar de rama. Usar comandos explícitos del runbook.
El mecanismo histórico de hooks existe; `EDUTECH_SKIP_DEPLOY=1` evita que actúe.
Los workflows no equivalen a protección de rama: esta cuenta tiene WRITE, no ADMIN.

## Límites para evitar conflictos

Juan define el sobre y el helper público de eventos; Santiago consume ese contrato,
no crea otra tabla de sesiones ni otro contabilizador del proveedor. Los cambios en
`app/api/token/route.ts` se coordinan: Juan lleva identidad/correlación; Santiago
agrega modalidad/capacidad sin reemplazar autenticación ni el despacho del agente.
Los cambios de rama no modifican prompts, nombres de roles ni voces por accidente.

Avatar: actualizar desde `origin/main`, una persona por mapa/Blueprint y locks LFS.
Las candidatas aprobadas Lira/Elian/Noa se conservan; Noa usa SK_Noa_AlternateFace.
Subir LFS antes del PR. El gitlink Edutech/Avatar se avanza por PR a un commit
publicado y validado de Avatar. No copiar Content a Edutech ni subir ejecutables.
Un checkout externo `../Avatar` es el lugar de edición; el submódulo es el pin de
reproducción. Solo inicializarlo si se construye desde ese checkout, evitando dos
bibliotecas de assets por necesidad inexistente.

## Entrega a Jacobo

Compartir enlace a esta carpeta docs/mvp, SHA de Edutech, gitlink de Avatar,
modalidad, sistema/driver, comando de arranque y pruebas hechas/pendientes.
Antes de actualizar UAM: revisar `git status`, rama y commits locales de Jacobo;
guardar/publicar lo pendiente, registrar configuración solo por nombres y hacer
respaldo de los datos persistentes. Probar en checkout separado con puertos propios.
No sobrescribir .env ni ejecutar `docker compose down -v`.

Los cambios de UAM no publicados no aparecen por fetch. Un merge local no los valida.

## Workspace de otro colaborador

Clonar los dos repositorios como carpetas hermanas Edutech y Avatar. No se necesita
copiar archive/tmp de Juan: son conservación local de su historia.
Desde la carpeta padre, copiar docs de contexto versionados:

```sh
cp Edutech/docs/mvp/workspace/AGENTS.md AGENTS.md
cp Edutech/docs/mvp/workspace/CLAUDE.md CLAUDE.md
cp Edutech/docs/mvp/workspace/README.md README.md
```

Las menciones a archive/tmp son condicionales al workspace original, no requisitos
para arrancar voz. Reemplazar solo el apartado de rutas locales si el equipo usa
otro layout; el contrato técnico y las ramas siguen iguales. Los históricos de
Santiago permanecen en Git; no borrar mapas para que solo aparezcan seis carpetas.
