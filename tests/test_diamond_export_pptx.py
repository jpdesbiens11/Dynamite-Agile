"""0.60.50 (D-O-059): the diagrams of Diamond in PowerPoint (native shapes, glued connectors) and « Exporter ▾ » on the tree
and structure screens: the diagram and the table of that screen only (?only=tree | structure) in draw.io, PowerPoint, Excel."""
import io
import json
import re
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


class DiamondPptxTest(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path, pid=None):
        url = "{}/api/diamond/p/{}/{}".format(self.url, pid or self.pid, path)
        with self.admin.opener.open(urllib.request.Request(url)) as r:
            return r.headers.get("Content-Disposition"), r.read()

    def slides(self, body):
        z = zipfile.ZipFile(io.BytesIO(body))
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                ET.fromstring(z.read(name))  # every part is well-formed
        names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.sub(r"\D", "", n)))
        types = z.read("[Content_Types].xml").decode("utf-8")
        pres = z.read("ppt/presentation.xml").decode("utf-8")
        for n in names:
            self.assertIn('PartName="/{}"'.format(n), types)
        self.assertEqual(pres.count("<p:sldId "), len(names))
        return z, [z.read(n).decode("utf-8") for n in names]

    def test_01_pptx_every_diagram(self):
        disposition, body = self.get("export.pptx")
        self.assertIn("Diamond_LAMPE_Diagrammes_", disposition)
        self.assertIn(".pptx", disposition)
        z, slides = self.slides(body)
        self.assertIn("docProps/custom.xml", z.namelist())  # stamped with the revision by the core
        self.assertIn("Dynamite", slides[0])
        self.assertIn(X.WORKFLOW, slides[0])
        text = "".join(slides)
        self.assertIn("Éclairer une surface de travail", text)
        self.assertIn("vue d&apos;ensemble", text.replace("'", "&apos;"))  # the tree of 21 functions is cut: overview + branches
        self.assertGreaterEqual(len(slides), 6)
        for s in slides[1:]:
            self.assertIn(X.WORKFLOW, s)
            ids = re.findall(r'<p:cNvPr id="(\d+)"', s)
            self.assertEqual(len(ids), len(set(ids)))  # unique on each slide
            for a, b in re.findall(r'<a:stCxn id="(\d+)"[^>]*/><a:endCxn id="(\d+)"', s):
                self.assertIn(a, ids)  # every connector is glued to boxes of its slide
                self.assertIn(b, ids)
        self.assertIn("bentConnector3", text)
        self.assertIn('prst="roundRect"', text)

    def test_02_only_tree(self):
        disposition, body = self.get("export.drawio?only=tree")
        self.assertIn("Diamond_LAMPE_Arbre_", disposition)
        names = [p.get("name") for p in ET.fromstring(body).findall("diagram")]
        self.assertEqual(names, ["Arbre fonctionnel"])
        disposition, body = self.get("export.xlsx?only=tree")
        self.assertIn("Diamond_LAMPE_Arbre_", disposition)
        book = zipfile.ZipFile(io.BytesIO(body)).read("xl/workbook.xml").decode("utf-8")
        self.assertIn('name="Arbre fonctionnel"', book)
        self.assertNotIn('name="DFMEA"', book)
        _d, body = self.get("export.pptx?only=tree")
        _z, slides = self.slides(body)
        self.assertTrue(all("Structure fonctionnelle" not in s for s in slides[1:]))

    def test_03_only_structure(self):
        _d, body = self.get("export.drawio?only=structure")
        names = [p.get("name") for p in ET.fromstring(body).findall("diagram")]
        self.assertEqual(names, ["Structure — vue générale", "Structure — vue détaillée"])
        _d, body = self.get("export.xlsx?only=structure")
        book = zipfile.ZipFile(io.BytesIO(body)).read("xl/workbook.xml").decode("utf-8")
        self.assertIn('name="Structure"', book)
        self.assertNotIn('name="Arbre fonctionnel"', book)
        _d, body = self.get("export.pptx?only=structure")
        _z, slides = self.slides(body)
        self.assertEqual(len(slides), 3)  # the title, the general view, the detailed view
        _d, body = self.get("export.drawio?only=nimporte")  # an unknown value: every diagram
        self.assertEqual(len(ET.fromstring(body).findall("diagram")), 4)

    def test_04_empty_space_and_screens(self):
        empty = self.admin.post("/api/admin/projects", {"key": "VIDE", "name": "Vide"})["project"]["id"]
        for q in ("export.pptx", "export.pptx?only=tree", "export.pptx?only=structure"):
            self.slides(self.get(q, empty)[1])
        js = lambda name: (BASE_DIR / "static" / "js" / "diamond" / name).read_text("utf-8")  # noqa: E731
        self.assertIn('D.exportMenu(ctx, "tree")', js("tree.js"))
        self.assertIn('D.exportMenu(ctx, "structure")', js("structure.js"))
        self.assertIn('"?only=" + only', js("export_menu.js"))
        self.assertIn('["pptx", "Diapositives"', js("export.js"))
        manifest = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        self.assertIn("/js/diamond/export_menu.js", manifest["scripts"])
        self.assertNotIn("innerHTML", js("export_menu.js"))


if __name__ == "__main__":
    unittest.main()
