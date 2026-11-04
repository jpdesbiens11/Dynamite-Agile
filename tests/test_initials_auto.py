"""0.60.19 (D-O-030): the 3-letter traceability key is given automatically from the name (JDE for Jean-Philippe
Desbiens, ADM for admin), unique, at creation, at start-up and at the first visit; and a write of the settings merges
its own keys, so two writes sent together (the default Space and the [new] badge it carries) never undo each other."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, prefs, router, update  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


class InitialsAutoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_candidates(self):
        first = lambda name, user="x": next(prefs.initial_candidates(name, user))  # noqa: E731
        self.assertEqual(first("Jean-Philippe Desbiens"), "JDE")
        self.assertEqual(first("Administrateur", "admin"), "ADM")
        self.assertEqual(first("Léa Tremblay"), "LTR")
        self.assertEqual(first("Nina"), "NIN")
        self.assertIn("JPD", list(prefs.initial_candidates("Jean-Philippe Desbiens"))[:12])  # the middle name

    def test_02_given_at_creation_and_unique(self):
        self.assertEqual(self.admin.get("/api/me")["prefs"]["initials"], "ADM")
        a = self.admin.post("/api/admin/users", {"username": "jp", "display_name": "Jean-Philippe Desbiens"})["user"]
        b = self.admin.post("/api/admin/users", {"username": "jd", "display_name": "Julie Desrosiers"})["user"]
        with db.connect() as conn:
            self.assertEqual(prefs.get(conn, a["id"])["initials"], "JDE")
            self.assertEqual(prefs.get(conn, b["id"])["initials"], "JDS")  # JDE taken: next letter of the name

    def test_03_start_up_fills_older_accounts(self):
        with db.connect() as conn:
            uid = conn.execute("INSERT INTO users (username, display_name, password_hash, is_admin, is_active, "
                               "must_change_password, created_at) VALUES ('hugo', 'Hugo Martin', 'x', 0, 1, 1, ?)",
                               (db.utc_now(),)).lastrowid
            self.assertFalse(prefs.has_initials(conn, uid))
            self.assertGreaterEqual(prefs.fill_initials(conn), 1)
            self.assertEqual(prefs.get(conn, uid)["initials"], "HMA")
            prefs._put(conn, uid, {"initials": "HUG"})  # chosen by the person: never replaced
            prefs.fill_initials(conn)
            self.assertEqual(prefs.get(conn, uid)["initials"], "HUG")

    def test_04_writes_merge(self):
        """The default Space survives the [new] badge saved at the same time from an older copy of the settings."""
        self.admin.post("/api/admin/projects", {"provision": False, "key": "EQP", "name": "EQP", "description": ""})
        self.admin.put("/api/me/prefs", {"default_space": "EQP"})
        self.admin.post("/api/new/seen", {"id": "0.60.19-test"})
        me = self.admin.get("/api/me")["prefs"]
        self.assertEqual(me["default_space"], "EQP")
        with db.connect() as conn:
            uid = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
            self.assertIn("0.60.19-test", update._seen(conn, uid)[1])
        self.admin.put("/api/me/prefs", {"theme": "carnet"})  # another setting keeps the list of badges seen
        with db.connect() as conn:
            self.assertIn("0.60.19-test", update._seen(conn, uid)[1])
        self.admin.put("/api/me/prefs", {"default_space": ""})

    def test_05_tools_wiki_never_default(self):
        js = (BASE_DIR / "static" / "js" / "tools" / "spaces.js").read_text("utf-8")
        self.assertIn("disabled: wikiOnly", js)
        self.assertIn("DA.wikiOnlyKey = WIKI_ONLY_KEY", (BASE_DIR / "static" / "js" / "app.js").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
