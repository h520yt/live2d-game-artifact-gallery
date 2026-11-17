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


    def test_curated_catalog_only_exposes_special_and_style_matches(self):
        prestige, chosen = installer.read_catalog()
        self.assertEqual(6, len(prestige))
        self.assertEqual(48, len(chosen))
        self.assertEqual(54, len(prestige + chosen))
        self.assertEqual(54, len({item["id"] for item in prestige + chosen}))
        self.assertEqual(9, sum(item["tier"] == "Special Skin" for item in chosen))
        self.assertEqual(32, sum(bool(item.get("preference_tags")) for item in chosen))
        self.assertEqual(16, sum(item["tier"] == "Fated Guest" for item in chosen))
        self.assertEqual(16, sum("interaction" in item["roles"] for item in chosen))

        full_catalog = json.loads(installer.ALL_COSTUMES.read_text(encoding="utf-8"))
        self.assertEqual(200, len(full_catalog["skins"]))
        self.assertNotIn("costume-100501", {item["id"] for item in chosen})
        self.assertIn("costume-000706", {item["id"] for item in chosen})

    def test_only_curated_collections_are_downloadable(self):
        prestige, chosen = installer.read_catalog()
        select = installer.select_skins
        self.assertEqual(6, len(select(prestige, chosen, "prestige")))
        self.assertEqual(15, len(select(prestige, chosen, "special")))
        self.assertEqual(32, len(select(prestige, chosen, "style")))
        self.assertEqual(32, len(select(prestige, chosen, "other")))
        self.assertEqual(8, len(select(prestige, chosen, "interaction-batch")))
        self.assertEqual(16, len(select(prestige, chosen, "guest")))
        self.assertEqual(22, len(select(prestige, chosen, "interactive")))
        self.assertEqual(54, len(select(prestige, chosen, "all")))
        self.assertEqual(3, len(select(prestige, chosen, "all", limit=3)))
        self.assertEqual(3, len(select(prestige, chosen, "all", limit=3, offset=3)))
        selected = select(prestige, chosen, "all", only="costume-000706")
        self.assertEqual(1, len(selected))
        self.assertEqual("Eclipse", selected[0]["character_en"])
        self.assertTrue(select(prestige, chosen, "all", character="Celia"))
        with self.assertRaises(ValueError):
            select(prestige, chosen, "all", only="costume-100501")
        with self.assertRaises(ValueError):
            select(prestige, chosen, "all", limit=0)
        with self.assertRaises(ValueError):
            select(prestige, chosen, "all", offset=-1)

    def test_style_tags_and_sources_have_valid_catalog_entries(self):
        full = json.loads(installer.ALL_COSTUMES.read_text(encoding="utf-8"))
        selections = json.loads(installer.CURATED_STYLE.read_text(encoding="utf-8"))
        all_ids = {item["id"] for item in full["skins"]}
        styles = selections["styles"]
        self.assertEqual(12, len(styles))
        self.assertEqual(len(styles), len({item["id"] for item in styles}))
        for item in styles:
            self.assertIn(item["id"], all_ids)
            self.assertTrue(item["tags"])
            self.assertTrue(item["reason"])
            self.assertTrue(item["evidence"].startswith("https://"))
        _, chosen = installer.read_catalog()
        eclipse = next(item for item in chosen if item["id"] == "costume-000706")
        self.assertIn("黑丝/网袜", eclipse["preference_tags"])
        self.assertEqual("Fated Guest", eclipse["tier"])

    def test_third_batch_contains_20_unique_styles_and_aquila_two_interactions(self):
        prestige, chosen = installer.read_catalog()
        batch = installer.select_skins(prestige, chosen, "batch-20")
        self.assertEqual(20, len(batch))
        self.assertEqual(20, len({item["id"] for item in batch}))
        self.assertEqual(1, sum("interaction" in item["roles"] for item in batch))
        aquila = next(item for item in batch if item["id"] == "costume-067902")
        self.assertEqual("Fated Guest", aquila["tier"])
        self.assertEqual("spine/illust/illust_dating/illust_dating22_1",
                         aquila["roles"]["interaction"])
        self.assertEqual("spine/illust/illust_dating/illust_dating22_2",
                         aquila["roles"]["interaction2"])
        liatris = next(item for item in batch if item["id"] == "costume-001297")
        self.assertEqual("Special Skin", liatris["tier"])
        for item in batch:
            with self.subTest(skin=item["id"]):
                self.assertTrue(item["preference_tags"])
                self.assertEqual("interaction-03", item["interaction_batch"])
                self.assertIn("character", item["roles"])
                self.assertIn("cutscene", item["roles"])

    def test_aquila_alternate_interaction_paths_and_manifest(self):
        folder1 = "spine/illust/illust_dating/illust_dating22_1"
        folder2 = "spine/illust/illust_dating/illust_dating22_2"
        installer.validate_folder(folder1)
        installer.validate_folder(folder2)
        installer.validate_folder("spine/illust/illust_dating/illust_dating22")
        self.assertEqual(
            installer.DATA / "costume-067902" / "interaction2" /
            "illust_dating22_2.skel",
            installer.target_path("costume-067902", "interaction2",
                                  folder2 + "/illust_dating22_2.skel", folder2))
        aquila = next(s for s in installer.read_catalog()[1]
                      if s["id"] == "costume-067902")
        example = {"skel":"sample.skel", "atlas":"sample.atlas",
                   "pages":["sample.png"], "version":"4.1"}
        with patch.object(installer,"inspect_model",return_value=example):
            manifest = installer.build_manifest([aquila])
        self.assertEqual({"character","cutscene","interaction","interaction2"},
                         set(manifest["installed"][0]["roles"]))

    def test_interaction_only_downloads_both_aquila_scenes(self):
        from contextlib import redirect_stdout
        from io import StringIO
        folder="spine/illust/illust_dating/"
        with patch.object(installer, "remote_files", return_value=[
            {"path":folder + "sample.skel","size":1,
             "url":"https://raw.githubusercontent.com/mock"}
        ]) as mocked:
            with redirect_stdout(StringIO()):
                code=installer.main(["--plan","--only","costume-067902",
                                     "--interaction-only"])
        self.assertEqual(0,code)
        self.assertEqual([
            "spine/illust/illust_dating/illust_dating22_1",
            "spine/illust/illust_dating/illust_dating22_2",
        ],[call.args[0] for call in mocked.call_args_list])

    def test_next_eight_interactions_are_verified_and_do_not_require_char_or_skill(self):
        _, chosen = installer.read_catalog()
        batch = [item for item in chosen
                 if item.get("interaction_batch") == "interaction-02"]
        self.assertEqual(8, len(batch))
        expected = {
            "costume-003203": "illust_dating3",
            "costume-067004": "illust_dating15",
            "costume-066403": "illust_dating10",
            "costume-060802": "illust_dating5",
            "costume-067104": "illust_dating19",
            "costume-001106": "illust_dating4",
            "costume-004202": "illust_dating17",
            "costume-004102": "illust_dating13",
        }
        self.assertEqual(set(expected), {item["id"] for item in batch})
        for item in batch:
            with self.subTest(skin=item["id"]):
                self.assertTrue(item["interaction_only"])
                self.assertEqual({"interaction"}, set(item["roles"]))
                self.assertEqual(
                    "spine/illust/illust_dating/" + expected[item["id"]],
                    item["roles"]["interaction"])
                self.assertGreaterEqual(item["source"]["atlas_pages"], 6)
        all_interactions = [item["roles"]["interaction"]
                            for item in chosen if "interaction" in item["roles"]]
        self.assertEqual(len(all_interactions), len(set(all_interactions)))

    def test_interaction_batch_plan_does_not_request_other_roles(self):
        from contextlib import redirect_stdout
        from io import StringIO
        prestige, chosen = installer.read_catalog()
        batch = installer.select_skins(prestige, chosen, "interaction-batch")
        with patch.object(installer, "remote_files",
                          return_value=[{"path":"spine/illust/illust_dating/illust_dating3/test.skel",
                                         "size":100,
                                         "url":"https://raw.githubusercontent.com/mock"}]) as mocked:
            with redirect_stdout(StringIO()):
                result = installer.main(["--plan", "--collection", "interaction-batch"])
        self.assertEqual(0, result)
        self.assertEqual(8, mocked.call_count)
        called_folders = [call.args[0] for call in mocked.call_args_list]
        self.assertEqual({item["roles"]["interaction"] for item in batch},
                         set(called_folders))

    def test_batch_only_manifest_and_interaction_state(self):
        batch = json.loads(installer.INTERACTION_BATCH.read_text(encoding="utf-8"))["skins"]
        first = batch[0]
        example = {"skel":"illust_dating3.skel","atlas":"illust_dating3.atlas",
                   "pages":["illust_dating3.png"],"version":"4.1"}
        with patch.object(installer, "inspect_model", return_value=example):
            manifest = installer.build_manifest([first])
            self.assertEqual(1, len(manifest["installed"]))
            self.assertEqual({"interaction"},
                             set(manifest["installed"][0]["roles"]))
            self.assertEqual("已安装独立互动",
                             installer.interaction_state(first))
        with patch.object(installer, "inspect_model", return_value=None):
            self.assertEqual("有独立互动，待本地下载",
                             installer.interaction_state(first))

    def test_four_added_fated_guest_interactions_have_unique_real_mappings(self):
        _, curated = installer.read_catalog()
        expected = {
            "costume-001006": "illust_dating8",
            "costume-067603": "illust_dating6",
            "costume-061302": "illust_dating20",
            "costume-003604": "illust_dating16",
        }
        for skin_id, folder in expected.items():
            with self.subTest(skin=skin_id):
                skin = next(item for item in curated if item["id"] == skin_id)
                self.assertEqual(
                    "spine/illust/illust_dating/" + folder,
                    skin["roles"]["interaction"])
                self.assertTrue(skin.get("preference_tags"))
                self.assertEqual("Fated Guest", skin["tier"])
        seen = [skin["roles"]["interaction"] for skin in curated
                if "interaction" in skin["roles"]]
        self.assertEqual(len(seen), len(set(seen)))

    def test_official_special_skin_is_distinguished_from_missing_download(self):
        _, curated = installer.read_catalog()
        special = next(item for item in curated if item["tier"] == "Special Skin")
        self.assertNotIn("interaction", special["roles"])
        self.assertEqual("官方 Special Skin 不含独立互动",
                         installer.interaction_state(special))
        fated = next(item for item in curated if item["id"] == "costume-001006")
        with patch.object(installer, "inspect_model", return_value=None):
            self.assertEqual("有独立互动，待本地下载",
                             installer.interaction_state(fated))
        with patch.object(installer, "inspect_model", return_value={"skel":"model.skel"}):
            self.assertEqual("已安装独立互动", installer.interaction_state(fated))
        celia = next(item for item in curated if item["id"] == "costume-060403")
        self.assertEqual("尚未发现该服装的独立互动资源",
                         installer.interaction_state(celia))

    def test_role_interaction_limits_plan_to_interaction_only(self):
        from contextlib import redirect_stdout
        from io import StringIO
        _, curated = installer.read_catalog()
        skin = next(item for item in curated if item["id"] == "costume-001006")
        fake = [{"path":skin["roles"]["interaction"] + "/test.skel",
                 "size":100, "url":"https://raw.githubusercontent.com/test"}]
        out = StringIO()
        with patch.object(installer, "remote_files", return_value=fake) as mocked:
            with redirect_stdout(out):
                code = installer.main(
                    ["--plan", "--only", skin["id"], "--role", "interaction"])
        self.assertEqual(0, code)
        mocked.assert_called_once_with(skin["roles"]["interaction"], "raw", [])

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
