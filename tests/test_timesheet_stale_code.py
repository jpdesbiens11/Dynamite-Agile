"""0.60.20: a range entered before the Funding Space of its Space was changed keeps its old code. The screen now shows
that code as « hors du Funding Space » (instead of showing the first code of the new list, which looked saved), and the
week is not submitted until the range gets a code of the current Funding Space."""
import datetime as dt
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


class StaleCodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
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

    def test_01_changed_funding_space(self):
        a = self.admin
        pid = a.post("/api/admin/projects", {"key": "RNG", "name": "Ding"})["project"]["id"]
        monday = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat()
        entry = a.post("/api/timesheet/entries", {"project_id": pid, "work_date": monday, "hours": 8, "description": "x"})["entry"]
        old = entry["task_key"]  # a PDP code, the default Funding Space
        s = a.post("/api/timesheet/budget/sets", {"label": "C'est un projet facile"})
        a.post("/api/timesheet/budget/lines", {"set_id": s["id"], "code": "PF-01", "label": "Je perds mon temps"})
        a.put("/api/timesheet/projects/{}".format(pid), {"task_set": s["key"]})
        with self.assertRaises(ApiFailure) as err:
            a.post("/api/timesheet/week/submit", {"start": monday})
        self.assertEqual(err.exception.status, 400)
        self.assertIn("le code {} n'est pas dans le Funding Space actuel de RNG".format(old), str(err.exception))
        self.assertIn("PF-01", str(err.exception))
        a.patch("/api/timesheet/entries/{}".format(entry["id"]), {"task_key": "PF-01"})
        week = a.post("/api/timesheet/week/submit", {"start": monday})
        self.assertEqual(week["week"]["status"], "submitted")
        self.assertEqual(week["entries"][0]["task_key"], "PF-01")

    def test_02_screen(self):
        js = (BASE_DIR / "static" / "js" / "timesheet" / "timesheet.js").read_text("utf-8")
        self.assertIn("0.60.20-stale-code", js)
        self.assertIn("hors du Funding Space", js)


if __name__ == "__main__":
    unittest.main()
