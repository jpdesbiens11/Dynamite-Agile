/* Admin → Update: step-by-step review (core lot v0.26, D-B-094), shared by the three parts.
   DA.updateReview.show(box, opts) draws the steps of a review (Framework changes, Données accounts / Spaces,
   Site complet content / code / Spaces / accounts). Each step is opened (its files and differences, or what it
   imports), then approved or refused with a reason. A refusal closes the review and shows the « Retour pour
   Claude » text. Every step approved -> « Appliquer ».
   opts: { base: "/api/.../review/<token>", summary, apply: async () => result, onApplied(result), applyLabel } */
(function () {
  "use strict";
  const { api, el, clear, toast } = DA;
  const STATUS = { pending: ["À revoir", "neutral"], approved: ["Approuvé", "ok"], refused: ["Refusé", "danger"] };
  const STATE = { added: "ajouté", changed: "modifié", removed: "retiré" };

  function diffBlock(f) {
    if (f.binary) return el("p", { class: "muted" }, f.binary);
    const pre = el("pre", { class: "up-diff" }, f.diff.map((line) => el("span", {
      class: line.startsWith("@@") ? "up-hunk" : line.startsWith("+") && !line.startsWith("+++") ? "up-add"
        : line.startsWith("-") && !line.startsWith("---") ? "up-del" : "" }, line || " ")));
    return el("div", null, pre, f.truncated ? el("p", { class: "muted" }, "… " + f.truncated + " ligne(s) de différence de plus, non affichées.") : null);
  }

  function filesBlock(files) {
    if (!files || !files.length) return null;
    return el("div", { class: "up-files" }, files.map((f, i) => el("details", { open: files.length <= 3 || i === 0 },
      el("summary", null, el("code", null, f.path), " ", DA.badge(STATE[f.state] || f.state, f.state === "removed" ? "danger" : f.state === "added" ? "info" : "neutral"),
        f.plus !== undefined ? el("span", { class: "muted" }, "  +" + f.plus + " / −" + f.minus) : null),
      diffBlock(f))));
  }

  function countsTable(counts, labels) {
    const rows = Object.entries(counts || {});
    if (!rows.length) return el("p", { class: "muted" }, "Aucune ligne : le Space est vide.");
    return DA.table(["Type", "Lignes"], rows.map(([k, n]) => el("tr", null, el("td", null, (labels || {})[k] || k), el("td", null, String(n)))));
  }

  function spaceOptions(step, labels, fixedTypes) {
    const o = step.options || { action: "skip", key: "", types: [] };
    const name = "up-act-" + step.n;
    const skip = el("input", { type: "radio", name, value: "skip", checked: o.action === "skip" });
    const neu = el("input", { type: "radio", name, value: "new", checked: o.action === "new" });
    const key = el("input", { type: "text", maxlength: 10, value: o.key || "", "aria-label": "Clé du nouveau Space", class: "up-key" });
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    const boxes = Object.keys(step.counts || {}).filter((k) => k !== "core").map((k) => {
      const fixed = (fixedTypes || []).includes(k);  // site-only types: shown, never ticked
      const box = el("input", { type: "checkbox", value: k, checked: !fixed && (o.types || []).includes(k), disabled: fixed });
      return el("label", { class: "up-type" }, box, " " + ((labels || {})[k] || k) + " (" + step.counts[k] + ")");
    });
    const typesBox = el("fieldset", { class: "up-types" }, el("legend", null, "Types à importer (le noyau suit toujours)"), boxes);
    const sync = () => { const on = neu.checked; key.disabled = !on; typesBox.disabled = !on; };
    [skip, neu].forEach((r) => r.addEventListener("change", sync));
    sync();
    const form = el("div", { class: "up-options" },
      el("label", { class: "up-choice" }, skip, step.exists ? " Sauter ce Space (il existe déjà ici et ne sera jamais écrasé)" : " Sauter ce Space"),
      el("label", { class: "up-choice" }, neu, " Importer comme nouveau Space, clé ", key), typesBox);
    form.read = () => ({ action: neu.checked ? "new" : "skip", key: key.value.trim(),
      types: boxes.map((b) => b.querySelector("input")).filter((b) => b.checked && !b.disabled).map((b) => b.value) });
    return form;
  }

  function stepDetail(d) {
    const s = d.step;
    const parts = [el("p", null, s.why || "")];
    if (s.unknown && s.unknown.length) parts.push(el("p", { class: "form-error" }, "Fichiers annoncés mais absents du zip ou inchangés : " + s.unknown.join(", ")));
    if (s.kind === "accounts") {
      if ((s.new || []).length) parts.push(el("details", { open: true }, el("summary", null, "Comptes (" + s.new.length + ")"), el("p", null, s.new.join(", "))));
      if ((s.same || []).length) parts.push(el("details", null, el("summary", null, "Déjà présents, inchangés (" + s.same.length + ")"), el("p", null, s.same.join(", "))));
    }
    if (s.kind === "space") parts.push(countsTable(s.counts, d.types));
    parts.push(filesBlock(d.files));
    if (s.kind === "code" && !(d.files || []).length) parts.push(el("p", { class: "up-ok" }, "Aucune différence de code."));
    return parts;
  }

  DA.updateReview = {
    show(box, opts) {
      let summary = opts.summary;
      let current = (summary.steps.find((x) => x.status !== "approved") || summary.steps[0] || {}).n || 1;
      const nav = el("ol", { class: "up-review-nav", "aria-label": "Étapes de la revue" });
      const panel = el("section", { class: "up-review-step", "aria-live": "polite" });
      const footer = el("div", { class: "up-review-foot" });
      clear(box);
      box.append(el("div", { class: "up-review" }, nav, panel, footer));

      function drawNav() {
        clear(nav);
        summary.steps.forEach((x) => nav.append(el("li", null, el("button", {
          type: "button", class: "up-nav-btn" + (x.n === current ? " active" : ""), "aria-current": x.n === current ? "step" : null,
          onclick: () => { current = x.n; drawStep(); } },
          el("span", { class: "up-nav-n" }, String(x.n)), " " + x.title + " ", DA.badge(STATUS[x.status][0], STATUS[x.status][1])))));
      }

      function drawFoot() {
        clear(footer);
        footer.append(el("p", null, el("strong", null, summary.approved + " / " + summary.total + " étape(s) approuvée(s).")));
        if (summary.refused) {
          const text = el("pre", { class: "up-feedback" }, summary.feedback);
          footer.append(el("div", { class: "form-error" }, el("strong", null, "Revue refusée : rien n'a été appliqué. "),
            "Donnez ce retour à Claude avec le zip exporté, puis vérifiez le nouveau zip qu'il rendra."), text,
          el("button", { type: "button", class: "btn", onclick: async () => {
            try { await navigator.clipboard.writeText(summary.feedback); toast("Retour copié.", "success"); }
            catch (err) { toast("Copie impossible : sélectionnez le texte et faites Ctrl+C.", "error"); }
          } }, "Copier le retour pour Claude"));
          return;
        }
        if (summary.ready) {
          footer.append(el("button", { type: "button", class: "btn btn-primary", onclick: async (ev) => {
            if (!confirm(opts.confirm || "Appliquer maintenant ? Une sauvegarde est faite avant.")) return;
            ev.target.disabled = true;
            try { opts.onApplied(await opts.apply()); }
            catch (err) { toast(err.message, "error"); ev.target.disabled = false; }
          } }, opts.applyLabel || "Appliquer"));
        } else {
          footer.append(el("p", { class: "muted" }, "« Appliquer » apparaît quand chaque étape est approuvée."));
        }
      }

      async function decide(decision, body) {
        try {
          summary = await api.post(opts.base + "/" + current, Object.assign({ decision }, body || {}));
          const next = summary.steps.find((x) => x.status === "pending");
          if (decision === "approve" && next) current = next.n;
          drawStep();
        } catch (err) { toast(err.message, "error"); }
      }

      async function drawStep() {
        drawNav(); drawFoot();
        clear(panel);
        panel.append(el("p", { class: "muted" }, "Chargement de l'étape " + current + "…"));
        let d;
        try { d = await api.get(opts.base + "/" + current); } catch (err) { clear(panel); panel.append(el("p", { class: "form-error" }, err.message)); return; }
        const s = d.step;
        const options = s.kind === "space" && s.options ? spaceOptions(s, d.types, d.fixed) : null;
        const reason = el("textarea", { rows: 3, placeholder: "Ce qui ne va pas (ce texte part dans le retour pour Claude)", "aria-label": "Raison du refus" });
        const refuseBox = el("div", { class: "up-refuse", hidden: true }, reason,
          el("button", { type: "button", class: "btn btn-danger", onclick: () => decide("refuse", { comment: reason.value }) }, "Confirmer le refus"));
        const closed = summary.closed;
        clear(panel);
        panel.append(el("div", null, el("h3", null, "Étape " + s.n + " / " + d.total + " — " + s.title, " ", DA.badge(STATUS[s.status][0], STATUS[s.status][1])),
          stepDetail(d), options,
          s.status !== "pending" && s.by ? el("p", { class: "muted" }, (s.status === "approved" ? "Approuvé" : "Refusé") + " par " + s.by + " le "
            + (s.at || "").replace("T", " ").slice(0, 16) + (s.comment ? " : « " + s.comment + " »" : "")) : null,
          closed ? null : el("div", { class: "form-actions" },
            el("button", { type: "button", class: "btn btn-primary", onclick: () => decide("approve", options ? { options: options.read() } : null) },
              s.status === "approved" ? "Approuver de nouveau" : "Approuver cette étape"),
            el("button", { type: "button", class: "btn", onclick: () => { refuseBox.hidden = false; reason.focus(); } }, "Refuser…")),
          refuseBox));  // el() skips null parts (native append would print « null »)
      }

      drawStep();
    },
  };
})();
