/* Dynamite - threaded comments under a saved page (D-B-002).
   Plain text, rendered with textContent; each comment shows the page
   version it was written against. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const DY = DA.dynamite;

  function initials(name) { return DA.initials ? DA.initials(name || "?") : (name || "?").slice(0, 2); }

  function commentsSection(ctx, pageId) {
    const url = "/api/dynamite/p/" + ctx.pid + "/pages/" + pageId + "/comments";
    const section = el("section", { class: "dy-comments", "aria-labelledby": "dy-comments-title" });
    let data = null;
    let replyForm = null;

    async function load() {
      try { data = await api.get(url); draw(); }
      catch (err) { clear(section); section.append(el("p", { class: "form-error" }, err.message)); }
    }

    function composer(parentId, placeholder, onCancel) {
      const area = el("textarea", { rows: parentId ? 2 : 3, maxlength: 10000, placeholder,
        "aria-label": parentId ? "Réponse" : "Nouveau commentaire" });
      const submit = el("button", { type: "submit", class: "btn btn-primary btn-small" },
        parentId ? "Répondre" : "Commenter");
      const form = el("form", { class: "dy-comment-form" + (parentId ? " dy-reply-form" : ""),
        onsubmit: async (ev) => {
          ev.preventDefault();
          if (!area.value.trim()) { area.focus(); return; }
          submit.disabled = true;
          try {
            await api.post(url, { body: area.value, parent_comment_id: parentId || null });
            await load();
          } catch (err) { toast(err.message, "error"); submit.disabled = false; }
        } }, area, el("div", { class: "form-actions" },
        onCancel ? el("button", { type: "button", class: "btn btn-small", onclick: onCancel }, "Annuler") : null,
        submit));
      return { form, area };
    }

    function node(cm, depth) {
      const mine = cm.author_id === DA.session.user.id;
      const canDelete = mine || data.role === "admin";
      const older = cm.page_version < data.current_version;
      const article = el("article", { class: "dy-comment dy-depth-" + Math.min(depth, 3), id: "dy-comment-" + cm.id },
        el("div", { class: "dy-comment-head" },
          el("span", { class: "avatar", "aria-hidden": "true" }, initials(cm.author_name)),
          el("strong", null, cm.author_name || "Ancien compte"),
          el("span", { class: "badge " + (older ? "badge-neutral" : "badge-ok"),
            title: older ? "Écrit sur une version antérieure de la page" : "Écrit sur la version actuelle" },
          "v" + cm.page_version),
          el("span", { class: "muted" }, DA.formatDate(cm.created_at)),
          el("button", { type: "button", class: "link-btn", onclick: () => reply(cm, article) }, "Répondre"),
          canDelete ? el("button", { type: "button", class: "link-btn", onclick: async () => {
            const replies = data.comments.some((x) => x.parent_comment_id === cm.id);
            if (replies && !window.confirm("Supprimer ce commentaire et ses réponses ?")) return;
            try { await api.del(url + "/" + cm.id); await load(); } catch (err) { toast(err.message, "error"); }
          } }, "Supprimer") : null),
        el("div", { class: "dy-comment-body" }, cm.body));
      return article;
    }

    function reply(cm, after) {
      if (replyForm) replyForm.remove();
      const { form, area } = composer(cm.id, "Répondre à " + (cm.author_name || "ce commentaire") + "…",
        () => { form.remove(); replyForm = null; });
      replyForm = form;
      after.after(form);
      area.focus();
    }

    function draw() {
      clear(section);
      replyForm = null;
      section.append(el("h2", { id: "dy-comments-title" }, "Commentaires (" + data.comments.length + ")"));
      const byParent = new Map();
      data.comments.forEach((cm) => {
        const k = cm.parent_comment_id || 0;
        if (!byParent.has(k)) byParent.set(k, []);
        byParent.get(k).push(cm);
      });
      (function walk(parentId, depth) {
        (byParent.get(parentId) || []).forEach((cm) => { section.append(node(cm, depth)); walk(cm.id, depth + 1); });
      })(0, 0);
      if (!data.comments.length) section.append(el("p", { class: "muted" }, "Aucun commentaire pour l'instant."));
      section.append(composer(null, "Ajouter un commentaire sur cette page…").form);
    }

    section.append(el("h2", { id: "dy-comments-title" }, "Commentaires"), el("p", { class: "muted" }, "Chargement…"));
    load();
    return section;
  }

  DY.commentsSection = commentsSection;
})();
