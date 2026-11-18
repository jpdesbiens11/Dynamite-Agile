"""0.60.123 (D-O-136): Diamond -- « PDF » next to « ↔ IA » on every page: the page's artefacts as a PDF in the format of the
Word documents (cover page with signatures, table of contents and log of revision; header with Doc.-No., Revision, Page n of N;
footer), Letter or Tabloid landscape when a table is wide, wide tables cut in column groups; a page's own document (Golden
Nuggets) sent as blocks and checked; a page without artefacts gets all of Diamond."""
import json
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


def text_of(pdf):
    out = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", pdf, re.S):
        try:
            out.append(zlib.decompress(m.group(1)).decode("cp1252", "replace"))
        except zlib.error:
            pass
    return "\n".join(out)


class DiamondPdfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/me")["projects"] if p["key"] == "DEMO")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def pdf(self, body):
        req = urllib.request.Request(self.url + "/api/diamond/p/{}/pdf".format(self.pid), data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-CSRF-Token", self.admin.csrf)
        try:
            with self.admin.opener.open(req, timeout=60) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def test_01_page_of_artefacts(self):
        status, headers, data = self.pdf({"title": "DFMEA", "view": "dfmea", "sections": ["functions", "dfmea"]})
        self.assertEqual(status, 200, data[:300])
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn("application/pdf", headers.get("Content-Type", ""))
        self.assertIn(b"/MediaBox [0 0 1224 792]", data)  # the DFMEA is wide: Tabloid landscape
        text = text_of(data)
        for words in ("Doc.-No. : DM-DEMO-DFMEA", "Revision : A", "Table des mati", "Journal des r", "Prepared by", "Checked by",
                      "Document g\xe9n\xe9r\xe9 par Dynamite | Agile", "Page : 1 of"):
            self.assertIn(words, text)
        self.assertIn("suite du tableau", text)  # more than 11 columns: cut in groups that all start with the code
        with db.connect() as conn:
            row = conn.execute("SELECT details FROM audit_log WHERE action = 'diamond_export_pdf' ORDER BY id DESC").fetchone()
        self.assertIn('"page": "dfmea"', row["details"])

    def test_02_page_without_artefacts_and_narrow_page(self):
        status, _h, data = self.pdf({"title": "Prioriser", "view": "prio"})
        self.assertEqual(status, 200)
        text = text_of(data)
        self.assertIn("Arbre fonctionnel", text)  # all of Diamond
        status, _h, data = self.pdf({"title": "Storyline", "view": "story", "sections": ["story"]})
        self.assertEqual(status, 200)
        self.assertIn(b"/MediaBox [0 0 612 792]", data)  # a narrow table stays on Letter

    def test_03_blocks_of_a_page(self):
        blocks = [{"type": "h", "level": 1, "text": "Disruptive Innovation"}, {"type": "p", "text": "Pourquoi des entreprises bien gérées perdent."},
                  {"type": "card", "code": "D1", "title": "Sustaining ou disruptive innovation", "tag": "Marché et technologie", "color": 3,
                   "idea": "Une innovation de continuité…", "details": [["Exemple", "Disques durs"], ["En entreprise aujourd'hui", "Classez"]]},
                  {"type": "ul", "items": ["un", "deux"]}, {"type": "note", "text": "Sources"}]
        status, _h, data = self.pdf({"title": "Golden Nuggets", "view": "nuggets", "blocks": blocks})
        self.assertEqual(status, 200)
        self.assertIn(b"/MediaBox [0 0 612 792]", data)
        text = text_of(data)
        self.assertIn("Sustaining ou disruptive innovation", text)
        self.assertIn("1   Disruptive Innovation", text)
        status, _h, body = self.pdf({"title": "X", "view": "nuggets", "blocks": [{"type": "script"}]})
        self.assertEqual(status, 400)
        self.assertIn("inconnu", json.loads(body)["error"])

    def test_04_button_next_to_round_trip(self):
        shell = (BASE_DIR / "static" / "js" / "diamond" / "diamond.js").read_text("utf-8")
        self.assertIn("DA.diamond.rtButton(ctx) : null, DA.diamond.pdfButton", shell)
        entry = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        self.assertLess(entry["scripts"].index("/js/diamond/rt.js"), entry["scripts"].index("/js/diamond/pdf.js"))
        self.assertIn("D.pdfBuilders.nuggets", (BASE_DIR / "static" / "js" / "diamond" / "nuggets.js").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
