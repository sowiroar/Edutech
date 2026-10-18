## Panel y texto opt-in — 17 octubre 2026 (vigente)

Leer `docs/mvp/TELEMETRY_DASHBOARD_Y_TRAZAS.md` desde la raíz del repo.
Usuario autorizó futuras transcripciones con ocultación básica, sin audio;
prevalece sobre la prohibición histórica de texto debajo. Contrato v2, compatible
con v1, texto separado con TTL (7 días local), captura desactivada por defecto.
No reconstruir sesiones antiguas. `/admin` claro como NeoIPS; voz visual intacta.
Pruebas PostgreSQL solo base `test`. No borrar datos reales. Sin despliegue UAM.

# Telemetría

Leer ../AGENTS.md y ../docs/mvp/SPEC_TELEMETRY.md. uv, pruebas y Ruff obligatorios.
No poner persistencia en ruta crítica de voz. No guardar audio, secretos, argumentos de tools ni texto sin redactar. Texto opt-in según el bloque vigente.
Contrato estricto versionado: regenerar JSON y probar test_schema_export al cambiarlo.
No sumar snapshots ni totales+desgloses. Tarifa/uso desconocido = null y cobertura.
Tests PostgreSQL SOLO en base llamada test; nunca truncar volúmenes del usuario.
Las tarifas se versionan por fecha. No modificar registros históricos para maquillar evidencia.
