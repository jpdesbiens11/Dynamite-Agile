"""0.60.111 (D-O-124): « ↔ IA », the round trip of every Diamond page with an AI assistant (modules/diamond/rt.py, rt_prompt.py,
rt_sections_*.py, static/js/diamond/rt.js). The export re-imported unchanged is « identique » everywhere; a change, a new item
pointing to another new item (« +F1 »), a removal; the rehearsal turns what a page's route refuses into « refusé » with the route's
message; a truncated answer leaves its removals unticked; apply writes a backup of the Space, journals, and a second import is
identical; readers cannot import; the prompt carries the method, the D-O-121 rule and the codes. On the Rover of DEMO.

    python -m unittest tests.test_diamond_rt -v
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

A = "story,functions,ports,parts,flows"


def answer(doc):
    return "Voici la révision :\n\n```json\n" + json.dumps(doc, ensure_ascii=False, indent=1) + "\n```\n\n- F7 reformulée."


class RoundTripTest(unittest.TestCase):
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
        cls.base = "/api/diamond/p/{}/rt".format(cls.pid)
        made = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", made["temp_password"], new_password="Lecture-2026!")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def export(self, sections=A):
        status, _h, data = self.admin.raw_get(self.base + "/export.json?sections=" + sections)
        self.assertEqual(status, 200)
        doc = json.loads(data)
        doc.pop("_context", None)
        return doc

    def preview(self, doc):
        return self.admin.post(self.base + "/import", {"file": answer(doc), "mode": "preview"})

    def test_01_every_page_has_its_sections(self):
        secs = {s["key"]: s for s in self.admin.get(self.base + "/sections")["sections"]}
        for key in A.split(","):
            self.assertIn(key, secs)
            self.assertGreater(secs[key]["count"], 0, key)
        self.assertIn("ftree", secs["functions"]["pages"])
        self.assertIn("fstructure", secs["flows"]["pages"])

    def test_02_unchanged_export_is_identical_everywhere(self):
        doc = self.export()
        res = self.preview(doc)
        self.assertEqual(res["counts"]["same"], sum(len(v) for v in doc.values()))
        self.assertEqual([res["counts"][k] for k in ("new", "update", "remove", "refused")], [0, 0, 0, 0], res["warnings"])
        self.assertTrue(all(f["code"].startswith("F") for f in doc["functions"]))
        self.assertTrue(all(isinstance(p["functions"], list) for p in doc["parts"]))
        self.assertTrue(all(x["src"] and x["dst"] for x in doc["flows"]))

    def test_03_change_new_linked_and_removal(self):
        doc = self.export()
        second = next(f for f in doc["functions"] if f["level"] == 2)
        doc["functions"][3]["text"] = "Mesurer la distance aux obstacles devant le Rover"
        doc["functions"].append({"code": "+F1", "text": "Journaliser les événements de la mission", "type": "usage", "parent": second["code"]})
        doc["functions"].append({"text": "Écrire le journal sur la carte SD", "type": "usage", "parent": "+F1"})  # level 4: refused
        doc["parts"].append({"name": "Carte microSD 16 Go", "kind": "bought", "functions": ["+F1"]})
        gone = doc["parts"].pop(0)
        res = self.preview(doc)
        kinds = {(e["section"], e["kind"]) for e in res["entries"] if e["kind"] != "same"}
        self.assertEqual(res["counts"]["update"], 1)
        self.assertIn(("functions", "new"), kinds)
        self.assertIn(("parts", "new"), kinds)
        removed = [e for e in res["entries"] if e["kind"] == "remove"]
        self.assertEqual([e["code"] for e in removed], [gone["code"]])
        refused = [e for e in res["entries"] if e["kind"] == "refused"]
        self.assertEqual(len(refused), 1)
        self.assertIn("Refusé par la page", refused[0]["reason"])
        self.assertIn("technique", refused[0]["reason"])
        done = self.admin.post(self.base + "/import", {"file": answer(doc), "mode": "apply"})
        self.assertEqual(done["applied"], {"new": 2, "update": 1, "remove": 1})
        self.assertTrue(done["backup"].endswith(".zip"))
        after = self.export()
        mine = next(f for f in after["functions"] if f["text"] == "Journaliser les événements de la mission")
        self.assertEqual(mine["parent"], second["code"])
        card = next(p for p in after["parts"] if p["name"] == "Carte microSD 16 Go")
        self.assertEqual(card["functions"], [mine["code"]])
        self.assertNotIn(gone["code"], [p["code"] for p in after["parts"]])
        again = self.preview(after)
        self.assertEqual([again["counts"][k] for k in ("new", "update", "remove", "refused")], [0, 0, 0, 0])
        log = self.admin.get("/api/admin/audit?action=diamond_rt_import")
        self.assertTrue(any(r.get("action") == "diamond_rt_import" for r in (log.get("entries") or log.get("rows") or [])))

    def test_04_truncated_answer_unticks_its_removals_and_skip_is_honoured(self):
        doc = self.export("flows")
        doc["flows"] = doc["flows"][:3]
        res = self.preview(doc)
        removes = [e for e in res["entries"] if e["kind"] == "remove"]
        self.assertTrue(removes)
        self.assertFalse(any(e["default"] for e in removes))
        self.assertTrue(any("tronquée" in w for w in res["warnings"]))
        doc = self.export("story")
        doc["story"][0]["title"] = "La découverte du kit"
        doc["story"][1]["title"] = "Le premier montage"
        res = self.preview(doc)
        skip = [e["id"] for e in res["entries"] if e["kind"] == "update" and e["code"] == doc["story"][1]["code"]]
        done = self.admin.post(self.base + "/import", {"file": answer(doc), "mode": "apply", "skip": skip})
        self.assertEqual(done["applied"]["update"], 1)
        titles = [s["title"] for s in self.export("story")["story"]]
        self.assertIn("La découverte du kit", titles)
        self.assertNotIn("Le premier montage", titles)

    def test_05_refusals_unknown_codes_and_links(self):
        doc = {"functions": self.export("functions")["functions"], "parts": [{"name": "Pièce fantôme", "functions": ["F999"]}]}
        doc["functions"].append({"code": "F998", "text": "Inconnue"})
        doc["functions"].append({"text": "Type faux", "type": "magique", "parent": doc["functions"][0]["code"]})
        res = self.preview(doc)
        reasons = " ".join(e["reason"] for e in res["entries"] if e["kind"] == "refused")
        self.assertIn("Code inconnu", reasons)
        self.assertIn("F999", reasons)
        self.assertIn("magique", reasons)
        self.assertIn("Sections ignorées", " ".join(self.preview({"bogus": [], "story": self.export("story")["story"]})["warnings"]))

    def test_06_reader_exports_but_never_imports(self):
        status, _h, _d = self.reader.raw_get(self.base + "/export.json?sections=functions")
        self.assertEqual(status, 200)
        with self.assertRaises(ApiFailure) as caught:
            self.reader.post(self.base + "/import", {"file": answer(self.export("story")), "mode": "preview"})
        self.assertEqual(caught.exception.status, 403)

    def test_07_prompt_carries_method_rule_codes_and_modes(self):
        for mode in ("review", "interview", "workshop"):
            p = self.admin.get(self.base + "/prompt?sections=functions,parts&mode=" + mode + "&goal=Revue%20de%20vendredi")["prompt"]
            self.assertIn("Termes techniques : toujours en anglais", p)
            self.assertIn("Revue de vendredi", p)
            self.assertIn("\"code\": \"F1\"", p)
            self.assertIn("« + »", p)
            self.assertIn("COMPLÈTE", p)
        self.assertIn("GÉNÈRE", self.admin.get(self.base + "/prompt?sections=functions&mode=workshop")["prompt"])
        self.assertIn("CONTEXTE", self.admin.get(self.base + "/prompt?sections=parts")["prompt"])  # parts point to functions

    def test_08_answer_reading(self):
        from modules.diamond.rt import read_doc
        from core.errors import ApiError
        self.assertEqual(read_doc('blabla ```json\n{"functions": []}\n``` fin'), {"functions": []})
        self.assertEqual(read_doc('{"diamond": {"story": []}}'), {"story": []})
        with self.assertRaises(ApiError):
            read_doc("pas de JSON ici")

    def test_10_two_new_items_without_code_and_all_of_diamond_unchanged(self):
        doc = self.export("story")
        doc["story"] += [{"title": "Le retour au labo", "caption": "Sam range le Rover."}, {"title": "La démo", "caption": "Devant la classe."}]
        res = self.preview(doc)
        self.assertEqual(res["counts"]["new"], 2, res["entries"])
        self.assertEqual(res["counts"]["refused"], 0)
        keys = ",".join(s["key"] for s in self.admin.get(self.base + "/sections")["sections"])
        everything = self.export(keys)
        self.assertGreaterEqual(len(everything), 15)
        res = self.preview(everything)
        moved = [(e["section"], e["code"], e["kind"], e["reason"]) for e in res["entries"] if e["kind"] != "same"]
        self.assertEqual(moved, [])

    def test_11_a_line_pointing_to_a_refused_or_unticked_new_item_is_refused(self):
        doc = self.export("functions")
        second = next(f for f in doc["functions"] if f["level"] == 2)["code"]
        doc["functions"].append({"code": "+F1", "text": "x" * 200, "type": "usage", "parent": second})  # too long: refused by the page
        doc["functions"].append({"text": "Sous-fonction orpheline", "type": "usage", "parent": "+F1"})
        res = self.preview(doc)
        child = next(e for e in res["entries"] if e["label"] == "Sous-fonction orpheline")
        self.assertEqual(child["kind"], "refused")
        self.assertIn("pointe un élément refusé ou décoché", child["reason"])
        doc["functions"][-2]["text"] = "Parent que l'on décoche"
        res = self.preview(doc)
        parent = next(e for e in res["entries"] if e["code"] == "+F1")
        self.assertEqual(parent["kind"], "new")
        before = len(self.export("functions")["functions"])
        with self.assertRaises(ApiFailure) as caught:  # the parent unticked: the child is refused, nothing is left to apply
            self.admin.post(self.base + "/import", {"file": answer(doc), "mode": "apply", "skip": [parent["id"]]})
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(len(self.export("functions")["functions"]), before, "the child must not be created without its parent")

    def test_12_truncated_answer_removals_need_an_explicit_tick_on_the_server(self):
        doc = self.export("flows")
        before = len(doc["flows"])
        doc["flows"] = doc["flows"][:2]
        doc["flows"][0]["label"] = "flux renommé"
        res = self.preview(doc)
        gone = [e["id"] for e in res["entries"] if e["kind"] == "remove"]
        done = self.admin.post(self.base + "/import", {"file": answer(doc), "mode": "apply"})  # no skip, no confirm
        self.assertEqual(done["applied"], {"new": 0, "update": 1, "remove": 0})
        self.assertEqual(len(self.export("flows")["flows"]), before)
        done = self.admin.post(self.base + "/import", {"file": answer(doc), "mode": "apply", "confirm": gone[:1]})
        self.assertEqual(done["applied"]["remove"], 1)
        self.assertEqual(len(self.export("flows")["flows"]), before - 1)

    def test_09_screen_rules(self):
        js = (BASE_DIR / "static/js/diamond/rt.js").read_text("utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertIn('"0.60.111-rt"', js)
        self.assertIn("headTools", (BASE_DIR / "static/js/diamond/diamond.js").read_text("utf-8"))
        self.assertIn("ctx.shell.headTools", (BASE_DIR / "static/js/agile/agile.js").read_text("utf-8"))
        from core.modules import MODULE_MANIFEST
        diamond = next(m for m in MODULE_MANIFEST if m["key"] == "diamond")
        self.assertIn("/js/diamond/rt.js", diamond["scripts"])
        self.assertIn("/css/diamond_rt.css", diamond["styles"])
        for name in ("rt.py", "rt_prompt.py", "rt_sections_a.py", "rt_sections_b.py", "rt_sections_c.py"):
            self.assertLess(len((BASE_DIR / "modules/diamond" / name).read_text("utf-8").splitlines()), 500, name)
        self.assertLess(len(js.splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
