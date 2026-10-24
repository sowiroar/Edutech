# Workspace Edutech — continuidad

Esta raíz no es un repositorio Git. Leer Edutech/AGENTS.md o Avatar/AGENTS.md
antes de trabajar en el componente correspondiente. Fuente documental vigente:
Edutech/docs/mvp/README.md; las copias en docs/ pueden estar desactualizadas.

Base de desarrollo: main en cada repo. Conservar backp-fase1 como compatibilidad
y backup-fase-2 como respaldo histórico de Edutech. Trabajar en feature/bugfix/chore
y volver por PR a main. No cambiar ramas con trabajo pendiente sin conservarlo.
Definir EDUTECH_SKIP_DEPLOY=1 al operar Git. No ejecutar deploy/UAM por organizar
el workspace. No reset, clean, force-push ni stash automático.

El frontend actual muestra LIRA de Juan, NEXO y ELIAN en WebGL con LiveKit/Gemini.
Unreal no permanece abierto para conversar. No confundir seis diseños Unreal
con seis modelos web o seis roles de agente. No rediseñar LIRA, ELIAN o NOA
aprobadas por una tarea de integración. No alterar voces/prompts/RAG sin petición.

Modelos GLB y fondos se entregan privadamente; ver Edutech/THIRD_PARTY_AVATARS.md.
No versionar claves, .env, bases generadas, caches ni resultados locales. Medir
RAM, memoria comprometida y GPU por separado; una prueba no certifica UAM o SSO.
Conservar los originales de autoría y actualizar el gitlink solo con SHA publicado.
