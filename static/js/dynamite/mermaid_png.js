/* 0.60.62 (D-O-071): the Mermaid drawings go into the PDF / Word exports.
   The server writes the documents but does not know the engine (mermaid_*.js): before an export, the browser asks for
   the Mermaid sources of the page (and its sub-pages), draws each one, turns it into a PNG on a white background and
   sends them with the export. The server puts each image in place of its code and keeps the code under it, in small
   type. A diagram the engine cannot draw stays as code. No external library: an <img> of the SVG, then a <canvas>. */
(function () {
  "use strict";
  const { el } = DA;
  const DY = DA.dynamite = DA.dynamite || {};
  const SCALE = 2;  // same value as export_mermaid.SCALE on the server
  /* The presentation of the SVG lives in dynamite.css; an image of the SVG does not see the page's CSS, so the
     computed values are copied onto each element. */
  const PROPS = ["fill", "fill-opacity", "stroke", "stroke-width", "stroke-dasharray", "stroke-opacity", "opacity",
    "font-family", "font-size", "font-weight", "font-style", "text-anchor", "dominant-baseline"];
  /* The light theme of Dynamite, whatever the screen theme: a printed page is white. */
  const LIGHT = { "--bg": "#ffffff", "--surface": "#ffffff", "--surface-2": "#eef1f4", "--ink": "#16222d", "--muted": "#5a6a79",
    "--line": "#d6dde4", "--dynamite": "#c9501c", "--warn": "#9a6512", "--ok": "#2d7a52", "--danger": "#b83a2e" };

  function inlineStyles(svg) {
    [svg, ...svg.querySelectorAll("*")].forEach((node) => {
      const cs = getComputedStyle(node);
      PROPS.forEach((name) => {
        const value = cs.getPropertyValue(name);
        if (value) node.style.setProperty(name, value);
      });
      node.removeAttribute("class");
    });
  }

  function svgImage(xml) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("image SVG illisible"));
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
    });
  }

  /** PNG (base64, without the data: prefix) of one Mermaid source, or null when the engine cannot draw it. */
  async function png(source) {
    let svg;
    try { svg = DY.mermaid.draw(source); } catch (err) { return null; }
    const host = el("div", { class: "dy-mm-export", "aria-hidden": "true" });
    Object.entries(LIGHT).forEach(([k, v]) => host.style.setProperty(k, v));
    host.style.setProperty("position", "fixed");
    host.style.setProperty("left", "-100000px");
    host.style.setProperty("top", "0");
    host.append(svg);
    (document.querySelector(".content.dy-main") || document.body).append(host);
    try {
      const box = svg.viewBox && svg.viewBox.baseVal;
      const w = Math.ceil((box && box.width) || Number(svg.getAttribute("width")) || 600);
      const h = Math.ceil((box && box.height) || Number(svg.getAttribute("height")) || 400);
      inlineStyles(svg);
      svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      svg.setAttribute("width", String(w));
      svg.setAttribute("height", String(h));
      svg.style.removeProperty("max-width");
      const img = await svgImage(new XMLSerializer().serializeToString(svg));
      const canvas = el("canvas", { width: w * SCALE, height: h * SCALE });
      const g = canvas.getContext("2d");
      g.fillStyle = "#ffffff";  // the PDF writer drops transparency: a white background, never black
      g.fillRect(0, 0, canvas.width, canvas.height);
      g.scale(SCALE, SCALE);
      g.drawImage(img, 0, 0, w, h);
      return canvas.toDataURL("image/png").split(",")[1];
    } catch (err) {
      console.error(err);  // eslint-disable-line no-console
      return null;
    } finally {
      host.remove();
    }
  }

  /** Export a page as PDF or Word with its Mermaid drawings; falls back to the plain link when there are none. */
  async function exportPage(pid, pageId, fmt, kids) {
    const base = "/api/dynamite/p/" + pid + "/pages/" + pageId;
    const found = await DA.api.get(base + "/export/mermaid" + (kids ? "?children=1" : ""));
    const diagrams = {};
    for (const source of found.sources || []) {
      const data = await png(source);
      if (data) diagrams[source] = data;
    }
    await DA.api.download(base + "/export." + fmt, { children: !!kids, diagrams });
    const n = Object.keys(diagrams).length;
    if (n) DA.toast(n + (n > 1 ? " diagrammes Mermaid inclus" : " diagramme Mermaid inclus") + " dans l'export.", "success");
  }

  DY.mermaidPng = png;
  DY.exportPage = exportPage;
})();
