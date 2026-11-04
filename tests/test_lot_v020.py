"""0.31.0: central lists of the Testing base (equipment, locations, product functions), traceability source, BDC page
of the product functions (D-B-082) and Word exports in the document template (D-B-083).

    python -m unittest tests.test_lot_v020 -v
"""
import csv
import io
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
from modules.testing.data_lists import EQUIPMENT, FUNCTIONS, LOCATIONS  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV020Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = cls.cfg = load_config(cls.data_dir)
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
        cls.tom.login(c["username"], c["temp_password"], "Essai-Lot-Vingt-2026!")
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["REQ"]
        cls.base = "/api/agile/p/{}".format(cls.pid)
        cls.tom.get("/api/testing/tests")  # joins TESTING as editor
        for code, label in (("F1", "Coller deux pièces"), ("F1.1", "Chauffer la colle")):  # 0.60.01: functions of the team
            cls.admin.post("/api/testing/lists", {"kind": "function", "code": code, "label": label})

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
            return resp.read(), resp.headers

    def test_01_lists_and_defaults(self):
        data = self.tom.get("/api/testing/lists")
        count = {k: sum(1 for x in data["items"] if x["kind"] == k) for k in ("location", "equipment", "function")}
        self.assertEqual(count, {"location": len(LOCATIONS), "equipment": len(EQUIPMENT), "function": len(FUNCTIONS) + 2})
        self.assertFalse(data["can_manage"])
        self.assertTrue(data["bdc_href"])  # the product functions page of the BDC
        tests = {t["test_id"]: t for t in self.tom.get("/api/testing/tests")["tests"]}
        self.assertEqual(tests["TST-ENV-03"]["functions"], "")
        self.assertIn("EQ-VIB", tests["TST-ENV-03"]["equipment"])
        self.assertEqual(tests["TST-CUS-01"]["location"], "LAB")
        self.assertIn("Abnormal operation", tests["TST-ELE-04"]["section"])
        self.assertEqual(tests["TST-ENV-03"]["source"], "IEC 60068-2-6, Test Fc — Vibration (sinusoidal)")
        self.assertIn("TST-SW-01", tests)

    def test_02_only_list_entries(self):
        url = "/api/testing/tests/TST-ENV-02"
        self.assertEqual(self.status(lambda: self.tom.patch(url, {"equipment": "EQ-DUST, EQ-FANTAISIE"})), 400)
        self.assertEqual(self.status(lambda: self.tom.patch(url, {"location": "Chez moi"})), 400)
        self.assertEqual(self.status(lambda: self.tom.patch(url, {"location": "LAB, EXT"})), 400)  # one location
        self.tom.patch(url, {"equipment": "eq-dust; EQ-CLIM", "location": "ext", "functions": "f1"})
        t = self.tom.get(url)["test"]
        self.assertEqual((t["equipment"], t["location"], t["functions"]), ("EQ-DUST, EQ-CLIM", "EXT", "F1"))

    def test_03_lists_managed_by_testing_admins(self):
        self.assertEqual(self.status(lambda: self.tom.post("/api/testing/lists", {"kind": "location", "code": "NRC",
                                                                                   "label": "CNRC"})), 403)
        made = self.admin.post("/api/testing/lists", {"kind": "equipment", "code": "EQ-HALT", "label": "Enceinte HALT",
                                                      "category": "Environnement"})
        self.assertEqual(self.status(lambda: self.admin.post("/api/testing/lists", {"kind": "function", "code": "XYZ-9",
                                                                                     "label": "x"})), 400)
        self.tom.patch("/api/testing/tests/TST-ENV-01", {"equipment": "EQ-HALT"})
        self.admin.patch("/api/testing/lists/{}".format(made["id"]), {"active": False})
        self.tom.patch("/api/testing/tests/TST-ENV-01", {"notes": "Garde son équipement désactivé."})  # kept where used
        self.assertEqual(self.status(lambda: self.tom.patch("/api/testing/tests/TST-MEC-01", {"equipment": "EQ-HALT"})), 400)
        used = [x for x in self.admin.get("/api/testing/lists")["items"] if x["code"] == "EQ-HALT"][0]
        self.assertEqual((used["used"], used["active"]), (1, False))
        self.admin.post("/api/testing/lists", {"kind": "function", "code": "F2.3", "label": "Afficher l'état",
                                               "details": {"primary": "Interface"}})

    def test_04_requirement_functions_and_source(self):
        url = self.base + "/goldmine/requirements"
        self.assertEqual(self.status(lambda: self.tom.post(url, {"statement": "x", "test_ref": "TST-ENV-03",
                                                                 "functions": "F99"})), 400)
        made = self.tom.post(url, {"statement": "Le module doit tenir les vibrations.", "test_ref": "TST-ENV-03",
                                   "functions": "f1"})
        item = [r for r in self.tom.get(self.base + "/goldmine")["requirements"] if r["key"] == made["key"]][0]
        self.assertEqual(item["functions"], "F1")
        self.assertEqual(item["test_source"], "TST-ENV-03 Transport vibration (IEC 60068-2-6, Test Fc — Vibration (sinusoidal))")
        data, _ = self.download(self.tom, self.base + "/export/requirements")
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
        row = [r for r in rows if r["key"] == made["key"]][0]
        self.assertEqual((row["functions"], row["test_source"]), ("F1", item["test_source"]))
        text = data.decode("utf-8-sig").replace(",F1,", ",F99,")
        res = self.tom.post(self.base + "/import/requirements", {"csv": text})
        self.assertIn("refusée", [r["status"] for r in res["report"]])

    def test_05_word_exports(self):
        data, headers = self.download(self.tom, "/api/testing/export.docx?ids=TST-ENV-03,TST-ELE-04&title=Plan%20EQP"
                                                 "&docno=TSP-00001&rev=B&lang=en&group=function")
        self.assertIn("TSP-00001", headers.get("Content-Disposition"))
        doc = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        head = zipfile.ZipFile(io.BytesIO(data)).read("word/header1.xml").decode("utf-8")
        self.assertIn("TST-ENV-03 - Test - Transport vibration", doc)
        self.assertIn('w:val="CBitemnamerequirement"', doc)
        self.assertIn("Source : IEC 60068-2-6, Test Fc — Vibration (sinusoidal)", doc)
        self.assertNotIn("{{", doc + head)
        self.assertIn("TSP-00001", head)
        made = self.tom.post(self.base + "/goldmine/requirements", {"statement": "Le produit doit être isolé.",
                                                                    "external_id": "REQ-EQP-1", "test_ref": "TST-ELE-02",
                                                                    "functions": "F1.1"})
        data, _ = self.download(self.tom, self.base + "/export/requirements.docx?lang=fr&group=category&numbers={}".format(
            made["number"]))
        doc = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        self.assertIn("REQ-EQP-1 - Requirement - ", doc)
        self.assertIn("Vérifiée par : TST-ELE-02", doc)
        self.assertEqual(self.status(lambda: self.tom.get("/api/testing/export.docx?group=nope")), 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
