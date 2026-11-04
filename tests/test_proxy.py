"""0.60.17 (D-O-029): behind an HTTPS reverse proxy (Traefik) -- trusted_proxies, X-Forwarded-For / -Proto, Secure
cookie, direct access refused in production, start rule kept fail closed."""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, proxy, router, startup, tls  # noqa: E402
from core.config import load_config  # noqa: E402


class ProxyRulesTest(unittest.TestCase):
    def test_01_rules(self):
        cfg = {"trusted_proxies": ["172.16.0.0/12", "bad value"], "dev_mode": False}
        self.assertTrue(proxy.enabled(cfg))
        self.assertTrue(proxy.trusted(cfg, "172.18.0.1"))
        self.assertFalse(proxy.trusted(cfg, "8.8.8.8"))
        headers = {"X-Forwarded-For": "203.0.113.7, 198.51.100.2", "X-Forwarded-Proto": "https"}
        self.assertEqual(proxy.client(cfg, "172.18.0.1", headers, False), ("198.51.100.2", True))  # the entry the proxy added
        self.assertEqual(proxy.client(cfg, "8.8.8.8", headers, False), ("8.8.8.8", False))     # headers of a stranger: ignored
        self.assertEqual(proxy.client(cfg, "172.18.0.1", {"X-Forwarded-Proto": "http"}, False), ("172.18.0.1", False))
        self.assertTrue(proxy.refused(cfg, "8.8.8.8", False))
        self.assertFalse(proxy.refused(cfg, "172.18.0.1", False))
        self.assertFalse(proxy.refused(dict(cfg, dev_mode=True), "8.8.8.8", False))
        self.assertFalse(proxy.refused({"trusted_proxies": []}, "8.8.8.8", False))

    def test_02_start_rule(self):
        base = {"host": "0.0.0.0", "tls_cert": ""}
        self.assertIsNotNone(tls.check_start(base, dev=False))                       # network without HTTPS: refused
        self.assertIsNone(tls.check_start(dict(base, trusted_proxies=["172.16.0.0/12"]), dev=False))  # behind the proxy


class ProxyServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False, dev_mode=False, trusted_proxies=["127.0.0.1/32"])
        db.init_db(data_dir / "p.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.cfg = cfg
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def call(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Content-Type": "application/json", "X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.9"}
        h.update(headers or {})
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, res.headers, json.loads(data or b"{}") if data[:1] in (b"{", b"[") else data

    def test_03_secure_cookie_and_visitor_ip(self):
        status, headers, body = self.call("POST", "/api/login", {"username": "admin", "password": "admin"})
        self.assertEqual(status, 200, body)
        cookie = headers.get("Set-Cookie")
        self.assertTrue(cookie.startswith(tls.COOKIE_SECURE + "="), cookie)
        self.assertIn("Secure", cookie)
        token = cookie.split(";")[0]
        status, _h, me = self.call("GET", "/api/me", headers={"Cookie": token})
        self.assertEqual(status, 200, me)
        with db.connect() as conn:
            row = conn.execute("SELECT ip FROM audit_log WHERE ip IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row["ip"], "203.0.113.9")  # the visitor, not the proxy
        status, _h, _b = self.call("GET", "/api/me", headers={"Cookie": token, "X-Forwarded-Proto": "http"})
        self.assertEqual(status, 401)  # the secure cookie is not read on a request the proxy received in clear

    def test_04_direct_access_refused(self):
        self.server.app_config["trusted_proxies"] = ["10.9.9.9/32"]  # the test client is no longer the proxy
        try:
            status, _h, body = self.call("GET", "/api/me")
            self.assertEqual(status, 403)
            self.assertIn("proxy", body["error"])
        finally:
            self.server.app_config["trusted_proxies"] = ["127.0.0.1/32"]


if __name__ == "__main__":
    unittest.main()
