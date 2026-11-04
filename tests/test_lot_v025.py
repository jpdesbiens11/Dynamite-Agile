"""0.36.0: Timesheet Word report (D-A-042) -- extract of the selected budget lines in the document template, addressed
to a funding organism or a customer entered at creation.

    python -m unittest tests.test_lot_v025 -v
"""
import io
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV025Test(unittest.TestCase):
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
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "EQP", "name": "Projet d'équipe", "description": ""})
        week = cls.admin.get("/api/timesheet/week")
        gen = next(p for p in week["projects"] if p["key"] == "EQP")
        cls.day = week["days"][0]
        cls.entry = cls.admin.post("/api/timesheet/entries", {"project_id": gen["id"], "work_date": cls.day, "hours": 2.5, "task_key": "A-04",
                                                              "description": "Rédaction du rapport de subvention"})["entry"]
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur tom | Tom Test | utilisateur | actif\n"})
        c = done["created"][0]
        cls.tom = Client(cls.url)
        cls.tom.login(c["username"], c["temp_password"], "Essai-Rapport-Word-2026!")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, client, query):
        with client.opener.open(self.url + "/api/timesheet/report.docx?" + query) as resp:
            return resp.read(), resp.headers

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status
        except Exception as exc:  # urllib HTTPError from opener.open
            return getattr(exc, "code", 0)
        return 200

    def test_report(self):
        q = "from={0}&to={0}&status=all&recipient_type=grant&recipient={1}&recipient_ref={2}&lang=fr".format(
            self.day, quote("Programme Innovation Étudiante"), quote("PIE-2026-17"))
        data, headers = self.get(self.admin, q)
        self.assertIn("wordprocessingml", headers["Content-Type"])
        doc = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        for text in ("Programme Innovation Étudiante", "PIE-2026-17", "Organisme de subvention", "Sommaire par Budget Line",
                     "Rédaction du rapport de subvention", self.entry["task_key"], "2.5", "Attestation", "Acronymes"):
            self.assertIn(text, doc)
        self.assertEqual(self.status(lambda: self.get(self.admin, q.replace("recipient=", "x="))), 400)
        self.assertEqual(self.status(lambda: self.get(self.admin, q.replace("grant", "bank"))), 400)
        self.assertEqual(self.status(lambda: self.get(self.tom, q)), 403)
        en, _ = self.get(self.admin, q.replace("recipient_type=grant", "recipient_type=client").replace("lang=fr", "lang=en"))
        doc = zipfile.ZipFile(io.BytesIO(en)).read("word/document.xml").decode("utf-8")
        self.assertIn("Customer", doc)
        self.assertIn("Summary per Budget Line", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
