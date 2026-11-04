"""0.35.2: Exploration edit mode (D-A-041) -- a new task joins the end of its phase, explicit position, whole-plan
reorder with phase changes (administrators only, stale order refused).

    python -m unittest tests.test_lot_v024 -v
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
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV024Test(unittest.TestCase):
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
        cls.admin.post("/api/admin/projects", {"key": "EXP", "name": "EXP", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur tom | Tom Test | utilisateur | actif\n"
                                                                  "droit tom | EXP | editeur\n"})
        c = done["created"][0]
        cls.tom = Client(url)
        cls.tom.login(c["username"], c["temp_password"], "Essai-Exploration-2026!")
        pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["EXP"]
        cls.base = "/api/exploration/p/{}".format(pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def tasks(self):
        return [(t["code"], t["phase"]) for t in self.admin.get(self.base + "/plan")["tasks"]]

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status
        return 200

    def test_edit_mode(self):
        for t in self.admin.get(self.base + "/plan")["tasks"]:  # the kick-off milestone of a new Space
            self.admin.delete(self.base + "/tasks/{}".format(t["id"]))
        for code, phase in (("A1", "Concept"), ("A2", "Concept"), ("B1", "Design"), ("B2", "Design")):
            self.admin.post(self.base + "/tasks", {"code": code, "title": code, "phase": phase})
        self.admin.post(self.base + "/tasks", {"code": "A3", "title": "A3", "phase": "Concept"})  # joins its phase
        self.admin.post(self.base + "/tasks", {"code": "Z0", "title": "Z0", "phase": "Design", "position": 0})  # explicit
        self.assertEqual([c for c, _ in self.tasks()], ["Z0", "A1", "A2", "A3", "B1", "B2"])
        plan = self.admin.get(self.base + "/plan")["tasks"]
        ids = {t["code"]: t["id"] for t in plan}
        order = [{"id": ids[c], "phase": p} for c, p in (("A1", "Concept"), ("A2", "Concept"), ("A3", "Concept"),
                                                          ("Z0", "Design"), ("B2", "Design"), ("B1", "Validation"))]
        res = self.admin.put(self.base + "/plan/order", {"order": order})
        self.assertEqual(res["phase_changed"], ["B1"])
        self.assertEqual(self.tasks(), [("A1", "Concept"), ("A2", "Concept"), ("A3", "Concept"), ("Z0", "Design"),
                                        ("B2", "Design"), ("B1", "Validation")])
        self.assertEqual(self.status(lambda: self.tom.put(self.base + "/plan/order", {"order": order})), 403)
        self.assertEqual(self.status(lambda: self.admin.put(self.base + "/plan/order", {"order": order[:-1]})), 409)
        self.assertEqual(self.status(lambda: self.admin.put(self.base + "/plan/order", {"order": "x"})), 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
