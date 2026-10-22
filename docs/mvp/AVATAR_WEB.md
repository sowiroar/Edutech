# LIRA, NEXO y ELIAN en el navegador

## Arquitectura y estado

El frontend usa Three.js/WebGL para dibujar el GLB del agente activo. LiveKit
transporta la voz de Gemini; Unreal solo prepara el modelo, no renderiza la llamada.
LIRA de Juan recibe con Aoede; al transferir a Nexus se carga NEXO/Puck.
ELIAN/Kore usa el modelo de su escena original. ATLAS, NOVA y NOA existen como
assets de Unreal, pero no tienen agentes implementados en este worker.
[Correspondencia y procedencia](AVATAR_AGENT_MAPPING.md).

`/api/token` publica los metadatos disponibles. El visor sigue `avatar.character`,
no el nombre del worker, libera el modelo anterior y mantiene voz ante error.
La sala se conecta antes de iniciar la sesión para conservar el primer anuncio.
Sin señal o modelo no se suplanta al agente con NEXO.
La espera de conexión se cancela ante desconexión y tiene un límite de 95 s
(90 s para la llegada del agente). Un error vuelve a habilitar el inicio de llamada;
ver [recuperación de LIRA](../validation/2026-10-21-lira-startup/README.md).

## Ejecutar y entregar

Seguir el [README principal](../../README.md). Ambos puertos locales, 3000 y 3500,
sirven el mismo frontend. `/avatar-preview?character=LIRA`, `?character=NEXO` y `?character=ELIAN`
permiten inspeccionar sin abrir una llamada ni activar micrófono.

Los GLB y fondos se instalan desde la [entrega privada del equipo](../../agent-starter-react/public/avatars/README.md).
Los manifiestos versionados identifican el SHA-256 de cada versión revisada.
Un clon sin modelos mantiene la voz; no debe anunciar avatares disponibles.
Después de instalar modelos: `python scripts/voice_demo.py web`.

## Exportación única desde Unreal

Requisitos de autoría: Windows, Python 3, Unreal 5.8 y el proyecto hermano
`../Avatar/Avatar1.uproject` con los assets necesarios. Instalar dependencias:

```powershell
python -m pip install -r scripts/requirements-avatar-web.txt
```

Guardar y cerrar el editor antes de exportar. Desde la raíz de Edutech:

```powershell
python scripts/avatar_web.py export --character NEXO
python scripts/avatar_web.py export --character LIRA
python scripts/avatar_web.py export --character ELIAN
```

Ejecutar una exportación a la vez. El exportador usa un proceso de Unreal,
lee los assets y termina sin guardar modificaciones de autoría. No necesita
MCP, Docker ni un renderer continuo. El usuario final no necesita Unreal o Python.

El almacenamiento se configura en `data/local-avatar/web-storage.json`, fuera
de Git. En el equipo de autoría, la caché, shaders, temporales y resultados
están en `D:/EdutechRuntime`. `avatar_web.py storage` prepara esa ubicación;
no mueve el proyecto ni el archivo de paginación. El script exige espacio libre
y no vuelve automáticamente a C: si D: falla.

Para diagnosticar, revisar `web-export/<fecha-hora>/` en esa ubicación.
`avatar_web.py cancel` detiene únicamente exportadores identificados por el script.
No iniciar varios editores para reintentar el mismo fallo.

## Fuentes y calidad

| Personaje | Fuente | GLB revisado | Geometría |
|---|---|---:|---:|
| NEXO | /Game/VIVA/Avatars/Nexo/NativeFinal/L_Nexo_Mateo_Work | 5,70 MiB | 64.330 triángulos, 420 joints |
| LIRA de Juan | /Game/VIVA/Avatars/Lira/Maps/L_Lira | 4,45 MiB | 75.781 triángulos, 486 joints |
| ELIAN | /Game/VIVA/Avatars/Elian/Maps/L_Elian | 4,38 MiB | 61.977 triángulos, 215 joints |

LIRA conserva sus cejas SlightArch, cabello en tarjetas y cuello. Sus líneas
procedurales se adaptan al shader web; EyeShell necesita transparencia corregida.
Conservar atribuciones del [cabello y recursos](../../THIRD_PARTY_AVATARS.md).
LIRA, NEXO y ELIAN comparten la imagen Uam-virtual por petición del usuario.
NEXO recupera los materiales procedurales de ropa y trazos faciales,
el acabado de su pelo y un encuadre más cercano. Su piel usa rugosidad completa,
reflejo especular atenuado y una luz principal más suave; los ojos mantienen su
material independiente. Este ajuste del visor no cambia el GLB ni los assets Unreal.
ELIAN conserva gafas, cabello,
uniforme, mangas y cuello. Sus ojos y dientes se hornean sobre su propia cara:
los grupos sin nombre del asset requieren reasignar los cuatro slots al exportar.
El packer verifica posiciones/índices y copia las UV de ese horneado antes de
incorporar sus texturas; no toma el rostro de otro personaje. El visor oculta
solo la falda lateral de piel cubierta por el uniforme para evitar intersecciones.

Se conservan los diseños y assets originales, pero glTF/WebGL no reproduce
automáticamente todos los shaders, iluminación ni posprocesado de Unreal.
No se promete una imagen idéntica píxel a píxel.

El perfil 3 conserva malla fuente, materiales, pesos y reposo. La compactación
de vértices no elimina triángulos ni cambia UV/normales. Los canales comunes de
cara y ropa deben seguir directamente al cuerpo: el retarget por offsets de
referencia de intentos anteriores produjo intersecciones en pecho/cuello.

La variante web actual de NEXO recupera el LOD3 real del DNA original de
CH_Nexo_MateoNative. La piel tiene 5.048 triángulos, como la de LIRA. Reutiliza
el rig y las matrices de enlace del ensamblado de NEXO: el esqueleto transitorio
del importador DNA no se instala. Se validan ejes, límites, normales y pesos.
El cuerpo, la ropa y el pelo conservan su geometría. Los cuatro pesos por
vértice siguen siendo una aproximación del rig completo.

`avatar_web.py export` obtiene primero los mapas/escena y luego ejecuta
`export_nexo_native_face.py` en un proceso sin renderizado. Solo crea geometría
transitoria y archivos de entrega; no guarda assets Unreal. Si falla esta etapa,
se conserva el modelo instalado. El instalador reconoce la geometría nativa
en `nexo-native-lod3.glb`; exportaciones históricas sin ese archivo mantienen
el refinamiento anterior. No usar esa vía histórica como aprobación de arte.
Ver [reparación y pruebas](../validation/2026-10-21-nexo-repair/README.md).

Presupuesto de admisión: 20 MiB por GLB, 100.000 triángulos, texturas estimadas
hasta 64 MiB. Dibujo limitado a 30 FPS, 1280 × 720 y DPR acotado; se prefiere
GPU de bajo consumo, sin obligar a todos los equipos a elegir la misma.

## Revisión y medición

Cada nueva exportación vuelve a `pending`. Revisar cara, ropa, cejas, cuello,
reposo durante varios ciclos y boca antes de habilitarla para llamadas.
Los campos `visual_review`, `motion_review` y `mouth_mapping` expresan revisión
técnica; no sustituyen aprobación artística del usuario. El valor histórico
`amplitude-verified` acredita el control de boca, no fonemas. No marcar como
revisado un asset solo porque el archivo sea válido.

El lector de audio usa RMS lineal y bandas espectrales para apertura, redondeo
y extensión de labios. Sustituye el FFT de 32 muestras cuyo rango saturaba la
boca; trabaja con 2048 muestras, puerta de silencio y transiciones cortas.
Analiza únicamente el audio remoto ya recibido, sin duplicar su salida ni
guardar PCM. Silencio, pista silenciada o bloqueo de reproducción vuelven al
reposo. Son formas acústicas aproximadas: no reconocimiento de fonemas ni
visemas con marcas de tiempo. La prueba manual de la vista previa verifica
deformaciones, no sincronía con voz.

Las llamadas locales comprobaron LIRA → NEXO, audio entrante/reproducción y
cero errores JavaScript con entrada sintética. Ver [LIRA](../validation/2026-10-21-lira-web/README.md)
y [NEXO](../validation/2026-10-21-nexo-web/README.md).
La [prueba posterior de los tres agentes](../validation/2026-10-21-avatar-speech-style/README.md)
comprueba LIRA → NEXO → ELIAN con las nuevas formas de boca y cierre en pausas.

La [medición conjunta](../validation/2026-10-21-avatar-resources/README.md) reemplaza
las cifras preliminares: 30 FPS, RAM privada residente media de navegador
596,6 MiB con LIRA y 555,9 MiB con NEXO. Docker se reporta aparte; WSL ya lo incluye.
La prueba usó AMD 740M integrada. No confundir tamaño GLB, heap JS, compromiso
privado, RAM residente, memoria gráfica compartida y VRAM NVIDIA.

No se certifican rendimiento móvil, arranque en frío, varias llamadas simultáneas,
sesiones prolongadas, lip sync fonético ni despliegue UAM con estos resultados.
Los bloqueos de exportación anteriores quedan en
[notas históricas](../history/AVATAR_WEB-through-20261021.md).
