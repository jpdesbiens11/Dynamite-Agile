"""0.60.102 (D-O-110): Diamond -- the characteristics C-n and the summary of the special characteristics: the
specification typed and written back, the class read from the DFMEA row (never typed twice), the required Cpk from the
customer, the status, a C-n made from a DFMEA row, the filter « SC sans caractéristique », numbers never given again,
rights, exports (Excel, Word, the workbook and the report of Diamond), search, copy of a Space, and the Rover in DEMO."""
import io
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, spacecopy, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from modules.diamond import char_spec as SP  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class SpecTest(unittest.TestCase):
    def test_01_written_like_a_drawing(self):
        cases = [({"nominal": "2,0", "tol": "0,3"}, "mm", "", "2,0 ± 0,3 mm"), ({"usl": "50"}, "ms", "", "≤ 50 ms"),
                 ({"nominal": "1.50", "tol": "0.05"}, "mm", "", "1,50 ± 0,05 mm"), ({"lsl": "3,0"}, "mm", "R", "R 3,0 mm min."),
                 ({"lsl": "0,05", "usl": "2,00"}, "m", "", "0,05 à 2,00 m"),
                 ({"nominal": "2,0", "tol_plus": "0,3", "tol_minus": "0,2"}, "mm", "", "2,0 +0,3 / −0,2 mm"),
                 ({"usl": "0,20"}, "s", "", "≤ 0,20 s")]
        for body, unit, prefix, want in cases:
            self.assertEqual(SP.spec(dict(SP.limits(body, {}), unit=unit, prefix=prefix)), want, body)
        self.assertEqual(SP.spec({"spec_text": "Aucune fuite à 0,5 bar"}), "Aucune fuite à 0,5 bar")
        for bad in ({"lsl": "3", "usl": "2"}, {"tol": "0,3"}, {"nominal": "x"}, {"nominal": "5", "lsl": "1", "usl": "2"}):
            with self.assertRaises(ApiError):
                SP.limits(bad, {})

    def test_02_cpk_and_status(self):
        cust = {"cc_cpk": 1.67, "sc_cpk": 1.33}
        c = {"control": "spc", "cpk_required": None, "part_id": 1, "nominal": 2.0, "lsl": 1.7, "usl": 2.3, "nature": "product", "drawing": "D"}
        self.assertEqual((SP.cpk_required(c, "CC", cust), SP.cpk_required(c, "SC", cust), SP.cpk_required(c, "", cust)), (1.67, 1.33, None))
        self.assertEqual(SP.cpk_required(dict(c, cpk_required=2.0), "SC", cust), 2.0)
        self.assertIsNone(SP.cpk_required(dict(c, control="test100"), "CC", cust))  # a 100 % test, never an invented Cpk
        self.assertEqual(SP.status(c, "SC")[0], "study")
        self.assertEqual(SP.status(dict(c, drawing=""), "SC"), ("incomplete", "À compléter : plan"))
        self.assertEqual(SP.status(dict(c, control="test100", test_id=None), "CC")[1], "À compléter : essai")
        self.assertEqual(SP.status(c, "")[0], "unclassed")


class CharacteristicApiTest(unittest.TestCase):
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
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "LAMPH", "name": "lampe"})["project"]["id"]
        cls.admin.post("/api/diamond/p/{}/example".format(cls.pid), {"name": "lampe"})
        made = cls.admin.post("/api/admin/users", {"username": "lectrice", "display_name": "Lectrice"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lectrice", made["temp_password"], new_password="Lecture-2026!")
        cls.base = "/api/diamond/p/{}".format(cls.pid)

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

    def item(self, data, code):
        return next(c for c in data["items"] if c["code"] == code)

    def test_03_from_a_classified_row(self):
        rows = self.admin.get(self.base + "/dfmea")["rows"]
        row = next(r for r in rows if r["class_proposed"] == "SC")
        data = self.admin.post(self.base + "/dfmea/rows/{}/class".format(row["id"]), {"decision": "SC", "reason": "fonction du client"})
        self.assertEqual(data["classes"]["counts"]["no_characteristic"], 1)  # a confirmed class without a C-n
        self.assertTrue(any("sans caractéristique C-n" in c for c in data["checks"]))
        self.fails(403, self.reader.post, self.base + "/characteristics", {"dfmea_id": row["id"]})
        made = self.admin.post(self.base + "/characteristics", {"dfmea_id": row["id"]})
        c = self.item(made, made["created"])
        self.assertEqual((made["created"], c["class_code"], c["class_symbol"], c["label"]), ("C-01", "SC", "SC", row["requirement"][:160]))
        self.assertEqual(c["test_id"], row["test_id"])  # the key test of the row
        self.assertEqual(c["status"], "incomplete")
        self.assertEqual(made["counts"], {"CC": 0, "SC": 1})
        dfmea = self.admin.get(self.base + "/dfmea")
        self.assertEqual(dfmea["classes"]["counts"]["no_characteristic"], 0)
        self.assertEqual(next(r for r in dfmea["rows"] if r["id"] == row["id"])["characteristics"][0]["code"], "C-01")
        # the dimension, the part of an interface, the drawing: complete
        parts = made["options"]["parts"]
        up = self.admin.patch(self.base + "/characteristics/{}".format(c["id"]), {
            "nominal": "2,0", "tol": "0,3", "unit": "mm", "part_id": parts[0]["id"], "part2_id": parts[1]["id"], "drawing": "LMP-01 rév. A",
            "sheet": "1", "zone": "B3", "datum": "A"})
        c = self.item(up, "C-01")
        self.assertEqual((c["spec"], c["cpk_req"], c["status"], c["part"], c["part2"]), ("2,0 ± 0,3 mm", 1.33, "study", "P-1", "P-2"))
        self.assertIn("même que la première", self.fails(400, self.admin.patch, self.base + "/characteristics/{}".format(c["id"]),
                                                         {"part2_id": parts[0]["id"]}))
        self.fails(400, self.admin.patch, self.base + "/characteristics/{}".format(c["id"]), {"lsl": "3", "usl": "2"})
        self.fails(400, self.admin.patch, self.base + "/characteristics/{}".format(c["id"]), {"control": "magic"})
        self.fails(403, self.reader.patch, self.base + "/characteristics/{}".format(c["id"]), {"label": "x"})
        self.assertEqual(self.reader.get(self.base + "/characteristics")["summary"][0]["code"], "C-01")
        # the class comes from the DFMEA only: refused there, the C-n leaves the summary
        self.admin.post(self.base + "/dfmea/rows/{}/class".format(row["id"]), {"decision": "refused", "reason": "revu"})
        after = self.admin.get(self.base + "/characteristics")
        self.assertEqual((after["summary"], self.item(after, "C-01")["status"]), ([], "unclassed"))
        self.admin.post(self.base + "/dfmea/rows/{}/class".format(row["id"]), {"decision": "SC", "reason": "de retour"})

    def test_04_customer_cpk_numbers_archive(self):
        self.admin.patch(self.base + "/dfmea/classes/customers/aiag", {"sc_cpk": "1,50"})
        c = self.item(self.admin.get(self.base + "/characteristics"), "C-01")
        self.assertEqual(c["cpk_req"], 1.5)
        self.fails(400, self.admin.patch, self.base + "/dfmea/classes/customers/aiag", {"sc_cpk": "9"})
        self.admin.post(self.base + "/dfmea/classes/customers/aiag/delete", {})  # back to 1,33
        own = self.admin.patch(self.base + "/characteristics/{}".format(c["id"]), {"cpk_required": "2,00"})
        self.assertEqual(self.item(own, "C-01")["cpk_req"], 2.0)
        self.admin.patch(self.base + "/characteristics/{}".format(c["id"]), {"cpk_required": ""})
        free = self.admin.post(self.base + "/characteristics", {"label": "Couple de serrage", "nature": "process"})
        self.assertEqual(free["created"], "C-02")
        self.assertTrue(any("C-02 sans ligne du DFMEA" in x for x in free["checks"]))
        gone = self.admin.post(self.base + "/characteristics/{}/archive".format(free["created_id"]), {"archived": True})
        self.assertEqual(([x["code"] for x in gone["items"]], [x["code"] for x in gone["archived"]]), (["C-01"], ["C-02"]))
        again = self.admin.post(self.base + "/characteristics", {"label": "Autre"})
        self.assertEqual(again["created"], "C-03")  # never given again
        with db.connect() as conn:
            self.assertTrue(conn.execute("SELECT 1 FROM audit_log WHERE action = 'diamond_characteristic_archive'").fetchone())

    def test_05_exports_search_copy(self):
        status, _h, x = self.admin.raw_get(self.base + "/characteristics/summary.xlsx")
        self.assertEqual(status, 200)
        sheet = "".join(zipfile.ZipFile(io.BytesIO(x)).read(n).decode("utf-8", "ignore") for n in zipfile.ZipFile(io.BytesIO(x)).namelist())
        for text in ("Sommaire des caractéristiques spéciales", "C-01", "2,0 ± 0,3 mm", "Company PN", "Étude à faire"):
            self.assertIn(text, sheet)
        status, _h, w = self.reader.raw_get(self.base + "/characteristics/summary.docx")
        doc = zipfile.ZipFile(io.BytesIO(w)).read("word/document.xml").decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("0 CC et 1 SC", doc)
        _s, _h, full = self.admin.raw_get(self.base + "/export.xlsx")
        self.assertIn("Caractéristiques spéciales", zipfile.ZipFile(io.BytesIO(full)).read("xl/workbook.xml").decode("utf-8"))
        _s, _h, rep = self.admin.raw_get(self.base + "/export.docx")
        self.assertIn("Sommaire des caractéristiques spéciales", zipfile.ZipFile(io.BytesIO(rep)).read("word/document.xml").decode("utf-8"))
        hits = self.admin.get("/api/search?q=C-01")["results"]
        self.assertTrue(any(h["href"].endswith("/chars/C-01") for h in hits))
        self.assertIn("diamond_characteristics", spacecopy.DIAMOND)
        made = self.admin.post("/api/admin/spacecopy", {"key": "LAMPY", "name": "Copie", "parts": {"diamond": "LAMPH"}})
        copy = self.admin.get("/api/diamond/p/{}/characteristics".format(made["project"]["id"]))
        self.assertEqual([c["code"] for c in copy["summary"]], ["C-01"])
        self.assertEqual(copy["summary"][0]["spec"], "2,0 ± 0,3 mm")
        manifest = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        for name in ("chars.js", "char_card.js"):
            self.assertIn("/js/diamond/" + name, manifest["scripts"])
            text = (BASE_DIR / "static" / "js" / "diamond" / name).read_text("utf-8")
            self.assertNotIn("innerHTML", text)
            self.assertIn('data-new": "0.60.102-', text)
        self.assertIn('["chars", "Caractéristiques"]', (BASE_DIR / "static" / "js" / "diamond" / "diamond.js").read_text("utf-8"))

    def test_06_rover(self):
        demo = self.admin.get("/api/me")["projects"]
        pid = next(p["id"] for p in demo if p["key"] == "DEMO")
        data = self.admin.get("/api/diamond/p/{}/characteristics".format(pid))
        self.assertEqual(len(data["items"]), 21)
        self.assertEqual([c["code"] for c in data["summary"]], ["C-05", "C-08", "C-10", "C-14", "C-16", "C-20", "C-21"])
        c14 = self.item(data, "C-14")
        self.assertEqual((c14["spec"], c14["part"], c14["part2"], c14["dfmea"]["line"], c14["cpk_req"], c14["test_code"]),
                         ("2,0 ± 0,3 mm", "P-14", "P-1", 24, 1.33, "TST-FUN-06"))
        self.assertEqual(self.item(data, "C-05")["status"], "test100")
        self.assertEqual(self.item(data, "C-17")["nature"], "process")
        self.assertEqual(self.item(data, "C-09")["class_code"], "")  # its CC is only proposed
        self.assertEqual(data["checks"], [])
        dfmea = self.admin.get("/api/diamond/p/{}/dfmea".format(pid))
        self.assertEqual(dfmea["classes"]["counts"], {"all": 41, "special": 7, "severe": 6, "cc_proposed": 3, "no_characteristic": 0})


if __name__ == "__main__":
    unittest.main()
