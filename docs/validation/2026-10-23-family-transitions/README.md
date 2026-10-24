# Familia web y transición — 23 octubre 2026

## Inventario verificado

Seis diseños existen en `../Avatar/avatars.json`, origin/main a204705. El paquete
privado `../avatars_santiago_glb` y su copia Downloads/avatars contienen solo
LIRA, NEXO y ELIAN. El repositorio remoto de assets no agregó commits después de
esa revisión. Tener un mapa Unreal no equivale a tener un GLB ni un agente.

| Personaje | Diseño Unreal | Entrega GLB de Santiago | Worker conversacional actual |
|---|---|---|---|
| LIRA | retenido de Juan | instalado | LiraAgent / Aoede |
| NEXO | nativo Mateo | instalado | NexusAgent / Puck |
| ELIAN | diseño turquesa | instalado | ElianAgent / Kore |
| NOA | SK_Noa_AlternateFace | no entregado | no implementado |
| NOVA | Final | no entregado | no implementado |
| ATLAS | Final | no entregado | no implementado |

El catálogo del frontend admite los seis. La vista `/avatar-preview` permite
cambiarlos sin recargar y señala los GLB pendientes. La API de llamadas sigue
anunciando únicamente modelos instalados/revisados. No se inventaron prompts,
voces ni handoffs para los tres especialistas que aún no existen en el worker.

## Cambio visual

Antes, la clave React del personaje desmontaba todo el visor en cada relevo.
Ahora permanece el contenedor y captura una imagen temporal del último fotograma.
Se libera la escena anterior (geometría, texturas, esqueletos y contexto WebGL),
y se carga la siguiente. Su primer fotograma inicia un fundido de 240 ms y la
imagen temporal se retira. No se habilita preserveDrawingBuffer ni se mantienen
dos escenas 3D. La imagen 2D usa como máximo el presupuesto del render, 1280×720
(~3,52 MiB de píxeles RGBA; no representa el consumo total del navegador).

La preferencia de movimiento reducido elimina el fundido y espera igualmente
al primer fotograma. Los cambios rápidos cancelan animaciones anteriores. Un
fallo conserva la vía de voz. El reproductor LiveKit y los prompts no cambian.
Las ventanas de métricas y el monitor acústico se reinician por hash del modelo,
para no atribuir muestras del personaje anterior al siguiente.

El pulido labial aceptado permanece: algoritmo de Santiago, mandíbula original,
55 ms para redondeo/extensión. Es reacción acústica; no reconocimiento de fonemas.

## Exportación de los diseños faltantes

`export_family_web.py` lee los mapas retenidos de NOA/NOVA/ATLAS y exporta su
personaje y accesorios estáticos unidos al cuerpo/rostro; excluye fondos y luces.
No guarda mapas, materiales ni blueprints. Comprueba la cara alternativa de NOA.
El empaquetador conserva los ojos y dientes horneados sobre cada cara original,
y exige sus tres archivos auxiliares antes de instalar. Los candidatos nuevos
siempre empiezan con revisiones pendientes.

Desde Edutech, uno por vez:

```sh
python3 scripts/avatar_web.py export --character NOA --no-install
python3 scripts/avatar_web.py export --character NOVA --no-install
python3 scripts/avatar_web.py export --character ATLAS --no-install
# Con la ruta de resultado que imprime cada exportación:
uv run --no-project --python 3.12 --with Pillow==12.0.0 python scripts/avatar_web.py install --path RUTA_EXPORTADA --preview-only
```

No promover un candidato a llamadas por pasar tests estructurales. Revisar cara,
ropa, accesorios, reposo, habla y memoria contra el diseño guardado. Una exportación
nueva tampoco hereda la aceptación del paquete de Santiago.

## Comprobación repetible

1. Reconstruir frontend: `python3 scripts/voice_demo.py web`.
2. Abrir `http://localhost:3500/avatar-preview?character=LIRA`.
3. Cambiar LIRA → NEXO → ELIAN y repetir rápidamente. Esperar el modelo nuevo;
   no debe quedar una imagen vieja superpuesta ni aumentar el número de lienzos.
4. Probar un nombre pendiente: informar que falta GLB, sin sustituir otro avatar.
5. Con movimiento reducido del sistema, el relevo espera la carga y no anima.
6. En llamada, pedir el cambio real de especialista. La voz debe continuar sin
   reiniciarse por el fundido. Revisar avatar_quality_sample por personaje/hash.

Pruebas automatizadas: 59 frontend aprobadas, 3 omitidas por assets privados
históricos; 35 scripts Python aprobadas; 21 pruebas de contrato/colector aprobadas;
TypeScript, lint y build aprobados. El contrato v2 y su JSON generado admiten
los seis nombres. Colector local reconstruido antes de habilitar cualquier
candidato adicional; frontend local reconstruido en el puerto 3500.
Verificación local Chrome: tres personajes, un canvas después del relevo, sin
errores de consola; muestra puntual ELIAN 30 FPS. No es un benchmark de memoria,
una validación nueva UAM/RTX4050 ni una prueba de conversación real.
