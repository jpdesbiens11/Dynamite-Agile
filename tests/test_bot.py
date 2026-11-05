"""0.60.35 (D-O-043, D-O-044): the pointer (a link that opens a page and shows its point of interest) and Bob le
mineur's read-only door -- keys by Space, shown once, hashed, revocable, rate-limited, journalled; answers carry
pointer links; the platform never calls the agent."""
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

from core import auth, bot, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))


class PointerStaticTest(unittest.TestCase):
    def test_01_pointer(self):
        js = (BASE_DIR / "static" / "js" / "tools" / "pointer.js").read_text("utf-8")
        for needed in ("DA.pointTo", "DA.pointLink", "location.search", "history.replaceState", "da-point-box", "da-point-arrow",
                       "prefers-reduced-motion"):
            self.assertIn(needed, js)
        self.assertNotIn("innerHTML", js)
        self.assertIn('<script src="/js/tools/pointer.js" defer></script>', (BASE_DIR / "static" / "index.html").read_text("utf-8"))
        self.assertIn("DA.pointLink(picked", (BASE_DIR / "static" / "js" / "tools" / "share.js").read_text("utf-8"))


class BotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "b.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/starter/apply", {"file": LAMPE})
        cls.token = cls.admin.post("/api/admin/bot/tokens", {"name": "Bob le mineur — test", "spaces": ["LAMPE"]})["token"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def call(self, path, token=None, method="GET"):
        token = self.token if token is None else token
        req = urllib.request.Request(self.url + path, method=method, headers={"Authorization": "Bearer " + token} if token else {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_01_key_stored_hashed(self):
        self.assertTrue(self.token.startswith(bot.PREFIX))
        with db.connect() as conn:
            row = conn.execute("SELECT * FROM bot_tokens").fetchone()
        self.assertNotIn(self.token, json.dumps(dict(row)))
        self.assertEqual(row["spaces"], "LAMPE")
        listed = self.admin.get("/api/admin/bot/tokens")["tokens"][0]
        self.assertNotIn("token", listed)
        self.assertEqual(listed["prefix"], self.token[:12])

    def test_02_read_with_pointer_links(self):
        status, data = self.call("/api/bot/v1/spaces")
        self.assertEqual((status, [s["key"] for s in data["spaces"]]), (200, ["LAMPE"]))
        status, data = self.call("/api/bot/v1/search?q=chaleur&space=LAMPE")
        self.assertEqual(status, 200)
        f18 = next(r for r in data["results"] if r["title"].startswith("F18"))
        self.assertTrue(f18["url"].endswith("/?focus=F18#/diamond/LAMPE/ftree"))
        dfmea = next(r for r in data["results"] if r["title"].startswith("DFMEA"))
        self.assertIn("focus=Chaleur+mal+dissip", dfmea["url"])
        status, data = self.call("/api/bot/v1/summary?space=LAMPE")
        self.assertEqual(status, 200)
        self.assertEqual(data["diamond"]["figures"]["dfmea"], 22)
        self.assertIn("focus=R-1", data["diamond"]["risks_to_act_on"][0]["url"])
        status, data = self.call("/api/bot/v1/point?space=LAMPE&page=Diamond%20%C2%B7%20DFMEA&focus=Chaleur&note=Ici")
        self.assertEqual((status, data["url"].split("/", 3)[3]), (200, "?focus=Chaleur&note=Ici#/diamond/LAMPE/dfmea"))
        status, data = self.call("/api/bot/v1/pages?space=LAMPE")
        self.assertTrue(any(p["url"].endswith("/#/diamond/LAMPE/ftree") for p in data["pages"]))

    def test_03_refusals(self):
        self.assertEqual(self.call("/api/bot/v1/summary?space=EQP")[0], 403)     # a Space the key does not open
        self.assertEqual(self.call("/api/bot/v1/spaces", token="")[0], 401)      # no key
        self.assertEqual(self.call("/api/bot/v1/spaces", token="da_bot_nope")[0], 401)
        self.assertEqual(self.call("/api/bot/v1/spaces", method="POST")[0], 405)  # read-only
        self.assertEqual(self.call("/api/admin/bot/tokens")[0], 401)             # a key is not a session
        created = self.admin.post("/api/admin/users", {"username": "membre", "display_name": "Membre"})
        member = Client(self.url)
        member.login("membre", created["temp_password"], "Lampe-Bleue-2026!")
        with self.assertRaises(Exception):
            member.post("/api/admin/bot/tokens", {"name": "x", "spaces": ["LAMPE"]})  # administrators only

    def test_04_journal_and_search_type(self):
        self.call("/api/bot/v1/spaces")
        with db.connect() as conn:
            n = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'bot_read'").fetchone()[0]
        self.assertGreater(n, 0)
        hits = self.admin.get("/api/search?q=F18&types=function")["results"]
        self.assertTrue(any(h["title"].startswith("F18") for h in hits))  # Diamond in the top-bar search too

    def test_05_rate_and_revoke(self):
        token = self.admin.post("/api/admin/bot/tokens", {"name": "Bob — limite", "spaces": ["LAMPE"]})["token"]
        codes = [self.call("/api/bot/v1/spaces", token=token)[0] for _ in range(bot.RATE + 1)]
        self.assertEqual(codes[-1], 429)
        tid = next(t["id"] for t in self.admin.get("/api/admin/bot/tokens")["tokens"] if t["name"] == "Bob — limite")
        self.admin.post("/api/admin/bot/tokens/{}/revoke".format(tid), {})
        self.assertEqual(self.call("/api/bot/v1/spaces", token=token)[0], 401)

    def test_06_guide_for_the_agent(self):
        text = self.admin.get("/api/admin/bot/guide")["text"]
        for needed in ("Bob le mineur", "DynamiteAgile", "/api/bot/v1/search", "DA_BOT_TOKEN", "Ne demande jamais un mot de passe"):
            self.assertIn(needed, text)
        self.assertNotIn("{{URL}}", text)
        self.assertIn("sh /opt/data/da.sh search", text)

    def test_07_da_sh_the_one_command_of_the_agent(self):
        """0.60.37: deploy/bob/da.sh -- the key from the environment or from the agent's .env file, the words encoded."""
        import os
        import shutil
        import subprocess
        if not shutil.which("curl"):
            self.skipTest("curl absent")
        script = Path(self.tmp.name) / "da.sh"
        script.write_text((BASE_DIR / "deploy" / "bob" / "da.sh").read_text("utf-8").replace("{{URL}}", self.url), "utf-8")
        env_file = Path(self.tmp.name) / "agent.env"
        env_file.write_text("OTHER=1\nDA_BOT_TOKEN={}\n".format(self.token), "utf-8")
        env = {k: v for k, v in os.environ.items() if k != "DA_BOT_TOKEN"}

        def run(*args, **extra):
            out = subprocess.run(["sh", str(script)] + list(args), capture_output=True, text=True, timeout=30, env=dict(env, **extra))
            return out.returncode, out.stdout

        code, out = run("spaces", DA_BOT_TOKEN=self.token)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["spaces"][0]["key"], "LAMPE")
        code, out = run("search", "dissiper la chaleur", "LAMPE", DA_ENV_FILE=str(env_file))
        hits = json.loads(out)["results"]
        self.assertTrue(hits and all("focus=" in h["url"] for h in hits))
        code, out = run("summary", "LAMPE", DA_ENV_FILE=str(env_file))
        self.assertIn("url", out)
        code, out = run("spaces", DA_ENV_FILE=str(Path(self.tmp.name) / "none.env"), HOME=self.tmp.name)
        self.assertEqual(code, 2)
        self.assertIn("Correctif", out)


if __name__ == "__main__":
    unittest.main()
