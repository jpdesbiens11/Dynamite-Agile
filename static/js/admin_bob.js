/* ⚙ Admin → « Bob (agent IA) » (0.60.36, D-O-044): the keys of Bob le mineur, the AI agent of the team that lives
   outside the platform (Telegram) and answers with pointer links. Make a key for chosen Spaces (shown once),
   copy the guide for the agent (persona + the read-only API, this server's address filled in), see each key's last use,
   revoke a key. Every write is journalled by the server. */
(function () {
  "use strict";
  const { api, el, clear, toast, modal, table, formatDate } = DA;

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast("Copié.", "success"); }
    catch (err) { toast("Copie impossible ici : sélectionnez le texte et faites Ctrl+C.", "info"); }
  }

  function showToken(token, guide) {
    const box = el("textarea", { class: "bob-token", readonly: true, rows: 2, "aria-label": "Clé de l'agent" }, token);
    modal("Clé de Bob — elle ne s'affichera plus", el("div", { class: "bob-once" },
      el("p", null, "Copiez-la maintenant dans la configuration de l'agent, comme variable d'environnement ",
        el("code", null, "DA_BOT_TOKEN"), ". Elle ne sera plus jamais montrée ; perdue, on la révoque et on en crée une autre."),
      box,
      el("div", { class: "actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: () => copy(token) }, "Copier la clé"),
        el("button", { type: "button", class: "btn", onclick: () => copy(guide) }, "Copier la fiche de Bob")),
      el("p", { class: "muted" }, "Ne la collez jamais dans une conversation, un courriel ou un ticket.")));
    box.select();
  }

  function tokensTable(data, redraw) {
    if (!data.tokens.length) return el("p", { class: "muted" }, "Aucune clé encore.");
    return table(["Nom", "Clé", "Spaces", "Créée", "Dernier appel", "Appels", ""], data.tokens.map((t) => el("tr", null, [
      t.name, el("code", null, t.prefix + "…"), t.spaces.split(",").join(", "),
      formatDate ? formatDate(t.created_at) : t.created_at, t.last_used_at ? (formatDate ? formatDate(t.last_used_at) : t.last_used_at) : "—",
      String(t.uses),
      t.revoked_at ? DA.badge("Révoquée", "off") : el("button", { type: "button", class: "btn btn-small btn-danger", onclick: async () => {
        if (!window.confirm("Révoquer « " + t.name + " » ? Bob ne pourra plus lire l'outil avec cette clé.")) return;
        try { redraw(await api.post("/api/admin/bot/tokens/" + t.id + "/revoke", {})); toast("Clé révoquée.", "success"); }
        catch (err) { toast(err.message, "error"); }
      } }, "Révoquer")].map((c) => el("td", null, c)))));
  }

  async function render(body) {
    const [data, guide] = await Promise.all([api.get("/api/admin/bot/tokens"), api.get("/api/admin/bot/guide")]);
    const holder = el("div");
    const name = el("input", { type: "text", maxlength: 60, value: "Bob le mineur — Telegram", "aria-label": "Nom de la clé" });
    const boxes = data.spaces.map((s) => el("label", { class: "check" }, el("input", { type: "checkbox", value: s.key }), " " + s.key + " · " + s.name));
    const redraw = (fresh) => { clear(holder); holder.append(tokensTable(fresh, redraw)); };
    body.append(
      el("div", { class: "page-head", "data-new": "0.60.36-bob" }, el("h2", null, "Bob le mineur, l'agent IA de l'équipe"),
        el("p", { class: "muted" }, "Bob vit hors de la plateforme (sur ce serveur ou ailleurs) et parle à l'équipe dans "
          + "Telegram. Avec une clé, il lit les Spaces choisis — rien d'autre, sans jamais rien modifier — et répond par des liens "
          + "qui ouvrent la page et encadrent le point d'intérêt. La plateforme n'appelle jamais Bob : c'est lui qui appelle.")),
      el("section", { class: "bob-new" }, el("h3", null, "1. Créer une clé"),
        DA.field("Nom", name),
        el("fieldset", { class: "bob-spaces" }, el("legend", null, "Spaces que Bob peut lire"), boxes),
        el("button", { type: "button", class: "btn btn-primary bob-create", onclick: async () => {
          const spaces = boxes.map((b) => b.querySelector("input")).filter((i) => i.checked).map((i) => i.value);
          try {
            const res = await api.post("/api/admin/bot/tokens", { name: name.value, spaces });
            redraw(res);
            showToken(res.token, guide.text);
          } catch (err) { toast(err.message, "error"); }
        } }, "Créer la clé")),
      el("section", null, el("h3", null, "2. Donner à l'agent la fiche de Bob"),
        el("p", null, "La fiche dit qui est Bob (DynamiteAgile seulement), comment il parle et comment il lit l'outil. Collez-la "
          + "comme consigne du profil de Bob dans l'agent ; la clé va dans la variable ", el("code", null, "DA_BOT_TOKEN"), "."),
        el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: () => copy(guide.text) }, "Copier la fiche"),
          el("span", { class: "muted" }, " Adresse de ce serveur : " + guide.url)),
        el("details", null, el("summary", null, "Voir la fiche"), el("pre", { class: "bob-guide" }, guide.text))),
      el("section", null, el("h3", null, "3. Les clés"), holder,
        el("p", { class: "muted" }, "Au plus " + data.rate + " appels par minute par clé ; chaque appel est inscrit au journal d'audit (« bot_read »).")));
    redraw(data);
  }

  DA.adminBob = { render };
})();
