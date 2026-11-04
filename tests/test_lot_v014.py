"""0.24.0: Pugh matrix in Goldmine (D-B-062), identifiers never reused
(D-B-061): retired Space keys, Exploration counter, requirements never
deleted; generic requirements catalogue synchronised by external ID (D-B-060).

    python -m unittest tests.test_lot_v014 -v
"""
import io
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV014Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.put("/api/me/prefs", {"initials": "ADM"})
        cls.admin.post("/api/admin/projects", {"key": "PRJ", "name": "PRJ", "description": ""})
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["PRJ"]
        cls.base = "/api/agile/p/{}".format(cls.pid)
        if not cls.admin.get(cls.base + "/goldmine").get("enabled"):
            cls.admin.post(cls.base + "/goldmine/setup")
        text = (BASE_DIR / "deploy" / "requis_generiques.csv").read_text(encoding="utf-8-sig")
        cls.admin.post(cls.base + "/import/requirements", {"csv": text})
        cls.reqs = {r["external_id"]: r for r in cls.admin.get(cls.base + "/goldmine")["requirements"]}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fail_status(self, call):
        with self.assertRaises(ApiFailure) as err:
            call()
        return err.exception.status

    # ---------------- D-B-062: Pugh ----------------
    def test_01_pugh_matrix(self):
        url = self.base + "/pugh"
        m = self.admin.post(url, {"title": "Fixation", "concepts": ["A vis", "B rails", "C colle"]})
        mid = m["matrix"]["id"]
        concepts = {c["name"][0]: c["id"] for c in m["concepts"]}
        self.assertEqual(m["matrix"]["datum_id"], concepts["A"])  # the first concept is the reference
        d = self.admin.patch(url + "/{}".format(mid), {"datum_id": concepts["A"]})
        self.assertEqual(d["matrix"]["datum_id"], concepts["A"])
        d = self.admin.post(url + "/{}/criteria".format(mid), {"numbers": [self.reqs["GR-029"]["number"],
                                                                           self.reqs["GR-005"]["number"]]})
        self.assertEqual(d["added"], 2)
        d = self.admin.post(url + "/{}/criteria".format(mid), {"lifecycle": "end_of_life"})
        n_eol = sum(1 for r in self.reqs.values() if r["lifecycle"] == "end_of_life")
        self.assertEqual(len(d["criteria"]), 2 + n_eol)
        again = self.admin.post(url + "/{}/criteria".format(mid), {"lifecycle": "end_of_life"})
        self.assertEqual(again["added"], 0)  # no duplicates
        crit = d["criteria"]
        for k in crit:
            self.admin.put(url + "/{}/score".format(mid), {"criterion_id": k["id"], "concept_id": concepts["B"], "score": "+"})
        self.admin.put(url + "/{}/score".format(mid), {"criterion_id": crit[0]["id"], "concept_id": concepts["C"], "score": "-",
                                                      "note": "Colle : pas de reprise possible"})
        d = self.admin.put(url + "/{}/score".format(mid), {"criterion_id": crit[1]["id"], "concept_id": concepts["C"], "score": "S"})
        t = d["totals"]
        self.assertEqual((t[str(concepts["B"])]["plus"], t[str(concepts["B"])]["net"], t[str(concepts["B"])]["rank"]),
                         (len(crit), len(crit), 1))
        self.assertEqual((t[str(concepts["C"])]["minus"], t[str(concepts["C"])]["same"], t[str(concepts["C"])]["net"]), (1, 1, -1))
        self.assertEqual(t[str(concepts["A"])]["same"], len(crit))  # the datum is S by definition
        self.assertEqual(self.fail_status(lambda: self.admin.put(url + "/{}/score".format(mid), {
            "criterion_id": crit[0]["id"], "concept_id": concepts["A"], "score": "+"})), 400)
        self.assertEqual(self.fail_status(lambda: self.admin.put(url + "/{}/score".format(mid), {
            "criterion_id": crit[0]["id"], "concept_id": concepts["B"], "score": "++"})), 400)
        # Excel export
        status, _h, data = self.admin.raw_get(url + "/{}/export.xlsx".format(mid))
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("COUNTIF(", sheet)
        self.assertIn(self.reqs["GR-029"]["key"], sheet)
        # decide -> read-only; reopen
        self.admin.patch(url + "/{}".format(mid), {"status": "decided", "decision_concept_id": concepts["B"],
                                                   "decision_note": "Meilleur net, démontable."})
        self.assertEqual(self.fail_status(lambda: self.admin.post(url + "/{}/concepts".format(mid), {"name": "D"})), 409)
        # new round around B, C dropped
        r2 = self.admin.post(url + "/{}/round".format(mid), {"datum_id": concepts["B"], "keep": [concepts["A"], concepts["B"]]})
        self.assertEqual((r2["matrix"]["round"], len(r2["concepts"]), len(r2["criteria"]), len(r2["scores"])), (2, 2, len(crit), 0))
        self.assertEqual(next(c["name"] for c in r2["concepts"] if c["id"] == r2["matrix"]["datum_id"]), "B rails")
        listing = self.admin.get(url)["matrices"]
        self.assertEqual(len(listing), 2)
        actions = [e["action"] for e in self.admin.get("/api/admin/audit?limit=80")["entries"]]
        for a in ("pugh_create", "pugh_score", "pugh_round", "pugh_export"):
            self.assertIn(a, actions)

    # ---------------- D-B-061: identifiers never reused ----------------
    def test_02_requirement_never_deleted(self):
        number = self.reqs["GR-035"]["number"]
        self.assertEqual(self.fail_status(lambda: self.admin.delete(self.base + "/issues/{}".format(number))), 409)

    def test_03_retired_space_key(self):
        self.admin.post("/api/admin/projects", {"key": "OLD", "name": "Ancien", "description": ""})
        pid = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}["OLD"]
        self.admin.patch("/api/admin/projects/{}".format(pid), {"is_archived": True})
        res = self.admin.post("/api/admin/projects/{}/delete".format(pid), {"confirm_key": "OLD"})
        self.assertEqual(self.fail_status(lambda: self.admin.post("/api/admin/projects", {
            "key": "OLD", "name": "Nouveau", "description": ""})), 409)
        restored = self.admin.post("/api/admin/backups/{}/restore".format(res["backup"]), {})  # the Space itself comes back
        self.assertEqual(restored["project"]["key"], "OLD")

    def test_04_exploration_codes_not_reused(self):
        url = "/api/exploration/p/{}".format(self.pid)
        t1 = self.admin.post(url + "/tasks", {"title": "Essai 1"})
        t2 = self.admin.post(url + "/tasks", {"title": "Essai 2"})
        code2 = (t2.get("task") or t2)["code"]
        self.admin.delete(url + "/tasks/{}".format((t2.get("task") or t2)["id"]))
        t3 = self.admin.post(url + "/tasks", {"title": "Essai 3"})
        self.assertNotEqual((t3.get("task") or t3)["code"], code2)
        self.assertNotEqual((t3.get("task") or t3)["code"], (t1.get("task") or t1)["code"])

    # ---------------- D-B-060: catalogue re-import updates by external ID ----------------
    def test_05_catalogue_sync(self):
        text = (BASE_DIR / "deploy" / "requis_generiques.csv").read_text(encoding="utf-8-sig")
        before = len(self.admin.get(self.base + "/goldmine")["requirements"])
        self.admin.post(self.base + "/import/requirements", {"csv": text})
        reqs = self.admin.get(self.base + "/goldmine")["requirements"]
        self.assertEqual(len(reqs), before)
        self.assertTrue(all(r["lifecycle"] for r in reqs if r["external_id"].startswith("GR-")))


if __name__ == "__main__":
    unittest.main()
