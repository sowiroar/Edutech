"""Exercise the production reply method without loading RAG or cloud clients."""

import ast
import asyncio
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace

source = ast.parse(
    (Path(__file__).parents[1] / "src/agent.py").read_text(encoding="utf8")
)
base = next(
    n
    for n in source.body
    if isinstance(n, ast.ClassDef) and n.name == "BaseEducationalAgent"
)
reply = next(
    n
    for n in base.body
    if isinstance(n, ast.AsyncFunctionDef) and n.name == "generar_respuesta_confiable"
)
namespace = {"asyncio": asyncio, "logger": logging.getLogger("test-reply")}
exec(
    compile(ast.Module(body=[reply], type_ignores=[]), "production-reply", "exec"),
    namespace,
)


class Session:
    def __init__(self, behavior):
        self.behavior = behavior
        self.handlers = {}
        self.calls = 0

    def on(self, event, callback):
        self.handlers.setdefault(event, []).append(callback)

    def off(self, event, callback):
        self.handlers[event].remove(callback)

    def emit(self, event, **fields):
        for callback in list(self.handlers.get(event, [])):
            callback(SimpleNamespace(**fields))

    async def generate_reply(self, **kwargs):
        self.calls += 1
        return await self.behavior(self)


class ReplyLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def run_reply(self, behavior, timeout=0.01):
        session = Session(behavior)
        agent = SimpleNamespace(session=session)
        session.current_agent = agent
        await namespace["generar_respuesta_confiable"](
            agent, "test greeting", timeout=timeout
        )
        self.assertTrue(all(not callbacks for callbacks in session.handlers.values()))
        return session

    async def test_speech_does_not_retry(self):
        async def behavior(session):
            session.emit("agent_state_changed", new_state="speaking")
            return SimpleNamespace(interrupted=False)

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 1)

    async def test_real_silence_retries_once(self):
        async def behavior(session):
            if session.calls == 2:
                session.emit("agent_state_changed", new_state="speaking")
            return SimpleNamespace(interrupted=False)

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 2)

    async def test_handoff_is_not_silence(self):
        async def behavior(session):
            if session.calls > 1:
                raise RuntimeError("old realtime session already stopped")
            session.current_agent._handoff_requested = True
            return SimpleNamespace(interrupted=False)

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 1)

    async def test_new_active_agent_prevents_old_reply(self):
        async def behavior(session):
            session.current_agent = object()
            return SimpleNamespace(interrupted=False)

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 1)

    async def test_close_during_generation_is_terminal(self):
        async def behavior(session):
            session.emit("close")
            raise RuntimeError("AgentSession is closing, cannot use generate_reply()")

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 1)

    async def test_close_while_waiting_does_not_retry(self):
        async def behavior(session):
            asyncio.get_running_loop().call_soon(session.emit, "close")
            return SimpleNamespace(interrupted=False)

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 1)

    async def test_user_interruption_is_not_silence(self):
        async def behavior(session):
            return SimpleNamespace(interrupted=True)

        session = await self.run_reply(behavior)
        self.assertEqual(session.calls, 1)

    async def test_all_real_handoff_tools_mark_the_old_agent(self):
        helper = next(
            n
            for n in base.body
            if isinstance(n, ast.FunctionDef) and n.name == "_prepare_handoff"
        )
        env = {
            "Agent": object,
            "RunContext": object,
            "logger": logging.getLogger("test-handoff"),
        }
        for name in ("LiraAgent", "NexusAgent", "ElianAgent"):
            env[name] = lambda **kwargs: SimpleNamespace(**kwargs)
        exec(
            compile(
                ast.Module(body=[helper], type_ignores=[]), "production-handoff", "exec"
            ),
            env,
        )
        tested = 0
        for cls in source.body:
            if not isinstance(cls, ast.ClassDef) or cls.name not in (
                "LiraAgent",
                "NexusAgent",
                "ElianAgent",
            ):
                continue
            for tool in cls.body:
                if not isinstance(
                    tool, ast.AsyncFunctionDef
                ) or not tool.name.startswith("transfer_to_"):
                    continue
                tool.decorator_list = []
                exec(
                    compile(
                        ast.Module(body=[tool], type_ignores=[]),
                        "production-tool",
                        "exec",
                    ),
                    env,
                )
                agent = SimpleNamespace(
                    chat_ctx=SimpleNamespace(copy=lambda **kwargs: "kept context"),
                    _reply_wake=asyncio.Event(),
                )
                agent._prepare_handoff = lambda target, agent=agent: env[
                    "_prepare_handoff"
                ](agent, target)
                target = await env[tool.name](agent, None)
                self.assertEqual(target.chat_ctx, "kept context")
                self.assertTrue(agent._handoff_requested)
                self.assertTrue(agent._reply_wake.is_set())
                tested += 1
        self.assertEqual(tested, 4)

    async def test_unrelated_errors_are_not_hidden(self):
        async def behavior(session):
            raise RuntimeError("unrelated failure")

        with self.assertRaisesRegex(RuntimeError, "unrelated failure"):
            await self.run_reply(behavior)


if __name__ == "__main__":
    unittest.main()
