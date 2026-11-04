"""Project Starter file (0.60.05, D-O-019): the project an AI assistant prepares with a person, read by « Commencer ».

A person pastes site/starter.md into an AI assistant, answers its questions one at a time, and gets one JSON file:

    {"format": "dynamite-project-starter", "format_version": 1, "language": "fr" | "en",
     "generated_by": "...", "generated_at": "YYYY-MM-DD",
     "project": {key, name, description, industry, product_type, markets: ["CA", "US", "EU", ...]},
     "team": [{username, display_name, study_profile, title, role: editor | manager | reader}],
     "requirements": [{ref, kind, statement, rationale, category, lifecycle, stakeholder, source, standard, edition,
                       clause, verification_method, acceptance_criteria, criticality, derived_from: [ref, ...]}],
     "tests": [{ref, title, subject, category, standard, section, level, method, objective, acceptance, means,
                verifies: [requirement ref, ...]}],
     "time_codes": [{key, label, codes: [{key, label}]}],
     "pages": [{ref, title, parent: page ref | null, body: Dynamite page body}]}

The file is written by an AI, not exported by this site: it is not sealed and nothing in it is trusted. parse()
checks every field, refuses with the path of the offending value and the fix (D-A-031), and returns a clean copy
where the file can no longer decide what only a person may decide (decisions of 2026-11-04):
- every requirement and every test arrives « À vérifier » (review = "to_verify"): a standard named by an AI may have
  the wrong edition or clause, so a person confirms it before the requirement can be approved;
- tests are « Draft »; every page is an « AI draft » (ai_draft = True) and starts with a panel saying so;
- team members are never administrators, and carry no password (the site makes a temporary one, shown once).
Pages accept the Dynamite blocks except image and ticket (they point to things that do not exist yet).
Nothing here touches the database: the creation of the Space is the next step (0.60.06).
"""
import json
import re

from .errors import ApiError

FORMAT = "dynamite-project-starter"
FORMAT_VERSION = 1
MAX_BYTES = 1536 * 1024  # fits in a 2 Mo JSON request (core/router.MAX_JSON_BYTES) once escaped
LIMITS = {"team": 12, "requirements": 300, "tests": 300, "time_codes": 40, "pages": 30}
KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")                      # same rule as core/admin.PROJECT_KEY_RE
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")          # same rule as core/admin.USERNAME_RE
REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,23}$")
GROUP_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,15}$")                # a heading of time codes, not a code
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LANGUAGES = ("fr", "en")
MARKETS = ("CA", "US", "EU", "UK", "MX", "AU", "JP", "CN", "KR", "IN", "BR", "INT")
ROLES = ("editor", "manager", "reader")
REVIEW = "to_verify"
AI_DRAFT_NOTE = {"fr": "Brouillon IA : contenu proposé par un assistant IA, à relire et corriger par l'équipe.",
                 "en": "AI draft: content proposed by an AI assistant, to be reviewed and corrected by the team."}


def _vocab():
    """Goldmine and Testing vocabularies, read from the modules so the two never drift apart."""
    from modules.agile import goldmine
    from modules.testing import data_tests
    return {"kind": tuple(goldmine.KINDS), "category": tuple(goldmine.CATEGORIES), "lifecycle": ("",) + tuple(goldmine.LIFECYCLE),
            "stakeholder": ("",) + tuple(goldmine.STAKEHOLDERS), "source": tuple(goldmine.SOURCES),
            "criticality": goldmine.CRITICALITY, "verification_method": ("",) + tuple(goldmine.METHODS),
            "test_category": tuple(data_tests.CATEGORIES), "level": ("",) + data_tests.LEVELS,
            "method": tuple(goldmine.METHODS), "subject": tuple(data_tests.SUBJECTS)}


def _code_re():
    """The pattern of a Timesheet code (Budget Line), read from Timesheet like the vocabularies."""
    from modules.timesheet import budget
    return budget.CODE_RE


def _bad(path, message, fix):
    raise ApiError(400, "Fichier Project Starter refusé ({}) : {} Correctif : {}".format(path, message, fix))


def _obj(value, path):
    if not isinstance(value, dict):
        _bad(path, "objet attendu.", "écrivez {…} à cet endroit.")
    return value


def _list(value, path, limit):
    if value is None:
        return []
    if not isinstance(value, list):
        _bad(path, "liste attendue.", "écrivez […] à cet endroit, même vide.")
    if len(value) > limit:
        _bad(path, "{} éléments.".format(len(value)), "{} au maximum.".format(limit))
    return value


def _text(obj, name, path, max_len, required=False, default=""):
    value = obj.get(name, default)
    value = default if value is None else value
    if not isinstance(value, str):
        _bad("{}.{}".format(path, name), "texte attendu.", "mettez la valeur entre guillemets.")
    value = value.strip()
    if required and not value:
        _bad("{}.{}".format(path, name), "champ requis vide.", "donnez une valeur.")
    if len(value) > max_len:
        _bad("{}.{}".format(path, name), "{} caractères.".format(len(value)), "{} au maximum.".format(max_len))
    if "<" in value and re.search(r"<\s*[a-zA-Z/!]", value):
        _bad("{}.{}".format(path, name), "balise HTML.", "du texte seulement, sans balise.")
    return value


def _choice(obj, name, path, options, default=""):
    value = obj.get(name, default)
    value = default if value is None else value
    if value not in options:
        _bad("{}.{}".format(path, name), "valeur « {} » inconnue.".format(value),
             "valeurs permises : " + ", ".join(o or "(vide)" for o in options) + ".")
    return value


def _refs(obj, name, path, known, what):
    values = _list(obj.get(name), "{}.{}".format(path, name), 50)
    for i, ref in enumerate(values):
        if ref not in known:
            _bad("{}.{}[{}]".format(path, name, i), "{} « {} » introuvable.".format(what, ref),
                 "utilisez le champ ref d'un élément déjà déclaré plus haut dans le fichier.")
    return list(dict.fromkeys(values))


def _ref(obj, path, seen):
    ref = obj.get("ref")
    if not isinstance(ref, str) or not REF_RE.match(ref):
        _bad(path + ".ref", "référence « {} » invalide.".format(ref), "lettres, chiffres, . _ - ; ex. R1, BES-3.")
    if ref in seen:
        _bad(path + ".ref", "référence « {} » déjà utilisée.".format(ref), "une référence unique par élément.")
    seen.add(ref)
    return ref


def _project(raw):
    p = _obj(raw.get("project"), "project")
    key = p.get("key")
    if not isinstance(key, str) or not KEY_RE.match(key):
        _bad("project.key", "clé « {} » invalide.".format(key), "2 à 10 majuscules ou chiffres, commençant par une lettre ; ex. LAMPE.")
    markets = _list(p.get("markets"), "project.markets", len(MARKETS))
    for i, m in enumerate(markets):
        if m not in MARKETS:
            _bad("project.markets[{}]".format(i), "marché « {} » inconnu.".format(m), "marchés permis : " + ", ".join(MARKETS) + ".")
    start = _text(p, "start_date", "project", 10)  # 0.60.22 (D-O-032): the reference plan of Exploration
    if start and not DATE_RE.match(start):
        _bad("project.start_date", "date « {} » invalide.".format(start), "format AAAA-MM-JJ, ou retirez la clé (lundi prochain).")
    weeks = p.get("weeks", 15)
    if isinstance(weeks, bool) or not isinstance(weeks, int) or not 4 <= weeks <= 104:
        _bad("project.weeks", "durée « {} » invalide.".format(weeks), "un nombre entier de semaines, de 4 à 104 (15 pour une session).")
    return {"key": key, "name": _text(p, "name", "project", 120, required=True),
            "description": _text(p, "description", "project", 4000), "industry": _text(p, "industry", "project", 120),
            "product_type": _text(p, "product_type", "project", 120), "markets": list(dict.fromkeys(markets)),
            "start_date": start, "weeks": weeks}


def _team(raw):
    out, names = [], set()
    for i, m in enumerate(_list(raw.get("team"), "team", LIMITS["team"])):
        path = "team[{}]".format(i)
        m = _obj(m, path)
        if "password" in m or "role" in m and m["role"] == "admin":
            _bad(path, "mot de passe ou rôle admin dans le fichier.",
                 "retirez-les : le site crée un mot de passe temporaire et aucun membre n'est administrateur.")
        username = m.get("username")
        if not isinstance(username, str) or not USERNAME_RE.match(username):
            _bad(path + ".username", "nom d'utilisateur « {} » invalide.".format(username),
                 "2 à 32 caractères : minuscules, chiffres, . _ - ; ex. nina, lea.b.")
        if username in names or username == "admin":
            _bad(path + ".username", "« {} » déjà pris dans le fichier ou réservé.".format(username), "un nom différent par personne.")
        names.add(username)
        out.append({"username": username, "display_name": _text(m, "display_name", path, 80, required=True),
                    "study_profile": _text(m, "study_profile", path, 80), "title": _text(m, "title", path, 120),
                    "role": _choice(m, "role", path, ROLES, "editor")})
    return out


def _requirements(raw, vocab):
    out, seen = [], set()
    for i, r in enumerate(_list(raw.get("requirements"), "requirements", LIMITS["requirements"])):
        path = "requirements[{}]".format(i)
        r = _obj(r, path)
        ref = _ref(r, path, seen)
        item = {"ref": ref, "kind": _choice(r, "kind", path, vocab["kind"], "requirement"),
                "statement": _text(r, "statement", path, 4000, required=True), "rationale": _text(r, "rationale", path, 4000),
                "category": _choice(r, "category", path, vocab["category"], "functional"),
                "lifecycle": _choice(r, "lifecycle", path, vocab["lifecycle"]),
                "stakeholder": _choice(r, "stakeholder", path, vocab["stakeholder"]),
                "source": _choice(r, "source", path, vocab["source"], "client"),
                "standard": _text(r, "standard", path, 200), "edition": _text(r, "edition", path, 40),
                "clause": _text(r, "clause", path, 80),
                "verification_method": _choice(r, "verification_method", path, vocab["verification_method"]),
                "acceptance_criteria": _text(r, "acceptance_criteria", path, 2000),
                "criticality": _choice(r, "criticality", path, vocab["criticality"]),
                "derived_from": _refs(r, "derived_from", path, seen - {ref}, "besoin ou requis"),
                "review": REVIEW}
        if item["source"] == "standard" and not item["standard"]:
            _bad(path + ".standard", "requis de source « standard » sans norme.", "nommez la norme, ex. IEC 62368-1.")
        out.append(item)
    return out


def _tests(raw, vocab, req_refs):
    out, seen = [], set()
    for i, t in enumerate(_list(raw.get("tests"), "tests", LIMITS["tests"])):
        path = "tests[{}]".format(i)
        t = _obj(t, path)
        out.append({"ref": _ref(t, path, seen), "title": _text(t, "title", path, 200, required=True),
                    "subject": _choice(t, "subject", path, vocab["subject"], "func"),
                    "category": _choice(t, "category", path, vocab["test_category"], "custom"),
                    "standard": _text(t, "standard", path, 200), "section": _text(t, "section", path, 80),
                    "level": _choice(t, "level", path, vocab["level"]),
                    "method": _choice(t, "method", path, vocab["method"], "T"),
                    "objective": _text(t, "objective", path, 4000), "acceptance": _text(t, "acceptance", path, 2000),
                    "means": _text(t, "means", path, 2000),
                    "verifies": _refs(t, "verifies", path, req_refs, "requis"),
                    "status": "Draft", "review": REVIEW})
    return out


def _time_codes(raw):
    """Groups of Timesheet codes. A group with codes is a heading (its key only groups them); a group without codes
    is itself a code. Every code follows the Timesheet pattern and is unique in the file (and, checked at creation,
    on the whole site)."""
    out, keys, count, code_re = [], set(), 0, _code_re()
    for i, g in enumerate(_list(raw.get("time_codes"), "time_codes", LIMITS["time_codes"])):
        path = "time_codes[{}]".format(i)
        g = _obj(g, path)
        codes = _list(g.get("codes"), path + ".codes", LIMITS["time_codes"])
        group = {"key": _key(g, path, keys, GROUP_RE if codes else code_re), "label": _text(g, "label", path, 120, required=True),
                 "codes": []}
        for j, c in enumerate(codes):
            sub = "{}.codes[{}]".format(path, j)
            c = _obj(c, sub)
            if "codes" in c:
                _bad(sub + ".codes", "troisième niveau de codes.", "deux niveaux au maximum : un groupe et ses codes.")
            group["codes"].append({"key": _key(c, sub, keys, code_re), "label": _text(c, "label", sub, 120, required=True)})
        count += len(group["codes"]) or 1
        out.append(group)
    if count > LIMITS["time_codes"]:
        _bad("time_codes", "{} codes au total.".format(count), "{} au maximum.".format(LIMITS["time_codes"]))
    return out


def _key(obj, path, keys, pattern):
    key = obj.get("key")
    if not isinstance(key, str) or not pattern.match(key):
        _bad(path + ".key", "code « {} » invalide.".format(key),
             "un code de temps s'écrit 1 à 5 majuscules, un tiret, puis 2 à 4 majuscules ou chiffres (ex. LA-MAR, C-BOI) ; "
             "un groupe qui contient des codes : 1 à 16 majuscules, chiffres ou tirets.")
    if key in keys:
        _bad(path + ".key", "code « {} » déjà utilisé.".format(key), "un code unique dans tout le fichier.")
    keys.add(key)
    return key


def codes_of(clean):
    """[(code, label)] the Space will offer in Timesheet: a group's codes are labelled « group · code »."""
    out = []
    for g in clean["time_codes"]:
        if g["codes"]:
            out += [(c["key"], "{} · {}".format(g["label"], c["label"])) for c in g["codes"]]
        else:
            out.append((g["key"], g["label"]))
    return out


def _blocks_used(node, found):
    if isinstance(node, dict):
        found.add(node.get("type"))
        for value in node.values():
            _blocks_used(value, found)
    elif isinstance(node, list):
        for value in node:
            _blocks_used(value, found)
    return found


def _pages(raw, language):
    from modules.dynamite import content
    out, seen, depth = [], set(), {}
    for i, p in enumerate(_list(raw.get("pages"), "pages", LIMITS["pages"])):
        path = "pages[{}]".format(i)
        p = _obj(p, path)
        ref = _ref(p, path, seen)
        parent = p.get("parent")
        if parent is not None and parent not in depth:
            _bad(path + ".parent", "page parente « {} » introuvable.".format(parent), "déclarez la page parente plus haut, ou null.")
        depth[ref] = 1 if parent is None else depth[parent] + 1
        if depth[ref] > 2:
            _bad(path + ".parent", "troisième niveau de pages.", "deux niveaux au maximum : une page et ses sous-pages.")
        body = _obj(p.get("body", {"type": "doc", "content": []}), path + ".body")
        banned = _blocks_used(body, set()) & {"image", "ticket"}
        if banned:
            _bad(path + ".body", "bloc « {} » dans une page de démarrage.".format(sorted(banned)[0]),
                 "retirez les images et les tickets : ils seront ajoutés dans l'outil.")
        try:
            content.validate(body)
        except ApiError as error:
            raise ApiError(400, "Fichier Project Starter refusé ({}.body) : {}".format(path, error.message))
        note = {"type": "panel", "kind": "note",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": AI_DRAFT_NOTE[language]}]}]}
        blocks = [b for b in body.get("content", []) if b != note]
        out.append({"ref": ref, "title": _text(p, "title", path, 200, required=True), "parent": parent, "ai_draft": True,
                    "body": {"type": "doc", "content": [note] + blocks}})
    return out


def parse(data):
    """Bytes, text or an already decoded object -> (clean starter, warnings). Raises ApiError on the first fault."""
    if isinstance(data, (bytes, bytearray)):
        if len(data) > MAX_BYTES:
            _bad("fichier", "plus de 1,5 Mo.", "réduisez le nombre de pages ou de requis.")
        try:
            data = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            _bad("fichier", "texte non UTF-8.", "enregistrez le fichier en UTF-8.")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as error:
            _bad("fichier", "JSON illisible (ligne {}, colonne {}).".format(error.lineno, error.colno),
                 "demandez à l'assistant de redonner le fichier complet, en un seul bloc JSON.")
    raw = _obj(data, "racine")
    if raw.get("format") != FORMAT:
        _bad("format", "format « {} ».".format(raw.get("format")), "le fichier doit commencer par \"format\": \"{}\".".format(FORMAT))
    version = raw.get("format_version")
    if isinstance(version, bool) or not isinstance(version, int) or not 1 <= version <= FORMAT_VERSION:
        _bad("format_version", "version {} non prise en charge.".format(version),
             "version {} ; mettez l'outil à jour si le fichier est plus récent.".format(FORMAT_VERSION))
    language = _choice(raw, "language", "racine", LANGUAGES, "fr")
    generated_at = _text(raw, "generated_at", "racine", 10)
    if generated_at and not DATE_RE.match(generated_at):
        _bad("generated_at", "date « {} » invalide.".format(generated_at), "format AAAA-MM-JJ.")
    vocab = _vocab()
    clean = {"format": FORMAT, "format_version": FORMAT_VERSION, "language": language,
             "generated_by": _text(raw, "generated_by", "racine", 120), "generated_at": generated_at,
             "project": _project(raw), "team": _team(raw)}
    clean["requirements"] = _requirements(raw, vocab)
    clean["tests"] = _tests(raw, vocab, {r["ref"] for r in clean["requirements"]})
    clean["time_codes"] = _time_codes(raw)
    clean["pages"] = _pages(raw, language)
    from . import starter_diamond  # 0.60.22 (D-O-032): the functional tree and what derives from it
    clean["diamond"] = starter_diamond.parse(raw, language)
    return clean, _warnings(clean)


def _warnings(clean):
    out = []
    if not clean["requirements"]:
        out.append("Aucun requis : Goldmine restera vide.")
    if not clean.get("diamond", {}).get("functions"):
        out.append("Aucun arbre fonctionnel : Diamond restera vide (arbre, structure, pièces, risques, DFMEA à faire dans l'outil).")
    if not clean["time_codes"]:
        out.append("Aucun code de temps : le Space utilisera les codes du PDP (A-01 … D-21).")
    untested = [r["ref"] for r in clean["requirements"] if r["kind"] == "requirement"
                and not any(r["ref"] in t["verifies"] for t in clean["tests"])]
    if untested:
        out.append("{} requis sans essai qui le vérifie : {}.".format(len(untested), ", ".join(untested[:10])
                                                                     + (" …" if len(untested) > 10 else "")))
    standards = sorted({x["standard"] for x in clean["requirements"] + clean["tests"] if x["standard"]})
    if standards:
        out.append("{} norme(s) nommée(s) dans le fichier, toutes « À vérifier » : confirmez l'édition en vigueur "
                   "et la clause avant d'approuver un requis.".format(len(standards)))
    return out


def starter_diamond_counts(clean):
    from . import starter_diamond
    return starter_diamond.counts(clean)


def summary(clean):
    """Counts shown before anything is created (the preview of « Commencer »)."""
    return {"project": clean["project"]["key"] + " · " + clean["project"]["name"], "team": len(clean["team"]),
            "requirements": sum(r["kind"] == "requirement" for r in clean["requirements"]),
            "needs": sum(r["kind"] == "need" for r in clean["requirements"]), "tests": len(clean["tests"]),
            "time_codes": len(codes_of(clean)), "pages": len(clean["pages"]), "plan_weeks": clean["project"]["weeks"],
            **{"diamond_" + k: n for k, n in starter_diamond_counts(clean).items()},
            "standards": sorted({x["standard"] for x in clean["requirements"] + clean["tests"] if x["standard"]})}
