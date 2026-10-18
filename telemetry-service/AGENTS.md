# Telemetría

Leer ../AGENTS.md y ../docs/mvp/SPEC_TELEMETRY.md. uv, pruebas y Ruff obligatorios.
No poner persistencia en ruta crítica de voz. No guardar texto/audio/secretos.
Contrato estricto versionado: regenerar JSON y probar test_schema_export al cambiarlo.
No sumar snapshots ni totales+desgloses. Tarifa/uso desconocido = null y cobertura.
Tests PostgreSQL SOLO en base llamada test; nunca truncar volúmenes del usuario.
Las tarifas se versionan por fecha. No modificar registros históricos para maquillar evidencia.
