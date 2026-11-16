"""首批 Prestige Skin 本地单元测试，不需要联网。"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "install_prestige.py"
spec = importlib.util.spec_from_file_location("installer", MODULE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PrestigeInstallTests(unittest.TestCase):
    def test_six_distinct_skins(self):
        skins = json.loads(installer.CATALOG.read_text(encoding="utf-8"))["skins"]
        self.assertEqual(6, len(skins))
        self.assertEqual(6, len({skin["id"] for skin in skins}))

    def test_atlas_pages(self):
        self.assertEqual(["a.png", "b.png"],
                         installer.atlas_pages("a.png\nsize:16,16\nskin\nbounds:0,0,4,4\nb.png\n"))

    def test_only_complete_models_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "model.skel").write_bytes(b"4.1.55\x00test")
            (folder / "model.atlas").write_text("model.png\nsize:16,16\n",encoding="utf-8")
            self.assertIsNone(installer.inspect_model(folder))
            (folder / "model.png").write_bytes(b"image")
            self.assertEqual("4.1",installer.inspect_model(folder)["version"])

    def test_path_and_source_guards(self):
        with self.assertRaises(ValueError):
            installer.request("https://example.com/model.skel")
        with self.assertRaises(ValueError):
            installer.remote_files("spine/../../private")
        with self.assertRaises(ValueError):
            installer.atlas_pages("../evil.png")


if __name__ == "__main__":
    unittest.main()
