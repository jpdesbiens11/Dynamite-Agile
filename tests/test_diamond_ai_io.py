"""0.60.104 (D-O-116): Diamond -- DFMEA, PFMEA and control plans to and from a spreadsheet or an AI assistant: the answer read
as JSON or CSV, the export re-imported unchanged gives « identique » on every row, the prompt templates (interview, review, the
codes of the Space, the exact keys), the preview (new, changed, identical, refused with its reason), « Appliquer la sélection »
with the unticked lines left out, the rules of the screens (S of the PFMEA locked, new PFMEA rows as drafts, an operation of the
plan's line), rights, the switches, the journal. On the Rover of DEMO."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from modules.diamond import ai_io as IO  # noqa: E402
from tests.test_diamond_process import dom_calls  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


def answer(items, prose=True):
    """What an assistant returns: a sentence, the ```json block, a list of points to check."""
    block = "```json\n" + json.dumps(items, ensure_ascii=False, indent=1) + "\n```"
    return "Voici le tableau :\n\n" + block + "\n\nÀ vérifier : la cale." if prose else block


class AiIoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = next(p["id"] for p in cls.admin.get("/api/me")["projects"] if p["key"] == "DEMO")
        cls.base = "/api/diamond/p/{}".format(cls.pid)
        made = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, made["user"]["id"]), {"role": "reader"})
        granted = [a["id"] for a in cls.admin.get(cls.base + "/process")["access"] if a["granted"]]
        cls.admin.put(cls.base + "/process/access", {"user_ids": granted + [made["user"]["id"]]})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", made["temp_password"], new_password="Lecture-2026!")

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

    def csv(self, path):
        status, _headers, data = self.admin.raw_get(self.base + path)
        self.assertEqual(status, 200, data[:200])
        return data.decode("utf-8")

    def preview(self, path, text, client=None):
        return (client or self.admin).post(self.base + path, {"file": text})

    def test_01_read_rows(self):
        fmt, rows = IO.read_rows(answer([{"Ligne": "L3", "O": 4}, {"Ligne": "", "Failure Mode": "x"}]))
        self.assertEqual((fmt, rows[0]), ("json", (1, {"ligne": "L3", "o": "4"})))
        fmt, rows = IO.read_rows('[{"op": "OP30", "d": 6}]')
        self.assertEqual(rows[0][1], {"op": "OP30", "d": "6"})
        fmt, rows = IO.read_rows("﻿Ligne;Failure Mode;S\n12;Entrefer;7\n\n13;\"Joint; vrillé\";6\n")
        self.assertEqual((fmt, rows[1]), ("csv", (4, {"ligne": "13", "failuremode": "Joint; vrillé", "s": "6"})))
        with self.assertRaises(ApiError):
            IO.read_rows("  ")
        self.assertEqual(IO.norm("Status de l'action"), "statusdelaction")
        self.assertEqual([IO.number(x, p) for x, p in (("L12", "L"), ("12", "L"), ("OP30", "OP"), ("PC-2", "PC"), ("F13 Mesurer", "F"))], [12, 12, 30, 2, 13])

    def test_02_dfmea(self):
        interview = self.reader.get(self.base + "/dfmea/prompt?mode=interview")
        self.assertIn("une seule question à la fois", interview["prompt"])
        self.assertIn("GÉNÈRE", interview["prompt"])
        self.assertIn("F13 ", interview["prompt"])
        self.assertIn("« Essai clé (Test Base) »", interview["prompt"])
        review = self.admin.get(self.base + "/dfmea/prompt?mode=review")["prompt"]
        self.assertIn("Déroulement : révision", review)
        self.fails(400, self.admin.get, self.base + "/dfmea/prompt?mode=magie")
        rows = self.admin.get(self.base + "/dfmea")["rows"]
        same = self.preview("/dfmea/import", self.csv("/dfmea/export.csv"))  # the round trip: nothing changes
        self.assertEqual(same["counts"], {"new": 0, "update": 0, "same": len(rows), "refused": 0}, [e for e in same["entries"] if e["kind"] != "same"][:3])
        gap = next(r for r in rows if r["failure_mode"].startswith("Impulsions manquées"))
        other = next(r for r in rows if r["function_number"] and r["function_number"] != gap["function_number"])
        items = [{"Ligne": "L{}".format(gap["line"]), "O": 3, "Actions": "Support réglable, nouvelle étude"},
                 {"Ligne": "", "Function of Focus Element": "F{}".format(gap["function_number"]), "Failure Mode": "Aimant décollé de l'arbre",
                  "Failure Effect": "Vitesse lue à zéro", "S": 7, "Failure Cause": "Colle non polymérisée", "O": 3, "D": 4},
                 {"Ligne": "L999", "O": 2},
                 {"Ligne": "L{}".format(gap["line"]), "Function of Focus Element": "F{}".format(other["function_number"])},
                 {"Ligne": "", "Failure Mode": "Hors échelle", "S": 12},
                 {"Ligne": "", "Function of Focus Element": "F999", "Failure Mode": "?"}]
        pv = self.preview("/dfmea/import", answer(items), self.reader)  # a reader may read the preview
        self.assertEqual(pv["counts"], {"new": 1, "update": 1, "same": 0, "refused": 4})
        kinds = {e["n"]: e for e in pv["entries"]}
        self.assertEqual(sorted(c[0] for c in kinds[1]["changes"]), ["Actions", "O"])
        self.assertIn("n'existe pas", kinds[3]["reason"])
        self.assertIn("a changé depuis l'export", kinds[4]["reason"])
        self.assertIn("de 1 à 10", kinds[5]["reason"])
        self.assertIn("absente de l'arbre", kinds[6]["reason"])
        self.assertEqual(len(self.admin.get(self.base + "/dfmea")["rows"]), len(rows))  # a preview writes nothing
        self.fails(403, self.reader.post, self.base + "/dfmea/import", {"file": answer(items), "mode": "apply"})
        done = self.admin.post(self.base + "/dfmea/import", {"file": answer(items), "mode": "apply"})
        self.assertEqual(done["applied"], {"new": 1, "update": 1})
        before, rows = len(rows), done["dfmea"]["rows"]
        self.assertEqual(len(rows), before + 1)
        self.assertEqual(next(r for r in rows if r["id"] == gap["id"])["occurrence"], 3)
        new = next(r for r in rows if r["failure_mode"] == "Aimant décollé de l'arbre")
        self.assertEqual(new["line"], gap["line"] + 1)  # after the last row of its function
        # « Prevention Controls » leaves without the good practices the tool appended, and they stay after a corrected text
        line = next(x for x in interview["prompt"].splitlines() if x.startswith('{"Ligne": "L%d"' % gap["line"]))
        team = json.loads(line)["Prevention Controls"]
        self.assertNotIn("Bonnes pratiques (industrie)", interview["prompt"])
        self.assertIn("Bonnes pratiques (industrie)", gap["prevention"])
        kept = self.preview("/dfmea/import", answer([{"Ligne": "L%d" % gap["line"], "Prevention Controls": team}]))
        self.assertEqual(kept["counts"]["same"], 1)
        self.admin.post(self.base + "/dfmea/import", {"file": answer([{"Ligne": "L%d" % gap["line"], "Prevention Controls": team + " Gabarit G-30."}]),
                                                      "mode": "apply"})
        stored = next(r for r in self.admin.get(self.base + "/dfmea")["rows"] if r["id"] == gap["id"])["prevention"]
        self.assertTrue(stored.startswith(team + " Gabarit G-30.\nBonnes pratiques (industrie)"), stored[:200])
        skipped = self.admin.post(self.base + "/dfmea/import", {"file": answer(items[1:2]), "mode": "apply", "skip": [1]})
        self.assertEqual(skipped["applied"], {"new": 0, "update": 0})
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'diamond_dfmea_import'").fetchone()[0], 3)

    def test_03_pfmea(self):
        gen = self.admin.get(self.base + "/pfmea/prompt?line=1")
        self.assertEqual(gen["mode"], "generate")
        self.assertIn("EXTRAIT FINAL DU DFMEA", gen["prompt"])
        interview = self.admin.get(self.base + "/pfmea/prompt?line=1&mode=interview")["prompt"]
        for text in ("OP30", "C-14", "« Cause 5M »", "une seule question à la fois", "laisse « S » vide"):
            self.assertIn(text, interview)
        same = self.preview("/pfmea/import", self.csv("/pfmea/export.csv"))
        self.assertEqual(same["counts"], {"new": 0, "update": 0, "same": 14, "refused": 0}, [e for e in same["entries"] if e["kind"] != "same"][:3])
        items = [{"Code": "PF-30.1", "D": 3},
                 {"Code": "", "Ligne": "L1", "Opération": "OP40", "Product Characteristic": "C-21", "Process Step": "Fermer le boîtier",
                  "Failure Mode": "Joint pincé", "Failure Effect": "Eau sur le Raspberry Pi", "Failure Cause": "Vis serrées en croix oubliées",
                  "Cause 5M": "Méthode", "O": 3, "D": 4},
                 {"Code": "PF-60.1", "S": 5},
                 {"op": "OP99", "failure_mode": "Hors ligne"},
                 {"Code": "PF-30.1", "S": 7}]  # the inherited S copied back: identical
        pv = self.preview("/pfmea/import", answer(items))
        self.assertEqual(pv["counts"], {"new": 1, "update": 1, "same": 1, "refused": 2})
        refused = [e["reason"] for e in pv["entries"] if e["kind"] == "refused"]
        self.assertIn("S 5 refusée", refused[0])
        self.assertIn("OP99 absente de L1", refused[1])
        done = self.admin.post(self.base + "/pfmea/import", {"file": answer(items), "mode": "apply"})
        rows = {r["code"]: r for r in done["pfmea"]["rows"]}
        self.assertEqual(rows["PF-30.1"]["detection"], 3)
        self.assertEqual((rows["PF-40.2"]["state"], rows["PF-40.2"]["s"], rows["PF-40.2"]["source"]), ("draft", 6, "ai"))  # a draft, S of C-21
        self.admin.put("/api/admin/features", {"features": {"diamond_pfmea": False}})
        try:
            self.fails(404, self.admin.post, self.base + "/pfmea/import", {"file": answer(items)})
            self.assertEqual(self.admin.raw_get(self.base + "/pfmea/export.csv")[0], 404)
        finally:
            self.admin.put("/api/admin/features", {"features": {"diamond_pfmea": True}})

    def test_04_control_plans(self):
        same = self.preview("/cplans/import", self.csv("/cplans/export.csv"))
        self.assertEqual(same["counts"], {"new": 0, "update": 0, "same": 20, "refused": 0}, [e for e in same["entries"] if e["kind"] != "same"][:3])
        one = self.csv("/cplans/export.csv?plan=2")
        self.assertEqual(len([x for x in one.splitlines()[1:] if x.strip()]), 11)
        review = self.admin.get(self.base + "/cplans/prompt?mode=review&plan=2")["prompt"]
        for text in ("PC-2", "« Reaction Plan »", "Déroulement : révision", "P-21"):
            self.assertIn(text, review)
        items = [{"Plan": "PC-2", "Code": "CP-30.1", "Frequency": "10 par heure"},
                 {"Plan": "PC-3", "Code": "", "Opération": "OP20", "Product Characteristic": "C-21", "Measurement Technique": "Comparateur",
                  "Sample": "1", "Frequency": "chaque prototype", "Control Method": "Fiche du prototype", "Reaction Plan": "Reprendre le joint"},
                 {"Plan": "PC-9", "Code": "", "Product Characteristic": "C-10"},
                 {"Plan": "PC-1", "Code": "", "Opération": "OP30", "Product Characteristic": "C-14"},
                 {"Plan": "PC-2", "Code": "", "Opération": "OP99", "Product Characteristic": "C-14"},
                 {"Plan": "PC-2", "Code": "", "Opération": "OP20"}]
        pv = self.preview("/cplans/import", answer(items, prose=False))
        self.assertEqual(pv["counts"], {"new": 1, "update": 1, "same": 0, "refused": 4})
        reasons = " | ".join(e["reason"] for e in pv["entries"] if e["kind"] == "refused")
        for text in ("PC-9", "plan de réception", "OP99 absente", "une C-n ou nomme"):
            self.assertIn(text, reasons)
        done = self.admin.post(self.base + "/cplans/import", {"file": answer(items), "mode": "apply"})
        plans = {p["number"]: p for p in done["cplans"]["plans"]}
        self.assertEqual(next(i for i in plans[2]["items"] if i["code"] == "CP-30.1")["frequency"], "10 par heure")
        self.assertIn("CP-20.4", [i["code"] for i in plans[3]["items"]])
        self.fails(403, self.reader.post, self.base + "/cplans/import", {"file": answer(items), "mode": "apply"})

    def test_05_screens(self):
        js = (BASE_DIR / "static" / "js" / "diamond" / "ai_io.js").read_text("utf-8")
        self.assertNotIn("innerHTML", js)
        for tag in ("0.60.104-ai-prompt", "0.60.104-ai-import", "0.60.104-ai-export"):
            self.assertIn(tag, js)
        for name in ("ai_io", "dfmea", "pfmea", "cplans"):
            text = (BASE_DIR / "static" / "js" / "diamond" / (name + ".js")).read_text("utf-8")
            for call, args in dom_calls(text):
                for arg in args:
                    self.assertFalse(arg.startswith("[") or ".map(" in arg or arg.endswith(": null") or arg == "null", "{} : {}".format(name, arg[:60]))
        self.assertIn("/js/diamond/ai_io.js", json.dumps(modules.nav_manifest()))


if __name__ == "__main__":
    unittest.main()
