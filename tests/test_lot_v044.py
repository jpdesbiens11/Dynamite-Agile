"""0.50.5 (D-B-111, core lot v0.30): annual review in 3 signed steps, internship evaluation, professional profile.

    python -m unittest tests.test_lot_v044 -v
"""
import datetime as dt
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, profile, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

RULES = """
utilisateur lea | Léa Systèmes | utilisateur | actif
utilisateur paul | Paul Stagiaire | utilisateur | actif
utilisateur marc | Marc Gestion | utilisateur | actif
utilisateur zoe | Zoé Autre | utilisateur | actif
"""
STATIC = BASE_DIR / "static"


class LotV044Test(unittest.TestCase):
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
        cls.server = router.create_server(cfg, STATIC, data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.c, cls.ids = {}, {}
        for item in done["created"]:
            client = Client(url)
            me = client.login(item["username"], item["temp_password"], "Essai-Lot-Trente-2026!")
            cls.c[item["username"]], cls.ids[item["username"]] = client, me["user"]["id"]
        for name in ("lea", "paul"):
            cls.c[name].put("/api/me/prefs", {"manager_id": cls.ids["marc"]})
        cls.year = dt.date.today().year

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_profile_rights_and_context(self):
        lea, marc, zoe = self.c["lea"], self.c["marc"], self.c["zoe"]
        uid = self.ids["lea"]
        res = marc.patch("/api/profile/{}".format(uid), {"job_title": "Ingénieure systèmes", "level": "intermediate",
                                                         "hire_date": "2024-01-15"})
        self.assertEqual(res["profile"]["level_label"], "Intermédiaire (3 à 7 ans)")
        self.assertTrue(res["profile"]["seniority"])
        with self.assertRaises(ApiFailure) as err:  # title and level are the manager's
            lea.patch("/api/profile/{}".format(uid), {"job_title": "Cheffe"})
        self.assertEqual(err.exception.status, 403)
        eid = lea.post("/api/profile/{}/entries".format(uid), {"section": "education", "title": "B.Ing. génie électrique",
                                                               "org": "Polytechnique Montréal", "period": "2016 – 2020"})["id"]
        lea.patch("/api/profile/entries/{}".format(eid), {"details": "Projet de fin d'études : buse chauffante"})
        with self.assertRaises(ApiFailure) as err:  # the background is the employee's
            marc.post("/api/profile/{}/entries".format(uid), {"section": "skill", "title": "x"})
        self.assertEqual(err.exception.status, 403)
        seen = marc.get("/api/profile/{}".format(uid))
        self.assertEqual((seen["relation"], seen["entries"][0]["details"]), ("manager", "Projet de fin d'études : buse chauffante"))
        for outsider in (zoe, self.admin):  # private like the objectives
            with self.assertRaises(ApiFailure) as err:
                outsider.get("/api/profile/{}".format(uid))
            self.assertEqual(err.exception.status, 403)
        self.assertNotIn("buse chauffante", str(self.admin.get("/api/admin/audit")))  # private text never journalled
        self.assertEqual(profile._seniority("2024-01-15", dt.date(2026, 10, 4)), "2 ans et 8 mois")

    def test_02_employee_cycle_signed_step_by_step(self):
        lea, marc = self.c["lea"], self.c["marc"]
        uid, y = self.ids["lea"], self.year
        base = "/api/reviews/{}/{}".format(uid, y)
        self.assertIn("Aucun objectif", " ".join(lea.get("/api/reviews/{}?year={}".format(uid, y))["blockers"]["start"]))
        o1 = lea.post("/api/objectives/{}/{}".format(uid, y), {"kind": "annual", "title": "Plan de qualification"})["id"]
        with self.assertRaises(ApiFailure) as err:  # mid is not open before start is signed by both
            lea.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": o1, "employee_comment": "x"})
        self.assertEqual(err.exception.status, 409)
        lea.post(base + "/sign/start", {})
        marc.post(base + "/sign/start", {})
        with self.assertRaises(ApiFailure) as err:  # a comment on every item before signing mid
            lea.post(base + "/sign/mid", {})
        self.assertIn("Plan de qualification", str(err.exception))
        with self.assertRaises(ApiFailure) as err:  # each side its own fields
            lea.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": o1, "manager_comment": "x"})
        self.assertEqual(err.exception.status, 403)
        lea.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": o1, "employee_comment": "À 60 %"})
        marc.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": o1, "manager_comment": "Bon rythme"})
        lea.post(base + "/sign/mid", {})
        marc.post(base + "/sign/mid", {})
        with self.assertRaises(ApiFailure) as err:  # signed = read-only
            lea.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": o1, "employee_comment": "changé"})
        self.assertEqual(err.exception.status, 409)
        lea.put(base + "/item", {"phase": "end", "item_type": "objective", "item_id": o1, "employee_comment": "Livré",
                                 "employee_verdict": "achieved"})
        marc.put(base + "/item", {"phase": "end", "item_type": "objective", "item_id": o1, "manager_comment": "Livré tôt"})
        marc.put(base + "/phase/end", {"manager_comment": "Très bonne année"})
        with self.assertRaises(ApiFailure) as err:  # every item needs the manager's verdict
            marc.post(base + "/sign/end", {})
        self.assertIn("Verdict manquant", str(err.exception))
        marc.put(base + "/item", {"phase": "end", "item_type": "objective", "item_id": o1, "verdict": "exceeded"})
        marc.post(base + "/sign/end", {})
        with self.assertRaises(ApiFailure):  # the year closes only once both signed the end step
            marc.post("/api/objectives/{}/{}/archive".format(uid, y), {"carry": []})
        lea.put(base + "/phase/end", {"employee_comment": "Fière du plan"})
        lea.post(base + "/sign/end", {})
        data = lea.get("/api/reviews/{}?year={}".format(uid, y))
        self.assertEqual(data["current"], "done")
        self.assertEqual(data["reviews"]["objective:{}".format(o1)]["end"]["verdict"], "exceeded")
        marc.post(base + "/reopen/end", {})  # the manager can reopen
        self.assertFalse(lea.get("/api/reviews/{}?year={}".format(uid, y))["phases"]["end"]["signed"])
        with self.assertRaises(ApiFailure) as err:
            lea.post(base + "/reopen/mid", {})
        self.assertEqual(err.exception.status, 403)
        lea.post(base + "/sign/end", {})
        marc.post(base + "/sign/end", {})
        self.assertEqual(marc.post("/api/objectives/{}/{}/archive".format(uid, y), {"carry": []})["archived"], y)

    def test_03_intern_evaluation(self):
        paul, marc = self.c["paul"], self.c["marc"]
        uid, y = self.ids["paul"], self.year
        res = marc.patch("/api/profile/{}".format(uid), {"kind": "intern", "start_date": "{}-05-04".format(y),
                                                         "end_date": "{}-02-01".format(y + 1), "school": "ÉTS", "program": "Génie électrique"})
        self.assertIn("9 mois", res["warning"] or "")  # 4 to 8 months expected: said, not refused
        self.assertIsNone(marc.patch("/api/profile/{}".format(uid), {"end_date": "{}-12-18".format(y)})["warning"])
        with self.assertRaises(ApiFailure):
            marc.patch("/api/profile/{}".format(uid), {"end_date": "{}-04-01".format(y)})
        data = paul.get("/api/reviews/{}?year={}".format(uid, y))
        self.assertEqual((data["labels"]["start"], data["labels"]["end"]), ("Accueil", "Évaluation finale"))
        base = "/api/reviews/{}/{}".format(uid, y)
        oid = paul.post("/api/objectives/{}/{}".format(uid, y), {"kind": "annual", "title": "Banc de test de la buse"})["id"]
        for phase in ("start", "mid"):
            if phase == "mid":
                paul.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": oid, "employee_comment": "Montage fait"})
                marc.put(base + "/item", {"phase": "mid", "item_type": "objective", "item_id": oid, "manager_comment": "Bien"})
            paul.post(base + "/sign/" + phase, {})
            marc.post(base + "/sign/" + phase, {})
        with self.assertRaises(ApiFailure) as err:  # the grid is the tutor's
            paul.put(base + "/rating", {"criterion": "autonomie", "score": 4})
        self.assertEqual(err.exception.status, 403)
        marc.put(base + "/item", {"phase": "end", "item_type": "objective", "item_id": oid, "manager_comment": "Banc livré",
                                  "verdict": "achieved"})
        marc.put(base + "/phase/end", {"manager_comment": "Stage réussi"})
        with self.assertRaises(ApiFailure) as err:
            marc.post(base + "/sign/end", {})
        self.assertIn("Grille de stage incomplète", str(err.exception))
        with self.assertRaises(ApiFailure):
            marc.put(base + "/rating", {"criterion": "technique", "score": 7})
        for k in ("technique", "qualite", "autonomie", "communication", "equipe", "apprentissage"):
            marc.put(base + "/rating", {"criterion": k, "score": 3, "comment": "Exemple concret"})
        with self.assertRaises(ApiFailure) as err:
            marc.post(base + "/sign/end", {})
        self.assertIn("Recommandation", str(err.exception))
        marc.put(base + "/phase/end", {"recommendation": "rehire"})
        marc.post(base + "/sign/end", {})
        with self.assertRaises(ApiFailure):  # the recommendation belongs to interns only
            self.c["marc"].put("/api/reviews/{}/{}/phase/start".format(self.ids["lea"], y + 1), {"recommendation": "rehire"})

    def test_04_training_plan_joins_the_review_and_ui_is_wired(self):
        self.assertIn("training", [k for k, _ in modules.review_hooks()])
        index = (STATIC / "index.html").read_text("utf-8")
        for script in ("review_parts.js", "objectives_review.js", "objectives.js", "profile.js"):
            self.assertIn("/js/tools/" + script, index)
            text = (STATIC / "js" / "tools" / script).read_text("utf-8")
            self.assertNotIn("innerHTML", text)
            self.assertLess(len(text.splitlines()), 500, script)
        for path in ("core/reviews.py", "core/profile.py"):
            self.assertLess(len((BASE_DIR / path).read_text("utf-8").splitlines()), 500, path)
        self.assertIn('"0.50.5-profile"', (STATIC / "js" / "tools" / "objectives.js").read_text("utf-8"))  # D-A-049


if __name__ == "__main__":
    unittest.main(verbosity=2)
