/* Diamond · Caractéristiques → « # de pièce de l'entreprise » (0.60.103, D-O-112), #/diamond/KEY/chars/pn: the BOM of
   the ERP imported as CSV (preview, then apply), the prompt for an AI assistant that matches the Diamond parts to the
   company PNs (never inventing one), its answer pasted back (preview: sure, to choose, to create in the ERP, refused),
   and the PNs of each Diamond part, set by hand. The external loop only: nothing leaves the server. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const D = DA.diamond;
  const VERDICT = { sure: "sûre", choose: "à choisir", todo: "à créer dans l'ERP", refused: "refusée" };
  const STATUS = { new: "nouveau", changed: "modifié", same: "inchangé" };

  async function view(holder, state) {
    const base = D.base(state.ctx) + "/pn";
    const s = { base, editable: state.editable, data: await api.get(base) };
    const box = el("div", { class: "dm-pn", "data-new": "0.60.103-pn" });
    holder.append(box);
    s.redraw = () => draw(box, s);
    draw(box, s);
  }

  function draw(box, s) {
    clear(box);
    const d = s.data, c = d.counts;
    box.append(el("p", { class: "dm-ch-count" }, el("span", { class: "badge badge-neutral" }, c.linked + " / " + c.parts + " pièces reliées"),
      " ", el("span", null, c.bom + " PN dans la nomenclature de l'ERP"), c.todo ? " · " : "", c.todo ? el("span", null, c.todo + " pièce(s) à créer dans l'ERP") : ""));
    if (s.editable) box.append(bomSection(s), aiSection(s));
    box.append(partsSection(s));
  }

  function bomSection(s) {
    const area = el("textarea", { rows: 4, "aria-label": "BOM de l'ERP (CSV)", placeholder: "PN;Révision;Désignation;Fournisseur;Matière" });
    const file = el("input", { type: "file", accept: ".csv,text/csv,text/plain", "aria-label": "Fichier CSV du BOM" });
    file.addEventListener("change", async () => { if (file.files[0]) area.value = await file.files[0].text(); });
    const out = el("div");
    const send = async (mode) => {
      try {
        const res = await api.post(s.base + "/bom", { file: area.value, mode });
        if (mode === "apply") { s.data = res; toast(res.counts_import.new + " PN ajouté(s), " + res.counts_import.changed + " modifié(s).", "success"); s.redraw(); return; }
        clear(out);
        out.append(...[el("p", null, res.counts.new + " nouveau(x), " + res.counts.changed + " modifié(s), " + res.counts.same + " inchangé(s)."),
          res.problems.length ? el("ul", { class: "dm-cls-err" }, res.problems.map((p) => el("li", null, p))) : null,
          DA.table(["Ligne", "PN", "Rév.", "Désignation", "Fournisseur", "Matière", "Statut"], res.plan.map((r) => el("tr", null,
            [r.line, r.pn, r.rev, r.designation, r.supplier, r.material, STATUS[r.status]].map((v) => el("td", null, String(v || "")))))),
          el("button", { type: "button", class: "btn btn-primary", onclick: () => send("apply") }, "Appliquer")].filter(Boolean));
      } catch (err) { toast(err.message, "error"); }
    };
    return el("section", { class: "dm-pn-step" }, el("h2", null, "1. Nomenclature de l'ERP"),
      el("p", { class: "muted" }, "Un CSV avec les colonnes PN, Révision, Désignation, Fournisseur, Matière. Un PN connu est mis à jour, un nouveau "
        + "est ajouté ; rien n'est effacé."), file, area,
      el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-small", onclick: () => send("preview") }, "Aperçu de l'import")), out);
  }

  function aiSection(s) {
    const area = el("textarea", { rows: 4, "aria-label": "Réponse de l'IA", placeholder: "Collez ici le tableau JSON rendu par l'assistant IA" });
    const out = el("div");
    const copy = async () => {
      try {
        const res = await api.get(s.base + "/prompt");
        await navigator.clipboard.writeText(res.prompt);
        toast("Prompt copié : " + res.parts + " pièces et " + res.bom + " PN. Collez-le dans votre assistant IA.", "success");
      } catch (err) { toast(err.message, "error"); }
    };
    const preview = async () => {
      try {
        const res = await api.post(s.base + "/ai", { answer: area.value, mode: "preview" });
        clear(out);
        const checks = res.rows.map((r) => {
          const box = el("input", { type: "checkbox", checked: r.verdict === "sure" || r.verdict === "todo", disabled: r.verdict === "refused",
            "aria-label": "Retenir la proposition " + (r.index + 1) });
          return [r, box];
        });
        out.append(el("p", null, res.counts.sure + " sûre(s), " + res.counts.choose + " à choisir, " + res.counts.todo + " à créer dans l'ERP, "
          + res.counts.refused + " refusée(s)."),
        DA.table(["", "Pièce", "PN proposé", "Confiance", "Raison", "Verdict"], checks.map(([r, box]) => el("tr", { class: "dm-pn-" + r.verdict },
          el("td", null, box), el("td", null, r.part), el("td", null, r.label || r.pn || "aucun"), el("td", null, Math.round(r.confidence * 100) + " %"),
          el("td", null, r.reason), el("td", null, VERDICT[r.verdict] + (r.why ? " — " + r.why : ""))))),
        el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
          const pick = checks.filter(([r, b]) => b.checked && r.company_id).map(([r]) => r.index);
          const todo = checks.filter(([r, b]) => b.checked && r.verdict === "todo").map(([r]) => r.part);
          try {
            s.data = await api.post(s.base + "/ai", { answer: area.value, mode: "apply", pick, todo });
            toast(s.data.applied.linked + " PN reliés, " + s.data.applied.erp_todo + " pièce(s) à créer dans l'ERP.", "success");
            s.redraw();
          } catch (err) { toast(err.message, "error"); }
        } }, "Appliquer la sélection"));
      } catch (err) { toast(err.message, "error"); }
    };
    return el("section", { class: "dm-pn-step" }, el("h2", null, "2. Correspondance par l'IA"),
      el("p", { class: "muted" }, "Le prompt donne les pièces Diamond (fonctions, notes) et la nomenclature, avec une règle stricte : ne jamais "
        + "inventer un PN, répondre « aucun » si rien ne convient, une raison par proposition. La réponse revient en aperçu : les "
        + "propositions sûres sont cochées, les autres se choisissent à la main ; un PN absent de la nomenclature est refusé."),
      el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.103-pn-prompt", onclick: copy }, "Copier le prompt pour l'IA")),
      area, el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-small", onclick: preview }, "Aperçu de la réponse")), out);
  }

  function partsSection(s) {
    const d = s.data;
    const save = async (p, body) => {
      try { s.data = await api.put(s.base + "/parts/" + p.id, body); s.redraw(); } catch (err) { toast(err.message, "error"); }
    };
    return el("section", { class: "dm-pn-step" }, el("h2", null, "3. Pièces Diamond et # de l'entreprise"),
      el("div", { class: "dm-scroll" }, DA.table(["Pièce", "Nom", "# entreprise", "À créer dans l'ERP"], d.parts.map((p) => {
        const chips = p.pns.map((x) => el("span", { class: "dm-pn-chip", "data-tip": x.designation + (x.reason ? " — " + x.reason : "") },
          x.label, x.source === "ai" ? el("span", { class: "muted" }, " IA") : null,
          s.editable ? el("button", { type: "button", class: "link-btn", "aria-label": "Retirer " + x.label + " de " + p.code,
            onclick: () => save(p, { pn_ids: p.pns.filter((y) => y.id !== x.id).map((y) => y.id) }) }, "×") : null));
        const add = s.editable && d.bom.length ? el("select", { "aria-label": "Ajouter un PN à " + p.code },
          el("option", { value: "" }, "+ PN…"), d.bom.filter((b) => !p.pns.some((x) => x.id === b.id)).map((b) => el("option", { value: b.id }, b.label + " · " + b.designation))) : null;
        if (add) add.addEventListener("change", () => add.value && save(p, { pn_ids: p.pns.map((x) => x.id).concat([Number(add.value)]) }));
        const todo = el("input", { type: "checkbox", checked: !!p.erp_todo, disabled: !s.editable, "aria-label": p.code + " à créer dans l'ERP" });
        todo.addEventListener("change", () => save(p, { erp_todo: todo.checked }));
        return el("tr", null, el("td", { class: "dm-code" }, p.code), el("td", null, p.name), el("td", null, el("div", { class: "dm-pn-chips" }, chips, add)), el("td", null, todo));
      }))));
  }

  DA.diamond = Object.assign(DA.diamond || {}, { pnView: view });
})();
