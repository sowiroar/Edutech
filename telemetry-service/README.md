# VIVA Metrics

Colector privado FastAPI/PostgreSQL. Ver [guía completa](../docs/mvp/TELEMETRY_IMPLEMENTACION.md).
No publicar el puerto 8090; Next y el agente acceden por red interna y clave.
Contrato exportado en `../contracts/telemetry-event.v2.schema.json`.

```sh
uv sync --locked
uv run ruff check .
uv run pytest -q
```

Los tests de base se omiten sin `TEST_DATABASE_URL`; CI usa PostgreSQL efímero
con nombre de base `test`. Nunca apuntar esas pruebas al volumen real.
La migración se ejecuta transaccionalmente al iniciar con advisory lock.
`DATABASE_URL`, `TELEMETRY_INTERNAL_KEY` y `TELEMETRY_SIGNING_SECRET` son privadas.

Texto opt-in con retención separada: [guía](../docs/mvp/TELEMETRY_DASHBOARD_Y_TRAZAS.md).
