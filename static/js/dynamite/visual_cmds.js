/* Dynamite - visual editor, part 2: editing commands on the surface
   (D-B-006). Text formatting goes through the browser (execCommand, which
   keeps Ctrl+Z working); blocks the browser does not know (panels, tables,
   tickets, images, status, table of contents, sub-pages) are built with
   render(doc, {editable: true}) -- never from an HTML string. */
(function () {
  "use strict";

  const { api, el, toast, modal } = DA;
  const DY = DA.dynamite;
  const LINK_RE = /^(https?:\/\/[^\s"<>]+|#\/[\w/.\-]*)$/;

  /* Small form in a dialog; resolves with the values, or null if closed. */
  function ask(title, fields, submitLabel) {
    return new Promise((resolve) => {
      let done = false;
      let close = null;
      const inputs = fields.map((f) => (f.options
        ? el("select", null, f.options.map(([v, l]) => el("option", { value: v, selected: v === f.value }, l)))
        : el("input", { type: "text", value: f.value || "", maxlength: f.max || 300, placeholder: f.placeholder || "" })));
      const form = el("form", { class: "dy-ask", onsubmit: (ev) => {
        ev.preventDefault();
        done = true;
        close();
        resolve(inputs.map((i) => i.value));
      } }, fields.map((f, i) => DA.field(f.label, inputs[i], f.hint)),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, submitLabel || "OK")));
      close = modal(title, form);
      const watch = new MutationObserver(() => {
        if (!form.isConnected) { watch.disconnect(); if (!done) resolve(null); }
      });
      watch.observe(document.body, { childList: true, subtree: true });
    });
  }

  function visualCommands(surface, hooks) {
    let saved = null;

    const inSurface = (node) => !!node && surface.contains(node);
    function saveSelection() {
      const sel = window.getSelection();
      if (sel.rangeCount && inSurface(sel.anchorNode)) saved = sel.getRangeAt(0).cloneRange();
    }
    function restore() {
      surface.focus({ preventScroll: true });
      if (saved && inSurface(saved.startContainer)) {
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(saved);
      }
    }
    function range() {
      let sel = window.getSelection();
      if (!(sel.rangeCount && inSurface(sel.anchorNode))) { restore(); sel = window.getSelection(); }
      return sel.rangeCount && inSurface(sel.anchorNode) ? sel.getRangeAt(0) : null;
    }
    function caretInto(node, atEnd) {
      const r = document.createRange();
      r.selectNodeContents(node);
      r.collapse(!atEnd);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      saved = r.cloneRange();
    }
    function caretAfter(node) {
      const r = document.createRange();
      r.setStartAfter(node);
      r.collapse(true);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      saved = r.cloneRange();
    }
    const changed = () => { normalize(); hooks.changed(); };

    function emptyPara() { return el("p", null, el("br")); }
    function isEmptyP(n) { return !!n && n.tagName === "P" && !n.textContent.trim() && !n.querySelector("[data-status]"); }
    function normalize() {
      const last = surface.lastElementChild;
      if (!last || last.tagName !== "P") surface.append(emptyPara());
      surface.querySelectorAll("p, td, th").forEach((p) => { if (!p.firstChild) p.append(el("br")); });
    }
    /* Direct child of the surface (or of a panel body) holding `node`. */
    function blockOf(node) {
      let n = node && node.nodeType === 3 ? node.parentNode : node;
      while (n && n !== surface) {
        const p = n.parentNode;
        if (p === surface || (p && p.classList && p.classList.contains("dy-panel-body"))) return n;
        n = p;
      }
      return null;
    }
    function currentBlock() { const r = range(); return r ? blockOf(r.startContainer) : null; }
    function editable(block) { return DY.render({ type: "doc", content: [block] }, { editable: true }).firstChild; }

    /* Put a block after the caret's block (replacing it if it is an empty line). */
    function insertBlock(node, caretTarget) {
      const blk = currentBlock();
      if (blk && isEmptyP(blk)) blk.replaceWith(node);
      else if (blk) blk.after(node);
      else surface.append(node);
      let next = node.nextElementSibling;
      if (!next || next.tagName !== "P") { next = emptyPara(); node.after(next); }
      normalize();
      caretInto(caretTarget || next, false);
      hooks.changed();
      return node;
    }

    function exec(command, value) { restore(); document.execCommand(command, false, value); changed(); }

    function sameBlock(r) { return blockOf(r.startContainer) === blockOf(r.endContainer); }
    function wrapSelection(makeWrapper, strip) {
      const r = range();
      if (!r || r.collapsed) { toast("Sélectionnez d'abord le texte à mettre en forme.", "info"); return; }
      if (!sameBlock(r)) { toast("Sélectionnez du texte dans un seul paragraphe.", "info"); return; }
      const frag = r.extractContents();
      frag.querySelectorAll(strip).forEach((n) => n.replaceWith(...n.childNodes));
      const wrapper = makeWrapper();
      wrapper.append(frag);
      r.insertNode(wrapper);
      const sel = window.getSelection();
      const after = document.createRange();
      after.selectNodeContents(wrapper);
      sel.removeAllRanges();
      sel.addRange(after);
      saved = after.cloneRange();
      changed();
    }

    function color(name) {
      wrapSelection(() => (name ? el("span", { class: "dy-color-" + name, "data-color": name }) : el("span", { "data-color": "" })),
        "[data-color]");
    }

    function inlineCode() {
      const r = range();
      const code = r && r.startContainer.parentElement && r.startContainer.parentElement.closest("code");
      if (code && inSurface(code) && !code.closest("pre")) { code.replaceWith(...code.childNodes); changed(); return; }
      wrapSelection(() => el("code"), "code");
    }

    async function link() {
      saveSelection();
      const r = range();
      const anchor = r && r.startContainer.parentElement && r.startContainer.parentElement.closest("a");
      const vals = await ask(anchor ? "Modifier le lien" : "Insérer un lien", [{ label: "Adresse", placeholder: "https://… ou #/dynamite/…",
        value: anchor ? anchor.getAttribute("href") : "https://", hint: "Laissez vide pour retirer le lien." }], "Appliquer");
      if (vals === null) { restore(); return; }
      const url = vals[0].trim();
      restore();
      if (!url) { if (anchor) anchor.replaceWith(...anchor.childNodes); changed(); return; }
      if (!LINK_RE.test(url)) { toast("Lien refusé : il commence par http://, https:// ou #/ (page interne).", "error"); return; }
      if (anchor) { anchor.setAttribute("href", url); changed(); return; }
      const rr = range();
      if (rr && rr.collapsed) {
        const a = el("a", { href: url }, url);
        rr.insertNode(a);
        caretAfter(a);
        changed();
      } else exec("createLink", url);
    }

    async function status(existing) {
      saveSelection();
      const vals = await ask(existing ? "Modifier le status" : "Insérer un status", [
        { label: "Texte", value: existing ? existing.textContent : "EN COURS", max: 40 },
        { label: "Couleur", options: Object.entries(DY.STATUS_COLORS), value: existing ? existing.dataset.status : "blue" }],
      existing ? "Modifier" : "Insérer");
      if (!vals || !vals[0].trim()) { restore(); return; }
      const node = DY.inline([{ type: "status", text: vals[0].trim().slice(0, 40), color: vals[1] }], { editable: true })[0];
      if (existing) { existing.replaceWith(node); changed(); return; }
      restore();
      const r = range();
      if (!r) return;
      r.deleteContents();
      r.insertNode(node);
      const space = document.createTextNode(" ");
      node.after(space);
      caretAfter(space);
      changed();
    }

    async function ticket() {
      saveSelection();
      const vals = await ask("Insérer un ticket Agile", [{ label: "Clé du ticket", placeholder: "EQP-4", max: 30,
        hint: "Le bloc restera à jour : status, assigné et titre actuels." }], "Insérer");
      restore();
      const key = vals ? vals[0].trim().toUpperCase() : "";
      if (!key) return;
      try {
        const t = await api.get("/api/dynamite/ticket/" + encodeURIComponent(key));
        restore();
        insertBlock(editable({ type: "ticket", key: t.key }));
      } catch (err) {
        toast(err.status === 404 ? key + " introuvable ou non accessible. Vérifiez la clé dans Agile → Tickets." : err.message, "error");
      }
    }

    async function imageLegend(figure) {
      const vals = await ask("Légende de l'image", [{ label: "Légende (texte alternatif)", value: figure.dataset.alt || "", max: 300,
        hint: "Lue par les lecteurs d'écran et affichée sous l'image." }], "Appliquer");
      if (vals === null) return;
      figure.replaceWith(editable({ type: "image", id: Number(figure.dataset.id), alt: vals[0].trim() }));
      changed();
    }

    function panel(kind) {
      restore();
      const blk = currentBlock();
      const node = editable({ type: "panel", kind, content: [] });
      const body = node.querySelector(".dy-panel-body");
      if (blk && blk.tagName === "P" && !isEmptyP(blk) && blk.parentNode === surface) {
        blk.replaceWith(node);
        body.append(blk);
        if (!node.nextElementSibling) node.after(emptyPara());
        normalize();
        caretInto(blk, true);
        hooks.changed();
        return;
      }
      const inner = emptyPara();
      body.append(inner);
      insertBlock(node, inner);
    }

    /* ---------- Tables ---------- */
    function table() {
      restore();
      const rows = [0, 1, 2].map(() => [[], [], []]);
      const node = editable({ type: "table", header: true, rows });
      node.querySelectorAll("th, td").forEach((c) => c.append(el("br")));
      insertBlock(node, node.rows[0].cells[0]);
    }
    function cellInfo() {
      const r = range();
      let n = r && r.startContainer;
      while (n && n !== surface && !(n.tagName === "TD" || n.tagName === "TH")) n = n.parentNode;
      if (!n || n === surface) { toast("Placez d'abord le curseur dans une cellule du tableau.", "info"); return null; }
      const tr = n.parentNode;
      return { cell: n, tr, table: tr.closest("table"), col: Array.from(tr.cells).indexOf(n) };
    }
    function isHeaderRow(t, tr) { return t.dataset.header === "true" && tr === t.rows[0]; }
    const tableOps = {
      addRow() {
        const c = cellInfo(); if (!c) return;
        const tr = el("tr", null, Array.from(c.tr.cells).map(() => el("td", null, el("br"))));
        c.tr.after(tr);
        caretInto(tr.cells[Math.max(0, c.col)], false);
        changed();
      },
      addCol() {
        const c = cellInfo(); if (!c) return;
        Array.from(c.table.rows).forEach((row) => {
          const cell = el(isHeaderRow(c.table, row) ? "th" : "td", null, el("br"));
          const ref = row.cells[c.col];
          if (ref) ref.after(cell); else row.append(cell);
        });
        changed();
      },
      delRow() {
        const c = cellInfo(); if (!c) return;
        if (c.table.rows.length === 1) { c.table.remove(); changed(); return; }
        if (isHeaderRow(c.table, c.tr)) c.table.dataset.header = "false";
        c.tr.remove();
        changed();
      },
      delCol() {
        const c = cellInfo(); if (!c) return;
        Array.from(c.table.rows).forEach((row) => { if (row.cells[c.col]) row.cells[c.col].remove(); });
        if (!c.table.rows[0] || !c.table.rows[0].cells.length) c.table.remove();
        changed();
      },
      toggleHeader() {
        const c = cellInfo(); if (!c) return;
        const on = c.table.dataset.header !== "true";
        c.table.dataset.header = on ? "true" : "false";
        Array.from(c.table.rows[0].cells).forEach((cell) => {
          const swap = el(on ? "th" : "td");
          swap.append(...cell.childNodes);
          cell.replaceWith(swap);
        });
        changed();
      },
      next(backwards) {
        const r = range();
        let n = r && r.startContainer;
        while (n && n !== surface && !(n.tagName === "TD" || n.tagName === "TH")) n = n.parentNode;
        if (!n || n === surface) return false;
        const cells = Array.from(n.closest("table").querySelectorAll("th, td"));
        const i = cells.indexOf(n) + (backwards ? -1 : 1);
        if (i >= cells.length) { tableOps.addRow(); return true; }
        if (i >= 0) caretInto(cells[i], true);
        return true;
      },
    };

    return {
      saveSelection, restore, range, normalize, insertBlock, editable, exec, color, inlineCode, link, status,
      ticket, imageLegend, panel, table, tableOps, currentBlock, caretInto,
      heading: (level) => exec("formatBlock", level ? "<h" + (level + 1) + ">" : "<p>"),
      quote: () => exec("formatBlock", "<blockquote>"),
      codeBlock: () => exec("formatBlock", "<pre>"),
      rule: () => { restore(); insertBlock(el("hr")); },
      atom: (type) => { restore(); insertBlock(editable({ type })); },
      image: (id, alt) => { restore(); insertBlock(editable({ type: "image", id, alt })); },
    };
  }

  Object.assign(DY, { visualCommands, ask });
})();
