"""0.60.94 (D-O-100): evidence of a test plan -- the screen's addresses, any type of file under its own cap, network
references for larger files, newer versions under the same evidence, removal out of the results.

    python -m unittest tests.test_testing_evidence -v
"""
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup, update  # noqa: E402
from core.config import load_config  # noqa: E402
from modules import testing  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

MB = 1048576


class ScreenAddressTest(unittest.TestCase):
    def test_space_query_stays_at_the_end(self):
        # T.api(x) adds « ?space=KEY »; anything glued after it lands in the query string (the 405 of 0.60.90)
        for path in sorted((BASE_DIR / "static" / "js" / "testing").glob("*.js")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"T\.api\([^()]*(\([^()]*\)[^()]*)*\)\s*\+", text), path.name)
            self.assertNotIn("base + ", text, path.name)
        self.assertIn("/js/testing/testing_evidence.js", [s for m in modules.MODULE_MANIFEST for s in m.get("scripts", [])])


class MigrationTest(unittest.TestCase):
    def test_evidence_rows_survive_the_rebuild(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY); CREATE TABLE attachments (id INTEGER PRIMARY KEY);"
                           "CREATE TABLE testing_plans (id INTEGER PRIMARY KEY);"
                           "INSERT INTO users VALUES (1); INSERT INTO attachments VALUES (5); INSERT INTO testing_plans VALUES (3);")
        steps = dict(testing.MIGRATIONS)
        conn.executescript(steps[6])
        conn.execute("INSERT INTO testing_evidence (id, plan_id, attachment_id, name, note, created_by, created_at) "
                     "VALUES (9, 3, 5, 'rapport.docx', 'v finale', 1, '2026-11-08')")
        self.assertIsNone(update.DESTRUCTIVE.search(steps[7]))  # an online update refuses any DROP
        conn.executescript(steps[7])
        row = conn.execute("SELECT id, plan_id, attachment_id, name, note, kind, version, history FROM testing_evidence").fetchone()
        self.assertEqual(row, (9, 3, 5, "rapport.docx", "v finale", "file", 1, "[]"))


class EvidenceApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        cfg["max_upload_mb"], cfg["max_evidence_mb"] = 1, 3  # evidence has its own cap, above the usual one
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

    def fails(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status, str(exc)
        return 200, ""

    def download(self, path):
        try:
            with self.admin.opener.open(self.url + path) as resp:
                return resp.read(), resp.headers.get("Content-Disposition", "")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def test_evidence_cycle(self):
        tests = [t["test_id"] for t in self.admin.get("/api/testing/tests")["tests"] if t["subject"] == "env"][:2]
        code = self.admin.post("/api/testing/plans", {"title": "Drop campaign", "location": "EXT", "tests": tests})["code"]
        base = "/api/testing/plans/{}".format(code)
        up = lambda path, data, name: self.admin.upload(base + path, data, "application/octet-stream", name)  # noqa: E731
        self.assertEqual(self.fails(lambda: up("/evidence", b"x", "a.txt"))[0], 409)  # draft plan: not yet
        self.admin.post(base + "/status", {"status": "sent"})

        # any type, up to max_evidence_mb (3 Mo here) even though max_upload_mb is 1 Mo
        raw = bytes(range(256)) * (2 * MB // 256)  # 2 Mo of binary data, no known type
        v1 = up("/evidence", raw, "mesures_brutes.bin")
        self.assertEqual(self.download(base + "/evidence/{}/file".format(v1["id"]))[0], raw)
        self.assertEqual(self.fails(lambda: up("/evidence", b"\0" * (4 * MB), "trop_gros.mp4"))[0], 413)
        plan = self.admin.get(base)["plan"]
        self.assertEqual(plan["evidence_max_mb"], 3)
        ev = plan["evidence"][0]
        self.assertEqual((ev["name"], ev["kind"], ev["version"], ev["size"], ev["history"]), ("mesures_brutes.bin", "file", 1, len(raw), []))

        # a larger file stays on the network: name, size, where it lies
        link = "\\\\labo-srv\\essais\\{}\\video_chute.mp4".format(code)
        net = self.admin.post(base + "/evidence/link", {"name": "video_chute.mp4", "link": link, "size": 412 * MB, "note": "Caméra rapide"})
        self.assertEqual(self.fails(lambda: self.admin.post(base + "/evidence/link", {"name": "x", "link": "a\nb"}))[0], 400)
        self.assertEqual(self.fails(lambda: self.admin.post(base + "/evidence/link", {"name": "x", "link": ""}))[0], 400)
        note, disposition = self.download(base + "/evidence/{}/file".format(net["id"]))  # its reference document
        self.assertIn(link, note.decode("utf-8"))
        self.assertIn("412 Mo", note.decode("utf-8"))
        self.assertIn("video_chute.mp4 - emplacement.txt", disposition)

        # results cite both; a newer version keeps the same evidence (and so the results)
        bundle = self.admin.post(base + "/bundles", {"proto": "P1"})["id"]
        result = "{}/bundles/{}/results/{}".format(base, bundle, tests[0])
        self.admin.put(result, {"result": "passed", "evidence": [v1["id"], net["id"]]})
        v2 = up("/evidence/{}/replace".format(v1["id"]), b"rev B\n", "mesures_revB.csv")
        self.assertEqual((v2["id"], v2["version"]), (v1["id"], 2))
        ev = {e["id"]: e for e in self.admin.get(base)["plan"]["evidence"]}[v1["id"]]
        self.assertEqual((ev["name"], ev["version"], [h["version"] for h in ev["history"]]), ("mesures_revB.csv", 2, [1]))
        self.assertEqual(self.download(base + "/evidence/{}/file".format(v1["id"]))[0], b"rev B\n")
        body, disposition = self.download(base + "/evidence/{}/file?version=1".format(v1["id"]))
        self.assertEqual(body, raw)
        self.assertIn("mesures_brutes.bin", disposition)
        self.assertIn("attachment", disposition)
        # the next version too heavy for the platform: it moves to the network, the earlier ones stay downloadable
        v3 = self.admin.post(base + "/evidence/{}/link".format(v1["id"]), {"link": "S:\\Essais\\mesures_revC.zip", "size": 900 * MB})
        self.assertEqual(v3["version"], 3)
        ev = {e["id"]: e for e in self.admin.get(base)["plan"]["evidence"]}[v1["id"]]
        self.assertEqual((ev["kind"], ev["link"], ev["size"], [h["version"] for h in ev["history"]]), ("link", "S:\\Essais\\mesures_revC.zip", 900 * MB, [2, 1]))
        self.assertEqual(self.download(base + "/evidence/{}/file?version=2".format(v1["id"]))[0], b"rev B\n")
        self.assertEqual(self.download(base + "/evidence/{}/file?version=7".format(v1["id"]))[0], 404)
        self.assertEqual(self.admin.get(base)["plan"]["bundles"][0]["results"][tests[0]]["evidence"], sorted([v1["id"], net["id"]]))

        # removing an evidence takes it out of the results that cited it; the blockers say so
        out = self.admin.delete(base + "/evidence/{}".format(net["id"]))
        self.assertEqual(out["results"], ["P1 · " + tests[0]])
        plan = self.admin.get(base)["plan"]
        self.assertEqual(plan["bundles"][0]["results"][tests[0]]["evidence"], [v1["id"]])
        self.assertEqual([e["id"] for e in plan["evidence"]], [v1["id"]])
        self.admin.delete(base + "/evidence/{}".format(v1["id"]))
        self.assertTrue(any("aucune preuve" in b for b in self.admin.get(base)["plan"]["blockers"]))

        # the usual cap still holds on the other upload routes (the results PDF: max_upload_mb)
        self.assertEqual(self.fails(lambda: up("/results", b"%PDF-1.4\n" + b"0" * (2 * MB), "r.pdf"))[0], 413)
        # every write is in the audit log
        with db.connect() as conn:
            actions = {r[0] for r in conn.execute("SELECT action FROM audit_log WHERE action LIKE 'testing_evidence_%'")}
        self.assertTrue({"testing_evidence_added", "testing_evidence_linked", "testing_evidence_replaced",
                         "testing_evidence_deleted"} <= actions, actions)

    def test_restore_keeps_results_and_versions(self):
        # a Space restored (here under a new key) renumbers evidence and attachments: results and old versions follow
        self.admin.post("/api/admin/projects", {"provision": False, "key": "TPS", "name": "Essais", "description": ""})
        tests = [t["test_id"] for t in self.admin.get("/api/testing/tests?space=TPS")["tests"] if t["subject"] == "env"][:1]
        code = self.admin.post("/api/testing/plans?space=TPS", {"title": "Restore", "location": "EXT", "tests": tests})["code"]
        base = "/api/testing/plans/{}".format(code)
        q = "?space=TPS"
        self.admin.post(base + "/status" + q, {"status": "sent"})
        ev = self.admin.upload(base + "/evidence" + q, b"version A\n", "application/octet-stream", "rapport.txt")
        self.admin.upload(base + "/evidence/{}/replace{}".format(ev["id"], q), b"version B\n", "application/octet-stream", "rapport_B.txt")
        # a later evidence elsewhere holds the highest id, so the restored rows get new numbers
        other = self.admin.post("/api/testing/plans", {"title": "Autre", "location": "EXT", "tests": tests})["code"]
        self.admin.post("/api/testing/plans/{}/status".format(other), {"status": "sent"})
        self.admin.upload("/api/testing/plans/{}/evidence".format(other), b"autre\n", "application/octet-stream", "autre.txt")
        bundle = self.admin.post(base + "/bundles" + q, {"proto": "R1"})["id"]
        self.admin.put("{}/bundles/{}/results/{}{}".format(base, bundle, tests[0], q), {"result": "passed", "evidence": [ev["id"]]})
        with db.connect() as conn:
            pid = conn.execute("SELECT id FROM projects WHERE key = 'TPS'").fetchone()[0]
        raw = self.download("/api/admin/projects/{}/backup.zip".format(pid))[0]
        self.admin.patch("/api/admin/projects/{}".format(pid), {"is_archived": True})
        self.admin.post("/api/admin/projects/{}/delete".format(pid), {"confirm_key": "TPS"})  # plan codes are platform-wide
        self.admin.upload("/api/admin/restore?key=TPR", raw, "application/zip", "tps.zip")
        plan = self.admin.get(base + "?space=TPR")["plan"]
        new_id = plan["evidence"][-1]["id"]
        self.assertNotEqual(new_id, ev["id"])
        self.assertEqual(plan["bundles"][-1]["results"][tests[0]]["evidence"], [new_id])
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(self.download(base + "/evidence/{}/file?space=TPR".format(new_id))[0], b"version B\n")
        self.assertEqual(self.download(base + "/evidence/{}/file?version=1&space=TPR".format(new_id))[0], b"version A\n")


if __name__ == "__main__":
    unittest.main()
