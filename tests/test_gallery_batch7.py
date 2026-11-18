"""第七批候选名单及安装报告逻辑：无版权素材的离线回归测试。"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "azur_lane" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import install_batch7  # noqa: E402
from gallery_core.catalog import build_catalog  # noqa: E402


class BatchSevenIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(install_batch7.COLLECTIONS.read_text(encoding="utf-8"))
        self.items = self.config["batches"]["batch7"]["items"]

    def test_no_previous_batch_or_committed_model_repeats(self):
        self.assertEqual(len(self.items), 20)
        assets = [item["asset"] for item in self.items]
        self.assertEqual(len(assets), len(set(assets)))
        known = {
            item["asset"]
            for key, group in self.config["batches"].items() if key != "batch7"
            for item in group["items"]
        }
        self.assertFalse(known.intersection(assets))

        source = json.loads((ROOT / "azur_lane/viewer/manifest.json").read_text(
            encoding="utf-8"
        ))
        installed = {item["name"].removesuffix("_hx") for item in source["models"]}
        self.assertFalse(installed.intersection(assets))
        install_batch7.validate_batch_uniqueness()

    def test_explicit_pending_visual_review_and_source_id_hints(self):
        for item in self.items:
            with self.subTest(skin=item["asset"]):
                self.assertTrue(item["title_hint"].strip())
                self.assertTrue(item["style"].strip())
                self.assertIn("候选", item["footwear"])
                self.assertEqual(item["review_status"], "待视觉与动作核验")
                self.assertIsInstance(item["source_skin_id"], int)
                self.assertGreater(item["source_skin_id"], 0)

    def test_shared_gallery_includes_new_batch_style_tags(self):
        index = build_catalog(ROOT)
        # 在 CI 不下载第七批资源，未安装的候选不能假装已有模型。
        self.assertEqual(len(self.items), 20)
        first = self.items[0]["asset"]
        existing = [
            row for row in index["assets"]
            if row["game"] == "azur_lane" and row["source_id"] == first
        ]
        self.assertFalse(existing)
        html = (ROOT / "azur_lane/viewer/index.html").read_text(encoding="utf-8")
        self.assertNotIn('href="batch5.html"', html)
        self.assertNotIn('href="batch6.html"', html)
        self.assertIn('data-view="live2d-view"', html)
        self.assertIn('data-view="gallery-view"', html)

        catalog_src = (ROOT / "gallery_core/catalog.py").read_text(encoding="utf-8")
        self.assertIn('"风格候选：" + style.strip()', catalog_src)

    def test_validate_report_does_not_claim_shoe_review_complete(self):
        report = {"batch": "azur_lane_batch7", "skins": [{
            "asset": "baerdimo_6",
            "paintings_expected": 2,
            "paintings_built": 2,
            "models_expected": 1,
            "models_built": 1,
            "status": "live2d_files_ready",
        }]}
        self.assertEqual(install_batch7.validate_report(report), [])
        row = report["skins"][0]
        self.assertEqual(row["review_status"], "pending_visual_and_motion_review")
        self.assertFalse(row["footwear_verified"])
        self.assertFalse(row["all_motions_verified"])
        self.assertIn("赛车", row["style_candidate"])

    def test_incomplete_models_fail_and_never_count_as_ready(self):
        report = {"batch": "azur_lane_batch7", "skins": [{
            "asset": "baerdimo_6",
            "paintings_expected": 1,
            "paintings_built": 1,
            "models_expected": 0,
            "models_built": 0,
            "status": "painting_only",
        }]}
        self.assertEqual(install_batch7.validate_report(report), ["kubo_2"])
        self.assertEqual(report["skins"][0]["status"], "incomplete")

    def test_duplicate_batch_sources_raise(self):
        with TemporaryDirectory() as temporary:
            temp = Path(temporary) / "collections.json"
            modified = json.loads(json.dumps(self.config, ensure_ascii=False))
            modified["batches"]["batch6"]["items"].append(
                {"asset": "baerdimo_6"}
            )
            temp.write_text(json.dumps(modified, ensure_ascii=False),
                            encoding="utf-8")
            with patch.object(install_batch7, "COLLECTIONS", temp):
                with self.assertRaisesRegex(ValueError, "重复"):
                    install_batch7.validate_batch_uniqueness()

    def test_new_batch_reuses_unified_viewer_entrypoint(self):
        with patch.object(install_batch7, "load_catalog") as catalog, \
             patch.object(install_batch7, "install_batch", return_value=0) as install:
            catalog.return_value = ()
            self.assertEqual(install_batch7.main(["--plan"]), 0)
        self.assertEqual(install.call_args.kwargs["gallery_page"], "index.html")
        self.assertEqual(install.call_args.kwargs["batch_key"], "batch7")


if __name__ == "__main__":
    unittest.main()
