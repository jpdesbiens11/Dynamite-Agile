"""0.60.108 (D-O-120, D-O-121): FR | EN of a Space's content -- a dictionary per Space in the database (core/space_i18n.py),
added to the display dictionary in EN; and the technical terms in English in every AI prompt (core/terms.py).

    python -m unittest tests.test_space_i18n -v
"""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, backup, db, modules, router, startup, terms  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

USER_PW = "Space-i18n-2026!"
STATEMENT = "Le module doit se remplacer en moins de trente minutes sur la piste."


class SpaceI18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = load_config(cls.data_dir)
        cfg.update(port=0, require_initials=False, dev_mode=False)
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        for key in ("TRA", "OTR"):
            cls.admin.post("/api/admin/projects", {"key": key, "name": "Traduction " + key, "description": "Un Space pour la traduction."})
        projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.pid, cls.other = projects["TRA"], projects["OTR"]
        cls.admin.post("/api/agile/p/{}/goldmine/requirements".format(cls.pid), {"title": "Remplacement rapide", "statement": STATEMENT, "test_ref": "TST-ELE-02"})
        cls.users = {}
        for name, role in (("redacteur", "editor"), ("lectrice", "reader")):
            created = cls.admin.post("/api/admin/users", {"username": name, "display_name": name.title()})
            cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, created["user"]["id"]), {"role": role})
            client = Client(cls.url)
            client.login(name, created["temp_password"], USER_PW)
            cls.users[name] = client
        created = cls.admin.post("/api/admin/users", {"username": "ailleurs", "display_name": "Ailleurs"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.other, created["user"]["id"]), {"role": "editor"})
        cls.outsider = Client(cls.url)
        cls.outsider.login("ailleurs", created["temp_password"], USER_PW)
        cls.base = "/api/projects/{}/i18n".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, call):
        with self.assertRaises(ApiFailure) as caught:
            call()
        return caught.exception.status

    def test_01_texts_of_the_space_not_the_interface(self):
        r = self.users["redacteur"].get(self.base + "/texts")
        self.assertIn("Un Space pour la traduction.", r["texts"])
        self.assertIn("Traduction TRA", r["texts"])
        self.assertIn(STATEMENT, r["texts"])  # a requirement: a row of a module table, found through the foreign keys
        self.assertIn("JSON", r["prompt"])  # the instructions for the AI come along
        self.assertNotIn("Draft", r["texts"])  # interface words already in the display dictionary are left out
        self.assertEqual(self.status(lambda: self.users["lectrice"].get(self.base + "/texts")), 403)
        self.assertEqual(self.status(lambda: self.outsider.get(self.base + "/texts")), 404)

    def test_02_preview_apply_remove_replace(self):
        pairs = {"Un Space pour la traduction.": "A Space for translation.", "  Traduction   TRA ": "Translation TRA"}
        dry = self.admin.put(self.base, {"pairs": pairs, "dry_run": True})
        self.assertEqual((dry["added"], dry["changed"], dry["removed"]), (2, 0, 0))
        self.assertEqual(self.admin.get(self.base)["count"], 0)  # nothing written by a preview
        done = self.admin.put(self.base, {"pairs": pairs})
        self.assertEqual(done["count"], 2)
        listed = {p["fr"]: p["en"] for p in self.admin.get(self.base)["pairs"]}
        self.assertEqual(listed["Traduction TRA"], "Translation TRA")  # spaces collapsed, as the screen shows it
        again = self.admin.put(self.base, {"pairs": {"Traduction TRA": "TRA translation", "Un Space pour la traduction.": ""}})
        self.assertEqual((again["changed"], again["removed"], again["count"]), (1, 1, 1))
        self.admin.put(self.base, {"pairs": [{"fr": STATEMENT, "en": "The module shall be replaced in under thirty minutes."}]})
        replaced = self.admin.put(self.base, {"pairs": {STATEMENT: "The module shall be replaced in under 30 minutes."}, "mode": "replace"})
        self.assertEqual((replaced["changed"], replaced["removed"], replaced["count"]), (1, 1, 1))
        self.assertIn("space_i18n_import", json.dumps(self.admin.get("/api/admin/audit")))

    def test_03_who_writes_who_reads(self):
        self.assertEqual(self.status(lambda: self.users["redacteur"].put(self.base, {"pairs": {"a b c": "x"}})), 403)
        self.assertEqual(self.status(lambda: self.users["lectrice"].put(self.base, {"pairs": {"a b c": "x"}})), 403)
        self.assertEqual(self.status(lambda: self.outsider.put(self.base, {"pairs": {"a b c": "x"}})), 404)
        self.assertEqual(self.status(lambda: self.admin.put(self.base, {"pairs": "texte"})), 400)
        self.assertEqual(self.status(lambda: self.admin.put(self.base, {"pairs": {"x y z": "w"}, "mode": "all"})), 400)
        self.admin.put(self.base, {"pairs": {STATEMENT: "The module shall be replaced in under 30 minutes."}})
        self.assertIn(STATEMENT, self.users["lectrice"].get("/api/i18n/spaces")["pairs"])  # a member reads it in EN
        self.assertNotIn(STATEMENT, self.outsider.get("/api/i18n/spaces")["pairs"])        # another Space's member does not

    def test_04_travels_with_the_space_backup(self):
        self.admin.put(self.base, {"pairs": {"Traduction TRA": "Translation TRA"}})
        with db.connect() as conn:
            _info, rows = backup.collect(conn, self.pid)
        self.assertIn("Traduction TRA", [r["fr"] for r in rows.get("space_i18n", [])])
        status, headers, data = self.admin.raw_get(self.base + ".json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data.decode("utf-8"))["Traduction TRA"], "Translation TRA")

    def test_05_browser_side(self):
        dom = (BASE_DIR / "static" / "js" / "tools" / "i18n_dom.js").read_text("utf-8")
        self.assertIn('"/api/i18n/spaces"', dom)
        self.assertIn("DA.i18nReload", dom)
        card = (BASE_DIR / "static" / "js" / "admin_space_i18n.js").read_text("utf-8")
        self.assertNotIn("innerHTML", card)
        self.assertIn('"0.60.108-space-i18n"', card)
        self.assertIn('<script src="/js/admin_space_i18n.js" defer></script>', (BASE_DIR / "static" / "index.html").read_text("utf-8"))

    def test_06_technical_terms_in_english_in_every_prompt(self):
        from modules.diamond import ai_prompts, concept_ai, costs_prompt, pfmea_ai, story_ai
        for mod in (ai_prompts, pfmea_ai, story_ai, concept_ai, costs_prompt):
            self.assertIn("terms", Path(mod.__file__).read_text("utf-8"), mod.__name__)
        self.assertIn("{terms}", concept_ai.GUIDE_BRICKS + concept_ai.GUIDE_SHEETS + story_ai.GUIDE + costs_prompt.GUIDE)
        self.assertIn("anglais", terms.RULE_FR)
        self.assertIn("Termes techniques", (BASE_DIR / "tools" / "site" / "starter.md").read_text("utf-8"))
        self.assertIn("Technical terms always in", (BASE_DIR / "tools" / "site" / "en" / "starter.md").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
