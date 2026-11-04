"""0.26.0: Goldmine -- export of the filtered subset (D-B-069) and re-import
with a preview of every value that would be overwritten, confirmed twice in
the browser (D-B-070).

    python -m unittest tests.test_lot_v016 -v
"""
import csv
import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

SPEC = ("ID;Énoncé;Catégorie;Criticité\r\n"
        "SYS-1;Le produit doit supporter 3000 cycles.;Performance;C\r\n"
        "SYS-2;Le firmware doit journaliser les défauts.;Fonctionnelle;D\r\n"
        "SYS-3;Le produit doit peser moins de 90 kg.;Performance;E\r\n")


class GoldmineSubsetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False
        db.init_db(data_dir / "v16.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "SUB", "name": "SUB", "description": ""})
        cls.base = "/api/agile/p/{}".format(cls.admin.get("/api/admin/projects")["projects"][0]["id"])
        cls.admin.post(cls.base + "/init")
        cls.admin.post(cls.base + "/goldmine/setup")
        cls.admin.post(cls.base + "/import/requirements", {"csv": SPEC})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def export(self, query=""):
        with self.admin.opener.open(self.url + self.base + "/export/requirements" + query) as resp:
            disposition = resp.headers.get("Content-Disposition", "")
            return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig")))), disposition

    def fields(self, ext):
        for r in self.admin.get(self.base + "/goldmine")["requirements"]:
            if r["external_id"] == ext:
                return r
        raise AssertionError(ext)

    def test_01_export_only_the_selection(self):
        rows, _ = self.export()
        self.assertEqual(len(rows), 3)
        numbers = sorted(int(r["key"].split("-")[1]) for r in rows)
        sel, disposition = self.export("?numbers={}-{}".format(numbers[0], numbers[1]))
        self.assertEqual([r["external_id"] for r in sel], ["SYS-1", "SYS-2"])
        self.assertIn("selection-2", disposition)
        sel, _ = self.export("?numbers={}".format(numbers[2]))
        self.assertEqual([r["external_id"] for r in sel], ["SYS-3"])
        with self.assertRaises(ApiFailure) as ctx:
            self.admin.get(self.base + "/export/requirements?numbers=abc")
        self.assertIn("Correctif", ctx.exception.message)

    def test_02_preview_lists_overwrites_and_writes_nothing(self):
        text = SPEC.replace("3000 cycles", "4000 cycles").replace("défauts.;Fonctionnelle;D", "défauts.;Fonctionnelle;B")
        res = self.admin.post(self.base + "/import/requirements", {"csv": text, "mode": "preview"})
        self.assertEqual(res["overwrites"], 2)
        self.assertEqual(res["overwrite_rows"], 2)
        by_line = {r["line"]: r for r in res["report"]}
        self.assertEqual(by_line[2]["differences"][0]["field"], "statement")
        self.assertEqual(by_line[3]["differences"][0]["current"], "D")
        self.assertEqual(by_line[3]["differences"][0]["new"], "B")
        self.assertEqual(by_line[4]["status"], "inchangée")
        self.assertIn("3000", self.fields("SYS-1")["statement"])  # rolled back
        self.assertEqual(self.fields("SYS-2")["criticality"], "D")

    def test_03_apply_keeps_the_unchecked_values(self):
        text = SPEC.replace("3000 cycles", "5000 cycles").replace("défauts.;Fonctionnelle;D", "défauts.;Fonctionnelle;A")
        with self.assertRaises(ApiFailure) as ctx:  # the user confirmed 2, but only 1 is left after « keep »
            self.admin.post(self.base + "/import/requirements", {"csv": text, "mode": "apply",
                                                                 "keep": {"3": ["criticality"]}, "confirm_overwrites": 2})
        self.assertIn("La base a changé", ctx.exception.message)
        self.assertIn("3000", self.fields("SYS-1")["statement"])  # nothing written
        res = self.admin.post(self.base + "/import/requirements", {"csv": text, "mode": "apply",
                                                                   "keep": {"3": ["criticality"]}, "confirm_overwrites": 1})
        self.assertEqual(res["kept"], 1)
        self.assertIn("5000", self.fields("SYS-1")["statement"])
        self.assertEqual(self.fields("SYS-2")["criticality"], "D")  # kept

    def test_04_list_carries_the_assignee_for_my_items(self):
        # D-B-071: « Mes éléments » filters in the browser on assignee_id; it was missing from the list
        number = self.fields("SYS-3")["number"]
        me = self.admin.get("/api/me")["user"]["id"]
        self.admin.patch(self.base + "/issues/{}".format(number), {"assignee_id": me})
        r3, r1 = self.fields("SYS-3"), self.fields("SYS-1")
        self.assertEqual(r3["assignee_id"], me)
        self.assertTrue(r3["assignee_name"])
        self.assertIsNone(r1["assignee_id"])  # generic content, nobody owns it

