/* Diamond · Storyline → IA (0.60.52, D-O-061): the two buttons of the Storyline page.
   « Copier pour l'IA »: the prompt built by the server from the scenes (GET …/story/prompt) goes to the clipboard, else it is
   shown in a field to copy by hand. « Importer la réponse de l'IA »: the JSON the assistant returned, pasted or read from a
   .json file, is checked (dry run: what will be created), then imported into this Space (POST …/import); the team lands on
   the functional tree, every item marked as an AI draft to review. 0.60.53 (D-O-062): « Compléter » brings only what the
   Space is missing; « Tout remplacer » backs the Space up, then rebuilds Diamond from the file. */
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

  const KEPT = { functions: "l'arbre fonctionnel", structure: "la structure", parts: "les pièces", risks: "les risques projet",
    story: "la Storyline" };
  const DROPPED = { functions: "fonction(s) du fichier absente(s) de l'arbre", flows: "flux sans fonction correspondante",
    part_links: "lien(s) de pièce sans fonction correspondante", risks_links: "risque(s) détaché(s) d'une fonction absente",
    dfmea_links: "ligne(s) de DFMEA détachée(s) d'une fonction absente", dfmea_rows: "ligne(s) de DFMEA déjà écrite(s) par l'équipe" };

  function report(data) {
    const lines = [];
    if (data.mode === "replace" && Object.keys(data.removed || {}).length) {
      lines.push("Sera effacé après une sauvegarde complète du Space : " + summary(data.removed) + ".");
    }
    lines.push((data.imported ? "Importé : " : "Sera créé : ") + summary(data.counts) + ", en « Brouillon IA », à relire en équipe.");
    const kept = Object.keys(data.kept || {}).map((k) => KEPT[k] || k);
    if (kept.length) lines.push("Gardé tel quel, déjà dans le Space : " + kept.join(", ") + ".");
    const dropped = Object.keys(data.dropped || {}).map((k) => data.dropped[k] + " " + (DROPPED[k] || k));
    if (dropped.length) lines.push("Laissé de côté : " + dropped.join(" ; ") + ".");
    if (data.backup) lines.push("Sauvegarde : " + data.backup + " (⚙ Admin → Spaces → Sauvegardes).");
    return lines;
  }

  function importDialog(ctx) {
    const area = el("textarea", { rows: 10, class: "dm-story-ai-text", placeholder: "Collez ici la réponse de l'assistant : le bloc ```json {\"diamond\": …}```",
      "aria-label": "Réponse de l'assistant IA" });
    const file = el("input", { type: "file", accept: ".json,application/json,text/plain", "aria-label": "Fichier JSON" });
    const result = el("div", { class: "muted", role: "status" }, el("p", null, "Vérifiez d'abord : rien n'est créé ni effacé avant « Importer »."));
    const go = el("button", { type: "button", class: "btn btn-primary", disabled: "" }, "Importer");
    const state = { mode: "add" };
    const show = (lines) => { DA.clear(result); lines.forEach((t) => result.append(el("p", null, t))); };
    const reset = () => { go.disabled = true; };
    const choice = (value, title, text) => {
      const input = el("input", { type: "radio", name: "dm-import-mode", value });
      if (value === state.mode) input.checked = true;
      input.addEventListener("change", () => {
        state.mode = value;
        go.textContent = value === "replace" ? "Sauvegarder et remplacer" : "Importer";
        go.className = "btn " + (value === "replace" ? "btn-danger" : "btn-primary");
        reset();
      });
      return el("label", { class: "dm-import-mode" }, input, el("span", null, el("strong", null, title), " — " + text));
    };
    const modes = el("fieldset", { class: "dm-import-modes", "data-new": "0.60.53-import-mode" }, el("legend", null, "Ce que l'import fait"),
      choice("add", "Compléter", "ajoute seulement ce qui manque au Space (une partie à la fois, ou tout un Space vide) ; ce qui existe déjà reste tel quel."),
      choice("replace", "Tout remplacer", "écrit d'abord une sauvegarde complète du Space, puis vide Diamond et le refait à partir du fichier "
        + "(la Storyline reste si le fichier n'en a pas). Réservé aux admins du Space."));
    file.addEventListener("change", () => {
      const chosen = file.files && file.files[0];
      if (!chosen) return;
      const reader = new FileReader();
      reader.onload = () => { area.value = String(reader.result || ""); reset(); };
      reader.readAsText(chosen);
    });
    area.addEventListener("input", reset);
    const check = async () => {
      try {
        const data = await api.post(D.base(ctx) + "/import", { file: area.value, dry: true, mode: state.mode });
        show(["Prêt."].concat(report(data)));
        go.disabled = false;
      } catch (err) { show([err.message]); reset(); }
    };
    const close = modal("Importer la réponse de l'IA", el("div", { class: "dm-story-ai", "data-new": "0.60.52-story-import" },
      modes, area, el("label", { class: "dm-story-ai-file" }, "ou un fichier .json : ", file), result,
      el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Vérifier"), go)));
    go.addEventListener("click", async () => {
      go.disabled = true;
      try {
        const data = await api.post(D.base(ctx) + "/import", { file: area.value, mode: state.mode });
        close();
        toast(report(data).join(" "), "ok");
        location.hash = A.href(ctx, "ftree");
      } catch (err) { show([err.message]); }
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
