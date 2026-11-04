"""0.50.10 (D-B-128): Training -- a multiple-choice test of medium difficulty for every topic, mark at the end,
circle-back of the missed questions below the pass mark until each one is answered right, item Completed (green)
when the test is passed, platform coverage (TL-06, RH-01, RH-02).

    python -m unittest tests.test_lot_v049 -v
"""
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
from modules.help import tour  # noqa: E402
from modules.training import catalog, quiz, quizzes  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

STATIC = BASE_DIR / "static"
# Each tab / page of the platform and the topic that teaches it (About and Help are the references themselves).
COVERAGE = {"dashboard": "HL-12", "dynamite": "HL-03", "agile": "HL-06", "goldmine": "HL-04", "testing": "HL-13",
            "exploration": "HL-05", "tools": "HL-08", "training": "HL-14", "codex": "TL-06",
            "timesheet": "HL-09", "admin": "HL-11", "search": "HL-10", "objectives": "RH-01", "team": "RH-02",
            "bdc-definitions": "KB-01", "bdc-gtd": "KB-02", "bdc-functions": "KB-03",
            "ideation": "TL-01", "pugh": "TL-02", "kt": "TL-03"}


def answers(parsed, wrong=()):
    out = {}
    for i, q in enumerate(parsed["questions"]):
        good = [j for j, o in enumerate(q["options"]) if o["right"]]
        bad = [j for j, o in enumerate(q["options"]) if not o["right"]][:1]
        out[str(i)] = bad if i in wrong else good
    return out


class QuizContentTest(unittest.TestCase):
    def test_every_topic_has_a_valid_default_quiz(self):
        topics = catalog._topics()
        codes = {t[0] for t in topics}
        heads = {t[0] for t in topics if t[1] is None}
        for code in codes - heads:
            text = quizzes.default(code)
            self.assertTrue(text, code)
            parsed, problems = quiz.parse(text)
            self.assertEqual(problems, [], code)
            self.assertEqual(parsed["pass"], 80, code)
            self.assertTrue(10 <= len(parsed["questions"]) <= 25, (code, len(parsed["questions"])))
            for q in parsed["questions"]:
                self.assertGreaterEqual(len(q["options"]), 3, (code, q["text"]))
                self.assertTrue(any(not o["right"] for o in q["options"]), (code, q["text"]))  # never all right
            texts = [q["text"] for q in parsed["questions"]]
            self.assertEqual(len(texts), len(set(texts)), code)
        self.assertEqual(set(quizzes.QUIZZES) - codes, set())  # no quiz without its topic

    def test_platform_coverage(self):
        codes = {t[0] for t in catalog._topics()}
        for what, code in COVERAGE.items():
            self.assertIn(code, codes, what)
        for chapter, code in tour.TOPIC_CODES.items():   # every step of the Help tour has its topic and its test
            self.assertIn(code, codes, chapter)
            self.assertTrue(quizzes.default(code), chapter)
        self.assertEqual(len(tour.TOPIC_CODES), len(tour.STEPS))
        tabs = {e["key"] for e in modules.MODULE_MANIFEST if e.get("placement") != "none"} - {"about", "help"}
        self.assertEqual(tabs - set(COVERAGE), set())

    def test_screen_rules(self):
        js = (STATIC / "js/training/quiz.js").read_text(encoding="utf-8")
        tr = (STATIC / "js/training/training.js").read_text(encoding="utf-8")
        for src in (js, tr):
            self.assertNotIn("innerHTML", src)
        self.assertIn('"data-new": "0.50.10-training-circle"', js)
        self.assertIn('"data-new": "0.50.10-training-retry"', js)
        self.assertIn("#/training/test/", tr)
        self.assertIn('completed: "ok"', tr)              # Completed in green
        self.assertNotIn("modal(", js)                     # a page, not a window that scrolls (D-B-118)
        css = (STATIC / "css/training.css").read_text(encoding="utf-8")
        self.assertNotIn("max-height: 70vh", css)
        self.assertNotIn("#c9372c", css)                   # tokens only


class CircleBackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.data_dir, cls.cfg = data_dir, cfg
        cls.server = router.create_server(cfg, STATIC, data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        done = cls.admin.post("/api/admin/access-rules", {"text": "utilisateur lea | Léa | utilisateur | actif\n"
                                                                  "utilisateur max | Max | utilisateur | actif\n"})
        clients = {}
        for c in done["created"]:
            clients[c["username"]] = Client(url)
            clients[c["username"]].login(c["username"], c["temp_password"], "Essai-Reprise-Formation-2026!")
        cls.lea, cls.max = clients["lea"], clients["max"]
        cls.lea_id = cls.lea.get("/api/me")["user"]["id"]
        cls.lea.put("/api/me/prefs", {"manager_id": cls.max.get("/api/me")["user"]["id"]})

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

    def add(self, code):
        topic = next(t for t in self.lea.get("/api/training/topics")["topics"] if t["code"] == code)
        self.assertTrue(topic["has_quiz"], code)
        return self.lea.post("/api/training/plan/{}/items".format(self.lea_id), {"topic_id": topic["id"]})["id"]

    def parsed(self, code):
        with db.connect() as conn:
            return quiz.checked(conn.execute("SELECT quiz_md FROM training_topics WHERE code = ?", (code,)).fetchone()[0])

    def item(self, iid):
        return next(i for i in self.lea.get("/api/training/plan/{}".format(self.lea_id))["items"] if i["id"] == iid)

    def test_01_every_seeded_topic_has_its_test(self):
        topics = {t["code"]: t for t in self.lea.get("/api/training/topics")["topics"]}
        for code in ("HL-01", "HL-14", "KB-03", "TL-06", "RH-01", "RH-02"):
            self.assertTrue(topics[code]["has_quiz"], code)
        self.assertFalse({"TL-04", "TL-05", "KB-04"} & set(topics))  # 0.50.14: retired with their tools (D-B-132); KB-04 in 0.60.01
        self.assertFalse(topics["RH"]["has_quiz"])  # group headings have no test

    def test_02_circle_back_until_every_missed_question_is_right(self):
        iid = self.add("HL-04")
        p = self.parsed("HL-04")
        total = len(p["questions"])
        first = self.lea.post("/api/training/items/{}/quiz".format(iid), {"answers": answers(p, wrong={1, 4, 7, 10})})
        self.assertEqual(first["mode"], "full")
        self.assertFalse(first["passed"])
        self.assertEqual(first["score"], round(100 * (total - 4) / total))
        self.assertEqual(first["remaining"], [1, 4, 7, 10])
        missed = [rv for rv in first["review"] if not rv["ok"]]
        self.assertTrue(all("right" not in rv and "explain" not in rv for rv in missed))  # answers kept secret
        self.assertTrue(all("right" in rv for rv in first["review"] if rv["ok"]))
        it = self.item(iid)
        self.assertEqual((it["status"], it["quiz_remaining"], it["quiz_first"]), ("in_progress", 4, first["score"]))
        # the round asks the missed questions only, keyed by their original index
        rnd = self.lea.get("/api/training/items/{}/quiz".format(iid))
        self.assertEqual([q["index"] for q in rnd["questions"]], [1, 4, 7, 10])
        self.assertEqual(rnd["circle_back"]["round"], 1)
        self.assertNotIn("right", json.dumps(rnd))
        two = self.lea.post("/api/training/items/{}/quiz".format(iid), {"answers": answers(p, wrong={4, 10})})
        self.assertEqual((two["mode"], two["round"], two["passed"], two["remaining"]), ("retry", 1, False, [4, 10]))
        self.assertEqual(two["first"], first["score"])
        self.assertEqual(self.item(iid)["quiz_remaining"], 2)
        done = self.lea.post("/api/training/items/{}/quiz".format(iid), {"answers": answers(p)})
        self.assertTrue(done["passed"])
        self.assertEqual((done["status"], done["round"], done["remaining"]), ("completed", 2, []))
        self.assertTrue(all("right" in rv for rv in done["review"]))   # everything revealed at the end
        it = self.item(iid)
        self.assertEqual((it["status"], it["quiz_passed"], it["quiz_remaining"], it["quiz_score"]),
                         ("completed", 1, 0, first["score"]))
        self.assertEqual(it["quiz_attempts"], 1)  # one full test; the rounds are not attempts
        with db.connect() as conn:
            rounds = [r[0] for r in conn.execute("SELECT round FROM training_attempts WHERE item_id = ? ORDER BY id", (iid,))]
        self.assertEqual(rounds, [0, 1, 2])

    def test_03_pass_directly_and_complete_from_todo(self):
        iid = self.add("KB-02")
        p = self.parsed("KB-02")
        r = self.lea.post("/api/training/items/{}/quiz".format(iid), {"answers": answers(p, wrong={0, 1})})
        self.assertTrue(r["passed"])                   # 12 / 14 = 86 %: passed above the mark
        self.assertEqual(r["status"], "completed")     # straight from To Do
        self.assertEqual([rv["index"] for rv in r["review"] if not rv["ok"]], [0, 1])
        self.assertTrue(all("right" in rv for rv in r["review"]))
        self.assertEqual(self.item(iid)["quiz_remaining"], 0)

    def test_04_manual_completion_needs_the_test(self):
        iid = self.add("TL-02")
        self.lea.patch("/api/training/items/{}".format(iid), {"status": "in_progress"})
        self.assertEqual(self.status(lambda: self.lea.patch("/api/training/items/{}".format(iid), {"status": "completed"})), 409)
        self.assertEqual(self.status(lambda: self.max.post("/api/training/items/{}/quiz".format(iid), {"answers": {}})), 403)

    def test_05_edited_quiz_resets_the_round(self):
        iid = self.add("TL-03")
        p = self.parsed("TL-03")
        self.lea.post("/api/training/items/{}/quiz".format(iid), {"answers": answers(p, wrong={0, 1, 2, 3, 4})})
        self.assertEqual(len(self.lea.get("/api/training/items/{}/quiz".format(iid))["questions"]), 5)
        topic = next(t for t in self.admin.get("/api/training/topics")["topics"] if t["code"] == "TL-03")
        self.admin.patch("/api/training/topics/{}".format(topic["id"]), {"quiz_md": quizzes.default("TL-03") + "\n"})
        fresh = self.lea.get("/api/training/items/{}/quiz".format(iid))
        self.assertIsNone(fresh["circle_back"])
        self.assertEqual(len(fresh["questions"]), len(p["questions"]))

    def test_06_existing_site_gets_the_default_tests_once(self):
        with db.connect() as conn:
            conn.execute("UPDATE training_topics SET quiz_md = ? WHERE code = 'HL-09'", (catalog.EXAMPLE_QUIZ,))
            conn.execute("UPDATE training_topics SET quiz_md = '' WHERE code = 'KB-01'")
            conn.execute("UPDATE training_topics SET quiz_md = ? WHERE code = 'HL-01'", (catalog.EXAMPLE_QUIZ + "\n## Q\n- [x] a\n- [ ] b\n",))
            conn.execute("DELETE FROM training_topics WHERE code IN ('KB-03', 'RH', 'RH-01', 'RH-02', 'TL-06')")
            conn.execute("DELETE FROM app_settings WHERE key = ?", (catalog.QUIZ_SETTING,))
        startup.run(self.data_dir, self.cfg)
        with db.connect() as conn:
            q = {r["code"]: r["quiz_md"] for r in conn.execute("SELECT code, quiz_md FROM training_topics")}
            rh = conn.execute("SELECT parent_id FROM training_topics WHERE code = 'RH-01'").fetchone()[0]
            head = conn.execute("SELECT id FROM training_topics WHERE code = 'RH'").fetchone()[0]
        self.assertEqual(q["HL-09"], quizzes.default("HL-09"))   # 0.37 example replaced
        self.assertEqual(q["KB-01"], quizzes.default("KB-01"))   # empty filled
        self.assertIn("## Q", q["HL-01"])                        # edited by an administrator: left alone
        self.assertEqual(q["RH-02"], quizzes.default("RH-02"))
        self.assertEqual(rh, head)
        with db.connect() as conn:                               # once: a test emptied later stays empty
            conn.execute("UPDATE training_topics SET quiz_md = '' WHERE code = 'KB-01'")
        startup.run(self.data_dir, self.cfg)
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT quiz_md FROM training_topics WHERE code = 'KB-01'").fetchone()[0], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
