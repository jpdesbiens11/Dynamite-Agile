"""0.60.80 (D-O-086): when the SMTP server refuses, the message names the step that broke (connexion, STARTTLS,
login, envoi), the settings really used (host:port, security) and the usual cause there.

    python -m unittest tests.test_mail_steps -v
"""
import base64
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import mail  # noqa: E402
from core.errors import ApiError  # noqa: E402
from tests.test_password_reset import SmtpSink  # noqa: E402


def fake_gmail(accept, refusal=("535-5.7.8 Username and Password not accepted. For more information, go to",
                                   "535 5.7.8  https://support.google.com/mail/?p=BadCredentials")):
    """A server announcing AUTH LOGIN PLAIN: 535 then hang-up (like Gmail), or 235 then a normal session. -> (port, seen)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    seen = []

    def serve():
        conn, _ = sock.accept()
        f = conn.makefile("rb")
        send = lambda line: conn.sendall((line + "\r\n").encode())  # noqa: E731
        send("220 fake ESMTP")
        for raw in f:
            cmd = raw.decode().strip()
            seen.append(cmd.split(" ")[0].upper() + (" " + cmd.split(" ")[1].upper() if cmd.upper().startswith("AUTH") else ""))
            up = cmd.upper()
            if up.startswith("EHLO"):
                send("250-fake")
                send("250 AUTH LOGIN PLAIN")
            elif up.startswith("AUTH"):
                if not accept:
                    for line in refusal:
                        send(line)
                    conn.close()
                    sock.close()
                    return
                seen.append(base64.b64decode(cmd.split(" ")[2]).split(b"\0")[1].decode())
                send("235 2.7.0 Accepted")
            elif up.startswith(("MAIL", "RCPT")):
                send("250 ok")
            elif up == "DATA":
                send("354 go")
            elif cmd == ".":
                send("250 queued")
            elif up == "QUIT":
                send("221 bye")
                conn.close()
                sock.close()
                return

    threading.Thread(target=serve, daemon=True).start()
    return sock.getsockname()[1], seen


class MailStepsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sink = SmtpSink()  # plain SMTP: no STARTTLS, no AUTH

    @classmethod
    def tearDownClass(cls):
        cls.sink.sock.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def error(self, **cfg):
        values = dict(mail.DEFAULTS, host="127.0.0.1", port=self.sink.port, security="none", sender="noreply@exemple.ca")
        values.update(cfg)
        mail._save(self.tmp.name, values)
        with self.assertRaises(ApiError) as caught:
            mail.send(self.tmp.name, "nina@exemple.ca", "Essai", "Bonjour")
        self.assertEqual(caught.exception.status, 502)
        return caught.exception.message

    def test_nothing_listens(self):
        text = self.error(port=1)
        self.assertIn("« connexion au serveur »", text)
        self.assertIn("127.0.0.1:1", text)

    def test_ssl_on_a_plain_port(self):  # what JP saw: SSL / TLS with the port left at 587
        text = self.error(security="ssl")
        self.assertIn("connexion au serveur", text)
        self.assertIn("SSL / TLS va avec le port 465, STARTTLS avec le port 587", text)

    def test_starttls_refused(self):
        text = self.error(security="starttls")
        self.assertIn("« passage en chiffré (STARTTLS) »", text)

    def test_login_step(self):
        text = self.error(security="none", username="jp@exemple.ca", password="x")
        self.assertIn("« connexion au compte »", text)
        self.assertIn("mot de passe d'application", text)

    def test_account_without_password_said_plainly(self):  # 0.60.81 (D-O-087): before Gmail cuts the connection
        values = dict(mail.DEFAULTS, host="127.0.0.1", port=1, security="starttls", sender="jp@exemple.ca",
                      username="jp@exemple.ca", password="")
        mail._save(self.tmp.name, values)
        with self.assertRaises(ApiError) as caught:
            mail.send(self.tmp.name, "nina@exemple.ca", "Essai", "Bonjour")
        self.assertEqual(caught.exception.status, 400)
        self.assertIn("Aucun mot de passe SMTP enregistré", caught.exception.message)

    def test_gmail_refusal_is_shown_not_the_hang_up(self):  # 0.60.85 (D-O-091): what JP saw on the demo
        port, seen = fake_gmail(accept=False)
        text = self.error(port=port, username="jp@gmail.com", password="mauvais")
        self.assertIn("535 5.7.8 Username and Password not accepted", text)
        self.assertNotIn("Connection unexpectedly closed", text)
        self.assertIn("NOUVEAU mot de passe d'application", text)
        self.assertEqual([c for c in seen if c.startswith("AUTH")], ["AUTH PLAIN"])  # one method only

    def test_account_password_instead_of_an_app_password(self):  # 0.60.87 (D-O-093): JP's 534 on the demo
        port, _seen = fake_gmail(accept=False, refusal=(
            "534-5.7.9 Application-specific password required. For more information, go to",
            "534 5.7.9  https://support.google.com/mail/?p=InvalidSecondFactor"))
        text = self.error(port=port, username="jp@gmail.com", password="mot-de-passe-du-compte")
        self.assertIn("534 5.7.9 Application-specific password required", text)
        self.assertIn("pas le mot de passe du compte Google", text)
        self.assertIn("https://myaccount.google.com/apppasswords", text)

    def test_login_accepted(self):
        port, seen = fake_gmail(accept=True)
        values = dict(mail.DEFAULTS, host="127.0.0.1", port=port, security="none", sender="jp@gmail.com",
                      username="jp@gmail.com", password="bon-mot-de-passe")
        mail._save(self.tmp.name, values)
        mail.send(self.tmp.name, "nina@exemple.ca", "Essai", "Bonjour")
        self.assertIn("jp@gmail.com", seen)
        self.assertIn("DATA", seen)

    def test_starttls_on_465_hint(self):
        hint = mail._hint("connexion", {"security": "starttls", "port": 465}, OSError("Connection unexpectedly closed"))
        self.assertIn("mettez le port 587", hint)

    def test_still_sends_when_all_is_right(self):
        before = len(self.sink.messages)
        values = dict(mail.DEFAULTS, host="127.0.0.1", port=self.sink.port, security="none", sender="noreply@exemple.ca")
        mail._save(self.tmp.name, values)
        mail.send(self.tmp.name, "nina@exemple.ca", "Essai", "Bonjour")
        self.assertEqual(len(self.sink.wait(before + 1)), before + 1)


if __name__ == "__main__":
    unittest.main()
