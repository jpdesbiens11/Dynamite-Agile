"""0.60.86 (D-O-092): an HTTP header is Latin-1 only; a download whose name held « œ », « — », « € » or an emoji (the
export of a page « Cœur du moteur ») was cut short by a UnicodeEncodeError. Content-Disposition now carries an ASCII
name and, when it differs, the exact name in filename*=UTF-8'' (RFC 6266).

    python -m unittest tests.test_download_names -v
"""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, files, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402


class DownloadNamesTest(unittest.TestCase):
    def test_header_is_ascii_and_keeps_the_exact_name(self):
        value = files.disposition("Cœur du moteur — révision €.pdf")
        value.encode("latin-1")  # what http.server does with every header
        self.assertTrue(value.startswith('attachment; filename="Coeur du moteur - revision _.pdf"'))
        self.assertEqual(unquote(value.split("filename*=UTF-8''")[1]), "Cœur du moteur — révision €.pdf")
        self.assertEqual(files.disposition("rapport.csv", inline=True), 'inline; filename="rapport.csv"')
        self.assertNotIn("\r", files.disposition('a"\r\nSet-Cookie: x.txt'))
        self.assertNotIn('a"', files.disposition('a"b.txt').split("filename=")[1][1:])

    def test_page_with_oe_exports(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data_dir = Path(tmp.name)
        cfg = load_config(data_dir)
        cfg.update(port=0, require_initials=False)
        db.init_db(data_dir / "d.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        c = Client("http://127.0.0.1:{}".format(server.server_address[1]))
        c.login("admin", "admin")
        pid = c.post("/api/admin/projects", {"key": "NOM", "name": "Noms"})["project"]["id"]
        page = c.post("/api/dynamite/p/{}/pages".format(pid), {"title": "Cœur du moteur — révision €", "body": {
            "type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Bonjour"}]}]}})
        page_id = (page.get("page") or page)["id"]
        for fmt in ("docx", "pdf"):
            with self.subTest(fmt=fmt):
                status, headers, data = c.raw_get("/api/dynamite/p/{}/pages/{}/export.{}".format(pid, page_id, fmt))
                self.assertEqual(status, 200)
                self.assertGreater(len(data), 500)
                self.assertIn("C%C5%93ur", headers["Content-Disposition"])


if __name__ == "__main__":
    unittest.main()
