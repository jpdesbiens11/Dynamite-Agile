"""Exploration plan (D-B-019): scheduling, rights, Excel/CSV round trip.

    python -m unittest tests.test_exploration -v
"""
import datetime as dt
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.exploration import xlsx  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur marc | Marc Essai | utilisateur | actif
utilisateur ines | Inès Essai | utilisateur | actif
droit marc | EXP | editeur
droit ines | EXP | editeur
"""


class ExplorationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "e.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "EXP", "name": "Essai plan", "description": ""})
        pid = next(p["id"] for p in cls.admin.get("/api/admin/projects")["projects"] if p["key"] == "EXP")
        cls.base = "/api/exploration/p/{}".format(pid)
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.users = {u["username"]: u["id"] for u in cls.admin.get("/api/admin/users")["users"]}
        cls.people = {}
        for c in done["created"]:
            client = Client(cls.url)
            client.login(c["username"], c["temp_password"], "Plan-Essai-Gantt-2026")
            cls.people[c["username"]] = client

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def download(self, path):
        with self.admin.opener.open(self.url + self.base + path) as resp:
            return resp.read()

    def upload(self, data, name, dry):
        return self.admin.upload(self.base + "/import?dry_run=" + ("1" if dry else "0"), data, filename=name)

    def tasks(self):
        return {t["code"]: t for t in self.admin.get(self.base + "/plan")["tasks"]}

    def test_1_provisioned_and_scheduled(self):
        plan = self.admin.get(self.base + "/plan")
        self.assertEqual([t["code"] for t in plan["tasks"]], ["J0"])  # kick-off milestone of a new project
        self.admin.put(self.base + "/plan", {"start_date": "2026-10-05"})
        self.admin.post(self.base + "/tasks", {"code": "T1", "title": "Concept", "duration_weeks": 4,
                                               "predecessors": "J0", "owner_id": self.users["marc"]})
        self.admin.post(self.base + "/tasks", {"code": "T2", "title": "Conception", "duration_weeks": 6,
                                               "predecessors": "T1", "phase": "Préliminaire"})
        self.admin.post(self.base + "/tasks", {"code": "T3", "title": "Essais", "duration_weeks": 2,
                                               "predecessors": "T1, T2", "start_date": "2027-02-01"})
        t = self.tasks()
        self.assertEqual((t["T1"]["start"], t["T1"]["end"]), ("2026-10-05", "2026-11-02"))
        self.assertEqual((t["T2"]["start"], t["T2"]["end"]), ("2026-11-02", "2026-12-14"))
        self.assertEqual(t["T3"]["start"], "2027-02-01")  # imposed "not before" wins over T2's end
        with self.assertRaises(ApiFailure) as loop:
            self.admin.patch(self.base + "/tasks/{}".format(t["T1"]["id"]), {"predecessors": "T3"})
        self.assertIn("Boucle", loop.exception.message)
        # Renaming an ID follows through the predecessors.
        self.admin.patch(self.base + "/tasks/{}".format(t["T1"]["id"]), {"code": "C1"})
        self.assertEqual(self.tasks()["T3"]["predecessors"], ["C1", "T2"])
        self.admin.patch(self.base + "/tasks/{}".format(t["T1"]["id"]), {"code": "T1"})

    def test_2_owner_follow_up_only(self):
        t = self.tasks()
        marc, ines = self.people["marc"], self.people["ines"]
        url = self.base + "/tasks/{}".format(t["T1"]["id"])
        marc.patch(url, {"status": "In Progress", "progress": 40, "note": "Revue concept planifiée"})
        with self.assertRaises(ApiFailure):
            marc.patch(url, {"duration_weeks": 1})  # structure: administrators
        with self.assertRaises(ApiFailure):
            ines.patch(url, {"status": "Done"})  # not her task
        with self.assertRaises(ApiFailure):
            ines.post(self.base + "/tasks", {"title": "x"})
        self.assertEqual(self.tasks()["T1"]["status"], "doing")
        marc.patch(url, {"status": "done"})
        self.assertEqual(self.tasks()["T1"]["progress"], 100)

    def test_3_excel_round_trip(self):
        data = self.download("/export.xlsx")
        sheets = xlsx.read(data)
        self.assertEqual(sheets["Plan"][0][:3], ["ID", "Phase", "Task"])
        self.assertTrue(any(r and r[0] == "Plan Start" and r[1] == "2026-10-05" for r in sheets["Lisez-moi"]))
        same = self.upload(data, "plan.xlsx", dry=True)
        self.assertEqual(same["summary"]["inchangée"], 4, same)
        self.assertFalse(same["problems"])
        # Edit the plan as a CSV (what an AI agent would produce), then apply.
        csv_text = ("ID;Tâche;Responsable;Prédécesseurs;Durée (sem.);Statut;Avancement (%);Phase\n"
                    "J0;Lancement;;;0;Terminé;100;Lancement\n"
                    "T1;Concept;Marc Essai;J0;5;En cours;0,5;Concept\n"
                    "T2;Conception;ines;T1;6;À faire;;Préliminaire\n"
                    "T4;Revue PDR;Personne Inconnue;T2;0;;;Préliminaire\n")
        check = self.upload(csv_text.encode("cp1252"), "plan.csv", dry=True)
        actions = {r["code"]: r["action"] for r in check["report"]}
        self.assertEqual(actions, {"J0": "mise à jour", "T1": "mise à jour", "T2": "mise à jour",
                                   "T4": "créée", "T3": "supprimée"})
        self.assertIn("inconnu", next(r["detail"] for r in check["report"] if r["code"] == "T4"))
        self.assertEqual(len(self.tasks()), 4)  # dry run wrote nothing
        applied = self.upload(csv_text.encode("cp1252"), "plan.csv", dry=False)
        self.assertTrue(applied["applied"])
        t = self.tasks()
        self.assertEqual(sorted(t), ["J0", "T1", "T2", "T4"])
        self.assertEqual(t["T1"]["progress"], 50)
        self.assertEqual(t["T2"]["owner_id"], self.users["ines"])
        self.assertIsNone(t["T4"]["owner_id"])
        # A loop in a file refuses the whole import.
        bad = "ID,Tâche,Prédécesseurs\nA,Un,B\nB,Deux,A\n"
        refused = self.upload(bad.encode(), "boucle.csv", dry=False)
        self.assertFalse(refused["applied"])
        self.assertIn("Boucle", refused["problems"][0])
        csv_out = self.download("/export.csv").decode("utf-8-sig")
        self.assertTrue(csv_out.startswith("ID,Phase,Task"))

    def test_4_rights_on_import(self):
        with self.assertRaises(ApiFailure):
            self.people["marc"].post(self.base + "/tasks", {"title": "x"})
        self.assertEqual(self.people["ines"].get(self.base + "/plan")["can_admin"], False)
        self.assertLess(dt.date.fromisoformat(self.tasks()["T1"]["start"]), dt.date(2027, 1, 1))


if __name__ == "__main__":
    unittest.main()
