"""Goldmine CSV (D-A-034): client spec with French headers, re-import by
external ID, workflow + verification guard, actionable errors.

    python -m unittest tests.test_goldmine_csv -v
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

SPEC = ("ID;Énoncé;Catégorie;Criticité;Méthode;Critère d'acceptation;Colonne client\r\n"
        "SYS-100;Le produit doit supporter 3000 cycles.;Performance;C;T;80 % de capacité après 3000 cycles;x\r\n"
        "SYS-101;Le firmware doit journaliser les défauts.;Fonctionnelle;D;D, A;;y\r\n")


class GoldmineCsvTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "gc.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "REQ", "name": "REQ", "description": ""})
        cls.base = "/api/agile/p/{}".format(cls.admin.get("/api/admin/projects")["projects"][0]["id"])
        cls.admin.post(cls.base + "/init")
        cls.admin.post(cls.base + "/goldmine/setup")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def imp(self, text):
        return self.admin.post(self.base + "/import/requirements", {"csv": text})

    def export_rows(self):
        with self.admin.opener.open(self.url + self.base + "/export/requirements") as resp:
            return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))

    def test_01_client_spec_with_french_headers(self):
        result = self.imp(SPEC)
        self.assertEqual([r["status"] for r in result["report"]], ["créée", "créée"])
        self.assertIn("Colonne client", result["note"])
        req = self.admin.get(self.base + "/issues/2")["issue"]["requirement"]
        self.assertEqual((req["category"], req["criticality"], req["verification_method"]),
                         ("functional", "D", "AD"))
        self.assertEqual(self.admin.get(self.base + "/issues/1")["issue"]["status_name"], "Received")

    def test_02_reimport_updates_by_external_id(self):
        revised = SPEC.replace("3000 cycles.", "3500 cycles.")
        result = self.imp(revised)
        self.assertEqual(result["report"][0]["status"], "mise à jour (par ID externe)")
        self.assertIn("sans changement de révision", result["report"][0]["warning"])
        self.assertEqual(len(self.export_rows()), 2)  # no duplicate

    def test_03_status_follows_workflow_and_guard(self):
        head = "key,status,verification_ref,statement\r\n"
        r = self.imp(head + "REQ-1,Vérifiée,,Le produit doit supporter 3500 cycles.")["report"][0]
        self.assertEqual(r["status"], "refusée")
        self.assertIn("« Received » → « Verified »", r["reason"])
        for step in ("In Analysis", "Accepted", "Allocated", "Implemented", "In Verification"):
            r = self.imp(head + "REQ-1,{},,Le produit doit supporter 3500 cycles.".format(step))["report"][0]
            self.assertTrue(r["status"].startswith("mise à jour"), r)
        r = self.imp(head + "REQ-1,Vérifiée,,Le produit doit supporter 3500 cycles.")["report"][0]
        self.assertIn("sans méthode ou sans réf.", r["reason"])
        r = self.imp(head + "REQ-1,Vérifiée,TP-CYC-01,Le produit doit supporter 3500 cycles.")["report"][0]
        self.assertTrue(r["status"].startswith("mise à jour"), r)  # ref given on the same line

    def test_04_every_problem_with_fix(self):
        bad = ("external_id,statement,category,criticality,verification_method,received_at\r\n"
               "SYS-200,,Magique,Z,TX,32/13/2026\r\n"
               ",Sans identifiant,,,,\r\n")
        report = self.imp(bad)["report"]
        self.assertEqual(report[0]["status"], "refusée")
        self.assertGreaterEqual(len(report[0]["problems"]), 5)
        self.assertTrue(all(p["fix"] for p in report[0]["problems"]))
        self.assertIn("external_id", report[1]["fix"])

    def test_04b_method_words_from_client_sheets(self):
        sheet = ("ID,Énoncé,Méthode\r\n"
                 "SYS-300,Le système doit A.,\"Test, Analyse\"\r\n"
                 "SYS-301,Le système doit B.,Démonstration + essai\r\n"
                 "SYS-302,Le système doit C.,Simulation\r\n")
        report = self.imp(sheet)["report"]
        self.assertEqual([r["status"][:5] for r in report], ["créée", "créée", "refus"])
        self.assertIn("IADT", report[2]["fix"])

    def test_05_missing_columns_message(self):
        with self.assertRaises(ApiFailure) as ctx:
            self.imp("Nom,Commentaire\r\nx,y")
        self.assertIn("Correctif", ctx.exception.message)

    def test_06_export_round_trip(self):
        rows = self.export_rows()
        self.assertEqual(rows[0]["key"], "REQ-1")
        self.assertEqual(rows[0]["category"], "Performance")
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
        report = self.imp(buf.getvalue())["report"]
        # D-B-069: an exported file re-imported as is changes nothing and writes nothing
        self.assertTrue(all(r["status"] == "inchangée" for r in report), report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
