"""0.60.13 (D-O-025): Diamond 💎 -- the functional structure (boundary diagram): inputs and outputs, general and detail
views built from the tree, energy / material / information flows, the method's checks, positions, the example."""
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


class DiamondStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        mk = lambda key: cls.admin.post("/api/admin/projects", {"key": key, "name": key})["project"]["id"]
        cls.lamp, cls.own = mk("LAMPS"), mk("GLUES")
        cls.admin.post("/api/diamond/p/{}/example".format(cls.lamp), {"name": "lampe"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def base(self, pid):
        return "/api/diamond/p/{}/structure".format(pid)

    def test_01_example_is_consistent(self):
        s = self.admin.get(self.base(self.lamp))
        self.assertEqual(s["primary"]["text"], "Éclairer une surface de travail")
        self.assertEqual(sorted(f["number"] for f in s["views"]["general"]), [2, 5, 8, 12, 17])
        detail = {f["number"] for f in s["views"]["detail"]}
        self.assertNotIn(16, detail)  # the technique function stays out of the system design
        self.assertTrue({3, 4, 13, 20} <= detail)
        self.assertEqual(len(s["ports"]), 6)
        self.assertEqual(len([f for f in s["flows"] if f["view"] == "general"]), 11)
        self.assertEqual(s["checks"], [])  # every function exchanges a flow, every general flow is in the detail view
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(self.base(self.lamp) + "/example", {})
        self.assertEqual(err.exception.status, 409)  # not twice

    def test_02_build_by_hand_with_rules(self):
        fn = "/api/diamond/p/{}/functions".format(self.own)
        data = self.admin.post(fn, {"text": "Appliquer de la colle chaude", "primary": True})
        f1 = data["functions"][0]["id"]
        stock = max(self.admin.post(fn, {"text": "Stocker la colle", "parent_id": f1})["functions"], key=lambda f: f["number"])["id"]
        melt = max(self.admin.post(fn, {"text": "Fondre la colle", "parent_id": f1})["functions"], key=lambda f: f["number"])["id"]
        heat = max(self.admin.post(fn, {"text": "Chauffer la colle", "parent_id": melt})["functions"], key=lambda f: f["number"])["id"]
        s = self.admin.get(self.base(self.own))
        self.assertTrue(any("Aucune entrée" in c for c in s["checks"]))
        s = self.admin.post(self.base(self.own) + "/ports", {"side": "in", "label": "Bâtonnets de colle solide", "kind": "material"})
        s = self.admin.post(self.base(self.own) + "/ports", {"side": "out", "label": "Colle liquide appliquée", "kind": "material"})
        pin = next(p["id"] for p in s["ports"] if p["side"] == "in")
        pout = next(p["id"] for p in s["ports"] if p["side"] == "out")
        flow = lambda body: self.admin.post(self.base(self.own) + "/flows", body)
        s = flow({"view": "general", "kind": "material", "label": "colle solide", "src": {"type": "port", "id": pin}, "dst": {"type": "function", "id": stock}})
        s = flow({"view": "general", "kind": "material", "label": "colle solide", "src": {"type": "function", "id": stock}, "dst": {"type": "function", "id": melt}})
        s = flow({"view": "general", "kind": "material", "label": "colle liquide", "src": {"type": "function", "id": melt}, "dst": {"type": "port", "id": pout}})
        self.assertEqual(s["checks"], [])
        refused = [
            {"view": "general", "kind": "energy", "src": {"type": "function", "id": heat}, "dst": {"type": "function", "id": melt}},  # a tertiary
            {"view": "detail", "kind": "energy", "src": {"type": "function", "id": melt}, "dst": {"type": "function", "id": heat}},   # has tertiaries
            {"view": "general", "kind": "energy", "src": {"type": "port", "id": pout}, "dst": {"type": "function", "id": melt}},     # from an output
            {"view": "general", "kind": "energy", "src": {"type": "port", "id": pin}, "dst": {"type": "port", "id": pout}},          # no function
            {"view": "general", "kind": "vapeur", "src": {"type": "function", "id": stock}, "dst": {"type": "function", "id": melt}},
        ]
        for body in refused:
            with self.assertRaises(ApiFailure) as err:
                flow(body)
            self.assertIn("Correctif", err.exception.message, body)
        # detail view: the general flow stock -> melt must be found again (stock has no tertiary: it stands for itself)
        s = flow({"view": "detail", "kind": "material", "label": "colle solide", "src": {"type": "port", "id": pin}, "dst": {"type": "function", "id": stock}})
        self.assertTrue(any("absent(s) de la vue détaillée" in c for c in s["checks"]))
        s = flow({"view": "detail", "kind": "material", "label": "colle solide", "src": {"type": "function", "id": stock}, "dst": {"type": "function", "id": heat}})
        s = flow({"view": "detail", "kind": "material", "label": "colle liquide", "src": {"type": "function", "id": heat}, "dst": {"type": "port", "id": pout}})
        self.assertEqual(s["checks"], [])

    def test_03_positions_edit_delete(self):
        s = self.admin.get(self.base(self.own))
        stock = s["views"]["general"][0]["id"]
        self.admin.put(self.base(self.own) + "/position", {"view": "general", "node": {"type": "function", "id": stock}, "x": 300, "y": 120})
        pin = next(p["id"] for p in s["ports"] if p["side"] == "in")
        self.admin.put(self.base(self.own) + "/position", {"view": "general", "node": {"type": "port", "id": pin}, "x": 10, "y": 50})
        self.admin.put(self.base(self.own) + "/position", {"view": "general", "node": {"type": "function", "id": stock}, "x": 320, "y": 140})
        s = self.admin.get(self.base(self.own))
        mine = [p for p in s["positions"] if p["view"] == "general"]
        self.assertEqual(len(mine), 2)  # one position per box, the last one
        self.assertIn({"view": "general", "function_id": stock, "port_id": None, "x": 320.0, "y": 140.0}, mine)
        fl = s["flows"][0]["id"]
        s = self.admin.patch(self.base(self.own) + "/flows/{}".format(fl), {"kind": "energy", "label": "chaleur"})
        self.assertEqual((s["flows"][0]["kind"], s["flows"][0]["label"]), ("energy", "chaleur"))
        with self.assertRaises(ApiFailure):  # an input with flows does not become an output
            self.admin.patch(self.base(self.own) + "/ports/{}".format(pin), {"side": "out"})
        n = len(s["flows"])
        s = self.admin.post(self.base(self.own) + "/ports/{}/delete".format(pin), {})
        self.assertEqual(len(s["flows"]), n - 2)  # its flows go with it
        s = self.admin.post(self.base(self.own) + "/layout/reset", {"view": "general"})
        self.assertEqual([p for p in s["positions"] if p["view"] == "general"], [])

    def test_04_reader_and_archived_function(self):
        made = self.admin.post("/api/admin/users", {"username": "hugo2", "display_name": "Hugo"})
        self.admin.put("/api/admin/projects/{}/members/{}".format(self.lamp, made["user"]["id"]), {"role": "reader"})
        reader = Client(self.url)
        reader.login("hugo2", made["temp_password"], new_password="Lecture-2026!")
        self.assertEqual(len(reader.get(self.base(self.lamp))["ports"]), 6)
        with self.assertRaises(ApiFailure) as err:
            reader.post(self.base(self.lamp) + "/ports", {"side": "in", "label": "x"})
        self.assertEqual(err.exception.status, 403)
        s = self.admin.get(self.base(self.lamp))
        f20 = next(f for f in s["views"]["detail"] if f["number"] == 20)
        self.admin.post("/api/diamond/p/{}/functions/{}/archive".format(self.lamp, f20["id"]), {})
        s = self.admin.get(self.base(self.lamp))
        self.assertFalse(any(fl["dst_function_id"] == f20["id"] for fl in s["flows"]))  # an archived function leaves the drawing


if __name__ == "__main__":
    unittest.main()
