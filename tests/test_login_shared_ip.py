"""0.60.95 (D-O-101, R1 of D-O-095): behind a shared address (company VPN, NAT, school network), one person mistyping
their password must not lock everyone out. The address ceiling counts the different usernames that failed (spraying)
next to a much higher ceiling of raw failures; above it, a username that already signed in from that address may still
try (its own lock still applies); a successful login takes that person's typos out of the address count.

    python -m unittest tests.test_login_shared_ip -v
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

ADDRESS = "127.0.0.1"


class SharedAddressTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(self.tmp.name)
        self.cfg = load_config(data_dir)
        self.cfg.update(port=0, require_initials=False, login_ip_max_usernames=4, login_ip_max_failures=12)
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, self.cfg)
        self.server = router.create_server(self.cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:{}".format(self.server.server_address[1])
        auth._failures.clear()
        auth._ip_failures.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()
        auth._failures.clear()
        auth._ip_failures.clear()

    def attempt(self, username, password="Printemps2026!"):
        try:
            Client(self.url).login(username, password)
            return 200
        except ApiFailure as err:
            return err.status

    def test_one_person_mistyping_locks_only_their_username(self):
        codes = [self.attempt("lea") for _ in range(8)]
        self.assertEqual(codes, [401] * 5 + [429] * 3)  # their own lock (login_max_failures = 5)
        self.assertEqual(self.attempt("admin", "admin"), 200)  # a colleague behind the same address: not blocked

    def test_spraying_trips_the_ceiling_but_known_users_still_sign_in(self):
        self.assertEqual(self.attempt("admin", "admin"), 200)  # signed in from this address before
        codes = [self.attempt("compte{}".format(i)) for i in range(6)]
        self.assertEqual(codes, [401] * 4 + [429] * 2)  # 4 different usernames: the address is over its ceiling
        self.assertEqual(self.attempt("admin", "admin"), 200)  # known here: may still sign in
        self.assertEqual(self.attempt("admin", "faux-mot-de-passe"), 401)  # and its own lock still counts
        with db.connect() as conn:
            conn.execute("DELETE FROM audit_log WHERE action = 'login'")  # never signed in from here
            conn.commit()
        self.assertEqual(self.attempt("admin", "admin"), 429)

    def test_raw_failures_ceiling_still_holds(self):
        self.cfg["login_ip_max_usernames"] = 100
        for i in range(3):  # 3 usernames x 4 failures = 12 raw failures, none of them locked yet
            for _ in range(4):
                self.assertEqual(self.attempt("compte{}".format(i)), 401)
        self.assertEqual(self.attempt("compte9"), 429)

    def test_successful_login_clears_that_persons_typos(self):
        for _ in range(3):
            self.attempt("admin", "faux")
        self.assertEqual(self.attempt("admin", "admin"), 200)
        self.assertEqual([u for _t, u in auth._ip_failures.get(ADDRESS, [])], [])


if __name__ == "__main__":
    unittest.main()
