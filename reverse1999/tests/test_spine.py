"""Spine 下载与完整性审计的离线回归测试。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import spine


class SpineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(spine, "REPOSITORY_ROOT", self.root),
            mock.patch.object(spine, "DATA_DIR", self.root / "data" / "spine"),
            mock.patch.object(spine, "CUBISM_DIR", self.root / "data" / "models"),
            mock.patch.object(spine, "CONFIG_DIR", self.root / "config"),
            mock.patch.object(spine, "AUDIT_PATH", self.root / "config" / "audit-report.json"),
            mock.patch.object(spine, "CATALOG_PATH", self.root / "config" / "catalog_index.json"),
            mock.patch.object(spine, "VENDOR_DIR", self.root / "vendor"),
        ]
        for patch in self.patches:
            patch.start()
        self.mapping = [
            {"name": "佩施塔", "nameEng": "Perchta", "live2d": [
                {"id": 315901, "des": "初始皮肤",
                 "spine": "https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/roles/v4a1_315901_pst",
                 "cubism": "https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/live2d/roles/315901_pst"},
                {"id": 315902, "characterSkin": "童话出逃日",
                 "spine": "https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/roles/v4a1_315902_pst",
                 "cubism": "https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/live2d/roles/315902_pst"},
            ]},
        ]
        self.catalog = {
            "checked_at_utc": "2026-11-13T00:00:00+00:00",
            "spine": ["v4a1_315901_pst", "v4a1_315902_pst"],
            "cubism": ["v4a1_315902_pst"],
        }

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def test_all_skins_even_without_cubism(self):
        data = spine.skin_entries(self.mapping)
        self.assertEqual(len(data), 2)
        self.assertEqual(data["315901"]["spine"], "v4a1_315901_pst")
        self.assertEqual(data["315902"]["skin"], "童话出逃日")

    def test_prefixed_cubism_folder_resolves_by_id(self):
        entry = spine.skin_entries(self.mapping)["315902"]
        self.assertEqual(spine.catalog_matches(entry, self.catalog, "cubism"), "v4a1_315902_pst")
        entry = spine.skin_entries(self.mapping)["315901"]
        self.assertEqual(spine.catalog_matches(entry, self.catalog, "cubism"), "")

    def test_spine_42_binary_version_and_manifest(self):
        folder = spine.DATA_DIR / "v4a1_315901_pst"
        folder.mkdir(parents=True)
        (folder / "315901_pst_ui.skel").write_bytes(b"\x00" * 8 + b"\x074.2.36\x00")
        (folder / "315901_pst.atlas").write_text("315901_pst.png\n", encoding="utf-8")
        (folder / "315901_pst.png").write_bytes(b"fixture")
        self.assertEqual(spine.detect_version(folder / "315901_pst_ui.skel"), "4.2.36")
        result = spine.collect_spine_models(self.mapping)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 315901)
        self.assertEqual(result[0]["poses"]["ui"]["version"], "4.2.36")

    def test_audit_is_directory_only(self):
        with mock.patch.object(spine, "catalog", return_value=self.catalog):
            stats = spine.audit(self.mapping)
        self.assertEqual(stats["mapped_skins"], 2)
        self.assertEqual(stats["skin_spine_present"], 2)
        self.assertEqual(stats["skin_cubism_present"], 1)
        report = json.loads(spine.AUDIT_PATH.read_text(encoding="utf-8"))
        self.assertIn("目录存在", report["note"])

    def test_download_chooses_spine_if_no_cubism(self):
        with mock.patch.object(spine, "catalog", return_value=self.catalog), \
             mock.patch.object(spine, "download_asset") as download, \
             mock.patch.object(spine, "setup_runtime") as runtime:
            chosen = spine.download_selected(self.mapping, "315901")
            self.assertEqual(chosen, ["spine"])
            download.assert_called_once_with("spine", "v4a1_315901_pst")
            runtime.assert_called_once()

    def test_download_both_when_available(self):
        with mock.patch.object(spine, "catalog", return_value=self.catalog), \
             mock.patch.object(spine, "download_asset") as download, \
             mock.patch.object(spine, "setup_runtime"):
            chosen = spine.download_selected(self.mapping, "315902", "both")
            self.assertEqual(chosen, ["cubism", "spine"])
            self.assertEqual(download.call_count, 2)


if __name__ == "__main__":
    unittest.main()
