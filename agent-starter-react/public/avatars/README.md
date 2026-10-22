# Modelos web de Familia VIVA

Git conserva los manifiestos revisados de **LIRA de Juan**, **NEXO** y **ELIAN**. Los GLB
y fondos son una entrega privada del equipo, excluida de Git junto con las
exportaciones anteriores. No se necesita Unreal para usar la entrega ya exportada.

## Instalar la entrega

1. Obtener `viva-web-avatars-20261021-nexo-repair.zip` y su archivo SHA-256 por el canal privado
   del equipo. No contiene claves, datos de sesiones ni archivos de Unreal.
2. Comprobar el SHA-256 del ZIP con `Get-FileHash` en Windows o `sha256sum` en Linux.
3. Descomprimirlo en una carpeta temporal. Verificar `checksums.json` y leer
   `THIRD_PARTY_AVATARS.md`. Copiar el contenido de `avatars/` a esta carpeta:
   conservar una copia de modelos locales distintos antes de reemplazarlos.
4. Desde la raíz del repositorio: `python scripts/voice_demo.py web`.
5. Abrir `/avatar-preview?character=LIRA`, `?character=NEXO` y `?character=ELIAN`.
   Luego probar Avatar en una llamada: LIRA recibe y el modelo sigue al especialista.

El paquete vigente incluye el rostro LOD3 nativo de NEXO con su rig original y
el fondo UAM de los tres personajes. `viva-web-avatars-20261021.zip`,
`viva-web-avatars-20261021-three-agents.zip` y
`viva-web-avatars-20261021-visual-update.zip` son entregas anteriores.
Los materiales y la boca requieren también el código del visor actualizado;
instalar únicamente los GLB sobre un frontend anterior no incorpora esos cambios.

Cada carpeta debe tener `manifest.json`, `<personaje>-<sha256>.glb` y
`uam-background.jpg`. El SHA del nombre corresponde al contenido del GLB;
los bytes y la procedencia deben coincidir con el manifiesto de esa entrega.
No basta con cambiar el nombre de un archivo para instalar otra versión.

Si falta un modelo o está pendiente de revisión, no se anuncia para llamadas;
la presentación de voz sigue disponible. Los tests del visor usan fixtures y
no requieren distribuir estos assets en CI.

[Procedencia y condiciones](../../../THIRD_PARTY_AVATARS.md),
[guía de exportación](../../../docs/mvp/AVATAR_WEB.md) y
[medición de consumo](../../../docs/validation/2026-10-21-avatar-resources/README.md).
