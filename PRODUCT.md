# VIVAVerse: panel operativo de telemetría

Fuente del brief: petición del usuario del 17-oct-2026 y
`docs/mvp/SPEC_TELEMETRY.md`. El usuario autorizó ejecutar esa especificación y
conservar la arquitectura/voz existente. La referencia NeoIPS se utiliza como
concepto de medición, no como diseño ni código copiado.

Alcance: extensión local `/admin` del frontend de Jacobo para el equipo técnico
(Juan/Jacobo/Santiago). Consultar sesiones, consumo, costos parciales, latencias,
fallos y cobertura por periodo/entorno/modo; inspeccionar eventos sin transcripciones.
No nueva identidad visual ni sitio comercial. No se solicitó rediseñar voz/avatar.

## Contrato de dirección (adaptado a extensión existente)

- THESIS: toda cifra debe poder rastrearse a eventos y límites de medición.
- OWN-WORLD: heredar Public Sans, tokens semánticos y claro/oscuro existentes.
- STORY: filtros aplicados → actividad → costo/cobertura → tiempos → sesiones/eventos → salud.
- FIRST VIEWPORT: identificar entorno/periodo y sesiones; acceso al regreso a voz.
- FORM: tablas y secciones planas, sin tarjetas decorativas ni ilustraciones.
- INTERACTION: actualización explícita y consulta coherente al paginar; no sustituir
  una sesión inspeccionada mediante polling silencioso. Scroll horizontal accesible en móvil.

## QUALITY BAR

Cifras ausentes nunca se convierten en cero; costos conocidos no se presentan como
factura. Muestras y denominador explícitos para latencias, sin inferir cobertura
por número de sesiones. Contraste, foco, formularios etiquetados, estados de acceso,
error/vacío/carga y lectura a 1440/390 px. No desbordamiento de página. No comp
aprobado: implementación en código sobre el sistema existente.

La revisión visual no certifica backend, sincronía facial, despliegue UAM o SSO.
Moodle, RBAC institucional, roles nuevos y renderer de Santiago están fuera de esta
entrega. Evidencia: `docs/validation/2026-10-17-telemetry/`.
