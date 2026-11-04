"""Client summary (D-B-001): one curated field per ticket, history of every
version, CSV export/import for tickets and Goldmine.

    python -m unittest tests.test_client_summary -v
"""
import csv
import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure as ApiError, Client  # noqa: E402


class ClientSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "SUM", "name": "Synthèse", "description": ""})
        cls.base = "/api/agile/p/{}".format(cls.admin.get("/api/admin/projects")["projects"][0]["id"])
        cls.admin.post(cls.base + "/init")
        meta = cls.admin.get(cls.base + "/meta")
        task = next(t for t in meta["types"] if t["icon_key"] == "task")
        cls.number = cls.admin.post(cls.base + "/issues", {"type_id": task["id"], "title": "T"})["number"]
        cls.issue_url = "{}/issues/{}".format(cls.base, cls.number)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def download(self, path):
        with self.admin.opener.open(self.url + self.base + path) as resp:
            return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))

    def test_01_set_and_history(self):
        r = self.admin.put(self.issue_url + "/summary", {"client_summary": "Position A\r\nligne 2  "})
        self.assertTrue(r["changed"])
        self.assertEqual(r["client_summary"], "Position A\nligne 2")
        issue = self.admin.get(self.issue_url)["issue"]
        self.assertEqual(issue["client_summary_by_name"], issue["reporter_name"])
        self.admin.put(self.issue_url + "/summary", {"client_summary": "Position B"})
        hist = [h for h in self.admin.get(self.issue_url)["issue"]["history"] if h["field"] == "client_summary"]
        # D-B-017: lightweight trace -- who/when/length, never the full text.
        self.assertIsNone(hist[0]["old_value"])
        self.assertEqual(hist[0]["new_value"], "(modifiée, 10 car.)")
        self.assertFalse(self.admin.put(self.issue_url + "/summary", {"client_summary": "Position B"})["changed"])

    def test_02_from_comment_is_traced(self):
        self.admin.post(self.issue_url + "/comments", {"body": "Réponse longue"})
        cid = self.admin.get(self.issue_url)["issue"]["comments"][-1]["id"]
        self.admin.put(self.issue_url + "/summary", {"client_summary": "Réponse", "from_comment_id": cid})
        hist = self.admin.get(self.issue_url)["issue"]["history"][0]
        self.assertIn("commentaire #{}".format(cid), hist["new_value"])
        with self.assertRaises(ApiError):
            self.admin.put(self.issue_url + "/summary", {"client_summary": "x", "from_comment_id": 99999})

    def test_03_too_long_is_refused_with_fix(self):
        with self.assertRaises(ApiError) as cm:
            self.admin.put(self.issue_url + "/summary", {"client_summary": "x" * 4001})
        self.assertIn("Correctif", str(cm.exception))

    def test_04_ticket_csv_roundtrip(self):
        self.admin.put(self.issue_url + "/summary", {"client_summary": "Export; avec « guillemets »\net saut"})
        rows = self.download("/export/tickets")
        self.assertEqual(rows[0]["client_summary"], "Export; avec « guillemets »\net saut")
        # Re-import with a changed summary: applied and traced.
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        rows[0]["client_summary"] = "Modifiée dans Excel"
        writer.writerow(rows[0])
        report = self.admin.post(self.base + "/import/tickets", {"csv": out.getvalue()})["report"]
        self.assertEqual(report[0]["status"], "mise à jour", report)
        self.assertEqual(self.admin.get(self.issue_url)["issue"]["client_summary"], "Modifiée dans Excel")

    def test_05_ticket_csv_without_column_keeps_summary(self):
        before = self.admin.get(self.issue_url)["issue"]["client_summary"]
        rows = self.download("/export/tickets")  # a v0.6 file: no client_summary column
        out = io.StringIO()
        fields = [f for f in rows[0] if f != "client_summary"]
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        rows[0]["title"] = "T renommé"
        writer.writerow(rows[0])
        report = self.admin.post(self.base + "/import/tickets", {"csv": out.getvalue()})["report"]
        self.assertEqual(report[0]["status"], "mise à jour", report)
        self.assertEqual(self.admin.get(self.issue_url)["issue"]["client_summary"], before)

    def test_06_goldmine_csv(self):
        self.admin.post(self.base + "/goldmine/setup")
        spec = "ID;Énoncé;Synthèse client\r\nSYS-1;Le produit doit tenir.;Accepté par le client le 12/09\r\n"
        report = self.admin.post(self.base + "/import/requirements", {"csv": spec})["report"]
        self.assertEqual(report[0]["status"], "créée", report)
        rows = self.download("/export/requirements")
        row = next(r for r in rows if r["external_id"] == "SYS-1")
        self.assertEqual(row["client_summary"], "Accepté par le client le 12/09")


if __name__ == "__main__":
    unittest.main()
