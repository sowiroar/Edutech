"""Exercise the actual startup/callback without initializing RAG or cloud models."""

import ast
import contextlib
import logging
import os
import unittest
from pathlib import Path
from types import SimpleNamespace


class AvatarStartupTest(unittest.IsolatedAsyncioTestCase):
    async def test_first_agent_announces_character_on_connected_room(self):
        source = ast.parse(
            (Path(__file__).parents[1] / "src/agent.py").read_text(encoding="utf8")
        )
        startup = next(
            n
            for n in source.body
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "multiagent_session"
        )
        startup.decorator_list = []
        startup.args.args[0].annotation = None
        base = next(
            n
            for n in source.body
            if isinstance(n, ast.ClassDef) and n.name == "BaseEducationalAgent"
        )
        announce = next(
            n
            for n in base.body
            if isinstance(n, ast.AsyncFunctionDef)
            and n.name == "anunciar_personaje_avatar"
        )
        connected = False
        attributes = {}

        async def publish(values):
            if not connected:
                raise RuntimeError("room not connected")
            attributes.update(values)

        async def connect():
            nonlocal connected
            connected = True

        room = SimpleNamespace(
            name="test-room", local_participant=SimpleNamespace(set_attributes=publish)
        )
        context = SimpleNamespace(room=room, connect=connect)
        namespace = {
            "os": os,
            "GEMINI_LIVE_MODEL": "test",
            "contextlib": contextlib,
            "logger": logging.getLogger("test-avatar"),
            "TurnHandlingOptions": lambda **kw: kw,
            "viva_telemetry": SimpleNamespace(
                install=lambda *a: None, agent_changed=lambda *a: None
            ),
        }
        exec(
            compile(
                ast.Module(body=[announce, startup], type_ignores=[]),
                "startup-extracted",
                "exec",
            ),
            namespace,
        )

        class FirstAgent:
            AVATAR_CHARACTER = "LIRA"
            llm = object()

        class Session:
            def __init__(self, **kwargs):
                self.room_io = SimpleNamespace(room=room)

            def on(self, *args):
                pass

            async def start(self, *, agent, room):
                agent.session = self
                await namespace["anunciar_personaje_avatar"](agent)
                # Check at the first greeting boundary, not after a later handoff.
                self.initial_character = attributes.get("avatar.character")
                observed.append(self.initial_character)

        observed = []
        namespace.update(LiraAgent=FirstAgent, AgentSession=Session)
        await namespace["multiagent_session"](context)
        self.assertEqual(observed, ["LIRA"])
        self.assertEqual(attributes, {"avatar.character": "LIRA"})


if __name__ == "__main__":
    unittest.main()
