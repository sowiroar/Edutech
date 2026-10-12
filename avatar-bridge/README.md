# avatar-bridge · voz del agente → avatar (Unreal, Familia VIVA)

Le entrega a Unreal el audio del agente que esté hablando (Lira, Nexus o Elian) para que
el avatar correspondiente (LIRA, NEXO o ELIAN, ver Fase 2 más abajo) mueva los labios, y
le dice a la web cuándo el avatar está disponible.

```
 Navegador ── LiveKit self-hosted ── voice-agent (Gemini Live)
                   │
                   │ audio + estado/personaje del agente (participante oculto, solo lectura)
                   ▼
             avatar-bridge ══ ws://127.0.0.1:8766 (VVA1) ══► Unreal (VivaAvatarReceiver,
                   ▲                                          en avatar-render/, misma red)
                   │ GET /status                                    │ MJPEG (x11grab+ffmpeg)
                   │                                                ▼
             frontend (/api/avatar) ◄── /api/avatar/stream ── avatar-bridge:8080/stream
```

## Piezas

| Archivo | Qué hace |
|---|---|
| `vva1.py` | Protocolo VVA1 (portado del receptor C++ de `Avatar/Plugins/VivaAvatar`) |
| `segmenter.py` | Parte el audio continuo del agente en enunciados (`audio_start` … `audio_end`) |
| `link.py` | Conexión con Unreal: saludo, control de flujo con sus acuses, un enunciado a la vez |
| `bridge.py` | Une audio/estado del agente con el enlace |
| `livekit_source.py` | Busca la sala activa, se une oculto y reenvía audio y `lk.agent.state` |
| `main.py` | Servidor WebSocket en `:8766` y `GET /status` (`{"unreal_connected": bool}`) |

El puente solo trabaja **mientras haya un Unreal conectado**; sin él no se une a ninguna sala.

## Pruebas

```bash
# desde la raíz del repo, con la imagen del agente construida (misma versión de websockets/livekit)
docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD/avatar-bridge:/work:ro" -w /work \
  --entrypoint /app/.venv/bin/python edutech-voice-agent -m pytest -p no:cacheprovider -q
```

`tests/fake_unreal.py` es un port estricto de las reglas del receptor C++ (mismos límites,
mismo orden "texto antes que binario" por tick, mismos fallos con código 1008). Si el puente
rompe el protocolo, el simulado falla con el mismo mensaje que daría Unreal
(`Audio buffer full`, `Overlapping or reused utterance`, …).

## Estado de la verificación

Verificado aquí:
- Protocolo, segmentación y control de flujo contra el Unreal simulado (29 pruebas).
- De extremo a extremo con audio real: un usuario de prueba entró a una sala, Lira saludó con
  Gemini Live y el simulado recibió ese saludo intacto, sin violaciones de protocolo.

Verificado también contra Unreal real (no solo el simulado): el receptor acepta la
transmisión, el modelo de animación de habla funciona, y el cambio de personaje en vivo
(Fase 2) y el video por MJPEG (Fase 3) — ver `avatar-render/README.md`.

## Lado Unreal

El proyecto está en `Avatar/` (Unreal Engine 5.8, Familia VIVA: NEXO, LIRA, ELIAN, más
ATLAS/NOA sin voz todavía — ver `Avatar/FAMILIA_VIVA.md`). Ya hecho, no hace falta repetirlo:

- El componente `VivaAvatarReceiver` (plugin `VivaAvatar`, módulos `SpeechAnimationSolver`,
  `MetaHumanCoreTech`, `NNE`) está en el actor `NEXO_Delicate_Review` de `NewMap_NEXO_Lite`
  (nombre de instancia `VivaVoiceReceiver`), con `BridgeURL = ws://127.0.0.1:8766`,
  `bEnableSpeechAnimation = true`, `LiveLinkSubject = VivaNexo`.
- Fase 2 (2026-10-09): el mismo receptor cambia de personaje en tiempo real por el mensaje
  VVA1 `character_changed` (ver `vva1.py`), buscando el actor por Tag (`NEXO`/`LIRA`/`ELIAN`,
  ya puestos y guardados) en vez de estar fijo al actor dueño. Verificado en vivo en
  Play-In-Editor: LIRA→ELIAN→NEXO→LIRA, cada uno reenlazó cara/animación sin errores.
- Fase 3 (2026-10-09): `avatar-render/` reemplaza Pixel Streaming (nunca llegó a verse en el
  navegador — ICE no completaba) por MJPEG: el juego empaquetado corre headless contra Xvfb
  con GPU real, y ffmpeg manda los frames por HTTP. Ver `avatar-render/README.md`, incluye
  cómo generar el paquete (`RunUAT.sh BuildCookRun`, manual, ~2GB, no vive en git).

## Audio: quién suena

Con el avatar en vivo, el audio lo emite Unreal (se escucha a través del contenedor, no del
MJPEG: el video no lleva audio) y el de LiveKit se silencia
(`AVATAR_MUTE_AGENT_AUDIO=true`), para que la voz no salga duplicada y los labios queden
sincronizados. Con `AVATAR_MUTE_AGENT_AUDIO=false` se mantiene el audio de LiveKit y los
labios irán algo desfasados (el receptor retiene el audio hasta tener animación lista).

## Limitaciones conocidas

- Un solo Unreal a la vez (una conexión nueva reemplaza a la anterior) — un solo personaje
  visible a la vez incluso con varios usuarios conectados.
- Elige la sala más reciente que tenga un agente y una persona; pensado para una sola persona
  usando la app a la vez.
- El receptor exige loopback (`ws://127.0.0.1:…`). Ya no implica "misma máquina física": desde
  la Fase 3, `avatar-render` comparte el namespace de red de este contenedor
  (`network_mode: service:avatar-bridge`) precisamente para seguir cumpliendo esto sin estar
  literalmente en el mismo proceso/máquina.
- Cada cambio de agente reconecta su sesión de Gemini Live, y el receptor añade su propio
  retraso: la voz por el avatar llega algo después que la de LiveKit.
- El MJPEG no lleva audio (es solo video); el audio real sigue siendo el de LiveKit/Unreal
  descrito arriba, no algo que el navegador reciba del stream de video.
