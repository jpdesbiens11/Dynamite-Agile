"""Core lot v0.11 (0.21.0): duplicate an account (D-B-045), dashboard « voir
comme » (D-B-046), configuration snapshots (D-B-047), annual objectives
(D-B-048), no absence project (D-B-041), requirement bucket (D-B-039),
BDC upgrade of an existing HeadLamp (D-B-040).

    python -m unittest tests.test_lot_v011 -v
"""
import datetime as dt
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, platform_config, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur ana | Ana Modèle | utilisateur | actif
utilisateur marc | Marc Gestion | utilisateur | actif
utilisateur zoe | Zoé Autre | utilisateur | actif
droit ana | ONE | editeur
droit ana | TWO | lecteur
"""


class LotV011Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(cls.data_dir)
        cls.cfg["port"] = 0
        cls.cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cls.cfg)
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        for key in ("ONE", "TWO"):
            cls.admin.post("/api/admin/projects", {"key": key, "name": key, "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.people, cls.ids = {}, {}
        for c in done["created"]:
            client = Client(cls.url)
            me = client.login(c["username"], c["temp_password"], "Essai-Lot-Onze-2026!")
            cls.people[c["username"]] = client
            cls.ids[c["username"]] = me["user"]["id"]
        cls.projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_duplicate_user(self):
        self.people["ana"].put("/api/me/prefs", {"manager_id": self.ids["marc"], "theme": "dark"})
        res = self.admin.post("/api/admin/users/{}/duplicate".format(self.ids["ana"]),
                              {"username": "stagiaire.ana", "display_name": "Stagiaire Ana"})
        self.assertEqual(res["projects"], 2)
        self.assertTrue(res["temp_password"])
        cells = self.admin.get("/api/admin/rights")["cells"]
        uid = res["user"]["id"]
        self.assertEqual(cells["{}:{}".format(uid, self.projects["ONE"])], "editor")
        self.assertEqual(cells["{}:{}".format(uid, self.projects["TWO"])], "reader")
        prefs = self.admin.get("/api/admin/users/{}/prefs".format(uid))["prefs"]
        self.assertEqual(prefs["manager_id"], self.ids["marc"])
        self.assertFalse(res["user"]["is_admin"])
        with self.assertRaises(ApiFailure) as err:  # same username twice
            self.admin.post("/api/admin/users/{}/duplicate".format(self.ids["ana"]), {"username": "stagiaire.ana", "display_name": "X"})
        self.assertEqual(err.exception.status, 409)
        with self.assertRaises(ApiFailure):
            self.people["ana"].post("/api/admin/users/{}/duplicate".format(self.ids["ana"]), {"username": "x.y", "display_name": "X"})

    def test_02_view_as(self):
        mine = self.admin.get("/api/dashboard")
        self.assertIsNone(mine["viewing"])
        self.assertTrue(mine["people"])
        other = self.admin.get("/api/dashboard?user={}".format(self.ids["ana"]))
        self.assertEqual(other["viewing"]["id"], self.ids["ana"])
        self.assertFalse(any("action" in i for s in other["sections"] for i in s["items"]))
        with self.assertRaises(ApiFailure) as err:
            self.people["ana"].get("/api/dashboard?user={}".format(self.ids["marc"]))
        self.assertEqual(err.exception.status, 403)
        self.assertIsNone(self.people["ana"].get("/api/dashboard")["people"])

    def test_03_config_snapshots(self):
        st, headers, raw = self.admin.raw_get("/api/admin/config/current.md")
        self.assertEqual(st, 200)
        text = raw.decode("utf-8")
        for tag in ("da:privacy", "da:access-rules", "da:timesheet-projects", "da:user-prefs", "da:diagnostic"):
            self.assertIn(tag, text)
        self.assertNotIn("password_hash", text)
        tuned = text.replace('"watermark": false', '"watermark": true').replace("droit       ana | TWO | lecteur", "droit       ana | TWO | editeur")
        dry = self.admin.post("/api/admin/config/import", {"text": tuned, "dry_run": True})
        sections = {c["section"] for c in dry["changes"]}
        self.assertEqual(sections, {"Confidentialité", "Comptes et droits"}, dry["changes"])
        self.assertFalse(self.admin.get("/api/admin/policy")["privacy"]["watermark"])
        res = self.admin.post("/api/admin/config/import", {"text": tuned, "dry_run": False, "note": "essai"})
        self.assertTrue(res["stored"].startswith("config_"))
        self.assertTrue(self.admin.get("/api/admin/policy")["privacy"]["watermark"])
        snaps = self.admin.get("/api/admin/config")["snapshots"]
        before = next(s for s in snaps if s["source"] == "before")
        back = self.admin.post("/api/admin/config/{}/apply".format(before["id"]), {"dry_run": False})  # revert
        self.assertTrue(back["changes"])
        self.assertFalse(self.admin.get("/api/admin/policy")["privacy"]["watermark"])
        cells = self.admin.get("/api/admin/rights")["cells"]
        self.assertEqual(cells["{}:{}".format(self.ids["ana"], self.projects["TWO"])], "reader")
        with db.connect() as conn:  # 3-month retention
            conn.execute("UPDATE config_snapshots SET created_at = '2020-01-01T00:00:00' WHERE id = ?", (before["id"],))
        self.admin.post("/api/admin/config/import", {"text": text, "dry_run": False})
        self.assertNotIn(before["id"], [s["id"] for s in self.admin.get("/api/admin/config")["snapshots"]])
        with self.assertRaises(ApiFailure):
            self.admin.post("/api/admin/config/import", {"text": "# rien ici", "dry_run": True})
        with self.assertRaises(ApiFailure):
            self.people["ana"].get("/api/admin/config")
        self.assertEqual(platform_config.sections("```json da:privacy\n{}\n```"), {"privacy": "{}"})

    def test_04_objectives(self):
        ana, marc, zoe = self.people["ana"], self.people["marc"], self.people["zoe"]
        year = dt.date.today().year
        ana.put("/api/me/prefs", {"manager_id": self.ids["marc"]})
        aid = self.ids["ana"]
        o1 = ana.post("/api/objectives/{}/{}".format(aid, year), {"kind": "annual", "title": "Livrer le plan d'essais"})["id"]
        o2 = ana.post("/api/objectives/{}/{}".format(aid, year), {"kind": "development", "title": "Maîtriser la DFMEA"})["id"]
        ana.patch("/api/objectives/item/{}".format(o1), {"progress": 40})
        with self.assertRaises(ApiFailure) as err:  # the level is the manager's
            ana.patch("/api/objectives/item/{}".format(o2), {"target_level": 3})
        self.assertEqual(err.exception.status, 403)
        marc.patch("/api/objectives/item/{}".format(o2), {"target_level": 3, "expectation": "Animer une DFMEA seule"})
        with self.assertRaises(ApiFailure):  # the title is the employee's
            marc.patch("/api/objectives/item/{}".format(o2), {"title": "x"})
        marc.post("/api/objectives/{}/{}/comments".format(aid, year), {"body": "Bon départ", "context": "mi-annee"})
        ana.post("/api/objectives/{}/{}/comments".format(aid, year), {"body": "Merci", "context": "libre", "objective_id": o2})
        data = marc.get("/api/objectives/{}?year={}".format(aid, year))
        self.assertEqual(data["relation"], "manager")
        self.assertEqual(len(data["comments"]), 2)
        self.assertEqual({o["target_level"] for o in data["objectives"] if o["kind"] == "development"}, {3})
        for outsider in (zoe, self.admin):  # private: not another employee, not an administrator
            with self.assertRaises(ApiFailure) as err:
                outsider.get("/api/objectives/{}?year={}".format(aid, year))
            self.assertEqual(err.exception.status, 403)
        self.assertIn(aid, [p["id"] for p in marc.get("/api/objectives/people")["people"]])
        with self.assertRaises(ApiFailure) as err:  # core lot v0.30 (D-B-111): the year closes once every item is evaluated
            marc.post("/api/objectives/{}/{}/archive".format(aid, year), {"carry": [o2]})
        self.assertEqual(err.exception.status, 409)
        base = "/api/reviews/{}/{}".format(aid, year)
        for who in (ana, marc):
            who.post(base + "/sign/start", {})
        for phase in ("mid", "end"):
            for oid in (o1, o2):
                ana.put(base + "/item", {"phase": phase, "item_type": "objective", "item_id": oid, "employee_comment": "Bilan"})
                marc.put(base + "/item", dict({"phase": phase, "item_type": "objective", "item_id": oid, "manager_comment": "Retour"},
                                              **({"verdict": "achieved"} if phase == "end" else {})))
            if phase == "end":
                ana.put(base + "/phase/end", {"employee_comment": "Bonne année"})
                marc.put(base + "/phase/end", {"manager_comment": "Bonne année"})
            for who in (ana, marc):
                who.post(base + "/sign/" + phase, {})
        res = marc.post("/api/objectives/{}/{}/archive".format(aid, year), {"carry": [o2]})
        self.assertEqual((res["carried"], res["next_year"]), (1, year + 1))
        with self.assertRaises(ApiFailure) as err:
            ana.patch("/api/objectives/item/{}".format(o1), {"progress": 90})
        self.assertEqual(err.exception.status, 409)
        nxt = ana.get("/api/objectives/{}?year={}".format(aid, year + 1))
        self.assertEqual([(o["title"], o["target_level"], o["carried_year"]) for o in nxt["objectives"]],
                         [("Maîtriser la DFMEA", 3, year)])
        marc.patch("/api/objectives/item/{}".format(nxt["objectives"][0]["id"]), {"target_level": 4})
        audit = str(self.admin.get("/api/admin/audit"))
        self.assertIn("objective_updated", audit)
        self.assertNotIn("Animer une DFMEA seule", audit)  # the private text never goes to the journal

    def test_05_no_absence_project_and_bucket(self):
        keys = [p["key"] for p in self.admin.get("/api/admin/projects")["projects"]]
        self.assertNotIn("ABS", keys)
        base = "/api/agile/p/{}".format(self.projects["ONE"])
        self.admin.post(base + "/goldmine/requirements", {"title": "Req", "statement": "Le produit doit…", "test_ref": "TST-VER-01"})
        board_titles = [i["title"] for i in self.admin.get(base + "/issues")["issues"]]
        self.assertNotIn("Req", board_titles)  # D-B-039: requirements only in Goldmine

    def test_06_bdc_upgrade(self):
        from modules.help import gtd
        hl = self.projects["HEADLAMP"]
        base = "/api/dynamite/p/{}/pages".format(hl)
        pages = self.admin.get(base)["pages"]
        hub = next(p for p in pages if p["title"] == gtd.HUB)
        main = next(p for p in pages if p["title"] == gtd.MAIN)
        for pid, title, body in ((hub["id"], "Connaissances", None),
                                 (main["id"], None, {"type": "doc", "content": [{"type": "paragraph", "content": [
                                     {"type": "text", "text": "Ancienne version"}]}]})):
            page = self.admin.get(base + "/{}".format(pid))["page"]
            self.admin.put(base + "/{}".format(pid), {"title": title or page["title"], "body": body or page["body"],
                                                      "base_version": page["version"], "note": "0.20"})
        startup.run(self.data_dir, self.cfg)
        pages = self.admin.get(base)["pages"]
        titles = [p["title"] for p in pages]
        self.assertIn(gtd.HUB, titles)
        self.assertNotIn("Connaissances", titles)
        body = self.admin.get(base + "/{}".format(main["id"]))["page"]
        self.assertIn(gtd.PEPITE_MARK, str(body["body"]))
        self.assertGreaterEqual(body["version"], 3)  # the old text stays in the history


if __name__ == "__main__":
    unittest.main()
