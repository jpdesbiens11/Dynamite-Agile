"""0.47.0: tour of the site in Help (D-B-092) and development sharing on the local network (D-B-091).

    python -m unittest tests.test_lot_v037 -v
"""
import http.client
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, devshare, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.help import headlamp, tour  # noqa: E402

OLD_ORDER = ["bienvenue", "projets", "dynamite", "goldmine", "exploration", "agile", "changements", "generator", "timesheet",
             "recherche-audit", "administration"]  # the 0.14 → 0.46 path


class DevShareTest(unittest.TestCase):
    def test_01_allow_rules(self):
        off = {"lan_share": False}
        self.assertTrue(devshare.client_allowed(off, "8.8.8.8"))  # not sharing: the router lets everything through
        on = {"lan_share": True, "lan_local_nets": ["192.0.2.0/24"]}
        for ip in ("127.0.0.1", "::1", "192.168.1.40", "10.2.3.4", "172.20.0.9", "100.80.1.1", "192.0.2.77", "::ffff:192.168.1.5"):
            self.assertTrue(devshare.client_allowed(on, ip), ip)
        for ip in ("8.8.8.8", "203.0.113.5", "2001:db8::1", "pas-une-ip"):
            self.assertFalse(devshare.client_allowed(on, ip), ip)
        only = dict(on, lan_allow=["192.168.1.40"])
        self.assertTrue(devshare.client_allowed(only, "192.168.1.40"))
        self.assertTrue(devshare.client_allowed(only, "127.0.0.1"))
        self.assertFalse(devshare.client_allowed(only, "192.168.1.41"))
        with self.assertRaises(ValueError):
            devshare.parse_allow(["192.168.1.400"])
        self.assertEqual(devshare.local_nets(["192.168.1.23", "fe80::1"]), ["192.168.1.0/24"])

    def test_02_prefill_only_here(self):
        self.assertTrue(devshare.prefill({"dev_mode": True}, "192.168.1.40"))  # local mode: unchanged
        self.assertTrue(devshare.prefill({"dev_mode": True, "lan_share": True}, "127.0.0.1"))
        self.assertFalse(devshare.prefill({"dev_mode": True, "lan_share": True}, "192.168.1.40"))
        self.assertFalse(devshare.prefill({"dev_mode": False}, "127.0.0.1"))
        text = devshare.banner({"lan_local_nets": ["192.168.1.0/24"]}, "https", 8443, ["192.168.1.23"])
        self.assertIn("https://192.168.1.23:8443", text)
        self.assertIn("pas un serveur de production", text)

    def test_03_lan_flag_refused_in_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = subprocess.run([sys.executable, str(BASE_DIR / "app_dynamite_agile.py"), "--data-dir", tmp, "--prod", "--lan"],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 1)
        self.assertIn("réservé au développement", run.stdout + run.stderr)

    def test_04_launchers(self):
        for mode in ("local", "reseau"):
            bat = (BASE_DIR / "Lancer_dev_{}.bat".format(mode)).read_bytes()
            self.assertIn(b"\r\n", bat)  # Windows line endings
            self.assertIn("lancer_dev.py {}".format(mode).encode(), bat)
        launcher = (BASE_DIR / "lancer_dev.py").read_text(encoding="utf-8")
        self.assertIn('MODE = "local"', launcher)
        self.assertNotIn("--dev-admin", launcher.split("def main")[1])  # never forces development mode


class LanServerTest(unittest.TestCase):
    """A real server shared on the LAN, reached through this computer's own network address (not the loopback)."""

    @classmethod
    def setUpClass(cls):
        addresses = [ip for ip in devshare.lan_addresses() if ":" not in ip]
        if not addresses:
            raise unittest.SkipTest("no network address on this computer")
        cls.ip = addresses[0]
        cls.tmp = tempfile.TemporaryDirectory()
        data = Path(cls.tmp.name)
        cfg = load_config(data)
        cfg.update(port=0, host="0.0.0.0", dev_mode=True, lan_share=True, lan_local_nets=devshare.local_nets(addresses),
                   require_initials=False)
        db.init_db(data / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data, dev_password="admin")
        cls.cfg = cfg
        cls.server = router.create_server(cfg, BASE_DIR / "static", data)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def call(self, host, method, path, body=None):
        conn = http.client.HTTPConnection(host, self.port, timeout=10)
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, {"Content-Type": "application/json"})
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read() or b"{}")
        finally:
            conn.close()

    def test_01_colleague_vs_this_computer(self):
        status, about = self.call(self.ip, "GET", "/api/about")
        self.assertEqual((status, about["prefill"], about["lan_share"]), (200, False, True))
        self.assertTrue(self.call("127.0.0.1", "GET", "/api/about")[1]["prefill"])
        status, refused = self.call(self.ip, "POST", "/api/login", {"username": "admin", "password": "admin"})
        self.assertEqual(status, 403)
        self.assertIn("ne s'ouvre que sur le poste", refused["error"])
        self.assertEqual(self.call("127.0.0.1", "POST", "/api/login", {"username": "admin", "password": "admin"})[0], 200)

    def test_02_allow_list(self):
        self.cfg["lan_allow"] = ["10.9.9.9"]
        try:
            self.assertEqual(self.call(self.ip, "GET", "/")[0], 403)  # pages too, not only the API
            self.assertEqual(self.call("127.0.0.1", "GET", "/api/about")[0], 200)
        finally:
            self.cfg["lan_allow"] = []


class TourTest(unittest.TestCase):
    def test_01_same_order_everywhere(self):
        ids = []
        for name in ("content_path.js", "content_path2.js"):
            ids += re.findall(r'\{ id: "([a-z-]+)"', (BASE_DIR / "static" / "js" / "help" / name).read_text(encoding="utf-8"))
        self.assertEqual(ids, [s[0] for s in tour.STEPS])
        self.assertEqual(set(tour.TOPIC_CODES), set(ids))
        self.assertEqual(len(set(tour.TOPIC_CODES.values())), len(ids))
        self.assertEqual(tour.TOPIC_CODES["timesheet"], "HL-09")  # training plans that hold HL-09 keep their meaning
        manifest = next(m for m in modules.MODULE_MANIFEST if m["key"] == "help")["scripts"]
        self.assertLess(manifest.index("/js/help/content_path2.js"), manifest.index("/js/help/help.js"))

    def test_02_existing_headlamp_follows_the_tour(self):
        new_steps = list(tour.STEPS)
        old_steps = [next(s for s in new_steps if s[0] == c) for c in OLD_ORDER]
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            cfg = load_config(data)
            db.init_db(data / "t.db", modules.registered_schema(), modules.registered_migrations())
            with db.connect() as conn:
                auth.ensure_initial_admin(conn, data, dev_password="admin")
            headlamp.STEPS[:] = old_steps  # same list object in tour and headlamp: a 0.46 HeadLamp
            try:
                startup.run(data, cfg)
            finally:
                headlamp.STEPS[:] = new_steps
            with db.connect() as conn:
                pid = headlamp.project_id(conn)
                before = tour.step_tickets(conn, pid)
            self.assertEqual(len(before), 11)
            self.assertTrue(before["timesheet"]["title"].startswith("Étape 9 —"))
            startup.run(data, cfg)  # 0.47.0 start-up
            with db.connect() as conn:
                after = tour.step_tickets(conn, pid)
                hub = conn.execute("SELECT v.body FROM dynamite_pages p JOIN dynamite_versions v ON v.page_id = p.id AND "
                                   "v.version = p.current_version WHERE p.project_id = ? AND p.parent_id IS NULL", (pid,)).fetchone()
                topics = {r["code"]: r["reference"] for r in conn.execute("SELECT code, reference FROM training_topics")}
            self.assertEqual(len(after), 14)
            self.assertEqual(after["timesheet"]["number"], before["timesheet"]["number"])  # same ticket, same key
            self.assertTrue(after["timesheet"]["title"].startswith("Étape 12 —"))
            self.assertTrue(after["dashboard"]["title"].startswith("Étape 2 —"))
            self.assertIn("Le parcours en 14 étapes", hub["body"])
            self.assertEqual(topics["HL-09"], "#/help/timesheet")
            self.assertEqual(topics["HL-12"], "#/help/dashboard")
            startup.run(data, cfg)  # third start: nothing left to change
            with db.connect() as conn:
                self.assertEqual(tour.step_tickets(conn, pid), after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
