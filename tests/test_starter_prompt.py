"""0.60.18 (D-O-019): the prompt of the Project Starter -- the questions, the rules of the interview and the exact
format, with the values read from the tool itself; its short example is a valid file."""
import json
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import starter, starter_prompt  # noqa: E402


class StarterPromptTest(unittest.TestCase):
    def test_01_render(self):
        for lang in ("fr", "en"):
            text = starter_prompt.render(lang)
            self.assertEqual(re.findall(r"\{\{[A-Z_]+\}\}", text), [], lang)
            for question in range(1, 27):  # 26 questions, numbered, one per message
                self.assertRegex(text, r"\n{}\. \*\*".format(question) if question < 10 else r"\n{}\. ".format(question))
            for value in ("personnel_safety", "Product in Use", "ingress", "verification_method", "dynamite-project-starter"):
                self.assertIn(value, text, (lang, value))
            self.assertIn("⚙ Admin → Spaces → Commencer", text)
            for value in ("diamond.flows[]", "project.weeks", "`designed`", "`reduire`", "(Recomm"):  # 0.60.22
                self.assertIn(value, text, (lang, value))
            self.assertNotIn('"marks": [{', text)  # marks are plain strings in Dynamite

    def test_05_click_first(self):
        """0.60.22: answers to click (the multiple-choice tool of the interface), free text only twice."""
        self.assertIn("Ne demandez du texte libre que deux fois", starter_prompt.render("fr"))
        self.assertIn("Ask for free\n   text only twice", starter_prompt.render("en"))

    def test_02_example_is_valid(self):
        clean, _ = starter.parse(json.loads(starter_prompt.example()))
        self.assertEqual(len(clean["requirements"]), 2)
        self.assertEqual(len(clean["diamond"]["functions"]), 4)
        self.assertEqual(clean["tests"][0]["verifies"], [clean["requirements"][1]["ref"]])

    def test_03_values_follow_the_tool(self):
        vocab = starter._vocab()
        table = starter_prompt.values_table("fr")
        for key in ("category", "lifecycle", "stakeholder", "subject", "level"):
            for value in vocab[key]:
                if value:
                    self.assertIn("`{}`".format(value), table, value)

    def test_04_site_and_screen(self):
        self.assertTrue((BASE_DIR / "site" / "starter.md").exists())
        self.assertTrue((BASE_DIR / "site" / "en" / "starter.md").exists())
        js = (BASE_DIR / "static" / "js" / "admin_starter.js").read_text("utf-8")
        self.assertIn("0.60.18-starter-prompt", js)
        self.assertIn("/api/starter/prompt?lang=fr&download=1", js)
