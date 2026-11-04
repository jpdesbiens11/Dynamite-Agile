"""Goldmine change management (D-B-010): PR / bug -> ECN -> CCB ->
implementation (sub-tasks) -> verification -> closed, with guards, and the
split between the Agile views and Goldmine.

    python -m unittest tests.test_changes -v
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


class ChangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "c.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "PRJ", "name": "PRJ", "description": ""})
        pid = cls.admin.get("/api/admin/projects")["projects"][0]["id"]
        cls.base = "/api/agile/p/{}".format(pid)
        cls.admin.post(cls.base + "/init")
        meta = cls.admin.get(cls.base + "/meta")
        wf = next(w for w in meta["workflows"] if w["is_default"])
        cls.admin.post(cls.base + "/types", {"name": "ECN", "icon_key": "ecn", "workflow_id": wf["id"]})
        types = {t["icon_key"]: t for t in cls.admin.get(cls.base + "/meta")["types"]}
        cls.old_ecn = cls.admin.post(cls.base + "/issues", {"type_id": types["ecn"]["id"], "title": "ECN historique"})
        cls.old_bug = cls.admin.post(cls.base + "/issues", {"type_id": types["bug"]["id"], "title": "Bogue historique"})
        cls.task = cls.admin.post(cls.base + "/issues", {"type_id": types["task"]["id"], "title": "Travail Agile"})
        made = cls.admin.post("/api/admin/users", {"username": "redac", "display_name": "Éditrice"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(pid, made["user"]["id"]), {"role": "editor"})
        cls.editor = Client(cls.url)
        cls.editor.login("redac", made["temp_password"], "Plume-Essai-Pass-2026")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, func, *args):
        with self.assertRaises(ApiFailure) as ctx:
            func(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)
        return ctx.exception.message

    def issue(self, number):
        return self.admin.get("{}/issues/{}".format(self.base, number))["issue"]

    def move(self, client, number, to_name):
        issue = self.issue(number)
        t = next((t for t in issue["transitions"] if t["to_name"] == to_name), None)
        self.assertIsNotNone(t, "no transition to {} from {}".format(to_name, issue["status_name"]))
        return client.post("{}/issues/{}/transition".format(self.base, number), {"transition_id": t["id"]})

    def test_1_setup_moves_ecn_and_bugs_out_of_agile(self):
        self.assertFalse(self.admin.get(self.base + "/changes")["enabled"])
        self.fails(403, self.editor.post, self.base + "/changes/setup")
        done = self.admin.post(self.base + "/changes/setup")["types"]
        self.assertEqual(len(done), 4)
        self.assertEqual(self.issue(self.old_ecn["number"])["status_name"], "Draft")
        self.assertEqual(self.issue(self.old_bug["number"])["status_name"], "Open")
        agile = [i["key"] for i in self.admin.get(self.base + "/issues")["issues"]]
        self.assertEqual(agile, [self.task["key"]])
        board = [i["key"] for i in self.admin.get(self.base + "/board")["issues"]]
        self.assertEqual(board, [self.task["key"]])
        listing = self.admin.get(self.base + "/changes")
        self.assertEqual(sorted(i["change_role"] for i in listing["items"]), ["bug", "ecn"])
        self.fails(409, self.admin.post, self.base + "/changes/setup")
        # D-B-011: PR / bugs / ECN form the "change" bucket (Agile's Change Management),
        # the Goldmine bucket is kept for requirements.
        buckets = {t["change_role"]: t["bucket"] for t in self.admin.get(self.base + "/meta")["types"] if t["change_role"]}
        self.assertEqual(set(buckets.values()), {"change"})
        self.assertEqual(len(self.admin.get(self.base + "/issues?bucket=change")["issues"]), 2)
        nav = {m["key"]: m for m in self.admin.get("/api/me")["modules"]}
        self.assertEqual([k for k in nav], ["dynamite", "agile", "goldmine", "diamond", "testing", "exploration", "tools", "training", "codex",
                                            "timesheet", "help", "about"])
        self.assertTrue(nav["goldmine"]["available"])

    def test_2_full_change_cycle(self):
        types = self.admin.get(self.base + "/changes")["types"]
        pr = self.editor.post(self.base + "/issues", {"type_id": types["pr"]["id"], "title": "Fissure sur le boîtier",
                                                      "description": "Observée après cyclage thermique."})
        self.editor.put("{}/issues/{}/change".format(self.base, pr["number"]),
                        {"severity": "majeure", "detected_in": "essai", "item_ref": "PRD-BOX-100 rév. B"})
        self.assertIn("Correctif", self.fails(400, self.editor.put, "{}/issues/{}/change".format(self.base, pr["number"]),
                                              {"severity": "grave"}))
        self.assertIn("Analyse", self.fails(409, self.editor.post, "{}/issues/{}/derive".format(self.base, pr["number"]), {}))
        self.move(self.editor, pr["number"], "In Analysis")
        self.assertIn("bouton", self.fails(409, self.move, self.editor, pr["number"], "Derived to ECN"))
        ecn = self.editor.post("{}/issues/{}/derive".format(self.base, pr["number"]), {})
        self.assertEqual(self.issue(pr["number"])["status_name"], "Derived to ECN")
        detail = self.issue(ecn["number"])
        self.assertEqual(detail["change_role"], "ecn")
        self.assertEqual([t["key"] for t in detail["treats"]], [pr["key"]])
        self.assertEqual(detail["change"]["reason"], "correctif")

        url = "{}/issues/{}".format(self.base, ecn["number"])
        msg = self.fails(409, self.move, self.editor, ecn["number"], "Submitted")
        self.assertIn("classe", msg)
        self.assertIn("article", msg)
        self.editor.put(url + "/change", {"change_class": "majeur", "impact_fff": True, "impact_notes": "Masse +40 g"})
        self.assertIn("type", self.fails(400, self.editor.put, url + "/change/items",
                                         {"items": [{"item_type": "vis", "item_number": "X"}]}))
        self.editor.put(url + "/change/items", {"items": [
            {"item_type": "piece", "item_number": "PRD-BOX-100", "item_title": "Boîtier", "rev_from": "B", "rev_to": "C",
             "disposition": "retoucher"},
            {"item_type": "plan", "item_number": "DWG-PRD-100", "rev_from": "B", "rev_to": "C"}]})
        self.move(self.editor, ecn["number"], "Submitted")
        self.move(self.editor, ecn["number"], "CCB Review")
        # Approval is a CCB decision: project admins only, and approvers named.
        self.assertNotIn("Approved", [t["to_name"] for t in self.editor.get(url)["issue"]["transitions"]])
        self.assertIn("approbateurs", self.fails(409, self.move, self.admin, ecn["number"], "Approved"))
        self.admin.put(url + "/change", {"approvers": "J.-P. D., qualité, production", "decision_date": "2026-09-24"})
        self.move(self.admin, ecn["number"], "Approved")
        self.move(self.editor, ecn["number"], "In Implementation")
        task_type = self.issue(ecn["number"])["ecn_task_type_id"]
        sub = self.editor.post(self.base + "/issues", {"type_id": task_type, "title": "Réviser le plan DWG-PRD-100",
                                                       "parent_number": ecn["number"]})
        self.assertIn(sub["key"], self.fails(409, self.move, self.editor, ecn["number"], "In Verification"))
        self.move(self.editor, sub["number"], "In Progress")
        self.move(self.editor, sub["number"], "Done")
        self.move(self.editor, ecn["number"], "In Verification")
        self.assertIn("effectivité", self.fails(409, self.move, self.editor, ecn["number"], "Closed"))
        # The problem cannot close while its ECN is open.
        self.assertIn(ecn["key"], self.fails(409, self.move, self.editor, pr["number"], "Closed"))
        self.editor.put(url + "/change", {"effectivity": "S/N 0012 et suivants", "verification_ref": "RPT-PRD-044"})
        self.move(self.editor, ecn["number"], "Closed")
        self.move(self.editor, pr["number"], "Closed")
        listing = {i["key"]: i for i in self.admin.get(self.base + "/changes")["items"]}
        self.assertEqual(listing[ecn["key"]]["tasks"], {"total": 1, "done": 1})
        self.assertEqual(listing[pr["key"]]["treated_by"], [ecn["key"]])
        self.assertNotIn(sub["key"], [i["key"] for i in self.admin.get(self.base + "/issues")["issues"]])

        with self.admin.opener.open(self.url + self.base + "/export/changes") as resp:
            rows = {r["key"]: r for r in csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig")))}
        self.assertEqual(rows[ecn["key"]]["change_class"], "Major")
        self.assertIn("PRD-BOX-100 B→C (Rework)", rows[ecn["key"]]["affected_items"])
        self.assertEqual(rows[pr["key"]]["treated_by"], ecn["key"])

    def test_3_close_problem_without_ecn_needs_root_cause(self):
        types = self.admin.get(self.base + "/changes")["types"]
        bug = self.editor.post(self.base + "/issues", {"type_id": types["bug"]["id"], "title": "Valeur SOC affichée à 101 %"})
        self.move(self.editor, bug["number"], "In Analysis")
        self.assertIn("cause racine", self.fails(409, self.move, self.editor, bug["number"], "Closed"))
        self.editor.put("{}/issues/{}/change".format(self.base, bug["number"]),
                        {"root_cause": "Arrondi d'affichage ; corrigé en 2.3.1", "found_version": "2.3.0"})
        self.move(self.editor, bug["number"], "Closed")


if __name__ == "__main__":
    unittest.main()
