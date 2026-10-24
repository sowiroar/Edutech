# Recuperación del arranque de LIRA

Revisión del 21 de octubre de 2026, America/Bogota, tras el aviso «Agent did not
join the room» y el botón «Conectando…» bloqueado.

## Evidencia y corrección

El intento de las 22:40:28 llegó al worker y anunció LIRA, pero Gemini Live
falló al conectar con `OSError: [Errno 101] Network is unreachable`; el SDK cerró
la sesión. El intento siguiente no encontró un proceso precargado y esperó unos
13,5 segundos antes de entrar al código de sesión. No se atribuye este fallo a
la malla de LIRA ni al acabado mate de NEXO.

La comprobación de red posterior encontró HTTPS hacia Google operativo. Durante
la reconstrucción también falló una resolución DNS de Docker Hub; el reintento
funcionó después de volver a comprobar DNS y TCP. Esto no demuestra que la red
sea permanentemente estable. No se modificaron DNS, firewall ni credenciales.

El cliente tenía un límite de 20 segundos para que llegara el agente, inferior
a varias precargas observadas de 25–62 segundos. Se amplía a 90 segundos, sin
añadir espera a un worker ya preparado. El inicio completo tiene un límite de
95 segundos. Una desconexión cancela la espera pendiente del SDK y libera el
botón para iniciar una llamada nueva. Los errores se muestran en español y ya
no remiten al usuario a una guía para desarrolladores. Se impide el doble inicio.

Se mantienen los agentes, voces, documentos, modelos web y materiales. No se
aumenta el número de procesos precargados ni se abre Unreal.

## Verificación de código

Se escribieron primero cuatro pruebas de ciclo de inicio. Verifican desconexión
con promesa del SDK pendiente, tiempo agotado, éxito sin cortar la conexión y
conservación de un error de permiso/token. Pasan las cuatro, más las tres pruebas
de origen autorizado. ESLint, TypeScript, Prettier y compilación de producción
completados. El frontend local fue reconstruido.

## Prueba del recorrido publicado

Un navegador aislado creó una sala sintética sin worker y la cerró antes de que
terminara start(). El botón «Iniciar llamada» volvió a habilitarse y apareció el
mensaje de conexión interrumpida. Sin recargar, inició otra sala: se retrasó
deliberadamente el envío del worker 25 segundos. La web mantuvo la conexión más
allá del antiguo límite de 20 segundos; después LIRA apareció y emitió audio.
Se terminó esa llamada y se abrió una tercera con despacho normal: LIRA volvió
a aparecer y hablar. Un solo avatar por sala y cero errores JavaScript.

La prueba usó preguntas/arranque sintéticos, micrófono falso silencioso y detección
de audio por RMS. Solo cerró una sala creada por el propio navegador de prueba;
no interrumpió salas del usuario. Resultado en [recovery.json](recovery.json).
Comprueba recuperación y disponibilidad local, no ausencia futura de caídas de red.

Evidencia privada en `data/local-avatar/lira-startup-20261021/`. No se almacenó
audio ni se usó el micrófono real. No se hizo commit, push ni despliegue UAM.
