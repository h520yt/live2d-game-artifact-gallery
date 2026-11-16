"""第四批资源目录与双模型变体的纯逻辑测试，无网络 / UnityPy 依赖。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import install_batch2 as shared
import install_batch3 as batch3
import install_batch4 as batch4


class Batch4Tests(unittest.TestCase):
    def test_twelve_new_skins_with_unique_ids(self):
        self.assertEqual(len(batch4.BATCH), 12)
        ids = {s.skin_id for s in batch4.BATCH}
        self.assertEqual(len(ids), 12)
        self.assertEqual(len({s.asset for s in batch4.BATCH}), 12)
        self.assertTrue(all(s.category == "live2d" for s in batch4.BATCH))
        self.assertFalse(ids.intersection({s.skin_id for s in shared.BATCH}))
        self.assertFalse(ids.intersection({s.skin_id for s in batch3.BATCH}))

    def test_all_have_paintings_and_live2d_bundles(self):
        hashes = SCRIPTS.parent / "config" / "hashes"
        paintings = shared.parse_csv(hashes / "PAINTING.csv")
        models = shared.parse_csv(hashes / "L2D.csv")
        expected = {}
        for skin in batch4.BATCH:
            with self.subTest(skin=skin.asset):
                p = shared.painting_rows(paintings, skin.asset)
                m = shared.live2d_rows(models, skin.asset)
                self.assertGreaterEqual(len(p), 1)
                self.assertGreaterEqual(len(m), 1)
                expected[skin.asset] = m
        # _hx 是斯特拉斯堡同一皮肤的第二个资源包，不是另一款换装。
        self.assertEqual(
            {row.path for row in expected["sitelasibao_2"]},
            {"live2d/sitelasibao_2", "live2d/sitelasibao_2_hx"},
        )
        self.assertEqual(sum(len(x) for x in expected.values()), 13)

    def test_layered_painting_resources_are_not_ignored(self):
        hashes = SCRIPTS.parent / "config" / "hashes"
        paintings = shared.parse_csv(hashes / "PAINTING.csv")
        golden_hind = {row.path for row in shared.painting_rows(paintings, "jinluhao_3")}
        self.assertIn("painting/jinluhao_3_bj_tex", golden_hind)
        self.assertIn("painting/jinluhao_3_n_bj_hx_tex", golden_hind)
        self.assertNotIn("painting/jinluhao_3_n_tex", golden_hind)

    def test_strict_report_detects_missing_second_variant(self):
        data = {
            "batch": "azur_lane_batch4",
            "skins": [{
                "asset": "sitelasibao_2",
                "status": "live2d_files_ready",
                "paintings_built": 4,
                "paintings_expected": 4,
                "models_built": 1,
                "models_expected": 2,
                "animated_effect_verified": True,
            }],
        }
        self.assertEqual(batch4.review_report(data), ["sitelasibao_2"])
        self.assertEqual(data["skins"][0]["status"], "incomplete")
        self.assertFalse(data["skins"][0]["animated_effect_verified"])

        data["skins"][0]["models_built"] = 2
        self.assertEqual(batch4.review_report(data), [])
        self.assertEqual(data["skins"][0]["status"], "incomplete")  # 不会伪造已验证成功

    def test_report_rejects_empty_assets(self):
        data = {"skins": [{"asset": "x", "paintings_built": 0,
                           "paintings_expected": 0, "models_built": 0, "models_expected": 0}]}
        self.assertEqual(batch4.review_report(data), ["x"])

    def test_only_and_batch_name_are_isolated(self):
        selected = shared.pick_skins(["499023"], batch4.BATCH)
        self.assertEqual([x.asset for x in selected], ["feiteliedadi_4"])
        # 同一角色有两款皮肤，按中文名选择两款并不会丢失一款。
        by_character = shared.pick_skins(["腓特烈大帝"], batch4.BATCH)
        self.assertEqual({x.asset for x in by_character}, {"feiteliedadi_3", "feiteliedadi_4"})
        with patch.object(batch4, "install_batch", return_value=0) as execute:
            self.assertEqual(batch4.main(["--plan", "--only", "feiteliedadi_4"]), 0)
        self.assertEqual(execute.call_args.kwargs["batch_key"], "batch4")
        self.assertEqual(execute.call_args.kwargs["gallery_page"], "batch4.html")

    def test_post_install_report_is_rewritten_with_partial_status(self):
        report = {
            "batch": "azur_lane_batch4",
            "skins": [{"asset": "sitelasibao_2", "status": "live2d_files_ready",
                       "paintings_built": 4, "paintings_expected": 4,
                       "models_built": 1, "models_expected": 2}],
        }
        with tempfile.TemporaryDirectory() as folder:
            report_path = Path(folder) / "batch4-install-report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with patch.object(batch4, "install_batch", return_value=0), patch.object(batch4, "REPORT", report_path):
                self.assertEqual(batch4.main(["--only", "sitelasibao_2"]), 1)
            revised = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(revised["skins"][0]["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
