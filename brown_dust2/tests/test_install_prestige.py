"""首批 Prestige Skin 本地单元测试，不需要联网。"""
import importlib.util
import json
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "install_prestige.py"
spec = importlib.util.spec_from_file_location("installer", MODULE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PrestigeInstallTests(unittest.TestCase):
    def test_six_distinct_skins(self):
        skins = json.loads(installer.CATALOG.read_text(encoding="utf-8"))["skins"]
        self.assertEqual(6, len(skins))
        self.assertEqual(6, len({skin["id"] for skin in skins}))

    def test_atlas_pages(self):
        self.assertEqual(["a.png", "b.png"],
                         installer.atlas_pages("a.png\nsize:16,16\nskin\nbounds:0,0,4,4\nb.png\n"))

    def test_only_complete_models_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "model.skel").write_bytes(b"4.1.55\x00test")
            (folder / "model.atlas").write_text("model.png\nsize:16,16\n",encoding="utf-8")
            self.assertIsNone(installer.inspect_model(folder))
            (folder / "model.png").write_bytes(b"image")
            self.assertEqual("4.1",installer.inspect_model(folder)["version"])

    def test_path_and_source_guards(self):
        with self.assertRaises(ValueError):
            installer.request("https://example.com/model.skel")
        with self.assertRaises(ValueError):
            installer.remote_files("spine/../../private")
        with self.assertRaises(ValueError):
            installer.atlas_pages("../evil.png")


    def test_raw_listing_reads_atlas_without_api(self):
        folder = "spine/char/char001197"
        atlas = b"char001197.png\nsize:2048,512\nregion\nbounds:0,0,1,1\n"
        with patch.object(installer, "request", return_value=atlas) as mocked:
            files = installer.remote_files(folder)
        self.assertEqual(1, mocked.call_count)
        self.assertEqual("https://raw.githubusercontent.com/myssal/Brown-Dust-2-Asset/master/"
                         + folder + "/char001197.atlas", mocked.call_args.args[0])
        self.assertEqual(["char001197.skel", "char001197.atlas", "char001197.png"],
                         [Path(item["path"]).name for item in files])
        self.assertEqual(atlas, files[1]["payload"])
        self.assertTrue(all(item["size"] is None for item in (files[0], files[2])))

    def test_yuri_prestige_has_real_interaction_and_backgrounds(self):
        catalog = json.loads(installer.CATALOG.read_text(encoding="utf-8"))
        yuri = next(skin for skin in catalog["skins"]
                    if skin["id"] == "yuri-forever-mascot")
        self.assertEqual("spine/illust/illust_dating/illust_dating21",
                         yuri["roles"]["interaction"])
        self.assertEqual("confirmed", yuri["mapping"])
        self.assertEqual(5, len(yuri["extra_files"]["cutscene"]))

    def test_additional_yuri_backgrounds_use_raw_urls_and_preserve_subfolder(self):
        atlas = b"cutscene_char065193.png\nsize:2048,2048\n"
        folder = "spine/cutscenes/cutscene_char065193"
        extras = ["bg/Char065193_back1-1.png", "bg/Char065193_back2-2.png"]
        with patch.object(installer, "request", return_value=atlas) as mocked:
            files = installer.remote_files(folder, extras=extras)
        self.assertEqual(1, mocked.call_count)
        self.assertEqual(5, len(files))
        paths = [item["path"] for item in files]
        self.assertIn(folder + "/bg/Char065193_back1-1.png", paths)
        self.assertEqual(
            installer.DATA / "yuri-forever-mascot" / "cutscene" /
            "bg" / "Char065193_back1-1.png",
            installer.target_path("yuri-forever-mascot", "cutscene", paths[-2], folder)
        )
        self.assertTrue(all("api.github.com" not in record["url"]
                            for record in files))

    def test_extra_files_cannot_escape_resource_directory(self):
        folder = "spine/cutscenes/cutscene_char065193"
        atlas = b"cutscene_char065193.png\n"
        for path in ("../escape.png", "/escape.png", "other/file.png",
                     "bg/../../escape.png", "bg/unsafe.exe"):
            with self.subTest(path=path), patch.object(
                installer, "request", return_value=atlas
            ), self.assertRaises(ValueError):
                installer.raw_files(folder, extras=[path])

    def test_raw_mode_works_with_expired_api_quota(self):
        atlas = b"cutscene_char001197.png\ncutscene_char001197_2.png\n"
        with patch.object(installer, "request", side_effect=lambda url, binary=False:
                          atlas if "raw.githubusercontent.com" in url else
                          (_ for _ in ()).throw(RuntimeError("API 403 rate limit"))):
            records = installer.remote_files("spine/cutscenes/cutscene_char001197")
        self.assertEqual(4, len(records))

    def test_cached_files_do_not_trigger_download(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cached.png"
            destination.write_bytes(b"previously-downloaded")
            with patch.object(installer, "request", side_effect=AssertionError("downloaded again")):
                status = installer.download_one({"path":"cached.png","size":None,
                                                 "url":"https://raw.githubusercontent.com/x"}, destination)
            self.assertEqual("cached", status)

    def test_raw_download_writes_atomic_content(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "model.png"
            record = {"path":"model.png", "size":None, "url":"https://raw.githubusercontent.com/test"}
            with patch.object(installer, "request", return_value=b"PNG-data") as mocked:
                self.assertEqual("downloaded", installer.download_one(record, destination))
                mocked.assert_called_once()
            self.assertEqual(b"PNG-data", destination.read_bytes())

    def test_nested_api_path_does_not_flatten_backgrounds(self):
        target = installer.target_path(
            "skin", "cutscene", "spine/cutscenes/cutscene_char001197/bg/back.png",
            "spine/cutscenes/cutscene_char001197"
        )
        self.assertEqual(Path("skin/cutscene/bg/back.png"), target.relative_to(installer.DATA))


    def test_full_catalog_has_200_additional_costumes_without_prestige_duplicates(self):
        prestige, other = installer.read_catalog()
        self.assertEqual(6, len(prestige))
        self.assertEqual(200, len(other))
        self.assertEqual(206, len(prestige + other))
        self.assertEqual(206, len({x["id"] for x in prestige + other}))
        self.assertEqual(8, sum(x["tier"] == "Special Skin" for x in other))
        self.assertEqual(15, sum(x["tier"] == "Fated Guest" for x in other))
        self.assertEqual(177, sum(x["tier"] == "Costume" for x in other))
        self.assertEqual(15, sum("interaction" in x["roles"] for x in other))

    def test_collection_selection_and_character_filter(self):
        prestige, other = installer.read_catalog()
        self.assertEqual(6, len(installer.select_skins(prestige, other, "prestige")))
        self.assertEqual(8, len(installer.select_skins(prestige, other, "special")))
        self.assertEqual(15, len(installer.select_skins(prestige, other, "guest")))
        self.assertEqual(21, len(installer.select_skins(prestige, other, "interactive")))
        self.assertEqual(20, len(installer.select_skins(prestige, other, "other", limit=20)))
        target = installer.select_skins(prestige, other, "all",
                                        only="costume-000706")
        self.assertEqual(1, len(target))
        self.assertEqual("Eclipse", target[0]["character_en"])
        group = installer.select_skins(prestige, other, "all", character="Teresse")
        self.assertGreaterEqual(len(group), 2)
        with self.assertRaises(ValueError):
            installer.select_skins(prestige, other, "other", limit=0)

    def test_scheherazade_interaction_directory_added(self):
        prestige, _ = installer.read_catalog()
        item = next(skin for skin in prestige
                    if skin["id"] == "scheherazade-deliberate-ace")
        self.assertEqual("spine/illust/illust_dating/illust_dating18",
                         item["roles"]["interaction"])

    def test_catalog_sync_parser_filters_npc_and_preserves_tiers(self):
        script = MODULE.with_name("sync_costume_catalog.py")
        spec_sync = importlib.util.spec_from_file_location("catalog_sync", script)
        catalog_sync = importlib.util.module_from_spec(spec_sync)
        spec_sync.loader.exec_module(catalog_sync)
        source = (
            '"003392": {\n"charName": "Nebris",\n'
            '"costumeName": "Lucky Bikini",\n"spine": "char003392",\n'
            '"cutscene": "cutscene_char003392",\n"dating": "",\n  },\n'
            '"400001": {\n"charName": "Young Liberta (Npc)",\n'
            '"costumeName": "???",\n"spine": "npc400001",\n  },\n'
            '"000296": {\n"charName": "Justia",\n'
            '"costumeName": "Hot Summer Dream",\n"spine": "char000296",\n  },\n'
            '"003303": {\n"charName": "Nebris",\n'
            '"costumeName": "New Hire",\n"spine": "char003303",\n'
            '"dating": "illust_dating1",\n  },\n'
        )
        prestige, _ = installer.read_catalog()
        result = catalog_sync.parse_index(source, prestige)
        self.assertEqual(["costume-003303", "costume-003392"],
                         [entry["id"] for entry in result])
        self.assertEqual("Special Skin", result[1]["tier"])
        self.assertEqual("Fated Guest", result[0]["tier"])
        self.assertEqual("spine/illust/illust_dating/illust_dating1",
                         result[0]["roles"]["interaction"])


if __name__ == "__main__":
    unittest.main()
