"""检查精选画风门槛：偏幼态、待复核资源不能进入批次安装或精选标签。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gallery_core.collections import load_batch_candidates
from gallery_core.catalog import _azur_collection_info

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "azur_lane/config/curated_collections.json"
FIELDS = ("character", "title_hint", "asset", "style", "footwear", "review_status")


class MatureStyleScreeningTests(unittest.TestCase):
    def test_known_childlike_styles_are_excluded_from_install(self):
        seven = load_batch_candidates(CONFIG, "batch7", FIELDS)
        eight = load_batch_candidates(CONFIG, "batch8", FIELDS)
        self.assertEqual(len(seven), 16)
        self.assertEqual(len(eight), 19)
        assets = {item[2] for item in seven + eight}
        self.assertFalse({"weiyan_2", "weiyan_4", "kubo_2",
                          "ailunsamuna_2", "linuo_3"} & assets)

    def test_filtered_assets_cannot_receive_mature_curated_tags(self):
        metadata = _azur_collection_info(ROOT)
        for asset in ("weiyan_2", "weiyan_4", "kubo_2",
                      "ailunsamuna_2", "linuo_3"):
            self.assertNotIn(asset, metadata)

    def test_original_candidates_remain_auditable(self):
        document = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(document["batches"]["batch7"]["items"]), 20)
        self.assertEqual(len(document["batches"]["batch8"]["items"]), 20)
        statuses = {
            item["asset"]: item["maturity_screen"]
            for batch in ("batch7", "batch8")
            for item in document["batches"][batch]["items"]
        }
        self.assertEqual(statuses["weiyan_2"], "excluded")
        self.assertEqual(statuses["weiyan_4"], "excluded")
        self.assertEqual(statuses["kubo_2"], "excluded")
        self.assertEqual(statuses["ailunsamuna_2"], "hold")
        self.assertEqual(statuses["linuo_3"], "hold")

    def test_new_collections_require_explicit_maturity_review_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "collections.json"
            data = {"schema_version": 1, "batches": {"batch9": {
                "items": [{
                    "asset": "future_1", "character": "A", "title_hint": "B",
                    "style": "uniform", "footwear": "shoes", "review_status": "pending"
                }]
            }}}
            config.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "成熟画风初筛"):
                load_batch_candidates(config, "batch9", FIELDS)
            data["batches"]["batch9"]["items"][0]["maturity_screen"] = "candidate"
            config.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(len(load_batch_candidates(config, "batch9", FIELDS)), 1)

    def test_historical_batch6_is_unaffected(self):
        self.assertEqual(
            len(load_batch_candidates(CONFIG, "batch6", ("asset",))), 20
        )


if __name__ == "__main__":
    unittest.main()
