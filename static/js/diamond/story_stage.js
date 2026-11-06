/* Diamond · Storyline (0.60.51, D-O-060): the stage of a scene and its tools.
   D.storyStage(items, opts) -> the 16:9 scene with its pictograms at x / y in percent: drag to move (saved on drop),
   click to select, Alt + arrows to nudge, Suppr to remove. opts.mini draws a small, inert copy for the board.
   D.storyTools(item, onChange) -> label, size, mirror and remove of the selected pictogram.
   D.storyPalette(onAdd) -> the pictograms by group, a click adds one in the middle of the scene. */
(function () {
  "use strict";

  const { el } = DA;
  const D = DA.diamond;
  const SIZES = [[1, "Petit"], [2, "Moyen"], [3, "Grand"]];

  function place(node, item) {
    node.style.left = item.x + "%";
    node.style.top = item.y + "%";
  }

  function storyStage(items, opts) {
    const stage = el("div", { class: "dm-story-stage" + (opts.mini ? " dm-story-mini" : ""), role: opts.mini ? null : "group",
      "aria-label": opts.mini ? null : "Scène : glissez les pictogrammes" });
    items.forEach((item, i) => {
      const node = el(opts.mini ? "span" : "button", {
        type: opts.mini ? null : "button", class: "dm-story-item dm-size-" + item.s + (item.f ? " dm-flip" : "") + (opts.selected === i ? " is-selected" : ""),
        "aria-label": opts.mini ? null : (D.PICTO_NAMES[item.p] || item.p) + (item.t ? " : " + item.t : ""), "aria-pressed": opts.mini ? null : String(opts.selected === i),
      }, D.picto(item.p), item.t ? el("span", { class: "dm-story-label" }, item.t) : null);
      place(node, item);
      if (!opts.mini) drag(node, stage, item, i, opts);
      stage.append(node);
    });
    if (!opts.mini && opts.editable) {
      stage.addEventListener("click", (ev) => { if (ev.target === stage) opts.onSelect(null); });
    }
    return stage;
  }

  function drag(node, stage, item, i, opts) {
    let start = null;
    node.addEventListener("pointerdown", (ev) => {
      if (!opts.editable || ev.button !== 0) return;
      const box = stage.getBoundingClientRect();
      start = { x: ev.clientX, y: ev.clientY, ix: item.x, iy: item.y, w: box.width, h: box.height, moved: false };
      node.setPointerCapture(ev.pointerId);
    });
    node.addEventListener("pointermove", (ev) => {
      if (!start) return;
      const dx = ev.clientX - start.x, dy = ev.clientY - start.y;
      if (!start.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      start.moved = true;
      item.x = Math.round(Math.min(100, Math.max(0, start.ix + dx / start.w * 100)) * 10) / 10;
      item.y = Math.round(Math.min(100, Math.max(0, start.iy + dy / start.h * 100)) * 10) / 10;
      place(node, item);
    });
    node.addEventListener("pointerup", () => {
      const was = start;
      start = null;
      if (was && was.moved) opts.onChange(i);
    });
    node.addEventListener("click", () => opts.onSelect(i));
    node.addEventListener("keydown", (ev) => {
      if (!opts.editable) return;
      if (ev.key === "Delete" || ev.key === "Backspace") { ev.preventDefault(); opts.onRemove(i); return; }
      const step = { ArrowUp: [0, -2], ArrowDown: [0, 2], ArrowLeft: [-2, 0], ArrowRight: [2, 0] }[ev.key];
      if (!ev.altKey || !step) return;
      ev.preventDefault();
      item.x = Math.min(100, Math.max(0, item.x + step[0]));
      item.y = Math.min(100, Math.max(0, item.y + step[1]));
      place(node, item);
      opts.onChange(i);
    });
  }

  function storyTools(item, onChange, onRemove) {
    const label = el("input", { type: "text", maxlength: "40", value: item.t || "", placeholder: "ex. Léa, 9 ans",
      "aria-label": "Étiquette du pictogramme" });
    label.addEventListener("change", () => { item.t = label.value.trim(); onChange(); });
    return el("div", { class: "dm-story-tools", "data-new": "0.60.51-story-tools" },
      el("span", { class: "dm-story-tools-name" }, D.picto(item.p), D.PICTO_NAMES[item.p] || item.p),
      el("label", { class: "dm-story-tools-label" }, "Étiquette ", label),
      el("div", { class: "dm-story-sizes", role: "group", "aria-label": "Taille" }, SIZES.map(([s, name]) => el("button", {
        type: "button", class: "btn btn-small", "aria-pressed": String(item.s === s), onclick: () => { item.s = s; onChange(); } }, name))),
      el("button", { type: "button", class: "btn btn-small", "aria-pressed": String(!!item.f),
        onclick: () => { item.f = item.f ? 0 : 1; onChange(); } }, "Miroir"),
      el("button", { type: "button", class: "btn btn-small", onclick: onRemove }, "Retirer"));
  }

  function storyPalette(onAdd) {
    return el("aside", { class: "dm-story-palette", "aria-label": "Pictogrammes", "data-new": "0.60.51-story-palette" },
      el("h2", null, "Pictogrammes"),
      el("p", { class: "muted" }, "Un clic l'ajoute au centre ; glissez-le ensuite où il va."),
      D.PICTO_GROUPS.map(([group, items]) => el("section", { class: "dm-story-group" }, el("h3", null, group),
        el("div", { class: "dm-story-grid" }, items.map(([key, name]) => el("button", { type: "button", class: "dm-story-pick",
          "data-tip": name, "aria-label": "Ajouter : " + name, onclick: () => onAdd(key) }, D.picto(key)))))));
  }

  DA.diamond = Object.assign(DA.diamond || {}, { storyStage, storyTools, storyPalette });
})();
