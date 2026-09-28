# avatar-bridge · voz del agente → avatar NEXO (Unreal)

Le entrega a Unreal el audio del agente que esté hablando (Lira, Nexus o Elian) para que
el avatar NEXO mueva los labios, y le dice a la web cuándo el avatar está disponible.

```
 Navegador ── LiveKit Cloud ── voice-agent (Gemini Live)
                   │
                   │ audio + estado del agente (participante oculto, solo lectura)
                   ▼
             avatar-bridge ══ ws://127.0.0.1:8766 (VVA1) ══► Unreal (VivaAvatarReceiver)
                   ▲                                              │ Pixel Streaming (WebRTC)
                   │ GET /status                                   ▼
             frontend (/api/avatar) ◄──────────────────── iframe con el avatar
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

**Sin verificar** (necesita Unreal instalado): que el receptor real y su modelo de animación
acepten esta transmisión, la sincronía labios/audio, y todo lo de Pixel Streaming.

## Lado Unreal (lo que falta)

El proyecto está en `Avatar/` (Unreal Engine 5.8.2, personaje MetaHuman `NEXO`).

1. **Instalar Unreal Engine 5.8 para Linux** desde Epic (cuenta y EULA de Epic; no se puede
   automatizar). Con los plugins MetaHuman y Python habilitados.
2. **Assets reales**: el repo usa Git LFS (`git lfs install && git lfs pull --exclude="Binaries,Intermediate,DerivedDataCache,Saved"`, ≈1.7 GB).
   `Binaries/` e `Intermediate/` son de macOS/Apple Silicon y no sirven en Linux.
3. **Compilar el plugin `VivaAvatar` para Linux** (solo trae binarios de Mac). Depende de los
   módulos `SpeechAnimationSolver`, `MetaHumanCoreTech`, `NNE` y del plugin `StreamingADA`.
4. **Añadir el receptor al actor NEXO**: ningún asset del proyecto usa hoy `VivaAvatarReceiver`
   (el `VivaVoiceReceiver` que menciona `Avatar/AGENTS.md` no está en el repositorio).
   Agregar el componente `VivaAvatarReceiver` al actor `NEXO` con:
   `BridgeURL = ws://127.0.0.1:8766`, `bEnableSpeechAnimation = true`, `LiveLinkSubject = VivaNexo`.
5. **Pixel Streaming**: habilitar el plugin y lanzar el juego/editor con transmisión.
   Los parámetros de arranque y el servidor de señalización cambian entre versiones de Unreal:
   seguir la documentación de Epic de la versión instalada.
6. **Conectar la web**: poner en `.env` `AVATAR_STREAM_URL=<página del reproductor de Pixel Streaming>`
   (alcanzable desde el navegador) y `docker compose up -d frontend`. El avatar aparece solo
   cuando Unreal está conectado al puente.

## Audio: quién suena

Con el avatar en vivo, el audio lo emite Unreal por Pixel Streaming y el de LiveKit se
silencia (`AVATAR_MUTE_AGENT_AUDIO=true`), para que la voz no salga duplicada y los labios
queden sincronizados. Si el navegador bloquea la reproducción automática del avatar, hará
falta un clic sobre él. Con `AVATAR_MUTE_AGENT_AUDIO=false` se mantiene el audio de LiveKit y
los labios irán algo desfasados (el receptor retiene el audio hasta tener animación lista).

## Limitaciones conocidas

- Un solo Unreal a la vez (una conexión nueva reemplaza a la anterior).
- Elige la sala más reciente que tenga un agente y una persona; pensado para una sola persona
  usando la app a la vez.
- El receptor exige loopback (`ws://127.0.0.1:…`): Unreal y este puente deben estar en la
  misma máquina. El puerto solo se publica en `127.0.0.1`.
- Cada cambio de agente reconecta su sesión de Gemini Live, y el receptor añade su propio
  retraso: la voz por el avatar llega algo después que la de LiveKit.
