"""NIKKE 下载恢复与 manifest 完整性检查（离线单元测试）。"""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


NIKKE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NIKKE_DIR / "scripts"))

import config as C
from fetch_nikke import fetch_pose, get_local_pose
from gen_nikke_manifest import find_pose


class FakeResponse:
    def __init__(self, status_code, content=b"", content_type="application/octet-stream"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def iter_content(self, size):
        if self.content:
            yield self.content


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.responses.get(url, FakeResponse(404))


class DownloadRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(C, "DATA_DIR", str(self.root)))
        self.stack.enter_context(patch.object(C, "CDN_BASE", "https://primary.test/l2d"))
        self.stack.enter_context(patch.object(C, "CDN_MIRROR", "https://mirror.test/l2d"))
        self.cid = "c290_01"
        self.prefix = self.cid + "_00"
        self.base = "https://mirror.test/l2d/" + self.cid + "/"

    def test_main_cdn_fails_then_mirror_succeeds(self):
        data = {
            self.base + self.prefix + ".atlas": FakeResponse(
                200, (self.cid + ".png\nsize: 512,512\n").encode()
            ),
            self.base + self.prefix + ".skel": FakeResponse(200, b"4.1.0 skeleton"),
            self.base + self.cid + ".png": FakeResponse(200, b"image-binary-payload"),
        }
        session = FakeSession(data)
        info = fetch_pose(session, self.cid, "fb")
        self.assertIsNotNone(info)
        self.assertEqual(info["pages"], [self.cid + ".png"])
        self.assertIn("https://primary.test/l2d/" + self.cid + "/" + self.prefix + ".atlas", session.calls)
        self.assertIn(self.base + self.prefix + ".atlas", session.calls)
        self.assertIsNotNone(get_local_pose(self.cid, "fb"))
        self.assertIsNotNone(find_pose(str(self.root / self.cid), self.cid, "fb"))

    def test_missing_texture_is_not_success(self):
        data = {
            self.base + self.prefix + ".atlas": FakeResponse(
                200, (self.cid + ".png\nsize: 512,512\n").encode()
            ),
            self.base + self.prefix + ".skel": FakeResponse(200, b"4.1.0 skeleton"),
        }
        session = FakeSession(data)
        self.assertIsNone(fetch_pose(session, self.cid, "fb"))
        self.assertIsNone(get_local_pose(self.cid, "fb"))
        self.assertIsNone(find_pose(str(self.root / self.cid), self.cid, "fb"))

    def test_recovery_from_incomplete_download(self):
        # 已有 skel/atlas 但缺 PNG，重新执行 fetch_pose 应只补缺图。
        folder = self.root / self.cid
        folder.mkdir()
        (folder / (self.prefix + ".skel")).write_bytes(b"4.1.0 skeleton")
        (folder / (self.prefix + ".atlas")).write_text(self.cid + ".png\n", encoding="utf-8")
        session = FakeSession({
            self.base + self.cid + ".png": FakeResponse(200, b"image-binary-payload")
        })
        info = fetch_pose(session, self.cid, "fb")
        self.assertIsNotNone(info)
        self.assertTrue((folder / (self.cid + ".png")).is_file())
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
