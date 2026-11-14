"""12 套女性 UNIQUE 商城衣着：资源清单、无 API 下载、断点重试、完整性测试。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import unique
import spine
import scene
import showcase
import sync


class UniqueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [
            mock.patch.object(unique, "DATA_DIR", self.root / "data" / "unique"),
            mock.patch.object(sync, "MANIFEST", self.root / "viewer" / "manifest.json"),
            mock.patch.object(sync, "DATA_DIR", self.root / "data" / "models"),
            mock.patch.object(spine, "DATA_DIR", self.root / "data" / "spine"),
            mock.patch.object(scene, "SCENES", self.root / "data" / "scenes"),
            mock.patch.object(showcase, "SCENE_DIR", self.root / "data" / "showcase"),
        ]
        for patch in self.patches:
            patch.start()
        self.mapping = [{
            "name": "贝丽尔", "nameEng": "Beryl",
            "live2d": [{"id": 313403, "characterSkin": "释命运以弦音"}],
        }]

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temp.cleanup()

    def fake_download(self, url, target, size=0):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.name.endswith(".model3.json"):
            model = {"FileReferences": {
                "Moc": "v4a0_313403_ble.moc3",
                "Textures": ["textures/313403_ble_00.png"],
                "Motions": {
                    "b_idle": [{"File": "motions/b_idle.motion3.json"}],
                    "b_ruchang": [{"File": "motions/b_ruchang.motion3.json"}],
                },
                "Expressions": [{"Name": "e_weixiao", "File": "expressions/e_weixiao.exp3.json"}],
            }}
            data = json.dumps(model).encode("utf-8")
        elif target.name == "background.png":
            data = unique.PNG_SIGNATURE + b"x" * (size - len(unique.PNG_SIGNATURE))
        elif target.suffix == ".png":
            data = unique.PNG_SIGNATURE + b"fixture"
        else:
            data = b"fixture"
        target.write_bytes(data)
        return True

    def test_roster_is_twelve_distinct_verified_unique_entries(self):
        self.assertEqual(len(unique.UNIQUE_SKINS), 12)
        self.assertEqual(len(unique.SKINS), 12)
        self.assertEqual({x[0] for x in unique.UNIQUE_SKINS},
                         {"302504", "306604", "308303", "308603", "310003", "311003",
                          "305305", "314403", "312003", "310504", "315503", "313403"})
        self.assertTrue(all(row[4] > 1_000_000 for row in unique.UNIQUE_SKINS))
        self.assertEqual(len(unique.catalog()), 12)
        self.assertTrue(all(not row["downloaded"] for row in unique.catalog()))

    def test_no_unsafe_user_provided_path(self):
        for value in ("../../313403", "313403\\secret", "bogus", "123456", "313403/../../"):
            with self.assertRaises(ValueError):
                unique.require_skin(value)
        for value in ("../bad", "foo//bad", "/tmp/bad", "foo\\bad", "https://bad"):
            with self.assertRaises(ValueError):
                unique.resource_url(value)

    def test_download_one_uses_original_urls_and_no_api(self):
        with mock.patch.object(spine, "fetch_json", side_effect=AssertionError("GitHub API called")), \
             mock.patch.object(spine, "github_files", side_effect=AssertionError("GitHub API called")), \
             mock.patch.object(spine, "download_file", side_effect=self.fake_download) as fetch:
            info = unique.download_one(self.mapping, "313403")
        self.assertEqual(info["motion_groups"], 2)
        self.assertTrue(unique.inspect_local("313403"))
        self.assertEqual(len(unique.collect_models(self.mapping)), 1)
        self.assertEqual(fetch.call_count, 7)  # 背景、配置、模型、贴图、2动作、1表情
        self.assertTrue(all(args[0].startswith(
            "https://raw.githubusercontent.com/myssal/Reverse-1999-CN-Asset/master/")
            for args, kwargs in fetch.call_args_list))

        # 再次执行只检查已经完整下载的文件，不重复发起任何网络请求。
        with mock.patch.object(spine, "download_file", side_effect=AssertionError("duplicate download")):
            unique.download_one(self.mapping, "313403")

    def test_incomplete_model_not_published(self):
        with mock.patch.object(spine, "download_file", side_effect=self.fake_download):
            unique.download_one(self.mapping, "313403")
        self.assertEqual(len(unique.collect_models(self.mapping)), 1)
        dest = unique.DATA_DIR / "313403" / "cubism" / "motions" / "b_idle.motion3.json"
        dest.unlink()
        self.assertIsNone(unique.inspect_local("313403"))
        self.assertEqual(unique.collect_models(self.mapping), [])
        row = next(x for x in unique.catalog() if x["id"] == 313403)
        self.assertFalse(row["downloaded"])

    def test_sync_manifest_includes_all_twelve_status_and_unique_model(self):
        with mock.patch.object(spine, "download_file", side_effect=self.fake_download):
            unique.download_one(self.mapping, "313403")
        sync.generate_manifest(self.mapping)
        payload = json.loads(sync.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["unique"]), 12)
        self.assertEqual(sum(x["downloaded"] for x in payload["unique"]), 1)
        self.assertEqual(len(payload["models"]), 1)
        model = payload["models"][0]
        self.assertEqual(model["tier"], "UNIQUE")
        self.assertEqual(model["type"], "scene-live2d")
        self.assertTrue(model["path"].endswith("/v4a0_313403_ble.model3.json"))
        self.assertIn("313403", model["background"])


if __name__ == "__main__":
    unittest.main()
