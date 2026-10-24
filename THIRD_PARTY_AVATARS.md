# Procedencia de los avatares web

Los modelos son derivados del proyecto privado Familia VIVA. El código del visor
no convierte las mallas, texturas o imágenes en recursos de libre redistribución.
NEXO proviene de su base MetaHuman; LIRA conserva los assets de Juan, incluido
el cabello adaptado de Ellie Hair. ELIAN mantiene su variante de esos recursos,
como se documenta más abajo. Los fondos pertenecen al material de trabajo
aportado para el proyecto. Conservar las condiciones de sus fuentes.

La entrega GLB se comparte dentro del equipo autorizado y se mantiene fuera de
Git. No adjuntarla a una release pública o publicar una biblioteca de assets
sin revisar las condiciones correspondientes. Esto conserva la restricción ya
documentada en Avatar/THIRD_PARTY.md; no es una licencia nueva.

A continuación se conserva la ficha de procedencia del repositorio Avatar,
revisada allí el 12 de octubre de 2026. No se afirma una revisión legal nueva.

# Recursos de terceros

## Ellie Hair — Vivek Kumar (revisión 12 octubre 2026)

Cabello usado como candidata de Lira. Es el recurso de la segunda referencia
que compartió el usuario. No se atribuye su autoría al equipo VIVAVerse.

- Autor y ficha: https://www.artstation.com/marketplace/p/ovWPa/free-real-time-hair-asset-unreal-engine-game-ready-ellie-hair
- Publicación del autor: https://forums.unrealengine.com/t/free-real-time-hair-asset-unreal-engine-game-ready-ellie-hair/2345056
- Se descargó el proyecto Unreal desde el enlace Dropbox que publica el autor.
- Archivo original `RealTimeHair_UEProject.zip`, SHA-256:
  `ddf5547263a4c9c6b9399a3fb79f7b30a80d5ec689c79a0dbed0f117cc3f16e2`.
- Archivo completo conservado localmente en `Saved/ThirdPartyReview/EllieHair/`;
  no se incluye en Git. No se importaron sus plugins, scripts, Config,
  StarterContent, mapas ni compilaciones.

La ficha permite proyectos personales y comerciales, y muestra **Standard Use
License** con límite de un proyecto comercial, 2.000 ventas o 20.000 vistas.
No es una licencia de dominio público ni autorización para redistribuir el
recurso como producto independiente. Conservar la atribución y revisar el
alcance de la licencia antes de ampliar la distribución institucional/pública.
Este repositorio de colaboración es privado; no publicar estos assets sueltos.

Los paquetes necesarios mantienen `/Game/HAIR` para conservar sus referencias.
La malla adaptada y el material de Lira viven en `/Game/VIVA/Avatars/Lira`:
`SM_Lira_HairCardsBone` y `MI_Lira_HairCards`. Se ajustaron tamaño/encaje a
Face/head, color, rugosidad y brillo; texturas con máximo 1K–2K y streaming.
El original sigue disponible para reproducir la adaptación. Las texturas
conservan su fuente 4K de edición; el límite de render/cooking no significa
que el archivo del repositorio mida lo mismo que su recurso en GPU.

## Reutilización en Elian — 12 octubre 2026

La candidata `elian-design` reutiliza las mismas texturas de Ellie en este
proyecto privado. `SM_Elian_HairCardsBone`, `MI_Elian_HairCards` y
`M_Elian_SilverHair` son copias propias bajo `/Game/VIVA/Avatars/Elian`.
El material gris usa Default Lit sobre cards, sin simulación. No modifica las
mallas/materiales de Lira ni el recurso vendor. Se conserva la misma atribución
y las condiciones descritas arriba; no constituye un recurso original del equipo.

## Adaptación para Noa — 12 octubre 2026

`SM_Noa_LooseBobCards` deriva de Ellie a través de la copia ajustada de Elian.
Se retiraron 67 cards del recogido y se reformaron los mechones laterales y la
coronilla para un corte corto suelto: 20.566 triángulos, material castaño propio.
Reutiliza las texturas vendor existentes, sin Groom ni simulación; conserva
la atribución y condiciones anteriores. No se distribuye como recurso autónomo.
Las pruebas de cabello procedimental/Epic se descartaron y no están en la escena.
