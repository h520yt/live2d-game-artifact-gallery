"""离线运行：python -m unittest discover -s azur_lane/tests -p 'test_install_curated_live2d.py'"""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_curated_live2d.py"
FIXTURE = {
    "jianwu_2": (503011, 3), "aijier_4": (499053, 4),
    "ougen_8": (403037, 8), "luoen_4": (499012, 3), "shengluyisi_5": (102134, 2),
}
PNG = b"\x89PNG\r\n\x1a\n"


class InstallCuratedLive2DTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        hashes = root / "hashes"
        hashes.mkdir()
        self.models = root / "models"
        self.models.mkdir()
        self.paintings = root / "paintings"
        self.paintings.mkdir()
        self.cache = root / "cache"
        self.cache.mkdir()
        self.manifest = root / "manifest.json"
        models, characters, l2d, painting = [], [], [], []
        self.names = []
        for name, (sid, cnt) in FIXTURE.items():
            self.names.append(name)
            models.append({"name": name, "id": sid, "ver": 4,
                           "path": f"../data/models/{name}/{name}.model3.json"})
            items = []
            for i in range(cnt):
                art_name = name if i == 0 else f"{name}_rw{i}"
                items.append({"name": art_name, "path": f"../data/paintings/{art_name}.png"})
                painting.append(f"painting/{art_name}_tex,11,{'b'*32}")
            characters.append({"skin": sid, "items": items})
            l2d.append(f"live2d/{name},12,{'a'*32}")
        self.manifest.write_text(json.dumps({"models": models, "characters": characters}), encoding="utf-8")
        (hashes / "L2D.csv").write_text("\n".join(l2d) + "\n", encoding="utf-8")
        (hashes / "PAINTING.csv").write_text("\n".join(painting) + "\n", encoding="utf-8")
        self.cfg = types.ModuleType("config")
        self.cfg.HASHES_DIR = str(hashes)
        self.cfg.MANIFEST_PATH = str(self.manifest)
        self.cfg.MODELS_DIR = str(self.models)
        self.cfg.PAINTINGS_DIR = str(self.paintings)
        self.cfg.CACHE_DIR = str(self.cache)
        self.cfg.USE_PROXY = True
        self.modules_patch = patch.dict(sys.modules, {"config": self.cfg})
        self.modules_patch.start()
        spec = importlib.util.spec_from_file_location("curated_installer_test", SCRIPT)
        self.installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.installer)

    def tearDown(self):
        self.modules_patch.stop()
        self.temp.cleanup()

    def make_model(self, name="jianwu_2"):
        base = self.models / name
        (base / "motions").mkdir(parents=True, exist_ok=True)
        (base / (name + ".moc3")).write_bytes(b"MOC3" + b"\x04\0\0\0")
        (base / "texture.png").write_bytes(PNG + b"rest")
        (base / "motions" / "idle.motion3.json").write_text('{"Meta":{"CurveCount":1}}')
        (base / (name + ".model3.json")).write_text(json.dumps({"FileReferences": {
            "Moc": name + ".moc3", "Textures": ["texture.png"],
            "Motions": {"idle": [{"File": "motions/idle.motion3.json"}]}
        }}), encoding="utf-8")
        return base

    def test_preflight_five_models_and_twenty_paintings(self):
        entries = self.installer.catalog(self.names)
        self.assertEqual(len(entries), 5)
        self.assertEqual(sum(len(e["paintings"]) for e in entries), 20)
        self.assertEqual(entries[2]["l2d"][0], "live2d/ougen_8")
        self.assertEqual(entries[2]["id"], 403037)

    def test_can_select_one_model_without_others(self):
        entries = self.installer.catalog(["aijier_4"])
        self.assertEqual(len(entries), 1)
        self.assertEqual(len(entries[0]["paintings"]), 4)

    def test_model_is_missing_by_default(self):
        self.assertFalse(self.installer.check_model("jianwu_2")[0])

    def test_complete_model_passes_file_check(self):
        self.make_model()
        valid, reason, motion_count = self.installer.check_model("jianwu_2")
        self.assertTrue(valid, reason)
        self.assertEqual(motion_count, 1)

    def test_bad_moc3_fails(self):
        base = self.make_model()
        (base / "jianwu_2.moc3").write_bytes(b"NOPE")
        self.assertFalse(self.installer.check_model("jianwu_2")[0])

    def test_missing_motion_fails(self):
        base = self.make_model()
        (base / "motions" / "idle.motion3.json").unlink()
        self.assertFalse(self.installer.check_model("jianwu_2")[0])

    def test_unsafe_relative_path_rejected(self):
        with self.assertRaises(ValueError):
            self.installer.safe_relative(self.models / "jianwu_2", "../../secret.txt")

    def test_valid_painting_uses_png_signature(self):
        p = self.paintings / "jianwu_2.png"
        self.assertFalse(self.installer.valid_painting("jianwu_2"))
        p.write_bytes(PNG + b"abc")
        self.assertTrue(self.installer.valid_painting("jianwu_2"))

    def test_manifest_not_modified_by_catalog_and_check(self):
        before = self.manifest.read_bytes()
        entries = self.installer.catalog(["jianwu_2"])
        self.installer.check(entries)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_inconsistent_skin_name_fails_preflight(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["characters"][0]["items"][0]["path"] = "../other/evil.png"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.installer.catalog(["jianwu_2"])


if __name__ == "__main__":
    unittest.main()
