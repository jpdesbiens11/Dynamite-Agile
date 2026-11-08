"""0.60.84 (D-O-090): one password tried on every account from one address (« password spraying ») -- each username had
its own counter, so nothing locked and every attempt cost a full PBKDF2. Now 30 failures per address in 15 minutes,
every username together, then 429 before any password is hashed; the counters that no longer lock are forgotten.

    python -m unittest tests.test_login_ip -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LoginIpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(data_dir)
        cls.cfg.update(port=0, require_initials=False, login_ip_max_failures=6)
        db.init_db(data_dir / "l.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cls.cfg)
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        auth._failures.clear()
        auth._ip_failures.clear()

    def tearDown(self):
        auth._failures.clear()
        auth._ip_failures.clear()

    def attempt(self, username, password="Printemps2026!"):
        try:
            Client(self.url).login(username, password)
            return 200
        except ApiFailure as err:
            return err.status

    def test_spraying_stops_at_the_ceiling(self):
        codes = [self.attempt("compte{}".format(i)) for i in range(10)]
        self.assertEqual(codes, [401] * 6 + [429] * 4)
        self.assertEqual(self.attempt("admin", "admin"), 429)  # even the right password, until the window passes

    def test_window_passes(self):
        for i in range(6):
            self.attempt("compte{}".format(i))
        with auth._fail_lock:  # 16 minutes later
            auth._ip_failures["127.0.0.1"] = [(t - 16 * 60, u) for t, u in auth._ip_failures["127.0.0.1"]]
        self.assertEqual(self.attempt("admin", "admin"), 200)

    def test_old_counters_forgotten(self):
        with auth._fail_lock:
            for i in range(1500):
                auth._failures["vieux{}|10.0.0.1".format(i)] = (1, 0, 0.0)
                auth._ip_failures["10.0.{}.{}".format(i // 250, i % 250)] = [(0.0, "vieux")]
        self.attempt("compte-x")
        self.assertLess(len(auth._failures), 10)
        self.assertLess(len(auth._ip_failures), 10)


if __name__ == "__main__":
    unittest.main()
