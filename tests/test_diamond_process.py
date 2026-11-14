"""0.60.103 (D-O-113 to D-O-115): Diamond -- the process side: the Rover's lines, PFMEA, control plans, measurements and waves;
the access list of the process side (and DEMO, where whoever joins sees it); the PFMEA with its S inherited and locked, the
drafts of the AI reviewed row by row, an action followed in Agile; several control plans (one per line configuration), the
CC without a Reaction Plan; Cpk / Ppk; the waves of « Prioriser » and the due date of the ticket that follows; the switches
of ⚙ Admin → Modules et fonctions; an ECN on a dimension: everything citing the C-n « à revoir », then « Revu »."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, spacecopy, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import capability as CAP  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class ProcessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "p.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/me")["projects"] if p["key"] == "DEMO")
        cls.base = "/api/diamond/p/{}".format(cls.pid)
        cls.users = {}
        for name, role in (("eleve", "editor"), ("lectrice", "reader"), ("etudiant", None)):
            made = cls.admin.post("/api/admin/users", {"username": name, "display_name": name.capitalize()})
            if role:
                cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": role})
            client = Client(cls.url)
            client.login(name, made["temp_password"], new_password="Procede-2026!")
            cls.users[name] = (made["user"]["id"], client)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as caught:
            fn(*args)
        self.assertEqual(caught.exception.status, status, caught.exception)
        return str(caught.exception)

    def client(self, name):
        return self.users[name][1]

    def chars(self):
        return {c["code"]: c for c in self.admin.get(self.base + "/characteristics")["items"]}

    def pf(self):
        return {r["code"]: r for r in self.admin.get(self.base + "/pfmea")["rows"]}

    def op(self, line, op):
        lines = self.admin.get(self.base + "/process")["lines"]
        return next(o["id"] for x in lines if x["number"] == line for o in x["operations"] if o["op"] == op)

    def test_01_rover(self):
        for table in ("diamond_lines", "diamond_operations", "diamond_control_points", "diamond_process_access", "diamond_pfmea",
                      "diamond_control_plans", "diamond_cp_items", "diamond_measurements", "diamond_waves", "diamond_review_flags"):
            self.assertIn(table, spacecopy.DIAMOND)
        pr = self.admin.get(self.base + "/process")
        self.assertEqual([x["code"] for x in pr["lines"]], ["L1", "L2"])
        self.assertEqual([o["op"] for o in pr["lines"][0]["operations"]], [10, 20, 30, 40, 50, 60, 70])
        self.assertEqual(pr["checks"], [])  # every special C-n has a control point
        access = {a["name"]: a for a in pr["access"]}
        self.assertTrue(access["Nina (exemple)"]["granted"])
        self.assertFalse(access["Alexis (exemple)"]["granted"])
        self.assertFalse(access["Nina (exemple)"]["active"])  # the demo accounts cannot sign in: listed, marked
        rows = self.pf()
        self.assertEqual(len(rows), 14)
        self.assertEqual((rows["PF-60.1"]["s"], rows["PF-60.1"]["inherited_s"], rows["PF-60.1"]["ap"]), (9, 9, "H"))
        self.assertEqual(rows["PF-70.1"]["state"], "draft")
        self.assertTrue(rows["PF-30.2"]["ticket"]["key"].startswith("DEMO-"))
        cp = self.admin.get(self.base + "/cplans")
        self.assertEqual([p["number"] for p in cp["plans"]], [1, 2, 3])
        self.assertEqual([i["code"] for i in cp["plans"][0]["items"]], ["CP-R.1", "CP-R.2", "CP-R.3", "CP-R.4", "CP-R.5"])
        self.assertEqual(cp["checks"], [])
        c = self.chars()
        self.assertEqual((c["C-10"]["status"], c["C-10"]["cpk"]), ("capable", 1.82))
        self.assertEqual(c["C-14"]["cpk"], 1.21)
        self.assertEqual(c["C-14"]["status_label"], "Sous l'exigé · " + rows["PF-30.2"]["ticket"]["key"])
        self.assertEqual((c["C-21"]["status"], c["C-21"]["cpk"]), ("capable", 1.47))
        self.assertEqual(c["C-16"]["status"], "study")
        self.assertEqual(c["C-05"]["cpk_text"], "essai 100 %")
        self.assertEqual(c["C-14"]["pfmea_refs"], ["PF-30.1", "PF-30.2"])
        self.assertIn("PC-2 CP-30.1", c["C-14"]["cp_refs"])
        prio = self.admin.get(self.base + "/prio")
        self.assertEqual(len(prio["waves"]), 3)
        h = next(r for r in prio["rows"] if r["kind"] == "pfmea" and r["code"] == "PF-60.1")
        self.assertEqual((h["ap"], h["wave_id"]), ("H", prio["waves"][2]["id"]))  # the planning error of page 16, on purpose

    def test_02_access(self):
        eleve, eleve_id = self.client("eleve"), self.users["eleve"][0]
        for path in ("/process", "/pfmea", "/cplans"):
            self.assertIn("Accès", self.fails(403, eleve.get, self.base + path))
        self.assertFalse([r for r in eleve.get(self.base + "/prio")["rows"] if r["kind"] == "pfmea"])  # the DFMEA side only
        self.fails(403, eleve.put, self.base + "/process/access", {"user_ids": [eleve_id]})  # the Admin of the Space chooses
        granted = [a["id"] for a in self.admin.get(self.base + "/process")["access"] if a["granted"]]
        self.fails(400, self.admin.put, self.base + "/process/access", {"user_ids": granted + [self.users["etudiant"][0]]})  # not a member
        lectrice = self.users["lectrice"][0]
        self.admin.put(self.base + "/process/access", {"user_ids": granted + [eleve_id, lectrice]})
        made = eleve.post(self.base + "/process/lines", {"name": "Ligne d'essai"})
        self.assertEqual([x["code"] for x in made["lines"]][-1], "L3")
        self.fails(403, self.client("lectrice").post, self.base + "/process/lines", {"name": "Non"})  # a reader reads
        self.client("lectrice").get(self.base + "/pfmea")
        etudiant = self.client("etudiant")
        etudiant.post("/api/help/headlamp/join", {})  # DEMO is a learning Space: whoever joins it sees the process side
        etudiant.get(self.base + "/process")
        with db.connect() as conn:
            self.assertTrue(conn.execute("SELECT 1 FROM audit_log WHERE action = 'diamond_process_access'").fetchone())

    def test_03_pfmea(self):
        rows = self.pf()
        url = self.base + "/pfmea/rows/{}".format(rows["PF-60.1"]["id"])
        self.assertIn("S 5 refusée", self.fails(400, self.admin.patch, url, {"severity": 5}))
        self.assertEqual({r["code"]: r for r in self.admin.patch(url, {"severity": 10})["rows"]}["PF-60.1"]["s"], 10)
        self.assertEqual({r["code"]: r for r in self.admin.patch(url, {"severity": ""})["rows"]}["PF-60.1"]["s"], 9)
        self.fails(400, self.admin.patch, url, {"cause_5m": "météo"})
        c = self.chars()
        made = self.admin.post(self.base + "/pfmea/rows", {"operation_id": self.op(1, 30), "characteristic_id": c["C-14"]["id"],
                                                           "failure_mode": "Aimant inversé", "occurrence": 3, "detection": 4})
        new = next(r for r in made["rows"] if r["id"] == made["created"])
        self.assertEqual((new["code"], new["s"], new["state"]), ("PF-30.3", 7, "accepted"))
        prompt = self.admin.get(self.base + "/pfmea/prompt?line=1")["prompt"]
        self.assertIn("C-14", prompt)
        self.assertIn("OP30", prompt)
        answer = [{"op": "OP40", "char": "C-21", "step": "Fermer le boîtier", "failure_mode": "Joint absent", "cause_5m": "main-d'œuvre",
                   "o": 2, "d": 5},
                  {"op": "OP99", "char": "C-21", "failure_mode": "?"}, {"op": "OP30", "char": "C-99", "failure_mode": "inventée"},
                  {"op": "OP30", "char": "C-14", "failure_mode": "Note hors échelle", "o": 12, "d": 2}]
        res = self.admin.post(self.base + "/pfmea/ai", {"line": 1, "answer": "```json\n" + json.dumps(answer) + "\n```"})
        self.assertEqual(res["drafts"], 1)
        self.assertEqual(len(res["refused"]), 3)
        self.assertIn("OP99 absente de L1", res["refused"][0])
        self.assertIn("C-99 n'existe pas", res["refused"][1])
        drafts = [r for r in res["rows"] if r["state"] == "draft"]
        self.assertEqual(len(drafts), 2)
        joint = next(r for r in drafts if r["failure_mode"] == "Joint absent")
        self.assertEqual((joint["s"], joint["cause_5m"]), (6, "man"))  # inherited from the DFMEA row of C-21
        rows = self.pf()
        self.admin.post(self.base + "/pfmea/rows/{}/review".format(rows["PF-70.1"]["id"]), {"state": "rejected"})
        self.assertEqual(self.admin.post(self.base + "/pfmea/accept-all", {})["accepted"], 1)
        self.assertEqual(self.pf()["PF-70.1"]["state"], "rejected")  # kept: one knows the proposal was read
        track = self.base + "/pfmea/rows/{}/track".format(new["id"])
        self.assertIn("pas encore d'action", self.fails(400, self.admin.post, track, {}))
        self.admin.patch(self.base + "/pfmea/rows/{}".format(new["id"]), {"action": "Aimant détrompé"})
        self.assertTrue(self.admin.post(track, {})["tracked"].startswith("DEMO-"))
        self.fails(403, self.client("lectrice").patch, url, {"occurrence": 2})

    def test_04_control_plans(self):
        lines = {x["number"]: x for x in self.admin.get(self.base + "/process")["lines"]}
        made = self.admin.post(self.base + "/cplans/plans", {"title": "Pré-série", "scope": "assembly", "line_id": lines[2]["id"], "phase": "prelaunch"})
        plan = next(p for p in made["plans"] if p["id"] == made["created"])
        self.assertEqual((plan["number"], plan["phase"]), (4, "prelaunch"))
        items = self.base + "/cplans/plans/{}/items".format(plan["id"])
        c10 = self.chars()["C-10"]["id"]
        self.assertIn("pas sur la ligne", self.fails(400, self.admin.post, items, {"operation_id": self.op(1, 60), "characteristic_id": c10}))
        self.fails(400, self.admin.post, items, {"operation_id": self.op(2, 20)})  # neither a C-n nor a process characteristic
        res = self.admin.post(items, {"operation_id": self.op(2, 20), "characteristic_id": c10, "technique": "Multimètre"})
        row = next(i for p in res["plans"] if p["id"] == plan["id"] for i in p["items"])
        self.assertEqual(row["code"], "CP-20.1")
        self.assertTrue(any(x.startswith("PC-4 : CP-20.1") and "Reaction Plan" in x for x in res["checks"]))  # a CC without its reaction
        res = self.admin.patch(self.base + "/cplans/items/{}".format(row["id"]), {"reaction_plan": "Arrêt, ré-étalonner"})
        self.assertFalse(any("Reaction Plan" in x for x in res["checks"]))
        self.assertIn("PC-4 CP-20.1", self.chars()["C-10"]["cp_refs"])
        self.fails(400, self.admin.patch, self.base + "/cplans/plans/{}".format(plan["id"]), {"phase": "série"})
        res = self.admin.patch(self.base + "/cplans/plans/{}".format(plan["id"]), {"phase": "production", "revision": "C"})
        self.assertEqual(next(p for p in res["plans"] if p["id"] == plan["id"])["revision"], "C")
        self.admin.patch(self.base + "/cplans/items/{}".format(row["id"]), {"delete": True})
        self.assertNotIn("PC-4 CP-20.1", self.chars()["C-10"]["cp_refs"])

    def test_05_capability(self):
        st = CAP.stats([10.0, 10.2, 9.8, 10.1, 9.9], 9.0, 11.0)
        self.assertEqual((st["n"], st["ppk"], st["cpk"], st["short"]), (5, 2.11, 1.37, True))
        self.assertEqual(CAP.stats([10.0, 10.2, 9.8, 10.1, 9.9], None, 11.0)["cpk"], 1.37)  # one-sided
        self.assertIsNone(CAP.stats([10.0], 9.0, 11.0)["cpk"])
        self.assertEqual([v for v, _d, _s in CAP.parse("2,05\n2,10\n", "2026-11-13")[0]], [2.05, 2.1])  # a decimal comma
        values, problems = CAP.parse("Valeur,Date\n2.05,2026-11-01\nx,2026-11-02\n", "2026-11-13")
        self.assertEqual((values, len(problems)), ([(2.05, "2026-11-01", "")], 1))
        self.assertIn("Ligne 3", problems[0])
        self.assertEqual(CAP.parse("2,05;2026-11-01;L1", "d")[0], [(2.05, "2026-11-01", "L1")])
        c16 = self.chars()["C-16"]["id"]
        res = self.admin.post(self.base + "/cplans/measures", {"characteristic_id": c16, "values": "1,0\n1,1\n0,9"})
        self.assertEqual((res["added"], res["stats"]["n"], res["stats"]["short"]), (3, 3, True))
        self.assertIn("Aucune valeur", self.fails(400, self.admin.post, self.base + "/cplans/measures", {"characteristic_id": c16, "values": "abc"}))
        self.fails(403, self.client("lectrice").post, self.base + "/cplans/measures", {"characteristic_id": c16, "values": "1,0"})
        self.assertEqual(self.client("lectrice").get(self.base + "/cplans/measures/{}".format(c16))["stats"]["n"], 3)

    def test_06_waves_and_switches(self):
        prio = self.admin.get(self.base + "/prio")
        w1, w2 = prio["waves"][0], prio["waves"][1]
        h = next(r for r in prio["rows"] if r["code"] == "PF-60.1")
        moved = self.admin.post(self.base + "/prio/move", {"kind": "pfmea", "id": h["id"], "wave_id": w1["id"]})
        self.assertEqual(next(r for r in moved["rows"] if r["code"] == "PF-60.1")["due"], w1["due_date"])
        self.fails(403, self.client("lectrice").post, self.base + "/prio/move", {"kind": "pfmea", "id": h["id"], "wave_id": None})
        res = self.admin.patch(self.base + "/prio/waves/{}".format(w2["id"]), {"due_date": "2027-04-15"})
        tracked = next(r for r in res["rows"] if r["code"] == "PF-30.2")
        self.assertEqual(tracked["due"], "2027-04-15")
        with db.connect() as conn:
            issue = conn.execute("SELECT id, due_date FROM agile_issues WHERE project_id = ? AND number = ?",
                                 (self.pid, int(tracked["ticket"]["key"].split("-")[1]))).fetchone()
            self.assertEqual(issue["due_date"], "2027-04-15")  # the ticket follows its wave
            self.assertTrue(conn.execute("SELECT 1 FROM agile_history WHERE issue_id = ? AND field = 'due_date' AND new_value = '2027-04-15'",
                                         (issue["id"],)).fetchone())
        self.admin.put("/api/admin/features", {"features": {"diamond_pfmea": False}})
        try:
            self.assertIn("Modules et fonctions", self.fails(404, self.admin.get, self.base + "/pfmea"))
            prio = self.admin.get(self.base + "/prio")
            self.assertFalse(prio["pfmea"])
            self.assertFalse([r for r in prio["rows"] if r["kind"] == "pfmea"])
            self.admin.get(self.base + "/process")
            self.admin.get(self.base + "/cplans")
            self.admin.put("/api/admin/features", {"features": {"diamond_process": False}})
            self.fails(404, self.admin.get, self.base + "/cplans")  # the control plans need the assembly lines
            self.admin.get(self.base + "/dfmea")
        finally:
            self.admin.put("/api/admin/features", {"features": {"diamond_pfmea": True, "diamond_process": True}})
        self.admin.get(self.base + "/pfmea")

    def test_07_ecn(self):
        c14 = self.chars()["C-14"]
        url = self.base + "/characteristics/{}".format(c14["id"])
        self.admin.patch(url, {"notes": c14["notes"] + " Revue."})  # no change of the dimension: nothing to review
        self.assertEqual(self.chars()["C-14"]["flags"], [])
        self.admin.patch(url, {"nominal": "1,8", "tol": "0,3"})
        c14 = self.chars()["C-14"]
        kinds = {f["kind"] for f in c14["flags"]}
        self.assertTrue({"pfmea", "cp_item", "capability"} <= kinds, kinds)
        self.assertEqual(c14["status"], "review")
        self.assertTrue(c14["status_label"].startswith("À revoir ("))
        self.assertTrue(self.pf()["PF-30.1"]["review"])
        cp = self.admin.get(self.base + "/cplans")
        self.assertTrue(next(i for p in cp["plans"] for i in p["items"] if i["code"] == "CP-30.1" and p["number"] == 2)["review"])
        self.fails(403, self.client("lectrice").post, url + "/reviewed", {})
        self.admin.post(url + "/reviewed", {})
        c14 = self.chars()["C-14"]
        self.assertEqual(c14["flags"], [])
        self.assertTrue(c14["status_label"].startswith("Sous l'exigé"))
        self.assertFalse(self.pf()["PF-30.1"]["review"])
        with db.connect() as conn:
            self.assertTrue(conn.execute("SELECT 1 FROM diamond_review_flags WHERE characteristic_id = ? AND reviewed_by IS NOT NULL",
                                         (c14["id"],)).fetchone())


if __name__ == "__main__":
    unittest.main()
