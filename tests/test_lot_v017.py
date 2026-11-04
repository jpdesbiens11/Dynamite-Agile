"""0.27.0: Tools in three sections, lean catalogue, brainwriting in rotating
pairs, mind map, PRJ Simulator isolated by the core (lot v0.15) (D-B-073).

    python -m unittest tests.test_lot_v017 -v
"""
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.toolbox import ideation_bw  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur ana | Ana Alpha | utilisateur | actif
utilisateur bob | Bob Bravo | utilisateur | actif
utilisateur cyd | Cyd Charlie | utilisateur | actif
utilisateur dan | Dan Delta | utilisateur | actif
droit ana | DSN | editeur
droit bob | DSN | editeur
droit cyd | DSN | editeur
droit dan | DSN | lecteur
"""


class LotV017Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(cls.data_dir)
        cls.cfg["port"] = 0
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cls.cfg)
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.put("/api/me/prefs", {"initials": "ADM"})
        cls.admin.post("/api/admin/projects", {"key": "DSN", "name": "Design", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.p = {}
        for c in done["created"]:
            client = Client(cls.url)
            client.login(c["username"], c["temp_password"], "Essai-Lot-DixSept-2026!")
            client.put("/api/me/prefs", {"initials": c["username"].upper()})
            cls.p[c["username"]] = client
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["DSN"]
        cls.url_i = "/api/tools/p/{}/ideation".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fail(self, call):
        with self.assertRaises(ApiFailure) as err:
            call()
        return err.exception

    def test_01_pairs_round_robin(self):
        ids = [1, 2, 3, 4, 5, 6]
        met = set()
        for rnd in range(1, 6):
            groups = ideation_bw.pairs(ids, rnd)
            self.assertEqual(sorted(u for g in groups for u in g), ids)  # everybody, once
            met |= {frozenset(g) for g in groups}
        self.assertEqual(len(met), 15)  # 6 people meet each other in 5 rounds
        odd = ideation_bw.pairs([1, 2, 3], 1)
        self.assertEqual(sorted(len(g) for g in odd), [3])  # the odd one out joins a pair: a trio

    def test_02_catalogue_sections(self):
        cat = self.p["ana"].get("/api/tools/catalog")
        self.assertEqual(list(cat["sections"]), ["design", "generator"])
        keys = [m["key"] for m in cat["methods"]]
        self.assertEqual(keys, ["brainstorming", "brainwriting", "storytelling", "mindmap", "pugh", "kepner_tregoe", "generator"])
        gen = next(m for m in cat["methods"] if m["key"] == "generator")
        self.assertEqual(gen["name"], "Reference Generator")
        self.assertTrue(gen["page_id"] and gen["faq_id"])
        methods = self.p["ana"].get(self.url_i)["methods"]
        self.assertEqual(list(methods), ["brainstorming", "brainwriting", "storytelling", "mindmap"])
        self.assertEqual(self.fail(lambda: self.p["ana"].post(self.url_i, {"title": "x", "method": "scamper"})).status, 400)
        startup.run(self.data_dir, self.cfg)  # refresh is idempotent: no new version when nothing changed
        tools = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}["TOOLS"]
        vers = self.admin.get("/api/dynamite/p/{}/pages/{}/versions".format(tools, gen["page_id"]))["versions"]
        startup.run(self.data_dir, self.cfg)
        self.assertEqual(len(self.admin.get("/api/dynamite/p/{}/pages/{}/versions".format(tools, gen["page_id"]))["versions"]), len(vers))

    def test_03_isolated_app(self):
        # core lot v0.15: an offline app page (static/apps/*/index.html) gets its isolated policy (the vitrine)
        with urllib.request.urlopen(self.url + "/apps/vitrine/index.html") as resp:
            csp = resp.headers["Content-Security-Policy"]
        self.assertIn("connect-src 'none'", csp)
        self.assertIn("sandbox allow-scripts", csp)
        self.assertNotIn("allow-same-origin", csp)
        self.assertEqual(resp.headers["X-Frame-Options"], "SAMEORIGIN")
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.url + "/apps/nope/index.html")  # an app that does not exist
        with urllib.request.urlopen(self.url + "/") as resp:
            self.assertEqual(resp.headers["X-Frame-Options"], "DENY")

    def test_04_brainwriting_rounds_pairs_visibility(self):
        ana, bob, cyd, dan = (self.p[k] for k in ("ana", "bob", "cyd", "dan"))
        s = ana.post(self.url_i, {"title": "Fixation", "method": "brainwriting", "rounds": 3, "round_minutes": 5})["session"]
        u = self.url_i + "/{}".format(s["id"])
        self.assertEqual(self.fail(lambda: ana.post(u + "/ideas", {"text": "trop tôt"})).status, 409)
        for c in (ana, bob, cyd):
            c.post(u + "/brainwriting", {"action": "join"})
        self.assertEqual(self.fail(lambda: bob.post(u + "/brainwriting", {"action": "start"})).status, 403)  # not facilitator
        d = ana.post(u + "/brainwriting", {"action": "start"})
        self.assertEqual((d["bw"]["phase"], d["bw"]["round"]), ("running", 1))
        for c, text in ((ana, "idée A1"), (bob, "idée B1"), (cyd, "idée C1")):
            c.post(u + "/ideas", {"text": text, "round": 9})  # the server's clock decides the round
        views = {k: self.p[k].get(u) for k in ("ana", "bob", "cyd")}
        for k, v in views.items():
            partners = {p["name"] for p in v["bw"]["partners"]}
            visible = {i["author_initials"] for i in v["ideas"]}
            self.assertEqual(len(partners), 2 if len(v["bw"]["groups"]) == 1 else len(partners))
            self.assertIn(k.upper(), visible)
            self.assertTrue(all(i["round"] == 1 for i in v["ideas"]))
        self.assertEqual(dan.get(u)["ideas"], [])  # not a participant: sees nothing until the review
        self.assertEqual(dan.get(u)["hidden"], 3)
        ana.post(u + "/brainwriting", {"action": "next"})
        d = bob.post(u + "/ideas", {"text": "idée B2"})
        self.assertEqual(d["ideas"][-1]["round"], 2)
        ana.post(u + "/brainwriting", {"action": "finish"})
        d = dan.get(u)
        self.assertEqual((d["bw"]["phase"], len(d["ideas"])), ("review", 4))
        idea = d["ideas"][0]
        d = bob.patch(u + "/ideas/{}".format(idea["id"]), {"tag": "Guidage", "impact": "high", "feasibility": "low"})
        got = next(i for i in d["ideas"] if i["id"] == idea["id"])
        self.assertEqual((got["tag"], got["impact"], got["feasibility"]), ("Guidage", "high", "low"))
        self.assertEqual(self.fail(lambda: bob.patch(u + "/ideas/{}".format(idea["id"]), {"text": "réécrit"})).status, 403)
        dan.post(u + "/ideas/{}/star".format(idea["id"]))
        d = bob.post(u + "/ideas/{}/star".format(idea["id"]))
        self.assertEqual(next(i for i in d["ideas"] if i["id"] == idea["id"])["stars"], 2)
        self.assertEqual(self.fail(lambda: ana.post(u + "/brainwriting", {"action": "join"})).status, 409)

    def test_05_mindmap(self):
        ana, bob = self.p["ana"], self.p["bob"]
        s = ana.post(self.url_i, {"title": "Carte", "method": "mindmap", "prompt": "Fin de vie"})["session"]
        u = self.url_i + "/{}".format(s["id"])
        a = ana.post(u + "/ideas", {"text": "Démontage", "x": 900, "y": 700, "link_to": "centre"})["ideas"][-1]
        b = bob.post(u + "/ideas", {"text": "Vis standard", "link_to": a["id"]})
        card = b["ideas"][-1]
        self.assertIsNotNone(card["pos_x"])  # placed around the centre when no position is given
        self.assertEqual(len(b["links"]), 2)
        d = bob.patch(u + "/ideas/{}".format(a["id"]), {"x": 99999, "y": -5})  # anyone moves; clamped to the surface
        moved = next(i for i in d["ideas"] if i["id"] == a["id"])
        self.assertEqual((moved["pos_x"], moved["pos_y"]), (2960, 0))
        d = ana.post(u + "/links", {"a_id": card["id"], "b_id": a["id"]})  # same pair again: no duplicate
        self.assertEqual(len(d["links"]), 2)
        d = ana.delete(u + "/links/{}".format(d["links"][0]["id"]))
        self.assertEqual(len(d["links"]), 1)
        self.assertEqual(self.fail(lambda: self.p["dan"].post(u + "/links", {"a_id": a["id"]})).status, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
