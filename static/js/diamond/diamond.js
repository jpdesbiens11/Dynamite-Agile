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
    nav: [["ftree", "Arbre fonctionnel"], ["fstructure", "Structure fonctionnelle"], ["prisk", "Risques projet"], ["dfmea", "DFMEA"]],  // 0.60.13 to 0.60.15
  };

  DA.diamond = Object.assign(DA.diamond || {}, {
    SHELL,
    base: (ctx) => "/api/diamond/p/" + ctx.pid,
    later: (fn) => setTimeout(fn, 0),  // redraw after the event that asked for it (never inside its own handler)
  });

  DA.registerModule("diamond", (main, parts) => DA.agile.render(main, parts, SHELL));
})();
