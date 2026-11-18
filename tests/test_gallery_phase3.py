"""第三阶段：新游戏注册、通用 manifest、插件脚手架回归测试。"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gallery_core.catalog import GAME_MANIFESTS, build_catalog, verify_catalog
from gallery_core.plugins import load_plugins
from scripts import new_game

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class GamePluginTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        for source in GAME_MANIFESTS.values():
            target = self.root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, target)

    def tearDown(self):
        self.dir.cleanup()

    def register(self, game: str, manifest: dict) -> None:
        viewer = self.root / "games" / game / "viewer"
        viewer.mkdir(parents=True, exist_ok=True)
        (viewer / "index.html").write_text("<!doctype html><title>test</title>", encoding="utf-8")
        write_json(viewer / "manifest.json", manifest)
        write_json(self.root / "gallery/plugins.json", {
            "schema_version": 1, "plugins": [{"id": game, "title": "新游戏"}]
        })

    def test_generic_manifest_registers_game_without_changing_core_adapters(self):
        self.register("future_game", {
            "schema_version": 1,
            "assets": [{
                "id": "skin_01", "title": "Future Skin", "renderer": "spine",
                "roles": {"character": ["../data/skin_01.skel", "../data/skin_01.atlas"]},
                "required_files": ["../data/skin_01.skel", "../data/skin_01.atlas"],
                "preview": "../data/skin_01.png", "tags": ["运动系"],
                "metadata": {"character": "Someone"},
            }],
        })
        catalog = build_catalog(self.root)
        self.assertIn("future_game", catalog["games"])
        self.assertEqual(catalog["game_info"]["future_game"]["viewer"],
                         "games/future_game/viewer/index.html")
        entries = [item for item in catalog["assets"] if item["game"] == "future_game"]
        self.assertEqual(len(entries), 1)
        asset = entries[0]
        self.assertEqual(asset["id"], "future_game:skin_01")
        self.assertEqual(asset["renderer"], "spine")
        self.assertEqual(asset["tags"], ["运动系"])
        self.assertEqual(asset["roles"]["character"], [
            "games/future_game/data/skin_01.skel",
            "games/future_game/data/skin_01.atlas"
        ])
        report = verify_catalog(self.root, catalog)
        selected = next(row for row in report["items"] if row["id"] == asset["id"])
        self.assertEqual(selected["status"], "missing")

    def test_plugin_rejects_escape_paths(self):
        self.register("future_game", {
            "schema_version": 1,
            "assets": [{
                "id": "skin_01", "renderer": "static",
                "preview": "../../../../../outside.png",
                "roles": {}, "required_files": []
            }],
        })
        with self.assertRaises(ValueError):
            build_catalog(self.root)

    def test_plugin_rejects_duplicate_reserved_ids(self):
        self.register("azur_lane", {"schema_version": 1, "assets": []})
        with self.assertRaises(ValueError):
            load_plugins(self.root, reserved=set(GAME_MANIFESTS))

    def test_plugin_rejects_unsafe_source_ids(self):
        self.register("future_game", {
            "schema_version": 1,
            "assets": [{"id": "../broken", "renderer": "static"}],
        })
        with self.assertRaises(ValueError):
            build_catalog(self.root)

    def test_scaffold_dry_run_does_not_touch_worktree(self):
        with patch.object(new_game, "ROOT", self.root):
            paths = new_game.create_game("future_game", "测试新游戏", dry_run=True)
        self.assertIn("games/future_game/viewer/manifest.json", paths)
        self.assertFalse((self.root / "games").exists())
        self.assertFalse((self.root / "gallery/plugins.json").exists())

    def test_scaffold_creates_minimal_valid_generic_plugin(self):
        with patch.object(new_game, "ROOT", self.root):
            paths = new_game.create_game("future_game", "测试新游戏")
        self.assertIn("gallery/plugins.json", paths)
        self.assertTrue((self.root / "games/future_game/viewer/viewer.js").is_file())
        plugins = load_plugins(self.root, reserved=set(GAME_MANIFESTS))
        self.assertEqual([entry["id"] for entry in plugins], ["future_game"])
        catalog = build_catalog(self.root)
        self.assertEqual(catalog["game_info"]["future_game"]["title"], "测试新游戏")
        self.assertEqual(len([row for row in catalog["assets"]
                              if row["game"] == "future_game"]), 0)
        with patch.object(new_game, "ROOT", self.root):
            with self.assertRaises(FileExistsError):
                new_game.create_game("future_game", "重复新增")


if __name__ == "__main__":
    unittest.main()
