"""0.30.0: « Testing » -- test base, draft procedures in the TESTING space, and the mandatory « Test Procedure »
of every Goldmine requirement (D-B-079).

    python -m unittest tests.test_lot_v019 -v
"""
import csv
import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.testing.data_procedures import PROCEDURES  # noqa: E402
from modules.testing.data_tests import TESTS  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

SPEC = ("ID;Énoncé;Catégorie;Test Procedure\r\n"
        "T-1;Le module doit tenir les vibrations.;Environnementale;tst-env-03\r\n"
        "T-2;Le module doit être bleu.;Fonctionnelle;\r\n"
        "T-3;Le module doit être rouge.;Fonctionnelle;TST-NOPE-1\r\n")


class LotV019Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = cls.cfg = load_config(cls.data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "REQ", "name": "REQ", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur tia | Tia Test | utilisateur | actif\n"
                                                                  "droit tia | REQ | editeur\n"})
        c = done["created"][0]
        cls.tia = Client(cls.url)
        cls.tia.login(c["username"], c["temp_password"], "Essai-Lot-DixNeuf-2026!")
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["REQ"]
        cls.base = "/api/agile/p/{}".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status
        return 200

    def test_01_space_base_and_procedures(self):
        data = self.tia.get("/api/testing/tests")  # tia joins TESTING as an editor on first use
        self.assertEqual(len([t for t in data["tests"] if t["origin"] != "example"]), len(TESTS))  # 0.60.49: + the Rover's tests in DEMO
        self.assertTrue(data["can_edit"])
        ids = {t["test_id"]: t for t in data["tests"]}
        self.assertEqual(ids["TST-ENV-03"]["standard"], "IEC 60068-2-6")
        self.assertIn("Vibration", ids["TST-ENV-03"]["section"])
        self.assertEqual(ids["TST-CUS-01"]["category"], "custom")
        self.assertEqual(ids["TST-CUS-01"]["status"], "Draft")
        self.assertTrue(all(t["procedure"] for t in data["tests"]))  # every subject has its procedure page
        tpid = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}["DEMO"]
        titles = {p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(tpid))["pages"]}
        self.assertIn("Testing — Test Procedures", titles)
        self.assertEqual(sum(1 for t in titles if t.startswith("PRC-")), len(PROCEDURES))
        page = self.admin.get("/api/dynamite/p/{}/pages/{}".format(tpid, ids["TST-ENV-03"]["procedure"]["id"]))["page"]
        self.assertIn("#/testing/test/TST-ENV-03", str(page["body"]))

    def test_02_requirement_needs_a_test(self):
        url = self.base + "/goldmine/requirements"
        with self.assertRaises(ApiFailure) as ctx:
            self.tia.post(url, {"statement": "Le module doit tenir 3000 cycles."})
        self.assertIn("Test Procedure", ctx.exception.message)
        self.assertEqual(self.status(lambda: self.tia.post(url, {"statement": "x", "test_ref": "TST-NOPE-9"})), 400)
        made = self.tia.post(url, {"statement": "Le module doit tenir 3000 cycles.", "test_ref": "tst-lif-01; TST-ELE-01"})
        need = self.tia.post(url, {"statement": "Les utilisateurs ont besoin d'autonomie.", "kind": "need"})  # a need: no test
        items = {r["key"]: r for r in self.tia.get(self.base + "/goldmine")["requirements"]}
        self.assertEqual(items[made["key"]]["test_ref"], "TST-LIF-01, TST-ELE-01")
        self.assertEqual(items[need["key"]]["test_ref"], "")
        put = self.base + "/issues/{}/requirement".format(made["number"])
        self.assertEqual(self.status(lambda: self.tia.put(put, {"test_ref": ""})), 400)  # cannot remove the last test
        self.tia.put(put, {"test_ref": "TST-LIF-01"})
        record = self.tia.get("/api/testing/tests/TST-LIF-01")
        self.assertIn(made["key"], [r["key"] for r in record["requirements"]])

    def test_03_old_requirement_and_obsolete_test(self):
        url = self.base + "/goldmine/requirements"
        made = self.admin.post(url, {"statement": "Le module doit être gris.", "test_ref": "TST-VER-01"})
        with db.connect() as conn:  # a requirement saved before 0.30 (no test)
            conn.execute("UPDATE agile_requirements SET test_ref = '' WHERE issue_id = (SELECT id FROM agile_issues "
                         "WHERE project_id = ? AND number = ?)", (self.pid, made["number"]))
        put = self.base + "/issues/{}/requirement".format(made["number"])
        self.assertEqual(self.status(lambda: self.admin.put(put, {"rationale": "Parce que."})), 400)
        gaps = self.admin.get(self.base + "/goldmine")["gaps"]
        self.assertIn(made["key"], gaps["no_test"])
        self.admin.patch("/api/testing/tests/TST-VER-04?space=REQ", {"status": "Obsolete"})
        self.assertEqual(self.status(lambda: self.admin.put(put, {"test_ref": "TST-VER-04"})), 400)
        self.admin.put(put, {"test_ref": "TST-VER-01", "rationale": "Parce que."})
        self.admin.patch("/api/testing/tests/TST-VER-01?space=REQ", {"status": "Obsolete"})
        self.admin.put(put, {"rationale": "Toujours."})  # an obsolete test already chosen does not block other edits
        self.admin.patch("/api/testing/tests/TST-VER-01?space=REQ", {"status": "In Review"})
        self.admin.patch("/api/testing/tests/TST-VER-04?space=REQ", {"status": "In Review"})

    def test_04_csv_import_and_export(self):
        res = self.admin.post(self.base + "/import/requirements", {"csv": SPEC})
        by_row = {r["line"]: r for r in res["report"]}
        self.assertEqual(by_row[2]["status"], "créée")
        self.assertEqual(by_row[3]["status"], "refusée")
        self.assertIn("Test Procedure", by_row[3]["reason"])
        self.assertEqual(by_row[4]["status"], "refusée")
        with self.admin.opener.open(self.url + self.base + "/export/requirements") as resp:
            rows = list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))
        self.assertIn("test_ref", rows[0])
        self.assertEqual([r["test_ref"] for r in rows if r["external_id"] == "T-1"], ["TST-ENV-03"])

    def test_05_create_edit_and_catalogue_follow_up(self):
        made = self.tia.post("/api/testing/tests", {"title": "Chute du chariot", "subject": "mech"})
        self.assertRegex(made["test_id"], r"^TST-MEC-\d\d$")  # 0.60.49: after the Rover's tests in DEMO
        self.assertEqual(self.status(lambda: self.tia.post("/api/testing/tests", {"title": "x", "subject": "mech",
                                                                                   "test_id": made["test_id"]})), 409)
        self.tia.patch("/api/testing/tests/TST-ENV-02", {"notes": "Moyens : laboratoire externe."})
        with db.connect() as conn:  # the code changed the catalogue: TST-ENV-01 not edited, TST-ENV-02 edited
            conn.execute("UPDATE testing_tests SET title = 'ancien' WHERE test_id IN ('TST-ENV-02', 'TST-ENV-01')")
        startup.run(self.data_dir, self.cfg)
        tests = {t["test_id"]: t for t in self.tia.get("/api/testing/tests")["tests"]}
        self.assertEqual(tests["TST-ENV-01"]["title"], "Storage and operation at the temperature extremes")
        self.assertEqual(tests["TST-ENV-02"]["title"], "ancien")  # the team's version is kept
        rec = self.tia.get("/api/testing/tests/TST-ENV-02")
        self.assertTrue(rec["history"])
        with db.connect() as conn:
            conn.execute("UPDATE memberships SET role = 'reader' WHERE user_id = (SELECT id FROM users WHERE username = 'tia') "
                         "AND project_id = (SELECT id FROM projects WHERE key = 'DEMO')")
        self.assertEqual(self.status(lambda: self.tia.patch("/api/testing/tests/TST-ENV-02", {"notes": "x"})), 403)
        with db.connect() as conn:
            conn.execute("UPDATE memberships SET role = 'editor' WHERE user_id = (SELECT id FROM users WHERE username = 'tia') "
                         "AND project_id = (SELECT id FROM projects WHERE key = 'DEMO')")

    def test_06_csv_round_trip_of_the_base(self):
        with self.admin.opener.open(self.url + "/api/testing/export.csv?ids=TST-MEC-01,TST-MEC-02") as resp:
            rows = list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))
        self.assertEqual([r["test_id"] for r in rows], ["TST-MEC-01", "TST-MEC-02"])
        rows[0]["means"] = "Laboratoire de chute"
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        preview = self.admin.post("/api/testing/import", {"csv": buf.getvalue(), "mode": "preview"})
        self.assertEqual([r["status"] for r in preview["report"]], ["mis à jour", "inchangé"])
        self.assertEqual(self.admin.get("/api/testing/tests/TST-MEC-01")["test"]["means"], "")  # preview wrote nothing
        self.admin.post("/api/testing/import", {"csv": buf.getvalue(), "mode": "apply"})
        self.assertEqual(self.admin.get("/api/testing/tests/TST-MEC-01")["test"]["means"], "Laboratoire de chute")

    def test_07_search_and_baselines(self):
        res = self.tia.get("/api/search?q=vibration&types=test")
        self.assertIn("TST-ENV-03 · Transport vibration", [r["title"] for r in res["results"]])
        known = {t[0] for t in TESTS}
        for name in ("requis_generiques.csv",):
            rows = list(csv.DictReader(io.StringIO((BASE_DIR / "deploy" / name).read_text(encoding="utf-8-sig"))))
            reqs = [r for r in rows if r["kind"] in ("Requirement", "requirement")]
            self.assertTrue(reqs)
            for r in reqs:
                refs = [x for x in r["test_ref"].split(", ") if x]
                self.assertTrue(refs, (name, r["external_id"]))
                self.assertTrue(set(refs) <= known, (name, r["external_id"], refs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
