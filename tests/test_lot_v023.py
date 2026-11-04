"""0.35.1: development temporary password « admin » (D-A-040) -- given to new and not-yet-activated accounts only in
development mode, never in production; the change at first login stays mandatory.

    python -m unittest tests.test_lot_v023 -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules  # noqa: E402


class LotV023Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db.init_db(Path(self.tmp.name) / "t.db", modules.registered_schema(), modules.registered_migrations())

    def tearDown(self):
        auth.DEV_TEMP_PASSWORD = None
        self.tmp.cleanup()

    def test_production_passwords_stay_random(self):
        auth.DEV_TEMP_PASSWORD = None
        self.assertNotEqual(auth.generate_temp_password(), auth.generate_temp_password())
        with db.connect() as conn:
            self.assertEqual(auth.reset_pending_temp_passwords(conn), 0)

    def test_development_temp_password(self):
        with db.connect() as conn:
            conn.execute("INSERT INTO users (username, display_name, password_hash, must_change_password, is_active, "
                         "created_at) VALUES ('ana', 'Ana', ?, 1, 1, '2026-09-29')", (auth.hash_password("x" * 16),))
            conn.execute("INSERT INTO users (username, display_name, password_hash, must_change_password, is_active, "
                         "created_at) VALUES ('bob', 'Bob', ?, 0, 1, '2026-09-29')", (auth.hash_password("Mine-2026-Bob!"),))
        auth.DEV_TEMP_PASSWORD = "admin"
        self.assertEqual(auth.generate_temp_password(), "admin")
        with db.connect() as conn:
            self.assertEqual(auth.reset_pending_temp_passwords(conn), 1)
            ana, bob = [conn.execute("SELECT password_hash FROM users WHERE username = ?", (u,)).fetchone()[0]
                        for u in ("ana", "bob")]
        self.assertTrue(auth.verify_password("admin", ana))
        self.assertTrue(auth.verify_password("Mine-2026-Bob!", bob))  # own password kept


if __name__ == "__main__":
    unittest.main(verbosity=2)
