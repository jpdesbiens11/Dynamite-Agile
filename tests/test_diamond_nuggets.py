"""0.60.16 (D-O-028): Diamond 💎 -- Golden Nuggets: 20 first principles, the 5-step algorithm and the design rules, each
with its use on the project; the screen is registered in the Diamond shell."""
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

STATIC = BASE_DIR / "static" / "js" / "diamond"


class NuggetsTest(unittest.TestCase):
    def test_01_content(self):
        text = (STATIC / "nuggets_content.js").read_text("utf-8")
        blocks = {name: re.search(r"const {} = \[(.*?)\n  \];".format(name), text, re.S).group(1) for name in ("PRINCIPLES", "ALGORITHM", "RULES")}
        counts = {name: len(re.findall(r'\{ title: "', body)) for name, body in blocks.items()}
        self.assertEqual(counts, {"PRINCIPLES": 20, "ALGORITHM": 5, "RULES": 5})
        for name, body in blocks.items():
            self.assertEqual(len(re.findall(r'apply: "', body)), counts[name], name)  # every nugget says how to use it
        self.assertEqual(len(re.findall(r'example: "', blocks["PRINCIPLES"])), 20)  # one industry example each
        self.assertNotIn("innerHTML", (STATIC / "nuggets.js").read_text("utf-8"))

    def test_02_registered(self):
        shell = (STATIC / "diamond.js").read_text("utf-8")
        self.assertIn('["nuggets", "Golden Nuggets"]', shell)
        from core import modules
        entry = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        self.assertIn("/js/diamond/nuggets.js", entry["scripts"])
        self.assertLess(entry["scripts"].index("/js/diamond/nuggets_content.js"), entry["scripts"].index("/js/diamond/nuggets.js"))


if __name__ == "__main__":
    unittest.main()
