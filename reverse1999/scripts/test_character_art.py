#!/usr/bin/env python3
"""佩施塔原画索引的离线回归测试：不访问图源，不修改本地素材。"""
import unittest
from pathlib import Path
from unittest.mock import patch

import character_art


def fake_artwork_exists(filename):
    path = Path(filename)
    # 仅模拟 315902 的背景合成原图和 315901 的独立立绘已经落盘。
    return ((path.parent.name == "315902" and path.name == "scene.webp")
            or (path.parent.name == "315901" and path.name == "artwork.webp"))


class PerchtaArtTest(unittest.TestCase):
    def test_verified_character_ids(self):
        self.assertEqual(sorted(character_art.SKINS), ["315901", "315902"])
        self.assertIn("315902", character_art.VERIFIED_SCENE_ART)

    @patch.object(character_art.artwork, "exists", side_effect=fake_artwork_exists)
    def test_true_scene_and_plain_portrait_are_distinct(self, _):
        scene = character_art.selected_image("315902")
        portrait = character_art.selected_image("315901")
        self.assertEqual(scene[1], "character-scene-portrait")
        self.assertEqual(scene[0].name, "scene.webp")
        self.assertEqual(portrait[1], "character-portrait")
        self.assertEqual(portrait[0].name, "artwork.webp")

    @patch.object(character_art.artwork, "exists", side_effect=fake_artwork_exists)
    def test_attach_same_skin_without_duplicate_card(self, _):
        models = [
            {"id": 315901, "type": "spine", "name": "佩施塔"},
            {"id": 315902, "type": "spine", "name": "佩施塔"},
        ]
        with patch.object(character_art.spine, "skin_entries", return_value={}):
            character_art.attach_artwork(models, [])
        self.assertEqual(len(models), 2)
        self.assertTrue(models[0]["artwork"].endswith("/315901/artwork.webp"))
        self.assertTrue(models[1]["artwork"].endswith("/315902/scene.webp"))

    @patch.object(character_art.artwork, "exists", side_effect=fake_artwork_exists)
    def test_artwork_only_adds_one_viewer_entry(self, _):
        models = [{"id": 315901, "type": "spine", "name": "佩施塔"}]
        with patch.object(character_art.spine, "skin_entries", return_value={}):
            character_art.attach_artwork(models, [])
        second = [row for row in models if row["id"] == 315902]
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["type"], "artwork")
        self.assertEqual(second[0]["artwork_kind"], "character-scene-portrait")


if __name__ == "__main__":
    unittest.main()
