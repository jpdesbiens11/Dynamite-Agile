"""0.60.20 (D-O-031): Diamond 💎 -- the parts on the functions of the functional structure: the matrix parts x
functions, integrated parts, functions shared by several parts, parts with no function, the example, rights, journal."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class DiamondPartsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "p.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        mk = lambda key: cls.admin.post("/api/admin/projects", {"key": key, "name": key})["project"]["id"]
        cls.lamp, cls.own = mk("LAMPP"), mk("OWNP")
        cls.admin.post("/api/diamond/p/{}/example".format(cls.lamp), {"name": "lampe"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def base(self, pid):
        return "/api/diamond/p/{}/structure".format(pid)

    def test_01_example(self):
        s = self.admin.get(self.base(self.lamp))
        self.assertEqual(len(s["parts"]), 11)
        num = {f["id"]: f["number"] for f in s["views"]["detail"] + s["views"]["general"]}
        head = next(p for p in s["parts"] if p["name"].startswith("Tête"))
        self.assertEqual(sorted(num[f] for f in head["functions"]), [4, 18, 20])
        st = s["part_stats"]
        self.assertEqual((st["parts"], st["integrated"]), (11, 4))
        self.assertGreaterEqual(st["shared"], 2)  # F20 (3 parts), F14 (2 cards), F4 (2 parts)
        text = " ".join(s["part_checks"])
        self.assertIn("pièce intégrée", text)
        self.assertIn("F20", text)
        self.assertIn("Vis M3", text)  # no function of the tree: the best part is no part
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(self.base(self.lamp) + "/parts/example", {})
        self.assertEqual(err.exception.status, 409)

    def test_02_by_hand(self):
        s = self.admin.get(self.base(self.lamp))
        f13 = next(f for f in s["views"]["detail"] if f["number"] == 13)
        tech = 16  # technique function: not in the structure
        s = self.admin.post(self.base(self.lamp) + "/parts", {"name": "Lentille", "kind": "bought", "functions": [f13["id"]]})
        part = next(p for p in s["parts"] if p["name"] == "Lentille")
        self.assertEqual((part["number"], part["kind"], part["functions"]), (12, "bought", [f13["id"]]))
        s = self.admin.put(self.base(self.lamp) + "/parts/{}/functions".format(part["id"]), {"function_id": f13["id"], "on": False})
        self.assertEqual(next(p for p in s["parts"] if p["id"] == part["id"])["functions"], [])
        with db.connect() as conn:
            tid = conn.execute("SELECT id FROM diamond_functions WHERE project_id = ? AND number = ?", (self.lamp, tech)).fetchone()["id"]
        with self.assertRaises(ApiFailure) as err:
            self.admin.put(self.base(self.lamp) + "/parts/{}/functions".format(part["id"]), {"function_id": tid, "on": True})
        self.assertEqual(err.exception.status, 409)
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(self.base(self.lamp) + "/parts", {"name": "X", "kind": "magique"})
        self.assertEqual(err.exception.status, 400)
        s = self.admin.patch(self.base(self.lamp) + "/parts/{}".format(part["id"]), {"name": "Lentille de Fresnel", "notes": "PMMA"})
        self.assertEqual(next(p for p in s["parts"] if p["id"] == part["id"])["name"], "Lentille de Fresnel")
        s = self.admin.post(self.base(self.lamp) + "/parts/{}/delete".format(part["id"]), {})
        self.assertFalse(any(p["id"] == part["id"] for p in s["parts"]))
        with db.connect() as conn:
            actions = {r["action"] for r in conn.execute("SELECT action FROM audit_log WHERE action LIKE 'diamond_part%'")}
        self.assertTrue({"diamond_part_create", "diamond_part_untag", "diamond_part_update", "diamond_part_delete"} <= actions)

    def test_03_other_space_and_rights(self):
        s = self.admin.get(self.base(self.own))
        self.assertEqual((s["parts"], s["part_checks"]), ([], []))
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(self.base(self.own) + "/parts/example", {})
        self.assertEqual(err.exception.status, 409)  # not the lamp tree
        lamp = self.admin.get(self.base(self.lamp))
        with self.assertRaises(ApiFailure) as err:  # a part of another Space
            self.admin.post(self.base(self.own) + "/parts/{}/delete".format(lamp["parts"][0]["id"]), {})
        self.assertEqual(err.exception.status, 404)

    def test_05_copy_keeps_diamond(self):
        """0.60.21: « Dupliquer / Enregistrer sous » and « Copier / composer » take the whole of Diamond along."""
        made = self.admin.post("/api/admin/projects/{}/copy".format(self.lamp), {"key": "LAMPC", "name": "Copie lampe"})
        new = made["project"]["id"]
        tables = ("diamond_functions", "diamond_ports", "diamond_flows", "diamond_parts", "diamond_part_functions",
                  "diamond_risks", "diamond_dfmea")
        with db.connect() as conn:
            for t in tables:
                n = lambda pid: conn.execute("SELECT COUNT(*) FROM {} WHERE project_id = ?".format(t), (pid,)).fetchone()[0]  # noqa: E731
                self.assertEqual(n(new), n(self.lamp), t)
                self.assertGreater(n(new), 0, t)
            bad = conn.execute("SELECT COUNT(*) FROM diamond_flows fl JOIN diamond_functions f ON f.id = fl.src_function_id "
                               "WHERE fl.project_id = ? AND f.project_id != ?", (new, new)).fetchone()[0]
            self.assertEqual(bad, 0)
            parents = conn.execute("SELECT COUNT(*) FROM diamond_functions c JOIN diamond_functions p ON p.id = c.parent_id "
                                   "WHERE c.project_id = ? AND p.project_id = ?", (new, new)).fetchone()[0]
            self.assertGreater(parents, 10)
        s = self.admin.get(self.base(new))
        self.assertEqual(len(s["parts"]), len(self.admin.get(self.base(self.lamp))["parts"]))

    def test_04_screen(self):
        js = (BASE_DIR / "static" / "js" / "diamond" / "structure_parts.js").read_text("utf-8")
        for needed in ("0.60.20-parts-matrix", "0.60.20-part-panel", "aria-pressed", "partsByFunction"):
            self.assertIn(needed, js)
        self.assertNotIn("innerHTML", js)
        self.assertIn("/js/diamond/structure_parts.js", (BASE_DIR / "core" / "modules.py").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
