"""0.60.103 (D-O-112): Diamond -- the company part numbers: the BOM of the ERP imported as CSV (preview then apply, problems
with their line, nothing deleted), the prompt for an AI assistant, its answer sorted (sure, to choose, to create in the ERP,
refused when the PN is not in the BOM: never written), the links by hand, rights, the summary of the special
characteristics, the copy of a Space, and the Rover."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, spacecopy, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

CSV = "PN;Révision;Désignation;Fournisseur;Matière\nLMP-100;A;Tête en aluminium;Usineur;Al 6063\nLMP-200;;Bras articulé;;Acier\n;;vide;;\nLMP-100;;double;;\n"


class PnTest(unittest.TestCase):
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
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "LAMPN", "name": "lampe"})["project"]["id"]
        cls.admin.post("/api/diamond/p/{}/example".format(cls.pid), {"name": "lampe"})
        made = cls.admin.post("/api/admin/users", {"username": "lectrice", "display_name": "Lectrice"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lectrice", made["temp_password"], new_password="Lecture-2026!")
        cls.base = "/api/diamond/p/{}/pn".format(cls.pid)

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

    def test_01_bom(self):
        self.assertIn("vide", self.fails(400, self.admin.get, self.base + "/prompt"))  # no BOM yet
        self.assertIn("PN introuvable", self.fails(400, self.admin.post, self.base + "/bom", {"file": "Nom;Prix\nx;1\n"}))
        pv = self.admin.post(self.base + "/bom", {"file": CSV})
        self.assertEqual((pv["mode"], pv["counts"]), ("preview", {"new": 2, "changed": 0, "same": 0}))
        self.assertEqual(pv["problems"], ["Ligne 4 : PN vide — ligne ignorée.", "Ligne 5 : PN LMP-100 déjà plus haut dans le fichier — ligne ignorée."])
        self.assertEqual(self.admin.get(self.base)["counts"]["bom"], 0)  # a preview writes nothing
        self.fails(403, self.reader.post, self.base + "/bom", {"file": CSV, "mode": "apply"})
        ap = self.admin.post(self.base + "/bom", {"file": CSV, "mode": "apply"})
        self.assertEqual([b["label"] for b in ap["bom"]], ["LMP-100 A", "LMP-200"])
        again = self.admin.post(self.base + "/bom", {"file": CSV.replace("Usineur", "Usineur B")})
        self.assertEqual(again["counts"], {"new": 0, "changed": 1, "same": 1})

    def test_02_ai_loop(self):
        parts = self.admin.get(self.base)["parts"]
        prompt = self.reader.get(self.base + "/prompt")["prompt"]
        self.assertIn("Ne jamais inventer un numéro", prompt)
        self.assertIn("LMP-100 ; A ; Tête en aluminium", prompt)
        self.assertIn(parts[0]["code"] + " ; " + parts[0]["name"], prompt)
        answer = [{"part": parts[0]["code"], "pn": "LMP-100", "rev": "A", "confiance": 0.9, "raison": "tête"},
                  {"part": parts[1]["code"], "pn": "LMP-200", "confiance": "50 %", "raison": "peut-être"},
                  {"part": parts[2]["code"], "pn": "aucun", "confiance": 0, "raison": "rien ne convient"},
                  {"part": parts[0]["code"], "pn": "LMP-999", "confiance": 0.99, "raison": "inventé"},
                  {"part": "P-999", "pn": "LMP-200", "confiance": 0.9, "raison": "?"}]
        text = "Voici la réponse :\n```json\n" + json.dumps(answer) + "\n```"
        pv = self.admin.post(self.base + "/ai", {"answer": text})
        self.assertEqual([r["verdict"] for r in pv["rows"]], ["sure", "choose", "todo", "refused", "refused"])
        self.assertIn("absent de la nomenclature", pv["rows"][3]["why"])
        self.assertIn("Aucun tableau JSON", self.fails(400, self.admin.post, self.base + "/ai", {"answer": "rien"}))
        done = self.admin.post(self.base + "/ai", {"answer": text, "mode": "apply"})
        self.assertEqual(done["applied"], {"linked": 1, "erp_todo": 1})
        by = {p["code"]: p for p in done["parts"]}
        self.assertEqual([x["label"] for x in by[parts[0]["code"]]["pns"]], ["LMP-100 A"])
        self.assertEqual(by[parts[0]["code"]]["pns"][0]["source"], "ai")
        self.assertEqual(by[parts[2]["code"]]["erp_todo"], 1)
        self.assertEqual(by[parts[1]["code"]]["pns"], [])  # « à choisir »: not applied unless picked
        # by hand: the second PN on the first part, then removed
        ids = [b["id"] for b in done["bom"]]
        both = self.admin.put(self.base + "/parts/{}".format(by[parts[0]["code"]]["id"]), {"pn_ids": ids})
        self.assertEqual(len({p["code"]: p for p in both["parts"]}[parts[0]["code"]]["pns"]), 2)
        self.fails(400, self.admin.put, self.base + "/parts/{}".format(by[parts[0]["code"]]["id"]), {"pn_ids": [99999]})
        self.fails(403, self.reader.put, self.base + "/parts/{}".format(by[parts[0]["code"]]["id"]), {"pn_ids": []})
        one = self.admin.put(self.base + "/parts/{}".format(by[parts[0]["code"]]["id"]), {"pn_ids": ids[:1]})
        self.assertEqual(len({p["code"]: p for p in one["parts"]}[parts[0]["code"]]["pns"]), 1)

    def test_03_rover_summary_copy(self):
        for table in ("diamond_company_parts", "diamond_part_pns"):
            self.assertIn(table, spacecopy.DIAMOND)
        demo = next(p["id"] for p in self.admin.get("/api/me")["projects"] if p["key"] == "DEMO")
        pn = self.admin.get("/api/diamond/p/{}/pn".format(demo))
        self.assertEqual(pn["counts"], {"parts": 23, "linked": 22, "todo": 1, "bom": 27})
        p14 = next(p for p in pn["parts"] if p["code"] == "P-14")
        self.assertEqual([x["label"] for x in p14["pns"]], ["RVR-3140-02 C", "RVR-3141-01"])
        summary = {c["code"]: c for c in self.admin.get("/api/diamond/p/{}/characteristics".format(demo))["summary"]}
        self.assertEqual(summary["C-10"]["pns"], ["RVR-5090-02"])
        self.assertEqual(summary["C-08"]["pns"], ["RVR-5180-01", "RVR-5190-03"])
        made = self.admin.post("/api/admin/spacecopy", {"key": "LAMPQ", "name": "Copie", "parts": {"diamond": "LAMPN"}})
        copy = self.admin.get("/api/diamond/p/{}/pn".format(made["project"]["id"]))
        self.assertEqual(copy["counts"]["bom"], 2)
        self.assertEqual(copy["counts"]["linked"], 1)


if __name__ == "__main__":
    unittest.main()
