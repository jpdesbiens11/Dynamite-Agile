/* Diamond · the platform's catalogue of competencies (0.60.116, D-O-129), at the bottom of « Compétences et équipe »: every
   competency with its icon, its code, its summary and the link to its page in the « Base de connaissances (BDC) ». An
   administrator (or an « Admin du Space » of DEMO) adds one, changes its name, icon, summary or the content of its BDC page
   (background, training, tools, knowledge, artifacts), marks it as a starter column of a new Space
   (0.60.118, D-O-131), or deactivates it -- never deletes it. The editor is a page-wide form
   in a dialog (two columns, no scroll bar inside the dialog). */
(function () {
  "use strict";

  const { api, el, toast } = DA;
  const D = DA.diamond;

  function competencyCatalog(ctx, comp, reload) {
    const cards = comp.catalog.map((c) => el("li", { class: "dm-cc-item" + (c.active ? "" : " dm-cc-off") },
      D.compIcon(c.icon, "dm-cc-icon"),
      el("div", null, el("strong", null, c.name), el("span", { class: "dm-code" }, " " + c.code),
        c.active ? null : el("span", { class: "badge badge-off" }, "Désactivée"),
        c.starter ? el("span", { class: "badge badge-info", "data-new": "0.60.118-competency-starter",
          "data-tip": "Colonne de départ de la grille d'un nouveau Space" }, "Départ") : null,
        el("p", { class: "muted" }, c.summary || "—"),
        el("div", { class: "dm-cc-links" }, c.bdc ? el("a", { href: c.bdc }, "Page BDC →") : el("span", { class: "muted" }, "Page BDC à venir"),
          comp.can_manage ? el("button", { type: "button", class: "btn btn-small", onclick: () => editor(comp, c, reload) }, "Modifier") : null))));
    return el("section", { class: "dm-cb-section", "data-new": "0.60.116-competency-catalog" },
      el("div", { class: "dm-cc-head" }, el("h2", null, "Catalogue des compétences (" + comp.catalog.length + ")"),
        comp.can_manage ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => editor(comp, null, reload) },
          "Ajouter une compétence") : null),
      el("p", { class: "muted" }, "Commun à tous les Spaces. Chaque compétence a sa page dans la ",
        comp.bdc_hub ? el("a", { href: comp.bdc_hub }, "Base de connaissances (BDC)") : "Base de connaissances (BDC)",
        " : profil professionnel, formation, outils, connaissances supposées, livrables typiques."
        + (comp.can_manage ? "" : " Seul un administrateur modifie le catalogue.")),
      el("ul", { class: "dm-cc-list" }, cards));
  }

  function editor(comp, c, reload) {
    const isNew = !c;
    const d = (c && c.details) || {};
    const code = el("input", { type: "text", maxlength: 8, value: c ? c.code : "", disabled: isNew ? null : "disabled", placeholder: "ex. EMC",
      "aria-label": "Code" });
    const name = el("input", { type: "text", maxlength: 60, value: c ? c.name : "", placeholder: "ex. EMC design" });
    const summary = el("input", { type: "text", maxlength: 200, value: c ? c.summary : "", placeholder: "Ce que cette compétence apporte, en une phrase" });
    let icon = c ? c.icon : comp.icons[0];
    const icons = el("div", { class: "dm-cc-icons", role: "radiogroup", "aria-label": "Icône" });
    const paint = () => icons.querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", b.dataset.key === icon ? "true" : "false"));
    comp.icons.forEach((k) => icons.append(el("button", { type: "button", role: "radio", "data-key": k, "data-tip": k, "aria-label": k,
      onclick: () => { icon = k; paint(); } }, D.compIcon(k))));
    paint();
    const areas = Object.entries(comp.detail_labels).map(([k, label]) => [k, label,
      el("textarea", { rows: 3, maxlength: 1200, placeholder: "Éléments séparés par « ; »" }, d[k] || "")]);
    const active = el("input", { type: "checkbox", checked: c ? c.active : true });
    const starter = el("input", { type: "checkbox", checked: c ? c.starter : false });
    let close = null;
    const form = el("form", { class: "ag-form dm-cc-form", onsubmit: async (ev) => {
      ev.preventDefault();
      const body = { name: name.value, summary: summary.value, icon, starter: starter.checked, details: Object.fromEntries(areas.map(([k, , t]) => [k, t.value])) };
      try {
        if (isNew) await api.post("/api/diamond/competencies", Object.assign({ code: code.value.toUpperCase() }, body));
        else await api.patch("/api/diamond/competencies/" + c.code, Object.assign({ active: active.checked }, body));
      } catch (err) { toast(err.message, "error"); return; }
      close();
      toast(isNew ? "Compétence ajoutée ; sa page BDC est créée." : "Compétence enregistrée ; sa page BDC suit (sauf si elle a été modifiée à la main).", "success");
      reload();
    } },
    el("div", { class: "dm-cc-cols" },
      el("div", null, isNew ? DA.field("Code", code, "2 à 8 lettres ou chiffres majuscules, pour toujours (ex. EMC, OPTICS).") : null,
        DA.field("Nom (terme technique en anglais)", name), DA.field("Résumé", summary), DA.field("Icône", icons),
        isNew ? null : el("label", { class: "check" }, active, " Active (offerte dans la grille ; désactivée, ses notes restent)"),
        el("label", { class: "check", "data-new": "0.60.118-competency-starter" }, starter,
          " Colonne de départ (la grille d'un nouveau Space commence avec elle)")),
      el("div", null, areas.map(([, label, t]) => DA.field(label, t)))),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, isNew ? "Ajouter" : "Enregistrer")));
    close = DA.modal(isNew ? "Nouvelle compétence" : c.name + " (" + c.code + ")", form);
    (isNew ? code : name).focus();
  }

  D.competencyCatalog = competencyCatalog;
})();
