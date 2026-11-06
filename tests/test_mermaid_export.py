"""0.60.62 (D-O-071): the Mermaid diagrams stay drawings in the PDF / Word exports of a Dynamite page -- the sources
the browser draws, the POST export with the PNGs (image in place of the code, the code kept under it in small type),
the old GET link unchanged, bad images refused."""
import base64
import io
import json
import struct
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
import zlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.dynamite.export_mermaid import looks  # noqa: E402
from tools.api_client import Client  # noqa: E402

FLOW = "flowchart LR\n  A[Début] --> B{Choix}\n  B -- Oui --> C[Fin]"
SEQ = "sequenceDiagram\n  Alice->>Bob: Bonjour"


def tiny_png(w=40, h=20):
    """A plain white RGBA PNG, as a canvas makes it."""
    raw = b"".join(b"\x00" + b"\xff\xff\xff\xff" * w for _ in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def code(text, lang=None):
    node = {"type": "code", "text": text}
    if lang:
        node["lang"] = lang
    return node


class MermaidExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "MMX", "name": "Mermaid export"})["project"]["id"]
        body = {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Audit"}]},
            code(FLOW, "mermaid"), code("print('pas un diagramme')", "python"),
            {"type": "bullet_list", "items": [[code(SEQ)]]}]}  # no language, inside a list: still found
        made = cls.admin.post("/api/dynamite/p/{}/pages".format(cls.pid), {"title": "Audit IA", "body": body})
        cls.page = (made.get("page") or made)["id"]
        child = {"type": "doc", "content": [code("graph TD\n  X --> Y", "mermaid")]}
        cls.admin.post("/api/dynamite/p/{}/pages".format(cls.pid), {"title": "Suite", "parent_id": cls.page, "body": child})
        cls.base = "/api/dynamite/p/{}/pages/{}".format(cls.pid, cls.page)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def post_file(self, path, body):
        req = urllib.request.Request(self.admin.base + path, data=json.dumps(body).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-CSRF-Token", self.admin.csrf)
        try:
            with self.admin.opener.open(req, timeout=15) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def test_01_looks_like_the_engine(self):
        self.assertTrue(looks("%% note\nflowchart LR\n A-->B"))
        self.assertTrue(looks("---\ntitle: X\n---\nsequenceDiagram\n A->>B: x"))
        self.assertFalse(looks("print('flowchart LR')"))

    def test_02_sources(self):
        self.assertEqual(self.admin.get(self.base + "/export/mermaid")["sources"], [FLOW, SEQ])
        self.assertEqual(len(self.admin.get(self.base + "/export/mermaid?children=1")["sources"]), 3)

    def test_03_word_with_drawings(self):
        png = base64.b64encode(tiny_png()).decode()
        status, data = self.post_file(self.base + "/export.docx", {"children": True, "diagrams": {FLOW: png, SEQ: png}})
        self.assertEqual(status, 200, data[:200])
        z = zipfile.ZipFile(io.BytesIO(data))
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        self.assertEqual(len(media), 2)
        doc = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Diagramme Mermaid", doc)
        self.assertIn("A[Début] --&gt; B{Choix}", doc)  # the code stays, for the audit
        self.assertIn('<w:sz w:val="14"/>', doc)  # in small type
        self.assertIn("X --&gt; Y", doc)  # the sub-page diagram, not drawn: code as before
        self.assertIn('cx="{}"'.format(20 * 9525), doc)  # drawn at 2x, shown at its own size

    def test_04_pdf_with_drawing(self):
        status, data = self.post_file(self.base + "/export.pdf", {"diagrams": {FLOW: base64.b64encode(tiny_png()).decode()}})
        self.assertEqual(status, 200, data[:200])
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertIn(b"/Subtype /Image", data)

    def test_05_get_link_unchanged(self):
        status, _headers, data = self.admin.raw_get(self.base + "/export.docx")
        self.assertEqual(status, 200)
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertFalse([n for n in z.namelist() if n.startswith("word/media/")])

    def test_06_bad_images_refused(self):
        for diagrams in ({FLOW: "pas du base64 !"}, {FLOW: base64.b64encode(b"GIF89a....").decode()}, ["x"]):
            status, data = self.post_file(self.base + "/export.pdf", {"diagrams": diagrams})
            self.assertEqual(status, 400, data[:200])
        journal = self.admin.get("/api/admin/audit?action=dynamite_page_export")
        self.assertTrue(journal)


if __name__ == "__main__":
    unittest.main()
