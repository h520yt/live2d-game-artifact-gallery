"""所有新游戏与 1999 遵守同一「卡片网格 → 大舞台 → 原位返回」界面约定。"""
import json
import re
import unittest
from pathlib import Path

from scripts import new_game
from gallery_core.catalog import build_catalog

ROOT = Path(__file__).resolve().parents[2]


class UnifiedGalleryLayoutTests(unittest.TestCase):
    def test_reverse1999_has_one_catalog_and_shared_layout(self):
        page = (ROOT / "reverse1999/viewer/index.html").read_text(encoding="utf-8")
        self.assertIn('../../shared/skin_gallery.css', page)
        self.assertIn('../../shared/skin_gallery.js', page)
        self.assertIn('id="catalog-view"', page)
        self.assertIn('id="detail-view"', page)
        self.assertIn('id="back-to-catalog"', page)
        self.assertIn('SkinGallery.create', page)
        self.assertNotIn('id="filter-unique"', page)
        self.assertNotIn('id="filter-jukebox"', page)
        self.assertNotIn('id="filter-latest"', page)
        self.assertNotIn('id="filter-tier68"', page)

    def test_legacy_model_flex_rule_cannot_override_shared_grid(self):
        """截图回归：旧 #models:flex 曾让每张 4:5 预览变成整屏宽度。"""
        page = (ROOT / "reverse1999/viewer/index.html").read_text(encoding="utf-8")
        shared_css = (ROOT / "shared/skin_gallery.css").read_text(encoding="utf-8")
        self.assertNotRegex(page, r"#models\\s*\\{\\s*display\\s*:\\s*flex")
        self.assertIn(".sg-host #models.sg-grid{", page)
        self.assertIn("display:grid;", page)
        self.assertIn("grid-template-columns:repeat(auto-fill,minmax(185px,1fr))", page)
        self.assertIn(".sg-grid{display:grid;", shared_css)
        self.assertIn("class=\"sg-grid\"", page)
        self.assertIn("preview:model.full_scene||model.artwork||null", page)

    def test_1999_metadata_keeps_both_skin_types_in_single_grid(self):
        payload = json.loads((ROOT / "reverse1999/viewer/manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["unique"])
        self.assertTrue(payload["jukebox"])
        page = (ROOT / "reverse1999/viewer/index.html").read_text(encoding="utf-8")
        self.assertIn("uniqueCatalog", page)
        self.assertIn("jukeboxCatalog", page)
        self.assertIn("galleryRows()", page)
        self.assertIn("full_scene", page)

    def test_future_game_scaffold_uses_same_grid_and_stage(self):
        page = new_game.viewer_html("测试游戏")
        script = new_game.viewer_js("test_game")
        self.assertIn('../../../shared/skin_gallery.css', page)
        self.assertIn('../../../shared/skin_gallery.js', page)
        self.assertIn('id="catalog-view"', page)
        self.assertIn('id="detail-view"', page)
        self.assertIn('SkinGallery.create', script)
        self.assertIn('GalleryViewerBridge', script)

    def test_reverse1999_global_catalog_has_no_duplicate_skin_cards(self):
        catalog = build_catalog(ROOT)
        skin_ids = []
        for item in catalog["assets"]:
            if item["game"] == "reverse1999":
                skin_ids.append(item["source_id"].split(":")[0])
        self.assertEqual(len(skin_ids), len(set(skin_ids)))


if __name__ == "__main__":
    unittest.main()
