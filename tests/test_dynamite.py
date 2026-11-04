"""Dynamite increment 1: tree, versions, conflicts, lock, content whitelist,
live ticket block without leaks (D-A-035, D-A-036).

    python -m unittest tests.test_dynamite -v
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

DOC = {"type": "doc", "content": [
    {"type": "heading", "level": 1, "content": [{"type": "text", "text": "Procédure"}]},
    {"type": "paragraph", "content": [{"type": "text", "text": "Voir ", "marks": []},
                                      {"type": "text", "text": "le site", "marks": [{"type": "link", "href": "https://example.org"}]}]},
    {"type": "panel", "kind": "warning", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Attention"}]}]},
    {"type": "ticket", "key": "DEMO-1"},
]}


class DynamiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "d.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        for key in ("DOC", "DEMO", "SECRET"):
            cls.admin.post("/api/admin/projects", {"provision": False, "key": key, "name": key, "description": ""})
        ids = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.ids = ids
        for key in ("DEMO", "SECRET"):
            base = "/api/agile/p/{}".format(ids[key])
            cls.admin.post(base + "/init")
            task = next(t for t in cls.admin.get(base + "/meta")["types"] if t["icon_key"] == "task")
            cls.admin.post(base + "/issues", {"type_id": task["id"], "title": "Ticket " + key})
        made = cls.admin.post("/api/admin/users", {"username": "redac", "display_name": "Rédactrice"})
        for key, role in (("DOC", "editor"), ("DEMO", "reader")):
            cls.admin.put("/api/admin/projects/{}/members/{}".format(ids[key], made["user"]["id"]), {"role": role})
        cls.editor = Client(url)
        cls.editor.login("redac", made["temp_password"], "Plume-Essai-Pass-2026")
        cls.base = "/api/dynamite/p/{}".format(ids["DOC"])

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

    def test_01_tree_versions_restore(self):
        root = self.editor.post(self.base + "/pages", {"title": "Accueil", "body": DOC})["id"]
        child = self.editor.post(self.base + "/pages", {"title": "Sous-page", "parent_id": root})["id"]
        tree = self.editor.get(self.base + "/pages")["pages"]
        self.assertEqual({p["id"]: p["parent_id"] for p in tree}[child], root)
        self.assertIn("propre sous-page", self.fails(400, self.editor.patch,
                      self.base + "/pages/{}/move".format(root), {"parent_id": child}))
        page = self.editor.get(self.base + "/pages/{}".format(root))["page"]
        self.editor.put(self.base + "/pages/{}".format(root), {"title": "Accueil v2", "body": DOC, "base_version": 1})
        msg = self.fails(409, self.editor.put, self.base + "/pages/{}".format(root),
                         {"title": "Écrasement", "body": DOC, "base_version": page["version"]})
        self.assertIn("Correctif", msg)
        self.editor.post(self.base + "/pages/{}/versions/1/restore".format(root))
        now = self.editor.get(self.base + "/pages/{}".format(root))["page"]
        self.assertEqual((now["version"], now["title"]), (3, "Accueil"))
        self.assertEqual(len(self.editor.get(self.base + "/pages/{}/versions".format(root))["versions"]), 3)
        self.assertIn("sous-page", self.fails(409, self.admin.delete, self.base + "/pages/{}".format(root)))

    def test_02_content_whitelist(self):
        for bad, expected in (
                ({"type": "doc", "content": [{"type": "script"}]}, "bloc « script » inconnu"),
                ({"type": "doc", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "x", "marks": [{"type": "link", "href": "javascript:alert(1)"}]}]}]}, "lien"),
                ({"type": "doc", "content": [{"type": "heading", "level": 7, "content": []}]}, "niveau")):
            msg = self.fails(400, self.editor.post, self.base + "/pages", {"title": "Mauvaise", "body": bad})
            self.assertIn(expected, msg)
            self.assertIn("Correctif", msg)

    def test_03_lock(self):
        page = self.editor.post(self.base + "/pages", {"title": "Verrou"})["id"]
        self.editor.post(self.base + "/pages/{}/lock".format(page))
        self.assertIn("Rédactrice édite", self.fails(409, self.admin.post, self.base + "/pages/{}/lock".format(page)))
        self.editor.delete(self.base + "/pages/{}/lock".format(page))
        self.admin.post(self.base + "/pages/{}/lock".format(page))

    def test_04_ticket_block_live_and_no_leak(self):
        live = self.editor.get("/api/dynamite/ticket/DEMO-1")
        self.assertEqual((live["title"], live["status_name"]), ("Ticket DEMO", "To Do"))
        hidden = self.fails(404, self.editor.get, "/api/dynamite/ticket/SECRET-1")
        missing = self.fails(404, self.editor.get, "/api/dynamite/ticket/DEMO-999")
        self.assertNotIn("SECRET", hidden.replace("SECRET-1", ""))  # same wording, nothing revealed
        self.assertEqual(hidden.replace("SECRET-1", "X"), missing.replace("DEMO-999", "X"))

    def test_05_reader_cannot_write(self):
        demo = "/api/dynamite/p/{}".format(self.ids["DEMO"])
        self.fails(403, self.editor.post, demo + "/pages", {"title": "Non"})
        self.fails(404, self.editor.get, "/api/dynamite/p/{}/pages".format(self.ids["SECRET"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
