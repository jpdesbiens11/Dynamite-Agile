"""0.60.74 (D-O-080): the contact form of the website posts to the demo, which forwards it by e-mail -- off by default,
CORS for the website's origin and this route only, Reply-To the person, robots and floods stopped."""
import email
import email.policy
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, contact, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tests.test_password_reset import SmtpSink  # noqa: E402
from tools.api_client import Client  # noqa: E402

SITE = "https://dynamiteagile.example"


class ContactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.sink = SmtpSink()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.sink.sock.close()
        cls.tmp.cleanup()

    def setUp(self):
        contact._hits.clear()
        contact._day.clear()

    def call(self, method, body=None, origin=SITE):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(self.url + "/api/contact", method=method, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, dict(res.headers), json.loads(res.read() or b"{}")
        except urllib.error.HTTPError as err:
            raw = err.read()
            return err.code, dict(err.headers), json.loads(raw) if raw else {}

    def open_form(self):
        self.admin.put("/api/admin/mail", {"host": "127.0.0.1", "port": self.sink.port, "security": "none",
                                           "sender": "noreply@exemple.ca", "contact_to": "auteur@exemple.ca",
                                           "contact_origin": SITE, "contact_enabled": True})

    def form(self, **extra):
        body = {"name": "Nina", "email": "nina@ecole.ca", "organization": "UdeS", "topic": "course",
                "message": "Peut-on l'utiliser dans un cours ?", "lang": "fr"}
        body.update(extra)
        return body

    def test_01_closed_by_default(self):
        status, headers, _ = self.call("POST", self.form())
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.call("OPTIONS")[0], 403)

    def test_02_cors_for_the_site_only(self):
        self.open_form()
        status, headers, _ = self.call("OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(headers["Access-Control-Allow-Origin"], SITE)
        self.assertEqual(self.call("OPTIONS", origin="https://evil.example")[0], 403)
        status, headers, _ = self.call("POST", self.form(), origin="https://evil.example")
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        with urllib.request.urlopen(self.url + "/api/about") as res:  # every other route stays without CORS
            self.assertIsNone(res.headers.get("Access-Control-Allow-Origin"))

    def test_03_forwarded_with_reply_to(self):
        self.open_form()
        before = len(self.sink.messages)
        status, headers, body = self.call("POST", self.form())
        self.assertEqual(status, 200, body)
        self.assertEqual(headers["Access-Control-Allow-Origin"], SITE)
        self.assertIn("7 jours", body["message"])
        msg = email.message_from_string(self.sink.wait(before + 1)[-1]["data"], policy=email.policy.default)
        self.assertEqual(msg["Reply-To"], "nina@ecole.ca")
        self.assertEqual(self.sink.messages[-1]["to"], ["auteur@exemple.ca"])
        self.assertIn("Cours ou formation", msg["Subject"])
        self.assertIn("Peut-on l'utiliser", msg.get_content())
        self.assertNotIn("auteur@exemple.ca", json.dumps(body))  # the recipient never reaches the page

    def test_04_robots_bad_fields_and_floods(self):
        self.open_form()
        before = len(self.sink.messages)
        self.assertEqual(self.call("POST", self.form(website="http://spam"))[0], 200)
        self.assertEqual(len(self.sink.wait(before + 1, seconds=1)), before)  # nothing left
        self.assertEqual(self.call("POST", self.form(email="pas-un-courriel"))[0], 400)
        self.assertEqual(self.call("POST", self.form(message=""))[0], 400)
        self.assertEqual(self.call("POST", self.form(lang="en", message="x" * 6000))[0], 400)
        # the three refused requests above count: the fourth of the hour is refused
        self.assertEqual(self.call("POST", self.form())[0], 429)

    # 0.60.75 (D-O-081) -------------------------------------------------------------------------------------------
    def test_05_line_break_in_a_one_line_field_is_a_400(self):
        self.open_form()
        for extra in ({"name": "Bob\r\nBcc: x@exemple.ca"}, {"organization": "UdeS\nX-Spam: 1"}):
            contact._hits.clear()
            status, headers, body = self.call("POST", self.form(**extra))
            self.assertEqual(status, 400, body)
            self.assertEqual(headers["Access-Control-Allow-Origin"], SITE)
        contact._hits.clear()
        self.assertEqual(self.call("POST", self.form(message="Ligne 1\nLigne 2"))[0], 200)  # the message may

    def test_06_smtp_refusal_stays_in_the_log(self):
        self.open_form()
        self.admin.put("/api/admin/mail", {"port": 1})  # nothing listens there
        try:
            with self.assertLogs("dynamite_agile.contact", "WARNING"):
                status, _, body = self.call("POST", self.form())
            self.assertEqual(status, 502)
            self.assertNotIn("Errno", body["error"])
            self.assertNotIn("Gmail", body["error"])
            self.assertEqual(contact._day, [])  # a request that did not leave takes no place of the day
        finally:
            self.open_form()

    def test_07_only_forwarded_requests_fill_the_day(self):
        self.open_form()
        for i in range(contact.PER_DAY + 5):  # refused requests from many addresses: the day stays open
            contact._hits.clear()
            self.assertEqual(self.call("POST", self.form(email="x"))[0], 400)
        self.assertEqual(contact._day, [])
        contact._day.extend([__import__("time").time()] * contact.PER_DAY)
        contact._hits.clear()
        with self.assertLogs("dynamite_agile.contact", "WARNING"):
            contact._warned[0] = 0.0
            self.assertEqual(self.call("POST", self.form())[0], 429)

    def test_08_options_behind_the_same_gates(self):
        self.open_form()
        cfg = self.server.app_config
        saved = {k: cfg.get(k) for k in ("trusted_proxies", "dev_mode")}
        cfg.update(trusted_proxies=["10.9.9.9/32"], dev_mode=False)  # only a proxy we are not may talk to the server
        try:
            self.assertEqual(self.call("POST", self.form())[0], 403)
            status, headers, _ = self.call("OPTIONS")
            self.assertEqual(status, 403)
            self.assertNotIn("Access-Control-Allow-Origin", headers)
        finally:
            cfg.update(saved)
        self.assertEqual(self.call("OPTIONS")[0], 204)


if __name__ == "__main__":
    unittest.main()
