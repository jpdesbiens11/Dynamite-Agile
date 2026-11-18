/* Diamond · « PDF » (0.60.123, D-O-136): on every Diamond page, right next to « ↔ IA », the page as a PDF in the format of the
   platform's Word documents (cover page, header, footer; Letter, or Tabloid landscape when a table is wide). The server builds
   it from the artefacts of the page (POST …/pdf, modules/diamond/pdf_pages.py); a page with a document of its own registers
   D.pdfBuilders[view] = (ctx) -> blocks (Golden Nuggets). Idéation, Kepner-Tregoe, Prioriser and Exporter have no artefact
   of their own: their PDF holds all of Diamond. 0.60.124 (D-O-137): a page that registers D.docExporters[view] = (ctx, format)
   opens its own dialog instead (Golden Nuggets: one part or the four), and gets a « Word » button next to « PDF ». el() only. */
(function () {
  "use strict";

  const { api, el, toast } = DA;
  const D = DA.diamond = DA.diamond || {};
  D.pdfBuilders = D.pdfBuilders || {};
  let cache = null;  // {pid, sections}

  async function pageSections(ctx) {
    if (!cache || cache.pid !== ctx.pid) cache = { pid: ctx.pid, sections: (await api.get(D.base(ctx) + "/rt/sections")).sections };
    return cache.sections.filter((s) => s.pages.includes(ctx.view)).map((s) => s.key);
  }

  function pageTitle(ctx) {
    const item = (D.SHELL.nav || []).flatMap((g) => g.items).find(([k]) => k === ctx.view);
    return item ? item[1] : "Diamond";
  }

  async function exportPdf(ctx, button) {
    button.disabled = true;
    const label = button.textContent;
    button.textContent = "PDF…";
    try {
      const title = pageTitle(ctx);
      const builder = D.pdfBuilders[ctx.view];
      const body = { title, view: ctx.view };
      if (builder) body.blocks = builder(ctx);
      else body.sections = await pageSections(ctx);
      await api.download(D.base(ctx) + "/pdf", body);
      toast("PDF de « " + title + " » téléchargé.", "success");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  }

  /** The button of every Diamond page head, right of « ↔ IA » (SHELL.headTools). */
  D.pdfButton = function (ctx) {
    const own = ["ideation", "kt", "prio", "dexport"].includes(ctx.view) ? "tout Diamond (cette page n'a pas d'artéfacts à elle)" : "cette page";
    const button = el("button", { type: "button", class: "btn btn-small dm-pdf-btn", "data-new": "0.60.123-pdf",
      "data-tip": "Exporter " + own + " en PDF, au format des documents Word (page de garde, en-tête, pied de page)",
      "aria-label": "Exporter " + own + " en PDF" }, "PDF");
    button.addEventListener("click", () => ((D.docExporters || {})[ctx.view] ? D.docExporters[ctx.view](ctx, "pdf") : exportPdf(ctx, button)));
    return button;
  };

  /** « Word », right of « PDF », on a page that has its own export dialog (D.docExporters). */
  D.wordButton = function (ctx) {
    if (!(D.docExporters || {})[ctx.view]) return null;
    const button = el("button", { type: "button", class: "btn btn-small dm-pdf-btn", "data-new": "0.60.124-word",
      "data-tip": "Exporter cette page en Word (.docx), au gabarit des documents de Diamond", "aria-label": "Exporter cette page en Word" }, "Word");
    button.addEventListener("click", () => D.docExporters[ctx.view](ctx, "docx"));
    return button;
  };
})();
