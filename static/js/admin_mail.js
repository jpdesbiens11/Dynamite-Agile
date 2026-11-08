/* 0.60.73 (D-O-079): Admin → Plateforme → Courriel -- the SMTP server of « Mot de passe oublié ? » (off by default), a
   test message, and the « Courriel… » button of each account in Admin → Comptes. The SMTP password is write-only:
   the server never sends it back (has_password). */
(function () {
  "use strict";
  const { api, el, clear, field, modal, toast } = DA;

  const PRESETS = {
    gmail: { host: "smtp.gmail.com", port: 587, security: "starttls" },
    hostinger: { host: "smtp.hostinger.com", port: 465, security: "ssl" },
    outlook: { host: "smtp-mail.outlook.com", port: 587, security: "starttls" },
  };

  async function render(body) {
    const data = await api.get("/api/admin/mail");
    clear(body);
    const m = data.mail;
    const input = (value, attrs) => el("input", Object.assign({ type: "text", value: value == null ? "" : String(value), autocomplete: "off" }, attrs || {}));
    const on = el("input", { type: "checkbox", checked: m.enabled });
    const host = input(m.host, { placeholder: "smtp.gmail.com", maxlength: 253 });
    const port = input(m.port, { inputmode: "numeric", maxlength: 5 });
    const security = el("select", null, [["starttls", "STARTTLS (port 587)"], ["ssl", "SSL / TLS (port 465)"], ["none", "Aucune (relais local seulement)"]]
      .map(([v, label]) => el("option", { value: v, selected: m.security === v }, label)));
    const user = input(m.username, { placeholder: "compte@exemple.ca", maxlength: 254 });
    const pass = el("input", { type: "password", autocomplete: "new-password", maxlength: 256,
      placeholder: data.has_password ? "•••••••• (enregistré — laissez vide pour le garder)" : "Mot de passe du compte SMTP" });
    const sender = input(m.sender, { type: "text", inputmode: "email", spellcheck: "false", placeholder: "noreply@exemple.ca", maxlength: 254 });
    const name = input(m.sender_name, { maxlength: 80 });
    const url = input(m.public_url || data.suggested_url, { placeholder: "https://demo.exemple.ca", maxlength: 200 });
    /* 0.60.74 (D-O-080): the contact form of the project's website posts here; the recipient is never shown on the site */
    const cOn = el("input", { type: "checkbox", checked: !!m.contact_enabled });
    const cTo = input(m.contact_to, { inputmode: "email", spellcheck: "false", placeholder: "vous@exemple.ca", maxlength: 254 });
    const cOrigin = input(m.contact_origin, { placeholder: "https://votre-site.ca", maxlength: 200 });
    const preset = el("select", { onchange: () => {
      const p = PRESETS[preset.value];
      if (p) { host.value = p.host; port.value = p.port; security.value = p.security; }
    } }, el("option", { value: "" }, "Remplir pour…"), el("option", { value: "gmail" }, "Gmail"),
      el("option", { value: "hostinger" }, "Courriel Hostinger"), el("option", { value: "outlook" }, "Outlook / Microsoft 365"));
    const save = el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer");
    /* 0.60.80 (D-O-086): the port follows the encryption (it stayed at 587 with SSL / TLS: « wrong version number »), the
       test refuses changes not saved yet (it uses the saved settings), and a setup file fills the form at once */
    security.addEventListener("change", () => {
      const want = { starttls: "587", ssl: "465" }[security.value];
      if (want && ["", "25", "465", "587"].includes(port.value.trim())) port.value = want;
    });
    const fields = { host, port, security, username: user, sender, sender_name: name, public_url: url, contact_to: cTo,
      contact_origin: cOrigin };
    const checks = { enabled: on, contact_enabled: cOn };
    const state = () => JSON.stringify([Object.values(fields).map((f) => f.value.trim()), Object.values(checks).map((c) => c.checked), pass.value]);
    const saved = state();
    const load = el("input", { type: "file", accept: ".json,application/json", hidden: true });
    load.addEventListener("change", async () => {
      const file = load.files[0];
      load.value = "";
      if (!file) return;
      let setup;
      try { setup = JSON.parse(await file.text()); } catch (err) { toast("Fichier illisible : un réglage .json est attendu.", "error"); return; }
      if (!setup || typeof setup !== "object" || Array.isArray(setup)) { toast("Fichier illisible : un réglage .json est attendu.", "error"); return; }
      const mail = setup.mail && typeof setup.mail === "object" ? setup.mail : setup;
      let n = 0;
      Object.entries(fields).forEach(([k, f]) => { if (mail[k] != null && typeof mail[k] !== "object") { f.value = String(mail[k]); n += 1; } });
      Object.entries(checks).forEach(([k, c]) => { if (typeof mail[k] === "boolean") { c.checked = mail[k]; n += 1; } });
      toast(n + " réglage(s) chargé(s), jamais de mot de passe. Vérifiez" + (data.has_password ? "" : ", tapez le mot de passe SMTP")
        + ", puis Enregistrer.", "success");
    });
    const loadBtn = el("button", { type: "button", class: "btn", "data-new": "0.60.80-mail-setup", onclick: () => load.click() },
      "Charger un réglage…");
    const form = el("form", {
      class: "panel",
      onsubmit: async (ev) => {
        ev.preventDefault();
        save.disabled = true;
        try {
          const payload = { enabled: on.checked, host: host.value.trim(), port: Number(port.value), security: security.value,
            username: user.value.trim(), sender: sender.value.trim(), sender_name: name.value.trim(), public_url: url.value.trim(),
            contact_enabled: cOn.checked, contact_to: cTo.value.trim(), contact_origin: cOrigin.value.trim() };
          if (pass.value) payload.password = pass.value;
          await api.put("/api/admin/mail", payload);
          toast(on.checked ? "Courriel activé : « Mot de passe oublié ? » apparaît sur la page de connexion." : "Réglages enregistrés (courriel coupé).", "success");
          render(body);
        } catch (err) { toast(err.message, "error"); save.disabled = false; }
      },
    },
      el("div", { class: "form-row" }, field("Fournisseur de courriel", preset, "Remplit l'hôte, le port et le chiffrement."),
        field("Ou un fichier", el("span", null, loadBtn, load), "Un réglage .json (sans mot de passe) : remplit tout le formulaire.")),
      el("div", { class: "form-row" }, field("Hôte SMTP", host), field("Port", port), field("Chiffrement", security)),
      el("div", { class: "form-row" }, field("Compte SMTP", user), field("Mot de passe SMTP", pass,
        "Gmail : un « mot de passe d'application » (Compte Google → Sécurité → Validation en deux étapes)."),
      data.has_password ? el("label", { class: "check" }, el("input", { type: "checkbox", onchange: async (ev) => {
        if (!ev.target.checked) return;
        try { await api.put("/api/admin/mail", { clear_password: true }); toast("Mot de passe SMTP effacé.", "success"); render(body); }
        catch (err) { toast(err.message, "error"); }
      } }), "Effacer le mot de passe enregistré") : null),
      el("div", { class: "form-row" }, field("Expéditeur", sender, "L'adresse « De : » des courriels."), field("Nom de l'expéditeur", name)),
      el("div", { class: "form-row" }, field("Adresse de l'outil", url, "Celle que voit l'équipe : les liens envoyés y mènent.")),
      el("label", { class: "privacy-item" }, on, el("span", null, el("strong", null, "Activer « Mot de passe oublié ? »"),
        el("span", { class: "muted" }, "Ajoute le lien sous le formulaire de connexion ; un lien à usage unique, valide 30 minutes, "
          + "part vers le courriel du compte."))),
      el("h3", { "data-new": "0.60.74-contact" }, "Formulaire de contact du site"),
      el("p", { class: "muted" }, "Le site web du projet (pages statiques) ne sait pas envoyer de courriel : son formulaire « Nous joindre » "
        + "passe par ce serveur, qui transmet la demande au destinataire. Réponse à la personne par « Répondre » (Reply-To)."),
      el("div", { class: "form-row" }, field("Destinataire des demandes", cTo, "Jamais affiché sur le site."),
        field("Adresse du site", cOrigin, "Seul ce site peut envoyer le formulaire (https://…, sans chemin).")),
      el("label", { class: "privacy-item" }, cOn, el("span", null, el("strong", null, "Ouvrir le formulaire de contact du site"),
        el("span", { class: "muted" }, "3 demandes par heure et par adresse IP, 30 par jour au total ; un champ caché arrête les robots."))),
      el("div", { class: "form-actions" }, save));

    const to = input(data.my_email, { type: "text", inputmode: "email", spellcheck: "false", placeholder: "vous@exemple.ca", maxlength: 254 });
    const testBtn = el("button", { type: "button", class: "btn" }, "Envoyer un courriel test");
    testBtn.addEventListener("click", async () => {
      if (state() !== saved) {
        toast("Enregistrez d'abord vos changements : le courriel test utilise les réglages enregistrés sur le serveur.", "error");
        return;
      }
      testBtn.disabled = true;
      try { toast("Courriel test envoyé à " + (await api.post("/api/admin/mail/test", { to: to.value.trim() })).to + ".", "success"); }
      catch (err) { toast(err.message, "error"); }
      finally { testBtn.disabled = false; }
    });

    body.append(
      el("div", { class: "page-head", "data-new": "0.60.73-mail" }, el("h2", null, "Courriel"),
        el("p", { class: "muted" }, "Sert seulement à « Mot de passe oublié ? » : la personne reçoit un lien pour choisir un nouveau "
          + "mot de passe, sans passer par un administrateur. Coupé par défaut.")),
      el("div", { class: "danger-box info-box" }, el("strong", null, "À savoir. "),
        "C'est la seule fois où le serveur sort sur Internet : vers le serveur SMTP réglé ici, et seulement pour envoyer ces liens. "
        + "Le mot de passe SMTP reste dans data/mail.json sur le serveur (jamais renvoyé à l'écran, jamais dans une sauvegarde de Space). "
        + "Comptes actifs avec un courriel : " + data.accounts_with_email + "."),
      form,
      el("div", { class: "panel" }, el("h3", null, "Essai"),
        el("div", { class: "form-row" }, field("Envoyer à", to), testBtn)));
  }

  /** The « Courriel… » button of an account in Admin → Comptes. */
  function emailButton(user, refresh) {
    return el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.73-user-email", onclick: () => {
      const input = el("input", { type: "text", inputmode: "email", spellcheck: "false", maxlength: 254, value: user.email || "", placeholder: "prenom@exemple.ca" });
      let close = null;
      const form = el("form", {
        onsubmit: async (ev) => {
          ev.preventDefault();
          try {
            await api.patch("/api/admin/users/" + user.id, { email: input.value.trim() });
            toast("Courriel mis à jour.", "success");
            close();
            refresh();
          } catch (err) { toast(err.message, "error"); }
        },
      }, field("Courriel", input, "Pour « Mot de passe oublié ? ». Vide : pas de récupération par courriel pour ce compte."),
        el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
      close = modal("Courriel — " + user.display_name, form);
      input.focus();
    } }, "Courriel…");
  }

  DA.adminMail = { emailButton };
  DA.adminExtra = DA.adminExtra || {};
  DA.adminExtra.loaders = Object.assign(DA.adminExtra.loaders || {}, { mail: render });
})();
