"""0.60.63 (D-O-072): guest access -- off by default, opened by an administrator for chosen Spaces, a session with
no password, reading and exporting only (every other write refused by the server), limited per IP, closed again."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, guest, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class GuestTest(unittest.TestCase):
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
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.demo = next(p["id"] for p in cls.admin.get("/api/admin/projects")["projects"] if p["key"] == "DEMO")
        cls.other = cls.admin.post("/api/admin/projects", {"key": "PRIV", "name": "Privé"})["project"]["id"]
        made = cls.admin.post("/api/dynamite/p/{}/pages".format(cls.demo), {"title": "Page pour invités", "body": {
            "type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Bonjour"}]}]}})
        cls.page = (made.get("page") or made)["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, call):
        try:
            call()
        except ApiFailure as exc:
            return exc.status, exc.message
        return 200, ""

    def visitor(self):
        c = Client(self.url)
        me = c.post("/api/login/guest")
        return c, me

    def test_01_off_by_default(self):
        self.assertFalse(Client(self.url).get("/api/about")["guest"])
        self.assertEqual(self.status(lambda: Client(self.url).post("/api/login/guest"))[0], 403)
        self.assertEqual(self.status(lambda: self.admin.put("/api/admin/guest", {"enabled": True, "projects": []}))[0], 400)

    def test_02_open_and_read(self):
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        self.assertTrue(Client(self.url).get("/api/about")["guest"])
        c, me = self.visitor()
        self.assertTrue(me["user"]["is_guest"])
        self.assertFalse(me["user"]["is_admin"])
        self.assertEqual([p["id"] for p in me["projects"]], [self.demo])
        self.assertTrue(c.get("/api/dynamite/p/{}/pages".format(self.demo))["pages"])
        self.assertIn(self.status(lambda: c.get("/api/dynamite/p/{}/pages".format(self.other)))[0], (403, 404))
        self.assertEqual(self.status(lambda: c.get("/api/admin/users"))[0], 403)
        # each visitor has their own session
        c2, _ = self.visitor()
        self.assertTrue(c2.get("/api/me")["user"]["is_guest"])

    def test_03_never_writes(self):
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        c, _ = self.visitor()
        base = "/api/dynamite/p/{}/pages".format(self.demo)
        for call in (lambda: c.post(base, {"title": "X", "body": {"type": "doc", "content": []}}),
                     lambda: c.post(base + "/{}/comments".format(self.page), {"text": "pub !"}),
                     lambda: c.put("/api/me/prefs", {"theme": "terminal"}),
                     lambda: c.post("/api/me/password", {"old_password": "x", "new_password": "Nouveau-Mot-2026!"}),
                     lambda: c.post("/api/ui-audit", {"title": "x"})):
            status, message = self.status(call)
            self.assertEqual(status, 403)
            self.assertIn("Mode invité", message)

    def test_04_export_and_logout_allowed(self):
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        c, _ = self.visitor()
        status, _headers, data = c.raw_get("/api/dynamite/p/{}/pages/{}/export.pdf".format(self.demo, self.page))
        self.assertEqual(status, 200)
        self.assertTrue(data.startswith(b"%PDF"))
        guest.guard({"username": "invite"}, "POST", "/api/dynamite/p/1/pages/2/export.docx")  # the POST export (Mermaid) passes
        c.post("/api/logout")
        self.assertEqual(self.status(lambda: c.get("/api/me"))[0], 401)

    def test_05_close_ends_sessions(self):
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        c, _ = self.visitor()
        data = self.admin.put("/api/admin/guest", {"enabled": False})
        self.assertFalse(data["guest"]["enabled"])
        self.assertEqual(self.status(lambda: c.get("/api/me"))[0], 401)
        self.assertEqual(self.status(lambda: Client(self.url).post("/api/login/guest"))[0], 403)
        self.assertEqual(self.status(lambda: Client(self.url).post("/api/login", {"username": "invite", "password": "x"}))[0], 401)

    def test_06_rate_limited_and_journalled(self):
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        old = guest.MAX_PER_HOUR
        guest._hits.clear()
        guest.MAX_PER_HOUR = 2
        try:
            self.visitor()
            self.visitor()
            self.assertEqual(self.status(self.visitor)[0], 429)
        finally:
            guest.MAX_PER_HOUR = old
            guest._hits.clear()
        actions = [e["action"] for e in self.admin.get("/api/admin/audit")["entries"]]
        self.assertIn("guest_login", actions)
        self.assertIn("guest_access_changed", actions)

    def test_07_unchecked_space_hidden_even_with_an_old_membership(self):
        """0.60.64: visibility comes from the setting only -- a membership row left by 0.60.63 changes nothing."""
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        with db.connect() as conn:
            uid = conn.execute("SELECT id FROM users WHERE username = 'invite'").fetchone()["id"]
            conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) VALUES (?, ?, 'reader')", (uid, self.other))
        c, me = self.visitor()
        self.assertEqual([p["id"] for p in me["projects"]], [self.demo])
        self.assertIn(self.status(lambda: c.get("/api/dynamite/p/{}/pages".format(self.other)))[0], (403, 404))

    def test_08_never_the_list_of_the_accounts(self):  # 0.60.82 (D-O-088)
        made = self.admin.post("/api/admin/users", {"username": "secrete", "display_name": "Personne Secrète"})
        self.admin.put("/api/admin/projects/{}/members/{}".format(self.other, made["user"]["id"]), {"role": "editor"})
        self.admin.put("/api/admin/guest", {"enabled": True, "projects": [self.demo]})
        c, _me = self.visitor()
        for path in ("/api/mentions/people", "/api/mentions/people?q=s", "/api/me/prefs", "/api/ui-audit", "/api/ui-audit/export.csv"):
            with self.subTest(path=path):
                body = c.get(path) if not path.endswith(".csv") else c.raw_get(path)[2].decode("utf-8")
                self.assertNotIn("Personne Secrète", str(body))
                self.assertNotIn("secrete", str(body))
        self.assertEqual(c.get("/api/ui-audit/count")["open"], 0)
        # a team account still gets them
        self.assertIn("Personne Secrète", str(self.admin.get("/api/mentions/people?q=pers")))
        self.assertIn("Personne Secrète", str(self.admin.get("/api/me/prefs")["people"]))


class UpdateSafetyTest(unittest.TestCase):
    """0.60.64: the 0.60.63 package was refused online (« DELETE FROM memberships » added in core/guest.py). Every file
    of the code goes through the same DESTRUCTIVE check as an update: only the lines already there are allowed."""
    KNOWN = {("core/access_rules.py", "DELETE FROM MEMBERSHIPS"): 1, ("core/admin.py", "DELETE FROM MEMBERSHIPS"): 1,
             ("core/backup.py", "DELETE FROM PROJECTS"): 1, ("core/members.py", "DROP TABLE"): 1,
             ("core/members.py", "DELETE FROM MEMBERSHIPS"): 1, ("core/update.py", "DROP TABLE"): 1,
             ("core/update.py", "DROP COLUMN"): 1, ("modules/agile/schema.py", "DROP TABLE"): 1,
             ("modules/testing/__init__.py", "DROP TABLE"): 3}

    def test_no_new_destructive_sql(self):
        from core.update import DESTRUCTIVE
        found = {}
        for f in sorted(BASE_DIR.rglob("*.py")):
            rel = f.relative_to(BASE_DIR).as_posix()
            if rel.startswith(("tests/", ".git")) or "__pycache__" in rel:
                continue
            for m in DESTRUCTIVE.finditer(f.read_text("utf-8", "replace")):
                key = (rel, m.group(0).upper())
                found[key] = found.get(key, 0) + 1
        extra = {k: v for k, v in found.items() if v > self.KNOWN.get(k, 0)}
        self.assertEqual(extra, {}, "Une mise à jour serait refusée : SQL destructif ajouté.")


if __name__ == "__main__":
    unittest.main()
