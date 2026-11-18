/* Diamond · « Compétences et équipe » (0.60.116, D-O-129): #/diamond/KEY/competencies. The sum of the grid of the tree: per
   competency, the lines that need it, its points (the ratings 1 to 5 added up), its share of the whole, its average, the lines
   at 4 or 5, and the last column the evaluator fills -- the people to hire or to gather. A team size gives the split the shares
   suggest. Each competency links to its page in the « Base de connaissances (BDC) ». Then the ratings line by line, and the
   platform's catalogue (competency_catalog.js). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function view(page, ctx) {
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const state = { comp: await api.get(D.base(ctx) + "/competencies"), team: null };
    state.redraw = () => D.later(() => draw(holder, ctx, state));
    state.save = async (body) => {
      try { state.comp = await api.put(D.base(ctx) + "/competencies/staff", body); toast("Enregistré.", "success"); }
      catch (err) { toast(err.message, "error"); }
      state.redraw();
    };
    state.profile = async (key) => {  // 0.60.119 (D-O-132): a profile of columns
      try { state.comp = await api.post(D.base(ctx) + "/competencies/profile", { profile: key }); toast("Profil appliqué.", "success"); }
      catch (err) { toast(err.message, "error"); }
      state.redraw();
    };
    state.reload = async () => { state.comp = await api.get(D.base(ctx) + "/competencies"); state.redraw(); };
    draw(holder, ctx, state);
  }

  function draw(holder, ctx, state) {
    clear(holder);
    const comp = state.comp;
    const editable = A.canEdit(ctx);
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Compétences et équipe")],
      [editable ? D.profilePicker(comp, state.profile) : null,
        el("a", { class: "btn btn-small", href: A.href(ctx, "ftree") }, "Noter dans l'arbre"),
        el("a", { class: "btn btn-small", href: D.base(ctx) + "/competencies/summary.xlsx", download: "", "data-new": "0.60.116-competencies-xlsx" }, "Excel"),
        el("a", { class: "btn btn-small", href: D.base(ctx) + "/competencies/summary.docx", download: "", "data-new": "0.60.116-competencies-docx" }, "Word")]));
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.116-competencies" }, "Compétences et équipe"),
      el("p", { class: "muted" }, "Les compétences qu'il faut pour développer les briques du produit, lues dans l'arbre fonctionnel : "
        + "chaque ligne fonction → brique note les compétences de 1 à 5. La part de chaque compétence dit quelle équipe bâtir ; "
        + "la dernière colonne dit combien de personnes embaucher ou réunir.")));
    if (!comp.lines.length) {
      holder.append(DA.spaces.startHere("Compétences de " + ctx.meta.project.name,
        "Aucune ligne à noter : dans l'arbre fonctionnel, donnez une brique technologique (CB-n) aux fonctions tertiaires. Chaque ligne "
        + "qui aboutit à une brique reçoit sa grille de compétences.", [["Ouvrir l'arbre fonctionnel", () => { location.hash = A.href(ctx, "ftree"); }, true]]));
    } else {
      holder.append(cards(comp), summary(comp, state, editable), detail(ctx, comp));
    }
    holder.append(D.competencyCatalog(ctx, comp, state.reload));
  }

  function cards(comp) {
    const rated = comp.lines.filter((ln) => Object.keys(ln.ratings).length).length;
    const card = (label, value) => el("div", { class: "dm-cp-card" }, el("span", { class: "muted" }, label), el("strong", null, value));
    return el("div", { class: "dm-cp-cards" }, card("Lignes notées", rated + " / " + comp.lines.length),
      card("Points au total", String(comp.total_points)), card("Compétences sollicitées", String(comp.summary.filter((s) => s.points).length)),
      card("Personnes à embaucher ou réunir", String(comp.people_total)));
  }

  const fmt = (n) => (Math.round(n * 10) / 10).toLocaleString("fr-CA");

  function summary(comp, state, editable) {
    const total = comp.people_total || 0;
    if (state.team === null) state.team = total;
    const team = el("input", { type: "number", min: 0, max: 999, step: 0.5, value: state.team, class: "dm-cp-num", "aria-label": "Taille d'équipe visée" });
    team.addEventListener("change", () => { state.team = Math.max(0, Number(team.value) || 0); state.redraw(); });
    const rows = comp.summary.map((s) => {
      const people = el("input", { type: "number", min: 0, max: 999, step: 0.5, value: s.people, class: "dm-cp-num",
        "aria-label": "Personnes à embaucher ou réunir — " + s.name, disabled: editable ? null : "disabled" });
      const note = el("input", { type: "text", maxlength: 300, value: s.note, placeholder: "Embauche, interne, stage, sous-traitance…",
        "aria-label": "Note — " + s.name, disabled: editable ? null : "disabled" });
      const save = () => state.save({ code: s.code, people: people.value, note: note.value });
      people.addEventListener("change", save);
      note.addEventListener("change", save);
      const bar = el("span", { class: "dm-cp-bar" }, el("span", null));
      bar.firstChild.style.width = Math.min(100, s.share) + "%";
      const cat = comp.catalog.find((c) => c.code === s.code) || {};
      return el("tr", null,
        el("td", { class: "dm-cp-name" }, D.compIcon(s.icon), cat.bdc ? el("a", { href: cat.bdc, "data-tip": "Profil, formation, outils et livrables (BDC)" }, s.name)
          : el("span", null, s.name), el("span", { class: "dm-code" }, " " + s.code)),
        el("td", { class: "num" }, String(s.lines)), el("td", { class: "num" }, String(s.points)),
        el("td", { class: "dm-cp-share" }, bar, el("span", null, fmt(s.share) + " %")), el("td", { class: "num" }, fmt(s.average)),
        el("td", { class: "num" }, String(s.high)),
        el("td", { class: "num muted" }, state.team ? fmt(Math.round(2 * state.team * s.share / 100) / 2) : "—"),
        el("td", { class: "dm-cp-people" }, people), el("td", null, note));
    });
    const table = DA.table(["Compétence", "Lignes", "Points", "Part", "Moyenne", "Notes 4–5", "Répartition suggérée", "À embaucher / réunir", "Note"], rows);
    table.classList.add("dm-cp-table");
    table.querySelector("table").append(el("tfoot", null, el("tr", null, el("th", null, "Total"), el("th", null, ""), el("th", { class: "num" }, String(comp.total_points)),
      el("th", null, "100 %"), el("th", null, ""), el("th", null, ""), el("th", { class: "num" }, state.team ? fmt(state.team) : "—"),
      el("th", { class: "num" }, fmt(total)), el("th", null, ""))));
    return el("section", { class: "dm-cb-section", "data-new": "0.60.116-competency-summary" }, el("h2", null, "Synthèse par compétence"),
      el("p", { class: "muted" }, "Points = somme des notes de la compétence sur les lignes. Part = ses points sur le total : le ratio "
        + "de l'équipe à bâtir. « Répartition suggérée » partage la taille d'équipe visée selon ces parts (par demi-personne) ; "
        + "« À embaucher / réunir » est votre décision."),
      el("div", { class: "dm-cp-team" }, DA.field("Taille d'équipe visée (personnes)", team, "Sert seulement au calcul de la répartition suggérée.")),
      comp.summary.length ? table : el("p", { class: "muted" }, "Aucune compétence notée : notez-les dans l'arbre, ou avec « ↔ IA »."));
  }

  function detail(ctx, comp) {
    const cols = D.competencyColumns(comp);
    if (!cols.length) return null;
    const head = ["Fonction", "Brique"].concat(cols.map((c) => el("span", { "data-tip": c.name }, D.compIcon(c.icon), el("span", { class: "dm-sr" }, c.name))));
    const rows = comp.lines.map((ln) => el("tr", null,
      el("td", null, el("span", { class: "dm-code" }, ln.code), " " + ln.text),
      el("td", null, el("span", { class: "dm-code" }, ln.brick.code), " " + (ln.brick.frozen ? ln.brick.frozen_text : ln.brick.name),
        ln.brick.frozen ? el("span", { class: "badge badge-ok" }, "Figée") : null),
      cols.map((c) => el("td", { class: "num dm-cg-" + (ln.ratings[c.code] || 0) }, ln.ratings[c.code] ? String(ln.ratings[c.code]) : "·"))));
    const table = DA.table(head, rows);
    table.classList.add("dm-cp-detail");
    return el("section", { class: "dm-cb-section" }, el("h2", null, "Notes par ligne"),
      el("p", { class: "muted" }, "Les mêmes notes que la grille de l'arbre. Pour les modifier : « Noter dans l'arbre »."), table);
  }

  A.views.competencies = view;
})();
