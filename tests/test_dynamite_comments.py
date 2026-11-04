"""Dynamite page comments (D-B-002): readers may comment, only author or
admin deletes, replies cascade, version recorded, no cross-space access.

    python -m unittest tests.test_dynamite_comments -v
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


class DynamiteCommentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "c.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        for key in ("DOC", "OTHER"):
            cls.admin.post("/api/admin/projects", {"provision": False, "key": key, "name": key, "description": ""})
        ids = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        made = cls.admin.post("/api/admin/users", {"username": "lect", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(ids["DOC"], made["user"]["id"]),
                      {"role": "reader"})
        cls.reader = Client(url)
        cls.reader.login("lect", made["temp_password"], "Revue-Essai-Pass-2026")
        cls.base = "/api/dynamite/p/{}".format(ids["DOC"])
        cls.other = "/api/dynamite/p/{}".format(ids["OTHER"])
        cls.page = cls.admin.post(cls.base + "/pages", {"title": "Spec"})["id"]
        cls.url = "{}/pages/{}/comments".format(cls.base, cls.page)

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

    def test_01_reader_comments_and_replies(self):
        first = self.reader.post(self.url, {"body": "Section 2 : unité manquante."})["id"]
        self.admin.post(self.url, {"body": "Corrigé.", "parent_comment_id": first})
        listing = self.reader.get(self.url)["comments"]
        self.assertEqual([c["parent_comment_id"] for c in listing], [None, first])
        self.assertEqual(listing[0]["author_name"], "Lecteur")
        self.assertEqual(listing[0]["page_version"], 1)

    def test_02_version_recorded(self):
        page = self.admin.get("{}/pages/{}".format(self.base, self.page))["page"]
        self.admin.put("{}/pages/{}".format(self.base, self.page),
                       {"title": "Spec", "body": page["body"], "base_version": page["version"]})
        cid = self.reader.post(self.url, {"body": "Après la v2"})["id"]
        comment = next(c for c in self.reader.get(self.url)["comments"] if c["id"] == cid)
        self.assertEqual(comment["page_version"], 2)

    def test_03_delete_rules_and_cascade(self):
        parent = self.admin.post(self.url, {"body": "Remarque admin"})["id"]
        child = self.reader.post(self.url, {"body": "Réponse", "parent_comment_id": parent})["id"]
        self.fails(403, self.reader.delete, "{}/{}".format(self.url, parent))
        self.admin.delete("{}/{}".format(self.url, parent))
        ids = {c["id"] for c in self.admin.get(self.url)["comments"]}
        self.assertNotIn(child, ids)  # replies go with their parent

    def test_04_validation_and_isolation(self):
        self.assertIn("Correctif", self.fails(400, self.reader.post, self.url, {"body": "   "}))
        self.fails(400, self.reader.post, self.url, {"body": "x" * 10001})
        self.fails(404, self.reader.post, self.url, {"body": "x", "parent_comment_id": 99999})
        # Reader has no role on OTHER (404: the core never confirms it exists); page id of DOC under OTHER's space is not found either.
        self.fails(404, self.reader.get, "{}/pages/{}/comments".format(self.other, self.page))
        self.fails(404, self.admin.get, "{}/pages/{}/comments".format(self.other, self.page))


if __name__ == "__main__":
    unittest.main()
