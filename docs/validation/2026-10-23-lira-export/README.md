# LIRA: exportación web recuperada — 23 octubre 2026

Se completó el candidato de LIRA después de instalar MetaHuman Creator Core Data
desde Epic. El atlas original SlightArch ya existe. Se ejecutó únicamente
`export_lira_brows_web.py`, sin renderizado (`-nullrhi`), sobre la exportación
parcial guardada. Unreal terminó con código 0 y generó el atlas TGA de
12.582.930 bytes. Los originales del repositorio Avatar siguen sin cambios.

La fuente principal procede de Unreal 5.8.2 y las cejas se recuperaron con
5.8.4, instalada por el usuario al retomar. Esta combinación queda explícita
para reproducir la entrega; no se reexportó el cuerpo ni se guardaron assets.
Hashes, tamaños, versión de Avatar y manifiesto: [export-evidence.json](export-evidence.json).

## Resultado y alcance

- GLB: 4.654.876 bytes (4,44 MiB), 75.781 triángulos de geometría, 486
  articulaciones y un clip de animación. Los triángulos por frame que informa
  el renderer pueden ser distintos; no son el mismo contador.
- SHA-256: `08da9aead30163e46709fc417fb8e35275f7a73df6e037956e0cc28bac2f96b8`.
- Instalado con `--preview-only`: conserva los manifiestos canónicos y usa
  `manifest.preview.json`. El candidato sigue pendiente de aceptación; no se
  ofrece automáticamente en llamadas.
- Se revisaron cejas presentes, ropa sin duplicación visible, idle y cambios
  de forma de labios. El cabello se ve muy oscuro en la iluminación del visor;
  requiere comparación artística con Unreal y la entrega de Santiago.
- Tests de contrato, movimiento del habla y rig: 19 aprobados, 3 omitidos por
  ausencia de los GLB privados originales. Los tres candidatos generados sí
  pasan sus pruebas de boca, ojos y regreso al reposo.
- La prueba visual usa movimientos sintéticos, sin audio ni conversación.
  No certifica lip sync fonético, transferencias, UAM o concurrencia.

Vista local: `/avatar-preview?character=LIRA`. Capturas y medición completa:
`data/local-avatar/validation-20261023-lira/` (ignorado por Git).

## Medición y entrega privada

120 muestras en Chrome local, lienzo de 1280 × 720: mediana de **30 FPS**
(rango 29,14–30,25), 15 llamadas de dibujo y 76.031 triángulos por frame.
Una carga registró 96,4 ms de descarga, 82,4 ms de parseo y 1.300,6 ms hasta
el primer frame. Repetir esos valores en las muestras no constituye 120 cargas.
Texturas estimadas: 37,3 MiB; geometría: 3,4 MiB. El heap JavaScript estuvo
entre 32,8 y 38,9 MiB: **no representa RAM total ni VRAM del proceso**.
La mediana de envío de render fue 1,44 ms; no mide finalización de trabajo GPU.
Resumen reproducible: [browser-preview-summary.json](browser-preview-summary.json).

Paquete privado de los tres candidatos, con instrucciones y hashes individuales:
`data/local-avatar/delivery/viva-web-candidates-mac-20261023.zip`.
Son 11.952.389 bytes, 15 entradas; CRC y SHA-256 individuales verificados.
SHA-256 del ZIP: `f45ed1bb19c4b942bf86c9525e48895ada3a9f1eb75f65782cc8380971cb0c8a`.
El ZIP anterior del 22 se conserva como histórico. Ninguno se publica en Git.

## Reproducción

Desde la raíz de Edutech, con la exportación recuperada presente:

```sh
uv run --no-project --python 3.12 --with Pillow==12.0.0 python scripts/avatar_web.py install --path data/local-avatar/runtime/web-export/20261023-025746-lira --preview-only
```

Después de copiar un GLB nuevo a `public/avatars`, reiniciar el servidor Next
de producción que sirve esa carpeta. En esta prueba, el servidor iniciado antes
de la instalación devolvía 404 para el archivo nuevo; tras reiniciarlo devolvió
200 con los 4.654.876 bytes esperados. No fue necesario modificar el renderer.

La aceptación pendiente debe cubrir voz real, silencio, interrupción,
reconexión y cambios LIRA → NEXO → ELIAN, además de calidad del cabello y rostro.
Hasta entonces, conservar la separación entre candidatos y modelos de llamadas.
