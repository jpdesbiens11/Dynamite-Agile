/* Diamond · round trip with a spreadsheet or an AI assistant (0.60.104, D-O-116): the three buttons of the DFMEA, the PFMEA and
   the control plans.
   « Exporter (.csv) »    the table, for a spreadsheet.
   « Prompt pour l'IA »   a prompt template built by the server from the Space, for Claude, Gemini or another LLM: « Entrevue
                          guidée » (one question at a time, the table when the engineer writes « GÉNÈRE »), « Révision » (corrections
                          and missing rows at once), « Générer » for the PFMEA (from the DFMEA and the line). Copied, or shown to copy.
   « Importer »           the answer (a ```json block) or the edited CSV, pasted or chosen: a preview line by line -- new, changed
                          (field: before → after), identical, refused (with its reason) --, the person unticks what she does not
                          want, then « Appliquer la sélection ». Nothing is ever deleted. */
(function () {
  "use strict";

  const { api, el, toast, modal } = DA;
  const D = DA.diamond = DA.diamond || {};
  const MODES = {
    interview: ["Entrevue guidée", "L'IA pose une question à la fois, dans l'ordre de la méthode, puis rend le tableau quand vous écrivez « GÉNÈRE »."],
    review: ["Révision", "L'IA lit le tableau actuel et propose en une fois ses corrections et les lignes qui manquent."],
    generate: ["Générer depuis le DFMEA et la ligne", "L'IA propose le PFMEA à partir des lignes classées du DFMEA et des opérations de la ligne."]};

  async function toClipboard(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (err) { return false; }
  }

  function promptDialog(o) {
    const modes = o.modes || ["interview", "review"];
    let chosen = modes[0];
    const radios = modes.map((m) => {
      const r = el("input", { type: "radio", name: "dm-ai-mode", value: m, checked: m === chosen });
      r.addEventListener("change", () => { chosen = m; });
      return el("label", { class: "dm-ai-mode" }, r, el("span", null, el("strong", null, MODES[m][0]), el("span", { class: "muted" }, " — " + MODES[m][1])));
    });
    const out = el("div");
    const build = async () => {
      DA.clear(out);
      let res;
      try { res = await api.get(o.base + "/prompt?mode=" + chosen + (o.query ? "&" + o.query() : "")); } catch (err) { toast(err.message, "error"); return; }
      const field = el("textarea", { rows: 12, readonly: true, class: "dm-story-ai-text", "aria-label": "Prompt" }, res.prompt);
      const copied = await toClipboard(res.prompt);
      const again = el("button", { type: "button", class: "btn btn-small", onclick: () => {  // a page served without HTTPS: the selection, copied
        field.select();
        toast(document.execCommand && document.execCommand("copy") ? "Prompt copié." : "Copiez le texte sélectionné (Ctrl + C).", "success");
      } }, "Copier");
      out.append(el("p", { class: copied ? "up-ok" : "muted" }, copied ? "✓ Prompt copié (" + res.prompt.length + " caractères) : collez-le dans "
        + "Claude, Gemini ou un autre assistant. Sa réponse finale est un bloc JSON : « Importer » ici." : "Copiez ce texte (" + res.prompt.length
        + " caractères) et collez-le dans Claude, Gemini ou un autre assistant. Sa réponse finale est un bloc JSON : « Importer » ici."), field, again);
      field.select();
    };
    modal("Prompt pour l'IA · " + o.title, el("div", { class: "form dm-ai-dialog", "data-new": "0.60.104-ai-prompt" },
      el("p", { class: "muted" }, "Le prompt contient le tableau actuel, les codes utilisables du Space et le format de réponse exact. "
        + "Rien ne quitte la plateforme : vous copiez, vous collez."), el("fieldset", null, el("legend", null, "Mode"), radios),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: build }, "Préparer et copier le prompt")), out));
  }

  function previewTable(res, boxes) {
    const c = res.counts;
    const rows = res.entries.map((e) => {
      const box = e.kind === "new" || e.kind === "update" ? el("input", { type: "checkbox", checked: true, "aria-label": "Appliquer " + (e.code || "#" + e.n) }) : null;
      if (box) boxes.push([e, box]);
      return el("tr", { class: "dm-ai-" + e.kind }, el("td", null, box), el("td", { class: "dm-code nowrap" }, String(e.n)),
        el("td", { class: "dm-code nowrap" }, e.code || "—"), el("td", null, el("span", { class: "dm-ai-kind" }, e.kind_label)), el("td", null, e.label),
        el("td", null, e.reason ? el("span", { class: "dm-ch-miss" }, e.reason)
          : el("ul", { class: "dm-ai-changes" }, e.changes.map(([f, a, b]) => el("li", null, el("strong", null, f), " : ", a ? el("del", null, a) : null, a ? " → " : null, b || "—")))));
    });
    return el("div", { class: "dm-import-preview" },
      el("p", null, el("strong", null, "Aperçu : "), [c.new + " nouvelle(s)", c.update + " modifiée(s)", c.same + " identique(s)", c.refused + " refusée(s)"].join(" · ")),
      el("div", { class: "dm-scroll" }, DA.table(["", "N°", "Code", "Résultat", "Ligne", "Changements ou raison"], rows)),
      el("p", { class: "muted" }, "Aucune ligne n'est supprimée : une ligne absente du fichier reste telle quelle. Décochez ce que vous ne voulez pas."));
  }

  function importDialog(o) {
    const text = el("textarea", { rows: 8, class: "dm-story-ai-text", "aria-label": "Réponse de l'IA ou CSV",
      placeholder: "Collez ici la réponse de l'assistant IA (son bloc JSON) ou le contenu du .csv." });
    const file = el("input", { type: "file", accept: ".csv,.json,.txt,text/csv,application/json,text/plain", "aria-label": "Fichier .csv ou .json" });
    const result = el("div");
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true }, "Appliquer la sélection");
    let boxes = [], close = () => {}, run = 0;
    file.addEventListener("change", async () => { if (file.files[0]) { text.value = await file.files[0].text(); check(); } });
    async function check() {
      const mine = ++run;
      DA.clear(result);
      boxes = [];
      apply.disabled = true;
      if (!text.value.trim()) return;
      try {
        const res = await api.post(o.base + "/import", { file: text.value, mode: "preview" });
        if (mine !== run) return;
        result.append(previewTable(res, boxes));
        apply.disabled = !boxes.length;
      } catch (err) { if (mine === run) result.append(el("p", { class: "form-error", role: "alert" }, err.message)); }
    }
    apply.addEventListener("click", async () => {
      apply.disabled = true;
      try {
        const res = await api.post(o.base + "/import", { file: text.value, mode: "apply", skip: boxes.filter(([, b]) => !b.checked).map(([e]) => e.n) });
        toast(res.applied.new + " ligne(s) ajoutée(s)" + (o.drafts ? " en brouillon" : "") + ", " + res.applied.update + " modifiée(s).", "success");
        close();
        o.onDone(res);
      } catch (err) { apply.disabled = false; toast(err.message, "error"); }
    });
    text.addEventListener("change", check);
    close = modal("Importer · " + o.title, el("div", { class: "form dm-ai-dialog", "data-new": "0.60.104-ai-import" },
      el("p", { class: "muted" }, "La réponse de l'IA (un bloc JSON dont les clés sont les en-têtes du CSV) ou le CSV de « Exporter » retouché "
        + "dans un tableur. Un code existant modifie sa ligne ; un code vide en crée une" + (o.drafts ? " (en brouillon)" : "") + "."),
      DA.field("Fichier", file), DA.field("Ou le texte", text),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Vérifier"), apply), result));
    const m = result.closest(".modal");
    if (m) m.classList.add("dm-cls-modal");
  }

  /** The buttons of a page head. o: {base, title, exportHref, query?, modes?, editable, drafts?, onDone(res)}. */
  D.aiTools = function (o) {
    return [
      el("a", { class: "btn btn-small", href: o.exportHref, download: "", "data-new": "0.60.104-ai-export" }, "Exporter (.csv)"),
      el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.104-ai-prompt", onclick: () => promptDialog(o) }, "Prompt pour l'IA"),
      o.editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.104-ai-import", onclick: () => importDialog(o) }, "Importer…") : null
    ].filter(Boolean);
  };
})();
