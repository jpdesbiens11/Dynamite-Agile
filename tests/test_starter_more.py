"""0.60.43 (D-O-052): the Project Starter fills every module -- the Agile backlog by MVP (Versions MVP0…, epics then
their stories) and the Generator deliverables -- and a proven Space reads back as a Project Starter file (export),
which the prompt can carry as the worked example for the next product."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, starter, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))


class StarterMoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "m.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.result = cls.admin.post("/api/starter/apply", {"file": LAMPE})
        cls.pid = cls.result["project"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_backlog_by_mvp_and_deliverables(self):
        counts = self.result["counts"]
        self.assertEqual((counts["agile_backlog"], counts["agile_mvps"], counts["agile_deliverables"]), (8, 3, 4))
        with db.connect() as conn:
            versions = [r["name"] for r in conn.execute("SELECT name FROM agile_versions WHERE project_id = ? ORDER BY name", (self.pid,))]
            self.assertEqual(versions, ["MVP0", "MVP1", "MVP2"])
            story = conn.execute("SELECT i.parent_id, v.name, i.story_points FROM agile_issues i JOIN agile_versions v ON v.id = i.version_id "
                                 "WHERE i.project_id = ? AND i.title LIKE 'Entrevues%'", (self.pid,)).fetchone()
            self.assertIsNotNone(story["parent_id"])
            self.assertEqual((story["name"], story["story_points"]), ("MVP0", 3))
            refs = [r["doc_type"] for r in conn.execute("SELECT doc_type FROM codex_refs WHERE project_id = ? ORDER BY id", (self.pid,))]
            self.assertEqual(refs, ["LCV", "CDCF", "PUGH", "PDR"])

    def test_02_bad_backlog_is_refused_with_its_place(self):
        bad = copy.deepcopy(LAMPE)
        bad["backlog"][1]["parent"] = "S9"
        with self.assertRaises(ApiFailure) as err:
            self.admin.post("/api/starter/check", {"file": bad})
        self.assertIn("backlog[1].parent", str(err.exception))
        bad = copy.deepcopy(LAMPE)
        bad["deliverables"][0]["doc_type"] = "XYZ"
        with self.assertRaises(ApiFailure) as err:
            self.admin.post("/api/starter/check", {"file": bad})
        self.assertIn("deliverables[0].doc_type", str(err.exception))

    def test_03_a_proven_space_reads_back_as_a_starter_file(self):
        data = self.admin.get("/api/starter/export?space=LAMPE")
        clean, _warnings = starter.parse(json.dumps(data))  # what « Commencer » takes
        self.assertEqual(len(clean["requirements"]), len(LAMPE["requirements"]))
        self.assertGreaterEqual(len(clean["tests"]), len(LAMPE["tests"]))
        self.assertEqual(len(clean["diamond"]["functions"]), len(LAMPE["diamond"]["functions"]))
        self.assertGreaterEqual(len(clean["diamond"]["dfmea"]), len(LAMPE["diamond"]["dfmea"]))
        self.assertEqual(len(clean["more"]["backlog"]), 8)
        self.assertEqual({b["mvp"] for b in clean["more"]["backlog"]}, {"MVP0", "MVP1", "MVP2"})
        self.assertEqual(len(clean["more"]["deliverables"]), 4)
        self.assertTrue(any(t["verifies"] for t in clean["tests"]))
        status, headers, raw = self.admin.raw_get("/api/starter/export?space=LAMPE&download=1")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw.decode("utf-8"))["project"]["key"], "LAMPE")

    def test_04_the_prompt_carries_the_proven_space(self):
        text = self.admin.get("/api/starter/prompt?source=LAMPE")["text"]
        self.assertIn("Un Space éprouvé de l'équipe", text)
        self.assertIn('"key": "LAMPE"', text)
        self.assertIn("27. Montrez", text)
        self.assertIn("`backlog[]`", text)

    def test_05_export_is_for_managers(self):
        with db.connect() as conn:
            from core import auth as A
            uid = conn.execute("INSERT INTO users (username, display_name, password_hash, is_active, must_change_password, created_at) "
                               "VALUES ('lecteur', 'Lecteur', ?, 1, 0, 'x')", (A.hash_password("Lecteur-2026!x"),)).lastrowid
            conn.execute("INSERT INTO memberships (user_id, project_id, role) VALUES (?, ?, 'editor')", (uid, self.pid))
        reader = Client(self.url)
        reader.login("lecteur", "Lecteur-2026!x")
        with self.assertRaises(ApiFailure) as err:
            reader.get("/api/starter/export?space=LAMPE")
        self.assertEqual(err.exception.status, 403)


if __name__ == "__main__":
    unittest.main()
