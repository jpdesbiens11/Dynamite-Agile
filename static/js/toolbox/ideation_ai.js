/* Tools · « Idéation » · the AI proposes the groups of the board (0.60.112, D-O-125): a digital brainstorm.
   « IA : proposer des groupes »  the post-its of the session in a prompt (copied), the AI's answer pasted back: each post-it that
                                  changes group (label before → after), the post-its the AI suggests (unticked: the team decides),
                                  what is refused; « Appliquer la sélection » moves them, the board shows the new groups.
   « Vers Diamond ↔ IA »          the same session opened inside Diamond, where « ↔ IA » sends its post-its as source material. */
(function () {
  "use strict";

  const { api, el, toast, modal, field } = DA;
  const X = {};

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (err) { return false; }
  }

  function preview(res, boxes) {
    const c = res.counts;
    const groups = new Map();
    res.entries.forEach((e) => { const g = e.group || "—"; if (!groups.has(g)) groups.set(g, []); groups.get(g).push(e); });
    return el("div", { class: "dm-import-preview" },
      el("p", null, el("strong", null, "Aperçu : "), [c.move + " change(nt) de groupe", c.same + " déjà en place", c.new + " nouveau(x) post-it (IA)",
        c.refused + " refusé(s)"].join(" · ")),
      res.left.length ? el("p", { class: "dm-ai-note" }, res.left.length + " post-it sans groupe dans la réponse : " + res.left.join(", ") + " (ils gardent le leur).") : null,
      Array.from(groups.entries()).map(([name, list]) => el("details", { class: "tl-ai-group", open: true },
        el("summary", null, el("strong", null, name), list[0].why ? el("span", { class: "muted" }, " — " + list[0].why) : null),
        el("ul", { class: "tl-ai-list" }, list.map((e) => {
          const tick = e.kind === "move" || e.kind === "new";
          const box = tick ? el("input", { type: "checkbox", checked: e.default, "aria-label": "Appliquer " + (e.code || e.text.slice(0, 40)) }) : null;
          if (box) boxes.push([e, box]);
          return el("li", { class: "tl-ai-" + e.kind }, box, " ", e.code ? el("span", { class: "dm-code" }, e.code + " ") : null, e.text,
            el("span", { class: "muted" }, e.kind === "move" ? "  (" + (e.before || "sans groupe") + " → " + e.group + ")"
              : e.kind === "refused" ? "  — " + e.reason : e.kind === "new" ? "  — proposé par l'IA" : ""));
        })))),
      el("p", { class: "muted" }, "Décochez ce que l'équipe refuse ; les post-it proposés par l'IA sont décochés : cochez ceux que vous gardez."));
  }

  X.open = function (ctx, state) {
    const sid = state.data.session.id;
    const base = DA.tools.ideation.base(ctx) + "/" + sid + "/ai";
    const out = el("div");
    const text = el("textarea", { rows: 6, class: "dm-story-ai-text", "aria-label": "Réponse de l'IA",
      placeholder: "Collez ici la réponse de l'assistant IA (son bloc ```json {\"groups\": …})." });
    const result = el("div");
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true }, "Appliquer la sélection");
    let boxes = [], close = () => {};
    const prompt = async () => {
      DA.clear(out);
      let res;
      try { res = await api.get(base + "/prompt"); } catch (err) { toast(err.message, "error"); return; }
      const ok = await copy(res.prompt);
      const area = el("textarea", { rows: 6, readonly: true, class: "dm-story-ai-text", "aria-label": "Prompt" }, res.prompt);
      out.append(el("p", { class: ok ? "up-ok" : "muted" }, (ok ? "✓ Prompt copié" : "Copiez ce prompt") + " (" + res.count
        + " post-it) : collez-le dans Claude ou Gemini ; il dessine le tableau groupé, puis rend un bloc JSON à coller ci-dessous."), area);
      area.select();
    };
    const check = async () => {
      DA.clear(result);
      boxes = [];
      apply.disabled = true;
      if (!text.value.trim()) return;
      try {
        const res = await api.post(base + "/import", { file: text.value, mode: "preview" });
        result.append(preview(res, boxes));
        apply.disabled = !boxes.length;
      } catch (err) { result.append(el("p", { class: "form-error", role: "alert" }, err.message)); }
    };
    text.addEventListener("change", check);
    apply.addEventListener("click", async () => {
      apply.disabled = true;
      const skip = boxes.filter(([e, b]) => e.kind === "move" && !b.checked).map(([e]) => e.id);
      const take = boxes.filter(([e, b]) => e.kind === "new" && b.checked).map(([e]) => e.id);
      try {
        const res = await api.post(base + "/import", { file: text.value, mode: "apply", skip, take });
        toast(res.moved + " post-it regroupé(s), " + res.added + " ajouté(s).", "success");
        close();
        state.data = await api.get(DA.tools.ideation.base(ctx) + "/" + sid);
        state.sort = "group";
        state.redraw();
      } catch (err) { apply.disabled = false; toast(err.message, "error"); }
    });
    close = modal("IA : proposer des groupes", el("div", { class: "form dm-ai-dialog", "data-new": "0.60.112-ideation-ai" },
      el("p", { class: "muted" }, "Brainstorm numérique : l'équipe a posé ses post-it ; l'IA propose des groupes nommés, l'équipe "
        + "décide. Rien ne bouge avant « Appliquer la sélection »."),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: prompt }, "1 · Préparer et copier le prompt")), out,
      field("2 · La réponse de l'IA", text),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: check }, "Vérifier"), apply), result));
    const m = out.closest(".modal");
    if (m) m.classList.add("dm-cls-modal");
  };

  /** The buttons of a session's header: the AI's groups, and the board towards Diamond. */
  X.buttons = function (ctx, state) {
    const s = state.data.session;
    const canWrite = DA.agile.canEdit(ctx) && s.status !== "closed";
    const inDiamond = ctx.module === "diamond";
    return [
      canWrite && state.data.ideas.length ? el("button", { type: "button", class: "btn", "data-new": "0.60.112-ideation-ai",
        title: "L'IA propose des groupes de post-it ; l'équipe décide", onclick: () => X.open(ctx, state) }, "IA : proposer des groupes") : null,
      !inDiamond && state.data.ideas.length && (DA.session.modules || []).some((m) => m.key === "diamond" && m.available !== false)
        ? el("a", { class: "btn", "data-new": "0.60.112-ideation-diamond", href: "#/diamond/" + ctx.key + "/ideation/" + s.id,
          title: "Ouvrir la séance dans Diamond : « ↔ IA » y envoie ses post-it comme matière première" }, "Vers Diamond ↔ IA") : null];
  };

  DA.tools = DA.tools || {};
  DA.tools.ideationAi = X;
})();
