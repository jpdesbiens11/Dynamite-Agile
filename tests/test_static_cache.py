"""0.60.31 (D-O-039): the static files of the interface, lean on the wire -- ETag and 304 Not Modified when the browser
already has a file, gzip for the text types, a changed file picked up at once."""
import gzip
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup, static_cache  # noqa: E402
from core.config import load_config  # noqa: E402


class UnitTest(unittest.TestCase):
    def test_01_entry_and_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "a.js"
            f.write_text("const x = 1;\n" * 400, "utf-8")
            e1 = static_cache.get(f)
            self.assertIsNotNone(e1.gz)
            self.assertEqual(gzip.decompress(e1.gz), e1.raw)
            self.assertIs(static_cache.get(f), e1)  # kept in memory
            f.write_text("const y = 2;\n" * 400, "utf-8")
            os.utime(f, ns=(time.time_ns(), time.time_ns() + 10**9))
            e2 = static_cache.get(f)
            self.assertNotEqual(e2.etag, e1.etag)  # an edited file is picked up, no restart
            small = Path(tmp) / "b.js"
            small.write_text("x", "utf-8")
            self.assertIsNone(static_cache.get(small).gz)
            png = Path(tmp) / "c.png"
            png.write_bytes(b"\x89PNG" + b"\0" * 5000)
            self.assertIsNone(static_cache.get(png).gz)  # images are already compressed

    def test_02_headers(self):
        entry = static_cache.Entry((1, 1), b"", None, '"abc"')
        self.assertTrue(static_cache.not_modified(entry, '"abc"'))
        self.assertTrue(static_cache.not_modified(entry, 'W/"abc-gz", "zzz"'))
        self.assertFalse(static_cache.not_modified(entry, '"zzz"'))
        self.assertFalse(static_cache.not_modified(entry, None))
        self.assertTrue(static_cache.accepts_gzip("gzip, deflate, br"))
        self.assertTrue(static_cache.accepts_gzip("br;q=1.0, gzip;q=0.8"))
        self.assertFalse(static_cache.accepts_gzip("gzip;q=0"))
        self.assertFalse(static_cache.accepts_gzip("identity"))
        self.assertFalse(static_cache.accepts_gzip(None))


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path, **headers):
        req = urllib.request.Request(self.url + path, headers=headers)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_01_gzip_and_304(self):
        raw = (BASE_DIR / "static" / "js" / "app.js").read_bytes()
        status, h, body = self.get("/js/app.js")
        self.assertEqual((status, body), (200, raw))
        self.assertEqual(h["Vary"], "Accept-Encoding")
        self.assertEqual(h["Cache-Control"], "no-cache")
        status, hz, body = self.get("/js/app.js", **{"Accept-Encoding": "gzip"})
        self.assertEqual((status, hz["Content-Encoding"]), (200, "gzip"))
        self.assertEqual(gzip.decompress(body), raw)
        self.assertLess(len(body), len(raw) / 2)
        for tag in (h["ETag"], hz["ETag"]):
            status, h304, body = self.get("/js/app.js", **{"If-None-Match": tag, "Accept-Encoding": "gzip"})
            self.assertEqual((status, body), (304, b""))
            self.assertTrue(h304["ETag"])
        self.assertIn("default-src", h304.get("Content-Security-Policy", ""))  # the security headers stay
        self.assertEqual(self.get("/js/app.js", **{"If-None-Match": '"old"'})[0], 200)

    def test_02_index_and_images(self):
        status, h, _ = self.get("/", **{"Accept-Encoding": "gzip"})
        self.assertEqual((status, h["Content-Encoding"], h["Cache-Control"]), (200, "gzip", "no-cache"))
        status, h, _ = self.get("/img/sketch/hero.svg", **{"Accept-Encoding": "gzip"})
        self.assertEqual(status, 200)
        self.assertTrue(h["ETag"])


if __name__ == "__main__":
    unittest.main()
