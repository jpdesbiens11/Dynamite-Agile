/* Diamond · one brick (0.60.105, D-O-117): #/diamond/KEY/concepts/CB-3. Its card (nature, reference, functions), then what hangs
   under it: its concept sheets (digital, AI, scanned paper -- concept_sheets.js) and the Pugh matrices that judge it with other
   bricks. « Générer avec l'IA » copies the prompt of its sheets; « Importer » brings the assistant's answer back. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function conceptPage(page, ctx) {
    const list = await api.get(D.base(ctx) + "/concepts");
    const found = list.concepts.find((c) => c.code.toUpperCase() === String(ctx.arg).toUpperCase());
    if (!found) {
      page.append(A.pageHead(ctx, [el("a", { href: A.href(ctx, "concepts") }, "Briques technologiques"), el("span", null, ctx.arg)]),
        el("div", { class: "empty" }, el("p", null, "Brique « " + ctx.arg + " » introuvable dans ce Space (archivée ?)."),
          el("a", { class: "btn", href: A.href(ctx, "concepts") }, "Toutes les briques")));
      return;
    }
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const state = { data: await api.get(D.base(ctx) + "/concepts/" + found.id) };
    state.reload = async () => {
      state.data = await api.get(D.base(ctx) + "/concepts/" + found.id);
      D.later(() => draw(holder, ctx, state));
    };
    draw(holder, ctx, state);
  }

  function draw(holder, ctx, state) {
    clear(holder);
    const { concept: c, sheets, functions, labels } = state.data;
    const editable = A.canEdit(ctx);
    const fns = c.function_ids.map((id) => functions.find((f) => f.id === id)).filter(Boolean);
    holder.append(A.pageHead(ctx, [el("a", { href: A.href(ctx, "concepts") }, "Briques technologiques"), el("span", null, c.code)], [
      el("a", { class: "btn btn-small", href: A.href(ctx, "ftree") }, "Voir dans l'arbre"),
      ...D.sheetAiButtons(ctx, c, editable, state.reload),
      editable ? el("button", { type: "button", class: "btn btn-small btn-primary",
        onclick: () => D.openPughCreate(ctx, state.data, sheets, [c.id]) }, "Nouvelle matrice de Pugh") : null]));
    holder.append(el("div", { class: "page-head dm-intro" },
      el("h1", null, el("span", { class: "dm-code dm-code-big" }, c.code), " " + (c.initial_name ? "« " + c.initial_name + " »" : c.name)),
      c.initial_name ? el("p", { class: "dm-cb-name" }, "Brique technologique : " + c.name) : null,
      c.selected_sheet ? el("p", { class: "dm-concept-landed" }, "Idée de départ → retenu : " + c.selected_sheet.code + " " + c.selected_sheet.title
        + (c.pivot_note ? ". Pivot : " + c.pivot_note : "")) : null,
      el("div", { class: "dm-cb-top" }, el("span", { class: "badge " + (c.kind === "existing" ? "badge-ok" : "badge-warn") }, labels.kinds[c.kind]),
        el("span", { class: "badge badge-neutral" }, labels.status[c.status]),
        c.source === "ai" ? el("span", { class: "badge badge-info" }, "Brouillon IA") : null),
      c.reference ? el("p", { class: "muted" }, "Concept existant : " + c.reference) : null,
      c.description ? el("p", null, c.description) : null));
    holder.append(el("section", { class: "dm-cb-section" }, el("h2", null, "Fonctions réalisées (" + fns.length + ")"),
      fns.length ? el("ul", { class: "dm-brick-fns" }, fns.map((f) => el("li", null, el("span", { class: "dm-code" }, "F" + f.number), " " + f.text,
        f.kano ? el("span", { class: "muted" }, " · " + labels.kano[f.kano]) : null)))
        : el("p", { class: "muted" }, "Aucune fonction : rattachez-les depuis l'arbre fonctionnel (panneau de la fonction).")));
    holder.append(D.sheetSection(ctx, state, editable));
    holder.append(el("section", { class: "dm-cb-section" }, el("h2", null, "Matrices de Pugh (" + c.pughs.length + ")"),
      c.pughs.length ? DA.table(["Matrice", "Tour", "Status"], c.pughs.map((m) => el("tr", null,
        el("td", null, el("a", { href: A.href(ctx, "pugh/" + m.id) }, m.title)), el("td", null, String(m.round)),
        el("td", null, el("span", { class: "badge pg-status-" + m.status }, m.status === "decided" ? "Décidée" : "In Progress")))))
        : el("p", { class: "muted" }, c.kind === "existing" ? "Une brique existante n'a souvent pas besoin de matrice."
          : "Quand les feuilles sont prêtes, jugez-les (avec celles des briques voisines) dans une matrice de Pugh.")));
    if (editable && c.kind === "to_define" && !sheets.length) toast("Ajoutez des feuilles de concept : numériques, avec l'IA ou scannées.", "info");
  }

  D.conceptPage = conceptPage;
})();
