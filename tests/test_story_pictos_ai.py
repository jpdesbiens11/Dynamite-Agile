"""0.60.113 (D-O-126): the scenes an AI assistant writes are drawn -- the prompts of « ↔ IA » and of the Project Starter carry
the catalogue of the pictograms (modules/diamond/story_catalog.py), the import resolves names (« battery », « Soldat »), keeps
an unknown word visible as a « question » and lays out the pictograms that have no position; 17 military and field
pictograms join the library; the page buttons « ↔ IA » already does are gone.

    python -m unittest tests.test_story_pictos_ai -v
"""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

MILITARY = ("soldat", "blinde", "camion", "helicoptere", "quadrirotor", "tente", "drapeau", "radio", "generatrice", "conteneur",
            "carte", "cible", "jumelles", "parachute", "bouclier", "montagne", "feu")


def answer(doc):
    return "Voici la Storyline dessinée.\n\n```json\n" + json.dumps(doc, ensure_ascii=False) + "\n```"


class StoryPictosAiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/me")["projects"] if p["key"] == "DEMO")
        cls.base = "/api/diamond/p/{}".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_catalogue_names_and_military_group(self):
        from modules.diamond import story, story_catalog as C
        self.assertEqual(len(C.KEYS), 57)
        self.assertEqual(tuple(story.PICTOS), C.KEYS)
        for key in MILITARY:
            self.assertIn(key, C.KEYS)
        self.assertEqual([C.resolve(w) for w in ("battery", "Batterie", "Génératrice", "soldier", "genset", "quadcopter", "Feu")],
                         ["batterie", "batterie", "generatrice", "soldat", "generatrice", "quadrirotor", "feu"])
        self.assertIsNone(C.resolve("zzz"))
        palette = (BASE_DIR / "static/js/diamond/story_pictos.js").read_text("utf-8")
        self.assertIn('"Militaire et terrain"', palette)
        for key, name in C.NAMES.items():
            self.assertIn('["{}", "{}"]'.format(key, name), palette)  # the same French names in the palette

    def test_02_items_written_by_an_assistant(self):
        from modules.diamond import story
        items = story.ai_items([{"p": "battery", "t": "Pack"}, "Soldat", {"p": "zzz-truc"}, {"p": "froid", "t": "−40 °C"},
                                {"p": "danger"}, {"p": "produit", "x": 50, "y": 45, "s": 3, "t": "x" * 60}])
        self.assertEqual([i["p"] for i in items], ["batterie", "soldat", "question", "froid", "danger", "produit"])
        self.assertEqual(items[2]["t"], "zzz-truc")  # unknown: visible, with its word
        self.assertEqual((items[5]["x"], items[5]["y"], len(items[5]["t"])), (50, 45, 40))
        for i in items:
            self.assertTrue(0 <= i["x"] <= 100 and 0 <= i["y"] <= 100)
        self.assertLess(items[3]["y"], 40)  # the cold up in the sky, the person on the ground
        self.assertGreater(items[1]["y"], 40)
        self.assertNotEqual(items[0]["y"], items[1]["y"])  # neighbours on two rows
        ground = sorted(i["x"] for i in items[:2])
        self.assertGreaterEqual(ground[1] - ground[0], 14)

    def test_03_round_trip_prompt_and_import_draw_the_scenes(self):
        p = self.admin.get(self.base + "/rt/prompt?sections=story&mode=review")["prompt"]
        for words in ("PICTOGRAMMES DE LA STORYLINE", "quadrirotor — Quadrirotor", "Militaire et terrain", "3 à 8 pictogrammes",
                      "Chaque scène, nouvelle ou existante, est DESSINÉE"):
            self.assertIn(words, p)
        doc = {"story": [{"title": "Installation sur site isolé", "caption": "L'opérateur monte le pack.",
                          "items": [{"p": "soldier", "t": "Opérateur"}, {"p": "battery", "t": "Pack"}, {"p": "tente", "t": "Camp"},
                                    {"p": "horloge", "t": "< 5 min"}]}]}
        res = self.admin.post(self.base + "/rt/import", {"file": answer(doc), "mode": "preview"})
        new = [e for e in res["entries"] if e["kind"] == "new"]
        self.assertEqual(len(new), 1, res)
        keep = [e["id"] for e in res["entries"] if e["kind"] == "remove"]
        self.admin.post(self.base + "/rt/import", {"file": answer(doc), "mode": "apply", "skip": keep})
        scene = next(s for s in self.admin.get(self.base + "/story")["scenes"] if s["title"] == "Installation sur site isolé")
        self.assertEqual([i["p"] for i in scene["items"]], ["soldat", "batterie", "tente", "horloge"])
        self.assertEqual(scene["items"][0]["t"], "Opérateur")
        again = self.admin.post(self.base + "/rt/import", {"file": answer({"story": [dict(doc["story"][0], code="S-{}".format(scene["id"]),
                                                                                       items=scene["items"])]}), "mode": "preview"})
        self.assertEqual([e["kind"] for e in again["entries"] if e.get("code") == "S-{}".format(scene["id"])], ["same"])

    def test_04_project_starter_asks_for_drawn_scenes(self):
        from core import starter_diamond, starter_prompt
        for lang in ("fr", "en"):
            text = starter_prompt.render(lang)
            self.assertNotIn("{{PICTOS}}", text)
            self.assertIn("PICTOGRAMMES DE LA STORYLINE", text)
            self.assertIn("`diamond.story[]`", text)
        clean = starter_diamond._story({"story": [{"title": "Expédition", "items": ["crate", {"p": "Camion"}]}]})
        self.assertEqual([i["p"] for i in clean[0]["items"]], ["colis", "camion"])

    def test_06_fixed_wing_and_keys_kept_from_another_install(self):
        """0.60.115 (D-O-128): « aile » (Voilure fixe) joins the library; a stored key the library does not have shows « ? »
        with its word instead of an empty spot -- on screen, in Word, and the scene can still be saved."""
        from core import db
        from modules.diamond import story, story_catalog as C, story_figure
        self.assertIn("aile", C.KEYS)
        self.assertEqual([C.resolve(w) for w in ("fixed-wing", "UAV", "Voilure fixe", "ailes")], ["aile"] * 4)
        self.assertIn("aile — Voilure fixe", self.admin.get(self.base + "/rt/prompt?sections=story&mode=review")["prompt"])
        self.assertIn("aile", story_figure.pictos())
        sid = self.admin.post(self.base + "/story/scenes", {"title": "Autre installation"})["created"]
        items = [{"p": "zz-engin", "t": "Cruise ~2 h", "x": 50, "y": 50, "s": 2, "f": 0},
                 {"p": "zz-retour", "t": "", "x": 20, "y": 60, "s": 2, "f": 0}, {"p": "fixed-wing", "t": "", "x": 80, "y": 30, "s": 2, "f": 0}]
        with db.connect() as conn:
            conn.execute("UPDATE diamond_story_scenes SET items = ? WHERE id = ?", (json.dumps(items), sid))
        scene = next(s for s in self.admin.get(self.base + "/story")["scenes"] if s["id"] == sid)
        self.assertEqual([(i["p"], i["t"]) for i in scene["items"]], [("question", "Cruise ~2 h"), ("question", "zz-retour"), ("aile", "")])
        self.admin.patch(self.base + "/story/scenes/{}".format(sid), {"items": scene["items"]})  # saved again, no refusal
        self.assertTrue(story_figure.render(dict(scene, items=items), fit=True))  # unknown keys drawn as « ? »
        js = (BASE_DIR / "static/js/diamond/story_pictos.js").read_text("utf-8")
        self.assertIn('NAMES[key] ? key : "question"', js)

    def test_05_buttons_that_rt_already_does_are_gone(self):
        js = BASE_DIR / "static/js/diamond"
        self.assertFalse((js / "story_ai.js").exists())
        story_js = (js / "story.js").read_text("utf-8")
        self.assertNotIn("storyAiButtons", story_js)
        # 0.60.114 (D-O-127): « Export .docx » with the page's buttons, top right (pageHead actions, before « ↔ IA »)
        self.assertLess(story_js.index('"Export .docx"'), story_js.index('class: "page-head dm-intro"'))
        self.assertNotIn("dm-story-headline", story_js)
        self.assertNotIn("conceptAiButtons", (js / "concepts.js").read_text("utf-8"))
        self.assertIn("sheetAiButtons", (js / "concept_page.js").read_text("utf-8"))  # one brick's sheets: kept
        self.assertIn("prompt: false", (js / "dfmea.js").read_text("utf-8"))
        self.assertIn("prompt: false", (js / "cplans.js").read_text("utf-8"))
        self.assertIn('modes: ["generate"]', (js / "pfmea.js").read_text("utf-8"))
        from core.modules import MODULE_MANIFEST
        diamond = next(m for m in MODULE_MANIFEST if m["key"] == "diamond")
        self.assertNotIn("/js/diamond/story_ai.js", diamond["scripts"])
        self.assertTrue(all((BASE_DIR / "static" / s.lstrip("/")).exists() for s in diamond["scripts"]))


if __name__ == "__main__":
    unittest.main()
