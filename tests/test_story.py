"""0.60.51 (D-O-060): the Storyline of Diamond -- scenes with pictograms, before the functional tree.

The 39 pictograms have the same keys in the generator, both sprites, the server list and the palette; a scene keeps only
known pictograms inside its frame; scenes are created, reordered, duplicated, removed, journalled; a reader cannot write;
copying a Space carries the Storyline."""
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "tools"))

from core import auth, db, modules, router, spacecopy, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import story  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402
import story_pictos  # noqa: E402
from sketch_rough import Pen  # noqa: E402
import make_sketch_assets  # noqa: E402

PW = "Storyline-2026!"


class StoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "ROBOT", "name": "Robot"})["project"]["id"]
        cls.base = "/api/diamond/p/{}/story".format(cls.pid)
        created = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, created["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", created["temp_password"], PW)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as err:
            fn(*args)
        self.assertEqual(err.exception.status, status)
        return str(err.exception)

    def test_01_same_pictograms_everywhere(self):
        keys = list(story_pictos.PICTOS)
        self.assertEqual(len(keys), 39)
        self.assertEqual(keys, list(story.PICTOS))
        palette = (BASE_DIR / "static" / "js" / "diamond" / "story_pictos.js").read_text("utf-8")
        self.assertEqual(sorted(re.findall(r'\["([a-z]+)", "[^"]+"\]', palette)), sorted(keys))
        for name, term in (("story.svg", False), ("story-term.svg", True)):
            sprite = (BASE_DIR / "static" / "img" / name).read_text("utf-8")
            self.assertEqual(re.findall(r'<symbol id="p-([a-z]+)"', sprite), keys)
            self.assertNotIn("<text", sprite)  # no text inside an image (FONDATIONS §5)
            self.assertEqual(sprite, story_pictos.sprite(Pen, make_sketch_assets.HL, term=term))  # regenerated identically

    def test_02_scenes_and_pictograms(self):
        data = self.admin.post(self.base + "/scenes", {"title": "La découverte"})
        first = data["created"]
        self.assertEqual([s["title"] for s in data["scenes"]], ["La découverte"])
        items = [{"p": "enfant", "x": 30, "y": 60, "s": 3, "t": "Léa, 9 ans"}, {"p": "produit", "x": 140, "y": -5, "f": 1}]
        data = self.admin.patch(self.base + "/scenes/{}".format(first), {"items": items, "caption": "Léa ouvre la boîte.",
                                                                        "notes": "Où est le bouton ?"})
        scene = data["scenes"][0]
        self.assertEqual(scene["items"][0], {"p": "enfant", "x": 30.0, "y": 60.0, "s": 3, "f": 0, "t": "Léa, 9 ans"})
        self.assertEqual((scene["items"][1]["x"], scene["items"][1]["y"], scene["items"][1]["s"], scene["items"][1]["f"]), (100.0, 0.0, 2, 1))
        self.assertEqual(scene["caption"], "Léa ouvre la boîte.")
        message = self.fails(400, self.admin.patch, self.base + "/scenes/{}".format(first), {"items": [{"p": "licorne"}]})
        self.assertIn("Correctif", message)
        self.fails(400, self.admin.patch, self.base + "/scenes/{}".format(first), {"items": [{"p": "soleil"}] * 31})
        self.fails(400, self.admin.patch, self.base + "/scenes/{}".format(first), {"title": "x" * 81})
        data = self.admin.patch(self.base + "/scenes/{}".format(first), {"title": "  "})  # an empty title gets the scene's number
        self.assertEqual(data["scenes"][0]["title"], "Scène 1")

    def test_03_order_duplicate_delete(self):
        for title in ("Le premier essai", "L'obstacle"):
            self.admin.post(self.base + "/scenes", {"title": title})
        scenes = self.admin.get(self.base)["scenes"]
        last = scenes[-1]["id"]
        data = self.admin.post(self.base + "/scenes/{}/move".format(last), {"to": 0})
        self.assertEqual([s["title"] for s in data["scenes"]], ["L'obstacle", "Scène 1", "Le premier essai"])
        data = self.admin.post(self.base + "/scenes/{}/duplicate".format(scenes[0]["id"]))
        titles = [s["title"] for s in data["scenes"]]
        self.assertEqual(titles, ["L'obstacle", "Scène 1", "Scène 1 (copie)", "Le premier essai"])
        copy = next(s for s in data["scenes"] if s["id"] == data["created"])
        self.assertEqual(copy["items"], scenes[0]["items"])
        self.assertEqual([s["position"] for s in data["scenes"]], [0, 1, 2, 3])
        data = self.admin.post(self.base + "/scenes/{}/delete".format(data["created"]))
        self.assertEqual(len(data["scenes"]), 3)
        with db.connect() as conn:
            actions = {r["action"] for r in conn.execute("SELECT action FROM audit_log WHERE action LIKE 'diamond_story_%'")}
        self.assertEqual(actions, {"diamond_story_create", "diamond_story_update", "diamond_story_move", "diamond_story_duplicate",
                                   "diamond_story_delete"})

    def test_04_reader_and_copy(self):
        scenes = self.reader.get(self.base)["scenes"]
        self.assertTrue(scenes)
        self.fails(403, self.reader.post, self.base + "/scenes", {"title": "x"})
        self.fails(403, self.reader.patch, self.base + "/scenes/{}".format(scenes[0]["id"]), {"title": "x"})
        self.assertIn("diamond_story_scenes", spacecopy.DIAMOND)
        manifest = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        for name in ("story_pictos.js", "story_stage.js", "story.js"):
            self.assertIn("/js/diamond/" + name, manifest["scripts"])
            self.assertNotIn("innerHTML", (BASE_DIR / "static" / "js" / "diamond" / name).read_text("utf-8"))
        shell = (BASE_DIR / "static" / "js" / "diamond" / "diamond.js").read_text("utf-8")
        self.assertIn('nav: [["story", "Storyline"], ["ftree"', shell)  # before the tree


if __name__ == "__main__":
    unittest.main()
