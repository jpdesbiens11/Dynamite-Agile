"""0.60.54 (D-O-063): the Rover in DEMO is a project in motion in every module -- team (inactive accounts), Agile, Change
Management, Goldmine, Testing, Exploration, Timesheet, Diamond -- applied once, at week 15 of 15."""
import datetime as dt
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.help import demo_life  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class DemoLifeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(data_dir)
        cls.cfg["port"] = 0
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cls.cfg)
        startup.run(data_dir, cls.cfg)  # a restart never applies it twice
        cls.data_dir = data_dir
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/admin/projects")["projects"] if p["key"] == "DEMO")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def one(self, sql, *args):
        with db.connect() as conn:
            return conn.execute(sql, args).fetchone()[0]

    def test_01_once_and_inactive_team(self):
        self.assertEqual(self.one("SELECT COUNT(*) FROM audit_log WHERE action = 'demo_life_loaded'"), 1)
        self.assertEqual(self.one("SELECT COUNT(*) FROM users WHERE username LIKE 'demo.%' AND is_active = 0"), 4)
        with self.assertRaises(ApiFailure):
            Client(self.url).login("demo.nina", "admin")
        self.assertEqual(self.one("SELECT display_name FROM users WHERE username = 'demo.lea'"), "Léa (exemple)")

    def test_02_agile_and_changes(self):
        board = self.admin.get("/api/agile/p/{}/board".format(self.pid))
        self.assertEqual(board["sprint"]["name"], "Rover · Sprint 7")
        statuses = {i["status_name"] for i in board["issues"]}
        self.assertTrue({"Done", "In Progress", "In Review"} <= statuses)
        self.assertTrue(all(i["assignee_name"].endswith("(exemple)") for i in board["issues"]))
        self.assertEqual(self.one("SELECT COUNT(*) FROM agile_sprints WHERE project_id = ? AND state = 'closed'", self.pid), 6)
        self.assertGreaterEqual(self.one("SELECT COUNT(*) FROM agile_comments c JOIN agile_issues i ON i.id = c.issue_id WHERE i.project_id = ?", self.pid), 15)
        self.assertGreaterEqual(self.one("SELECT COUNT(*) FROM agile_links l JOIN agile_issues i ON i.id = l.source_id "
                                         "WHERE i.project_id = ? AND l.link_type = 'implements'", self.pid), 8)
        self.assertEqual(self.one("SELECT COUNT(*) FROM agile_versions WHERE project_id = ? AND is_released = 1", self.pid), 3)
        changes = self.one("SELECT COUNT(*) FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id "
                           "WHERE i.project_id = ? AND t.change_role IN ('pr', 'ecn')", self.pid)
        self.assertEqual(changes, 4)
        self.assertGreaterEqual(self.one("SELECT COUNT(*) FROM agile_change_items c JOIN agile_issues i ON i.id = c.issue_id "
                                         "WHERE i.project_id = ?", self.pid), 5)

    def test_03_goldmine_testing_plan_hours_diamond(self):
        verified = self.one("SELECT COUNT(*) FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id JOIN agile_statuses s "
                            "ON s.id = i.status_id WHERE i.project_id = ? AND s.name = 'Verified'", self.pid)
        self.assertEqual(verified, 18)  # 0.60.99 (D-O-106): every requirement whose recorded results prove it
        qa = self.admin.get("/api/agile/p/{}/qa".format(self.pid))["items"]
        self.assertEqual(sorted(q["status"] for q in qa), ["closed", "closed", "closed", "open"])
        plans = {p["code"]: p for p in self.admin.get("/api/testing/plans?space=DEMO")["plans"]}
        self.assertEqual({p["status"] for p in plans.values()}, {"closed", "results", "sent"})
        self.assertTrue(all(code.startswith("TP-ROVER-") for code in plans))  # never the TP-001, TP-002… of the teams
        self.assertEqual(self.one("SELECT COALESCE(MAX(CAST(SUBSTR(code, 4) AS INTEGER)), 0) FROM testing_plans"), 0)
        tasks = self.admin.get("/api/exploration/p/{}/plan".format(self.pid))["tasks"]
        rover = [t for t in tasks if t["phase"].startswith("Rover")]
        self.assertGreater(len(rover), 20)
        today = dt.date.today().isoformat()
        self.assertTrue(all(t["start"] <= today for t in rover if t["status"] == "done"))
        self.assertGreaterEqual(self.one("SELECT COUNT(*) FROM timesheet_entries WHERE project_id = ?", self.pid), 100)
        self.assertEqual(self.one("SELECT COUNT(*) FROM timesheet_entries WHERE project_id = ? AND work_date > ?", self.pid, today), 0)
        self.assertGreaterEqual(self.one("SELECT COUNT(*) FROM diamond_risks WHERE project_id = ? AND owner_id IS NOT NULL", self.pid), 8)

    def test_04_always_week_15(self):
        for today in (dt.date(2027, 3, 1), dt.date(2027, 3, 5)):
            clock = demo_life.Clock(today)
            self.assertEqual(clock.start.weekday(), 0)
            self.assertEqual(clock.date(15), today - dt.timedelta(days=today.weekday()))

    def test_05_a_fresh_site_stays_empty_for_a_site_move(self):
        from core import sitemove
        with db.connect() as conn:
            sitemove._empty(conn)  # the inactive example accounts do not make the site « in service »


if __name__ == "__main__":
    unittest.main()
