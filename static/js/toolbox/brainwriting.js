/* Tools · Design - Brainwriting 6-3-5 with connected participants (D-B-073).
   Préparation: everybody clicks « Rejoindre »; the facilitator « Démarrer ».
   Rounds of X minutes (server clock): pairs change every round (round robin),
   each participant sees live what his partner writes and builds on it
   (« Rebondir »); « Tour suivant » / « Terminer » for the facilitator.
   Revue: everybody sees every idea, labels them, gives impact and feasibility,
   and stars the best ones (« ★ seulement » brings them out of the log). */
(function () {
  "use strict";

  const { el, clear } = DA;
  const A = DA.agile;
  const PHASE = { setup: "Préparation", running: "Tours en cours", review: "Revue et tri" };

  function view(page, ctx, data) {
    const I = DA.tools.ideation;
    const state = { ctx, data, sort: "group", onlyStars: false, parent: null, selected: new Set(), offset: 0 };
    const top = el("div");
    const add = I.addForm(state);
    const body = el("div");
    const clock = el("span", { class: "tl-clock", role: "timer", "aria-live": "off" });
    page.append(top, add, body);

    function sync() {  // server time - local time, so the countdown matches the server's rounds
      const bw = state.data.bw;
      state.offset = bw && bw.server_now ? new Date(bw.server_now).getTime() - Date.now() : 0;
    }
    function tick() {
      const bw = state.data.bw;
      if (!bw || bw.phase !== "running" || !bw.ends_at) { clock.textContent = ""; return; }
      const left = Math.max(0, Math.round((new Date(bw.ends_at).getTime() - Date.now() - state.offset) / 1000));
      clock.textContent = Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
      clock.classList.toggle("tl-clock-end", left <= 30);
      if (left === 0 && !state.fetching) {
        state.fetching = true;
        DA.api.get(I.base(ctx) + "/" + state.data.session.id).then((d) => { state.data = d; state.redraw(); })
          .catch(() => {}).finally(() => { setTimeout(() => { state.fetching = false; }, 2000); });
      }
    }
    const timer = setInterval(() => { if (!page.isConnected) { clearInterval(timer); return; } tick(); }, 1000);

    const control = (action, label, primary) => el("button", { type: "button", class: "btn btn-small" + (primary ? " btn-primary" : ""),
      onclick: () => {
        if (action === "finish" && !window.confirm("Terminer les tours et passer à la revue ? Tout le monde verra toutes les idées.")) return;
        I.act(state, "post", "/brainwriting", { action });
      } }, label);

    function statusPanel() {
      const { bw, session: s } = state.data;
      const open = s.status !== "closed";
      const canWrite = A.canEdit(ctx) && open;
      const people = el("div", { class: "tl-people" }, bw.people.length ? bw.people.map((p) => el("span", {
        class: "badge" + (p.user_id === DA.session.user.id ? " tl-me" : "") }, p.name)) : el("span", { class: "muted" }, "Personne encore."));
      const actions = el("div", { class: "tl-actions" },
        canWrite && !bw.joined && bw.phase !== "review" ? control("join", "Rejoindre la séance", true) : null,
        canWrite && bw.facilitator && bw.phase === "setup" ? control("start", "Démarrer (tour 1)", true) : null,
        canWrite && bw.facilitator && bw.phase === "running" ? control("next", bw.round < bw.rounds ? "Tour suivant" : "Terminer ce tour") : null,
        canWrite && bw.facilitator && bw.phase === "running" ? control("finish", "Terminer et passer à la revue") : null);
      const line = bw.phase === "running"
        ? [el("strong", null, "Tour " + bw.round + " / " + bw.rounds), " · reste ", clock,
          " · " + bw.ideas_per_round + " idées visées par tour, " + bw.minutes + " min par tour"]
        : bw.phase === "setup" ? [el("strong", null, "En attente du départ"), " · " + bw.rounds + " tours de " + bw.minutes
          + " min, " + bw.ideas_per_round + " idées par tour. Chacun clique « Rejoindre », puis l'animateur « Démarrer »."]
          : [el("strong", null, "Revue"), " · toutes les idées sont visibles : étiquetez (« trier »), donnez impact et "
            + "faisabilité, étoilez ★ les meilleures."];
      const box = el("section", { class: "tl-bw-status tl-bw-" + bw.phase },
        el("div", { class: "tl-bw-line" }, el("span", { class: "badge tl-phase" }, PHASE[bw.phase]), ...line), people, actions);
      if (bw.phase === "running" && bw.joined) {
        const mineNow = state.data.ideas.filter((i) => i.author_id === DA.session.user.id && i.round === bw.round).length;
        box.append(el("p", { class: "tl-pair" }, bw.partners.length
          ? ["Votre partenaire ce tour : ", el("strong", null, bw.partners.map((p) => p.name).join(" et ")),
            " — ses idées s'affichent en direct ; « Rebondir » sur l'une d'elles pour la compléter."]
          : "Seul ce tour (nombre de participants) : écrivez vos idées, elles seront partagées à la revue.",
        el("span", { class: "muted" }, " · Vos idées ce tour : " + mineNow + " / " + bw.ideas_per_round)),
        bw.met.length ? el("p", { class: "muted" }, "Partenaires rencontrés : " + bw.met.join(", ") + ".") : "");
      } else if (bw.phase === "running") {
        box.append(el("p", { class: "muted" }, "Vous n'êtes pas participant : " + (state.data.hidden
          ? state.data.hidden + " idée(s) seront visibles à la revue." : "les idées seront visibles à la revue.")));
      }
      if (bw.groups.length && bw.phase === "running") {
        box.append(el("p", { class: "muted tl-groups" }, "Paires du tour : " + bw.groups.map((g) => g.join(" ↔ ")).join(" · ")));
      }
      return box;
    }

    state.redraw = () => {
      sync();
      clear(top);
      clear(body);
      const { ideas, bw } = state.data;
      top.append(...I.header(ctx, state).filter(Boolean), statusPanel());
      add.refresh();
      add.hidden = add.hidden || bw.phase === "setup" || (bw.phase === "running" && !bw.joined);
      const me = DA.session.user.id;
      if (bw.phase === "running") {
        const partners = new Set(bw.partners.map((p) => p.user_id));
        const cols = [["Mes idées", ideas.filter((i) => i.author_id === me), false],
          ["Mon partenaire (en direct)", ideas.filter((i) => partners.has(i.author_id)), true],
          ["Partenaires précédents", ideas.filter((i) => i.author_id !== me && !partners.has(i.author_id)), true]];
        body.append(el("div", { class: "tl-bw-cols" }, cols.filter(([, list], n) => n < 2 || list.length).map(([title, list, partner]) =>
          el("section", { class: "tl-bw-col" }, el("h3", { class: "tl-group" }, title + " (" + list.length + ")"),
            el("div", { class: "tl-ideas tl-ideas-col" }, list.slice().reverse().map((i) => I.card(state, i, { partner })))))));
      } else if (bw.phase === "review") {
        body.append(I.toolbar(state, "par étiquette"));
        I.groups(state, ideas, (i) => i.tag || "Sans étiquette (à trier)")
          .forEach((items, name) => {
            body.append(name ? el("h3", { class: "tl-group" }, name + " (" + items.length + ")") : "",
              el("div", { class: "tl-ideas" }, items.map((i) => I.card(state, i))));
          });
        if (!ideas.length) body.append(el("div", { class: "empty" }, el("p", null, "Aucune idée.")));
      }
      tick();
    };
    state.redraw();
    I.poll(state, page);
  }

  DA.tools = DA.tools || {};
  DA.tools.brainwriting = view;
})();
