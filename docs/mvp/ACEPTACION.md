# Ensayo reproducible para el martes

Guardar resultados en docs/validation/FECHA: SHA Edutech y Avatar, equipo/OS,
modo, configuración no secreta, inicio/fin, esperado/observado y log redactado.
Las pruebas que usan API deben distinguir gasto real de fixtures sintéticos.

| Caso | Esperado | Evidencia |
|---|---|---|
| Voz sin renderer | Conecta y responde sin esperar Unreal | Audio real y sesión correlacionada |
| 3 turnos | Respuestas audibles, transcripción coherente | Eventos por turno, tiempos |
| Handoff | Conserva contexto y cambia agente | agent_changed y atributo avatar.character |
| Interrupción | Para respuesta anterior y escucha | Evento y ensayo de reproducción |
| Reinicio/conexión fallida | Error visible y recuperación | Motivo/attempt_id |
| Dos visitantes | Identidad y memoria separadas | IDs distintos, no contenido cruzado |
| Duplicación de evento | Un registro | Conteo SQL antes/después |
| Costo sin tarifa | Sin medición, no $0 | Panel y fila del ledger |
| Admin sin acceso | Rechazo | HTTP y prueba de UUID ajeno |
| Avatar no disponible | Permite Voz sin romperla | Captura y evento |
| Avatar disponible | Labios/voz sin eco; retorno a reposo | Ensayo visual, no solo ACK |
| Segunda sesión Avatar | No roba la primera | Lease/rechazo y sesión |
| 1→2→4 voz | Medir latencia, CPU, errores, uso | No equivaler a prueba de 4 renderers |

Criterio de demo: voz real y métricas P0 verificadas; avatar opcional probado.
El catálogo, compilación y tests unitarios no sustituyen estos ensayos.
No registrar aceptación que nadie ejecutó. La sesión con matrícula Moodle queda
pendiente mientras Mario/Jacobo no definan y validen el identificador institucional.
