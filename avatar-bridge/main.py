"""Servidor VVA1: Unreal se conecta a ws://127.0.0.1:8766 y recibe la voz del agente."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from urllib.parse import urlsplit

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from bridge import Bridge
from frames import Frames
from lease import RendererLease
from link import UnrealLink
from livekit_source import RoomFollower

logger = logging.getLogger("avatar-bridge")


def make_handler(bridge: Bridge, frames=None):
    async def handler(ws: ServerConnection) -> None:
        if ws.request.path == "/capture":
            if frames is None:
                await ws.close(1008, "capture disabled")
                return
            if frames.source is not None:
                await ws.close(1008, "capture already connected")
                return
            frames.source = ws
            try:
                async for data in ws:
                    frames.push(data)
            except (ConnectionClosed, ValueError):
                pass
            finally:
                frames.clear()
            return
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


def make_process_request(
    bridge: Bridge, follower: RoomFollower, leases=None, secret="", frames=None
):
    """Responde `GET /status` y `GET /hint` por el mismo puerto.

    /hint es GET (no POST) porque el gancho process_request de la libreria
    websockets solo deja pasar peticiones GET; cualquier otro metodo se
    rechaza antes, a nivel del parser HTTP crudo, sin llegar aqui.
    """

    def process_request(connection: ServerConnection, request: Request):
        path = urlsplit(request.path).path

        def response(status, data):
            body = json.dumps(data).encode()
            return Response(
                status,
                "OK" if status == 200 else "Unavailable",
                Headers(
                    [
                        ("Content-Type", "application/json"),
                        ("Content-Length", str(len(body))),
                        ("Cache-Control", "no-store"),
                        ("Connection", "close"),
                    ]
                ),
                body,
            )

        if path == "/capture" or path.startswith("/render/"):
            if (
                not frames
                or not secret
                or not secrets.compare_digest(
                    request.headers.get("Authorization", ""), "Bearer " + secret
                )
            ):
                return response(403, {})
            if path == "/capture":
                return None
            if path == "/render/health":
                return response(200, frames.metrics())
            if path == "/render/frame":
                data = frames.snapshot()
                if data is None:
                    return response(503, {})
                return Response(
                    200,
                    "OK",
                    Headers(
                        [
                            ("Content-Type", "image/jpeg"),
                            ("Content-Length", str(len(data))),
                            ("Cache-Control", "no-store"),
                            ("Connection", "close"),
                        ]
                    ),
                    data,
                )
            return response(404, {})
        if path.startswith("/lease/"):
            if (
                not leases
                or not secret
                or not secrets.compare_digest(
                    request.headers.get("Authorization", ""), "Bearer " + secret
                )
            ):
                return response(403, {"error": "forbidden"})
            room = request.headers.get("X-Avatar-Room", "")
            token = request.headers.get("X-Avatar-Lease", "")
            action = path.rsplit("/", 1)[-1]
            if action == "acquire":
                lease = leases.acquire(room) if bridge.link else None
                if not lease:
                    return response(409, {"error": "busy_or_offline"})
                follower.hint()
                return response(200, {"token": lease.token})
            valid = leases.matches(room, token)
            if action == "renew":
                valid = leases.renew(room, token)
            elif action == "release":
                valid = leases.release(room, token)
                follower.hint()
            elif action != "verify":
                return response(404, {})
            return response(
                200 if valid else 409,
                {
                    "valid": valid,
                    "ready": valid and follower.ready_for(room, token),
                },
            )
        if path == "/status":
            status = {"unreal_connected": bridge.link is not None}
            if leases is not None:
                status.update(managed=True, busy=bool(leases.current))
            body = json.dumps(status).encode()
            headers = Headers(
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(body))),
                    ("Cache-Control", "no-store"),
                    ("Connection", "close"),
                ]
            )
            return Response(200, "OK", headers, body)
        if path == "/hint":
            # El frontend llama esto al crear una sala nueva, para que el
            # puente se una de inmediato sin esperar al proximo poll (ver
            # RoomFollower.hint en livekit_source.py). Sin cuerpo que leer:
            # no hace falta saber el nombre de la sala, solo "hay algo nuevo,
            # anda a mirar".
            follower.hint()
            return Response(204, "No Content", Headers([("Connection", "close")]), b"")
        return None  # el resto sigue su curso normal (handshake WebSocket)

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
    leases = RendererLease() if os.getenv("BRIDGE_REQUIRE_LEASE") == "true" else None
    secret = os.getenv("AVATAR_INTERNAL_KEY", "")
    if leases and len(secret) < 32:
        raise RuntimeError("Managed renderer requires AVATAR_INTERNAL_KEY")
    frames = Frames() if leases else None
    follower = RoomFollower(
        bridge,
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
        leases=leases,
    )
    # compression=None: el cliente WebSocket de Unreal no negocia permessage-deflate.
    async with serve(
        make_handler(bridge, frames),
        host,
        port,
        compression=None,
        process_request=make_process_request(bridge, follower, leases, secret, frames),
        max_size=4 * 1024 * 1024,
    ):
        logger.info("Puente VVA1 escuchando en %s:%d", host, port)
        await asyncio.gather(follower.run(), ticker(bridge))


if __name__ == "__main__":
    asyncio.run(main())
