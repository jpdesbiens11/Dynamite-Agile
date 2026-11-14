/* Diamond · the card of a C-n (0.60.103, D-O-115): its measurements and capability (entered at the station, one value per
   line, or imported as CSV from a SPC software; Cpk with σ = MR̄ / 1,128, Ppk with the overall σ, one-sided with one limit)
   and the « à revoir » flags raised when its dimension changed, cleared by « Revu » (who and when are kept). */
(function () {
  "use strict";

  const { api, el, toast } = DA;
  const D = DA.diamond;
  const num = (x, d) => (x == null ? "—" : Number(x).toFixed(d).replace(".", ","));

  function flags(state, c) {
    if (!(c.flags || []).length) return null;
    return el("section", { class: "dm-ch-flags", "data-new": "0.60.103-review-flags" }, el("h2", null, "À revoir après un changement de la cote"),
      el("ul", null, c.flags.map((f) => el("li", null, el("strong", null, f.kind_label), " · " + f.label + " — " + f.reason))),
      state.editable ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => state.send("post", "/" + c.id + "/reviewed", {}, "Revue enregistrée.") },
        "Revu : tout est à jour") : null);
  }

  function measures(state, c) {
    const box = el("section", { class: "dm-ch-measures", "data-new": "0.60.103-measures" }, el("h2", null, "Mesures et capabilité"));
    if (c.control === "test100") {
      box.append(el("p", { class: "muted" }, "Contrôlée par un essai à 100 % : on l'écrit, plutôt que d'inventer un Cpk."));
      return box;
    }
    const out = el("div");
    box.append(out);
    const load = async () => {
      try {
        const res = await api.get(D.base(state.ctx) + "/cplans/measures/" + c.id);
        out.replaceChildren(table(res, c), state.editable ? entry(state, c, load) : null);
      } catch (err) { out.replaceChildren(el("p", { class: "muted" }, err.message)); }
    };
    load();
    return box;
  }

  function table(res, c) {
    const s = res.stats;
    const req = c.cpk_req;
    return el("div", null, el("p", { class: "dm-ch-cap" },
      el("span", null, "n = " + s.n), el("span", null, "x̄ = " + num(s.mean, (c.decimals || 1) + 1)),
      el("span", { class: s.cpk != null && req != null && s.cpk < req ? "dm-ch-miss" : "dm-ch-ok" }, "Cpk " + num(s.cpk, 2)),
      el("span", null, "Ppk " + num(s.ppk, 2)), req != null ? el("span", { class: "muted" }, "exigé " + num(req, 2)) : null,
      s.n && s.short ? el("span", { class: "muted" }, "échantillon court (moins de 25 valeurs)") : null),
    res.measurements.length ? DA.table(["Valeur", "Date", "Lot · n° de série", "Saisie"], res.measurements.slice(0, 20).map((m) => el("tr", null,
      el("td", { class: "dm-ch-spec" }, num(m.value, c.decimals || 1)), el("td", null, m.taken_at.slice(0, 16)), el("td", null, m.sample || "—"),
      el("td", { class: "muted" }, (m.source === "csv" ? "CSV · " : "") + (m.by_name || ""))))) : el("p", { class: "muted" }, "Aucune mesure : la caractéristique est « à mesurer »."));
  }

  function entry(state, c, reload) {
    const area = el("textarea", { rows: 3, "aria-label": "Mesures", placeholder: "Une valeur par ligne : 2,05 — ou « valeur ; date ; lot »" });
    const file = el("input", { type: "file", accept: ".csv,text/csv,text/plain", "aria-label": "CSV d'un logiciel de SPC" });
    let source = "manual";
    file.addEventListener("change", async () => { if (file.files[0]) { area.value = await file.files[0].text(); source = "csv"; } });
    return el("div", { class: "dm-ch-entry" }, area, file, el("button", { type: "button", class: "btn btn-small btn-primary", onclick: async () => {
      try {
        const res = await api.post(D.base(state.ctx) + "/cplans/measures", { characteristic_id: c.id, values: area.value, source });
        toast(res.added + " mesure(s) ajoutée(s)." + (res.problems.length ? " " + res.problems.join(" ") : ""), res.problems.length ? "error" : "success");
        area.value = "";
        reload();
      } catch (err) { toast(err.message, "error"); }
    } }, "Ajouter les mesures"));
  }

  DA.diamond = Object.assign(DA.diamond || {}, { charFlags: flags, charMeasures: measures });
})();
