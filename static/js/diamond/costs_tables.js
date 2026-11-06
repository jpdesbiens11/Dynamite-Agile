/* Diamond · « Coûts et budget », the inputs (0.60.61, D-O-070): the assumptions (currency, prototypes, volumes,
   contingency, hourly rate), the NRE and the cost of each part. Every field is saved when it changes; the summary above
   (costs.js) follows. The parts come from « Structure fonctionnelle → Pièces »; free lines hold what is not a part
   (packaging, assembly, notice…). */
(function () {
  "use strict";

  const { el } = DA;
  const D = DA.diamond;

  const select = (value, options, onchange, disabled, label) => el("select", { "aria-label": label, disabled, onchange: (ev) => onchange(ev.target.value) },
    Object.entries(options).map(([k, v]) => { const o = el("option", { value: k }, v); if (k === value) o.selected = true; return o; }));
  const field = (value, onchange, opts) => {
    const o = opts || {};
    const input = el("input", { type: o.number ? "text" : "text", inputmode: o.number ? "decimal" : null, value: value === null || value === undefined ? "" : String(value).replace(".", o.number ? "," : "."),
      class: o.number ? "num" : null, placeholder: o.placeholder || "", maxlength: o.max || 160, disabled: o.disabled, "aria-label": o.label,
      size: o.size || null });
    input.addEventListener("change", () => onchange(input.value.trim()));
    return input;
  };

  function costTables(ctx, data, run, editable) {
    const ro = !editable;
    return el("div", { class: "dm-cost-inputs" }, assumptions(data, run, ro), nreTable(data, run, ro), linesTable(ctx, data, run, ro));
  }

  function assumptions(data, run, ro) {
    const s = data.settings;
    const set = (body) => run("/costs/settings", body, "patch");
    const vol = (i) => field(s.volumes[i], (v) => { const vols = s.volumes.slice(); vols[i] = v; set({ volumes: vols }); },
      { number: true, disabled: ro, label: "Volume " + (i + 1), size: 8 });
    const notes = el("textarea", { rows: 2, maxlength: 2000, disabled: ro, "aria-label": "Notes", placeholder: "Sources des prix, année, taxes…" }, s.notes || "");
    notes.addEventListener("change", () => set({ notes: notes.value }));
    const item = (label, input, hint) => el("label", { class: "dm-cost-field" }, el("span", null, label), input, hint ? el("small", { class: "muted" }, hint) : null);
    return el("section", { class: "dm-cost-section" }, el("h2", null, "Hypothèses"),
      el("div", { class: "dm-cost-fields" },
        item("Devise", select(s.currency, Object.fromEntries(data.labels.currencies.map((c) => [c, c])), (v) => set({ currency: v }), ro, "Devise")),
        item("Prototypes au budget", field(s.proto_qty, (v) => set({ proto_qty: v }), { number: true, disabled: ro, label: "Prototypes", size: 5 })),
        item("Volumes de production", el("span", { class: "dm-cost-vols" }, vol(0), vol(1), vol(2)), "trois volumes, du plus petit au plus grand"),
        item("Contingence (%)", field(s.contingency, (v) => set({ contingency: v }), { number: true, disabled: ro, label: "Contingence", size: 5 }),
          "les imprévus, sur tout le budget ; 10 à 20 % est courant"),
        item("Taux horaire de l'équipe", field(s.labour_rate, (v) => set({ labour_rate: v }), { number: true, disabled: ro, label: "Taux horaire", size: 7 }),
          "valeur d'une heure de Timesheet ; 0 = le temps ne compte pas")),
      item("Notes", notes));
  }

  function nreTable(data, run, ro) {
    const L = data.labels, m = D.costMoney(data.settings.currency, 2);
    const patch = (r, body) => run("/costs/nre/" + r.id, body, "patch");
    const rows = data.nre.map((r) => el("tr", null,
      el("td", { class: "dm-cost-code" }, "NRE-" + r.number),
      el("td", null, field(r.title, (v) => patch(r, { title: v }), { disabled: ro, label: "Intitulé", size: 28 })),
      el("td", null, select(r.category, L.categories, (v) => patch(r, { category: v }), ro, "Catégorie")),
      el("td", null, select(r.phase, L.phases, (v) => patch(r, { phase: v }), ro, "Phase")),
      el("td", null, field(r.amount, (v) => patch(r, { amount: v }), { number: true, disabled: ro, label: "Montant", size: 9 })),
      el("td", null, select(r.basis, L.bases, (v) => patch(r, { basis: v }), ro, "Base")),
      el("td", null, field(r.supplier, (v) => patch(r, { supplier: v }), { disabled: ro, label: "Fournisseur", size: 14 })),
      el("td", null, ro ? null : el("button", { type: "button", class: "btn btn-small", title: "Retirer cette ligne",
        onclick: () => { if (window.confirm("Retirer NRE-" + r.number + " « " + r.title + " » ?")) run("/costs/nre/" + r.id + "/delete"); } }, "✕"))));
    const title = el("input", { type: "text", maxlength: 160, placeholder: "Ex. Moule d'injection du boîtier", "aria-label": "Nouvel NRE", size: 30 });
    const amount = el("input", { type: "text", inputmode: "decimal", class: "num", placeholder: "Montant", "aria-label": "Montant", size: 9 });
    const cat = select("outillage", L.categories, () => {}, false, "Catégorie");
    const add = ro ? null : el("form", { class: "dm-cost-add", onsubmit: (ev) => {
      ev.preventDefault();
      run("/costs/nre", { title: title.value, amount: amount.value, category: cat.value });
    } }, title, cat, amount, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Ajouter un NRE"));
    const total = data.nre.reduce((s, r) => s + Number(r.amount || 0), 0);
    return el("section", { class: "dm-cost-section" }, el("h2", null, "NRE — coûts uniques du projet"),
      el("p", { class: "muted" }, "Ce qui se paie une fois, quel que soit le volume : ingénierie, outillage et moules, essais, certification, "
        + "logiciels, gabarits. La base dit à quel point le montant est sûr : estimation, soumission, engagé, payé."),
      el("div", { class: "dm-cost-scroll" }, el("table", { class: "dm-cost-table dm-cost-edit" },
        el("thead", null, el("tr", null, ["", "Intitulé", "Catégorie", "Phase", "Montant", "Base", "Fournisseur", ""].map((h) => el("th", null, h)))),
        el("tbody", null, rows.length ? rows : el("tr", null, el("td", { colspan: 8, class: "muted" }, "Aucun NRE pour l'instant."))),
        el("tfoot", null, el("tr", null, el("th", { colspan: 4 }, "Total des NRE"), el("th", { class: "num" }, m(total)), el("th", { colspan: 3 }))))),
      add);
  }

  function linesTable(ctx, data, run, ro) {
    const s = data.settings, L = data.labels, m = D.costMoney(s.currency, 2);
    const save = (ln, body) => (ln.id ? run("/costs/lines/" + ln.id, body, "patch") : run("/costs/lines", Object.assign({ part_id: ln.part_id }, body)));
    const num = (ln, key, label) => field(ln[key], (v) => save(ln, { [key]: v }), { number: true, disabled: ro, label, size: 7,
      placeholder: key === "proto_unit" ? "" : "= proto" });
    const rows = data.lines.map((ln) => el("tr", { class: ln.part_id ? null : "dm-cost-free" },
      el("td", { class: "dm-cost-code" }, ln.code || "+"),
      el("td", null, ln.part_id ? el("span", { title: ln.kind }, ln.name) : field(ln.name, (v) => save(ln, { name: v }), { disabled: ro, label: "Désignation", size: 24 })),
      el("td", null, field(ln.qty, (v) => save(ln, { qty: v }), { number: true, disabled: ro, label: "Quantité", size: 4 })),
      el("td", null, num(ln, "proto_unit", "Prix prototype")),
      el("td", null, num(ln, "prod_1", "Prix à " + s.volumes[0])),
      el("td", null, num(ln, "prod_2", "Prix à " + s.volumes[1])),
      el("td", null, num(ln, "prod_3", "Prix à " + s.volumes[2])),
      el("td", { class: "num" }, ln.proto_unit === null || ln.proto_unit === undefined ? "—" : m(Number(ln.qty || 1) * Number(ln.proto_unit))),
      el("td", null, field(ln.supplier, (v) => save(ln, { supplier: v }), { disabled: ro, label: "Fournisseur", size: 14 })),
      el("td", null, select(ln.basis || "estimation", L.bases, (v) => save(ln, { basis: v }), ro, "Base")),
      el("td", null, ro || !ln.id ? null : el("button", { type: "button", class: "btn btn-small", title: ln.part_id ? "Effacer les prix de cette pièce" : "Retirer cette ligne",
        onclick: () => { if (window.confirm(ln.part_id ? "Effacer les prix de « " + ln.name + " » ? La pièce reste dans Diamond." : "Retirer « " + ln.name + " » ?")) run("/costs/lines/" + ln.id + "/delete"); } }, "✕"))));
    const b = data.budget;
    const name = el("input", { type: "text", maxlength: 160, placeholder: "Ex. Boîte du kit et notice imprimée", "aria-label": "Nouvelle ligne", size: 30 });
    const add = ro ? null : el("form", { class: "dm-cost-add", onsubmit: (ev) => { ev.preventDefault(); run("/costs/lines", { name: name.value }); } },
      name, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Ajouter une ligne hors pièces"));
    return el("section", { class: "dm-cost-section" }, el("h2", null, "Coût par pièce"),
      el("p", { class: "muted" }, "Une ligne par pièce de Diamond (Structure fonctionnelle → Pièces), plus les lignes hors pièces : emballage, "
        + "assemblage, notice… Le prix de prototype est celui de l'unité chez un distributeur ; les prix de production, ceux des volumes. "
        + "Un prix de production vide compte au prix de prototype."),
      data.lines.length ? null : el("p", { class: "muted" }, el("a", { href: A().href(ctx, "fstructure") }, "Ajoutez d'abord les pièces dans la structure fonctionnelle"), "."),
      el("div", { class: "dm-cost-scroll" }, el("table", { class: "dm-cost-table dm-cost-edit" },
        el("thead", null, el("tr", null, ["", "Désignation", "Qté", "Prototype", "à " + new Intl.NumberFormat("fr-CA").format(s.volumes[0]),
          "à " + new Intl.NumberFormat("fr-CA").format(s.volumes[1]), "à " + new Intl.NumberFormat("fr-CA").format(s.volumes[2]), "Total proto",
          "Fournisseur", "Base", ""].map((h) => el("th", null, h)))),
        el("tbody", null, rows),
        el("tfoot", null, el("tr", null, el("th", { colspan: 3 }, "Coût d'une unité"), el("th", { class: "num" }, m(b.unit_proto)),
          b.volumes.map((v) => el("th", { class: "num" }, m(v.parts))), el("th", { colspan: 4 }))))),
      add);
  }

  const A = () => DA.agile;
  D.costTables = costTables;
})();
