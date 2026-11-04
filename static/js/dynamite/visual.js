/* Dynamite - visual editor, part 3: the editing surface (D-B-006).
   What you see is the page: toolbar, "/" command menu, paste from Word /
   Excel / web (converted through visual_dom.js, never inserted as HTML),
   images pasted or dropped, Tab between table cells, Ctrl+S to save.
   Produces the same JSON as the Source mode (editor.js). */
(function () {
  "use strict";

  const { el, clear } = DA;
  const DY = DA.dynamite;

  function slashItems(cmd, hooks) {
    return [
      ["Titre 1", "h1 titre", () => cmd.heading(1)],
      ["Titre 2", "h2 titre sous-titre", () => cmd.heading(2)],
      ["Titre 3", "h3 titre", () => cmd.heading(3)],
      ["Paragraphe", "texte normal p", () => cmd.heading(0)],
      ["Liste à puces", "liste puces ul", () => cmd.exec("insertUnorderedList")],
      ["Liste numérotée", "liste numéros ol", () => cmd.exec("insertOrderedList")],
      ["Tableau", "tableau table grille", () => cmd.table()],
      ["Panneau Info", "panneau info encadré", () => cmd.panel("info")],
      ["Panneau Note", "panneau note", () => cmd.panel("note")],
      ["Panneau Avertissement", "panneau avertissement attention warning", () => cmd.panel("warning")],
      ["Panneau Succès", "panneau succès success", () => cmd.panel("success")],
      ["Citation", "citation quote", () => cmd.quote()],
      ["Bloc de code", "code bloc", () => cmd.codeBlock()],
      ["Séparateur", "séparateur ligne trait hr", () => cmd.rule()],
      ["Ticket Agile", "ticket agile jira clé", () => cmd.ticket()],
      ["Image", "image photo capture", () => hooks.pickImage()],
      ["Status", "status status étiquette", () => cmd.status()],
      ["Table des matières", "table matières toc sommaire", () => cmd.atom("toc")],
      ["Sous-pages", "sous-pages enfants children", () => cmd.atom("children")],
      ["Contenu d'un agent IA", "ia ai agent chatgpt claude copilot markdown importer coller", () => hooks.aiImport()],
    ].map(([label, keys, run]) => ({ label, keys: (label + " " + keys).toLowerCase(), run }));
  }

  function visualEditor(options) {
    const surface = el("div", { class: "dy-content dy-visual", contenteditable: "true", role: "textbox",
      "aria-multiline": "true", "aria-label": "Contenu de la page", spellcheck: "true" });
    const menu = el("div", { class: "dy-slash", role: "listbox", "aria-label": "Insérer un bloc", hidden: true });
    const wrap = el("div", { class: "dy-visual-wrap" }, surface, menu);
    const hooks = { changed: () => {}, pickImage: () => options.pickImage(),
      aiImport: () => { cmd.saveSelection(); options.aiImport(); } };
    const cmd = DY.visualCommands(surface, hooks);
    const items = slashItems(cmd, hooks);
    let selectedAtom = null;
    let slash = null;  // { length, active, shown }

    try { document.execCommand("defaultParagraphSeparator", false, "p"); } catch (err) { /* old browser */ }

    /* ---------- Toolbar ---------- */
    const keep = (ev) => ev.preventDefault();  // keep the caret in the page
    const btn = (label, title, action) => el("button", { type: "button", class: "dy-tool", title, "aria-label": title,
      onmousedown: keep, onclick: action }, label);
    const pick = (label, choices, action) => {
      const select = el("select", { class: "dy-tool-select", "aria-label": label },
        el("option", { value: "" }, label), choices.map(([v, l]) => el("option", { value: v }, l)));
      select.addEventListener("mousedown", () => cmd.saveSelection());
      select.addEventListener("change", () => { const v = select.value; select.value = ""; if (v !== "") action(v); });
      return select;
    };
    const sep = () => el("span", { class: "dy-tool-sep" });
    const toolbar = el("div", { class: "dy-toolbar", role: "toolbar", "aria-label": "Mise en forme" },
      pick("Style…", [["p", "Paragraphe"], ["1", "Titre 1"], ["2", "Titre 2"], ["3", "Titre 3"],
        ["quote", "Citation"], ["code", "Bloc de code"]], (v) => {
        if (v === "quote") cmd.quote(); else if (v === "code") cmd.codeBlock(); else cmd.heading(v === "p" ? 0 : Number(v));
      }),
      sep(),
      btn("G", "Gras (Ctrl+B)", () => cmd.exec("bold")),
      btn("I", "Italique (Ctrl+I)", () => cmd.exec("italic")),
      btn("S", "Souligné (Ctrl+U)", () => cmd.exec("underline")),
      btn("B̶", "Barré", () => cmd.exec("strikeThrough")),
      btn("</>", "Code en ligne", () => cmd.inlineCode()),
      btn("🔗", "Lien (Ctrl+K)", () => cmd.link()),
      pick("Couleur…", [["none", "Aucune"]].concat(Object.entries(DY.COLORS)), (v) => cmd.color(v === "none" ? "" : v)),
      sep(),
      btn("• Liste", "Liste à puces", () => cmd.exec("insertUnorderedList")),
      btn("1. Liste", "Liste numérotée", () => cmd.exec("insertOrderedList")),
      pick("Panneau…", Object.entries(DY.PANEL_LABELS), (v) => cmd.panel(v)),
      btn("⊞ Tableau", "Insérer un tableau 3 × 3", () => cmd.table()),
      pick("Tableau…", [["addRow", "+ Ligne dessous"], ["addCol", "+ Colonne à droite"], ["delRow", "− Supprimer la ligne"],
        ["delCol", "− Supprimer la colonne"], ["toggleHeader", "En-tête oui / non"]], (v) => { cmd.restore(); cmd.tableOps[v](); }),
      sep(),
      btn("◉ Status", "Insérer un status", () => cmd.status()),
      btn("🎫 Ticket", "Insérer un bloc Ticket Agile", () => cmd.ticket()),
      btn("🖼 Image", "Insérer une image (ou collez-la avec Ctrl+V, ou glissez-la dans la page)", () => hooks.pickImage()),
      btn("☰ TdM", "Table des matières", () => cmd.atom("toc")),
      btn("↳ Sous-pages", "Liste des sous-pages", () => cmd.atom("children")),
      btn("―", "Séparateur", () => cmd.rule()),
      sep(),
      btn("✨ IA", "Importer du contenu d'un agent IA (texte, tableaux, liens, images)", () => hooks.aiImport()),
      el("span", { class: "dy-tool-hint" }, "Tapez / pour insérer un bloc"));

    /* ---------- "/" menu ---------- */
    function textBeforeCaret() {
      const sel = window.getSelection();
      if (!sel.rangeCount || !sel.isCollapsed) return null;
      const r = sel.getRangeAt(0);
      if (r.startContainer.nodeType !== 3 || !surface.contains(r.startContainer)) return null;
      return r.startContainer.nodeValue.slice(0, r.startOffset);
    }
    function closeMenu() { menu.hidden = true; slash = null; }
    function drawMenu(filter) {
      const words = filter.toLowerCase();
      const shown = items.filter((it) => it.keys.includes(words));
      if (!shown.length) { closeMenu(); return; }
      slash.shown = shown;
      slash.active = Math.min(slash.active || 0, shown.length - 1);
      clear(menu);
      shown.forEach((it, i) => menu.append(el("div", { class: "dy-slash-item" + (i === slash.active ? " active" : ""),
        role: "option", "aria-selected": i === slash.active ? "true" : "false",
        onmousedown: (ev) => { ev.preventDefault(); choose(i); } }, it.label)));
      const rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
      const box = wrap.getBoundingClientRect();
      menu.style.left = Math.max(0, rect.left - box.left) + "px";
      menu.style.top = (rect.bottom - box.top + 4) + "px";
      menu.hidden = false;
    }
    function updateSlash() {
      const before = textBeforeCaret();
      const m = before === null ? null : before.match(/(?:^|[\s ])\/([\p{L}\d -]{0,20})$/u);
      if (!m) { closeMenu(); return; }
      slash = Object.assign(slash || { active: 0 }, { length: m[1].length + 1 });
      drawMenu(m[1]);
    }
    function choose(i) {
      const item = slash && slash.shown[i];
      const length = slash ? slash.length : 0;
      closeMenu();
      if (!item) return;
      const sel = window.getSelection();
      const r = sel.getRangeAt(0);
      if (r.startContainer.nodeType === 3 && r.startOffset >= length) {
        r.setStart(r.startContainer, r.startOffset - length);
        r.deleteContents();
      }
      cmd.saveSelection();
      item.run();
    }

    /* ---------- Paste and drop: never raw HTML ---------- */
    function insertDoc(doc) {
      const blocks = doc.content || [];
      if (!blocks.length) return;
      const r = cmd.range();
      if (!r) {  // never focused: append at the end
        surface.append(...Array.from(DY.render(doc, { editable: true }).childNodes));
        cmd.normalize();
        hooks.changed();
        return;
      }
      r.deleteContents();
      if (blocks.length === 1 && blocks[0].type === "paragraph") {
        const frag = document.createDocumentFragment();
        DY.inline(blocks[0].content, { editable: true }).forEach((n) => frag.append(n));
        const last = frag.lastChild;
        r.insertNode(frag);
        if (last) { const after = document.createRange(); after.setStartAfter(last); after.collapse(true);
          const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(after); }
      } else {
        const nodes = Array.from(DY.render(doc, { editable: true }).childNodes);
        let anchor = cmd.currentBlock();
        nodes.forEach((n) => {
          if (anchor && anchor.tagName === "P" && !anchor.textContent.trim() && anchor.parentNode === surface) anchor.replaceWith(n);
          else if (anchor) anchor.after(n);
          else surface.append(n);
          anchor = n;
        });
        cmd.normalize();
        const next = anchor.nextElementSibling;
        if (next) cmd.caretInto(next, false);
      }
      cmd.normalize();
      hooks.changed();
    }
    const imagesIn = (list) => Array.from(list || []).filter((f) => f.type && f.type.startsWith("image/"));
    surface.addEventListener("paste", (ev) => {
      const data = ev.clipboardData;
      if (!data) return;
      const text = data.getData("text/plain") || "";
      const html = data.getData("text/html") || "";
      const files = imagesIn(data.files);
      ev.preventDefault();
      if (files.length && !text.trim()) { options.uploadFiles(files); return; }
      const r = cmd.range();
      if (r && r.startContainer.parentElement && r.startContainer.parentElement.closest("pre")) {
        document.execCommand("insertText", false, text);
        return;
      }
      // Plain text that looks like Markdown (the "copy" button of AI chats): keep its structure.
      insertDoc(html ? DY.htmlToDoc(html) : (DY.looksLikeMarkdown(text) ? DY.markdownToDoc(text) : DY.textToDoc(text)));
    });
    surface.addEventListener("dragover", (ev) => {
      if (Array.from(ev.dataTransfer.types || []).includes("Files")) { ev.preventDefault(); surface.classList.add("dy-dropping"); }
    });
    surface.addEventListener("dragleave", () => surface.classList.remove("dy-dropping"));
    surface.addEventListener("drop", (ev) => {
      surface.classList.remove("dy-dropping");
      const dt = ev.dataTransfer;
      if (!dt) return;
      ev.preventDefault();
      if (document.caretRangeFromPoint) {
        const at = document.caretRangeFromPoint(ev.clientX, ev.clientY);
        if (at && surface.contains(at.startContainer)) {
          const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(at);
        }
      }
      cmd.saveSelection();
      const files = imagesIn(dt.files);
      if (files.length) { options.uploadFiles(files); return; }
      const html = dt.getData("text/html");
      insertDoc(html ? DY.htmlToDoc(html) : DY.textToDoc(dt.getData("text/plain")));
    });

    /* ---------- Keyboard and clicks ---------- */
    function selectAtom(node) {
      if (selectedAtom) selectedAtom.classList.remove("dy-selected");
      selectedAtom = node;
      if (node) node.classList.add("dy-selected");
    }
    surface.addEventListener("keydown", (ev) => {
      if (slash && !menu.hidden) {
        if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
          ev.preventDefault();
          slash.active = (slash.active + (ev.key === "ArrowDown" ? 1 : -1) + slash.shown.length) % slash.shown.length;
          drawMenu(textBeforeCaret().match(/\/([\p{L}\d -]{0,20})$/u)[1]);
          return;
        }
        if (ev.key === "Enter" || ev.key === "Tab") { ev.preventDefault(); choose(slash.active); return; }
        if (ev.key === "Escape") { ev.preventDefault(); closeMenu(); return; }
      }
      if (selectedAtom && (ev.key === "Backspace" || ev.key === "Delete")) {
        ev.preventDefault();
        const next = selectedAtom.nextElementSibling;
        selectedAtom.remove();
        selectAtom(null);
        cmd.normalize();
        if (next) cmd.caretInto(next, false);
        hooks.changed();
        return;
      }
      selectAtom(null);
      const mod = ev.ctrlKey || ev.metaKey;
      if (mod && ev.key.toLowerCase() === "s") { ev.preventDefault(); options.onSave(); }
      else if (mod && ev.key.toLowerCase() === "k") { ev.preventDefault(); cmd.link(); }
      else if (ev.key === "Tab" && cmd.tableOps.next(ev.shiftKey)) ev.preventDefault();
    });
    surface.addEventListener("input", () => { updateSlash(); hooks.changed(); });
    surface.addEventListener("click", (ev) => {
      const status = ev.target.closest("[data-status]");
      if (status && surface.contains(status)) { cmd.status(status); return; }
      const atomNode = ev.target.closest("[data-block]");
      if (atomNode && surface.contains(atomNode) && !ev.target.closest("a")) {
        selectAtom(atomNode);
        if (atomNode.dataset.block === "image" && ev.detail === 2) cmd.imageLegend(atomNode);
        return;
      }
      selectAtom(null);
      closeMenu();
    });
    const onSelection = () => cmd.saveSelection();
    document.addEventListener("selectionchange", onSelection);
    surface.addEventListener("blur", () => setTimeout(closeMenu, 150));

    function setDoc(doc) {
      clear(surface);
      surface.append(...Array.from(DY.render(doc, { editable: true }).childNodes));
      cmd.normalize();
    }

    return {
      toolbar, element: wrap, setDoc, insertDoc,
      getDoc: () => DY.domToDoc(surface),
      focus: () => { surface.focus(); const first = surface.firstElementChild; if (first) cmd.caretInto(first, true); },
      insertImage: (id, alt) => cmd.image(id, alt),
      onChange: (fn) => { hooks.changed = fn; },
      destroy: () => document.removeEventListener("selectionchange", onSelection),
    };
  }

  DY.visualEditor = visualEditor;
})();
