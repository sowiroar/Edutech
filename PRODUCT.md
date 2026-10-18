# VIVAVerse: panel operativo de telemetría

Brief vigente: usuario, 17 octubre 2026. Rediseñar exclusivamente `/admin` como el
panel claro de NeoIPS. La interfaz de conversación de Jacobo se conserva.
Audiencia: equipo Juan/Jacobo/Santiago; operación, diagnóstico y costos parciales.
Referencia de lectura: NeoIps/frontend/src/components/admin-panel.tsx y trace-panel.tsx.

## Dirección /admin (Operate)

Fondo gris azulado, superficies blancas, texto azul oscuro, acento azul funcional.
Conservar Public Sans existente. Filtros → resumen → sesiones → herramientas →
consumo → tiempos → salud, con navegación por anclas. El detalle de sesión se
abre en primer plano de la página, con foco y tres vistas: conversación,
herramientas/acciones, todos los eventos. Sin modal ni nueva interfaz de voz.

## Producto y datos

Texto de futuras conversaciones autorizado por el usuario, ocultación básica de
identificadores, sin audio. Activación explícita por entorno, retención 7 días por
defecto; las sesiones antiguas no tienen texto recuperable. Sin argumentos ni
resultados sensibles de tools, razonamiento interno o inferencias de emociones.
Costos conocidos parciales, no factura. Ausentes = Sin dato; cobertura explícita.
Herramientas con resultado/tiempos y vínculos de ejecución; no afirmar tracing OTel.

## QUALITY BAR

Desktop 1440 y móvil 390: controles legibles, foco, sin desbordamiento de página,
tablas desplazables. Acceso/error/vacío/carga/paginación comprobables. Abrir una
sesión debe mostrar inmediatamente su detalle. Privacidad antes de encolar y
retención separada del historial técnico; voz sigue ante falla del colector.
