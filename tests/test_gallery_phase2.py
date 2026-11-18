"""第二阶段：批次配置、跨游戏共享缓存校验与静态界面完整性测试。"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gallery_core.collections import load_skin_batch, load_batch_candidates
from gallery_core.storage import atomic_write_bytes, file_ready

ROOT = Path(__file__).resolve().parents[1]
COLLECTIONS = ROOT / "azur_lane/config/curated_collections.json"


class PhaseTwoCollectionTests(unittest.TestCase):
    def test_historical_collections_keep_ids_and_order(self):
        expected = {
            "batch2": (10, "guanghui_9", "aisaikesi_10"),
            "batch3": (12, "gaoxiong_7", "aersasi_3"),
            "batch4": (12, "feiteliedadi_4", "qiye_10"),
        }
        for key, (count, first, last) in expected.items():
            with self.subTest(batch=key):
                entries = load_skin_batch(COLLECTIONS, key)
                self.assertEqual(len(entries), count)
                self.assertEqual(entries[0]["asset"], first)
                self.assertEqual(entries[-1]["asset"], last)
                self.assertTrue(all(type(entry["skin_id"]) is int for entry in entries))
        self.assertEqual(
            next(x for x in load_skin_batch(COLLECTIONS, "batch4")
                 if x["asset"] == "jinluhao_3")["skin_id"],
            9600032,
        )
        self.assertEqual(
            next(x for x in load_skin_batch(COLLECTIONS, "batch2")
                 if x["asset"] == "guanghui_9")["category"],
            "live2d_plus",
        )

    def test_unified_index_marks_azur_footwear_as_candidates(self):
        from gallery_core.catalog import build_catalog

        catalog = build_catalog(ROOT)
        indexed = {x["source_id"]: x for x in catalog["assets"]
                   if x["game"] == "azur_lane"}
        self.assertIn("ougen_5", indexed)
        entry = indexed["ougen_5"]
        self.assertIn("鞋履候选", entry["tags"])
        self.assertIn("候选：长靴", entry["tags"])
        self.assertIn("batch5", entry["metadata"]["batches"])
        self.assertEqual(entry["verification"], "not_checked")

    def test_all_five_batches_reuse_json_without_duplicate_items(self):
        config = json.loads(COLLECTIONS.read_text(encoding="utf-8"))
        self.assertEqual(set(config["batches"]), {
            "batch2", "batch3", "batch4", "batch5", "batch6"
        })
        for key, expected in (("batch5", 20), ("batch6", 20)):
            with self.subTest(batch=key):
                values = load_batch_candidates(COLLECTIONS, key, ("asset",))
                self.assertEqual(len(values), expected)
                self.assertEqual(len(set(values)), expected)

    def test_rejects_invalid_or_duplicate_fixed_skin_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "batches.json"
            base = {"character": "A", "title": "B", "asset": "a_1",
                    "skin_id": 1001, "category": "live2d"}
            for value in (0, "1001", -1, True):
                with self.subTest(value=value):
                    path.write_text(json.dumps({"schema_version": 1, "batches": {
                        "batch2": {"items": [{**base, "skin_id": value}]}}}),
                        encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_skin_batch(path, "batch2")
            path.write_text(json.dumps({"schema_version": 1, "batches": {
                "batch2": {"items": [base, {**base, "asset": "A_1"}]}}}),
                encoding="utf-8")
            with self.assertRaises(ValueError):
                load_skin_batch(path, "batch2")


class SharedStorageTests(unittest.TestCase):
    def test_atomic_write_and_streaming_md5(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sub" / "asset.bin"
            payload = b"example-test-payload"
            checksum = hashlib.md5(payload).hexdigest()
            self.assertFalse(file_ready(path))
            atomic_write_bytes(path, payload, expected_size=len(payload),
                               expected_md5=checksum)
            self.assertEqual(path.read_bytes(), payload)
            self.assertTrue(file_ready(path, expected_size=len(payload),
                                       expected_md5=checksum))
            self.assertFalse(file_ready(path, expected_md5="0" * 32))
            self.assertFalse(file_ready(path, expected_size=len(payload) + 1))

    def test_failed_write_does_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.atlas"
            path.write_bytes(b"older-safe-bytes")
            with self.assertRaises(ValueError):
                atomic_write_bytes(path, b"invalid", expected_size=1234)
            self.assertEqual(path.read_bytes(), b"older-safe-bytes")
            with self.assertRaises(ValueError):
                atomic_write_bytes(path, b"new", expected_md5="0" * 32)
            self.assertEqual(path.read_bytes(), b"older-safe-bytes")

    def test_empty_file_never_counts_as_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.png"
            path.touch()
            self.assertFalse(file_ready(path))
            with self.assertRaises(ValueError):
                atomic_write_bytes(path, b"")


class UnifiedBrowserFilesTests(unittest.TestCase):
    def test_static_browser_entry_is_locally_hosted(self):
        html = (ROOT / "gallery/index.html").read_text(encoding="utf-8")
        script = (ROOT / "gallery/app.js").read_text(encoding="utf-8")
        css = ROOT / "gallery/styles.css"
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('src="app.js"', html)
        self.assertIn('href="styles.css"', html)
        self.assertIn('href="gallery/index.html"', home)
        self.assertTrue(css.is_file())
        for game in ("azur_lane", "nikke", "reverse1999", "brown_dust2"):
            self.assertIn("../" + game + "/viewer/index.html", script)
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)


if __name__ == "__main__":
    unittest.main()
