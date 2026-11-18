"""第四阶段：仓库静态验收、摘要一致性、本地 HTTP 路由烟测。"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from gallery_core.catalog import build_catalog, verify_catalog
from gallery_core.doctor import diagnose_gallery

ROOT = Path(__file__).resolve().parents[1]


class CatalogReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build_catalog(ROOT)

    def test_catalog_digest_is_stable_across_regenerations(self):
        new_catalog = build_catalog(ROOT)
        self.assertEqual(self.catalog["catalog_digest"], new_catalog["catalog_digest"])
        self.assertEqual(len(self.catalog["catalog_digest"]), 64)

    def test_report_references_exact_catalog_digest(self):
        report = verify_catalog(ROOT, self.catalog)
        self.assertEqual(report["catalog_digest"], self.catalog["catalog_digest"])
        self.assertIn("entrypoints_present", report["counts"])

    def test_diagnostic_passes_for_checked_in_project_layout(self):
        report = diagnose_gallery(ROOT, self.catalog)
        self.assertEqual(report["error_count"], 0, report["errors"][:12])
        self.assertEqual(report["games"], 4)
        self.assertEqual(set(report["per_game"]), {
            "azur_lane", "nikke", "reverse1999", "brown_dust2"
        })
        self.assertGreater(report["resources"], 0)

    def test_diagnostic_rejects_broken_viewer_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "gallery").mkdir()
            (root / "shared").mkdir()
            (root / "index.html").write_text("", encoding="utf-8")
            (root / "gallery/index.html").write_text("", encoding="utf-8")
            (root / "gallery/app.js").write_text("", encoding="utf-8")
            (root / "shared/gallery_bridge.js").write_text("", encoding="utf-8")
            catalog = {
                "catalog_digest": "test",
                "game_info": {"broken": {"title": "broken",
                                         "viewer": "games/broken/viewer/missing.html"}},
                "assets": [],
            }
            report = diagnose_gallery(root, catalog)
            self.assertGreater(report["error_count"], 0)
            self.assertTrue(any("查看器不存在" in entry for entry in report["errors"]))


class StaticHttpSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """真实启动标准库 HTTP 服务器，仅绑定本机随机端口，禁止外部网络。"""
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

        handler = partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_all_game_viewer_routes_and_bridge_are_served(self):
        paths = [
            "/", "/gallery/", "/gallery/app.js", "/shared/gallery_bridge.js",
            "/azur_lane/viewer/index.html",
            "/nikke/viewer/index.html",
            "/reverse1999/viewer/index.html",
            "/brown_dust2/viewer/index.html",
        ]
        for path in paths:
            with self.subTest(path=path):
                with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=4) as response:
                    self.assertEqual(response.status, 200)
                    self.assertGreater(len(response.read()), 100)

    def test_generated_index_schema_can_be_served(self):
        """模拟生成的统一目录供 HTTP 读取，避免写入工作区产物。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 不向仓库生成临时索引：直接验证生成器返回可 JSON 序列化的结构。
            catalog = build_catalog(ROOT)
            file = Path(tmp) / "catalog.json"
            file.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
            loaded = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["catalog_digest"], catalog["catalog_digest"])
            self.assertGreater(len(loaded["assets"]), 0)


if __name__ == "__main__":
    unittest.main()
