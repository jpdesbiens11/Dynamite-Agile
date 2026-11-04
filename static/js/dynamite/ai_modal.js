/* Dynamite - the « Importer d'une IA » dialog (D-B-018): paste zone, format
   choice, live preview, then insert at the caret or replace the page.
   Conversion lives in ai_import.js; nothing here inserts HTML. */
(function () {
  "use strict";

  const { el, clear, toast, modal } = DA;
  const DY = DA.dynamite;

  const FORMATS = [["auto", "Détection automatique"], ["html", "Mise en forme copiée (HTML)"],
    ["markdown", "Markdown"], ["text", "Texte brut"]];

  function firstHeading(doc) {
    const i = doc.content.findIndex((b) => b.type === "heading");
    if (i !== 0) return null;
    const title = doc.content[0].content.map((n) => n.text || "").join("").trim();
    return title ? { title: title.slice(0, 200), rest: Object.assign({}, doc, { content: doc.content.slice(1) }) } : null;
  }

  /* options: { ctx, pageTitle: string, onInsert(doc, { replace, title }) } */
  function openAiImport(options) {
    const AI = DY.aiImport;
    let clip = { html: "", text: "", files: [] };
    let built = null;  // { doc (with markers), images, format }

    const zone = el("div", { class: "dy-ai-zone", contenteditable: "true", role: "textbox", tabindex: "0",
      "aria-label": "Zone de collage : collez ici la réponse de l'agent IA (Ctrl+V)" });
    const format = el("select", { class: "dy-ai-format", "aria-label": "Format du contenu" },
      FORMATS.map(([v, l]) => el("option", { value: v }, l)));
    const detected = el("span", { class: "muted dy-ai-detected" });
    const preview = el("div", { class: "dy-content dy-ai-preview", "aria-live": "polite" },
      el("p", { class: "muted" }, "L'aperçu apparaît ici dès que vous collez du contenu."));
    const statLine = el("p", { class: "muted dy-ai-stats" });
    const status = el("span", { class: "dy-upload-status", role: "status" });
    const replace = el("input", { type: "checkbox" });
    const useTitle = el("input", { type: "checkbox", checked: !options.pageTitle });
    const file = el("input", { type: "file", accept: ".md,.markdown,.txt,.html,.htm,text/markdown,text/plain,text/html",
      hidden: true, onchange: async () => {
        const f = file.files[0];
        file.value = "";
        if (!f) return;
        const content = await f.text();
        const isHtml = /\.html?$/i.test(f.name) || f.type === "text/html";
        clip = { html: isHtml ? content : "", text: isHtml ? "" : content, files: [] };
        zone.textContent = "« " + f.name + " » chargé (" + Math.round(content.length / 1024) + " Ko).";
        build();
      } });

    function chooseFormat() {
      if (format.value !== "auto") return format.value;
      if (clip.html.trim()) return "html";
      return DY.looksLikeMarkdown(clip.text) ? "markdown" : "text";
    }

    function build() {
      const images = [];
      const kind = chooseFormat();
      let doc;
      if (kind === "html" && clip.html.trim()) doc = AI.htmlToDocWithImages(clip.html, images);
      else if (kind === "markdown" || (kind === "html" && !clip.html.trim())) doc = DY.parse(AI.markdownToShort(clip.text, images));
      else doc = DY.textToDoc(clip.text);
      clip.files.forEach((f) => {
        const marker = AI.imageMarker(images, "", f.name && !/^image\.\w+$/i.test(f.name) ? f.name.replace(/\.\w+$/, "") : "Image collée");
        images[images.length - 1].file = f;
        doc.content.push({ type: "paragraph", content: [{ type: "text", text: marker }] });
      });
      built = { doc, images, kind };
      detected.textContent = format.value === "auto" && (clip.html || clip.text)
        ? "Détecté : " + FORMATS.find(([v]) => v === kind)[1] : "";
      clear(preview);
      const shown = AI.expand(doc, images, {});
      if (!shown.content.length) {
        preview.append(el("p", { class: "muted" }, "Rien à importer : collez du texte, un tableau ou une image."));
        statLine.textContent = "";
        return;
      }
      preview.append(DY.render(shown));
      statLine.textContent = AI.stats(shown, images);
      if (!options.pageTitle) useTitle.checked = !!firstHeading(shown);
    }

    zone.addEventListener("paste", (ev) => {
      const data = ev.clipboardData;
      if (!data) return;
      ev.preventDefault();
      clip = { html: data.getData("text/html") || "", text: data.getData("text/plain") || "",
        files: Array.from(data.files || []).filter((f) => f.type && f.type.startsWith("image/")) };
      const summary = [];
      if (clip.text.trim()) summary.push(clip.text.trim().split(/\n/).length + " ligne(s) de texte");
      if (clip.html.trim()) summary.push("mise en forme");
      if (clip.files.length) summary.push(clip.files.length + " image(s)");
      zone.textContent = "Contenu collé : " + (summary.join(", ") || "vide") + ". Collez à nouveau pour remplacer.";
      build();
    });
    zone.addEventListener("drop", (ev) => {
      const dt = ev.dataTransfer;
      if (!dt) return;
      ev.preventDefault();
      const files = Array.from(dt.files || []);
      const textFile = files.find((f) => /\.(md|markdown|txt|html?)$/i.test(f.name));
      if (textFile) {
        const transfer = new DataTransfer();
        transfer.items.add(textFile);
        file.files = transfer.files;
        file.dispatchEvent(new Event("change"));
        return;
      }
      clip = { html: dt.getData("text/html") || "", text: dt.getData("text/plain") || "",
        files: files.filter((f) => f.type && f.type.startsWith("image/")) };
      zone.textContent = "Contenu déposé.";
      build();
    });
    zone.addEventListener("beforeinput", (ev) => { if (ev.inputType !== "insertFromPaste") ev.preventDefault(); });
    format.addEventListener("change", build);

    let close = null;
    async function insert() {
      if (!built || !AI.expand(built.doc, built.images, {}).content.length) {
        toast("Collez d'abord le contenu produit par l'agent IA.", "error");
        return;
      }
      const ids = await AI.uploadImages(options.ctx, built.images, (msg) => { status.textContent = msg; });
      let doc = AI.expand(built.doc, built.images, ids);
      let title = null;
      if (useTitle.checked) {
        const split = firstHeading(doc);
        if (split) { title = split.title; doc = split.rest; }
      }
      const failed = Object.values(ids).filter((v) => v === null).length;
      if (failed) toast(failed + " image(s) non importée(s) (format ou taille) : laissées en texte dans la page.", "error");
      close();
      options.onInsert(doc, { replace: replace.checked, title });
      toast("Contenu IA importé : relisez-le et complétez-le avant d'enregistrer.", "success");
    }

    const body = el("div", { class: "dy-ai" },
      el("ol", { class: "dy-ai-steps" },
        el("li", null, "Dans l'outil IA, copiez la réponse (bouton « Copier » ou sélection + Ctrl+C)."),
        el("li", null, "Cliquez dans la zone ci-dessous et collez (Ctrl+V) — ou ouvrez un fichier .md / .html / .txt."),
        el("li", null, "Vérifiez l'aperçu, puis insérez. Vous pourrez tout modifier ensuite.")),
      zone,
      el("div", { class: "dy-ai-bar" }, format, detected,
        el("button", { type: "button", class: "btn btn-small", onclick: () => file.click() }, "Ouvrir un fichier…"), file),
      el("div", { class: "dy-pane-label" }, "Aperçu"), preview, statLine,
      el("p", { class: "muted dy-ai-note" }, "Titres, listes, tableaux, liens, code, citations et encadrés « > [!NOTE] » "
        + "sont conservés ; les images intégrées sont importées dans l'espace ; les images hébergées sur le web ne sont "
        + "pas chargées (réseau interne) et deviennent un lien."),
      el("div", { class: "dy-ai-options" },
        el("label", { class: "check" }, useTitle, "Utiliser le premier titre comme titre de la page"),
        el("label", { class: "check" }, replace, "Remplacer tout le contenu actuel (sinon : insérer au curseur)")),
      el("div", { class: "form-actions" }, status,
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "button", class: "btn btn-primary", onclick: insert }, "Insérer dans la page")));
    close = modal("Importer du contenu d'un agent IA", body);
    const dialog = body.closest(".modal");
    if (dialog) dialog.classList.add("dy-ai-modal");
    zone.focus();
  }

  DY.openAiImport = openAiImport;
})();
