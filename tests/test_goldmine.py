"""Goldmine: requirement type, dedicated workflow, fields, trace gaps,
verification guard (D-A-032).

    python -m unittest tests.test_goldmine -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class GoldmineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "g.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        for key in ("DEMOREQ", "DEMO"):
            cls.admin.post("/api/admin/projects", {"provision": False, "key": key, "name": key, "description": ""})
        ids = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.req = "/api/agile/p/{}".format(ids["DEMOREQ"])
        cls.demo = "/api/agile/p/{}".format(ids["DEMO"])
        for base in (cls.req, cls.demo):
            cls.admin.post(base + "/init")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, func, *args):
        with self.assertRaises(ApiFailure) as ctx:
            func(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)
        return ctx.exception.message

    def step(self, number, name):
        issue = self.admin.get(self.req + "/issues/{}".format(number))["issue"]
        t = next(t for t in issue["transitions"] if t["to_name"] == name)
        return self.admin.post(self.req + "/issues/{}/transition".format(number), {"transition_id": t["id"]})

    def test_01_setup_creates_type_and_workflow(self):
        self.assertFalse(self.admin.get(self.req + "/goldmine")["enabled"])
        self.admin.post(self.req + "/goldmine/setup")
        meta = self.admin.get(self.req + "/meta")
        wf = next(w for w in meta["workflows"] if w["name"] == "Requirement Workflow")
        names = [s["name"] for s in meta["statuses"] if s["workflow_id"] == wf["id"]]
        self.assertEqual(names[0], "Received")
        self.assertIn("Verified", names)
        self.assertIn("Goldmine est déjà activé", self.fails(409, self.admin.post, self.req + "/goldmine/setup"))

    def test_02_create_with_fields_and_validation(self):
        msg = self.fails(400, self.admin.post, self.req + "/goldmine/requirements", {"statement": ""})
        self.assertIn("Le système doit", msg)
        msg = self.fails(400, self.admin.post, self.req + "/goldmine/requirements",
                         {"statement": "Le produit doit couper à 55 °C.", "verification_method": "TX"})
        self.assertIn("IADT", msg)
        created = self.admin.post(self.req + "/goldmine/requirements", {
            "title": "Coupure thermique", "statement": "Le produit doit couper la charge au-delà de 55 °C.",
            "external_id": "SYS-045", "category": "safety", "criticality": "b",
            "verification_method": "t,a", "source_doc": "Spec client rév. B §4.2.1"})
        self.assertEqual(created["key"], "DEMOREQ-1")
        req = self.admin.get(self.req + "/issues/1")["issue"]["requirement"]
        self.assertEqual((req["criticality"], req["verification_method"]), ("B", "AT"))

    def test_03_trace_gaps_and_verification_guard(self):
        for name in ("In Analysis", "Accepted"):
            self.step(1, name)
        gaps = self.admin.get(self.req + "/goldmine")["gaps"]
        self.assertIn("DEMOREQ-1", gaps["no_implementation"])
        self.assertIn("DEMOREQ-1", gaps["no_acceptance"])
        task = next(t for t in self.admin.get(self.demo + "/meta")["types"] if t["icon_key"] == "task")
        work = self.admin.post(self.demo + "/issues", {"type_id": task["id"], "title": "Seuil de la buse"})
        self.admin.post(self.demo + "/issues/{}/links".format(work["number"]),
                        {"link_type": "implements", "target_key": "DEMOREQ-1"})
        listing = self.admin.get(self.req + "/goldmine")
        self.assertEqual(listing["requirements"][0]["implemented_by"], [work["key"]])
        self.assertNotIn("DEMOREQ-1", listing["gaps"]["no_implementation"])
        for name in ("Allocated", "Implemented", "In Verification"):
            self.step(1, name)
        issue = self.admin.get(self.req + "/issues/1")["issue"]
        verified = next(t for t in issue["transitions"] if t["to_name"] == "Verified")
        msg = self.fails(409, self.admin.post, self.req + "/issues/1/transition", {"transition_id": verified["id"]})
        self.assertIn("Verification Ref.", msg)
        self.assertIn("Correctif", msg)
        self.admin.put(self.req + "/issues/1/requirement", {"verification_ref": "TP-PRD-012 rév. A",
                                                             "acceptance_criteria": "Coupure < 55,5 °C sur 3 essais"})
        self.admin.post(self.req + "/issues/1/transition", {"transition_id": verified["id"]})
        self.assertEqual(self.admin.get(self.req + "/issues/1")["issue"]["status_name"], "Verified")
        history = self.admin.get(self.req + "/issues/1")["issue"]["history"]
        self.assertTrue(any(h["field"] == "req:Verification Ref." for h in history))

    def test_04_not_a_requirement(self):
        task = next(t for t in self.admin.get(self.demo + "/meta")["types"] if t["icon_key"] == "task")
        work = self.admin.post(self.demo + "/issues", {"type_id": task["id"], "title": "Pas une exigence"})
        msg = self.fails(400, self.admin.put, self.demo + "/issues/{}/requirement".format(work["number"]),
                         {"external_id": "X"})
        self.assertIn("n'est pas un requirement", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
