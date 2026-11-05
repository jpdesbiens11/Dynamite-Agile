"""0.42.0: Agile method guide in the BDC (D-A-050) -- French page with the tool's function names and 8 screenshots
stored once as images of the DEMO Space.

    python -m unittest tests.test_lot_v032 -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.help import agile_guide  # noqa: E402


class LotV032Test(unittest.TestCase):
    def test_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            cfg = load_config(data_dir)
            db.init_db(data_dir / "t.db", modules.registered_schema(), modules.registered_migrations())
            with db.connect() as conn:
                auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
            startup.run(data_dir, cfg)
            startup.run(data_dir, cfg)  # second start: nothing duplicated
            with db.connect() as conn:
                page = conn.execute("SELECT p.*, pr.key FROM dynamite_pages p JOIN projects pr ON pr.id = p.project_id "
                                    "WHERE p.title = ?", (agile_guide.TITLE,)).fetchone()
                self.assertIsNotNone(page)
                self.assertEqual(page["key"], "DEMO")
                body = conn.execute("SELECT body FROM dynamite_versions WHERE page_id = ? AND version = ?",
                                    (page["id"], page["current_version"])).fetchone()["body"]
                self.assertEqual(page["current_version"], 1)
                images = [n for n in json.loads(body)["content"] if n.get("type") == "image"]
                self.assertEqual(len(images), 0)  # the guide has no screenshots
                n = conn.execute("SELECT COUNT(*) FROM attachments WHERE project_id = ? AND module = 'dynamite'",
                                 (page["project_id"],)).fetchone()[0]
                self.assertEqual(n, 0)
            text = json.dumps(json.loads(body), ensure_ascii=False)
            for words in ("Créer un sprint", "Démarrer le sprint", "Clôturer", "Paramètres du Space", "Story Points",
                          "Retours arrière", "Pour et contre", "Limites de l'outil", "Problèmes connus", "FAQ", "@identifiant"):
                self.assertIn(words, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
