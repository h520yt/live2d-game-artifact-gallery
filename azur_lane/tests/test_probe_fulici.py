"""无需网络、无需 UnityPy 的小型本地检查；在仓库根目录运行 python -m unittest discover -s azur_lane/tests。"""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "probe_fulici.py"


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.hashes = self.root / "config" / "hashes"
        self.hashes.mkdir(parents=True)
        self.models = self.root / "data" / "models"
        self.paintings = self.root / "data" / "paintings"
        self.models.mkdir(parents=True)
        self.paintings.mkdir(parents=True)
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"models":[{
            "name":"fulici_2", "id":407041, "en":"Schwarzes Kaninchen", "ver":4,
            "path":"../data/models/fulici_2/fulici_2.model3.json", "cover":"../data/paintings/fulici_2_rw.png"
        }]}), encoding="utf-8")
        (self.hashes / "L2D.csv").write_text("live2d/fulici_20,4,"+"a"*32+"\nlive2d/fulici_2,4,"+"b"*32+"\n", encoding="utf-8")
        (self.hashes / "PAINTING.csv").write_text("painting/fulici_2_rw_tex,4,"+"c"*32+"\n", encoding="utf-8")
        cfg = types.ModuleType("config")
        cfg.HASHES_DIR = str(self.hashes)
        cfg.MODELS_DIR = str(self.models)
        cfg.PAINTINGS_DIR = str(self.paintings)
        cfg.CACHE_DIR = str(self.cache)
        cfg.MANIFEST_PATH = str(self.manifest)
        cfg.USE_PROXY = True
        self.config_patch = patch.dict(sys.modules, {"config": cfg})
        self.config_patch.start()
        spec = importlib.util.spec_from_file_location("test_loaded_probe_fulici", SCRIPT)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def tearDown(self):
        self.config_patch.stop()
        self.temp.cleanup()

    def create_model(self):
        d = self.models / "fulici_2"
        (d / "motions").mkdir(parents=True)
        (d / "fulici_2.moc3").write_bytes(b"MOC3" + bytes([4, 0, 0, 0]))
        (d / "tex.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"test")
        (d / "motions" / "idle.motion3.json").write_text(json.dumps({"Meta":{"CurveCount":1}}), encoding="utf-8")
        (d / "fulici_2.model3.json").write_text(json.dumps({"FileReferences":{
            "Moc":"fulici_2.moc3", "Textures":["tex.png"],
            "Motions":{"idle":[{"File":"motions/idle.motion3.json"}]}
        }}), encoding="utf-8")
        return d

    def test_csv_uses_exact_path(self):
        row = self.mod.csv_row(self.hashes / "L2D.csv", "live2d/fulici_2")
        self.assertEqual(row, ("live2d/fulici_2", 4, "b" * 32))

    def test_manifest_record_found(self):
        self.assertEqual(self.mod.catalog()["id"], 407041)

    def test_missing_model_fails(self):
        self.assertFalse(self.mod.check())

    def test_reconstructed_model_passes(self):
        self.create_model()
        self.assertTrue(self.mod.check())

    def test_missing_motion_file_fails(self):
        d = self.create_model()
        (d / "motions" / "idle.motion3.json").unlink()
        self.assertFalse(self.mod.check())

    def test_invalid_texture_fails(self):
        d = self.create_model()
        (d / "tex.png").write_bytes(b"not-png")
        self.assertFalse(self.mod.check())

    def test_unsafe_model_reference_rejected(self):
        with self.assertRaises(ValueError):
            self.mod._safe_file(self.models / "fulici_2", "../../escape.moc3")


if __name__ == "__main__":
    unittest.main()
