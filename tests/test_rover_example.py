"""0.60.46 (D-O-055): the academic example Rover -- a complete Project Starter file that a fresh installation never loads,
published on the installation page, and the design methods (ideation, Pugh, Kepner-Tregoe) of the Project Starter format."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, starter, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from tools import make_rover_example  # noqa: E402
from tools.api_client import Client  # noqa: E402

FILE = BASE_DIR / "deploy" / "spaces_exemples" / "rover.json"


class RoverFileTest(unittest.TestCase):
    def test_01_file_is_current_and_valid(self):
        built = json.dumps(make_rover_example.build(), ensure_ascii=False, indent=1) + "\n"
        self.assertEqual(FILE.read_text("utf-8"), built, "relancez python3 tools/make_rover_example.py")
        clean, _warnings = starter.parse(built)
        self.assertEqual(clean["project"]["key"], "ROVER")
        self.assertEqual([m["username"] for m in clean["team"]], ["nina", "lea", "hugo", "alexis"])
        refs = [f["ref"] for f in clean["diamond"]["functions"]]
        self.assertEqual(refs, ["F{}".format(n) for n in range(1, len(refs) + 1)])  # Diamond keeps the same numbers
        covered = {d["function"] for d in clean["diamond"]["dfmea"]}
        self.assertEqual(covered, set(refs))  # one DFMEA line per function: nothing left to complete
        self.assertEqual({b["mvp"] for b in clean["more"]["backlog"]}, {"MVP0", "MVP1", "MVP2", "MVP3"})
        self.assertEqual({k: len(v) for k, v in clean["more"]["tools"].items()}, {"ideation": 1, "pugh": 1, "kt": 1})
        self.assertLessEqual(len(clean["pages"]), 30)

    def test_02_tools_are_checked(self):
        raw = json.loads(FILE.read_text("utf-8"))
        raw["tools"]["pugh"][0]["criteria"][0]["requirement"] = "REQ-99"
        with self.assertRaises(ApiError) as caught:
            starter.parse(json.dumps(raw))
        self.assertIn("tools.pugh[0].criteria[0].requirement", caught.exception.message)
        raw = json.loads(FILE.read_text("utf-8"))
        raw["tools"]["kt"][0]["criteria"][0]["scores"] = {raw["tools"]["kt"][0]["alternatives"][0]["name"]: 5}
        with self.assertRaises(ApiError) as caught:
            starter.parse(json.dumps(raw))
        self.assertIn("0 ou 1", caught.exception.message)

    def test_03_demo_on_the_installation_page(self):
        subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build_site.py")], check=True, capture_output=True)
        for rel in ("site/installation.html", "site/en/installation.html"):
            page = (BASE_DIR / rel).read_text("utf-8")
            self.assertIn('data-new="0.60.49-demo"', page)
            self.assertIn("Cacher pour tous", page)
        self.assertFalse((BASE_DIR / "deploy" / "starter_exemples" / "rover.json").exists())  # not among the « Commencer » examples


class RoverApplyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "r.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_10_rover_file_still_loads_as_its_own_space(self):
        keys = [p["key"] for p in self.admin.get("/api/admin/projects")["projects"]]
        self.assertEqual(keys, ["DEMO"])  # 0.60.49 (D-O-058): one Space at installation
        self.assertNotIn("rover", [x["id"] for x in self.admin.get("/api/starter/examples")["examples"]])
        result = self.admin.post("/api/starter/apply", {"file": FILE.read_text("utf-8")})
        counts = result["counts"]
        self.assertEqual((counts["agile_tools_ideation"], counts["agile_tools_pugh"], counts["agile_tools_kt"]), (1, 1, 1))
        self.assertEqual(counts["diamond_dfmea"], 41)
        pid = result["project"]["id"]
        with db.connect() as conn:
            kt = conn.execute("SELECT status, decision_alt_id FROM tools_kt WHERE project_id = ?", (pid,)).fetchone()
            self.assertEqual(kt["status"], "decided")
            wants = conn.execute("SELECT COUNT(*) FROM tools_kt_criteria c JOIN tools_kt k ON k.id = c.kt_id WHERE k.project_id = ? "
                                 "AND c.kind = 'want'", (pid,)).fetchone()[0]
            self.assertEqual(wants, 6)
            scores = conn.execute("SELECT COUNT(*) FROM goldmine_pugh_scores s JOIN goldmine_pugh_criteria c ON c.id = s.criterion_id "
                                  "JOIN goldmine_pugh p ON p.id = c.pugh_id WHERE p.project_id = ?", (pid,)).fetchone()[0]
            self.assertEqual(scores, 27)
            ideas = conn.execute("SELECT COUNT(*) FROM tools_ideas i JOIN tools_ideation s ON s.id = i.session_id WHERE s.project_id = ?",
                                 (pid,)).fetchone()[0]
            self.assertEqual(ideas, 16)
            f15 = conn.execute("SELECT text, ftype FROM diamond_functions WHERE project_id = ? AND number = 15", (pid,)).fetchone()
            self.assertEqual((f15["text"], f15["ftype"]), ("Convertir l'écho 5 V en 3,3 V", "technique"))
        # a proven Space reads back with its methods, and the file is one « Commencer » takes
        exported = self.admin.get("/api/starter/export?space=ROVER")
        self.assertEqual(exported["tools"]["kt"][0]["decision"], exported["tools"]["kt"][0]["alternatives"][0]["name"])
        self.assertEqual(len(exported["tools"]["pugh"][0]["criteria"]), 9)
        starter.parse(json.dumps(exported))


if __name__ == "__main__":
    unittest.main()
