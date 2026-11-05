"""0.60.01 / 0.60.02 (branch open/v0.60): the generic open-source Dynamite | Agile for product-design students and
start-up teams -- nothing of the original use left anywhere in the repository (D-O-012), the example team (Nina, Léa,
Hugo, Alexis) with its « Profil d'études », the PDP deliverables in Generator, the PDP steps as time codes, generic
requirements and tests, vacation bank and funding claims, MIT licence.

    python -m unittest tests.test_open_v060 -v
"""
import argparse
import base64
import io
import re
import zipfile
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import APP_VERSION, auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

# Words that must not appear anywhere in the repository (D-O-012): stored encoded, so that this file does not hold them.
_CI = ("aDU1fGF2aWF0fGFbw6llXXJvbmF1dHxhW8OpZV1yb25lZnxhaXJjcmFmdHxhaXJwbGFuZXxcYmF2aW9ucz9cYnxcYmF0YV98ZHJvbmVzP1xifHNv"
       "bGFyfHZlaGljbGV8cnRjYXxcYmRvLT8xWzY3XVswOF18XGJkby0/MjU0fFxiZG8tPzMxMXxhcnAgPzQ3fGV2dG9sfFxiZW4gdm9sXGJ8aW4tZmxp"
       "Z2h0fGZsaWdodHxjcmVlcGFnZXxjcmNsfGhlcm1lc3xzd2FwbGlua3xpbXB1bHNlfHBpY2NhcmR8Ym9yc2NoYmVyZw==")
_CS = "XGJBVEFcYnxcYlVBU1xifFxiRVNTXGJ8XGJCTVNcYnxcYkRBTFxifFxiTVJPXGJ8XGJTV1BcYnxcYkdFTi1cZA=="
FORBIDDEN_CI = re.compile(base64.b64decode(_CI).decode("utf-8"), re.I)
FORBIDDEN_CS = re.compile(base64.b64decode(_CS).decode("utf-8"))
TEXT_SUFFIXES = (".py", ".js", ".css", ".html", ".md", ".txt", ".csv", ".json", ".svg", ".bat", ".sh", ".service",
                 ".cfg", ".toml", ".yml", ".yaml", ".gitignore", "")
SKIPPED = {".git", "__pycache__", "data"}


def forbidden(text):
    return FORBIDDEN_CI.search(text) or FORBIDDEN_CS.search(text)


def repo_files():
    for f in sorted(BASE_DIR.rglob("*")):
        if f.is_file() and not SKIPPED & set(f.relative_to(BASE_DIR).parts):
            yield f


def scanned_files():
    """Python and JavaScript sources (for the 500-line rule)."""
    for f in repo_files():
        if f.suffix in (".py", ".js") and "tests" not in f.relative_to(BASE_DIR).parts:
            yield f


class StaticContentTest(unittest.TestCase):
    def test_01_version(self):
        self.assertEqual(APP_VERSION, "0.60.49")

    def test_02_nothing_of_the_original_use_left(self):
        hits = []
        for f in repo_files():
            rel = str(f.relative_to(BASE_DIR))
            hits += ["{} (file name)".format(rel)] if forbidden(rel) else []
            texts = []
            if f.suffix in (".docx", ".xlsx", ".pptx", ".zip"):
                with zipfile.ZipFile(io.BytesIO(f.read_bytes())) as z:
                    texts = [(rel + "!" + n, z.read(n).decode("utf-8", "replace")) for n in z.namelist()
                             if n.endswith((".xml", ".rels", ".txt", ".json"))]
            elif f.suffix in TEXT_SUFFIXES or f.name in ("LICENSE", "Makefile"):
                texts = [(rel, f.read_text("utf-8", errors="replace"))]
            for name, text in texts:
                for n, line in enumerate(text.splitlines(), start=1):
                    if forbidden(line):
                        hits.append("{}:{}: {}".format(name, n, line.strip()[:100]))
        self.assertEqual(hits, [], "\n".join(hits[:60]))

    def test_03_clean_baseline(self):
        from modules.agile import schema
        from modules.codex import MIGRATIONS as CODEX
        sql = " ".join(m[1] for m in schema.MIGRATIONS) + " ".join(m[1] for m in CODEX)
        self.assertIn("pdp_step", sql)
        self.assertFalse((BASE_DIR / "docs" / "historique").exists())
        self.assertTrue((BASE_DIR / "docs" / "DECISIONS_ANTERIEURES.md").exists())

    def test_04_text_logo_and_themes(self):
        app = (BASE_DIR / "static" / "js" / "app.js").read_text("utf-8")
        self.assertIn('class: "da-logo"', app)
        i18n = (BASE_DIR / "static" / "js" / "tools" / "i18n.js").read_text("utf-8")
        self.assertIn("Thème par défaut", i18n)  # 0.60.48 (D-O-057): the themes are named in Paramètres
        from core import prefs
        self.assertEqual(prefs.CHOICES["theme"][:2], ("carnet", "terminal"))

    def test_05_about(self):
        about = (BASE_DIR / "static" / "js" / "about" / "about.js").read_text("utf-8")
        for words in ("Jean-Philippe Desbiens", "Claude Opus 5.5", "octobre 2026", 'data-new'):
            self.assertIn(words, about)

    def test_05b_mit_license(self):
        text = (BASE_DIR / "LICENSE").read_text("utf-8")
        self.assertTrue(text.startswith("MIT License"))
        self.assertIn("Copyright (c) 2026 Jean-Philippe Desbiens", text)
        self.assertIn("0.60.01-license", (BASE_DIR / "static" / "js" / "about" / "about.js").read_text("utf-8"))

    def test_06_generator_pdp(self):
        from modules.codex import catalog
        codes = {code for _g, types in catalog.DOC_GROUPS for code, *_ in types}
        self.assertTrue({"LCV", "CRV", "PDR", "CDR", "VVR", "CDCF"} <= codes)  # 0.60.09 (D-O-021)
        self.assertEqual(catalog.svn_path("01_Discovery", "01", "00", "CHAUF"), "Documents/01_Discovery/01-00_CHAUF/")

    def test_07_time_codes_follow_the_pdp(self):
        from modules.timesheet import catalog
        keys = [t["key"] for t in catalog.task_list(catalog.DEFAULT_SET)]
        self.assertEqual(keys[0], "A-01")
        self.assertEqual(keys[-1], "D-21")
        self.assertEqual({k[0] for k in keys}, {"A", "B", "C", "D"})

    def test_08_example_team(self):
        text = (BASE_DIR / "deploy" / "utilisateurs_exemple.txt").read_text("utf-8")
        for name, profile in (("nina", "Génie mécanique"), ("lea", "Génie électrique"), ("hugo", "Design industriel"),
                              ("alexis", "Génie informatique")):
            self.assertRegex(text, r"(?m)^profil\s+{} \| {}$".format(name, profile))
        admin_js = (BASE_DIR / "static" / "js" / "admin.js").read_text("utf-8")
        self.assertIn("0.60.01-study-profile", admin_js)
        self.assertIn("Profil d'études", admin_js)

    def test_08b_website(self):
        """D-O-015: the website is its own deliverable in site/, built from tools/site/, self-contained."""
        import subprocess
        names = ("index.html", "installation.html", "guide.html", "installer.md")
        before = {n: (BASE_DIR / "site" / n).read_text("utf-8") for n in names + ("install.sh",)}
        before.update({"en/" + n: (BASE_DIR / "site" / "en" / n).read_text("utf-8") for n in names})  # D-O-017
        subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build_site.py")], check=True, capture_output=True)
        for name, old in before.items():
            page = (BASE_DIR / "site" / name).read_text("utf-8")
            self.assertEqual(page, old, "site/{} is not up to date: python3 tools/build_site.py".format(name))
            self.assertNotRegex(page, r'<script[^>]+src=|<link(?![^>]*rel="alternate")[^>]+href="http|url\((?:\'|")?http')  # nothing loaded from outside
            self.assertNotIn("{{", page)
        index = before["index.html"]
        for part in ('id="descente"', 'class="level"', 'id="journee"', 'id="chaine"', 'id="outils"', 'id="term"'):
            self.assertIn(part, index)
        page = before["installation.html"]
        for part in ('name="dest" value="online"', 'name="dest" value="local"', 'name="dest" value="windows"', 'name="pc" value="win"',
                     'name="vps" value="oracle"', 'id="agent-text"', "install.sh | sudo bash -s --", "-- --local", 'data-where="pc"',
                     'data-where="srv"', 'data-dest="windows"', 'data-pc="mac"'):  # 0.60.39: 5 steps; 0.60.44: 3 places, 3 computers
            self.assertIn(part, page)
        from tools import build_site
        script = (BASE_DIR / "site" / "install.sh").read_text("utf-8")
        self.assertIn('REPO="${{DA_REPO:-{}.git}}"'.format(build_site.REPO), script)
        self.assertEqual(subprocess.run(["bash", "-n", str(BASE_DIR / "site" / "install.sh")]).returncode, 0)
        agent = (BASE_DIR / "site" / "installer.md").read_text("utf-8")
        self.assertIn(build_site.SITE_URL + "/install.sh", agent)
        self.assertIn("Ne demandez jamais un mot de passe", agent)
        self.assertTrue((BASE_DIR / ".github" / "workflows" / "pages.yml").exists())
        # D-O-017: the English pages, the FR | EN switch both ways, the English messages of the script
        self.assertIn('<html lang="en">', before["en/index.html"])
        self.assertIn('class="lang" href="en/index.html"', index)
        self.assertIn('class="lang" href="../installation.html"', before["en/installation.html"])
        self.assertIn('hreflang="en" href="{}/en/guide.html"'.format(build_site.SITE_URL), before["guide.html"])
        for part in ('id="descente"', 'id="journee"', 'id="chaine"', 'id="outils"', "Eleven tools", "hot glue gun dropped"):
            self.assertIn(part, before["en/index.html"])
        self.assertIn("sudo DA_LANG=en bash -s --", before["en/installation.html"])
        self.assertIn("Never ask for a password", before["en/installer.md"])
        self.assertIn(build_site.SITE_URL + "/en/installation.html", before["en/installer.md"])
        install = (BASE_DIR / "deploy" / "install.sh").read_text("utf-8")
        for part in ("certbot certonly", '"dev_mode": False', "systemctl enable --now", "INITIAL_ADMIN_PASSWORD.txt", "--essai",
                     "git clone --depth 1", 'DA_LANG:-fr', '"Error:"'):
            self.assertIn(part, install)

    def test_09_files_stay_short(self):
        for f in scanned_files():
            if f.suffix in (".py", ".js") and "apps" not in f.parts:
                self.assertLess(len(f.read_text("utf-8").splitlines()), 500, f)


class ExampleSiteTest(unittest.TestCase):
    """The development start: EQP, the four students with their profile, the generic requirements."""

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
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        from tools import seed_demo
        cls.created = seed_demo.run(argparse.Namespace(url=cls.url, user="admin", password="admin"))
        cls.again = seed_demo.run(argparse.Namespace(url=cls.url, user="admin", password="admin"))
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_team_and_profiles(self):
        self.assertEqual(sorted(self.created), ["alexis", "hugo", "lea", "nina"])
        self.assertEqual(self.again, {})  # idempotent
        users = {u["username"]: u for u in self.admin.get("/api/admin/users")["users"]}
        self.assertEqual(users["hugo"]["study_profile"], "Design industriel")
        uid = users["alexis"]["id"]
        self.admin.patch("/api/admin/users/{}".format(uid), {"study_profile": "Génie robotique"})
        self.assertEqual({u["username"]: u for u in self.admin.get("/api/admin/users")["users"]}["alexis"]["study_profile"],
                         "Génie robotique")
        acts = [e["action"] for e in self.admin.get("/api/admin/audit?limit=20")["entries"]]
        self.assertIn("user_updated", acts)

    def test_02_generic_requirements_in_eqp(self):
        pid = next(p["id"] for p in self.admin.get("/api/admin/projects")["projects"] if p["key"] == "EQP")
        reqs = self.admin.get("/api/agile/p/{}/goldmine".format(pid))["requirements"]
        ids = {r["external_id"] for r in reqs}
        self.assertIn("GR-012", ids)
        self.assertIn("GN-001", ids)
        from tools import generic_requirements
        self.assertEqual(len(ids), len(generic_requirements.all_requirements()))

    def test_03_example_spaces(self):
        keys = {p["key"] for p in self.admin.get("/api/admin/projects")["projects"]}
        # 0.60.41 (D-O-050): no TESTING, TOOLS, TRAINING nor INT Space; HeadLamp holds the reference content
        self.assertEqual(keys, {"EQP", "DEMO"})

    def test_04_unknown_theme_falls_back(self):
        from core import prefs
        with db.connect() as conn:
            uid = conn.execute("SELECT id FROM users WHERE username = 'nina'").fetchone()[0]
            conn.execute("INSERT OR REPLACE INTO user_prefs (user_id, prefs, updated_at) VALUES (?, ?, 'x')", (uid, '{"theme": "neon"}'))
            self.assertEqual(prefs.get(conn, uid)["theme"], "carnet")  # an unknown theme falls back to the default


    def test_05_funding_claim_justified_hour_by_hour(self):
        """A start-up team claims its hours on a funded project: Funding Space + Budget Lines, then the Excel export
        and the Word report justify every claimed hour with its range; the leave is never claimed."""
        import datetime as dt
        import io
        import zipfile
        from modules.exploration import xlsx
        fs = self.admin.post("/api/timesheet/budget/sets", {"label": "Programme PARI — prototype"})
        self.admin.post("/api/timesheet/budget/lines", {"set_id": fs["id"], "code": "PARI-01", "label": "Conception du prototype"})
        self.admin.post("/api/timesheet/budget/lines", {"set_id": fs["id"], "code": "PARI-02", "label": "Essais du prototype"})
        projects = {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}
        self.admin.put("/api/timesheet/projects/{}".format(projects["EQP"]), {"task_set": fs["key"], "organism": "CNRC-PARI",
                                                                             "contract_ref": "PARI-2026-01"})
        monday = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat()
        for code, hours, text in (("PARI-01", 3, "Modèle CAO du boîtier rev A"), ("PARI-02", 2.5, "Essai de chute, 10 chutes")):
            self.admin.post("/api/timesheet/entries", {"work_date": monday, "project_id": projects["EQP"], "task_key": code,
                                                       "hours": hours, "description": text})
        self.admin.post("/api/timesheet/entries", {"work_date": monday, "project_id": projects["EQP"], "task_key": "INT-VAC",
                                                   "hours": 4, "description": "Vacances"})
        query = "from={0}&to={0}&status=all&tasks=PARI-01,PARI-02".format(monday)
        status, _h, data = self.admin.raw_get("/api/timesheet/export.xlsx?" + query)
        self.assertEqual(status, 200)
        sheets = xlsx.read(data)
        lines = " ".join(" ".join(map(str, r)) for r in sheets["Budget Lines"])
        for text in ("PARI-01", "Modèle CAO du boîtier rev A", "Essai de chute, 10 chutes", "5.5"):
            self.assertIn(text, lines)
        self.assertNotIn("Vacances", " ".join(" ".join(map(str, r)) for r in sheets["Détail"]))
        self.assertIn("CNRC-PARI", " ".join(" ".join(map(str, r)) for r in sheets["Sommaire"]))
        status, _h, doc = self.admin.raw_get("/api/timesheet/report.docx?{}&recipient_type=grant&recipient=CNRC-PARI"
                                             "&recipient_ref=PARI-2026-01&lang=fr".format(query))
        self.assertEqual(status, 200)
        body = zipfile.ZipFile(io.BytesIO(doc)).read("word/document.xml").decode("utf-8")
        for text in ("CNRC-PARI", "PARI-2026-01", "Sommaire par Budget Line", "Essai de chute, 10 chutes", "Attestation"):
            self.assertIn(text, body)
        self.assertNotIn("INT-VAC", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
