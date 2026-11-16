/* Diamond · a Pugh matrix for a group of bricks (0.60.105, D-O-117). The bricks judged together, the columns -- one per line,
   usually a combination of concept sheets written with their codes (« CB-1.2 + CB-3.1 »: the sheets are linked to the column);
   the first column is the reference (datum). The criteria arrive in order: the needs, the functions of the bricks (estime, base,
   performance) and the requirements of criticality A or B; the toolbar of the matrix adds others. */
(function () {
  "use strict";

  const { api, el, field, modal } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  function openPughCreate(ctx, data, sheets, preselect) {
    const bricks = data.concepts.filter((c) => c.kind === "to_define" || c.sheets);
    const boxes = bricks.map((c) => el("input", { type: "checkbox", value: c.id, checked: (preselect || []).includes(c.id) }));
    const title = el("input", { type: "text", maxlength: 200, placeholder: "ex. Architecture thermique du module" });
    const description = el("textarea", { rows: 2, maxlength: 4000, placeholder: "La question de conception à trancher" });
    const columns = el("textarea", { rows: 5, placeholder: "Une colonne par ligne (la première est la référence)\nCB-3.1 + CB-5.1\nCB-3.2 + CB-5.1" });
    const chosen = () => boxes.filter((b) => b.checked).map((b) => Number(b.value));
    const oneEach = () => {
      const ids = chosen();
      columns.value = sheets.filter((s) => ids.includes(s.concept_id) && s.status !== "dropped").map((s) => s.code + " " + s.title).join("\n");
    };
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      if (!chosen().length) { error.textContent = "Cochez au moins une brique à juger."; return; }
      try {
        const res = await api.post(D.base(ctx) + "/pugh", { title: title.value, description: description.value, concept_ids: chosen(),
          concepts: columns.value.split("\n").map((x) => x.trim()).filter(Boolean).map((x) => x.slice(0, 80)) });
        close();
        location.hash = A.href(ctx, "pugh/" + res.matrix.id);
      } catch (err) { error.textContent = err.message; }
    } }, field("Titre", title), field("Description", description),
    field("Briques jugées ensemble", bricks.length ? el("div", { class: "dm-cb-pick" }, bricks.map((c, i) => el("label", { class: "check" }, boxes[i],
      c.code + " " + c.name + " (" + c.sheets + " feuille" + (c.sheets > 1 ? "s" : "") + ")")))
      : el("p", { class: "muted" }, "Aucune brique à définir.")),
    field("Colonnes (options)", columns, "Écrivez les codes des feuilles (CB-3.1) : elles seront liées à la colonne et retenues quand la matrice sera décidée."),
    el("button", { type: "button", class: "btn btn-small", onclick: oneEach }, "Une colonne par feuille des briques cochées"),
    el("p", { class: "muted" }, "Critères ajoutés dans l'ordre : besoins, fonctions (estime, base, performance), requirements de criticité A et B."),
    error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer la matrice")));
    close = modal("Nouvelle matrice de Pugh", form);
    document.querySelectorAll(".modal").forEach((m) => m.classList.add("modal-wide"));
    title.focus();
  }

  D.openPughCreate = openPughCreate;
  /* « Nouvelle matrice » of the Pugh list opened from Diamond (static/js/agile/pugh.js calls it, never DA.diamond itself) */
  DA.agile.pughCreate = async (ctx) => {
    try {
      const [data, sheets] = await Promise.all([DA.api.get(D.base(ctx) + "/concepts"), DA.api.get(D.base(ctx) + "/sheets")]);
      openPughCreate(ctx, data, sheets.sheets);
    } catch (err) { DA.toast(err.message, "error"); }
  };
})();
