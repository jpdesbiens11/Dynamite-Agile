/* « Audit » of the interface (core lot v0.7, D-B-022): from any screen,
   capture the page, describe what to fix or improve, and file it in a
   platform-wide list (#/audit, audit_list.js) that administrators plan.

   Capture: the browser's screen-capture API (asks which tab to share; only
   over HTTPS or on localhost). Without it -- e.g. plain HTTP on the internal
   network -- a screenshot is pasted instead (Win+Shift+S then Ctrl+V). The
   image is sent as bytes and checked by the server; nothing is inserted as
   HTML. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field } = DA;
  let meta = null;

  const canCapture = () => !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia && window.isSecureContext);

  function toolOfPage() {
    const key = (location.hash.replace(/^#\/?/, "").split("/")[0] || "home");
    const mod = (DA.session.modules || []).find((m) => m.key === key);
    return mod ? mod.label : ({ home: "Accueil", admin: "Admin", search: "Recherche", audit: "Audit" }[key] || key);
  }

  /* Grab one frame of the shared tab: {dataUrl, blob} or null (refused, unsupported). */
  async function capture() {
    if (!canCapture()) return null;
    let stream = null;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({ video: { displaySurface: "browser" }, audio: false,
        preferCurrentTab: true, selfBrowserSurface: "include" });
      const video = el("video", { muted: true, playsinline: true });
      video.srcObject = stream;
      await video.play();
      await new Promise((r) => setTimeout(r, 350));  // let the picker close and the frame settle
      const canvas = el("canvas", { width: video.videoWidth, height: video.videoHeight });
      canvas.getContext("2d").drawImage(video, 0, 0);
      const blob = await new Promise((r) => canvas.toBlob(r, "image/png"));
      return blob ? { dataUrl: canvas.toDataURL("image/png"), blob } : null;
    } catch (err) {
      return null;  // the user cancelled the picker
    } finally {
      if (stream) stream.getTracks().forEach((t) => t.stop());
    }
  }

  function readFile(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve({ dataUrl: reader.result, blob: file });
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(file);
    });
  }

  async function loadMeta() {
    if (!meta) meta = await api.get("/api/ui-audit");
    return meta;
  }

  /* ---------- New observation ---------- */
  async function start(draft) {
    const shot = draft && draft.shot !== undefined ? draft.shot : await capture();
    let m;
    try { m = await loadMeta(); } catch (err) { toast(err.message, "error"); return; }
    openDialog(Object.assign({ tool: toolOfPage(), url: location.hash || "#/home", title: document.title,
      kind: "improvement", priority: "normal", description: "" }, draft || {}, { shot }), m);
  }

  function openDialog(state, m) {
    const preview = el("div", { class: "au-shot", tabindex: "0", "aria-label": "Capture : collez une image ici (Ctrl+V)" });
    function drawShot() {
      clear(preview);
      if (state.shot) preview.append(el("img", { src: state.shot.dataUrl, alt: "Capture de la page" }));
      else preview.append(el("p", { class: "muted" }, canCapture()
        ? "Aucune capture. Cliquez « Capturer la page », ou collez une image (Ctrl+V) / glissez un fichier ici."
        : "Collez ici une capture d'écran : Win+Maj+S (ou Impr. écran), puis cliquez ici et Ctrl+V. "
          + "Vous pouvez aussi glisser un fichier image."));
    }
    async function takeFile(file) {
      if (!file || !/^image\/(png|jpeg|gif|webp)$/.test(file.type)) { toast("Image PNG, JPEG, GIF ou WebP attendue.", "error"); return; }
      state.shot = await readFile(file);
      drawShot();
    }
    preview.addEventListener("paste", (ev) => {
      const file = Array.from((ev.clipboardData && ev.clipboardData.files) || [])[0];
      if (file) { ev.preventDefault(); takeFile(file); }
    });
    preview.addEventListener("dragover", (ev) => ev.preventDefault());
    preview.addEventListener("drop", (ev) => { ev.preventDefault(); takeFile((ev.dataTransfer.files || [])[0]); });
    drawShot();

    const kind = el("select", null, Object.entries(m.kinds).map(([k, v]) => el("option", { value: k, selected: k === state.kind }, v)));
    const priority = el("select", null, Object.entries(m.priorities).map(([k, v]) =>
      el("option", { value: k, selected: k === state.priority }, v)));
    const description = el("textarea", { rows: 5, maxlength: 4000, required: true,
      placeholder: "Ce qui ne va pas ou ce qu'il faudrait changer, et où (bouton, colonne, message…)." });
    description.value = state.description;
    const keep = () => Object.assign(state, { kind: kind.value, priority: priority.value, description: description.value });

    let close = null;
    async function submit(ev) {
      ev.preventDefault();
      keep();
      if (!state.description.trim()) { toast("Décrivez l'observation avant d'envoyer.", "error"); description.focus(); return; }
      try {
        const made = (await api.post("/api/ui-audit", { kind: state.kind, priority: state.priority, module: state.tool,
          page_url: state.url, page_title: state.title, description: state.description })).item;
        if (state.shot) {
          const blob = state.shot.blob;
          const file = blob instanceof File ? blob : new File([blob], "capture.png", { type: blob.type || "image/png" });
          await api.upload("/api/ui-audit/" + made.id + "/image", file);
        }
        close();
        meta = null;
        toast("Observation #" + made.id + " enregistrée. Merci !", "success");
        if (DA.audit.refreshCount) DA.audit.refreshCount();
        if (location.hash.startsWith("#/audit")) window.dispatchEvent(new HashChangeEvent("hashchange"));
      } catch (err) { toast(err.message, "error"); }
    }

    const body = el("form", { class: "form au-form", onsubmit: submit },
      el("p", { class: "muted au-where" }, "Outil : " + state.tool + " · Page : " + state.url),
      preview,
      el("div", { class: "au-shot-actions" },
        canCapture() ? el("button", { type: "button", class: "btn btn-small", onclick: () => { keep(); close(); start(Object.assign({}, state, { shot: undefined })); } },
          state.shot ? "Reprendre la capture" : "Capturer la page") : null,
        state.shot ? el("button", { type: "button", class: "btn btn-small", onclick: () => { state.shot = null; drawShot(); } }, "Retirer la capture") : null),
      el("div", { class: "au-row" }, field("Type", kind), field("Priority", priority)),
      field("Description (obligatoire)", description),
      el("div", { class: "form-actions" },
        el("a", { href: "#/audit", onclick: () => close() }, "Voir toutes les observations"),
        el("span", { class: "au-spacer" }),
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Envoyer")));
    close = modal("Audit de l'interface", body);
    const dialog = body.closest(".modal");
    if (dialog) dialog.classList.add("au-modal");
    description.focus();
  }

  function auditButton() {
    return el("button", { type: "button", class: "tb-audit", title: "Signaler une correction ou une amélioration de cet écran",
      onclick: (ev) => { ev.stopPropagation(); start(); } }, "Audit");
  }

  DA.audit = Object.assign(DA.audit || {}, { start });
  DA.topbarTools = DA.topbarTools || [];
  auditButton.order = 40;
  DA.topbarTools.push(auditButton);  // after « Liste Audit » (audit_list.js, loaded first)
})();
