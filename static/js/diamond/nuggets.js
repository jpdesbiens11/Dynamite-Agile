/* Diamond · « Golden Nuggets » (0.60.16, D-O-028; four parts on one layout, 0.60.121, D-O-134): #/diamond/KEY/nuggets.
   Four parts, the same card everywhere: 20 first principles in the spirit of TRIZ, the 5-step design « algorithm » Elon Musk
   has described for SpaceX and Tesla, their design rules, and « Disruptive Innovation » -- the principles of Clayton
   Christensen, then the reference, a summary of the book and its case studies. A card = its code, its colour family, the
   idea; « Exemple et application » opens the example and how to use it. Search, family chips, « Tout déplier ». Static
   content (nuggets_content.js, nuggets_disruption.js); el() only. */
(function () {
  "use strict";

  const { el, clear } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const TAGS = { "coût": "cost", ressources: "cost", "matériaux": "cost", "méthode": "method", exigences: "method", simplifier: "method",
    architecture: "arch", "intégrer": "arch", interfaces: "arch", commande: "arch", fabrication: "make", "procédé": "make", assemblage: "make",
    essais: "test" };
  const SPX = "Méthodes décrites publiquement par Elon Musk, SpaceX et Tesla (entrevues, visite de Starbase de 2021). Résumés écrits pour la formation, pas des citations.";

  function parts() {
    const N = D.NUGGETS;
    return [
      { key: "principles", label: "First Principles", code: "P", items: N.PRINCIPLES, fam: (it) => TAGS[it.tag] || "method",
        fams: [["cost", "Coût et matières", 1], ["method", "Méthode", 2], ["arch", "Architecture", 3], ["make", "Fabrication", 4], ["test", "Essais", 5]],
        labels: ["Dans l'industrie", "Sur votre projet"], title: "Penser à partir des premiers principes",
        lead: "Ramener un problème à ce que la physique et les coûts imposent vraiment, puis reconstruire la solution : vingt principes dans l'esprit de TRIZ, chacun avec un exemple de l'industrie.",
        source: "Principes inventifs de TRIZ (G. Altshuller) et méthodes décrites publiquement par SpaceX et Tesla. Résumés écrits pour la formation, pas des citations." },
      { key: "algorithm", label: "L'algorithme en 5 étapes", code: "A", items: N.ALGORITHM, fam: (it, i) => (i < 2 ? "cut" : i < 3 ? "simplify" : "speed"),
        fams: [["cut", "Questionner et supprimer", 6], ["simplify", "Simplifier", 2], ["speed", "Accélérer et automatiser", 5]],
        labels: ["Exemple", "Sur votre projet"], title: "L'algorithme de conception en 5 étapes",
        lead: "Dans cet ordre, et seulement dans cet ordre : l'erreur la plus fréquente est d'automatiser, d'accélérer ou d'optimiser une pièce ou un procédé qu'il aurait fallu supprimer.",
        source: SPX },
      { key: "rules", label: "Règles SpaceX et Tesla", code: "R", items: N.RULES, fam: (it, i) => ["design", "make", "make", "test", "team"][i] || "design",
        fams: [["design", "Conception", 3], ["make", "Fabrication", 4], ["test", "Essais", 5], ["team", "Organisation", 7]],
        labels: ["Exemple", "Sur votre projet"], title: "Les règles de conception de SpaceX et Tesla",
        lead: "Cinq règles de conception tirées des mêmes méthodes : moins de pièces, l'usine conçue comme un produit, des essais jusqu'à la rupture, un responsable par pièce.",
        source: SPX },
      { key: "disruption", label: "Disruptive Innovation", code: "D", items: N.DISRUPTION, fam: (it) => it.fam, isNew: true,
        fams: [["market", "Marché et technologie", 3], ["customer", "Clients", 1], ["org", "Organisation", 2], ["act", "Agir en entreprise", 5], ["case", "Études de cas", 8]],
        labels: ["Exemple", "En entreprise aujourd'hui"], title: "Disruptive Innovation : les principes de Clayton Christensen, toujours valables",
        lead: "Pourquoi des entreprises bien gérées perdent face à des produits plus simples et moins chers, et ce qu'une entreprise fait pour innover sans se faire dépasser : les concepts, puis les pratiques à appliquer, puis le livre et ses études de cas.",
        source: "Clayton M. Christensen et ses co-auteurs (références plus bas). Résumés écrits pour la formation, pas des citations." },
    ];
  }

  function view(page, ctx) {
    const PARTS = parts();
    const state = { part: "principles", q: "", fam: "", open: false };
    const holder = el("div", { class: "dm-page dm-nug-page" });
    const toggle = el("button", { type: "button", class: "btn", "data-new": "0.60.121-nuggets-expand",
      onclick: () => { state.open = !state.open; draw(); } });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Golden Nuggets")], toggle),
      el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.16-nuggets" }, "Golden Nuggets"),
        el("p", { class: "muted" }, "Les grands principes à appliquer pour concevoir et innover : penser à partir des premiers principes, "
          + "l'algorithme de conception et les règles de SpaceX et Tesla, et la disruptive innovation de Clayton Christensen. "
          + "Chaque carte donne l'idée ; « Exemple et application » montre un cas de l'industrie et ce qu'elle donne sur votre projet.")),
      holder);
    const search = el("input", { type: "search", placeholder: "Chercher : coût, client, pièce, marché…", "aria-label": "Chercher un nugget" });
    search.addEventListener("input", () => { state.q = search.value.trim().toLowerCase(); draw(); });
    const draw = () => {
      const part = PARTS.find((p) => p.key === state.part);
      toggle.textContent = state.open ? "Tout replier" : "Tout déplier";
      clear(holder);
      holder.append(el("nav", { class: "subtabs", "aria-label": "Parties" }, PARTS.map((p) => el("a", { href: "#",
        class: "subtab" + (state.part === p.key ? " active" : ""), "aria-current": state.part === p.key ? "page" : null,
        "data-new": p.isNew ? "0.60.121-nuggets-disruption" : null,
        onclick: (ev) => { ev.preventDefault(); state.part = p.key; state.fam = ""; draw(); } },
      p.label, el("span", { class: "dm-nug-count" }, String(p.items.length + (p.key === "disruption" ? D.NUGGETS.CASES.length : 0)))))),
      el("div", { class: "dm-nug-lead" }, el("h2", null, part.title), el("p", null, part.lead), el("p", { class: "dm-nug-source" }, part.source)),
      el("div", { class: "dm-actions dm-nug-bar" }, search, chips(part, state, draw)));
      const hit = (item) => !state.q || [item.title, item.idea, item.example, item.apply, item.triz, item.sector].join(" ").toLowerCase().includes(state.q);
      const list = part.items.map((item, i) => Object.assign({ code: part.code + (i + 1), family: part.fam(item, i) }, item))
        .filter((item) => (!state.fam || item.family === state.fam) && hit(item));
      const cases = part.key !== "disruption" || (state.fam && state.fam !== "case") ? []
        : D.NUGGETS.CASES.map((item, i) => ({ code: "C" + (i + 1), family: "case", title: item.title, sector: item.sector,
          idea: item.apply, example: item.example })).filter(hit);  // a case shows its lesson, and opens on what happened
      if (list.length) holder.append(el("div", { class: "dm-nug-grid" }, list.map((item) => card(item, part, state))));
      if (part.key === "disruption" && !state.q && !state.fam) holder.append(D.nuggetBook(D.NUGGETS.BOOK));
      if (cases.length) {
        holder.append(el("h2", { class: "dm-nug-h2" }, "Les études de cas du livre (" + cases.length + ")"),
          el("div", { class: "dm-nug-grid" }, cases.map((item) => card(item, Object.assign({}, part, { labels: ["Ce qui s'est passé", "", "Ce qui s'est passé"] }), state))));
      }
      if (!list.length && !cases.length) holder.append(el("p", { class: "muted" }, "Aucun nugget pour « " + state.q + " ». Essayez un autre mot, ou « Tous »."));
      search.focus();
    };
    draw();
  }

  function chips(part, state, draw) {
    const count = (k) => (k === "case" ? D.NUGGETS.CASES.length : part.items.filter((it, i) => part.fam(it, i) === k).length);
    return el("div", { class: "dm-nug-tags", role: "group", "aria-label": "Familles" },
      [["", "Tous", 0]].concat(part.fams).map(([k, label, color]) => el("button", { type: "button",
        class: "dm-nug-tag" + (color ? " dm-c" + color : "") + (state.fam === k ? " active" : ""), "aria-pressed": state.fam === k ? "true" : "false",
        onclick: () => { state.fam = k; draw(); } }, color ? el("span", { class: "dm-nug-dot", "aria-hidden": "true" }) : null,
      label, k ? el("span", { class: "dm-nug-n" }, String(count(k))) : null)));
  }

  function card(item, part, state) {
    const fam = part.fams.find(([k]) => k === item.family) || part.fams[0];
    const [exLabel, applyLabel, moreLabel] = part.labels;
    const more = item.example || item.apply ? el("details", { class: "dm-nug-more", open: state.open },
      el("summary", null, moreLabel || (item.example && item.apply ? "Exemple et application" : item.example ? "Exemple" : "Application")),
      item.example ? el("p", { class: "dm-nug-ex" }, moreLabel ? null : el("strong", null, exLabel + ". "), item.example) : null,
      item.apply ? el("p", { class: "dm-nug-apply" }, el("strong", null, applyLabel + ". "), item.apply) : null) : null;
    return el("article", { class: "dm-nug dm-c" + fam[2] },
      el("div", { class: "dm-nug-top" }, el("span", { class: "dm-code" }, item.code),
        el("span", { class: "dm-nug-fam" }, el("span", { class: "dm-nug-dot", "aria-hidden": "true" }), item.sector || fam[1]),
        item.triz ? el("span", { class: "badge badge-neutral" }, item.triz) : null),
      el("h3", null, item.title.replace(/^\d+\.\s*/, "")),
      item.idea ? el("p", { class: "dm-nug-idea" }, item.idea) : null,
      more);
  }

  /* the reference, the sequels and the summary of the book, after the concepts (part « Disruptive Innovation ») */
  D.nuggetBook = function (book) {
    return el("section", { class: "dm-nug-book", "aria-label": "Le livre" },
      el("h2", { class: "dm-nug-h2" }, "Le livre et ses suites"),
      el("div", { class: "dm-nug-book-grid" },
        el("article", { class: "dm-nug dm-nug-ref dm-c7" },
          el("div", { class: "dm-nug-top" }, el("span", { class: "dm-nug-fam" }, el("span", { class: "dm-nug-dot", "aria-hidden": "true" }), "Référence")),
          el("h3", null, "The Innovator's Dilemma"), el("p", { class: "dm-nug-cite" }, book.reference), el("p", { class: "muted" }, book.author),
          el("h4", null, "Pour aller plus loin"), el("ul", { class: "dm-nug-refs" }, book.more.map((m) => el("li", null, m)))),
        el("article", { class: "dm-nug dm-c8" },
          el("div", { class: "dm-nug-top" }, el("span", { class: "dm-nug-fam" }, el("span", { class: "dm-nug-dot", "aria-hidden": "true" }), "Sommaire")),
          el("h3", null, "Le livre en bref"), book.summary.map((s) => el("p", null, s)))));
  };

  A.views.nuggets = view;
})();
