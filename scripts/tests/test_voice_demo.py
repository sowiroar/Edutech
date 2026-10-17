import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("voice_demo", Path(__file__).parents[1] / "voice_demo.py")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class VoiceDemoTests(unittest.TestCase):
    def test_all_commands_are_isolated_from_server_compose(self):
        for action in ("config", "up", "infra", "web", "ps", "down"):
            command = demo.command(action)
            self.assertIn("edutech-voice-local", command)
            self.assertIn(str(demo.ROOT / "compose.voice.yml"), command)
            self.assertNotIn("--remove-orphans", command)
            self.assertNotIn("--volumes", command)

    def test_missing_config_and_empty_values_do_not_pass(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / ".env.voice"
            self.assertEqual(len(demo.missing_settings(path)), 2)
            path.write_text('GOOGLE_API_KEY=""\nGEMINI_LIVE_MODEL=\n')
            self.assertEqual(len(demo.missing_settings(path)), 2)
            path.write_text('GOOGLE_API_KEY=synthetic\nGEMINI_LIVE_MODEL=synthetic-model\n')
            self.assertEqual(demo.missing_settings(path), [])
            with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
                self.assertEqual(demo.missing_settings(path), ["GOOGLE_API_KEY"])


if __name__ == "__main__":
    unittest.main()
