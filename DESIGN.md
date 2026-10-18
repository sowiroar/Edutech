---
name: VIVAVerse — voz y operación
description: Sistema compartido conservado y superficie administrativa clara de alcance local.
colors:
  background: "oklch(1 0 0)"
  foreground: "oklch(0.145 0 0)"
  muted: "oklch(0.97 0 0)"
  muted-foreground: "oklch(0.556 0 0)"
  border: "oklch(0.922 0 0)"
  destructive: "oklch(0.577 0.245 27.325)"
  primary: "#002cf2"
  dark-background: "oklch(0.145 0 0)"
  dark-foreground: "oklch(0.985 0 0)"
  dark-muted: "oklch(0.269 0 0)"
  dark-muted-foreground: "oklch(0.708 0 0)"
  dark-border: "oklch(1 0 0 / 10%)"
  dark-destructive: "oklch(0.704 0.191 22.216)"
  dark-primary: "#1fd5f9"
  admin-canvas: "#f6f8fb"
  admin-surface: "#fff"
  admin-ink: "#1b2b43"
  admin-muted: "#eef3f9"
  admin-secondary-text: "#5e6e84"
  admin-border: "#dfe6ef"
  admin-error-border: "#ba3545"
  admin-accent: "#245fd3"
  admin-accent-hover: "#1a4dab"
  admin-selected-text: "#174798"
  admin-selected-surface: "#e4edff"
  admin-error-surface: "#fff0f1"
  admin-error-text: "#962337"
  admin-table-heading: "#475b77"
  admin-row-hover: "#f8faff"
  admin-status-text: "#52647e"
  admin-active-text: "#246647"
  admin-active-surface: "#e7f3ed"
typography:
  headline:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.8rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
  metric:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.8rem"
    fontWeight: 600
  caption:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8rem"
  detail:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
  code:
    fontFamily: "CommitMono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
rounded:
  status: "4px"
  code: "6px"
  control: "8px"
  surface: "12px"
spacing:
  tight: "4px"
  small: "8px"
  compact: "12px"
  standard: "16px"
  content: "20px"
  group: "24px"
  spacious: "32px"
  wide: "48px"
components:
  admin-button-default:
    backgroundColor: "{colors.admin-surface}"
    textColor: "{colors.admin-ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  admin-button-default-hover:
    backgroundColor: "{colors.admin-muted}"
  admin-button-primary:
    backgroundColor: "{colors.admin-accent}"
    textColor: "{colors.admin-surface}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  admin-button-primary-hover:
    backgroundColor: "{colors.admin-accent-hover}"
  admin-button-selected:
    backgroundColor: "{colors.admin-selected-surface}"
    textColor: "{colors.admin-selected-text}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  admin-input:
    backgroundColor: "{colors.admin-surface}"
    textColor: "{colors.admin-ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  admin-panel:
    backgroundColor: "{colors.admin-surface}"
    textColor: "{colors.admin-ink}"
    rounded: "{rounded.surface}"
    padding: "24px"
  admin-table-heading:
    backgroundColor: "{colors.admin-muted}"
    textColor: "{colors.admin-table-heading}"
    padding: "14px"
  admin-status:
    backgroundColor: "{colors.admin-muted}"
    textColor: "{colors.admin-status-text}"
    rounded: "{rounded.status}"
    padding: "4px 8px"
  admin-status-active:
    backgroundColor: "{colors.admin-active-surface}"
    textColor: "{colors.admin-active-text}"
    rounded: "{rounded.status}"
    padding: "4px 8px"
---

# Design System: VIVAVerse

## Overview

**Creative North Star: "Operación clara, continuidad de voz"**

La superficie administrativa tiene una paleta clara propia, inspirada en la referencia NeoIPS autorizada: lienzo gris azulado, paneles blancos, texto azul oscuro y acento azul funcional. Public Sans mantiene la continuidad tipográfica; tablas, divisores y cifras tabulares organizan la lectura operativa.

El alcance del cambio es `/admin`. La pantalla de voz conserva su sistema semántico claro/oscuro y su composición previa. Los tokens sin prefijo y `dark-*` preservan la paleta compartida de `styles/globals.css`; `admin-*`, la jerarquía tipográfica y los patrones operativos de este documento describen exclusivamente el panel. No sustituyen la identidad ni los componentes de voz.

**Key Characteristics:**

- Paleta clara fija solo en /admin.
- Paneles blancos planos y tablas con encabezado tonal.
- Cifras tabulares, unidades y cobertura visibles.
- Detalle inline y controles con foco visible.

Registro fusionado desde el código terminado: `agent-starter-react/styles/globals.css`,
`app/layout.tsx`, `app/admin/telemetry.css`, `app/admin/page.tsx` y
`app/admin/session-detail.tsx` (rutas `app/` relativas al frontend).
Evidencia de revisión: `.impeccable/review/desktop.png`, `mobile.png`,
`detail-desktop.png`, `detail-mobile.png` y `actions-desktop.png`; revisión final: ship.
La dirección y el brief de esta superficie permanecen en `PRODUCT.md`.

## Colors

La paleta administrativa combina blancos y neutros azulados con acento funcional.
El frontmatter conserva los valores canónicos; no hay variante oscura del panel.

### Primary

`admin-accent` identifica acciones principales, enlaces, borde seleccionado y foco.
`admin-accent-hover` oscurece las acciones al pasar el puntero; la selección combina
`admin-selected-surface` y `admin-selected-text` con un borde de acento.
`primary` y `dark-primary` siguen perteneciendo exclusivamente al sistema compartido.

### Neutral

`admin-canvas` es el lienzo; `admin-surface`, los paneles y controles.
`admin-ink` identifica contenido principal; `admin-secondary-text`, explicación y
metadatos; `admin-muted`, encabezados, estados neutrales y pie de salud;
`admin-border`, separaciones; `admin-table-heading`, los títulos de columna.
`admin-row-hover` facilita seguir una fila. Los estados activos combinan
`admin-active-text` y `admin-active-surface`; los errores usan la familia `admin-error-*`
con un mensaje explícito. Los colores compartidos y `dark-*` se conservan sin cambio.
Las rampas del sidecar son muestras sintetizadas de vista previa, no tokens adicionales.

**The Surface Scope Rule.** El panel resuelve localmente sus colores semánticos; la pantalla de voz conserva las variables y el tema compartidos.

## Typography

**Display / Body Font:** Public Sans con respaldo sans-serif del sistema.
**Label/Mono Font:** etiquetas en Public Sans; identificadores y JSON en CommitMono.

La escala del frontmatter describe el panel: headline para la cabecera, title para
secciones, body para párrafos, label para campos y filas, metric para el resumen,
caption para metadatos y encabezados de tabla, detail para notas de celdas y JSON.
El título de cabecera conserva su tamaño en móvil por la regla específica vigente.
Los párrafos tienen el interlineado body y un ancho máximo de 75ch, excepto captions.
Los importes de sección y cifras de calidad usan 1.25rem, con pesos 550 y 600,
respectivamente. Las tablas usan label y encabezados de peso 600.
Toda la superficie administrativa activa cifras tabulares.

**The Measured Number Rule.** Tamaño y alineación ayudan a comparar cifras; la unidad, el denominador y la ausencia de dato permanecen visibles junto a ellas.

## Layout

El contenedor administrativo tiene ancho máximo de 1440px, margen automático y
padding de 48px 32px 64px. La cabecera alinea título y navegación. Los paneles
usan separación y padding de 24px; el área de filtros usa 20px. El resumen es una
rejilla abierta de cinco columnas con separadores verticales, sin panel envolvente.
La navegación por anclas permite saltar entre secciones de la página.

A 700px o menos, el contenedor usa padding de 24px 16px y los paneles, filtros y
pie usan 16px. Cabecera y encabezados se apilan; filtros y resumen usan dos columnas,
con cada fecha ocupando ambas columnas. Las tablas mantienen 610px de ancho mínimo
solo dentro de su región desplazable. El aviso de desplazamiento permanece visible.
El detalle de sesión se inserta después de los filtros y antes de la navegación;
su línea de tiempo pasa de una columna horaria de 80px y contenido flexible a una
sola columna en móvil. El acceso tiene ancho máximo de 460px y padding de 32px.
El chrome fijo compartido se oculta únicamente mientras está presente /admin.

## Elevation & Depth

El panel no usa sombras: la separación del lienzo se consigue con superficie blanca
y borde fino. El foco usa contorno azul de 2px y separación de 3px. Esta regla de
profundidad pertenece al panel y no cambia los componentes compartidos de voz.
No se añaden transiciones de estado en el CSS administrativo. Las anclas heredan
el desplazamiento suave del layout compartido; el detalle solicita scroll y foco
al abrirse. No se extrae una duración o curva nueva de esa conducta nativa.

**The Flat Panel Rule.** Bordes y cambios de superficie separan los grupos del panel sin sombras.

## Shapes

Paneles, filtros, acceso y pie usan la escala surface; tablas y controles, control;
estados, status; bloques de JSON del detalle, code. Los bordes son de 1px.
Botones tienen altura mínima de 44px; inputs y selects, de 42px, y pueden crecer
con su contenido. Los estados son etiquetas compactas, no botones.

## Components

### Buttons

Acciones legibles de peso 550. El control normal usa blanco y texto principal,
con hover muted. Filtros y acceso usan azul y blanco; el acceso conserva además
opacidad 0.85 en hover. La vista pulsada y la sesión expandida usan superficie azul
clara, borde azul y texto oscuro con `aria-pressed` o `aria-expanded`.
Disabled usa opacidad 0.55 y cursor de espera. Todos conservan foco visible.

### Inputs / Fields

Campos nativos blancos, con borde, esquinas de control y etiquetas persistentes.
Las fechas conservan el selector nativo de tema claro. Error se presenta en fondo
rojizo, texto oscuro y borde de error con `role=alert`; la consulta usa `role=status`.
Los filtros editados pendientes de aplicar se explican mediante texto.

### Navigation

La cabecera ofrece regreso a voz subrayado y cierre de sesión. La navegación de
secciones usa enlaces azules de peso 600, subrayado al hover, ajuste de líneas y
borde inferior. El detalle usa botones de vista que se distribuyen en varias líneas
cuando falta espacio. La actualización del detalle se alinea a la derecha en
escritorio y vuelve al flujo en móvil.

### Chips / Status

Estado neutral y activo comparten forma compacta; el activo usa verde tenue.
Cada estado tiene texto, para que el significado no dependa del color.

### Panels / Tables

Paneles blancos delimitan grupos de datos. Las tablas usan encabezado tonal,
filas con divisores y hover suave. Las celdas tienen padding de 14px; la primera
columna conserva 10px a la izquierda. Consumo e importe se alinean a la derecha
sin salto; notas secundarias aparecen debajo. Las regiones desplazables admiten
foco por teclado. El pie de salud usa fondo muted y conserva el radio de panel.

### Session detail / Timeline

El detalle permanece dentro de la página y mueve el foco a su título al abrirse;
al cerrarse, lo devuelve al botón de sesión. Conversación, acciones y todos los
eventos comparten estructura temporal y metadatos secundarios. El texto preserva
saltos y permite cortes de palabras largas. El JSON usa `details/summary`, fondo
del lienzo, padding de 16px y máximo de 320px de alto con desplazamiento propio.
Estados vacíos, carga, error, texto retirado y ausencia de transcripción se expresan
con mensajes explícitos. Paginar conserva la consulta aplicada y la vista elegida.

El detalle técnico muestra los campos disponibles y agrupa los campos superiores
sin dato en «Campos sin dato y su significado», un desplegable con explicaciones
de las correlaciones ausentes. El JSON conserva `null`, cero y `false` dentro de
`payload`; el texto de conversación aparece arriba sin duplicarse allí. La versión
`unknown` se presenta como «No registrada». Esta presentación no modifica el
contrato almacenado ni atribuye agentes, turnos o costos sin evidencia.

## Do's and Don'ts

### Do:

- Do conservar Public Sans y limitar la paleta administrativa a /admin.
- Do acompañar cifras con unidades, cobertura y estados de ausencia de dato.
- Do mantener foco visible y regiones de tabla accesibles por teclado.
- Do mantener la densidad legible mediante desplazamiento local de tablas en móvil.

### Don't:

- Don’t representar ausencia de medición como cero ni estimación como factura.
- Don’t aplicar la paleta o composición de /admin al recorrido de voz.
- Don’t comunicar selección o error solamente mediante color.
