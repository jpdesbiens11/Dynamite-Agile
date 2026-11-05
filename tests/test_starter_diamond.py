"""0.60.22 (D-O-032): the Project Starter file also carries the functional tree and what derives from it -- structure
(inputs, outputs, flows), parts, project risks, first DFMEA rows -- created in the new Space by « Commencer »."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, starter, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from tools.api_client import Client  # noqa: E402

LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))


def refused(data):
    try:
        starter.parse(data)
    except ApiError as error:
        return error.message
    return ""


class StarterDiamondTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "d.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.result = cls.admin.post("/api/starter/apply", {"file": LAMPE})
        cls.pid = cls.result["project"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_created(self):
        c = self.result["counts"]
        self.assertEqual((c["diamond_functions"], c["diamond_ports"], c["diamond_flows"], c["diamond_parts"], c["diamond_risks"],
                          c["diamond_dfmea"]), (21, 6, 32, 11, 9, 22))  # 0.60.28: one row per function
        base = "/api/diamond/p/{}".format(self.pid)
        tree = self.admin.get(base + "/functions")
        self.assertEqual(tree["functions"][0]["text"] if tree["functions"][0]["is_primary"] else
                         next(f["text"] for f in tree["functions"] if f["is_primary"]), "Éclairer une surface de travail")
        s = self.admin.get(base + "/structure")
        self.assertEqual(s["checks"], [])  # the same consistent structure as the example of the screens
        self.assertEqual(s["part_stats"]["integrated"], 4)
        d = self.admin.get(base + "/dfmea")
        rows = d.get("rows") or d.get("items") or []
        self.assertEqual(len(rows), 22)  # 0.60.28 (D-O-037): the 7 rows of the file, then one per other function
        self.assertTrue(all(r["function_id"] for r in rows))
        self.assertEqual(len({r["function_id"] for r in rows}), 21)  # no function skipped, the esteem one included
        self.assertTrue(all(r["test_id"] for r in rows))  # every row with its key test
        self.assertTrue(all(r["test_space"] == "LAMPE" for r in rows[:7] if r["test_id"]))  # the file's choices kept
        with db.connect() as conn:
            note = conn.execute("SELECT notes FROM diamond_functions WHERE project_id = ? AND number = 2", (self.pid,)).fetchone()["notes"]
        self.assertIn("Brouillon IA", note)

    def test_04_reference_plan(self):
        plan = self.admin.get("/api/exploration/p/{}/plan".format(self.pid))
        codes = [t["code"] for t in plan["tasks"]]
        for code in ("J0", "A-01", "LCV", "CRV", "PDR", "CDR", "D-21", "VVR"):
            self.assertIn(code, codes)
        self.assertTrue(any(t["owner_id"] for t in plan["tasks"]))
        import datetime as dt
        start = dt.date.fromisoformat(plan["start_date"])
        end = max(dt.date.fromisoformat(t["end"]) for t in plan["tasks"])
        self.assertTrue(13 <= (end - start).days / 7 <= 17, (end - start).days / 7)  # 15 weeks by default

    def test_02_preview_counts(self):
        s = self.admin.post("/api/starter/check", {"file": dict(LAMPE, project=dict(LAMPE["project"], key="LAMPZ"))})["summary"]
        self.assertEqual((s["diamond_functions"], s["diamond_parts"]), (21, 11))

    def test_03_rules(self):
        bad = copy.deepcopy(LAMPE)
        bad["diamond"]["flows"][0]["src"] = "F3"  # a tertiary function in the general view
        self.assertIn("diamond.flows[0].src", refused(bad))
        bad = copy.deepcopy(LAMPE)
        bad["diamond"]["functions"][3]["parent"] = "F99"
        self.assertIn("introuvable plus haut", refused(bad))
        bad = copy.deepcopy(LAMPE)
        bad["diamond"]["parts"][0]["functions"] = ["F16"]  # technique: not in the structure
        self.assertIn("diamond.parts[0].functions", refused(bad))
        bad = copy.deepcopy(LAMPE)
        bad["diamond"]["dfmea"][0]["severity"] = 11
        self.assertIn("de 1 à 10", refused(bad))
        bad = copy.deepcopy(LAMPE)
        bad["diamond"]["dfmea"][0]["test"] = "ESSAI-99"
        self.assertIn("diamond.dfmea[0].test", refused(bad))
        bad = copy.deepcopy(LAMPE)
        bad["diamond"]["functions"] = []
        self.assertIn("sans arbre fonctionnel", refused(bad))
        none = copy.deepcopy(LAMPE)
        del none["diamond"]
        clean, warnings = starter.parse(none)
        self.assertEqual(clean["diamond"]["functions"], [])
        self.assertTrue(any("Aucun arbre fonctionnel" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
