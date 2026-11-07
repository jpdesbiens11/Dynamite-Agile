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
    const preset = el("select", { onchange: () => {
      const p = PRESETS[preset.value];
      if (p) { host.value = p.host; port.value = p.port; security.value = p.security; }
    } }, el("option", { value: "" }, "Remplir pour…"), el("option", { value: "gmail" }, "Gmail"),
      el("option", { value: "hostinger" }, "Courriel Hostinger"), el("option", { value: "outlook" }, "Outlook / Microsoft 365"));
    const save = el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer");
    const form = el("form", {
      class: "panel",
      onsubmit: async (ev) => {
        ev.preventDefault();
        save.disabled = true;
        try {
          const payload = { enabled: on.checked, host: host.value.trim(), port: Number(port.value), security: security.value,
            username: user.value.trim(), sender: sender.value.trim(), sender_name: name.value.trim(), public_url: url.value.trim() };
          if (pass.value) payload.password = pass.value;
          await api.put("/api/admin/mail", payload);
          toast(on.checked ? "Courriel activé : « Mot de passe oublié ? » apparaît sur la page de connexion." : "Réglages enregistrés (courriel coupé).", "success");
          render(body);
        } catch (err) { toast(err.message, "error"); save.disabled = false; }
      },
    },
      el("div", { class: "form-row" }, field("Fournisseur de courriel", preset, "Remplit l'hôte, le port et le chiffrement.")),
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
      el("div", { class: "form-actions" }, save));

    const to = input(data.my_email, { type: "text", inputmode: "email", spellcheck: "false", placeholder: "vous@exemple.ca", maxlength: 254 });
    const testBtn = el("button", { type: "button", class: "btn" }, "Envoyer un courriel test");
    testBtn.addEventListener("click", async () => {
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
