"""Agile v0.3: requirement links, comment threading, CSV import/export.

    python -m unittest tests.test_agile_v03 -v
"""
import csv
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

ADMIN_PW = "Chef-Essai-Pass-2026"

# A trimmed copy of the tables as they looked before migration 2 (v0.2.0
# shape), to prove the migration brings a genuinely old database forward,
# not just that CREATE TABLE IF NOT EXISTS happens to already be right.
V1_SCHEMA = """
CREATE TABLE IF NOT EXISTS agile_issue_types (
    id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, name TEXT NOT NULL,
    icon_key TEXT NOT NULL DEFAULT 'task', workflow_id INTEGER NOT NULL,
    is_subtask INTEGER NOT NULL DEFAULT 0, position INTEGER NOT NULL DEFAULT 0,
    UNIQUE (project_id, name)
);
CREATE TABLE IF NOT EXISTS agile_links (
    id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
    link_type TEXT NOT NULL CHECK (link_type IN ('blocks', 'relates', 'duplicates')),
    created_by INTEGER, created_at TEXT NOT NULL, UNIQUE (source_id, target_id, link_type)
);
CREATE TABLE IF NOT EXISTS agile_issues (
    id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, number INTEGER NOT NULL,
    title TEXT NOT NULL, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS agile_comments (
    id INTEGER PRIMARY KEY, issue_id INTEGER NOT NULL, author_id INTEGER,
    body TEXT NOT NULL, created_at TEXT NOT NULL, edited_at TEXT
);
"""


class MigrationTest(unittest.TestCase):
    def test_v1_shape_migrates_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.db"
            conn = sqlite3.connect(str(path))
            conn.executescript(V1_SCHEMA)
            conn.execute("INSERT INTO agile_links (source_id, target_id, link_type, created_at) "
                        "VALUES (1, 2, 'blocks', '2026-01-01T00:00:00')")
            conn.commit()
            conn.close()

            agile_migrations = [(mod, ver, sql) for mod, ver, sql in modules.registered_migrations()
                                if mod == "agile"]
            conn = sqlite3.connect(str(path))
            conn.execute("PRAGMA foreign_keys = OFF")  # old table has no FKs to satisfy
            conn.executescript("CREATE TABLE IF NOT EXISTS schema_migrations "
                               "(module TEXT, version INTEGER, applied_at TEXT, "
                               "PRIMARY KEY (module, version));")
            applied = db.apply_migrations(conn, agile_migrations)
            conn.commit()

            self.assertEqual(applied, len(agile_migrations))  # every pending migration, once
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("agile_requirements", tables)  # migration 3 (Goldmine)
            self.assertEqual(db.apply_migrations(conn, agile_migrations), 0)  # idempotent
            link = conn.execute("SELECT link_type FROM agile_links WHERE source_id = 1").fetchone()
            self.assertEqual(link[0], "blocks")  # data survived the table rebuild
            try:
                conn.execute("INSERT INTO agile_links (source_id, target_id, link_type, created_at) "
                            "VALUES (3, 4, 'implements', '2026-01-01T00:00:00')")
            except sqlite3.IntegrityError:
                self.fail("'implements' should be insertable after migration (CHECK constraint gone)")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(agile_comments)")}
            self.assertTrue({"parent_comment_id", "external_author", "is_question",
                            "requirement_ref"} <= columns)
            self.assertIn("client_summary", {row[1] for row in
                          conn.execute("PRAGMA table_info(agile_issues)")})  # migration 4
            self.assertIn("is_requirement", {row[1] for row in
                          conn.execute("PRAGMA table_info(agile_issue_types)")})
            conn.close()


class ApiTest(unittest.TestCase):
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
        for key, name in (("PRJ", "PRJ"), ("REQ", "Exigences")):
            cls.admin.post("/api/admin/projects", {"provision": False, "key": key, "name": name, "description": ""})
        projects = {p["key"]: p["id"] for p in cls.admin.get("/api/admin/projects")["projects"]}
        cls.prj, cls.req = projects["PRJ"], projects["REQ"]
        cls.admin.post("/api/agile/p/{}/init".format(cls.prj))
        cls.admin.post("/api/agile/p/{}/init".format(cls.req))
        # Turn REQ's "Story" type into a requirement type for the test.
        req_meta = cls.admin.get("/api/agile/p/{}/meta".format(cls.req))
        cls.req_type = next(t for t in req_meta["types"] if t["icon_key"] == "story")
        cls.admin.patch("/api/agile/p/{}/types/{}".format(cls.req, cls.req_type["id"]),
                        {"is_requirement": True})

        created = cls.admin.post("/api/admin/users", {"username": "editeur2", "display_name": "Éditeur Deux"})
        uid = created["user"]["id"]
        cls.admin.put("/api/admin/projects/{}/members/{}".format(cls.prj, uid), {"role": "editor"})
        cls.editor = Client(cls.url)
        cls.editor.login("editeur2", created["temp_password"], "Poste-Essai-Pass-2026")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def assertFails(self, status, func, *args):
        with self.assertRaises(ApiFailure) as ctx:
            func(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)

    def prj_base(self):
        return "/api/agile/p/{}".format(self.prj)

    def req_base(self):
        return "/api/agile/p/{}".format(self.req)

    def test_01_requirement_link_strict(self):
        req_meta = self.admin.get(self.req_base() + "/meta")
        plain_type = next(t for t in req_meta["types"] if t["id"] != self.req_type["id"])
        requirement = self.admin.post(self.req_base() + "/issues",
                                      {"type_id": self.req_type["id"], "title": "Seuil thermique 60C"})
        other = self.admin.post(self.req_base() + "/issues", {"type_id": plain_type["id"], "title": "Non-exigence"})
        ess_meta = self.admin.get(self.prj_base() + "/meta")
        task_type = next(t for t in ess_meta["types"] if t["icon_key"] == "task")
        ticket = self.admin.post(self.prj_base() + "/issues", {"type_id": task_type["id"],
                                                                "title": "Implémente le seuil"})
        # Strict: linking to a non-requirement type is refused.
        self.assertFails(400, self.admin.post, self.prj_base() + "/issues/{}/links".format(ticket["number"]),
                         {"link_type": "implements", "target_key": other["key"]})
        # Correct target: succeeds, cross-project.
        self.admin.post(self.prj_base() + "/issues/{}/links".format(ticket["number"]),
                        {"link_type": "implements", "target_key": requirement["key"]})
        req_detail = self.admin.get(self.req_base() + "/issues/{}".format(requirement["number"]))["issue"]
        self.assertTrue(req_detail["is_requirement"])
        self.assertEqual(req_detail["implemented_by"][0]["key"], ticket["key"])
        ticket_detail = self.admin.get(self.prj_base() + "/issues/{}".format(ticket["number"]))["issue"]
        self.assertEqual(ticket_detail["links"][0]["key"], requirement["key"])
        self.assertEqual(ticket_detail["links"][0]["direction"], "out")

    def test_02_comment_threading_and_editor_access(self):
        ticket = self.admin.post(self.prj_base() + "/issues", {
            "type_id": self.admin.get(self.prj_base() + "/meta")["types"][0]["id"], "title": "Fil de questions"})
        q = self.editor.post(self.prj_base() + "/issues/{}/comments".format(ticket["number"]),
                             {"body": "Seuil confirmé ?", "is_question": True, "requirement_ref": "SYS-045"})
        self.editor.post(self.prj_base() + "/issues/{}/comments".format(ticket["number"]),
                         {"body": "Oui.", "parent_comment_id": q["id"]})
        self.assertFails(400, self.editor.post, self.prj_base() + "/issues/{}/comments".format(ticket["number"]),
                         {"body": "orphelin", "parent_comment_id": 999999})
        detail = self.admin.get(self.prj_base() + "/issues/{}".format(ticket["number"]))["issue"]
        self.assertEqual(len(detail["comments"]), 2)
        self.assertTrue(detail["comments"][0]["is_question"])
        self.assertEqual(detail["comments"][1]["parent_comment_id"], q["id"])

    def test_03_export_import_tickets_round_trip(self):
        types = self.admin.get(self.prj_base() + "/meta")["types"]
        task = next(t for t in types if t["icon_key"] == "task")
        created = self.admin.post(self.prj_base() + "/issues", {"type_id": task["id"], "title": "À exporter",
                                                                 "priority": "high"})
        with self.admin.opener.open(self.url + self.prj_base() + "/export/tickets") as resp:
            csv_text = resp.read().decode("utf-8-sig")
            disposition = resp.headers.get("Content-Disposition")
        self.assertIn("attachment", disposition)
        self.assertIn(created["key"], csv_text)

        rows = list(csv.DictReader(csv_text.splitlines()))
        for row in rows:
            if row["key"] == created["key"]:
                row["title"] = "Titre corrigé"
        rows.append({"key": "", "parent_key": "", "type": "Task", "title": "Nouvelle ligne CSV",
                    "description": "", "priority": "low", "status": "To Do", "assignee": "",
                    "labels": "", "sprint": "", "version": "", "points": "", "due_date": "",
                    "updated_at": "", "implements": ""})
        out = []
        buf_fields = list(rows[0].keys())
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=buf_fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
        result = self.admin.post(self.prj_base() + "/import/tickets", {"csv": buf.getvalue()})
        statuses = {r["row"]: r["status"] for r in result["report"]}
        self.assertEqual(statuses[created["key"]], "mise à jour")
        self.assertTrue(any(s == "créée" for s in statuses.values()))
        updated = self.admin.get(self.prj_base() + "/issues/{}".format(created["number"]))["issue"]
        self.assertEqual(updated["title"], "Titre corrigé")

    def test_04_import_rejects_stale_row(self):
        types = self.admin.get(self.prj_base() + "/meta")["types"]
        task = next(t for t in types if t["icon_key"] == "task")
        created = self.admin.post(self.prj_base() + "/issues", {"type_id": task["id"], "title": "Verrou optimiste"})
        header = ("key,parent_key,type,title,description,priority,status,assignee,"
                  "labels,sprint,version,points,due_date,updated_at\r\n")
        stale_row = "{},,Tâche,Ancien titre,,medium,À faire,,,,,,,{}".format(
            created["key"], "2000-01-01T00:00:00")
        result = self.admin.post(self.prj_base() + "/import/tickets", {"csv": header + stale_row})
        self.assertEqual(result["report"][0]["status"], "refusée")
        self.assertIn("modifié sur le serveur", result["report"][0]["reason"])
        self.assertIn("Réexportez", result["report"][0]["fix"])

    def test_05_questions_export_import(self):
        ticket = self.admin.post(self.prj_base() + "/issues", {
            "type_id": self.admin.get(self.prj_base() + "/meta")["types"][0]["id"], "title": "Pour le client"})
        self.editor.post(self.prj_base() + "/issues/{}/comments".format(ticket["number"]),
                         {"body": "Confirmez-vous 60C ?", "is_question": True, "requirement_ref": "SYS-045"})
        with self.admin.opener.open(self.url + self.prj_base() + "/export/questions") as resp:
            csv_text = resp.read().decode("utf-8-sig")
        self.assertIn("SYS-045", csv_text)
        self.assertIn("oui", csv_text)

        header = "issue_key,comment_id,parent_comment_id,requirement_ref,author,is_question,body,created_at"
        reply = '{},,,SYS-045,Client XYZ,non,"Oui, confirmé.",'.format(ticket["key"])
        result = self.admin.post(self.prj_base() + "/import/questions", {"csv": header + "\r\n" + reply})
        self.assertEqual(result["report"][0]["status"], "ajoutée")
        detail = self.admin.get(self.prj_base() + "/issues/{}".format(ticket["number"]))["issue"]
        reply_comment = detail["comments"][-1]
        self.assertEqual(reply_comment["author_name"], "Client XYZ")
        self.assertFalse(reply_comment["author_id"])
        # Re-importing the same export (comment_id filled) must be a no-op.
        with self.admin.opener.open(self.url + self.prj_base() + "/export/questions") as resp:
            full_csv = resp.read().decode("utf-8-sig")
        result2 = self.admin.post(self.prj_base() + "/import/questions", {"csv": full_csv})
        self.assertTrue(all(r["status"] == "ignorée" for r in result2["report"]))

    def test_06b_import_implements_column_is_applied(self):
        req_meta = self.admin.get(self.req_base() + "/meta")
        requirement = self.admin.post(self.req_base() + "/issues",
                                      {"type_id": self.req_type["id"], "title": "Exigence pour import CSV"})
        types = self.admin.get(self.prj_base() + "/meta")["types"]
        task = next(t for t in types if t["icon_key"] == "task")
        created = self.admin.post(self.prj_base() + "/issues", {"type_id": task["id"], "title": "Sans lien encore"})
        ticket = self.admin.get(self.prj_base() + "/issues/{}".format(created["number"]))["issue"]
        header = ("key,parent_key,type,title,description,priority,status,assignee,"
                  "labels,sprint,version,points,due_date,updated_at,implements\r\n")
        row = "{},,Tâche,{},,medium,À faire,,,,,,,{},{}".format(
            ticket["key"], ticket["title"], ticket["updated_at"], requirement["key"])
        result = self.admin.post(self.prj_base() + "/import/tickets", {"csv": header + row})
        self.assertEqual(result["report"][0]["status"], "mise à jour")
        self.assertEqual(result["report"][0]["reason"], "")
        detail = self.admin.get(self.prj_base() + "/issues/{}".format(ticket["number"]))["issue"]
        self.assertEqual(detail["links"][0]["key"], requirement["key"])
        # Re-importing the same row is idempotent -- no duplicate link, no error.
        result2 = self.admin.post(self.prj_base() + "/import/tickets", {"csv": header + row.replace(
            ticket["updated_at"], detail["updated_at"])})
        self.assertEqual(result2["report"][0]["status"], "inchangée")  # D-B-008: nothing to write
        detail2 = self.admin.get(self.prj_base() + "/issues/{}".format(ticket["number"]))["issue"]
        self.assertEqual(len(detail2["links"]), 1)

    def test_06_dependency_warning_endpoint(self):
        types = self.admin.get(self.prj_base() + "/meta")["types"]
        task = types[0]["id"]
        a = self.admin.post(self.prj_base() + "/issues", {"type_id": task, "title": "Bloqueur"})
        b = self.admin.post(self.prj_base() + "/issues", {"type_id": task, "title": "Bloqué"})
        self.admin.post(self.prj_base() + "/issues/{}/links".format(a["number"]),
                        {"link_type": "blocks", "target_number": b["number"]})
        deps = self.admin.get(self.prj_base() + "/dependencies")["blocks"]
        self.assertTrue(any(d["blocker"] == a["number"] and d["blocked"] == b["number"] for d in deps))


if __name__ == "__main__":
    unittest.main(verbosity=2)
