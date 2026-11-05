/* Diamond · « Exporter » (0.60.33, D-O-041): #/diamond/KEY/dexport. The three files of the Space's functional analysis,
   made to be shown (a teacher, a jury, an investor) and to feed a Word or PowerPoint presentation:
   Excel -- every table; draw.io -- every diagram, editable; Word -- the report (Save as PDF in Word). Each carries the
   mark « DynamiteAgile · Co-Intelligence WorkFlow™ »; Excel and Word are also stamped with the revision (core). */
(function () {
  "use strict";

  const { el } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  const FILES = [
    ["xlsx", "Tableaux", "Excel (.xlsx)", "Chaque tableau, complet et mis en forme : synthèse, arbre fonctionnel, structure (entrées, sorties, "
      + "flux), pièces × fonctions, risques projet et carte P × I, DFMEA AIAG-VDA avec ses bonnes pratiques et ses essais clés.",
    ["Prêt à imprimer : paysage, ajusté à la largeur", "Couleurs des niveaux, des AP et des risques", "Filtres et volets figés"]],
    ["drawio", "Diagrammes", "draw.io (.drawio)", "Les diagrammes, une page chacun et modifiables : l'arbre fonctionnel, la structure "
      + "fonctionnelle (vue générale et vue détaillée), la carte des risques maintenant et résiduelle — avec leur légende.",
    ["Ouvrir dans draw.io (diagrams.net, application ou web)", "Fichier → Exporter en PNG ou SVG", "Puis Insertion → Image dans Word ou PowerPoint"]],
    ["pptx", "Diapositives", "PowerPoint (.pptx)", "Les mêmes diagrammes en diapositives, avec des formes et des flèches natives : "
      + "on les déplace, les recolore et les retape dans PowerPoint, Keynote, LibreOffice ou Google Slides. Un grand arbre est "
      + "découpé : vue d'ensemble, puis une diapositive par branche.",
    ["Diapositive de titre, puis un diagramme par diapositive", "Les flèches suivent les blocs qu'on déplace",
      "Les vues denses se lisent en zoomant (vectoriel)"], "0.60.50"],
    ["docx", "Rapport", "Word (.docx)", "Le rapport de l'analyse fonctionnelle : page de titre, table des matières, synthèse, arbre, structure, "
      + "pièces, risques, DFMEA, ce qu'une revue demanderait, et les fichiers joints.",
    ["Gabarit de la plateforme, en-tête et pied de page", "Fichier → Enregistrer sous → PDF", "Mettre à jour la table des matières (F9)"]],
  ];

  function view(page, ctx) {
    const cards = FILES.map(([ext, kind, label, what, tips, since]) => el("article", { class: "dm-ex-card", "data-new": (since || "0.60.33") + "-export-" + ext },
      el("p", { class: "dm-ex-kind" }, kind),
      el("h2", null, label),
      el("p", null, what),
      el("ul", { class: "dm-ex-tips" }, tips.map((t) => el("li", null, t))),
      el("a", { class: "btn btn-primary", href: D.base(ctx) + "/export." + ext, download: "" }, "Télécharger " + label.split(" ")[0])));
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Exporter")]),
      el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.33-export" }, "Exporter Diamond"),
        el("p", { class: "muted" }, "Toute l'analyse fonctionnelle du Space « " + ctx.meta.project.name + " », en quatre fichiers faits pour "
          + "être montrés : les tableaux dans Excel, les diagrammes dans draw.io ou PowerPoint, le rapport dans Word. Chacun porte la marque "
          + "« DynamiteAgile · Co-Intelligence WorkFlow™ » ; Excel et Word portent aussi la révision des données.")),
      el("div", { class: "dm-ex-grid" }, cards),
      el("p", { class: "muted dm-ex-note" }, "Les Golden Nuggets sont le texte de référence de l'outil, pas le contenu du Space : ils "
        + "restent dans Diamond → Golden Nuggets."));
  }

  A.views.dexport = view;
})();
