"""Core lot v0.7 (D-B-022): search, interface Audit, start-up hooks;
Timesheet (D-B-023): weeks, submission rules, approval, Excel export, a course project open to all.

    python -m unittest tests.test_platform_tools -v
"""
import datetime as dt
import io
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
droit nora | TSK | editeur
"""
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
       b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\x88\x00\x00\x00\x00IEND\xaeB`\x82")


class PlatformToolsTest(unittest.TestCase):
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
        startup.run(data_dir, cfg)  # idempotent
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "TSK", "name": "Étanchéité du boîtier", "description": ""})
        # the course Space, open to all, with its own code set
        cls.admin.post("/api/admin/projects", {"key": "CRS", "name": "Cours", "description": ""})
        projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.tsk, cls.gen = projects["TSK"], projects["CRS"]
        cours = cls.admin.post("/api/timesheet/budget/sets", {"label": "Cours"})
        for code, label in (("CRS-01", "Séances de cours"), ("CRS-02", "Réunion d'équipe"), ("CRS-03", "Lectures")):
            cls.admin.post("/api/timesheet/budget/lines", {"set_id": cours["id"], "code": code, "label": label})
        cls.admin.put("/api/timesheet/projects/{}".format(cls.gen), {"task_set": cours["key"], "open_to_all": True,
                                                                    "organism": "Interne"})
        cls.cours = cours["key"]
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.people = {}
        for c in done["created"]:
            client = Client(cls.url)
            client.login(c["username"], c["temp_password"], "Outils-Essai-Plateforme-2026")
            cls.people[c["username"]] = client
        cls.monday = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    # ---------------- course Space open to all ----------------
    def test_01_gen_project(self):
        keys = [p["key"] for p in self.admin.get("/api/admin/projects")["projects"]]
        self.assertEqual(keys.count("CRS"), 1)
        conf = {p["key"]: p for p in self.admin.get("/api/timesheet/projects")["projects"]}
        self.assertEqual(conf["CRS"]["task_set"], self.cours)
        self.assertEqual(conf["CRS"]["open_to_all"], 1)
        self.assertEqual(conf["TSK"]["task_set"], "pdp")
        # Théo is member of nothing, yet can log time on the Spaces open to all
        week = self.people["theo"].get("/api/timesheet/week")
        self.assertEqual([p["key"] for p in week["projects"]], ["CRS"])  # 0.60.41 (D-O-050): no INT; leave in every Space
        self.assertEqual(len(week["meta"]["task_sets"]["pdp"]["tasks"]), 19)  # 0.60.01: steps of the PDP
        self.assertEqual(len(week["meta"]["task_sets"][self.cours]["tasks"]), 3)

    # ---------------- Help / HeadLamp (D-B-024) ----------------
    def test_01b_headlamp(self):
        mods = {m["key"]: m for m in self.admin.get("/api/me")["modules"]}
        self.assertEqual(mods["help"]["placement"], "end")
        self.assertEqual(mods["dynamite"]["placement"], "main")
        keys = [p["key"] for p in self.admin.get("/api/admin/projects")["projects"]]
        self.assertEqual(keys.count("DEMO"), 1)
        theo = self.people["theo"]
        status = theo.get("/api/help/headlamp")
        self.assertFalse(status["member"])
        self.assertEqual(sorted(int(k) for k in status["steps"]), list(range(1, 15)))  # 0.47.0: 14 steps (D-B-092)
        joined = theo.post("/api/help/headlamp/join")
        self.assertTrue(joined["member"])
        self.assertEqual(joined["role"], "editor")
        theo.post("/api/help/headlamp/join")  # twice: no error, no duplicate
        pid = joined["project"]["id"]
        pages = [p["title"] for p in theo.get("/api/dynamite/p/{}/pages".format(pid))["pages"]]
        self.assertIn("ROVER — Bienvenue dans la démo", pages)
        tasks = theo.get("/api/exploration/p/{}/plan".format(pid))["tasks"]
        self.assertEqual(len([t for t in tasks if not t["phase"].startswith("Rover")]), 6)  # the tour; then the Rover (0.60.54)
        self.assertEqual(len(theo.get("/api/codex/p/{}/refs".format(pid))["refs"]), 22)  # the guide + the Rover's 21 deliverables
        week = theo.get("/api/timesheet/week")  # HeadLamp is closed to time sheets
        self.assertNotIn("DEMO", [p["key"] for p in week["projects"]])
        found = theo.get("/api/search?q=parcours%20demo")["results"]
        self.assertTrue(any(r["project"] == "DEMO" for r in found))

    # ---------------- search ----------------
    def test_02_search(self):
        nora = self.people["nora"]
        tree = self.admin.get("/api/dynamite/p/{}/pages".format(self.tsk))
        self.assertTrue(tree)
        res = nora.get("/api/search?q=etancheite")  # accents and case ignored
        self.assertTrue(any(r["module"] == "dynamite" for r in res["results"]), res)
        self.assertTrue(all(r["project"] in ("TSK", "") for r in res["results"]))  # "" = platform (people, Audit)
        theo = self.people["theo"].get("/api/search?q=etancheite")
        self.assertEqual(theo["results"], [])  # not a member of TSK
        self.assertEqual(nora.get("/api/search?q=a")["results"], [])  # too short
        with self.assertRaises(ApiFailure):
            nora.get("/api/search?q=" + "x" * 201)  # D-B-076: 200 characters

    # ---------------- audit ----------------
    def test_03_audit(self):
        nora = self.people["nora"]
        with self.assertRaises(ApiFailure) as err:
            nora.post("/api/ui-audit", {"description": "  "})
        self.assertIn("Correctif", str(err.exception))
        item = nora.post("/api/ui-audit", {"kind": "bug", "priority": "high", "module": "Agile",
                                           "page_url": "javascript:alert(1)", "description": "Colonne trop étroite"})["item"]
        self.assertEqual(item["page_url"], "")  # never a javascript: link
        item = nora.upload("/api/ui-audit/{}/image".format(item["id"]), PNG, "image/png", "capture.png")["item"]
        self.assertTrue(item["has_image"])
        with self.assertRaises(ApiFailure) as err:
            nora.upload("/api/ui-audit/{}/image".format(item["id"]), b"<svg/>", "image/svg+xml", "x.svg")
        self.assertEqual(err.exception.status, 415)
        with self.people["theo"].opener.open(self.url + "/api/ui-audit/{}/image".format(item["id"])) as resp:
            self.assertEqual(resp.read(), PNG)
        with self.assertRaises(ApiFailure) as err:
            nora.patch("/api/ui-audit/{}".format(item["id"]), {"status": "done"})
        self.assertEqual(err.exception.status, 403)
        done = self.admin.patch("/api/ui-audit/{}".format(item["id"]), {"status": "done", "admin_note": "Corrigé"})["item"]
        self.assertEqual(done["status_label"], "Fait")
        self.assertEqual(self.people["theo"].get("/api/ui-audit")["items"][0]["id"], item["id"])

    def test_03b_audit_planning(self):
        nora = self.people["nora"]
        ids = [nora.post("/api/ui-audit", {"description": "Obs {}".format(n)})["item"]["id"] for n in range(3)]
        self.assertGreaterEqual(nora.get("/api/ui-audit/count")["open"], 3)
        with self.assertRaises(ApiFailure) as err:  # planning is for administrators
            nora.post("/api/ui-audit/bulk", {"ids": ids, "changes": {"target_release": "0.15.0"}})
        self.assertEqual(err.exception.status, 403)
        items = self.admin.post("/api/ui-audit/bulk", {"ids": ids[:2], "changes": {"target_release": "0.15.0"}})["items"]
        self.assertEqual({i["status"] for i in items}, {"planned"})  # a release given: planned
        users = {u["display_name"]: u["id"] for u in self.admin.get("/api/ui-audit")["users"]}
        one = self.admin.patch("/api/ui-audit/{}".format(ids[2]), {"assignee_id": users["Nora Essai"],
                                                                   "target_release": "0.9.0", "priority": "high"})["item"]
        self.assertEqual((one["assignee_name"], one["status"]), ("Nora Essai", "planned"))
        with self.assertRaises(ApiFailure):
            self.admin.patch("/api/ui-audit/{}".format(ids[2]), {"assignee_id": 99999})
        listing = self.admin.get("/api/ui-audit")
        self.assertEqual(listing["releases"], ["0.9.0", "0.15.0"])  # numeric order
        with self.admin.opener.open(self.url + "/api/ui-audit/export.csv") as resp:
            text = resp.read().decode("utf-8-sig")
        self.assertTrue(text.startswith("ID,Statut,Type"))
        self.assertIn("0.15.0", text)

    # ---------------- timesheet ----------------
    def test_04_week_cycle(self):
        nora = self.people["nora"]
        e1 = nora.post("/api/timesheet/entries", {"work_date": self.monday, "project_id": self.tsk,
                                                  "task_key": "B-09", "hours": 3.5, "description": ""})["entry"]
        e2 = nora.post("/api/timesheet/entries", {"work_date": self.monday, "project_id": self.gen,
                                                  "hours": 1, "description": "Séance de cours"})["entry"]
        self.assertEqual(e2["task_key"], "CRS-01")  # default = first task of the course set
        with self.assertRaises(ApiFailure):  # PDP code on the course project
            nora.patch("/api/timesheet/entries/{}".format(e2["id"]), {"task_key": "A-01"})
        nora.patch("/api/timesheet/entries/{}".format(e2["id"]), {"task_key": "CRS-03"})
        with self.assertRaises(ApiFailure) as err:  # blocked: empty description
            nora.post("/api/timesheet/week/submit", {"start": self.monday})
        self.assertIn("description vide", str(err.exception))
        with self.assertRaises(ApiFailure):  # quarter hours only
            nora.patch("/api/timesheet/entries/{}".format(e1["id"]), {"hours": 1.1})
        with self.assertRaises(ApiFailure):  # more than 24 h in one day
            nora.patch("/api/timesheet/entries/{}".format(e1["id"]), {"hours": 23.5})
        nora.patch("/api/timesheet/entries/{}".format(e1["id"]), {"description": "Arbre des fonctions rev B"})
        week = nora.post("/api/timesheet/week/submit", {"start": self.monday})["week"]
        self.assertEqual(week["status"], "submitted")
        with self.assertRaises(ApiFailure) as err:  # locked once submitted
            nora.patch("/api/timesheet/entries/{}".format(e1["id"]), {"hours": 2})
        self.assertEqual(err.exception.status, 409)
        with self.assertRaises(ApiFailure):  # approval is for administrators
            nora.get("/api/timesheet/approvals")
        pending = self.admin.get("/api/timesheet/approvals")["weeks"]
        mine = next(w for w in pending if w["username"] == "nora")
        self.assertEqual(mine["total"], 4.5)
        with self.assertRaises(ApiFailure):  # a return needs a note
            self.admin.post("/api/timesheet/weeks/{}/decision".format(mine["id"]), {"action": "return"})
        self.admin.post("/api/timesheet/weeks/{}/decision".format(mine["id"]), {"action": "return", "note": "Précisez"})
        self.assertEqual(nora.get("/api/timesheet/week?start=" + self.monday)["week"]["status"], "returned")
        nora.post("/api/timesheet/week/submit", {"start": self.monday})
        self.admin.post("/api/timesheet/weeks/{}/decision".format(mine["id"]), {"action": "approve"})
        self.assertEqual(nora.get("/api/timesheet/week?start=" + self.monday)["week"]["status"], "approved")

    def test_05_export(self):
        self.admin.put("/api/timesheet/projects/{}".format(self.tsk), {"organism": "CNRC-PARI", "contract_ref": "PARI-123"})
        with self.assertRaises(ApiFailure) as err:
            self.people["nora"].get("/api/timesheet/export.xlsx")
        self.assertEqual(err.exception.status, 403)
        start = (dt.date.today() - dt.timedelta(days=40)).isoformat()
        url = "/api/timesheet/export.xlsx?from={}&to={}&status=approved".format(start, dt.date.today() + dt.timedelta(days=7))
        with self.admin.opener.open(self.url + url) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            summary = z.read("xl/worksheets/sheet1.xml").decode()
            detail = z.read("xl/worksheets/sheet2.xml").decode()
        self.assertIn("CNRC-PARI", summary)
        self.assertIn("Interne", summary)
        self.assertIn("TOTAL GÉNÉRAL", summary)
        self.assertIn("Arbre des fonctions rev B", detail)
        with self.admin.opener.open(self.url + url + "&organism=CNRC-PARI") as resp:
            with zipfile.ZipFile(io.BytesIO(resp.read())) as z:
                only = z.read("xl/worksheets/sheet2.xml").decode()
        self.assertNotIn("Séance de cours", only)
        self.assertIn("Arbre des fonctions rev B", only)


    def test_06_copies(self):
        nora = self.people["nora"]
        cur = dt.date.fromisoformat(self.monday)
        wa, wb = (cur - dt.timedelta(days=14)).isoformat(), (cur - dt.timedelta(days=7)).isoformat()
        e1 = nora.post("/api/timesheet/entries", {"work_date": wa, "project_id": self.tsk, "task_key": "A-04",
                                                  "hours": 6, "description": "Architecture"})["entry"]
        nora.post("/api/timesheet/entries", {"work_date": wa, "project_id": self.gen, "task_key": "CRS-02",
                                             "hours": 1, "description": "Réunion générale"})
        days = [(dt.date.fromisoformat(wa) + dt.timedelta(days=n)).isoformat() for n in range(1, 5)]
        res = nora.post("/api/timesheet/copy/days", {"entry_ids": [e1["id"]], "to_days": days})
        self.assertEqual(res["copied"]["created"], 4)
        self.assertEqual(res["total"], 31)
        monday_ids = [e["id"] for e in res["entries"] if e["work_date"] == wa]
        with self.assertRaises(ApiFailure) as err:  # 3 x (6 + 1 + 6...) would pass 24 h on Tuesday
            for _ in range(4):
                nora.post("/api/timesheet/copy/days", {"entry_ids": monday_ids, "to_days": [days[0]]})
        self.assertIn("24 h", str(err.exception))
        with self.assertRaises(ApiFailure):  # another person's ranges
            self.people["theo"].post("/api/timesheet/copy/days", {"entry_ids": [e1["id"]], "to_days": [days[0]]})
        recent = [w["week_start"] for w in nora.get("/api/timesheet/copy/weeks")["weeks"]]
        self.assertIn(wa, recent)
        week_a = nora.get("/api/timesheet/week?start=" + wa)
        res = nora.post("/api/timesheet/copy/week", {"start": wb, "source": wa})
        self.assertEqual(len(res["entries"]), len(week_a["entries"]))
        self.assertEqual(res["total"], week_a["total"])
        self.assertEqual(sorted(e["work_date"] for e in res["entries"]),
                         sorted((dt.date.fromisoformat(e["work_date"]) + dt.timedelta(days=7)).isoformat()
                                for e in week_a["entries"]))
        res = nora.post("/api/timesheet/copy/week", {"start": wb, "source": wa, "mode": "replace"})
        self.assertEqual((len(res["entries"]), res["copied"]["removed"]), (len(week_a["entries"]),) * 2)
        with self.assertRaises(ApiFailure):  # same week
            nora.post("/api/timesheet/copy/week", {"start": wa, "source": wa})
        with self.assertRaises(ApiFailure) as err:  # the current week is approved (test_04): locked
            nora.post("/api/timesheet/copy/week", {"start": self.monday, "source": wa})
        self.assertEqual(err.exception.status, 409)

if __name__ == "__main__":
    unittest.main()
