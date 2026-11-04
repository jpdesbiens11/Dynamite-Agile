/* Codex - shared helpers and the « Registre » view (D-B-021): every
   reference reserved in the project, searchable, with revision, voiding
   (administrators) and CSV export. Loaded before codex.js. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field, formatDate } = DA;
  const CX = (DA.codex = DA.codex || {});

  CX.base = (ctx) => "/api/codex/p/" + ctx.pid;

  /* Metadata (types, steps of the PDP) served by the module: one source of truth. */
  CX.loadMeta = async function () {
    if (!CX.meta) {
      const meta = await api.get("/api/codex/meta");
      meta.types = {};
      (meta.retired_types || []).forEach((t) => { meta.types[t.code] = t; });  // references already issued (D-B-109)
      meta.doc_groups.forEach((g) => g.types.forEach((t) => { meta.types[t.code] = t; }));
      meta.steps = {};
      meta.step_groups.forEach((g) => g.steps.forEach((c) => { meta.steps[c.step] = c; }));
      CX.meta = meta;
    }
    return CX.meta;
  };

  /* Copy to the clipboard. navigator.clipboard needs HTTPS (or localhost):
     on the internal network over plain HTTP, fall back to a hidden field. */
  CX.copy = async function (text, button) {
    let ok = false;
    try {
      if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); ok = true; }
    } catch (err) { ok = false; }
    if (!ok) {
      const area = el("textarea", { class: "cx-clip", readonly: true, "aria-hidden": "true" });
      area.value = text;
      document.body.append(area);
      area.select();
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
      area.remove();
    }
    if (!ok) { toast("Copie impossible : sélectionnez le texte et faites Ctrl+C.", "error"); return; }
    if (button) {
      const label = button.textContent;
      button.textContent = "✓ Copié";
      button.classList.add("cx-copied");
      setTimeout(() => { button.textContent = label; button.classList.remove("cx-copied"); }, 1500);
    }
  };

  CX.copyButton = (text, label) => {
    const b = el("button", { type: "button", class: "btn btn-small cx-copy" }, label || "Copier");
    b.addEventListener("click", () => CX.copy(typeof text === "function" ? text() : text, b));
    return b;
  };

  /* D-B-106: Project ID of a Space -- its name in capitals when it is one word (Pistolet -> PISTOLET), else its key (EQP) */
  CX.projectId = (project) => {
    const name = String((project && project.name) || "").trim();
    return /^[A-Za-z0-9-]{2,20}$/.test(name) ? name.toUpperCase() : String((project && project.key) || "");
  };

  CX.statusBadge = (ref) => el("span", { class: "badge cx-status cx-status-" + ref.status }, ref.status_label);

  /* ---------- Edit (title, system, revision) ---------- */
  function editDialog(ctx, ref, reload) {
    const title = el("input", { type: "text", value: ref.title, maxlength: 150 });
    const system = el("input", { type: "text", value: ref.system_code, maxlength: 20, placeholder: "ex. CHAUF" });
    const revision = el("input", { type: "number", value: ref.revision, min: ref.revision, max: 99 });
    let close = null;
    async function save(ev) {
      ev.preventDefault();
      try {
        await api.patch(CX.base(ctx) + "/refs/" + ref.id,
          { title: title.value, system_code: system.value, revision: Number(revision.value) });
        close();
        toast("Référence " + ref.reference + " mise à jour.", "success");
        reload();
      } catch (err) { toast(err.message, "error"); }
    }
    const form = el("form", { class: "form", onsubmit: save },
      el("p", { class: "muted" }, "Le numéro " + ref.reference + " ne change jamais. La révision ne peut qu'augmenter."),
      field("Titre du document", title),
      field("Code système", system, "Lettres, chiffres et tirets (ex. CHAUF, SS-02)."),
      field("Révision", revision, "Nouvelle révision : augmentez ce nombre."),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Modifier " + ref.reference, form);
  }

  function voidDialog(ctx, ref, reload) {
    const reason = el("input", { type: "text", maxlength: 300, required: true,
      placeholder: "Ex. doublon de ICD-46290-50000, document abandonné…" });
    let close = null;
    async function save(ev) {
      ev.preventDefault();
      try {
        await api.patch(CX.base(ctx) + "/refs/" + ref.id, { status: "void", void_reason: reason.value });
        close();
        toast("Référence " + ref.reference + " annulée : son numéro ne sera jamais réutilisé.", "success");
        reload();
      } catch (err) { toast(err.message, "error"); }
    }
    const form = el("form", { class: "form", onsubmit: save },
      el("p", null, "La référence reste au registre, marquée « Annulée ». Son numéro n'est jamais réattribué."),
      field("Motif", reason),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Retour"),
        el("button", { type: "submit", class: "btn btn-danger" }, "Annuler la référence")));
    close = modal("Annuler " + ref.reference, form);
  }

  async function restore(ctx, ref, reload) {
    try {
      await api.patch(CX.base(ctx) + "/refs/" + ref.id, { status: "active" });
      toast("Référence " + ref.reference + " rétablie.", "success");
      reload();
    } catch (err) { toast(err.message, "error"); }
  }

  /* ---------- Registry view ---------- */
  CX.registryView = function (page, ctx, reload) {
    const data = ctx.data;
    const meta = CX.meta;
    const search = el("input", { type: "search", placeholder: "Rechercher : référence, titre, système, auteur…",
      "aria-label": "Rechercher dans le registre", class: "cx-search", value: ctx.initialQuery || null });
    const typeSel = el("select", { "aria-label": "Filtrer par type" }, el("option", { value: "" }, "Tous les types"),
      Object.keys(meta.types).sort().map((c) => el("option", { value: c }, c)));
    const stepSel = el("select", { "aria-label": "Filtrer par étape du PDP" }, el("option", { value: "" }, "Toutes les étapes"),
      Object.keys(meta.steps).sort().map((c) => el("option", { value: c }, c + " — " + meta.steps[c].name)));
    const showVoid = el("input", { type: "checkbox" });
    const count = el("span", { class: "muted" });
    const holder = el("div");

    page.append(
      el("div", { class: "page-head" }, el("h1", null, "Registre — " + ctx.project.name),
        el("p", { class: "muted" }, "Toutes les références réservées dans ce projet. Un numéro n'est jamais réutilisé.")),
      el("div", { class: "cx-toolbar" }, search, typeSel, stepSel,
        el("label", { class: "check" }, showVoid, "Afficher les annulées"), count, el("span", { class: "cx-spacer" }),
        el("a", { class: "btn", href: CX.base(ctx) + "/export.csv", download: "" }, "Exporter CSV"),
        data.can_edit ? el("a", { class: "btn btn-primary", href: "#/codex/" + ctx.key + "/generer" }, "+ Nouvelle référence") : null),
      holder);

    function matches(ref) {
      if (!showVoid.checked && ref.status === "void") return false;
      if (typeSel.value && ref.doc_type !== typeSel.value) return false;
      if (stepSel.value && ref.pdp_step !== stepSel.value) return false;
      const q = search.value.trim().toLowerCase();
      if (!q) return true;
      return [ref.reference, ref.title, ref.system_code, ref.file_name, ref.created_by_name, ref.type_name]
        .some((v) => String(v || "").toLowerCase().includes(q));
    }

    function draw() {
      clear(holder);
      const refs = data.refs.filter(matches);
      count.textContent = refs.length + " / " + data.refs.length + " référence(s)";
      if (!data.refs.length) {
        holder.append(el("div", { class: "empty" }, el("p", null, "Aucune référence réservée dans ce projet."),
          data.can_edit ? el("a", { class: "btn btn-primary", href: "#/codex/" + ctx.key + "/generer" }, "Générer une référence") : null));
        return;
      }
      const rows = refs.map((ref) => el("tr", { class: ref.status === "void" ? "cx-void" : null },
        el("td", { class: "cx-mono cx-ref" }, ref.reference),
        el("td", { class: "cx-num" }, String(ref.revision)),
        el("td", { title: ref.type_name }, ref.doc_type),
        el("td", { class: "cx-nowrap", title: (meta.steps[ref.pdp_step] || {}).name || "" },
          ref.pdp_step + "-" + ref.pdp_sub),
        el("td", null, ref.system_code || "—"),
        el("td", { class: "cx-title" }, ref.title || el("span", { class: "muted" }, "(sans titre)"),
          ref.void_reason ? el("div", { class: "muted cx-small" }, "Annulée : " + ref.void_reason) : null),
        el("td", { class: "cx-mono cx-small", title: ref.svn_path }, ref.folder),
        el("td", { class: "cx-small" }, ref.created_by_name || "—", el("br"), formatDate(ref.created_at)),
        el("td", null, CX.statusBadge(ref)),
        el("td", { class: "cx-actions" },
          CX.copyButton(ref.file_name, "Nom"),
          CX.copyButton(ref.svn_path, "Dossier"),
          data.can_edit && ref.status === "active"
            ? el("button", { type: "button", class: "btn btn-small", onclick: () => editDialog(ctx, ref, reload) }, "Modifier…") : null,
          data.can_void && ref.status === "active"
            ? el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => voidDialog(ctx, ref, reload) }, "Annuler…") : null,
          data.can_void && ref.status === "void"
            ? el("button", { type: "button", class: "btn btn-small", onclick: () => restore(ctx, ref, reload) }, "Rétablir") : null)));
      holder.append(DA.table(["Référence", "Rév.", "Type", "Étape", "Système", "Titre", "Dossier", "Réservée par",
        "Status", "Copier / actions"], rows.length ? rows : []));
    }

    [search, typeSel, stepSel, showVoid].forEach((c) => c.addEventListener("input", draw));
    [typeSel, stepSel, showVoid].forEach((c) => c.addEventListener("change", draw));
    draw();
    search.focus();
  };
})();
