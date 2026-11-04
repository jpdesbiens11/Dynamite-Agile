"""0.50.1 (D-B-103 to D-B-106): Space drop-down in Testing, restore points of the data and 3 copies of the code
(« 2 × 3 chances »), Admin « Update et sauvegardes » in one tab, Generator name pre-filled.

    python -m unittest tests.test_lot_v041 -v
"""
import datetime as dt
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, restorepoints, router, startup, update  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

DOC = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Texte"}]}]}


class LotV041Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = load_config(cls.data_dir)
        cfg.update(port=0, require_initials=False, dev_mode=False)
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "ALP", "name": "Alpha"})
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["ALP"]

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

    def page(self, title, pid=None):
        pages = "/api/dynamite/p/{}/pages".format(pid or self.pid)
        home = self.admin.get(pages)["pages"][0]
        return self.admin.post(pages, {"title": title, "parent_id": home["id"], "body": DOC})

    def titles(self, pid):
        return {p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]}

    # ---------------------------------------------------------------- D-B-104
    def test_01_daily_point_once_a_day(self):
        listed = self.admin.get("/api/admin/restore-points")
        self.assertEqual(listed["keep"], 3)
        daily = [p for p in listed["points"] if p["reason"] == "quotidien"]
        self.assertEqual(len(daily), 1)  # the first request of the day took it
        self.assertEqual(daily[0]["day"], dt.date.today().isoformat())
        self.assertIsNone(restorepoints.daily(self.data_dir, {}))  # never twice the same day
        restorepoints._checked.pop(str(self.data_dir))
        self.assertIsNone(restorepoints.daily(self.data_dir, {}))  # still one (found on disk)
        self.assertEqual(sum(p["reason"] == "quotidien" for p in self.admin.get("/api/admin/restore-points")["points"]), 1)
        self.assertTrue((self.data_dir / "restore_points" / (daily[0]["name"] + ".sqlite")).exists())

    def test_02_three_points_kept(self):
        for n in range(4):
            made = self.admin.post("/api/admin/restore-points", {"note": "essai {}".format(n)})
        points = made["points"]
        self.assertEqual(len(points), 3)
        self.assertEqual(points[0]["note"], "essai 3")
        self.assertNotIn("quotidien", [p["reason"] for p in points])  # the oldest went first
        self.assertEqual(len(list((self.data_dir / "restore_points").glob("*.sqlite"))), 3)
        self.fails(404, self.admin.get, "/api/admin/restore-points/data_20000101-000000_manuel/spaces")

    def test_03_one_space_back_as_a_new_space(self):
        self.page("Page du point")
        ref = self.admin.post("/api/codex/p/{}/refs".format(self.pid), {"doc_type": "CDCF", "step": "10", "sub": "00",
                                                                        "system_code": "CHAUF", "revision": 1, "title": "CdCF ALPHA"})
        point = self.admin.post("/api/admin/restore-points", {"note": "avant ménage"})["point"]
        spaces = {s["key"]: s for s in self.admin.get("/api/admin/restore-points/{}/spaces".format(point["name"]))["spaces"]}
        self.assertTrue(spaces["ALP"]["exists_now"])
        self.assertEqual(spaces["ALP"]["suggested_key"], "ALPR")
        url = "/api/admin/restore-points/{}/space".format(point["name"])
        self.assertIn("existe déjà", self.fails(409, self.admin.post, url, {"key": "ALP", "new_key": "ALP"}))
        done = self.admin.post(url, {"key": "ALP", "new_key": "ALPR", "new_name": "Alpha (point)"})
        self.assertEqual(done["project"]["key"], "ALPR")
        self.assertIn("Page du point", self.titles(done["project"]["id"]))
        self.assertEqual(done["skipped"].get("codex_refs"), 1, done)  # the Generator number stays unique
        self.assertTrue(ref)
        log = [a["action"] for a in self.admin.get("/api/admin/audit")["entries"]][:5]
        self.assertIn("restore_point_space", log)

    def test_04_whole_site_back_to_a_point(self):
        point = self.admin.post("/api/admin/restore-points", {"note": "avant le retour"})["point"]
        self.page("Écrite après le point")
        made = self.admin.post("/api/admin/users", {"username": "zoe", "display_name": "Zoé"})
        self.assertTrue(made)
        url = "/api/admin/restore-points/{}/revert".format(point["name"])
        self.fails(400, self.admin.post, url, {"confirm": "non"})
        done = self.admin.post(url, {"confirm": point["name"]})
        self.assertTrue(done["signed_out"])
        self.assertGreaterEqual(done["audit_rows_kept"], 2)
        self.fails(401, self.admin.get, "/api/admin/restore-points")  # every session closed
        self.admin.login("admin", "admin")
        self.assertNotIn("Écrite après le point", self.titles(self.pid))
        self.assertNotIn("zoe", [u["username"] for u in self.admin.get("/api/admin/users")["users"]])
        actions = [a["action"] for a in self.admin.get("/api/admin/audit")["entries"]]
        self.assertIn("data_reverted", actions)
        self.assertIn("user_created", actions)  # the journal written since the point is never taken back
        points = self.admin.get("/api/admin/restore-points")["points"]
        self.assertLessEqual(len(points), 3)
        self.assertEqual(points[0]["reason"], "avant-retour")
        with db.connect() as conn:  # migrations of the running code applied again
            self.assertTrue(conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0])

    def test_05_three_copies_of_the_code(self):
        ctx = types.SimpleNamespace(data_dir=self.data_dir)
        folder = update._dir(ctx, "backups")
        for n, version in enumerate(("0.49.0", "0.50.0", "0.50.1", "0.50.2")):
            (folder / "code_v{}_2026100{}-120000.zip".format(version, n + 1)).write_bytes(b"PK")
        removed = update.prune_code_backups(ctx)
        self.assertEqual(removed, ["code_v0.49.0_20261001-120000.zip"])
        versions = update.code_versions(ctx)
        self.assertEqual([c["version"] for c in versions], ["0.50.2", "0.50.1", "0.50.0"])
        status = self.admin.get("/api/update/status")
        self.assertEqual(len(status["backups"]), 3)
        self.assertEqual([c["version"] for c in self.admin.get("/api/admin/restore-points")["framework"]], ["0.50.2", "0.50.1", "0.50.0"])

    def test_06_configuration_takes_a_point(self):
        _st, _h, raw = self.admin.raw_get("/api/admin/config/current.md")
        text = raw.decode("utf-8")
        flag = '"watermark": false' if '"watermark": false' in text else '"watermark": true'
        tuned = text.replace(flag, '"watermark": true' if flag.endswith("false") else '"watermark": false')
        res = self.admin.post("/api/admin/config/import", {"text": tuned, "dry_run": False, "note": "essai point"})
        self.assertTrue(res["point"].startswith("data_"))
        self.assertEqual(self.admin.get("/api/admin/restore-points")["points"][0]["reason"], "avant-config")

    # ---------------------------------------------------------------- screens
    def test_07_screens(self):
        static = BASE_DIR / "static"
        admin = (static / "js" / "admin.js").read_text("utf-8")
        self.assertIn('["update", "Update et sauvegardes"]', admin)
        self.assertNotIn('["config", "Configuration"]', admin)  # D-B-105: one tab
        self.assertIn('MOVED = { config: "config", backups: "data" }', admin)
        self.assertIn('<script src="/js/admin_restore.js" defer></script>', (static / "index.html").read_text("utf-8"))
        upd = (static / "js" / "admin_update.js").read_text("utf-8")
        for part in ('"restore"', '"framework"', '"config"', '"data"', '"site"', "Que voulez-vous faire ?"):
            self.assertIn(part, upd)
        self.assertIn("DA.spaces.picker(T.space", (static / "js" / "testing" / "testing.js").read_text("utf-8"))  # D-B-103
        self.assertIn("opts.picker", (static / "js" / "app.js").read_text("utf-8"))
        codex = (static / "js" / "codex" / "codex.js").read_text("utf-8")  # D-B-106
        for part in ('placeholder: "ex. CHAUF"', "Copier le nom", "Project ID", "titleAuto"):
            self.assertIn(part, codex)
        self.assertIn("CX.projectId", (static / "js" / "codex" / "registry.js").read_text("utf-8"))
        for path in [static / "js" / "admin_restore.js", BASE_DIR / "core" / "restorepoints.py"]:
            self.assertLess(len(path.read_text("utf-8").splitlines()), 500, path)


if __name__ == "__main__":
    unittest.main()
