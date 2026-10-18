# Lectura de campos y estado compartido — 17 octubre 2026

Base comprobada: PR #8 integrado en backp-fase1 `3abca14`. CI de merge
[39086759054](https://github.com/sowiroar/Edutech/actions/runs/39086759054) aprobado.
Nueva rama feature/telemetry-field-clarity; no despliegue UAM.

## Cambio

Solo presentación del detalle técnico: omite nulls del sobre, explica su ausencia,
conserva null/0/false del payload y el contrato/API/base intactos. Texto se presenta
por separado, sin duplicarlo en JSON. `unknown` histórico no se reatribuye.
Guía de equipo en ../../mvp/GUIA_METRICAS_EQUIPO.md.

## Comprobaciones

- Ruff del agente correcto; 36 pytest aprobados en esta revisión.
- 5 pruebas Node: 3 de representación/correlación ausente y 2 de medios existentes.
- TypeScript, ESLint de archivos modificados, build Docker frontend y diff-check correctos.
- Detector Impeccable del componente sin hallazgos.
- Chromium real, sesión sintética histórica que compartió el usuario: campo disponible,
  false conservado, texto no duplicado, explicaciones de agente/turno/visitante visibles.
- Escritorio 1440, tablet 768, móvil 390 y ancho CSS 720 (equivalente al viewport de
  escritorio al 200%); sin desborde de documento ni errores JS. Esto último no
  sustituye una prueba de zoom nativo completa. Ver browser.json y capturas.
- No se consumió API de modelo ni se modificaron conversaciones en este ensayo.
- El frontend local se recreó con APP_RELEASE provisional identificado como dirty;
  las sesiones previas siguen mostrando su versión original.

Repetición: `PLAYWRIGHT_MODULE=/ruta/al/modulo/playwright node scripts/test_telemetry_field_clarity.cjs`.
Requiere servicios locales y la sesión sintética documentada, aún dentro de retención.
No registra contraseña, tokens ni datos nuevos del usuario.

## Límites conservados

No implementa atribución nueva de agente/turno/request en mensajes, SSO, renderer,
latencia de reproducción por turno ni costos completos. Explicar ausentes no es
medirlos. No altera prompts, roles, backend ni diseño de voz.
