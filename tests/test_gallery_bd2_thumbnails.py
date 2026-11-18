"""棕色尘埃2封面一对一映射、离线缓存与安全回退测试。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brown_dust2.scripts import download_thumbnails
from gallery_core.catalog import _brown_dust2, build_catalog

ROOT = Path(__file__).resolve().parents[1]


def sample_png() -> bytes:
    """构造足够让原有缓存验证器识别的 PNG 头，不访问远端素材。"""
    return (download_thumbnails.PNG_SIGNATURE + b"\x00" * 8
            + (256).to_bytes(4, "big") + (256).to_bytes(4, "big") + b"offline-test")


class FakeResponse:
    """只模拟 urllib 返回的数据与关闭行为。"""
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit: int) -> bytes:
        return self.payload[:limit]


class BrownDustGalleryThumbnailTests(unittest.TestCase):
    def test_all_54_installed_skins_have_inventory_artwork_mapping(self):
        installed_data = json.loads(
            (ROOT / "brown_dust2/viewer/manifest.json").read_text(encoding="utf-8")
        )
        images = download_thumbnails.read_catalog()
        catalog = build_catalog(ROOT)
        brown = [item for item in catalog["assets"] if item["game"] == "brown_dust2"]
        installed = {item["id"] for item in installed_data["installed"]}

        self.assertEqual(len(installed), 54)
        self.assertEqual(len(brown), 54)
        self.assertEqual(set(images), installed)
        self.assertEqual({row["source_id"] for row in brown}, installed)
        for row in brown:
            with self.subTest(skin=row["source_id"]):
                name = images[row["source_id"]]
                self.assertEqual(
                    row["metadata"]["thumbnail_url"], download_thumbnails.CDN + name
                )
                self.assertTrue(row["preview"] is None or row["preview"].startswith(
                    "brown_dust2/data/_thumbnails/"
                ))
                self.assertEqual(row["renderer"], "spine")

    def test_cached_thumbnail_becomes_local_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "brown_dust2/viewer/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}", encoding="utf-8")
            (root / "brown_dust2/thumbnail_catalog.json").write_text(
                json.dumps({"images": {
                    "costume-123456": "illust_inven_char123456_17.png"
                }}), encoding="utf-8"
            )
            installed = {"installed": [{"id": "costume-123456", "roles": {}}]}
            before = _brown_dust2(root, manifest, installed)[0]
            self.assertIsNone(before["preview"])
            self.assertIn("illust_inven_char123456_17.png",
                          before["metadata"]["thumbnail_url"])

            local = root / "brown_dust2/data/_thumbnails/costume-123456.png"
            local.parent.mkdir(parents=True)
            local.write_bytes(sample_png())
            after = _brown_dust2(root, manifest, installed)[0]
            self.assertEqual(after["preview"],
                             "brown_dust2/data/_thumbnails/costume-123456.png")
            self.assertEqual(before["required_files"], after["required_files"])

    def test_invalid_thumbnail_filename_cannot_be_used(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "brown_dust2/viewer/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}", encoding="utf-8")
            (root / "brown_dust2/thumbnail_catalog.json").write_text(
                json.dumps({"images": {"costume-123456": "../../secret.png"}}),
                encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "封面映射非法"):
                _brown_dust2(root, manifest, {
                    "installed": [{"id": "costume-123456", "roles": {}}]
                })

    def test_cache_download_reuses_existing_verified_png(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = sample_png()
            calls = []
            def fake_open(request, timeout):
                calls.append((request.full_url, timeout))
                return FakeResponse(payload)

            result, path = download_thumbnails.download_one(
                "costume-123456", "illust_inven_char123456_17.png",
                target=root, opener=fake_open
            )
            self.assertEqual(result, "downloaded")
            self.assertEqual(path.read_bytes(), payload)
            result, _ = download_thumbnails.download_one(
                "costume-123456", "illust_inven_char123456_17.png",
                target=root, opener=fake_open
            )
            self.assertEqual(result, "cached")
            self.assertEqual(len(calls), 1)

    def test_frontend_only_accepts_allowlisted_bd2_source(self):
        js = (ROOT / "gallery/app.js").read_text(encoding="utf-8")
        self.assertIn("safeBd2ThumbnailUrl", js)
        self.assertIn("raw.githubusercontent.com/myssal/Brown-Dust-2-Asset/", js)
        self.assertIn("picture.referrerPolicy", js)
        self.assertIn("sourceIndex < sources.length", js)


if __name__ == "__main__":
    unittest.main()
