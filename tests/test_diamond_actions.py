"""0.60.38 (D-O-047): owners of the actions of Diamond -- the DFMEA rows get an owner, a due date and a status like the
project risks; « Suivre dans Agile » turns an action into a ticket whose status the row then reads; « Mes actions
Diamond » on the Dashboard; the actions in Bob's summary; the Project Starter names owners; additive migration."""
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


class DiamondActionsTest(unittest.TestCase):
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
        cls.pid = cls.admin.post("/api/starter/apply", {"file": LAMPE})["project"]["id"]
        cls.base = "/api/diamond/p/{}".format(cls.pid)
        cls.me = cls.admin.get("/api/me")["user"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def dfmea_row(self, data, rid):
        return next(r for r in data["rows"] if r["id"] == rid)

    def test_01_dfmea_owner_due_status(self):
        data = self.admin.get(self.base + "/dfmea")
        self.assertIn(self.me, [m["id"] for m in data["members"]])
        self.assertEqual(data["labels"]["statuses"]["done"], "Fait")
        row = data["rows"][0]
        self.assertEqual((row["action_status"], row["action_due"], row["action_owner_id"], row["ticket"]), ("open", "", None, None))
        data = self.admin.patch(self.base + "/dfmea/rows/{}".format(row["id"]), {"action": "Essai de chaleur 8 h", "action_owner_id": self.me,
                                                                                  "action_due": "2020-01-15", "action_status": "in_progress"})
        row = self.dfmea_row(data, row["id"])
        self.assertTrue(row["action_owner_name"])
        self.assertTrue(row["late"])
        self.assertTrue(any("en retard" in c for c in data["checks"]))
        for bad in ({"action_due": "15/01/2020"}, {"action_status": "fini"}, {"action_owner_id": 99999}):
            with self.assertRaises(ApiFailure) as err:
                self.admin.patch(self.base + "/dfmea/rows/{}".format(row["id"]), bad)
            self.assertEqual(err.exception.status, 400)
            self.assertIn("Correctif", str(err.exception))

    def test_02_track_dfmea_in_agile(self):
        data = self.admin.get(self.base + "/dfmea")
        empty = next(r for r in data["rows"] if not r["action"].strip())
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(self.base + "/actions/dfmea/{}/track".format(empty["id"]), {})
        self.assertEqual(err.exception.status, 400)
        row = data["rows"][0]
        data = self.admin.post(self.base + "/actions/dfmea/{}/track".format(row["id"]), {})
        key = data["tracked"]
        self.assertTrue(key.startswith("LAMPE-"))
        row = self.dfmea_row(data, row["id"])
        self.assertEqual(row["ticket"]["key"], key)
        self.assertTrue(row["status_from_ticket"])
        issue = self.admin.get("/api/agile/p/{}/issues/{}".format(self.pid, key.split("-")[1]))["issue"]
        self.assertIn("DFMEA L1", issue["title"])
        self.assertIn("#/diamond/LAMPE/dfmea", issue["description"])
        self.assertEqual(issue["due_date"], "2020-01-15")
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(self.base + "/actions/dfmea/{}/track".format(row["id"]), {})
        self.assertEqual(err.exception.status, 409)
        # the ticket reaches a done status in Agile: the row reads « Fait », no copy
        with db.connect() as conn:
            done = conn.execute("SELECT s.id FROM agile_statuses s JOIN agile_issues i ON i.project_id = ? WHERE s.category = 'done' "
                                "AND s.workflow_id = (SELECT workflow_id FROM agile_issue_types WHERE id = i.type_id) AND i.number = ?",
                                (self.pid, int(key.split("-")[1]))).fetchone()["id"]
            conn.execute("UPDATE agile_issues SET status_id = ? WHERE project_id = ? AND number = ?", (done, self.pid, int(key.split("-")[1])))
        row = self.dfmea_row(self.admin.get(self.base + "/dfmea"), row["id"])
        self.assertEqual(row["action_status"], "done")
        self.assertFalse(row["late"])

    def test_03_track_risk_and_dashboard(self):
        risks = self.admin.get(self.base + "/risks")["risks"]
        risk = next(r for r in risks if r["action"].strip())
        self.admin.patch(self.base + "/risks/{}".format(risk["id"]), {"owner_id": self.me, "due_date": "2999-12-31"})
        data = self.admin.post(self.base + "/actions/risk/{}/track".format(risk["id"]), {})
        risk = next(r for r in data["risks"] if r["id"] == risk["id"])
        self.assertEqual(risk["ticket"]["key"], data["tracked"])
        self.assertEqual(risk["status"], "open")
        dash = self.admin.get("/api/dashboard")
        text = json.dumps(dash, ensure_ascii=False)
        self.assertIn("Mes actions Diamond", text)
        self.assertIn("R-{}".format(risk["number"]), text)
        self.assertIn("focus=", text)
        bot_like = self.admin.get(self.base + "/risks")
        self.assertTrue(any(r["ticket"] for r in bot_like["risks"]))

    def test_04_bot_summary_has_actions(self):
        token = self.admin.post("/api/admin/bot/tokens", {"name": "Bob — actions", "spaces": ["LAMPE"]})["token"]
        import urllib.request
        req = urllib.request.Request(self.url + "/api/bot/v1/summary?space=LAMPE", headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req) as r:
            summary = json.loads(r.read())
        actions = summary["diamond"]["actions"]
        self.assertTrue(actions)
        self.assertTrue(all("url" in a and "owner" in a for a in actions))

    def test_05_exports_carry_the_owner(self):
        with self.admin.opener.open(urllib_request(self.url + self.base + "/dfmea/export.csv")) as r:
            text = r.read().decode("utf-8-sig")
        self.assertIn("Responsable;Échéance;Status de l'action;Ticket Agile", text)


def urllib_request(url):
    import urllib.request
    return urllib.request.Request(url)


if __name__ == "__main__":
    unittest.main()
