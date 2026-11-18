/* Diamond · Golden Nuggets, export of one part or of the four (0.60.124, D-O-137). « PDF » and « Word » at the top right of
   the page open the same dialog: the parts to put in (the part on screen, or the four), the guide of each part or not, and
   the format. PDF: POST …/pdf (pdf_doc.py, the format of the Word documents); Word: POST …/docx (docx_pages.py, the template
   of the Diamond report -- cover page, table of contents, header, the « Co-Intelligence WorkFlow™ » mark in the footer).
   Registered as D.docExporters.nuggets, which pdf.js calls instead of its own export. el() only. */
(function () {
  "use strict";

  const { api, el, modal, toast } = DA;
  const D = DA.diamond = DA.diamond || {};
  D.docExporters = D.docExporters || {};

  async function send(ctx, keys, guide, format) {
    const parts = D.nuggetParts().filter((p) => keys.includes(p.key));
    const title = "Golden Nuggets" + (parts.length === 1 ? " — " + parts[0].label : "");
    await api.download(D.base(ctx) + "/" + format, { title, view: "nuggets", blocks: D.nuggetBlocks(keys, { guide }) });
    toast((format === "docx" ? "Word" : "PDF") + " de « " + title + " » téléchargé.", "success");
  }

  function dialog(ctx, format) {
    const parts = D.nuggetParts();
    const current = D.nuggetsPart || parts[0].key;
    const boxes = parts.map((p) => el("input", { type: "checkbox", value: p.key, checked: p.key === current }));
    const counts = parts.map((p) => p.items.length + (p.key === "disruption" ? D.NUGGETS.CASES.length : 0));
    const guide = el("input", { type: "checkbox", checked: true });
    const radios = [["pdf", "PDF"], ["docx", "Word (.docx)"]].map(([value, label]) => [el("input", { type: "radio", name: "dm-nug-format",
      value, checked: value === format }), label]);
    const go = el("button", { type: "button", class: "btn btn-primary", "data-new": "0.60.124-nuggets-export" });
    const status = el("p", { class: "muted dm-nug-xsum", "aria-live": "polite" });
    const chosen = () => boxes.filter((b) => b.checked).map((b) => b.value);
    const fmt = () => (radios.find(([r]) => r.checked) || radios[0])[0].value;
    const refresh = () => {
      const n = chosen().length;
      go.disabled = !n;
      go.textContent = "Exporter en " + (fmt() === "docx" ? "Word" : "PDF");
      status.textContent = !n ? "Cochez au moins une partie." : n === parts.length ? "Les quatre parties, dans l'ordre des onglets."
        : n + (n > 1 ? " parties." : " partie : « " + parts.find((p) => p.key === chosen()[0]).label + " ».");
    };
    const set = (keys) => { boxes.forEach((b) => { b.checked = keys.includes(b.value); }); refresh(); };
    boxes.concat(guide, radios.map(([r]) => r)).forEach((input) => input.addEventListener("change", refresh));
    const close = modal("Exporter Golden Nuggets", el("div", { class: "dm-nug-export" },
      el("fieldset", null, el("legend", null, "Parties à exporter"),
        parts.map((p, i) => el("label", { class: "dm-nug-xpart" }, boxes[i], el("span", null, p.label),
          el("span", { class: "dm-nug-n" }, counts[i] + " cartes"))),
        el("div", { class: "dm-actions" },
          el("button", { type: "button", class: "btn btn-small", onclick: () => set([current]) }, "Seulement la partie affichée"),
          el("button", { type: "button", class: "btn btn-small", onclick: () => set(parts.map((p) => p.key)) }, "Les quatre parties"))),
      el("label", { class: "dm-nug-xpart" }, guide, el("span", null, "Le guide de chaque partie (contexte, problématique, portée, mode "
        + "d'emploi, contenu des cartes)")),
      el("fieldset", null, el("legend", null, "Format"), radios.map(([r, label]) => el("label", { class: "dm-nug-xpart" }, r, el("span", null, label))),
        el("p", { class: "muted" }, "Les deux suivent le gabarit des documents de Diamond (analyse fonctionnelle, DFMEA) : page de garde, "
          + "table des matières, en-tête avec le numéro et la révision, la marque « DynamiteAgile · Co-Intelligence WorkFlow™ » en pied de page.")),
      status,
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"), go)));
    go.addEventListener("click", async () => {
      go.disabled = true;
      go.textContent = "Export…";
      try {
        await send(ctx, chosen(), guide.checked, fmt());
        close();
      } catch (err) {
        toast(err.message, "error");
        refresh();
      }
    });
    refresh();
  }

  D.docExporters.nuggets = dialog;
})();
