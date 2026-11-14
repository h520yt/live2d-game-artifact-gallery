"""吼吼点唱机典藏衣着批量下载器：清单、重试、Spine/Cubism 分支及索引。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import jukebox
import spine
import sync
import scene
import showcase
import unique


class JukeboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.patches = [
            mock.patch.object(jukebox, "DATA_DIR", self.root / "data" / "jukebox"),
            mock.patch.object(sync, "DATA_DIR", self.root / "data" / "models"),
            mock.patch.object(sync, "MANIFEST", self.root / "viewer" / "manifest.json"),
            mock.patch.object(scene, "SCENES", self.root / "data" / "scenes"),
            mock.patch.object(spine, "DATA_DIR", self.root / "data" / "spine"),
            mock.patch.object(showcase, "SCENE_DIR", self.root / "data" / "showcase"),
            mock.patch.object(unique, "DATA_DIR", self.root / "data" / "unique"),
        ]
        for p in self.patches:
            p.start()
        self.mapping = [
            {"name": "玛尔纱", "nameEng": "Marsha",
             "live2d": [{"id": 312704, "characterSkin": "告慰尘与惘"}]},
            {"name": "夏利", "nameEng": "Charlie",
             "live2d": [{"id": 301703, "characterSkin": "镜中幕间"}]},
        ]

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temporary.cleanup()

    def test_roster_32_with_27_live2d_and_5_spine(self):
        self.assertEqual(len(jukebox.SKINS), 32)
        self.assertEqual(len(jukebox.BY_ID), 32)
        self.assertEqual(sum(row[3] == "cubism" for row in jukebox.SKINS), 27)
        self.assertEqual(sum(row[3] == "spine" for row in jukebox.SKINS), 5)
        self.assertEqual(len(jukebox.catalog()), 32)
        self.assertEqual(jukebox.require_skin(312704)[2], "告慰尘与惘")
        self.assertFalse(any(row["downloaded"] for row in jukebox.catalog()))

    def test_disallow_arbitrary_ids_and_asset_paths(self):
        for invalid in ("../../301703", "123456", "../", r"301703\evil"):
            with self.assertRaises(ValueError):
                jukebox.require_skin(invalid)
        for invalid in ("../../danger", "live2d/../x", "/root/file", "foo\\bar", "https://evil"):
            with self.assertRaises(ValueError):
                jukebox.remote(invalid)

    @staticmethod
    def fake_file(url, target):
        dest = Path(target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.name.endswith(".model3.json"):
            obj = {"FileReferences": {
                "Moc": "v4a1_312704_mes.moc3",
                "Textures": ["textures/312704_mes_00.png"],
                "Motions": {"b_idle": [{"File": "motions/b_idle.motion3.json"}]},
                "Expressions": [{"Name": "smile", "File": "expressions/smile.exp3.json"}]
            }}
            dest.write_text(json.dumps(obj), encoding="utf-8")
        else:
            dest.write_bytes(b"fixture-payload")
        return True

    def test_cubism_does_not_use_github_api_and_can_resume(self):
        with mock.patch.object(spine, "fetch_json", side_effect=AssertionError("unexpected GitHub API")), \
             mock.patch.object(spine, "download_file", side_effect=self.fake_file) as downloader:
            info = jukebox.download_one(self.mapping, "312704")
        self.assertEqual(info["type"], "cubism")
        self.assertEqual(info["motions"], 1)
        self.assertEqual(downloader.call_count, 5)  # config/moc/png/motion/expression
        self.assertTrue(all(
            args[0].startswith("https://raw.githubusercontent.com/myssal/Reverse-1999-CN-Asset/master/")
            for args, kwargs in downloader.call_args_list
        ))
        with mock.patch.object(spine, "download_file", side_effect=AssertionError("downloaded again")):
            jukebox.download_one(self.mapping, "312704")
        self.assertEqual(len(jukebox.collect_models(self.mapping)), 1)
        self.assertEqual(jukebox.collect_models(self.mapping)[0]["channel"], "JUKEBOX")

    def test_spine_all_ui_room_fight_and_runtime(self):
        with mock.patch.object(spine, "download_file", side_effect=self.fake_file) as downloader, \
             mock.patch.object(spine, "detect_version", return_value="4.2.36"), \
             mock.patch.object(spine, "setup_runtime") as setup:
            info = jukebox.download_one(self.mapping, "301703")
            self.assertEqual(info["type"], "spine")
            self.assertEqual(downloader.call_count, 6)
            setup.assert_called_once()
            models = jukebox.collect_models(self.mapping)
        self.assertEqual(len(models), 1)
        self.assertEqual(set(models[0]["poses"]), {"ui", "room", "fight"})
        self.assertEqual(models[0]["poses"]["ui"]["version"], "4.2.36")

    def test_incomplete_skin_not_published(self):
        with mock.patch.object(spine, "download_file", side_effect=self.fake_file):
            jukebox.download_one(self.mapping, "312704")
        model = jukebox.DATA_DIR / "312704" / "cubism" / "textures" / "312704_mes_00.png"
        model.unlink()
        self.assertIsNone(jukebox.known_models("312704"))
        self.assertFalse(next(x for x in jukebox.catalog() if x["id"] == 312704)["downloaded"])
        self.assertEqual(jukebox.collect_models(self.mapping), [])

    def test_manifest_includes_full_status_and_preview_for_downloaded_skin(self):
        with mock.patch.object(spine, "download_file", side_effect=self.fake_file):
            jukebox.download_one(self.mapping, "312704")
        sync.generate_manifest(self.mapping)
        data = json.loads(sync.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(data["jukebox"]), 32)
        self.assertEqual(sum(1 for x in data["jukebox"] if x["downloaded"]), 1)
        self.assertEqual(len(data["models"]), 1)
        self.assertEqual(data["models"][0]["channel"], "JUKEBOX")
        self.assertEqual(data["models"][0]["type"], "cubism")
        self.assertTrue(data["models"][0]["path"].endswith("v4a1_312704_mes.model3.json"))


if __name__ == "__main__":
    unittest.main()
