"""0.60.15 (D-O-027): Diamond 💎 -- the DFMEA (AIAG-VDA): the AP table, RPN, rows on the functions of the tree, add /
duplicate / move / delete, « Depuis l'arbre », « Depuis les risques », checks, CSV, the example, rights."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import dfmea_ap as AP  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class ApTableTest(unittest.TestCase):
    def test_01_table_and_severity_first(self):
        cases = {(10, 10, 10): "H", (9, 2, 1): "L", (9, 3, 5): "M", (9, 4, 1): "M", (9, 6, 1): "H", (8, 6, 1): "M", (7, 4, 2): "M",
                 (6, 8, 7): "H", (6, 8, 2): "M", (5, 6, 1): "L", (4, 4, 7): "M", (3, 9, 6): "M", (3, 9, 3): "L", (2, 6, 10): "L",
                 (1, 10, 10): "L"}
        for (s, o, d), ap in cases.items():
            self.assertEqual(AP.action_priority(s, o, d), ap, (s, o, d))
        self.assertEqual(AP.action_priority(5, None, 3), "")
        self.assertGreater(AP.rpn(1, 10, 10), AP.rpn(9, 4, 1))  # the RPN hides a severe effect...
        self.assertEqual((AP.action_priority(1, 10, 10), AP.action_priority(9, 4, 1)), ("L", "M"))  # ...the AP does not
        every = {AP.action_priority(s, o, d) for s in range(1, 11) for o in range(1, 11) for d in range(1, 11)}
        self.assertEqual(every, {"H", "M", "L"})
        legend = AP.legend()
        self.assertEqual(len(legend["table"]), 5)
        self.assertEqual(set(legend["scales"]), {"severity", "occurrence", "detection"})


class DfmeaApiTest(unittest.TestCase):
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
        mk = lambda key: cls.admin.post("/api/admin/projects", {"key": key, "name": key})["project"]["id"]
        cls.lamp, cls.own = mk("LAMPF"), mk("FMEA")
        cls.admin.post("/api/diamond/p/{}/example".format(cls.lamp), {"name": "lampe"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def base(self, pid):
        return "/api/diamond/p/{}/dfmea".format(pid)

    def test_02_example(self):
        data = self.admin.get(self.base(self.lamp))
        rows = data["rows"]
        self.assertEqual(len(rows), 7)
        self.assertEqual([r["line"] for r in rows], list(range(1, 8)))
        self.assertEqual(sorted({r["ap"] for r in rows}), ["H", "L", "M"])
        self.assertEqual((rows[0]["rpn"], rows[0]["ap"], rows[0]["function_text"], rows[0]["risk_number"]),
                         (140, "M", "Dissiper la chaleur des DEL", 1))
        self.assertTrue(all(r["function_id"] for r in rows))
        self.assertTrue(any("sans ligne" in c for c in data["checks"]))
        added = self.admin.post(self.base(self.lamp) + "/from-tree", {})
        self.assertGreater(added["added"], 0)
        self.assertFalse(any("pas encore analysée" in c for c in added["checks"]))
        again = self.admin.post(self.base(self.lamp) + "/from-tree", {})
        self.assertEqual(again["added"], 0)  # never twice

    def test_03_rows_add_duplicate_move_delete(self):
        fn = "/api/diamond/p/{}/functions".format(self.own)
        f1 = self.admin.post(fn, {"text": "Appliquer de la colle", "primary": True})["functions"][0]["id"]
        f2 = max(self.admin.post(fn, {"text": "Fondre la colle", "parent_id": f1})["functions"], key=lambda f: f["number"])["id"]
        b = self.base(self.own)
        self.assertTrue(self.admin.get(b)["checks"][0].startswith("DFMEA vide"))
        d1 = self.admin.post(b + "/rows", {"focus": "Buse", "function_id": f2, "failure_mode": "Colle figée", "severity": 6,
                                          "occurrence": 4, "detection": 3})["created"]
        d2 = self.admin.post(b + "/rows", {"focus": "Résistance", "function_id": f2})["created"]
        data = self.admin.post(b + "/rows", {"focus": "Inséré", "after_id": d1})
        self.assertEqual([r["focus"] for r in data["rows"]], ["Buse", "Inséré", "Résistance"])
        data = self.admin.post(b + "/rows/{}/duplicate".format(d1), {})
        self.assertEqual([r["focus"] for r in data["rows"]], ["Buse", "Buse", "Inséré", "Résistance"])
        copy = data["created"]
        self.assertEqual(next(r for r in data["rows"] if r["id"] == copy)["ap"], "L")
        data = self.admin.post(b + "/rows/{}/move".format(d2), {"direction": "up"})
        self.assertEqual([r["focus"] for r in data["rows"]], ["Buse", "Buse", "Résistance", "Inséré"])
        data = self.admin.post(b + "/rows/{}/move".format(d2), {"index": 0})
        self.assertEqual(data["rows"][0]["id"], d2)
        data = self.admin.post(b + "/rows/{}/delete".format(copy), {})
        self.assertEqual([r["line"] for r in data["rows"]], [1, 2, 3])
        for bad in ({"severity": 11}, {"occurrence": "x"}, {"function_id": 99999}, {"failure_mode": "x" * 401}):
            with self.assertRaises(ApiFailure) as err:
                self.admin.patch(b + "/rows/{}".format(d1), bad)
            self.assertIn("Correctif" if "failure_mode" not in bad else "caractères", err.exception.message, bad)
        data = self.admin.patch(b + "/rows/{}".format(d1), {"severity": 9, "occurrence": 6, "detection": 8})
        row = next(r for r in data["rows"] if r["id"] == d1)
        self.assertEqual((row["rpn"], row["ap"]), (432, "H"))
        self.assertTrue(any("AP High sans action" in c for c in data["checks"]))
        self.assertTrue(any("sévérité 9-10" in c for c in data["checks"]))
        status, _h, body = self.admin.raw_get(b + "/export.csv")
        self.assertEqual(status, 200)
        self.assertIn("Higher-Level Element;Focus Element;Lower-Level Element", body.decode("utf-8-sig"))

    def test_04_from_risks(self):
        b = "/api/diamond/p/{}/risks".format(self.own)
        rid = self.admin.post(b, {"title": "Buse bouchée", "cause": "colle de mauvaise qualité", "consequence": "aucun débit",
                                  "probability": 3, "impact": 4, "to_dfmea": True})["created"]
        self.assertTrue(any("Depuis les risques" in c for c in self.admin.get(self.base(self.own))["checks"]))
        data = self.admin.post(self.base(self.own) + "/from-risks", {})
        self.assertEqual(data["added"], 1)
        row = next(r for r in data["rows"] if r["risk_id"] == rid)
        self.assertEqual((row["failure_mode"], row["cause"], row["effect"]), ("Buse bouchée", "colle de mauvaise qualité", "aucun débit"))
        self.assertEqual(self.admin.post(self.base(self.own) + "/from-risks", {})["added"], 0)

    def test_06_key_test(self):
        """0.60.24 (D-O-033): one key test of the Test Base per row -- the Space's own tests, then the catalogue."""
        with db.connect() as conn:
            now = db.utc_now()
            own = conn.execute("INSERT INTO testing_tests (project_id, test_id, title, subject, created_at, updated_at) "
                               "VALUES (?, 'LAMPF-T1', 'Essai d''échauffement', 'therm', ?, ?)", (self.lamp, now, now)).lastrowid
            other = conn.execute("INSERT INTO testing_tests (project_id, test_id, title, subject, created_at, updated_at) "
                                 "VALUES (?, 'FMEA-T1', 'Autre Space', 'func', ?, ?)", (self.own, now, now)).lastrowid
        data = self.admin.get(self.base(self.lamp))
        offered = [t["id"] for t in data["tests"]]
        self.assertEqual(offered[0], own)  # the Space first
        self.assertNotIn(other, offered)
        self.assertEqual({t["space"] for t in data["tests"]}, {"LAMPF"})  # 0.60.41 (D-O-050): the Space's own base only
        row = data["rows"][0]
        data = self.admin.patch(self.base(self.lamp) + "/rows/{}".format(row["id"]), {"test_id": own})
        got = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual((got["test_id"], got["test_code"], got["test_space"]), (own, "LAMPF-T1", "LAMPF"))
        with self.assertRaises(ApiFailure) as err:
            self.admin.patch(self.base(self.lamp) + "/rows/{}".format(row["id"]), {"test_id": other})
        self.assertEqual(err.exception.status, 400)
        dup = self.admin.post(self.base(self.lamp) + "/rows/{}/duplicate".format(row["id"]), {})
        self.assertEqual(next(r for r in dup["rows"] if r["id"] == dup["created"])["test_id"], own)
        with self.admin.opener.open(self.url + self.base(self.lamp) + "/export.csv") as resp:
            self.assertIn("LAMPF-T1 Essai d'échauffement", resp.read().decode("utf-8-sig"))
        data = self.admin.patch(self.base(self.lamp) + "/rows/{}".format(row["id"]), {"test_id": None})
        self.assertIsNone(next(r for r in data["rows"] if r["id"] == row["id"])["test_id"])

    def test_05_reader(self):
        made = self.admin.post("/api/admin/users", {"username": "nina4", "display_name": "Nina"})
        self.admin.put("/api/admin/projects/{}/members/{}".format(self.lamp, made["user"]["id"]), {"role": "reader"})
        reader = Client(self.url)
        reader.login("nina4", made["temp_password"], new_password="Lecture-2026!")
        self.assertTrue(reader.get(self.base(self.lamp))["rows"])
        with self.assertRaises(ApiFailure) as err:
            reader.post(self.base(self.lamp) + "/rows", {})
        self.assertEqual(err.exception.status, 403)


if __name__ == "__main__":
    unittest.main()
