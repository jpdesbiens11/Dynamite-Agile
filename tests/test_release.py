"""0.60.12 (D-O-024): official versions -- a published package updates a portal by one or several versions, data kept,
tampering refused, files edited by hand listed, « Plus tard » changes nothing."""
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import APP_VERSION, auth, db, modules, release, router, startup, update  # noqa: E402
from core.config import load_config  # noqa: E402
from tools import build_release  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

NEXT = "0.60.98", "0.60.99"


def copy_code(dest):
    for rel in update.code_files(BASE_DIR):
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE_DIR / rel, dest / rel)


def future_package(tmp):
    """The current code as if it were 0.60.99, with two more versions in the series (0.60.98 and 0.60.99)."""
    src = tmp / "future"
    copy_code(src)
    init = src / "core" / "__init__.py"
    init.write_text(init.read_text("utf-8").replace('APP_VERSION = "{}"'.format(APP_VERSION), 'APP_VERSION = "0.60.99"'), "utf-8")
    for v in NEXT:
        (src / "docs" / "releases" / (v + ".json")).write_text(json.dumps({"version": v, "date": "2026-12-01", "summary": {
            "fr": "Essai " + v, "en": "Test " + v}, "changes": [{"id": "C1", "title": "Changement " + v, "files": ["core/__init__.py"]}]}), "utf-8")
    (src / "docs" / "NOUVEAU.md").write_text("fichier ajouté par la version future\n", "utf-8")
    return build_release.build(src, "0.60.99")


class ReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        cls.code = tmp / "installed"
        copy_code(cls.code)
        cls.data, cls.listing = future_package(tmp)
        data_dir = tmp / "data"
        data_dir.mkdir()
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False, code_root=str(cls.code), update_restart=False)
        db.init_db(data_dir / "r.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def check(self, data):
        return self.admin.upload("/api/update/check", data, "application/zip", "paquet.zip")

    def test_01_package_and_listing(self):
        z = zipfile.ZipFile(io.BytesIO(self.data))
        names = set(z.namelist())
        self.assertIn("Dynamite_Agile/docs/RELEASE.json", names)
        self.assertIn("Dynamite_Agile/UPDATE_CHANGES.json", names)
        self.assertFalse(any("/data/" in n for n in names))
        merged = json.loads(z.read("Dynamite_Agile/UPDATE_CHANGES.json"))["changes"]
        self.assertTrue(any(c["id"].startswith("0.60.05-") for c in merged))  # the whole series, for older portals
        self.assertEqual(self.listing["latest"], "0.60.99")
        self.assertEqual([v["version"] for v in self.listing["versions"][:3]], ["0.60.99", "0.60.98", APP_VERSION])
        again, _ = future_package(Path(tempfile.mkdtemp(dir=self.tmp.name)))
        self.assertEqual(again, self.data)  # reproducible: the same SHA-256 on the site and in CI

    def test_02_tampered_package_refused(self):
        src = zipfile.ZipFile(io.BytesIO(self.data))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as out:
            for info in src.infolist():
                body = src.read(info)
                if info.filename.endswith("core/router.py"):
                    body += b"\n# changed after publication\n"
                out.writestr(info, body)
        r = self.check(buf.getvalue())
        self.assertFalse(r["ok"])
        self.assertTrue(any("modifié après sa publication" in p for p in r["problems"]), r["problems"])

    def test_03_later_changes_nothing(self):
        r = self.check(self.data)
        self.assertTrue(r["ok"], r["problems"])
        self.assertTrue(self.admin.post("/api/update/later", {"token": r["token"]})["ok"])
        with self.assertRaises(ApiFailure):
            self.admin.get("/api/update/review/" + r["token"])
        self.assertIn('APP_VERSION = "{}"'.format(APP_VERSION), (self.code / "core" / "__init__.py").read_text("utf-8"))

    def test_04_series_review_and_apply(self):
        marker = self.code / "data"  # never touched (here, a stand-in next to the code)
        r = self.check(self.data)
        self.assertTrue(r["ok"], r["problems"])
        self.assertEqual(r["official"]["version"], "0.60.99")
        self.assertEqual(r["sha256"], self.listing["sha256"])
        mine = [p.stem for p in sorted((BASE_DIR / "docs" / "releases").glob("*.json"))
                if release.version_tuple(p.stem) > release.version_tuple(APP_VERSION)]
        expected = mine + list(NEXT)
        self.assertEqual([s["version"] for s in r["series"]], expected)
        self.assertEqual(r["review"]["total"], len(expected))  # one step per version skipped or brought
        base = "/api/update/review/" + r["token"]
        for n in range(1, len(expected) + 1):
            self.admin.get("{}/{}".format(base, n))
            self.admin.post("{}/{}".format(base, n), {"decision": "approve"})
        done = self.admin.post("/api/update/apply", {"token": r["token"]})
        self.assertEqual(done["version"], "0.60.99")
        self.assertIn('APP_VERSION = "0.60.99"', (self.code / "core" / "__init__.py").read_text("utf-8"))
        self.assertTrue((self.code / "docs" / "NOUVEAU.md").is_file())
        self.assertFalse(marker.exists())
        with db.connect() as conn:  # the accounts are still there
            self.assertTrue(conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone())
        man = release.installed(self.code, "0.60.99")
        self.assertEqual(man["version"], "0.60.99")
        self.assertEqual(release.local_changes(self.code, "0.60.99", update.code_files(self.code)), [])
        (self.code / "core" / "router.py").write_text("# edited by hand\n", "utf-8")
        self.assertEqual(release.local_changes(self.code, "0.60.99", update.code_files(self.code)), ["core/router.py"])
        self.assertIsNone(release.local_changes(self.code, "0.61.00", update.code_files(self.code)))  # another version: unknown

    def test_05_status_links_to_the_versions_page(self):
        s = self.admin.get("/api/update/status")["release"]
        self.assertTrue(s["pages"]["fr"].endswith("/versions.html#depuis=" + APP_VERSION))
        self.assertTrue(s["pages"]["en"].endswith("en/versions.html#depuis=" + APP_VERSION))
        self.assertIn("git", s)

    def test_06_every_version_is_published_with_its_page(self):
        rec = json.loads((BASE_DIR / "docs" / "releases" / (APP_VERSION + ".json")).read_text("utf-8"))
        self.assertTrue(rec["summary"]["fr"] and rec["summary"]["en"])  # the record the site and the review read
        for page in ("site/versions.html", "site/en/versions.html"):
            text = (BASE_DIR / page).read_text("utf-8")
            self.assertIn("updates/versions.json", text)
            self.assertIn('id="ver-list"', text)
        flow = (BASE_DIR / ".github" / "workflows" / "pages.yml").read_text("utf-8")
        self.assertIn("tools/build_release.py --out site/updates", flow)
        for script in ("deploy/install.sh", "deploy/install.ps1"):
            text = (BASE_DIR / script).read_text("utf-8-sig")
            self.assertNotIn("pull --ff-only", text)  # an applied package never blocks the next installation command
            self.assertIn("code-local-", text)


if __name__ == "__main__":
    unittest.main()
