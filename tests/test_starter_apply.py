"""0.60.06 (D-O-019): « Commencer » on the server -- a Project Starter file becomes a new Space, in one transaction."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))
CODES = ["LA-MAR", "LA-BES", "LB-OPT", "LB-ELE", "LB-APP", "LC-FAB", "LC-ESA"]


class StarterApplyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.result = cls.admin.post("/api/starter/apply", {"file": LAMPE})
        cls.pid = cls.result["project"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def sql(self, query, params=()):
        with db.connect() as conn:
            return [dict(r) for r in conn.execute(query, params)]

    def test_01_check_writes_nothing(self):
        chk = self.admin.post("/api/starter/check", {"file": LAMPE, "key": "LAMPEX", "drop": CODES})
        self.assertTrue(chk["ready"], chk["blocking"])
        self.assertEqual(chk["summary"]["key"], "LAMPEX")
        self.assertEqual(chk["summary"]["time_codes"], 0)
        self.assertTrue(all(m["exists"] for m in chk["team"]))
        self.assertEqual(self.sql("SELECT 1 FROM projects WHERE key = 'LAMPEX'"), [])

    def test_02_space_and_team(self):
        self.assertEqual(self.result["project"]["key"], "LAMPE")
        accounts = self.result["accounts"]
        self.assertEqual(sorted(a["username"] for a in accounts), ["ines", "maya", "samuel", "theo"])
        self.assertTrue(all(len(a["temp_password"]) >= 8 for a in accounts))
        users = self.sql("SELECT username, is_admin, must_change_password, study_profile FROM users WHERE username = 'maya'")
        self.assertEqual(users, [{"username": "maya", "is_admin": 0, "must_change_password": 1,
                                  "study_profile": "Génie mécanique"}])
        roles = {r["username"]: r["role"] for r in self.sql(
            "SELECT u.username, m.role FROM memberships m JOIN users u ON u.id = m.user_id WHERE m.project_id = ?", (self.pid,))}
        self.assertEqual(roles["maya"], "manager")
        self.assertEqual(roles["theo"], "editor")

    def test_03_requirements_tests_review(self):
        keys = self.result["requirements"]
        reqs = {r["external_id"]: r for r in self.sql(
            "SELECT r.* FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id WHERE i.project_id = ?", (self.pid,))}
        self.assertEqual(len(reqs), 8)
        self.assertTrue(all(r["standard_review"] == "to_verify" for r in reqs.values()))
        self.assertEqual(reqs["REQ-1"]["derived_from"], keys["BES-1"])
        self.assertEqual(reqs["REQ-3"]["source_doc"], "CSA C22.2 No. 62368-1 / UL 62368-1")
        tests = {t["test_id"]: t for t in self.sql("SELECT * FROM testing_tests WHERE project_id = ?", (self.pid,))}
        self.assertEqual(len(tests), 6)  # only the file's tests: the reference catalogue is not copied in
        self.assertTrue(all(t["status"] == "Draft" and t["review"] == "to_verify" for t in tests.values()))
        self.assertEqual(reqs["REQ-6"]["test_ref"], self.result["tests"]["ESSAI-6"])
        self.assertEqual(tests[self.result["tests"]["ESSAI-6"]]["subject"], "mech")

    def test_04_pages_are_ai_drafts(self):
        pages = self.admin.get("/api/dynamite/p/{}/pages".format(self.pid))["pages"]
        self.assertEqual(len(pages), 3)
        home = [p for p in pages if p["parent_id"] is None]
        self.assertEqual([p["title"] for p in home], ["Lampe de bureau connectée"])
        page = self.admin.get("/api/dynamite/p/{}/pages/{}".format(self.pid, pages[1]["id"]))
        self.assertIn("Brouillon IA", json.dumps(page, ensure_ascii=False))

    def test_05_time_codes(self):
        row = self.sql("SELECT task_set FROM timesheet_projects WHERE project_id = ?", (self.pid,))[0]
        self.assertEqual(row["task_set"], "starter-lampe")
        codes = [r["code"] for r in self.sql("SELECT l.code FROM timesheet_budget_lines l JOIN timesheet_budget_sets s "
                                             "ON s.id = l.set_id WHERE s.key = 'starter-lampe' ORDER BY l.position")]
        self.assertEqual(codes, CODES)
        label = self.sql("SELECT label FROM timesheet_budget_lines WHERE code = 'LB-OPT'")[0]["label"]
        self.assertEqual(label, "Concepts · Optique et dissipation thermique")

    def test_06_nothing_twice_and_renames(self):
        with self.assertRaises(ApiFailure) as ctx:
            self.admin.post("/api/starter/apply", {"file": LAMPE})
        self.assertEqual(ctx.exception.status, 409)
        chk = self.admin.post("/api/starter/check", {"file": LAMPE, "key": "LAMPE2"})
        self.assertEqual(sorted(b["value"] for b in chk["blocking"]), sorted(CODES))
        with self.assertRaises(ApiFailure):  # a taken code: nothing at all is created, not even the Space
            self.admin.post("/api/starter/apply", {"file": LAMPE, "key": "LAMPE2"})
        self.assertEqual(self.sql("SELECT 1 FROM projects WHERE key = 'LAMPE2'"), [])
        renames = {c: "M" + c[1:] for c in CODES}
        done = self.admin.post("/api/starter/apply", {"file": LAMPE, "key": "LAMPE2", "renames": renames})
        self.assertEqual(sorted(done["reused"]), ["ines", "maya", "samuel", "theo"])
        self.assertEqual(done["accounts"], [])
        self.assertEqual(len(self.sql("SELECT 1 FROM users WHERE username = 'maya'")), 1)

    def test_07_untested_requirement_gets_a_placeholder(self):
        data = json.loads(json.dumps(LAMPE))
        data["project"]["key"] = "LAMPE3"
        data["tests"] = [t for t in data["tests"] if t["ref"] != "ESSAI-6"]
        res = self.admin.post("/api/starter/apply", {"file": data, "drop": CODES})
        self.assertEqual(res["placeholder_for"], ["REQ-6"])
        row = self.sql("SELECT r.test_ref FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id "
                       "WHERE i.project_id = ? AND r.external_id = 'REQ-6'", (res["project"]["id"],))[0]
        title = self.sql("SELECT title FROM testing_tests WHERE project_id = ? AND test_id = ?",
                         (res["project"]["id"], row["test_ref"]))[0]["title"]
        self.assertEqual(title, "Essai à définir (Project Starter)")
        sets = self.sql("SELECT task_set FROM timesheet_projects WHERE project_id = ?", (res["project"]["id"],))
        self.assertEqual([s["task_set"] for s in sets], ["pdp"])  # every code dropped: the PDP codes stay

    def test_08_admins_only_and_journal(self):
        member = Client(self.url)
        member.login("maya", self.result["accounts"][[a["username"] for a in self.result["accounts"]].index("maya")]
                     ["temp_password"], new_password="Nouveau-mot-de-passe-1")
        with self.assertRaises(ApiFailure) as ctx:
            member.post("/api/starter/check", {"file": LAMPE})
        self.assertEqual(ctx.exception.status, 403)
        actions = {r["action"] for r in self.sql("SELECT action FROM audit_log")}
        self.assertTrue({"starter_applied", "project_created", "user_created", "testing_test_create"} <= actions)


if __name__ == "__main__":
    unittest.main()
