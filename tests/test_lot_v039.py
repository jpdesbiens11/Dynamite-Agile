"""0.49.0: core lot v0.26 (D-B-094) -- Admin → Update in three parts: Framework reviewed step by step, « Données »
(sealed, imported Space by Space, never over a Space in service) and « Site complet » (move into an empty site).

    python -m unittest tests.test_lot_v039 -v
"""
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import APP_VERSION, auth, backup, datapack, db, modules, router, seal, startup, update  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

NEXT = ".".join(str(x) for x in (update._version_tuple(APP_VERSION)[:2] + (update._version_tuple(APP_VERSION)[2] + 1,)))
PASS = "quatre mots bien longs"


class _Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name) / "data"
        cls.code = Path(cls.tmp.name) / "code"
        for rel in update.code_files(BASE_DIR):
            (cls.code / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BASE_DIR / rel, cls.code / rel)
        cls.data_dir.mkdir()
        cfg = load_config(cls.data_dir)
        cfg.update(port=0, require_initials=False, code_root=str(cls.code), update_restart=False, dev_mode=False)
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as ctx:
            fn(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)
        return ctx.exception.message

    def download(self, path):
        with self.admin.opener.open(self.url + path) as resp:
            return resp.read()

    def approve_all(self, base, summary, options=None):
        for step in summary["steps"]:
            self.admin.get("{}/{}".format(base, step["n"]))
            body = {"decision": "approve"}
            if options and step.get("options") is not None:
                body["options"] = options(step)
            summary = self.admin.post("{}/{}".format(base, step["n"]), body)
        return summary


class FrameworkReviewTest(_Site):
    def make_zip(self, changes):
        exported = self.download("/api/update/export.zip")
        src = zipfile.ZipFile(io.BytesIO(exported))
        root = update.ROOT + "/"
        files = {i.filename: src.read(i) for i in src.infolist() if not i.is_dir()}
        key = root + "core/__init__.py"
        files[key] = files[key].replace(APP_VERSION.encode(), NEXT.encode())
        files[root + "docs/NOUVEAU.md"] = b"nouveau"
        files[root + "docs/INTRUS.md"] = b"pas declare"
        if changes is not None:
            files[root + "UPDATE_CHANGES.json"] = json.dumps(changes).encode()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name, data in files.items():
                z.writestr(name, data)
        return self.admin.upload("/api/update/check", buf.getvalue(), "application/zip", "maj.zip")

    def test_01_prompt_asks_for_changes(self):
        self.assertIn("UPDATE_CHANGES.json", self.admin.get("/api/update/status")["prompt"])

    def test_02_bad_changes_file_blocks(self):
        bad = self.make_zip({"changes": [{"files": ["x"]}]})
        self.assertFalse(bad["ok"])
        self.assertIn("sans titre", " ".join(bad["problems"]))

    def test_03_steps_refusal_and_feedback(self):
        good = self.make_zip({"changes": [{"id": "C1", "title": "Version et nouveau document", "why": "Démonstration",
                                           "files": ["core/__init__.py", "docs/NOUVEAU.md", "docs/ABSENT.md"]}]})
        self.assertTrue(good["ok"], good["problems"])
        steps = good["review"]["steps"]
        self.assertEqual([s["title"] for s in steps], ["Version et nouveau document", "Changement non déclaré"])
        base = "/api/update/review/" + good["token"]
        self.assertIn("pas encore approuvée", self.fails(409, self.admin.post, "/api/update/apply", {"token": good["token"]}))
        self.assertIn("jamais ouverte", self.fails(409, self.admin.post, base + "/1", {"decision": "approve"}))
        detail = self.admin.get(base + "/1")
        self.assertEqual({f["path"] for f in detail["files"]}, {"core/__init__.py", "docs/NOUVEAU.md"})
        self.assertIn("docs/ABSENT.md", detail["step"]["unknown"])
        version = next(f for f in detail["files"] if f["path"] == "core/__init__.py")
        self.assertTrue(any(NEXT in line for line in version["diff"]))
        self.admin.post(base + "/1", {"decision": "approve"})
        self.assertEqual([f["path"] for f in self.admin.get(base + "/2")["files"]], ["docs/INTRUS.md"])
        self.fails(400, self.admin.post, base + "/2", {"decision": "refuse"})  # a refusal needs a reason
        out = self.admin.post(base + "/2", {"decision": "refuse", "comment": "INTRUS.md n'est expliqué nulle part."})
        self.assertTrue(out["refused"] and out["closed"])
        self.assertIn("INTRUS.md n'est expliqué nulle part.", out["feedback"])
        self.assertIn("## Approuvé (à garder)", out["feedback"])
        self.fails(409, self.admin.post, "/api/update/apply", {"token": good["token"]})
        self.assertFalse((self.code / "docs" / "NOUVEAU.md").exists())

    def test_04_all_approved_then_applied(self):
        good = self.make_zip(None)  # no UPDATE_CHANGES.json: one undeclared step with every file
        self.assertEqual(len(good["review"]["steps"]), 1)
        summary = self.approve_all("/api/update/review/" + good["token"], good["review"])
        self.assertTrue(summary["ready"])
        done = self.admin.post("/api/update/apply", {"token": good["token"]})
        self.assertEqual(done["version"], NEXT)
        self.assertTrue((self.code / "docs" / "INTRUS.md").exists())
        self.admin.post("/api/update/rollback", {"backup": done["backup"]})


class DataPackTest(_Site):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin.post("/api/admin/projects", {"key": "PRJ", "name": "PRJ Proto", "description": "démo"})
        cls.admin.post("/api/admin/users", {"username": "marie.c", "display_name": "Marie C."})

    def rows(self, key):
        with db.connect() as conn:
            pid = conn.execute("SELECT id FROM projects WHERE key = ?", (key,)).fetchone()[0]
            return datapack._counts(backup.collect(conn, pid)[1])

    def export(self, spaces=None):
        out = self.admin.post("/api/data/export", {"passphrase": PASS, "spaces": spaces or []})
        return self.download("/api/data/export/" + out["token"]), out

    def test_01_export_sealed_without_passwords(self):
        self.assertIn("12 au minimum", self.fails(400, self.admin.post, "/api/data/export", {"passphrase": "court"}))
        data, out = self.export(["PRJ"])
        self.assertEqual([s["key"] for s in out["spaces"]], ["PRJ"])
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertIn("SEAL.json", z.namelist())
        self.assertNotIn("password_hash", z.read("accounts.json").decode())
        with self.assertRaises(urllib.error.HTTPError) as gone:  # one download only
            self.download("/api/data/export/" + out["token"])
        self.assertEqual(gone.exception.code, 404)
        with db.connect() as conn:
            logged = " ".join(r[0] or "" for r in conn.execute("SELECT details FROM audit_log"))
        self.assertNotIn(PASS, logged)

    def test_02_seal_refuses_wrong_passphrase_and_tampering(self):
        data, _out = self.export(["PRJ"])
        token = self.admin.upload("/api/data/upload", data, "application/zip", "d.zip")["token"]
        self.assertIn("Sceau invalide", self.fails(403, self.admin.post, "/api/data/open", {"token": token, "passphrase": "mauvaise phrase!!"}))
        src = zipfile.ZipFile(io.BytesIO(data))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name in src.namelist():
                body = src.read(name)
                z.writestr(name, body.replace(b"PRJ Proto", b"PRJ Faux") if name.startswith("spaces/") else body)
        token = self.admin.upload("/api/data/upload", buf.getvalue(), "application/zip", "d.zip")["token"]
        self.assertIn("modifié depuis l'export", self.fails(403, self.admin.post, "/api/data/open", {"token": token, "passphrase": PASS}))

    def test_03_import_never_overwrites(self):
        before = self.rows("PRJ")
        data, _out = self.export()
        with db.connect() as conn:  # an account the package knows but this site lost
            conn.execute("UPDATE users SET username = 'marie.old' WHERE username = 'marie.c'")
        token = self.admin.upload("/api/data/upload", data, "application/zip", "d.zip")["token"]
        summary = self.admin.post("/api/data/open", {"token": token, "passphrase": PASS})
        steps = {s["id"]: s for s in summary["steps"]}
        self.assertEqual(steps["accounts"]["count"], 1)
        self.assertEqual(steps["space-PRJ"]["options"]["action"], "skip")
        self.assertEqual(steps["space-PRJ"]["options"]["key"], "PRJ2")
        base = "/api/data/review/" + token
        n = steps["space-PRJ"]["n"]
        self.admin.get("{}/{}".format(base, n))
        self.assertIn("existe déjà", self.fails(409, self.admin.post, "{}/{}".format(base, n),
                                                {"decision": "approve", "options": {"action": "new", "key": "PRJ", "types": []}}))
        self.fails(409, self.admin.post, "/api/data/apply/" + token)

        def choose(step):
            if step["id"] == "space-PRJ":
                return {"action": "new", "key": "PRJ2", "types": list(before)}  # site-only types are ignored
            return {"action": "skip"}
        summary = self.approve_all(base, summary, choose)
        self.assertTrue(summary["ready"])
        done = self.admin.post("/api/data/apply/" + token)
        self.assertEqual([s["key"] for s in done["spaces"]], ["PRJ2"])
        self.assertEqual(self.rows("PRJ2"), {k: n for k, n in before.items() if k not in datapack.SITE_ONLY})
        self.assertEqual(done["spaces"][0]["lost_links"], 0)
        self.assertEqual(self.rows("PRJ"), before)  # the Space in service is untouched
        self.assertEqual([c["username"] for c in done["created"]], ["marie.c"])
        with db.connect() as conn:
            row = conn.execute("SELECT is_admin, must_change_password FROM users WHERE username = 'marie.c'").fetchone()
        self.assertEqual(tuple(row), (0, 1))


class SiteMoveTest(_Site):
    def test_01_move_into_empty_site(self):
        self.admin.post("/api/admin/projects", {"key": "MOV", "name": "Déménagé"})
        with db.connect() as conn:
            before = conn.execute("SELECT COUNT(*) FROM dynamite_pages").fetchone()[0]
        out = self.admin.post("/api/site/export", {"passphrase": PASS})
        self.assertIn("MOV", out["spaces"])
        data = self.download("/api/site/export/" + out["token"])
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertIn("database.sqlite", names)
        self.assertIn("code/core/__init__.py", names)
        self.assertFalse(any(n.startswith("files/") and "config.json" in n for n in names))
        with db.connect() as conn:  # what happens after the export is gone once the package is back
            conn.execute("UPDATE projects SET name = 'Renommé après' WHERE key = 'MOV'")
        token = self.admin.upload("/api/site/upload", data, "application/zip", "s.zip")["token"]
        summary = self.admin.post("/api/site/open", {"token": token, "passphrase": PASS})
        titles = [s["title"] for s in summary["steps"]]
        self.assertEqual(titles[1], "Framework : code identique")
        self.assertTrue(any(t.startswith("Space MOV") for t in titles))
        summary = self.approve_all("/api/site/review/" + token, summary)
        done = self.admin.post("/api/site/apply/" + token)
        self.assertFalse(done["restarting"])
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT name FROM projects WHERE key = 'MOV'").fetchone()[0], "Déménagé")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM dynamite_pages").fetchone()[0], before)
        self.fails(401, self.admin.get, "/api/update/status")  # the session did not travel
        again = Client(self.url)
        again.login("admin", "admin")  # same password: the hash travelled
        self.assertTrue(any(b == done["backup"] for b in again.get("/api/update/status")["backups"]))

    def test_02_refused_on_a_site_in_service(self):
        admin = Client(self.url)
        admin.login("admin", "admin")
        admin.post("/api/admin/users", {"username": "paul.t", "display_name": "Paul T."})
        with self.assertRaises(ApiFailure) as ctx:
            admin.upload("/api/site/upload", b"PK", "application/zip", "s.zip")
        self.assertEqual(ctx.exception.status, 409)
        self.assertIn("pas vide", ctx.exception.message)


class SealUnitTest(unittest.TestCase):
    def test_seal_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.zip"
            seal.write(path, "da-test", [("a.txt", b"bonjour")], PASS, {"created_by": "t"})
            z, manifest = seal.open_sealed(path, PASS, "da-test", "Test")
            self.assertEqual(z.read("a.txt"), b"bonjour")
            self.assertEqual(manifest["created_by"], "t")


if __name__ == "__main__":
    unittest.main(verbosity=2)
