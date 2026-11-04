"""0.34.0: definitions and acronyms of the platform (D-A-037) -- central lists, BDC pages (Definitions, Acronyms,
French translation of the terms) and their automatic sections in the Word exports of Goldmine and Testing.

    python -m unittest tests.test_lot_v022 -v
"""
import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.testing import glossary  # noqa: E402
from modules.testing.data_acronyms import ACRONYMS  # noqa: E402
from modules.testing.data_definitions import DEFINITIONS  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV022Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = load_config(cls.data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "REQ", "name": "REQ", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur tom | Tom Test | utilisateur | actif\n"
                                                                  "droit tom | REQ | editeur\n"})
        c = done["created"][0]
        cls.tom = Client(cls.url)
        cls.tom.login(c["username"], c["temp_password"], "Essai-Lot-Glossaire-2026!")
        projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.projects, cls.pid = projects, projects["REQ"]
        cls.tom.get("/api/testing/tests")  # joins TESTING as editor

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status
        return 200

    def download(self, client, path):
        with client.opener.open(self.url + path) as resp:
            return resp.read()

    def page(self, title):
        href = self.admin.get("/api/testing/lists")["glossary_pages"][title]
        key, _, page_id = href.replace("#/dynamite/", "").partition("/page/")
        return self.admin.get("/api/dynamite/p/{}/pages/{}".format(self.projects[key], page_id))["page"]

    def doc(self, path):
        return zipfile.ZipFile(io.BytesIO(self.download(self.tom, path))).read("word/document.xml").decode("utf-8")

    def test_01_default_lists(self):
        data = self.tom.get("/api/testing/lists")
        acr = {x["code"]: x for x in data["items"] if x["kind"] == "acronym"}
        defs = {x["code"]: x for x in data["items"] if x["kind"] == "definition"}
        self.assertEqual(len(acr), sum(len(v) for v in ACRONYMS.values()))
        self.assertEqual(len(defs), sum(len(v) for v in DEFINITIONS.values()))
        self.assertEqual(acr["RoHS"]["label"], "Restriction of Hazardous Substances")  # case kept
        self.assertEqual(acr["ESD"]["details"]["fr"], "Décharge électrostatique")
        self.assertTrue(acr["CdCF"]["label"].startswith("Cahier des charges fonctionnel"))
        self.assertEqual(defs["Function"]["details"]["fr"], "Fonction")
        self.assertEqual(set(data["glossary_pages"]), {glossary.DEF_TITLE, glossary.ACR_TITLE, glossary.TR_TITLE})
        self.assertFalse(data["can_manage"])
        self.assertNotIn("acronym", self.tom.get("/api/testing/tests")["lists"])  # not a picker

    def test_02_bdc_pages(self):
        defs = json.dumps(self.page(glossary.DEF_TITLE)["body"], ensure_ascii=False)
        for text in ("Functional Tree", "Service Function", "esteem function", "degrees Celsius", "Functional Analysis"):
            self.assertIn(text, defs)
        acr = json.dumps(self.page(glossary.ACR_TITLE)["body"], ensure_ascii=False)
        self.assertIn("Restriction of Hazardous Substances", acr)
        self.assertIn("Electrostatic Discharge", acr)
        tr = json.dumps(self.page(glossary.TR_TITLE)["body"], ensure_ascii=False)
        for text in ("Arbre fonctionnel", "Décharge électrostatique", "In Analysis", "En analyse"):
            self.assertIn(text, tr)

    def test_03_manage_entries(self):
        new = {"kind": "acronym", "code": "LOTO", "label": "Lockout / Tagout", "category": "General / Quality / Regulatory",
               "details": {"fr": "Consignation"}}
        self.assertEqual(self.status(lambda: self.tom.post("/api/testing/lists", new)), 403)
        made = self.admin.post("/api/testing/lists", new)
        self.assertEqual(made["code"], "LOTO")
        self.assertIn("Lockout / Tagout", json.dumps(self.page(glossary.ACR_TITLE)["body"]))
        self.assertIn("Consignation", json.dumps(self.page(glossary.TR_TITLE)["body"]))
        self.assertEqual(self.status(lambda: self.admin.post("/api/testing/lists", dict(new, code="loto"))), 409)
        self.assertEqual(self.status(lambda: self.admin.post("/api/testing/lists", dict(new, code="LO TO"))), 400)
        self.assertEqual(self.status(lambda: self.admin.post("/api/testing/lists", {
            "kind": "definition", "code": "Cell Venting", "label": "x" * 601})), 400)
        self.admin.post("/api/testing/lists", {"kind": "definition", "code": "Lockout / Tagout", "label": "Isolation and "
                        "locking of energy sources before work.", "category": "General", "details": {"fr": "Consignation"}})
        self.assertIn("Isolation and locking", json.dumps(self.page(glossary.DEF_TITLE)["body"]))
        ids = {x["code"]: x["id"] for x in self.admin.get("/api/testing/lists")["items"] if x["kind"] == "acronym"}
        self.admin.patch("/api/testing/lists/{}".format(ids["UL"]), {"active": False})
        self.assertNotIn("UL Solutions (Underwriters Laboratories)", json.dumps(self.page(glossary.ACR_TITLE)["body"]))

    def test_04_word_exports(self):
        for path, lang in (("/api/testing/export.docx?ids=TST-ENV-03&lang=en", "en"),
                           ("/api/testing/export.docx?ids=TST-ENV-03&lang=fr", "fr")):
            doc = self.doc(path)
            self.assertIn("Acronyms" if lang == "en" else "Acronymes", doc)
            for text in ("Restriction of Hazardous Substances", "Functional Tree", "Lockout / Tagout",
                         "International System of Units"):
                self.assertIn(text, doc)
            self.assertNotIn("UL Solutions (Underwriters Laboratories)", doc)  # deactivated in test_03
            self.assertNotIn("Brouillon", doc)
        self.assertIn("Arbre fonctionnel", self.doc("/api/testing/export.docx?ids=TST-ENV-03&lang=fr"))
        made = self.tom.post("/api/agile/p/{}/goldmine/requirements".format(self.pid), {
            "statement": "The product shall be insulated.", "test_ref": "TST-ELE-02"})
        doc = self.doc("/api/agile/p/{}/export/requirements.docx?lang=fr&numbers={}".format(self.pid, made["number"]))
        for text in ("Acronymes", "Electrostatic Discharge", "Received, In Analysis", "A = Analysis"):
            self.assertIn(text, doc)
        self.assertNotIn("Reçue", doc)

    def test_05_hand_edited_page_left_alone(self):
        page = self.page(glossary.ACR_TITLE)
        href = self.admin.get("/api/testing/lists")["glossary_pages"][glossary.ACR_TITLE]
        key, _, page_id = href.replace("#/dynamite/", "").partition("/page/")
        pid = self.projects[key]
        body = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Edited"}]}]}
        self.admin.put("/api/dynamite/p/{}/pages/{}".format(pid, page_id), {"title": page["title"], "body": body,
                                                                            "base_version": page["version"],
                                                                            "note": "Correction manuelle"})
        self.admin.post("/api/testing/lists", {"kind": "acronym", "code": "PPE", "label": "Personal Protective Equipment"})
        self.assertNotIn("Personal Protective Equipment", json.dumps(self.page(glossary.ACR_TITLE)["body"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
