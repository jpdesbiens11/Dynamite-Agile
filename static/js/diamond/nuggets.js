/* Diamond · « Golden Nuggets » (0.60.16, D-O-028): #/diamond/KEY/nuggets. Guidelines to design from first principles:
   20 principles in the spirit of TRIZ with an industry example each, the 5-step design « algorithm » Elon Musk has
   described for SpaceX and Tesla, and their main design rules -- each with how to use it on the project, and a link to
   the Diamond / Tools screen where it applies. Static content (nuggets_content.js); a search box and theme chips. */
(function () {
  "use strict";

  const { el, clear } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const PARTS = [["principles", "First Principles Thinking (20)"], ["algorithm", "L'algorithme en 5 étapes"], ["rules", "Règles SpaceX et Tesla"]];

  function view(page, ctx) {
    const N = D.NUGGETS;
    const state = { part: "principles", q: "", tag: "" };
    const holder = el("div", { class: "dm-page" });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Golden Nuggets")]),
      el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.16-nuggets" }, "Golden Nuggets"),
        el("p", { class: "muted" }, "Penser à partir des premiers principes : ramener un problème à ce que la physique et les coûts "
          + "imposent vraiment, puis reconstruire la solution. Vingt principes dans l'esprit de TRIZ, l'algorithme de conception "
          + "en cinq étapes qu'Elon Musk décrit pour SpaceX et Tesla, et leurs règles de conception — chacun avec un exemple de "
          + "l'industrie et ce qu'il donne sur votre projet.")),
      el("p", { class: "dm-nug-source" }, "Sources : méthodes décrites publiquement par Elon Musk, SpaceX et Tesla (entrevues, visite de "
        + "Starbase de 2021), et principes inventifs de TRIZ (G. Altshuller). Résumés écrits pour la formation, pas des citations."),
      holder);
    const search = el("input", { type: "search", placeholder: "Chercher : coût, chaleur, pièce, essai…", "aria-label": "Chercher un nugget" });
    search.addEventListener("input", () => { state.q = search.value.trim().toLowerCase(); draw(); });
    const draw = () => {
      clear(holder);
      holder.append(el("nav", { class: "subtabs", "aria-label": "Parties" }, PARTS.map(([k, label]) => el("a", { href: "#",
        class: "subtab" + (state.part === k ? " active" : ""), "aria-current": state.part === k ? "page" : null,
        onclick: (ev) => { ev.preventDefault(); state.part = k; state.tag = ""; draw(); } }, label))),
      el("div", { class: "dm-actions dm-nug-bar" }, search, state.part === "principles" ? tags(N.PRINCIPLES, state, draw) : null));
      const list = (state.part === "principles" ? N.PRINCIPLES : state.part === "algorithm" ? N.ALGORITHM : N.RULES)
        .map((item, i) => Object.assign({ n: i + 1 }, item))
        .filter((item) => (!state.tag || item.tag === state.tag) && (!state.q || [item.title, item.idea, item.example, item.apply, item.triz]
          .join(" ").toLowerCase().includes(state.q)));
      holder.append(list.length ? el("div", { class: state.part === "algorithm" ? "dm-nug-steps" : "dm-nug-grid" },
        list.map((item) => card(item, state.part, ctx))) : el("p", { class: "muted" }, "Aucun nugget pour « " + state.q + " »."));
      if (state.part === "algorithm") {
        holder.append(el("p", { class: "dm-advice" }, el("strong", null, "L'ordre compte. "), "L'erreur la plus fréquente est de faire les "
          + "étapes à l'envers : automatiser, accélérer et optimiser une pièce ou un procédé qu'il aurait fallu supprimer."));
      }
      search.focus();
    };
    draw();
  }

  function tags(items, state, draw) {
    const all = [...new Set(items.map((i) => i.tag))];
    return el("div", { class: "dm-nug-tags", role: "group", "aria-label": "Thèmes" }, [["", "Tous"]].concat(all.map((t) => [t, t])).map(([t, label]) =>
      el("button", { type: "button", class: "dm-nug-tag" + (state.tag === t ? " active" : ""), "aria-pressed": state.tag === t ? "true" : "false",
        onclick: () => { state.tag = t; draw(); } }, label)));
  }

  function card(item, part, ctx) {
    return el("article", { class: "dm-nug" + (part === "algorithm" ? " dm-nug-step" : "") },
      el("div", { class: "dm-nug-top" }, part === "algorithm" ? null : el("span", { class: "dm-code" }, (part === "rules" ? "R" : "") + item.n),
        el("h3", null, item.title), item.triz ? el("span", { class: "badge badge-neutral" }, item.triz) : item.tag ? el("span", { class: "badge badge-info" }, item.tag) : null),
      el("p", null, item.idea),
      item.example ? el("p", { class: "dm-nug-ex" }, el("strong", null, "Dans l'industrie. "), item.example) : null,
      el("p", { class: "dm-nug-apply" }, el("strong", null, "Sur votre projet. "), item.apply));
  }

  A.views.nuggets = view;
})();
