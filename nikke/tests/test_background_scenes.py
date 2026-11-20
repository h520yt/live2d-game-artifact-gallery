"""NIKKE 场景素材导入、背景关联、合成预览的离线回归测试。"""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

NIKKE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NIKKE_DIR / "scripts"))

import config as C
from gen_nikke_manifest import load_backgrounds, load_scene_bindings, scene_variant
from install_backgrounds import load_catalog, canonical_filename, valid_image, scan_source
from render_scene_previews import compose_preview, select_background


def image_bytes(color=(20, 70, 120), size=(640, 360)):
    buff = io.BytesIO()
    Image.new("RGB", size, color).save(buff, "PNG")
    return buff.getvalue()


class BackgroundSceneTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bgdir = self.root / "backgrounds"
        self.catalog = load_catalog()
        self.assertIn("commanderroom.png", self.catalog)

    def test_zip_import_matches_only_canonical_and_valid_images(self):
        archive = self.root / "source.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("subdir/COMMANDERROOM.PNG", image_bytes())
            bundle.writestr("subdir/Ark.png", b"<html>not a PNG</html>")
            bundle.writestr("subdir/unrelated.png", image_bytes())
            bundle.writestr("../../Ark_n.png", image_bytes())
        stats = {}
        scan_source(archive, self.catalog, self.bgdir, report=stats)
        self.assertTrue((self.bgdir / "CommanderRoom.png").is_file())
        self.assertEqual(stats["rejected"], 1)
        self.assertFalse((self.root / "Ark_n.png").exists())
        self.assertFalse((self.bgdir / "unrelated.png").exists())

    def test_plan_does_not_write(self):
        source = self.root / "folder"
        source.mkdir()
        (source / "Ark.png").write_bytes(image_bytes())
        stats = {}
        scan_source(source, self.catalog, self.bgdir, plan=True, report=stats)
        self.assertEqual(stats["planned"], 1)
        self.assertFalse(self.bgdir.exists())

    def test_existing_images_not_overwritten_by_default(self):
        self.bgdir.mkdir()
        first = image_bytes((10, 20, 30))
        (self.bgdir / "Ark.png").write_bytes(first)
        source = self.root / "folder"
        source.mkdir()
        (source / "Ark.png").write_bytes(image_bytes((90, 80, 70)))
        stats = {}
        scan_source(source, self.catalog, self.bgdir, report=stats)
        self.assertEqual(stats["existing"], 1)
        self.assertEqual((self.bgdir / "Ark.png").read_bytes(), first)

    def test_image_validity_and_names(self):
        self.assertTrue(valid_image(image_bytes()))
        self.assertFalse(valid_image(b"fake png"))
        self.assertFalse(valid_image(image_bytes(size=(80, 80))))
        self.assertEqual(canonical_filename("folder/ark.png", self.catalog), "Ark.png")
        self.assertIsNone(canonical_filename("folder/fake.png", self.catalog))
        self.assertEqual(scene_variant("CommanderRoom_n.png"), "夜晚")

    def test_location_category_and_strict_scene_bindings(self):
        self.bgdir.mkdir()
        (self.bgdir / "CommanderRoom.png").write_bytes(image_bytes())
        with patch.object(C, "DATA_DIR", str(self.root)):
            backgrounds = load_backgrounds()
        self.assertEqual(len(backgrounds), 1)
        self.assertEqual(backgrounds[0]["category"], "The Ark")
        self.assertEqual(backgrounds[0]["filename"], "CommanderRoom.png")
        with (self.root / "scene_bindings.json").open("w", encoding="utf-8") as out:
            json.dump({
                "c090": {"background": "CommanderRoom.png", "evidence": "verified in gameplay"},
                "c091": {"background": "CommanderRoom.png"},
                "c092": {"background": "Missing.png", "evidence": "unavailable"}
            }, out)
        with patch.object(C, "BASE", str(self.root)):
            verified = load_scene_bindings(backgrounds)
        self.assertEqual(set(verified), {"c090"})
        self.assertIn("background", verified["c090"])

    def test_image_composition_and_verified_preference(self):
        self.bgdir.mkdir()
        bg = self.bgdir / "CommanderRoom.png"
        bg.write_bytes(image_bytes())
        alt = self.bgdir / "Ark.png"
        alt.write_bytes(image_bytes((50, 60, 90)))
        art = self.root / "character.png"
        person = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
        person.paste((200, 120, 100, 255), (100, 100, 320, 570))
        person.save(art)
        output = self.root / "scene_preview.webp"
        compose_preview(bg, art, output)
        with Image.open(output) as result:
            self.assertEqual(result.size, (720, 1080))
        backgrounds = {"Ark.png": alt, "CommanderRoom.png": bg}
        self.assertEqual(select_background({"scene": {"filename": "Ark.png"}}, backgrounds), alt)
        self.assertEqual(select_background({"scene": None}, backgrounds), bg)


if __name__ == "__main__":
    unittest.main()
