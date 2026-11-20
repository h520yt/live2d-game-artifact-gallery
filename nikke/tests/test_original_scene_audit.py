"""只记录真实 Lobby/Burst 场景候选名，禁止在扫描阶段伪造皮肤配对。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_original_scenes import (
    classify_candidate_name, hinted_character_id, record_asset, scan_extracted_directory,
)


class OriginalSceneAuditTest(unittest.TestCase):
    def test_name_classification_is_conservative(self):
        self.assertEqual(classify_candidate_name("Lobby_WallPaper_c090_02"), "lobby")
        self.assertEqual(classify_candidate_name("c123_01_skillcut"), "burst")
        self.assertEqual(classify_candidate_name("EventScene_Summer"), "event")
        self.assertIsNone(classify_candidate_name("CommanderRoom.png"))
        self.assertIsNone(classify_candidate_name("c090_02_00"))

    def test_hinted_id_is_not_verification(self):
        self.assertEqual(hinted_character_id("lobby_c090_02_background"), "c090_02")
        self.assertIsNone(hinted_character_id("unrelated_scene"))
        result = {}
        record_asset(result, "lobby_c090_02_background", "Texture2D", "00/abc")
        self.assertEqual(len(result), 1)
        entry = next(iter(result.values()))
        self.assertFalse(entry["verified"])
        self.assertEqual(entry["character_id_hint"], "c090_02")
        self.assertNotIn("background", entry)

    def test_only_named_scenes_from_extracted_data_are_catalogued(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "EventScene_Test.skel").write_bytes(b"spine")
            (root / "c090_02_00.atlas").write_text("atlas", encoding="utf-8")
            (root / "Lobby_c090_02.atlas").write_text("atlas", encoding="utf-8")
            records = {}
            counts = scan_extracted_directory(root, records)
            self.assertEqual(counts["files"], 3)
            self.assertEqual(len(records), 2)
            self.assertTrue(all(not entry["verified"] for entry in records.values()))


if __name__ == "__main__":
    unittest.main()
