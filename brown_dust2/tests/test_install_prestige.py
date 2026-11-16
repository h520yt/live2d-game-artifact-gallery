"""首批 Prestige Skin 本地单元测试，不需要联网。"""
import importlib.util
import json
from unittest.mock import patch
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


    def test_raw_listing_reads_atlas_without_api(self):
        folder = "spine/char/char001197"
        atlas = b"char001197.png\nsize:2048,512\nregion\nbounds:0,0,1,1\n"
        with patch.object(installer, "request", return_value=atlas) as mocked:
            files = installer.remote_files(folder)
        self.assertEqual(1, mocked.call_count)
        self.assertEqual("https://raw.githubusercontent.com/myssal/Brown-Dust-2-Asset/master/"
                         + folder + "/char001197.atlas", mocked.call_args.args[0])
        self.assertEqual(["char001197.skel", "char001197.atlas", "char001197.png"],
                         [Path(item["path"]).name for item in files])
        self.assertEqual(atlas, files[1]["payload"])
        self.assertTrue(all(item["size"] is None for item in (files[0], files[2])))

    def test_raw_mode_works_with_expired_api_quota(self):
        atlas = b"cutscene_char001197.png\ncutscene_char001197_2.png\n"
        with patch.object(installer, "request", side_effect=lambda url, binary=False:
                          atlas if "raw.githubusercontent.com" in url else
                          (_ for _ in ()).throw(RuntimeError("API 403 rate limit"))):
            records = installer.remote_files("spine/cutscenes/cutscene_char001197")
        self.assertEqual(4, len(records))

    def test_cached_files_do_not_trigger_download(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cached.png"
            destination.write_bytes(b"previously-downloaded")
            with patch.object(installer, "request", side_effect=AssertionError("downloaded again")):
                status = installer.download_one({"path":"cached.png","size":None,
                                                 "url":"https://raw.githubusercontent.com/x"}, destination)
            self.assertEqual("cached", status)

    def test_raw_download_writes_atomic_content(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "model.png"
            record = {"path":"model.png", "size":None, "url":"https://raw.githubusercontent.com/test"}
            with patch.object(installer, "request", return_value=b"PNG-data") as mocked:
                self.assertEqual("downloaded", installer.download_one(record, destination))
                mocked.assert_called_once()
            self.assertEqual(b"PNG-data", destination.read_bytes())

    def test_nested_api_path_does_not_flatten_backgrounds(self):
        target = installer.target_path(
            "skin", "cutscene", "spine/cutscenes/cutscene_char001197/bg/back.png",
            "spine/cutscenes/cutscene_char001197"
        )
        self.assertEqual(Path("skin/cutscene/bg/back.png"), target.relative_to(installer.DATA))


if __name__ == "__main__":
    unittest.main()
