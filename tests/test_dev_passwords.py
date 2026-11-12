"""0.60.97 (D-O-104): a trial (install.sh --essai, development mode: admin / admin) that later goes online never keeps a
known password. At the first start outside development mode, admin and the accounts not yet activated that still have
the development password get a random temporary password; admin's is written to INITIAL_ADMIN_PASSWORD.txt (0600).

    python -m unittest tests.test_dev_passwords -v
"""
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules  # noqa: E402


class DevPasswordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        db.init_db(self.data / "t.db", modules.registered_schema(), modules.registered_migrations())

    def add_pending(self, conn, username, password):
        conn.execute("INSERT INTO users (username, display_name, password_hash, is_admin, is_active, must_change_password, "
                     "created_at) VALUES (?, ?, ?, 0, 1, 1, ?)", (username, username, auth.hash_password(password), db.utc_now()))

    def user(self, conn, username):
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def test_trial_gone_online_retires_admin_admin(self):
        with db.connect() as conn:  # the trial: development mode
            auth.ensure_initial_admin(conn, self.data, dev_password="admin")
            auth.mark_dev_passwords(conn)
            self.add_pending(conn, "nina", "admin")       # the shared development temporary password
            self.add_pending(conn, "lea", "Xk3-random-temp")  # a real temporary password: kept
        with db.connect() as conn:  # the same data, started online
            retired, temp = auth.retire_dev_passwords(conn, self.data)
        self.assertEqual(sorted(retired), ["admin", "nina"])
        self.assertTrue(temp)
        with db.connect() as conn:
            admin = self.user(conn, "admin")
            self.assertFalse(auth.verify_password("admin", admin["password_hash"]))
            self.assertTrue(auth.verify_password(temp, admin["password_hash"]))
            self.assertEqual(admin["must_change_password"], 1)
            self.assertFalse(auth.verify_password("admin", self.user(conn, "nina")["password_hash"]))
            self.assertTrue(auth.verify_password("Xk3-random-temp", self.user(conn, "lea")["password_hash"]))
            self.assertIsNone(conn.execute("SELECT 1 FROM app_settings WHERE key = ?", (auth.DEV_PASSWORDS_FLAG,)).fetchone())
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'dev_password_retired'").fetchone()[0], 2)
        path = self.data / auth.INITIAL_PASSWORD_FILE
        self.assertIn(temp, path.read_text(encoding="utf-8"))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with db.connect() as conn:  # next start: nothing left to retire
            self.assertEqual(auth.retire_dev_passwords(conn, self.data), ([], None))

    def test_installation_made_before_the_flag(self):
        """An older trial gone online (no flag): admin still on admin / admin is enough to look at the others."""
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, self.data, dev_password="admin")
            self.add_pending(conn, "nina", "admin")
            retired, temp = auth.retire_dev_passwords(conn, self.data)
        self.assertEqual(sorted(retired), ["admin", "nina"])
        self.assertTrue(temp)

    def test_production_admin_untouched(self):
        with db.connect() as conn:
            temp = auth.ensure_initial_admin(conn, self.data)
            auth.change_password(conn, self.user(conn, "admin")["id"], temp, "a-strong-password-of-mine")
            self.add_pending(conn, "nina", "Xk3-random-temp")
            self.assertEqual(auth.retire_dev_passwords(conn, self.data), ([], None))
            self.assertTrue(auth.verify_password("a-strong-password-of-mine", self.user(conn, "admin")["password_hash"]))

    def test_custom_dev_temp_password(self):
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, self.data, dev_password="admin")
            auth.mark_dev_passwords(conn)
            self.add_pending(conn, "nina", "equipe-2026")
            retired, _ = auth.retire_dev_passwords(conn, self.data, ("admin", "equipe-2026"))
        self.assertEqual(sorted(retired), ["admin", "nina"])


class TrialGoneOnlineEndToEnd(unittest.TestCase):
    """The real server: a start in development mode, then --prod on the same data (what install.sh does)."""

    def start(self, data, *flags):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        proc = subprocess.Popen([sys.executable, str(BASE_DIR / "app_dynamite_agile.py"), "--data-dir", data,
                                 "--host", "127.0.0.1", "--port", str(port), *flags],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.terminate)
        url = "http://127.0.0.1:{}".format(port)
        for _ in range(120):
            try:
                urllib.request.urlopen(url + "/api/about", timeout=1).close()
                return proc, url
            except OSError:
                time.sleep(0.5)
        self.fail("the server did not start")

    def login(self, url, password):
        req = urllib.request.Request(url + "/api/login", data=json.dumps({"username": "admin", "password": password}).encode(),
                                     headers={"Content-Type": "application/json", "Origin": url})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as exc:
            return exc.code, {}

    def test_dev_then_prod(self):
        with tempfile.TemporaryDirectory() as data:
            proc, url = self.start(data, "--dev-admin")
            self.assertEqual(self.login(url, "admin")[0], 200)
            proc.terminate()
            proc.wait()
            proc, url = self.start(data, "--prod")
            self.assertEqual(self.login(url, "admin")[0], 401)
            text = (Path(data) / auth.INITIAL_PASSWORD_FILE).read_text(encoding="utf-8")
            status, body = self.login(url, text.split("Temporary password: ")[1].split()[0])
            self.assertEqual(status, 200)
            self.assertTrue(body["user"]["must_change_password"])
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(os.stat(data).st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((Path(data) / auth.INITIAL_PASSWORD_FILE).stat().st_mode), 0o600)
            proc.terminate()
            proc.wait()


if __name__ == "__main__":
    unittest.main()
