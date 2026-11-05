"""0.60.33 (D-O-041): « Exporter Diamond » -- every table in Excel, every diagram in draw.io, the report in Word, each
with the mark « DynamiteAgile · Co-Intelligence WorkFlow™ »; Excel and Word stamped with the revision by the core."""
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import export_data as X  # noqa: E402
from tools.api_client import Client  # noqa: E402

LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))


class DiamondExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "e.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/starter/apply", {"file": LAMPE})["project"]["id"]
        cls.files = {}
        for ext in ("xlsx", "docx", "drawio"):
            with cls.admin.opener.open(urllib.request.Request("{}/api/diamond/p/{}/export.{}".format(cls.url, cls.pid, ext))) as r:
                cls.files[ext] = (r.headers.get("Content-Disposition"), r.read())

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_excel(self):
        disposition, body = self.files["xlsx"]
        self.assertIn("Diamond_LAMPE_Tableaux_", disposition)
        z = zipfile.ZipFile(io.BytesIO(body))
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                ET.fromstring(z.read(name))  # every part is well-formed
        book = z.read("xl/workbook.xml").decode("utf-8")
        for sheet in ("Synthèse", "Arbre fonctionnel", "Structure", "Pièces × fonctions", "Risques projet", "DFMEA", "Révision"):
            self.assertIn('name="{}"'.format(sheet), book)  # « Révision »: the stamp of the core
        first = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("Co-Intelligence WorkFlow™", first)
        self.assertIn("&amp;KE0602FDynamite&amp;K0E9A9AAgile", first)  # the brand in the printed header
        dfmea = z.read("xl/worksheets/sheet6.xml").decode("utf-8")
        self.assertIn("Prevention Controls", dfmea)
        self.assertIn("Bonnes pratiques (industrie)", dfmea)
        self.assertIn("_xlnm.Print_Titles", book)

    def test_02_drawio(self):
        disposition, body = self.files["drawio"]
        self.assertIn("Diamond_LAMPE_Diagrammes_", disposition)
        root = ET.fromstring(body)
        pages = root.findall("diagram")
        self.assertEqual([p.get("name") for p in pages], ["Arbre fonctionnel", "Structure — vue générale", "Structure — vue détaillée",
                                                          "Carte des risques"])
        ids = [c.get("id") for c in root.iter("mxCell")]
        self.assertEqual(len(ids), len(set(ids)))  # unique in the whole file (draw.io and mxGraph)
        known = set(ids)
        for c in root.iter("mxCell"):
            if c.get("edge"):
                self.assertIn(c.get("source"), known)
                self.assertIn(c.get("target"), known)
        for p in pages:
            text = ET.tostring(p, encoding="unicode")
            self.assertIn(X.WORKFLOW, text)
            self.assertIn("Dynamite", text)
        tree = ET.tostring(pages[0], encoding="unicode")
        self.assertEqual(tree.count('edge="1"'), 19)  # every link of the 21 functions' tree (20 in it, 1 outside)
        self.assertIn("Éclairer une surface de travail", tree)

    def test_03_word(self):
        disposition, body = self.files["docx"]
        self.assertIn("Diamond_LAMPE_Rapport_", disposition)
        z = zipfile.ZipFile(io.BytesIO(body))
        footers = "".join(z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("word/footer"))
        self.assertIn(X.MARK, footers)
        doc = z.read("word/document.xml").decode("utf-8")
        ET.fromstring(doc)
        for title in ("Synthèse", "Arbre fonctionnel", "Structure fonctionnelle", "Pièces et fonctions", "Risques projet", "DFMEA",
                      "Ce qu'une revue demanderait", "Fichiers joints"):
            self.assertIn(">{}<".format(title.replace("'", "&apos;")), doc.replace("'", "&apos;"))

    def test_04_rights_and_empty_space(self):
        empty = self.admin.post("/api/admin/projects", {"key": "VIDE", "name": "Vide"})["project"]["id"]
        for ext in ("xlsx", "docx", "drawio"):  # an empty Space still exports (guided empty sections)
            with self.admin.opener.open(urllib.request.Request("{}/api/diamond/p/{}/export.{}".format(self.url, empty, ext))) as r:
                self.assertEqual(r.status, 200)
        anonymous = Client(self.url)
        with self.assertRaises(Exception):
            anonymous.get("/api/diamond/p/{}/export.xlsx".format(self.pid))


if __name__ == "__main__":
    unittest.main()
