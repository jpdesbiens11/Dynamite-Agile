"""0.60.09 (D-O-021): the PDP modernised with Lean Startup -- A. Discovery, B. Concept, C. Design, D. Validation et
lancement, one Build-Measure-Learn loop and its MVP per phase, industry reviews instead of the course reports."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, startup  # noqa: E402
from core.config import load_config  # noqa: E402

OLD = re.compile(r"\b(MIP|RCS|RVE)\b|Pré-étude|Étude conceptuelle|Fabrication et validation du prototype")
# Where the old names may still be written: the retired Generator codes, the old Timesheet labels kept for the update.
ALLOWED = {"modules/codex/catalog.py", "modules/timesheet/catalog.py"}


class LeanTest(unittest.TestCase):
    def test_01_no_old_name_shown(self):
        hits = []
        for folder in ("modules", "static", "tools", "deploy", "site"):
            for f in (BASE_DIR / folder).rglob("*"):
                rel = f.relative_to(BASE_DIR).as_posix()
                if not f.is_file() or "__pycache__" in rel or rel in ALLOWED or f.suffix not in (".py", ".js", ".html", ".md", ".csv", ".json"):
                    continue
                for n, line in enumerate(f.read_text("utf-8", errors="replace").splitlines(), start=1):
                    if OLD.search(line):
                        hits.append("{}:{}: {}".format(rel, n, line.strip()[:90]))
        self.assertEqual(hits, [], "\n".join(hits[:30]))

    def test_02_timesheet_labels_follow_on_an_existing_site(self):
        from modules.timesheet import budget, catalog
        self.assertEqual(catalog.PHASES, {"A": "Discovery", "B": "Concept", "C": "Design", "D": "Validation et lancement"})
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            db.init_db(data_dir / "l.db", modules.registered_schema(), modules.registered_migrations())
            with db.connect() as conn:
                auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
            startup.run(data_dir, load_config(data_dir))
            with db.connect() as conn:
                conn.execute("UPDATE timesheet_budget_lines SET label = ? WHERE code = 'B-07'", (catalog.OLD_PDP_LABELS["B-07"],))
                conn.execute("UPDATE timesheet_budget_lines SET label = 'Libellé de l''équipe' WHERE code = 'C-13'")
                budget.seed(conn)
                labels = {r["code"]: r["label"] for r in conn.execute("SELECT code, label FROM timesheet_budget_lines")}
        self.assertEqual(labels["B-07"], "B. Concept · 7. Bilan du MVP 0 : persévérer ou pivoter")
        self.assertEqual(labels["C-13"], "Libellé de l'équipe")  # reworded by an administrator: kept

    def test_03_one_review_and_one_mvp_per_phase(self):
        from modules.codex import catalog
        notes = {s["step"]: s["note"] for s in catalog.STEPS.values()}
        self.assertEqual([notes[s] for s in ("06", "12", "15", "21")], ["→ LCV", "→ CRV", "→ CDR", "→ VVR"])
        self.assertEqual({notes[s] for s in ("07", "13", "19")}, {"Build-Measure-Learn"})
        self.assertEqual([g for g, _ in catalog.DOC_GROUPS][:4], ["A. Discovery", "B. Concept", "C. Design", "D. Validation et lancement"])


if __name__ == "__main__":
    unittest.main()
