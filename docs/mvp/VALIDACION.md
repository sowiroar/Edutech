# Validación de preparación — 17 octubre 2026

No equivale a aceptación del MVP ni prueba real de Gemini/UAM.

## Comprobado

- Fetch de ambos repositorios; fase1 es ancestro de fase2 (18 commits).
- Git worktree reparado tras organización; repos históricos y archivos locales conservados.
- Avatar: descarga LFS completa, fsck correcto, 13 entradas verificadas, 36 tests.
- Frontend de fase2: npm ci y build Next.js correctos con Node 24. El proyecto
  omite lint/typecheck en build por configuración previa: no son validaciones hechas.
- Agente antes de correcciones: 19 pruebas correctas, 15 hallazgos Ruff y seis
  archivos sin formato. Se corrigen imports/Any, formato y conservación de tareas
  de fondo; no se cambian prompts. Tres pruebas nuevas de retención/error/cancelación. Resultado final: 22 tests,
  Ruff y formato correctos. Knowledge-sync: 11 tests, Ruff y formato correctos.
- Perfil local: config Compose válido y dos pruebas del lanzador correctas.
- Motor OrbStack iniciado; LiveKit y Qdrant arrancados en proyecto aislado;
  HTTP LiveKit responde OK. Frontend y POST /api/token responden 200; un cliente
  RTC se conectó y desconectó con ese token. No se imprimió ni persistió el token.
  No se publicó micrófono ni se ejecutó un agente en esa prueba.
  Otros contenedores existentes no se modificaron.

## Límites y bloqueo real

El checkout no tenía .env/.env.local. Se creó .env.voice excluido de Git con
GOOGLE_API_KEY y GEMINI_LIVE_MODEL vacíos. Deben configurarse localmente; el doctor
los detecta sin imprimir valores. No se llamó a Google, no se midió voz conversacional,
RAG/Mem0 con proveedor ni gasto real. El ID histórico del modelo no se certifica.
No se accedió a UAM ni se ejecutó Unreal en esta preparación. No se reconstruyó
el paquete de seis avatares. No hay nuevo dato NVIDIA/RAM/VRAM/FPS.
Selector y telemetría son specs para las features, no funcionalidades ya entregadas.

## Reproducción

Ver RUNBOOK.md y ACEPTACION.md. Separar tests de código/configuración, conectividad
LiveKit y conversación de usuario. Registrar los resultados posteriores aquí o en
un informe fechado; nunca cambiar pendientes a exitosos sin ejecutar el ensayo.

Avatar PR #8 integrado en main a204705fca64f012b5c66c605ea34dc11ee3de43;
checks repository/tests/required aprobados. Edutech fija ese SHA para reproducción.
