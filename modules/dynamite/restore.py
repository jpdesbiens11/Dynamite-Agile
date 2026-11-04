"""Dynamite after a project restore (core lot v0.10, D-B-030).

Page bodies are JSON documents that name images by attachment id and
tickets by key: once core/backup.py has copied the rows under new ids,
the bodies of the restored versions point to the new attachments and, if
the project key changed, to the new ticket keys.
"""
import json


def _fix(node, images, old_key, new_key):
    if isinstance(node, list):
        return any([_fix(item, images, old_key, new_key) for item in node])
    if not isinstance(node, dict):
        return False
    changed = False
    if node.get("type") == "image" and node.get("id") in images:
        node["id"] = images[node["id"]]
        changed = True
    if node.get("type") == "ticket" and old_key != new_key and str(node.get("key", "")).startswith(old_key + "-"):
        node["key"] = new_key + node["key"][len(old_key):]
        changed = True
    for value in node.values():
        if isinstance(value, (list, dict)) and _fix(value, images, old_key, new_key):
            changed = True
    return changed


def on_restore(conn, maps, old_key, new_key):
    images = maps.get("attachments", {})
    version_ids = list(maps.get("dynamite_versions", {}).values())
    for vid in version_ids:
        row = conn.execute("SELECT body FROM dynamite_versions WHERE id = ?", (vid,)).fetchone()
        if not row:
            continue
        try:
            body = json.loads(row["body"])
        except ValueError:
            continue
        if _fix(body, images, old_key, new_key):
            conn.execute("UPDATE dynamite_versions SET body = ? WHERE id = ?", (json.dumps(body, ensure_ascii=False), vid))
