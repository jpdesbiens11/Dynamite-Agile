/* Dynamite - editor (increment 1): a short syntax typed in a text area,
   converted to the JSON page body (D-A-035) with a live preview. The
   visual Confluence-style toolbar editor (increment 2) will produce the
   same JSON, so pages written now stay valid. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const DY = DA.dynamite;

  const HELP = [
    ["# Titre / ## Sous-titre / ### Niveau 3", "Titres"],
    ["**gras**  *italique*  __souligné__  ~~barré~~  `code`", "Mise en forme"],
    ["[texte](https://…)", "Lien (s'ouvre dans un nouvel onglet)"],
    ["- élément   ou   1. élément", "Listes"],
    ["> citation", "Citation"],
    ["```langage … ```", "Bloc de code"],
    [":::info … :::   (info, note, warning, success)", "Panneau"],
    ["[[EQP-4]]   seul sur sa ligne", "Bloc Ticket Agile (vivant)"],
    ["![légende](image:12)   seul sur sa ligne", "Image : collez (Ctrl+V), glissez un fichier ou bouton 🖼 Image"],
    ["{{red:texte}}   (red, orange, green, blue, purple, gray)", "Couleur du texte"],
    ["{{status:green:TERMINÉ}}   (gray, blue, green, yellow, red)", "Status"],
    ["| A | B |  puis  | --- | --- |  puis  | 1 | 2 |", "Tableau (la 2e ligne --- marque l'en-tête)"],
    ["[[toc]]   /   [[sous-pages]]", "Table des matières / liste des sous-pages"],
    ["---", "Séparateur"],
  ];

  /* ---------- Text -> JSON ---------- */
  const INLINE_RE = new RegExp([
    "(`[^`]+`)",                                                   // 1 code
    "(\\{\\{status:(gray|blue|green|yellow|red):([^}]{1,40})\\}\\})",     // 2 status, 3 colour, 4 text
    "(\\{\\{(red|orange|green|blue|purple|gray):((?:(?!\\}\\}).)+)\\}\\})", // 5 colour, 6 name, 7 inner
    "(\\*\\*((?:(?!\\*\\*).)+)\\*\\*)",                                  // 8 bold, 9 inner
    "(__((?:(?!__).)+)__)",                                         // 10 underline, 11 inner
    "(~~((?:(?!~~).)+)~~)",                                         // 12 strike, 13 inner
    "(\\*([^*\\s][^*]*)\\*)",                                          // 14 italic, 15 inner
    "(\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+|#\\/[^\\s)]*)\\))",         // 16 link, 17 text, 18 href
  ].join("|"), "g");

  function withMark(nodes, mark) {
    return nodes.map((n) => (n.type === "text" ? Object.assign({}, n, { marks: (n.marks || []).concat([mark]) }) : n));
  }

  function parseInline(text) {
    const out = [];
    let last = 0;
    const re = new RegExp(INLINE_RE.source, "g");
    let m;
    while ((m = re.exec(text))) {
      if (m.index > last) out.push({ type: "text", text: text.slice(last, m.index) });
      if (m[1]) out.push({ type: "text", text: m[1].slice(1, -1), marks: ["code"] });
      else if (m[2]) out.push({ type: "status", text: m[4].trim(), color: m[3] });
      else if (m[5]) out.push(...withMark(parseInline(m[7]), { type: "color", color: m[6] }));
      else if (m[8]) out.push(...withMark(parseInline(m[9]), "bold"));
      else if (m[10]) out.push(...withMark(parseInline(m[11]), "underline"));
      else if (m[12]) out.push(...withMark(parseInline(m[13]), "strike"));
      else if (m[14]) out.push(...withMark(parseInline(m[15]), "italic"));
      else if (m[16]) out.push(...withMark(parseInline(m[17]), { type: "link", href: m[18] }));
      last = m.index + m[0].length;
    }
    if (last < text.length) out.push({ type: "text", text: text.slice(last) });
    return out.map((n) => (n.marks && !n.marks.length ? { type: n.type, text: n.text } : n));
  }

  const TABLE_SEP = /^\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{0,}:?\s*\|?$/;
  function tableCells(line) {
    let t = line.trim();
    if (t.startsWith("|")) t = t.slice(1);
    if (t.endsWith("|") && !t.endsWith("\\|")) t = t.slice(0, -1);
    return t.split(/(?<!\\)\|/).map((c) => parseInline(c.trim().replace(/\\\|/g, "|")));
  }

  function parseBlocks(lines) {
    const out = [];
    let para = [];
    const flush = () => {
      if (para.length) out.push({ type: "paragraph", content: parseInline(para.join(" ")) });
      para = [];
    };
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const t = line.trim();
      let m;
      if (!t) { flush(); continue; }
      if ((m = t.match(/^```\s*([\w+#.-]{0,20})$/))) {
        flush();
        const code = [];
        for (i++; i < lines.length && lines[i].trim() !== "```"; i++) code.push(lines[i]);
        out.push({ type: "code", lang: m[1] || "", text: code.join("\n") });
      } else if ((m = t.match(/^:::(info|note|warning|success)$/i))) {
        flush();
        const inner = [];
        let depth = 1;
        for (i++; i < lines.length; i++) {
          const x = lines[i].trim();
          if (/^:::(info|note|warning|success)$/i.test(x)) depth++;
          if (x === ":::" && --depth === 0) break;
          inner.push(lines[i]);
        }
        out.push({ type: "panel", kind: m[1].toLowerCase(), content: parseBlocks(inner) });
      } else if ((m = t.match(/^\[\[([A-Za-z][A-Za-z0-9]{1,9}-\d+)\]\]$/))) {
        flush();
        out.push({ type: "ticket", key: m[1].toUpperCase() });
      } else if (/^\[\[(toc|tdm|table des matières)\]\]$/i.test(t)) {
        flush();
        out.push({ type: "toc" });
      } else if (/^\[\[(sous-pages|children)\]\]$/i.test(t)) {
        flush();
        out.push({ type: "children" });
      } else if (t.startsWith("|")) {
        flush();
        const rows = [];
        let header = false;
        for (; i < lines.length && lines[i].trim().startsWith("|"); i++) {
          if (rows.length === 1 && TABLE_SEP.test(lines[i].trim())) { header = true; continue; }
          rows.push(tableCells(lines[i]));
        }
        i--;
        out.push({ type: "table", header, rows });
      } else if ((m = t.match(/^!\[([^\]]{0,300})\]\(image:(\d{1,12})\)$/))) {
        flush();
        out.push({ type: "image", id: Number(m[2]), alt: m[1].trim() });
      } else if (/^(-{3,}|\*{3,})$/.test(t)) {
        flush();
        out.push({ type: "rule" });
      } else if ((m = t.match(/^(#{1,3})\s+(.*)$/))) {
        flush();
        out.push({ type: "heading", level: m[1].length, content: parseInline(m[2]) });
      } else if (/^>\s?/.test(t)) {
        flush();
        const inner = [];
        for (; i < lines.length && /^>\s?/.test(lines[i].trim()); i++) inner.push(lines[i].trim().replace(/^>\s?/, ""));
        i--;
        out.push({ type: "quote", content: parseBlocks(inner) });
      } else if (/^([-*]|\d+[.)])\s+/.test(t)) {
        flush();
        const ordered = /^\d/.test(t);
        const items = [];
        for (; i < lines.length && (ordered ? /^\d+[.)]\s+/ : /^[-*]\s+/).test(lines[i].trim()); i++) {
          items.push([{ type: "paragraph", content: parseInline(lines[i].trim().replace(/^([-*]|\d+[.)])\s+/, "")) }]);
        }
        i--;
        out.push({ type: ordered ? "ordered_list" : "bullet_list", items });
      } else {
        para.push(t);
      }
    }
    flush();
    return out;
  }

  function parse(text) { return { type: "doc", content: parseBlocks(String(text || "").split(/\r?\n/)) }; }

  /* ---------- JSON -> text (to edit an existing page) ---------- */
  function inlineText(nodes) {
    return (nodes || []).map((n) => {
      if (n.type === "status") return "{{status:" + n.color + ":" + n.text + "}}";
      let s = n.text || "";
      for (const mark of n.marks || []) {
        if (mark === "bold") s = "**" + s + "**";
        else if (mark === "italic") s = "*" + s + "*";
        else if (mark === "underline") s = "__" + s + "__";
        else if (mark === "strike") s = "~~" + s + "~~";
        else if (mark === "code") s = "`" + s + "`";
        else if (mark && mark.type === "link") s = "[" + s + "](" + mark.href + ")";
        else if (mark && mark.type === "color") s = "{{" + mark.color + ":" + s + "}}";
      }
      return s;
    }).join("");
  }

  function serializeBlocks(nodes) {
    return (nodes || []).map((b) => {
      switch (b.type) {
        case "paragraph": return inlineText(b.content);
        case "heading": return "#".repeat(b.level) + " " + inlineText(b.content);
        case "bullet_list": return b.items.map((it) => "- " + serializeBlocks(it)).join("\n");
        case "ordered_list": return b.items.map((it, i) => (i + 1) + ". " + serializeBlocks(it)).join("\n");
        case "quote": return serializeBlocks(b.content).split("\n").map((l) => "> " + l).join("\n");
        case "code": return "```" + (b.lang || "") + "\n" + b.text + "\n```";
        case "rule": return "---";
        case "panel": return ":::" + b.kind + "\n" + serializeBlocks(b.content) + "\n:::";
        case "ticket": return "[[" + b.key + "]]";
        case "image": return "![" + (b.alt || "") + "](image:" + b.id + ")";
        case "toc": return "[[toc]]";
        case "children": return "[[sous-pages]]";
        case "table": {
          const line = (row) => "| " + row.map((cell) => inlineText(cell).replace(/\|/g, "\\|").replace(/\n/g, " ")).join(" | ") + " |";
          const out = b.rows.map(line);
          if (b.header) out.splice(1, 0, "| " + b.rows[0].map(() => "---").join(" | ") + " |");
          return out.join("\n");
        }
        default: return "";
      }
    }).join("\n\n");
  }

  function serialize(doc) { return serializeBlocks((doc || {}).content); }

  /* ---------- Editor screen ---------- */
  function wrap(area, before, after, placeholder) {
    const start = area.selectionStart, end = area.selectionEnd;
    const selected = area.value.slice(start, end) || placeholder || "";
    area.setRangeText(before + selected + after, start, end, "select");
    area.focus();
    area.dispatchEvent(new Event("input"));
  }

  function insertLine(area, text) {
    const pos = area.selectionStart;
    const needsBreak = pos > 0 && area.value[pos - 1] !== "\n";
    area.setRangeText((needsBreak ? "\n\n" : "") + text + "\n", pos, area.selectionEnd, "end");
    area.focus();
    area.dispatchEvent(new Event("input"));
  }

  /* ---------- Images: paste, drop, file picker (D-B-004) ---------- */
  const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
  const MAX_IMAGE_MB = 10;

  function altFromName(name) {
    const base = String(name || "").replace(/\.[a-z0-9]{2,5}$/i, "").replace(/[\]\[_]+/g, " ").trim();
    return /^image$/i.test(base) || !base ? "Image collée" : base.slice(0, 120);
  }

  /* Upload each image, then hand it to `insert(id, alt)` (visual or source). */
  function imageUploader(ctx, status, insert) {
    const url = "/api/dynamite/p/" + ctx.pid + "/images";
    return async function uploadFiles(files) {
      for (const file of files) {
        if (!IMAGE_TYPES.includes(file.type)) {
          toast("« " + file.name + " » n'est pas une image PNG, JPEG, GIF ou WebP.", "error");
          continue;
        }
        if (file.size > MAX_IMAGE_MB * 1048576) {
          toast("« " + file.name + " » dépasse " + MAX_IMAGE_MB + " Mo : réduisez-la ou exportez-la en JPEG.", "error");
          continue;
        }
        status.textContent = "Envoi de « " + (file.name || "l'image") + " »…";
        try {
          const saved = await api.upload(url, file);
          insert(saved.id, altFromName(file.name));
        } catch (err) { toast(err.message, "error"); }
      }
      status.textContent = "";
    };
  }

  function wireImages(area, uploadFiles) {
    const imagesIn = (list) => Array.from(list || []).filter((f) => f.type && f.type.startsWith("image/"));
    area.addEventListener("paste", (ev) => {
      const data = ev.clipboardData;
      const files = imagesIn(data && data.files);
      // Excel/Word put both text and a picture on the clipboard: keep the text then.
      if (!files.length || (data.getData("text/plain") || "").trim()) return;
      ev.preventDefault();
      uploadFiles(files);
    });
    area.addEventListener("dragover", (ev) => {
      if (Array.from(ev.dataTransfer.types || []).includes("Files")) { ev.preventDefault(); area.classList.add("dy-dropping"); }
    });
    area.addEventListener("dragleave", () => area.classList.remove("dy-dropping"));
    area.addEventListener("drop", (ev) => {
      area.classList.remove("dy-dropping");
      const files = imagesIn(ev.dataTransfer && ev.dataTransfer.files);
      if (!files.length) return;
      ev.preventDefault();
      uploadFiles(files);
    });
  }

  /* ---------- Source mode (short syntax + live preview) ---------- */
  function sourcePane(ctx, area, onSave, uploadFiles, pickImage) {
    const preview = el("div", { class: "dy-preview" });
    const refresh = () => { clear(preview); preview.append(DY.render(parse(area.value))); };
    let timer = null;
    area.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(refresh, 250); });
    area.addEventListener("keydown", (ev) => {
      if (!(ev.ctrlKey || ev.metaKey)) return;
      const k = ev.key.toLowerCase();
      if (k === "b") { ev.preventDefault(); wrap(area, "**", "**", "gras"); }
      if (k === "i") { ev.preventDefault(); wrap(area, "*", "*", "italique"); }
      if (k === "u") { ev.preventDefault(); wrap(area, "__", "__", "souligné"); }
      if (k === "k") { ev.preventDefault(); wrap(area, "[", "](https://)", "texte du lien"); }
      if (k === "s") { ev.preventDefault(); onSave(); }
    });
    wireImages(area, uploadFiles);

    const btn = (label, title, action) => el("button", { type: "button", class: "dy-tool", title, onclick: action }, label);
    const panelSelect = el("select", { class: "dy-tool-select", "aria-label": "Insérer un panneau" },
      el("option", { value: "" }, "Panneau…"),
      Object.entries(DY.PANEL_LABELS).map(([k, v]) => el("option", { value: k }, v)));
    panelSelect.addEventListener("change", () => {
      if (panelSelect.value) insertLine(area, ":::" + panelSelect.value + "\nTexte du panneau\n:::");
      panelSelect.value = "";
    });
    async function insertTicket() {
      const vals = await DY.ask("Insérer un ticket Agile", [{ label: "Clé du ticket", placeholder: "EQP-4", max: 30 }], "Insérer");
      const key = vals ? vals[0].trim().toUpperCase() : "";
      if (!key) return;
      try {
        const t = await api.get("/api/dynamite/ticket/" + encodeURIComponent(key));
        insertLine(area, "[[" + t.key + "]]");
      } catch (err) {
        toast(err.status === 404 ? key + " introuvable ou non accessible. Vérifiez la clé dans Agile → Tickets."
          : err.message, "error");
      }
    }
    const toolbar = el("div", { class: "dy-toolbar", role: "toolbar", "aria-label": "Mise en forme (source)" },
      btn("H1", "Titre", () => insertLine(area, "# Titre")),
      btn("H2", "Sous-titre", () => insertLine(area, "## Sous-titre")),
      btn("H3", "Titre niveau 3", () => insertLine(area, "### Titre")),
      el("span", { class: "dy-tool-sep" }),
      btn("G", "Gras (Ctrl+B)", () => wrap(area, "**", "**", "gras")),
      btn("I", "Italique (Ctrl+I)", () => wrap(area, "*", "*", "italique")),
      btn("S", "Souligné (Ctrl+U)", () => wrap(area, "__", "__", "souligné")),
      btn("B̶", "Barré", () => wrap(area, "~~", "~~", "barré")),
      btn("</>", "Code en ligne", () => wrap(area, "`", "`", "code")),
      btn("🔗", "Lien (Ctrl+K)", () => wrap(area, "[", "](https://)", "texte du lien")),
      el("span", { class: "dy-tool-sep" }),
      btn("• Liste", "Liste à puces", () => insertLine(area, "- élément\n- élément")),
      btn("1. Liste", "Liste numérotée", () => insertLine(area, "1. élément\n2. élément")),
      btn("⊞", "Tableau", () => insertLine(area, "| Colonne 1 | Colonne 2 |\n| --- | --- |\n| | |")),
      btn("{ }", "Bloc de code", () => insertLine(area, "```\ncode\n```")),
      btn("―", "Séparateur", () => insertLine(area, "---")),
      panelSelect,
      btn("🎫 Ticket", "Insérer un bloc Ticket Agile", insertTicket),
      btn("🖼 Image", "Insérer une image (ou collez-la avec Ctrl+V)", pickImage));
    const help = el("details", { class: "dy-help" }, el("summary", null, "Aide-mémoire de la syntaxe"),
      DA.table(["Écrire", "Pour"], HELP.map(([a, b]) => el("tr", null, el("td", null, el("code", null, a)), el("td", null, b)))));
    const element = el("div", null, toolbar, help,
      el("div", { class: "dy-split" },
        el("div", { class: "dy-split-pane" }, el("div", { class: "dy-pane-label" }, "Source"), area),
        el("div", { class: "dy-split-pane" }, el("div", { class: "dy-pane-label" }, "Aperçu"), preview)));
    return { element, refresh };
  }

  const MODE_KEY = "dynamite.editorMode";
  function preferredMode() { try { return localStorage.getItem(MODE_KEY) === "source" ? "source" : "visual"; } catch (e) { return "visual"; } }
  function rememberMode(mode) { try { localStorage.setItem(MODE_KEY, mode); } catch (e) { /* private window */ } }

  async function openEditor(page, ctx, existing) {
    const url = "/api/dynamite/p/" + ctx.pid + "/pages";
    let lockTimer = null;
    if (existing) {
      try {
        await api.post(url + "/" + existing.id + "/lock");
        lockTimer = setInterval(() => api.post(url + "/" + existing.id + "/lock").catch(() => {}), 10 * 60 * 1000);
      } catch (err) {
        toast(err.message, "error");
        location.replace("#/dynamite/" + ctx.key + "/page/" + existing.id);  // the editor leaves no history entry
        return;
      }
    }
    let visual = null;
    const stopLock = () => {
      if (lockTimer) clearInterval(lockTimer);
      if (existing) api.del(url + "/" + existing.id + "/lock").catch(() => {});
      if (visual) visual.destroy();
    };

    const title = el("input", { type: "text", class: "dy-title-input", maxlength: 200,
      placeholder: "Titre de la page", value: existing ? existing.title : "" });
    const area = el("textarea", { class: "dy-source", spellcheck: "true", "aria-label": "Contenu de la page (source)" });
    const note = el("input", { type: "text", maxlength: 200, placeholder: "Note de version (optionnel)", class: "dy-note-input" });
    const error = el("p", { class: "form-error", role: "alert" });
    const uploadStatus = el("span", { class: "dy-upload-status", role: "status" });
    let mode = preferredMode();

    const insertImage = (id, alt) => (mode === "visual" ? visual.insertImage(id, alt)
      : insertLine(area, "![" + alt + "](image:" + id + ")"));
    const uploadFiles = imageUploader(ctx, uploadStatus, insertImage);
    const picker = el("input", { type: "file", accept: IMAGE_TYPES.join(","), multiple: true, hidden: true,
      onchange: () => { uploadFiles(Array.from(picker.files)); picker.value = ""; } });
    const pickImage = () => picker.click();

    const initial = existing ? existing.body : { type: "doc", content: [] };
    area.value = serialize(initial);
    const source = sourcePane(ctx, area, save, uploadFiles, pickImage);
    function aiImport() {
      DY.openAiImport({ ctx, pageTitle: title.value.trim(), onInsert: (doc, how) => {
        if (how.title) title.value = how.title;
        if (mode === "visual") {
          if (how.replace) visual.setDoc(doc); else visual.insertDoc(doc);
        } else {
          if (how.replace) area.value = serialize(doc); else insertLine(area, serialize(doc));
          source.refresh();
        }
      } });
    }
    visual = DY.visualEditor({ ctx, onSave: save, uploadFiles, pickImage, aiImport });
    visual.setDoc(initial);
    const visualBox = el("div", { class: "dy-visual-mode" }, visual.toolbar, visual.element);

    const currentDoc = () => (mode === "visual" ? visual.getDoc() : parse(area.value));
    const modeBtn = (value, label) => el("button", { type: "button", class: "dy-mode-btn", "data-mode": value,
      onclick: () => switchMode(value) }, label);
    const modes = el("div", { class: "dy-modes", role: "group", "aria-label": "Mode d'édition" },
      modeBtn("visual", "Visuel"), modeBtn("source", "Source"));
    function showMode() {
      visualBox.hidden = mode !== "visual";
      source.element.hidden = mode !== "source";
      modes.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    }
    function switchMode(next) {
      if (next === mode) return;
      if (next === "source") { area.value = serialize(visual.getDoc()); source.refresh(); }
      else visual.setDoc(parse(area.value));
      mode = next;
      rememberMode(mode);
      showMode();
      if (mode === "visual") visual.focus(); else area.focus();
    }

    async function save() {
      error.textContent = "";
      const body = currentDoc();
      try {
        if (existing) {
          await api.put(url + "/" + existing.id, { title: title.value, body, note: note.value,
            base_version: existing.version });
          stopLock();
          toast("Page enregistrée (version " + (existing.version + 1) + ").", "success");
          location.replace("#/dynamite/" + ctx.key + "/page/" + existing.id);  // the editor leaves no history entry
        } else {
          const created = await api.post(url, { title: title.value, body, parent_id: ctx.parentId || null });
          if (visual) visual.destroy();
          toast("Page créée.", "success");
          location.replace("#/dynamite/" + ctx.key + "/page/" + created.id);
        }
      } catch (err) { error.textContent = err.message; }
    }

    page.append(
      el("div", { class: "dy-edit-head" }, title,
        el("div", { class: "dy-edit-actions" },
          el("button", { type: "button", class: "btn dy-ai-btn", title: "Coller la réponse d'un agent IA : texte, "
            + "tableaux, liens, images", onclick: aiImport }, "✨ Importer d'une IA"), modes, note,
          el("button", { type: "button", class: "btn", onclick: () => {
            stopLock();
            location.replace(existing ? "#/dynamite/" + ctx.key + "/page/" + existing.id : "#/dynamite/" + ctx.key);
          } }, "Annuler"),
          el("button", { type: "button", class: "btn btn-primary", onclick: save }, "Enregistrer (Ctrl+S)"))),
      error, picker, uploadStatus, visualBox, source.element);
    showMode();
    source.refresh();
    if (!existing) title.focus(); else if (mode === "visual") visual.focus(); else area.focus();
    window.addEventListener("hashchange", stopLock, { once: true });
  }

  Object.assign(DY, { parse, serialize, openEditor });
})();
