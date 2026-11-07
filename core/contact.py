"""0.60.74 (D-O-080): the contact form of the project's WEBSITE (dynamiteagile.ca, GitHub Pages) -- never in the tool.

The website cannot send e-mail (static pages), so its form posts to one public instance of the tool, the demo, which
forwards the request to the author with its own SMTP server (core/mail.py). Off by default; in Admin → Plateforme →
Courriel the administrator of that instance turns it on, types the recipient (never written in the code, never shown
on the site) and the address of the website allowed to post (CORS: that origin only, this route only).

The person never learns the recipient's address; the e-mail has Reply-To = the person's address, so the author
answers from his own mailbox. No confirmation e-mail is sent (the form would become a way to mail strangers).
Spam: a hidden field (« website ») that people never fill, 3 requests per hour per IP address, 30 per day in all.
"""
import threading
import time

from . import audit, mail
from .errors import ApiError

TOPICS = {"question": ("Question sur l'outil", "Question about the tool"),
          "install": ("Installation", "Installation"),
          "partner": ("Collaboration ou partenariat", "Collaboration or partnership"),
          "course": ("Cours ou formation", "Course or training"),
          "other": ("Autre", "Other")}
PER_IP_HOUR = 3
PER_DAY = 30
_hits, _day = {}, []
_lock = threading.Lock()

THANKS = {"fr": "Merci ! Votre demande est envoyée. Vous aurez une réponse à votre courriel d'ici 7 jours ouvrables.",
          "en": "Thank you! Your request is sent. You will get an answer at your e-mail within 7 business days."}


def allowed_origin(data_dir, origin):
    """The Origin header of the website when the form is on and this origin is the one set in Admin, else None."""
    cfg = mail.load(data_dir)
    want = (cfg.get("contact_origin") or "").rstrip("/")
    if cfg.get("contact_enabled") and want and origin and origin.rstrip("/") == want:
        return want
    return None


def cors_headers(data_dir, origin):
    ok = allowed_origin(data_dir, origin)
    if not ok:
        return {}
    return {"Access-Control-Allow-Origin": ok, "Vary": "Origin", "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600",
            "Cross-Origin-Resource-Policy": "cross-origin"}


def _rate(ip, lang):
    now = time.time()
    with _lock:
        recent = [t for t in _hits.get(ip, []) if now - t < 3600]
        _day[:] = [t for t in _day if now - t < 86400]
        if len(recent) >= PER_IP_HOUR or len(_day) >= PER_DAY:
            raise ApiError(429, "Trop de demandes pour l'instant. Correctif : réessayez plus tard." if lang == "fr"
                           else "Too many requests for now. Fix: try again later.")
        recent.append(now)
        _hits[ip] = recent
        _day.append(now)


def _field(body, key, limit, required, lang, label):
    value = body.get(key, "")
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise ApiError(400, ("Champ requis : " if lang == "fr" else "Required field: ") + label)
    if len(value) > limit:
        raise ApiError(400, ("Trop long : " if lang == "fr" else "Too long: ") + label)
    return value


def api_contact(ctx):
    body = ctx.body
    lang = "en" if body.get("lang") == "en" else "fr"
    if not allowed_origin(ctx.data_dir, ctx.origin):
        raise ApiError(403, "Formulaire de contact fermé." if lang == "fr" else "Contact form closed.")
    if body.get("website"):  # the hidden field: a robot filled it; it is told « sent » and nothing leaves
        return {"ok": True, "message": THANKS[lang]}
    _rate(ctx.ip, lang)
    fr = lang == "fr"
    name = _field(body, "name", 120, True, lang, "nom" if fr else "name")
    try:
        email = mail.clean_email(body.get("email"), required=True)
    except ApiError:
        raise ApiError(400, "Courriel invalide : une adresse comme prenom@exemple.ca est attendue." if fr
                       else "Invalid e-mail: an address like firstname@example.com is expected.")
    org = _field(body, "organization", 160, False, lang, "organisation" if fr else "organization")
    topic = body.get("topic") if body.get("topic") in TOPICS else "other"
    text = _field(body, "message", 5000, True, lang, "message")
    cfg = mail.load(ctx.data_dir)
    if not cfg.get("contact_to"):
        raise ApiError(503, "Formulaire de contact non configuré." if fr else "Contact form not configured.")
    subject = "[DynamiteAgile] {} — {}".format(TOPICS[topic][0], name)[:200]
    lines = ["Demande reçue par le formulaire du site / Request from the website form", "",
             "Nom / Name : " + name, "Courriel / E-mail : " + email, "Organisation : " + (org or "—"),
             "Sujet / Topic : " + TOPICS[topic][0], "Langue / Language : " + lang, "Adresse IP : " + str(ctx.ip), "",
             "— Message —", "", text, "", "Répondre à ce courriel écrit directement à la personne (Reply-To).",
             "À répondre d'ici 7 jours ouvrables (promis sur le site)."]
    mail.send(ctx.data_dir, cfg["contact_to"], subject, "\n".join(lines), reply_to=email)
    audit.log_action(ctx.conn, None, "contact_request", "contact", None, {"topic": topic, "lang": lang}, ctx.ip)
    return {"ok": True, "message": THANKS[lang]}


api_contact.cors = True  # the router answers the OPTIONS request and adds the CORS headers for the allowed origin only

ROUTES = [("POST", r"/api/contact", api_contact, "public")]
