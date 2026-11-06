/* 0.60.63 (D-O-072): Admin → Comptes → Accès invité -- open the instance to visitors, read-only, and pick the Spaces. */
(function () {
  "use strict";
  const { api, el, clear, toast } = DA;

  async function render(body) {
    const data = await api.get("/api/admin/guest");
    clear(body);
    const g = data.guest;
    const chosen = new Set(g.projects.length ? g.projects : data.projects.filter((p) => p.key === "DEMO").map((p) => p.id));
    const onBox = el("input", { type: "checkbox", checked: g.enabled });
    const boxes = data.projects.map((p) => {
      const box = el("input", { type: "checkbox", value: String(p.id), checked: chosen.has(p.id) });
      return el("label", { class: "privacy-item" }, box, el("span", null, el("strong", null, p.key), el("span", { class: "muted" }, p.name)));
    });
    const save = el("button", { type: "button", class: "btn btn-primary" }, "Enregistrer");
    save.addEventListener("click", async () => {
      const projects = boxes.map((b) => b.querySelector("input")).filter((b) => b.checked).map((b) => Number(b.value));
      save.disabled = true;
      try {
        await api.put("/api/admin/guest", { enabled: onBox.checked, projects });
        toast(onBox.checked ? "Accès invité ouvert : « Entrer en invité » apparaît sur la page de connexion." : "Accès invité fermé ; les sessions invité sont terminées.", "success");
        render(body);
      } catch (err) { toast(err.message, "error"); save.disabled = false; }
    });
    body.append(
      el("div", { class: "page-head", "data-new": "0.60.63-guest" }, el("h2", null, "Accès invité"),
        el("p", { class: "muted" }, "Pour une instance publique (démo, publicité) : n'importe qui entre sans compte ni mot de passe, "
          + "en lecture seule, dans les Spaces cochés. L'invité consulte et exporte en PDF / Word ; il ne peut rien modifier, ni commenter.")),
      el("div", { class: "danger-box info-box" }, el("strong", null, "À savoir. "),
        "N'ouvrez pas l'accès invité sur le serveur d'une équipe qui contient du contenu confidentiel : tout ce qui est dans "
        + "les Spaces cochés devient visible par n'importe qui qui connaît l'adresse. Les visites sont inscrites au journal d'audit "
        + "(« guest_login ») et limitées à 30 par heure et par adresse IP."),
      el("label", { class: "privacy-item" }, onBox, el("span", null, el("strong", null, "Ouvrir l'accès invité"),
        el("span", { class: "muted" }, "Ajoute « Entrer en invité (lecture seule) » sous le formulaire de connexion."))),
      el("h3", null, "Spaces visibles par les invités"),
      el("div", { class: "privacy-list" }, boxes),
      el("p", { class: "muted" }, "Sessions invité ouvertes en ce moment : " + data.sessions + "."),
      el("div", { class: "form-actions" }, save));
  }

  DA.adminExtra = DA.adminExtra || {};
  DA.adminExtra.loaders = Object.assign(DA.adminExtra.loaders || {}, { guest: render });
})();
