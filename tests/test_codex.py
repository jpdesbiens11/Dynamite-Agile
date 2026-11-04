"""Codex (D-B-021): naming rules, unique reservation, rights, revision, voiding, CSV.

    python -m unittest tests.test_codex -v
"""
import datetime as dt
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.codex import catalog, registry  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur edith | Édith Essai | utilisateur | actif
utilisateur lucas | Lucas Essai | utilisateur | actif
droit edith | CDX | editeur
droit lucas | CDX | lecteur
"""


class CatalogTest(unittest.TestCase):
    """Same strings as the stand-alone generator page."""

    def test_serial(self):
        noon = dt.datetime(2026, 9, 25, 12, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(catalog.serial_parts(noon), (46290, 50000))
        late = dt.datetime(2026, 9, 25, 23, 59, 59, 900000, tzinfo=dt.timezone.utc)
        self.assertEqual(catalog.serial_parts(late), (46291, 0))
        self.assertEqual(catalog.next_slot(46290, 99999), (46291, 0))

    def test_names(self):
        made = catalog.names("CDCF", 46290, 50000, "11", "03", "CHAUF", 2, "CdCF: pistolet / v2?")
        self.assertEqual(made["reference"], "CDCF-46290-50000")
        self.assertEqual(made["file_name"], "CDCF-46290-50000_2_CHAUF CdCF- pistolet - v2-")
        self.assertEqual(made["svn_path"], "Documents/02_Etude-conceptuelle/11-03_CHAUF/")
        plain = catalog.names("PRO", 46290, 7, "09", "00", "", 1, "")
        self.assertEqual(plain["file_name"], "PRO-46290-00007_1")
        self.assertEqual(plain["svn_path"], "Documents/06_Rapports/09-00_FCT/")
        same = catalog.names("MIP", 46290, 7, "06", "00", "RSK", 1, "")
        self.assertEqual(same["svn_path"], "Documents/01_Pre-etude/06-00_RSK/")

    def test_catalog_complete(self):
        """0.60.01: the deliverables of the product development process, filed by step of the PDP."""
        self.assertEqual(len(catalog.DOC_TYPES), 34)
        for code in ("MIP", "RCS", "CDCF", "RC", "RVE"):
            self.assertIn(code, catalog.DOC_TYPES)
        self.assertEqual(sorted(catalog.STEPS), ["{:02d}".format(n) for n in list(range(1, 16)) + [19, 20, 21]])
        self.assertEqual(catalog.STEPS["09"]["name"], "Recherche des fonctions")
        self.assertEqual(catalog.RETIRED_TYPES, {})


class CodexApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "c.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "CDX", "name": "Essai Codex", "description": ""})
        cls.pid = next(p["id"] for p in cls.admin.get("/api/admin/projects")["projects"] if p["key"] == "CDX")
        cls.base = "/api/codex/p/{}".format(cls.pid)
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.people = {}
        for c in done["created"]:
            client = Client(cls.url)
            client.login(c["username"], c["temp_password"], "Codex-Essai-PDP-2026")
            cls.people[c["username"]] = client

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def reserve(self, who, **extra):
        body = {"doc_type": "CDCF", "step": "11", "sub": "3", "system_code": "chauf",
                "revision": 1, "title": "CdCF pistolet"}
        body.update(extra)
        return who.post(self.base + "/refs", body)["ref"]

    def test_1_meta_and_nav(self):
        meta = self.admin.get("/api/codex/meta")
        self.assertEqual(meta["doc_groups"][0]["types"][0]["code"], "MIP")  # 0.60.01: deliverables of the PDP
        mods = {m["key"]: m for m in self.admin.get("/api/me")["modules"]}
        self.assertTrue(mods["codex"]["available"])
        self.assertIn("/js/codex/codex.js", mods["codex"]["scripts"])

    def test_2_reserve_unique(self):
        edith = self.people["edith"]
        a = self.reserve(edith)
        b = self.reserve(edith)  # same second: the server moves to the next free slot
        self.assertNotEqual((a["date_serial"], a["time_serial"]), (b["date_serial"], b["time_serial"]))
        self.assertRegex(a["reference"], r"^CDCF-\d{5}-\d{5}$")
        self.assertTrue(a["file_name"].endswith("_1_CHAUF CdCF pistolet"))
        self.assertEqual(a["svn_path"], "Documents/02_Etude-conceptuelle/11-03_CHAUF/")
        self.assertEqual(a["created_by_name"], "Édith Essai")

    def test_3_collision_in_code(self):
        moment = dt.datetime(2030, 1, 1, 8, 0, tzinfo=dt.timezone.utc)
        fields = {"doc_type": "REP", "pdp_step": "09", "pdp_sub": "00", "system_code": "", "revision": 1, "title": ""}

        class Ctx:
            pass
        ids = []
        with db.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
            ctx = Ctx()
            ctx.conn, ctx.user, ctx.ip = conn, user, "127.0.0.1"
            for _ in range(3):
                ids.append(registry.reserve(ctx, self.pid, fields, moment))
            refs = [conn.execute("SELECT reference FROM codex_refs WHERE id = ?", (i,)).fetchone()[0] for i in ids]
        d, t = catalog.serial_parts(moment)
        self.assertEqual(refs, [catalog.reference("REP", d, t + k) for k in range(3)])

    def test_4_rights_and_validation(self):
        with self.assertRaises(ApiFailure) as err:
            self.reserve(self.people["lucas"])
        self.assertEqual(err.exception.status, 403)
        self.assertFalse(self.people["lucas"].get(self.base + "/refs")["can_edit"])  # reader: registry only
        for bad, word in (({"doc_type": "XYZ"}, "XYZ"), ({"step": "99"}, "99"), ({"sub": "3a"}, "3a"),
                          ({"system_code": "CHAUF 03"}, "CHAUF 03"), ({"revision": 0}, "0")):
            with self.assertRaises(ApiFailure) as err:
                self.reserve(self.people["edith"], **bad)
            self.assertEqual(err.exception.status, 400)
            self.assertIn(word, str(err.exception))
            self.assertIn("Correctif", str(err.exception))

    def test_5_revise_and_void(self):
        edith = self.people["edith"]
        ref = self.reserve(edith, title="CdCF")
        url = self.base + "/refs/{}".format(ref["id"])
        up = edith.patch(url, {"revision": 2, "title": "CdCF rév. 2"})["ref"]
        self.assertTrue(up["file_name"].startswith(ref["reference"] + "_2_"))
        self.assertEqual(up["reference"], ref["reference"])
        with self.assertRaises(ApiFailure):
            edith.patch(url, {"revision": 1})  # never lowered
        with self.assertRaises(ApiFailure) as err:
            edith.patch(url, {"status": "void", "void_reason": "doublon"})
        self.assertEqual(err.exception.status, 403)
        with self.assertRaises(ApiFailure):
            self.admin.patch(url, {"status": "void"})  # reason required
        void = self.admin.patch(url, {"status": "void", "void_reason": "doublon"})["ref"]
        self.assertEqual(void["status"], "void")
        with self.assertRaises(ApiFailure):
            edith.patch(url, {"title": "x"})
        self.assertEqual(self.admin.patch(url, {"status": "active"})["ref"]["status"], "active")
        with db.connect() as conn:
            actions = [r[0] for r in conn.execute(
                "SELECT action FROM audit_log WHERE object_type = 'codex_ref' AND object_id = ?", (str(ref["id"]),))]
        self.assertEqual(actions, ["codex_reserve", "codex_update", "codex_update", "codex_update"])

    def test_6_csv(self):
        self.reserve(self.people["edith"], title="Pour export")
        with self.admin.opener.open(self.url + self.base + "/export.csv") as resp:
            text = resp.read().decode("utf-8-sig")
        self.assertTrue(text.startswith("Référence,Revision,Type"))
        self.assertIn("Pour export", text)

    def test_8_pdp_deliverables(self):
        """0.60.01: every deliverable of the PDP can be reserved; an unknown step is refused with the list to choose from."""
        edith = self.people["edith"]
        for code, step in (("MIP", "06"), ("RCS", "12"), ("AF", "09"), ("RC", "15"), ("RVE", "21")):
            ref = self.reserve(edith, doc_type=code, step=step, title="")
            self.assertTrue(ref["reference"].startswith(code + "-"))
            self.assertEqual(ref["pdp_step"], step)
        with self.assertRaises(ApiFailure) as err:
            self.reserve(edith, step="16")
        self.assertIn("Étape du PDP", str(err.exception))
        self.assertEqual(self.admin.get("/api/codex/meta")["retired_types"], [])

    def test_7_other_project_hidden(self):
        with self.assertRaises(ApiFailure) as err:
            self.people["edith"].get("/api/codex/p/{}/refs".format(self.pid + 999))
        self.assertEqual(err.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
