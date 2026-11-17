/* Diamond · « ↔ IA » (0.60.111, D-O-124): the round trip of every Diamond page with an AI assistant, top right of the page.
   « Vers l'IA »            the page (or all of Diamond) as one JSON document inside a prompt -- Révision, Entrevue guidée or
                            Atelier (the blackboard of a session) -- copied, or as a .json file.
   « Importer la réponse »  the answer pasted or chosen: the server rehearses it against the Space and shows, section by section,
                            what comes in (Nouveau), what changes (field: before → after), what leaves (Retiré) and what the page
                            refuses (with its reason); the team unticks what it does not want, then « Appliquer la sélection »
                            -- a backup of the Space first, then every page of Diamond is up to date. */
(function () {
  "use strict";

  const { api, el, toast, modal } = DA;
  const D = DA.diamond = DA.diamond || {};
  const MODES = {
    review: ["Révision", "L'IA lit les artéfacts, corrige, complète et retire ce qui est en double ; elle rend le document en une fois."],
    interview: ["Entrevue guidée", "Une question à la fois dans l'ordre de la méthode ; le document quand vous écrivez « GÉNÈRE »."],
    workshop: ["Atelier (tableau blanc)", "L'équipe écrit ou dicte ses post-it ; l'IA dessine le tableau global en couleurs, propose des "
      + "groupes à « REGROUPE », et ne rend le document qu'à « GÉNÈRE »."]};
  let cache = null;  // {pid, sections}

  async function sections(ctx) {
    if (!cache || cache.pid !== ctx.pid) cache = { pid: ctx.pid, sections: (await api.get(D.base(ctx) + "/rt/sections")).sections };
    return cache.sections;
  }

  async function toClipboard(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (err) { return false; }
  }

  /* The scope: the sections of this page, ticked; the others below, unticked; « Tout Diamond » ticks them all. */
  function scopePicker(all, view) {
    const mine = all.filter((s) => s.pages.includes(view));
    const boxes = all.map((s) => {
      const box = el("input", { type: "checkbox", value: s.key, checked: mine.length ? mine.includes(s) : true });
      return [s, box, el("label", { class: "dm-rt-sec" }, box, el("span", null, s.label), el("span", { class: "muted" }, " · " + s.count))];
    });
    const setAll = (on) => boxes.forEach(([, b]) => { b.checked = on; });
    const page = () => boxes.forEach(([s, b]) => { b.checked = mine.includes(s); });
    const head = el("div", { class: "dm-rt-scope-head" },
      mine.length ? el("button", { type: "button", class: "btn btn-small", onclick: page }, "Cette page") : null,
      el("button", { type: "button", class: "btn btn-small", onclick: () => setAll(true) }, "Tout Diamond"),
      el("button", { type: "button", class: "btn btn-small", onclick: () => setAll(false) }, "Aucune"));
    return { node: el("fieldset", { class: "dm-rt-scope" }, el("legend", null, "Ce qui part vers l'IA"), head,
      el("div", { class: "dm-rt-secs" }, boxes.map(([, , l]) => l))),
      keys: () => boxes.filter(([, b]) => b.checked).map(([s]) => s.key) };
  }

  function outPane(ctx, all) {
    const scope = scopePicker(all, ctx.view);
    let mode = /^\d+$/.test(ctx.view === "ideation" ? ctx.arg || "" : "") ? "workshop" : "review";
    const radios = Object.keys(MODES).map((m) => {
      const r = el("input", { type: "radio", name: "dm-rt-mode", value: m, checked: m === mode });
      r.addEventListener("change", () => { mode = m; });
      return el("label", { class: "dm-ai-mode" }, r, el("span", null, el("strong", null, MODES[m][0]), el("span", { class: "muted" }, " — " + MODES[m][1])));
    });
    const sid = ctx.view === "ideation" && /^\d+$/.test(ctx.arg || "") ? ctx.arg : null;  // 0.60.112 (D-O-125): an Idéation board
    const board = sid ? el("input", { type: "checkbox", checked: true }) : null;
    const goal = el("input", { type: "text", maxlength: 300, placeholder: "Ex. : boucler l'arbre fonctionnel avant la revue de vendredi", "aria-label": "Objectif de la séance" });
    const out = el("div");
    const query = () => "sections=" + encodeURIComponent(scope.keys().join(",")) + (board && board.checked ? "&ideation=" + sid : "");
    const prompt = async () => {
      DA.clear(out);
      if (!scope.keys().length) { toast("Cochez au moins une section.", "error"); return; }
      let res;
      try { res = await api.get(D.base(ctx) + "/rt/prompt?" + query() + "&mode=" + mode + "&goal=" + encodeURIComponent(goal.value)); }
      catch (err) { toast(err.message, "error"); return; }
      const field = el("textarea", { rows: 10, readonly: true, class: "dm-story-ai-text", "aria-label": "Prompt" }, res.prompt);
      const copied = await toClipboard(res.prompt);
      const again = el("button", { type: "button", class: "btn btn-small", onclick: () => {
        field.select();
        toast(document.execCommand && document.execCommand("copy") ? "Prompt copié." : "Copiez le texte sélectionné (Ctrl + C).", "success");
      } }, "Copier");
      out.append(el("p", { class: copied ? "up-ok" : "muted" }, (copied ? "✓ Prompt copié" : "Copiez ce prompt") + " (" + res.prompt.length
        + " caractères) : collez-le dans Claude, Gemini ou un autre assistant. Sa réponse revient par « Importer la réponse »."), field, again);
      field.select();
    };
    return el("div", { class: "dm-rt-pane" }, scope.node,
      board ? el("label", { class: "check", "data-new": "0.60.112-rt-board" }, board, " Joindre les post-it de cette séance d'Idéation "
        + "(par groupe, avec leurs étoiles) comme matière première") : null,
      el("fieldset", null, el("legend", null, "Mode"), radios),
      DA.field("Objectif de la séance (facultatif)", goal),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn btn-primary", onclick: prompt }, "Préparer et copier le prompt"),
        el("button", { type: "button", class: "btn", onclick: () => {
          if (!scope.keys().length) { toast("Cochez au moins une section.", "error"); return; }
          window.location.href = D.base(ctx) + "/rt/export.json?" + query();
        } }, "Télécharger le .json")),
      el("p", { class: "muted" }, "Rien ne quitte la plateforme par elle-même : vous copiez, vous collez. Le document porte les codes "
        + "(F12, CB-4, D-37…) qui ramènent chaque changement au bon artéfact."), out);
  }

  function entryRow(e, boxes) {
    const tick = ["new", "update", "remove"].includes(e.kind);
    const box = tick ? el("input", { type: "checkbox", checked: e.default, "aria-label": "Appliquer " + (e.code || e.label) }) : null;
    if (box) boxes.push([e, box]);
    return el("tr", { class: "dm-ai-" + e.kind }, el("td", null, box), el("td", { class: "dm-code nowrap" }, e.code || "—"),
      el("td", null, el("span", { class: "dm-ai-kind" }, e.kind_label)), el("td", null, e.label),
      el("td", null, e.reason ? el("span", { class: e.kind === "refused" ? "dm-ch-miss" : "muted" }, e.reason)
        : el("ul", { class: "dm-ai-changes" }, e.changes.map(([f, a, b]) => el("li", null, el("strong", null, f), " : ",
          a ? el("del", null, a) : null, a ? " → " : null, b || "—")))));
  }

  function preview(res, boxes) {
    const c = res.counts;
    const bySection = {};
    res.entries.forEach((e) => { (bySection[e.section] = bySection[e.section] || []).push(e); });
    const blocks = Object.keys(bySection).map((key) => {
      const list = bySection[key];
      const moving = list.filter((e) => e.kind !== "same");
      const n = (k) => list.filter((e) => e.kind === k).length;
      const head = el("summary", null, el("strong", null, res.labels[key] || key), " — ",
        [n("new") + " nouveau(x)", n("update") + " modifié(s)", n("remove") + " retiré(s)", n("refused") + " refusé(s)", n("same") + " identique(s)"].join(" · "));
      const rows = (moving.length ? moving : []).map((e) => entryRow(e, boxes));
      return el("details", { class: "dm-rt-block", open: moving.length > 0 }, head,
        rows.length ? el("div", { class: "dm-scroll" }, DA.table(["", "Code", "Résultat", "Élément", "Changements ou raison"], rows))
          : el("p", { class: "muted" }, "Rien ne change dans cette section."));
    });
    return el("div", { class: "dm-import-preview" },
      el("p", null, el("strong", null, "Aperçu : "), [c.new + " nouveau(x)", c.update + " modifié(s)", c.remove + " retiré(s)", c.refused + " refusé(s)",
        c.same + " identique(s)"].join(" · ")),
      res.warnings.map((w) => el("p", { class: "dm-ai-note", role: "status" }, w)), blocks,
      el("p", { class: "muted" }, "Chaque ligne a été essayée à blanc par la page elle-même : une ligne refusée l'est pour la raison donnée. "
        + "Décochez ce que vous ne voulez pas ; une sauvegarde du Space est prise avant d'appliquer."));
  }

  function inPane(ctx, close) {
    const text = el("textarea", { rows: 7, class: "dm-story-ai-text", "aria-label": "Réponse de l'IA",
      placeholder: "Collez ici la réponse de l'assistant IA (son bloc ```json) ou choisissez le .json." });
    const file = el("input", { type: "file", accept: ".json,.txt,application/json,text/plain", "aria-label": "Fichier .json" });
    const result = el("div");
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true }, "Appliquer la sélection");
    let boxes = [], run = 0;
    const skip = () => boxes.filter(([, b]) => !b.checked).map(([e]) => e.id);
    async function check() {
      const mine = ++run;
      DA.clear(result);
      boxes = [];
      apply.disabled = true;
      if (!text.value.trim()) return;
      result.append(el("p", { class: "muted" }, "Vérification contre le Space…"));
      try {
        const res = await api.post(D.base(ctx) + "/rt/import", { file: text.value, mode: "preview" });
        if (mine !== run) return;
        DA.clear(result);
        result.append(preview(res, boxes));
        apply.disabled = !boxes.length;
      } catch (err) { if (mine === run) { DA.clear(result); result.append(el("p", { class: "form-error", role: "alert" }, err.message)); } }
    }
    file.addEventListener("change", async () => { if (file.files[0]) { text.value = await file.files[0].text(); check(); } });
    text.addEventListener("change", check);
    apply.addEventListener("click", async () => {
      const n = boxes.filter(([, b]) => b.checked).length;
      const out = boxes.filter(([e, b]) => b.checked && e.kind === "remove").length;
      if (out && !window.confirm(n + " changement(s) dont " + out + " retrait(s) seront appliqués. Une sauvegarde du Space est prise avant. Continuer ?")) return;
      apply.disabled = true;
      try {
        const confirm = boxes.filter(([e, b]) => b.checked && e.kind === "remove" && !e.default).map(([e]) => e.id);  // ticked by hand
        const res = await api.post(D.base(ctx) + "/rt/import", { file: text.value, mode: "apply", skip: skip(), confirm });
        const a = res.applied;
        toast(a.new + " ajout(s), " + a.update + " modification(s), " + a.remove + " retrait(s). Sauvegarde : " + res.backup, "success");
        cache = null;
        close();
        window.dispatchEvent(new HashChangeEvent("hashchange"));  // every page of Diamond reads the Space again
      } catch (err) { apply.disabled = false; toast(err.message, "error"); }
    });
    return el("div", { class: "dm-rt-pane" },
      el("p", { class: "muted" }, "La réponse de l'IA : un objet JSON {section: [éléments]}, chaque section rendue complète. Un code "
        + "connu modifie son élément, un élément sans code (ou « +… ») est créé, un élément absent d'une section rendue est retiré."),
      DA.field("Fichier", file), DA.field("Ou le texte", text),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Vérifier"), apply), result);
  }

  async function open(ctx, tab) {
    let all;
    try { all = await sections(ctx); } catch (err) { toast(err.message, "error"); return; }
    const editable = DA.agile.canEdit(ctx);
    const body = el("div");
    const tabs = el("div", { class: "dm-rt-tabs", role: "tablist" });
    let close = () => {};
    const show = (which) => {
      DA.clear(body);
      tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === which)));
      body.append(which === "in" ? inPane(ctx, () => close()) : outPane(ctx, all));
    };
    tabs.append(el("button", { type: "button", role: "tab", "data-tab": "out", class: "btn btn-small", onclick: () => show("out") }, "1 · Vers l'IA"),
      editable ? el("button", { type: "button", role: "tab", "data-tab": "in", class: "btn btn-small", onclick: () => show("in") }, "2 · Importer la réponse") : null);
    close = modal("↔ IA · aller-retour de Diamond", el("div", { class: "form dm-ai-dialog dm-rt", "data-new": "0.60.111-rt" }, tabs, body));
    const m = body.closest(".modal");
    if (m) m.classList.add("dm-cls-modal");
    show(tab === "in" && editable ? "in" : "out");
  }

  /** The button of every Diamond page head (SHELL.headTools). */
  D.rtButton = function (ctx) {
    return el("button", { type: "button", class: "btn btn-small dm-rt-btn", "data-new": "0.60.111-rt", title: "Aller-retour avec un assistant IA : "
      + "exporter cette page ou tout Diamond, importer la réponse, tout reste synchronisé", onclick: () => open(ctx) }, "↔ IA");
  };
})();
