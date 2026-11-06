"""0.25.0: « Tools » (D-B-065): catalogue and wiki pages (TOOLS space), ideation
sessions (D-B-066), Kepner-Tregoe (D-B-067); Goldmine needs (D-B-064).

    python -m unittest tests.test_lot_v015 -v
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
utilisateur ines | Inès Idée | utilisateur | actif
utilisateur remi | Rémi Lecteur | utilisateur | actif
droit ines | PRJ | editeur
droit remi | PRJ | lecteur
"""


class LotV015Test(unittest.TestCase):
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
        cls.admin.post("/api/admin/projects", {"key": "PRJ", "name": "PRJ", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.people = {}
        for i, c in enumerate(done["created"]):
            client = Client(cls.url)
            client.login(c["username"], c["temp_password"], "Essai-Lot-Quinze-2026!")
            client.put("/api/me/prefs", {"initials": ["INS", "RML"][i]})
            cls.people[c["username"]] = client
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["PRJ"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fail_status(self, call):
        with self.assertRaises(ApiFailure) as err:
            call()
        return err.exception.status

    def test_01_catalogue_and_wiki(self):
        cat = self.people["remi"].get("/api/tools/catalog")  # joins TOOLS as editor
        keys = {m["key"]: m for m in cat["methods"]}
        for k in ("brainstorming", "brainwriting", "mindmap", "pugh", "kepner_tregoe", "generator"):  # D-B-073

            self.assertIn(k, keys)
            self.assertTrue(keys[k]["page_id"] and keys[k]["faq_id"], k)
        self.assertEqual(keys["pugh"]["family"], "convergent")
        tools_pid = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}["DEMO"]
        page = self.people["remi"].get("/api/dynamite/p/{}/pages/{}".format(tools_pid, keys["brainstorming"]["faq_id"]))["page"]
        self.assertIn("FAQ", page["title"])
        startup.run(self.data_dir, self.cfg)  # idempotent: no duplicate page
        titles = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(tools_pid))["pages"]]
        self.assertEqual(titles.count("Brainstorming"), 1)
        self.assertNotIn("SCAMPER", titles)  # D-B-073: retired method, generated page removed
        nav = [m["key"] for m in self.admin.get("/api/me")["modules"]]
        self.assertLess(nav.index("tools"), nav.index("codex"))
        codex = next(m for m in self.admin.get("/api/me")["modules"] if m["key"] == "codex")
        self.assertEqual(codex["placement"], "tools")
        dash = [p["key"] for p in self.people["remi"].get("/api/dashboard")["projects"]]
        self.assertNotIn("TOOLS", dash)  # D-B-068

    def test_02_ideation(self):
        ines, remi = self.people["ines"], self.people["remi"]
        url = "/api/tools/p/{}/ideation".format(self.pid)
        s = ines.post(url, {"title": "Fixation", "method": "brainstorming", "prompt": "Comment pourrions-nous…"})["session"]
        self.assertEqual(self.fail_status(lambda: remi.post(url, {"title": "x"})), 403)
        d = ines.post(url + "/{}/ideas".format(s["id"]), {"text": "Rails détrompés", "round": 1})
        first = d["ideas"][0]
        self.assertEqual(first["author_initials"], "INS")
        d = ines.post(url + "/{}/ideas".format(s["id"]), {"text": "Rails qui guident le connecteur", "round": 2, "parent_id": first["id"]})
        self.assertEqual(d["ideas"][1]["parent_id"], first["id"])
        d = remi.post(url + "/{}/ideas/{}/star".format(s["id"], first["id"]))  # a reader stars (D-B-073)
        self.assertEqual((d["ideas"][0]["stars"], d["ideas"][0]["starred"]), (1, 1))
        self.assertEqual(self.fail_status(lambda: remi.patch(url + "/{}/ideas/{}".format(s["id"], first["id"]), {"text": "x"})), 403)
        ines.patch(url + "/{}".format(s["id"]), {"status": "closed"})
        self.assertEqual(self.fail_status(lambda: ines.post(url + "/{}/ideas".format(s["id"]), {"text": "trop tard"})), 409)
        status, _h, data = ines.raw_get(url + "/{}/export.csv".format(s["id"]))
        self.assertEqual(status, 200)
        self.assertIn("Rails détrompés", data.decode("utf-8-sig"))

    def test_03_kepner_tregoe(self):
        url = "/api/tools/p/{}/kt".format(self.pid)
        k = self.admin.post(url, {"title": "Fournisseur de l'élément chauffant", "statement": "Choisir…", "alternatives": ["A", "B", "C"]})
        kid = k["kt"]["id"]
        alts = {a["name"]: a["id"] for a in k["alts"]}
        d = self.admin.post(url + "/{}/criteria".format(kid), {"kind": "must", "text": "UN 38.3 réussi"})
        must = d["criteria"][0]["id"]
        d = self.admin.post(url + "/{}/criteria".format(kid), {"kind": "want", "text": "Énergie spécifique", "weight": 10})
        d = self.admin.post(url + "/{}/criteria".format(kid), {"kind": "want", "text": "Coût", "weight": 5})
        wants = [c["id"] for c in d["criteria"] if c["kind"] == "want"]
        for name, (m, s1, s2) in {"A": (1, 8, 5), "B": (1, 6, 10), "C": (0, 10, 10)}.items():
            self.admin.put(url + "/{}/score".format(kid), {"criterion_id": must, "alt_id": alts[name], "value": m})
            self.admin.put(url + "/{}/score".format(kid), {"criterion_id": wants[0], "alt_id": alts[name], "value": s1})
            d = self.admin.put(url + "/{}/score".format(kid), {"criterion_id": wants[1], "alt_id": alts[name], "value": s2})
        r = d["results"]
        self.assertTrue(r[str(alts["C"])]["eliminated"])
        self.assertEqual((r[str(alts["A"])]["weighted"], r[str(alts["B"])]["weighted"]), (105, 110))
        self.assertEqual((r[str(alts["B"])]["rank"], r[str(alts["A"])]["rank"], r[str(alts["C"])]["rank"]), (1, 2, None))
        self.assertEqual(self.fail_status(lambda: self.admin.put(url + "/{}/score".format(kid), {
            "criterion_id": wants[0], "alt_id": alts["A"], "value": 11})), 400)
        d = self.admin.post(url + "/{}/risks".format(kid), {"alt_id": alts["B"], "text": "Fournisseur unique", "probability": 2, "seriousness": 3})
        self.assertEqual(d["results"][str(alts["B"])]["risk"], 6)
        self.admin.patch(url + "/{}".format(kid), {"status": "decided", "decision_alt_id": alts["B"], "decision_note": "Meilleur score."})
        self.assertEqual(self.fail_status(lambda: self.admin.post(url + "/{}/alts".format(kid), {"name": "D"})), 409)

    def test_04_goldmine_needs(self):
        base = "/api/agile/p/{}".format(self.pid)
        need = self.admin.post(base + "/goldmine/requirements", {"kind": "need", "stakeholder": "production", "external_id": "BN-900",
                                                                 "statement": "Les assembleurs ont besoin de monter sans erreur."})
        req = self.admin.post(base + "/goldmine/requirements", {"statement": "Le module doit être détrompé.", "derived_from": "bn-900",
                                                                "test_ref": "TST-PRD-01"})
        orphan = self.admin.post(base + "/goldmine/requirements", {"statement": "Le module doit être bleu.", "derived_from": "BN-999",
                                                                   "test_ref": "TST-VER-01"})
        data = self.admin.get(base + "/goldmine")
        items = {r["key"]: r for r in data["requirements"]}
        self.assertEqual(items[req["key"]]["needs"], [need["key"]])
        self.assertEqual(items[need["key"]]["derived_requirements"], [req["key"]])
        self.assertIn(orphan["key"], data["gaps"]["unknown_need"])
        self.assertNotIn(need["key"], data["gaps"]["no_method"])
        self.assertEqual(self.fail_status(lambda: self.admin.post(base + "/goldmine/requirements", {
            "statement": "x", "kind": "souhait"})), 400)
        m = self.admin.post(base + "/pugh", {"title": "Test", "concepts": ["A", "B"]})
        d = self.admin.post(base + "/pugh/{}/criteria".format(m["matrix"]["id"]), {"kind": "need"})
        self.assertEqual([c["key"] for c in d["criteria"]], [need["key"]])


if __name__ == "__main__":
    unittest.main()
