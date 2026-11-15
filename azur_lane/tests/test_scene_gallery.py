"""静态场景：分层解析、人物归组与 Mesh 坐标清单测试（不下载资源）。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config as C
import gen_manifest
import install_batch2
import install_scene_layers


class SceneGalleryTests(unittest.TestCase):
    def test_bj_and_front_belong_to_original_skin(self):
        p2info = {"hu_2": {"group": 200, "id": 202, "name": "Test", "rel": 1}}
        for name in ("hu_2_bj", "hu_2_n_bj_hx", "hu_2_front"):
            with self.subTest(name=name):
                group, skin, _, kind = gen_manifest.resolve(name, p2info)
                self.assertEqual((group, skin, kind), (200, 202, "part"))
        self.assertEqual(gen_manifest.split_suffixes("hu_20_bj")[0], "hu_20")

    def test_scene_row_selection(self):
        assets = ["hu_2_tex", "hu_2_bj_tex", "hu_2_n_bj_hx_tex",
                  "hu_2_front_tex", "hu_2_unknown_tex", "hu_20_bj_tex"]
        rows = [install_batch2.AssetRow("painting/" + x, 12, "a" * 32) for x in assets]
        grouped = install_batch2.painting_rows(rows, "hu_2")
        selected = install_scene_layers.select_rows(grouped, {"hu_2"})
        self.assertEqual([row.path for row in selected], [
            "painting/hu_2_bj_tex", "painting/hu_2_front_tex", "painting/hu_2_n_bj_hx_tex"
        ])

    def test_manifest_keeps_scene_parts_and_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            images = root / "paintings"
            images.mkdir()
            cfg = root / "skins.json"
            cfg.write_text(json.dumps({
                "202": {"painting": "hu_2", "id": 202, "ship_group": 20,
                        "name": "Test", "shop_id": 900, "group_index": 2}
            }), encoding="utf-8")
            for name in ("hu_2", "hu_2_n_rw", "hu_2_bj"):
                (images / (name + ".png")).write_bytes(b"fake-file")
            bounds = {"minX": -200, "minY": -400, "maxX": 200, "maxY": 400}
            (images / "hu_2_bj.meta.json").write_text(
                json.dumps({"geometry": "mesh", "bounds": bounds}), encoding="utf-8"
            )
            manifest = root / "manifest.json"
            with patch.object(gen_manifest, "SKIN_TPL", str(cfg)), \
                 patch.object(C, "PAINTINGS_DIR", str(images)), \
                 patch.object(C, "MODELS_DIR", str(root / "models")), \
                 patch.object(C, "VIEWER_DIR", str(root)), \
                 patch.object(C, "MANIFEST_PATH", str(manifest)):
                self.assertEqual(install_scene_layers.installed_assets(), {"hu_2"})
                gen_manifest.generate()
            chars = json.loads(manifest.read_text(encoding="utf-8"))["characters"]
            self.assertEqual(len(chars), 1)
            self.assertEqual(chars[0]["asset"], "hu_2")
            self.assertEqual(chars[0]["rep"], "hu_2_n_rw")
            named = {item["name"]: item for item in chars[0]["items"]}
            self.assertEqual(named["hu_2_bj"]["kind"], "part")
            self.assertEqual(named["hu_2_bj"]["bounds"], bounds)
            self.assertIsNone(named["hu_2"]["bounds"])


if __name__ == "__main__":
    unittest.main()
