"""Core lot v0.10 (0.17.0): project rights and project admins (D-B-027),
personal settings (D-B-028), content protection (D-B-029), backup /
restore / delete (D-B-030), vacation bank and manager approval (D-B-031),
personal dashboard (D-B-032), HeadLamp « Connaissances » GTD (D-B-033).

    python -m unittest tests.test_lot_v010 -v
"""
import datetime as dt
import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur nora | Nora Essai | utilisateur | actif
utilisateur theo | Théo Essai | utilisateur | actif
droit nora | BKP | editeur
"""
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
       b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\x88\x00\x00\x00\x00IEND\xaeB`\x82")


def restored_ids(test, pid):
    from core import db as core_db
    with core_db.connect() as conn:
        return conn.execute("SELECT id FROM attachments WHERE project_id = ?", (pid,)).fetchone()[0]


class LotV010Test(unittest.TestCase):
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
        startup.run(data_dir, cfg)
        startup.run(data_dir, cfg)  # idempotent (INT, HEADLAMP, BDC pages)
        cls.data_dir = data_dir
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "BKP", "name": "Banc de cyclage", "description": "Essais"})
        cls.projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.bkp = cls.projects["BKP"]
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.people, cls.ids = {}, {}
        for c in done["created"]:
            client = Client(cls.url)
            me = client.login(c["username"], c["temp_password"], "Essai-Lot-Dix-2026!")
            cls.people[c["username"]] = client
            cls.ids[c["username"]] = me["user"]["id"]
        cls.monday = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def _audit_actions(self):
        return json.dumps(self.admin.get("/api/admin/audit"))

    # ---------------- D-B-027: rights ----------------
    def test_01_project_admin(self):
        nora, theo = self.people["nora"], self.people["theo"]
        self.admin.put("/api/admin/rights", {"user_id": self.ids["nora"], "project_id": self.bkp, "role": "manager"})
        matrix = self.admin.get("/api/admin/rights")
        self.assertEqual(matrix["cells"]["{}:{}".format(self.ids["nora"], self.bkp)], "manager")
        me = {p["key"]: p for p in nora.get("/api/me")["projects"]}
        self.assertEqual(me["BKP"]["role"], "editor")  # modules see an editor
        self.assertTrue(me["BKP"]["is_manager"])
        self.assertEqual([p["key"] for p in nora.get("/api/me/managed-projects")["projects"]], ["BKP"])
        members = nora.put("/api/projects/{}/members/{}".format(self.bkp, self.ids["theo"]), {"role": "reader"})
        self.assertIn("theo", [m["username"] for m in members["members"]])
        with self.assertRaises(ApiFailure) as err:  # a reader manages nothing
            theo.get("/api/projects/{}/members".format(self.bkp))
        self.assertEqual(err.exception.status, 403)
        with self.assertRaises(ApiFailure) as err:  # cannot drop his own admin right
            nora.put("/api/projects/{}/members/{}".format(self.bkp, self.ids["nora"]), {"role": "editor"})
        self.assertEqual(err.exception.status, 400)
        with self.assertRaises(ApiFailure):  # not a platform administrator
            nora.get("/api/admin/rights")
        self.assertIn("member_set", self._audit_actions())

    # ---------------- D-B-028: settings ----------------
    def test_02_prefs(self):
        nora = self.people["nora"]
        self.assertEqual(self.people["theo"].get("/api/me")["prefs"]["theme"], "carnet")  # D-B-087: default (was atlassian, D-B-035)
        prefs = nora.put("/api/me/prefs", {"theme": "atlassian", "font_size": "112", "my_items": True})["prefs"]
        self.assertEqual((prefs["theme"], prefs["language"], prefs["font_size"], prefs["my_items"]), ("atlassian", "fr", "112", True))
        with self.assertRaises(ApiFailure):  # D-B-042: French only
            nora.put("/api/me/prefs", {"language": "en"})
        self.assertEqual(nora.get("/api/me")["prefs"]["theme"], "atlassian")
        for bad in ({"theme": "neon"}, {"manager_id": self.ids["nora"]}, {"vacation_bank_hours": "beaucoup"}):
            with self.assertRaises(ApiFailure) as err:
                nora.put("/api/me/prefs", bad)
            self.assertEqual(err.exception.status, 400)
        data = nora.get("/api/me/prefs")
        self.assertIn("atlassian", data["choices"]["theme"])
        self.assertNotIn(self.ids["nora"], [u["id"] for u in data["people"]])
        nora.put("/api/me/prefs", {"theme": "system", "font_size": "100", "my_items": False})

    # ---------------- D-B-029: content protection ----------------
    def test_03_policy(self):
        with self.assertRaises(ApiFailure):
            self.people["theo"].get("/api/admin/policy")
        self.admin.put("/api/admin/policy", {"watermark": True, "block_print": True})
        me = self.people["theo"].get("/api/me")
        self.assertTrue(me["policy"]["watermark"])
        self.assertTrue(me["policy"]["block_print"])
        self.assertFalse(me["policy"]["block_copy"])
        self.assertTrue(me["client_ip"])
        self.people["theo"].post("/api/privacy/event", {"kind": "print", "page": "#/agile/BKP/board"})
        with self.assertRaises(ApiFailure):
            self.people["theo"].post("/api/privacy/event", {"kind": "rien"})
        text = self._audit_actions()
        self.assertIn("privacy_print_attempt", text)
        self.assertIn("privacy_policy_changed", text)
        self.admin.put("/api/admin/policy", {"watermark": False, "block_print": False})

    # ---------------- D-B-031: vacation bank, health leave, approver (INT Space since 0.60.01) ----------------
    def test_04_vacation(self):
        theo, nora = self.people["theo"], self.people["nora"]
        week = theo.get("/api/timesheet/week")
        self.assertIn("INT", [p["key"] for p in week["projects"]])  # open to everyone
        int_id = next(p["id"] for p in week["projects"] if p["key"] == "INT")
        tasks = [t["key"] for t in week["meta"]["task_sets"]["interne"]["tasks"]]
        self.assertEqual(tasks[-2:], ["INT-VAC", "INT-SAN"])
        pdp = [t["key"] for t in week["meta"]["task_sets"]["pdp"]["tasks"]]
        self.assertEqual((pdp[0], pdp[-1]), ("A-01", "D-21"))
        with self.assertRaises(ApiFailure):  # nobody named nora yet
            nora.get("/api/timesheet/approvals")
        theo.put("/api/me/prefs", {"manager_id": self.ids["nora"], "vacation_bank_hours": 40, "vacation_bank_date": self.monday})
        self.assertTrue(nora.get("/api/timesheet/leave")["is_manager"])
        theo.post("/api/timesheet/entries", {"work_date": self.monday, "project_id": int_id, "task_key": "INT-VAC",
                                             "hours": 8, "description": "Vacances"})
        theo.post("/api/timesheet/entries", {"work_date": self.monday, "project_id": int_id, "task_key": "INT-SAN",
                                             "hours": 4, "description": "Rendez-vous"})
        leave = theo.get("/api/timesheet/week?start=" + self.monday)["leave"]
        self.assertEqual((leave["remaining"], leave["vacation_week"], leave["health_week"]), (32, 8, 4))
        self.assertEqual(leave["manager"]["id"], self.ids["nora"])
        theo.post("/api/timesheet/week/submit", {"start": self.monday})
        weeks = nora.get("/api/timesheet/approvals")["weeks"]
        self.assertEqual([w["username"] for w in weeks], ["theo"])
        self.assertEqual(weeks[0]["leave"]["remaining"], 32)
        with self.assertRaises(ApiFailure):  # the approver of nobody, theo, cannot approve
            theo.post("/api/timesheet/weeks/{}/decision".format(weeks[0]["id"]), {"action": "approve"})
        nora.post("/api/timesheet/weeks/{}/decision".format(weeks[0]["id"]), {"action": "approve"})
        self.assertEqual(theo.get("/api/timesheet/week?start=" + self.monday)["week"]["status"], "approved")
        # the administrator corrects the bank: journalled
        self.admin.put("/api/admin/users/{}/prefs".format(self.ids["theo"]), {"vacation_bank_hours": 50})
        self.assertEqual(theo.get("/api/timesheet/leave")["remaining"], 42)
        self.assertIn("prefs_hr_changed", self._audit_actions())
        claim = {t["key"]: t["claimable"] for t in self.admin.get("/api/timesheet/budget")["sets"]["interne"]["tasks"]}
        self.assertFalse(claim["INT-VAC"] or claim["INT-SAN"])  # leave is never claimed from a funding organism
        self.assertTrue(claim["INT-03"])

    # ---------------- D-B-032: dashboard ----------------
    def test_05_dashboard(self):
        nora = self.people["nora"]
        base = "/api/agile/p/{}".format(self.bkp)
        types = {t["icon_key"]: t for t in nora.get(base + "/meta")["types"] if t["bucket"] == "agile"}
        nora.post(base + "/issues", {"type_id": types["task"]["id"], "title": "Mesurer la chauffe du contacteur",
                                     "priority": "high", "assignee_id": self.ids["nora"]})
        data = nora.get("/api/dashboard")
        sections = {s["key"]: s for s in data["sections"]}
        self.assertTrue(any("contacteur" in i["title"] for i in sections["tickets"]["items"]))
        self.assertIn("timesheet", sections)
        self.assertIn("approvals", sections)  # nora approves theo
        self.assertTrue(data["kpis"])
        theo = {s["key"]: s for s in self.people["theo"].get("/api/dashboard")["sections"]}
        self.assertFalse(any("contacteur" in i["title"] for i in theo.get("tickets", {"items": []})["items"]))

    # ---------------- D-B-030: backup, archive, delete, restore ----------------
    def test_06_backup_delete_restore(self):
        nora = self.people["nora"]
        pages = "/api/dynamite/p/{}/pages".format(self.bkp)
        image = nora.upload("/api/dynamite/p/{}/images".format(self.bkp), PNG, "image/png", "banc.png")
        home = nora.get(pages)["pages"][0]
        nora.post(pages, {"title": "Photo du banc", "parent_id": home["id"], "body": {"type": "doc", "content": [
            {"type": "image", "id": image["id"], "alt": "banc"}, {"type": "ticket", "key": "BKP-1"}]}})
        base = "/api/agile/p/{}".format(self.bkp)
        types = {t["icon_key"]: t for t in nora.get(base + "/meta")["types"] if t["bucket"] == "agile"}
        nora.post(base + "/issues", {"type_id": types["task"]["id"], "title": "Sauvegarder le banc", "priority": "low"})
        status, headers, raw = self.admin.raw_get("/api/admin/projects/{}/backup.zip".format(self.bkp))
        self.assertEqual(status, 200)
        z = zipfile.ZipFile(io.BytesIO(raw))
        self.assertIn("manifest.json", z.namelist())
        self.assertTrue(any(n.startswith("attachments/") for n in z.namelist()))
        with self.assertRaises(ApiFailure) as err:  # must be archived first
            self.admin.post("/api/admin/projects/{}/delete".format(self.bkp), {"confirm_key": "BKP"})
        self.assertEqual(err.exception.status, 409)
        self.admin.patch("/api/admin/projects/{}".format(self.bkp), {"is_archived": True})
        impact = self.admin.get("/api/admin/projects/{}/impact".format(self.bkp))
        self.assertGreater(impact["counts"].get("agile_issues", 0), 0)
        with self.assertRaises(ApiFailure):
            self.admin.post("/api/admin/projects/{}/delete".format(self.bkp), {"confirm_key": "XXX"})
        res = self.admin.post("/api/admin/projects/{}/delete".format(self.bkp), {"confirm_key": "BKP"})
        self.assertTrue(res["backup"].endswith("_avant-suppression.zip"))
        keys = [p["key"] for p in self.admin.get("/api/admin/projects")["projects"]]
        self.assertNotIn("BKP", keys)
        backups = self.admin.get("/api/admin/backups")["backups"]
        names = [b["name"] for b in backups]
        self.assertIn(res["backup"], names)
        self.assertGreaterEqual(len(names), 2)
        # restore the automatic backup under another key
        restored = self.admin.post("/api/admin/backups/{}/restore".format(res["backup"]), {"key": "BKP2", "name": "Banc (copie)"})
        pid = restored["project"]["id"]
        tree = self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]
        photo = next(p for p in tree if p["title"] == "Photo du banc")
        body = self.admin.get("/api/dynamite/p/{}/pages/{}".format(pid, photo["id"]))["page"]["body"]
        blocks = {b["type"]: b for b in body["content"]}
        self.assertEqual(blocks["image"]["id"], restored_ids(self, pid))  # points to the restored attachment
        self.assertEqual(blocks["ticket"]["key"], "BKP2-1")
        st, _h, png = self.admin.raw_get("/api/dynamite/image/{}".format(blocks["image"]["id"]))
        self.assertEqual((st, png), (200, PNG))
        issues = self.admin.get("/api/agile/p/{}/issues".format(pid))["issues"]
        self.assertIn("Mesurer la chauffe du contacteur", [i["title"] for i in issues])
        # the downloaded file restores under its original key, now free; again -> 409
        again = self.admin.upload("/api/admin/restore?key=", raw, "application/zip", "bkp.zip")
        self.assertEqual(again["project"]["key"], "BKP")
        pid2 = again["project"]["id"]
        photo2 = next(p for p in self.admin.get("/api/dynamite/p/{}/pages".format(pid2))["pages"] if p["title"] == "Photo du banc")
        body2 = self.admin.get("/api/dynamite/p/{}/pages/{}".format(pid2, photo2["id"]))["page"]["body"]
        image2 = next(b for b in body2["content"] if b["type"] == "image")["id"]
        self.assertEqual(image2, restored_ids(self, pid2))
        self.assertNotEqual(image2, blocks["image"]["id"])  # two copies, two attachments
        with self.assertRaises(ApiFailure) as err:
            self.admin.upload("/api/admin/restore?key=BKP", raw, "application/zip", "bkp.zip")
        self.assertEqual(err.exception.status, 409)
        with self.assertRaises(ApiFailure):  # tampered file
            self.admin.upload("/api/admin/restore?key=BKP3", raw[:-40] + b"x" * 40, "application/zip", "bad.zip")
        with self.assertRaises(ApiFailure):
            self.people["nora"].get("/api/admin/backups")
        self.admin.post("/api/admin/backups/{}/delete".format(res["backup"]), {"confirm": res["backup"]})
        self.assertNotIn(res["backup"], [b["name"] for b in self.admin.get("/api/admin/backups")["backups"]])

    # ---------------- D-B-033: HeadLamp « Connaissances » ----------------
    def test_07_gtd_pages(self):
        hl = self.projects["HEADLAMP"]
        titles = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(hl))["pages"]]
        for title in ("Base de connaissances (BDC)", "Getting Things Done — les principes",  # D-B-040
                      "GTD appliqué au développement mécatronique", "Revue hebdomadaire GTD — gabarit"):
            self.assertEqual(titles.count(title), 1, title)
        self.assertNotIn("Politique de l'équipe — vacances et congés", titles)  # in the INT Space (0.60.01)
        pid = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}["INT"]
        internal = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]]
        self.assertEqual(internal.count("Politique de l'équipe — vacances et congés"), 1)
        self.assertIn("Politiques de l'équipe", internal)
        self.assertNotIn("Connaissances", titles)
        main = next(p for p in self.admin.get("/api/dynamite/p/{}/pages".format(hl))["pages"] if p["title"].startswith("Getting"))
        body = self.admin.get("/api/dynamite/p/{}/pages/{}".format(hl, main["id"]))["page"]["body"]
        self.assertIn("◆ Pépite", str(body))

    def test_09_dashboard_actions(self):
        nora = self.people["nora"]
        data = nora.get("/api/dashboard")
        sections = {s["key"]: s for s in data["sections"]}
        tickets = sections["tickets"]
        self.assertEqual(tickets["list_href"], "#/agile/{key}/issues")
        self.assertTrue(tickets["mine"])
        item = next(i for i in tickets["items"] if "contacteur" in i["title"])
        action = item["action"]
        self.assertEqual((action["method"], action["field"]), ("POST", "transition_id"))
        target_id, target_name = action["choices"][0]
        res = nora.post(action["url"], {action["field"]: target_id})
        self.assertEqual(res["status"], target_name)
        after = {s["key"]: s for s in nora.get("/api/dashboard")["sections"]}
        moved = [i for i in after["tickets"]["items"] if "contacteur" in i["title"]]
        self.assertTrue(not moved or moved[0]["status"] == target_name)


if __name__ == "__main__":
    unittest.main()
