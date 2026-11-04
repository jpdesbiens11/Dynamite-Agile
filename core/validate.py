"""Small helpers to validate JSON request bodies and URL parameters."""
from .errors import ApiError


def text(body, name, max_len, required=True):
    """Return a stripped string field, enforcing presence and length."""
    value = body.get(name, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ApiError(400, "Champ invalide : {}.".format(name))
    value = value.strip()
    if required and not value:
        raise ApiError(400, "Champ requis : {}.".format(name))
    if len(value) > max_len:
        raise ApiError(400, "Champ trop long : {} (maximum {} caractères).".format(name, max_len))
    return value


def boolean(body, name, default=None):
    """Return a JSON boolean field; `default` is used when it is absent."""
    if name not in body:
        if default is None:
            raise ApiError(400, "Champ requis : {}.".format(name))
        return default
    value = body[name]
    if not isinstance(value, bool):
        raise ApiError(400, "Champ invalide : {} (vrai/faux attendu).".format(name))
    return value


def choice(body, name, options):
    """Return a string field that must be one of `options`."""
    value = body.get(name)
    if value not in options:
        raise ApiError(400, "Valeur invalide pour {}.".format(name))
    return value


def int_param(params, name):
    """Return an integer captured from the URL pattern."""
    try:
        return int(params[name])
    except (KeyError, TypeError, ValueError):
        raise ApiError(400, "Paramètre invalide : {}.".format(name))
