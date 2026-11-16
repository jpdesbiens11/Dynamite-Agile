/* Diamond · concept sheets (0.60.105, D-O-117). Under a brick (concept_page.js): its sheets as cards -- CB-3.1, title, principle,
   pros and cons, the scan of a paper sheet shown as an image (or a PDF link) -- with « Feuille numérique » and « Scanner une feuille ».
   #/diamond/KEY/csheets: every sheet of the Space, brick by brick (« Feuilles de concept »). */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  function fileUrl(ctx, s) { return D.base(ctx) + "/sheets/" + s.id + "/file"; }

  function card(ctx, s, editable, done, labels) {
    const status = (labels && labels.status ? labels.status : { open: "Open", selected: "Selected", dropped: "Dropped" })[s.status];
    const scan = s.attachment_id ? (String(s.file_mime || "").startsWith("image/")
      ? el("a", { href: fileUrl(ctx, s), target: "_blank", rel: "noopener" }, el("img", { class: "dm-sheet-scan", src: fileUrl(ctx, s), alt: "Scan de " + s.code }))
      : el("a", { class: "btn btn-small", href: fileUrl(ctx, s), target: "_blank", rel: "noopener" }, "Ouvrir le scan (PDF)")) : null;
    const row = (label, text) => (text ? el("p", null, el("strong", null, label + " "), text) : null);
    return el("article", { class: "dm-sheet dm-sheet-" + s.kind + " dm-sheet-st-" + s.status },
      el("div", { class: "dm-cb-top" }, el("span", { class: "dm-code" }, s.code),
        el("span", { class: "badge badge-neutral" }, { digital: "Numérique", ai: "IA", scan: "Scan" }[s.kind] || s.kind),
        s.status !== "open" ? el("span", { class: "badge " + (s.status === "selected" ? "badge-ok" : "badge-off") }, status) : null),
      el("h3", null, s.title), scan,
      row("Principe :", s.principle), s.description ? el("p", { class: "dm-sheet-desc" }, s.description) : null,
      row("+", s.pros), row("−", s.cons),
      el("p", { class: "muted dm-sheet-by" }, (s.author_name || "") + " · " + DA.formatDate(s.updated_at || s.created_at)),
      editable ? el("div", { class: "dm-actions" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => openSheet(ctx, s.concept_id, s, done) }, "Modifier"),
        el("button", { type: "button", class: "btn btn-small btn-danger", onclick: async () => {
          if (!window.confirm("Archiver la feuille " + s.code + " « " + s.title + " » ?")) return;
          try { await api.post(D.base(ctx) + "/sheets/" + s.id + "/archive", {}); done(); } catch (err) { toast(err.message, "error"); }
        } }, "Archiver")) : null);
  }

  function sheetSection(ctx, state, editable) {
    const { concept: c, sheets } = state.data;
    return el("section", { class: "dm-cb-section", "data-new": "0.60.105-sheets" },
      el("div", { class: "dm-panel-head" }, el("h2", null, "Feuilles de concept (" + sheets.length + ")"),
        editable ? el("div", { class: "dm-actions" },
          el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => openSheet(ctx, c.id, null, state.reload) }, "Feuille numérique"),
          el("button", { type: "button", class: "btn btn-small", onclick: () => openScan(ctx, c.id, state.reload) }, "Scanner une feuille")) : null),
      sheets.length ? el("div", { class: "dm-sheets" }, sheets.map((s) => card(ctx, s, editable, state.reload)))
        : el("p", { class: "muted" }, c.kind === "existing" ? "Concept existant : une feuille n'est utile que pour comparer des variantes."
          : "Aucune feuille. Dessinez des solutions vraiment différentes : en séance (scannez les feuilles), dans l'outil, ou avec l'IA."));
  }

  function openSheet(ctx, conceptId, s, done) {
    const title = el("input", { type: "text", maxlength: 160, value: s ? s.title : "", placeholder: "ex. Plaque froide sous les cellules" });
    const principle = el("input", { type: "text", maxlength: 600, value: s ? s.principle : "", placeholder: "Le principe en une phrase" });
    const description = el("textarea", { rows: 4, maxlength: 4000 }, s ? s.description : "");
    const pros = el("textarea", { rows: 2, maxlength: 1500 }, s ? s.pros : "");
    const cons = el("textarea", { rows: 2, maxlength: 1500 }, s ? s.cons : "");
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      const body = { title: title.value, principle: principle.value, description: description.value, pros: pros.value, cons: cons.value };
      try {
        if (s) await api.patch(D.base(ctx) + "/sheets/" + s.id, body);
        else await api.post(D.base(ctx) + "/concepts/" + conceptId + "/sheets", Object.assign(body, { kind: "digital" }));
        close();
        done();
      } catch (err) { error.textContent = err.message; }
    } }, field("Titre", title), field("Principe de fonctionnement", principle),
    field("Description (ce que montre la feuille : architecture, matériaux, ordres de grandeur)", description),
    el("div", { class: "dm-row" }, field("Avantages", pros), field("Inconvénients", cons)), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal(s ? "Feuille " + s.code : "Nouvelle feuille de concept", form);
    document.querySelectorAll(".modal").forEach((m) => m.classList.add("modal-wide"));
    title.focus();
  }

  function openScan(ctx, conceptId, done) {
    const file = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp,application/pdf", "aria-label": "Scan" });
    const title = el("input", { type: "text", maxlength: 160, placeholder: "Titre écrit sur la feuille" });
    const principle = el("input", { type: "text", maxlength: 600, placeholder: "Le principe en une phrase (facultatif)" });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      if (!file.files.length) { error.textContent = "Choisissez la photo ou le PDF de la feuille."; return; }
      try {
        const up = await api.upload(D.base(ctx) + "/sheets/upload", file.files[0]);
        await api.post(D.base(ctx) + "/concepts/" + conceptId + "/sheets", { title: title.value || file.files[0].name.replace(/\.[^.]+$/, ""),
          principle: principle.value, kind: "scan", attachment_id: up.id });
        close();
        done();
      } catch (err) { error.textContent = err.message; }
    } }, field("Photo ou scan (PNG, JPEG, WebP ou PDF, 15 Mo au plus)", file), field("Titre", title), field("Principe", principle), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Déposer")));
    close = modal("Scanner une feuille de concept", form);
  }

  /* #/diamond/KEY/csheets */
  async function listView(page, ctx) {
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const draw = async () => {
      const data = await api.get(D.base(ctx) + "/sheets");
      clear(holder);
      holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Feuilles de concept")]),
        el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.105-csheets" }, "Feuilles de concept"),
          el("p", { class: "muted" }, "Toutes les solutions dessinées, brique par brique : feuilles numériques, générées avec l'IA ou scannées "
            + "après une séance de créativité. Elles nourrissent les matrices de Pugh.")));
      if (!data.sheets.length) {
        holder.append(el("div", { class: "empty" }, el("p", null, "Aucune feuille pour l'instant. Ouvrez une brique à définir pour en ajouter."),
          el("a", { class: "btn btn-primary", href: A.href(ctx, "concepts") }, "Briques technologiques")));
        return;
      }
      const by = new Map();
      data.sheets.forEach((s) => { const k = "CB-" + s.concept_number; if (!by.has(k)) by.set(k, []); by.get(k).push(s); });
      by.forEach((list, code) => holder.append(el("section", { class: "dm-cb-section" },
        el("h2", null, el("a", { href: A.href(ctx, "concepts/" + code) }, code), " " + list[0].concept_name),
        el("div", { class: "dm-sheets" }, list.map((s) => card(ctx, s, A.canEdit(ctx), draw, data.labels))))));
    };
    await draw();
  }

  D.sheetSection = sheetSection;
  A.views.csheets = listView;
})();
