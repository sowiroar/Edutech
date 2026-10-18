# Validación de telemetría — 17 octubre 2026

Implementación local en Mac, Docker/OrbStack. Base f072455 y rama feature/telemetry.
No despliegue UAM ni cambios de assets. Configuración privada de Jacobo comprobada;
Google/modelo/portal conservados. Modelo probado: gemini-3.8-live.

## Evidencia real

| Prueba | Resultado | Archivo |
|---|---|---|
| Saludo frontend → LiveKit → Gemini → RTC | 210720 muestras, 426 frames no nulos, speaking → listening | rtc-greeting.json |
| Texto sintético → handoff Lira→Nexus → RAG → audio | 1340640 muestras, 2747 frames no nulos; dos roles, herramientas y uso separados | rtc-handoff.json |
| Navegador Chromium, micrófono sintético silencioso | Un evento real HTML audio playing, endpoint medios 200, cero errores de página | browser-voice.json |
| PostgreSQL detenido durante saludo | 229920 muestras, saludo completo; consulta métricas 503, sin bloquear voz | rtc-db-unavailable.json |
| Emisor durante caída | Hasta 12 fallos de escritura y 6 eventos descartados observados; contadores siguen visibles en logs | db-outage-counters.json |
| Recuperación | Base disponible después de restaurarla, contador de fallos preservado por colector | health-after-outage.json |
| Panel: filtros y detalle | Cambios sin aplicar no consultan; aplicar filtra, detalle y logout correctos, sin errores JS | admin-behavior.json |
| Acceso HTTP | Rechazo anónimo/otro origen/uso falso/UUID ajeno/firma inválida; visitante estable y sesiones distintas; logout | http-access.json |

La inspección del handoff se hizo 6 s después de desconectar: todavía no mostraba
session_ended. Una consulta posterior confirmó **4 inicios y 4 cierres** de las
cuatro primeras sesiones; el cierre de LiveKit puede llegar después de ese plazo.
El saludo bajo caída puede perder eventos; no se presenta como sesión completa.
La cuenta de 12 fallos no es el número de llamadas de voz fallidas.

Se detectó la etiqueta SDK `Gemini` en lugar de `google`; las dos primeras sesiones
quedaron sin tarifa. Se corrigió el adaptador y se probó de nuevo. El historial
previo se conserva sin recalcularlo retroactivamente. Una consulta posterior
observó subtotal conocido de **0,01640885 USD**, parcial y de lista, no factura:
0,01394775 conversación + 0,00246110 RAG. Incluye varias pruebas, no precio por usuario.
Hay tokens de modalidad no especificada sin tarifa y embeddings sin usage.

Un primer script de prueba no pudo guardar su JSON por directorio de salida
inexistente; la voz y eventos quedaron en la base, pero no se usan sus muestras
como evidencia. Se corrigió la ruta y se repitió. No se ocultaron estos intentos.

## Pruebas automatizadas

- Agente: 31 pruebas, Ruff/formato. Incluye tipo LLMModelUsage del SDK instalado,
  snapshots/deltas/reinicio/caché, cola llena, transporte caído, cancelación tardía
  conservando agente, visitante aislado, proxy conservando resultado sin texto y contabilidad de
  eventos en tránsito al agotar el drenaje de cierre. Uso agregado del SDK queda
  sin agente/turno cuando no existe atribución fiable (prueba específica).
- Colector: 14 pruebas, incluidas integración PostgreSQL efímero, contrato exportado,
  costo Decimal/unknown, inicio obligatorio, deduplicación, contexto ajeno, expiración,
  auth, filtros y cobertura de latencias por eventos/intentos, no por sesiones.
- Arranque: 2 pruebas existentes. Frontend: comprobación TypeScript independiente
  del build (el build histórico omite tipos), ESLint de archivos de telemetría.
- Build Docker de frontend/agente/colector correcto. La caída no borró volúmenes.
- Capturas reales de escritorio 1440 y móvil 390, sin desbordamiento de página ni
  errores JS; controles administrativos requieren autenticación. Revisión visual
  independiente y ajustes de filtros/cobertura documentados en review.md.

## Alcance de lo demostrado

Sí: infraestructura de voz local, saludo real, handoff por texto sintético, RAG real,
uso proveedor disponible, primera reproducción en navegador y voz sin base de métricas.
No: conversación humana por micrófono, calidad pedagógica, facturación completa,
cobertura total Mem0/reintentos/bootstrap, sincronía facial, seis avatares concurrentes,
Moodle/SSO/RBAC institucional o validación Windows/NVIDIA/UAM.

Las métricas de cliente tienen confianza de cliente: el contexto se autoriza y no
pueden emitir consumo/costos, pero un navegador modificado puede mentir sobre sus
tiempos. No se usan para facturación. Costo conocido y ausencia de dato se separan.

Los scripts de acceso/runtime están en scripts/; requieren uv del agente.
`--live` señala consumo real de API. Sin grabación de audio ni transcripciones
persistidas en estos archivos. No hay credenciales en evidencia.

## Instalación limpia y CI

El primer CI falló en TypeScript: npm resolvía `@livekit/protocol` 1.51.0
junto a la copia 1.48.0 del SDK servidor; la instalación pnpm local tenía otras
versiones. Se fijan `livekit-server-sdk` 2.18.0 y protocolo 1.48.0, manteniendo
la versión del SDK ya usada por Docker/npm, y se actualizan ambos lockfiles.
También se precisa el literal `linear` de una transición existente, sin cambiar
su comportamiento. Se conserva el chequeo TypeScript independiente en CI.

Se actualiza además Next.js 15.5.18 → 15.5.28, dentro de la misma serie,
por el [aviso oficial del 14 de octubre](https://nextjs.org/blog/nextjs-security-update-october-14-2026).
La auditoría npm de dependencias runtime posterior ya no reporta críticos, pero
conserva 16 entradas (5 altas, 4 moderadas, 7 bajas); ver dependency-audit.json.
Son hallazgos de dependencias, no una evaluación de explotabilidad. Algunos
requieren migraciones mayores: esta entrega no ejecuta `audit fix --force` ni
certifica seguridad para exposición pública. Resolver ese mantenimiento antes
de producción externa; el entorno entregado sigue ligado a loopback.
