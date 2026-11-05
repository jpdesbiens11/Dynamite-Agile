"""Platform search (core lot v0.7, D-B-022; everywhere + advanced, lot v0.16, D-B-076).

The core knows which Spaces the user can see and parses the query; every
module answers for its own data through a `search(conn, projects, q)` hook
(core/modules.py) and returns hits scored by q.score(). The core adds two
platform-wide sources: the people directory and the interface Audit.

Query syntax (all words must appear, accents and case ignored):
    rails verrou          both words, anywhere in the item
    "coupure thermique"   exact phrase
    -collage              exclude the items that contain this word
    EQP-12                a key: exact match first
Advanced options (all optional): spaces (keys), types (result codes, TYPES),
in=title (titles and keys only), since / until (last change, aaaa-mm-jj),
open=1 (leave out closed / done / cancelled items), sort=date.
Results are never HTML: the browser shows title / snippet as text and
follows `href`.
"""
import re
import unicodedata

from . import modules, permissions
from .errors import ApiError

MAX_QUERY = 200
MAX_TERMS = 10
MAX_RESULTS = 400
PER_TYPE = 200
SNIPPET = 180

# result type -> (label, group) -- the advanced search offers them by group
TYPES = {
    "page": ("Pages wiki", "Dynamite"), "page_comment": ("Commentaires de page", "Dynamite"),
    "ticket": ("Issues", "Agile"), "ticket_comment": ("Commentaires d'issue", "Agile"),
    "change": ("PR, Bugs, ECN", "Change Management"),
    "requirement": ("Requirements", "Goldmine"), "need": ("Needs", "Goldmine"), "qa": ("Q&A", "Goldmine"),
    "test": ("Tests (Testing base)", "Testing"),
    "task": ("Plan Tasks", "Exploration"),
    "function": ("Fonctions, risques et DFMEA", "Diamond"),  # 0.60.36 (D-O-044)
    "idea": ("Idées et séances", "Tools"), "analysis": ("Pugh et Kepner-Tregoe", "Tools"),
    "reference": ("Références documentaires", "Generator"),
    "person": ("Personnes (annuaire)", "Plateforme"), "audit": ("Observations Audit", "Plateforme"),
}


def fold(text):
    """Lower case without accents: « Étanchéité » matches « etancheite »."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return text.lower()


def terms_of(query):
    """Kept for compatibility (0.13 hooks): the plain words of a query."""
    return [fold(t) for t in re.split(r"\s+", query.strip()) if len(t) >= 2][:MAX_TERMS]


def matches(terms, *texts):
    blob = fold(" ".join(str(t or "") for t in texts))
    return all(t in blob for t in terms)


def _date(value, label):
    value = str(value or "").strip()
    if not value:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ApiError(400, "Date « {} » : format aaaa-mm-jj attendu ({}).".format(value[:20], label))
    return value


class Query:
    """A parsed query and its options; modules call q.wants(), q.score(), q.hit()."""

    def __init__(self, raw, types=None, fields="all", since="", until="", open_only=False, user_id=None):
        self.raw = raw
        self.required, self.excluded, self.phrases = [], [], []
        for neg, phrase, word in re.findall(r'(-?)(?:"([^"]+)"|(\S+))', raw):
            text = fold(phrase if phrase else word).strip()
            if not text or (len(text) < 2 and not phrase):
                continue
            (self.excluded if neg else self.required).append(text)
            if phrase and not neg:
                self.phrases.append(text)
        self.required, self.excluded = self.required[:MAX_TERMS], self.excluded[:MAX_TERMS]
        self.types = set(types or TYPES)
        self.title_only = fields == "title"
        self.since, self.until = since, until
        self.open_only = open_only
        self.user_id = user_id

    @property
    def empty(self):
        return not self.required

    def wants(self, *types):
        return any(t in self.types for t in types)

    def in_window(self, updated_at):
        day = str(updated_at or "")[:10]
        if self.since and (not day or day < self.since):
            return False
        return not (self.until and day and day > self.until)

    def score(self, key="", title="", body=()):
        """0 when the item does not match; otherwise higher = more relevant."""
        head = fold("{} {}".format(key or "", title or ""))
        text = head if self.title_only else head + " " + fold(" ".join(str(b or "") for b in body))
        if any(t not in text for t in self.required) or any(t in text for t in self.excluded):
            return 0
        score = sum(4 if t in head else 1 for t in self.required) + sum(3 for p in self.phrases if p in head)
        if key and fold(key) in self.required:
            score += 50  # EQP-12 typed: that item first
        return score

    def snippet(self, text):
        """A short extract around the first word found."""
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        low = fold(text)
        pos = min([p for p in (low.find(t) for t in self.required) if p >= 0] or [0])
        start = max(0, pos - 60)
        cut = text[start:start + SNIPPET]
        return ("…" if start else "") + cut + ("…" if start + SNIPPET < len(text) else "")

    def hit(self, type_, score, project, title, href, body_text="", updated_at="", closed=False, extra=""):
        """A result dict, or None when a filter excludes it."""
        if not score or not self.wants(type_) or not self.in_window(updated_at) or (self.open_only and closed):
            return None
        return {"type": type_, "kind": TYPES[type_][0], "score": score, "project": project, "title": title,
                "snippet": self.snippet(body_text) if body_text else "", "href": href, "updated_at": updated_at or "",
                "closed": bool(closed), "extra": extra}


def snippet(text, terms):
    """Kept for compatibility (0.13 hooks)."""
    q = Query(" ".join(terms))
    return q.snippet(text)


def _people(conn, q):
    hits = []
    if not q.wants("person"):
        return hits
    for r in conn.execute("SELECT username, display_name, title, expertise, route_when FROM users WHERE is_active = 1"):
        s = q.score(r["display_name"], r["username"], (r["title"], r["expertise"], r["route_when"]))
        h = q.hit("person", s, "", "{} ({})".format(r["display_name"], r["username"]), "#/home",
                  " · ".join(filter(None, (r["title"], r["expertise"], r["route_when"]))))
        if h:
            hits.append(h)
    return hits


def _audits(conn, q):
    hits = []
    if not q.wants("audit"):
        return hits
    for r in conn.execute("SELECT id, kind, status, module, page_title, description, admin_note, updated_at FROM ui_audits"):
        s = q.score("AUDIT-{}".format(r["id"]), r["page_title"], (r["description"], r["admin_note"], r["module"]))
        h = q.hit("audit", s, "", "Audit #{} · {}".format(r["id"], (r["description"] or "")[:80]), "#/audit/{}".format(r["id"]),
                  r["description"], r["updated_at"], closed=r["status"] in ("done", "rejected"))
        if h:
            hits.append(h)
    return hits


def run(conn, user, q, space_keys=None):
    projects = {p["id"]: p["key"] for p in permissions.visible_projects(conn, user)
                if not space_keys or p["key"] in space_keys}
    results = []
    if projects:
        for key, hook in modules.search_hooks():
            for hit in hook(conn, projects, q) or []:
                results.append(dict(hit, module=key))
    if not space_keys:
        results += [dict(h, module="platform") for h in _people(conn, q) + _audits(conn, q)]
    return results


def api_search(ctx):
    raw = str(ctx.query.get("q", "")).strip()
    if len(raw) > MAX_QUERY:
        raise ApiError(400, "Recherche trop longue. Correctif : {} caractères au maximum.".format(MAX_QUERY))
    types = [t for t in str(ctx.query.get("types", "")).split(",") if t]
    unknown = [t for t in types if t not in TYPES]
    if unknown:
        raise ApiError(400, "Type de résultat inconnu : {}. Valeurs : {}.".format(", ".join(unknown), ", ".join(TYPES)))
    spaces = [s.strip().upper() for s in str(ctx.query.get("spaces", "")).split(",") if s.strip()]
    q = Query(raw, types=types or None, fields=ctx.query.get("in", "all"),
              since=_date(ctx.query.get("since"), "modifié depuis"), until=_date(ctx.query.get("until"), "modifié avant"),
              open_only=str(ctx.query.get("open", "")) in ("1", "true", "oui"), user_id=ctx.user["id"])
    base = {"query": raw, "types": {k: {"label": v[0], "group": v[1]} for k, v in TYPES.items()}}
    if q.empty:
        return dict(base, results=[], counts={}, total=0, truncated=False)
    results = run(ctx.conn, ctx.user, q, spaces or None)
    counts = {}
    for r in results:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    if ctx.query.get("sort") == "date":
        results.sort(key=lambda r: r["updated_at"], reverse=True)
    else:
        results.sort(key=lambda r: (r["score"], r["updated_at"]), reverse=True)
    return dict(base, results=results[:MAX_RESULTS], counts=counts, total=len(results), truncated=len(results) > MAX_RESULTS)


ROUTES = [
    ("GET", r"/api/search", api_search, "user"),
]
