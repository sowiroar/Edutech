"""Servidor VVA1: Unreal se conecta a ws://127.0.0.1:8766 y recibe la voz del agente."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from bridge import Bridge
from link import UnrealLink
from livekit_source import RoomFollower

logger = logging.getLogger("avatar-bridge")


def make_handler(bridge: Bridge):
    async def handler(ws: ServerConnection) -> None:
        # Un Unreal a la vez: una conexion nueva reemplaza a la anterior.
        if bridge.link is not None:
            logger.info("Nueva conexion de Unreal; se cierra la anterior")
            await bridge.link.ws.close(1000, "replaced")
        link = UnrealLink(ws)
        reader = asyncio.create_task(link.read_loop())
        try:
            await link.handshake()
            bridge.attach(link)
            await reader
        except (TimeoutError, ConnectionClosed):
            pass
        finally:
            reader.cancel()
            bridge.detach(link)
            if ws.close_code not in (None, 1000, 1001):
                logger.warning(
                    "Unreal cerro con %s: %s", ws.close_code, ws.close_reason
                )

    return handler


def make_process_request(bridge: Bridge):
    """Responde `GET /status` por el mismo puerto (lo consulta el frontend)."""

    def process_request(connection: ServerConnection, request: Request):
        if request.path != "/status":
            return None  # el resto sigue su curso normal (handshake WebSocket)
        body = json.dumps({"unreal_connected": bridge.link is not None}).encode()
        headers = Headers(
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("Connection", "close"),
            ]
        )
        return Response(200, "OK", headers, body)

    return process_request


async def ticker(bridge: Bridge) -> None:
    while True:
        await bridge.on_tick()
        await asyncio.sleep(0.1)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    host = os.getenv("BRIDGE_HOST", "0.0.0.0")
    port = int(os.getenv("BRIDGE_PORT", "8766"))
    bridge = Bridge()
    follower = RoomFollower(
        bridge,
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    # compression=None: el cliente WebSocket de Unreal no negocia permessage-deflate.
    async with serve(
        make_handler(bridge),
        host,
        port,
        compression=None,
        process_request=make_process_request(bridge),
    ):
        logger.info("Puente VVA1 escuchando en %s:%d", host, port)
        await asyncio.gather(follower.run(), ticker(bridge))


if __name__ == "__main__":
    asyncio.run(main())
