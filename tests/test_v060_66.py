"""0.60.66: the guest reads the team's timesheets of the demo (D-O-072), FR | EN for everyone with the display
dictionary (D-O-073), the guest's guided tour (D-O-074), and Diamond « Coûts et budget » import + AI prompt (D-O-075)."""
import json
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import costs_import  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

STATIC = BASE_DIR / "static"


class ServerTest(unittest.TestCase):
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
        cls.server = router.create_server(cfg, STATIC, data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        projects = cls.admin.get("/api/admin/projects")["projects"]
        cls.demo = next(p["id"] for p in projects if p["key"] == "DEMO")
        cls.other = cls.admin.post("/api/admin/projects", {"key": "PRIV", "name": "Privé"})["project"]["id"]
        with db.connect() as conn:  # a week of a team member with hours on DEMO and on PRIV
            uid = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
            week = conn.execute("INSERT INTO timesheet_weeks (user_id, week_start, status, created_at, updated_at) "
                                "VALUES (?, '2026-11-02', 'submitted', 'x', 'x')", (uid,)).lastrowid
            for pid, hours in ((cls.demo, 3), (cls.other, 2)):
                conn.execute("INSERT INTO timesheet_entries (week_id, project_id, work_date, task_key, hours, description, created_at, "
                             "updated_at) VALUES (?, ?, '2026-11-03', 'A-01', ?, 'Essai', 'x', 'x')", (week, pid, hours))
        cls.admin.put("/api/admin/guest", {"enabled": True, "projects": [cls.demo]})
        cls.guest = Client(cls.url)
        cls.guest.post("/api/login/guest")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, call):
        try:
            call()
        except ApiFailure as exc:
            return exc.status
        return 200

    def test_01_guest_reads_the_team_sheets_of_his_spaces_only(self):
        self.assertTrue(self.guest.get("/api/timesheet/leave")["guest_team"])
        data = self.guest.get("/api/timesheet/approvals?status=all")
        self.assertTrue(data["read_only"])
        lines = [e for w in data["weeks"] for e in w["entries"]]
        self.assertTrue(lines)
        self.assertEqual({e["project_id"] for e in lines}, {self.demo})  # the PRIV hours never show
        week = data["weeks"][0]["id"]
        self.assertEqual(self.status(lambda: self.guest.post("/api/timesheet/weeks/{}/decision".format(week), {"action": "approve"})), 403)

    def test_02_guest_language_is_never_written_on_the_server(self):
        self.assertEqual(self.status(lambda: self.guest.put("/api/me/prefs", {"language": "en"})), 403)
        prefs = (STATIC / "js" / "tools" / "prefs.js").read_text("utf-8")
        self.assertIn("da.guest.lang", prefs)

    def test_03_costs_round_trip_and_prompt(self):
        base = "/api/diamond/p/{}/costs".format(self.demo)
        self.admin.post(base + "/nre", {"title": "Moule du boîtier", "category": "outillage", "amount": 1000})
        text = self.admin.raw_get(base + "/export.csv")[2].decode("utf-8-sig")
        self.assertEqual(sum(self.admin.post(base + "/import", {"file": text})["preview"][k]
                             for k in ("nre_new", "nre_updated", "lines_new", "lines_updated")), 0)  # unchanged file: nothing to do
        changed = text.replace(";Moule du boîtier;Outillage et moules;;1000.0", ";Moule du boîtier;Outillage et moules;;1250,50")
        added = changed + "\n\nPièce;Désignation;Quantité;Prix prototype;Prix à 100;Prix à 1000;Prix à 10000;Fournisseur;Base;Notes\n" \
            ";Emballage;1;4;3;2;1;Imprimeur;Estimation;IA\n"
        preview = self.admin.post(base + "/import", {"file": added})["preview"]
        self.assertEqual((preview["nre_updated"], preview["lines_new"]), (1, 1))
        done = self.admin.post(base + "/import", {"file": added, "apply": True})
        self.assertEqual(next(r["amount"] for r in done["nre"] if r["title"] == "Moule du boîtier"), 1250.5)
        self.assertIn("Emballage", [ln["name"] for ln in done["lines"]])
        self.assertEqual(self.status(lambda: self.guest.post(base + "/import", {"file": added})), 403)
        prompt = self.admin.get(base + "/prompt")["prompt"]
        self.assertIn("NRE;Intitulé;Catégorie;Phase;Montant;Base;Fournisseur;Notes", prompt)
        self.assertIn("Moule du boîtier", prompt)


class StaticTest(unittest.TestCase):
    def test_04_parse_tolerates_an_ai_answer(self):
        data = costs_import.parse("Voici :\n```csv\nNRE,Intitulé,Catégorie,Phase,Montant,Base,Fournisseur,Notes\n"
                                  ",Essais CEM,Essais et validation,D. Validation et lancement,\"2 500 $\",Soumission,Labo,\n```")
        self.assertEqual(data["nre"][0]["body"]["category"], "essais")
        self.assertEqual(data["nre"][0]["body"]["phase"], "D")
        self.assertEqual(data["nre"][0]["body"]["amount"], "2500")

    def test_05_dictionary_and_tour_are_wired(self):
        index = (STATIC / "index.html").read_text("utf-8")
        for script in ("i18n_dom.js", "guest_tour_steps.js", "guest_tour.js"):
            self.assertIn('src="/js/tools/{}"'.format(script), index)
        total = 0
        for n in range(1, 7):
            part = json.loads((STATIC / "i18n" / "en_{}.json".format(n)).read_text("utf-8"))
            total += len(part)
            self.assertTrue(all(isinstance(v, str) and v.strip() for v in part.values()))
        self.assertGreater(total, 2500)
        demo = 0
        for n in range(1, 7):  # 0.60.67: the Rover's content in English
            demo += len(json.loads((STATIC / "i18n" / "demo_en_{}.json".format(n)).read_text("utf-8")))
        self.assertGreater(demo, 1500)
        tour = (STATIC / "js" / "tools" / "guest_tour.js").read_text("utf-8")
        self.assertIn("da:language", tour)  # the top bar FR | EN redraws the card
        steps = (STATIC / "js" / "tools" / "guest_tour_steps.js").read_text("utf-8")
        self.assertGreaterEqual(len(re.findall(r'id: "', steps)), 12)
        self.assertEqual(len(re.findall(r"\bfr: \[", steps)), len(re.findall(r"\ben: \[", steps)))


if __name__ == "__main__":
    unittest.main()
