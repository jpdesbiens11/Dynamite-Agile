/* Admin → Spaces → « Copier / composer un Space » (core lot v0.27, D-B-099).
   Always a NEW Space: for each tab, the Space its content comes from, or « Vide (comme un Space neuf) »; Testing can
   also start from the reference catalogue. « Revoir » shows what will be copied; « Créer le Space » does it in one go. */
(function () {
  "use strict";
  const { api, el, field, toast, modal, clear } = DA;

  async function open(onDone) {
    let data;
    try { data = await api.get("/api/admin/spacecopy"); } catch (err) { toast(err.message, "error"); return; }
    const key = el("input", { type: "text", maxlength: 10, required: true, autocomplete: "off", placeholder: "PRJ4" });
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    const name = el("input", { type: "text", maxlength: 100, required: true, autocomplete: "off" });
    const description = el("input", { type: "text", maxlength: 500, autocomplete: "off" });
    const selects = {};
    data.parts.forEach(({ part }) => {
      const first = part === "testing" ? [["TESTING", "Catalogue de référence (TESTING)"]]
        : [["", part === "members" ? "Aucun (vous seul, Admin du Space)" : "Vide (comme un Space neuf)"]];
      const spaces = data.spaces.filter((s) => !(part === "testing" && s.key === "TESTING")).map((s) => [s.key, s.key + " · " + s.name]);
      selects[part] = el("select", { "aria-label": part }, first.concat(spaces).map(([v, l]) => el("option", { value: v }, l)));
    });
    const summary = el("div", { class: "sc-summary", "aria-live": "polite" });
    const body = () => ({ key: key.value.trim(), name: name.value.trim(), description: description.value.trim(),
      parts: Object.fromEntries(Object.entries(selects).map(([p, s]) => [p, s.value])) });
    const create = el("button", { type: "submit", class: "btn btn-primary", disabled: true }, "Créer le Space");
    Object.values(selects).concat([key]).forEach((i) => i.addEventListener("change", () => { create.disabled = true; clear(summary); }));
    let close = null;
    const form = el("form", { class: "form sc-form", onsubmit: async (ev) => {
      ev.preventDefault();
      create.disabled = true;
      try {
        const made = await api.post("/api/admin/spacecopy", body());
        close();
        toast("Space " + made.project.key + " créé" + (made.lost_links ? " (" + made.lost_links + " lien(s) vers du contenu non copié vidé(s))" : "") + ".", "success");
        onDone(made);
      } catch (err) { toast(err.message, "error"); create.disabled = false; }
    } },
    el("p", { class: "muted" }, "Crée toujours un NOUVEAU Space ; aucun Space existant n'est modifié. Pour chaque onglet, choisissez "
      + "le Space dont le contenu est le plus à jour. Les liens vers du contenu non copié sont vidés (comptés au résumé)."),
    el("div", { class: "form-row" }, field("Clé du nouveau Space", key), field("Nom", name), field("Description", description)),
    el("div", { class: "sc-grid" }, data.parts.map(({ part, label }) => field(label, selects[part]))),
    summary,
    el("div", { class: "form-actions" },
      el("button", { type: "button", class: "btn", onclick: async () => {
        try {
          const r = await api.post("/api/admin/spacecopy", Object.assign(body(), { mode: "preview" }));
          clear(summary);
          summary.append(el("h3", null, "Résumé — " + r.key + " · " + r.name),
            DA.table(["Onglet", "Source", "Contenu"], r.summary.map((s) => el("tr", null, el("td", null, s.label),
              el("td", null, s.source || "—"), el("td", null, s.detail)))));
          create.disabled = !name.value.trim();
        } catch (err) { toast(err.message, "error"); }
      } }, "Revoir"), create));
    close = modal("Copier / composer un Space", form);
  }

  DA.spaceCopy = {
    button(onDone) {
      return el("button", { type: "button", class: "btn", "data-new": "0.50.0-space-copy", onclick: () => open(onDone) },
        "Copier / composer un Space…");
    },
  };
})();
