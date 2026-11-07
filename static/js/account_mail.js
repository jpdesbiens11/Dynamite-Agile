/* 0.60.73 (D-O-079): « Mot de passe oublié ? » under the sign-in form, the « Nouveau mot de passe » card opened by the
   e-mailed link (https://<tool>/#reset=<token>: a fragment, never sent to the server nor in a Referer), and
   « Courriel de récupération » from the menu at one's name. The server decides everything (core/password_reset.py,
   core/mail.py); written in French, translated on screen by the display dictionary like the other screens. */
(function () {
  "use strict";
  const { api, el, field, modal, toast } = DA;

  /** The link under « Se connecter », only when the administrator turned the e-mail on (GET /api/about). */
  DA.forgotLink = function (about) {
    if (!about || !about.mail_reset) return null;
    return el("p", { class: "auth-note forgot-link", "data-new": "0.60.73-forgot" },
      el("button", { type: "button", class: "link-btn", onclick: openForgot }, "Mot de passe oublié ?"));
  };

  function openForgot() {
    const login = el("input", { type: "text", autocomplete: "username", required: true, maxlength: 254 });
    const error = el("p", { class: "form-error", role: "alert" });
    const done = el("p", { class: "form-ok", role: "status" });
    const submit = el("button", { type: "submit", class: "btn btn-primary" }, "Envoyer le lien");
    const form = el("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        error.textContent = "";
        done.textContent = "";
        submit.disabled = true;
        try {
          done.textContent = (await api.post("/api/password/forgot", { login: login.value.trim() })).message;
        } catch (err) {
          error.textContent = err.message;
          submit.disabled = false;
        }
      },
    },
      el("p", { class: "muted" }, "Tapez votre identifiant ou votre courriel : un lien pour choisir un nouveau mot de passe "
        + "part vers le courriel de votre compte."),
      field("Identifiant ou courriel", login), error, done,
      el("div", { class: "form-actions" }, submit));
    modal("Mot de passe oublié", form);
    login.focus();
  }

  /** The token of an e-mailed link, or null. */
  DA.resetToken = function () {
    const match = /^#reset=([A-Za-z0-9_-]{20,100})$/.exec(location.hash || "");
    return match ? match[1] : null;
  };

  /** The « Nouveau mot de passe » card. onDone(): back to the sign-in page. */
  DA.showReset = async function (root, token, brand, onDone) {
    const forget = () => history.replaceState(null, "", location.pathname + location.search);  // the token leaves the address bar
    root.replaceChildren();
    let username = "";
    try {
      username = (await api.post("/api/password/reset/check", { token })).username;  // 0.60.76: never in an address
    } catch (err) {
      forget();
      root.append(el("main", { class: "auth-page" }, el("div", { class: "auth-card", "data-new": "0.60.73-reset" }, brand(),
        el("h1", { class: "auth-title" }, "Lien expiré"), el("p", { class: "form-error", role: "alert" }, err.message),
        el("button", { type: "button", class: "btn btn-primary btn-block", onclick: () => onDone() }, "Retour à la connexion"))));
      return;
    }
    const next = el("input", { type: "password", autocomplete: "new-password", required: true, minlength: 12 });
    const again = el("input", { type: "password", autocomplete: "new-password", required: true });
    const error = el("p", { class: "form-error", role: "alert" });
    const submit = el("button", { type: "submit", class: "btn btn-primary btn-block" }, "Enregistrer le mot de passe");
    const form = el("form", {
      class: "auth-card", "data-new": "0.60.73-reset",
      onsubmit: async (ev) => {
        ev.preventDefault();
        error.textContent = "";
        if (next.value.length < 12) { error.textContent = "Au moins 12 caractères."; return; }
        if (next.value !== again.value) { error.textContent = "Les deux mots de passe diffèrent."; return; }
        submit.disabled = true;
        try {
          await api.post("/api/password/reset", { token, new_password: next.value });
          forget();
          toast("Mot de passe changé : connectez-vous avec le nouveau.", "success");
          onDone(username);
        } catch (err) {
          error.textContent = err.message;
          submit.disabled = false;
        }
      },
    },
      brand(),
      el("h1", { class: "auth-title" }, "Nouveau mot de passe"),
      el("p", { class: "muted" }, "Compte : ", el("strong", null, username)),
      el("input", { type: "text", autocomplete: "username", value: username, hidden: true, readonly: true }),  // password managers
      field("Nouveau mot de passe", next, "12 caractères minimum, sans votre identifiant."),
      field("Confirmer le mot de passe", again),
      error, submit,
      el("p", { class: "auth-note" }, "Toutes les sessions ouvertes de ce compte seront fermées."));
    root.append(el("main", { class: "auth-page" }, form));
    next.focus();
  };

  /** Menu at one's name → « Courriel de récupération ». */
  async function openMine() {
    let data;
    try { data = await api.get("/api/me/email"); } catch (err) { toast(err.message, "error"); return; }
    const input = el("input", { type: "text", inputmode: "email", spellcheck: "false", maxlength: 254, value: data.email || "", autocomplete: "email",
      placeholder: "prenom@exemple.ca" });
    let close = null;
    const form = el("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          await api.put("/api/me/email", { email: input.value.trim() });
          toast(input.value.trim() ? "Courriel enregistré." : "Courriel retiré.", "success");
          close();
        } catch (err) { toast(err.message, "error"); }
      },
    },
      field("Courriel de récupération", input, "Si vous oubliez votre mot de passe, « Mot de passe oublié ? » envoie un lien à cette adresse."),
      data.reset_ready ? null : el("p", { class: "muted" }, "La récupération par courriel n'est pas encore activée par l'administrateur "
        + "(Admin → Courriel) : votre adresse servira dès qu'elle le sera."),
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Courriel de récupération", form);
    input.focus();
  }

  DA.accountMail = { open: openMine };
})();
