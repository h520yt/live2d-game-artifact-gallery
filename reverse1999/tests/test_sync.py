"""无需网络的本地回归测试。运行：python -m unittest discover -s reverse1999/tests -v"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SYNC_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync.py"
spec = importlib.util.spec_from_file_location("reverse1999_sync", SYNC_PATH)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patchers = [mock.patch.object(sync, "ROOT", self.root),
                         mock.patch.object(sync, "DATA_DIR", self.root / "data" / "models"),
                         mock.patch.object(sync, "CONFIG_DIR", self.root / "config"),
                         mock.patch.object(sync, "CACHE", self.root / "config" / "ArcanistMap.json"),
                         mock.patch.object(sync, "MANIFEST", self.root / "viewer" / "manifest.json")]
        for patcher in self.patchers:
            patcher.start()
        self.mapping = [{"name":"槲寄生","nameEng":"Druvis III","live2d":[
            {"id":300301,"des":"初始皮肤","cubism":"https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/live2d/roles/300301_hujisheng"},
            {"id":300502,"des":"无资源","cubism":"https://github.com/myssal/Reverse-1999-CN-Asset/tree/master/live2d/roles/"},
        ]}]

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def test_mapping_filters_empty_urls(self):
        got=sync.mapped_entries(self.mapping)
        self.assertIn("300301",got)
        self.assertNotIn("300502",got)
        self.assertEqual(got["300301"]["name"],"槲寄生")

    def test_reject_traversal(self):
        with self.assertRaises(ValueError):
            sync.safe_model_dir("../../bad")

    def test_manifest_valid_local_model_only(self):
        folder=sync.DATA_DIR / "300301_hujisheng"
        (folder/"textures").mkdir(parents=True)
        (folder/"300301_hujisheng.moc3").write_bytes(b"fixture")
        (folder/"textures"/"300301_hujisheng.png").write_bytes(b"fixture")
        data={"FileReferences":{"Moc":"300301_hujisheng.moc3","Textures":["textures/300301_hujisheng.png"]}}
        (folder/"300301_hujisheng.model3.json").write_text(json.dumps(data),encoding="utf-8")
        sync.generate_manifest(self.mapping)
        result=json.loads(sync.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(result["models"]),1)
        self.assertEqual(result["models"][0]["name"],"槲寄生")
        self.assertEqual(result["models"][0]["path"],"../data/models/300301_hujisheng/300301_hujisheng.model3.json")


if __name__=="__main__":
    unittest.main()
