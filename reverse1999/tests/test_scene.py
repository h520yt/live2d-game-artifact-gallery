"""商城皮肤同 ID 背景与商城骨骼组合测试（无网络）。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import scene
import spine


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [
            mock.patch.object(scene, "ROOT", self.root),
            mock.patch.object(scene, "SCENES", self.root / "data" / "scenes"),
            mock.patch.object(spine, "REPOSITORY_ROOT", self.root),
        ]
        for patch in self.patches:
            patch.start()
        self.mapping = [{"name": "贝丽尔", "nameEng": "Beryl",
                         "live2d": [{"id": 313403, "characterSkin": "释命运以弦音",
                                     "spine": "https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/roles/v4a0_313403_ble"}]}]

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temp.cleanup()

    def test_select_store_asset_by_id(self):
        tree = [
            {"path": "v4a0_313403_ble_skinstore", "type": "tree"},
            {"path": "v4a0_313403_ble_skinstorecardface", "type": "tree"},
            {"path": "v3a4_305305_yx_skinstore", "type": "tree"}
        ]
        self.assertEqual(scene.choose_bust_directory(tree, "313403"),
                         "v4a0_313403_ble_skinstorecardface")
        self.assertEqual(scene.choose_bust_directory(tree, "305305"),
                         "v3a4_305305_yx_skinstore")
        self.assertEqual(scene.choose_bust_directory(tree, "315901"), "")
        with self.assertRaises(ValueError):
            scene.choose_bust_directory(tree, "../313403")

    def test_locate_full_scene_assets(self):
        prefix = "https://raw.githubusercontent.com/myssal/Reverse-1999-CN-Asset/master"
        replies = [
            {"tree": [{"path": "roles_bust", "type": "tree", "sha": "bust_sha"}]},
            {"tree": [{"path": "v4a0_313403_ble_skinstorecardface", "type": "tree"}]},
            [{"type": "file", "name": "313403.png", "size": 123,
              "download_url": prefix + "/singlebg/skin2dbg/313403.png"}],
        ]
        nodes = [
            {"path": "roles_bust/v4a0_313403_ble_skinstorecardface/313403_ble_skinstorecardface.skel",
             "name": "313403_ble_skinstorecardface.skel", "type": "file", "size": 101,
             "download_url": prefix + "/roles_bust/v4a0_313403_ble_skinstorecardface/313403_ble_skinstorecardface.skel"},
            {"path": "roles_bust/v4a0_313403_ble_skinstorecardface/313403_ble_skinstorecardface.atlas",
             "name": "313403_ble_skinstorecardface.atlas", "type": "file",
             "download_url": prefix + "/roles_bust/v4a0_313403_ble_skinstorecardface/313403_ble_skinstorecardface.atlas"},
            {"path": "roles_bust/v4a0_313403_ble_skinstorecardface/313403_ble_skinstorecardface.png",
             "name": "313403_ble_skinstorecardface.png", "type": "file",
             "download_url": prefix + "/roles_bust/v4a0_313403_ble_skinstorecardface/313403_ble_skinstorecardface.png"},
        ]
        with mock.patch.object(spine, "fetch_json", side_effect=replies), \
             mock.patch.object(spine, "github_files", return_value=iter(nodes)), \
             mock.patch.object(spine, "fetch_bytes", return_value=b"313403_ble_skinstorecardface.png\nsize:2048,2048\n"):
            answer = scene.locate_scene_remote("313403")
        self.assertEqual(answer["skeleton"], "313403_ble_skinstorecardface.skel")
        self.assertEqual(answer["pages"], ["313403_ble_skinstorecardface.png"])

    def test_verified_scene_bypasses_github_api(self):
        with mock.patch.object(spine, "fetch_json", side_effect=AssertionError("GitHub API called")), \
             mock.patch.object(spine, "github_files", side_effect=AssertionError("GitHub API called")):
            found = scene.locate_scene("313403")
        self.assertEqual(found["id"], "313403")
        self.assertEqual(found["folder"], "v4a0_313403_ble_skinstorecardface")
        self.assertEqual(found["background"]["size"], 9438795)
        self.assertEqual(found["skeleton"], "313403_ble_skinstorecardface.skel")
        self.assertEqual(found["atlas"], "313403_ble_skinstorecardface.atlas")
        self.assertEqual(found["pages"], ["313403_ble_skinstorecardface.png"])
        self.assertEqual(len(found["items"]), 3)
        for item in found["items"]:
            self.assertTrue(item["download_url"].startswith(
                "https://raw.githubusercontent.com/myssal/Reverse-1999-CN-Asset/master/"))

    def test_verified_download_and_manifest_without_api(self):
        def fake_download(url, target, expected=0):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.name.endswith(".skel"):
                target.write_bytes(b"\x00" * 8 + b"\x074.2.36\x00")
            else:
                target.write_bytes(b"fixture")
            return True

        with mock.patch.object(spine, "fetch_json", side_effect=AssertionError("GitHub API called")), \
             mock.patch.object(spine, "download_file", side_effect=fake_download) as downloader, \
             mock.patch.object(spine, "setup_runtime"), \
             mock.patch.object(scene, "download_verified_live2d", return_value=None):
            metadata = scene.download_scene(self.mapping, "313403")
        self.assertEqual(downloader.call_count, 4)
        self.assertEqual(metadata["id"], "313403")
        self.assertEqual(len(scene.collect_scenes(self.mapping)), 1)

    def test_cubism_refs_include_entry_motions_expressions_and_textures(self):
        config = {"FileReferences": {
            "Moc": "v4a0_313403_ble.moc3",
            "Textures": ["textures/313403_ble_00.png"],
            "DisplayInfo": "v4a0_313403_ble.cdi3.json",
            "Motions": {"b_idle": [{"File": "motions/b_idle.motion3.json"}],
                        "b_ruchang": [{"File": "motions/b_ruchang.motion3.json"}]},
            "Expressions": [{"Name": "smile", "File": "expressions/e_weixiao.exp3.json"}]
        }}
        files = scene.cubism_references(config)
        self.assertIn("v4a0_313403_ble.moc3", files)
        self.assertIn("motions/b_ruchang.motion3.json", files)
        self.assertIn("expressions/e_weixiao.exp3.json", files)
        self.assertIn("textures/313403_ble_00.png", files)
        for unsafe in ("../../bad", "/tmp/secret", r"textures\escape.png", "textures/../bad"):
            with self.assertRaises(ValueError):
                scene.safe_cubism_reference(unsafe)

    def test_cubism_scene_only_visible_when_dependencies_complete(self):
        folder = scene.SCENES / "313403"
        cubism = folder / "cubism"
        (cubism / "textures").mkdir(parents=True)
        file_name = "v4a0_313403_ble.model3.json"
        model_json = {"FileReferences": {
            "Moc": "v4a0_313403_ble.moc3",
            "Textures": ["textures/313403_ble_00.png"],
            "Motions": {"b_idle": [{"File": "motions/b_idle.motion3.json"}]}
        }}
        config = cubism / file_name
        config.write_text(json.dumps(model_json), encoding="utf-8")
        meta = {"cubism": "cubism/" + file_name}
        self.assertIsNone(scene.cubism_ready("313403", folder, meta))
        (cubism / "v4a0_313403_ble.moc3").write_bytes(b"fixture")
        (cubism / "textures/313403_ble_00.png").write_bytes(b"fixture")
        self.assertIsNone(scene.cubism_ready("313403", folder, meta))
        (cubism / "motions").mkdir()
        (cubism / "motions/b_idle.motion3.json").write_text("{}", encoding="utf-8")
        self.assertEqual(scene.cubism_ready("313403", folder, meta),
                         "../data/scenes/313403/cubism/" + file_name)

    def test_scene_manifest_requires_downloaded_files(self):
        folder = scene.SCENES / "313403"
        spine_dir = folder / "spine"
        spine_dir.mkdir(parents=True)
        metadata = {"id": "313403", "skeleton": "313403_ble_skinstorecardface.skel",
                    "atlas": "313403_ble_skinstorecardface.atlas",
                    "pages": ["313403_ble_skinstorecardface.png"],
                    "actor_source": "roles_bust/v4a0_313403_ble_skinstorecardface"}
        (folder / "scene.json").write_text(json.dumps(metadata), encoding="utf-8")
        (folder / "background.png").write_bytes(b"bg")
        (spine_dir / metadata["skeleton"]).write_bytes(b"\x00"*8 + b"\x074.2.36\x00")
        (spine_dir / metadata["atlas"]).write_text(metadata["pages"][0], encoding="utf-8")
        self.assertEqual(scene.collect_scenes(self.mapping), [])
        (spine_dir / metadata["pages"][0]).write_bytes(b"png")
        records = scene.collect_scenes(self.mapping)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "scene")
        self.assertEqual(records[0]["name"], "贝丽尔")
        self.assertEqual(records[0]["scene"]["version"], "4.2.36")


if __name__ == "__main__":
    unittest.main()
