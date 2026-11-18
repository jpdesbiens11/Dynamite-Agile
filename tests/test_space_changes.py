"""0.60.120 (D-O-133, core lot v0.39): « Changements » of a Space -- every change by hand or by an AI, placed in its Space and
its tab with a link, the three letters of who made it, grouped per person / item / day; new for me until my visit or « Vu »;
the Dashboard section; exports left out; a deleted item still listed; the read state never travels with a Space."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import audit, auth, backup, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


def _id(made):
    return made.get("id") or (made.get("page") or made.get("risk") or {}).get("id")


class SpaceChangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.put("/api/me/prefs", {"initials": "ADM"})
        cls.pid = next(p["id"] for p in cls.admin.get("/api/me")["projects"] if p["key"] == "DEMO")
        made = cls.admin.post("/api/admin/users", {"username": "editeur", "display_name": "Éditeur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "editor"})
        cls.editor = Client(cls.url)
        cls.editor.login("editeur", made["temp_password"], new_password="Edition-2026!")
        cls.editor.put("/api/me/prefs", {"initials": "EDT"})
        cls.admin.post("/api/changes/seen", {"space": "DEMO"})  # what the start-up wrote is old news for the admin
        dy, dm = "/api/dynamite/p/{}".format(cls.pid), "/api/diamond/p/{}".format(cls.pid)
        cls.page_id = _id(cls.editor.post(dy + "/pages", {"title": "Note de conception"}))
        gone = _id(cls.editor.post(dy + "/pages", {"title": "Brouillon à jeter"}))
        cls.admin.delete(dy + "/pages/{}".format(gone))  # deleting a page: manager role
        risk = cls.editor.post(dm + "/risks", {"title": "Fournisseur unique du moteur"})
        cls.risk = next(r for r in risk["risks"] if r["id"] == risk["created"])
        cls.editor.patch(dm + "/risks/{}".format(cls.risk["id"]), {"title": "Fournisseur unique du moteur DC"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def lines(self, client=None, **q):
        q.setdefault("since", "all")
        query = "&".join("{}={}".format(k, v) for k, v in q.items())
        return (client or self.admin).get("/api/changes?space=DEMO&" + query)

    def line(self, data, title):
        return next(ln for ln in data["lines"] if title in ln["title"])

    def test_01_lines_say_where_who_and_what(self):
        data = self.lines()
        page = self.line(data, "Note de conception")
        self.assertEqual((page["tab"], page["initials"], page["source"]), ("dynamite", "EDT", ""))
        self.assertEqual(page["href"], "#/dynamite/DEMO/page/{}".format(self.page_id))
        self.assertEqual(page["verb"], "Création")
        self.assertTrue(page["new"])
        risk = self.line(data, "Fournisseur unique")
        self.assertEqual((risk["tab"], risk["code"], risk["count"]), ("diamond", "R-{}".format(self.risk["number"]), 2))
        self.assertIn("focus=R-", risk["href"])
        self.assertEqual(risk["verb"], "Création")  # created then modified the same day: one line
        gone = self.line(data, "Brouillon à jeter")
        self.assertTrue(gone["gone"])  # the Space was kept at the time of the write

    def test_02_filters(self):
        self.assertTrue(all(ln["tab"] == "diamond" for ln in self.lines(tab="diamond")["lines"]))
        self.assertTrue(self.lines(who="EDT")["lines"])
        self.assertFalse(self.lines(who="ZZZ")["lines"])
        self.assertIn("EDT", self.lines()["people"])
        with self.assertRaises(ApiFailure) as caught:
            self.lines(since="hier")
        self.assertEqual(caught.exception.status, 400)
        with self.assertRaises(ApiFailure) as caught:
            self.admin.get("/api/changes?space=NOPE")
        self.assertEqual(caught.exception.status, 404)

    def test_03_ai_source_and_exports_left_out(self):
        with db.connect() as conn:
            with audit.source("ai"):
                audit.log_action(conn, None, "diamond_risk_update", "diamond_risks", self.risk["id"], {"fields": ["impact"]})
            audit.log_action(conn, None, "dynamite_page_export", "dynamite_page", self.page_id)
            conn.commit()
        ai = self.lines(source="ai")["lines"]
        self.assertEqual(len(ai), 1)
        self.assertEqual((ai[0]["source"], ai[0]["fields"]), ("ai", ["impact"]))
        self.assertFalse([ln for ln in self.lines()["lines"] if ln["action"].endswith("_export")])
        self.assertTrue(all(ln["source"] == "" for ln in self.lines(source="manual")["lines"]))

    def test_04_new_for_me_until_seen(self):
        mine = self.lines(client=self.editor)
        self.assertFalse(self.line(mine, "Note de conception")["new"])  # my own change is never new for me
        before = self.admin.get("/api/changes/count?space=DEMO")["new"]
        self.assertGreaterEqual(before, 3)
        page = self.line(self.lines(), "Note de conception")
        self.admin.post("/api/changes/ack", {"space": "DEMO", "ids": page["ids"]})
        after = self.line(self.lines(), "Note de conception")
        self.assertEqual((after["new"], after["seen"]), (False, True))
        self.assertEqual(self.admin.get("/api/changes/count?space=DEMO")["new"], before - 1)
        dash = next(s for s in self.admin.get("/api/dashboard?all=1")["sections"] if s["key"] == "changes")
        self.assertTrue(any(it["href"] == "#/changes/DEMO" for it in dash["items"]))
        self.admin.post("/api/changes/seen", {"space": "DEMO"})
        self.assertEqual(self.admin.get("/api/changes/count?space=DEMO")["new"], 0)
        self.assertFalse(self.lines(state="new")["lines"])

    def test_05_trail_keeps_who_and_where(self):
        self.assertIn("change_seen", backup.SKIP)
        self.assertIn("change_acks", backup.SKIP)
        with db.connect() as conn:
            row = conn.execute("SELECT initials, project_id FROM audit_log WHERE object_type = 'diamond_risks' "
                               "AND user_id IS NOT NULL ORDER BY id DESC").fetchone()
        self.assertEqual((row["initials"], row["project_id"]), ("EDT", self.pid))


if __name__ == "__main__":
    unittest.main()
