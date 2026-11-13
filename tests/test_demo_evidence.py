"""0.60.99 (D-O-106): the Rover's evidence is consistent -- what a quality auditor checks first in the demo.

The site is first started as a DEMO filled by 0.60.98 (the repair held back, the two HeadLamp examples added through the
API as the former path did), then restarted: the repair runs once and leaves nothing that says more than its evidence."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.help import demo_evidence  # noqa: E402
from modules.testing import bundles  # noqa: E402
from tools.api_client import Client  # noqa: E402

HEADLAMP = [("Prise en main en une semaine", {"external_id": "HL-001", "category": "performance", "verification_method": "D",
                                              "test_ref": "TST-VER-03", "statement": "Un nouveau membre de l'équipe réalise le parcours.",
                                              "acceptance_criteria": "En 5 jours ou moins.", "source_doc": "Exemple DEMO"}),
            ("Heures de formation déclarées", {"external_id": "HL-002", "category": "functional", "verification_method": "I",
                                               "test_ref": "TST-VER-01", "statement": "Chaque séance est déclarée dans Timesheet.",
                                               "acceptance_criteria": "Une plage avec un code du PDP.", "source_doc": "Exemple DEMO"})]


class DemoEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(data_dir)
        cls.cfg["port"] = 0
        cls.cfg["require_initials"] = False
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        with mock.patch.object(demo_evidence, "ensure_evidence", lambda ctx: None):
            startup.run(data_dir, cls.cfg)  # a DEMO as 0.60.98 left it
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/admin/projects")["projects"] if p["key"] == "DEMO")
        base = "/api/agile/p/{}".format(cls.pid)
        cls.before = cls.admin.get("/api/testing/verification?space=DEMO")["counts"]
        for title, fields in HEADLAMP:
            cls.admin.post(base + "/goldmine/requirements", dict(fields, title=title))
        startup.run(data_dir, cls.cfg)  # 0.60.99 arrives: the repair runs
        startup.run(data_dir, cls.cfg)  # a restart never applies it twice

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def one(self, sql, *args):
        with db.connect() as conn:
            return conn.execute(sql, args).fetchone()[0]

    def goldmine(self):
        return self.admin.get("/api/agile/p/{}/goldmine".format(self.pid))

    def test_01_once(self):
        self.assertEqual(self.before["verified"], 0)  # 0.60.98: « Verified » in Goldmine, « Not run » in Testing
        self.assertEqual(self.one("SELECT COUNT(*) FROM audit_log WHERE action = ?", demo_evidence.DONE), 1)

    def test_02_status_follows_the_verdict(self):
        verification = self.admin.get("/api/testing/verification?space=DEMO")
        rows = verification["requirements"]
        self.assertGreaterEqual(verification["counts"]["verified"], 10)
        for r in rows:
            self.assertEqual(r["status"] == "Verified", r["verdict"] in ("verified", "derogation"), r)
        gm = self.goldmine()
        self.assertEqual(gm["gaps"]["no_verification_ref"], [])
        refs = {r["external_id"]: r["verification_ref"] for r in gm["requirements"] if r["status_name"] == "Verified"}
        self.assertTrue(all(ref.startswith("TP-ROVER-") for ref in refs.values()), refs)

    def test_03_closed_plan_has_its_results_and_evidence(self):
        with db.connect() as conn:
            plans = conn.execute("SELECT * FROM testing_plans WHERE project_id = ? AND status IN ('closed', 'results')",
                                 (self.pid,)).fetchall()
            self.assertEqual(len(plans), 2)
            for p in plans:
                self.assertEqual(bundles.close_blockers(conn, p), [], p["code"])

    def test_04_ecn_and_problem_report(self):
        with db.connect() as conn:
            rows = conn.execute("SELECT i.number, s.name AS status, c.approvers, c.decision_date, c.verification_ref "
                                "FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id JOIN agile_statuses s "
                                "ON s.id = i.status_id LEFT JOIN agile_changes c ON c.issue_id = i.id "
                                "WHERE i.project_id = ? AND t.change_role IN ('pr', 'ecn') ORDER BY i.number", (self.pid,)).fetchall()
        ecns = [r for r in rows if r["approvers"] is not None and r["status"] != "Derived to ECN" and r["decision_date"]]
        self.assertEqual(len(ecns), 2)
        closed = [r for r in rows if r["status"] == "Closed" and r["verification_ref"]]
        self.assertTrue(closed and "refait" in closed[0]["verification_ref"])
        self.assertEqual(sum(1 for r in rows if r["status"] == "Derived to ECN"), 1)  # the one whose ECN is still open

    def test_05_headlamp_examples_rejected_never_deleted(self):
        gm = self.goldmine()
        hl = {r["external_id"]: r["status_name"] for r in gm["requirements"] if r["external_id"].startswith("HL-")}
        self.assertEqual(hl, {"HL-001": "Rejected", "HL-002": "Rejected"})
        self.assertEqual(gm["gaps"]["no_need"], [])
        listed = {r["external_id"] for r in self.admin.get("/api/testing/verification?space=DEMO")["requirements"]}
        self.assertFalse(listed & {"HL-001", "HL-002"})
        self.assertEqual(self.one("SELECT COUNT(*) FROM agile_comments WHERE body LIKE '%HeadLamp%'"), 2)


if __name__ == "__main__":
    unittest.main()
