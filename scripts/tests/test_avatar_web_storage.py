import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "avatar_web_storage", Path(__file__).parents[1] / "avatar_web_storage.py"
)
storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage)


class StorageTests(unittest.TestCase):
    def test_project_on_d_can_keep_runtime_on_d(self):
        with patch.object(storage, "ROOT", Path("D:/Edutech/Edutech")):
            storage.validate_runtime_drive("D:/EdutechRuntime", "C:/Windows")

    def test_system_volume_is_rejected_even_if_project_is_on_d(self):
        with patch.object(storage, "ROOT", Path("D:/Edutech/Edutech")):
            with self.assertRaisesRegex(ValueError, "Windows"):
                storage.validate_runtime_drive("c:/runtime", "C:/Windows")

    def test_system_volume_can_have_another_letter(self):
        with self.assertRaisesRegex(ValueError, "Windows"):
            storage.validate_runtime_drive("E:/runtime", "e:/Windows")
        storage.validate_runtime_drive("D:/runtime", "e:/Windows")

    def setup_paths(self, base):
        parent, runtime = Path(base) / "project-data", Path(base) / "runtime"
        source, destination = parent / "web-export", runtime / "web-export"
        source.mkdir(parents=True)
        runtime.mkdir()
        (source / "run").mkdir()
        (source / "run/model.glb").write_bytes(b"test-model\x00\x01")
        (source / "run/export.json").write_text('{"ok":true}')
        return parent, runtime, source, destination

    def test_moves_verified_files_and_can_run_again(self):
        with tempfile.TemporaryDirectory() as base:
            parent, runtime, source, destination = self.setup_paths(base)
            expected = storage.snapshot(source)
            result = storage.move_verified(source, destination, parent, runtime)
            self.assertEqual(result["files_moved"], 2)
            self.assertEqual(storage.snapshot(destination), expected)
            self.assertFalse(source.exists())
            self.assertEqual(len(list(runtime.glob("move-verification-*.json"))), 1)
            self.assertEqual(
                storage.move_verified(source, destination, parent, runtime)[
                    "files_moved"
                ],
                0,
            )

    def test_different_destination_preserves_every_original(self):
        with tempfile.TemporaryDirectory() as base:
            parent, runtime, source, destination = self.setup_paths(base)
            (destination / "run").mkdir(parents=True)
            (destination / "run/model.glb").write_bytes(b"other-model")
            expected = storage.snapshot(source)
            with self.assertRaisesRegex(ValueError, "archivo diferente"):
                storage.move_verified(source, destination, parent, runtime)
            self.assertEqual(storage.snapshot(source), expected)
            self.assertEqual(
                (destination / "run/model.glb").read_bytes(), b"other-model"
            )

    def test_incomplete_copy_never_removes_originals(self):
        with tempfile.TemporaryDirectory() as base:
            parent, runtime, source, destination = self.setup_paths(base)
            expected = storage.snapshot(source)
            with patch.object(
                storage.shutil,
                "copyfileobj",
                lambda src, dst, **kw: dst.write(b"broken"),
            ):
                with self.assertRaisesRegex(RuntimeError, "verificacion"):
                    storage.move_verified(source, destination, parent, runtime)
            self.assertEqual(storage.snapshot(source), expected)

    def test_rejects_paths_outside_the_named_export_directories(self):
        with tempfile.TemporaryDirectory() as base:
            parent, runtime, source, destination = self.setup_paths(base)
            with self.assertRaisesRegex(ValueError, "limitado"):
                storage.move_verified(source, runtime / "other", parent, runtime)
            self.assertTrue((source / "run/model.glb").is_file())

    def test_export_redirects_cache_logs_and_temporary_paths(self):
        root = Path("D:/EdutechRuntime")
        paths = {
            key: root / value
            for key, value in {
                "temp": "Temp",
                "cache": "DerivedDataCache",
                "user": "UnrealUser",
                "shaders": "ShaderWorkingDir",
            }.items()
        }
        output = root / "web-export/run"
        env, flags = storage.export_environment(paths, output)
        self.assertEqual(env["NEXO_WEB_EXPORT_DIR"], str(output))
        for key in ("TEMP", "TMP", "TMPDIR"):
            self.assertEqual(env[key], str(paths["temp"]))
        self.assertIn(f"-LocalDataCachePath={paths['cache']}", flags)
        self.assertIn(f"-UserDir={paths['user']}", flags)
        self.assertIn(f"-ShaderWorkingDir={paths['shaders']}", flags)


if __name__ == "__main__":
    unittest.main()
