"""四批资源安装脚本的离线回归测试（不下载游戏素材）。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest


NIKKE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NIKKE_DIR / "scripts"))

from install_batches import load_batches, select_items, validate_pose, verify_installations
from gen_nikke_manifest import load_curated_batches


class CuratedBatchTest(unittest.TestCase):
    def test_four_batches_have_35_distinct_ids(self):
        batches = load_batches()
        self.assertEqual([len(batch["items"]) for batch in batches], [6, 9, 14, 6])
        items = select_items(batches, [], True)
        self.assertEqual(len(items), 35)
        self.assertEqual(len({item["id"] for item in items}), 35)
        self.assertEqual(set(load_curated_batches()["c272_01"]), {"3"})

    def test_single_batch_selection(self):
        items = select_items(load_batches(), ["2"], False)
        self.assertEqual(len(items), 9)
        self.assertEqual(items[0]["id"], "c181_01")
        self.assertTrue(all(item["batches"] == ["2"] for item in items))

    def test_missing_atlas_page_is_incomplete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            char_dir = root / "c290"
            char_dir.mkdir()
            (char_dir / "c290_00.skel").write_bytes(b"Spine")
            (char_dir / "c290_00.atlas").write_text("atlas.png", encoding="utf-8")
            info = {"sub": "", "skel": "c290_00.skel",
                    "atlas": "c290_00.atlas", "pages": ["atlas.png"]}
            ok, missing = validate_pose("c290", info, root)
            self.assertFalse(ok)
            self.assertEqual(len(missing), 1)
            (char_dir / "atlas.png").write_bytes(b"image-bytes")
            ok, missing = validate_pose("c290", info, root)
            self.assertTrue(ok)
            self.assertEqual(missing, [])

    def test_ready_partial_and_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pose = {"sub": "", "skel": "c290_00.skel",
                    "atlas": "c290_00.atlas", "pages": ["a.png"]}
            model_dir = root / "c290"
            model_dir.mkdir()
            for name in ["c290_00.skel", "c290_00.atlas", "a.png"]:
                (model_dir / name).write_bytes(b"x")
            items = [{"id": "c290", "name": "玛娜", "batches": ["1"]},
                     {"id": "c840", "name": "艾达", "batches": ["1"]}]
            manifest = {"characters": [{"id": "c290", "poses": {"fb": pose}}]}
            result = verify_installations(items, manifest, root)
            self.assertEqual([item["status"] for item in result], ["ready", "missing"])


if __name__ == "__main__":
    unittest.main()
