"""0.60.111 (D-O-124): Diamond « ↔ IA », the sections of rt_sections_b.py -- bricks, concept sheets, Pugh matrices, project
risks, DFMEA, characteristics. For each: the dump carries every record with its code and its links as codes, the dump sent back
unchanged is all « same », one field changed is one « update » applied, an item without code is created with its links, an item
left out is removed (archived or deleted). On the Rover of DEMO."""
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


class RoundTripBTest(unittest.TestCase):
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
        fns = cls.admin.get(cls.base + "/concepts")["functions"]
        cls.fns = [f for f in fns if f["in_tree"] and f["level"] == 3]
        cls.me = cls.admin.get("/api/me")["user"]["display_name"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    # ------------------------------------------------------------ helpers

    def dump(self, key):
        status, _h, data = self.admin.raw_get(self.base + "/rt/export.json?sections=" + key)
        self.assertEqual(status, 200, data[:300])
        return json.loads(data.decode("utf-8"))

    def send(self, doc, mode="preview"):
        return self.admin.post(self.base + "/rt/import", {"file": json.dumps(doc, ensure_ascii=False), "mode": mode})

    def same_again(self, key):
        """The dump sent back unchanged: every item « same », nothing else."""
        doc = self.dump(key)
        self.assertTrue(doc[key], key)
        out = self.send({key: doc[key]})
        self.assertEqual({k: v for k, v in out["counts"].items() if v}, {"same": len(doc[key])},
                         [e for e in out["entries"] if e["kind"] != "same"])
        return doc[key]

    def one_update(self, key, code, field, value):
        items = self.dump(key)[key]
        item = next(i for i in items if i["code"] == code)
        item[field] = value
        out = self.send({key: items})
        changed = [e for e in out["entries"] if e["kind"] != "same"]
        self.assertEqual([(e["kind"], e["code"], [c[0] for c in e["changes"]]) for e in changed], [("update", code, [field])], changed)
        self.assertEqual(self.send({key: items}, "apply")["applied"], {"new": 0, "update": 1, "remove": 0})
        return next(i for i in self.dump(key)[key] if i["code"] == code)

    def add(self, key, item):
        items = self.dump(key)[key]
        before = {i["code"] for i in items}
        out = self.send({key: items + [item]})
        self.assertEqual([e["kind"] for e in out["entries"] if e["kind"] != "same"], ["new"], out["entries"])
        self.assertEqual(self.send({key: items + [item]}, "apply")["applied"]["new"], 1)
        made = [i for i in self.dump(key)[key] if i["code"] not in before]
        self.assertEqual(len(made), 1)
        return made[0]

    def remove(self, key, code):
        items = [i for i in self.dump(key)[key] if i["code"] != code]
        out = self.send({key: items})
        self.assertEqual([(e["kind"], e["code"]) for e in out["entries"] if e["kind"] != "same"], [("remove", code)])
        self.assertEqual(self.send({key: items}, "apply")["applied"]["remove"], 1)
        self.assertNotIn(code, [i["code"] for i in self.dump(key)[key]])

    def brick(self, name, fids):
        data = self.admin.post(self.base + "/concepts", {"name": name, "function_ids": fids})
        return next(c for c in data["concepts"] if c["id"] == data["created"])

    # ------------------------------------------------------------ sections

    def test_01_concepts(self):
        a = self.brick("Bloc A", [self.fns[0]["id"], self.fns[1]["id"]])
        self.brick("Bloc B", [self.fns[2]["id"]])
        items = self.same_again("concepts")
        mine = next(i for i in items if i["code"] == a["code"])
        f0, f1 = ("F{}".format(self.fns[n]["number"]) for n in (0, 1))
        self.assertEqual((mine["name"], sorted(mine["functions"]), mine["owner"]), ("Bloc A", sorted([f0, f1]), ""))
        got = self.one_update("concepts", a["code"], "owner", self.me)
        self.assertEqual(got["owner"], self.me)
        got = self.one_update("concepts", a["code"], "functions", [f0])
        self.assertEqual(got["functions"], [f0])
        out = self.send({"concepts": [dict(mine, owner="Personne Inconnue")]})
        # 0.60.116 (D-O-129): the frozen bricks of the Rover refuse to leave too (only the owner is under test here)
        self.assertEqual([e["code"] for e in out["entries"] if e["kind"] == "refused" and "figée" not in e.get("reason", "")], [a["code"]])
        f3 = "F{}".format(self.fns[3]["number"])
        made = self.add("concepts", {"name": "Bloc C", "kind": "existing", "functions": [f3], "status": "exploring"})
        self.assertEqual((made["kind"], made["status"], made["functions"]), ("existing", "exploring", [f3]))
        self.remove("concepts", made["code"])

    def test_02_sheets(self):
        b = self.brick("Bloc feuilles", [self.fns[4]["id"]])
        other = self.brick("Bloc autre", [self.fns[5]["id"]])
        for t in ("Plaque", "Ailettes"):
            self.admin.post(self.base + "/concepts/{}/sheets".format(b["id"]), {"title": t, "pros": "Compact"})
        items = self.same_again("sheets")
        self.assertIn((b["code"] + ".1", b["code"], "Plaque"), [(i["code"], i["concept"], i["title"]) for i in items])
        got = self.one_update("sheets", b["code"] + ".1", "cons", "Pompe")
        self.assertEqual(got["cons"], "Pompe")
        made = self.add("sheets", {"concept": b["code"], "title": "Caloduc", "kind": "ai", "status": "dropped"})
        self.assertEqual((made["code"], made["kind"], made["status"]), (b["code"] + ".3", "ai", "dropped"))
        refused = self.send({"sheets": self.dump("sheets")["sheets"] + [{"title": "Sans brique"}]})
        self.assertEqual(refused["counts"]["refused"], 1, refused["entries"])  # a new sheet needs its brick
        scan = self.send({"sheets": self.dump("sheets")["sheets"] + [{"concept": b["code"], "title": "Papier", "kind": "scan"}]})
        self.assertIn("scan", next(e for e in scan["entries"] if e["kind"] == "refused")["reason"])
        items = self.dump("sheets")["sheets"]  # a sheet moved to another brick: redrawn there, the old one archived
        next(i for i in items if i["code"] == b["code"] + ".2")["concept"] = other["code"]
        self.assertEqual(self.send({"sheets": items}, "apply")["applied"]["update"], 1)
        codes = {i["code"]: i for i in self.dump("sheets")["sheets"]}
        self.assertNotIn(b["code"] + ".2", codes)
        self.assertEqual((codes[other["code"] + ".1"]["title"], codes[other["code"] + ".1"]["pros"]), ("Ailettes", "Compact"))
        self.remove("sheets", made["code"])

    def test_03_pugh(self):
        b1, b2 = self.brick("Bloc P1", [self.fns[6]["id"]]), self.brick("Bloc P2", [self.fns[7]["id"]])
        self.admin.post(self.base + "/pugh", {"title": "Global", "concept_ids": [b1["id"]], "concepts": ["Option 1", "Option 2"]})
        items = self.same_again("pugh")
        mine = next(i for i in items if i["title"] == "Global")
        self.assertEqual((mine["bricks"], mine["columns"], mine["datum"], mine["status"]), ([b1["code"]], ["Option 1", "Option 2"], "Option 1", "draft"))
        got = self.one_update("pugh", mine["code"], "bricks", [b1["code"], b2["code"]])
        self.assertEqual(sorted(got["bricks"]), sorted([b1["code"], b2["code"]]))
        got = self.one_update("pugh", mine["code"], "columns", ["Option 1", "Option 2", "Option 3"])
        self.assertEqual(len(got["columns"]), 3)
        got = self.one_update("pugh", mine["code"], "datum", "Option 2")
        self.assertEqual(got["datum"], "Option 2")
        items = self.dump("pugh")["pugh"]
        item = next(i for i in items if i["code"] == mine["code"])
        item.update(status="decided", decision="Nope")
        self.assertEqual(self.send({"pugh": items})["counts"]["refused"], 1)  # the decision is a column
        item.update(decision="Option 3")
        self.assertEqual(self.send({"pugh": items}, "apply")["applied"]["update"], 1)
        got = next(i for i in self.dump("pugh")["pugh"] if i["code"] == mine["code"])
        self.assertEqual((got["status"], got["decision"]), ("decided", "Option 3"))
        items = self.dump("pugh")["pugh"]
        next(i for i in items if i["code"] == mine["code"])["title"] = "Changé"
        self.assertEqual(self.send({"pugh": items})["counts"]["refused"], 1)  # a decided matrix is read only
        got = self.one_update("pugh", mine["code"], "status", "draft")
        self.assertEqual((got["status"], got["decision"]), ("draft", ""))
        made = self.add("pugh", {"title": "Tour IA", "bricks": [b2["code"]], "columns": ["X", "Y"], "datum": "Y"})
        self.assertEqual((made["bricks"], made["columns"], made["datum"]), ([b2["code"]], ["X", "Y"], "Y"))
        self.remove("pugh", made["code"])

    def test_04_risks(self):
        items = self.same_again("risks")
        code = items[0]["code"]
        got = self.one_update("risks", code, "probability", 5 if items[0]["probability"] != 5 else 4)
        self.assertEqual(got["score"], got["probability"] * got["impact"])
        got = self.one_update("risks", code, "owner", self.me if items[0]["owner"] != self.me else "")
        fn = "F{}".format(self.fns[0]["number"])
        made = self.add("risks", {"title": "Si le moteur chauffe, alors il ralentit", "category": "technique", "probability": 3,
                                  "impact": 4, "function": fn, "to_dfmea": True, "owner": self.me})
        self.assertEqual((made["function"], made["to_dfmea"], made["score"], made["owner"]), (fn, True, 12, self.me))
        bad = self.send({"risks": self.dump("risks")["risks"] + [{"title": "x", "category": "nope"}]})
        self.assertEqual(bad["counts"]["refused"], 1)
        self.remove("risks", made["code"])

    def test_05_dfmea(self):
        items = self.same_again("dfmea")
        self.assertTrue(all(i["code"].startswith("D-") for i in items))
        row = next(i for i in items if i["function"])
        got = self.one_update("dfmea", row["code"], "occurrence", 2 if row["occurrence"] != 2 else 3)
        self.assertEqual(got["rpn"], (got["severity"] or 0) * got["occurrence"] * (got["detection"] or 0) or got["rpn"])
        tests = self.admin.get(self.base + "/dfmea")["tests"]
        if tests:
            got = self.one_update("dfmea", row["code"], "test", tests[0]["code"] if row["test"] != tests[0]["code"] else "")
        fn = "F{}".format(self.fns[1]["number"])
        made = self.add("dfmea", {"function": fn, "failure_mode": "Ne démarre pas", "severity": 7, "occurrence": 3, "detection": 4,
                                  "action_owner": self.me, "action_status": "in_progress"})
        self.assertEqual((made["function"], made["rpn"], made["action_owner"], made["action_status"]), (fn, 84, self.me, "in_progress"))
        out = self.send({"dfmea": self.dump("dfmea")["dfmea"] + [{"failure_mode": "x", "test": "TST-NOPE"}]})
        self.assertEqual(out["counts"]["refused"], 1)
        self.remove("dfmea", made["code"])

    def test_06_chars(self):
        items = self.same_again("chars")
        c = items[0]
        got = self.one_update("chars", c["code"], "notes", "Mesurée au banc")
        self.assertEqual(got["notes"], "Mesurée au banc")
        row = self.dump("dfmea")["dfmea"][0]["code"]
        part = self.admin.get(self.base + "/structure")["parts"][0]["number"]
        made = self.add("chars", {"label": "Jeu axial", "dfmea": row, "nominal": 2.0, "lsl": 1.8, "usl": 2.2, "unit": "mm",
                                  "part": "P-{}".format(part), "control": "spc"})
        self.assertEqual((made["dfmea"], made["part"], made["nominal"], made["usl"]), (row, "P-{}".format(part), 2.0, 2.2))
        self.assertEqual(made["spec"], "2,0 ± 0,2 mm")
        self.remove("chars", made["code"])

    def test_07_all_sections_same(self):
        """The whole dump of these sections, sent back as it is, changes nothing."""
        keys = "concepts,sheets,pugh,risks,dfmea,chars"
        status, _h, data = self.admin.raw_get(self.base + "/rt/export.json?sections=" + keys)
        doc = json.loads(data.decode("utf-8"))
        out = self.send({k: doc[k] for k in keys.split(",")})
        self.assertEqual({k for k, v in out["counts"].items() if v}, {"same"}, [e for e in out["entries"] if e["kind"] != "same"][:5])


if __name__ == "__main__":
    unittest.main()
