/* « Diamond » 💎 (0.60.11, D-O-023): functional analysis and design risk of a Space's product, 1 000 m deep in the mine.
   Agile shell (Space picker, left panel): #/diamond/KEY/ftree -> Arbre fonctionnel (tree.js),
   #/diamond/KEY/fstructure -> Structure fonctionnelle (structure.js, 0.60.13), #/diamond/KEY/prisk -> Risques projet (risks.js, 0.60.14),
   #/diamond/KEY/dfmea -> DFMEA and #/diamond/KEY/dfmeaap -> its AP legend (dfmea*.js, 0.60.15).
   The next sub-modules (structure fonctionnelle, risques projet, DFMEA, Golden Nuggets) add their entry to SHELL.nav. */
(function () {
  "use strict";

  const { el } = DA;
  const mark = () => el("img", { src: DA.mark("diamond"), alt: "", class: "ag-mark-img" });

  const SHELL = {
    module: "diamond", title: "Diamond", home: "ftree", issueNav: "ftree", noCreate: true, mark,
    headTools: (ctx) => (DA.diamond.rtButton ? DA.diamond.rtButton(ctx) : null),  // 0.60.111 (D-O-124): « ↔ IA » on every page
    /* 0.60.105 (D-O-117): pages in groups that fold; the Design tools of Tools (Idéation, Pugh, Kepner-Tregoe) now live under
       « Concept / Brique technologique », right after the functional structure */
    nav: [
      { group: "analysis", label: "Analyse fonctionnelle", items: [["story", "Storyline"], ["ftree", "Arbre fonctionnel"], ["fstructure", "Structure fonctionnelle"]] },
      { group: "concepts", label: "Concept / Brique technologique", items: [["concepts", "Briques technologiques"], ["csheets", "Feuilles de concept"],
        ["ideation", "Idéation"], ["pugh", "Matrices de Pugh"], ["kt", "Kepner-Tregoe"], ["competencies", "Compétences et équipe"]] },
      { group: "risk", label: "Risques et conception", items: [["prisk", "Risques projet"], ["dfmea", "DFMEA"], ["chars", "Caractéristiques"]] },
      { group: "industrial", label: "Industrialisation", open: false, items: [["process", "Procédés"], ["pfmea", "PFMEA"], ["cplans", "Plans de contrôle"], ["prio", "Prioriser"]] },
      { group: "project", label: "Projet", open: false, items: [["costs", "Coûts et budget"], ["nuggets", "Golden Nuggets"], ["dexport", "Exporter"]] },
    ],  // 0.60.13 to 0.60.16, 0.60.33; Storyline 0.60.51; Coûts 0.60.61; Caractéristiques 0.60.102; Procédés… 0.60.103; groups 0.60.105;
    // Compétences et équipe 0.60.116
  };

  DA.diamond = Object.assign(DA.diamond || {}, {
    SHELL,
    base: (ctx) => "/api/diamond/p/" + ctx.pid,
    // redraw after the event that asked for it (never inside its own handler), the page staying where it was (0.60.23)
    later: (fn) => setTimeout(() => DA.keepScroll(fn), 0),
  });

  /* 0.60.103 (D-O-111): the parts an administrator turned off leave the left menu (⚙ Admin → Modules et fonctions) */
  const PART = { process: "diamond_process", pfmea: "diamond_pfmea", cplans: "diamond_cplans", competencies: "diamond_competencies" };
  const on = (key) => !PART[key] || !DA.session.features || DA.session.features[PART[key]] !== false;
  DA.diamond.partOn = on;  // 0.60.116 (D-O-129): a page also uses it for a section it shows (the grid of the competencies in the tree)
  const nav = () => SHELL.nav.map((g) => Object.assign({}, g, { items: g.items.filter(([k]) => on(k)) })).filter((g) => g.items.length);
  DA.registerModule("diamond", (main, parts) => DA.agile.render(main, parts, Object.assign({}, SHELL, { nav: nav() })));
})();
