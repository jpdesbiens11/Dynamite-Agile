"""CSV import feedback (D-A-030): refused rows name the problem AND the fix;
an explicit status must be reachable through the workflow.

    python -m unittest tests.test_agile_csv_feedback -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

HEADER = ("key,parent_key,type,title,description,priority,status,assignee,"
          "labels,sprint,version,points,due_date,updated_at,implements")


class CsvFeedbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "DEMO", "name": "Démo", "description": ""})
        pid = cls.admin.get("/api/admin/projects")["projects"][0]["id"]
        cls.base = "/api/agile/p/{}".format(pid)
        cls.admin.post(cls.base + "/init")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def run_import(self, *lines, prefix_bom=False, sep=","):
        text = HEADER.replace(",", sep) + "\r\n" + "\r\n".join(lines)
        return self.admin.post(self.base + "/import/tickets", {"csv": ("\ufeff" if prefix_bom else "") + text})

    def entry(self, result, index=0):
        return result["report"][index]

    def test_unknown_status_lists_valid_values(self):
        r = self.entry(self.run_import(",,Tâche,T1,,medium,Fini,,,,,,,,"))
        self.assertEqual(r["status"], "refusée")
        self.assertIn("« Fini »", r["reason"])
        self.assertIn("To Do, In Progress, In Review, Done", r["fix"])
        self.assertEqual(r["line"], 2)

    def test_status_skipping_workflow_is_refused_with_reachable_steps(self):
        r = self.entry(self.run_import(",,Tâche,T2,,medium,Terminé,,,,,,,,"))
        self.assertEqual(r["status"], "refusée")
        self.assertIn("« To Do » → « Done »", r["reason"])
        self.assertIn("In Progress (« Start »)", r["fix"])

    def test_one_step_transition_is_applied_and_logged(self):
        created = self.entry(self.run_import(",,Tâche,T3,,medium,En cours,,,,,,,,"))
        self.assertEqual(created["status"], "créée")
        number = int(created["row"].split("-")[1])
        issue = self.admin.get(self.base + "/issues/{}".format(number))["issue"]
        self.assertEqual(issue["status_name"], "In Progress")
        self.assertTrue(any("Start" in (h["new_value"] or "") for h in issue["history"]))
        # Next step on the same ticket, then an illegal jump back is refused.
        ok = self.entry(self.run_import("{},,Tâche,T3,,medium,En revue,,,,,,,,".format(created["row"])))
        self.assertEqual(ok["status"], "mise à jour")

    def test_every_refusal_carries_a_fix(self):
        result = self.run_import(
            ",,Tache,Mauvais type,,medium,,,,,,,,,",
            ",,Tâche,Mauvaise priorité,,urgente,,,,,,,,,",
            ",,Tâche,Assigné inconnu,,medium,,Jean Personne,,,,,,,",
            ",,Tâche,Label espace,,medium,,,label avec espace,,,,,,",
            ",,Tâche,Sprint inconnu,,medium,,,,Sprint 99,,,,,",
            ",,Tâche,Points texte,,medium,,,,,,beaucoup,,,",
            ",,Tâche,Date bizarre,,medium,,,,,,,15 nov,,",
            ",,Tâche,,,medium,,,,,,,,,",
            "OTH-3,,Tâche,Autre projet,,medium,,,,,,,,,")
        self.assertEqual(result["summary"]["refused"], 9)
        for entry in result["report"]:
            self.assertEqual(entry["status"], "refusée", entry)
            self.assertTrue(entry["fix"], entry)
        self.assertIn("remplacez les espaces par un tiret", result["report"][3]["fix"])

    def test_excel_friendly_inputs_are_accepted(self):
        # French-Excel ';' separator, BOM, French priority label, dd/mm/yyyy date, comma decimal.
        line = ";;Tâche;Excel fr;;Haute;;;therm;;;2,5;15/11/2026;;"
        r = self.entry(self.run_import(line, prefix_bom=True, sep=";"))
        self.assertEqual(r["status"], "créée", r)
        issue = self.admin.get(self.base + "/issues/{}".format(int(r["row"].split("-")[1])))["issue"]
        self.assertEqual((issue["priority"], issue["due_date"], issue["story_points"]),
                         ("high", "2026-11-15", 2.5))

    def test_all_problems_of_a_line_reported_at_once(self):
        r = self.entry(self.run_import(",,Tâche,Deux erreurs,,urgente,,Jean Tremblay,essai env,,,,,,"))
        self.assertEqual(r["status"], "refusée")
        self.assertEqual(len(r["problems"]), 3)
        self.assertTrue(all(p["fix"] for p in r["problems"]))

    def test_refused_row_writes_nothing(self):
        before = len(self.admin.get(self.base + "/issues")["issues"])
        self.run_import(",,Tâche,Rien,,medium,Terminé,,,,,,,,")
        self.assertEqual(len(self.admin.get(self.base + "/issues")["issues"]), before)

    def test_missing_column_error_explains_fix(self):
        from tools.api_client import ApiFailure
        with self.assertRaises(ApiFailure) as ctx:
            self.admin.post(self.base + "/import/tickets", {"csv": "clé,titre\r\n,x"})
        self.assertIn("Correctif", ctx.exception.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
