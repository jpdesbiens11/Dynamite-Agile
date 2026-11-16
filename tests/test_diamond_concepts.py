"""0.60.105 (D-O-117): Diamond -- « Concept initial / Brique technologique »: the bricks of the tree (one brick for several
functions, a function in one brick at most), the concept sheets (digital, AI, scanned paper), the Pugh matrix of a group of bricks
(criteria in order: needs, functions estime / base / performance, requirements; columns made of sheets; deciding selects the sheets),
the AI prompts and the import of the answer, the Project Starter, the rights, the menu in groups. On the Rover of DEMO."""
import base64
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, starter_diamond, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))


class ConceptsTest(unittest.TestCase):
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
        cls.base = "/api/diamond/p/{}".format(cls.pid)
        made = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", made["temp_password"], new_password="Lecture-2026!")
        fns = cls.admin.get(cls.base + "/concepts")["functions"]
        cls.tertiary = [f for f in fns if f["in_tree"] and f["level"] == 3]
        cls.estime = [f for f in fns if f["ftype"] == "estime"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as caught:
            fn(*args)
        self.assertEqual(caught.exception.status, status, caught.exception)
        return str(caught.exception)

    def brick(self, name, fids, **more):
        data = self.admin.post(self.base + "/concepts", dict({"name": name, "initial_name": name[:20], "function_ids": fids}, **more))
        return next(c for c in data["concepts"] if c["id"] == data["created"])

    def test_01_one_brick_for_several_functions(self):
        a, b, c = self.tertiary[:3]
        brick = self.brick("Bloc commun", [a["id"], b["id"]], kind="existing", reference="Pièce du commerce")
        self.assertEqual((brick["code"][:3], sorted(brick["function_ids"])), ("CB-", sorted([a["id"], b["id"]])))
        self.assertEqual((brick["kind"], brick["source"], brick["initial_name"]), ("existing", "team", "Bloc commun"))
        other = self.brick("Autre bloc", [b["id"], c["id"]])  # b leaves the first brick: a function belongs to one brick
        data = self.admin.get(self.base + "/concepts")
        first = next(x for x in data["concepts"] if x["id"] == brick["id"])
        self.assertEqual(first["function_ids"], [a["id"]])
        self.assertEqual(sorted(next(x for x in data["concepts"] if x["id"] == other["id"])["function_ids"]), sorted([b["id"], c["id"]]))
        data = self.admin.post(self.base + "/concepts/link", {"function_id": c["id"], "concept_id": None})
        self.assertNotIn(c["id"], next(x for x in data["concepts"] if x["id"] == other["id"])["function_ids"])
        data = self.admin.patch(self.base + "/concepts/{}".format(other["id"]), {"initial_name": "Sandwich froid", "status": "exploring",
                                                                                  "function_ids": [c["id"]]})
        mine = next(x for x in data["concepts"] if x["id"] == other["id"])
        self.assertEqual((mine["initial_name"], mine["status"], mine["function_ids"]), ("Sandwich froid", "exploring", [c["id"]]))
        self.assertIn("Correctif", self.fails(400, self.admin.patch, self.base + "/concepts/{}".format(other["id"]), {"kind": "maybe"}))
        self.fails(400, self.admin.post, self.base + "/concepts", {"name": "x", "function_ids": [999999]})
        self.admin.post(self.base + "/concepts/{}/archive".format(brick["id"]), {})
        data = self.admin.get(self.base + "/concepts")
        self.assertNotIn(brick["id"], [x["id"] for x in data["concepts"]])
        again = self.brick("Après archive", [])
        self.assertGreater(int(again["code"][3:]), int(brick["code"][3:]))  # numbers are never given again

    def test_02_sheets_digital_and_scan(self):
        brick = self.brick("Thermique", [self.tertiary[4]["id"]])
        made = self.admin.post(self.base + "/concepts/{}/sheets".format(brick["id"]), {"title": "Plaque froide", "principle": "Un liquide",
                                                                                         "pros": "Compact", "cons": "Pompe"})
        self.assertEqual(made["sheets"][0]["code"], brick["code"] + ".1")
        up = self.admin.upload(self.base + "/sheets/upload", PNG, "image/png", "feuille.png")
        made = self.admin.post(self.base + "/concepts/{}/sheets".format(brick["id"]), {"title": "Croquis", "attachment_id": up["id"]})
        scan = next(s for s in made["sheets"] if s["title"] == "Croquis")
        self.assertEqual((scan["kind"], scan["code"], scan["file_mime"]), ("scan", brick["code"] + ".2", "image/png"))
        status, headers, data = self.admin.raw_get(self.base + "/sheets/{}/file".format(scan["id"]))
        self.assertEqual((status, data), (200, PNG))
        self.fails(415, self.admin.upload, self.base + "/sheets/upload", b"not an image", "image/png", "x.png")
        self.fails(400, self.admin.post, self.base + "/concepts/{}/sheets".format(brick["id"]), {"title": ""})
        self.admin.post(self.base + "/sheets/{}/archive".format(scan["id"]), {})
        self.assertEqual([s["title"] for s in self.admin.get(self.base + "/sheets")["sheets"] if s["concept_id"] == brick["id"]], ["Plaque froide"])

    def test_03_pugh_of_a_group_of_bricks(self):
        f1, f2 = self.tertiary[5], self.tertiary[6]
        b1, b2 = self.brick("Brique un", [f1["id"]]), self.brick("Brique deux", [f2["id"]])
        sheets = {}
        for b in (b1, b2):
            for t in ("A", "B"):
                rows = self.admin.post(self.base + "/concepts/{}/sheets".format(b["id"]), {"title": b["name"] + " " + t})["sheets"]
                sheets[(b["id"], t)] = rows[-1]["code"]
        cols = ["{} + {}".format(sheets[(b1["id"], "A")], sheets[(b2["id"], "A")]), "{} + {}".format(sheets[(b1["id"], "B")], sheets[(b2["id"], "A")])]
        m = self.admin.post(self.base + "/pugh", {"title": "Concept global", "concept_ids": [b1["id"], b2["id"]], "concepts": cols})
        self.assertEqual([b["code"] for b in m["scope"]], [b1["code"], b2["code"]])
        self.assertEqual([len(c["sheets"]) for c in m["concepts"]], [2, 2])
        groups = [k["group"] for k in m["criteria"]]
        order = list(m["groups"])
        self.assertEqual(groups, sorted(groups, key=order.index))  # needs, then functions, then requirements
        self.assertIn("need", groups)
        fn_ids = {k["function_id"] for k in m["criteria"] if k.get("fn")}
        self.assertTrue({f1["id"], f2["id"]} <= fn_ids)
        self.assertTrue({f["id"] for f in self.estime} <= fn_ids)
        self.assertTrue(all(k["group"] == "constraint" for k in m["criteria"] if k.get("fn") and k["ftype"] == "contrainte"))
        fk = next(k for k in m["criteria"] if k.get("fn"))
        rk = next(k for k in m["criteria"] if not k.get("fn"))
        other = m["concepts"][1]["id"]
        m = self.admin.put(self.base + "/pugh/{}/score".format(m["matrix"]["id"]), {"criterion_id": fk["id"], "concept_id": other, "score": "+"})
        m = self.admin.put(self.base + "/pugh/{}/score".format(m["matrix"]["id"]), {"criterion_id": rk["id"], "concept_id": other, "score": "+"})
        self.assertEqual(m["totals"][str(other)]["plus"], 2)
        self.fails(400, self.admin.put, self.base + "/pugh/{}/score".format(m["matrix"]["id"]),
                   {"criterion_id": fk["id"], "concept_id": m["matrix"]["datum_id"], "score": "+"})
        n = len(m["criteria"])
        m = self.admin.delete(self.base + "/pugh/{}/criteria/{}".format(m["matrix"]["id"], fk["id"]))
        self.assertEqual(len(m["criteria"]), n - 1)
        m = self.admin.post(self.base + "/pugh/{}/criteria".format(m["matrix"]["id"]), {"fill": True})
        self.assertEqual(len(m["criteria"]), n)
        listed = self.admin.get(self.base + "/pugh")["matrices"]
        self.assertEqual(next(x for x in listed if x["id"] == m["matrix"]["id"])["scope"], [b1["code"], b2["code"]])
        nxt = self.admin.post(self.base + "/pugh/{}/round".format(m["matrix"]["id"]), {"datum_id": other})
        self.assertEqual((nxt["matrix"]["round"], len(nxt["criteria"]), len(nxt["scope"])), (2, n, 2))
        self.assertEqual(sum(len(c["sheets"]) for c in nxt["concepts"]), 4)
        win = next(c for c in nxt["concepts"] if c["id"] != nxt["matrix"]["datum_id"])
        self.admin.patch(self.base + "/pugh/{}".format(nxt["matrix"]["id"]), {"status": "decided", "decision_concept_id": win["id"],
                                                                              "decision_note": "Meilleur net."})
        data = self.admin.get(self.base + "/concepts")
        for b in (b1, b2):
            mine = next(x for x in data["concepts"] if x["id"] == b["id"])
            self.assertEqual(mine["status"], "selected")
            self.assertIn(mine["selected_sheet"]["code"], win["name"])
        status, _h, body = self.admin.raw_get(self.base + "/pugh/{}/export.xlsx".format(nxt["matrix"]["id"]))
        self.assertEqual((status, body[:2]), (200, b"PK"))

    def test_04_ai_prompts_and_import(self):
        prompt = self.admin.get(self.base + "/concepts/prompt")["prompt"]
        self.assertIn("F{}".format(self.tertiary[0]["number"]), prompt)
        self.assertIn("nom qui parle", prompt)
        f = self.tertiary[8]
        answer = "Voici :\n```json\n" + json.dumps({"concepts": [{"name": "Brique IA", "initial_name": "Œil de lynx", "kind": "to_define",
                                                                  "functions": ["F{}".format(f["number"]), "F99999"]}],
                                                    "sheets": [{"concept": "Brique IA", "title": "Option IA", "principle": "p"}]},
                                                   ensure_ascii=False) + "\n```"
        dry = self.admin.post(self.base + "/concepts/ai", {"file": answer, "dry": True})
        self.assertEqual((dry["concepts"], dry["links"], dry["sheets"], dry["dropped"]), (1, 1, 1, 1))
        self.assertNotIn("Brique IA", [c["name"] for c in self.admin.get(self.base + "/concepts")["concepts"]])
        self.admin.post(self.base + "/concepts/ai", {"file": answer})
        mine = next(c for c in self.admin.get(self.base + "/concepts")["concepts"] if c["name"] == "Brique IA")
        self.assertEqual((mine["source"], mine["initial_name"], mine["function_ids"], mine["sheets"]), ("ai", "Œil de lynx", [f["id"]], 1))
        sheet_prompt = self.admin.get(self.base + "/concepts/{}/prompt".format(mine["id"]))["prompt"]
        self.assertIn("Œil de lynx", sheet_prompt)
        self.assertIn("Option IA", sheet_prompt)
        self.fails(409, self.admin.post, self.base + "/concepts/ai", {"file": json.dumps({"concepts": [{"name": "Brique IA"}]})})
        self.assertIn("Correctif", self.fails(400, self.admin.post, self.base + "/concepts/ai", {"file": "pas du JSON"}))

    def test_05_reader_reads_only(self):
        self.reader.get(self.base + "/concepts")
        self.reader.get(self.base + "/sheets")
        self.fails(403, self.reader.post, self.base + "/concepts", {"name": "Non"})
        self.fails(403, self.reader.post, self.base + "/pugh", {"title": "Non", "concepts": ["A"]})

    def test_06_project_starter(self):
        tests = {t["ref"] for t in LAMPE["tests"]}
        clean = starter_diamond.parse(LAMPE, "fr", tests)
        self.assertEqual(len(clean["concepts"]), 7)
        self.assertTrue(all(c["initial_name"] for c in clean["concepts"]))
        bad = json.loads(json.dumps(LAMPE))
        bad["diamond"]["concepts"][1]["functions"].append(bad["diamond"]["concepts"][0]["functions"][0])
        with self.assertRaises(ApiError) as caught:
            starter_diamond.parse(bad, "fr", tests)
        self.assertIn("déjà dans une autre brique", str(caught.exception))
        space = self.admin.post("/api/admin/projects", {"key": "LMP", "name": "Lampe"})
        pid = space["project"]["id"] if "project" in space else space["id"]
        diamond = dict(LAMPE["diamond"], dfmea=[{k: v for k, v in r.items() if k != "test"} for r in LAMPE["diamond"]["dfmea"]])
        out = self.admin.post("/api/diamond/p/{}/import".format(pid), {"file": json.dumps({"diamond": diamond}, ensure_ascii=False)})
        self.assertEqual(out["counts"]["concepts"], 7)
        bricks = self.admin.get("/api/diamond/p/{}/concepts".format(pid))["concepts"]
        self.assertEqual({c["source"] for c in bricks}, {"ai"})
        self.assertEqual(max(len(c["function_ids"]) for c in bricks), 3)

    def test_07_menu_in_groups_and_tools_moved(self):
        js = (BASE_DIR / "static" / "js" / "diamond" / "diamond.js").read_text("utf-8")
        for name in ("Concept / Brique technologique", '["concepts"', '["pugh"', '["kt"', '["ideation"'):
            self.assertIn(name, js)
        self.assertIn("tools", modules.REQUIRES["diamond"])
        tools = (BASE_DIR / "static" / "js" / "toolbox" / "tools.js").read_text("utf-8")
        self.assertIn('"#/diamond/" + space', tools)


if __name__ == "__main__":
    unittest.main()
