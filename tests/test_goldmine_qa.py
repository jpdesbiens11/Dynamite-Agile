"""Goldmine question & answer register and client round trip (D-B-037).

    python -m unittest tests.test_goldmine_qa -v
"""
import datetime as dt
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.exploration import xlsx  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

STAMP = re.compile(r"^\d{8}-[A-Z]{2,4}$")


class GoldmineQaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "q.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.admin.put("/api/me/prefs", {"initials": "JDE"})
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "REQ", "name": "Spec client", "description": ""})
        pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["REQ"]
        cls.base = "/api/agile/p/{}".format(pid)
        cls.admin.post(cls.base + "/init")
        cls.admin.post(cls.base + "/goldmine/setup")
        for n in range(3):
            cls.admin.post(cls.base + "/goldmine/requirements", {"title": "Tension {}".format(n),
                                                                  "statement": "Le produit doit fournir [TBD] V ({}).".format(n)})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def step(self, number, name):
        issue = self.admin.get(self.base + "/issues/{}".format(number))["issue"]
        t = next(t for t in issue["transitions"] if t["to_name"] == name)
        return self.admin.post(self.base + "/issues/{}/transition".format(number), {"transition_id": t["id"]})

    def test_01_register_and_guard(self):
        q = self.admin.post(self.base + "/issues/1/qa", {"direction": "team", "question": "400 V ± 5 % ?", "blocking": True})
        self.assertEqual((q["ref"], q["req_key"], q["waiting_on"]), ("Qteam-001", "REQ-1", "client"))
        self.assertTrue(STAMP.match(q["asked_stamp"]) and q["asked_stamp"].endswith("-JDE"), q["asked_stamp"])
        self.assertEqual(q["asked_stamp"][:8], dt.date.today().strftime("%d%m%Y"))
        self.step(1, "In Analysis")
        self.step(1, "Customer Clarification")
        with self.assertRaises(ApiFailure) as err:  # a question is still open
            self.step(1, "In Analysis")
        self.assertEqual(err.exception.status, 409)
        a = self.admin.post(self.base + "/qa/{}/answer".format(q["id"]), {"answer": "Confirmé", "external_name": "Marc Tremblay"})
        self.assertEqual((a["status"], a["answered_who"], a["waiting_on"]), ("answered", "Marc Tremblay", "team"))
        self.assertTrue(a["answered_stamp"].endswith("-MTR"))
        closed = self.admin.post(self.base + "/qa/{}/close".format(q["id"]), {})
        self.assertEqual(closed["status"], "closed")
        self.assertEqual([e["kind"] for e in closed["events"]], ["question", "answer", "close"])
        self.step(1, "In Analysis")  # all closed: allowed
        cust = self.admin.post(self.base + "/issues/2/qa", {"direction": "cust", "question": "Redondance ?", "external_name": "Client X"})
        self.assertEqual((cust["ref"], cust["waiting_on"]), ("Qcust-001", "team"))
        data = self.admin.get(self.base + "/qa")
        self.assertEqual(data["counts"]["team"], 1)
        self.assertEqual(len(self.admin.get(self.base + "/qa?issue=2")["items"]), 1)
        with self.assertRaises(ApiFailure):
            self.admin.post(self.base + "/issues/2/qa", {"direction": "xx", "question": "?"})

    def test_02_client_round_trip(self):
        """D-B-044: one Q&R table, every status, nothing locked; import = diff, idempotent, archived."""
        h = self.admin.post(self.base + "/issues/3/qa", {"direction": "team", "question": "Plage de température ?"})
        cust = next(q for q in self.admin.get(self.base + "/qa")["items"] if q["ref"] == "Qcust-001")
        self.admin.post(self.base + "/qa/{}/answer".format(cust["id"]), {"answer": "Deux capteurs par module."})
        st, _h, raw = self.admin.raw_get(self.base + "/qa/client.xlsx")
        self.assertEqual(st, 200)
        sheets = xlsx.read(raw)
        self.assertTrue({"Lisez-moi", "Q&R", "Synthèse", "Requirements"} <= set(sheets))
        table = sheets["Q&R"]
        head = table[0]
        refs = [r[0] for r in table[1:] if r and r[0]]
        self.assertEqual(sorted(refs), sorted(["Qteam-001", "Qteam-002", "Qcust-001"]))  # closed ones included
        col = {name: head.index(name) for name in head}

        def row_of(ref):
            r = next(r for r in table[1:] if r and r[0] == ref)
            return list(r) + [""] * (len(head) - len(r))
        rows = [head]
        a = row_of(h["ref"]); a[col["Réponse"]] = "-30 °C à +55 °C"; a[col["Vos initiales"]] = "MTR"; rows.append(a)
        b = row_of("Qcust-001"); b[col["Status"]] = "Close"; b[col["Commentaire / suivi"]] = "Merci, clair."; rows.append(b)
        c = row_of("Qteam-001"); rows.append(c)  # unchanged (closed stays closed)
        new = [""] * len(head); new[col["Requirement Key"]] = "REQ-1"; new[col["Question"]] = "Et en usage continu ?"
        new[col["Vos initiales"]] = "MTR"; rows.append(new)
        sheet = xlsx.Sheet("Q&R")
        for r in rows:
            sheet.add(*r)
        data = xlsx.write([sheet])
        dry = self.admin.upload(self.base + "/qa/import?dry_run=1", data, "application/octet-stream", "retour.xlsx")
        self.assertEqual(dry["summary"], {"answer": 1, "comment": 1, "status": 1, "unchanged": 1, "create": 1}, dry["lines"])
        self.assertEqual(self.admin.get(self.base + "/qa")["counts"]["all"], 3)  # nothing written yet
        res = self.admin.upload(self.base + "/qa/import?dry_run=0", data, "application/octet-stream", "retour.xlsx")
        self.assertTrue(res["archive"].endswith("_import_QR.xlsx"))
        items = {q["ref"]: q for q in self.admin.get(self.base + "/qa")["items"]}
        self.assertEqual((items[h["ref"]]["answer"], items[h["ref"]]["status"]), ("-30 °C à +55 °C", "answered"))
        self.assertTrue(items[h["ref"]]["answered_stamp"].endswith("-MTR"))
        self.assertEqual(items["Qcust-001"]["status"], "closed")
        self.assertIn("comment", [e["kind"] for e in items["Qcust-001"]["events"]])
        self.assertEqual(items["Qcust-002"]["question"], "Et en usage continu ?")
        again = self.admin.upload(self.base + "/qa/import?dry_run=1", data, "application/octet-stream", "retour.xlsx")
        self.assertEqual(set(again["summary"]), {"unchanged"}, again["lines"])
        archives = self.admin.get(self.base + "/qa/archives")["archives"]
        self.assertTrue(any(a["kind"] == "Import" for a in archives) and any(a["kind"] == "Export" for a in archives))
        st, _h, back = self.admin.raw_get(self.base + "/qa/archives/" + archives[0]["name"])
        self.assertEqual(st, 200)
        st, _h, _b = self.admin.raw_get(self.base + "/qa/archives/..%2Fsecret.xlsx")
        self.assertEqual(st, 404)
        with self.assertRaises(ApiFailure):
            self.admin.upload(self.base + "/qa/import?dry_run=1", b"not a workbook", "application/octet-stream", "x.xlsx")

    def test_02b_cancel_revert(self):
        q = self.admin.post(self.base + "/issues/2/qa", {"direction": "team", "question": "Masse visée ?"})
        self.admin.post(self.base + "/qa/{}/answer".format(q["id"]), {"answer": "12 kg"})
        r = self.admin.post(self.base + "/qa/{}/reopen".format(q["id"]), {"note": "Préciser la tolérance"})
        self.assertEqual(r["status"], "open")
        r = self.admin.post(self.base + "/qa/{}/revert".format(q["id"]), {})  # undo the reopening
        self.assertEqual(r["status"], "answered")
        r = self.admin.post(self.base + "/qa/{}/reopen".format(q["id"]), {})
        r = self.admin.post(self.base + "/qa/{}/close".format(q["id"]), {})  # close straight from « open »
        self.assertEqual(r["status"], "closed")
        r = self.admin.post(self.base + "/qa/{}/reopen".format(q["id"]), {})
        r = self.admin.post(self.base + "/qa/{}/cancel".format(q["id"]), {"note": "Sans objet"})
        self.assertEqual((r["status"], r["waiting_on"]), ("cancelled", ""))
        self.assertEqual([e["kind"] for e in r["events"]][-2:], ["reopen", "cancel"])
        with self.assertRaises(ApiFailure):
            self.admin.post(self.base + "/qa/{}/answer".format(q["id"]), {"answer": "x"})
        self.assertEqual(self.admin.get(self.base + "/qa")["counts"]["cancelled"], 1)

    def test_03_register(self):
        st, _h, raw = self.admin.raw_get(self.base + "/qa/register.xlsx")
        self.assertEqual(st, 200)
        sheets = xlsx.read(raw)
        self.assertIn("Registre Q&R", sheets)
        self.assertGreaterEqual(len(sheets["Historique"]), 6)
        self.assertTrue(all(STAMP.match(r[8]) for r in sheets["Registre Q&R"][1:]))


if __name__ == "__main__":
    unittest.main()
