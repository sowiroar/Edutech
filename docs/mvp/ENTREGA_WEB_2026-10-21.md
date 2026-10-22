# Entrega web preparada — 21 de octubre de 2026

## Cambio para el equipo

El frontend ofrece LIRA de Juan, NEXO y ELIAN sin mantener Unreal abierto. La llamada
empieza con LIRA/Aoede y cambia a NEXO/Puck cuando el agente transfiere a Nexus.
La falta de modelo conserva la voz. ELIAN/Kore usa el avatar de su escena original.
El primer anuncio de personaje se publica después de conectar la sala, evitando
que la recepción muestre otro avatar o quede esperando por una carrera de arranque.

El perfil local conserva LiveKit/Gemini, RAG/Mem0 y telemetría. Frontend en 3000 y
3500, misma aplicación. Se mantienen los contratos nativos de bridge/frames como
antecedentes separados; no se activan para el recorrido WebGL.

## Contenido de la entrega

- Visor y selector, presupuesto gráfico, materiales, rig web y carga por agente.
- Exportación de NEXO, LIRA y ELIAN desde Unreal con validación y revisión por manifiesto.
- Materiales de NEXO restaurados, encuadre cercano y fondo UAM compartido con LIRA.
- Rostro nativo LOD3 de NEXO, con su rig original y sus mapas; ELIAN también usa
  UAM. La evidencia vigente está en 2026-10-21-nexo-repair; arte pendiente de aceptación.
- El saludo no reintenta sobre una sesión de voz que está transfiriendo o cerrando.
  NEXO aclara consultas ambiguas antes de transferir a ELIAN.
- Boca por RMS y bandas espectrales: apertura, redondeo y extensión, sin afirmar
  reconocimiento de fonemas. Ojos y dientes de ELIAN horneados sobre su propia malla.
- Correcciones de arranque/construcción local y comprobaciones de origen.
- Cancelación de intentos de conexión interrumpidos: el botón vuelve a estar
  disponible y permite reintentar; espera acotada para un agente que se prepara en frío.
- Piel mate de NEXO y reducción del razonamiento interno de la síntesis documental
  a 512 tokens. Se conservan Gemini 2.5 Flash, fuentes, voces y longitud de respuesta.
- README principal, frontend, agente e índice técnico actualizados; AGENTS como
  fuente de continuidad y CLAUDE como referencia a ella.
- Evidencia de voz/cambio de avatar y medición separada de RAM, CPU y GPU.
- Manifiestos de modelos y procedencia. GLB/fondos excluidos de Git y entregados
  en un paquete privado verificado para los colaboradores autorizados.
- Base generada data/knowledge.db retirada del índice; archivo local conservado.

Los 11 GLB descartados se respaldaron en
data/local-avatar/publication-20261021/retired-models, fuera de Git y de public/.
Se retiraron 103,18 MiB de la carpeta pública, sin borrar versiones de trabajo.
Un build posterior deja de incluir esos modelos antiguos; una imagen Docker
ya construida no cambia retroactivamente.

La limpieza final apartó otras siete variantes de NEXO/ELIAN en
data/local-avatar/publication-20261021/retired-models-cleanup (35,00 MiB), con
verificación SHA-256. Queda únicamente el GLB del manifiesto vigente de cada
personaje dentro de public/avatars; los descartados permanecen recuperables.

## Entrega de modelos dentro del equipo

Paquete vigente: data/local-avatar/publication-20261021/viva-web-avatars-20261021-nexo-repair.zip
(11,44 MiB), con nueve archivos de runtime, atribución, instalación y checksums.
Incluye NEXO con rostro LOD3 original y los tres fondos UAM. Los paquetes
visual-update y three-agents se conservan como antecedentes; no son la versión vigente.
El ZIP anterior de 7,67 MiB se conserva como antecedente de dos avatares.
Se conserva el SHA-256 en el archivo .zip.sha256 contiguo. No subir ese ZIP a una
release pública. [Instalación](../../agent-starter-react/public/avatars/README.md)
y [procedencia](../../THIRD_PARTY_AVATARS.md).

Un clon de código por sí solo arranca en voz. Para revisar avatares, instalar
el paquete privado antes de construir la web, o reexportar desde el proyecto
Unreal autorizado. No se requieren texturas/Content completos en este repo.

## Rama y publicación

Rama local de entrega: feature/avatar-web-delivery, creada conservando todos los
cambios de fix/local-frontend-startup-20261018. Base local: 90e05a0. Destino: main.
No se ha hecho commit, push, PR, merge ni despliegue UAM durante esta preparación.
La base remota, la autenticación de Git y CI deben comprobarse al publicar;
esta limpieza no sincroniza cambios remotos.

Revisar diff e índice (incluida la retirada de knowledge.db), registrar el cambio,
publicar la feature y abrir PR a main según [FLUJO.md](FLUJO.md). No usar git add -f
para incluir modelos, .env o datos excluidos. Los commits deben incluir todos los
archivos de código y tests nuevos necesarios; no solo los README.

Desde PowerShell, para revisar lo que se publicará:

```powershell
Set-Location 'C:\Users\santi\Edutech\Edutech'
$env:EDUTECH_SKIP_DEPLOY='1'
git branch --show-current
git status --short
git diff --check
git diff --stat
git diff --cached --stat
```

La rama debe ser `feature/avatar-web-delivery`. Cuando estés conforme, prepara
el commit desde esta raíz; el archivo `.gitignore` excluye los recursos privados:

```powershell
git add -A
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
```

Comprueba la lista antes de continuar: no debe incluir `.env`, GLB, fondos,
exportaciones, bases o registros locales. La eliminación de `data/knowledge.db`
del índice es intencional; su copia local se conserva. Después:

```powershell
git commit -m "feat: integrate web avatars and improve voice session recovery"
git push -u origin feature/avatar-web-delivery
```

Abre un PR hacia `main` y revisa CI. Si el remoto rechaza el push, revisa la
divergencia; no uses `--force`. Estos comandos son pasos para el responsable de
publicar, no acciones ejecutadas durante la limpieza.

## Descripción propuesta del PR

Título: **Integrar avatares web y corregir el arranque y las transferencias de voz**

La presentación Avatar dibuja en WebGL el personaje del agente activo: LIRA de
Juan al recibir, NEXO al transferir a Nexus y ELIAN al transferir a Elian. Conserva la voz cuando el modelo
no está disponible y libera los recursos del avatar anterior. Se corrige el
orden de conexión de la sala para conservar el anuncio inicial de LIRA. La boca
usa amplitud lineal y bandas espectrales con cierre en pausas; se recuperan
los materiales de NEXO y se comparte su fondo con LIRA y ELIAN. NEXO recupera
el LOD3 de su DNA original, manteniendo el rig del ensamblado y su torso. El
reintento del saludo distingue silencio de transferencia/cierre y no reutiliza
una sesión de voz inactiva. Las consultas ambiguas se aclaran antes de derivar.
Una desconexión durante el arranque cancela la espera y permite reintentar sin
recargar. Se admite la preparación en frío del agente con tiempos acotados.
NEXO usa piel mate; la síntesis documental limita su razonamiento interno y
prepara el índice fuera del bucle de audio, conservando fuentes y voces.

Incluye exportación validada, presupuesto gráfico, manifiestos, documentación
de instalación privada y mediciones locales. En el benchmark anterior a la
revisión facial, a 960x540 ambos modelos mantuvieron
30 FPS; la RAM privada residente media del navegador fue 597/556 MiB para
LIRA/NEXO. Los resultados son de una llamada por vez, no pruebas de concurrencia.

La entrega no incluye GLB/fondos en Git, credenciales ni datos generados. No
certifica aceptación artística, sincronía fonética, Moodle/SSO o despliegue UAM.
Las verificaciones finales están en
[validación de publicación](../validation/2026-10-21-publication/README.md).
La ampliación posterior y su llamada LIRA → NEXO → ELIAN están en
[verificación de labios y materiales](../validation/2026-10-21-avatar-speech-style/README.md).
La reparación vigente de NEXO está en
[voz y rostro nativo](../validation/2026-10-21-nexo-repair/README.md).
Las verificaciones más recientes están en
[latencia y piel de NEXO](../validation/2026-10-21-nexo-latency/README.md) y
[recuperación del arranque de LIRA](../validation/2026-10-21-lira-startup/README.md).
