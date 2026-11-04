"""Core v0.2 checks: versioned migrations, module assets, HEAD support.

    python -m unittest tests.test_core_v02 -v
"""
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402


class CoreV02Test(unittest.TestCase):
    def test_migrations_run_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.db"
            migration = [("demo", 1, "CREATE TABLE demo_t (id INTEGER PRIMARY KEY);"),
                         ("demo", 2, "ALTER TABLE demo_t ADD COLUMN note TEXT;")]
            db.init_db(path, "", migration)
            db.init_db(path, "", migration)  # second start: nothing re-applied
            conn = sqlite3.connect(str(path))
            versions = conn.execute("SELECT version FROM schema_migrations WHERE module = 'demo' "
                                    "ORDER BY version").fetchall()
            columns = [row[1] for row in conn.execute("PRAGMA table_info(demo_t)")]
            conn.close()
            self.assertEqual(versions, [(1,), (2,)])
            self.assertIn("note", columns)

    def test_manifest_exposes_assets(self):
        agile = next(m for m in modules.nav_manifest() if m["key"] == "agile")
        self.assertTrue(agile["available"])
        self.assertIn("/js/agile/agile.js", agile["scripts"])
        for url in agile["scripts"] + agile["styles"]:
            self.assertTrue((BASE_DIR / "static" / url.lstrip("/")).is_file(), url)
        dynamite = next(m for m in modules.nav_manifest() if m["key"] == "dynamite")
        self.assertIn("/js/dynamite/dynamite.js", dynamite["scripts"])

    def test_head_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
            cfg["port"] = 0
            cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
            db.init_db(Path(tmp) / "h.db", modules.registered_schema(), modules.registered_migrations())
            server = router.create_server(cfg, BASE_DIR / "static", Path(tmp))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = "http://127.0.0.1:{}/".format(server.server_address[1])
                with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(resp.read(), b"")
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)


class DevAdminTest(unittest.TestCase):
    def test_dev_password_skips_forced_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            db.init_db(data_dir / "dev.db", modules.registered_schema(), modules.registered_migrations())
            with db.connect() as conn:
                from core import auth
                temp = auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
                row = conn.execute("SELECT must_change_password FROM users WHERE username = 'admin'").fetchone()
            self.assertEqual(temp, "admin")
            self.assertEqual(row["must_change_password"], 0)
            self.assertFalse((data_dir / auth.INITIAL_PASSWORD_FILE).exists())
