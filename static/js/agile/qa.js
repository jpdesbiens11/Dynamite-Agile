/* Goldmine - « Q&A » (D-B-037): the register of questions
   with the client, one card per question, answered in place.
   Keyboard: J / K next / previous card, R reply, Ctrl+Entrée send.
   Dialogs (new question, client file import) live in qa_io.js. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const DONE = ["closed", "cancelled"];
  const isDone = (q) => DONE.includes(q.status);
  const A = DA.agile;
  const base = (ctx) => "/api/agile/p/" + ctx.pid;

  const FILTERS = [
    ["open", "Not Closed", (q) => !isDone(q)],
    ["team", "À traiter par l'équipe", (q) => q.waiting_on === "team"],
    ["client", "En attente du client", (q) => q.waiting_on === "client"],
    ["mine", "À moi", (q, me) => q.waiting_on === "team" && (q.owner_id || q.req_assignee) === me],
    ["blocking", "Blocking", (q) => q.blocking && !isDone(q)],
    ["closed", "Closed", (q) => q.status === "closed"],
    ["cancelled", "Cancelled", (q) => q.status === "cancelled"],
    ["all", "Toutes", () => true],
  ];
  const COUNT_KEY = { open: null, team: "team", client: "client", mine: "mine", blocking: "blocking", closed: "closed", cancelled: "cancelled", all: "all" };

  /* ---------- One card ---------- */
  function card(ctx, q, data, onChange) {
    const editable = data.can_edit;
    const node = el("article", { class: "qa-card qa-" + q.direction + " qa-st-" + q.status + (q.blocking ? " qa-blocking" : ""),
      tabindex: "0", "data-id": q.id });
    const waiting = q.waiting_on === "client" ? el("span", { class: "qa-wait qa-wait-client" }, "Attente client")
      : q.waiting_on === "team" ? el("span", { class: "qa-wait qa-wait-team" }, "À traiter (équipe)") : null;
    const owner = editable && !isDone(q)
      ? el("select", { class: "qa-owner", "aria-label": "Assignee (équipe)" },
        A.options(data.members.map((m) => [m.id, m.display_name]), q.owner_id || "", "— Assignee —"))
      : el("span", { class: "muted" }, q.owner_name ? "Resp. " + q.owner_name : "");
    if (owner.tagName === "SELECT") owner.addEventListener("change", () => patch({ owner_id: owner.value || null }));
    const late = q.due_date && !isDone(q) && q.due_date < new Date().toISOString().slice(0, 10);
    node.append(el("header", { class: "qa-head" },
      el("span", { class: "qa-ref" }, q.ref),
      el("a", { class: "ag-key", href: "#/goldmine/" + ctx.key + "/issue/" + q.number }, q.req_key),
      el("span", { class: "qa-req", title: q.req_statement || q.req_title }, q.req_title),
      el("span", { class: "qa-spacer" }),
      q.blocking ? el("span", { class: "qa-flag" }, "Blocking") : null,
      q.due_date ? el("span", { class: late ? "qa-due qa-late" : "qa-due" }, "Due Date " + q.due_date) : null,
      waiting, el("span", { class: "badge badge-" + ({ closed: "ok", answered: "warn", cancelled: "off" }[q.status] || "neutral") }, q.status_label),
      owner));
    node.append(el("div", { class: "qa-msg qa-q" },
      el("div", { class: "qa-who" }, el("strong", null, q.ask_label), " ", el("span", { class: "qa-stamp" }, q.asked_stamp),
        q.asked_who ? el("span", { class: "muted" }, " · " + q.asked_who) : null,
        q.req_revision ? el("span", { class: "muted" }, " · requirement rév. " + q.req_revision) : null),
      el("p", { class: "qa-text" }, q.question)));
    if (q.answer) {
      node.append(el("div", { class: "qa-msg qa-a" },
        el("div", { class: "qa-who" }, el("strong", null, q.answer_label), " ", el("span", { class: "qa-stamp" }, q.answered_stamp),
          q.answered_who ? el("span", { class: "muted" }, " · " + q.answered_who) : null),
        el("p", { class: "qa-text" }, q.answer)));
    }
    if (isDone(q)) node.append(el("p", { class: "qa-closed muted" }, q.status_label + " " + q.closed_stamp));

    const actions = el("div", { class: "qa-actions" });
    node.append(actions);
    if (editable) {
      const needsAnswer = q.status === "open";
      const box = el("textarea", { class: "qa-reply", rows: needsAnswer ? 2 : 1, maxlength: 4000,
        placeholder: q.direction === "team" ? "Réponse du client (reçue par courriel ou en réunion)…" : "Réponse de l'équipe au client…",
        "aria-label": "Réponse à " + q.ref });
      const clientName = q.direction === "team" ? el("input", { type: "text", class: "qa-client", maxlength: 80,
        placeholder: "Client (nom ou initiales)", "aria-label": "Nom du client" }) : null;
      const send = el("button", { type: "button", class: "btn btn-primary btn-small", onclick: () => submit() },
        q.answer ? "Remplacer la réponse" : "Enregistrer la réponse");
      const replyRow = el("div", { class: "qa-reply-row" }, box, clientName, send);
      box.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); submit(); } });
      if (!isDone(q)) {
        if (!needsAnswer) replyRow.hidden = true;
        actions.append(replyRow);
      }
      /* D-B-044: from any state, the useful next moves -- close, undo a reopening, reopen, cancel. */
      const btn = (label, fn, cls) => el("button", { type: "button", class: "btn btn-small" + (cls ? " " + cls : ""), onclick: fn }, label);
      const buttons = el("div", { class: "qa-buttons" });
      if (!isDone(q)) {
        buttons.append(btn(q.status === "answered" ? (q.direction === "team" ? "✓ Clore (réponse satisfaisante)" : "✓ Clore (le client accepte)")
          : "✓ Clore", () => action("close"), "qa-close"));
      }
      if (q.status === "open" && q.answer) buttons.append(btn("↶ Annuler la réouverture", () => action("revert")));
      if (q.status === "answered") {
        buttons.append(btn("↺ Rouvrir…", () => reopen()),
          el("button", { type: "button", class: "link-btn", onclick: () => { replyRow.hidden = false; box.focus(); } }, "Remplacer la réponse"));
      }
      if (isDone(q)) buttons.append(btn("↺ Rouvrir…", () => reopen()));
      if (!isDone(q)) {
        buttons.append(btn("✕ Annuler la question…", () => cancel(), "btn-danger"),
          el("label", { class: "check qa-block-toggle" },
            el("input", { type: "checkbox", checked: !!q.blocking, onchange: (ev) => patch({ blocking: ev.target.checked }) }), "Blocking"));
      }
      actions.append(buttons);
      node.qaReply = () => { replyRow.hidden = false; box.focus(); };

      async function submit() {
        if (!box.value.trim()) { toast("Écrivez la réponse.", "error"); box.focus(); return; }
        send.disabled = true;
        try {
          await api.post(base(ctx) + "/qa/" + q.id + "/answer", { answer: box.value, external_name: clientName ? clientName.value : "" });
          toast(q.ref + " : réponse enregistrée.", "success");
          onChange(q.id);
        } catch (err) { toast(err.message, "error"); send.disabled = false; }
      }
    }
    if (q.events && q.events.length > 1) {
      const kinds = { question: "Question", answer: "Réponse", close: "Fermeture", reopen: "Réouverture", cancel: "Annulation",
        revert: "Réouverture annulée", comment: "Commentaire" };
      node.append(el("details", { class: "qa-history" }, el("summary", null, "Historique (" + q.events.length + ")"),
        el("ol", null, q.events.map((e) => el("li", null, el("span", { class: "qa-stamp" }, e.stamp), " ",
          el("strong", null, kinds[e.kind] || e.kind), (e.name || e.user_name) ? " · " + (e.name || e.user_name) : "",
          e.text ? el("div", { class: "qa-text" }, e.text) : null)))));
    }

    async function patch(body) {
      try { await api.patch(base(ctx) + "/qa/" + q.id, body); onChange(q.id, true); } catch (err) { toast(err.message, "error"); }
    }
    async function action(kind, note) {
      const done = { close: " close.", reopen: " rouverte.", cancel: " annulée.", revert: " : retour à « Répondue »." }[kind];
      try { await api.post(base(ctx) + "/qa/" + q.id + "/" + kind, { note: note || "" }); toast(q.ref + done, "success"); onChange(q.id); }
      catch (err) { toast(err.message, "error"); }
    }
    function reopen() { A.qaReopenDialog(q, (note) => action("reopen", note)); }
    function cancel() { A.qaReopenDialog(q, (note) => action("cancel", note), true); }
    return node;
  }

  /* Move between cards with J / K, reply with R. */
  function keyboard(list) {
    list.addEventListener("keydown", (ev) => {
      if (ev.target.closest("textarea, input, select") || ev.ctrlKey || ev.metaKey || ev.altKey) return;
      const cards = Array.from(list.querySelectorAll(".qa-card"));
      const current = ev.target.closest(".qa-card");
      const i = cards.indexOf(current);
      if (ev.key === "j" || ev.key === "k") {
        ev.preventDefault();
        const next = cards[Math.max(0, Math.min(cards.length - 1, i + (ev.key === "j" ? 1 : -1)))];
        if (next) { next.focus(); next.scrollIntoView({ block: "nearest" }); }
      } else if (ev.key === "r" && current && current.qaReply) {
        ev.preventDefault();
        current.qaReply();
      }
    });
  }

  /* ---------- The register screen ---------- */
  async function qaView(page, ctx) {
    let data = await api.get(base(ctx) + "/qa");
    const focusId = Number(ctx.arg) || null;
    let filter = focusId ? "all" : (DA.myItems && DA.myItems() ? "mine" : (data.counts.team ? "team" : "open"));  // D-B-038
    page.append(A.pageHead(ctx, [el("span", null, "Q&A")],
      data.can_edit ? el("button", { type: "button", class: "btn btn-primary", onclick: () => A.qaNewDialog(ctx, null, reload) }, "+ Question") : null));
    page.append(el("div", { class: "qa-io" },
      el("a", { class: "btn btn-small", href: base(ctx) + "/qa/client.xlsx", download: "",
        title: "Toutes les Q&R du projet dans un seul tableau, quel que soit leur status ; le client modifie réponses et statuses" }, "⇩ Exporter les Q&R (Excel)"),
      data.can_edit ? el("button", { type: "button", class: "btn btn-small", onclick: () => A.qaImportDialog(ctx, reload) }, "⇧ Importer les Q&R…") : null,
      el("button", { type: "button", class: "btn btn-small", onclick: () => A.qaArchivesDialog(ctx) }, "🗄 Archives des échanges"),
      el("a", { class: "btn btn-small", href: base(ctx) + "/qa/register.xlsx", download: "",
        title: "Toutes les requirements, questions, réponses et l'historique signé (traçabilité)" }, "⇩ Registre complet (Excel)"),
      el("span", { class: "muted qa-keys" }, "Clavier : J / K pour passer d'une question à l'autre, R pour répondre, Ctrl+Entrée pour envoyer.")));
    const chips = el("div", { class: "qa-chips", role: "tablist" });
    const search = el("input", { type: "search", class: "qa-search", placeholder: "Filtrer (réf., clé, texte, personne)…", "aria-label": "Filtrer" });
    const dir = el("select", { "aria-label": "Sens" }, A.options([["team", "Questions de l'équipe (Qteam)"], ["cust", "Questions du client (Qcust)"]], "", "Les deux sens"));
    const list = el("div", { class: "qa-list" });
    page.append(chips, el("div", { class: "ag-filters" }, search, dir), list);
    keyboard(list);

    async function reload(changedId, keepFocus) {
      data = await api.get(base(ctx) + "/qa");
      draw(changedId, keepFocus);
    }
    function draw(changedId, keepFocus) {
      clear(chips);
      FILTERS.forEach(([key, label]) => {
        const n = COUNT_KEY[key] ? data.counts[COUNT_KEY[key]] : data.items.filter((q) => !isDone(q)).length;
        chips.append(el("button", { type: "button", role: "tab", class: "qa-chip" + (filter === key ? " active" : ""),
          "aria-selected": filter === key ? "true" : "false", onclick: () => { filter = key; draw(); } },
        label, el("span", { class: "qa-chip-n" }, String(n))));
      });
      const test = FILTERS.find(([k]) => k === filter)[2];
      const text = search.value.trim().toLowerCase();
      const items = data.items.filter((q) => test(q, data.me)
        && (!dir.value || q.direction === dir.value)
        && (!text || [q.full_ref, q.req_title, q.question, q.answer, q.asked_who, q.answered_who, q.owner_name].join(" ").toLowerCase().includes(text)));
      clear(list);
      if (!items.length) {
        list.append(el("div", { class: "empty" }, el("p", null, filter === "team" ? "Rien à traiter côté équipe. Bravo."
          : "Aucune question dans ce filtre.")));
        return;
      }
      items.forEach((q) => list.append(card(ctx, q, data, (id, soft) => reload(id, soft))));
      const target = list.querySelector('[data-id="' + (changedId || focusId || "") + '"]');
      if (target && !keepFocus) { target.focus(); target.scrollIntoView({ block: "center" }); }
    }
    search.addEventListener("input", () => draw());
    dir.addEventListener("change", () => draw());
    draw();
  }

  /* ---------- On the requirement page ---------- */
  function qaPanel(ctx, issue) {
    if (!issue.is_requirement) return null;
    const box = el("section", { class: "ag-block qa-panel" });
    async function load(changedId) {
      let data;
      try { data = await api.get(base(ctx) + "/qa?issue=" + issue.number); } catch (err) { return; }
      clear(box);
      const open = data.items.filter((q) => !isDone(q)).length;
      box.append(el("div", { class: "ag-block-head" },
        el("h2", null, "Q&A client (" + data.items.length + (open ? ", " + open + " non close(s)" : "") + ")"),
        el("span", null,
          data.can_edit ? el("button", { type: "button", class: "btn btn-small", onclick: () => A.qaNewDialog(ctx, issue, () => load()) }, "+ Question") : null,
          " ", el("a", { href: "#/goldmine/" + ctx.key + "/qa" }, "Toutes les questions"))));
      if (!data.items.length) box.append(el("p", { class: "muted" }, "Aucune question sur ce requirement."));
      data.items.forEach((q) => box.append(card(ctx, q, data, (id) => load(id))));
      if (changedId) { const t = box.querySelector('[data-id="' + changedId + '"]'); if (t) t.focus(); }
    }
    load();
    return box;
  }

  A.views.qa = qaView;
  A.qaPanel = qaPanel;
})();
