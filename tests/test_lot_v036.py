"""0.46.0: secure transport (core lot v0.24, D-B-090) -- real HTTPS on a real socket: TLS 1.3 only, HSTS, __Host-
cookie, optional then required mTLS, session bound to the client certificate, fail-closed start, HTTP redirect.

    python -m unittest tests.test_lot_v036 -v
"""
import contextlib
import http.client
import io
import json
import shutil
import ssl
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup, tls  # noqa: E402
from core.config import load_config  # noqa: E402
from tools import make_dev_ca  # noqa: E402


def client_context(ca, cert=None, tls12=False):
    ctx = ssl.create_default_context(cafile=str(ca))
    if tls12:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    if cert:
        ctx.load_cert_chain(str(cert.with_suffix(".crt")), str(cert.with_suffix(".key")))
    return ctx


@unittest.skipUnless(shutil.which("openssl"), "openssl command line needed to create the test certificates")
class LotV036Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            make_dev_ca.main(["--data-dir", str(cls.data), "--client", "alice", "--client", "bob"])
        cls.ca = cls.data / "tls" / "ca.crt"
        cls.alice, cls.bob = cls.data / "tls" / "client-alice", cls.data / "tls" / "client-bob"
        db.init_db(cls.data / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data, dev_password="admin")
        cls.servers = []

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        cls.tmp.cleanup()

    def start(self, **extra):
        cfg = load_config(self.data)
        cfg.update(port=0, require_initials=False, dev_mode=False, tls_cert="tls/server.crt", tls_key="tls/server.key")
        cfg.update(extra)
        startup.run(self.data, cfg)
        server = router.create_server(cfg, BASE_DIR / "static", self.data)
        tls.enable(server, cfg, self.data)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return server.server_address[1]

    def call(self, port, method, path, body=None, cookie=None, cert=None, csrf=None, tls12=False):
        conn = http.client.HTTPSConnection("localhost", port, timeout=10, context=client_context(self.ca, cert, tls12))
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["X-CSRF-Token"] = csrf
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, headers)
            resp = conn.getresponse()
            data = resp.read()
        finally:
            conn.close()
        json_body = (resp.getheader("Content-Type") or "").startswith("application/json")
        return resp, (json.loads(data) if data and json_body else {})

    def login(self, port, cert=None):
        resp, data = self.call(port, "POST", "/api/login", {"username": "admin", "password": "admin"}, cert=cert)
        self.assertEqual(resp.status, 200, data)
        set_cookie = resp.getheader("Set-Cookie")
        return set_cookie, set_cookie.split(";")[0], data

    def test_01_fail_closed_start(self):
        self.assertIn("Production refusée", tls.check_start({"host": "0.0.0.0", "tls_cert": ""}, dev=False))
        self.assertIsNone(tls.check_start({"host": "127.0.0.1", "tls_cert": ""}, dev=False))  # loopback only
        self.assertIsNone(tls.check_start({"host": "0.0.0.0", "tls_cert": "tls/server.crt"}, dev=False))
        self.assertIsNone(tls.check_start({"host": "0.0.0.0", "tls_cert": ""}, dev=True))
        self.assertIn("tls_client_ca", tls.check_start({"host": "127.0.0.1", "tls_client_required": True}, dev=True))
        with db.connect() as conn:
            self.assertIn("client_cert", [r["name"] for r in conn.execute("PRAGMA table_info(sessions)")])

    def test_02_tls13_headers_cookie_and_binding(self):
        port = self.start(tls_client_ca="tls/ca.crt")  # mTLS optional
        with self.assertRaises(ssl.SSLError):
            self.call(port, "GET", "/api/about", tls12=True)  # TLS 1.2 refused
        resp, _ = self.call(port, "GET", "/")
        self.assertEqual(resp.getheader("Strict-Transport-Security"), "max-age=31536000; includeSubDomains")
        self.assertEqual(resp.getheader("Referrer-Policy"), "no-referrer")
        raw, cookie, _ = self.login(port)  # no client certificate: allowed in optional mode, session not bound
        self.assertTrue(cookie.startswith("__Host-da_session="))
        self.assertIn("Secure", raw)
        self.assertIn("HttpOnly", raw)
        resp, me = self.call(port, "GET", "/api/me", cookie=cookie, cert=self.bob)
        self.assertEqual(resp.status, 200)
        resp, _ = self.call(port, "GET", "/api/me", cookie=cookie.replace("__Host-", ""))
        self.assertEqual(resp.status, 401)  # the plain-HTTP cookie name means nothing over HTTPS
        _, bound, data = self.login(port, cert=self.alice)
        self.assertEqual(self.call(port, "GET", "/api/me", cookie=bound, cert=self.alice)[0].status, 200)
        self.assertEqual(self.call(port, "GET", "/api/me", cookie=bound)[0].status, 401)  # stolen cookie, no cert
        self.assertEqual(self.call(port, "GET", "/api/me", cookie=bound, cert=self.bob)[0].status, 401)  # other cert
        resp, status = self.call(port, "GET", "/api/admin/transport", cookie=bound, cert=self.alice)
        self.assertEqual(resp.status, 200, status)
        self.assertEqual((status["https"], status["mtls"], status["min_version"]), (True, "optional", "TLS 1.3"))
        self.assertEqual(status["connection"]["version"], "TLSv1.3")
        self.assertEqual(status["connection"]["client_subject"], "alice")
        self.assertEqual(status["server_cert"]["issuer"], "Dynamite Dev Root CA (development only)")
        self.assertGreater(status["server_cert"]["days_left"], 300)

    def test_03_mtls_required(self):
        port = self.start(tls_client_ca="tls/ca.crt", tls_client_required=True)
        with self.assertRaises((ssl.SSLError, ConnectionResetError, BrokenPipeError, http.client.RemoteDisconnected)):  # 0.50.12: the refusal may also arrive as a broken pipe
            self.call(port, "GET", "/api/about")  # no certificate: not even the public « about »
        resp, about = self.call(port, "GET", "/api/about", cert=self.bob)
        self.assertEqual(resp.status, 200)
        self.assertIn("version", about)

    def test_04_dev_mode_no_hsts(self):
        port = self.start(dev_mode=True)
        resp, _ = self.call(port, "GET", "/")
        self.assertIsNone(resp.getheader("Strict-Transport-Security"))  # would stick to localhost for a year

    def test_05_http_redirect(self):
        redirect = tls.start_redirect({"host": "127.0.0.1", "port": 8443, "http_redirect_port": 0})
        self.assertIsNone(redirect)  # « http_redirect_port »: 0 = no plain-HTTP listener at all
        server = tls.ThreadingHTTPServer(("127.0.0.1", 0), tls._RedirectHandler)  # same handler, free port
        server.https_port, server.public_name = 8443, "dynamite-dev.local"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("GET", "/#/dashboard?x=1")
        resp = conn.getresponse()
        self.assertEqual((resp.status, resp.getheader("Location")), (301, "https://dynamite-dev.local:8443/#/dashboard?x=1"))
        conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("POST", "/api/login", "{}")
        self.assertEqual(conn.getresponse().status, 403)  # never replay a write sent in clear
        conn.close()

    def test_06_admin_screen(self):
        admin = (BASE_DIR / "static" / "js" / "admin.js").read_text(encoding="utf-8")
        self.assertIn('["transport", "Sécurité réseau"]', admin)
        self.assertIn('"0.46.0-admin-transport"', admin)
        self.assertIn("/js/admin_transport.js", (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))
        screen = (BASE_DIR / "static" / "js" / "admin_transport.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", screen)


if __name__ == "__main__":
    unittest.main(verbosity=2)
