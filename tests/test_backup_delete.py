"""0.60.79 (D-O-085): an administrator erases a restore point or a copy of the code, with the exact name sent back
as the second confirmation; anybody else is refused, and the audit journal keeps the trace.

    python -m unittest tests.test_backup_delete -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, restorepoints, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

CODE = "code_v0.60.70_20261101-101500.zip"


class BackupDeleteTest(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fail_code(self, call):
        with self.assertRaises(ApiFailure) as caught:
            call()
        return caught.exception.status

    def test_01_restore_point(self):
        name = self.admin.post("/api/admin/restore-points", {"note": "à effacer"})["point"]["name"]
        url = "/api/admin/restore-points/" + name + "/delete"
        self.assertEqual(self.fail_code(lambda: self.admin.post(url, {"confirm": "autre"})), 400)
        self.assertIn(name, [p["name"] for p in restorepoints.points(self.data_dir)])  # still there
        done = self.admin.post(url, {"confirm": name})
        self.assertNotIn(name, [p["name"] for p in done["points"]])
        folder = self.data_dir / "restore_points"
        self.assertFalse((folder / (name + ".sqlite")).exists())
        self.assertFalse((folder / (name + ".json")).exists())
        self.assertEqual(self.fail_code(lambda: self.admin.post(url, {"confirm": name})), 404)  # gone
        audit = self.admin.get("/api/admin/audit")
        self.assertIn("restore_point_deleted", str(audit))

    def test_02_code_copy(self):
        backups = self.data_dir / "updates" / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        (backups / CODE).write_bytes(b"PK\x05\x06" + b"\0" * 18)  # an empty zip is enough: it is never opened here
        url = "/api/admin/code-backups/" + CODE + "/delete"
        self.assertEqual(self.fail_code(lambda: self.admin.post(url, {"confirm": ""})), 400)
        self.assertTrue((backups / CODE).exists())
        done = self.admin.post(url, {"confirm": CODE})
        self.assertEqual(done["framework"], [])
        self.assertFalse((backups / CODE).exists())
        self.assertEqual(self.fail_code(lambda: self.admin.post(url, {"confirm": CODE})), 404)
        self.assertIn("code_backup_deleted", str(self.admin.get("/api/admin/audit")))

    def test_03_not_for_a_plain_account(self):
        made = self.admin.post("/api/admin/users", {"username": "bob", "display_name": "Bob"})
        bob = Client(self.url)
        bob.login("bob", made["temp_password"], "Sauvegarde-Test-2026!")
        name = self.admin.post("/api/admin/restore-points", {})["point"]["name"]
        status = self.fail_code(lambda: bob.post("/api/admin/restore-points/" + name + "/delete", {"confirm": name}))
        self.assertIn(status, (401, 403))
        self.assertIn(name, [p["name"] for p in restorepoints.points(self.data_dir)])


if __name__ == "__main__":
    unittest.main()
