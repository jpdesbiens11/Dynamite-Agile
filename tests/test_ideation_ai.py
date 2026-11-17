"""0.60.112 (D-O-125): the digital brainstorm -- the AI proposes the groups of an Idéation board (modules/toolbox/ideation_ai.py,
static/js/toolbox/ideation_ai.js), the board goes to Diamond's « ↔ IA » as source material, and the Atelier prompt draws a live
board in colours. On a session of DEMO.

    python -m unittest tests.test_ideation_ai -v
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
from tools.api_client import ApiFailure, Client  # noqa: E402

POSTITS = ["Glisser le module sur des rails", "Le connecteur s'engage en fin de course", "Verrou à levier", "Risque de coincement",
           "Indicateur verrouillé / déverrouillé", "Quelle masse maximale à la main ?"]


class IdeationAiTest(unittest.TestCase):
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
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/me")["projects"] if p["key"] == "DEMO")
        base = "/api/tools/p/{}/ideation".format(cls.pid)
        cls.sid = cls.admin.post(base, {"title": "Atelier verrouillage", "method": "brainstorming", "prompt": "Comment verrouiller le module ?"})["session"]["id"]
        cls.base = "{}/{}".format(base, cls.sid)
        for text in POSTITS:
            data = cls.admin.post(cls.base + "/ideas", {"text": text})
        cls.ids = ["I{}".format(i["id"]) for i in data["ideas"]]
        made = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", made["temp_password"], new_password="Lecture-2026!")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def answer(self, groups, new=()):
        return "Voici le tableau groupé.\n\n```json\n" + json.dumps({"groups": groups, "new": list(new)}, ensure_ascii=False) + "\n```"

    def test_01_prompt_carries_the_post_its_the_method_and_the_colours(self):
        p = self.admin.get(self.base + "/ai/prompt")["prompt"]
        for code in self.ids:
            self.assertIn('"' + code + '"', p)
        self.assertIn("Comment verrouiller le module ?", p)
        self.assertIn("Termes techniques : toujours en anglais", p)
        self.assertIn("rouge = risque", p)
        self.assertIn('"groups"', p)

    def test_02_preview_then_apply_moves_and_ticked_new_post_its(self):
        i = self.ids
        groups = [{"name": "Guidage", "why": "Comment le module entre", "ideas": [i[0], i[1]]},
                  {"name": "Verrouillage", "why": "Tenir et montrer l'état", "ideas": [i[2], i[4], i[2]]},
                  {"name": "Risques", "why": "", "ideas": [i[3], "I99999"]},
                  {"name": "x" * 61, "ideas": [i[5]]}]
        new = [{"text": "Détrompeur asymétrique", "group": "Guidage"}, {"text": "Second verrou de sécurité", "group": "Verrouillage"}]
        res = self.admin.post(self.base + "/ai/import", {"file": self.answer(groups, new), "mode": "preview"})
        self.assertEqual(res["counts"], {"move": 5, "same": 0, "new": 2, "refused": 3})
        reasons = " ".join(e.get("reason", "") for e in res["entries"] if e["kind"] == "refused")
        self.assertIn("Déjà placé", reasons)
        self.assertIn("inconnu", reasons)
        self.assertIn("60 caractères", reasons)
        self.assertEqual(res["left"], [i[5]])
        self.assertFalse(any(e["default"] for e in res["entries"] if e["kind"] == "new"))
        skip = [e["id"] for e in res["entries"] if e["kind"] == "move" and e["code"] == i[3]]
        take = [e["id"] for e in res["entries"] if e["kind"] == "new" and e["text"].startswith("Détrompeur")]
        done = self.admin.post(self.base + "/ai/import", {"file": self.answer(groups, new), "mode": "apply", "skip": skip, "take": take})
        self.assertEqual((done["moved"], done["added"]), (4, 1))
        ideas = {"I{}".format(x["id"]): x for x in self.admin.get(self.base)["ideas"]}
        self.assertEqual(ideas[i[0]]["tag"], "Guidage")
        self.assertEqual(ideas[i[2]]["tag"], "Verrouillage")
        self.assertEqual(ideas[i[3]]["tag"], "")  # unticked
        added = [x for x in ideas.values() if x["text"] == "Détrompeur asymétrique"]
        self.assertEqual(len(added), 1)
        self.assertEqual((added[0]["tag"], added[0]["author_initials"]), ("Guidage", "IA"))
        again = self.admin.post(self.base + "/ai/import", {"file": self.answer(groups[:1]), "mode": "preview"})
        self.assertEqual(again["counts"]["same"], 2)
        log = self.admin.get("/api/admin/audit?action=ideation_ai_groups")
        self.assertTrue(any(r.get("action") == "ideation_ai_groups" for r in (log.get("entries") or log.get("rows") or [])))

    def test_03_rights_closed_session_and_bad_answers(self):
        self.reader.get(self.base + "/ai/prompt")  # a reader may prepare the prompt
        with self.assertRaises(ApiFailure) as caught:
            self.reader.post(self.base + "/ai/import", {"file": self.answer([]), "mode": "preview"})
        self.assertEqual(caught.exception.status, 403)
        for bad in ("", "pas de json", '```json\n{"autre": []}\n```'):
            with self.assertRaises(ApiFailure) as caught:
                self.admin.post(self.base + "/ai/import", {"file": bad, "mode": "preview"})
            self.assertEqual(caught.exception.status, 400)
        self.admin.patch(self.base, {"status": "closed"})
        try:
            with self.assertRaises(ApiFailure) as caught:
                self.admin.post(self.base + "/ai/import", {"file": self.answer([{"name": "A", "ideas": [self.ids[0]]}]), "mode": "apply"})
            self.assertEqual(caught.exception.status, 409)
        finally:
            self.admin.patch(self.base, {"status": "open"})

    def test_04_the_board_goes_to_diamond_as_source_material(self):
        rt = "/api/diamond/p/{}/rt/prompt?sections=functions&mode=workshop".format(self.pid)
        p = self.admin.get(rt + "&ideation={}".format(self.sid))["prompt"]
        self.assertIn("POST-IT DE LA SÉANCE D'IDÉATION « Atelier verrouillage »", p)
        self.assertIn("Glisser le module sur des rails", p)
        self.assertIn("## Guidage", p)
        self.assertNotIn("POST-IT DE LA SÉANCE", self.admin.get(rt)["prompt"])
        self.assertNotIn("POST-IT DE LA SÉANCE", self.admin.get(rt + "&ideation=999999")["prompt"])  # not in this Space: ignored

    def test_05_workshop_prompt_draws_a_live_board_in_colours(self):
        p = self.admin.get("/api/diamond/p/{}/rt/prompt?sections=functions&mode=workshop".format(self.pid))["prompt"]
        for words in ("UN seul artefact HTML « Tableau »", "jaune = idée / solution", "bleu = besoin / fonction", "rouge = risque",
                      "violet = question", "gris = contrainte", "REGROUPE", "« GÉNÈRE » seulement", "P1"):
            self.assertIn(words, p)

    def test_06_screens(self):
        js = (BASE_DIR / "static/js/toolbox/ideation_ai.js").read_text("utf-8")
        self.assertNotIn("innerHTML", js)
        for key in ("0.60.112-ideation-ai", "0.60.112-ideation-diamond"):
            self.assertIn(key, js)
        self.assertIn("DA.tools.ideationAi", (BASE_DIR / "static/js/toolbox/ideation.js").read_text("utf-8"))
        self.assertIn("0.60.112-ideation-dictate", (BASE_DIR / "static/js/toolbox/ideation.js").read_text("utf-8"))
        self.assertIn("ideation=", (BASE_DIR / "static/js/diamond/rt.js").read_text("utf-8"))
        from core.modules import MODULE_MANIFEST
        tools = next(m for m in MODULE_MANIFEST if m["key"] == "tools")
        self.assertLess(tools["scripts"].index("/js/toolbox/ideation.js"), tools["scripts"].index("/js/toolbox/ideation_ai.js"))
        for path in ("modules/toolbox/ideation_ai.py", "static/js/toolbox/ideation_ai.js", "static/js/toolbox/ideation.js",
                     "static/js/diamond/rt.js", "modules/diamond/rt.py", "modules/diamond/rt_prompt.py"):
            self.assertLess(len((BASE_DIR / path).read_text("utf-8").splitlines()), 500, path)


if __name__ == "__main__":
    unittest.main()
