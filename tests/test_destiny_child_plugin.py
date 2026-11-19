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
