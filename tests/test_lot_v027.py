"""0.37.0: Training (D-A-045) -- topics, plans, workflow with different rights, Markdown tests graded on the server.

    python -m unittest tests.test_lot_v027 -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.training import catalog, quiz  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV027Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur tom | Tom | utilisateur | actif\n"
                                                                  "utilisateur ana | Ana | utilisateur | actif\n"})
        clients = {}
        for c in done["created"]:
            clients[c["username"]] = Client(url)
            clients[c["username"]].login(c["username"], c["temp_password"], "Essai-Formation-Plateforme-2026!")
        cls.tom, cls.ana = clients["tom"], clients["ana"]
        cls.ana_id = cls.ana.get("/api/me")["user"]["id"]
        cls.tom_id = cls.tom.get("/api/me")["user"]["id"]
        cls.tom.put("/api/me/prefs", {"manager_id": cls.ana_id})

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

    def test_01_topics_seeded(self):
        topics = self.tom.get("/api/training/topics")
        codes = {t["code"]: t for t in topics["topics"]}
        self.assertIn("HL-01", codes)
        self.assertEqual(codes["HL-09"]["reference"], "#/help/timesheet")
        self.assertTrue(codes["HL-09"]["has_quiz"])
        self.assertFalse(topics["can_manage"])
        self.assertNotIn("quiz_md", codes["HL-09"])  # answers never sent to the employee

    def test_02_plan_workflow_and_test(self):
        hl09 = next(t for t in self.tom.get("/api/training/topics")["topics"] if t["code"] == "HL-09")
        iid = self.tom.post("/api/training/plan/{}/items".format(self.tom_id), {"topic_id": hl09["id"]})["id"]
        self.assertEqual(self.status(lambda: self.tom.post("/api/training/plan/{}/items".format(self.tom_id),
                                                           {"topic_id": hl09["id"]})), 409)
        self.assertEqual(self.status(lambda: self.admin.get("/api/training/plan/{}".format(self.tom_id))), 403)
        self.tom.patch("/api/training/items/{}".format(iid), {"status": "in_progress"})
        self.assertEqual(self.status(lambda: self.tom.patch("/api/training/items/{}".format(iid), {"status": "achieved"})), 400)
        # 0.50.10 (D-B-128): a topic with a test becomes Completed by passing it, not by the button
        self.assertEqual(self.status(lambda: self.tom.patch("/api/training/items/{}".format(iid), {"status": "completed"})), 409)
        public = self.tom.get("/api/training/items/{}/quiz".format(iid))
        self.assertNotIn("right", str(public))
        with db.connect() as conn:
            parsed = quiz.checked(conn.execute("SELECT quiz_md FROM training_topics WHERE code = 'HL-09'").fetchone()[0])
        good = {str(i): [j for j, o in enumerate(q["options"]) if o["right"]] for i, q in enumerate(parsed["questions"])}
        result = self.tom.post("/api/training/items/{}/quiz".format(iid), {"answers": good})
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.status(lambda: self.ana.post("/api/training/items/{}/quiz".format(iid), {"answers": good})), 403)
        self.assertEqual(self.status(lambda: self.ana.patch("/api/training/items/{}".format(iid), {"status": "achieved"})), 409)
        self.assertEqual(self.status(lambda: self.tom.patch("/api/training/items/{}".format(iid), {"manager_eval": "x"})), 403)
        self.ana.patch("/api/training/items/{}".format(iid), {"manager_eval": "Maîtrise la saisie et la soumission."})
        self.ana.patch("/api/training/items/{}".format(iid), {"status": "achieved"})
        item = self.tom.get("/api/training/plan/{}".format(self.tom_id))["items"][0]
        self.assertEqual(item["status"], "achieved")
        self.assertEqual(item["quiz_attempts"], 1)
        self.assertEqual(self.status(lambda: self.tom.post("/api/training/items/{}/quiz".format(iid), {"answers": good})), 409)
        self.assertEqual(self.status(lambda: self.tom.del_("/api/training/items/{}".format(iid))
                                     if hasattr(self.tom, "del_") else self.tom.delete("/api/training/items/{}".format(iid))), 409)

    def test_03_admin_topics_and_workflow(self):
        bad = "## Question sans bonne réponse\n- [ ] a\n- [ ] b\nligne libre\n"
        with self.assertRaises(ApiFailure) as ctx:
            self.admin.post("/api/training/topics", {"title": "IEC 60068", "quiz_md": bad})
        self.assertIn("aucune bonne réponse", str(ctx.exception))
        self.assertIn("non reconnue", str(ctx.exception))
        made = self.admin.post("/api/training/topics", {"code": "IEC68", "title": "IEC 60068", "quiz_md": catalog.EXAMPLE_QUIZ})
        self.assertTrue(made["id"])
        self.assertEqual(self.status(lambda: self.tom.post("/api/training/topics", {"title": "x"})), 403)
        self.assertEqual(self.admin.post("/api/training/quiz-check", {"quiz_md": catalog.EXAMPLE_QUIZ})["questions"], 5)
        rules = self.admin.get("/api/training/workflow")["rules"]
        self.assertEqual(self.status(lambda: self.tom.put("/api/training/workflow", {"rules": rules})), 403)
        no_manager = [[a, b, c, [r for r in roles if r != "manager"] if b == "achieved" else roles] for a, b, c, roles in rules]
        self.assertEqual(self.status(lambda: self.admin.put("/api/training/workflow", {"rules": no_manager})), 400)
        self.admin.put("/api/training/workflow", {"rules": rules})


if __name__ == "__main__":
    unittest.main(verbosity=2)
