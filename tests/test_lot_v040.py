"""0.50.0 (D-B-096 to D-B-101): one Test Base per Space, Space composed tab by tab, answers from the Dashboard,
default Space, Funding Spaces in Excel.

    python -m unittest tests.test_lot_v040 -v
"""
import io
import sqlite3
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
from modules.exploration import xlsx  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV040Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False, dev_mode=False)
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        for key, name in (("P1", "Projet 1"), ("P3", "Projet 3")):
            cls.admin.post("/api/admin/projects", {"key": key, "name": name})
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        made = cls.admin.post("/api/admin/users", {"username": "davide", "display_name": "Davide"})
        cls.davide_pw = made.get("temp_password") or made.get("password")
        for key in ("P1", "P3"):
            cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid[key], made.get("id") or made["user"]["id"]), {"role": "editor"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as ctx:
            fn(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)
        return ctx.exception.message

    # ---------------------------------------------------------------- D-B-097
    def test_01_one_test_base_per_space(self):
        ref = self.admin.get("/api/testing/tests")
        self.assertTrue(ref["reference"])
        p1 = self.admin.get("/api/testing/tests?space=P1")
        self.assertEqual(p1["space"], "P1")
        self.assertEqual(len(p1["tests"]), len(ref["tests"]))  # a copy of the catalogue
        self.admin.patch("/api/testing/tests/TST-ELE-01?space=P1", {"title": "Capacité P1"})
        self.assertEqual(self.admin.get("/api/testing/tests/TST-ELE-01?space=P1")["test"]["title"], "Capacité P1")
        self.assertNotEqual(self.admin.get("/api/testing/tests/TST-ELE-01")["test"]["title"], "Capacité P1")
        self.assertNotEqual(self.admin.get("/api/testing/tests/TST-ELE-01?space=P3")["test"]["title"], "Capacité P1")
        made = self.admin.post("/api/testing/tests?space=P1", {"title": "Essai propre à P1", "subject": "mech"})
        self.fails(404, self.admin.get, "/api/testing/tests/{}?space=P3".format(made["test_id"]))
        base = "/api/agile/p/{}".format(self.pid["P3"])
        msg = self.fails(400, self.admin.post, base + "/goldmine/requirements",
                         {"statement": "Le module doit être gris.", "test_ref": made["test_id"]})
        self.assertIn("inconnu", msg)  # P1's own test is not in P3's base
        self.admin.post("/api/agile/p/{}/goldmine/requirements".format(self.pid["P1"]),
                        {"statement": "Le module doit être gris.", "test_ref": made["test_id"]})

    def test_02_history_kept_by_migration(self):
        with db.connect() as conn:
            sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'testing_tests'").fetchone()[0]
            self.assertIn("UNIQUE (project_id, test_id)", sql)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    # ---------------------------------------------------------------- D-B-099
    def test_03_compose_a_space(self):
        p1 = "/api/agile/p/{}".format(self.pid["P1"])
        self.admin.post(p1 + "/goldmine/requirements", {"statement": "Le produit doit tenir 400 V.", "test_ref": "TST-ELE-01"})
        ticket = self.admin.post(p1 + "/issues", {"type_id": self.admin.get(p1 + "/meta")["types"][0]["id"], "title": "Ticket P1"})
        preview = self.admin.post("/api/admin/spacecopy", {"key": "NEW", "name": "Composé", "mode": "preview",
                                                            "parts": {"goldmine": "P1", "testing": "P1", "dynamite": ""}})
        parts = {s["part"]: s for s in preview["summary"]}
        self.assertEqual(parts["goldmine"]["source"], "P1")
        self.assertEqual(parts["dynamite"]["source"], "")
        self.fails(409, self.admin.post, "/api/admin/spacecopy", {"key": "P1", "name": "x", "mode": "preview", "parts": {}})
        made = self.admin.post("/api/admin/spacecopy", {"key": "NEW", "name": "Composé", "parts": {"goldmine": "P1", "testing": "P1"}})
        new = made["project"]["id"]
        reqs = self.admin.get("/api/agile/p/{}/goldmine".format(new))["requirements"]
        self.assertTrue(any(r["title"].startswith("Le produit doit tenir 400 V") or "400 V" in r.get("statement", "") for r in reqs))
        issues = [i["title"] for i in self.admin.get("/api/agile/p/{}/issues".format(new)).get("issues", [])]
        self.assertNotIn("Ticket P1", issues)  # Agile was « Vide »
        self.assertEqual(self.admin.get("/api/testing/tests/TST-ELE-01?space=NEW")["test"]["title"], "Capacité P1")
        self.assertTrue(ticket["key"].startswith("P1-"))

    # ---------------------------------------------------------------- D-B-100
    def test_04_answer_from_the_dashboard(self):
        davide = Client(self.url)
        me = davide.login("davide", self.davide_pw, new_password="Mot-De-Passe-2026!")
        self.assertTrue(me["user"])
        p1 = "/api/agile/p/{}".format(self.pid["P1"])
        issue = self.admin.post(p1 + "/issues", {"type_id": self.admin.get(p1 + "/meta")["types"][0]["id"], "title": "Question tension"})
        davide.post(p1 + "/issues/{}/comments".format(issue["number"]), {"body": "@admin quelle tension nominale ?"})
        inbox = self.admin.get("/api/mentions")["messages"]
        msg = next(m for m in inbox if "tension" in m["excerpt"])
        self.assertTrue(msg["can_reply"])
        done = self.admin.post("/api/mentions/{}/reply".format(msg["id"]), {"text": "400 V nominal."})
        self.assertIn("Davide", done["notice"])
        self.assertNotIn(msg["id"], [m["id"] for m in self.admin.get("/api/mentions")["messages"]])
        self.assertIn(msg["id"], [m["id"] for m in self.admin.get("/api/mentions?box=done")["messages"]])
        comments = self.admin.get(p1 + "/issues/{}".format(issue["number"]))
        self.assertIn("400 V nominal. @davide", str(comments))
        answer = next(m for m in davide.get("/api/mentions")["messages"] if m["reply_to"] == msg["id"])
        davide.post("/api/mentions/{}/ack".format(answer["id"]), {})
        self.assertNotIn(answer["id"], [m["id"] for m in davide.get("/api/mentions")["messages"]])
        self.fails(404, davide.post, "/api/mentions/{}/ack".format(msg["id"]), {})  # not his message

    # ---------------------------------------------------------------- D-B-098
    def test_05_default_space(self):
        self.assertEqual(self.admin.put("/api/me/prefs", {"default_space": "p3"})["prefs"]["default_space"], "P3")
        self.fails(400, self.admin.put, "/api/me/prefs", {"default_space": "NOPE"})
        self.assertEqual(self.admin.put("/api/me/prefs", {"default_space": ""})["prefs"]["default_space"], "")

    # ---------------------------------------------------------------- D-B-101
    def _book(self, data):
        return xlsx.read(data, prefer=())

    def test_06_funding_spaces_in_excel(self):
        with self.admin.opener.open(self.url + "/api/timesheet/budget/export.xlsx") as resp:
            book = self._book(resp.read())
        name, rows = next(iter(book.items()))
        self.assertTrue(rows[0][0].startswith("Funding Space key"))
        sheet = xlsx.Sheet("Nouveau")
        sheet.add("Funding Space key (vide = nouvel espace)", "")
        sheet.add("Label", "PARI Prototype")
        sheet.add("Active", "oui")
        sheet.add()
        sheet.add("Code", "Label", "Claimable", "Active")
        sheet.add("PARI-01", "Conception", "oui", "oui")
        sheet.add("PARI-02", "Essais", "non", "oui")
        bad = xlsx.Sheet("Mauvais")
        bad.add("Funding Space key", "")
        bad.add("Label", "Mauvais")
        bad.add("Active", "peut-être")
        bad.add()
        bad.add("Code", "Label", "Claimable", "Active")
        bad.add("X1", "Code invalide", "oui", "oui")
        existing = xlsx.Sheet("Existant")
        for r in rows:
            existing.add(*[c for c in r])
        existing.rows[5][1] = existing.rows[5][1] + " (révisé)"
        res = self.admin.upload("/api/timesheet/budget/import", xlsx.write([sheet, bad, existing]))
        by = {s["sheet"]: s for s in res["spaces"]}
        self.assertEqual(by["Nouveau"]["status"], "new")
        self.assertTrue(by["Mauvais"]["problems"])
        self.assertEqual(by["Existant"]["status"], "changed")
        self.assertIn("(révisé)", " ".join(by["Existant"]["changes"]))
        done = self.admin.post("/api/timesheet/budget/import/" + res["token"], {"accept": ["Nouveau"]})
        self.assertEqual([d["label"] for d in done["applied"]], ["PARI Prototype"])
        sets = self.admin.get("/api/timesheet/budget")["sets"]
        self.assertTrue(any(s["label"] == "PARI Prototype" and len(s["tasks"]) == 2 for s in sets.values()))
        self.assertFalse(any("(révisé)" in t["label"] for s in sets.values() for t in s["tasks"]))  # refused: unchanged


if __name__ == "__main__":
    unittest.main(verbosity=2)
