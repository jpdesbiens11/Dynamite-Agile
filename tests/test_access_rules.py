"""Core lot v0.6 (D-B-016): access rules exported and imported as text --
users, directory fields and project rights; dry run; safety of admins.

    python -m unittest tests.test_access_rules -v
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


class AccessRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "r.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "EQP", "name": "Projet d'équipe", "provision": False})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_1_default_base_dry_run_then_apply(self):
        text = self.admin.get("/api/admin/access-rules/default")["text"]
        dry = self.admin.post("/api/admin/access-rules", {"text": text, "dry_run": True})
        self.assertEqual(dry["summary"]["problems"], 0, dry["report"])
        self.assertEqual(len(self.admin.get("/api/admin/users")["users"]), 1)  # nothing written
        done = self.admin.post("/api/admin/access-rules", {"text": text})
        self.assertEqual(len(done["created"]), 4)
        users = {u["username"]: u for u in self.admin.get("/api/admin/users")["users"]}
        self.assertEqual(users["lea"]["title"], "Responsable électrique")
        self.assertEqual(users["nina"]["study_profile"], "Génie mécanique")
        self.assertTrue(users["hugo"]["must_change_password"])
        pid = self.admin.get("/api/admin/projects")["projects"][0]["id"]
        roles = {m["username"]: m["role"] for m in self.admin.get("/api/admin/projects/{}/members".format(pid))["members"]}
        self.assertEqual(roles["nina"], "manager")
        self.assertEqual(roles["lea"], "editor")
        # First login with the temporary password forces a change.
        temp = next(c["temp_password"] for c in done["created"] if c["username"] == "hugo")
        hugo = Client(self.url)
        me = hugo.login("hugo", temp)
        self.assertTrue(me["user"]["must_change_password"])
        hugo.post("/api/me/password", {"old_password": temp, "new_password": "Vivace-Essai-Pass-2026"})
        # Directory for every signed-in user.
        people = hugo.get("/api/directory")
        self.assertGreaterEqual(len(people["people"]), 4)
        # Re-import: idempotent.
        again = self.admin.post("/api/admin/access-rules", {"text": text})
        self.assertEqual(again["created"], [])
        self.assertTrue(all(r["action"] == "inchangé" for r in again["report"]), again["report"])

    def test_2_export_roundtrip_and_rules(self):
        with self.admin.opener.open(self.url + "/api/admin/access-rules") as resp:
            exported = resp.read().decode("utf-8")
        self.assertIn("droit       lea | EQP | editeur", exported)
        self.assertNotIn("password", exported.lower().replace("mots de passe", "").replace("mot de passe", ""))
        result = self.admin.post("/api/admin/access-rules", {"text": exported})
        self.assertEqual(result["summary"]["problems"], 0)
        bad = self.admin.post("/api/admin/access-rules", {"text": "\n".join([
            "utilisateur admin | Admin | utilisateur | actif",   # would remove own admin right
            "droit inconnu | EQP | editeur",
            "droit lea | NOPE | editeur",
            "droit lea | EQP | patron",
            "blabla x",
            "droit alexis | EQP | aucun"])})
        problems = [r for r in bad["report"] if not r["ok"]]
        self.assertEqual(len(problems), 5)
        self.assertTrue(all("Correctif" in r["detail"] or "créez-le" in r["detail"] or "rester" in r["detail"]
                            or "propre compte" in r["detail"] for r in problems), problems)
        pid = self.admin.get("/api/admin/projects")["projects"][0]["id"]
        members = [m["username"] for m in self.admin.get("/api/admin/projects/{}/members".format(pid))["members"]]
        self.assertNotIn("alexis", members)  # "aucun" removed the right
        self.assertTrue(self.admin.get("/api/me")["user"]["is_admin"])

    def test_3_admin_only(self):
        with self.assertRaises(ApiFailure):
            Client(self.url).get("/api/admin/access-rules")


if __name__ == "__main__":
    unittest.main()
