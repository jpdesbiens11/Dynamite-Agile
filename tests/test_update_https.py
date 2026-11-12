"""0.60.97 (D-O-103): the online update downloads code over HTTPS only -- an http:// « release_site » or a redirect to
http:// is refused before any byte is read (plain HTTP only on the loopback, for the tests).

    python -m unittest tests.test_update_https -v
"""
import http.server
import sys
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import update_online  # noqa: E402


class Redirect(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(302)
        self.send_header("Location", "http://198.51.100.7/updates/versions.json")  # TEST-NET-2: never reached
        self.end_headers()

    def log_message(self, *args):
        pass


class HttpsOnlyTest(unittest.TestCase):
    def test_addresses(self):
        for url in ("https://dynamiteagile.ca/updates/versions.json", "http://127.0.0.1:8123/updates/x",
                    "http://localhost/updates/x", "http://[::1]:9/updates/x"):
            self.assertEqual(update_online._https_only(url), url)
        for url in ("http://dynamiteagile.ca/updates/versions.json", "http://127.0.0.1.example.com/x",
                    "http://127.0.0.1@example.com/x", "http://localhost.example.com/x",
                    "ftp://dynamiteagile.ca/x", "file:///etc/passwd"):
            with self.assertRaises(ValueError):
                update_online._https_only(url)

    def test_redirect_to_http_refused(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), Redirect)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with self.assertRaises(ValueError) as caught:
            update_online._open("http://127.0.0.1:{}/updates/versions.json".format(server.server_address[1]))
        self.assertIn("HTTPS seulement", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
