# Conservar y sincronizar el trabajo de Jacobo en UAM

12 octubre 2026. Jacobo reporta cambios de frontend guardados en el servidor
que todavía no están en GitHub. También reporta imagen del avatar en el
frontend a unos 2 fps. No se ha inspeccionado ese checkout ni medido la causa.

La base compartida para continuar agentes/frontend es
**`feature/gemini-live-api+MVP`**. Nuestro cambio actual solo incorpora la revisión
de Avatar mediante el submódulo y documentación. El repositorio antiguo
`feature/avatar-bridge` se conserva como histórico y banco de pruebas WAV.

## Antes de actualizar el servidor

FortiClient da acceso a la red UAM. El cliente de escritorio remoto permite
operar Windows dentro de esa red. Las credenciales de cada conexión son
separadas y permanecen fuera de Git. No es necesario copiar ninguna al chat.

En una terminal del checkout real de Edutech en Windows:

```powershell
$env:EDUTECH_SKIP_DEPLOY = '1'
git status --short --branch
git branch --show-current
git diff --stat
git submodule status
```

Primero identificar el repositorio, la rama y los cambios. Si no es un checkout
Git, hacer una copia preservada del proyecto y compararla con un clon separado;
no ejecutar los comandos siguientes a ciegas. El hook opcional de despliegue no
debe reiniciar servicios mientras se conserva el trabajo.

Si hay cambios sin commit, crear una rama desde **el estado actual del servidor**:

```powershell
git switch -c feature/uam-frontend-20261012
```

Añadir explícitamente las rutas revisadas. No usar `git add .` con archivos de
configuración locales, claves, grabaciones o cachés. Revisar el diff preparado,
crear un commit y publicarlo antes de integrar cambios de otro equipo:

```powershell
# Sustituir RUTAS_REVISADAS por archivos concretos; no es un nombre literal.
git add RUTAS_REVISADAS
git diff --cached --stat
git diff --cached
git commit -m "Preserva frontend y render del servidor UAM"
git push -u origin feature/uam-frontend-20261012
```

Si `Avatar` también tiene cambios locales, preservarlos en una rama/commit de
su propio repositorio, publicar LFS y ese commit primero. El repo padre solo
guarda un SHA; no incorpora automáticamente archivos sueltos del submódulo.

## Integración posterior

Con el trabajo ya publicado y el checkout limpio:

```powershell
git fetch origin
git merge origin/feature/gemini-live-api+MVP
```

Resolver conflictos por archivo, ejecutar las pruebas correspondientes y abrir
PR desde la rama del servidor hacia `feature/gemini-live-api+MVP`. Preferir
resolver/revisar en un checkout separado si el servidor está en uso. No usar
reset hard, clean, submodule update --force ni elegir ours/theirs globalmente.
Conservar el commit anterior para poder volver a una combinación conocida.

Solo después del merge y la coordinación con el operador se actualiza el
checkout de ejecución y se reconstruye el paquete Unreal de la plataforma
final. Registrar SHA Edutech, SHA Avatar y SHA del paquete desplegado. Un gitlink
nuevo no actualiza por sí solo un ejecutable guardado fuera de Git.

## Rendimiento pendiente

Para los 2 fps hay que medir por separado: render Unreal, frecuencia de captura,
codificación FFmpeg/MJPEG, transporte por VPN y recepción/pintado del navegador.
Registrar resolución, limitadores de fps, CPU, GPU/VRAM y el comando real de
captura. No atribuirlo a NVIDIA, RAM o frontend sin revisar la implementación
que está actualmente en el servidor.

## CI de la base al preparar el pin de Avatar

El run 38310420398 falló en Ruff del agente: importaciones sin uso, `Any` no
importado, tareas asyncio sin referencia y estilo de dos módulos RAG. Son
fallos preexistentes en `f1ccd3c`; estos archivos son idénticos en el PR del pin.
Frontend y knowledge-sync pasaron; Docker se omitió por dependencia del job
fallido. No se desactivaron checks ni se modificaron prompts/backend para
ocultar ese resultado. Corregirlo junto con la versión que Jacobo publique,
porque cambiar esos archivos ahora aumentaría los conflictos del servidor.

Esta excepción documenta la integración de un pin de assets sin cambios al
agente; **no acredita un CI global verde ni una versión desplegable**.
