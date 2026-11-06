"""0.60.52 (D-O-061): Storyline → IA. The prompt carries the scenes, the method and the exact « diamond » format; the AI's
answer is checked by the Project Starter rules and imported into a Space whose tree is empty; the Storyline travels in the
Project Starter file (diamond.story); the Rover of DEMO has its Storyline; Storytelling left Tools for Diamond."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, starter_diamond, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from core.errors import ApiError  # noqa: E402
from modules.toolbox import ideation, methods_divergent  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

PW = "Storyline-IA-2026!"
ROVER = json.loads((BASE_DIR / "deploy" / "spaces_exemples" / "rover.json").read_text("utf-8"))


def answer():
    """The Rover's Diamond, the way an assistant would return it: in a ```json block, without owners nor tests."""
    d = {k: [{kk: vv for kk, vv in r.items() if kk not in ("owner", "test")} for r in v] for k, v in ROVER["diamond"].items() if k != "story"}
    return "Voici l'analyse :\n```json\n" + json.dumps({"diamond": d}, ensure_ascii=False) + "\n```\nBonne relecture !"


class StoryAiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "a.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.demo = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["DEMO"]
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "ROB", "name": "Robot"})["project"]["id"]
        created = cls.admin.post("/api/admin/users", {"username": "lecteur", "display_name": "Lecteur"})
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, created["user"]["id"]), {"role": "reader"})
        cls.reader = Client(cls.url)
        cls.reader.login("lecteur", created["temp_password"], PW)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_demo_rover_has_its_storyline_and_the_prompt_tells_it(self):
        scenes = self.admin.get("/api/diamond/p/{}/story".format(self.demo))["scenes"]
        self.assertEqual([s["title"] for s in scenes], [s["title"] for s in ROVER["diamond"]["story"]])
        self.assertEqual(len(scenes), 7)
        data = self.reader.get("/api/diamond/p/{}/story/prompt".format(self.pid))  # a reader may copy the prompt
        self.assertEqual(data["scenes"], 0)
        prompt = self.admin.get("/api/diamond/p/{}/story/prompt".format(self.demo))["prompt"]
        self.assertIn("### Scène 1 — La découverte", prompt)
        self.assertIn("Adulte « Sam »", prompt)
        self.assertIn("Idées, irritants, questions : Par où commencer ?", prompt)
        self.assertIn("| `diamond.functions.type` |", prompt)
        self.assertNotIn("| `requirements.", prompt)  # only the Diamond part of the format
        example = prompt.split("```json\n")[1].split("\n```")[0]
        starter_diamond.parse(json.loads(example))  # the example of the prompt is a valid answer

    def test_02_import_checks_then_applies(self):
        base = "/api/diamond/p/{}/import".format(self.pid)
        with self.assertRaises(ApiFailure) as err:
            self.reader.post(base, {"file": answer(), "dry": True})
        self.assertEqual(err.exception.status, 403)
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(base, {"file": "Désolé, je ne peux pas."})
        self.assertEqual(err.exception.status, 400)
        self.assertIn("Correctif", str(err.exception))
        bad = json.loads(answer().split("```json\n")[1].split("\n```")[0])
        bad["diamond"]["functions"][1]["parent"] = "F999"
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(base, {"file": bad})
        self.assertIn("Project Starter", str(err.exception))
        dry = self.admin.post(base, {"file": answer(), "dry": True})["counts"]
        self.assertEqual((dry["functions"], dry["flows"], dry["story"]), (39, 62, 0))
        self.assertEqual(self.admin.get("/api/diamond/p/{}/functions".format(self.pid))["functions"], [])  # nothing created by a dry run
        made = self.admin.post(base, {"file": answer()})
        self.assertTrue(made["imported"])
        functions = self.admin.get("/api/diamond/p/{}/functions".format(self.pid))["functions"]
        self.assertEqual(len(functions), 39)
        self.assertTrue(all("Brouillon IA" in f["notes"] for f in functions))
        with self.assertRaises(ApiFailure) as err:  # a second tree on top of the first: refused
            self.admin.post(base, {"file": answer(), "dry": True})
        self.assertEqual(err.exception.status, 409)
        with db.connect() as conn:
            self.assertTrue(conn.execute("SELECT 1 FROM audit_log WHERE action = 'diamond_import' AND object_id = ?", (str(self.pid),)).fetchone())

    def test_03_storyline_in_the_project_starter_file(self):
        clean = starter_diamond.parse({"diamond": {"story": ROVER["diamond"]["story"]}})
        self.assertEqual(len(clean["story"]), 7)
        self.assertEqual(starter_diamond.counts({"diamond": clean})["story"], 7)
        with self.assertRaises(ApiError) as err:
            starter_diamond.parse({"diamond": {"story": [{"title": "x", "items": [{"p": "licorne"}]}]}})
        self.assertIn("diamond.story[0].items", err.exception.message)
        exported = self.admin.get("/api/starter/export?space=DEMO")
        exported = exported.get("file", exported)
        self.assertEqual([s["title"] for s in exported["diamond"]["story"]], [s["title"] for s in ROVER["diamond"]["story"]])

    def test_04_storytelling_left_tools(self):
        self.assertNotIn("storytelling", ideation.CREATABLE)
        self.assertIn("storytelling", ideation.METHODS)  # older sessions stay readable
        self.assertNotIn("storytelling", [m["key"] for m in methods_divergent.DIVERGENT])
        self.assertIn("Storytelling", methods_divergent.RETIRED)
        js = (BASE_DIR / "static" / "js" / "toolbox" / "ideation.js").read_text("utf-8")
        self.assertIn("Diamond → Storyline", js)


if __name__ == "__main__":
    unittest.main()
