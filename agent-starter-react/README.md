# Frontend Edutech

Aplicación Next.js 15 / React 19 basada en LiveKit Agents UI. Integra conversación,
transcripción, presentación de voz, avatares WebGL y panel privado de telemetría.

## Ejecutar

La opción reproducible con todos los servicios está en el [README principal](../README.md).
Para desarrollar solo la web se necesita Node.js 24 y la configuración local de
LiveKit/telemetría. Desde esta carpeta:

```sh
npm ci --legacy-peer-deps
npm run dev -- --port 3501
```

Usar 3501 cuando Docker ya sirve 3000/3500. Copiar `.env.example` a `.env.local`
y completar la conexión del entorno autorizado. El worker vigente se despacha
como `AGENT_NAME=nexus`; eso no sustituye el personaje inicial LIRA.
El panel y su autenticación necesitan también la configuración descrita en
[telemetría](../docs/mvp/TELEMETRY_IMPLEMENTACION.md). No copiar secretos al código.
El lock de npm es el utilizado por Docker y CI; no regenerar otro lock para esta entrega.

## Avatares

Instalar los [modelos privados del equipo](public/avatars/README.md) antes de
construir la imagen que deba incluirlos. `/avatar-preview` permite revisarlos
sin una llamada. La selección en conversación sigue `avatar.character`:

| Agente | Modelo | Voz |
|---|---|---|
| LiraAgent | LIRA de Juan | Aoede |
| NexusAgent | NEXO | Puck |
| ElianAgent | ELIAN original | Kore |

El visor carga solo el personaje activo, libera sus recursos al cambiar y limita
el dibujo a 30 FPS y 1280 × 720. No necesita Unreal ni streaming de video.
Una revisión técnica del manifiesto permite ofrecer el modelo; sin modelo válido
se conserva la voz. El movimiento usa RMS y bandas espectrales para apertura,
redondeo y extensión de labios; no reconoce fonemas. LIRA comparte el fondo de
NEXO y ELIAN. NEXO usa el rostro LOD3 del DNA original, con su rig y mapas propios.
Los shaders web reproducen los detalles
procedurales guardados, sin modificar los assets de autoría.

## Rutas y módulos

| Ruta | Función |
|---|---|
| `app/api/token/` | Emisión de token y metadatos de avatares disponibles |
| `app/api/avatar/` | Catálogo de modelos web |
| `app/avatar-preview/` | Inspección de modelo y métricas |
| `components/avatar/` | Renderer, materiales, rig y presupuesto gráfico |
| `lib/browser-avatar*.ts` | Contrato y lectura de manifiestos locales |
| `lib/session-start.ts`, `hooks/useAgentErrors.tsx` | Espera de conexión, cancelación y reintento tras error |
| `hooks/useAvatarStream.tsx` | Estado de presentación y agente activo |
| `app/admin/`, `lib/telemetry/` | Panel, autenticación e instrumentación |

`/api/avatar/frame` conserva el contrato del renderer nativo histórico; no es
la fuente del avatar WebGL. No activar el bridge para probar este visor.

## Comprobar antes de entregar

```sh
npm test
npx tsc --noEmit
npm run lint
npm run build
```

Los tests usan datos sintéticos, sin llamadas a Gemini. Las tres comprobaciones
adicionales de los rigs instalados se omiten explícitamente cuando faltan los GLB
privados; las pruebas sintéticas del rig siguen ejecutándose en CI.
El build comprueba el
código, no la calidad artística ni una conversación real. [Evidencia local](../docs/validation/2026-10-21-lira-web/README.md)
y [mediciones de recursos](../docs/validation/2026-10-21-avatar-resources/README.md).

La conexión admite hasta 90 s para la llegada de un worker que se prepara en frío;
el intento completo se limita a 95 s. Un fallo libera la espera y permite iniciar
otra llamada. La [prueba de recuperación](../docs/validation/2026-10-21-lira-startup/README.md)
incluye desconexión, agente tardío y dos llamadas con LIRA. Una caída del proveedor
sigue necesitando una conexión disponible para volver a conversar.

Se conserva la atribución del starter LiveKit y sus licencias en el repositorio.
