"""NIKKE 皮肤自动补齐脚本的离线测试。"""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from install_skins import family, select_skins, curated_families


class InstallSkinsTest(unittest.TestCase):
    def test_family_links_skin_to_base(self):
        self.assertEqual(family("c090_02"), "c090")
        self.assertEqual(family("c090"), "c090")
        self.assertIsNone(family("eventscene_c090_02"))
        self.assertIsNone(family("c090_extra"))
    
    def test_select_only_curated_family_skin_ids(self):
        entries = [
            {"id": "c090", "name": "Emma"},
            {"id": "c090_01", "name": "Emma Skin 1"},
            {"id": "c090_02", "name": "Emma Skin 2"},
            {"id": "c011_01", "name": "Other"},
            {"id": "eventscene_c090_01", "name": "Cutscene"},
            {"id": "c090_01", "name": "Emma Skin 1"},
        ]
        selected = select_skins(entries, {"c090"})
        self.assertEqual([skin["id"] for skin in selected], ["c090_01", "c090_02"])
        self.assertEqual(len(selected), 2)
        self.assertEqual(len(select_skins(entries, set(), True)), 3)

    def test_curated_family_targets(self):
        groups = curated_families()
        self.assertIn("c090", groups)
        self.assertIn("c272", groups)
        self.assertNotIn(None, groups)


if __name__ == "__main__":
    unittest.main()
