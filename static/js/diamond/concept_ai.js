/* Diamond · the bricks and their sheets with an AI assistant (0.60.105, D-O-117), in an external loop: « Copier pour l'IA » puts the
   prompt built by the server in the clipboard (the tree, or one brick with its functions and the needs and requirements); the
   person iterates with the assistant of the company, then pastes its answer in « Importer la réponse de l'IA »: checked first
   (what would be created), then imported. Nothing is removed; what arrives is « Brouillon IA ». */
(function () {
  "use strict";

  const { api, el, clear, toast, modal } = DA;
  const D = DA.diamond;

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (err) { return false; }
  }

  async function copyPrompt(ctx, path, what) {
    let data;
    try { data = await api.get(D.base(ctx) + path); } catch (err) { toast(err.message, "error"); return; }
    if (await copy(data.prompt)) {
      toast("Prompt copié : collez-le dans votre assistant IA (" + what + "), itérez avec lui, puis importez sa réponse ici.", "ok");
      return;
    }
    const area = el("textarea", { rows: 14, readonly: true, class: "dm-story-ai-text" }, data.prompt);
    modal("Copier pour l'IA", el("div", null, el("p", null, "Copiez ce texte (Ctrl + A, Ctrl + C) et collez-le dans votre assistant IA."), area));
    area.select();
  }

  function importDialog(ctx, done) {
    const area = el("textarea", { rows: 10, class: "dm-story-ai-text", "aria-label": "Réponse de l'assistant IA",
      placeholder: "Collez ici la réponse de l'assistant : le bloc ```json {\"concepts\": […], \"sheets\": […]}```" });
    const result = el("div", { class: "muted", role: "status" }, el("p", null, "Vérifiez d'abord : rien n'est créé avant « Importer »."));
    const go = el("button", { type: "button", class: "btn btn-primary", disabled: "" }, "Importer");
    const say = (t) => { clear(result); result.append(el("p", null, t)); };
    const text = (r) => r.concepts + " brique(s) nouvelle(s), " + r.links + " fonction(s) rattachée(s), " + r.sheets + " feuille(s) de concept"
      + (r.kept ? " ; " + r.kept + " brique(s) déjà là, gardée(s)" : "") + (r.dropped ? " ; " + r.dropped + " fonction(s) laissée(s) de côté "
      + "(inconnue ou déjà dans une brique)" : "") + ".";
    area.addEventListener("input", () => { go.disabled = true; });
    const check = el("button", { type: "button", class: "btn", onclick: async () => {
      try { say("Sera créé : " + text(await api.post(D.base(ctx) + "/concepts/ai", { file: area.value, dry: true }))); go.disabled = false; }
      catch (err) { say(err.message); go.disabled = true; }
    } }, "Vérifier");
    let close = null;
    go.addEventListener("click", async () => {
      try {
        const r = await api.post(D.base(ctx) + "/concepts/ai", { file: area.value });
        close();
        toast("Importé : " + text(r), "success");
        done();
      } catch (err) { say(err.message); }
    });
    close = modal("Importer la réponse de l'IA", el("div", { class: "ag-form" }, area, result,
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"), check, go)));
    document.querySelectorAll(".modal").forEach((m) => m.classList.add("modal-wide"));
    area.focus();
  }

  function sheetAiButtons(ctx, c, editable, done) {
    return [el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.105-sheets-ai",
      "data-tip": "Le prompt qui demande des feuilles de concept pour cette brique : ses fonctions, les besoins et requirements",
      onclick: () => copyPrompt(ctx, "/concepts/" + c.id + "/prompt", "les feuilles de " + c.code) }, "Générer avec l'IA"),
    editable ? el("button", { type: "button", class: "btn btn-small", onclick: () => importDialog(ctx, done) }, "Importer la réponse de l'IA") : null];
  }

  D.sheetAiButtons = sheetAiButtons;
})();
