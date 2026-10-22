# Antecedentes conservados, no instrucciones vigentes

Consultar README.md y AGENTS.md de la raíz para el estado actual.

## Consumo web medido — 21 octubre 2026

Ver `docs/validation/2026-10-21-avatar-resources/README.md`, resumen JSON y CSV.
Prueba local Chrome aislado, Unreal cerrado, entrada de audio sintética; 60 s por
llamada, 12 muestras cada ~5 s, visor 960x540, una llamada simultánea. LIRA de Juan
y NEXO mantuvieron ~30 FPS. RAM privada residente navegador media/pico: LIRA
596,6/642,7 MiB; NEXO 555,9/616,9 MiB. Solo voz: 450,6/484,7 MiB. No confundir
estos valores con PrivateBytes/commit de medidas anteriores. Docker reportó
1708,2 MiB medios con LIRA y 1729,8 con NEXO; ya está incluido en la memoria WSL.
GPU real: AMD 740M integrada, memoria compartida media 234,6/176,4 MiB para
LIRA/NEXO. NVIDIA sin asignaciones atribuidas a este navegador en las muestras.
No sumar GPU compartida otra vez a RAM ni Docker a WSL. El equipo tenía poca
RAM libre (mínimo global 0,29 GiB); no extrapolar a concurrencia, máximos de
arranque, teléfono, navegador de Codex o sesiones largas. No se modificó runtime.

## LIRA de Juan y NEXO web — estado vigente, 21 octubre 2026, cierre

El usuario confirmó que quiere LIRA de Juan, no la candidata de Santiago.
Fuente exclusiva `/Game/VIVA/Avatars/Lira/Maps/L_Lira` y `BP_Lira`; se conservaron
los originales de Unreal sin guardados. Exportación web en
`D:/EdutechRuntime/web-export/20261021-214541-lira`. Ver
`docs/mvp/AVATAR_AGENT_MAPPING.md` y `docs/validation/2026-10-21-lira-web/README.md`.
LIRA GLB 4,666,084 bytes / 75,781 triángulos, SHA
`87da34733fb1ffce0433daa6a7da9047e28b4e665abb70598f46897ae875a431`.
Rostro, uniforme, cabello, cuello y cejas SlightArch originales; shader web para
sus líneas/decal y corrección de EyeShell. Revisión técnica pasada, no aprobación
artística del usuario ni visemas. Una sola copia del personaje activo en memoria.

Frontend reconstruido en localhost:3000 y :3500. Ambas API ofrecen LIRA y NEXO.
LIRA/Aoede recibe; `avatar.character=NEXO` cambia a NEXO/Puck durante transferencia.
ELIAN/Kore conserva visual de voz, sin modelo web; no suplantarlo con NEXO.
La ausencia del atributo muestra espera, nunca un avatar elegido por defecto.
Se corrigió el arranque del agente: `ctx.connect()` ANTES de `session.start()`.
El SDK conectaba la sala y ejecutaba `on_enter` en paralelo, perdiendo el anuncio
inicial de LIRA. Voces, prompts, roles, modelos y RAG se conservaron. Agente local
reconstruido y operativo; no despliegue UAM. Prueba con entrada artificial pasó:
LIRA primero, NEXO después, audio entrante/reproducción, cero errores JS.
TypeScript, build frontend/agente, 15 pruebas frontend, 9 Python de exportación,
4 pruebas de voces/personajes y 1 regresión de arranque pasaron. Dev 3501 cerrado.
La medición de recursos de ambos personajes se añadió en el bloque superior.

## Comprobaciones previas de NEXO — 21 octubre 2026

Corrección de acceso: se identificó `edutech-frontend-1` sirviendo la plantilla
antigua en 3000, mientras NEXO funcionaba en `edutech-voice-local-frontend-1` en
3500. El frontend vigente ahora publica ambos puertos, solo en loopback.
Mantener detenido únicamente el frontend histórico; no borrarlo ni tocar sus
volúmenes. En ese primer corte solo NEXO tenía modelo web; la incorporación de
LIRA está documentada arriba. No afirmar seis avatares integrados.
Comprobados ambos puertos: interfaz actual y token de NEXO HTTP 200; origen
ajeno HTTP 403. `TELEMETRY_ADDITIONAL_ORIGINS` admite solo el alias configurado.
La llamada desde 3000 pasó con entrada artificial, audio y canvas NEXO visibles,
sin errores JS. Evidencia en call-3000.json e integrated-call-3000.png bajo
docs/validation/2026-10-21-nexo-web. TypeScript, 13 pruebas y build Docker pasaron.

Leer docs/validation/2026-10-21-nexo-web/README.md y docs/mvp/AVATAR_WEB.md.
La sesión ya comprobó escritura en C:/Users/santi/Edutech y, mediante aprobación
elevada, en D:/EdutechRuntime. No repetir las peticiones de exportación manual
por el bloqueo histórico. Caché/exportaciones permanecen en D:; código en C:.

El GLB perfil 3 funciona: 5.46 MiB, 59,578 triángulos, 235 articulaciones y reposo.
Fuente: D:/EdutechRuntime/web-export/20261021-194503. Corregidos el setter de LOD
(override_min_lod era bool), los slots de piel/dientes y animación común de cara/
ropa. Copiar directamente los canales comunes del cuerpo: preservar offsets
distintos de referencia de la cara produce intersecciones en cuello/pecho.
No volver al retarget por delta que se descartó con comparación visual.
Vértices idénticos compactados sin modificar triángulos, UV ni normales.
Texturas estimadas 24 MiB; geometría 2.25 MiB. No confundir con VRAM total.

Revisado técnicamente en producción local: ~30 FPS, GPU integrada AMD 740M,
~177 MiB adicionales de memoria privada en los procesos Chrome frente a portada.
Unreal cerrado y sin llamada durante esa medida. El manifiesto permite prueba
local; aceptación estética final y voz real se verifican aparte. Cada nueva
exportación reinicia revisiones a pending; no aprobar nuevas variantes sin verlas.
La cara fuente solo tiene 905 vértices en su LOD más detallado. Boca por amplitud
no equivale a visemas. Sin cambios guardados en assets/mapas de Unreal.

No activar renderer nativo, --avatar, MJPEG ni avatar_local.py para esta petición.
Conservar LiveKit/Gemini, roles, prompts, RAG, telemetría y cambios ajenos.
Docker reconstruido, frontend en localhost:3500. Pasó la prueba integrada con
pregunta por texto y micrófono artificial silencioso: Nexus anunció NEXO y llegó
audio, sin errores JS. Sin prueba de micrófono humano ni sincronía fonética.
Telemetría devolvió 409 inicial y luego 200; no afirmar validación integral de
telemetría. Se detuvo la copia auxiliar de Next en 3501. Ver evidencia vigente.
Con llamada conectada: Chrome privado ~606–687 MiB, CPU ~2.71% del equipo;
contenedores ~1.76 GiB en una muestra. No es consumo total de Windows/WSL ni un
máximo. GPU integrada confirmada también en la llamada. Evidencia en call.json.

## Antecedentes históricos — 18 octubre 2026

El estado del 21 de octubre reemplaza los bloqueos y pendientes de este corte.

Santiago pidió que el avatar se ejecute en el frontend sin Unreal activo.
Leer docs/mvp/AVATAR_WEB.md antes de continuar integración o medir recursos.
El visor WebGL es local. Dos GLB se exportaron pero fallaron la revisión de
apariencia/pesos; falta validar el perfil 3. No afirmar que está terminado ni que
se midió su consumo final. Exportaciones, caché y temporales ahora apuntan a
D:/EdutechRuntime. El usuario ejecutó `python scripts/avatar_web.py storage`:
15 archivos y 27,81 MiB trasladados y verificados; configuración local comprobada
y origen anterior ausente. D: tenía 228,30 GiB libres según el host. Tras devolver
los repositorios a C:, esta sesión confirmó lectura/escritura del frontend y
31,7 GiB libres en C:. El usuario mantiene la caché en D:, aún bloqueada para
esta sesión; se solicitó exportar desde PowerShell del host. Esperar su resultado
antes de iniciar otro exportador. Pasaron 12 pruebas Python, 9 del frontend y
TypeScript; /avatar-preview respondió sin errores en desarrollo (puerto 3501),
pero todavía no hay un modelo perfil 3 validado. La limpieza propuesta de cachés
npm/Next fue bloqueada anteriormente y no se ejecutó. No reintentar ese borrado
por otra herramienta. Ver AVATAR_WEB.md antes de reiniciar.
Voz/LiveKit y
prompts se conservan. avatar_local.py queda suspendido; no iniciar --avatar,
captura ni builds nativos como solución a esta petición. Unreal solo se usa
para exportar una vez, sin guardar cambios de autoría. El Docker actual todavía
necesita reconstruir frontend para mostrar los cambios. Conservar los
antecedentes del bridge; no sobrescribir trabajo ajeno para limpiar la rama.

## Main es la base única de desarrollo — 17 octubre 2026, cierre

Decisión final del usuario: trabajar desde origin/main en Edutech y Avatar.
Edutech conserva main, backp-fase1 (alineada al cerrar esta limpieza, sin sincronía
automática) y backup-fase-2 (respaldo intacto de Jacobo 5e5abc3). Avatar conserva main.
Gemini MVP y las features anteriores ya están integradas; se retiran sus nombres.
No recrear develop ni las ramas cerradas por seguir bloques históricos debajo.
Santiago crea una feature nueva desde origin/main actualizado; Juan y Jacobo igual.
PR a main, checks, merge y retiro de la rama terminada. Leer docs/mvp/FLUJO.md y
AUDITORIA_RAMAS_2026-10-17.md en esa carpeta. CI permite features a main; releases
no abren back-merge a develop ni despliegan UAM. La cuenta WRITE no configura protección.
Las bases anteriores y pruebas se conservan en la historia. UAM/renderer/concurrencia
siguen pendientes de aceptación; este cambio no altera runtime, prompts ni assets.

## Campos de telemetría y base integrada — 17 octubre 2026, cierre

PR #8 ya fusionado en `backp-fase1` `3abca14`; CI de la base aprobado
(run 39086759054). El log antiguo de 15 errores Ruff no corresponde a esta base.
Nueva rama `feature/telemetry-field-clarity` desde esa base: detalle técnico
muestra campos disponibles y explica ausentes, conserva contrato/historial y
nulls de mediciones. Leer `docs/mvp/GUIA_METRICAS_EQUIPO.md`. No inventar agente,
turno ni costo por mensaje; aún falta correlación mensaje → turno → reproducción.
Jacobo puede probar voz/telemetría; UAM y renderer siguen sin validación nueva.
El frontend local se reconstruyó; backend, prompts, activos y datos sin cambios.

## Panel y texto opt-in — 17 octubre 2026 (vigente)

Leer `docs/mvp/TELEMETRY_DASHBOARD_Y_TRAZAS.md` desde la raíz del repo.
Usuario autorizó futuras transcripciones con ocultación básica, sin audio;
prevalece sobre la prohibición histórica de texto debajo. Contrato v2, compatible
con v1, texto separado con TTL (7 días local), captura desactivada por defecto.
No reconstruir sesiones antiguas. `/admin` claro como NeoIPS; voz visual intacta.
Pruebas PostgreSQL solo base `test`. No borrar datos reales. Sin despliegue UAM.

## Telemetría implementada — 17 octubre 2026, noche

Publicado por PR #8 https://github.com/sowiroar/Edutech/pull/8 contra
`backp-fase1` f072455, sin merge ni deploy. Rama activa `feature/telemetry`. Leer
`docs/mvp/TELEMETRY_IMPLEMENTACION.md` y `docs/validation/2026-10-17-telemetry/README.md`.
Colector PostgreSQL separado, cola acotada, contrato v1, ledger/tarifas versionadas,
visitante firmado y panel privado `/admin` implementados. `voice_demo.py up` genera
secretos faltantes en `.env.voice`; contraseña administrativa solo allí.
Voz predeterminada y prompts conservados; no modificar assets/roles ni presentar
Moodle, renderer o despliegue UAM como terminados. Costos parciales: no factura.
Uso Live por snapshot/delta, alias SDK Gemini→google. RAG/memoria con cobertura
explícita; Mem0 con hilos internos y embeddings sin usage no tienen costo completo.
Prueba real Lira→Nexus+RAG correcta; navegador con micrófono sintético, audio playing.
Postgres detenido: voz sigue; 12 fallos/6 descartes observados; base restaurada.
No confundir pruebas sintéticas habladas por Gemini con aceptación humana de voz.
Selector Voz/Avatar sigue siendo feature/avatar-presentation de Santiago.

# Contexto vigente — 17 octubre 2026

Leer README.md y docs/mvp/README.md; este documento prevalece sobre instrucciones
históricas de ramas. Base compartida Edutech: backp-fase1. Voz de backup-fase-2
5e5abc3 incorporada sin migrar arquitectura. Trabajar por PR desde la base:
Juan feature/telemetry; Santiago feature/avatar-presentation; Jacobo
feature/voice-validation. Specs en docs/mvp, CI incluye PR a backp-fase1.

- Mantener LiveKit/Gemini, prompts/roles y RAG/Mem0. No copiar Pipecat/IPS de NeoIPS.
- Voz predeterminada; selector Voz/Avatar pendiente. Telemetría: ver bloque vigente arriba.
- La falla del renderer no debe tumbar voz. No compartir video/audio de una sala
  con otra; validar lease antes de concurrencia Unreal.
- Identidad Moodle pendiente: separar visitante de usuario autenticado. No usar
  estudiante_uam como identificador único para métricas/memoria de todos.
- Sin datos de costo/latencia: null y cobertura. Medir reproducción en cliente
  aparte de generación. Sin credenciales no hay prueba de conversación real.
- Arranque local: python3 scripts/voice_demo.py init/doctor/up. Windows usa python.
  compose.voice.yml aislado, sin CUDA, sin deploy UAM; .env.voice fuera de Git.
- EDUTECH_SKIP_DEPLOY=1 al operar Git. No ejecutar scripts/setup o deploy sin
  revisar host/puertos/datos. Nunca reset/clean/force-push para "sincronizar".
- Assets en repo independiente Avatar, gitlink por SHA publicado y probado.
  No traer el bridge histórico VVA1 de archive al código de Gemini.
- Leer agent-starter-python/AGENTS.md antes de editar agente. uv y lock existentes.
- Medir RAM de proceso y VRAM por separado; Mac unificada no prueba Windows.
- No divulgar claves, tokens, DSN o credenciales VPN/RDP en evidencia.
- No afirmar deploy, autenticación, voz, seis mapas cocinados o UI probados por
  un simple catálogo/CI. Ver docs/mvp/VALIDACION.md.
