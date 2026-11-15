"""第三批：纯逻辑 / 仓库清单验证（不访问网络、不依赖 UnityPy）。"""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import install_batch2 as shared
import install_batch3 as batch3


class Batch3Tests(TestCase):
    def test_batch_is_twelve_distinct_live2d_skins(self):
        self.assertEqual(len(batch3.BATCH), 12)
        self.assertEqual(len({x.skin_id for x in batch3.BATCH}), 12)
        self.assertEqual(len({x.asset for x in batch3.BATCH}), 12)
        self.assertTrue(all(x.category == "live2d" for x in batch3.BATCH))

    def test_repository_has_paintings_and_model_hashes_for_every_skin(self):
        hashes = SCRIPTS.parent / "config" / "hashes"
        painting = shared.parse_csv(hashes / "PAINTING.csv")
        models = shared.parse_csv(hashes / "L2D.csv")
        for skin in batch3.BATCH:
            with self.subTest(skin=skin.asset):
                self.assertGreaterEqual(len(shared.painting_rows(painting, skin.asset)), 1)
                self.assertGreaterEqual(len(shared.live2d_rows(models, skin.asset)), 1)

    def test_legacy_batch_two_selection_still_works(self):
        self.assertEqual(len(shared.pick_skins(None)), 10)
        self.assertEqual(len(shared.pick_skins(None, batch3.BATCH)), 12)
        self.assertEqual(shared.pick_skins(["gaoxiong_7"], batch3.BATCH)[0].skin_id, 303117)
        with self.assertRaises(ValueError):
            shared.pick_skins(["something_missing"], batch3.BATCH)

    def test_batch_three_report_and_gallery_are_isolated(self):
        with patch.object(batch3, "install_batch", return_value=0) as run:
            code = batch3.main(["--plan", "--only", "gaoxiong_7"])
        self.assertEqual(code, 0)
        args, kwargs = run.call_args
        self.assertEqual(args, (["--plan", "--only", "gaoxiong_7"],))
        self.assertEqual(kwargs["batch_key"], "batch3")
        self.assertEqual(kwargs["batch_label"], "第三批")
        self.assertEqual(kwargs["gallery_page"], "batch3.html")
        self.assertEqual(len(kwargs["batch"]), 12)
