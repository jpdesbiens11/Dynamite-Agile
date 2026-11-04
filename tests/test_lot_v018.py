"""0.28.0: search everywhere + advanced search (lot noyau v0.16, D-B-076).

    python -m unittest tests.test_lot_v018 -v
"""
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
utilisateur ana | Ana Alpha | utilisateur | actif
utilisateur bob | Bob Bravo | utilisateur | actif
droit ana | AAA | editeur
droit bob | AAA | editeur
droit bob | BBB | editeur
"""


class LotV018Test(unittest.TestCase):
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
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        for key in ("AAA", "BBB"):
            cls.admin.post("/api/admin/projects", {"key": key, "name": key, "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.p = {}
        for c in done["created"]:
            client = Client(cls.url)
            client.login(c["username"], c["temp_password"], "Essai-Lot-DixHuit-2026!")
            cls.p[c["username"]] = client
        ids = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.a, cls.b = ids["AAA"], ids["BBB"]
        ana, bob = cls.p["ana"], cls.p["bob"]
        base = "/api/agile/p/{}".format(cls.a)
        types = {t["icon_key"]: t for t in ana.get(base + "/meta")["types"]}
        cls.t1 = ana.post(base + "/issues", {"type_id": types["task"]["id"], "title": "Rails détrompés du module",
                                             "description": "Verrou quart de tour, sans collage"})
        cls.t2 = ana.post(base + "/issues", {"type_id": types["task"]["id"], "title": "Collage du boîtier",
                                             "description": "Colle époxy, verrou thermique"})
        ana.post(base + "/issues/{}/comments".format(cls.t1["number"]), {"body": "Attention au fretting sous vibration"})
        pages = "/api/dynamite/p/{}/pages".format(cls.a)
        home = ana.get(pages)["pages"][0]
        cls.page = ana.post(pages, {"title": "Étanchéité du connecteur", "parent_id": home["id"],
                                    "body": {"type": "doc", "content": [{"type": "paragraph", "content": [
                                        {"type": "text", "text": "Le degré IP69K est défini par ISO 20653."}]}]}})
        bob.post("/api/dynamite/p/{}/pages".format(cls.b), {"title": "Budget Bravo verrou", "body": {"type": "doc", "content": []}})
        s = bob.post("/api/tools/p/{}/ideation".format(cls.a), {"title": "Paires", "method": "brainwriting"})["session"]
        u = "/api/tools/p/{}/ideation/{}".format(cls.a, s["id"])
        for c in (ana, bob):
            c.post(u + "/brainwriting", {"action": "join"})
        bob.post(u + "/brainwriting", {"action": "start"})
        bob.post(u + "/ideas", {"text": "Idée secrète zeppelin"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def find(self, who, q, **opts):
        params = "&".join("{}={}".format(k, v) for k, v in opts.items())
        return self.p[who].get("/api/search?q={}{}".format(q, "&" + params if params else ""))

    def test_01_everywhere_and_ranking(self):
        res = self.find("ana", "verrou")
        titles = [r["title"] for r in res["results"]]
        self.assertTrue(any("Rails" in t for t in titles) and any("Collage" in t for t in titles))
        self.assertFalse(any("Bravo" in t for t in titles))  # BBB not visible to ana
        key = "AAA-{}".format(self.t2["number"])
        self.assertEqual(self.find("ana", key)["results"][0]["title"].split(" · ")[0], key)  # the key first
        self.assertTrue(any(r["type"] == "ticket_comment" for r in self.find("ana", "fretting")["results"]))
        self.assertTrue(any(r["type"] == "page" for r in self.find("ana", "iso%2020653")["results"]))
        self.assertTrue(any(r["type"] == "person" for r in self.find("ana", "bravo")["results"]))

    def test_02_syntax(self):
        res = self.find("ana", "verrou%20-epoxy")  # exclusion (accents ignored: « époxy »)
        self.assertTrue(res["results"])
        self.assertFalse(any("Collage structural" in r["title"] for r in res["results"]))
        res = self.find("ana", "%22quart%20de%20tour%22")  # exact phrase
        self.assertEqual({r["type"] for r in res["results"]}, {"ticket"})
        self.assertEqual(self.find("ana", "%22tour%20de%20quart%22")["results"], [])

    def test_03_advanced_filters(self):
        self.assertEqual({r["type"] for r in self.find("ana", "verrou", types="page")["results"]}, set())
        only = self.find("bob", "verrou", spaces="BBB")["results"]
        self.assertTrue(only and all(r["project"] == "BBB" for r in only))
        self.assertEqual(self.find("ana", "fretting", **{"in": "title"})["results"], [])  # only in a comment
        self.assertEqual(self.find("ana", "verrou", since="2999-01-01")["results"], [])
        counts = self.find("ana", "verrou")["counts"]
        self.assertGreaterEqual(counts.get("ticket", 0), 2)
        with self.assertRaises(ApiFailure):
            self.find("ana", "verrou", types="nope")
        with self.assertRaises(ApiFailure):
            self.find("ana", "verrou", since="28/09/2026")

    def test_04_private_brainwriting_ideas(self):
        self.assertEqual([r for r in self.find("ana", "zeppelin")["results"] if r["type"] == "idea"], [])  # rounds running
        self.assertTrue([r for r in self.find("bob", "zeppelin")["results"] if r["type"] == "idea"])  # the author finds it


if __name__ == "__main__":
    unittest.main(verbosity=2)
