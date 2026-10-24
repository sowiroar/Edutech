# Antecedentes conservados, no instrucciones vigentes

Consultar README.md y AGENTS.md de la raíz para el estado actual.

# LIRA y NEXO ejecutados en el navegador — 21 octubre 2026

## Estado vigente — 21 de octubre

Acceso local: `http://localhost:3000` y `http://localhost:3500` sirven ahora
el mismo frontend de `edutech-voice-local`. El contenedor histórico
`edutech-frontend-1` quedó detenido: servía la plantilla de LiveKit sin avatares
en 3000. No eliminar sus datos ni iniciarlo junto con el frontend vigente.
El perfil local admite explícitamente el origen 3000 mediante
`TELEMETRY_ADDITIONAL_ORIGINS`; no se desactiva la comprobación de origen.
Modelos instalados: LIRA de Juan y NEXO. Los otros cuatro aún no tienen entrega web.
LIRA procede exclusivamente de `/Game/VIVA/Avatars/Lira/Maps/L_Lira`; conservar
su variante histórica separada. Recepción Lira/Aoede → transferencia Nexus/NEXO/Puck.
Elian/Kore mantiene la visualización de voz si interviene. Ver
[correspondencia y procedencia](AVATAR_AGENT_MAPPING.md) y
[revisión de LIRA](../validation/2026-10-21-lira-web/README.md).
Se carga un solo modelo a la vez, indicado por `avatar.character`; sin señal no
se elige NEXO. La exportación de LIRA se reproduce con
`python scripts/avatar_web.py export --character LIRA`; incluye las cejas originales.

Preparación del exportador en otro Windows: Python 3, Unreal 5.8 y
`python -m pip install -r scripts/requirements-avatar-web.txt` desde Edutech.
El navegador/usuario final no requiere Python ni Unreal. No reexportar por llamada.

El perfil 3 ya se exportó y funciona en el navegador. C:/Users/santi/Edutech
permite escritura; D:/EdutechRuntime también, mediante aprobación elevada.
Se corrigieron el setter de LOD, los slots de material de la cara y la pose
compartida de cara/ropa. Copiar directamente los canales comunes del cuerpo;
mantener offsets de referencia distintos de la cara hizo atravesar el pecho
por la ropa en el intento descartado. No se guardaron assets de Unreal.

Entrega técnica de NEXO: **5.46 MiB, 59,578 triángulos, 37,203 vértices de exportación,
235 articulaciones y un reposo nativo**. Fuente:
`D:/EdutechRuntime/web-export/20261021-194503`. Compactación exacta, sin eliminar
triángulos ni modificar UV/normales; geometría de 9.9 a 2.25 MiB. Normal del pelo
limitada a 1024; texturas del visor ~24 MiB estimados con mipmaps (límite 64 MiB).

Render a máximo 30 FPS, hasta 1280 × 720 y DPR acotado, antialiasing y preferencia
gráfica low-power. Chrome eligió la AMD Radeon 740M integrada de este equipo.
No obliga a otros equipos a usar esa GPU ni traslada todo el render a CPU/RAM.
Medición de producción: ~30 FPS, ~494 MiB de memoria privada de procesos Chrome
frente a ~318 MiB en la portada (+177 MiB); heap máximo observado ~37 MiB.
No incluye llamada, Docker ni toda la VRAM. Ver
[evidencia y límites](../validation/2026-10-21-nexo-web/README.md).

`/avatar-preview` funciona sin llamada/micrófono. `/api/avatar` ofrece solo modelos
revisados técnicamente; cada instalación reinicia los campos a pending.
Apariencia final aprobada por el usuario, voz real y sincronía fonética son
comprobaciones distintas. La apertura de boca por amplitud no equivale a visemas.

Compilación de producción local y Docker correctas, TypeScript correcto. Web
actualizada en `http://localhost:3500/avatar-preview`; la copia auxiliar del host
en 3501 se detuvo. Pasó la prueba integrada con entrada artificial por texto,
personaje NEXO anunciado y audio del agente reproduciéndose. No se usó micrófono
humano. Detalles y limitaciones de telemetría en la evidencia.

## Antecedentes históricos — 18 de octubre

Los bloqueos y pendientes descritos debajo corresponden al corte del 18 de
octubre; los reemplazan el estado vigente de arriba y su evidencia.

La decisión vigente de Santiago es ejecutar el avatar en el frontend, sin mantener
Unreal abierto ni transmitir un render de Unreal. Se conserva LiveKit/Gemini y la
telemetría de voz. La preparación nativa en D: queda suspendida y
`avatar_local.py` rechaza su ejecución. El puente y sus pruebas permanecen como
antecedentes; no forman parte de este recorrido. No usar `--avatar` para iniciar
esta variante.

## Estado real

Actualización tras devolver el proyecto a C: (18 de octubre): se confirmó lectura
y escritura en `C:/Users/santi/Edutech/Edutech`; Git vuelve a responder. C: tenía
31,7 GiB libres en esta comprobación. El usuario eligió conservar caché, shaders
y resultados de exportación en `D:/EdutechRuntime`, aún inaccesible desde esta
sesión. La exportación se solicitó desde PowerShell del host; falta su resultado.
No se debe iniciar una segunda exportación mientras esa operación esté activa.

Se corrigió la comprobación del disco de Windows: ya no se confunde con el disco
donde está el repositorio. Pasaron 12 pruebas Python (almacenamiento, validación
GLB y procesamiento), 9 pruebas seleccionadas del frontend y TypeScript.
El visor de desarrollo respondió HTTP 200 en `http://127.0.0.1:3501/avatar-preview`,
sin errores JavaScript y sin crear un canvas para el modelo antiguo rechazado.
Esto verifica la ruta de vista previa, no el personaje ni su rendimiento.
No hay una compilación de producción nueva ni una medición del modelo final.

Implementado localmente: visor Three.js cargado solo al elegir Avatar, lectura de
un GLB instalado, vista `/avatar-preview` sin llamada ni micrófono, recuperación
a voz si falla WebGL y descarga de muestras de rendimiento. La interfaz no
anuncia NEXO disponible mientras falte su archivo. Voz sigue siendo la opción
predeterminada. Otro personaje del agente vuelve a la animación de voz hasta
tener su propio modelo; no se presenta NEXO como LIRA/ELIAN.

Se generaron dos exportaciones reales desde PowerShell del usuario. El perfil 1
produjo 3,9 MiB, pero falló la revisión visual de cara y materiales. El perfil 2
produjo unos 22 MiB y presentó pesos de piel incorrectos en el GLB. Ninguno es
una entrega aceptada. El perfil 3 usa la malla fuente para evitar la ruta de
buffers del exportador; su exportación y revisión visual están pendientes.
Los intentos anteriores de iniciar Unreal desde la sesión restringida terminaron
sin exportar. Actualmente la exportación queda a cargo del host por el bloqueo
de D:. Tampoco está reconstruido el frontend de Docker.
No se ha validado apariencia, ropa, labios, movimiento o consumo del modelo final.
Las pruebas de código usan fixtures. Pasaron TypeScript, las pruebas anteriores
del frontend y 8 pruebas de validación/traslado del exportador.
La compilación de producción se detuvo con EPERM en `.next`, incluso tras
conceder escritura a esa carpeta; queda pendiente ejecutarla en el host/Docker.

## Exportación única

### Almacenamiento local en D:

El intento del 18 de octubre a las 14:36 creó una caché adicional en C: y se
detuvo con `avatar_web.py cancel`, confirmado por el usuario. C: llegó a llenarse.
El usuario ejecutó este comando desde PowerShell del host y confirmó el traslado:
15 archivos, 27,81 MiB, verificados por SHA-256. Se comprobó además que el archivo
de configuración apunta a D: y que el origen de C: ya no existe. Esta sesión
continúa sin acceso efectivo a los archivos de D:, incluso con permiso de lectura.

```powershell
python "C:\Users\santi\Edutech\Edutech\scripts\avatar_web.py" storage
```

Traslada únicamente `Edutech/data/local-avatar/web-export` a
`D:\EdutechRuntime\web-export`. Copia todos los archivos, comprueba SHA-256 y
solo entonces retira los originales verificados. Un conflicto o copia incompleta
conserva los originales. Guarda un registro de verificación en D: y la ubicación
en `data/local-avatar/web-storage.json`, fuera de Git. Puede repetirse después
de un traslado completo. No migra los repositorios, Docker ni la instalación de
Unreal. La carpeta de resultados ocupa unos 28 MiB; su traslado no libera varios GB.

Después del traslado el host informó 0,45 GiB libres en C: y 228,30 GiB en D:.
Se identificaron dos cachés regenerables: `agent-starter-react/.next/cache`
(587,36 MiB) y `C:/Users/santi/Documents/Codex/2026-09-09/new-chat-2/work/npm-cache`
(201,98 MiB). El intento de limpieza fue rechazado antes de ejecutarse porque
requiere aprobación de sandbox no disponible en esta sesión. No se borraron y
no se deben eludir esas restricciones cambiando de herramienta. Esta fue la
situación anterior al traslado de vuelta a C:; el espacio disponible actual y
las comprobaciones más recientes están indicados en «Estado real».

Las exportaciones nuevas usan D: por defecto, sin retorno automático a C:.
Allí van registros, GLB bruto y optimizado, `DerivedDataCache`, `UnrealUser`
(Saved/Intermediate), `ShaderWorkingDir` y TEMP/TMP del proceso exportador.
La primera caché de D: puede requerir compilar shaders. Los assets de autoría
y la pequeña copia pública del modelo web permanecen en sus ubicaciones actuales.
El exportador exige 10 GiB disponibles en destino y 1 GiB en C: para Windows;
no inicia Unreal si falta espacio. Windows y su archivo de paginación no se
trasladan con esta configuración.

Guardar y cerrar el editor antes de esta operación evita cargar dos editores.
No es necesario iniciar el MCP, Docker ni un renderer para exportar:

```powershell
python "C:\Users\santi\Edutech\Edutech\scripts\avatar_web.py" export
```

El comando abre el exportador de Unreal, lee
`/Game/VIVA/Avatars/Nexo/NativeFinal/L_Nexo_Mateo_Work`, termina y valida el GLB.
No guarda mapas ni assets de autoría. Selecciona los actores de NEXO, exporta
la malla fuente de LOD 0, conserva pesos de piel y morphs, y solicita texturas
horneadas de 512 px. El procesamiento posterior conserva los cuatro pesos de
mayor influencia por vértice, normaliza sus valores, retira huesos sin uso y
registra la influencia descartada. Rechaza vértices sin pesos válidos. El límite
de tamaño se comprueba sobre el archivo procesado, no sobre el bruto.
Los materiales con ajustes propios pueden requerir revisión adicional.
No incluye el fondo como geometría; se copia `Avatar/Uam-virtual.jpg` para CSS.
Los archivos generados y la entrega pública local están fuera de Git.

La entrega está limitada a 20 MiB y 100.000 triángulos. Son límites iniciales de
admisión, no valores medidos de NEXO ni garantías de rendimiento. Un archivo que
los exceda se rechaza para poder simplificarlo antes de habilitarlo. Se exige
GLB autónomo, sin referencias de texturas externas, y presencia de esqueleto.
El nombre del modelo contiene su SHA-256; el manifiesto anterior se respalda.

Registros de cada intento:
`D:\EdutechRuntime\web-export\<fecha-hora>\` (tras el cambio de almacenamiento).
Salida instalada:
`Edutech/agent-starter-react/public/avatars/nexo/`.

Tras obtener y revisar el modelo, reconstruir solamente la web con el comando
existente. Esta sesión no tiene acceso al motor Docker del host:

```powershell
python "C:\Users\santi\Edutech\Edutech\scripts\voice_demo.py" web
```

Abrir `http://localhost:3500/avatar-preview`. Unreal debe permanecer cerrado
durante las mediciones. La exportación no debe repetirse para cada conversación;
solo cuando cambien los assets que se entregan.

## Rendimiento y animación

- Render limitado a 30 FPS, relación de píxeles 1 y ancho interno máximo 960 px.
- Sin sombras dinámicas, posprocesado, física de ropa o Groom.
- Se pausa al ocultar la pestaña y libera geometrías, texturas, skeletons,
  contexto WebGL y analizador opcional al salir.
- Se descarga un archivo estático. No hay captura MJPEG, reserva compartida de
  renderer ni proceso Unreal por usuario.
- El audio lo reproduce únicamente LiveKit. Un analizador local puede controlar
  un morph o los huesos identificados de mandíbula del perfil Mateo. Se calculan
  los ejes a partir del rig; **no equivale a visemas ni a lip sync fonético**.
  La prueba de apertura de boca en la vista previa es sintética, sin micrófono.
- El perfil 3 solicita el reposo nativo para cuerpo y ropa. El procesamiento
  copia canales de cuerpo a cara únicamente cuando coinciden los nombres y las
  transformaciones locales de enlace. El Leader Pose de Unreal no se traslada
  por sí solo al GLB. Ropa, cara y accesorios siguen pendientes de revisión visual.

La vista previa conserva como máximo 120 muestras, una por segundo visible.
Registra FPS, tiempo de envío de render en CPU (no tiempo de GPU), triángulos,
llamadas de dibujo, conteos de recursos, bytes del modelo, tiempo de carga y
heap JavaScript si el navegador lo expone. Ese heap **no mide RAM total ni VRAM**
y puede incluir otros contextos del proceso. El informe no contiene audio,
transcripciones, credenciales ni tokens.

Comparar reposo de voz, vista previa del modelo y conversación real por separado,
con iguales tamaño de ventana y condiciones. Medir además RAM de los procesos
del navegador y GPU global con las herramientas del sistema; registrar las
aplicaciones abiertas para no atribuir su consumo al avatar. La conversación
requiere permiso de micrófono del usuario. No inferir sincronía por FPS.

La muestra de servicios aportada por Santiago suma **1504,53 MiB (~1,469 GiB)**
sin avatar. Los 570 MiB de GPU eran globales del equipo. Ninguna de esas cifras
demuestra todavía cuánto consume esta presentación web.
