---
name: VIVAVerse — extensión operativa
description: Sistema existente del frontend aplicado al panel de telemetría.
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
typography:
  headline:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2rem"
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
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
  metric:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 550
  detail:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
  code:
    fontFamily: "CommitMono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
rounded:
  control: "8px"
spacing:
  control-y: "8px"
  control-x: "12px"
  compact: "12px"
  standard: "16px"
  content: "20px"
  group: "24px"
  section: "40px"
  wide: "48px"
components:
  button-default:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  button-default-hover:
    backgroundColor: "{colors.muted}"
  button-primary:
    backgroundColor: "{colors.foreground}"
    textColor: "{colors.background}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  table-heading:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.foreground}"
    padding: "13px 16px"
---

# Design System: VIVAVerse

## Overview

**Creative North Star: "Continuidad del frontend VIVAVerse"**

La superficie operativa hereda Public Sans, los colores semánticos y el cambio claro/oscuro del frontend existente. La jerarquía se construye con tipografía, espacio y divisores; las tablas conservan la relación entre datos, unidades y cobertura. No se establece una identidad visual nueva.

Registro extraído del código al cierre de la extensión `/admin`; no es un rediseño
global. El nombre de dirección describe la continuidad autorizada en `PRODUCT.md`,
no una metáfora de marca nueva. Ese archivo conserva el brief y la secuencia de la
superficie; este documento registra reglas reutilizables verificadas.

**Key Characteristics:**

- Tipografía continua con el frontend de voz.
- Superficies planas y contraste semántico.
- Cifras tabulares y contexto de medición visible.
- Controles etiquetados y desplazamiento horizontal local.

Fuentes: `agent-starter-react/styles/globals.css`, `app/layout.tsx`,
`app/admin/telemetry.css` y `app/admin/page.tsx`, con rutas relativas al frontend.
Se contrastaron las capturas `docs/validation/2026-10-17-telemetry/desktop.png` y `mobile.png`.
Las capturas verifican el tema claro; la variante oscura aquí se deriva del código.

## Colors

La base neutral comparte los colores semánticos del frontend, con acento heredado
azul en claro y cian en oscuro.

### Primary

`primary` y `dark-primary` pertenecen al sistema compartido. El botón principal del
acceso administrativo usa inversión foreground/background, tal como lo implementa
la superficie; no introduce un nuevo color de marca.

### Neutral

`background` define el lienzo, `foreground` el texto principal, `muted` los encabezados
de tabla y hover, `muted-foreground` las explicaciones y `border` las separaciones.
Las entradas `dark-*` documentan los valores del mismo rol bajo `.dark`: en código
se consume siempre la variable semántica, no un color fijado por componente.
`destructive` se reserva al borde de error; el texto conserva el color principal.
Las rampas del sidecar son muestras sintetizadas para la vista previa, no colores
adicionales del producto ni valores para implementar componentes.

**The Semantic Theme Rule.** Los componentes consumen las variables compartidas para
que texto, fondo y estados cambien juntos con el tema.

## Typography

**Display / Body Font:** Public Sans con respaldo sans-serif del sistema.
**Label/Mono Font:** las etiquetas conservan Public Sans; los identificadores y JSON
usan la pila CommitMono existente del frontend.

La jerarquía de la extensión está registrada en el frontmatter: título principal,
títulos de sección, cuerpo, etiquetas, métricas y detalle. No se añade una familia
de exhibición. El título principal pasa a 1.7rem bajo el breakpoint móvil. El
importe de sección utiliza 1.25rem y peso 550; el texto auxiliar de consulta,
0.82rem. Los párrafos limitan su ancho a 75ch. Las tablas usan 0.875rem y encabezados
con peso 600. Toda la superficie activa cifras tabulares.

**The Measured Number Rule.** Tamaño y alineación ayudan a comparar cifras; la unidad,
el denominador y la ausencia de dato permanecen visibles junto a ellas.

## Layout

El contenedor de `/admin` centra un ancho máximo de 1280px, con padding de
48px 32px 64px. La cabecera alinea título y navegación; las secciones tienen
40px de separación y los grupos se distinguen con espacio y divisores. La síntesis
de actividad es una lista de definiciones flexible, no una cuadrícula de tarjetas.

A 700px o menos, el padding pasa a 28px 16px 40px. Cabecera y encabezados de sección
se apilan. Los filtros forman dos columnas; las dos fechas ocupan ambas y los demás
campos pueden compartir fila. Las tablas conservan un ancho mínimo de 560px dentro
de una región desplazable, con indicación visible y acceso por teclado. La tabla,
no la página completa, absorbe el ancho adicional. El formulario de acceso tiene
ancho máximo de 460px y separación de campos de 12px.

Estas dimensiones describen la extensión operativa, no un mandato de composición
para voz/avatar. La navegación propia del panel sustituye visualmente el chrome
fijo compartido para evitar superposición durante la lectura.

## Elevation & Depth

El panel no usa sombras. Divisores finos y fondos de encabezado expresan agrupación;
el foco es un contorno de 2px en foreground con separación de 3px. No se generaliza
esta ausencia de sombras a componentes externos al panel: el botón outline de la
biblioteca compartida conserva su sombra existente.

## Shapes

Los controles y errores usan esquinas suaves de la escala `control` y borde de 1px.
Tablas y secciones permanecen rectangulares y abiertas. Los botones, inputs y
selects comparten altura mínima de 42px; el tamaño puede crecer con el contenido.

## Components

### Buttons

Controles sobrios con peso 550, padding de la escala y borde semántico. El botón
normal usa fondo del lienzo y hover muted. El acceso principal invierte fondo/texto;
su hover reduce opacidad a 0.85. Disabled usa opacidad 0.55 y cursor de espera. Todos
comparten el foco visible. No hay animación añadida en esta superficie.

### Inputs / Fields

Inputs y selects comparten forma y color con botones, tipografía heredada y etiquetas
persistentes. Las fechas conservan controles nativos. Error se comunica mediante
mensaje con role alert y borde destructive; los estados de consulta usan role status.

### Navigation

Enlace subrayado de regreso a voz y acción de cierre de sesión, con separación de
20px en escritorio. En móvil la navegación ocupa una fila propia y distribuye
ambas acciones a los extremos. La interacción no depende solo del hover.

### Tables / Containers

Encabezado muted, filas con divisor inferior, celdas de 13px 16px y primera columna
con 10px a la izquierda. Consumo e importe se alinean a la derecha sin salto;
metadatos aparecen en texto secundario bajo su valor. No hay chips ni tarjetas
propios de esta extensión. Los detalles JSON se despliegan con details/summary,
con área de código desplazable de hasta 420px de ancho.

### Query state

Los campos pueden contener cambios aún no aplicados: un aviso textual lo explica.
Actualizar confirma la consulta; paginar conserva esa consulta aplicada. La consulta
no reemplaza silenciosamente una sesión inspeccionada. Estados vacíos y “Sin dato”
conservan su significado, además del formato visual de cifras y cobertura.

## Do's and Don'ts

### Do:

- Do conservar Public Sans y los tokens semánticos compartidos.
- Do acompañar cifras con unidades, cobertura y estados de ausencia de dato.
- Do mantener foco visible y regiones de tabla accesibles por teclado.
- Do mantener la densidad legible mediante desplazamiento de tablas en móvil.

### Don't:

- Don’t convertir las secciones operativas en tarjetas decorativas.
- Don’t representar ausencia de medición como cero ni estimación como factura.
- Don’t aplicar la composición de /admin al recorrido de voz sin revisar su contexto.
