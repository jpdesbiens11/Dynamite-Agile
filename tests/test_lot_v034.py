"""0.44.0: « Thème par défaut » design (D-B-087, core lot v0.22) -- default theme with a one-time move from Atlassian,
hand-drawn assets generated identically, every icon / mark used by the interface exists, tabs by order of use,
self-contained showcase page.

    python -m unittest tests.test_lot_v034 -v
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, prefs  # noqa: E402

STATIC = BASE_DIR / "static"


class LotV034Test(unittest.TestCase):
    def test_01_default_theme_and_migration(self):
        self.assertEqual(prefs.DEFAULTS["theme"], "carnet")
        self.assertIn("atlassian", prefs.CHOICES["theme"])  # still selectable
        with tempfile.TemporaryDirectory() as tmp:
            migrations = [m for m in modules.registered_migrations() if not (m[0] == "core" and m[1] == 11)]
            db.init_db(Path(tmp) / "t.db", modules.registered_schema(), migrations)
            with db.connect() as conn:
                auth.ensure_initial_admin(conn, Path(tmp), dev_password="admin")
                uid = conn.execute("SELECT id FROM users").fetchone()[0]
                conn.execute("INSERT INTO user_prefs (user_id, prefs, updated_at) VALUES (?, ?, '2026-01-01')",
                             (uid, json.dumps({"theme": "atlassian", "font_size": "112"})))
            db.init_db(Path(tmp) / "t.db", modules.registered_schema(), modules.registered_migrations())  # 0.43 -> 0.44
            with db.connect() as conn:
                got = prefs.get(conn, uid)
        self.assertEqual((got["theme"], got["font_size"]), ("carnet", "112"))

    def test_02_assets_complete_and_reproducible(self):
        sprite = (STATIC / "img" / "icons.svg").read_text(encoding="utf-8")
        ids = set(re.findall(r'id="i-([a-z]+)"', sprite))
        used = set(re.findall(r'\["([a-z]+)", "', (STATIC / "js" / "tools" / "sketch.js").read_text(encoding="utf-8")))
        used |= set(re.findall(r'DA\.icon\("([a-z]+)"\)', (STATIC / "js" / "app.js").read_text(encoding="utf-8")))
        used |= {"auditlist", "audit", "mine", "admin"}
        self.assertTrue(used <= ids, used - ids)
        for path in list((STATIC / "js").rglob("*.js")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("-mark.png", text, path)  # mining-era PNG marks are gone
            for mark in re.findall(r'DA\.mark\("([a-z]+)"\)', text):  # 0.45.0: one mark per theme (D-B-088)
                for folder in ("marks", "marks-term"):
                    self.assertTrue((STATIC / "img" / folder / (mark + ".svg")).exists(), (folder, mark))
        before = {p: p.read_bytes() for p in (STATIC / "img").rglob("*.svg")}
        from tools import make_sketch_assets
        make_sketch_assets.main()  # seeded: regenerating changes nothing
        after = {p: p.read_bytes() for p in (STATIC / "img").rglob("*.svg")}
        self.assertEqual(before, after)
        for body in after.values():
            self.assertNotIn(b"<text", body)  # no text in images (FONDATIONS §5)

    def test_03_shell_and_showcase(self):
        index = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-sketch="carnet"', index)
        self.assertLess(index.index("/css/themes.css"), index.index("/css/sketch.css"))
        self.assertLess(index.index("/js/tools/sketch.js"), index.index("/js/app.js"))
        sketch = (STATIC / "js" / "tools" / "sketch.js").read_text(encoding="utf-8")
        order = re.search(r"groups: (\[\[.*?\]\]),", sketch).group(1)
        self.assertEqual(json.loads(order), [["dashboard", "home"], ["goldmine", "exploration", "agile", "dynamite", "testing"],
                                             ["tools", "training", "timesheet"]])
        from tools import build_vitrine
        path, _size = build_vitrine.build()
        page = path.read_text(encoding="utf-8")
        self.assertFalse(re.search(r'(src|href)="https?://', page), "no external resource")
        for marker in ("<!--SPRITE-->", "<!--HERO-->", "<!--TOOLS-->", "<!--VERSION-->"):
            self.assertNotIn(marker, page)
        self.assertEqual(page.count('class="step"'), 8)  # the day of an engineer, eight tools
        self.assertIn('id="energy"', page)
        self.assertIn("prefers-reduced-motion", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
