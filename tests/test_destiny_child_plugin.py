"""天命之子插件离线清单检查。"""
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DestinyChildTests(unittest.TestCase):
    def test_registered(self):
        plugins=json.loads((ROOT/"gallery/plugins.json").read_text(encoding="utf-8"))["plugins"]
        self.assertEqual(sum(p["id"]=="destiny_child" for p in plugins),1)
    def test_homepage_has_destination_and_auto_registration(self):
        home = (ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('href="games/destiny_child/viewer/index.html"',home)
        self.assertIn('DESTINY CHILD',home)
        self.assertIn('gallery/plugins.json',home)
        self.assertIn('knownGames.has(id)',home)

    def test_cubism2_runtime_order_and_local_install(self):
        html = (ROOT/"games/destiny_child/viewer/index.html").read_text(encoding="utf-8")
        sdk = 'src="../vendor/live2d.min.js"'
        pixi = 'src="../../../shared/vendor/pixi.min.js"'
        adapter = 'src="../vendor/pixi-live2d-display-cubism2.min.js"'
        self.assertLess(html.index(sdk), html.index(pixi))
        self.assertLess(html.index(pixi), html.index(adapter))
        self.assertNotIn('src="../../../shared/vendor/live2d.min.js"', html)
        downloader = (ROOT/"games/destiny_child/scripts/sync.py").read_text(encoding="utf-8")
        self.assertIn("--runtime-only", downloader)
        self.assertIn("install_runtime(args.force)", downloader)
        self.assertIn("RUNTIME_REVISION", downloader)
        self.assertIn("games/*/vendor/", (ROOT/".gitignore").read_text(encoding="utf-8"))
        viewer = (ROOT/"games/destiny_child/viewer/viewer.js").read_text(encoding="utf-8")
        self.assertIn("typeof globalThis.PIXI?.live2d?.Live2DModel?.from", viewer)

    def test_hidpi_canvas_rendering(self):
        script = (ROOT/"games/destiny_child/viewer/viewer.js").read_text(encoding="utf-8")
        self.assertIn("window.devicePixelRatio", script)
        self.assertIn("resolution:pixelRatio", script)
        self.assertIn("autoDensity:true", script)
        self.assertIn("Math.min(2", script)
        # 纹理源图仅为有限像素，不能通过增大画布缓冲区修改素材本身。
        self.assertIn("app.renderer.resize(", script)

    def test_manifest(self):
        manifest=json.loads((ROOT/"games/destiny_child/viewer/manifest.json").read_text(encoding="utf-8"))
        rows=manifest["assets"]
        self.assertEqual(manifest["schema_version"],1)
        self.assertEqual(len(rows),20)
        self.assertEqual(len({r["id"] for r in rows}),len(rows))
        for row in rows:
            self.assertEqual(row["renderer"],"cubism")
            self.assertEqual(row["roles"]["model"],["../data/"+row["id"]+"/model.json"])
            self.assertTrue(row["metadata"]["thumbnail_url"].endswith("/"+row["id"]+"/icon.png"))
if __name__=="__main__":unittest.main()
