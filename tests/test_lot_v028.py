"""0.38.0: @mentions and messages (core lot v0.19, D-A-046).

    python -m unittest tests.test_lot_v028 -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, mentions, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


def doc(text):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


class LotV028Test(unittest.TestCase):
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
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(url)
        cls.admin.login("admin", "admin")
        cls.admin.post("/api/admin/projects", {"key": "MEN", "name": "Mentions", "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": (
            "utilisateur tom | Tom | utilisateur | actif\nutilisateur ana | Ana | utilisateur | actif\n"
            "utilisateur bob | Bob | utilisateur | actif\ndroit tom | MEN | editeur\ndroit ana | MEN | editeur\n")})
        cls.c = {}
        for acc in done["created"]:
            cl = Client(url)
            cl.login(acc["username"], acc["temp_password"], "Essai-Mentions-Plateforme-2026!")
            cls.c[acc["username"]] = cl
        cls.pid = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}["MEN"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def count(self, who):
        return self.c[who].get("/api/mentions/count")["unread"]

    def test_parse(self):
        self.assertEqual(mentions.usernames("Salut @Ana et @jean-philippe, écris à x@example.org ; @ana encore"),
                         ["ana", "jean-philippe"])
        self.assertIn("Bonjour", mentions.text_of_blocks(doc("Bonjour @ana")))

    def test_flow(self):
        tom = self.c["tom"]
        base = "/api/dynamite/p/{}/pages".format(self.pid)
        made = tom.post(base, {"title": "Revue du produit", "body": doc("Point pour @ana, @bob, @personne et @tom")})
        self.assertIn("Message envoyé à Ana", made["mentions_notice"])
        self.assertIn("@bob : n'a pas accès à ce Space", made["mentions_notice"])
        self.assertIn("@personne : compte inconnu", made["mentions_notice"])
        self.assertEqual(self.count("ana"), 1)
        self.assertEqual(self.count("bob"), 0)
        self.assertEqual(self.count("tom"), 1)  # D-B-089: « @me » files a note in one's own Messages
        self.assertIn("Note ajoutée à vos Messages", made["mentions_notice"])
        sent = tom.get("/api/mentions?box=sent")["messages"]
        self.assertEqual([m["recipient"] for m in sent], ["Ana"])  # the note to oneself is not a « sent » message
        page = tom.get(base + "/{}".format(made["id"]))["page"]
        saved = tom.put(base + "/{}".format(made["id"]), {"title": page["title"], "body": doc("Point pour @ana, suite"),
                                                         "base_version": page["version"]})
        self.assertEqual(saved["mentions_notice"], "")  # already mentioned in the previous version
        self.assertEqual(self.count("ana"), 1)
        tom.post(base + "/{}/comments".format(made["id"]), {"body": "@ana peux-tu relire la section 3 ?"})
        self.assertEqual(self.count("ana"), 2)
        req = tom.post("/api/agile/p/{}/goldmine/requirements".format(self.pid),
                       {"statement": "The product shall be insulated.", "test_ref": "TST-ELE-02"})
        r = tom.post("/api/agile/p/{}/issues/{}/comments".format(self.pid, req["number"]), {"body": "@ana valeur à confirmer"})
        self.assertIn("Ana", r["mentions_notice"])
        q = tom.post("/api/agile/p/{}/issues/{}/qa".format(self.pid, req["number"]), {"question": "@ana quelle tension ?"})
        self.assertIn("Ana", q["mentions_notice"])
        box = self.c["ana"].get("/api/mentions")
        self.assertEqual(box["unread"], 4)
        kinds = {m["kind"]: m for m in box["messages"]}
        self.assertEqual(set(kinds), {"page", "page_comment", "ticket_comment", "qa"})
        self.assertEqual(kinds["ticket_comment"]["href"], "#/goldmine/MEN/issue/{}".format(req["number"]))
        self.assertEqual(kinds["page"]["href"], "#/dynamite/MEN/page/{}".format(made["id"]))
        self.assertIn("section 3", kinds["page_comment"]["excerpt"])
        self.c["ana"].post("/api/mentions/read", {"ids": [kinds["page"]["id"]]})
        self.assertEqual(self.count("ana"), 3)
        self.assertEqual(self.c["ana"].post("/api/mentions/read", {"all": True})["unread"], 0)
        people = self.c["ana"].get("/api/mentions/people?q=to")["people"]
        self.assertIn("tom", [p["username"] for p in people])


if __name__ == "__main__":
    unittest.main(verbosity=2)
