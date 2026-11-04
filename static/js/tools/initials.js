/* Traceability key (D-B-058): nobody changes anything before setting his
   3-letter initials. api.js asks DA.needsInitials() before every write; when
   they are missing (or the server answers 428), a warning is shown and the
   settings open in a NEW tab, on the empty box. Back on this tab, the
   initials are re-read as soon as the window regains focus: the person just
   redoes the action. A banner stays at the top of the page meanwhile. */
(function () {
  "use strict";

  const { el, api, toast } = DA;
  const VALID = /^[A-Z]{3}$/;
  const FREE = /^\/api\/(me\/prefs|privacy\/event|logout|login|me\/password)(\?|$)/;
  let banner = null;
  let lastPrompt = 0;
  let waiting = false;
  let closePrompt = null;  // only our own dialog is closed: a form the person was filling stays open

  const has = () => VALID.test((DA.prefs && DA.prefs().initials) || "");

  DA.needsInitials = function (method, url) {
    if (method === "GET" || FREE.test(url)) return false;
    if (!DA.session || !DA.session.user || DA.session.user.must_change_password) return false;
    return !has();
  };

  function settingsUrl() {
    return location.pathname + "#/settings/initials";
  }

  function openSettings() {
    const tab = window.open(settingsUrl(), "_blank");
    waiting = true;
    return !!tab;
  }

  /* Called by api.js (before a write, or on a 428 answer). One prompt per 4 s at most. */
  DA.onInitialsMissing = function () {
    if (Date.now() - lastPrompt < 4000) return;
    lastPrompt = Date.now();
    if (location.hash.indexOf("#/settings") === 0) {  // already on the settings: focus the box
      const box = document.getElementById("set-initials");
      if (box) { box.scrollIntoView({ block: "center" }); box.focus(); }
      toast("Saisissez d'abord vos initiales (3 lettres).", "error");
      return;
    }
    const opened = openSettings();
    const body = el("div", { class: "form" },
      el("p", null, "Avant toute modification, définissez votre clé de traçabilité : vos initiales de 3 lettres "
        + "(ex. JDE). Elles signent chacun de vos changements."),
      el("p", { class: "muted" }, opened
        ? "Les Paramètres viennent de s'ouvrir dans un nouvel onglet, sur la case à remplir. Revenez ensuite ici "
          + "et refaites votre action : rien n'a été enregistré."
        : "Votre navigateur a bloqué l'ouverture automatique : utilisez le bouton ci-dessous."),
      el("div", { class: "form-actions" },
        el("a", { class: "btn btn-primary", href: settingsUrl(), target: "_blank", rel: "noopener",
          onclick: () => { waiting = true; } }, "Ouvrir les Paramètres (nouvel onglet)")));
    closePrompt = DA.modal("Initiales requises", body);
  };

  /* Back from the settings tab: re-read the preferences. */
  async function refresh() {
    if (!DA.session || !DA.session.user) return;
    try {
      const res = await api.get("/api/me/prefs");
      DA.applyPrefs(res.prefs);
      DA.session.prefs = res.prefs;
      DA.initialsChanged();
      if (waiting && has()) {
        waiting = false;
        if (closePrompt) { closePrompt(); closePrompt = null; }
        toast("Initiales « " + res.prefs.initials + " » enregistrées : vous pouvez refaire votre action.", "success");
      }
    } catch (err) { /* offline: the next write will ask again */ }
  }
  window.addEventListener("focus", () => { if (waiting || !has()) refresh(); });

  /* Banner at the top of every screen while the key is missing. */
  DA.initialsChanged = function () {
    const missing = DA.session && DA.session.user && !DA.session.user.must_change_password && !has();
    if (!missing) { if (banner) { banner.remove(); banner = null; } return; }
    if (banner && document.body.contains(banner)) return;
    banner = el("div", { class: "initials-banner", role: "status" },
      el("strong", null, "Initiales requises. "),
      "Définissez votre clé de traçabilité de 3 lettres avant de modifier quoi que ce soit. ",
      el("a", { href: settingsUrl(), target: "_blank", rel: "noopener", onclick: () => { waiting = true; } },
        "Ouvrir les Paramètres (nouvel onglet)"));
    document.body.prepend(banner);
  };
})();
