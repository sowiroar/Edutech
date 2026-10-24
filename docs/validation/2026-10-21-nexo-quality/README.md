# NEXO: acabado comparable a LIRA; fondo compartido de ELIAN

Validación local del 21 de octubre de 2026 (America/Bogota).

**Antecedente, sustituido:** el usuario rechazó esta apariencia. La aprobación
técnica registrada aquí no fue una aprobación artística. La versión vigente
usa geometría facial nativa; ver [reparación posterior](../2026-10-21-nexo-repair/README.md).

## Cambios

- NEXO conserva el cuerpo masculino, la ropa, el rostro y el rig de Mateo. Se
  recupera el color original aprobado y se incorpora el mapa normal nativo de
  la piel. No se usa el albedo nativo que oscurecía demasiado los ojos.
- Una subdivisión de la superficie facial guiada por normales suaviza la
  silueta. Conserva los vértices originales y los bordes, e interpola UV, pesos
  y deformaciones. Es un refinamiento del modelo web, no un LOD nativo superior
  ni una recuperación de detalle anatómico perdido. La piel pasa de 1.104 a
  4.416 triángulos; la de LIRA tiene 5.048.
- Se suavizan los bordes del pelo, se reduce su brillo y se acerca el encuadre
  a la distancia de LIRA. El torso y la geometría de la ropa no se modifican.
- ELIAN comparte la imagen UAM de NEXO y LIRA. Su manifiesto deja de sustituirla
  por el fondo sólido. El exportador conserva esta decisión al regenerarlo.
- La exportación aplica materiales temporalmente: no guarda cambios en los
  assets del proyecto Unreal. LIRA no se modifica.

## Modelo instalado

| Dato de NEXO | Antes | Ahora |
| --- | ---: | ---: |
| Tamaño GLB | 5.46 MiB | 5.68 MiB |
| Triángulos totales | 59.578 | 64.150 |
| Joints | 235 | 235 |
| Animaciones | 1 | 1 |

SHA-256 del NEXO vigente:
`1a0fd3da7161f6a6f62131b3bd14d830dc3e647c2f7cb8886c6558882d98ac26`.

Exportación privada de origen: `D:\EdutechRuntime\web-export\20261022-010757`.
Incluye el GLB principal y el horneado de color sobre las mismas posiciones y
UV del rostro; el optimizador comprueba esa coincidencia antes de combinarlos.
El límite de cuatro influencias por vértice del perfil web sigue siendo una
aproximación del rig, como en la versión anterior.

## Comprobaciones

- 26 pruebas Python: 25 aprobadas y una omitida por ser exclusiva de Linux.
- TypeScript sin errores, lint aprobado y siete pruebas de rig/presupuesto
  gráfico aprobadas con los tres modelos instalados.
- Las pruebas nuevas verifican conservación de vértices y bordes, interpolación
  de UV/deformaciones/pesos, orientación de triángulos y curvatura interior.
- NEXO y ELIAN revisados en reposo y con apertura, redondeo y extensión de boca.
  Ambos regresan a boca cerrada al detener la prueba; sin errores del navegador.
- La web reconstruida en `http://localhost:3000` entrega el hash de NEXO indicado
  y la URL del fondo UAM para los tres avatares. Los servicios de voz permanecen
  activos. No se utiliza el micrófono en esta prueba de presentación.

Las muestras del navegador están en [preview-summary.json](preview-summary.json).
Las capturas locales están en
`data/local-avatar/nexo-lira-quality-20261021/`, excluidas de Git.
Son muestras de un solo avatar visible a 960×540 con límite de 30 FPS, no una
prueba de concurrencia. Las estimaciones de texturas/geometría no equivalen a
VRAM total medida. No se ha repetido aquí el benchmark completo de RAM/VRAM
ni la llamada de transferencia entre agentes, porque no cambió su integración.

La revisión técnica está completa; la aprobación artística corresponde al
usuario. La representación web no garantiza equivalencia píxel a píxel con
Unreal ni sincronización fonética exacta.

## Entrega privada actualizada

`data/local-avatar/publication-20261021/viva-web-avatars-20261021-visual-update.zip`
contiene los tres modelos, manifiestos, fondos y sus instrucciones/checksums.
Tamaño: 12.005.927 bytes (11.45 MiB). SHA-256:
`32fa7aa6ef50444afc11d88de539217e5aafe9bd0fb440b56908b23c39edd57a`.

Se verificaron las entradas del ZIP y sus checksums. Sustituye al paquete
`three-agents` para esta apariencia. Ningún GLB o ZIP se agrega al repositorio.
