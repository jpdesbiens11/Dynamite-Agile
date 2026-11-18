"""0.60.16 (D-O-028): Diamond 💎 -- Golden Nuggets: 20 first principles, the 5-step algorithm and the design rules, each
with its use on the project; the screen is registered in the Diamond shell. 0.60.121 (D-O-134): a 4th part, « Disruptive
Innovation » (Christensen: 20 concepts and practices, the 12 case studies of the book, the reference and a summary), and one
card layout with colour families for the four parts."""
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

    def test_03_disruption(self):
        text = (STATIC / "nuggets_disruption.js").read_text("utf-8")
        blocks = {name: re.search(r"const {} = \[(.*?)\n  \];".format(name), text, re.S).group(1) for name in ("DISRUPTION", "CASES")}
        self.assertEqual(len(re.findall(r'\{ title: "', blocks["DISRUPTION"])), 20)
        self.assertEqual(len(re.findall(r'\{ title: "', blocks["CASES"])), 12)
        for name, body in blocks.items():  # every item has its example and what to do with it in a company
            n = len(re.findall(r'\{ title: "', body))
            self.assertEqual((len(re.findall(r'example: "', body)), len(re.findall(r'apply: "', body))), (n, n), name)
        fams = set(re.findall(r'fam: "([a-z]+)"', blocks["DISRUPTION"]))
        self.assertEqual(fams, {"market", "customer", "org", "act"})
        self.assertIn("The Innovator's Dilemma: When New Technologies Cause Great Firms to Fail", text)
        self.assertIn("1997", text)
        screen = (STATIC / "nuggets.js").read_text("utf-8")
        for fam in fams | {"case"}:
            self.assertIn('["{}", '.format(fam), screen)  # every family has its label and colour
        css = (BASE_DIR / "static" / "css" / "diamond_nuggets.css").read_text("utf-8")
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,6}\b")  # tokens only

    def test_02_registered(self):
        shell = (STATIC / "diamond.js").read_text("utf-8")
        self.assertIn('["nuggets", "Golden Nuggets"]', shell)
        from core import modules
        entry = next(m for m in modules.MODULE_MANIFEST if m["key"] == "diamond")
        self.assertIn("/js/diamond/nuggets.js", entry["scripts"])
        order = [entry["scripts"].index("/js/diamond/" + f) for f in ("nuggets_content.js", "nuggets_disruption.js", "nuggets.js")]
        self.assertEqual(order, sorted(order))
        self.assertIn("/css/diamond_nuggets.css", entry["styles"])


if __name__ == "__main__":
    unittest.main()
