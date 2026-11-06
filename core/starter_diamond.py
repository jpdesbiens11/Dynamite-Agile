"""Diamond in the Project Starter file (0.60.22, D-O-032): the functional analysis an AI assistant prepares with the
team -- the functional tree, then what derives from it: the functional structure (inputs, outputs, flows), the parts on
the functions, the project risks and the first DFMEA rows.

    "diamond": {"functions": [{ref, text, type, parent, kano, importance, critical, notes}],
                "ports": [{ref, side: in | out, label, kind}],
                "flows": [{view: general | detail, kind, label, src: ref, dst: ref}],
                "parts": [{ref, name, kind, notes, functions: [ref]}],
                "risks": [{title, cause, consequence, category, phase, probability, impact, response, action, function,
                           owner, due}],
                "dfmea": [{higher, focus, lower, function, requirement, failure_mode, effect, severity, cause, prevention,
                           occurrence, detection_ctrl, detection, action, owner, due}],
                "story": [{title, caption, notes, items: [{p, x, y, s, f, t}]}]}
story (0.60.52, D-O-061): the Storyline, scene by scene; p = a pictogram key of modules/diamond/story.PICTOS, x / y in % of
the scene, s = size 1 to 3, f = mirror 0 / 1, t = a short label. It may come without any function (a team that only told
the story so far).
owner (0.60.38, D-O-047): the username of a person of the "team" list who carries the action; due: AAAA-MM-JJ.

The first function without a parent is the primary function; its descendants are the tree (secondary, tertiary,
technique at level 4); other functions without a parent stay outside the tree (« estime »). The rules are those of the
screens of Diamond, read from the module so they never drift apart: the general view links the secondary functions, the
detail view the tertiary ones (no technique function), a flow goes from an input or a function to a function or an
output. Every item arrives as an AI draft (« Brouillon IA » in its notes). parse() checks, apply() creates.
"""
from .errors import ApiError

LIMITS = {"functions": 120, "ports": 40, "flows": 200, "parts": 80, "risks": 60, "dfmea": 120, "story": 40}
NOTE = {"fr": "Brouillon IA (Project Starter) : à relire par l'équipe.", "en": "AI draft (Project Starter): to be reviewed by the team."}


def _vocab():
    from modules.diamond import dfmea, functions, parts, risks, structure
    return {"type": functions.TYPES, "kano": functions.KANO, "importance": functions.IMPORTANCE, "side": structure.SIDES,
            "kind": structure.KINDS, "view": structure.VIEWS, "part_kind": parts.KINDS, "category": risks.CATEGORIES,
            "phase": risks.PHASES, "response": risks.RESPONSES, "dfmea_texts": dfmea.TEXTS, "max_level": functions.MAX_LEVEL}


def _bad(path, message, fix):
    raise ApiError(400, "Fichier Project Starter refusé (diamond.{}) : {} Correctif : {}".format(path, message, fix))


def _list(raw, name):
    value = raw.get(name)
    if value is None:
        return []
    if not isinstance(value, list):
        _bad(name, "liste attendue.", "écrivez […] à cet endroit, même vide.")
    if len(value) > LIMITS[name]:
        _bad(name, "{} éléments (au plus {}).".format(len(value), LIMITS[name]), "gardez l'essentiel ; l'équipe complétera dans Diamond.")
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            _bad("{}[{}]".format(name, i), "objet attendu.", "écrivez {…} pour chaque élément.")
    return value


def _text(obj, name, path, limit, required=False):
    value = obj.get(name, "")
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        _bad(path + "." + name, "texte attendu.", "écrivez une chaîne entre guillemets.")
    value = " ".join(str(value).split())
    if required and not value:
        _bad(path + "." + name, "champ obligatoire vide.", "écrivez quelques mots.")
    if len(value) > limit:
        _bad(path + "." + name, "{} caractères (au plus {}).".format(len(value), limit), "raccourcissez.")
    if "<" in value and ">" in value:
        _bad(path + "." + name, "balise HTML.", "du texte seulement.")
    return value


def _choice(obj, name, path, options, default=""):
    value = obj.get(name, default)
    value = default if value in (None, "") else str(value)
    if value not in options:
        _bad(path + "." + name, "valeur « {} » inconnue.".format(value), "une de : {}.".format(", ".join(k for k in options if k)))
    return value


def _scale(obj, name, path, low, high, optional=False):
    value = obj.get(name)
    if optional and value in (None, "", 0):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        _bad(path + "." + name, "« {} » n'est pas un entier de {} à {}.".format(value, low, high),
             "un nombre entier de {} à {}{}.".format(low, high, ", ou retirez la clé" if optional else ""))
    return value


def _ref(obj, path, seen):
    ref = _text(obj, "ref", path, 24, required=True)
    if ref in seen:
        _bad(path + ".ref", "« {} » déjà utilisée.".format(ref), "une ref unique par élément.")
    seen.add(ref)
    return ref


def _functions(raw, v):
    out, seen, level, primary = [], set(), {}, None
    for i, f in enumerate(_list(raw, "functions")):
        path = "functions[{}]".format(i)
        ref = _ref(f, path, seen)
        parent = f.get("parent")
        if parent in ("", None):
            parent = None
        elif parent not in level:
            _bad(path + ".parent", "fonction « {} » introuvable plus haut.".format(parent), "déclarez la fonction parente avant ses enfants, ou null.")
        ftype = _choice(f, "type", path, v["type"], "usage")
        if parent is None:
            if primary is None:
                if ftype != "usage":
                    _bad(path, "la première fonction sans parent est la fonction primaire ; « {} » est de type {}.".format(ref, ftype),
                         "écrivez la fonction primaire (type usage) en premier ; les fonctions d'estime viennent après.")
                primary = ref
            depth = 1
        else:
            depth = level[parent][0] + 1
        if depth > v["max_level"] or (depth == v["max_level"] and ftype != "technique"):
            _bad(path + ".parent", "niveau {} : l'arbre a trois niveaux ; seule une fonction de type technique va au niveau 4.".format(depth),
                 "placez-la plus haut, ou donnez-lui le type technique.")
        in_tree = ref == primary or (parent is not None and level[parent][1])
        level[ref] = (depth, in_tree)
        out.append({"ref": ref, "text": _text(f, "text", path, 160, required=True), "ftype": ftype, "parent": parent,
                    "kano": _choice(f, "kano", path, v["kano"]), "importance": _choice(f, "importance", path, v["importance"]),
                    "critical": 1 if f.get("critical") is True else 0, "notes": _text(f, "notes", path, 1500),
                    "primary": ref == primary, "level": depth, "in_tree": in_tree})
    if out and not primary:
        _bad("functions", "aucune fonction primaire.", "la première fonction sans parent est la fonction primaire.")
    return out


def _views(functions):
    """{"general": refs of the secondary functions, "detail": refs of the tertiary ones (+ secondaries without any)}."""
    tree = [f for f in functions if f["in_tree"]]
    secondaries = [f["ref"] for f in tree if f["level"] == 2]
    tertiaries = [f for f in tree if f["level"] == 3 and f["ftype"] != "technique"]
    with_kids = {f["parent"] for f in tertiaries}
    return {"general": set(secondaries), "detail": {f["ref"] for f in tertiaries} | {r for r in secondaries if r not in with_kids}}


def _owner(obj, path, usernames):
    """0.60.38 (D-O-047): who carries the action (a username of the team) and by when."""
    who = obj.get("owner") or None
    if who is not None and who not in usernames:
        _bad(path + ".owner", "« {} » n'est pas dans l'équipe.".format(str(who)[:40]), "le username d'une personne de la liste team, ou retirez la clé.")
    when = str(obj.get("due") or "").strip()
    if when:
        import datetime as dt
        try:
            dt.date.fromisoformat(when)
        except ValueError:
            _bad(path + ".due", "date « {} ».".format(when[:20]), "AAAA-MM-JJ, ou retirez la clé.")
    return {"owner": who, "due": when}


def parse(raw, language="fr", test_refs=(), usernames=()):
    """The "diamond" object of the file -> its clean copy (empty lists when absent)."""
    raw = raw.get("diamond") or {}
    if not isinstance(raw, dict):
        _bad("", "objet attendu.", "écrivez \"diamond\": {…}, ou retirez la clé.")
    v = _vocab()
    functions = _functions(raw, v)
    if not functions and any(raw.get(k) for k in ("ports", "flows", "parts", "dfmea")):
        _bad("functions", "structure, pièces ou DFMEA sans arbre fonctionnel.", "écrivez d'abord les fonctions.")
    refs = {f["ref"] for f in functions}
    views = _views(functions)
    ports, seen = [], set(refs)
    for i, p in enumerate(_list(raw, "ports")):
        path = "ports[{}]".format(i)
        ports.append({"ref": _ref(p, path, seen), "side": _choice(p, "side", path, v["side"]),
                      "label": _text(p, "label", path, 80, required=True), "kind": _choice(p, "kind", path, v["kind"], "energy")})
    side = {p["ref"]: p["side"] for p in ports}
    flows = []
    for i, fl in enumerate(_list(raw, "flows")):
        path = "flows[{}]".format(i)
        view = _choice(fl, "view", path, v["view"], "general")
        ends = []
        for end in ("src", "dst"):
            ref = fl.get(end)
            if ref in side:
                if (end == "src") != (side[ref] == "in"):
                    _bad(path + "." + end, "« {} » est une {}.".format(ref, "entrée" if side[ref] == "in" else "sortie"),
                         "un flux part d'une entrée (ou d'une fonction) et arrive à une sortie (ou à une fonction).")
            elif ref not in views[view]:
                _bad(path + "." + end, "« {} » n'est pas une fonction de la vue {}.".format(ref, view),
                     "vue general : les fonctions secondaires ; vue detail : les fonctions tertiaires (sans les techniques).")
            ends.append(ref)
        if ends[0] == ends[1]:
            _bad(path, "flux de « {} » vers elle-même.".format(ends[0]), "un flux relie deux éléments différents.")
        if ends[0] in side and ends[1] in side:
            _bad(path, "flux d'une entrée directement vers une sortie.", "faites passer le flux par la fonction qui le traite.")
        flows.append({"view": view, "kind": _choice(fl, "kind", path, v["kind"], "energy"),
                      "label": _text(fl, "label", path, 60), "src": ends[0], "dst": ends[1]})
    taggable = views["general"] | views["detail"]
    parts = []
    for i, p in enumerate(_list(raw, "parts")):
        path = "parts[{}]".format(i)
        fns = p.get("functions") or []
        if not isinstance(fns, list) or any(f not in taggable for f in fns):
            _bad(path + ".functions", "fonction hors de la structure.", "des refs de fonctions secondaires ou tertiaires de l'arbre.")
        parts.append({"name": _text(p, "name", path, 80, required=True), "kind": _choice(p, "kind", path, v["part_kind"], "designed"),
                      "notes": _text(p, "notes", path, 1000), "functions": list(dict.fromkeys(fns))})
    risks = []
    for i, r in enumerate(_list(raw, "risks")):
        path = "risks[{}]".format(i)
        fn = r.get("function") or None
        if fn is not None and fn not in refs:
            _bad(path + ".function", "fonction « {} » introuvable.".format(fn), "la ref d'une fonction de l'arbre, ou retirez la clé.")
        risks.append({"title": _text(r, "title", path, 200, required=True), "cause": _text(r, "cause", path, 400),
                      "consequence": _text(r, "consequence", path, 400), "category": _choice(r, "category", path, v["category"], "technique"),
                      "phase": _choice(r, "phase", path, v["phase"]), "probability": _scale(r, "probability", path, 1, 5),
                      "impact": _scale(r, "impact", path, 1, 5), "response": _choice(r, "response", path, v["response"]),
                      "action": _text(r, "action", path, 600), "function": fn, **_owner(r, path, usernames)})
    dfmea = []
    for i, d in enumerate(_list(raw, "dfmea")):
        path = "dfmea[{}]".format(i)
        fn = d.get("function") or None
        if fn is not None and fn not in refs:
            _bad(path + ".function", "fonction « {} » introuvable.".format(fn), "la ref d'une fonction de l'arbre, ou retirez la clé.")
        row = {name: _text(d, name, path, limit) for name, (_label, limit) in v["dfmea_texts"].items()}
        from modules.diamond import dfmea_practices as GP
        row["failure_mode"] = GP.ras(row["failure_mode"])  # 0.60.28: « Rien à signaler », justified in effect
        if row["failure_mode"] == GP.RAS and not row["effect"]:
            _bad(path + ".effect", "« Rien à signaler » sans justification.", "écrivez dans effect pourquoi cette fonction ne peut pas "
                 "faillir (officiellement, toute fonction peut tomber en panne), ou décrivez un vrai mode de défaillance.")
        if not row["failure_mode"]:
            _bad(path + ".failure_mode", "mode de défaillance vide.", "chaque ligne du DFMEA a un Failure Mode.")
        row.update({name: _scale(d, name, path, 1, 10, optional=True) for name in ("severity", "occurrence", "detection")})
        row["function"] = fn
        test = d.get("test") or None  # 0.60.24 (D-O-033): the key test, a ref of the file's tests
        if test is not None and test not in test_refs:
            _bad(path + ".test", "essai « {} » introuvable.".format(test), "la ref d'un essai de la liste tests, ou retirez la clé.")
        row["test"] = test
        row.update(_owner(d, path, usernames))
        dfmea.append(row)
    return {"functions": functions, "ports": ports, "flows": flows, "parts": parts, "risks": risks, "dfmea": dfmea,
            "story": _story(raw), "note": NOTE[language]}


def _story(raw):
    from modules.diamond import story
    out = []
    for i, scene in enumerate(_list(raw, "story")):
        path = "story[{}]".format(i)
        try:
            items = story.clean_items(scene.get("items") or [])
        except ApiError as err:
            _bad(path + ".items", err.message.split(" Correctif")[0], "des clés de pictogrammes de la liste, x et y de 0 à 100, "
                 "30 pictogrammes au plus par scène.")
        out.append({"title": _text(scene, "title", path, story.LIMITS["title"]) or "Scène {}".format(i + 1),
                    "caption": _text(scene, "caption", path, story.LIMITS["caption"]),
                    "notes": _text(scene, "notes", path, story.LIMITS["notes"]), "items": items})
    return out


def counts(clean):
    """What « Commencer » will create; DFMEA: the file's rows plus one per function of the tree without a row (D-O-037)."""
    d = clean.get("diamond") or {}
    out = {k: len(d.get(k) or []) for k in LIMITS}
    if d.get("functions"):
        out["dfmea"] += len({f["ref"] for f in d["functions"] if f["in_tree"]} - {r["function"] for r in d.get("dfmea") or []})
    return out


def apply(conn, user_id, pid, d, test_ids=None, known=None):
    """Creates the Diamond items of one Space (inside the transaction of « Commencer »); returns their counts.
    known (0.60.53, D-O-062): {ref: id} of functions already in the Space, for a file that completes an existing tree."""
    from modules.diamond import dfmea, functions as F, parts as P, risks as R, structure as S
    ids, ports = dict(known or {}), {}
    user_of = lambda name: (conn.execute("SELECT id FROM users WHERE username = ?", (name,)).fetchone() or [None])[0] if name else None  # noqa: E731
    for f in d["functions"]:
        notes = (f["notes"] + " — " if f["notes"] else "") + d["note"]
        ids[f["ref"]] = F.create(conn, user_id, pid, {"text": f["text"], "ftype": f["ftype"], "kano": f["kano"],
                                                       "importance": f["importance"], "critical": f["critical"], "notes": notes[:2000]},
                                 ids.get(f["parent"]), None, f["primary"])
    for p in d["ports"]:
        ports[p["ref"]] = S.add_port(conn, pid, p["side"], p["label"], p["kind"])
    end = lambda ref: (None, ports[ref]) if ref in ports else (ids[ref], None)  # noqa: E731
    for fl in d["flows"]:
        S.add_flow(conn, pid, fl["view"], fl["kind"], fl["label"], end(fl["src"]), end(fl["dst"]))
    for p in d["parts"]:
        oid = P.add_part(conn, user_id, pid, p["name"], p["kind"], p["notes"])
        for ref in p["functions"]:
            P.tag(conn, pid, oid, ids[ref])
    for r in d["risks"]:
        fields = {k: r[k] for k in ("title", "cause", "consequence", "category", "phase", "probability", "impact", "response", "action")}
        fields.update(function_id=ids.get(r["function"]), notes=d["note"], owner_id=user_of(r.get("owner")), due_date=r.get("due") or "")
        R.create(conn, user_id, pid, fields)
    for row in d["dfmea"]:
        fields = {k: v for k, v in row.items() if k not in ("function", "test", "owner", "due")}
        fields.update(action_owner_id=user_of(row.get("owner")), action_due=row.get("due") or None)
        fields["function_id"] = ids.get(row["function"])
        fields["test_id"] = (test_ids or {}).get(row.get("test"))
        dfmea.insert(conn, user_id, pid, fields)
    from modules.diamond import story as ST  # 0.60.52 (D-O-061): the Storyline
    for scene in d.get("story") or []:
        ST.create(conn, user_id, pid, scene)
    from modules.diamond import dfmea_complete  # 0.60.28 (D-O-037): every function, its key test, the good practices
    done = dfmea_complete.complete(conn, user_id, pid)
    return dict({k: len(d[k]) for k in LIMITS}, dfmea=len(d["dfmea"]) + done["added"], dfmea_tests=done["tested"])
