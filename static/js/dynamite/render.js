/* Dynamite - page renderer. Builds the DOM from the JSON page body
   (D-A-035) with el()/textContent only: no HTML string is ever parsed.
   "Ticket Agile" blocks are live (D-A-036): fetched on display, the key
   opens the ticket in a new tab.

   render(doc, { editable, children }) -- with editable: true the same DOM
   is used as the visual editor's surface (visual.js): atoms (ticket, image,
   status, table of contents, sub-pages) carry data-* attributes and are
   contenteditable=false, so visual_dom.js can read the page back. */
(function () {
  "use strict";

  const { api, el } = DA;
  const PANEL_ICONS = { info: "ℹ", note: "✎", warning: "⚠", success: "✓" };
  const PANEL_LABELS = { info: "Info", note: "Note", warning: "Avertissement", success: "Succès" };
  const COLORS = { red: "Rouge", orange: "Orange", green: "Vert", blue: "Bleu", purple: "Violet", gray: "Gris" };
  const STATUS_COLORS = { gray: "Gris", blue: "Bleu", green: "Vert", yellow: "Jaune", red: "Rouge" };

  function textWithBreaks(text) {
    const parts = String(text || "").split("\n");
    const out = [];
    parts.forEach((part, i) => {
      if (i) out.push(el("br"));
      if (part) out.push(document.createTextNode(part));
    });
    return out;
  }

  function statusNode(n, editable) {
    const color = STATUS_COLORS[n.color] ? n.color : "gray";
    return el("span", { class: "dy-status dy-status-" + color, "data-status": color,
      contenteditable: editable ? "false" : null, title: editable ? "Cliquer pour modifier le status" : null }, n.text);
  }

  function inline(nodes, opts) {
    const editable = !!(opts && opts.editable);
    return (nodes || []).map((n) => {
      if (n.type === "status") return statusNode(n, editable);
      let node = textWithBreaks(n.text);
      for (const mark of n.marks || []) {
        if (mark === "bold") node = el("strong", null, node);
        else if (mark === "italic") node = el("em", null, node);
        else if (mark === "underline") node = el("u", null, node);
        else if (mark === "strike") node = el("s", null, node);
        else if (mark === "code") node = el("code", null, node);
        else if (mark && mark.type === "color" && COLORS[mark.color]) {
          node = el("span", { class: "dy-color-" + mark.color, "data-color": mark.color }, node);
        } else if (mark && mark.type === "link") {
          const external = /^https?:\/\//.test(mark.href);
          node = el("a", { href: mark.href, target: external && !editable ? "_blank" : null,
            rel: external ? "noopener noreferrer" : null }, node);
        }
      }
      return node;
    }).flat();
  }

  function ticketBlock(key) {
    const box = el("div", { class: "dy-ticket dy-ticket-loading" }, el("span", { class: "muted" }, "Ticket " + key + "…"));
    api.get("/api/dynamite/ticket/" + encodeURIComponent(key)).then((t) => {
      DA.clear(box);
      box.classList.remove("dy-ticket-loading");
      const A = DA.agile || {};
      box.append(...[
        A.typeIcon ? A.typeIcon(t.icon_key, t.type_name) : el("span", null, t.type_name),
        el("a", { class: "dy-ticket-key", href: "#/agile/" + t.project_key + "/issue/" + t.number,
          target: "_blank", rel: "noopener", title: "Ouvrir " + t.key + " dans un nouvel onglet" }, t.key + " ↗"),
        el("span", { class: "dy-ticket-title" }, t.title),
        t.is_requirement ? el("span", { class: "badge badge-admin" }, "Requirement") : null,
        A.statusBadge ? A.statusBadge(t.status_name, t.status_category) : el("span", null, t.status_name),
        el("span", { class: "muted dy-ticket-who" }, t.assignee_name || "Non assigné")].filter(Boolean));
    }).catch((err) => {
      DA.clear(box);
      box.classList.remove("dy-ticket-loading");
      box.classList.add("dy-ticket-missing");
      box.append(el("span", { class: "dy-ticket-key" }, key),
        el("span", { class: "muted" }, err.status === 404
          ? "introuvable, ou dans un projet auquel vous n'avez pas accès."
          : err.message));
    });
    return box;
  }

  /* Image (D-B-004): served by the platform after a role check; a missing or
     forbidden image shows the same neutral notice. */
  function imageBlock(b) {
    const img = el("img", { src: "/api/dynamite/image/" + Number(b.id), alt: b.alt || "", loading: "lazy",
      class: "dy-image", decoding: "async" });
    const figure = el("figure", { class: "dy-figure" }, img,
      b.alt ? el("figcaption", null, b.alt) : null);
    img.addEventListener("error", () => {
      DA.clear(figure);
      figure.classList.add("dy-image-missing");
      figure.append(el("span", { class: "muted" }, "Image " + b.id + " introuvable, ou dans un espace auquel vous n'avez pas accès."));
    });
    return figure;
  }

  function tableBlock(b, opts) {
    const rows = (b.rows || []).map((row, r) => el("tr", null, row.map((cell) =>
      el(b.header && r === 0 ? "th" : "td", null, inline(cell, opts)))));
    const table = el("table", { class: "dy-table", "data-header": b.header ? "true" : "false" }, el("tbody", null, rows));
    return opts.editable ? table : el("div", { class: "dy-table-wrap" }, table);
  }

  function tocBlock(opts) {
    const heads = opts.headings || [];
    if (!heads.length) return el("nav", { class: "dy-toc" }, el("p", { class: "muted" }, "Table des matières : aucun titre."));
    return el("nav", { class: "dy-toc", "aria-label": "Table des matières" },
      el("div", { class: "dy-toc-title" }, "Table des matières"),
      el("ul", null, heads.map((h) => el("li", { class: "dy-toc-" + h.level },
        el("button", { type: "button", class: "link-btn", onclick: () => {
          const target = document.getElementById(h.id);
          const calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          if (target) target.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" });
        } }, h.text)))));
  }

  function childrenBlock(opts) {
    const kids = opts.children || [];
    return el("nav", { class: "dy-children-block", "aria-label": "Sous-pages" },
      kids.length ? el("ul", null, kids.map((c) => el("li", null, el("a", { href: c.href }, c.title))))
        : el("p", { class: "muted" }, "Aucune sous-page."));
  }

  function atom(kind, label) {
    return el("div", { class: "dy-atom dy-atom-" + kind, "data-block": kind, contenteditable: "false" }, label);
  }

  function blocks(nodes, opts) {
    const ed = opts.editable;
    return (nodes || []).map((b) => {
      switch (b.type) {
        case "paragraph": return el("p", null, inline(b.content, opts));
        // Page title is the h1 of the screen: content headings start at h2.
        case "heading": {
          const id = !ed && opts.headings ? (opts.headings[opts.headingIndex++] || {}).id : null;
          return el("h" + (Number(b.level) + 1), { class: "dy-h" + b.level, id }, inline(b.content, opts));
        }
        case "bullet_list": return el("ul", null, b.items.map((item) => el("li", null, blocks(item, opts))));
        case "ordered_list": return el("ol", null, b.items.map((item) => el("li", null, blocks(item, opts))));
        case "quote": return el("blockquote", null, blocks(b.content, opts));
        case "code":
          if (ed) return el("pre", { class: "dy-code", "data-lang": b.lang || "" }, el("code", null, b.text));
          return el("pre", { class: "dy-code" }, b.lang ? el("span", { class: "dy-code-lang" }, b.lang) : null,
            el("code", null, b.text));
        case "rule": return el("hr");
        case "panel": return el("div", { class: "dy-panel dy-panel-" + b.kind, role: ed ? null : "note", "data-kind": b.kind },
          el("span", { class: "dy-panel-icon", "aria-label": PANEL_LABELS[b.kind], contenteditable: ed ? "false" : null },
            PANEL_ICONS[b.kind] || "•"),
          el("div", { class: "dy-panel-body" }, blocks(b.content, opts)));
        case "ticket": {
          const box = ticketBlock(b.key);
          if (ed) { box.dataset.block = "ticket"; box.dataset.key = b.key; box.contentEditable = "false"; }
          return box;
        }
        case "image": {
          const fig = imageBlock(b);
          if (ed) {
            Object.assign(fig.dataset, { block: "image", id: String(b.id), alt: b.alt || "" });
            fig.contentEditable = "false";
          }
          return fig;
        }
        case "table": return tableBlock(b, opts);
        case "toc": return ed ? atom("toc", "☰ Table des matières (générée à la lecture)") : tocBlock(opts);
        case "children": return ed ? atom("children", "↳ Liste des sous-pages (générée à la lecture)") : childrenBlock(opts);
        default: return el("p", { class: "muted" }, "[bloc inconnu : " + b.type + "]");
      }
    });
  }

  function collectHeadings(nodes, out) {
    (nodes || []).forEach((b) => {
      if (b.type === "heading") {
        out.push({ level: b.level, text: (b.content || []).map((n) => n.text || "").join(""), id: "dy-h-" + out.length });
      } else if (b.type === "panel" || b.type === "quote") collectHeadings(b.content, out);
      else if (b.type === "bullet_list" || b.type === "ordered_list") (b.items || []).forEach((it) => collectHeadings(it, out));
    });
    return out;
  }

  function render(doc, options) {
    const opts = Object.assign({ editable: false, children: [] }, options || {});
    const content = (doc || {}).content;
    if (!opts.editable) { opts.headings = collectHeadings(content, []); opts.headingIndex = 0; }
    const out = el("div", { class: "dy-content" }, blocks(content, opts));
    if (!out.childNodes.length && !opts.editable) {
      out.append(el("p", { class: "muted" }, "Page vide. Cliquez sur « Modifier » pour la rédiger."));
    }
    return out;
  }

  DA.dynamite = Object.assign(DA.dynamite || {}, { render, inline, PANEL_LABELS, COLORS, STATUS_COLORS });
})();
