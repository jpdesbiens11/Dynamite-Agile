"""0.60.101 (D-O-108): Diamond -- the classes CC / SC of the DFMEA: the rule proposes (never assigns), a person confirms or
refuses with a reason (a refusal is kept, the history too), the rules and the customer dictionary of the Space (AIAG, Ford,
aerospace; a customer of the team), the symbols in the payload and the CSV, the filters' counts, the checks, the rights,
the copy of a Space, the search, and the Rover's CDR decisions in DEMO (once, never over a person's decision)."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, spacecopy, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import classes as CL  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class RuleTest(unittest.TestCase):
    def test_01_proposal(self):
        r = dict(CL.RULES)
        cases = {(9, 1): "CC", (10, None): "CC", (8, 4): "SC", (5, 4): "SC", (5, 3): "", (4, 9): "", (8, 3): "", (None, 9): ""}
        for (s, o), want in cases.items():
            self.assertEqual(CL.propose(s, o, r), want, (s, o))
        r.update(cc_severity=10, sc_severity=6, sc_occurrence=5)  # a customer with its own rule
        self.assertEqual((CL.propose(9, 5, r), CL.propose(9, 4, r), CL.propose(5, 9, r), CL.propose(10, 1, r)), ("SC", "", "", "CC"))

    def test_02_status(self):
        row = {"class_state": "", "class_code": ""}
        self.assertEqual(CL.status(row, "CC"), "proposed")
        self.assertEqual(CL.status(row, ""), "")
        refused = {"class_state": "refused", "class_code": "SC"}
        self.assertEqual(CL.status(refused, "SC"), "refused")  # the question was asked: no longer proposed
        self.assertEqual(CL.status(refused, "CC"), "proposed")  # S went up: a new question
        self.assertEqual(CL.status({"class_state": "confirmed", "class_code": "SC"}, ""), "confirmed")  # never undone by the rule

    def test_03_presets(self):
        codes = [p["code"] for p in CL.PRESETS]
        self.assertEqual(codes, ["aiag", "ford", "aero"])
        ford = CL.PRESETS[1]
        self.assertEqual((ford["cc_dfmea"], ford["sc_dfmea"], ford["cc_symbol"], ford["sc_symbol"]), ("YC", "YS", "CC ∇", "SC"))
        self.assertEqual((CL.PRESETS[2]["cc_symbol"], CL.PRESETS[2]["sc_symbol"]), ("CSC", "KC"))
        self.assertIn("CSR", ford["source"])  # to confirm with the customer, never asserted
        self.assertNotIn("CSR", CL.PRESETS[0]["source"])
        self.assertEqual(CL.symbol(ford, "CC"), "YC")
        self.assertEqual(CL.symbol(ford, "CC", "process"), "CC ∇")
        self.assertEqual(CL.symbol(ford, ""), "")


class ClassApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "f.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "LAMPK", "name": "lampe"})["project"]["id"]
        cls.admin.post("/api/diamond/p/{}/example".format(cls.pid), {"name": "lampe"})
        made = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", made["temp_password"], new_password="Lecture-2026!")
        cls.base = "/api/diamond/p/{}/dfmea".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as caught:
            fn(*args)
        self.assertEqual(caught.exception.status, status, caught.exception)
        return str(caught.exception)

    def rows(self):
        return self.admin.get(self.base)["rows"]

    def test_04_proposed_never_assigned(self):
        data = self.admin.get(self.base)
        rows = data["rows"]
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["class_proposed"], CL.propose(r["severity"], r["occurrence"], CL.RULES))
            self.assertEqual((r["class_state"], r["special"]), ("", False))  # nothing becomes CC by itself
        info = data["classes"]
        self.assertEqual((info["rules"]["customer"], info["customer"]["code"], info["counts"]["special"]), ("aiag", "aiag", 0))
        self.assertEqual(info["counts"]["cc_proposed"], sum(1 for r in rows if r["class_proposed"] == "CC"))
        self.assertTrue(any("CC proposée" in c for c in data["checks"]))

    def test_05_decide_with_reason_and_history(self):
        row = next(r for r in self.rows() if r["class_proposed"] == "CC")
        url = self.base + "/rows/{}/class".format(row["id"])
        self.assertIn("Justification obligatoire", self.fails(400, self.admin.post, url, {"decision": "CC", "reason": " "}))
        self.fails(400, self.admin.post, url, {"decision": "XX", "reason": "raison"})
        self.fails(403, self.reader.post, url, {"decision": "CC", "reason": "lecteur"})
        data = self.admin.post(url, {"decision": "CC", "reason": "peut blesser une personne"})
        got = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual((got["class_status"], got["class_symbol"], got["class_by_initials"], got["special"]), ("confirmed", "CC", "ADM", True))
        self.assertEqual((got["class_severity"], got["class_occurrence"], got["class_history"]), (row["severity"], row["occurrence"], 1))
        self.assertEqual(data["classes"]["counts"]["special"], 1)
        # refuse it afterwards: the refusal is the decision now, the confirmation stays in the history
        data = self.admin.post(url, {"decision": "refused", "reason": "revu à la CDR : la norme ne s'applique pas"})
        got = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual((got["class_status"], got["class_code"], got["special"]), ("refused", "CC", False))
        hist = self.reader.get(url)["history"]
        self.assertEqual([h["state"] for h in hist], ["refused", "confirmed"])
        self.assertEqual(hist[1]["reason"], "peut blesser une personne")
        # back to the rule: proposed again, three decisions kept
        data = self.admin.post(url, {"decision": "clear", "reason": "erreur de ligne"})
        got = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual((got["class_status"], got["class_state"], got["class_history"]), ("proposed", "", 3))
        self.assertIn("Aucune décision", self.fails(400, self.admin.post, url, {"decision": "clear", "reason": "encore"}))

    def test_06_manual_class_refuse_nothing(self):
        row = next(r for r in self.rows() if not r["class_proposed"] and r["severity"])
        url = self.base + "/rows/{}/class".format(row["id"])
        self.assertIn("Rien à refuser", self.fails(400, self.admin.post, url, {"decision": "refused", "reason": "non"}))
        data = self.admin.post(url, {"decision": "SC", "reason": "exigence du client malgré la règle"})
        got = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual((got["class_status"], got["class_code"]), ("confirmed", "SC"))
        # S changes: the decision stays, the row says so
        data = self.admin.patch(self.base + "/rows/{}".format(row["id"]), {"severity": (row["severity"] % 10) + 1})
        got = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual((got["class_status"], got["class_changed"]), ("confirmed", True))
        # a confirmed class that no characteristic C-n carries is flagged (0.60.102, D-O-110)
        self.admin.patch(self.base + "/rows/{}".format(row["id"]), {"requirement": ""})
        data = self.admin.get(self.base)
        self.assertGreaterEqual(data["classes"]["counts"]["no_characteristic"], 1)
        self.assertTrue(any("sans caractéristique C-n" in c for c in data["checks"]))
        # a duplicated row is a new failure chain: its class is decided again
        dup = self.admin.post(self.base + "/rows/{}/duplicate".format(row["id"]), {})
        copy = next(r for r in dup["rows"] if r["id"] == dup["created"])
        self.assertEqual(copy["class_state"], "")

    def test_07_rules_and_customers(self):
        s = self.admin.get(self.base + "/classes")
        self.assertEqual([c["code"] for c in s["customers"]], ["aiag", "ford", "aero"])
        self.assertIn("sévérité la plus basse", self.fails(400, self.admin.patch, self.base + "/classes", {"sc_severity": 9}))
        self.fails(400, self.admin.patch, self.base + "/classes", {"cc_severity": 11})
        self.fails(400, self.admin.patch, self.base + "/classes", {"customer": "gm"})  # never assumed
        self.fails(403, self.reader.patch, self.base + "/classes", {"customer": "ford"})
        s = self.admin.patch(self.base + "/classes", {"customer": "ford", "cc_severity": 10})
        self.assertEqual((s["rules"]["customer"], s["rules"]["cc_severity"]), ("ford", 10))
        data = self.admin.get(self.base)
        confirmed = [r for r in data["rows"] if r["class_status"] == "confirmed"]
        self.assertTrue(confirmed)
        self.assertTrue(all(r["class_symbol"] == ("YC" if r["class_code"] == "CC" else "YS") for r in confirmed))
        self.assertFalse(any(r["class_proposed"] == "CC" and r["severity"] == 9 for r in data["rows"]))  # S 9 is not CC at 10
        csv = self.admin.raw_get(self.base + "/export.csv")[2].decode("utf-8-sig")
        head = csv.splitlines()[0].split(";")
        self.assertEqual(head[-4:], ["Class", "Class Status", "Décision de classe", "Justification de la classe"])
        self.assertIn(";YS;Confirmée;ADM", csv)
        # a customer of the team, its symbols from its CSR
        self.assertIn("obligatoire", self.fails(400, self.admin.post, self.base + "/classes/customers", {"name": "Client X"}))
        made = self.admin.post(self.base + "/classes/customers", {"name": "Client X", "cc_dfmea": "◆", "sc_dfmea": "◇", "cc_symbol": "◆",
                                                                  "sc_symbol": "◇", "source": "CSR révision C, § 4.2"})
        self.assertEqual(made["created"], "client-x")
        self.admin.patch(self.base + "/classes", {"customer": "client-x"})
        self.assertIn("client du Space", self.fails(409, self.admin.post, self.base + "/classes/customers/client-x/delete", {}))
        s = self.admin.patch(self.base + "/classes/customers/ford", {"cc_label": "CC selon le SCCAF"})
        ford = next(c for c in s["customers"] if c["code"] == "ford")
        self.assertEqual((ford["cc_label"], ford["edited"]), ("CC selon le SCCAF", True))
        s = self.admin.post(self.base + "/classes/customers/ford/delete", {})  # a preset: back to its start values
        ford = next(c for c in s["customers"] if c["code"] == "ford")
        self.assertEqual((ford["cc_label"], ford["edited"]), (CL.PRESETS[1]["cc_label"], False))
        self.admin.patch(self.base + "/classes", {"customer": "aiag", "cc_severity": 9})
        s = self.admin.post(self.base + "/classes/customers/client-x/delete", {})
        self.assertEqual([c["code"] for c in s["customers"]], ["aiag", "ford", "aero"])

    def test_08_copy_search_journal(self):
        for table in ("diamond_class_settings", "diamond_class_customers", "diamond_class_decisions"):
            self.assertIn(table, spacecopy.DIAMOND)
        manifest = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        for name in ("dfmea_class.js", "dfmea_classes.js"):
            self.assertIn("/js/diamond/" + name, manifest["scripts"])
            text = (BASE_DIR / "static" / "js" / "diamond" / name).read_text("utf-8")
            self.assertNotIn("innerHTML", text)
            self.assertIn('data-new": "0.60.101-', text)
        self.assertLess(manifest["scripts"].index("/js/diamond/dfmea_class.js"), manifest["scripts"].index("/js/diamond/dfmea_table.js"))
        row = next(r for r in self.rows() if r["class_proposed"])
        self.admin.post(self.base + "/rows/{}/class".format(row["id"]), {"decision": row["class_proposed"], "reason": "trace de recherche unique"})
        hits = self.admin.get("/api/search?q=" + "trace%20de%20recherche%20unique")["results"]
        self.assertTrue(any("DFMEA" in h["title"] for h in hits))
        with db.connect() as conn:
            self.assertTrue(conn.execute("SELECT 1 FROM audit_log WHERE action = 'diamond_dfmea_class'").fetchone())
        # « Copier / composer un Space »: the decisions, their history and the rules go with Diamond
        self.admin.patch(self.base + "/classes", {"sc_occurrence": 5})
        made = self.admin.post("/api/admin/spacecopy", {"key": "LAMPZ", "name": "Copie", "parts": {"diamond": "LAMPK"}})
        nb = "/api/diamond/p/{}/dfmea".format(made["project"]["id"])
        copy = self.admin.get(nb)
        self.assertEqual(copy["classes"]["rules"]["sc_occurrence"], 5)
        kept = [r for r in copy["rows"] if r["class_reason"] == "trace de recherche unique"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["class_history"], 1)
        self.assertEqual(self.admin.get(nb + "/rows/{}/class".format(kept[0]["id"]))["history"][0]["reason"], "trace de recherche unique")
        # a backup of the Space, restored as a new Space: the same (backup.collect follows the foreign keys)
        status, _headers, zipped = self.admin.raw_get("/api/admin/projects/{}/backup.zip".format(self.pid))
        self.assertEqual(status, 200)
        restored = self.admin.upload("/api/admin/restore?key=LAMPR&name=Restauree", zipped, "application/zip", "lampk.zip")
        rb = "/api/diamond/p/{}/dfmea".format(restored["project"]["id"])
        back = self.admin.get(rb)
        self.assertEqual(back["classes"]["rules"]["sc_occurrence"], 5)
        again = [r for r in back["rows"] if r["class_reason"] == "trace de recherche unique"]
        self.assertEqual((len(again), again[0]["class_history"], again[0]["class_by_initials"]), (1, 1, "ADM"))
        self.admin.patch(self.base + "/classes", {"sc_occurrence": 4})


if __name__ == "__main__":
    unittest.main()
