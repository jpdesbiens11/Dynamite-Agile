/* 0.60.26 (D-O-035): several choices before anything happens. In a box of check boxes (the parts of a function, the
   columns of the DFMEA…), a click only ticks: nothing is saved, nothing is redrawn. A bar shows « Appliquer (n) » and
   « Annuler »; the choices take effect on « Appliquer », or when the person clicks outside the box (as with a menu);
   Escape or « Annuler » puts the boxes back. DA.choiceBatch(box, apply) -- apply(changed) receives the inputs whose
   state changed, each with its new .checked; it may return a promise. */
(function () {
  "use strict";

  const { el } = DA;

  DA.choiceBatch = function (box, apply) {
    const inputs = () => [...box.querySelectorAll("input[type=checkbox]:not(:disabled)")];
    const initial = new Map(inputs().map((i) => [i, i.checked]));
    const changed = () => inputs().filter((i) => initial.has(i) && initial.get(i) !== i.checked);
    const count = el("span", { class: "choice-count" });
    let busy = false;

    async function commit() {
      const list = changed();
      if (busy || !list.length) return;
      busy = true;
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", escape, true);
      try { await apply(list); } finally { busy = false; }
    }

    function cancel() {
      initial.forEach((value, input) => { input.checked = value; });
      refresh();
    }

    const bar = el("div", { class: "choice-bar", hidden: true, role: "group", "aria-label": "Choix en attente", "data-new": "0.60.26-choices" },
      count,
      el("button", { type: "button", class: "btn btn-small btn-primary", onclick: commit }, "Appliquer"),
      el("button", { type: "button", class: "btn btn-small", onclick: cancel }, "Annuler"));

    function escape(ev) {
      if (ev.key === "Escape" && box.isConnected && changed().length) { ev.stopPropagation(); cancel(); }
    }

    function outside(ev) {
      if (!box.isConnected) { document.removeEventListener("pointerdown", outside, true); return; }
      if (!box.contains(ev.target)) commit();
    }

    function refresh() {
      const n = changed().length;
      bar.hidden = !n;
      count.textContent = n ? n + " choix en attente — cliquez à côté ou « Appliquer »" : "";
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", escape, true);
      if (n) { document.addEventListener("pointerdown", outside, true); document.addEventListener("keydown", escape, true); }
    }

    box.addEventListener("change", (ev) => { if (ev.target.type === "checkbox") refresh(); });
    box.append(bar);
    return { commit, cancel };
  };
})();
