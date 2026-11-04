"""Core lot v0.5 (D-B-012): creating a project prepares it in every tab --
Dynamite home page named after the project, Agile with Change Management,
Goldmine requirements -- in one transaction.

    python -m unittest tests.test_project_provisioning -v
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


class ProvisioningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "p.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_new_project_is_ready_everywhere(self):
        pid = self.admin.post("/api/admin/projects", {"key": "PRO", "name": "Prototype 2027",
                                                      "description": ""})["project"]["id"]
        agile = "/api/agile/p/{}".format(pid)
        self.assertTrue(self.admin.get(agile + "/meta")["enabled"])
        self.assertTrue(self.admin.get(agile + "/goldmine")["enabled"])
        changes = self.admin.get(agile + "/changes")
        self.assertTrue(changes["enabled"])
        self.assertEqual(sorted(changes["types"]), ["bug", "ecn", "ecn_task", "pr"])
        pages = self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]
        self.assertEqual([p["title"] for p in pages], ["Prototype 2027"])
        body = self.admin.get("/api/dynamite/p/{}/pages/{}".format(pid, pages[0]["id"]))["page"]["body"]
        kinds = {b["type"] for b in body["content"]}
        self.assertTrue({"toc", "table", "children", "panel"} <= kinds)
        # Agile types stay Agile work; no fictitious tickets in a real project.
        self.assertEqual(self.admin.get(agile + "/issues?bucket=all")["issues"], [])
        # Manual activation buttons now answer "already enabled".
        with self.assertRaises(ApiFailure) as ctx:
            self.admin.post(agile + "/init")
        self.assertEqual(ctx.exception.status, 409)

    def test_bare_project_on_request(self):
        pid = self.admin.post("/api/admin/projects", {"key": "RAW", "name": "Brut", "provision": False})["project"]["id"]
        self.assertFalse(self.admin.get("/api/agile/p/{}/meta".format(pid))["enabled"])
        self.assertEqual(self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"], [])


if __name__ == "__main__":
    unittest.main()
