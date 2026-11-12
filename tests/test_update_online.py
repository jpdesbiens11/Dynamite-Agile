"""0.60.36 (D-O-045): online update -- off by default; on, the portal reads the website's listing, shows the newer
versions, refuses to start until each one is ticked « Lu », then downloads, checks the SHA-256 and the package, saves
and installs, with a live progress (percent, step, lines). The website here is a local test server."""
import functools
import http.server
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tests.test_release import LATEST, NEXT, copy_code, future_package  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class UpdateOnlineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        cls.code = tmp / "installed"
        copy_code(cls.code)
        data, listing = future_package(tmp)
        site = tmp / "site" / "updates"
        site.mkdir(parents=True)
        (site / listing["package"]).write_bytes(data)
        (site / "versions.json").write_text(json.dumps(listing), "utf-8")
        cls.site, cls.listing = site, listing
        cls.web = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(tmp / "site")))
        threading.Thread(target=cls.web.serve_forever, daemon=True).start()
        data_dir = tmp / "data"
        data_dir.mkdir()
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False, code_root=str(cls.code), update_restart=False,
                   release_site="http://127.0.0.1:{}/".format(cls.web.server_address[1]))
        db.init_db(data_dir / "u.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.web.shutdown()
        cls.web.server_close()
        cls.tmp.cleanup()

    def test_01_flow(self):
        state = self.admin.get("/api/admin/update/online")
        self.assertFalse(state["enabled"])  # off by default: no outbound call
        with self.assertRaises(Exception):
            self.admin.post("/api/admin/update/online/check", {})
        self.admin.put("/api/admin/update/online", {"enabled": True})
        state = self.admin.post("/api/admin/update/online/check", {})
        self.assertEqual(state["latest"], LATEST)
        newer = [v["version"] for v in state["newer"]]
        self.assertIn(NEXT[0], newer)
        self.assertIn(LATEST, newer)
        self.assertTrue(all(v["summary"] for v in state["newer"]))
        with self.assertRaises(Exception):  # every version must be read first
            self.admin.post("/api/admin/update/online/start", {"read": [LATEST]})
        self.admin.post("/api/admin/update/online/start", {"read": newer})
        seen, job = [], {}
        for _ in range(200):
            job = self.admin.get("/api/admin/update/online/progress")
            seen.append(job["percent"])
            if job["state"] in ("done", "error"):
                break
            time.sleep(0.1)
        self.assertEqual(job["state"], "done", job.get("error"))
        self.assertEqual(job["percent"], 100)
        self.assertTrue(any("SHA-256 conforme" in line for line in job["lines"]))
        self.assertEqual(seen, sorted(seen))  # the bar only moves forward
        self.assertIn('APP_VERSION = "{}"'.format(LATEST), (self.code / "core" / "__init__.py").read_text("utf-8"))
        self.assertTrue((self.code / "docs" / "NOUVEAU.md").exists())
        with db.connect() as conn:
            actions = {r["action"] for r in conn.execute("SELECT action FROM audit_log")}
        for a in ("update_online_enabled", "update_online_checked", "update_online_started", "update_applied", "restore_point_created"):
            self.assertIn(a, actions)


    def test_02_listing_without_fingerprint_or_size_refused(self):  # 0.60.83 (D-O-089)
        self.admin.put("/api/admin/update/online", {"enabled": True})
        broken = [dict(self.listing, sha256=""), dict(self.listing, bytes=0), dict(self.listing, package="../../x.zip")]
        broken.append({k: v for k, v in self.listing.items() if k != "sha256"})
        try:
            for listing in broken:
                (self.site / "versions.json").write_text(json.dumps(listing), "utf-8")
                with self.subTest(listing={k: listing.get(k) for k in ("package", "bytes", "sha256")}):
                    with self.assertRaises(ApiFailure) as caught:
                        self.admin.post("/api/admin/update/online/check", {})
                    self.assertEqual(caught.exception.status, 502)
                    self.assertIn("SHA-256", caught.exception.message)
        finally:
            (self.site / "versions.json").write_text(json.dumps(self.listing), "utf-8")


if __name__ == "__main__":
    unittest.main()
