"""0.60.107 (D-O-119): the Budget Lines fold by Funding Space and by sub-project (the label before « · ») in the export
picker, « Spaces et organismes » and the week view (static/js/timesheet/fold.js). Behaviour: tests/js/timesheet_fold.js.

    python -m unittest tests.test_timesheet_fold -v
"""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
JS = BASE_DIR / "static" / "js" / "timesheet"


class TimesheetFoldTest(unittest.TestCase):
    def test_01_loaded_first_and_used_by_the_three_screens(self):
        from core.modules import MODULE_MANIFEST
        scripts = next(m for m in MODULE_MANIFEST if m["key"] == "timesheet")["scripts"]
        self.assertEqual(scripts[0], "/js/timesheet/fold.js")
        self.assertIn("TS.foldButton(", (JS / "manage.js").read_text("utf-8"))
        self.assertIn("TS.foldButton(", (JS / "budget.js").read_text("utf-8"))
        self.assertIn("TS.taskOptions(", (JS / "timesheet.js").read_text("utf-8"))

    def test_02_no_html_string_state_in_the_browser_only(self):
        text = (JS / "fold.js").read_text("utf-8")
        self.assertNotIn("innerHTML", text)
        self.assertNotIn("api.", text)  # the fold state never goes to the server
        self.assertIn('"0.60.107-ts-fold"', text)
        for name in ("fold.js", "manage.js", "budget.js", "timesheet.js"):
            self.assertLess(len((JS / name).read_text("utf-8").splitlines()), 500)

    def test_03_a_folded_node_is_hidden_whatever_its_display(self):
        css = (BASE_DIR / "static" / "css" / "timesheet.css").read_text("utf-8")
        self.assertIn(".tt-page [hidden] { display: none !important; }", css)
        self.assertIn(".tt-fold:focus-visible", css)

    def test_05_project_starter_export_keeps_the_sub_projects(self):
        """export -> import gives back the same labels: one group per sub-project, a line without one stands alone"""
        from core import starter, starter_export
        lines = [("PR-PM1", "1. Gestion du programme · Suivi et rapports (client)"), ("PR-MEC", "4. Conception détaillée · Mécanique"),
                 ("PR-PM2", "1. Gestion du programme · Revues"), ("PR-X1", "Essais divers")]
        groups = starter_export._code_groups(lines)
        self.assertEqual([g["label"] for g in groups], ["1. Gestion du programme", "4. Conception détaillée", "Essais divers"])
        self.assertEqual([c["key"] for c in groups[0]["codes"]], ["PR-PM1", "PR-PM2"])
        self.assertEqual(groups[2], {"key": "PR-X1", "label": "Essais divers"})
        self.assertTrue(all(starter.GROUP_RE.match(g["key"]) for g in groups[:2]))
        self.assertEqual(sorted(starter.codes_of({"time_codes": [dict(g, codes=g.get("codes", [])) for g in groups]})), sorted(lines))

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_04_behaviour(self):
        out = subprocess.run(["node", str(BASE_DIR / "tests" / "js" / "timesheet_fold.js")], capture_output=True, text=True,
                             timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("timesheet_fold OK", out.stdout)


if __name__ == "__main__":
    unittest.main()
