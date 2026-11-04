"""0.32.0: Timesheet financial spaces and budget lines administered in « Spaces et organismes » (D-B-084).

    python -m unittest tests.test_lot_v021 -v
"""
import datetime as dt
import io
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class LotV021Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "PARI", "name": "Projet PARI", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur lia | Lia Lab | utilisateur | actif\n"
                                                                  "droit lia | PARI | editeur\n"})
        c = done["created"][0]
        cls.lia = Client(cls.url)
        cls.lia.login(c["username"], c["temp_password"], "Essai-Lot-VingtEtUn-2026!")
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["PARI"]
        cls.day = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def status(self, fn):
        try:
            fn()
        except ApiFailure as exc:
            return exc.status
        return 200

    def test_01_financial_spaces_and_lines(self):
        data = self.admin.get("/api/timesheet/budget")["sets"]
        self.assertEqual({k: len(v["tasks"]) for k, v in data.items()}, {"pdp": 19, "interne": 7})  # 0.60.01: steps of the PDP, internal time and leave
        claim = {t["key"]: t["claimable"] for t in data["pdp"]["tasks"]}
        self.assertTrue(claim["A-01"] and claim["D-21"])
        internal = {t["key"]: t["claimable"] for t in data["interne"]["tasks"]}
        self.assertFalse(internal["INT-VAC"] or internal["INT-SAN"])
        self.assertEqual(self.status(lambda: self.lia.get("/api/timesheet/budget")), 403)
        self.assertEqual(self.status(lambda: self.lia.post("/api/timesheet/budget/sets", {"label": "X"})), 403)

        made = self.admin.post("/api/timesheet/budget/sets", {"label": "Programme PARI-CNRC 2027"})
        self.assertEqual(self.status(lambda: self.admin.post("/api/timesheet/budget/sets", {"label": "programme pari-cnrc 2027"})), 409)
        self.assertEqual(self.status(lambda: self.admin.post("/api/timesheet/budget/lines", {
            "set_id": made["id"], "code": "pari 1", "label": "x"})), 400)
        a = self.admin.post("/api/timesheet/budget/lines", {"set_id": made["id"], "code": "pari-01", "label": "Essais"})
        b = self.admin.post("/api/timesheet/budget/lines", {"set_id": made["id"], "code": "PARI-02", "label": "Rapport",
                                                            "claimable": False})
        self.assertEqual(a["code"], "PARI-01")
        self.assertEqual(self.status(lambda: self.admin.post("/api/timesheet/budget/lines", {
            "set_id": made["id"], "code": "PARI-01", "label": "doublon"})), 409)

        self.admin.put("/api/timesheet/projects/{}".format(self.pid), {"task_set": made["key"], "organism": "CNRC-PARI"})
        week = self.lia.get("/api/timesheet/week")
        tasks = [t["key"] for t in week["meta"]["task_sets"][made["key"]]["tasks"]]
        self.assertEqual(tasks, ["PARI-01", "PARI-02"])
        entry = self.lia.post("/api/timesheet/entries", {"work_date": self.day, "project_id": self.pid, "task_key": "PARI-01",
                                                         "hours": 3, "description": "Essai de vibration"})["entry"]
        self.assertEqual(self.status(lambda: self.lia.post("/api/timesheet/entries", {
            "work_date": self.day, "project_id": self.pid, "task_key": "A-01", "hours": 1, "description": "x"})), 400)

        # deactivated: kept on its range, no longer offered; never deleted once used
        self.admin.patch("/api/timesheet/budget/lines/{}".format(a["id"]), {"active": False, "label": "Essais de qualification"})
        self.lia.patch("/api/timesheet/entries/{}".format(entry["id"]), {"hours": 4})
        self.assertEqual(self.status(lambda: self.lia.post("/api/timesheet/entries", {
            "work_date": self.day, "project_id": self.pid, "task_key": "PARI-01", "hours": 1, "description": "x"})), 400)
        self.assertEqual(self.status(lambda: self.admin.call("DELETE", "/api/timesheet/budget/lines/{}".format(a["id"]))), 409)
        self.assertEqual(self.lia.get("/api/timesheet/week")["entries"][0]["task_label"], "Essais de qualification")
        self.admin.call("DELETE", "/api/timesheet/budget/lines/{}".format(b["id"]))  # never used: removed
        self.assertEqual(self.status(lambda: self.admin.patch("/api/timesheet/budget/sets/{}".format(made["id"]),
                                                              {"active": False})), 409)  # PARI uses it

        with self.admin.opener.open(self.url + "/api/timesheet/export.xlsx?status=all&from={}&to={}".format(
                self.day, (dt.date.fromisoformat(self.day) + dt.timedelta(days=6)).isoformat())) as resp:
            with zipfile.ZipFile(io.BytesIO(resp.read())) as z:
                text = "".join(z.read(n).decode() for n in z.namelist() if n.endswith(".xml"))
        self.assertIn("Essais de qualification", text)
        self.assertIn("Pré-étude", text)  # the PDP codes in the Lisez-moi legend
        self.assertIn("(non réclamable)", text)  # INT-VAC / INT-SAN in the Lisez-moi legend


if __name__ == "__main__":
    unittest.main(verbosity=2)
