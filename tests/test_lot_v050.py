"""0.50.11, core lot v0.33 (D-B-129): revisions revX.XX of the whole database -- numbers that never go back, records
chained by hash, read-only view of a revision with the CURRENT rights, exports stamped with their revision (name, Word
header, Excel sheet, Office properties) and the register of extractions.

    python -m unittest tests.test_lot_v050 -v
"""
import io
import json
import re
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, baselines, db, modules, router, startup, stamp_office  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from modules.exploration import xlsx  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

STATIC = BASE_DIR / "static"


class NumberTest(unittest.TestCase):
    def test_parse_and_label(self):
        for text, value in (("rev1.1", 110), ("1.10", 110), ("REV 2", 200), ("rev1,05", 105), ("rev12.34", 1234),
                            (" rev3 ", 300), ("rev1.9", 190)):
            self.assertEqual(baselines.parse(text), value, text)
        for bad in ("", "rev", "1.234", "v1.2", "rev-1", "rev0", "abc"):
            with self.assertRaises(ApiError):
                baselines.parse(bad)
        self.assertEqual(baselines.label(110), "rev1.10")
        self.assertEqual(baselines.label(105), "rev1.05")
        self.assertEqual((baselines.next_auto(0), baselines.next_auto(110), baselines.next_auto(200)), (100, 200, 300))
        self.assertLess(baselines.parse("rev1.05"), baselines.parse("rev1.1"))   # 1.05 < 1.10 < 1.9 (= 1.90)
        self.assertLess(baselines.parse("rev1.1"), baselines.parse("rev1.9"))

    def test_office_stamp_keeps_a_valid_package(self):
        sheet = xlsx.Sheet("Plan")
        sheet.add("Code", "Titre")
        sheet.add("T1", "Essai")
        data = xlsx.write([sheet])
        out = stamp_office.stamp(data, "xlsx", ["ligne 1", "ligne 2"], [("Référence de révision", "rev1.10")],
                                 [("DA Revision", "rev1.10")])
        book = xlsx.read(out)
        self.assertEqual(list(book)[:1], ["Plan"])
        self.assertEqual(book["Révision"][0], ["Référence de révision", "rev1.10"])
        self.assertIn(b"DA Revision", zipfile.ZipFile(io.BytesIO(out)).read("docProps/custom.xml"))
        self.assertEqual(stamp_office.stamp(b"pas un zip", "docx", [], [], []), b"pas un zip")


class BaselineApiTest(unittest.TestCase):
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
        cls.data_dir, cls.cfg = data_dir, cfg
        cls.server = router.create_server(cfg, STATIC, data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.put("/api/me/prefs", {"initials": "ADM"})
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "REV", "name": "Revue"})["project"]["id"]
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur ana | Ana | utilisateur | actif\n"
                                                                  "droit ana | REV | éditeur\n"})
        c = done["created"][0]
        cls.ana = Client(cls.url)
        cls.ana.login(c["username"], c["temp_password"], "Essai-Revision-Plateforme-2026!")
        cls.ana.put("/api/me/prefs", {"initials": "ANA"})
        cls.ana_id = cls.ana.get("/api/me")["user"]["id"]
        cls.base = "/api/agile/p/{}".format(cls.pid)
        cls.task = next(t for t in cls.ana.get(cls.base + "/meta")["types"] if t["icon_key"] == "task")["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status, str(exc)
        return 200, ""

    def ticket(self, title):
        return self.ana.post(self.base + "/issues", {"type_id": self.task, "title": title, "priority": "medium"})

    def titles(self, client):
        return {i["title"] for i in client.get(self.base + "/issues")["issues"]}

    def get_file(self, client, path):
        status, headers, data = client.raw_get(path)
        self.assertEqual(status, 200, data[:200])
        name = re.search(r'filename="([^"]+)"', headers.get("Content-Disposition", "")).group(1)
        return name, data

    def test_01_numbers_never_go_back(self):
        first = self.admin.post("/api/baselines", {"title": "Revue PDR"})["baseline"]
        self.assertEqual(first["label"], "rev1.00")
        manual = self.admin.post("/api/baselines", {"number": "rev1.1", "title": "Revue partielle client"})["baseline"]
        self.assertEqual(manual["label"], "rev1.10")
        auto = self.admin.post("/api/baselines", {"title": "Revue CDR"})["baseline"]
        self.assertEqual(auto["label"], "rev2.00")
        code, msg = self.status(lambda: self.admin.post("/api/baselines", {"number": "rev1.50", "title": "x"}))
        self.assertEqual(code, 409)
        self.assertIn("rev2.01", msg)
        self.assertEqual(self.status(lambda: self.admin.post("/api/baselines", {"number": "2", "title": "x"}))[0], 409)
        self.assertEqual(self.status(lambda: self.admin.post("/api/baselines", {"title": ""}))[0], 400)
        self.assertEqual(self.status(lambda: self.ana.post("/api/baselines", {"title": "x"}))[0], 403)
        listing = self.ana.get("/api/baselines")
        self.assertEqual([b["label"] for b in listing["baselines"]], ["rev2.00", "rev1.10", "rev1.00"])
        self.assertEqual((listing["next"], listing["last"], listing["can_create"]), ("rev3.00", "rev2.00", False))
        folder = self.data_dir / "baselines"
        self.assertTrue((folder / "rev1.10.sqlite.gz").exists())
        self.assertGreater(auto["bytes"], 0)
        self.assertLess(auto["bytes"], auto["bytes_raw"])                      # compressed
        self.assertTrue(self.admin.get("/api/baselines/rev2.00/verify")["ok"])
        rec = json.loads((folder / "rev1.10.json").read_text("utf-8"))
        self.assertEqual(rec["previous"], "rev1.00")
        self.assertNotIn("sessions", rec["counts"])

    def test_02_tampered_record_is_detected(self):
        self.admin.post("/api/baselines", {"title": "À altérer"})
        last = self.admin.get("/api/baselines")["last"]
        path = self.data_dir / "baselines" / (last + ".json")
        rec = json.loads(path.read_text("utf-8"))
        path.write_text(json.dumps(dict(rec, title="Autre titre"), ensure_ascii=False), "utf-8")
        result = self.admin.get("/api/baselines/{}/verify".format(last))
        self.assertFalse(result["ok"])
        path.write_text(json.dumps(rec, ensure_ascii=False), "utf-8")
        self.assertTrue(self.admin.get("/api/baselines/{}/verify".format(last))["ok"])

    def test_03_read_only_view_with_current_rights(self):
        self.ticket("Avant la révision")
        rev = self.admin.post("/api/baselines", {"title": "Vue figée"})["baseline"]["label"]
        self.ticket("Après la révision")
        self.assertEqual(self.ana.post("/api/baselines/view", {"label": rev})["view"], rev)
        frozen = self.titles(self.ana)
        self.assertIn("Avant la révision", frozen)
        self.assertNotIn("Après la révision", frozen)
        code, msg = self.status(lambda: self.ticket("Interdit"))
        self.assertEqual(code, 409)
        self.assertIn("LECTURE_SEULE", msg)
        self.assertEqual(self.ana.get("/api/me")["user"]["id"], self.ana_id)   # free routes still answer
        # rights are the current ones: removed from the Space since, no access in the revision either
        member = "/api/admin/projects/{}/members/{}".format(self.pid, self.ana_id)
        self.admin.delete(member)
        self.assertIn(self.status(lambda: self.ana.get(self.base + "/issues"))[0], (403, 404))
        self.admin.put(member, {"role": "editor"})
        self.assertIn("Avant la révision", self.titles(self.ana))
        self.assertEqual(self.ana.post("/api/baselines/view", {"label": ""})["view"], "")
        self.assertIn("Après la révision", self.titles(self.ana))
        self.assertFalse(list((self.data_dir / "baselines_work").glob("*_u{}.sqlite".format(self.ana_id))))
        self.assertEqual(self.status(lambda: self.ana.post("/api/baselines/view", {"label": "rev99.00"}))[0], 404)

    def test_04_exports_carry_the_revision_and_are_registered(self):
        rev = self.admin.post("/api/baselines", {"title": "Revue client partielle"})["baseline"]["label"]
        self.ana.post("/api/baselines/view", {"label": rev})
        self.admin.post("/api/baselines/view", {"label": rev})
        name, data = self.get_file(self.admin, "/api/testing/export.docx")
        self.admin.post("/api/baselines/view", {"label": ""})
        self.assertTrue(name.endswith("_{}.docx".format(rev)), name)
        z = zipfile.ZipFile(io.BytesIO(data))
        text = "".join(z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("word/") and n.endswith(".xml"))
        self.assertIn("Révision de référence " + rev, text)
        self.assertIn("(ADM)", text)
        self.assertIn(rev, z.read("docProps/custom.xml").decode("utf-8"))
        csv_name, csv_data = self.get_file(self.ana, self.base + "/export/tickets")
        self.assertTrue(csv_name.endswith("_{}.csv".format(rev)), csv_name)
        self.assertNotIn("Révision", csv_data.decode("utf-8-sig").splitlines()[0])   # content unchanged: re-importable
        self.ana.post("/api/baselines/view", {"label": ""})
        live_name, _ = self.get_file(self.ana, self.base + "/export/tickets")
        self.assertRegex(live_name, r"_hors-rev-\d{8}-\d{4}\.csv$")
        xname, xdata = self.get_file(self.admin, "/api/exploration/p/{}/export.xlsx".format(self.pid))
        self.assertIn("Révision", xlsx.read(xdata))
        reg = self.admin.get("/api/baselines/extracts")
        self.assertIsNone(reg["broken_at"])
        mine = [e for e in reg["extracts"] if e["username"] == "ana"]
        self.assertEqual([e["baseline"] for e in mine[:2]], [None, rev])
        self.assertEqual(mine[0]["after"], rev)
        self.assertEqual(mine[1]["initials"], "ANA")
        self.assertEqual(self.status(lambda: self.ana.get("/api/baselines/extracts"))[0], 403)
        status, headers, body = self.admin.raw_get("/api/baselines/extracts.csv")
        self.assertEqual(status, 200)
        self.assertNotIn("_rev", headers.get("Content-Disposition", ""))     # the register itself is not stamped
        path = self.data_dir / "baselines" / "extracts.jsonl"
        lines = path.read_text("utf-8").splitlines()
        edited = json.loads(lines[0])
        edited["name"] = "Quelqu'un d'autre"
        path.write_text("\n".join([json.dumps(edited, ensure_ascii=False)] + lines[1:]) + "\n", "utf-8")
        self.assertEqual(self.admin.get("/api/baselines/extracts")["broken_at"], 1)
        path.write_text("\n".join(lines) + "\n", "utf-8")

    def test_05_return_to_a_restore_point_keeps_the_numbers(self):
        point = self.admin.post("/api/admin/restore-points", {"note": "avant essai"})
        name = point["point"]["name"]
        made = self.admin.post("/api/baselines", {"title": "Après le point"})["baseline"]["label"]
        self.admin.post("/api/admin/restore-points/{}/revert".format(name), {"confirm": name})
        self.admin.login("admin", "admin")
        listing = self.admin.get("/api/baselines")
        self.assertEqual(listing["last"], made)
        self.assertGreater(baselines.parse(listing["next"]), baselines.parse(made))


if __name__ == "__main__":
    unittest.main(verbosity=2)
