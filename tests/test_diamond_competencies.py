"""0.60.116 (D-O-129): Diamond -- « Compétences et équipe »: the platform's catalogue (seeded, one BDC page per competency, managed by
the administrators only), the rating 1 to 5 of each competency per function line that ends with a brick, the summary (points,
share, people to hire or gather), the « ↔ IA » round trip of the ratings, and the frozen bricks (no new concept sheet, no new Pugh
matrix, read-only fields, unfreeze with a reason). On the Rover of DEMO."""
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
from modules.diamond import data_competencies as DC  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class CompetenciesTest(unittest.TestCase):
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
        made = cls.admin.post("/api/admin/users", {"username": "editeur", "display_name": "Éditeur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "editor"})
        cls.editor = Client(cls.url)
        cls.editor.login("editeur", made["temp_password"], new_password="Edition-2026!")
        fns = cls.admin.get(cls.base + "/concepts")["functions"]
        tertiary = [f for f in fns if f["in_tree"] and f["level"] == 3]
        have = {fid for c in cls.admin.get(cls.base + "/concepts")["concepts"] for fid in c["function_ids"]}
        free = [f["id"] for f in tertiary if f["id"] not in have]
        for i, name in enumerate(("Pack Li-ion", "Microcontrôleur Wi-Fi", "Ultrasonic sensor", "Motoréducteur DC")):
            cls.admin.post(cls.base + "/concepts", {"name": name, "kind": "existing", "function_ids": free[i * 2:i * 2 + 2]})

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

    def data(self):
        return self.admin.get(self.base + "/competencies")

    def trim(self):
        from core.startup import StartupContext
        from modules.help import demo_competencies as DM
        with db.connect() as conn:
            conn.execute("DELETE FROM audit_log WHERE action = ?", (DM.TRIMMED,))
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
            counts = DM.trim_competencies(StartupContext(conn, user, Path(self.tmp.name)))
            conn.commit()
        return counts

    def test_00_rover_starts_with_the_starter_columns(self):
        """0.60.118 (D-O-131): the Rover's grid is the base of mechatronics only; a DEMO of 0.60.116 is trimmed once."""
        data = self.data()
        self.assertEqual(data["columns"], list(DC.STARTER))
        self.assertTrue(all(set(ln["ratings"]) <= set(DC.STARTER) for ln in data["lines"]))
        self.assertTrue({s["code"] for s in data["summary"] if s["people"]} <= set(DC.STARTER))
        self.assertEqual([c["code"] for c in data["catalog"] if c["starter"]], list(DC.STARTER))
        line = data["lines"][0]
        self.admin.put(self.base + "/competencies/rating", {"function_id": line["function_id"], "code": "SAFE", "rating": 4})
        self.admin.put(self.base + "/competencies/staff", {"code": "SAFE", "people": 0.5})
        self.assertEqual(self.trim(), {"ratings": 1, "staff": 1, "skipped": False})
        data = self.data()
        self.assertEqual(data["columns"], list(DC.STARTER))
        self.assertNotIn("SAFE", {s["code"] for s in data["summary"] if s["people"]})

    def test_01_catalogue_seeded_with_bdc_pages(self):
        data = self.data()
        codes = [c["code"] for c in data["catalog"]]
        self.assertEqual(codes, [d[0] for d in DC.DEFAULTS])
        self.assertTrue(data["can_manage"])
        self.assertTrue(data["bdc_hub"].startswith("#/dynamite/DEMO/page/"))
        for c in data["catalog"]:
            self.assertTrue(c["bdc"], c["code"])
            self.assertIn(c["icon"], data["icons"])
        page_id = data["catalog"][1]["bdc"].rsplit("/", 1)[1]
        page = self.admin.get("/api/dynamite/p/{}/pages/{}".format(self.pid, page_id))["page"]
        self.assertEqual(page["title"], "Compétence — Thermal analysis (THERM)")
        text = json.dumps(page["body"], ensure_ascii=False)
        for label in DC.DETAIL_LABELS.values():
            self.assertIn(label, text)
        self.assertIn("Ansys Icepak", text)

    def test_02_lines_are_the_functions_with_a_brick(self):
        data = self.data()
        self.assertTrue(data["lines"], "the Rover's tree has bricks")
        concepts = self.admin.get(self.base + "/concepts")
        linked = {fid for c in concepts["concepts"] for fid in c["function_ids"]}
        self.assertEqual({ln["function_id"] for ln in data["lines"]}, linked)
        line = data["lines"][0]
        self.assertRegex(line["code"], r"^F\d+$")
        self.assertRegex(line["brick"]["code"], r"^CB-\d+$")

    def test_03_rate_a_cell_and_summary(self):
        for ln in self.data()["lines"]:  # a clean grid (the Rover of DEMO comes with its example ratings)
            self.admin.put(self.base + "/competencies/lines/{}".format(ln["function_id"]), {"ratings": {}})
        a, b = self.data()["lines"][:2]
        self.editor.put(self.base + "/competencies/rating", {"function_id": a["function_id"], "code": "THERM", "rating": 4})
        self.editor.put(self.base + "/competencies/rating", {"function_id": a["function_id"], "code": "MECH", "rating": 2})
        data = self.editor.put(self.base + "/competencies/rating", {"function_id": b["function_id"], "code": "THERM", "rating": 5})
        row = next(s for s in data["summary"] if s["code"] == "THERM")
        self.assertEqual((row["lines"], row["points"], row["high"]), (2, 9, 2))
        self.assertEqual(data["total_points"], 11)
        self.assertAlmostEqual(row["share"], round(900 / 11, 1))
        data = self.editor.put(self.base + "/competencies/rating", {"function_id": a["function_id"], "code": "MECH", "rating": 0})
        self.assertNotIn("MECH", next(ln for ln in data["lines"] if ln["function_id"] == a["function_id"])["ratings"])
        self.assertIn("1 (presque pas", self.fails(400, self.editor.put, self.base + "/competencies/rating",
                                                   {"function_id": a["function_id"], "code": "THERM", "rating": 7}))
        self.assertIn("inconnue", self.fails(400, self.editor.put, self.base + "/competencies/rating",
                                             {"function_id": a["function_id"], "code": "NOPE", "rating": 3}))
        fns = self.admin.get(self.base + "/functions")["functions"]
        lone = next(f for f in fns if f["id"] not in {ln["function_id"] for ln in data["lines"]})
        self.assertIn("sans brique", self.fails(400, self.editor.put, self.base + "/competencies/rating",
                                                {"function_id": lone["id"], "code": "THERM", "rating": 3}))

    def test_04_people_to_hire(self):
        data = self.editor.put(self.base + "/competencies/staff", {"code": "THERM", "people": 1.5, "note": "Stage d'été"})
        row = next(s for s in data["summary"] if s["code"] == "THERM")
        self.assertEqual((row["people"], row["note"]), (1.5, "Stage d'été"))
        data = self.editor.put(self.base + "/competencies/staff", {"code": "CERT", "people": 1})
        self.assertIn("CERT", [s["code"] for s in data["summary"]])  # planned without points: still in the summary
        self.fails(400, self.editor.put, self.base + "/competencies/staff", {"code": "THERM", "people": -1})

    def test_05_catalogue_admin_only(self):
        self.assertIn("réservé", self.fails(403, self.editor.post, "/api/diamond/competencies",
                                            {"code": "EMC", "name": "EMC design", "icon": "magnet"}))
        made = self.admin.post("/api/diamond/competencies", {"code": "EMC", "name": "EMC design", "icon": "magnet",
                                                            "summary": "Tenir les essais de compatibilité électromagnétique."})
        self.assertEqual(made["created"], "EMC")
        self.fails(409, self.admin.post, "/api/diamond/competencies", {"code": "EMC", "name": "Encore", "icon": "magnet"})
        self.fails(400, self.admin.post, "/api/diamond/competencies", {"code": "X", "name": "Trop court", "icon": "magnet"})
        self.fails(400, self.admin.post, "/api/diamond/competencies", {"code": "OPT", "name": "Optics", "icon": "rocket"})
        data = self.data()
        self.assertTrue(next(c for c in data["catalog"] if c["code"] == "EMC")["bdc"])
        self.admin.patch("/api/diamond/competencies/EMC", {"name": "EMC & EMI design", "details": {"tools": "Analyseur de spectre ; LISN"}})
        data = self.data()
        emc = next(c for c in data["catalog"] if c["code"] == "EMC")
        page = self.admin.get("/api/dynamite/p/{}/pages/{}".format(self.pid, emc["bdc"].rsplit("/", 1)[1]))["page"]
        self.assertEqual(page["title"], "Compétence — EMC & EMI design (EMC)")
        self.assertIn("LISN", json.dumps(page["body"], ensure_ascii=False))
        self.admin.patch("/api/diamond/competencies/EMC", {"active": False})
        line = self.data()["lines"][0]
        self.assertIn("désactivée", self.fails(400, self.editor.put, self.base + "/competencies/rating",
                                               {"function_id": line["function_id"], "code": "EMC", "rating": 2}))

    def test_06_ai_round_trip_fills_the_grid(self):
        data = self.data()
        status, _h, raw = self.admin.raw_get(self.base + "/rt/export.json?sections=competencies")
        self.assertEqual(status, 200)
        doc = json.loads(raw)
        self.assertIn("competency_catalog", doc["_context"])
        self.assertNotIn("competency_catalog", doc)
        target = doc["competencies"][2]
        target["competencies"] = ["PCB:4", "FW:5", "SAFE:2"]
        prompt = self.admin.get(self.base + "/rt/prompt?sections=competencies")["prompt"]
        self.assertIn("CODE:note", prompt)
        bad = json.loads(json.dumps(doc))
        bad["competencies"][3]["competencies"] = ["ZZZ:3"]
        bad["competencies"].append({"code": "+F1", "competencies": ["MECH:1"]})
        preview = self.admin.post(self.base + "/rt/import", {"file": json.dumps(bad), "mode": "preview"})
        kinds = {e["code"]: e["kind"] for e in preview["entries"]}
        self.assertEqual((kinds[target["code"]], kinds[bad["competencies"][3]["code"]], kinds["+F1"]), ("update", "refused", "refused"))
        done = self.admin.post(self.base + "/rt/import", {"file": json.dumps(doc), "mode": "apply"})
        self.assertEqual(done["applied"]["update"], 1)
        line = next(ln for ln in self.data()["lines"] if ln["code"] == target["code"])
        self.assertEqual(line["ratings"], {"PCB": 4, "FW": 5, "SAFE": 2})
        sections = [s["key"] for s in self.admin.get(self.base + "/rt/sections")["sections"]]
        self.assertIn("competencies", sections)
        self.assertNotIn("competency_catalog", sections)
        self.assertTrue(len(data["lines"]) > 3)

    def test_07_frozen_brick(self):
        concepts = self.admin.get(self.base + "/concepts")["concepts"]
        brick = next(c for c in concepts if c["function_ids"])
        self.fails(400, self.editor.post, self.base + "/concepts/{}/freeze".format(brick["id"]), {"text": "  "})
        data = self.editor.post(self.base + "/concepts/{}/freeze".format(brick["id"]), {"text": "Pack Li-ion 2S, protection du commerce 5 A"})
        frozen = next(c for c in data["concepts"] if c["id"] == brick["id"])
        self.assertEqual((frozen["frozen"], frozen["status"], frozen["frozen_by_name"]), (1, "selected", "Éditeur"))
        msg = self.fails(409, self.editor.patch, self.base + "/concepts/{}".format(brick["id"]), {"name": "Autre chose"})
        self.assertIn("figée", msg)
        self.editor.patch(self.base + "/concepts/{}".format(brick["id"]), {"name": brick["name"], "owner_id": None})  # unchanged name: fine
        self.fails(409, self.editor.post, self.base + "/concepts/{}/sheets".format(brick["id"]), {"title": "Nouvelle idée", "kind": "digital"})
        self.fails(409, self.editor.post, self.base + "/pugh", {"title": "Revoir", "concept_ids": [brick["id"]]})
        self.fails(409, self.editor.post, self.base + "/concepts/{}/archive".format(brick["id"]), {})
        line = next(ln for ln in self.data()["lines"] if ln["brick"]["id"] == brick["id"])
        self.assertTrue(line["brick"]["frozen"])
        self.fails(400, self.editor.post, self.base + "/concepts/{}/unfreeze".format(brick["id"]), {})
        data = self.editor.post(self.base + "/concepts/{}/unfreeze".format(brick["id"]), {"reason": "Nouvelle cellule disponible"})
        self.assertFalse(next(c for c in data["concepts"] if c["id"] == brick["id"])["frozen"])
        self.editor.post(self.base + "/concepts/{}/sheets".format(brick["id"]), {"title": "Nouvelle idée", "kind": "digital"})
        with db.connect() as conn:
            row = conn.execute("SELECT details FROM audit_log WHERE action = 'diamond_concept_unfreeze' ORDER BY id DESC").fetchone()
        self.assertIn("Nouvelle cellule", row["details"])

    def test_09_exports(self):
        import io
        import zipfile
        for ext in ("xlsx", "docx"):
            status, headers, body = self.admin.raw_get(self.base + "/competencies/summary." + ext)
            self.assertEqual((status, body[:2]), (200, b"PK"), ext)
            self.assertIn("Competences_et_equipe", headers.get("Content-Disposition", ""))
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                text = " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".xml"))
            self.assertIn("Thermal analysis", text)
            self.assertIn("À embaucher / réunir", text)
        status, _h, body = self.admin.raw_get(self.base + "/export.xlsx")
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            self.assertIn("Compétences — synthèse", z.read("xl/workbook.xml").decode("utf-8"))
        status, _h, body = self.admin.raw_get(self.base + "/export.docx")
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            self.assertIn("Compétences et équipe", z.read("word/document.xml").decode("utf-8"))
        self.admin.put("/api/admin/features", {"features": {"diamond_competencies": False}})
        try:
            status, _h, body = self.admin.raw_get(self.base + "/export.xlsx")
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                self.assertNotIn("Compétences — synthèse", z.read("xl/workbook.xml").decode("utf-8"))
        finally:
            self.admin.put("/api/admin/features", {"features": {"diamond_competencies": True}})

    def test_10_columns_of_the_space(self):
        """0.60.117 (D-O-130): a Space keeps the 4 or 5 competencies it needs as columns of its grid."""
        data = self.data()
        rated = {c for ln in data["lines"] for c in ln["ratings"]}
        self.assertEqual(data["columns"][:5], list(DC.STARTER))  # by default: the starter set, then what the lines rate
        self.assertTrue(rated <= set(data["columns"]))
        data = self.editor.post(self.base + "/competencies/columns", {"code": "CFD"})
        self.assertEqual(data["columns"][-1], "CFD")  # a column added stays before any rating
        self.assertNotIn("CFD", rated)
        line = data["lines"][0]
        self.editor.put(self.base + "/competencies/rating", {"function_id": line["function_id"], "code": "THERM", "rating": 3})
        before = sum(1 for ln in self.data()["lines"] if "THERM" in ln["ratings"])
        data = self.editor.post(self.base + "/competencies/columns/THERM/remove", {})
        self.assertNotIn("THERM", data["columns"])
        self.assertFalse(any("THERM" in ln["ratings"] for ln in data["lines"]))
        with db.connect() as conn:
            row = conn.execute("SELECT details FROM audit_log WHERE action = 'diamond_competency_column_remove' ORDER BY id DESC").fetchone()
        self.assertIn('"ratings": {}'.format(before), row["details"])
        self.fails(404, self.editor.post, self.base + "/competencies/columns/THERM/remove", {})
        data = self.editor.post(self.base + "/competencies/columns", {"code": "THERM"})
        self.assertEqual(data["columns"][-1], "THERM")
        self.assertIn("inconnue", self.fails(400, self.editor.post, self.base + "/competencies/columns", {"code": "NOPE"}))

    def test_11_starter_set_of_a_new_space(self):
        """0.60.118 (D-O-131): a new Space starts with the starter columns; an administrator changes the set; a team that removed
        every column keeps an empty grid; a DEMO whose team chose its columns is never trimmed."""
        self.assertTrue(self.trim()["skipped"])  # test_10 chose the columns of DEMO
        self.admin.patch("/api/diamond/competencies/CFD", {"starter": True})
        try:
            made = self.admin.post("/api/admin/projects", {"key": "MEC", "name": "Mécatronique", "description": "Essai"})["project"]
            base = "/api/diamond/p/{}".format(made["id"])
            order = [d[0] for d in DC.DEFAULTS]
            self.assertEqual(self.admin.get(base + "/competencies")["columns"], [c for c in order if c in DC.STARTER + ("CFD",)])
            for code in self.admin.get(base + "/competencies")["columns"]:
                data = self.admin.post(base + "/competencies/columns/{}/remove".format(code), {})
            self.assertEqual(data["columns"], [])
            self.assertEqual(self.admin.get(base + "/competencies")["columns"], [])  # emptied by the team: stays empty
        finally:
            self.admin.patch("/api/diamond/competencies/CFD", {"starter": False})
        self.assertNotIn("CFD", [c["code"] for c in self.data()["catalog"] if c["starter"]])

    def test_08_turned_off_like_the_pfmea(self):
        self.admin.put("/api/admin/features", {"features": {"diamond_competencies": False}})
        try:
            self.fails(404, self.admin.get, self.base + "/competencies")
            self.fails(404, self.admin.post, "/api/diamond/competencies", {"code": "OPT", "name": "Optics", "icon": "eye"})
            sec = next(s for s in self.admin.get(self.base + "/rt/sections")["sections"] if s["key"] == "competencies")
            self.assertEqual(sec["count"], 0)
            self.assertFalse(self.admin.get("/api/me")["features"]["diamond_competencies"])
            self.admin.post(self.base + "/concepts", {"name": "Brique sans grille"})  # the bricks stay
        finally:
            self.admin.put("/api/admin/features", {"features": {"diamond_competencies": True}})
        self.assertTrue(self.data()["lines"])  # back on: everything is there


if __name__ == "__main__":
    unittest.main()
