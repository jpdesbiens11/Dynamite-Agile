"""The prompt of the Project Starter (0.60.18, D-O-019): the text a person pastes into an AI assistant.

tools/site/starter.md (FR) and tools/site/en/starter.md (EN) hold the interview; this module fills in what must never
drift from the tool: {{VALUES}} (the vocabularies read by core/starter.py from Goldmine, Testing and Timesheet),
{{EXAMPLE}} (a short valid file cut from deploy/starter_exemples/lampe_bureau.json), {{SITE_URL}} and {{REPO}}.
Used by tools/build_site.py (site/starter.md) and by GET /api/starter/prompt (the « Commencer » screen, offline too).
"""
import json
from pathlib import Path

from . import starter

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "tools" / "site"
EXAMPLE_FILE = BASE / "deploy" / "starter_exemples" / "lampe_bureau.json"
REPO = "https://github.com/jpdesbiens11/Dynamite-Agile"
SITE_URL = "https://jpdesbiens11.github.io/Dynamite-Agile"

FIELDS = [  # (field, FR, EN, vocabulary key or a fixed tuple)
    ("project.markets", "marchés", "markets", starter.MARKETS),
    ("team.role", "rôle dans le Space", "role in the Space", starter.ROLES),
    ("requirements.kind", "besoin ou requis", "need or requirement", "kind"),
    ("requirements.category", "catégorie", "category", "category"),
    ("requirements.lifecycle", "étape du cycle de vie", "life-cycle stage", "lifecycle"),
    ("requirements.stakeholder", "partie prenante", "stakeholder", "stakeholder"),
    ("requirements.source", "origine", "origin", "source"),
    ("requirements.verification_method", "I inspection, A analyse, D démonstration, T essai",
     "I inspection, A analysis, D demonstration, T test", "verification_method"),
    ("requirements.criticality", "A la plus critique … E la moins", "A most critical … E least", "criticality"),
    ("tests.subject", "sujet de l'essai", "test subject", "subject"),
    ("tests.category", "type d'essai", "kind of test", "test_category"),
    ("tests.level", "niveau d'intégration", "integration level", "level"),
    ("tests.method", "méthode", "method", "method"),
]


def values_table(lang):
    vocab = starter._vocab()
    head = ("| Champ | Valeurs | Sens |\n|---|---|---|" if lang == "fr" else "| Field | Values | Meaning |\n|---|---|---|")
    rows = [head]
    for field, fr, en, source in FIELDS:
        options = [v for v in (vocab[source] if isinstance(source, str) else source) if v]
        rows.append("| `{}` | {} | {} |".format(field, ", ".join("`{}`".format(v) for v in options), fr if lang == "fr" else en))
    return "\n".join(rows)


def example():
    """One item of each list, from the complete lamp example: a need, a requirement derived from it, the test of it."""
    full = json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))
    reqs = full["requirements"]
    req = next(r for r in reqs if r.get("kind", "requirement") == "requirement" and r.get("derived_from"))
    need = next(r for r in reqs if r["ref"] == req["derived_from"][0])
    test = next(t for t in full["tests"] if req["ref"] in t.get("verifies", []))
    group = dict(full["time_codes"][0], codes=full["time_codes"][0]["codes"][:2])
    short = {k: full[k] for k in ("format", "format_version", "language", "generated_by", "generated_at", "project")}
    short.update(team=full["team"][:1], requirements=[need, dict(req, derived_from=[need["ref"]])],
                 tests=[dict(test, verifies=[req["ref"]])], time_codes=[group], pages=full["pages"][:2])
    return json.dumps(short, ensure_ascii=False, indent=1)


def render(lang="fr", site_url=SITE_URL, repo=REPO):
    src = SRC if lang == "fr" else SRC / "en"
    text = (src / "starter.md").read_text(encoding="utf-8")
    for key, value in (("VALUES", values_table(lang)), ("EXAMPLE", example()), ("SITE_URL", site_url), ("REPO", repo)):
        text = text.replace("{{" + key + "}}", value)
    return text
