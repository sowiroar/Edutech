# Auditoría de avatares y latencia — 22 octubre 2026

## Base y alcance

Se obtuvo `origin/backp-fase1` en `0225f0a` (integración de Santiago) y se incorporó
por avance rápido a `chore/avatar-latency-audit`, nacida de `origin/main`.
Avatar está en `a204705`, sin modificaciones de autoría. No se actualizó UAM.
El CI remoto de la integración, ejecución `39722307221`, estaba aprobado.

Fuentes: código sincronizado, `INFORME_INTEGRACION_AVATARES.md` entregado por
Santiago y resumen de la reunión en audio. Prioridad comunicada para el martes
27: voz probada; avatar integrado si supera las pruebas. No atribuir a nombres
concretos los fragmentos poco claros de la transcripción automática del audio.

## Viabilidad y calidad

El diseño actual es viable para repartir el renderizado: el servidor ejecuta
agentes y entrega audio; cada navegador dibuja **un** GLB activo. No necesita
una instancia de Unreal por participante. El consumo gráfico se traslada al
dispositivo cliente; no desaparece. La capacidad de concurrencia del servidor
y del proveedor requiere medición independiente.

Mantener la calidad significa preservar identidad, rostro, pelo, ropa, colores
y movimiento con comparación visual. No significa equivalencia automática con
Unreal: glTF no reproduce todos sus materiales, efectos y luces.
[Limitaciones oficiales del exportador](https://dev.epicgames.com/documentation/en-us/unreal-engine/how-the-gltf-exporter-handles-unreal-engine-content).
No se redujeron aquí resolución, número de triángulos ni presupuesto de texturas.
Se conservan los perfiles de Santiago, la liberación al cambiar de avatar y la
continuidad de voz ante fallo gráfico. La boca usa energía y bandas del audio;
no es reconocimiento de fonemas ni lip sync fonético certificado.

## Mejoras comprobables

1. **Arranque de ambos RAG:** el constructor de LlamaIndex hacía `models.get`
   sincrónicamente porque faltaban los límites del modelo. Se declaran los
   límites nativos de Gemini 2.5 Flash (1.048.576 entrada / 65.536 salida),
   conservando `generation_config`, temperatura 0,2 y razonamiento 512.
   `max_output_tokens` sigue sin límite adicional explícito. No cambian voz,
   prompts, documentos, retrieval ni herramientas.
   [Ficha oficial del modelo](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash).
2. **Caché HTTP:** solamente los GLB cuyo nombre contiene SHA-256 se sirven
   como inmutables durante un año. Un modelo cambiado obtiene otra URL.
   El manifiesto y el fondo mantienen revalidación. No se retienen modelos
   adicionales en RAM/GPU para acelerar las transferencias entre agentes.
3. **Medición gráfica:** las muestras de vista previa separan descarga (`fetchMs`),
   parseo (`parseMs`) y primera entrega de frame (`firstFrameMs`). `loadMs`
   conserva su significado anterior, anterior al primer dibujo. Los tiempos
   son del navegador; no representan latencia del agente ni tiempo GPU.
4. **Exportador Mac:** selección de ejecutable nativo, almacenamiento local,
   interrupción del proceso propio y `--no-install` para conservar la entrega
   revisada mientras se genera un candidato. No se guardan assets Unreal.
   `install --preview-only` separa el candidato local del manifiesto canónico;
   una prueba verifica que ni el fondo ni el modelo de llamadas se sustituyen.

## Exportaciones generadas en este Mac

| Personaje | Resultado | GLB | Triángulos / articulaciones |
|---|---|---:|---:|
| ELIAN | Candidato completo, vista previa y controles comprobados | 4.36 MiB | 61.977 / 215 |
| NEXO | Candidato completo, rostro DNA LOD3, vista previa y controles comprobados | 7.06 MiB | 64.330 / 420 |
| LIRA | Fuente y tarjetas exportadas; falta atlas original SlightArch | No instalable todavía | Sin validar |

NEXO conserva 5.048 triángulos de piel del rostro DNA original. Su GLB es mayor
que el de Windows (5,70 MiB); no se redujo calidad para igualar el peso. Los
hashes nuevos y las métricas están en [browser-preview-summary.json](browser-preview-summary.json).
No se reemplazaron los manifiestos canónicos del equipo. Los candidatos locales
siguen en `pending`; no se ofrecen en llamadas ni se presentan como aprobación
artística o de sincronización con audio real.

Cada vista guardó 120 muestras durante aproximadamente dos minutos. Mediana de
FPS: ELIAN 30,0 (mínimo 27), NEXO 30,0 (mínimo 28). Primera entrega de frame en
esta carga: ELIAN 1.296 ms y NEXO 825 ms. **Es una sola carga por modelo**, repetida
en las muestras, no 120 cargas ni un p95 de arranque. Texturas estimadas: 24,0 y
25,3 MiB respectivamente; no equivalen a RAM del proceso ni VRAM global.
El ensayo es una vista previa con movimientos sintéticos, sin micrófono ni llamada.
Se comprobaron idle, gafas/ropa sin duplicación visible y movimientos de labios;
los tests sobre ambos GLB comprueban retorno exacto al reposo y ojos estables.
Falta comparación artística lado a lado con el paquete final privado de Santiago.

En este Mac se instaló Metal Toolchain con el comando oficial de Xcode. LIRA
detectó después que falta **MetaHuman Creator Core Data**, cuyo atlas no viene
en Git. Se solicitó desbloquear el Mac para acceder a las opciones de Epic Games
Launcher; no se sustituyeron cejas ni se omitió ese fallo. La exportación parcial
permanece en `data/local-avatar/runtime/web-export/20261023-025746-lira/`.
Una vez disponible el atlas, basta ejecutar `export_lira_brows_web.py` en un
commandlet con `NEXO_WEB_EXPORT_DIR` apuntando a esa carpeta y `-nullrhi`; después
instalar con `--preview-only` y revisar. No hace falta repetir el horneado principal.

ELIAN: `data/local-avatar/runtime/web-export/20261023-031916-elian/`.
NEXO: `data/local-avatar/runtime/web-export/20261023-032427/`.
Capturas y muestras completas: `data/local-avatar/validation-20261022/` (privado).

Entrega privada generada: `data/local-avatar/delivery/viva-web-candidates-mac-20261022.zip`
(8.546.448 bytes). SHA-256:
`ade3a8a8e935d0b263c5d4fb13ef2628a6fca3374b3c47d3ddafcedcd71d8bc5`.
Sus diez entradas se verificaron después de comprimir. Incluye NEXO, ELIAN,
manifiestos de previsualización, fondos, instrucciones, procedencia y hashes;
no incluye LIRA ni credenciales. Requiere el lector de candidatos de esta rama.
Copiar su carpeta `avatars/` a `agent-starter-react/public/avatars/`, conservando
`manifest.json`. No renombrar `manifest.preview.json` para saltarse la revisión.

## Comprobaciones automatizadas

- Agente: 50 pruebas; Ruff y formato correctos.
- Exportación/flujo: 34 pruebas, incluida separación de manifiesto y fondo de producción.
- Frontend: 35 pruebas aprobadas y 4 omitidas explícitamente por GLB ausentes;
  TypeScript, lint y compilación de producción; tests de contratos,
  controles de boca, límites gráficos y candidato aislado. Los GLB privados
  ausentes se omiten explícitamente, no se cuentan como aprobados.
- La compilación no sustituye la aceptación de arte, audio humano o UAM.

## Medición local del arranque

Tres pares secuenciales con el SDK instalado y acceso real al endpoint de
metadatos de Google. No se generaron respuestas ni audio. Milisegundos:

Equipo: Mac M5, 24 GiB; Unreal compilaba shaders en paralelo. Es una medición
operativa local, no un benchmark de hardware aislado.

| Par | Constructor con consulta de red | Constructor con límites explícitos |
|---|---:|---:|
| 1 | 660,34 | 10,12 |
| 2 | 783,42 | 9,14 |
| 3 | 267,72 | 9,01 |

Es una muestra pequeña de inicialización; **no** es p95, tiempo total de RAG,
tiempo hasta primera voz ni una reducción equivalente en todos los turnos.
Datos: [rag-startup-20261022.json](rag-startup-20261022.json).
La regresión ejecuta los constructores reales de ambos RAG con `models.get`
bloqueado, y comprueba que el ajuste no limita la respuesta a 2.048 tokens.

La caché se verificó por HTTP contra una compilación Next.js de producción en
puerto aislado: GLB de prueba `200 + immutable`; manifiesto `200 + max-age=0`.
El archivo sintético se retiró; no es un avatar de entrega.
Evidencia: [cache-http-20261022.json](cache-http-20261022.json).

## Plan de aceptación para el equipo

1. Exportar e inspeccionar LIRA, NEXO y ELIAN. Comparar frontal y tres cuartos
   con su referencia: rostro, ojos, cejas, pelo, cuello, manos y ropa. Dos
   ciclos completos de idle, apertura/redondeo/extensión y retorno a reposo.
   Un candidato mantiene `pending` hasta completar la revisión de su hash.
2. Voz: conexión en frío y caliente, saludo, pregunta directa, RAG, transferencia,
   interrupción y reconexión. Verificar que el texto y las fuentes no empeoran.
3. Llamada con avatar: LIRA → NEXO → ELIAN → LIRA; voz continua durante cargas,
   boca cerrada al parar/mutar/interrumpir, sin audio duplicado ni ropa duplicada.
4. Medir al menos 20 turnos comparables por condición; separar comienzo de
   conexión, fin de habla del usuario, primera reproducción, duración RAG y
   primera imagen. Reportar tamaño de muestra, p50/p95 y errores. No mezclar
   entrada sintética por texto con latencia desde micrófono.
5. Probar dos sesiones independientes y después concurrencia gradual en UAM.
   Medir RAM de servidor y navegador por separado, GPU del cliente, FPS,
   pérdida de audio y errores del proveedor. No inferir capacidad de la VRAM
   total ni de una sola sesión. Repetir cambios de avatar durante 15 minutos.
6. Para volver atrás, usar el commit previo por el flujo de PR; para un modelo,
   restaurar su manifiesto y GLB correspondientes, no renombrar otro GLB como
   si tuviera ese hash. Los respaldos de instalación quedan en su exportación.

La entrega privada del 21 de octubre no estaba disponible en este Mac. Generar
desde Unreal produce candidatos nuevos: no garantiza el hash ni la aprobación
artística del paquete de Santiago. No hay validación nueva de UAM, Moodle,
micrófono humano o concurrencia por esta auditoría.
