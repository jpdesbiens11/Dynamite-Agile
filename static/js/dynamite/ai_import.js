/* Dynamite - « Coller depuis une IA » (D-B-018).

   Content produced by an AI agent (ChatGPT, Claude, Copilot, Gemini, a
   local model...) arrives as HTML (copy from a chat window), as Markdown
   (the "copy" button of most chats, a .md file) or as plain text. It is
   converted to the page JSON -- never inserted as HTML -- through the same
   whitelist as any paste (visual_dom.js, editor.js parse):
   - headings, bold/italic/strike, inline code, links, lists, task lists,
     tables (GFM), code blocks, quotes, GitHub callouts (> [!NOTE]) -> panels;
   - embedded images (data:) are uploaded to the space and become image
     blocks; images on the web are NOT loaded (internal network only): they
     become a link the reader can open.
   The modal previews the result and inserts it at the caret or replaces
   the page; users then edit and enrich it as usual. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const DY = DA.dynamite;
  const OPEN = "\uE000", CLOSE = "\uE001";
  const MARKER_RE = /\uE000img:(\d+)\uE001/g;
  const CALLOUTS = { NOTE: "note", TIP: "success", IMPORTANT: "info", WARNING: "warning", CAUTION: "warning" };
  const MAX_IMAGE_BYTES = 10 * 1048576;
  const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];

  /* ---------- Markdown (CommonMark / GFM as AI agents write it) ---------- */
  function imageMarker(images, src, alt) {
    images.push({ src: String(src || "").trim(), alt: String(alt || "").trim().slice(0, 300) });
    return OPEN + "img:" + (images.length - 1) + CLOSE;
  }

  function inlineMd(text, images) {
    // Outside code spans only.
    return text.split(/(`[^`]*`)/).map((part, i) => {
      if (i % 2) return part;
      return part
        .replace(/!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g, (m, alt, src) => imageMarker(images, src, alt))
        .replace(/<br\s*\/?>/gi, " ")
        .replace(/<(https?:\/\/[^>\s]+)>/g, "[$1]($1)")
        .replace(/(^|[\s(])(?<!\]\()(https?:\/\/[^\s<>()\]]+[^\s<>()\].,;:!?'"])/g, "$1[$2]($2)")
        .replace(/(^|[^\w_])__(?=\S)([^_]+?)__(?=[^\w_]|$)/g, "$1**$2**")
        .replace(/(^|[^\w*_\\])_(?=\S)([^_\n]+?)_(?=[^\w_]|$)/g, "$1*$2*")
        .replace(/\\([\\`*_{}[\]()#+\-.!>~])/g, "$1");
    }).join("");
  }

  function markdownToShort(md, images) {
    const lines = String(md || "").replace(/\r\n?/g, "\n").split("\n");
    const out = [];
    let fence = null;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const t = line.trim();
      const f = t.match(/^(`{3,}|~{3,})\s*([\w+#.-]{0,20})/);
      if (fence) {
        if (f && t.replace(/[`~]/g, "") === "" && t[0] === fence[0] && t.length >= fence.length) { out.push("```"); fence = null; }
        else out.push(line);
        continue;
      }
      if (f) { fence = f[1]; out.push("```" + f[2]); continue; }
      const callout = t.match(/^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$/i);
      if (callout) {
        out.push(":::" + CALLOUTS[callout[1].toUpperCase()]);
        if (callout[2]) out.push(inlineMd(callout[2], images));
        for (i++; i < lines.length && /^\s*>/.test(lines[i]); i++) out.push(inlineMd(lines[i].replace(/^\s*>\s?/, ""), images));
        i--;
        out.push(":::");
        continue;
      }
      let m;
      if ((m = t.match(/^(#{1,6})\s+(.*?)(?:\s+#+)?(?:\s*\{#[\w-]+\})?\s*$/))) {
        out.push("#".repeat(Math.min(3, m[1].length)) + " " + inlineMd(m[2], images));
      } else if ((m = line.match(/^\s*[-*+•]\s+\[([ xX])\]\s+(.*)$/))) {
        out.push("- " + (m[1] === " " ? "☐ " : "☑ ") + inlineMd(m[2], images));
      } else if ((m = line.match(/^\s*[+•]\s+(.*)$/))) {
        out.push("- " + inlineMd(m[1], images));
      } else if ((m = line.match(/^\s*((?:[-*]|\d+[.)])\s+|>\s?)(.*)$/))) {
        out.push(m[1] + inlineMd(m[2], images));  // list item or quote (nesting flattened)
      } else if (/^(-{3,}|\*{3,}|_{3,})$/.test(t.replace(/\s/g, ""))) {
        out.push("---");
      } else {
        out.push(inlineMd(line, images));
      }
    }
    if (fence) out.push("```");
    return out.join("\n");
  }

  function markdownToDoc(md) {
    const images = [];
    return expand(DY.parse(markdownToShort(md, images)), images, {});
  }

  /* Does plain text look like Markdown (Claude / ChatGPT "copy" button)? */
  function looksLikeMarkdown(text) {
    const s = String(text || "");
    if (/^(#{1,6}\s|```|~~~|\|.*\|\s*$|>\s*\[!)/m.test(s)) return true;
    let score = 0;
    if (/^\s*([-*+]|\d+\.)\s+\S/m.test(s)) score++;
    if (/\*\*[^*\n]+\*\*/.test(s)) score++;
    if (/\[[^\]\n]+\]\(https?:\/\/[^)\s]+\)/.test(s)) score++;
    if (/`[^`\n]+`/.test(s)) score++;
    return score >= 2;
  }

  /* ---------- HTML (copied from a chat window or a web page) ---------- */
  function htmlToDocWithImages(html, images) {
    const withMarkers = String(html || "").replace(/<img\b[^>]*>/gi, (tag) => {
      const attr = (name) => ((tag.match(new RegExp("\\s" + name + "\\s*=\\s*(\"[^\"]*\"|'[^']*'|[^\\s>]+)", "i")) || [])[1] || "")
        .replace(/^["']|["']$/g, "").replace(/&amp;/g, "&").replace(/&quot;/g, "\"");
      return imageMarker(images, attr("src"), attr("alt") || attr("title"));
    });
    return DY.htmlToDoc(withMarkers);
  }

  /* ---------- Markers -> image blocks / links ---------- */
  function placeholder(img, resolved) {
    const label = "🖼 " + (img.alt || "image");
    if (/^https?:\/\//i.test(img.src)) return { type: "text", text: label + " (image externe)", marks: [{ type: "link", href: img.src }] };
    return { type: "text", text: "[" + label + (resolved === false ? " — non importée" : "") + "]" };
  }

  function inlineOnly(nodes, images, ids) {
    const out = [];
    (nodes || []).forEach((n) => {
      if (n.type !== "text" || !n.text.includes(OPEN)) { out.push(n); return; }
      n.text.split(/(\uE000img:\d+\uE001)/).forEach((piece) => {
        const m = piece.match(/^\uE000img:(\d+)\uE001$/);
        if (m) out.push(placeholder(images[Number(m[1])], ids[m[1]] === undefined ? undefined : false));
        else if (piece) out.push(Object.assign({}, n, { text: piece }));
      });
    });
    return out;
  }

  function splitParagraph(block, images, ids) {
    const out = [];
    let run = [];
    const flush = () => {
      if (run.some((n) => n.type !== "text" || n.text.trim())) out.push({ type: "paragraph", content: run });
      run = [];
    };
    (block.content || []).forEach((n) => {
      if (n.type !== "text" || !n.text.includes(OPEN)) { run.push(n); return; }
      n.text.split(/(\uE000img:\d+\uE001)/).forEach((piece) => {
        const m = piece.match(/^\uE000img:(\d+)\uE001$/);
        if (!m) { if (piece) run.push(Object.assign({}, n, { text: piece })); return; }
        const id = ids[m[1]];
        if (id) { flush(); out.push({ type: "image", id, alt: images[Number(m[1])].alt || "Image importée" }); }
        else run.push(placeholder(images[Number(m[1])], id === undefined ? undefined : false));
      });
    });
    flush();
    return out;
  }

  function expand(doc, images, ids) {
    const blocks = (list) => (list || []).flatMap((b) => {
      switch (b.type) {
        case "paragraph": return splitParagraph(b, images, ids);
        case "heading": return [Object.assign({}, b, { content: inlineOnly(b.content, images, ids) })];
        case "quote": case "panel": return [Object.assign({}, b, { content: blocks(b.content) })];
        case "bullet_list": case "ordered_list": return [Object.assign({}, b, { items: b.items.map(blocks) })];
        case "table": return [Object.assign({}, b, { rows: b.rows.map((row) => row.map((cell) => inlineOnly(cell, images, ids))) })];
        default: return [b];
      }
    });
    return { type: "doc", content: blocks(doc.content) };
  }

  /* ---------- Embedded images: upload to the space ---------- */
  function dataUrlToFile(src, index) {
    const m = src.match(/^data:(image\/[a-z+.-]+);base64,([\s\S]+)$/i);
    if (!m || !IMAGE_TYPES.includes(m[1].toLowerCase())) return null;
    const bin = atob(m[2].replace(/\s+/g, ""));
    if (bin.length > MAX_IMAGE_BYTES) return null;
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const ext = m[1].split("/")[1].replace("jpeg", "jpg").replace("svg+xml", "svg");
    return new File([bytes], "image-ia-" + (index + 1) + "." + ext, { type: m[1].toLowerCase() });
  }

  async function uploadImages(ctx, images, report) {
    const ids = {};
    for (let i = 0; i < images.length; i++) {
      const img = images[i];
      if (/^https?:\/\//i.test(img.src)) continue;
      const file = img.file || (img.src.startsWith("data:") ? dataUrlToFile(img.src, i) : null);
      if (!file) { ids[i] = null; continue; }
      try {
        report("Envoi de l'image " + (i + 1) + " / " + images.length + "…");
        ids[i] = (await api.upload("/api/dynamite/p/" + ctx.pid + "/images", file)).id;
      } catch (err) { ids[i] = null; toast(err.message, "error"); }
    }
    report("");
    return ids;
  }

  /* ---------- Statistics shown under the preview ---------- */
  function stats(doc, images) {
    const count = { blocks: 0, headings: 0, tables: 0, links: 0, lists: 0, code: 0 };
    (function walk(list) {
      (list || []).forEach((b) => {
        count.blocks++;
        if (b.type === "heading") count.headings++;
        if (b.type === "table") { count.tables++; b.rows.forEach((r) => r.forEach((c) => c.forEach(inl))); }
        if (b.type === "code") count.code++;
        if (b.type === "bullet_list" || b.type === "ordered_list") { count.lists++; b.items.forEach(walk); }
        if (b.type === "quote" || b.type === "panel") walk(b.content);
        (b.type === "paragraph" || b.type === "heading" ? b.content : []).forEach(inl);
      });
    })(doc.content);
    function inl(n) { if ((n.marks || []).some((m) => m && m.type === "link")) count.links++; }
    const parts = [count.blocks + " bloc(s)", count.headings + " titre(s)", count.tables + " tableau(x)",
      count.lists + " liste(s)", count.links + " lien(s)", count.code + " bloc(s) de code"];
    const embedded = images.filter((i) => !/^https?:/i.test(i.src)).length;
    const external = images.length - embedded;
    if (embedded) parts.push(embedded + " image(s) à importer");
    if (external) parts.push(external + " image(s) externe(s) → lien");
    return parts.join(" · ");
  }

  Object.assign(DY, { markdownToDoc, looksLikeMarkdown, aiImport: { markdownToShort, htmlToDocWithImages, expand,
    uploadImages, stats, imageMarker } });
})();
