/* Goldmine - top tab for engineering requirements (D-B-011): "the
   requirements are the raw, unrefined ore". Same data and screens as the
   requirement matrix (static/js/agile/goldmine.js) and ticket page, in a
   shell of its own: project picker, requirements, requirement import/export.
   Agile scripts are loaded before this one (MODULE_MANIFEST order). */
(function () {
  "use strict";

  const A = DA.agile;

  /* Goldmine logo supplied by the user (miners in a cave), on white,
     served locally (D-B-013). */
  function goldmineMark() {
    return DA.el("img", { src: DA.mark("goldmine"), alt: "", class: "gm-mark-img" });
  }

  const GOLDMINE_SHELL = {
    module: "goldmine", title: "Goldmine", home: "goldmine", issueNav: "goldmine",
    mark: goldmineMark,
    nav: [["goldmine", "Requirements et needs"], ["qa", "Q&A"], ["csv", "Import / Export"]],
  };

  DA.registerModule("goldmine", (main, parts) => A.render(main, parts, GOLDMINE_SHELL));
})();
