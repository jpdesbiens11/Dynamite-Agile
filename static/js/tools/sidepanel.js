/* Left panel of every module (D-A-040): width set by dragging its right edge, hidden / shown with the « ‹‹‹ » /
   « ››› » button. Applied automatically to each .ag-layout (Agile, Goldmine, Testing, Exploration, Timesheet, Tools,
   Help...) and .dy-layout (Dynamite page tree) -- no module code. The width and the hidden state are kept per kind of
   layout in this browser (per-viewer convenience; storage may be unavailable, the defaults then apply). */
(function () {
  "use strict";

  const KINDS = { "ag-layout": { key: "da-side-ag", width: 220 }, "dy-layout": { key: "da-side-dy", width: 250 } };
  const MIN = 160, MAX = 560;

  function load(kind) {
    try { return JSON.parse(localStorage.getItem(KINDS[kind].key) || "{}"); } catch (err) { return {}; }
  }
  function save(kind, state) {
    try { localStorage.setItem(KINDS[kind].key, JSON.stringify(state)); } catch (err) { /* private mode: not kept */ }
  }

  function apply(layout, kind, state) {
    const width = Math.min(MAX, Math.max(MIN, Number(state.width) || KINDS[kind].width));
    layout.style.setProperty("--side-w", width + "px");
    layout.classList.toggle("side-collapsed", !!state.hidden);
    const button = layout.querySelector(":scope > .side-toggle");
    if (button) {
      button.textContent = state.hidden ? ">>>" : "<<<";  // D-A-044: blue button, top-right corner of the panel
      button.title = state.hidden ? "Afficher le panneau de gauche" : "Masquer le panneau de gauche";
      button.setAttribute("aria-label", button.title);
      button.setAttribute("aria-expanded", String(!state.hidden));
    }
  }

  function enhance(layout) {
    if (layout.dataset.sidePanel) return;
    const kind = Object.keys(KINDS).find((k) => layout.classList.contains(k));
    const aside = layout.querySelector(":scope > aside");
    if (!kind || !aside) return;
    layout.dataset.sidePanel = "1";
    const state = load(kind);
    const button = DA.el("button", { type: "button", class: "side-toggle", onclick: () => {
      state.hidden = !state.hidden; save(kind, state); apply(layout, kind, state);
    } });
    const handle = DA.el("div", { class: "side-handle", role: "separator", "aria-orientation": "vertical",
      "aria-label": "Largeur du panneau de gauche (glisser ou flèches)", tabindex: "0",
      onkeydown: (ev) => {
        if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
        ev.preventDefault();
        state.width = Math.min(MAX, Math.max(MIN, (Number(state.width) || KINDS[kind].width) + (ev.key === "ArrowLeft" ? -20 : 20)));
        save(kind, state); apply(layout, kind, state);
      },
      onpointerdown: (ev) => {
        ev.preventDefault();
        const left = layout.getBoundingClientRect().left;
        layout.classList.add("side-resizing");
        const move = (e) => { state.width = Math.round(e.clientX - left); apply(layout, kind, state); };
        const up = () => {
          document.removeEventListener("pointermove", move);
          document.removeEventListener("pointerup", up);
          layout.classList.remove("side-resizing");
          save(kind, state);
        };
        document.addEventListener("pointermove", move);
        document.addEventListener("pointerup", up);
      },
      ondblclick: () => { delete state.width; save(kind, state); apply(layout, kind, state); } });
    layout.append(handle, button);
    apply(layout, kind, state);
  }

  function scan(root) {
    if (!(root instanceof Element)) return;
    Object.keys(KINDS).forEach((k) => {
      if (root.classList.contains(k)) enhance(root);
      root.querySelectorAll("." + k).forEach(enhance);
    });
  }

  new MutationObserver((records) => records.forEach((r) => r.addedNodes.forEach(scan)))
    .observe(document.documentElement, { childList: true, subtree: true });
})();
