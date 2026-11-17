"""0.60.111 (D-O-124): « ↔ IA » -- the sections of Industrialisation (lines, operations and their control points, PFMEA,
control plans and their rows) and of Projet (NRE, cost lines), on the Rover of DEMO: the dump with its codes and links, the
dump given back unchanged (all « same »), one field changed, a new item linked by codes (temporary « +… » codes included),
a removal where the page can remove, the create-only fields and an operation that still has PFMEA rows refused."""
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
from modules.diamond import rt, rt_sections_b  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

KEYS = ["process_lines", "process_ops", "pfmea", "cplans", "cplan_items", "costs_nre", "costs_lines"]


def _chars_fallback():
    """The C-n section belongs to rt_sections_b; while it is not there, a minimal one lets these sections point to it."""
    if any(s.key == "chars" for s in rt.registry().values()):
        return
    rt_sections_b.SECTIONS = rt_sections_b.SECTIONS + [rt.Section(
        "chars", "Caractéristiques", ["chars"], order=60, table="diamond_characteristics",
        items=lambda r: r.call("GET", "/characteristics")["items"], code=lambda r: r["code"], fields=[rt.Field("label")])]


class RoundTripIndustrialisationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _chars_fallback()
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "rtc.db", modules.registered_schema(), modules.registered_migrations())
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

    def export(self, keys=KEYS):
        status, _headers, data = self.admin.raw_get(self.base + "/rt/export.json?sections=" + ",".join(keys))
        self.assertEqual(status, 200, data[:300])
        return json.loads(data.decode("utf-8"))

    def preview(self, doc):
        return self.admin.post(self.base + "/rt/import", {"file": json.dumps(doc, ensure_ascii=False)})

    def apply(self, doc, skip=()):
        return self.admin.post(self.base + "/rt/import", {"file": json.dumps(doc, ensure_ascii=False), "mode": "apply", "skip": list(skip)})

    def kinds(self, result, section=None):
        return [(e["code"], e["kind"]) for e in result["entries"] if section is None or e["section"] == section]

    def item(self, doc, key, code):
        return next(i for i in doc[key] if i["code"] == code)

    def page(self, path):
        return self.admin.get(self.base + path)

    # ---------------------------------------------------------------- (a) and (b)

    def test_01_dump(self):
        doc = self.export()
        self.assertEqual([i["code"] for i in doc["process_lines"]], ["L1", "L2"])
        ops = [i["code"] for i in doc["process_ops"]]
        self.assertIn("L1-OP70", ops)
        self.assertIn("L2-OP10", ops)  # OP10 on both lines: the line is in the code
        self.assertEqual(len(ops), len(set(ops)))
        op10 = self.item(doc, "process_ops", "L1-OP10")
        self.assertEqual(op10["line"], "L1")
        self.assertEqual([p["char"] for p in op10["points"]], ["C-21", "C-20", ""])
        self.assertEqual(op10["points"][2]["label"], "Certificat du lot INA219")
        self.assertEqual(len(doc["pfmea"]), 14)
        pf = self.item(doc, "pfmea", "PF-30.1")
        self.assertEqual(pf["operation"], "L1-OP30")
        self.assertTrue(pf["characteristic"].startswith("C-"))
        self.assertEqual(pf["owner"], "Nina (exemple)")
        self.assertEqual([i["code"] for i in doc["cplans"]], ["PC-1", "PC-2", "PC-3"])
        self.assertEqual(self.item(doc, "cplans", "PC-2")["line"], "L1")
        self.assertEqual(self.item(doc, "cplans", "PC-1")["line"], "")
        items = [i["code"] for i in doc["cplan_items"]]
        self.assertIn("PC-2/CP-20.1", items)
        self.assertIn("PC-3/CP-20.1", items)  # the same row code in two plans: the plan is in the code
        self.assertEqual(self.item(doc, "cplan_items", "PC-1/CP-R.4")["part"], "P-21")
        self.assertEqual(self.item(doc, "cplan_items", "PC-2/CP-30.1")["operation"], "L1-OP30")
        self.assertEqual(len(doc["costs_nre"]), 9)
        self.assertEqual(doc["costs_nre"][0]["code"], "NRE-1")
        lines = [i["code"] for i in doc["costs_lines"]]
        self.assertEqual(lines[:2], ["P-1", "P-2"])
        self.assertTrue(lines[-1].startswith("CL-"))
        self.assertEqual(self.item(doc, "costs_lines", "P-3")["part"], "P-3")
        self.assertIn("chars", doc["_context"])
        self.assertIn("parts", doc["_context"])

    def test_02_unchanged_is_same(self):
        result = self.preview(self.export())
        self.assertEqual(result["counts"]["same"], len(result["entries"]), [e for e in result["entries"] if e["kind"] != "same"][:3])
        self.assertEqual(result["warnings"], [])

    # ---------------------------------------------------------------- process

    def test_10_lines_and_operations(self):
        doc = self.export(["process_lines", "process_ops"])
        self.item(doc, "process_lines", "L2")["name"] = "Cellule prototypes (partenaire)"
        op40 = self.item(doc, "process_ops", "L1-OP40")
        op40["equipment"] = "Gabarit de joint\nPresse"
        op40["points"].append({"char": "C-14", "method": "Visuel", "frequency": "1 par heure"})
        doc["process_lines"].append({"code": "+L", "name": "Ligne série", "description": "Chez le partenaire"})
        doc["process_ops"].append({"code": "+OP", "line": "+L", "op": 10, "name": "Montage série",
                                   "points": [{"label": "Couple des vis", "method": "Clé dynamométrique", "frequency": "100 %"}]})
        doc["process_lines"].remove(self.item(doc, "process_lines", "L1"))  # lines are never removed from here
        result = self.preview(doc)
        self.assertEqual(sorted(k for _c, k in self.kinds(result) if k != "same"), ["new", "new", "update", "update"])
        self.assertNotIn("remove", [k for _c, k in self.kinds(result)])
        done = self.apply(doc)
        self.assertEqual(done["applied"], {"new": 2, "update": 2, "remove": 0})
        lines = self.page("/process")["lines"]
        self.assertEqual(lines[1]["name"], "Cellule prototypes (partenaire)")
        self.assertEqual(lines[0]["name"], "Ligne pilote — kits Rover")
        l3 = next(x for x in lines if x["code"] == "L3")
        self.assertEqual(l3["operations"][0]["op"], 10)
        self.assertEqual(l3["operations"][0]["points"][0]["label"], "Couple des vis")
        op = next(o for o in lines[0]["operations"] if o["op"] == 40)
        self.assertEqual(op["equipment_list"], ["Gabarit de joint", "Presse"])
        self.assertEqual([p["code"] or p["label"] for p in op["points"]], ["Sealing de l'enclosure", "C-14"])
        self.assertEqual(self.preview(self.export(["process_ops"]))["counts"]["same"], len(self.export(["process_ops"])["process_ops"]))

    def test_11_operation_removed(self):
        doc = self.export(["process_ops"])
        doc["process_ops"] = [i for i in doc["process_ops"] if i.get("code") != "L3-OP10"]
        result = self.preview(doc)
        self.assertEqual([c for c, k in self.kinds(result) if k == "remove"], ["L3-OP10"])
        self.apply(doc)
        self.assertEqual(next(x for x in self.page("/process")["lines"] if x["code"] == "L3")["operations"], [])

    def refused(self, doc, code):
        """The preview refuses the entry with the page's own message; applying it alone has nothing to apply."""
        entry = next(e for e in self.preview(doc)["entries"] if e["code"] == code)
        self.assertEqual(entry["kind"], "refused", entry)
        return entry["reason"]

    def test_12_operation_with_pfmea_rows_is_refused_the_rest_applied(self):
        doc = self.export(["process_lines", "process_ops"])
        self.item(doc, "process_lines", "L2")["name"] = "Cellule prototypes"
        doc["process_ops"] = [i for i in doc["process_ops"] if i.get("code") != "L1-OP30"]
        self.assertIn("PFMEA", self.refused(doc, "L1-OP30"))
        self.assertEqual(self.apply(doc)["applied"], {"new": 0, "update": 1, "remove": 0})
        lines = self.page("/process")["lines"]
        self.assertEqual(lines[1]["name"], "Cellule prototypes")
        self.assertIn(30, [o["op"] for o in lines[0]["operations"]])

    def test_13_line_of_an_operation_is_create_only(self):
        doc = self.export(["process_ops"])
        self.item(doc, "process_ops", "L1-OP70")["line"] = "L2"
        self.assertIn("ne change pas", self.refused(doc, "L1-OP70"))
        with self.assertRaises(ApiFailure) as caught:
            self.apply(doc)
        self.assertEqual(caught.exception.status, 400)  # nothing left to apply

    # ---------------------------------------------------------------- PFMEA

    def test_20_pfmea(self):
        owner = self.page("/pfmea")["members"][0]["display_name"]
        doc = self.export(["pfmea"])
        self.item(doc, "pfmea", "PF-30.1")["occurrence"] = 2
        doc["pfmea"].append({"operation": "L1-OP20", "failure_mode": "Vis oubliée", "cause": "Opérateur pressé", "cause_5m": "man",
                             "occurrence": 3, "detection": 4, "owner": owner, "action_due": "2026-12-15"})
        doc["pfmea"].append({"code": "+X", "operation": "L1-OP20", "failure_mode": "Refusée", "cause_5m": "luck", "owner": "Personne",
                             "severity": "x", "action_due": "15/12"})
        self.item(doc, "pfmea", "PF-20.2")["action_status"] = ""  # empty: back to « open », never refused
        doc["pfmea"] = [i for i in doc["pfmea"] if i.get("code") != "PF-10.1"]  # no removal from here
        result = self.preview(doc)
        kinds = [k for _c, k in self.kinds(result)]
        self.assertEqual((kinds.count("update"), kinds.count("new"), kinds.count("refused"), kinds.count("remove")), (1, 1, 1, 0))
        refused = next(e for e in result["entries"] if e["kind"] == "refused")
        for word in ("cause_5m", "owner", "severity", "action_due"):
            self.assertIn(word, refused["reason"])
        self.apply(doc)
        rows = {r["code"]: r for r in self.page("/pfmea")["rows"]}
        self.assertEqual(rows["PF-30.1"]["occurrence"], 2)
        new = next(r for r in rows.values() if r["failure_mode"] == "Vis oubliée")
        self.assertEqual((new["code"], new["state"], new["cause_5m"], new["action_owner_name"], new["action_due"]),
                         ("PF-20.5", "draft", "man", owner, "2026-12-15"))
        self.assertIn("PF-10.1", rows)
        again = self.preview(self.export(["pfmea"]))
        self.assertEqual(again["counts"]["same"], len(again["entries"]))

    def test_21_pfmea_severity_below_the_dfmea_is_refused_by_the_page(self):
        doc = self.export(["pfmea"])
        row = self.item(doc, "pfmea", "PF-30.1")
        row["severity"] = 1  # the DFMEA gives 7
        self.assertIn("sévérité vient du DFMEA", self.refused(doc, "PF-30.1"))

    # ---------------------------------------------------------------- control plans

    def test_30_control_plans_and_rows(self):
        doc = self.export(["cplans", "cplan_items"])
        self.item(doc, "cplans", "PC-3")["revision"] = "B"
        doc["cplans"].append({"code": "+PC", "title": "Production série", "scope": "assembly", "line": "L1", "phase": "production"})
        self.item(doc, "cplan_items", "PC-2/CP-30.1")["reaction_plan"] = "Arrêter, trier depuis le dernier bon contrôle"
        doc["cplan_items"].append({"plan": "+PC", "operation": "L1-OP30", "characteristic": "C-14", "technique": "Jauge",
                                   "frequency": "5 par heure"})
        doc["cplan_items"] = [i for i in doc["cplan_items"] if i.get("code") != "PC-1/CP-R.1"]
        doc["cplans"] = [i for i in doc["cplans"] if i.get("code") != "PC-1"]  # a plan is never removed from here
        result = self.preview(doc)
        self.assertEqual(sorted((c, k) for c, k in self.kinds(result) if k != "same"),
                         [("", "new"), ("+PC", "new"), ("PC-1/CP-R.1", "remove"), ("PC-2/CP-30.1", "update"), ("PC-3", "update")])
        self.assertEqual(self.apply(doc)["applied"], {"new": 2, "update": 2, "remove": 1})
        plans = {p["code"]: p for p in self.page("/cplans")["plans"]}
        self.assertEqual(plans["PC-3"]["revision"], "B")
        self.assertEqual((plans["PC-4"]["phase"], plans["PC-4"]["line_id"]), ("production", plans["PC-2"]["line_id"]))
        self.assertEqual([(i["code"], i["char_code"]) for i in plans["PC-4"]["items"]], [("CP-30.1", "C-14")])
        self.assertNotIn("CP-R.1", [i["code"] for i in plans["PC-1"]["items"]])
        row = next(i for i in plans["PC-2"]["items"] if i["code"] == "CP-30.1")
        self.assertEqual(row["reaction_plan"], "Arrêter, trier depuis le dernier bon contrôle")

    def test_31_scope_is_create_only(self):
        doc = self.export(["cplans"])
        self.item(doc, "cplans", "PC-1")["scope"] = "assembly"
        self.assertIn("ne change pas", self.refused(doc, "PC-1"))
        with self.assertRaises(ApiFailure) as caught:
            self.apply(doc)
        self.assertEqual(caught.exception.status, 400)

    # ---------------------------------------------------------------- costs

    def test_40_nre(self):
        doc = self.export(["costs_nre"])
        self.item(doc, "costs_nre", "NRE-1")["amount"] = 650
        doc["costs_nre"].append({"title": "Moule du boîtier", "category": "outillage", "phase": "C", "amount": 12000, "basis": "soumission"})
        doc["costs_nre"] = [i for i in doc["costs_nre"] if i.get("code") != "NRE-2"]
        result = self.preview(doc)
        self.assertEqual(sorted(k for _c, k in self.kinds(result) if k != "same"), ["new", "remove", "update"])
        self.apply(doc)
        nre = {"NRE-{}".format(r["number"]): r for r in self.page("/costs")["nre"]}
        self.assertEqual(nre["NRE-1"]["amount"], 650)
        self.assertNotIn("NRE-2", nre)
        self.assertEqual((nre["NRE-10"]["category"], nre["NRE-10"]["amount"]), ("outillage", 12000))

    def test_41_cost_lines(self):
        part = self.admin.post(self.base + "/structure/parts", {"name": "Câble de recharge"})
        number = next(p["number"] for p in self.page("/structure")["parts"] if p["name"] == "Câble de recharge")
        code = "P-{}".format(number)
        doc = self.export(["costs_lines"])
        self.assertTrue(part)
        self.assertEqual(self.item(doc, "costs_lines", code)["proto_unit"], "")  # a part not priced yet is on the page too
        self.item(doc, "costs_lines", code)["proto_unit"] = 9.5
        self.item(doc, "costs_lines", "P-3")["prod_1"] = 11.25
        self.item(doc, "costs_lines", "P-3")["name"] = "ignored: the name of a part is the part's"
        free = [i["code"] for i in doc["costs_lines"] if i["code"].startswith("CL-")]
        doc["costs_lines"].append({"name": "Câbles et gaines", "qty": 2, "proto_unit": 3.5})
        doc["costs_lines"] = [i for i in doc["costs_lines"] if i.get("code") not in (free[-1], "P-4")]
        result = self.preview(doc)
        self.assertEqual(sorted((c, k) for c, k in self.kinds(result) if k != "same"),
                         sorted([("", "new"), (code, "update"), ("P-3", "update"), (free[-1], "remove"), ("P-4", "remove")]))
        self.apply(doc)
        lines = {ln["code"] or ln["name"]: ln for ln in self.page("/costs")["lines"]}
        self.assertEqual(lines[code]["proto_unit"], 9.5)
        self.assertEqual(lines["P-3"]["prod_1"], 11.25)
        self.assertNotEqual(lines["P-3"]["name"], "ignored: the name of a part is the part's")
        self.assertIsNone(lines["P-4"]["id"])  # its prices cleared, the part stays
        self.assertEqual(lines["Câbles et gaines"]["qty"], 2)
        self.assertEqual(len([ln for ln in lines.values() if not ln["part_id"]]), len(free))
        again = self.preview(self.export(["costs_lines"]))
        self.assertEqual(again["counts"]["same"], len(again["entries"]))

    def test_42_part_of_a_cost_line_is_create_only(self):
        doc = self.export(["costs_lines"])
        self.item(doc, "costs_lines", "P-5")["part"] = "P-6"
        self.assertIn("ne change pas", self.refused(doc, "P-5"))
        with self.assertRaises(ApiFailure) as caught:
            self.apply(doc)
        self.assertEqual(caught.exception.status, 400)


if __name__ == "__main__":
    unittest.main()
