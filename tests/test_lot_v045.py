"""0.50.6 (D-B-112, core lot v0.31): « Mon équipe » for managers and review messages on each signature.

    python -m unittest tests.test_lot_v045 -v
"""
import datetime as dt
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur lea | Léa Systèmes | utilisateur | actif
utilisateur paul | Paul Stagiaire | utilisateur | actif
utilisateur marc | Marc Gestion | utilisateur | actif
utilisateur zoe | Zoé Autre | utilisateur | actif
"""
STATIC = BASE_DIR / "static"


class LotV045Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, STATIC, data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.c, cls.ids = {}, {}
        for item in done["created"]:
            client = Client(url)
            me = client.login(item["username"], item["temp_password"], "Essai-Lot-Trente-2026!")
            cls.c[item["username"]], cls.ids[item["username"]] = client, me["user"]["id"]
        for name in ("lea", "paul"):
            cls.c[name].put("/api/me/prefs", {"manager_id": cls.ids["marc"]})
        cls.year = dt.date.today().year

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def _inbox(self, who):
        return [m for m in self.c[who].get("/api/mentions")["messages"] if m["kind"] == "review"]

    def test_01_signature_messages_both_ways(self):
        lea, marc = self.c["lea"], self.c["marc"]
        uid, y = self.ids["lea"], self.year
        lea.post("/api/objectives/{}/{}".format(uid, y), {"kind": "annual", "title": "Plan de qualification"})
        team = marc.get("/api/team?year={}".format(y))
        row = next(p for p in team["people"] if p["id"] == uid)
        self.assertFalse(row["mine"])
        base = "/api/reviews/{}/{}".format(uid, y)
        lea.post(base + "/sign/start", {})
        msgs = self._inbox("marc")
        self.assertEqual(len(msgs), 1)
        self.assertIn("Début d'année", msgs[0]["title"])
        self.assertIn("approuver son plan annuel", msgs[0]["excerpt"])
        self.assertEqual(msgs[0]["href"], "#/objectives/{}/{}/start".format(uid, y))
        self.assertEqual(msgs[0]["kind_label"], "Évaluation annuelle")
        team = marc.get("/api/team?year={}".format(y))
        row = next(p for p in team["people"] if p["id"] == uid)
        self.assertTrue(row["mine"])
        self.assertIn("À vous", row["todo"])
        self.assertGreaterEqual(team["pending"], 1)
        self.assertGreaterEqual(marc.get("/api/me")["team"]["pending"], 1)
        marc.post(base + "/sign/start", {})
        msgs = self._inbox("lea")
        self.assertEqual(len(msgs), 1)
        self.assertIn("signée par les deux", msgs[0]["excerpt"])
        self.assertIn("Mi-année", msgs[0]["excerpt"])
        marc.post(base + "/reopen/start", {})
        msgs = self._inbox("lea")
        self.assertEqual(len(msgs), 2)
        self.assertIn("rouvert", msgs[0]["excerpt"])
        self.assertEqual(len(self._inbox("zoe")), 0)

    def test_02_team_is_private_to_the_manager(self):
        marc, zoe = self.c["marc"], self.c["zoe"]
        names = {p["profile"]["name"] for p in marc.get("/api/team")["people"]}
        self.assertEqual(names, {"Léa Systèmes", "Paul Stagiaire"})
        self.assertEqual(zoe.get("/api/team")["people"], [])
        self.assertEqual(zoe.get("/api/me")["team"], {"size": 0, "pending": 0})
        self.assertEqual(self.admin.get("/api/team")["people"], [])
        self.assertEqual(marc.get("/api/me")["team"]["size"], 2)

    def test_03_ui_is_wired(self):
        js = (STATIC / "js" / "tools" / "team.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertIn("DA.coreViews.team", js)
        self.assertIn('"0.50.6-team"', js)
        app = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("DA.teamLabel(session.team)", app)
        self.assertIn("session.team = me.team", app)
        self.assertIn('"team"', app)
        self.assertIn("/js/tools/team.js", (STATIC / "index.html").read_text(encoding="utf-8"))
        for path in ("js/tools/team.js", "js/app.js"):
            self.assertLess(len((STATIC / path).read_text(encoding="utf-8").splitlines()), 500)
        self.assertLess(len((BASE_DIR / "core" / "team.py").read_text(encoding="utf-8").splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
