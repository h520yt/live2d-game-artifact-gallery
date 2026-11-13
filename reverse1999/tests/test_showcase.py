"""《重返未来：1999》完整皮肤展示离线测试。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import showcase
import spine
import sync


class ShowcaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data" / "showcase"
        self.patch = mock.patch.object(showcase, "SCENE_DIR", self.data)
        self.patch.start()
        self.mapping = [{"name": "露西", "nameEng": "Lucy", "live2d": [
            {"id": 308603, "characterSkin": "生如行棋"}]}]

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def create_fixture(self):
        folder = self.data / "308603"
        fg = folder / "foreground"
        fg.mkdir(parents=True)
        (folder / "background.png").write_bytes(showcase.PNG_SIGNATURE + b"fixture")
        (fg / "308603_lxxx_skinstore.skel").write_bytes(b"12345678\x074.2.36\x00")
        (fg / "308603_lxxx_skinstore.atlas").write_text("308603_lxxx_skinstore.png\n", encoding="utf-8")
        (fg / "308603_lxxx_skinstore.png").write_bytes(showcase.PNG_SIGNATURE + b"fixture")
        return folder

    def test_scene_path_safety(self):
        self.assertEqual(showcase.safe_scene_id("308603"), "308603")
        for value in ("315901", "../308603", "not-an-id"):
            with self.assertRaises(ValueError):
                showcase.safe_scene_id(value)
        with self.assertRaises(ValueError):
            showcase.validate_recipe("308603", {
                "background": "singlebg/skin2dbg/315901.png",
                "foreground": "roles_bust/v2a8_308603_lxxx_skinstore",
            })

    def test_manifest_only_when_complete(self):
        self.assertEqual(showcase.collect_showcases(self.mapping), [])
        folder = self.create_fixture()
        models = showcase.collect_showcases(self.mapping)
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["type"], "showcase")
        self.assertEqual(models[0]["name"], "露西")
        self.assertEqual(models[0]["poses"]["商城展示"]["version"], "4.2.36")
        (folder / "background.png").unlink()
        self.assertEqual(showcase.collect_showcases(self.mapping), [])

    def test_unsupported_spine_version_excluded(self):
        folder = self.create_fixture()
        (folder / "foreground" / "308603_lxxx_skinstore.skel").write_bytes(b"?" * 120)
        self.assertEqual(showcase.collect_showcases(self.mapping), [])

    def test_full_manifest_integration(self):
        self.create_fixture()
        with mock.patch.object(sync, "MANIFEST", self.root / "manifest.json"), \
             mock.patch.object(sync, "DATA_DIR", self.root / "models"), \
             mock.patch.object(spine, "DATA_DIR", self.root / "spine"):
            sync.generate_manifest(self.mapping)
        data = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["models"]), 1)
        self.assertEqual(data["models"][0]["type"], "showcase")

    def test_download_uses_matched_resources(self):
        asset_dir = "roles_bust/v2a8_308603_lxxx_skinstore"
        files = [{
            "name": name, "path": asset_dir + "/" + name,
            "download_url": f"https://raw.githubusercontent.com/{spine.SOURCE}/master/{asset_dir}/{name}",
            "size": 8,
        } for name in ("308603_lxxx_skinstore.skel", "308603_lxxx_skinstore.atlas", "308603_lxxx_skinstore.png")]
        meta = {
            "type": "file", "size": 8,
            "download_url": f"https://raw.githubusercontent.com/{spine.SOURCE}/master/singlebg/skin2dbg/308603.png",
        }
        def fake_download(url, dest, expected):
            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.suffix == ".skel":
                data = b"12345678\x074.2.36\x00"
            elif dest.suffix == ".png":
                data = showcase.PNG_SIGNATURE + b"fixture"
            else:
                data = b"308603_lxxx_skinstore.png\n"
            dest.write_bytes(data)
        with mock.patch.object(spine, "fetch_json", return_value=meta) as fetched, \
             mock.patch.object(spine, "github_files", return_value=files) as listed, \
             mock.patch.object(spine, "download_file", side_effect=fake_download) as downloaded, \
             mock.patch.object(spine, "setup_runtime") as runtime:
            self.assertEqual(showcase.download_showcase(self.mapping, "308603"), "308603")
            fetched.assert_called_once_with(f"{spine.API}/contents/singlebg/skin2dbg/308603.png")
            listed.assert_called_once_with(asset_dir)
            self.assertEqual(downloaded.call_count, 4)
            runtime.assert_called_once()


if __name__ == "__main__":
    unittest.main()
