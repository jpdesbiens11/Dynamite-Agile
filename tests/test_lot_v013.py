"""0.23.0: 3-letter traceability key required before any write (D-B-058),
Goldmine life-cycle phase (D-B-055), « Norme / Standard » and « Sécurité des
personnes » (D-B-056), last change with initials (D-B-059), life-cycle
requirements (D-B-060).

    python -m unittest tests.test_lot_v013 -v
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
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur lea | Léa Trace | utilisateur | actif
utilisateur max | Max Double | utilisateur | actif
droit lea | REQ | editeur
"""


class LotV013Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0  # require_initials stays on (default): this file tests it
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
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

    def status_of(self, call):
        with self.assertRaises(ApiFailure) as err:
            call()
        return err.exception.status

    def test_01_initials_required(self):
        admin = self.admin
        self.assertEqual(self.status_of(lambda: admin.post("/api/admin/projects", {
            "provision": False, "key": "REQ", "name": "REQ", "description": ""})), 428)
        self.assertEqual(self.status_of(lambda: admin.put("/api/me/prefs", {"initials": "AB"})), 400)
        self.assertEqual(self.status_of(lambda: admin.put("/api/me/prefs", {"initials": "ABCD"})), 400)
        self.assertEqual(admin.put("/api/me/prefs", {"initials": "adm"})["prefs"]["initials"], "ADM")
        admin.post("/api/admin/projects", {"provision": False, "key": "REQ", "name": "REQ", "description": ""})
        done = admin.post("/api/admin/access-rules", {"text": RULES})
        people = {}
        for c in done["created"]:
            client = Client(self.url)
            client.login(c["username"], c["temp_password"], "Essai-Lot-Treize-2026!")  # password change is allowed
            people[c["username"]] = client
        pid = admin.get("/api/admin/projects")["projects"][0]["id"]
        base = "/api/agile/p/{}".format(pid)
        admin.post(base + "/init")
        admin.post(base + "/goldmine/setup")
        lea, other = people["lea"], people["max"]
        self.assertEqual(self.status_of(lambda: lea.post(base + "/goldmine/requirements", {"statement": "Le module doit…"})), 428)
        lea.put("/api/me/prefs", {"initials": "LTR"})
        self.assertEqual(self.status_of(lambda: other.put("/api/me/prefs", {"initials": "LTR"})), 409)  # unique key
        other.put("/api/me/prefs", {"initials": "MDO"})
        type(self).base, type(self).lea = base, lea

    def test_02_lifecycle_category_and_last_change(self):
        base, lea = self.base, self.lea
        made = lea.post(base + "/goldmine/requirements", {
            "title": "Aucune pièce libre", "statement": "Aucune pièce libre ne doit tomber dans la cavité.",
            "category": "personnel_safety", "lifecycle": "assembly", "source": "internal"})
        self.assertEqual(self.status_of(lambda: lea.post(base + "/goldmine/requirements", {
            "statement": "Le module doit…", "lifecycle": "bientot"})), 400)
        listing = self.admin.get(base + "/goldmine")
        self.assertIn("Standard / Regulatory", listing["labels"]["categories"].values())
        self.assertEqual(len(listing["labels"]["lifecycle"]), 12)
        req = next(r for r in listing["requirements"] if r["key"] == made["key"])
        self.assertEqual((req["lifecycle"], req["category"]), ("assembly", "personnel_safety"))
        self.assertEqual(req["last_change"]["by"], "LTR")
        self.assertRegex(req["last_change"]["stamp"], r"^\d{8}-LTR$")
        self.admin.put(base + "/issues/{}/requirement".format(made["number"]), {"lifecycle": "maintenance"})
        req = next(r for r in self.admin.get(base + "/goldmine")["requirements"] if r["key"] == made["key"])
        self.assertEqual((req["lifecycle"], req["last_change"]["by"]), ("maintenance", "ADM"))
        with self.admin.opener.open(self.url + base + "/export/requirements") as resp:
            rows = list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))
        row = next(r for r in rows if r["key"] == made["key"])
        self.assertEqual(row["lifecycle"], "Maintenance & Repair")
        self.assertEqual(row["category"], "Personnel Safety")
        self.assertTrue(row["last_change"].endswith("-ADM"))

    def test_03_bm_life_cycle_catalogue(self):  # 0.60.01: generic consumer mechatronic catalogue
        from modules.testing.data_tests import TESTS
        from tools import generic_requirements
        rows = generic_requirements.all_requirements()
        ids = [r[0] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(r[11] for r in rows), "every requirement and need has a life-cycle phase")
        known = {t[0] for t in TESTS}
        self.assertTrue(all(r[15] in known for r in rows if r[12] == "requirement"))
        text = (BASE_DIR / "deploy" / "requis_generiques.csv").read_text(encoding="utf-8-sig")
        self.assertEqual(text, generic_requirements.csv_text().lstrip("\ufeff"))  # the file is up to date
        res = self.admin.post(self.base + "/import/requirements", {"csv": text})
        self.assertFalse(res.get("errors"), res.get("errors"))
        reqs = {r["external_id"]: r for r in self.admin.get(self.base + "/goldmine")["requirements"]}
        self.assertEqual(reqs["GR-018"]["lifecycle"], "transport")
        self.assertEqual(reqs["GR-012"]["category"], "regulatory")
        self.assertEqual(sum(1 for k in reqs if k.startswith(("GR-", "GN-"))), len(rows))


if __name__ == "__main__":
    unittest.main()
