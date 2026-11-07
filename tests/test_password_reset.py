"""0.60.73 (D-O-079): « Mot de passe oublié ? » -- a single-use link by e-mail, through an SMTP server set in Admin.

A real server of the tool and a tiny local SMTP sink (plain text, no authentication) that keeps the messages."""
import email
import email.policy
import json
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, mail, modules, password_reset, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

STATIC = BASE_DIR / "static"


class SmtpSink:
    """Enough of RFC 5321 for smtplib: EHLO, MAIL, RCPT, DATA, QUIT."""

    def __init__(self):
        self.messages = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self.talk, args=(conn,), daemon=True).start()

    def talk(self, conn):
        f = conn.makefile("rb")
        send = lambda line: conn.sendall((line + "\r\n").encode())  # noqa: E731
        send("220 sink")
        rcpt, data = [], None
        while True:
            line = f.readline()
            if not line:
                break
            cmd = line.decode(errors="replace").strip()
            up = cmd.upper()
            if data is not None:
                if cmd == ".":
                    self.messages.append({"to": rcpt, "data": b"".join(data).decode("utf-8", "replace")})
                    data, rcpt = None, []
                    send("250 queued")
                else:
                    data.append(line)
            elif up.startswith("EHLO") or up.startswith("HELO"):
                send("250 sink")
            elif up.startswith("MAIL"):
                send("250 ok")
            elif up.startswith("RCPT"):
                rcpt.append(cmd.split(":", 1)[1].strip(" <>"))
                send("250 ok")
            elif up == "DATA":
                data = []
                send("354 go")
            elif up == "QUIT":
                send("221 bye")
                break
            else:
                send("250 ok")
        conn.close()

    def wait(self, count, seconds=5):
        end = time.time() + seconds
        while len(self.messages) < count and time.time() < end:
            time.sleep(0.05)
        return self.messages


class PasswordResetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = load_config(cls.data_dir)
        cfg["port"] = 0
        db.init_db(cls.data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, STATIC, cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.sink = SmtpSink()
        created = cls.admin.post("/api/admin/users", {"username": "jp", "display_name": "Jean-Philippe",
                                                      "email": "JP@Exemple.ca"})
        cls.jp_temp = created["temp_password"]
        cls.jp_id = created["user"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.sink.sock.close()
        cls.tmp.cleanup()

    def setUp(self):
        password_reset._hits.clear()

    def fails(self, call):
        with self.assertRaises(ApiFailure) as caught:
            call()
        return caught.exception.status

    def enable(self):
        self.admin.put("/api/admin/mail", {"enabled": True, "host": "127.0.0.1", "port": self.sink.port, "security": "none",
                                           "sender": "noreply@exemple.ca", "public_url": "https://demo.exemple.ca"})

    def test_01_email_stored_lowercase_and_unique(self):
        users = {u["username"]: u for u in self.admin.get("/api/admin/users")["users"]}
        self.assertEqual(users["jp"]["email"], "jp@exemple.ca")
        self.assertEqual(self.fails(lambda: self.admin.post("/api/admin/users", {"username": "jp2", "display_name": "x",
                                                                                 "email": "jp@exemple.ca"})), 409)
        self.assertEqual(self.fails(lambda: self.admin.patch("/api/admin/users/{}".format(self.jp_id), {"email": "pas-un-courriel"})), 400)

    def test_02_off_by_default_and_settings_never_return_the_password(self):
        self.assertFalse(Client(self.url).get("/api/about")["mail_reset"])
        self.assertEqual(self.fails(lambda: Client(self.url).post("/api/password/forgot", {"login": "jp"})), 503)
        self.assertEqual(self.fails(lambda: self.admin.put("/api/admin/mail", {"enabled": True})), 400)  # host, sender, url
        self.assertEqual(self.fails(lambda: self.admin.put("/api/admin/mail", {"security": "none", "username": "u"})), 400)
        self.admin.put("/api/admin/mail", {"host": "smtp.exemple.ca", "password": "secret-smtp", "security": "starttls"})
        got = self.admin.get("/api/admin/mail")
        self.assertTrue(got["has_password"])
        self.assertNotIn("secret-smtp", json.dumps(got))
        self.assertEqual(oct((self.data_dir / "mail.json").stat().st_mode & 0o777), "0o600")
        self.admin.put("/api/admin/mail", {"clear_password": True, "username": ""})

    def test_03_forgot_then_reset(self):
        self.enable()
        self.assertTrue(Client(self.url).get("/api/about")["mail_reset"])
        before = len(self.sink.messages)
        visitor = Client(self.url)
        same = visitor.post("/api/password/forgot", {"login": "personne"})["message"]
        self.assertEqual(visitor.post("/api/password/forgot", {"login": "JP@exemple.ca"})["message"], same)  # never says
        msgs = self.sink.wait(before + 1)
        self.assertEqual(len(msgs), before + 1)
        self.assertEqual(msgs[-1]["to"], ["jp@exemple.ca"])
        body = email.message_from_string(msgs[-1]["data"], policy=email.policy.default).get_content()  # quoted-printable
        token = re.search(r"https://demo\.exemple\.ca/#reset=([A-Za-z0-9_-]+)", body).group(1)
        self.assertEqual(visitor.post("/api/password/reset/check", {"token": token})["username"], "jp")
        self.assertEqual(self.fails(lambda: visitor.post("/api/password/reset", {"token": token, "new_password": "court"})), 400)
        session = Client(self.url)
        session.login("jp", self.jp_temp, new_password="Ancien-mot-de-passe-1")
        visitor.post("/api/password/reset", {"token": token, "new_password": "Nouveau-mot-de-passe-2"})
        self.assertEqual(self.fails(lambda: session.get("/api/projects")), 401)  # sessions closed
        self.assertEqual(self.fails(lambda: visitor.post("/api/password/reset", {"token": token,
                                                                                  "new_password": "Encore-un-autre-3"})), 410)
        Client(self.url).login("jp", "Nouveau-mot-de-passe-2")
        with db.connect() as conn:
            actions = [r["action"] for r in conn.execute("SELECT action FROM audit_log WHERE object_id = ? AND object_type = 'user'",
                                                         (self.jp_id,))]
        self.assertIn("password_reset_requested", actions)
        self.assertIn("password_reset_by_email", actions)

    def test_04_expired_link_and_limits(self):
        self.enable()
        visitor = Client(self.url)
        with db.connect() as conn:
            conn.execute("INSERT INTO password_resets (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                         (password_reset._hash("x" * 43), self.jp_id, "2020-01-01T00:00:00+00:00", "2020-01-01T00:30:00+00:00"))
        self.assertEqual(self.fails(lambda: visitor.post("/api/password/reset/check", {"token": "x" * 43})), 410)
        for _ in range(password_reset.PER_IP_HOUR):
            visitor.post("/api/password/forgot", {"login": "personne"})
        self.assertEqual(self.fails(lambda: visitor.post("/api/password/forgot", {"login": "personne"})), 429)

    def test_05_own_email_and_guest_never_reset(self):
        self.enable()
        me = self.admin.put("/api/me/email", {"email": "admin@exemple.ca"})
        self.assertEqual(me["email"], "admin@exemple.ca")
        self.assertEqual(self.admin.get("/api/me/email")["email"], "admin@exemple.ca")
        with db.connect() as conn:
            self.assertIsNone(password_reset._account(conn, "invite"))
        self.assertIsNone(mail.clean_email("") or None)

    def test_06_test_message_from_admin(self):
        self.enable()
        before = len(self.sink.messages)
        self.assertTrue(self.admin.post("/api/admin/mail/test", {"to": "admin@exemple.ca"})["ok"])
        self.assertEqual(len(self.sink.wait(before + 1)), before + 1)

    # 0.60.76 (D-O-082) -------------------------------------------------------------------------------------------
    def test_07_token_never_in_an_address_nor_in_the_log(self):
        self.assertIn(self.fails(lambda: Client(self.url).get("/api/password/reset?token=" + "y" * 43)), (404, 405))
        with self.assertLogs("dynamite_agile.http", "INFO") as logs:
            try:
                urllib.request.urlopen(self.url + "/api/about?token=SECRET-in-the-address&x=1", timeout=10).read()
            except urllib.error.HTTPError:
                pass
        text = "\n".join(logs.output)
        self.assertNotIn("SECRET-in-the-address", text)
        self.assertIn("token=…&x=1", text)

    def test_08_new_smtp_host_forgets_the_saved_password(self):
        self.admin.put("/api/admin/mail", {"host": "smtp.exemple.ca", "username": "u@exemple.ca", "password": "secret-smtp",
                                           "security": "starttls"})
        self.admin.put("/api/admin/mail", {"host": "smtp.exemple.ca", "username": "u@exemple.ca"})  # same server: kept
        self.assertTrue(self.admin.get("/api/admin/mail")["has_password"])
        self.admin.put("/api/admin/mail", {"host": "smtp.ailleurs.example", "username": "u@exemple.ca"})
        self.assertFalse(self.admin.get("/api/admin/mail")["has_password"])
        self.admin.put("/api/admin/mail", {"host": "smtp.exemple.ca", "password": "secret-smtp"})
        self.admin.put("/api/admin/mail", {"username": "autre@exemple.ca"})  # another account: forgotten too
        self.assertFalse(self.admin.get("/api/admin/mail")["has_password"])
        self.admin.put("/api/admin/mail", {"host": "smtp.ailleurs.example", "password": "nouveau"})  # typed again: kept
        self.assertTrue(self.admin.get("/api/admin/mail")["has_password"])
        self.admin.put("/api/admin/mail", {"clear_password": True, "username": "", "host": "127.0.0.1", "security": "none"})

    def test_09_old_addresses_are_forgotten(self):
        hits = {"10.0.0.{}".format(i): [0.0] for i in range(300)}  # all older than an hour at 5000
        hits["10.0.1.1"] = [4000.0]
        password_reset.prune(hits, 5000.0, 3600)
        self.assertEqual(list(hits), ["10.0.1.1"])
        small = {"a": [0.0]}
        password_reset.prune(small, 99999.0, 3600)  # under the threshold: nothing to do
        self.assertEqual(list(small), ["a"])


if __name__ == "__main__":
    unittest.main()
