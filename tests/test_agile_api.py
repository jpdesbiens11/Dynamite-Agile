"""End-to-end tests of the Agile module through the real HTTP server.

Run from the repository root (terminal or Spyder):
    python -m unittest tests.test_agile_api -v
A temporary data folder is used; nothing touches data/.
"""
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

ADMIN_PW = "Chef-Essai-Pass-2026"
USER_PW = "Poste-Essai-Pass-2026"


class AgileApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(data_dir / "test.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            temp = auth.ensure_initial_admin(conn, data_dir)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])

        cls.admin = Client(cls.url)
        cls.admin.login("admin", temp, ADMIN_PW)
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "PRJ", "name": "PRJ", "description": ""})
        cls.admin.post("/api/admin/projects", {"provision": False, "key": "OTH", "name": "Autre", "description": ""})
        projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.pid, cls.other = projects["PRJ"], projects["OTH"]
        cls.users = {}
        for name, role in (("editeur", "editor"), ("lecteur", "reader")):
            created = cls.admin.post("/api/admin/users", {"username": name, "display_name": name.title()})
            uid = created["user"]["id"]
            cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.pid, uid), {"role": role})
            client = Client(cls.url)
            client.login(name, created["temp_password"], USER_PW)
            cls.users[name] = (client, uid)
        cls.editor, cls.editor_id = cls.users["editeur"]
        cls.reader, _ = cls.users["lecteur"]
        cls.base = "/api/agile/p/{}".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def assertFails(self, status, func, *args):
        with self.assertRaises(ApiFailure) as ctx:
            func(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)

    def meta(self):
        return self.admin.get(self.base + "/meta")

    # Tests run in alphabetical order: names are numbered on purpose.
    def test_01_activation(self):
        self.assertFalse(self.meta()["enabled"])
        self.assertFails(403, self.editor.post, self.base + "/init")
        self.assertFails(409, self.editor.get, self.base + "/issues")
        self.admin.post(self.base + "/init")
        meta = self.meta()
        self.assertEqual(len(meta["types"]), 5)
        self.assertEqual([s["name"] for s in meta["statuses"]], ["To Do", "In Progress", "In Review", "Done"])
        self.assertFails(409, self.admin.post, self.base + "/init")
        self.assertFails(404, self.editor.get, "/api/agile/p/{}/meta".format(self.other))

    def test_02_create_and_keys(self):
        task = next(t for t in self.meta()["types"] if t["icon_key"] == "task")
        body = {"type_id": task["id"], "title": "Capteur T3", "priority": "high",
                "labels": ["buse", "Therm"], "assignee_id": self.editor_id}
        first = self.editor.post(self.base + "/issues", body)
        self.assertEqual(first["key"], "PRJ-1")
        with ThreadPoolExecutor(max_workers=6) as pool:
            keys = list(pool.map(lambda i: self.editor.post(
                self.base + "/issues", dict(body, title="Parallèle {}".format(i)))["key"], range(6)))
        self.assertEqual(len(set(keys)), 6)
        self.assertFails(403, self.reader.post, self.base + "/issues", body)
        self.assertFails(400, self.editor.post, self.base + "/issues", dict(body, priority="urgent"))
        self.assertFails(400, self.editor.post, self.base + "/issues", dict(body, labels=["avec espace"]))
        issue = self.reader.get(self.base + "/issues/1")["issue"]
        self.assertEqual(issue["labels"], ["buse", "Therm"])
        self.assertEqual(issue["status_name"], "To Do")

    def test_03_update_and_history(self):
        self.editor.patch(self.base + "/issues/1", {"title": "Capteur T3 surchauffe", "story_points": 3})
        history = self.editor.get(self.base + "/issues/1")["issue"]["history"]
        self.assertIn("title", [h["field"] for h in history])
        self.assertFails(403, self.reader.patch, self.base + "/issues/1", {"title": "x"})

    def test_04_transitions(self):
        issue = self.editor.get(self.base + "/issues/1")["issue"]
        names = {t["name"]: t["id"] for t in issue["transitions"]}
        self.assertNotIn("Done", names)  # not reachable from "To Do"
        done = next(t for t in self.meta()["transitions"] if t["name"] == "Done")
        self.assertFails(409, self.editor.post, self.base + "/issues/1/transition", {"transition_id": done["id"]})
        self.editor.post(self.base + "/issues/1/transition", {"transition_id": names["Start"]})
        issue = self.editor.get(self.base + "/issues/1")["issue"]
        finish = next(t for t in issue["transitions"] if t["name"] == "Done")
        self.editor.post(self.base + "/issues/1/transition", {"transition_id": finish["id"]})
        issue = self.editor.get(self.base + "/issues/1")["issue"]
        self.assertEqual(issue["status_category"], "done")
        self.assertIsNotNone(issue["resolved_at"])

    def test_05_labels_and_search(self):
        self.editor.put(self.base + "/issues/2/labels", {"labels": ["BUSE"]})
        found = self.reader.get(self.base + "/issues?label=buse")["issues"]
        self.assertEqual({i["number"] for i in found} >= {1, 2}, True)
        meta_labels = [l["name"] for l in self.meta()["labels"]]
        self.assertEqual(sorted(meta_labels, key=str.lower), ["buse", "Therm"])
        found = self.reader.get(self.base + "/issues?q=surchauffe")["issues"]
        self.assertEqual([i["number"] for i in found], [1])

    def test_06_comments_and_links(self):
        cid = self.editor.post(self.base + "/issues/2/comments", {"body": "Vu en essai."})["id"]
        self.assertFails(403, self.reader.post, self.base + "/issues/2/comments", {"body": "x"})
        self.editor.post(self.base + "/issues/2/links", {"link_type": "blocks", "target_number": 3})
        self.assertFails(409, self.editor.post, self.base + "/issues/2/links",
                         {"link_type": "blocks", "target_number": 3})
        self.assertFails(400, self.editor.post, self.base + "/issues/2/links",
                         {"link_type": "blocks", "target_number": 2})
        linked = self.editor.get(self.base + "/issues/3")["issue"]["links"]
        self.assertEqual(linked[0]["direction"], "in")
        self.admin.delete(self.base + "/issues/2/comments/{}".format(cid))

    def test_07_sprints_and_board(self):
        sid = self.editor.post(self.base + "/sprints", {})["id"]
        for number in (1, 2, 3):
            self.editor.patch(self.base + "/issues/{}".format(number), {"sprint_id": sid})
        self.editor.post(self.base + "/sprints/{}/start".format(sid), {})
        second = self.editor.post(self.base + "/sprints", {})["id"]
        self.assertFails(409, self.editor.post, self.base + "/sprints/{}/start".format(second), {})
        board = self.reader.get(self.base + "/board")
        self.assertEqual(board["sprint"]["id"], sid)
        self.assertEqual(len(board["issues"]), 3)
        closed = self.editor.post(self.base + "/sprints/{}/close".format(sid))
        self.assertEqual(closed["returned_to_backlog"], 2)  # PRJ-1 is done

    def test_08_workflow_config(self):
        meta = self.meta()
        wf = meta["workflows"][0]["id"]
        sid = self.admin.post(self.base + "/statuses", {"workflow_id": wf, "name": "Bloqué",
                                                         "category": "in_progress"})["id"]
        self.admin.post(self.base + "/transitions", {"workflow_id": wf, "from_status_id": None,
                                                      "to_status_id": sid, "name": "Bloquer",
                                                      "min_role": "admin"})
        editor_view = self.editor.get(self.base + "/issues/2")["issue"]["transitions"]
        self.assertNotIn("Bloquer", [t["name"] for t in editor_view])
        admin_view = self.admin.get(self.base + "/issues/2")["issue"]["transitions"]
        block = next(t for t in admin_view if t["name"] == "Bloquer")
        self.admin.post(self.base + "/issues/2/transition", {"transition_id": block["id"]})
        self.assertFails(409, self.admin.delete, self.base + "/statuses/{}".format(sid))
        self.assertFails(403, self.editor.post, self.base + "/statuses",
                         {"workflow_id": wf, "name": "X", "category": "todo"})

    def test_09_delete_and_audit(self):
        self.assertFails(403, self.editor.delete, self.base + "/issues/7")
        self.admin.delete(self.base + "/issues/7")
        self.assertFails(404, self.admin.get, self.base + "/issues/7")
        actions = {e["action"] for e in self.admin.get("/api/admin/audit")["entries"]}
        self.assertTrue({"agile_enable", "agile_issue_create", "agile_issue_transition",
                         "agile_issue_delete"} <= actions)

    def test_10_csrf_and_auth(self):
        anonymous = Client(self.url)
        self.assertFails(401, anonymous.get, self.base + "/issues")
        forged = Client(self.url)
        forged.opener = self.editor.opener  # same cookie, no CSRF token
        self.assertFails(403, forged.post, self.base + "/issues", {"title": "x"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
