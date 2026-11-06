/* Dynamite page tools (D-B-049, D-B-050): move or copy a page to any space
   where the person is an editor (with or without its sub-pages), and export
   it as PDF or Word when an administrator gave the export right. */
(function () {
  "use strict";

  const { api, el, toast, modal, field } = DA;
  const DY = (DA.dynamite = DA.dynamite || {});

  function editableSpaces() {
    return DA.session.projects.filter((p) => p.role === "editor" || p.role === "admin" || DA.session.user.is_admin);
  }

  DY.canTransfer = () => editableSpaces().length > 0;

  DY.transferDialog = function (ctx, p) {
    const spaces = editableSpaces();
    const mode = el("select", null, el("option", { value: "move", disabled: !(ctx.role === "editor" || ctx.role === "admin") }, "Déplacer (la page et ses sous-pages)"),
      el("option", { value: "copy", selected: !(ctx.role === "editor" || ctx.role === "admin") }, "Copier"));
    const space = el("select", null, spaces.map((s) => el("option", { value: s.id, selected: s.id === ctx.pid }, s.key + " · " + s.name)));
    const parent = el("select");
    const children = el("input", { type: "checkbox", checked: true });
    const childrenRow = el("label", { class: "check" }, children, "Copier aussi les sous-pages");
    async function loadParents() {
      parent.replaceChildren(el("option", { value: "" }, "(racine du Space)"));
      let pages = [];
      try { pages = (await api.get("/api/dynamite/p/" + space.value + "/pages")).pages; } catch (err) { toast(err.message, "error"); }
      const own = new Set();
      if (Number(space.value) === ctx.pid && mode.value === "move") {  // not under itself
        own.add(p.id);
        let grew = true;
        while (grew) { grew = false; pages.forEach((x) => { if (x.parent_id && own.has(x.parent_id) && !own.has(x.id)) { own.add(x.id); grew = true; } }); }
      }
      pages.filter((x) => !own.has(x.id)).forEach((x) => parent.append(el("option", { value: x.id,
        selected: Number(space.value) === ctx.pid && x.id === p.parent_id }, x.title)));
    }
    const sync = () => { childrenRow.style.display = mode.value === "copy" ? "" : "none"; loadParents(); };
    mode.addEventListener("change", sync);
    space.addEventListener("change", loadParents);
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post("/api/dynamite/p/" + ctx.pid + "/pages/" + p.id + "/transfer", {
          mode: mode.value, target_pid: Number(space.value), parent_id: parent.value || null, with_children: children.checked });
        close();
        toast(mode.value === "move" ? res.moved + " page(s) déplacée(s) vers " + res.target_key + "."
          : res.copied + " page(s) copiée(s) dans " + res.target_key + ".", "success");
        location.hash = "#/dynamite/" + res.target_key + "/page/" + res.page_id;
        if (res.target_key === ctx.key) ctx.refresh();
      } catch (err) { toast(err.message, "error"); }
    } },
    field("Action", mode), field("Space de destination", space), field("Page parente", parent), childrenRow,
    el("p", { class: "muted" }, "Les images suivent la page ; l'historique et les commentaires restent attachés à la page déplacée. "
      + "Une copie commence à la version 1, notée « Copie de … »."),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Valider")));
    close = modal("Déplacer ou copier « " + p.title + " »", form);
    sync();
  };

  DY.canExport = () => DA.session.user.is_admin || !!(DA.prefs && DA.prefs().can_export);

  DY.exportMenu = function (ctx, p) {
    if (!DY.canExport()) return null;
    /* 0.60.62 (D-O-071): the export goes through DY.exportPage, which adds the Mermaid drawings (mermaid_png.js) */
    const sel = el("select", { class: "btn btn-small dy-export", "aria-label": "Exporter la page" },
      el("option", { value: "" }, "⇩ Exporter…"),
      el("option", { value: "pdf" }, "PDF — cette page"), el("option", { value: "pdf+" }, "PDF — avec les sous-pages"),
      el("option", { value: "docx" }, "Word — cette page"), el("option", { value: "docx+" }, "Word — avec les sous-pages"));
    sel.addEventListener("change", async () => {
      if (!sel.value) return;
      const fmt = sel.value.replace("+", ""), kids = sel.value.endsWith("+");
      sel.value = "";
      sel.disabled = true;
      try {
        await DY.exportPage(ctx.pid, p.id, fmt, kids);
      } catch (err) {
        DA.toast(err.message, "error");
      } finally {
        sel.disabled = false;
      }
    });
    return sel;
  };
})();
