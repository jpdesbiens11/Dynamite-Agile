/* Diamond · Storyline → IA (0.60.52, D-O-061): the two buttons of the Storyline page.
   « Copier pour l'IA »: the prompt built by the server from the scenes (GET …/story/prompt) goes to the clipboard, else it is
   shown in a field to copy by hand. « Importer la réponse de l'IA »: the JSON the assistant returned, pasted or read from a
   .json file, is checked (dry run: what will be created), then imported into this Space (POST …/import); the team lands on
   the functional tree, every item marked as an AI draft to review. */
(function () {
  "use strict";

  const { api, el, toast, modal } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function toClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      const field = el("textarea", { class: "sh-hidden", readonly: true }, text);
      document.body.append(field);
      field.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      field.remove();
      return ok;
    }
  }

  async function copyPrompt(ctx) {
    let data;
    try { data = await api.get(D.base(ctx) + "/story/prompt"); } catch (err) { toast(err.message, "error"); return; }
    if (await toClipboard(data.prompt)) {
      toast("Prompt copié (" + data.scenes + " scènes) : collez-le dans votre assistant IA, puis importez sa réponse ici.", "ok");
      return;
    }
    const field = el("textarea", { rows: 12, readonly: true, class: "dm-story-ai-text" }, data.prompt);
    modal("Copier pour l'IA", el("div", null, el("p", null, "Copiez ce texte (Ctrl + A, Ctrl + C) et collez-le dans votre assistant IA."), field));
    field.select();
  }

  const LABELS = { functions: "fonctions", ports: "entrées et sorties", flows: "flux", parts: "pièces", risks: "risques projet",
    dfmea: "lignes de DFMEA", story: "scènes", dfmea_tests: "essais clés reliés" };

  function summary(counts) {
    return Object.keys(LABELS).filter((k) => counts[k]).map((k) => counts[k] + " " + LABELS[k]).join(", ") || "rien";
  }

  function importDialog(ctx) {
    const area = el("textarea", { rows: 10, class: "dm-story-ai-text", placeholder: "Collez ici la réponse de l'assistant : le bloc ```json {\"diamond\": …}```",
      "aria-label": "Réponse de l'assistant IA" });
    const file = el("input", { type: "file", accept: ".json,application/json,text/plain", "aria-label": "Fichier JSON" });
    const result = el("p", { class: "muted", role: "status" }, "Vérifiez d'abord : rien n'est créé avant « Importer ».");
    const go = el("button", { type: "button", class: "btn btn-primary", disabled: "" }, "Importer");
    file.addEventListener("change", () => {
      const chosen = file.files && file.files[0];
      if (!chosen) return;
      const reader = new FileReader();
      reader.onload = () => { area.value = String(reader.result || ""); go.disabled = true; };
      reader.readAsText(chosen);
    });
    area.addEventListener("input", () => { go.disabled = true; });
    const check = async () => {
      try {
        const data = await api.post(D.base(ctx) + "/import", { file: area.value, dry: true });
        result.textContent = "Prêt : " + summary(data.counts) + ". Chaque élément arrive en « Brouillon IA », à relire en équipe.";
        go.disabled = false;
      } catch (err) { result.textContent = err.message; go.disabled = true; }
    };
    const close = modal("Importer la réponse de l'IA", el("div", { class: "dm-story-ai", "data-new": "0.60.52-story-import" },
      el("p", null, "L'arbre fonctionnel de ce Space doit être vide. Les scènes du fichier ne servent que si le Space n'a pas encore de Storyline."), area,
      el("label", { class: "dm-story-ai-file" }, "ou un fichier .json : ", file), result,
      el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Vérifier"), go)));
    go.addEventListener("click", async () => {
      try {
        const data = await api.post(D.base(ctx) + "/import", { file: area.value });
        close();
        toast("Importé : " + summary(data.counts) + ".", "ok");
        location.hash = A.href(ctx, "ftree");
      } catch (err) { result.textContent = err.message; }
    });
  }

  function storyAiButtons(ctx, editable, hasScenes) {
    return [hasScenes ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.52-story-copy",
      "data-tip": "Le prompt qui demande à un assistant IA l'arbre et le reste de Diamond, à partir des scènes",
      onclick: () => copyPrompt(ctx) }, "Copier pour l'IA") : null,
    editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.52-story-import-btn",
      onclick: () => importDialog(ctx) }, "Importer la réponse de l'IA") : null];
  }

  DA.diamond = Object.assign(DA.diamond || {}, { storyAiButtons });
})();
