# Correspondencia entre agente, voz y avatar web

El agente publica `avatar.character` en su participante de LiveKit. El frontend
usa esa señal para seleccionar el modelo; el nombre del worker (`nexus`) no
identifica al personaje que habla. La recepción empieza con `LiraAgent`.

| Agente | Voz configurada en su constructor | Personaje |
| --- | --- | --- |
| LiraAgent | Aoede | LIRA |
| NexusAgent | Puck | NEXO |
| ElianAgent | Kore | ELIAN, modelo original de L_Elian |

La configuración efectiva se consulta en `agent-starter-python/src/agent.py`.
Se conservan las voces, los roles, los prompts y sus transferencias. Una nota
antigua de Nexus menciona em_alex; su constructor actual usa Puck.

Se conecta `ctx.room` antes de iniciar `AgentSession`: el SDK instalado conecta
la sala y ejecuta `on_enter` en paralelo. Antes, el anuncio inicial de LIRA se
perdía porque `set_attributes` encontraba la sala sin conectar; los anuncios de
transferencias posteriores sí llegaban. El cambio solo ordena el arranque.
Prueba de regresión: `agent-starter-python/tests/test_avatar_startup.py`.

## Versión de LIRA solicitada

Usar la versión de **JuanGonzalezx**:

- Mapa fuente: `/Game/VIVA/Avatars/Lira/Maps/L_Lira`.
- Blueprint: `/Game/VIVA/Avatars/Lira/Blueprints/BP_Lira`.
- Cabello: `SM_Lira_HairCardsBone`, con `MI_Lira_HairCards`.
- Cuello: `SM_Lira_SoftCollarBone_v5`.
- Historial de referencia: `92869b3`, acabado del cabello y ropa por Juan.
- Referencia visual: Avatar/docs/validation/2026-10-12-lira/haircards/reopened-voice/.

No sustituirla por `/Game/UniversityVirtualAssistant/FamiliaVIVA/LIRA/NewMap_LIRA_Studio`,
que corresponde a la variante de Santiago. El lector del manifiesto comprueba
la ruta de procedencia de LIRA para evitar esa confusión.

La copia web conserva cara, cuerpo, uniforme, cabello y las tarjetas SlightArch
de las cejas originales. Los materiales procedurales de líneas se traducen al
shader web; las tarjetas de las cejas se ajustan a la superficie y toman los
pesos del rig facial existente. Se corrige la transparencia EyeShell que glTF
exporta como negro opaco. No se guarda ninguna modificación en los assets de Juan.
Los motores de iluminación son diferentes: no se promete igualdad píxel a píxel.

El cabello deriva de Ellie Hair de Vivek Kumar. Conservar la atribución y las
condiciones recogidas en `Avatar/THIRD_PARTY.md`; esta integración es local.

## Selección y recursos

`/api/token` devuelve los metadatos de los modelos disponibles, sin cargar todos
los GLB. El visor monta únicamente el modelo del agente activo y libera sus
recursos al cambiar. La ausencia de señal o de modelo nunca selecciona NEXO
por defecto. ELIAN conserva Kore y su escena original, con cabello, gafas,
uniforme; el usuario solicitó compartir el fondo UAM con LIRA y NEXO.
ATLAS/NOVA/NOA no tienen agentes implementados;
no asignarles una voz o un rol de otro personaje solo porque exista su asset.

El optimizador y el visor mantienen el presupuesto por modelo de 20 MiB,
100.000 triángulos y 30 FPS. No equivale a memoria máxima de navegador o Docker.
Las revisiones del manifiesto habilitan una entrega solo después de verificar
su apariencia, animación y control de boca. El movimiento por RMS y bandas
espectrales no es sincronización fonética. La exportación no guarda assets de
autoría de Unreal. LIRA usa ahora el mismo fondo Uam-virtual de NEXO.

Vista individual: `/avatar-preview?character=LIRA`, `?character=NEXO` o `?character=ELIAN`.
Para conversar: elegir Avatar e iniciar la llamada. Lira recibe; el avatar
cambia cuando ella transfiere la conversación al especialista.
