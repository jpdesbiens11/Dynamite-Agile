/* « Révisions de référence » #/revisions (core lot v0.33, D-B-129): the frozen, numbered revisions revX.XX of the
   whole database. Everybody: list, « Consulter » (the whole site read-only as it was, exports stamped with the revision)
   and the banner while viewing. Administrators: « Figer une révision » (number automatic or typed, never going back),
   « Vérifier » (SHA-256 and chain), the register of extractions (who took what, from which revision, when).
   Also reached from Admin → Plateforme → Révisions. el() / textContent only. */
(function () {
  "use strict";
  const { api, el, clear, field, toast, table } = DA;
  const BL = (DA.baselines = DA.baselines || {});
  let cache = null;

  const mb = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1).replace(".", ",") + " Mo" : Math.max(1, Math.round(n / 1024)) + " Ko");
  const short = (sha) => (sha || "").slice(0, 12);

  async function setView(label) {
    try {
      const r = await api.post("/api/baselines/view", { label });
      if (DA.session.prefs) DA.session.prefs.baseline_view = r.view;
      cache = null;
      toast(r.view ? "Vous consultez " + r.view + " : tout le site est en lecture seule." : "Retour à la base courante.", "success");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    } catch (err) { toast(err.message, "error"); }
  }
  BL.setView = setView;

  /* The banner shown under the top bar while a revision is viewed (app.js renderShell). */
  DA.baselineBanner = function () {
    const view = DA.session.prefs && DA.session.prefs.baseline_view;
    if (!view) return null;
    const title = el("span", { class: "bl-banner-title" });
    (cache ? Promise.resolve(cache) : api.get("/api/baselines").then((d) => (cache = d))).then((d) => {
      const rec = d.baselines.find((b) => b.label === view);
      if (rec) title.textContent = " — « " + rec.title + " », figée le " + rec.local;
    }).catch(() => {});
    return el("div", { class: "bl-banner", role: "status", "data-new": "0.50.11-baseline-view" },
      el("strong", null, "🔒 Révision " + view), title,
      el("span", { class: "bl-banner-text" }, " · lecture seule : le site est montré tel qu'il était, chaque export porte " + view + "."),
      el("a", { class: "btn btn-small", href: "#/revisions" }, "Révisions"),
      el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => setView("") }, "Revenir à la base courante"));
  };

  function createForm(data, reload) {
    const number = el("input", { type: "text", maxlength: 12, placeholder: "automatique : " + data.next, "aria-label": "Numéro" });
    const title = el("input", { type: "text", maxlength: 160, required: true, placeholder: "ex. Revue de conception CDR — BM3" });
    const note = el("textarea", { rows: 2, maxlength: 2000, placeholder: "Motif, périmètre de la revue, client concerné…" });
    const error = el("p", { class: "form-error", role: "alert" });
    const submit = el("button", { type: "submit", class: "btn btn-primary" }, "Figer la révision");
    return el("form", { class: "ag-form bl-card", "data-new": "0.50.11-baseline-create", onsubmit: async (ev) => {
      ev.preventDefault();
      submit.disabled = true;
      error.textContent = "";
      try {
        const r = await api.post("/api/baselines", { number: number.value, title: title.value, note: note.value });
        toast(r.baseline.label + " figée (" + mb(r.baseline.bytes) + ").", "success");
        reload();
      } catch (err) { error.textContent = err.message; submit.disabled = false; }
    } },
    el("h2", null, "Figer une révision"),
    el("p", { class: "muted" }, "Une copie exacte de toute la base (Goldmine, Testing, Agile, Dynamite, Exploration…), datée, à votre "
      + "nom, gardée pour toujours. Numéro vide = " + data.next + " (+1). À la main : revX.XX, toujours plus grand que "
      + (data.last || "rev0.00") + " (rev1.1 = rev1.10). Un numéro ne revient jamais en arrière."),
    el("div", { class: "form-row" }, field("Numéro", number), field("Titre", title)), field("Motif", note), error,
    el("div", { class: "form-actions tt-left" }, submit));
  }

  function listTable(data, reload) {
    if (!data.baselines.length) return el("div", { class: "empty" }, el("p", null, "Aucune révision pour l'instant."
      + (data.can_create ? " Figez la première ci-dessus : elle sera rev1.00." : " Un administrateur fige la première.")));
    return table(["Révision", "Titre", "Figée le", "Par", "Taille", "Empreinte", "Contenu", ""], data.baselines.map((b) => el("tr",
      { class: b.label === data.view ? "bl-current" : null },
      el("td", null, el("strong", null, b.label)),
      el("td", null, b.title, b.note ? el("div", { class: "muted bl-note" }, b.note) : null),
      el("td", null, b.local), el("td", null, b.by + (b.initials ? " (" + b.initials + ")" : "")),
      el("td", { "data-tip": "Brut : " + mb(b.bytes_raw) }, mb(b.bytes)),
      el("td", null, el("code", { "data-tip": b.sha256 }, short(b.sha256))),
      el("td", null, b.spaces.length + " Spaces · " + b.rows.toLocaleString("fr-CA") + " lignes"),
      el("td", { class: "bl-actions" },
        b.label === data.view ? el("span", { class: "badge badge-ok" }, "✓ Vous y êtes")
          : el("button", { type: "button", class: "btn btn-small", onclick: () => setView(b.label) }, "Consulter"),
        data.can_create ? el("button", { type: "button", class: "link-btn", onclick: async () => {
          try {
            const r = await api.get("/api/baselines/" + b.label + "/verify");
            toast(r.ok ? b.label + " intacte (SHA-256 " + short(r.sha256) + "…)." : b.label + " : " + r.problems.join(" "), r.ok ? "success" : "error");
          } catch (err) { toast(err.message, "error"); }
        } }, "Vérifier") : null))));
  }

  async function register(box) {
    const q = el("input", { type: "search", class: "bl-search", placeholder: "Nom, initiales ou fichier", "aria-label": "Filtrer le registre" });
    const rows = el("div");
    const state = el("p", { class: "muted", role: "status" });
    const load = async () => {
      const d = await api.get("/api/baselines/extracts?q=" + encodeURIComponent(q.value));
      clear(rows);
      state.textContent = d.total + " extraction(s) au registre · " + (d.broken_at ? "⚠ chaîne rompue à la ligne " + d.broken_at
        + " : une ligne a été modifiée ou retirée." : "chaîne intacte ✓");
      state.className = d.broken_at ? "form-error" : "muted";
      rows.append(d.extracts.length ? table(["N°", "Date", "Par", "Révision", "Fichier", "Taille", "SHA-256"], d.extracts.map((e) => el("tr", null,
        el("td", null, String(e.n)), el("td", null, e.at), el("td", null, e.name + " (" + (e.initials || "—") + ")"),
        el("td", null, e.baseline ? el("strong", null, e.baseline) : el("span", { class: "muted" }, "hors révision" + (e.after ? " (après " + e.after + ")" : ""))),
        el("td", { class: "bl-file" }, e.file), el("td", null, mb(e.bytes)), el("td", null, el("code", { "data-tip": e.sha256 }, short(e.sha256))))))
        : el("p", { class: "muted" }, "Aucune extraction."));
    };
    q.addEventListener("input", () => { clearTimeout(q._t); q._t = setTimeout(load, 250); });
    box.append(el("h2", null, "Registre des extractions"),
      el("p", { class: "muted" }, "Chaque fichier Word, Excel, PowerPoint, CSV ou PDF construit par la plateforme : qui, quand, de quelle "
        + "révision (ou hors révision), son nom et son empreinte. Une ligne par fichier, chaînée à la précédente."),
      el("div", { class: "bl-toolbar" }, q, el("a", { class: "btn btn-small", href: "/api/baselines/extracts.csv" }, "Exporter le registre (CSV)")),
      state, rows);
    await load();
  }

  async function render(main) {
    const reload = () => window.dispatchEvent(new HashChangeEvent("hashchange"));
    const data = await api.get("/api/baselines");
    cache = data;
    main.append(el("div", { class: "page-head" }, el("h1", null, "Révisions de référence"),
      el("p", { class: "muted" }, "Des points de référence figés de toute la base, pour les revues de fin de phase (Lean Canvas, Concept Review, PDR / CDR, Validation Report) et pour "
        + "prouver ce qui est sorti vers un client à une date précise. « Consulter » montre tout le site tel qu'il était, en lecture "
        + "seule ; chaque export porte alors la révision dans son nom et dans son en-tête.")),
    el("p", { class: "bl-where" }, data.view ? "Vous consultez " + data.view + " (lecture seule). " : "Vous travaillez sur la base courante. ",
      data.view ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => setView("") }, "Revenir à la base courante") : null),
    data.can_create ? createForm(data, reload) : null,
    el("h2", null, "Révisions"), listTable(data, reload),
    el("p", { class: "muted bl-where" }, "Sur le serveur : " + data.folder + " · " + data.baselines.length + " révision(s), "
      + mb(data.bytes_total) + " au total. Jamais effacées ; les pièces jointes ne sont pas recopiées (elles ne changent jamais)."));
    if (data.can_create) {
      const box = el("section", { class: "bl-register", "data-new": "0.50.11-baseline-register" });
      main.append(box);
      await register(box);
    }
  }

  BL.render = render;
  DA.coreViews = DA.coreViews || {};
  DA.coreViews.revisions = (main) => render(main).catch((err) => main.append(el("p", { class: "form-error" }, err.message)));
})();
