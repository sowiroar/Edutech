import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "voice_demo", Path(__file__).parents[1] / "voice_demo.py"
)
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class VoiceDemoTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("docker"), "Docker Compose CLI is required")
    def test_shared_runtime_image_has_one_build_producer(self):
        # Resolve YAML anchors with Compose itself; this does not use its daemon.
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--project-name",
                "edutech-voice-local",
                "--env-file",
                str(demo.ROOT / "voice.local.env.example"),
                "-f",
                str(demo.ROOT / "compose.voice.yml"),
                "config",
                "--no-interpolate",
                "--format",
                "json",
            ],
            cwd=demo.ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        services = json.loads(result.stdout)["services"]
        initializer = services["rag-init"]
        worker = services["voice-agent"]
        self.assertEqual(initializer["image"], worker["image"])
        producers = [
            name
            for name, service in services.items()
            if service.get("image") == worker["image"] and "build" in service
        ]
        self.assertEqual(
            len(producers), 1, f"Concurrent exports of one tag: {producers}"
        )
        self.assertEqual(initializer["pull_policy"], "never")
        self.assertEqual(
            worker["depends_on"]["rag-init"]["condition"],
            "service_completed_successfully",
        )

    def test_all_commands_are_isolated_from_server_compose(self):
        for action in ("config", "up", "infra", "web", "ps", "down"):
            command = demo.command(action)
            self.assertIn("edutech-voice-local", command)
            self.assertIn(str(demo.ROOT / "compose.voice.yml"), command)
            self.assertNotIn("--remove-orphans", command)
            self.assertNotIn("--volumes", command)

    def test_missing_config_and_empty_values_do_not_pass(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {}, clear=True),
        ):
            path = Path(directory) / ".env.voice"
            self.assertEqual(len(demo.missing_settings(path)), 2)
            path.write_text('GOOGLE_API_KEY=""\nGEMINI_LIVE_MODEL=\n')
            self.assertEqual(len(demo.missing_settings(path)), 2)
            path.write_text(
                "GOOGLE_API_KEY=synthetic\nGEMINI_LIVE_MODEL=synthetic-model\n"
            )
            self.assertEqual(demo.missing_settings(path), [])
            with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
                self.assertEqual(demo.missing_settings(path), ["GOOGLE_API_KEY"])


if __name__ == "__main__":
    unittest.main()
