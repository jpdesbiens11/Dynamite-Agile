"""API endpoints for the current user: login, logout, profile, password."""
import datetime as dt

from . import APP_DESCRIPTION, APP_NAME, APP_VERSION, audit, auth, devshare, guest, mail, modules, permissions, prefs, team
from .errors import ApiError


def _me_payload(conn, user_row, csrf, ip=None):
    prefs.ensure_initials(conn, user_row["id"])  # 0.60.19 (D-O-030): the key comes from the name
    return {
        "user": auth.public_user(user_row),
        "csrf": csrf,
        "projects": permissions.visible_projects(conn, user_row),
        "modules": modules.nav_manifest(),
        "prefs": prefs.get(conn, user_row["id"]),  # core lot v0.10
        "policy": prefs.policy(conn),
        "client_ip": ip,  # shown in the named watermark (D-B-029)
        "team": _team(conn, user_row["id"]),  # core lot v0.31 (D-B-112): « Mon équipe » in the account menu
    }


def _team(conn, user_id):
    size = len(team.team_of(conn, user_id))
    return {"size": size, "pending": team.pending_count(conn, user_id, dt.date.today().year) if size else 0}


def api_about(ctx):
    return {"name": APP_NAME, "version": APP_VERSION, "description": APP_DESCRIPTION,
            "dev_mode": bool(ctx.config.get("dev_mode")),
            "prefill": devshare.prefill(ctx.config, ctx.ip),  # D-B-091: admin / admin only on this computer
            "lan_share": bool(ctx.config.get("lan_share")),
            "guest": guest.enabled(ctx.conn),  # 0.60.63 (D-O-072): « Entrer en invité » on the sign-in page
            "mail_reset": mail.ready(ctx.data_dir)}  # 0.60.73 (D-O-079): « Mot de passe oublié ? »


def api_login(ctx):
    devshare.guard_login(ctx, ctx.body.get("username"))  # D-B-091
    token, csrf, user = auth.login(ctx.conn, ctx.body.get("username"),
                                   ctx.body.get("password"), ctx.ip, ctx.config)
    if ctx.client_cert:  # mTLS (D-B-090): the session only opens again from this certificate
        auth.bind_session_cert(ctx.conn, token, ctx.client_cert)
    ctx.set_session_cookie(token, int(float(ctx.config["session_hours"]) * 3600))
    return _me_payload(ctx.conn, user, csrf, ctx.ip)


def api_logout(ctx):
    auth.delete_session(ctx.conn, ctx.token)
    audit.log_action(ctx.conn, ctx.user["id"], "logout", "user", ctx.user["id"], None, ctx.ip)
    ctx.clear_session_cookie()
    return {"ok": True}


def api_me(ctx):
    return _me_payload(ctx.conn, ctx.user, ctx.user["csrf_token"], ctx.ip)


def api_change_password(ctx):
    user_id = ctx.user["id"]
    auth.change_password(ctx.conn, user_id, ctx.body.get("old_password"),
                         ctx.body.get("new_password"))
    auth.delete_user_sessions(ctx.conn, user_id, except_token=ctx.token)
    if ctx.user["username"] == auth.INITIAL_ADMIN_USERNAME:
        auth.remove_initial_password_file(ctx.data_dir)
    audit.log_action(ctx.conn, user_id, "password_changed", "user", user_id, None, ctx.ip)
    fresh = auth.get_session(ctx.conn, ctx.token)
    if fresh is None:
        raise ApiError(401, "Session expirée.")
    return _me_payload(ctx.conn, fresh, fresh["csrf_token"], ctx.ip)


def api_projects(ctx):
    return {"projects": permissions.visible_projects(ctx.conn, ctx.user)}


# Access levels: "public" (no login), "pending_ok" (allowed while a password
# change is required), "user" (any logged-in user), "admin".
ROUTES = [
    ("GET", r"/api/about", api_about, "public"),
    ("POST", r"/api/login", api_login, "public"),
    ("POST", r"/api/logout", api_logout, "pending_ok"),
    ("GET", r"/api/me", api_me, "pending_ok"),
    ("POST", r"/api/me/password", api_change_password, "pending_ok"),
    ("GET", r"/api/projects", api_projects, "user"),
]
