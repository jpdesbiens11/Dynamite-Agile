/* Diamond · « Exporter » on a screen (0.60.50, D-O-059): the diagram and the table of the screen in view, without going
   through the Exporter page. D.exportMenu(ctx, "tree" | "structure") -> a small menu: draw.io (the diagram, editable),
   PowerPoint (the diagram as slides, shapes and connectors editable), Excel (the table), and a link to the full Exporter. */
(function () {
  "use strict";

  const { el } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  const ITEMS = [
    ["drawio", "draw.io", "Le diagramme, modifiable (diagrams.net)"],
    ["pptx", "PowerPoint", "Le diagramme en diapositives : formes et flèches modifiables"],
    ["xlsx", "Excel", "Le tableau, mis en forme et prêt à imprimer"],
  ];

  function exportMenu(ctx, only) {
    const menu = el("div", { class: "dm-export-menu", role: "menu" },
      ITEMS.map(([ext, label, hint]) => el("a", { href: D.base(ctx) + "/export." + ext + "?only=" + only, download: "", role: "menuitem",
        class: "dm-export-item", "data-new": "0.60.50-export-" + only + "-" + ext },
      el("strong", null, label), el("span", { class: "muted" }, hint))),
      el("a", { href: A.href(ctx, "dexport"), role: "menuitem", class: "dm-export-item dm-export-all" },
        el("strong", null, "Tout Diamond…"), el("span", { class: "muted" }, "Tous les diagrammes et tableaux, et le rapport Word")));
    const box = el("details", { class: "dm-export", "data-new": "0.60.50-export-" + only },
      el("summary", { class: "btn btn-small", "aria-haspopup": "menu" }, "Exporter ▾"), menu);
    const close = (ev) => {
      if (!box.isConnected) { document.removeEventListener("click", close); return; }
      if (box.open && (ev.type === "keydown" ? ev.key === "Escape" : !box.contains(ev.target))) box.open = false;
    };
    document.addEventListener("click", close);
    box.addEventListener("keydown", close);
    menu.addEventListener("click", (ev) => { if (ev.target.closest("a")) box.open = false; });
    return box;
  }

  D.exportMenu = exportMenu;
})();
