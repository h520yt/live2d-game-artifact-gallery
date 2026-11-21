"""天命之子插件离线清单检查。"""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from games.destiny_child.scripts import sync

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_IDS = {
    "c001_14", "c001_16", "c002_01", "c049_10", "c124_10", "c167_11", "c247_02",
    "c287_02", "c294_02", "c296_02", "c311_02", "c344_10", "c363_02", "c370_02",
    "c371_02", "c374_02", "c394_02", "c417_02", "c430_02", "c440_02",
}

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
        self.assertLessEqual(ORIGINAL_IDS, {row["id"] for row in rows})
        self.assertEqual(len({r["id"] for r in rows}),len(rows))
        for row in rows:
            self.assertEqual(row["renderer"],"cubism")
            self.assertEqual(row["roles"]["model"],["../data/"+row["id"]+"/model.json"])
            self.assertTrue(row["metadata"]["thumbnail_url"].endswith("/"+row["id"]+"/icon.png"))
            if row["id"] not in ORIGINAL_IDS:
                metadata = row["metadata"]
                self.assertEqual(metadata["source"]["id"], row["id"])
                self.assertEqual(metadata["source"]["revision"], sync.SOURCE_COMMIT)
                dependencies = {Path(file).name for file in row["required_files"] + row["optional_files"]}
                self.assertEqual(set(metadata["file_sha256"]), dependencies)
                for digest in metadata["file_sha256"].values():
                    self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_install_resumes_only_missing_or_invalid_dependencies(self):
        png = io.BytesIO()
        Image.new("RGBA", (16, 16)).save(png, format="PNG")
        files = {
            "model.json": json.dumps({
                "model": "model.moc",
                "textures": ["texture_00.png"],
                "motions": {"idle": [{"file": "idle.mtn"}]},
            }).encode(),
            "model.moc": b"moc\x0boriginal",
            "texture_00.png": png.getvalue(),
            "icon.png": png.getvalue(),
            "idle.mtn": b"# Live2D Animator Motion Data\nPARAM=0,1,0",
        }
        row = {
            "id": "c001_01",
            "metadata": {
                "file_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
            },
        }
        with tempfile.TemporaryDirectory() as temporary, patch.object(sync, "GAME", Path(temporary)):
            folder = Path(temporary) / "data" / row["id"]
            folder.mkdir(parents=True)
            (folder / "idle.mtn").write_bytes(files["idle.mtn"][:-2])
            for name in ("model.json", "model.moc", "texture_00.png"):
                (folder / name).write_bytes(files[name])
            with patch.object(sync, "download", side_effect=lambda url, name, digest: files[name]) as download:
                sync.install(row, False)
                self.assertEqual([call.args[1] for call in download.call_args_list], ["icon.png", "idle.mtn"])
                download.reset_mock()
                sync.install(row, False)
                download.assert_not_called()
            for name, data in files.items():
                self.assertEqual((folder / name).read_bytes(), data)

if __name__=="__main__":unittest.main()
