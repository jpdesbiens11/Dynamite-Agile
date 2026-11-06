"""0.60.49 (D-O-058): one Space at installation, DEMO -- the former HeadLamp (guided tour, sandbox, training, reference
library) with the complete Rover example inside, no example account; an administrator hides it for everyone; an older
installation gets its HEADLAMP Space renamed DEMO and the Rover loaded once."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


def _server(name):
    tmp = tempfile.TemporaryDirectory()
    data_dir = Path(tmp.name)
    cfg = load_config(data_dir)
    cfg["port"] = 0
    db.init_db(data_dir / name, modules.registered_schema(), modules.registered_migrations())
    with db.connect() as conn:
        auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
    return tmp, data_dir, cfg


class DemoSpaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.data_dir, cls.cfg = _server("demo.db")
        startup.run(cls.data_dir, cls.cfg)
        startup.run(cls.data_dir, cls.cfg)  # a second start-up adds nothing
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_one_space_with_the_rover_and_inactive_example_accounts(self):
        projects = self.admin.get("/api/admin/projects")["projects"]
        self.assertEqual([p["key"] for p in projects], ["DEMO"])
        pid = projects[0]["id"]
        titles = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]]
        self.assertEqual(titles.count("Rover — accueil du projet"), 1)
        self.assertIn("ROVER — Bienvenue dans la démo", titles)
        with db.connect() as conn:
            users = {r["username"]: r["is_active"] for r in conn.execute("SELECT username, is_active FROM users")}
            # 0.60.54 (D-O-063): the Rover's team, inactive -- nobody signs in with them
            self.assertEqual(users, {"admin": 1, "demo.nina": 0, "demo.lea": 0, "demo.hugo": 0, "demo.alexis": 0})
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM diamond_functions WHERE project_id = ?", (pid,)).fetchone()[0], 39)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tools_kt WHERE project_id = ?", (pid,)).fetchone()[0], 1)
            loaded = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'demo_example_loaded'").fetchone()[0]
            self.assertEqual(loaded, 1)
            body = conn.execute("SELECT v.body FROM dynamite_pages p JOIN dynamite_versions v ON v.page_id = p.id AND "
                                "v.version = p.current_version WHERE p.project_id = ? AND p.title = 'Rover — accueil du projet'",
                                (pid,)).fetchone()["body"]
            self.assertNotIn("Brouillon IA", body)

    def test_02_hidden_for_everyone_pages_still_reachable(self):
        self.assertIn("DEMO", [p["key"] for p in self.admin.get("/api/me")["projects"]])
        self.assertTrue(self.admin.put("/api/admin/demo", {"hidden": True})["hidden"])
        self.assertNotIn("DEMO", [p["key"] for p in self.admin.get("/api/me")["projects"]])
        docs = self.admin.get("/api/help/headlamp")["docs"]
        pid = self.admin.get("/api/help/headlamp")["project"]["id"]
        self.assertEqual(self.admin.get("/api/dynamite/p/{}/pages/{}".format(pid, docs["hub"]))["page"]["title"], "Documentation des modules")
        self.assertFalse(self.admin.put("/api/admin/demo", {"hidden": False})["hidden"])


class HeadLampMigrationTest(unittest.TestCase):
    def test_older_installation_gets_demo(self):
        tmp, data_dir, cfg = _server("old.db")
        try:
            from modules.help import demo_example
            saved = demo_example.FILE
            demo_example.FILE = data_dir / "missing.json"  # the installation as it was: HeadLamp, no Rover yet
            try:
                startup.run(data_dir, cfg)
            finally:
                demo_example.FILE = saved
            with db.connect() as conn:
                conn.execute("UPDATE projects SET key = 'HEADLAMP', name = 'HeadLamp [Sandbox] — Prise en main' WHERE key = 'DEMO'")
                conn.execute("INSERT INTO user_prefs (user_id, prefs, updated_at) VALUES (1, '{\"default_space\": \"HEADLAMP\"}', '2026-01-01') "
                             "ON CONFLICT(user_id) DO UPDATE SET prefs = excluded.prefs")
            startup.run(data_dir, cfg)
            with db.connect() as conn:
                self.assertEqual([r["key"] for r in conn.execute("SELECT key FROM projects")], ["DEMO"])
                self.assertIn('"DEMO"', conn.execute("SELECT prefs FROM user_prefs WHERE user_id = 1").fetchone()["prefs"])
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'demo_example_loaded'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'project_key_changed'").fetchone()[0], 1)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
