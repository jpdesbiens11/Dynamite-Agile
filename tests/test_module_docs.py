"""0.60.45 (D-O-054): the documentation of every module -- why, need, steps, MVP 0 to MVP x, references ordered -- in the
HeadLamp library of the tool and on the « Modules » page of the website, from one source (modules/help/module_docs*.py)."""
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

from modules.help.module_docs import MODULES, MVPS  # noqa: E402
from modules.help.module_docs_refs import ACCESS, REFS  # noqa: E402


class ModuleDocsDataTest(unittest.TestCase):
    def test_01_every_module_complete_in_both_languages(self):
        self.assertEqual([m["key"] for m in MODULES],
                         ["help", "exploration", "dynamite", "goldmine", "tools", "agile", "testing", "timesheet", "diamond"])
        for m in MODULES:
            for lang in ("fr", "en"):
                t = m[lang]
                for field in ("role", "why", "need"):
                    self.assertTrue(t[field].strip(), (m["key"], lang, field))
                self.assertGreaterEqual(len(t["steps"]), 5, m["key"])
                self.assertEqual(len(t["mvps"]), len(MVPS[lang]), m["key"])
            self.assertGreaterEqual(len(m["refs"]), 4, m["key"])
            self.assertEqual(len(m["refs"]), len(set(m["refs"])), m["key"])
            for rid in m["refs"] + [r for p in m["parts"] for r in p["refs"]]:
                self.assertIn(rid, REFS, (m["key"], rid))
        self.assertEqual([p["name"] for p in MODULES[-1]["parts"]],
                         ["Storyline", "Arbre fonctionnel", "Structure fonctionnelle", "Risques projet", "DFMEA", "Golden Nuggets"])

    def test_02_references_are_clean(self):
        for rid, (name, source, year, url, lang, access, why) in REFS.items():
            self.assertTrue(url.startswith("https://"), rid)
            self.assertIn(access, ACCESS["fr"], rid)
            self.assertTrue(name and source and why, rid)
            self.assertNotRegex(url, r"\s", rid)
        self.assertEqual(REFS["aiag"][5], "paid")  # standards and books: public page only
        for m in MODULES:  # HeadLamp is never translated
            self.assertNotRegex(m["fr"]["why"] + m["en"]["why"], r"(?i)lanterne|lampe frontale")

    def test_03_site_page(self):
        subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build_site.py")], check=True, capture_output=True)
        for rel, word in (("site/modules.html", "Pourquoi ce module"), ("site/en/modules.html", "Why this module")):
            page = (BASE_DIR / rel).read_text("utf-8")
            self.assertEqual(page.count('class="mod reveal"'), len(MODULES), rel)
            self.assertEqual(page.count(word), len(MODULES), rel)
            self.assertIn(REFS["scrum_fr"][3], page)
            self.assertNotIn("{{", page)
            self.assertIn('href="modules.html"', page)
        self.assertIn('href="modules.html"', (BASE_DIR / "site" / "home.html").read_text("utf-8"))


class ModuleDocsHeadLampTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(cls.data_dir)
        cls.cfg["port"] = 0
        db.init_db(cls.data_dir / "d.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cls.cfg)
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_10_pages_in_headlamp_and_help(self):
        status = self.admin.get("/api/help/headlamp")
        docs = status["docs"]
        self.assertEqual(len(docs["modules"]), len(MODULES))
        self.assertTrue(all(m["page"] for m in docs["modules"]))
        page = self.admin.get("/api/dynamite/p/{}/pages/{}".format(status["project"]["id"], docs["modules"][-1]["page"]))["page"]
        self.assertEqual(page["title"], "Module — Diamond")
        text = str(page["body"])
        for part in ("Pourquoi ce module", "De MVP 0 à MVP x", "Golden Nuggets", REFS["aiag"][3], "000 m dans la mine"):
            self.assertIn(part, text)

    def test_11_regenerated_until_edited(self):
        status = self.admin.get("/api/help/headlamp")
        url = "/api/dynamite/p/{}/pages/{}".format(status["project"]["id"], status["docs"]["modules"][0]["page"])
        page = self.admin.get(url)["page"]
        body = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Notes de l'équipe"}]}]}
        self.admin.put(url, {"title": page["title"], "body": body, "base_version": page["version"], "note": "Mes notes"})
        startup.run(self.data_dir, self.cfg)  # the next start-up leaves a person's edit alone and creates nothing twice
        self.assertIn("Notes de l'équipe", str(self.admin.get(url)["page"]["body"]))
        titles = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(status["project"]["id"]))["pages"]]
        self.assertEqual(titles.count("Module — Diamond"), 1)


if __name__ == "__main__":
    unittest.main()
