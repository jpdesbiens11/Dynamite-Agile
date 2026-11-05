/* Admin → Update → Framework: « Mise à jour en ligne » (0.60.36, D-O-045). Off by default (the server makes no outbound
   call); an administrator switches it on for a server that is on the Internet. Then: « Vérifier maintenant » shows the
   newer versions with their summary and changes, each to tick « Lu » (D-B-094: never one click); « Approuver et
   installer » runs the job on the server, followed here live -- a bar in %, the current step, what happens line by
   line --, then the page waits for the restart and the new version. */
(function () {
  "use strict";
  const { api, el, clear, toast } = DA;
  const lang = () => (DA.lang ? DA.lang() : "fr");
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  function bar(percent) {
    const fill = el("i");
    fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
    return el("div", { class: "uo-bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(percent) },
      fill, el("span", null, Math.round(percent) + " %"));
  }

  async function follow(box, target) {
    let done = false;
    while (!done) {
      let job;
      try { job = await api.get("/api/admin/update/online/progress"); } catch (err) { job = { state: "restarting", percent: 96, step: "Redémarrage du serveur", lines: [] }; }
      clear(box);
      box.append(el("p", { class: "uo-step" }, el("strong", null, job.step || "…")), bar(job.percent || 0),
        el("pre", { class: "uo-lines", "aria-live": "polite" }, (job.lines || []).join("\n")));
      if (job.state === "error") {
        box.append(el("p", { class: "form-error" }, "La mise à jour s'est arrêtée : " + job.error + " Rien n'est perdu : le code et "
          + "les données d'avant restent en place (ou dans ↺ Restaurer)."));
        return;
      }
      if (job.state === "done") return;
      if (job.state === "restarting") {
        for (let i = 0; i < 80; i++) {  // up to two minutes for the service to come back
          await wait(1500);
          try {
            const about = await api.get("/api/about");
            if (about.version === target) {
              clear(box);
              box.append(el("p", { class: "uo-step" }, el("strong", null, "C'est à jour : version " + target)), bar(100),
                el("p", { class: "up-ok" }, "✓ Le serveur a redémarré avec la nouvelle version. La page se recharge…"));
              setTimeout(() => location.reload(), 2500);
              return;
            }
          } catch (err) { /* the server is restarting */ }
        }
        box.append(el("p", { class: "form-error" }, "Le serveur ne répond pas encore. Correctif : rechargez la page dans une minute."));
        return;
      }
      await wait(700);
    }
  }

  function versions(s, start) {
    const ticks = [];
    const go = el("button", { type: "button", class: "btn btn-primary", disabled: true, onclick: () => start(ticks.filter((t) => t.checked).map((t) => t.value)) },
      "Approuver et installer " + s.latest);
    const refresh = () => { go.disabled = !ticks.every((t) => t.checked); };
    const list = s.newer.map((v) => {
      const tick = el("input", { type: "checkbox", value: v.version, onchange: refresh });
      ticks.push(tick);
      return el("li", { class: "uo-version" },
        el("p", null, el("strong", null, v.version), " · " + (v.date || "") + " — " + ((v.summary && (v.summary[lang()] || v.summary.fr)) || "")),
        v.changes && v.changes.length ? el("ul", null, v.changes.map((c) => el("li", null, c))) : null,
        el("label", { class: "check" }, tick, " Lu"));
    });
    return el("div", null,
      el("p", null, el("strong", null, s.newer.length + " version(s) plus récente(s)"), " que la vôtre (" + s.current + ") — la dernière : "
        + s.latest + " du " + s.date + " (" + Math.round((s.bytes || 0) / 1024) + " Ko). Lisez ce que chacune apporte, cochez « Lu », puis approuvez."),
      el("ol", { class: "uo-versions" }, list),
      el("div", { class: "actions" }, go, el("span", { class: "muted" }, " Le code d'avant et vos données sont sauvegardés d'abord ; rien n'est effacé.")));
  }

  function draw(holder, s) {
    clear(holder);
    const toggle = el("input", { type: "checkbox", checked: s.enabled, onchange: async () => {
      try { draw(holder, await api.put("/api/admin/update/online", { enabled: toggle.checked })); }
      catch (err) { toast(err.message, "error"); toggle.checked = !toggle.checked; }
    } });
    const progress = el("div", { class: "uo-progress" });
    const start = async (read) => {
      if (!window.confirm("Installer la version " + s.latest + " maintenant ? Le serveur redémarre à la fin (quelques secondes).")) return;
      try { await api.post("/api/admin/update/online/start", { read }); follow(progress, s.latest); }
      catch (err) { toast(err.message, "error"); }
    };
    holder.append(el("h2", null, "Mise à jour en ligne"),
      el("label", { class: "check uo-toggle" }, toggle, " Vérifier les mises à jour en ligne — ce serveur a accès à Internet"),
      el("p", { class: "muted" }, "Coupé, le serveur ne va jamais sur Internet (réseau fermé) : on télécharge alors le paquet à la main, "
        + "ci-dessous. Activé, il ne va sur le site du projet (" + s.site + ") que lorsqu'un administrateur le demande."));
    if (s.enabled) {
      const result = el("div", { class: "uo-result" });
      holder.append(el("div", { class: "actions" },
        el("button", { type: "button", class: "btn", onclick: async () => {
          result.append(el("p", { class: "muted" }, "Vérification…"));
          try { draw(holder, await api.post("/api/admin/update/online/check", {})); }
          catch (err) { clear(result); result.append(el("p", { class: "form-error" }, err.message)); }
        } }, "Vérifier maintenant"),
        el("span", { class: "muted" }, s.last_check ? " Dernière vérification : " + s.last_check : " Jamais vérifié.")), result);
      if (s.last_check) {
        result.append(s.newer.length ? versions(s, start)
          : el("p", { class: "up-ok" }, "✓ À jour : " + s.current + " est la dernière version publiée" + (s.date ? " (" + s.date + ")." : ".")));
      }
    }
    holder.append(progress);
    if (s.job && (s.job.state === "running" || s.job.state === "restarting")) follow(progress, s.job.version);
  }

  function block() {
    const holder = el("section", { class: "up-step up-online", "data-new": "0.60.36-update-online" }, el("p", { class: "muted" }, "…"));
    api.get("/api/admin/update/online").then((s) => draw(holder, s)).catch((err) => { clear(holder); holder.append(el("p", { class: "form-error" }, err.message)); });
    return holder;
  }

  DA.adminUpdateOnline = { block };
})();
