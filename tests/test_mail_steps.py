"""0.60.80 (D-O-086): when the SMTP server refuses, the message names the step that broke (connexion, STARTTLS,
login, envoi), the settings really used (host:port, security) and the usual cause there.

    python -m unittest tests.test_mail_steps -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import mail  # noqa: E402
from core.errors import ApiError  # noqa: E402
from tests.test_password_reset import SmtpSink  # noqa: E402


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
