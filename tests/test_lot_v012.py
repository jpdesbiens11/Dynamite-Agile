"""0.22.0: move / copy wiki pages between spaces (D-B-049), Word / PDF export
with a per-account right (D-B-050)
(D-B-051), « hide the sandbox » setting and the [Sandbox] mark (D-B-052, D-B-054).

    python -m unittest tests.test_lot_v012 -v
"""
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

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
       b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef"
       b"\x00\x00\x00\x00IEND\xaeB`\x82")

RULES = """
utilisateur ana | Ana Modèle | utilisateur | actif
utilisateur marc | Marc Gestion | utilisateur | actif
droit ana | ONE | editeur
droit ana | TWO | lecteur
"""


def _p(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


class LotV012Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cls.cfg = load_config(cls.data_dir)
        cls.cfg["port"] = 0
        cls.cfg["require_initials"] = False  # D-B-058, tested in test_lot_v013
        db.init_db(cls.data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, cls.data_dir, dev_password="admin")
        startup.run(cls.data_dir, cls.cfg)
        cls.server = router.create_server(cls.cfg, BASE_DIR / "static", cls.data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        for key in ("ONE", "TWO"):
            cls.admin.post("/api/admin/projects", {"key": key, "name": key, "description": ""})
        done = cls.admin.post("/api/admin/access-rules", {"text": RULES})
        cls.people, cls.ids = {}, {}
        for c in done["created"]:
            client = Client(cls.url)
            me = client.login(c["username"], c["temp_password"], "Essai-Lot-Douze-2026!")
            cls.people[c["username"]] = client
            cls.ids[c["username"]] = me["user"]["id"]
        cls.projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def pages(self, pid):
        return {p["title"]: p for p in self.admin.get("/api/dynamite/p/{}/pages".format(pid))["pages"]}

    def new_page(self, client, pid, title, parent=None, extra=None):
        body = {"type": "doc", "content": [{"type": "heading", "level": 1, "content": [{"type": "text", "text": title}]},
                                           _p("Texte « accentué » de " + title)] + (extra or [])}
        made = client.post("/api/dynamite/p/{}/pages".format(pid), {"title": title, "parent_id": parent, "body": body})
        return (made.get("page") or made)["id"]

    # ---------------- D-B-053: sandbox mark  ----------------
    def test_01_policy_in_gen_and_sandbox_mark(self):
        names = {p["key"]: p["name"] for p in self.admin.get("/api/admin/projects")["projects"]}
        self.assertIn("bac à sable", names["DEMO"])  # 0.60.49 (D-O-058): DEMO, sandbox and training
        self.assertIn("DEMO — Bienvenue", self.pages(self.projects["DEMO"]))
        self.assertNotIn("Principes de la compagnie — vacances et congés", self.pages(self.projects["DEMO"]))
        startup.run(self.data_dir, self.cfg)  # idempotent

    # ---------------- D-B-049: move / copy ----------------
    def test_02_move_with_image_and_children(self):
        one, two = self.projects["ONE"], self.projects["TWO"]
        image = self.admin.upload("/api/dynamite/p/{}/images".format(one), PNG, "image/png", "banc.png")
        top = self.new_page(self.admin, one, "Banc d'essai", extra=[{"type": "image", "id": image["id"], "alt": "banc"}])
        child = self.new_page(self.admin, one, "Banc d'essai — mesures", parent=top)
        res = self.admin.post("/api/dynamite/p/{}/pages/{}/transfer".format(one, top), {"mode": "move", "target_pid": two})
        self.assertEqual((res["moved"], res["target_key"]), (2, "TWO"))
        self.assertNotIn("Banc d'essai", self.pages(one))
        moved = self.pages(two)
        self.assertEqual(moved["Banc d'essai — mesures"]["parent_id"], top)
        body = self.admin.get("/api/dynamite/p/{}/pages/{}".format(two, top))["page"]["body"]
        new_image = next(b for b in body["content"] if b["type"] == "image")["id"]
        self.assertNotEqual(new_image, image["id"])
        st, _h, data = self.admin.raw_get("/api/dynamite/image/{}".format(new_image))
        self.assertEqual((st, data), (200, PNG))
        self.assertEqual(self.admin.get("/api/dynamite/p/{}/pages/{}".format(two, child))["page"]["id"], child)
        with self.assertRaises(ApiFailure):  # gone from the source space
            self.admin.get("/api/dynamite/p/{}/pages/{}".format(one, top))

    def test_03_copy_rights(self):
        one, two = self.projects["ONE"], self.projects["TWO"]
        ana = self.people["ana"]
        src = self.new_page(self.admin, two, "Plan d'essai")
        self.new_page(self.admin, two, "Plan d'essai — annexe", parent=src)
        with self.assertRaises(ApiFailure) as err:  # reader of TWO: cannot move out of it
            ana.post("/api/dynamite/p/{}/pages/{}/transfer".format(two, src), {"mode": "move", "target_pid": one})
        self.assertEqual(err.exception.status, 403)
        res = ana.post("/api/dynamite/p/{}/pages/{}/transfer".format(two, src),
                       {"mode": "copy", "target_pid": one, "with_children": True})
        self.assertEqual(res["copied"], 2)
        copied = self.pages(one)
        self.assertIn("Plan d'essai — annexe", copied)
        self.assertIn("Plan d'essai", self.pages(two))  # the original stays
        mine = self.new_page(ana, one, "Brouillon Ana")
        with self.assertRaises(ApiFailure) as err:  # reader of TWO: cannot write there
            ana.post("/api/dynamite/p/{}/pages/{}/transfer".format(one, mine), {"mode": "copy", "target_pid": two})
        self.assertEqual(err.exception.status, 403)
        same = ana.post("/api/dynamite/p/{}/pages/{}/transfer".format(one, mine), {"mode": "copy", "target_pid": one})
        self.assertIn("Brouillon Ana (copie)", self.pages(one))
        self.assertNotEqual(same["page_id"], mine)
        actions = [e["action"] for e in self.admin.get("/api/admin/audit?limit=50")["entries"]]
        self.assertIn("dynamite_page_copy", actions)

    # ---------------- D-B-050: export ----------------
    def test_04_export_right(self):
        one = self.projects["ONE"]
        ana = self.people["ana"]
        page = self.new_page(self.admin, one, "Fiche d'export", extra=[
            {"type": "table", "header": True, "rows": [[[{"type": "text", "text": "Col"}]], [[{"type": "text", "text": "Val"}]]]},
            {"type": "bullet_list", "items": [[_p("Point un")], [_p("Point deux")]]}])
        self.new_page(self.admin, one, "Fiche d'export — suite", parent=page)
        url = "/api/dynamite/p/{}/pages/{}/export.".format(one, page)
        st, _h, _d = ana.raw_get(url + "pdf")
        self.assertEqual(st, 403)
        self.assertFalse(next(u for u in self.admin.get("/api/admin/rights")["users"] if u["username"] == "ana")["can_export"])
        self.admin.put("/api/admin/users/{}/prefs".format(self.ids["ana"]), {"can_export": True})
        self.assertTrue(next(u for u in self.admin.get("/api/admin/rights")["users"] if u["username"] == "ana")["can_export"])
        st, _h, pdf = ana.raw_get(url + "pdf?children=1")
        self.assertEqual(st, 200)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        st, _h, docx = ana.raw_get(url + "docx?children=1")
        self.assertEqual(st, 200)
        with zipfile.ZipFile(io.BytesIO(docx)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        for text in ("Fiche d'export", "Fiche d'export — suite", "Point deux", "accentué"):
            self.assertIn(text.replace("'", "&apos;") if "&apos;" in xml else text, xml)
        self.admin.put("/api/admin/policy", {"block_print": True})
        try:
            st, _h, _d = ana.raw_get(url + "docx")
            self.assertEqual(st, 403)
            st, _h, _d = self.admin.raw_get(url + "docx")
            self.assertEqual(st, 200)
        finally:
            self.admin.put("/api/admin/policy", {"block_print": False})
        actions = [e["action"] for e in self.admin.get("/api/admin/audit?limit=50")["entries"]]
        self.assertIn("dynamite_page_export", actions)

    # ---------------- D-B-052: hide the sandbox ----------------
    def test_05_hide_sandbox(self):
        marc = self.people["marc"]
        marc.post("/api/help/headlamp/join")
        self.assertIn("DEMO", [p["key"] for p in marc.get("/api/dashboard")["projects"]])
        self.assertTrue(marc.put("/api/me/prefs", {"hide_sandbox": True})["prefs"]["hide_sandbox"])
        self.assertNotIn("DEMO", [p["key"] for p in marc.get("/api/dashboard")["projects"]])
        hl = self.projects["DEMO"]
        self.assertTrue(marc.get("/api/dynamite/p/{}/pages".format(hl))["pages"])  # the wiki stays open


if __name__ == "__main__":
    unittest.main()
