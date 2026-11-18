"""0.60.124 (D-O-137): Golden Nuggets -- the guide of each part (Contexte, Problématique, Portée, Comment l'utiliser, Ce que
contient chaque carte), the export of one part or of the four, and « Word »: the same document as the PDF on the template of
the Diamond report (cover page, table of contents, header with Doc.-No., the « Co-Intelligence WorkFlow™ » mark in the footer).

    python -m unittest tests.test_diamond_nuggets_export -v
"""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402
from tests.test_diamond_pdf import text_of  # noqa: E402

STATIC = BASE_DIR / "static" / "js" / "diamond"
CARD = {"type": "card", "code": "A2", "title": "Supprimer la pièce ou le procédé", "tag": "Questionner et supprimer", "color": 6,
        "idea": "Retirez tout ce que vous pouvez.", "details": [["Exemple", "Des brides retirées"], ["Sur votre projet", "Une pièce de moins"]]}


def docx_parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        read = lambda prefix: "".join(z.read(n).decode("utf-8") for n in names if n.startswith(prefix) and n.endswith(".xml"))
        return read("word/document"), read("word/header"), read("word/footer")


class NuggetsExportTest(unittest.TestCase):
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
        cls.blocks = None
        if shutil.which("node"):  # the blocks the page really sends (tests/js/nuggets_export.js)
            out = Path(cls.tmp.name) / "blocks.json"
            subprocess.run(["node", str(BASE_DIR / "tests" / "js" / "nuggets_export.js"), "--dump", str(out)], check=True,
                           capture_output=True, timeout=60)
            cls.blocks = json.loads(out.read_text("utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def post(self, fmt, body, client=None):
        client = client or self.admin
        req = urllib.request.Request(self.url + "/api/diamond/p/{}/{}".format(self.pid, fmt), data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        if client.csrf:
            req.add_header("X-CSRF-Token", client.csrf)
        try:
            with client.opener.open(req, timeout=60) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def test_01_word_on_the_report_template(self):
        blocks = [{"type": "h", "level": 1, "text": "L'algorithme de conception en 5 étapes"}, {"type": "p", "text": "Dans cet ordre."},
                  {"type": "note", "text": "Sources"}, {"type": "h", "level": 3, "text": "Contexte"}, {"type": "ol", "items": ["un", "deux"]}, {"type": "ul", "items": ["trois"]},
                  {"type": "table", "header": ["Code", "Titre"], "rows": [["A1", "Exigences"]]}, CARD]
        status, headers, data = self.post("docx", {"title": "Golden Nuggets — L'algorithme en 5 étapes", "view": "nuggets", "blocks": blocks})
        self.assertEqual(status, 200, data[:300])
        self.assertIn("wordprocessingml", headers.get("Content-Type", ""))
        self.assertIn(".docx", headers.get("Content-Disposition", ""))
        doc, head, foot = docx_parts(data)
        plain = doc.replace("&apos;", "'")
        for words in ("L'algorithme de conception en 5 étapes", "Supprimer la pièce ou le procédé", "Questionner et supprimer",
                      "Sur votre projet. ", 'w:pStyle w:val="Titre1"', 'w:pStyle w:val="Titre3"', "Prepared by"):
            self.assertIn(words, plain)
        self.assertIn('w:left w:val="single" w:sz="36" w:color="FF7091"', doc)  # the card: its family colour on the left
        self.assertIn("DM-DEMO-NUGGETS", doc + head)
        self.assertIn("DynamiteAgile · Co-Intelligence WorkFlow™", foot)  # the mark of the Diamond report
        self.assertNotIn("{{", doc + head)
        with db.connect() as conn:
            row = conn.execute("SELECT details FROM audit_log WHERE action = 'diamond_export_docx' ORDER BY id DESC").fetchone()
        self.assertIn('"page": "nuggets"', row["details"])

    def test_02_bad_blocks_and_artefacts(self):
        status, _h, body = self.post("docx", {"title": "X", "view": "nuggets", "blocks": [{"type": "script"}]})
        self.assertEqual(status, 400)
        self.assertIn("inconnu", json.loads(body)["error"])
        status, _h, data = self.post("docx", {"title": "DFMEA", "view": "dfmea", "sections": ["dfmea"]})  # the same body as the PDF
        self.assertEqual(status, 200)
        self.assertIn("Code", docx_parts(data)[0])
        outsider = Client(self.url)
        status, _h, _b = self.post("docx", {"title": "X", "blocks": []}, client=outsider)
        self.assertIn(status, (401, 403))

    def test_03_one_part_or_the_four(self):
        if not self.blocks:
            self.skipTest("node is not installed")
        for fmt in ("docx", "pdf"):
            status, _h, one = self.post(fmt, {"title": "Golden Nuggets — L'algorithme en 5 étapes", "view": "nuggets", "blocks": self.blocks["one"]})
            self.assertEqual(status, 200, one[:300])
            status, _h, four = self.post(fmt, {"title": "Golden Nuggets", "view": "nuggets", "blocks": self.blocks["all"]})
            self.assertEqual(status, 200, four[:300])
            text_one = docx_parts(one)[0] if fmt == "docx" else text_of(one)
            text_four = docx_parts(four)[0] if fmt == "docx" else text_of(four)
            self.assertIn("Probl", text_one)  # the guide of the part
            self.assertNotIn("Disruptive Innovation : les principes", text_one)
            self.assertIn("Pourquoi Golden Nuggets", text_four)
            self.assertIn("Disques durs", text_four)
            self.assertNotIn("Disques durs", text_one)
            if fmt == "docx":  # one card = one tinted cell with its colour bar
                self.assertEqual((text_one.count('w:sz="36"'), text_four.count('w:sz="36"')), (5, 62))

    def test_04_screen(self):
        guide = (STATIC / "nuggets_guide.js").read_text("utf-8")
        for head in ("Contexte", "Problématique", "Portée", "Comment l'utiliser", "Ce que contient chaque carte"):
            self.assertIn('"{}"'.format(head), guide)
        for f in ("nuggets_guide.js", "nuggets_export.js", "nuggets.js", "pdf.js"):
            self.assertNotIn("innerHTML", (STATIC / f).read_text("utf-8"))
        entry = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        order = [entry["scripts"].index("/js/diamond/" + f) for f in ("nuggets_disruption.js", "nuggets_guide.js", "nuggets.js", "nuggets_export.js")]
        self.assertEqual(order, sorted(order))
        shell = (STATIC / "diamond.js").read_text("utf-8")
        self.assertIn("DA.diamond.wordButton(ctx)", shell)
        pdf = (STATIC / "pdf.js").read_text("utf-8")
        self.assertIn("D.docExporters[ctx.view](ctx, \"pdf\")", pdf)
        self.assertIn('"0.60.124-word"', pdf)
        self.assertIn('"0.60.124-nuggets-guide"', (STATIC / "nuggets.js").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
