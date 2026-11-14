"""第二批资源匹配器的纯逻辑测试；无需网络、UnityPy、游戏资源。"""
from pathlib import Path
import importlib.util
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "install_batch2.py"
spec = importlib.util.spec_from_file_location("install_batch2", MODULE)
mod = importlib.util.module_from_spec(spec)
import sys
sys.modules["install_batch2"] = mod
spec.loader.exec_module(mod)


class TestInstaller(unittest.TestCase):
    def test_batch_has_ten_unique_ids(self):
        self.assertEqual(len(mod.BATCH), 10)
        self.assertEqual(len({s.skin_id for s in mod.BATCH}), 10)
        self.assertEqual(len({s.asset for s in mod.BATCH}), 10)

    def test_painting_does_not_include_neighbours_or_backgrounds(self):
        rows = [mod.AssetRow(f"painting/{name}", 10, "a" * 32) for name in (
            "hu_2_tex", "hu_2_n_rw_tex", "hu_2_bj_tex", "hu_20_tex",
            "hu_2_bg_tex", "hu_2", "hu_2_rw_hx_tex",
        )]
        got = [r.path for r in mod.painting_rows(rows, "hu_2")]
        self.assertEqual(got, ["painting/hu_2_n_rw_tex", "painting/hu_2_rw_hx_tex", "painting/hu_2_tex"])

    def test_model_does_not_include_neighbours(self):
        rows = [mod.AssetRow(f"live2d/{name}", 10, "a" * 32) for name in (
            "guanghui_9", "guanghui_9_hx", "guanghui_90", "guanghui_8",
        )]
        got = [r.path for r in mod.live2d_rows(rows, "guanghui_9")]
        self.assertEqual(got, ["live2d/guanghui_9", "live2d/guanghui_9_hx"])

    def test_lookup_and_output(self):
        self.assertEqual(mod.pick_skins(["guanghui_9"])[0].skin_id, 237031)
        self.assertEqual(mod.pick_skins(["237031"])[0].asset, "guanghui_9")
        with self.assertRaises(ValueError):
            mod.pick_skins(["no-such-skin"])
        row = mod.AssetRow("painting/hu_2_n_rw_tex", 10, "a" * 32)
        self.assertEqual(mod.painting_output(row, Path("out")).name, "hu_2_n_rw.png")

    def test_read_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / "PAINTING.csv"
            f.write_text("painting/hu_2_tex,12," + "a" * 32 + "\n", encoding="utf-8")
            self.assertEqual(mod.parse_csv(f)[0].path, "painting/hu_2_tex")


if __name__ == "__main__":
    unittest.main()
