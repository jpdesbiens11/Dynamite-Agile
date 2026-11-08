/* Evidence of a test plan (0.60.90, D-O-096; any file, versions and network links: 0.60.94, D-O-100).
   Shown on the plan page once the plan is sent. Any file the supplier sends is dropped here (button or drag and drop),
   up to the platform's cap (150 Mo); a larger one stays on the network and the plan records where it lies. A newer
   version replaces a file under the same evidence, so the results that cite it follow; earlier versions stay listed. */
(function () {
  "use strict";
  const { api, el, toast, modal, field } = DA;
  const T = (DA.testing = DA.testing || {});
  const NEW = "0.60.94-evidence-files";
  const MB = 1048576;
  const size = (n) => (n == null ? "—" : n >= MB ? (n / MB).toFixed(1).replace(/\.0$/, "").replace(".", ",") + " Mo" : Math.max(1, Math.round(n / 1024)) + " Ko");
  const day = (iso) => (iso || "").slice(0, 10);

  /* p: the plan with its evidence and bundles; url(rest): the plan's API address for rest; live: the campaign runs */
  T.evidenceBlock = function (p, url, live, reload) {
    const max = (p.evidence_max_mb || 150) * MB;
    const status = el("p", { class: "muted te-status", role: "status", "aria-live": "polite" });
    const busy = (text) => { status.textContent = text || ""; buttons.forEach((b) => { b.disabled = !!text; }); };

    async function send(files, replaceOf) {
      const small = files.filter((f) => f.size <= max), big = files.filter((f) => f.size > max);
      let done = 0;
      try {
        for (const [i, f] of small.entries()) {
          busy("Envoi " + (i + 1) + " / " + small.length + " : " + f.name + " (" + size(f.size) + ")…");
          await api.upload(url(replaceOf ? "/evidence/" + replaceOf.id + "/replace" : "/evidence"), f);
          done += 1;
        }
      } catch (err) {
        toast(err.message, "error");
      } finally {
        busy("");
      }
      if (done) toast(replaceOf ? "Nouvelle version de « " + replaceOf.name + " » déposée." : done + " fichier(s) déposé(s).", "success");
      if (big.length) linkForm(big, replaceOf, done > 0); else if (done) reload();
    }

    /* Files over the cap (or none: a reference typed by hand) stay on the network: ask where each one lies. */
    function linkForm(big, replaceOf, reloadAfter) {
      const rows = (big.length ? big : [null]).map((f) => ({
        file: f,
        name: el("input", { type: "text", maxlength: 120, required: true, value: f ? f.name : replaceOf ? replaceOf.name : "", "aria-label": "Nom du fichier" }),
        link: el("input", { type: "text", maxlength: 1000, required: true, placeholder: "\\\\serveur\\partage\\Essais\\" + p.code + "\\" + (f ? f.name : "rapport.zip"), "aria-label": "Emplacement réseau" + (f ? " de " + f.name : "") }),
      }));
      const note = el("input", { type: "text", maxlength: 500, placeholder: "Facultatif : ce que contient le fichier" });
      const error = el("p", { class: "form-error", role: "alert" });
      let close = null;
      const finish = () => { close(); reload(); };
      const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
        ev.preventDefault();
        error.textContent = "";
        try {
          for (const r of rows) {
            const body = { name: r.name.value, link: r.link.value, size: r.file ? r.file.size : null };
            if (replaceOf) await api.post(url("/evidence/" + replaceOf.id + "/link"), body);
            else await api.post(url("/evidence/link"), Object.assign(body, { note: note.value }));
          }
          toast(rows.length > 1 ? rows.length + " liens réseau enregistrés." : "Lien réseau enregistré.", "success");
          finish();
        } catch (err) { error.textContent = err.message; }
      } },
      el("p", null, big.length
        ? (big.length > 1 ? big.length + " fichiers dépassent" : "Ce fichier dépasse") + " " + size(max) + " : il reste sur le réseau de l'équipe. "
          + "Indiquez où il est rangé (dossier partagé, chemin complet), et le plan le citera comme document de résultat."
        : "Un document trop lourd pour la plateforme reste sur le réseau : indiquez son nom et où il est rangé ; le plan le citera comme document de résultat."),
      rows.map((r) => el("fieldset", { class: "te-linkset" },
        r.file ? el("legend", null, r.file.name + " · " + size(r.file.size)) : null,
        field("Nom du fichier", r.name),
        field("Emplacement réseau (open local folder)", r.link, "Tel que l'équipe l'ouvre dans l'Explorateur ou le Finder, ex. \\\\serveur\\partage\\… ou S:\\Essais\\…"))),
      !replaceOf ? field("Note", note) : null, error,
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => (reloadAfter ? finish() : close()) }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, rows.length > 1 ? "Enregistrer les liens" : "Enregistrer le lien")));
      close = modal(replaceOf ? "Nouvelle version sur le réseau" : "Fichier sur le réseau", form);
    }

    const picker = el("input", { type: "file", multiple: true, hidden: true });
    picker.addEventListener("change", () => { const files = [...picker.files]; picker.value = ""; if (files.length) send(files, null); });
    let replaceOf = null;
    const replacer = el("input", { type: "file", hidden: true });
    replacer.addEventListener("change", () => { const f = replacer.files[0]; replacer.value = ""; if (f && replaceOf) send([f], replaceOf); });
    const buttons = live ? [
      el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => picker.click() }, "Déposer des fichiers…"),
      el("button", { type: "button", class: "btn btn-small", "data-new": NEW, onclick: () => linkForm([], null, false) }, "+ Lien réseau…"),
    ] : [];

    const cited = (e) => p.bundles.flatMap((b) => Object.entries(b.results).filter(([, r]) => (r.evidence || []).includes(e.id)).map(([t]) => b.proto + " · " + t));
    const remove = async (e) => {
      const uses = cited(e);
      if (!confirm("Retirer « " + e.name + " » du plan ?" + (uses.length ? "\n\nElle sera aussi retirée des résultats qui la citent : " + uses.join(", ") + "." : ""))) return;
      try { await api.del(url("/evidence/" + e.id)); toast("« " + e.name + " » retirée.", "success"); reload(); } catch (err) { toast(err.message, "error"); }
    };
    const copy = async (text) => {
      try { await navigator.clipboard.writeText(text); toast("Chemin copié : collez-le dans l'Explorateur (ou le Finder).", "success"); }
      catch (err) { toast("Copie impossible : sélectionnez le chemin et copiez-le à la main.", "error"); }
    };
    const where = (h, id) => (h.kind === "link"
      ? el("span", { class: "te-path" }, el("code", null, h.link), " ", el("button", { type: "button", class: "btn btn-small", onclick: () => copy(h.link) }, "Copier le chemin"))
      : el("a", { href: url("/evidence/" + id + "/file" + (h.version ? "?version=" + h.version : "")), download: h.name }, h.name));
    const bundleSelect = (e) => {
      const sel = el("select", { "aria-label": "Bundle de " + e.name, disabled: !live, onchange: async () => {
        try { await api.patch(url("/evidence/" + e.id), { bundle_id: sel.value ? Number(sel.value) : null }); reload(); } catch (err) { toast(err.message, "error"); }
      } }, el("option", { value: "" }, "En vrac"), p.bundles.map((b) => el("option", { value: b.id, selected: b.id === e.bundle_id }, b.proto)));
      return sel;
    };
    const row = (e) => el("tr", null,
      el("td", null, e.kind === "link" ? el("div", null, el("b", null, e.name), el("span", { class: "badge badge-info te-net" }, "Réseau"), el("div", null, where(e, e.id)))
        : where({ kind: "file", name: e.name }, e.id), e.note ? el("div", { class: "muted te-note" }, e.note) : null),
      el("td", { class: "te-ver" }, "v" + e.version, e.history.length ? el("details", { "data-new": NEW }, el("summary", null, e.history.length + " précédente(s)"),
        el("ul", { class: "te-history" }, e.history.map((h) => el("li", null, "v" + h.version + " · ", where(h, e.id), " · " + size(h.size) + " · " + day(h.at) + (h.by ? " · " + h.by : ""))))) : null),
      el("td", { class: "te-ver" }, size(e.size)),
      el("td", null, e.by || "", e.at ? el("div", { class: "muted te-note" }, day(e.at)) : null),
      el("td", null, bundleSelect(e)),
      el("td", null, live ? el("div", { class: "tg-actions" },
        el("button", { type: "button", class: "btn btn-small", "data-new": NEW, onclick: () => { replaceOf = e; replacer.click(); } }, "Remplacer…"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => remove(e) }, "Retirer")) : null));

    const section = el("section", { class: "te-drop", "data-new": "0.60.90-plan-evidence" },
      el("h2", null, "Preuves (" + p.evidence.length + ")"),
      el("p", { class: "muted" }, "Déposez tout ce que le fournisseur envoie, de tout type : rapport du plan rempli, rapports de laboratoire, données brutes, "
        + "Excel, photos, vidéos, archives. " + size(max) + " au plus par fichier ; au-delà, le fichier reste sur le réseau et le plan garde son emplacement. "
        + "Une version plus récente remplace la précédente (« Remplacer… ») sans défaire les résultats qui la citent."),
      live ? el("div", { class: "form-actions tt-left" }, buttons, picker, replacer) : null, status,
      p.evidence.length ? DA.table(["Fichier", "Version", "Taille", "Déposé par", "Bundle", ""], p.evidence.map(row))
        : el("p", { class: "muted" }, live ? "Aucune preuve pour le moment : glissez des fichiers ici, ou « Déposer des fichiers… »." : "Aucune preuve."));
    if (live) {
      section.addEventListener("dragover", (ev) => { ev.preventDefault(); section.classList.add("te-over"); });
      section.addEventListener("dragleave", (ev) => { if (!section.contains(ev.relatedTarget)) section.classList.remove("te-over"); });
      section.addEventListener("drop", (ev) => {
        ev.preventDefault(); section.classList.remove("te-over");
        const files = [...(ev.dataTransfer ? ev.dataTransfer.files : [])];
        if (files.length) send(files, null);
      });
    }
    return section;
  };
})();
