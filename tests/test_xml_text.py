"""0.60.83 (D-O-089): a control character pasted into a function or a page (U+0001, U+0008…) is forbidden in XML even
escaped; the PowerPoint and draw.io exports of Diamond and the Word export of a Dynamite page came out corrupt. Every
writer now goes through core.xmltext.escape, which drops those characters.

    python -m unittest tests.test_xml_text -v
"""
import io
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup, xmltext  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


def well_formed(data, single=False):
    """[(part, error)] of the XML parts that do not parse."""
    if single:
        parts = {"file": data}
    else:
        z = zipfile.ZipFile(io.BytesIO(data))
        parts = {n: z.read(n) for n in z.namelist() if n.endswith((".xml", ".rels"))}
    bad = []
    for name, raw in parts.items():
        try:
            ET.fromstring(raw)
        except ET.ParseError as err:
            bad.append((name, str(err)))
    return bad


class XmlTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False)
        db.init_db(data_dir / "x.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.c = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.c.login("admin", "admin")
        cls.pid = cls.c.post("/api/admin/projects", {"key": "CTL", "name": "Contrôle"})["project"]["id"]
        cls.c.post("/api/diamond/p/{}/functions".format(cls.pid), {"text": "Mesurer\x01 la distance\x08 au mur", "ftype": "usage"})
        page = cls.c.post("/api/dynamite/p/{}/pages".format(cls.pid), {"title": "Titre\x02", "body": {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Texte\x01 collé d'un PDF"}]}]}})
        cls.page = (page.get("page") or page)["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_escape_drops_what_xml_forbids(self):
        self.assertEqual(xmltext.escape("a\x01<b>\x08 & \tc\n"), "a&lt;b&gt; &amp; \tc\n")
        self.assertEqual(xmltext.escape('"x"', {'"': "&quot;"}), "&quot;x&quot;")

    def test_diamond_exports(self):
        for fmt in ("xlsx", "docx", "pptx", "drawio"):
            with self.subTest(fmt=fmt):
                status, _h, data = self.c.raw_get("/api/diamond/p/{}/export.{}".format(self.pid, fmt))
                self.assertEqual(status, 200)
                self.assertEqual(well_formed(data, single=fmt == "drawio"), [])

    def test_dynamite_page_word(self):
        status, _h, data = self.c.raw_get("/api/dynamite/p/{}/pages/{}/export.docx".format(self.pid, self.page))
        self.assertEqual(status, 200)
        self.assertEqual(well_formed(data), [])
        text = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        self.assertIn("Texte collé d'un PDF", text)


if __name__ == "__main__":
    unittest.main()
