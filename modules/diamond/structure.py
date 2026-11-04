"""« Structure fonctionnelle » of Diamond (0.60.13, D-O-025): the boundary diagram of the product, built from its
functional tree (course method).

The system frame carries the primary function; its inputs (« Entrées du système ») stand on the left, its outputs
(« Sorties du système ») on the right. Two views:
  general  the secondary functions become the sub-systems; the general flows link inputs, sub-systems and outputs;
  detail   the tertiary functions inside the frame of their sub-system (no technique function: a level of detail that
           does not belong to the system design); the general flows must still be there, now handled by tertiaries.
Each flow is of one kind -- énergie, matière, information -- (the legend of the course) and has a short label
(« courant », « colle liquide »). The checks tell what the method expects: a function that exchanges nothing, or a
general flow missing in the detail view, is often the sign that the tree must be revised. Positions are saved per view
when a box is dragged; without them the screen lays the boxes out by itself. Every write is journalled.
"""
from core import audit, db, validate
from core.errors import ApiError

from . import functions as F, parts

VIEWS = {"general": "Vue générale (sous-systèmes)", "detail": "Vue détaillée (fonctions tertiaires)"}
KINDS = {"energy": "Énergie", "material": "Matière", "information": "Information"}
SIDES = {"in": "Entrée du système", "out": "Sortie du système"}
MAX_PORTS, MAX_FLOWS = 40, 400


def _text(body, name, label, limit, required=True):
    value = " ".join(str(body.get(name) or "").split())
    if required and not value:
        raise ApiError(400, "{} obligatoire. Correctif : quelques mots (ex. « Alimentation 12 V », « chaleur »).".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def _choice(body, name, options, label, default=None):
    value = str(body.get(name) or default or "").strip()
    if value not in options:
        raise ApiError(400, "{} « {} » inconnu. Correctif : {}.".format(label, value, ", ".join(options)))
    return value


def nodes(conn, pid):
    """{view: {function id: function}} -- the functions each view may show (tree only, technique left out)."""
    items = F.rows(conn, pid)
    lv, tree = F.levels(items), F.in_tree(items)
    for f in items:
        f["level"] = lv[f["id"]]
    secondaries = [f for f in items if f["id"] in tree and f["level"] == 2]
    tertiaries = [f for f in items if f["id"] in tree and f["level"] == 3 and f["ftype"] != "technique"]
    with_kids = {f["parent_id"] for f in tertiaries}
    detail = tertiaries + [f for f in secondaries if f["id"] not in with_kids]
    return {"general": {f["id"]: f for f in secondaries}, "detail": {f["id"]: f for f in detail}}, items


def _ports(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_ports WHERE project_id = ? ORDER BY side, position, id", (pid,))]


def _flows(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_flows WHERE project_id = ? ORDER BY id", (pid,))]


def sub_of(f, by_id):
    """The sub-system (secondary) a function of the detail view belongs to."""
    return f["id"] if f["level"] == 2 else f["parent_id"]


def checks(view_nodes, items, ports, flows):
    out = []
    by_id = {f["id"]: f for f in items}
    if not view_nodes["general"]:
        return ["Aucune fonction secondaire dans l'arbre fonctionnel : construisez d'abord l'arbre (Diamond → Arbre fonctionnel)."]
    if not any(p["side"] == "in" for p in ports):
        out.append("Aucune entrée du système : ce que le produit reçoit (énergie, matière, information), à gauche.")
    if not any(p["side"] == "out" for p in ports):
        out.append("Aucune sortie du système : ce que le produit rend ou rejette (lumière, chaleur, colle appliquée), à droite.")
    for view in VIEWS:
        mine = [fl for fl in flows if fl["view"] == view]
        touched = {fl["src_function_id"] for fl in mine} | {fl["dst_function_id"] for fl in mine}
        alone = [f for f in view_nodes[view].values() if f["id"] not in touched]
        if mine and alone:
            out.append("{} : {} n'échange aucun flux — à rattacher, reformuler ou retirer de l'arbre.".format(
                "Vue générale" if view == "general" else "Vue détaillée", ", ".join("F{}".format(f["number"]) for f in alone[:6])))
    used = {fl["src_port_id"] for fl in flows} | {fl["dst_port_id"] for fl in flows}
    lonely = [p for p in ports if p["id"] not in used]
    if lonely:
        out.append("Entrée ou sortie sans flux : {}.".format(", ".join("« {} »".format(p["label"]) for p in lonely[:5])))
    detail = [fl for fl in flows if fl["view"] == "detail"]
    if detail:
        def end(fl, side):
            fid, port = fl[side + "_function_id"], fl[side + "_port_id"]
            return ("p", port) if port else ("f", sub_of(by_id[fid], by_id)) if fid in by_id else None
        present = {(end(fl, "src"), end(fl, "dst"), fl["kind"]) for fl in detail}
        missing = [fl for fl in flows if fl["view"] == "general" and (end(fl, "src"), end(fl, "dst"), fl["kind"]) not in present]
        if missing:
            out.append("{} flux de la vue générale absent(s) de la vue détaillée (ex. « {} ») : montrez quelle fonction tertiaire "
                       "les traite.".format(len(missing), missing[0]["label"] or KINDS[missing[0]["kind"]]))
    return out


def payload(conn, pid):
    view_nodes, items = nodes(conn, pid)
    primary = next((f for f in items if f["is_primary"]), None)
    ports, flows = _ports(conn, pid), _flows(conn, pid)
    live = set(view_nodes["general"]) | set(view_nodes["detail"])
    flows = [fl for fl in flows if (fl["src_function_id"] in live or fl["src_port_id"]) and (fl["dst_function_id"] in live or fl["dst_port_id"])]
    pick = lambda f: {k: f[k] for k in ("id", "number", "text", "level", "parent_id", "position", "ftype", "critical")}
    return {"primary": pick(primary) if primary else None,
            "views": {v: [pick(f) for f in sorted(view_nodes[v].values(), key=lambda f: (f["level"], f["position"]))] for v in VIEWS},
            "secondaries": [pick(f) for f in sorted(view_nodes["general"].values(), key=lambda f: f["position"])],
            "ports": ports, "flows": flows,
            "positions": [dict(r) for r in conn.execute("SELECT view, function_id, port_id, x, y FROM diamond_positions WHERE project_id = ?", (pid,))],
            "checks": checks(view_nodes, items, ports, flows),
            **_parts(conn, pid, view_nodes),
            "labels": {"views": VIEWS, "kinds": KINDS, "sides": SIDES, "part_kinds": parts.KINDS}}


def _parts(conn, pid, view_nodes):
    """0.60.20 (D-O-031): the parts on the functions, and what the allocation says about the architecture."""
    found = parts.rows(conn, pid, parts.taggable(view_nodes))
    part_checks, stats = parts.analysis(found, view_nodes)
    return {"parts": found, "part_checks": part_checks, "part_stats": stats}


def _log(ctx, action, table, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, table, oid, details, ctx.ip)


def api_get(ctx):
    return payload(ctx.conn, F.access(ctx))


def _port(ctx, pid, oid=None):
    oid = oid if oid is not None else validate.int_param(ctx.params, "oid")
    row = ctx.conn.execute("SELECT * FROM diamond_ports WHERE id = ? AND project_id = ?", (oid, pid)).fetchone()
    if row is None:
        raise ApiError(404, "Entrée ou sortie introuvable dans ce Space. Correctif : rechargez la page.")
    return dict(row)


def add_port(conn, pid, side, label, kind):
    if conn.execute("SELECT COUNT(*) FROM diamond_ports WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_PORTS:
        raise ApiError(409, "{} entrées et sorties au maximum. Correctif : regroupez-les (ex. « Commandes de l'utilisateur »).".format(MAX_PORTS))
    pos = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM diamond_ports WHERE project_id = ? AND side = ?", (pid, side)).fetchone()[0]
    return conn.execute("INSERT INTO diamond_ports (project_id, side, label, kind, position, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (pid, side, label, kind, pos, db.utc_now())).lastrowid


def api_port_create(ctx):
    pid = F.access(ctx, "editor")
    side = _choice(ctx.body, "side", SIDES, "Côté")
    oid = add_port(ctx.conn, pid, side, _text(ctx.body, "label", "Nom", 80), _choice(ctx.body, "kind", KINDS, "Type de flux", "energy"))
    _log(ctx, "diamond_port_create", "diamond_ports", oid, {"side": side, "label": ctx.body.get("label")})
    return payload(ctx.conn, pid)


def api_port_update(ctx):
    pid = F.access(ctx, "editor")
    row = _port(ctx, pid)
    changes = {}
    if "label" in ctx.body:
        changes["label"] = _text(ctx.body, "label", "Nom", 80)
    if "kind" in ctx.body:
        changes["kind"] = _choice(ctx.body, "kind", KINDS, "Type de flux")
    if "side" in ctx.body:
        changes["side"] = _choice(ctx.body, "side", SIDES, "Côté")
        if changes["side"] != row["side"] and ctx.conn.execute(
                "SELECT 1 FROM diamond_flows WHERE src_port_id = ? OR dst_port_id = ?", (row["id"], row["id"])).fetchone():
            raise ApiError(409, "« {} » a déjà des flux : une entrée ne devient pas une sortie. Correctif : effacez ses flux, ou "
                                "créez une nouvelle sortie.".format(row["label"]))
    if changes:
        ctx.conn.execute("UPDATE diamond_ports SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)), list(changes.values()) + [row["id"]])
        _log(ctx, "diamond_port_update", "diamond_ports", row["id"], changes)
    return payload(ctx.conn, pid)


def api_port_delete(ctx):
    pid = F.access(ctx, "editor")
    row = _port(ctx, pid)
    n = ctx.conn.execute("SELECT COUNT(*) FROM diamond_flows WHERE src_port_id = ? OR dst_port_id = ?", (row["id"], row["id"])).fetchone()[0]
    ctx.conn.execute("DELETE FROM diamond_ports WHERE id = ?", (row["id"],))  # its flows and positions go with it (CASCADE)
    _log(ctx, "diamond_port_delete", "diamond_ports", row["id"], {"label": row["label"], "flows": n})
    return payload(ctx.conn, pid)


def _end(conn, pid, view, body, side):
    """{"type": "function" | "port", "id": n} -> (function_id, port_id), checked against the view and the side."""
    end = body.get(side) or {}
    kind, oid = str(end.get("type") or ""), end.get("id")
    try:
        oid = int(oid)
    except (TypeError, ValueError):
        raise ApiError(400, "Extrémité « {} » du flux manquante. Correctif : choisissez une fonction, une entrée ou une sortie.".format(side))
    if kind == "port":
        row = conn.execute("SELECT * FROM diamond_ports WHERE id = ? AND project_id = ?", (oid, pid)).fetchone()
        if row is None:
            raise ApiError(400, "Entrée ou sortie introuvable. Correctif : rechargez la page.")
        if (side == "src") != (row["side"] == "in"):
            raise ApiError(409, "« {} » est une {} : un flux part d'une entrée et arrive à une sortie. Correctif : inversez le "
                                "sens.".format(row["label"], "entrée" if row["side"] == "in" else "sortie"))
        return None, oid
    if kind == "function":
        view_nodes, _items = nodes(conn, pid)
        f = view_nodes[view].get(oid)
        if f is None:
            raise ApiError(409, "Cette fonction n'est pas dans la {} : {}. Correctif : choisissez une fonction de la vue.".format(
                VIEWS[view].lower(), "les fonctions secondaires seulement" if view == "general"
                else "les fonctions tertiaires, sans les fonctions techniques"))
        return oid, None
    raise ApiError(400, "Type d'extrémité « {} » inconnu. Correctif : function ou port.".format(kind))


def add_flow(conn, pid, view, kind, label, src, dst):
    if conn.execute("SELECT COUNT(*) FROM diamond_flows WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_FLOWS:
        raise ApiError(409, "{} flux au maximum par Space.".format(MAX_FLOWS))
    return conn.execute(
        "INSERT INTO diamond_flows (project_id, view, kind, label, src_function_id, src_port_id, dst_function_id, dst_port_id, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (pid, view, kind, label) + src + dst + (db.utc_now(),)).lastrowid


def api_flow_create(ctx):
    pid = F.access(ctx, "editor")
    body = ctx.body
    view = _choice(body, "view", VIEWS, "Vue")
    src, dst = _end(ctx.conn, pid, view, body, "src"), _end(ctx.conn, pid, view, body, "dst")
    if src == dst:
        raise ApiError(400, "Un flux relie deux éléments différents. Correctif : choisissez une autre cible.")
    if src[1] and dst[1]:
        raise ApiError(409, "Un flux qui va d'une entrée directement à une sortie ne traverse aucune fonction. Correctif : "
                            "faites-le passer par la fonction qui le traite.")
    kind = _choice(body, "kind", KINDS, "Type de flux", "energy")
    oid = add_flow(ctx.conn, pid, view, kind, _text(body, "label", "Libellé du flux", 60, required=False), src, dst)
    _log(ctx, "diamond_flow_create", "diamond_flows", oid, {"view": view, "kind": kind, "label": body.get("label")})
    return payload(ctx.conn, pid)


def _flow(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_flows WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "oid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Flux introuvable dans ce Space. Correctif : rechargez la page.")
    return dict(row)


def api_flow_update(ctx):
    pid = F.access(ctx, "editor")
    row = _flow(ctx, pid)
    changes = {}
    if "kind" in ctx.body:
        changes["kind"] = _choice(ctx.body, "kind", KINDS, "Type de flux")
    if "label" in ctx.body:
        changes["label"] = _text(ctx.body, "label", "Libellé du flux", 60, required=False)
    if changes:
        ctx.conn.execute("UPDATE diamond_flows SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)), list(changes.values()) + [row["id"]])
        _log(ctx, "diamond_flow_update", "diamond_flows", row["id"], changes)
    return payload(ctx.conn, pid)


def api_flow_delete(ctx):
    pid = F.access(ctx, "editor")
    row = _flow(ctx, pid)
    ctx.conn.execute("DELETE FROM diamond_flows WHERE id = ?", (row["id"],))
    _log(ctx, "diamond_flow_delete", "diamond_flows", row["id"], {"view": row["view"], "label": row["label"]})
    return payload(ctx.conn, pid)


def api_position(ctx):
    """{view, node: {type, id}, x, y}: where a box was dropped (no journal line per drag: positions are layout only)."""
    pid = F.access(ctx, "editor")
    body = ctx.body
    view = _choice(body, "view", VIEWS, "Vue")
    node = body.get("node") or {}
    if node.get("type") == "port":
        port = _port(ctx, pid, int(node.get("id") or 0))["id"]
        fid = None
    else:
        fid, port = _end(ctx.conn, pid, view, {"src": node}, "src")
    try:
        x, y = max(0.0, min(float(body.get("x")), 6000.0)), max(0.0, min(float(body.get("y")), 6000.0))
    except (TypeError, ValueError):
        raise ApiError(400, "Position invalide. Correctif : x et y en pixels.")
    ctx.conn.execute("DELETE FROM diamond_positions WHERE project_id = ? AND view = ? AND function_id IS ? AND port_id IS ?", (pid, view, fid, port))
    ctx.conn.execute("INSERT INTO diamond_positions (project_id, view, function_id, port_id, x, y) VALUES (?, ?, ?, ?, ?, ?)",
                     (pid, view, fid, port, round(x, 1), round(y, 1)))
    return {"ok": True}


def api_reset_layout(ctx):
    pid = F.access(ctx, "editor")
    view = _choice(ctx.body, "view", VIEWS, "Vue")
    n = ctx.conn.execute("DELETE FROM diamond_positions WHERE project_id = ? AND view = ?", (pid, view)).rowcount
    _log(ctx, "diamond_layout_reset", "projects", pid, {"view": view, "positions": n})
    return payload(ctx.conn, pid)
