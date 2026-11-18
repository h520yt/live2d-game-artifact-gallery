"""统一资源索引与皮肤映射的离线回归测试（无需下载游戏资源）。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gallery_core.azur_metadata import load_skin_metadata, resolve_skin_entry
from gallery_core.catalog import build_catalog, verify_catalog


def save(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


class AzurMetadataTests(unittest.TestCase):
    def test_preferred_skin_wins_over_npc_shared_painting(self):
        index = {"wuzang_3": [
            {"id": 305102, "painting": "wuzang_3", "name": "Playable"},
            {"id": 900458, "painting": "wuzang_3", "name": "NPC"},
        ]}
        sid, entry = resolve_skin_entry(index, "WUZANG_3")
        self.assertEqual(sid, 305102)
        self.assertEqual(entry["name"], "Playable")

    def test_960xxxx_is_not_excluded_as_npc(self):
        index = {"test": [{"id": 900458}, {"id": 9600032}]}
        self.assertEqual(resolve_skin_entry(index, "test")[0], 9600032)

    def test_ambiguity_never_guesses(self):
        index = {"test": [{"id": 100}, {"id": 200}]}
        with self.assertRaises(ValueError):
            resolve_skin_entry(index, "test")
        self.assertEqual(resolve_skin_entry(index, "test", allow_unknown=True), (-1, {}))

    def test_stale_explicit_mapping_is_an_error(self):
        with self.assertRaises(ValueError):
            resolve_skin_entry({"wuzang_3": [{"id": 900458}]},
                               "wuzang_3", allow_unknown=True)

    def test_metadata_index(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "skin.json"
            save(file, {"1": {"id": 305102, "painting": "WuZang_3"},
                        "2": {"id": 900458, "painting": "wuzang_3"}})
            self.assertEqual(len(load_skin_metadata(file)["wuzang_3"]), 2)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        save(self.root / "azur_lane/viewer/manifest.json", {
            "models": [
                {"name": "skin_1", "path": "../data/models/skin_1/a.model3.json", "id": 123},
                {"name": "skin_1_hx", "path": "../data/models/skin_1_hx/b.model3.json", "id": 123},
            ],
            "characters": [{"asset": "skin_1", "en": "Test skin", "skin": 123,
                            "rep_path": "../data/paintings/a.png",
                            "items": [{"path": "../data/paintings/a.png"}]}],
        })
        save(self.root / "nikke/viewer/nikke_manifest.json", {
            "characters": [{"id": "c001", "name": "Test NIKKE",
                            "dir": "../data/c001", "tags": ["运动系"],
                            "poses": {"fb": {"skel": "c.skel", "atlas": "c.atlas",
                                             "pages": ["c.png"]}}}],
        })
        save(self.root / "reverse1999/viewer/manifest.json", {
            "models": [{"id": 120, "folder": "skin01", "name": "Test",
                        "skin": "skin", "type": "cubism",
                        "path": "../data/models/skin01.model3.json",
                        "artwork": "../data/artwork.webp"}],
            "unique": [{"id": 120}], "jukebox": [],
        })
        save(self.root / "brown_dust2/viewer/manifest.json", {
            "installed": [{"id": "costume-01", "roles": {"interaction": {
                "dir": "../data/costume-01/interaction", "skel": "a.skel",
                "atlas": "a.atlas", "pages": ["a.png", "b.png"]}}}],
        })
        save(self.root / "brown_dust2/costume_catalog.json", {
            "skins": [{"id": "costume-01", "character": "Example", "skin": "Costume"}],
        })
        save(self.root / "brown_dust2/curated_style.json", {
            "styles": [{"id": "costume-01", "tags": ["御姐"]}],
        })

    def tearDown(self):
        self.temp.cleanup()

    def test_all_games_can_be_indexed_without_local_assets(self):
        catalog = build_catalog(self.root)
        self.assertEqual(catalog["schema_version"], 1)
        self.assertEqual(len(catalog["assets"]), 4)
        self.assertEqual(len({r["id"] for r in catalog["assets"]}), 4)
        assets = {x["game"]: x for x in catalog["assets"]}
        self.assertEqual(len(assets["azur_lane"]["roles"]["model"]), 2)
        self.assertEqual(assets["nikke"]["tags"], ["运动系"])
        self.assertEqual(assets["brown_dust2"]["metadata"]["character"], "Example")
        self.assertEqual(assets["reverse1999"]["renderer"], "cubism")
        self.assertTrue(all(x["verification"] == "not_checked" for x in catalog["assets"]))

    def test_verification_reports_missing_instead_of_falsely_ready(self):
        catalog = build_catalog(self.root)
        report = verify_catalog(self.root, catalog)
        self.assertEqual(report["counts"]["missing"], 4)
        nikke = next(x for x in catalog["assets"] if x["game"] == "nikke")
        first = self.root / nikke["required_files"][0]
        first.parent.mkdir(parents=True, exist_ok=True)
        first.write_bytes(b"test")
        report = verify_catalog(self.root, catalog)
        entry = next(x for x in report["items"] if x["id"] == nikke["id"])
        self.assertEqual(entry["status"], "partial")

    def test_external_path_is_rejected(self):
        file = self.root / "reverse1999/viewer/manifest.json"
        save(file, {"models": [{"id": 1, "path": "../../../../outside.model3.json"}]})
        with self.assertRaises(ValueError):
            build_catalog(self.root)

    def test_duplicate_id_is_rejected(self):
        file = self.root / "nikke/viewer/nikke_manifest.json"
        save(file, {"characters": [{"id": "c001"}, {"id": "c001"}]})
        with self.assertRaises(ValueError):
            build_catalog(self.root)


if __name__ == "__main__":
    unittest.main()
