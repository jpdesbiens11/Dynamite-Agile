"""0.48.0: the design skill shared through the repository (D-B-093) -- valid, pointing at files that exist, its own
checks pass on the code, and Admin → Update carries it.

    python -m unittest tests.test_lot_v038 -v
"""
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import update  # noqa: E402

SKILL = BASE_DIR / ".claude" / "skills" / "dynamite-design" / "SKILL.md"
STATIC = BASE_DIR / "static"


class DesignSkillTest(unittest.TestCase):
    def test_01_valid_skill(self):
        text = SKILL.read_text(encoding="utf-8")
        head = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", text)
        self.assertIsNotNone(head, "frontmatter name / description")
        name, description = head.groups()
        self.assertEqual(name, "dynamite-design")
        self.assertLessEqual(len(description), 1024)
        self.assertNotRegex(description, r"[<>]")
        self.assertLess(len(text.splitlines()), 500)

    def test_02_paths_it_names_exist(self):
        text = SKILL.read_text(encoding="utf-8")
        for rel in sorted(set(re.findall(r"`((?:static|tools|tests|docs|core)/[\w./-]+\.(?:css|js|py|md|svg))`", text))):
            self.assertTrue((BASE_DIR / rel).exists(), rel)
        for rel in ("lancer_dev.py", "app_dynamite_agile.py", "CLAUDE.md"):
            self.assertIn(rel, text)
            self.assertTrue((BASE_DIR / rel).exists(), rel)
        css = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
        for token in re.findall(r"`(--[a-z0-9-]+)`", text.split("## 4.")[0]):  # every base token it lists is real
            if token != "--acc":
                self.assertIn(token + ":", css, token)

    def test_03_its_checks_pass_on_the_code(self):
        external = re.compile(r"(src|href)\s*[:=]\s*[\"']https?://|url\([\"']?https?://|@import")
        risky = re.compile(r"\.innerHTML\s*=|setAttribute\(\"style")
        files = [STATIC / "index.html"] + list((STATIC / "js").rglob("*.js")) + list((STATIC / "css").rglob("*.css"))
        for path in files:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                self.assertIsNone(external.search(line), "{}:{}".format(path, n))
                if path.name != "agile.js":  # the documented exception: constant SVG template
                    self.assertIsNone(risky.search(line), "{}:{}".format(path, n))

    def test_04_update_carries_it(self):
        self.assertIn(".claude", update.CODE_DIRS)
        files = update.code_files(BASE_DIR)
        self.assertIn(".claude/skills/dynamite-design/SKILL.md", files)
        self.assertTrue(update.SKIP.search(".claude/settings.local.json"))
        self.assertIn(".claude/settings.local.json", (BASE_DIR / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn("dynamite-design", update.PROMPT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
