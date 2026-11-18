"""棕色尘埃2统一展示柜封面关联与本地 PNG 缓存测试。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brown_dust2.scripts import sync_thumbnails
from gallery_core.catalog import _brown_dust2, build_catalog

ROOT = Path(__file__).resolve().parents[1]


class BrownDustGalleryThumbnailTests(unittest.TestCase):
    def test_every_installed_skin_maps_to_original_inventory_artwork(self):
        manifest = json.loads((ROOT / "brown_dust2/viewer/manifest.json").read_text(encoding="utf-8"))
        thumbnails = sync_thumbnails.load_mappings()
        catalog = build_catalog(ROOT)
        brown = [row for row in catalog["assets"] if row["game"] == "brown_dust2"]
        installed = {entry["id"] for entry in manifest["installed"]}

        self.assertEqual(len(installed), 54)
        self.assertEqual({row["source_id"] for row in brown}, installed)
        self.assertEqual(set(thumbnails), installed)
        for row in brown:
            with self.subTest(skin=row["source_id"]):
                filename = thumbnails[row["source_id"]]
                expected_url = sync_thumbnails.SOURCE + filename
                self.assertEqual(row["metadata"]["thumbnail_url"], expected_url)
                self.assertTrue(row["preview"] is None or row["preview"].startswith(
                    "brown_dust2/data/_thumbnails/"
                ))
                self.assertEqual(row["renderer"], "spine")

    def test_local_cached_png_becomes_preferred_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            viewer = root / "brown_dust2" / "viewer"
            viewer.mkdir(parents=True)
            manifest = viewer / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            images = {"costume-123456": "illust_inven_char123456_17.png"}
            thumbnail_catalog = root / "brown_dust2/thumbnail_catalog.json"
            thumbnail_catalog.write_text(json.dumps({"images": images}), encoding="utf-8")
            payload = {"installed": [{"id": "costume-123456", "roles": {}}]}

            before = _brown_dust2(root, manifest, payload)[0]
            self.assertIsNone(before["preview"])
            self.assertTrue(before["metadata"]["thumbnail_url"].startswith("https://"))

            local = root / "brown_dust2/data/_thumbnails/costume-123456.png"
            local.parent.mkdir(parents=True)
            local.write_bytes(sync_thumbnails.PNG_SIGNATURE + b"safe-test-payload")
            after = _brown_dust2(root, manifest, payload)[0]
            self.assertEqual(after["preview"], "brown_dust2/data/_thumbnails/costume-123456.png")
            self.assertEqual(before["required_files"], after["required_files"])

    def test_bad_thumbnail_index_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            viewer = root / "brown_dust2/viewer"
            viewer.mkdir(parents=True)
            manifest = viewer / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            path = root / "brown_dust2/thumbnail_catalog.json"
            path.write_text(json.dumps({"images": {
                "costume-123456": "../../private.png"
            }}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "封面映射非法"):
                _brown_dust2(root, manifest, {
                    "installed": [{"id": "costume-123456", "roles": {}}]
                })

    def test_validated_png_cache_ignores_html_and_empty_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "thumbnail.png"
            self.assertFalse(sync_thumbnails.is_valid_png(file))
            file.write_bytes(b"<html>error</html>")
            self.assertFalse(sync_thumbnails.is_valid_png(file))
            file.write_bytes(sync_thumbnails.PNG_SIGNATURE + b"valid-contents")
            self.assertTrue(sync_thumbnails.is_valid_png(file))

    def test_download_uses_atomic_cache_and_skips_existing_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = sync_thumbnails.PNG_SIGNATURE + b"some-image-bytes"
            with patch.object(sync_thumbnails, "OUTPUT", Path(tmp)), \
                 patch.object(sync_thumbnails, "fetch_image", return_value=payload) as fetch:
                result = sync_thumbnails.install_one(
                    "costume-123456", "illust_inven_char123456_17.png"
                )
                self.assertEqual(result, "downloaded")
                self.assertTrue(sync_thumbnails.is_valid_png(
                    Path(tmp) / "costume-123456.png"
                ))
                result = sync_thumbnails.install_one(
                    "costume-123456", "illust_inven_char123456_17.png"
                )
                self.assertEqual(result, "cached")
                fetch.assert_called_once()

    def test_gallery_frontend_supports_only_bd2_allowlisted_remote_image(self):
        js = (ROOT / "gallery/app.js").read_text(encoding="utf-8")
        self.assertIn("safeBd2ThumbnailUrl", js)
        self.assertIn("raw.githubusercontent.com/myssal/Brown-Dust-2-Asset/", js)
        self.assertIn("picture.referrerPolicy", js)
        self.assertIn("sourceIndex < sources.length", js)


if __name__ == "__main__":
    unittest.main()
