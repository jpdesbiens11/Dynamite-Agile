"""Tickets CSV re-import (D-B-008), from a real user file: Excel « ; »
separator, rows re-imported after a first import, and copied rows given
new keys (DEMO-21...) that do not exist yet.

    python -m unittest tests.test_csv_reimport -v
"""
import csv
import io
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


class CsvReimportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "r.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "DEMO", "name": "Démo", "description": ""})
        cls.base = "/api/agile/p/{}".format(cls.admin.get("/api/admin/projects")["projects"][0]["id"])
        cls.admin.post(cls.base + "/init")
        task = next(t for t in cls.admin.get(cls.base + "/meta")["types"] if t["icon_key"] == "task")
        for title in ("Banc de court-circuit", "Harnais d'équilibrage", "Seuil thermique"):
            cls.admin.post(cls.base + "/issues", {"type_id": task["id"], "title": title})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def export_excel(self):
        """Export, then save it the way French Excel does: « ; » separator."""
        with self.admin.opener.open(self.url + self.base + "/export/tickets") as resp:
            rows = list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))
        return rows

    def to_excel_text(self, rows):
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        return out.getvalue()

    def imp(self, text):
        return self.admin.post(self.base + "/import/tickets", {"csv": text})

    def test_user_scenario(self):
        rows = self.export_excel()
        # Copy two rows under keys that do not exist yet (what the user did).
        copies = [dict(rows[0], key="DEMO-21"), dict(rows[1], key="DEMO-22")]
        text = self.to_excel_text(rows + copies)

        first = self.imp(text)
        statuses = [r["status"] for r in first["report"]]
        self.assertEqual(statuses, ["inchangée"] * 3 + ["créée", "créée"], first["report"])
        self.assertEqual([first["report"][3]["row"], first["report"][4]["row"]], ["DEMO-21", "DEMO-22"])
        self.assertIn("créé avec cette clé", first["report"][3]["warning"])
        # A new ticket created afterwards continues after the highest number.
        task = next(t for t in self.admin.get(self.base + "/meta")["types"] if t["icon_key"] == "task")
        self.assertEqual(self.admin.post(self.base + "/issues", {"type_id": task["id"], "title": "Après"})["key"], "DEMO-23")
        self.admin.delete(self.base + "/issues/23")

        # Same file again: nothing refused, no duplicate (DEMO-21 -> DEMO-4 remembered).
        second = self.imp(text)
        self.assertEqual([r["status"] for r in second["report"]], ["inchangée"] * 5, second["report"])
        self.assertEqual(len(self.export_excel()), 5)
        # Deleted number: never reused, created under a fresh number, no duplicate on re-import.
        rows = self.export_excel()
        again = self.to_excel_text(rows + [dict(rows[0], key="DEMO-23", title="Numéro supprimé")])
        made = self.imp(again)["report"][-1]
        self.assertEqual((made["status"], made["row"]), ("créée", "DEMO-24"), made)
        self.assertEqual(self.imp(again)["report"][-1]["status"], "inchangée")
        self.admin.delete(self.base + "/issues/24")

        # A real change on a stale line is still refused, naming what would change.
        rows = self.export_excel()
        stale_time = rows[0]["updated_at"]
        time.sleep(1.1)  # updated_at has one-second resolution
        self.admin.patch(self.base + "/issues/1", {"priority": "low"})  # someone edits on the server
        rows[0]["title"] = "Banc de court-circuit (rév. B)"
        rows[0]["updated_at"] = stale_time
        refused = self.imp(self.to_excel_text(rows[:1]))["report"][0]
        self.assertEqual(refused["status"], "refusée")
        self.assertIn("titre", refused["reason"])
        # Clearing updated_at imposes the file's values.
        rows[0]["updated_at"] = ""
        forced = self.imp(self.to_excel_text(rows[:1]))["report"][0]
        self.assertEqual(forced["status"], "mise à jour", forced)


if __name__ == "__main__":
    unittest.main()
