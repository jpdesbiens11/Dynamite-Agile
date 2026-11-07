/* Diamond · « Coûts et budget » ↔ IA (0.60.66, D-O-075): the two buttons next to « Exporter (.csv) ».
   « Copier le prompt pour l'IA »: the server builds the full instructions from what Diamond holds (Storyline, function
   tree, parts and their functions, risks, key tests, assumptions, current CSV) → clipboard, else a field to copy.
   « Importer (.csv) »: the CSV of the export, or the block the assistant returned, from a file or pasted; a dry run says
   what will be added or changed (nothing is ever deleted), then « Appliquer ». */
(function () {
  "use strict";

  const { api, el, toast, modal } = DA;
  const D = DA.diamond;

  async function toClipboard(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (err) { return false; }
  }

  async function copyPrompt(ctx) {
    let data;
    try { data = await api.get(D.base(ctx) + "/costs/prompt"); } catch (err) { toast(err.message, "error"); return; }
    if (await toClipboard(data.prompt)) {
      toast("Prompt copié (" + data.parts + " pièces) : collez-le dans votre assistant IA, puis « Importer » sa réponse ici.", "ok");
      return;
    }
    const field = el("textarea", { rows: 12, readonly: true, class: "dm-story-ai-text" }, data.prompt);
    modal("Copier le prompt pour l'IA", el("div", null, el("p", null, "Copiez ce texte (Ctrl + A, Ctrl + C) et collez-le dans votre assistant IA."), field));
    field.select();
  }

  function preview(p) {
    const items = [
      p.nre_new ? p.nre_new + " ligne(s) NRE ajoutée(s)" : null,
      p.nre_updated ? p.nre_updated + " ligne(s) NRE modifiée(s)" : null,
      p.lines_new ? p.lines_new + " ligne(s) de coût ajoutée(s)" : null,
      p.lines_updated ? p.lines_updated + " ligne(s) de coût modifiée(s)" : null,
      p.volumes ? "volumes : " + p.volumes.join(", ") : null, p.currency ? "devise : " + p.currency : null].filter(Boolean);
    return el("div", { class: "dm-import-preview" },
      el("p", null, el("strong", null, "Ce qui changera : "), items.length ? items.join(" · ") : "rien, le fichier est identique à la page."),
      p.problems && p.problems.length ? el("ul", { class: "form-error" }, p.problems.map((x) => el("li", null, x))) : null,
      el("p", { class: "muted" }, "Aucune ligne n'est supprimée : une ligne absente du fichier reste dans la page."));
  }

  function importDialog(ctx, onDone) {
    const text = el("textarea", { rows: 9, placeholder: "Collez ici le bloc CSV rendu par l'assistant IA, ou choisissez un fichier .csv.",
      class: "dm-story-ai-text" });
    const file = el("input", { type: "file", accept: ".csv,text/csv,text/plain" });
    const result = el("div");
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true }, "Appliquer");
    let close = null;
    file.addEventListener("change", async () => {
      if (file.files[0]) { text.value = await file.files[0].text(); check(); }
    });
    let run = 0;
    async function check() {
      const mine = ++run;  // the field's « change » and the button can both ask: only the last answer is shown
      DA.clear(result);
      apply.disabled = true;
      if (!text.value.trim()) return;
      try {
        const res = await api.post(D.base(ctx) + "/costs/import", { file: text.value, apply: false });
        if (mine !== run) return;
        DA.clear(result);
        result.append(preview(res.preview));
        apply.disabled = !(res.preview.nre_new + res.preview.nre_updated + res.preview.lines_new + res.preview.lines_updated
          + (res.preview.volumes || res.preview.currency ? 1 : 0));
      } catch (err) { if (mine === run) result.append(el("p", { class: "form-error", role: "alert" }, err.message)); }
    }
    apply.addEventListener("click", async () => {
      apply.disabled = true;
      try {
        const res = await api.post(D.base(ctx) + "/costs/import", { file: text.value, apply: true });
        const n = res.imported;
        toast("Budget importé : " + (n.nre_new + n.lines_new) + " ligne(s) ajoutée(s), " + (n.nre_updated + n.lines_updated) + " modifiée(s).", "ok");
        close();
        onDone(res);
      } catch (err) { apply.disabled = false; toast(err.message, "error"); }
    });
    close = modal("Importer le budget (.csv)", el("div", { class: "form", "data-new": "0.60.66-cost-import" },
      el("p", { class: "muted" }, "Le format est celui d'« Exporter (.csv) » : tableaux « NRE » et « Pièce » avec leurs lignes d'en-tête. "
        + "NRE-3 ou P-5 corrige la ligne existante ; un code vide ajoute une ligne."),
      DA.field("Fichier", file), DA.field("Ou le texte de l'assistant IA", text),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Vérifier"), apply), result));
    text.addEventListener("change", check);
  }

  /** The buttons of the page head; onDone receives the new payload of the page. */
  D.costTools = function (ctx, editable, onDone) {
    return [
      el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.66-cost-prompt", onclick: () => copyPrompt(ctx) }, "Copier le prompt pour l'IA"),
      editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.66-cost-import", onclick: () => importDialog(ctx, onDone) },
        "Importer (.csv)") : null];
  };
})();
