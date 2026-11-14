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
    nav: [["story", "Storyline"], ["ftree", "Arbre fonctionnel"], ["fstructure", "Structure fonctionnelle"], ["prisk", "Risques projet"], ["dfmea", "DFMEA"], ["chars", "Caractéristiques"], ["process", "Procédés"], ["pfmea", "PFMEA"], ["cplans", "Plans de contrôle"], ["prio", "Prioriser"], ["costs", "Coûts et budget"], ["nuggets", "Golden Nuggets"], ["dexport", "Exporter"]],  // 0.60.13 to 0.60.16, 0.60.33; Storyline 0.60.51; Coûts et budget 0.60.61; Caractéristiques 0.60.102; Procédés, PFMEA, Plans de contrôle, Prioriser 0.60.103
  };

  DA.diamond = Object.assign(DA.diamond || {}, {
    SHELL,
    base: (ctx) => "/api/diamond/p/" + ctx.pid,
    // redraw after the event that asked for it (never inside its own handler), the page staying where it was (0.60.23)
    later: (fn) => setTimeout(() => DA.keepScroll(fn), 0),
  });

  /* 0.60.103 (D-O-111): the parts an administrator turned off leave the left menu (⚙ Admin → Modules et fonctions) */
  const PART = { process: "diamond_process", pfmea: "diamond_pfmea", cplans: "diamond_cplans" };
  const on = (key) => !PART[key] || !DA.session.features || DA.session.features[PART[key]] !== false;
  DA.registerModule("diamond", (main, parts) => DA.agile.render(main, parts, Object.assign({}, SHELL, { nav: SHELL.nav.filter(([k]) => on(k)) })));
})();
