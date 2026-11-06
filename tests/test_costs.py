"""0.60.61 (D-O-070): Diamond → « Coûts et budget » -- assumptions, NRE, cost of each part in prototype and at three
volumes, the budget computed from them (with the Timesheet hours), the CSV, the Rover's costs in DEMO, rights, copy."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond.costs_budget import budget  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

PW = "Couts-Budget-2026!"


class CostsTest(unittest.TestCase):
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
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "LAMP", "name": "Lampe"})["project"]["id"]
        cls.demo = next(p["id"] for p in cls.admin.get("/api/admin/projects")["projects"] if p["key"] == "DEMO")
        made = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", made["temp_password"], PW)
        cls.base = "/api/diamond/p/{}/costs".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_budget_arithmetic(self):
        s = {"currency": "CAD", "proto_qty": 2, "volumes": [10, 100, 1000], "contingency": 10.0, "labour_rate": 20.0}
        lines = [{"code": "P-1", "name": "Base", "qty": 2, "proto_unit": 10.0, "prod_1": 8.0, "prod_2": None, "prod_3": 5.0},
                 {"code": "", "name": "Boîte", "qty": 1, "proto_unit": None, "prod_1": None, "prod_2": None, "prod_3": None}]
        nre = [{"amount": 1000.0, "category": "outillage", "phase": "D", "basis": "soumission"},
               {"amount": 200.0, "category": "essais", "phase": "C", "basis": "paye"}]
        b = budget(s, nre, lines, 10.0)
        self.assertEqual((b["unit_proto"], b["nre_total"], b["prototypes"], b["labour"]), (20.0, 1200.0, 40.0, 200.0))
        self.assertEqual((b["subtotal"], b["contingency"], b["total"]), (1440.0, 144.0, 1584.0))
        self.assertEqual([v["parts"] for v in b["volumes"]], [16.0, 20.0, 10.0])  # a missing production price counts at the prototype price
        self.assertEqual(b["volumes"][0]["nre_per_unit"], 120.0)
        self.assertEqual(b["volumes"][2]["programme"], 1200.0 + 1000 * 10.0)
        self.assertEqual((b["nre_committed"], b["nre_paid"]), (200.0, 200.0))
        self.assertTrue(any("prototype manquant" in c for c in b["checks"]) and any("production manquant" in c for c in b["checks"]))

    def test_02_edit_and_compute(self):
        a = self.admin
        a.patch(self.base + "/settings", {"currency": "USD", "proto_qty": "3", "volumes": [50, 500, 5000], "contingency": "12,5",
                                          "labour_rate": "30"})
        with self.assertRaises(ApiFailure):
            a.patch(self.base + "/settings", {"volumes": [500, 50, 5000]})
        d = a.post(self.base + "/nre", {"title": "Moule du boîtier", "category": "outillage", "phase": "D", "amount": "12 000", "basis": "soumission"})
        nre = d["nre"][0]
        self.assertEqual((nre["number"], nre["amount"]), (1, 12000.0))
        a.patch(self.base + "/nre/{}".format(nre["id"]), {"basis": "paye"})
        with self.assertRaises(ApiFailure) as err:
            a.post(self.base + "/nre", {"title": "", "amount": "5"})
        self.assertEqual(err.exception.status, 400)
        with self.assertRaises(ApiFailure):
            a.post(self.base + "/nre", {"title": "Négatif", "amount": "-5"})
        a.post("/api/diamond/p/{}/structure/parts".format(self.pid), {"name": "Base lestée", "kind": "designed"})
        with db.connect() as conn:
            part_id = conn.execute("SELECT id FROM diamond_parts WHERE project_id = ?", (self.pid,)).fetchone()[0]
        d = a.get(self.base)
        line = next(ln for ln in d["lines"] if ln["part_id"] == part_id)
        self.assertIsNone(line["id"])  # the part is listed before it has a price
        d = a.post(self.base + "/lines", {"part_id": part_id, "proto_unit": "25,50", "prod_1": "20"})
        with self.assertRaises(ApiFailure) as err:
            a.post(self.base + "/lines", {"part_id": part_id})
        self.assertEqual(err.exception.status, 409)
        d = a.post(self.base + "/lines", {"name": "Notice et boîte", "qty": "1", "proto_unit": "4", "prod_1": "2", "prod_2": "1,5", "prod_3": "1"})
        b = d["budget"]
        self.assertEqual(b["currency"], "USD")
        self.assertEqual(b["unit_proto"], 29.5)
        self.assertEqual(b["nre_paid"], 12000.0)
        self.assertEqual(b["volumes"][0]["parts"], 22.0)
        free = next(ln for ln in d["lines"] if ln["name"] == "Notice et boîte")
        a.post(self.base + "/lines/{}/delete".format(free["id"]))
        a.post(self.base + "/nre/{}/delete".format(nre["id"]))
        self.assertEqual(a.get(self.base)["budget"]["nre_total"], 0)
        with db.connect() as conn:
            actions = {r[0] for r in conn.execute("SELECT action FROM audit_log WHERE action LIKE 'diamond_%cost%' OR action LIKE 'diamond_nre%'")}
        self.assertTrue({"diamond_cost_settings", "diamond_nre_create", "diamond_nre_update", "diamond_nre_delete",
                         "diamond_cost_line_create", "diamond_cost_line_delete"} <= actions, actions)

    def test_03_reader_reads_only(self):
        self.assertIn("budget", self.reader.get(self.base))
        for call in (lambda: self.reader.post(self.base + "/nre", {"title": "x", "amount": 1}),
                     lambda: self.reader.patch(self.base + "/settings", {"contingency": 5})):
            with self.assertRaises(ApiFailure) as err:
                call()
            self.assertEqual(err.exception.status, 403)

    def test_04_csv(self):
        raw = self.admin.raw_get(self.base + "/export.csv")
        text = (raw[2] if isinstance(raw, tuple) else raw)
        text = text.decode("utf-8-sig") if isinstance(text, bytes) else str(text)
        self.assertIn("Budget du projet", text)
        self.assertIn("NRE;Intitulé", text)

    def test_05_rover_costs_in_demo(self):
        d = self.admin.get("/api/diamond/p/{}/costs".format(self.demo))
        self.assertEqual(len(d["nre"]), 9)
        priced = [ln for ln in d["lines"] if ln["id"]]
        self.assertEqual(len(priced), 25)  # 23 parts + 2 lines outside the parts
        self.assertEqual(d["settings"]["labour_rate"], 25.0)
        parts_100 = sum(ln["qty"] * ln["prod_1"] for ln in priced if ln["part_id"])
        self.assertAlmostEqual(parts_100, 212.3, places=1)  # the Validation Report of the Rover: about 212 $ per robot
        self.assertGreater(d["budget"]["hours"], 100)
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'demo_costs_loaded'").fetchone()[0], 1)

    def test_06_copy_takes_the_costs(self):
        made = self.admin.post("/api/admin/projects/{}/copy".format(self.demo), {"key": "ROVC", "name": "Rover copie"})
        new = made["project"]["id"]
        d = self.admin.get("/api/diamond/p/{}/costs".format(new))
        self.assertEqual(len(d["nre"]), 9)
        self.assertEqual(len([ln for ln in d["lines"] if ln["id"] and ln["part_id"]]), 23)  # linked to the copied parts
        self.assertEqual(d["settings"]["proto_qty"], 4)


if __name__ == "__main__":
    unittest.main()
