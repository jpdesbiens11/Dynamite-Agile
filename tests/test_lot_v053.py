"""0.50.14 (D-B-132 to D-B-134, core lot v0.34): Tools in two sections, the card of a Space in Admin (rename, duplicate, save
as), every Space provisioned in every tab with a guided « Commencer ici ».

    python -m unittest tests.test_lot_v053 -v
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
from modules.training import catalog as training_catalog  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

STATIC = BASE_DIR / "static"


class LotV053Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(cls.data_dir)
        cls.cfg["port"] = 0
        cls.cfg["require_initials"] = False
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cls.cfg)
        cls.server = router.create_server(cls.cfg, STATIC, cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def project(self, key):
        return next(p for p in self.admin.get("/api/admin/projects")["projects"] if p["key"] == key)

    # D-B-132 ------------------------------------------------------------------------------------------------------
    def test_01_tools_sections(self):
        cat = self.admin.get("/api/tools/catalog")
        self.assertEqual(list(cat["sections"]), ["design", "generator"])
        self.assertFalse((BASE_DIR / "static" / "vendor").exists())  # no third-party library
        codes = {t[0] for t in training_catalog._topics()}
        self.assertFalse({"TL-04", "TL-05"} & codes)

    # D-B-133 ------------------------------------------------------------------------------------------------------
    def test_03_space_card(self):
        made = self.admin.post("/api/admin/projects", {"key": "ALP", "name": "Alpha", "description": "Essai"})["project"]
        card = self.admin.get("/api/admin/projects/{}/card".format(made["id"]))
        self.assertEqual(card["project"]["key"], "ALP")
        self.assertEqual(card["suggested_key"], "ALP2")
        self.assertNotIn("special", card)
        tabs = {c["tab"]: c["count"] for c in card["content"]}
        self.assertGreaterEqual(tabs["Dynamite"], 1)          # the home page of a new Space
        self.assertTrue(card["parts"])
        # rename: name only, the key never changes
        self.admin.patch("/api/admin/projects/{}".format(made["id"]), {"name": "Alpha bis"})
        self.assertEqual(self.project("ALP")["name"], "Alpha bis")
        # duplicate: everything, next free key, « (copie) »
        dup = self.admin.post("/api/admin/projects/{}/copy".format(made["id"]), {})["project"]
        self.assertEqual(dup["key"], "ALP2")
        self.assertEqual(self.project("ALP2")["name"], "Alpha bis (copie)")
        # save as: chosen key, name and parts
        part = card["parts"][0]["part"]
        saved = self.admin.post("/api/admin/projects/{}/copy".format(made["id"]),
                                {"key": "BET", "name": "Beta", "parts": [part]})["project"]
        self.assertEqual((saved["key"], self.project("BET")["name"]), ("BET", "Beta"))
        with self.assertRaises(ApiFailure) as err:
            self.admin.post("/api/admin/projects/{}/copy".format(made["id"]), {"key": "BET"})
        self.assertIn(err.exception.status, (400, 409))
        with self.assertRaises(ApiFailure) as err:
            self.admin.post("/api/admin/projects/{}/copy".format(made["id"]), {"key": "GAM", "parts": ["nope"]})
        self.assertEqual(err.exception.status, 400)
        self.assertEqual(self.admin.get("/api/admin/projects/{}/card".format(made["id"]))["suggested_key"], "ALP3")
        with db.connect() as conn:
            n = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'space_saved_as'").fetchone()[0]
        self.assertEqual(n, 2)

    # D-B-134 ------------------------------------------------------------------------------------------------------
    def test_04_ensure_space(self):
        bare = self.admin.post("/api/admin/projects", {"key": "NUE", "name": "Nu", "provision": False})["project"]
        old = self.admin.post("/api/admin/projects", {"key": "OLD", "name": "Archivé", "provision": False})["project"]
        self.admin.patch("/api/admin/projects/{}".format(old["id"]), {"is_archived": True})
        pid = bare["id"]
        checks = ["SELECT COUNT(*) FROM dynamite_pages WHERE project_id = ?",
                  "SELECT COUNT(*) FROM agile_settings WHERE project_id = ?",
                  "SELECT COUNT(*) FROM exploration_plans WHERE project_id = ?",
                  "SELECT COUNT(*) FROM timesheet_projects WHERE project_id = ?"]
        with db.connect() as conn:
            before = [conn.execute(sql, (pid,)).fetchone()[0] for sql in checks]
        self.assertEqual(before, [0, 0, 0, 0])
        startup.spaces_ready()
        with db.connect() as conn:
            once = [conn.execute(sql, (pid,)).fetchone()[0] for sql in checks]
        self.assertTrue(all(n >= 1 for n in once), once)
        startup.spaces_ready()                                   # idempotent: nothing added twice
        with db.connect() as conn:
            twice = [conn.execute(sql, (pid,)).fetchone()[0] for sql in checks]
            archived_untouched = conn.execute("SELECT COUNT(*) FROM agile_settings WHERE project_id = ?",
                                              (old["id"],)).fetchone()[0]
        self.assertEqual(once, twice)
        self.assertEqual(archived_untouched, 0)                 # an archived Space is left alone
        self.assertTrue(modules.space_hooks())

    def test_05_screens(self):
        spaces = (STATIC / "js/tools/spaces.js").read_text("utf-8")
        self.assertIn("startHere", spaces)
        self.assertIn("0.50.14-start-here", spaces)
        for rel in ("js/agile/board.js", "js/agile/goldmine.js", "js/agile/changes.js"):
            self.assertIn("DA.spaces.startHere(", (STATIC / rel).read_text("utf-8"), rel)
        card = (STATIC / "js/admin_spacecard.js").read_text("utf-8")
        self.assertNotIn("innerHTML", card)
        self.assertLess(card.count("\n"), 500)
        for tag in ("0.50.14-space-card",):
            self.assertIn(tag, card)
        for label in ("Renommer", "Dupliquer", "Enregistrer sous", "Archiver", "Supprimer"):
            self.assertIn(label, card)
        index = (STATIC / "index.html").read_text("utf-8")
        self.assertIn("/js/admin_spacecard.js", index)
        self.assertNotIn("/vendor/", index)


if __name__ == "__main__":
    unittest.main()
