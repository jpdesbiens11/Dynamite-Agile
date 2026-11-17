/* Timesheet - folding the Budget Lines (0.60.107, D-O-119). A Funding Space and, inside it, each sub-project (the part of
   a label before « · », e.g. « 3. Conception détaillée · Gestion thermique ») fold vertically with a chevron. The
   state is remembered per viewer in the browser (localStorage, never sent to the server). Used by the export picker
   (Export et rapport Word), « Spaces et organismes » and the Budget Line list of the week view. */
(function () {
  "use strict";

  const { el } = DA;
  const TS = (DA.timesheet = DA.timesheet || {});
  const STORE = "da.timesheet.fold.";
  const SEP = " · ";

  /* « 3. Conception détaillée · Gestion thermique » -> ["3. Conception détaillée", "Gestion thermique"]; no prefix -> ["", label] */
  TS.splitLabel = function (label) {
    const text = String(label || "");
    const at = text.indexOf(SEP);
    return at > 0 ? [text.slice(0, at), text.slice(at + SEP.length)] : ["", text];
  };

  /* The Budget Lines of a set cut into sub-projects, in the order each first appears: [{name, tasks}] (a line added later
     to a sub-project joins it; the lines without a prefix form one group named "") */
  TS.groupTasks = function (tasks) {
    const out = [];
    const byName = new Map();
    tasks.forEach((t) => {
      const name = TS.splitLabel(t.label)[0];
      if (!byName.has(name)) { byName.set(name, { name, tasks: [] }); out.push(byName.get(name)); }
      byName.get(name).tasks.push(t);
    });
    return out;
  };

  function remembered(key) {
    try { return localStorage.getItem(STORE + key) === "0"; } catch (err) { return false; }  // private window: open
  }

  function remember(key, open) {
    try { localStorage.setItem(STORE + key, open ? "1" : "0"); } catch (err) { /* private window */ }
  }

  /* A chevron button that shows or hides `targets` (nodes or a function returning nodes). Open by default. */
  TS.foldButton = function (key, name, targets, onToggle) {
    const list = () => (typeof targets === "function" ? targets() : targets);
    /* the [new] badge (D-A-049) on the Funding Space chevron only, not on each sub-project */
    const btn = el("button", { type: "button", class: "tt-fold", "data-new": key.split(".").length === 2 ? "0.60.107-ts-fold" : null });
    const apply = (open) => {
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.setAttribute("aria-label", (open ? "Replier " : "Déplier ") + name);
      btn.title = open ? "Replier" : "Déplier";
      btn.textContent = open ? "▾" : "▸";
      list().forEach((n) => { n.hidden = !open; });
      if (onToggle) onToggle(open);
    };
    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      const open = btn.getAttribute("aria-expanded") !== "true";
      remember(key, open);
      apply(open);
    });
    btn.init = () => apply(!remembered(key));
    return btn;
  };

  /* Week view: the Budget Lines of a Space in a <select>, one <optgroup> per sub-project */
  TS.taskOptions = function (tasks, render) {
    const groups = TS.groupTasks(tasks);
    if (groups.length < 2) return tasks.map((t) => render(t, t.label));
    return groups.map((g) => (g.name ? el("optgroup", { label: g.name }, g.tasks.map((t) => render(t, TS.splitLabel(t.label)[1])))
      : g.tasks.map((t) => render(t, t.label))));
  };
})();
