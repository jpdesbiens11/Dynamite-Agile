/* Dynamite - visual editor, part 1: DOM -> page JSON (D-B-006).

   Reads either the editor surface (built by render(doc, {editable: true}))
   or foreign HTML pasted from Word, Excel, Outlook or a web page (parsed
   with DOMParser into an inert document: no script runs, no image loads).
   Only what the page model knows is kept -- the same whitelist the server
   enforces (modules/dynamite/content.py) -- so pasting can never smuggle
   HTML into a page. Styles, classes, scripts, images in HTML, unknown tags:
   dropped, their text kept. */
(function () {
  "use strict";

  const DY = DA.dynamite;
  const BLOCK_TAGS = new Set(["P", "H1", "H2", "H3", "H4", "H5", "H6", "UL", "OL", "BLOCKQUOTE", "PRE", "HR",
    "TABLE", "DIV", "SECTION", "ARTICLE", "FIGURE", "FIGCAPTION", "HEADER", "FOOTER", "MAIN", "ASIDE", "NAV", "LI",
    "DL", "DT", "DD", "ADDRESS", "FIELDSET", "DETAILS", "SUMMARY", "CENTER", "FORM"]);
  const SKIP = new Set(["SCRIPT", "STYLE", "TEMPLATE", "HEAD", "META", "LINK", "TITLE", "NOSCRIPT", "IFRAME",
    "OBJECT", "EMBED", "SVG", "BUTTON", "INPUT", "SELECT", "TEXTAREA", "IMG", "VIDEO", "AUDIO", "CANVAS", "PICTURE"]);
  const COLORS = ["red", "orange", "green", "blue", "purple", "gray"];
  const STATUS = ["gray", "blue", "green", "yellow", "red"];
  const LINK_RE = /^(https?:\/\/[^\s"<>]+|#\/[\w/.\-]*)$/;
  const KEY_RE = /^[A-Z][A-Z0-9]{1,9}-\d+$/;
  const MARK_ORDER = ["bold", "italic", "underline", "strike", "code", "color", "link"];
  const MAX_ROWS = 500, MAX_COLS = 30;

  function markKey(mark) { return typeof mark === "string" ? mark : mark.type; }

  /* Simple marks are added once; link/colour replace an outer one (innermost wins). */
  function addMark(marks, mark) {
    if (typeof mark === "string") return marks.includes(mark) ? marks : marks.concat([mark]);
    return marks.filter((m) => markKey(m) !== mark.type).concat([mark]);
  }

  /* Word/Outlook express bold or italic with inline styles. They are read
     from the text of the attribute (renamed before parsing, see htmlToDoc),
     never applied: the page's CSP forbids inline styles anyway. */
  function styleMarks(elm, marks) {
    const css = (elm.getAttribute && elm.getAttribute("data-dy-style") || "").toLowerCase();
    if (!css) return marks;
    const weight = (css.match(/font-weight\s*:\s*([a-z0-9]+)/) || [])[1];
    if (weight === "bold" || weight === "bolder" || Number(weight) >= 600) marks = addMark(marks, "bold");
    if (/font-style\s*:\s*italic/.test(css)) marks = addMark(marks, "italic");
    if (/text-decoration[a-z-]*\s*:[^;]*underline/.test(css)) marks = addMark(marks, "underline");
    if (/text-decoration[a-z-]*\s*:[^;]*line-through/.test(css)) marks = addMark(marks, "strike");
    return marks;
  }

  function elementMarks(elm, marks) {
    switch (elm.tagName) {
      case "STRONG": case "B": marks = addMark(marks, "bold"); break;
      case "EM": case "I": case "CITE": marks = addMark(marks, "italic"); break;
      case "U": case "INS": marks = addMark(marks, "underline"); break;
      case "S": case "STRIKE": case "DEL": marks = addMark(marks, "strike"); break;
      case "CODE": case "KBD": case "SAMP": case "TT": marks = addMark(marks, "code"); break;
      case "A": {
        const href = elm.getAttribute("href") || "";
        if (LINK_RE.test(href)) marks = addMark(marks, { type: "link", href });
        break;
      }
      default: break;
    }
    const color = elm.getAttribute && elm.getAttribute("data-color");
    if (color !== null && color !== undefined) {
      marks = marks.filter((m) => markKey(m) !== "color");
      if (COLORS.includes(color)) marks = marks.concat([{ type: "color", color }]);
    }
    return styleMarks(elm, marks);
  }

  /* Inline content of `node` appended to `run` (a list of inline nodes). */
  function inlineFrom(node, marks, run) {
    if (node.nodeType === 3) {
      const text = node.nodeValue.replace(/ /g, " ").replace(/[ \t\r\n\f]+/g, " ");
      if (text) run.push({ type: "text", text, marks });
      return;
    }
    if (node.nodeType !== 1 || SKIP.has(node.tagName)) return;
    if (node.tagName === "BR") { run.push({ type: "text", text: "\n", marks }); return; }
    if (node.hasAttribute("data-status")) {
      const label = node.textContent.trim().slice(0, 40);
      const color = node.getAttribute("data-status");
      if (label) run.push({ type: "status", text: label, color: STATUS.includes(color) ? color : "gray" });
      return;
    }
    const next = elementMarks(node, marks);
    const blockish = BLOCK_TAGS.has(node.tagName);
    if (blockish && run.length) run.push({ type: "text", text: "\n", marks });
    node.childNodes.forEach((child) => inlineFrom(child, next, run));
  }

  function sortMarks(marks) {
    return marks.slice().sort((a, b) => MARK_ORDER.indexOf(markKey(a)) - MARK_ORDER.indexOf(markKey(b)));
  }

  /* Merge neighbours with the same marks, trim the ends, drop empties. */
  function cleanInline(run) {
    const out = [];
    run.forEach((n) => {
      if (n.type === "status") { out.push(n); return; }
      const marks = sortMarks(n.marks || []);
      const prev = out[out.length - 1];
      if (prev && prev.type === "text" && JSON.stringify(prev.marks || []) === JSON.stringify(marks)) {
        prev.text += n.text;
      } else {
        out.push(marks.length ? { type: "text", text: n.text, marks } : { type: "text", text: n.text });
      }
    });
    out.forEach((n) => { if (n.type === "text") n.text = n.text.replace(/ *\n */g, "\n").replace(/ {2,}/g, " "); });
    while (out.length && out[0].type === "text" && !(out[0].text = out[0].text.replace(/^[\s]+/, ""))) out.shift();
    while (out.length) {
      const last = out[out.length - 1];
      if (last.type !== "text") break;
      last.text = last.text.replace(/[\s]+$/, "");
      if (last.text) break;
      out.pop();
    }
    return out.filter((n) => n.type === "status" || n.text);
  }

  function atomFrom(elm) {
    const kind = elm.getAttribute("data-block");
    if (kind === "ticket") {
      const key = (elm.getAttribute("data-key") || "").toUpperCase();
      return KEY_RE.test(key) ? { type: "ticket", key } : null;
    }
    if (kind === "image") {
      const id = Number(elm.getAttribute("data-id"));
      return id > 0 ? { type: "image", id, alt: (elm.getAttribute("data-alt") || "").slice(0, 300) } : null;
    }
    if (kind === "toc") return { type: "toc" };
    if (kind === "children") return { type: "children" };
    return null;
  }

  function cellInline(cell) {
    const run = [];
    cell.childNodes.forEach((child) => inlineFrom(child, [], run));
    return cleanInline(run).map((n) => (n.type === "text" ? Object.assign(n, { text: n.text.slice(0, 20000) }) : n));
  }

  function tableFrom(table) {
    const rows = Array.from(table.rows || []).slice(0, MAX_ROWS)
      .map((tr) => Array.from(tr.cells).slice(0, MAX_COLS).map(cellInline))
      .filter((row) => row.length);
    if (!rows.length) return null;
    const first = table.rows[0];
    const header = table.getAttribute("data-header") === "true"
      || (first && first.cells.length > 0 && Array.from(first.cells).every((c) => c.tagName === "TH"));
    return { type: "table", header: !!header, rows };
  }

  function headingLevel(tag, foreign) {
    const n = Number(tag[1]);
    return foreign ? Math.min(3, n) : Math.max(1, Math.min(3, n - 1));
  }

  function blockFrom(elm, opts) {
    const tag = elm.tagName;
    if (/^H[1-6]$/.test(tag)) {
      const content = cleanInline(runOf(elm));
      return content.length ? [{ type: "heading", level: headingLevel(tag, opts.foreign), content }] : [];
    }
    switch (tag) {
      case "P": {
        const content = cleanInline(runOf(elm));
        return content.length ? [{ type: "paragraph", content }] : [];
      }
      case "UL": case "OL": {
        const items = Array.from(elm.children).map((li) => blocksFrom(li, opts)).filter((item) => item.length);
        return items.length ? [{ type: tag === "UL" ? "bullet_list" : "ordered_list", items }] : [];
      }
      case "BLOCKQUOTE": {
        const content = blocksFrom(elm, opts);
        return content.length ? [{ type: "quote", content }] : [];
      }
      case "PRE": {
        const source = elm.isConnected ? elm.innerText : elm.textContent;
        const text = source.replace(/\n$/, "").slice(0, 100000);
        return text.trim() ? [{ type: "code", lang: (elm.getAttribute("data-lang") || "").slice(0, 20), text }] : [];
      }
      case "HR": return [{ type: "rule" }];
      case "TABLE": { const t = tableFrom(elm); return t ? [t] : []; }
      default: break;
    }
    const kind = elm.getAttribute("data-kind");
    if (tag === "DIV" && elm.classList.contains("dy-panel") && ["info", "note", "warning", "success"].includes(kind)) {
      const body = elm.querySelector(":scope > .dy-panel-body") || elm;
      return [{ type: "panel", kind, content: blocksFrom(body, opts) }];
    }
    return blocksFrom(elm, opts);
  }

  function runOf(elm) {
    const run = [];
    elm.childNodes.forEach((child) => inlineFrom(child, [], run));
    return run;
  }

  function blocksFrom(parent, opts) {
    const out = [];
    let run = [];
    const flush = () => {
      const content = cleanInline(run);
      if (content.length) out.push({ type: "paragraph", content });
      run = [];
    };
    parent.childNodes.forEach((child) => {
      if (child.nodeType === 1 && child.hasAttribute("data-block")) {
        flush();
        const atom = atomFrom(child);
        if (atom) out.push(atom);
      } else if (child.nodeType === 1 && (BLOCK_TAGS.has(child.tagName) || child.classList.contains("dy-panel"))) {
        if (child.classList.contains("dy-panel-icon")) return;
        flush();
        out.push(...blockFrom(child, opts));
      } else {
        inlineFrom(child, [], run);
      }
    });
    flush();
    return out;
  }

  function domToDoc(root, options) {
    return { type: "doc", content: blocksFrom(root, Object.assign({ foreign: false }, options || {})) };
  }

  /* Pasted HTML -> page JSON (never inserted as HTML). */
  function htmlToDoc(html) {
    const renamed = String(html || "").replace(/(<[^>]*?\s)style\s*=/gi, "$1data-dy-style=");
    const parsed = new DOMParser().parseFromString(renamed, "text/html");
    return domToDoc(parsed.body, { foreign: true });
  }

  function textToDoc(text) {
    const content = String(text || "").replace(/\r\n?/g, "\n").split(/\n/)
      .map((line) => line.replace(/\t/g, "    ").trimEnd())
      .filter((line) => line.trim())
      .map((line) => ({ type: "paragraph", content: [{ type: "text", text: line }] }));
    return { type: "doc", content };
  }

  Object.assign(DY, { domToDoc, htmlToDoc, textToDoc });
})();
