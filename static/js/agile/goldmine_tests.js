/* Goldmine « Test Procedure » (D-B-079): the tests of the Testing base that verify a requirement. Mandatory for a
   requirement (the server refuses to save one without a test), not for a need. The list is grouped by subject,
   the subjects that fit the requirement's category / life-cycle phase first (★). Obsolete tests are not offered.
   D-B-082: each test shows its source « (IEC 60068-2-6, Test Fc) » and the source of the chosen tests is filled in
   automatically under the field; tests of the same functions as the requirement come first.
   Also shared with Testing (DA.gt): chipPicker (central lists) and the Word export dialog (D-B-083). */
(function () {
  "use strict";

  const { api, el, clear } = DA;
  const A = DA.agile;
  let cache = null, cachedAt = 0;

  /* subjects that usually verify a category / phase -- only an ordering hint, every test stays available */
  const BY_CATEGORY = { performance: ["func", "therm", "mech"], functional: ["func", "ver", "sw"], interface: ["sw", "usab", "elec"],
    environmental: ["env", "ingress", "emc"], safety: ["elec", "therm", "mech"], personnel_safety: ["elec", "therm", "usab"],
    regulatory: ["elec", "emc", "mat", "ver"] };
  const BY_PHASE = { transport: ["mech", "env"], manufacturing: ["prod"], assembly: ["prod"], test: ["prod"], operation: ["func", "usab"],
    second_life: ["life"], end_of_life: ["life", "mat"], maintenance: ["ver", "life"], installation: ["sw", "mech"],
    appearance: ["usab"] };

  /* D-B-097: a requirement cites tests of its own Space's Test Base -- the Space of the screen (#/goldmine/<KEY>/…) */
  let cachedSpace = "";
  function space() {
    const key = (location.hash.split("/")[2] || "").toUpperCase();
    return /^[A-Z][A-Z0-9]{1,9}$/.test(key) ? key : ((DA.session.projects || []).some((p) => p.key === "TESTING") ? "TESTING" : "DEMO");
  }
  const testHref = (id) => "#/testing/" + space() + "/test/" + id;

  function options() {  // one request shared by every picker / link list of the screen, renewed after a minute
    if (!cache || Date.now() - cachedAt > 60000 || cachedSpace !== space()) {
      cachedAt = Date.now();
      cachedSpace = space();
      cache = api.get("/api/testing/options?space=" + encodeURIComponent(cachedSpace)).catch((err) => { cache = null; throw err; });
    }
    return cache;
  }
  const split = (v) => Array.from(new Set(String(v || "").toUpperCase().split(/[\s,;]+/).filter(Boolean)));

  /* picker(value, context) -> { node, value(), refresh() }; context() gives {category, lifecycle, kind, functions} */
  function testPicker(value, context) {
    let chosen = split(value);
    let data = null;
    const chips = el("div", { class: "gt-chosen", "aria-live": "polite" });
    const select = el("select", { "aria-label": "Ajouter un test" });
    const note = el("span", { class: "field-hint" });
    const source = el("div", { class: "gt-source", "aria-live": "polite" });
    const node = el("div", { class: "gt-picker" }, chips, el("div", { class: "gt-add" }, select),
      el("span", { class: "field-hint gt-links" }, "Un ou plusieurs tests de la Test Base de ce Space ",
        el("a", { href: "#/testing/" + space(), target: "_blank", rel: "noopener" }, "Testing · " + space()),
        ". Rien ne convient ? Prenez un « Custom Test » (TST-CUS-…) ou demandez-en un à l'équipe de tests."), source, note);
    const title = (id) => { const t = data && data.tests.find((x) => x.test_id === id); return t ? t.title : ""; };

    function drawChips() {
      clear(chips);
      const need = context && context().kind === "need";
      if (!chosen.length) chips.append(el("span", { class: need ? "muted" : "gt-empty" },
        need ? "Non requis pour un need." : "Aucun test : obligatoire pour enregistrer un requirement."));
      chosen.forEach((id) => chips.append(el("span", { class: "gt-chip", title: title(id) },
        el("a", { href: testHref(id), target: "_blank", rel: "noopener" }, id), title(id) ? " · " + title(id).slice(0, 48) : "",
        el("button", { type: "button", "aria-label": "Retirer " + id, onclick: () => { chosen = chosen.filter((x) => x !== id); refresh(); } }, "×"))));
      clear(source);
      const known = chosen.map((id) => data && data.tests.find((x) => x.test_id === id)).filter(Boolean);
      if (known.length) source.append(el("span", { class: "ag-field-label" }, "Test Source (automatique) : "),
        known.map((t, i) => (i ? " ; " : "") + t.test_id + " (" + (t.source || "—") + ")").join(""));
    }
    function drawSelect() {
      clear(select);
      select.append(el("option", { value: "" }, data ? "+ Ajouter un test (par sujet)…" : "Chargement de la base Testing…"));
      if (!data) return;
      const ctx = context ? context() : {};
      const first = Array.from(new Set([].concat(BY_PHASE[ctx.lifecycle] || [], BY_CATEGORY[ctx.category] || [])));
      const order = first.concat(Object.keys(data.subjects).filter((s) => !first.includes(s)));
      const label = (t) => t.test_id + " · " + t.title + " (" + (t.source || "—") + ")" + (t.category === "custom" ? " [custom]" : "");
      const funcs = split(ctx.functions);
      const same = funcs.length ? data.tests.filter((t) => t.status !== "Obsolete" && !chosen.includes(t.test_id)
        && split(t.functions).some((f) => funcs.includes(f))) : [];
      if (same.length) select.append(el("optgroup", { label: "★ Mêmes fonctions (" + funcs.join(", ") + ")" },
        same.map((t) => el("option", { value: t.test_id }, label(t)))));
      order.forEach((subject) => {
        const tests = data.tests.filter((t) => t.subject === subject && t.status !== "Obsolete" && !chosen.includes(t.test_id));
        if (!tests.length) return;
        select.append(el("optgroup", { label: (first.includes(subject) ? "★ " : "") + data.subjects[subject] },
          tests.map((t) => el("option", { value: t.test_id }, label(t)))));
      });
    }
    function refresh() { drawChips(); drawSelect(); }
    select.addEventListener("change", () => {
      if (select.value && !chosen.includes(select.value)) chosen.push(select.value);
      refresh();
      select.focus();
    });
    options().then((d) => { data = d; if (!d.tests.length) note.textContent = "Base Testing vide : champ facultatif."; refresh(); })
      .catch((err) => { note.textContent = err.message; });
    refresh();
    return { node, value: () => chosen.join(", "), refresh };
  }

  /* Read-only: the tests as links, with their titles once the base is loaded */
  function testLinks(value) {
    const ids = split(value);
    if (!ids.length) return el("span", { class: "gm-missing" }, "Aucun test");
    const box = el("span", { class: "gt-links" }, ids.map((id) => el("a", { class: "ag-key", href: testHref(id) }, id)));
    options().then((d) => {
      box.querySelectorAll("a").forEach((a) => {
        const t = d.tests.find((x) => x.test_id === a.textContent);
        if (t) a.title = t.title + " (" + t.status + ")";
      });
    }).catch(() => {});
    return box;
  }

  /* Central-list picker (D-B-082): chips + a select of the active entries, nothing typed by hand.
     items [{code, label, category, active}] ; returns { node, value(), refresh() } */
  function chipPicker(items, value, opts) {
    const o = opts || {};
    let chosen = split(value);
    const chips = el("div", { class: "gt-chosen" });
    const select = el("select", { "aria-label": o.label || "Ajouter" });
    const labelOf = (code) => { const it = items.find((x) => x.code === code); return it ? it.label : code; };
    function draw() {
      clear(chips);
      if (!chosen.length) chips.append(el("span", { class: "muted" }, o.empty || "—"));
      chosen.forEach((code) => chips.append(el("span", { class: "gt-chip", title: labelOf(code) }, code,
        o.short ? "" : " · " + labelOf(code).slice(0, 50),
        el("button", { type: "button", "aria-label": "Retirer " + code, onclick: () => { chosen = chosen.filter((x) => x !== code); draw(); } }, "×"))));
      clear(select);
      select.append(el("option", { value: "" }, o.placeholder || "+ Ajouter…"));
      const groups = {};
      items.filter((it) => it.active && !chosen.includes(it.code)).forEach((it) => {
        (groups[it.category || ""] = groups[it.category || ""] || []).push(it);
      });
      Object.entries(groups).forEach(([g, list]) => {
        const opts2 = list.map((it) => el("option", { value: it.code }, it.code + " · " + it.label));
        if (g) select.append(el("optgroup", { label: g }, opts2)); else select.append(...opts2);
      });
    }
    select.addEventListener("change", () => {
      if (select.value) chosen.push(select.value);
      draw();
      select.focus();
      if (o.onchange) o.onchange();
    });
    draw();
    return { node: el("div", { class: "gt-picker" }, chips, el("div", { class: "gt-add" }, select)),
      value: () => chosen.join(", "), refresh: draw };
  }

  /* Word export dialog (D-B-083): document fields, grouping, language -> query string for the .docx route */
  function wordDialog(title, defaults, groups, go) {
    const f = {
      title: el("input", { type: "text", maxlength: 160, value: defaults.title || "" }),
      docno: el("input", { type: "text", maxlength: 40, value: defaults.docno || "", placeholder: "ex. TSP-00001" }),
      rev: el("input", { type: "text", maxlength: 10, value: defaults.rev || "A" }),
      subject: el("input", { type: "text", maxlength: 80, value: defaults.subject || "", placeholder: "ex. Projet d'équipe" }),
      doctype: el("input", { type: "text", maxlength: 60, value: defaults.doctype || "" }),
      prepared: el("input", { type: "text", maxlength: 80, value: (DA.session.user && DA.session.user.display_name) || "" }),
      group: el("select", null, groups.map(([v, l]) => el("option", { value: v }, l))),
      lang: el("select", null, el("option", { value: "en" }, "Anglais"), el("option", { value: "fr" }, "Français")),
    };
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault();
      const params = new URLSearchParams();
      Object.entries(f).forEach(([k, input]) => { if (input.value) params.set(k, input.value); });
      close();
      go(params);
    } }, el("p", { class: "muted" }, defaults.note || ""),
    DA.field("Titre du document", f.title),
    el("div", { class: "form-row" }, DA.field("N° de document", f.docno), DA.field("Revision", f.rev), DA.field("Sujet (page de garde)", f.subject)),
    el("div", { class: "form-row" }, DA.field("Type (en-tête)", f.doctype), DA.field("Préparé par", f.prepared)),
    el("div", { class: "form-row" }, DA.field("Regrouper par", f.group), DA.field("Langue des sections", f.lang)),
    el("p", { class: "field-hint" }, "Gabarit Word : page de garde, en-tête, table des matières (Word la met à jour à "
      + "l'ouverture : « Oui »), journal des révisions, un bloc par élément façon Codebeamer, matrice de traçabilité."),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Exporter en Word (.docx)")));
    close = DA.modal(title, form);
  }

  function download(url) {
    const frame = el("iframe", { src: url, class: "ag-hidden-frame" });
    document.body.append(frame);
    setTimeout(() => frame.remove(), 30000);
  }

  DA.gt = { options, split, chipPicker, wordDialog, download };
  A.testPicker = testPicker;
  A.testLinks = testLinks;
})();
