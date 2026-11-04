"""Core lot v0.4 (attachments) + Dynamite images (D-B-003, D-B-004):
type sniffed from bytes, SVG refused, size caps, dedup, no cross-space
leak, page body may only reference images of its own space.

    python -m unittest tests.test_dynamite_images -v
"""
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


def tiny_png():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x60\x10")) + chunk(b"IEND", b""))


def doc_with_image(image_id):
    return {"type": "doc", "content": [{"type": "image", "id": image_id, "alt": "Schéma électrique"}]}


class DynamiteImagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = load_config(cls.data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        cfg["max_upload_mb"] = 12
        db.init_db(cls.data_dir / "i.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        for key in ("DOC", "SECRET"):
            cls.admin.post("/api/admin/projects", {"provision": False, "key": key, "name": key, "description": ""})
        ids = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        made = cls.admin.post("/api/admin/users", {"username": "lect", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(ids["DOC"], made["user"]["id"]),
                      {"role": "reader"})
        cls.reader = Client(url)
        cls.reader.login("lect", made["temp_password"], "Revue-Essai-Pass-2026")
        cls.doc = "/api/dynamite/p/{}".format(ids["DOC"])
        cls.secret = "/api/dynamite/p/{}".format(ids["SECRET"])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, func, *args, **kwargs):
        with self.assertRaises(ApiFailure) as ctx:
            func(*args, **kwargs)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)
        return ctx.exception.message

    def test_01_upload_serve_and_dedup(self):
        png = tiny_png()
        first = self.admin.upload(self.doc + "/images", png, "image/png", "capture écran.png")
        self.assertEqual(first["mime"], "image/png")
        again = self.admin.upload(self.doc + "/images", png, "application/octet-stream", "autre.png")
        self.assertEqual(again["id"], first["id"])  # same bytes, same space: stored once
        status, headers, data = self.reader.raw_get("/api/dynamite/image/{}".format(first["id"]))
        self.assertEqual((status, data), (200, png))
        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertTrue(headers["Content-Disposition"].startswith("inline"))
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        stored = list((self.data_dir / "attachments").rglob("*.png"))
        self.assertEqual(len(stored), 1)

    def test_02_type_from_bytes_svg_refused(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        msg = self.fails(415, self.admin.upload, self.doc + "/images", svg, "image/png", "x.png")
        self.assertIn("SVG", msg)
        self.fails(415, self.admin.upload, self.doc + "/images", b"%PDF-1.7", "image/png", "x.png")
        self.fails(400, self.admin.upload, self.doc + "/images", b"", "image/png", "x.png")

    def test_03_size_caps(self):
        big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
        self.assertIn("10 Mo", self.fails(413, self.admin.upload, self.doc + "/images", big, "image/png"))
        huge = b"\x00" * (13 * 1024 * 1024)
        self.assertIn("max_upload_mb", self.fails(413, self.admin.upload, self.doc + "/images", huge))

    def test_04_roles_and_isolation(self):
        self.fails(403, self.reader.upload, self.doc + "/images", tiny_png(), "image/png")
        hidden = self.admin.upload(self.secret + "/images", tiny_png() + b"secret", "image/png")
        status, _, body = self.reader.raw_get("/api/dynamite/image/{}".format(hidden["id"]))
        missing_status, _, missing_body = self.reader.raw_get("/api/dynamite/image/999999")
        self.assertEqual((status, body), (missing_status, missing_body))  # indistinguishable 404

    def test_05_page_references(self):
        own = self.admin.upload(self.doc + "/images", tiny_png() + b"own", "image/png")
        other = self.admin.upload(self.secret + "/images", tiny_png() + b"other", "image/png")
        page = self.admin.post(self.doc + "/pages", {"title": "Avec image", "body": doc_with_image(own["id"])})
        body = self.admin.get("{}/pages/{}".format(self.doc, page["id"]))["page"]["body"]
        self.assertEqual(body["content"][0], {"type": "image", "id": own["id"], "alt": "Schéma électrique"})
        msg = self.fails(400, self.admin.post, self.doc + "/pages",
                         {"title": "Vol", "body": doc_with_image(other["id"])})
        self.assertIn("Correctif", msg)
        self.fails(400, self.admin.post, self.doc + "/pages",
                   {"title": "Mauvais", "body": {"type": "doc", "content": [{"type": "image", "id": "1"}]}})


if __name__ == "__main__":
    unittest.main()
