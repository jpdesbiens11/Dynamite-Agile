"""0.41.0: Admin → Update (core lot v0.21, D-A-049) -- code only, data kept; [new] tags; BDC guide.
Works on a copy of the code in a temporary folder (config « code_root »), without restart.

    python -m unittest tests.test_lot_v031 -v
"""
import io
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import APP_VERSION, auth, db, modules, router, startup, update  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

NEXT = ".".join(str(x) for x in (update._version_tuple(APP_VERSION)[:2] + (update._version_tuple(APP_VERSION)[2] + 1,)))


class LotV031Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name) / "data"
        cls.code = Path(cls.tmp.name) / "code"
        for rel in update.code_files(BASE_DIR):
            (cls.code / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BASE_DIR / rel, cls.code / rel)
        data_dir.mkdir()
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False, code_root=str(cls.code), update_restart=False)
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path):
        with self.admin.opener.open(self.url + path) as resp:
            return resp.read()

    def post_zip(self, path, data):
        req = urllib.request.Request(self.url + path, data=data, method="POST", headers={
            "Content-Type": "application/zip", "X-File-Name": "maj.zip", "X-CSRF-Token": self.admin.csrf})
        import json
        try:
            with self.admin.opener.open(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return {"http": exc.code, "error": json.loads(exc.read()).get("error")}

    def rezip(self, exported, edit):
        src = zipfile.ZipFile(io.BytesIO(exported))
        files = {i.filename: src.read(i) for i in src.infolist() if not i.is_dir()}
        edit(files)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name, data in files.items():
                z.writestr(name, data)
        return buf.getvalue()

    def test_update_cycle(self):
        exported = self.get("/api/update/export.zip")
        names = zipfile.ZipFile(io.BytesIO(exported)).namelist()
        root = update.ROOT + "/"
        self.assertIn(root + "UPDATE_PROMPT.md", names)
        self.assertIn(root + "SCHEMA.sql", names)
        self.assertFalse(any(n.startswith(root + "data/") for n in names))
        prompt = zipfile.ZipFile(io.BytesIO(exported)).read(root + "UPDATE_PROMPT.md").decode()
        self.assertIn("Claude Opus 5.5 ou plus récent", prompt)
        self.assertIn("mode verbose", prompt)
        same = self.post_zip("/api/update/check", exported)
        self.assertFalse(same["ok"])
        self.assertTrue(any("Version" in p for p in same["problems"]))

        def bump(files, extra=None):
            key = root + "core/__init__.py"
            files[key] = files[key].replace(APP_VERSION.encode(), NEXT.encode())
            files[root + "UPDATE_LOG.md"] = "# {}\n- Nouveau fichier de démonstration".format(NEXT).encode()
            files[root + "docs/NOUVEAU.md"] = b"nouveau"
            if extra:
                extra(files)

        bad = self.post_zip("/api/update/check", self.rezip(exported, lambda f: bump(f, lambda g: g.update({
            root + "data/intrus.db": b"x", root + "modules/testing/casse.py": b"def (:\n",
            root + "modules/testing/drop.py": b'MIGRATIONS = [(9, "DROP TABLE testing_tests")]\n'}))))
        self.assertFalse(bad["ok"])
        text = " ".join(bad["problems"])
        for part in ("data/ n'est jamais importé", "erreur de syntaxe", "ne supprime jamais de données"):
            self.assertIn(part, text)
        with db.connect() as conn:
            before = conn.execute("SELECT COUNT(*) FROM testing_tests").fetchone()[0]
        good = self.post_zip("/api/update/check", self.rezip(exported, bump))
        self.assertTrue(good["ok"], good["problems"])
        self.assertEqual(good["version"], NEXT)
        self.assertIn("docs/NOUVEAU.md", good["added"]["sample"])
        self.assertIn("Nouveau fichier", good["log"])
        for step in good["review"]["steps"]:  # D-B-094: each step opened and approved before applying
            self.admin.get("/api/update/review/{}/{}".format(good["token"], step["n"]))
            self.admin.post("/api/update/review/{}/{}".format(good["token"], step["n"]), {"decision": "approve"})
        done = self.admin.post("/api/update/apply", {"token": good["token"]})
        self.assertEqual(done["version"], NEXT)
        self.assertFalse(done["restarting"])
        self.assertTrue((self.code / "docs" / "NOUVEAU.md").exists())
        self.assertIn(NEXT, (self.code / "core" / "__init__.py").read_text())
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM testing_tests").fetchone()[0], before)  # data kept
        status = self.admin.get("/api/update/status")
        self.assertEqual(status["history"][0]["version"], NEXT)
        self.assertIn(done["backup"], status["backups"])
        back = self.admin.post("/api/update/rollback", {"backup": done["backup"]})
        self.assertEqual(back["version"], APP_VERSION)
        self.assertIn(APP_VERSION, (self.code / "core" / "__init__.py").read_text())
        self.assertFalse((self.code / "docs" / "NOUVEAU.md").exists())

    def test_new_tags_and_guide(self):
        self.assertEqual(self.admin.get("/api/new/seen")["seen"], [])
        self.admin.post("/api/new/seen", {"id": "0.41.0-admin-update"})
        self.assertEqual(self.admin.get("/api/new/seen")["seen"], ["0.41.0-admin-update"])
        pid = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}["HEADLAMP"]
        titles = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]]
        self.assertIn("Mettre à jour le site (Admin → Update) — pas à pas", titles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
