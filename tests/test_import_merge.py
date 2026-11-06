"""0.60.53 (D-O-062): « Importer la réponse de l'IA » completes a Space part by part (« Compléter ») or rebuilds its Diamond
from the file after a full backup (« Tout remplacer », admins of the Space)."""
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
from modules.diamond import import_merge  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

PW = "Import-Merge-2026!"
ROVER = json.loads((BASE_DIR / "deploy" / "spaces_exemples" / "rover.json").read_text("utf-8"))["diamond"]


def part(*keys, **extra):
    d = {k: [{kk: vv for kk, vv in r.items() if kk not in ("owner", "test")} for r in ROVER[k]] for k in keys}
    d.update(extra)
    return {"diamond": d}


class ImportMergeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cfg = load_config(cls.data_dir)
        cfg["port"] = 0
        db.init_db(cls.data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "PAS", "name": "Pas à pas"})["project"]["id"]
        cls.rep = cls.admin.post("/api/admin/projects", {"key": "REP", "name": "Remplacer"})["project"]["id"]
        created = cls.admin.post("/api/admin/users", {"username": "redac", "display_name": "Rédactrice"})
        for pid in (cls.pid, cls.rep):
            cls.admin.put("/api/admin/projects/{}/members/{}".format(pid, created["user"]["id"]), {"role": "editor"})
        cls.editor = Client(cls.url)
        cls.editor.login("redac", created["temp_password"], PW)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def base(self, pid):
        return "/api/diamond/p/{}/import".format(pid)

    def have(self, pid):
        with db.connect() as conn:
            return import_merge.present(conn, pid)

    def test_01_complete_part_by_part(self):
        story = self.editor.post(self.base(self.pid), {"file": part(story=ROVER["story"])})  # the Storyline alone
        self.assertEqual(story["counts"]["story"], 7)
        tree = self.editor.post(self.base(self.pid), {"file": part("functions")})  # then the tree alone
        self.assertEqual(tree["counts"]["functions"], len(ROVER["functions"]))
        auto = self.have(self.pid)["dfmea"]
        self.assertEqual(auto, len(ROVER["functions"]))  # one row written by the tool per function
        full = json.loads(json.dumps(part("functions", "ports", "flows", "parts", "risks", "dfmea", story=ROVER["story"])))
        dry = self.editor.post(self.base(self.pid), {"file": full, "dry": True})
        self.assertEqual(dry["counts"]["functions"], 0)
        self.assertEqual(dry["kept"]["functions"], len(ROVER["functions"]))
        self.assertEqual(dry["kept"]["story"], 7)
        self.assertEqual((dry["counts"]["ports"], dry["counts"]["flows"], dry["counts"]["parts"], dry["counts"]["risks"]),
                         (len(ROVER["ports"]), len(ROVER["flows"]), len(ROVER["parts"]), len(ROVER["risks"])))
        self.assertEqual(dry["dropped"], {})
        made = self.editor.post(self.base(self.pid), {"file": full})
        self.assertTrue(made["imported"])
        now = self.have(self.pid)
        self.assertEqual((now["functions"], now["story"], now["parts"]), (len(ROVER["functions"]), 7, len(ROVER["parts"])))
        with db.connect() as conn:  # the file's rows replaced the tool's rows of the same functions, never doubled them
            covered = {r["function"] for r in ROVER["dfmea"] if r.get("function")}
            dup = conn.execute("SELECT function_id, COUNT(*) FROM diamond_dfmea WHERE project_id = ? AND failure_mode LIKE 'Ne réalise pas « %' "
                               "GROUP BY function_id", (self.pid,)).fetchall()
            self.assertLessEqual(len(dup), len(ROVER["functions"]) - len(covered))
        with self.assertRaises(ApiFailure) as err:  # everything is there now
            self.editor.post(self.base(self.pid), {"file": full, "dry": True})
        self.assertEqual(err.exception.status, 409)
        self.assertIn("Tout remplacer", str(err.exception))

    def test_02_a_risk_by_its_F_number_on_the_existing_tree(self):
        number = ROVER["functions"][1]["ref"]
        with db.connect() as conn:
            row = conn.execute("SELECT number FROM diamond_functions WHERE project_id = ? AND parent_id IS NOT NULL ORDER BY number LIMIT 1",
                               (self.pid,)).fetchone()
        ref = "F{}".format(row["number"]) if row else number
        with db.connect() as conn:
            conn.execute("DELETE FROM diamond_risks WHERE project_id = ?", (self.pid,))
            conn.commit()
        risk = {"title": "Câble pincé", "category": "technique", "phase": "C", "probability": 2, "impact": 3, "response": "reduire",
                "function": ref}
        made = self.editor.post(self.base(self.pid), {"file": {"diamond": {"risks": [risk]}}})
        self.assertEqual(made["counts"]["risks"], 1)
        with db.connect() as conn:
            self.assertIsNotNone(conn.execute("SELECT function_id FROM diamond_risks WHERE project_id = ?", (self.pid,)).fetchone()[0])

    def test_03_replace_backs_up_then_rebuilds(self):
        self.admin.post(self.base(self.rep), {"file": part("functions", story=ROVER["story"])})
        with self.assertRaises(ApiFailure) as err:
            self.editor.post(self.base(self.rep), {"file": part("functions"), "mode": "replace", "dry": True})
        self.assertEqual(err.exception.status, 403)
        smaller = part("functions")
        smaller["diamond"]["functions"] = smaller["diamond"]["functions"][:4]
        dry = self.admin.post(self.base(self.rep), {"file": smaller, "mode": "replace", "dry": True})
        self.assertEqual(dry["removed"]["functions"], len(ROVER["functions"]))
        self.assertNotIn("story", dry["removed"])  # the file has no Storyline: the Space keeps its own
        self.assertEqual(self.have(self.rep)["functions"], len(ROVER["functions"]))  # nothing removed by a dry run
        made = self.admin.post(self.base(self.rep), {"file": smaller, "mode": "replace"})
        self.assertTrue((self.data_dir / "backups" / made["backup"]).exists())
        now = self.have(self.rep)
        self.assertEqual((now["functions"], now["story"]), (4, 7))
        self.assertEqual(now["dfmea"], 4)  # only the rows of the new tree
        with db.connect() as conn:
            log = conn.execute("SELECT details FROM audit_log WHERE action = 'diamond_import' AND object_id = ? ORDER BY id DESC",
                               (str(self.rep),)).fetchone()
        self.assertIn("replace", log["details"])


if __name__ == "__main__":
    unittest.main()
