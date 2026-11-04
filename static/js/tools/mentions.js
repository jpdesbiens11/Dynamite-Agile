/* @mentions (core lot v0.19, D-A-046).
   - red counter on the « Dashboard » tab: unread messages, refreshed every minute and at every screen change;
   - « @ » in any text field (comments, Q&A, the wiki's source mode...) proposes the accounts; the choice writes
     « @username », the name the server recognises;
   - DA.messagesPanel(): the « Messages » section of the Dashboard (excerpt, place, « Répondre » opens it). */
(function () {
  "use strict";
  const REFRESH_MS = 60000;
  let timer = null;

  async function refresh() {
    if (!window.DA || !DA.session || !DA.session.user) return;
    try {
      const r = await DA.api.get("/api/mentions/count");
      document.querySelectorAll(".mention-count").forEach((n) => {
        n.hidden = !r.unread;
        n.textContent = r.unread > 99 ? "99+" : String(r.unread);
        n.setAttribute("aria-label", r.unread + " message(s) non lu(s)");
        n.title = r.unread + " message(s) non lu(s)";
      });
    } catch (err) { /* signed out or offline: the counter just stays as it is */ }
  }
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(async () => { await refresh(); schedule(); }, REFRESH_MS);
  }
  window.addEventListener("hashchange", () => setTimeout(refresh, 300));
  document.addEventListener("DOMContentLoaded", () => { setTimeout(refresh, 800); schedule(); });

  /* ---------- « @ » suggestions ---------- */
  const box = document.createElement("div");
  box.className = "mention-suggest";
  box.setAttribute("role", "listbox");
  box.hidden = true;
  let field = null, start = -1, items = [], index = 0, pending = 0;

  function close() { box.hidden = true; field = null; items = []; }
  function choose(i) {
    if (!field || !items[i]) return;
    const value = field.value, caret = field.selectionStart;
    const insert = "@" + items[i].username + " ";
    field.value = value.slice(0, start) + insert + value.slice(caret);
    const pos = start + insert.length;
    field.setSelectionRange(pos, pos);
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.focus();
    close();
  }
  function draw() {
    box.textContent = "";
    items.forEach((p, i) => {
      const opt = document.createElement("div");
      opt.className = "mention-option" + (i === index ? " active" : "");
      opt.setAttribute("role", "option");
      opt.setAttribute("aria-selected", String(i === index));
      const name = document.createElement("strong");
      name.textContent = p.display_name || p.username;
      const login = document.createElement("span");
      login.textContent = " @" + p.username;
      opt.append(name, login);
      opt.addEventListener("mousedown", (ev) => { ev.preventDefault(); choose(i); });
      box.append(opt);
    });
    box.hidden = !items.length;
  }
  function place(target) {
    const r = target.getBoundingClientRect();
    box.style.left = Math.round(r.left + window.scrollX) + "px";
    box.style.top = Math.round(r.bottom + window.scrollY + 2) + "px";
    box.style.minWidth = Math.min(320, Math.round(r.width)) + "px";
  }
  document.addEventListener("input", async (ev) => {
    const t = ev.target;
    if (!(t instanceof HTMLTextAreaElement || (t instanceof HTMLInputElement && (t.type === "text" || t.type === "search")))) return;
    if (t.closest(".mention-off")) return;
    const before = t.value.slice(0, t.selectionStart);
    const m = /(^|[\s(])@([\w.-]{0,30})$/.exec(before);
    if (!m) { if (field === t) close(); return; }
    field = t; start = before.length - m[2].length - 1; index = 0;
    const ticket = ++pending;
    try {
      const r = await DA.api.get("/api/mentions/people?q=" + encodeURIComponent(m[2]));
      if (ticket !== pending || field !== t) return;
      items = r.people;
      if (!box.isConnected) document.body.append(box);
      place(t);
      draw();
    } catch (err) { close(); }
  });
  document.addEventListener("keydown", (ev) => {
    if (box.hidden || ev.target !== field) return;
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      index = (index + (ev.key === "ArrowDown" ? 1 : items.length - 1)) % items.length;
      draw();
    } else if (ev.key === "Enter" || ev.key === "Tab") {
      ev.preventDefault();
      choose(index);
    } else if (ev.key === "Escape") {
      close();
    }
  }, true);
  document.addEventListener("focusout", (ev) => { if (ev.target === field) setTimeout(close, 150); });

  /* ---------- Dashboard « Messages » ---------- */
  function when(iso) {
    const d = new Date(/([zZ]|[+-]\d\d:\d\d)$/.test(iso) ? iso : iso + "Z");  // server time in UTC
    return isNaN(d) ? iso : d.toLocaleString("fr-CA", { dateStyle: "short", timeStyle: "short" });
  }
  async function markRead(body) {
    await DA.api.post("/api/mentions/read", body);
    refresh();
  }
  (() => {  // DA exists: api.js is loaded before this file
    DA.refreshMentions = refresh;
    DA.messagesPanel = async function (box) {
      const { el } = DA;
      const sent = box === "sent";  // D-B-089: « Reçus » / « Envoyés »
      const done = box === "done";  // D-B-100: answered or acknowledged
      const panel = el("section", { class: "db-messages", "aria-label": "Messages" });
      let data;
      try { data = await DA.api.get("/api/mentions" + (sent ? "?box=sent" : done ? "?box=done" : "")); } catch (err) { return panel; }
      const list = data.messages.slice(0, 12);
      const swap = async (which) => { panel.replaceWith(await DA.messagesPanel(which)); };
      const tab = (which, label, on) => el("button", { type: "button", role: "tab", class: "link-btn" + (on ? " on" : ""),
        "aria-selected": on ? "true" : "false", onclick: () => { if (!on) swap(which); } }, label);
      const tabs = el("span", { class: "db-msg-tabs", role: "tablist", "data-new": "0.45.1-messages-sent" },
        tab("", "Reçus", !sent && !done), " · ", el("span", { "data-new": "0.50.0-messages-done" }, tab("done", "Traités", done)),
        " · ", tab("sent", "Envoyés", sent));
      panel.append(el("div", { class: "db-messages-head" },
        el("h2", null, "Messages", !sent && !done && data.unread ? el("span", { class: "mention-count db-inline" }, String(data.unread)) : null),
        tabs,
        !sent && !done && data.unread ? el("button", { type: "button", class: "link-btn", onclick: async () => { await markRead({ all: true }); DA.refreshView && DA.refreshView(); } },
          "Tout marquer comme lu") : null));
      if (!list.length) {
        panel.append(el("p", { class: "muted" }, sent
          ? "Aucun message envoyé. Écrivez « @identifiant » d'un collègue dans une page, un commentaire ou une Q&A : il le reçoit ici, "
            + "sur son Dashboard, et vous voyez ici s'il l'a lu."
          : done ? "Rien de traité pour l'instant : les messages auxquels vous répondez ici, et les réponses que vous acceptez "
            + "(« Acknowledge »), viennent ici."
          : "Aucun message. Quand quelqu'un écrit « @" + DA.session.user.username + " » dans une page, un commentaire ou une Q&A, le "
            + "message arrive ici et un « 1 » rouge s'affiche sur l'onglet Dashboard. Écrivez vous-même « @" + DA.session.user.username
            + " » pour vous laisser une note."));
        return panel;
      }
      if (sent) {
        panel.append(el("ul", { class: "db-message-list" }, list.map((m) => el("li", { class: "read" },
          el("div", { class: "db-message-meta" }, el("span", { class: "badge badge-info" }, m.kind_label), " à ",
            el("strong", null, m.recipient || "?"), " · " + when(m.created_at) + (m.project_key ? " · " + m.project_key : ""), " · ",
            m.read_at ? el("span", { class: "badge badge-ok" }, "Lu") : el("span", { class: "badge badge-warn" }, "Non lu")),
          el("a", { class: "db-message-title", href: m.href }, m.title),
          el("p", { class: "db-message-excerpt" }, m.excerpt)))));
        return panel;
      }
      const self = DA.session.user.id;
      const gone = (li) => { li.remove(); DA.refreshMentions && DA.refreshMentions(); };
      const ack = (m) => el("button", { type: "button", class: "btn btn-small" + (m.reply_to ? " btn-primary" : ""), "data-new": "0.50.0-acknowledge",
        "data-tip": "Retire ce message de votre Dashboard (gardé dans « Traités »)", onclick: async (ev) => {
          try { await DA.api.post("/api/mentions/" + m.id + "/ack", {}); gone(ev.target.closest("li")); }
          catch (err) { DA.toast(err.message, "error"); }
        } }, "Acknowledge");
      const replyBox = (m) => {
        const text = el("textarea", { rows: 3, maxlength: 9000, "aria-label": "Votre réponse à " + (m.author || "") });
        const box = el("div", { class: "db-reply", hidden: true }, text,
          el("p", { class: "muted" }, "Enregistrée en commentaire sur place, signée par vous, avec « @" + m.author_username + " » ajouté à la fin."),
          el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn btn-small btn-primary", onclick: async (ev) => {
            if (!text.value.trim()) { text.focus(); return; }
            ev.target.disabled = true;
            try {
              const r = await DA.api.post("/api/mentions/" + m.id + "/reply", { text: text.value });
              DA.toast(r.notice, "success");
              gone(ev.target.closest("li"));
            } catch (err) { DA.toast(err.message, "error"); ev.target.disabled = false; }
          } }, "Envoyer la réponse")));
        box.open = () => { box.hidden = false; text.focus(); };
        return box;
      };
      panel.append(el("ul", { class: "db-message-list" }, list.map((m) => {
        const box = !done && m.can_reply && !m.reply_to ? replyBox(m) : null;
        const kind = m.author_id === self ? "Note" : m.reply_to ? "Réponse" : m.kind_label;
        return el("li", { class: done || m.read_at ? "read" : "unread" },
          el("div", { class: "db-message-meta" }, el("span", { class: "badge " + (m.reply_to ? "badge-ok" : "badge-info") }, kind), " ",
            el("strong", null, m.author_id === self ? "Moi" : (m.author || "Quelqu'un")), " · " + when(m.created_at) + (m.project_key ? " · " + m.project_key : ""),
            done ? el("span", { class: "badge badge-neutral" }, m.answered_at ? "Répondu" : "Traité") : null),
          el("a", { class: "db-message-title", href: m.href, onclick: () => { if (!m.read_at) markRead({ ids: [m.id] }); } }, m.title),
          el("p", { class: "db-message-excerpt" }, m.excerpt),
          done ? null : el("div", { class: "db-message-actions" },
            box ? el("button", { type: "button", class: "btn btn-small btn-primary", "data-new": "0.50.0-reply-here", onclick: () => box.open() }, "Répondre ici") : null,
            el("a", { class: "btn btn-small", href: m.href, onclick: () => { if (!m.read_at) markRead({ ids: [m.id] }); } }, "Ouvrir sur place"),
            m.reply_to || m.author_id === self ? ack(m) : null,
            m.read_at || m.reply_to ? null : el("button", { type: "button", class: "btn btn-small", onclick: async (ev) => {
              await markRead({ ids: [m.id] });
              ev.target.closest("li").className = "read";
              ev.target.remove();
            } }, "Marquer comme lu")),
          box);
      })));
      return panel;
    };
  })();
})();
