"""BD2 inventory illustrations: filename safety, PNG integrity and offline caching."""
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "download_thumbnails.py"
spec = importlib.util.spec_from_file_location("download_thumbnails", SCRIPT)
thumbs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbs)


def fake_png():
    # 下载器只需要检查 PNG header 和合法的图像宽高。
    return (thumbs.PNG_SIGNATURE + b"\0\0\0\rIHDR" +
            (256).to_bytes(4, "big") + (256).to_bytes(4, "big") + b"\x08\x06")


class ThumbnailTests(unittest.TestCase):
    def test_every_curated_skin_has_an_actual_inventory_illustration(self):
        files = thumbs.read_catalog()
        self.assertEqual(54, len(files))
        self.assertEqual(len(set(files.values())),len(files))
        self.assertTrue(all(thumbs.IMAGE_NAME.fullmatch(x) for x in files.values()))
        self.assertIn("costume-003203",files)
        self.assertIn("zenith-stranger-bunny",files)

    def test_invalid_names_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"images":{"../../etc/passwd":"../../bad.png"}}',
                            encoding="utf-8")
            with self.assertRaises(ValueError):
                thumbs.read_catalog(path)

    def test_error_html_and_truncated_files_are_not_images(self):
        self.assertFalse(thumbs.is_valid_png(b"<html>API rate limit</html>"))
        self.assertFalse(thumbs.is_valid_png(thumbs.PNG_SIGNATURE))
        self.assertTrue(thumbs.is_valid_png(fake_png()))

    def test_download_cache_and_force_are_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            count = []
            def opener(req, timeout):
                count.append(req.full_url)
                self.assertIn("illust_inven_char003203_153.png",req.full_url)
                return io.BytesIO(fake_png())
            identifier="costume-003203"
            filename="illust_inven_char003203_153.png"
            status,file = thumbs.download_one(identifier,filename,tmp,opener)
            self.assertEqual("downloaded",status)
            self.assertTrue(file.is_file())
            self.assertTrue(thumbs.is_valid_png(file.read_bytes()))
            status, _ = thumbs.download_one(identifier,filename,tmp,opener)
            self.assertEqual("cached",status)
            self.assertEqual(1,len(count))
            status, _ = thumbs.download_one(identifier,filename,tmp,opener,overwrite=True)
            self.assertEqual("downloaded",status)
            self.assertEqual(2,len(count))
            self.assertFalse(file.with_suffix(".tmp").exists())

    def test_invalid_remote_image_does_not_overwrite_existing_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            name="costume-003203"
            target=Path(tmp)
            cached=target/(name+".png")
            cached.write_bytes(fake_png())
            with self.assertRaises(ValueError):
                thumbs.download_one(name,"illust_inven_char003203_153.png",
                                    target,lambda req,timeout: io.BytesIO(b"<html>403</html>"),
                                    overwrite=True)
            self.assertEqual(fake_png(),cached.read_bytes())


if __name__ == "__main__":
    unittest.main()
