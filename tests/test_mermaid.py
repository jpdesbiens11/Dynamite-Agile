"""0.60.60 (D-O-069): Mermaid diagrams written by an AI are drawn in Dynamite pages by the platform's own engine (no
third-party library): loaded after render.js, drawn without innerHTML, checked by tests/js/mermaid.js."""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import modules  # noqa: E402

FILES = ("mermaid_parse.js", "mermaid_layout.js", "mermaid_svg.js", "mermaid_seq.js")


class MermaidTest(unittest.TestCase):
    def test_01_loaded_after_render_before_the_editor(self):
        scripts = next(m for m in modules.MODULE_MANIFEST if m["key"] == "dynamite")["scripts"]
        at = {Path(s).name: i for i, s in enumerate(scripts)}
        for name in FILES:
            self.assertIn(name, at)
            self.assertLess(at["render.js"], at[name])
            self.assertLess(at[name], at["visual_dom.js"])

    def test_02_no_html_string_and_no_library(self):
        for name in FILES:
            text = (BASE_DIR / "static" / "js" / "dynamite" / name).read_text("utf-8")
            self.assertNotIn("innerHTML", text, name)
            self.assertNotIn("http://", text.replace("http://www.w3.org/2000/svg", ""), name)
            self.assertLess(len(text.splitlines()), 500, name)
        self.assertFalse((BASE_DIR / "static" / "vendor").exists())

    def test_03_the_editor_never_saves_the_drawing(self):
        dom = (BASE_DIR / "static" / "js" / "dynamite" / "visual_dom.js").read_text("utf-8")
        self.assertIn('hasAttribute("data-skip")', dom)
        self.assertIn("language|lang", dom)
        render = (BASE_DIR / "static" / "js" / "dynamite" / "render.js").read_text("utf-8")
        self.assertIn('"data-skip": "1"', render)
        self.assertIn("}).flat();", render)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_04_engine(self):
        out = subprocess.run(["node", str(BASE_DIR / "tests" / "js" / "mermaid.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("mermaid OK", out.stdout)


if __name__ == "__main__":
    unittest.main()
