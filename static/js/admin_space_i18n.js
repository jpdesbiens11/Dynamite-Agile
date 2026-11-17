/* Fiche d'un Space → « Contenu en anglais (FR | EN) » (0.60.108, D-O-120): the English of the Space's own texts, kept in
   the database with the Space (core/space_i18n.py) and shown when someone switches the top bar to EN. French stays the
   reference. « Copier pour l'IA » takes the texts not translated yet with the instructions; the answer {French: English}
   is pasted (or a .json file chosen), previewed, then applied. Nothing is sent to an AI by the server. */
(function () {
  "use strict";

  const { api, el, toast, modal, field } = DA;

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (err) { /* no clipboard: show it */ }
    const area = el("textarea", { rows: 14, class: "si-area", readonly: true });
    area.value = text;
    modal("À copier pour l'assistant IA", el("div", null, el("p", { class: "muted" }, "Sélectionnez tout (Ctrl+A), copiez (Ctrl+C)."), area));
    area.select();
    return false;
  }

  function importDialog(p, done) {
    const area = el("textarea", { rows: 12, class: "si-area", placeholder: "{\"Texte français\": \"English text\", …}",
      "aria-label": "Réponse de l'assistant IA (JSON)" });
    const file = el("input", { type: "file", accept: ".json,application/json", "aria-label": "Fichier de traduction (.json)" });
    file.addEventListener("change", async () => { if (file.files[0]) area.value = await file.files[0].text(); });
    const replace = el("input", { type: "checkbox" });
    const preview = el("div", { class: "si-preview", role: "status" });
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true }, "Appliquer");
    let close = null, body = null;
    const read = () => {
      const text = area.value.trim().replace(/^```(?:json)?\s*|\s*```$/g, "");
      try { return JSON.parse(text); } catch (err) { throw new Error("JSON illisible. Correctif : collez seulement l'objet {…} rendu par l'assistant."); }
    };
    const check = async () => {
      preview.textContent = "";
      apply.disabled = true;
      try {
        body = { pairs: read(), mode: replace.checked ? "replace" : "merge" };
        const r = await api.put("/api/projects/" + p.id + "/i18n", Object.assign({ dry_run: true }, body));
        preview.append(el("p", null, el("strong", null, r.added + " nouveau(x)"), " · " + r.changed + " corrigé(s) · " + r.removed
          + " retiré(s) · " + r.unchanged + " identique(s)"),
          r.examples.length ? el("ul", { class: "si-examples" }, r.examples.map((x) => el("li", null, el("span", { class: "muted" }, x.fr),
            " → ", x.en))) : null);
        apply.disabled = !(r.added || r.changed || r.removed);
      } catch (err) { preview.append(el("p", { class: "form-error" }, err.message)); }
    };
    apply.addEventListener("click", async () => {
      try {
        const r = await api.put("/api/projects/" + p.id + "/i18n", body);
        close(); toast(r.count + " texte(s) traduit(s) pour " + p.key + ".", "success");
        if (DA.i18nReload) DA.i18nReload();
        done();
      } catch (err) { toast(err.message, "error"); }
    });
    const form = el("div", { class: "form" },
      el("p", { class: "muted" }, "Collez la réponse de l'assistant IA (un objet JSON {français: anglais}) ou choisissez un fichier .json "
        + "exporté d'ici. Une traduction vide retire la paire."),
      field("Réponse ou fichier", area), file,
      el("label", { class: "check" }, replace, "Remplacer tout le dictionnaire du Space (sinon : ajouter et corriger)"),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Aperçu"), apply),
      preview);
    close = modal("Importer la traduction EN — " + p.key, form);
  }

  function section(p) {
    const box = el("section", { class: "si-box", "data-new": "0.60.108-space-i18n" });
    const stat = el("p", { class: "muted" }, "…");
    const refresh = async () => {
      try {
        const r = await api.get("/api/projects/" + p.id + "/i18n/texts");
        stat.textContent = r.translated + " texte(s) traduit(s) · " + r.total + " texte(s) du Space encore en français seulement.";
        return r;
      } catch (err) { stat.textContent = err.message; return null; }
    };
    box.append(
      el("h3", null, "Contenu en anglais (FR | EN)"),
      el("p", { class: "muted" }, "Le bouton FR | EN du coin droit traduit l'interface. Ici, l'anglais des textes écrits dans ce Space "
        + "(requirements, fonctions, briques, pages, Budget Lines…) : il reste dans la base avec le Space, suit sa sauvegarde (.zip) et "
        + "n'est jamais dans un fichier du code. Le français reste la référence ; l'anglais s'affiche à qui passe en EN."),
      stat,
      el("div", { class: "actions" },
        el("button", { type: "button", class: "btn", onclick: async () => {
          const r = await refresh();
          if (!r) return;
          if (!r.texts.length) { toast("Tout est traduit.", "success"); return; }
          const ok = await copy(r.prompt + "\n" + JSON.stringify(r.texts, null, 0));
          if (ok) toast(r.texts.length + " texte(s) copiés avec les instructions : collez-les à votre assistant IA.", "success");
        } }, "Copier pour l'IA"),
        el("button", { type: "button", class: "btn", onclick: () => importDialog(p, refresh) }, "Importer la traduction…"),
        el("a", { class: "btn", href: "/api/projects/" + p.id + "/i18n.json", download: "" }, "Exporter (.json)")));
    refresh();
    return box;
  }

  DA.spaceI18n = { section };
})();
