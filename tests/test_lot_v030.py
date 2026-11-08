"""0.40.0: test plans for an external supplier (D-A-048) and PDF store (core lot v0.20).

    python -m unittest tests.test_lot_v030 -v
"""
import io
import sys
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


class LotV030Test(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status
        return 200

    def upload(self, path, data, name):
        req = urllib.request.Request(self.url + path, data=data, method="POST",
                                     headers={"Content-Type": "application/pdf", "X-File-Name": name,
                                              "X-CSRF-Token": self.admin.csrf})
        try:
            with self.admin.opener.open(req) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def client_upload(self, path, data, name, full=False):
        try:
            out = self.admin.upload(path, data, "application/octet-stream", name)
        except ApiFailure as exc:
            return exc.status
        return out if full else 200

    def download(self, path):
        with self.admin.opener.open(self.url + path) as resp:
            return resp.read()

    def test_plan_cycle(self):
        tests = [t["test_id"] for t in self.admin.get("/api/testing/tests")["tests"] if t["subject"] == "env"][:3]
        tests.append("TST-CUS-01")
        self.assertEqual(self.status(lambda: self.admin.post("/api/testing/plans", {"tests": tests, "location": "NOPE"})), 400)
        self.assertEqual(self.status(lambda: self.admin.post("/api/testing/plans", {"tests": ["TST-XXX-99"], "location": "EXT"})), 400)
        code = self.admin.post("/api/testing/plans", {"title": "Environmental Campaign", "location": "EXT", "tests": tests,
                                                      "purpose": "Qualify the product against its environmental requirements."})["code"]
        self.assertEqual(code, "TP-001")
        doc = zipfile.ZipFile(io.BytesIO(self.download("/api/testing/plans/{}/plan.docx".format(code)))).read(
            "word/document.xml").decode("utf-8")
        for text in ("EXT", "Environmental Campaign", tests[0], "Test Procedures", "À COMPLÉTER", "Approvals",
                     "Qualify the product", "Acronyms"):
            self.assertIn(text, doc)
        self.assertNotIn("Tests Covered", doc)  # the procedure page's own table is left out
        base = "/api/testing/plans/{}".format(code)
        self.assertEqual(self.upload(base + "/results", PDF, "resultats.pdf"), 409)  # not sent yet
        self.admin.post(base + "/status", {"status": "sent"})
        self.assertEqual(self.status(lambda: self.admin.patch(base, {"location": "LAB"})), 409)  # draft only
        self.assertEqual(self.status(lambda: self.admin.post(base + "/status", {"status": "closed"})), 400)
        self.assertEqual(self.upload(base + "/results", b"\x89PNG\r\n\x1a\n...", "image.png"), 415)
        self.assertEqual(self.upload(base + "/results", PDF, "EXT_rapport.pdf"), 200)
        plan = self.admin.get(base)["plan"]
        self.assertEqual(plan["status"], "results")
        self.assertEqual(plan["results_name"], "EXT_rapport.pdf")
        self.assertEqual(self.download(base + "/results.pdf"), PDF)
        # 0.60.90 (D-O-096): closing needs a bundle per prototype tested, a result per test, evidence behind each result
        self.assertEqual(self.status(lambda: self.admin.post(base + "/status", {"status": "closed"})), 409)
        plan = self.admin.get(base)["plan"]
        bundle = self.admin.post(base + "/bundles", {"proto": "P2-B07", "serial": "SN-12"})["id"]
        self.assertEqual(self.status(lambda: self.admin.post(base + "/bundles", {"proto": "p2-b07"})), 409)  # one per proto
        self.assertEqual(self.status(lambda: self.admin.post(base + "/status", {"status": "closed"})), 409)  # no results yet
        docx = io.BytesIO()
        with zipfile.ZipFile(docx, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("word/document.xml", "<w:document/>")
        macro = io.BytesIO()
        with zipfile.ZipFile(macro, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("word/vbaProject.bin", "x")
        self.assertEqual(self.client_upload(base + "/evidence", macro.getvalue(), "macro.docm"), 415)
        self.assertEqual(self.client_upload(base + "/evidence", b"MZ\x90\x00\x03\x00\x00\x00", "virus.exe"), 415)
        ev = self.client_upload(base + "/evidence", docx.getvalue(), "rapport_rempli.docx", full=True)
        txt = self.client_upload(base + "/evidence", b"mesure;1.2\n", "mesures.csv", full=True)
        self.assertEqual(self.download(base + "/evidence/{}/file".format(ev["id"])), docx.getvalue())
        for i, t in enumerate(plan["tests"]):
            path = "{}/bundles/{}/results/{}".format(base, bundle, t)
            self.assertEqual(self.status(lambda: self.admin.put(path, {"result": "BOGUS"})), 400)
            if i == 0:
                self.admin.put(path, {"result": "derogation", "evidence": [ev["id"]]})  # no note yet
            else:
                self.admin.put(path, {"result": "passed", "evidence": [ev["id"], txt["id"]]})
        blockers = self.admin.get(base)["plan"]["blockers"]
        self.assertEqual(len(blockers), 1)
        self.assertIn("justification", blockers[0])
        self.assertEqual(self.status(lambda: self.admin.post(base + "/status", {"status": "closed"})), 409)
        self.assertEqual(self.status(lambda: self.admin.delete(base + "/evidence/{}".format(ev["id"]))), 409)  # supports a result
        self.admin.put("{}/bundles/{}/results/{}".format(base, bundle, plan["tests"][0]),
                       {"result": "derogation", "note": "Écart accepté par le client", "evidence": [ev["id"]]})
        self.admin.post(base + "/status", {"status": "closed"})
        self.assertEqual(self.admin.get(base)["plan"]["status"], "closed")
        self.assertEqual(self.status(lambda: self.admin.post(base + "/bundles", {"proto": "P3"})), 409)  # closed: read only
        summary = zipfile.ZipFile(io.BytesIO(self.download(base + "/results-summary.docx"))).read("word/document.xml").decode("utf-8")
        for text in ("P2-B07", "SN-12", "Passed with derogation", "Écart accepté par le client", "rapport_rempli.docx", "mesures.csv"):
            self.assertIn(text, summary)
        # 0.60.91 (D-O-097): the results show on the record of the test and in the verification of the requirements
        record = self.admin.get("/api/testing/tests/" + plan["tests"][0])
        self.assertEqual(record["verdict"], "derogation")
        self.assertEqual(record["executions"][0]["proto"], "P2-B07")
        self.assertEqual(self.admin.get("/api/testing/tests/" + plan["tests"][1])["verdict"], "passed")
        ver = self.admin.get("/api/testing/verification")
        self.assertIn("requirements", ver)
        self.assertEqual(set(ver["counts"]), {"verified", "derogation", "failed", "partial", "not_run"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
