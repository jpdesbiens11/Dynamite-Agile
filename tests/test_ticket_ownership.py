"""D-B-017: a ticket is edited only by its assignee (or an administrator);
other editors comment and may take an unassigned ticket; the history keeps
a lightweight trace.

    python -m unittest tests.test_ticket_ownership -v
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

RULES = """
utilisateur alice | Alice Test | utilisateur | actif
utilisateur bruno | Bruno Test | utilisateur | actif
utilisateur lea   | Léa Test   | utilisateur | actif
droit alice | OWN | editeur
droit bruno | OWN | editeur
droit lea   | OWN | lecteur
"""


class OwnershipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "o.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "OWN", "name": "Own", "description": ""})
        pid = cls.admin.get("/api/admin/projects")["projects"][0]["id"]
        cls.base = "/api/agile/p/{}".format(pid)
        cls.admin.post(cls.base + "/init")
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        temps = {c["username"]: c["temp_password"] for c in done["created"]}
        cls.users = {u["username"]: u["id"] for u in cls.admin.get("/api/admin/users")["users"]}
        cls.clients = {}
        for name in ("alice", "bruno", "lea"):
            client = Client(cls.url)
            client.login(name, temps[name], "Essai-Propriete-2026!")
            cls.clients[name] = client
        cls.task_type = next(t["id"] for t in cls.admin.get(cls.base + "/meta")["types"] if t["icon_key"] == "task")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def issue(self, client, number):
        return client.get(self.base + "/issues/{}".format(number))["issue"]

    def test_1_editor_creates_owns(self):
        alice, bruno = self.clients["alice"], self.clients["bruno"]
        n = alice.post(self.base + "/issues", {"type_id": self.task_type, "title": "Boîtier A"})["number"]
        mine = self.issue(alice, n)
        self.assertEqual(mine["assignee_id"], self.users["alice"])
        self.assertTrue(mine["can_edit"])
        alice.patch(self.base + "/issues/{}".format(n), {"title": "Boîtier A rév. 1"})
        # Bruno: read + comment, never edit.
        seen = self.issue(bruno, n)
        self.assertFalse(seen["can_edit"])
        self.assertFalse(seen["can_take"])
        self.assertEqual(seen["transitions"], [])
        for call in (lambda: bruno.patch(self.base + "/issues/{}".format(n), {"title": "x"}),
                     lambda: bruno.patch(self.base + "/issues/{}".format(n), {"assignee_id": self.users["bruno"]}),
                     lambda: bruno.put(self.base + "/issues/{}/labels".format(n), {"labels": ["x"]}),
                     lambda: bruno.put(self.base + "/issues/{}/summary".format(n), {"client_summary": "x"}),
                     lambda: bruno.post(self.base + "/issues/{}/transition".format(n),
                                        {"transition_id": mine["transitions"][0]["id"]})):
            with self.assertRaises(ApiFailure) as caught:
                call()
            self.assertEqual(caught.exception.status, 403)
        bruno.post(self.base + "/issues/{}/comments".format(n), {"body": "Avis de Bruno"})
        # Handing the ticket over moves the right with it.
        alice.patch(self.base + "/issues/{}".format(n), {"assignee_id": self.users["bruno"]})
        self.assertTrue(self.issue(bruno, n)["can_edit"])
        self.assertFalse(self.issue(alice, n)["can_edit"])

    def test_2_take_unassigned(self):
        n = self.admin.post(self.base + "/issues", {"type_id": self.task_type, "title": "Libre"})["number"]
        bruno, lea = self.clients["bruno"], self.clients["lea"]
        self.assertTrue(self.issue(bruno, n)["can_take"])
        self.assertFalse(self.issue(lea, n)["can_take"])  # readers never take
        with self.assertRaises(ApiFailure):
            bruno.patch(self.base + "/issues/{}".format(n), {"title": "avant de prendre"})
        bruno.patch(self.base + "/issues/{}".format(n), {"assignee_id": self.users["bruno"]})
        bruno.patch(self.base + "/issues/{}".format(n), {"title": "Pris par Bruno"})
        # Admin keeps full control.
        self.admin.patch(self.base + "/issues/{}".format(n), {"priority": "high"})

    def test_3_light_history(self):
        alice = self.clients["alice"]
        n = alice.post(self.base + "/issues", {"type_id": self.task_type, "title": "Trace"})["number"]
        url = self.base + "/issues/{}".format(n)
        alice.patch(url, {"description": "x" * 5000})
        alice.put(url + "/summary", {"client_summary": "y" * 800})
        history = self.issue(alice, n)["history"]
        for entry in history:
            self.assertLess(len(entry["new_value"] or ""), 200)
            self.assertLess(len(entry["old_value"] or ""), 200)
        self.assertEqual({h["user_name"] for h in history}, {"Alice Test"})


if __name__ == "__main__":
    unittest.main()
