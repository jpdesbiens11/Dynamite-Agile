/* Core lot v0.37 (0.60.103, D-O-111): ⚙ Admin → Plateforme → « Modules et fonctions » -- what is on and off for every
   Space: a whole module (Timesheet), a function of the core (objectives, annual review, profile, « Mon équipe »), a part
   of a module (Diamond: Procédés, PFMEA, Plans de contrôle). Turned off, a part leaves the menus and its routes answer 404;
   its data is kept, nothing is deleted. Checked together, applied by « Enregistrer ». */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;

  async function render(body) {
    const data = await api.get("/api/admin/features");
    draw(body, data);
  }

  function draw(body, data) {
    clear(body);
    const boxes = {};
    const byKey = Object.fromEntries(data.features.map((f) => [f.key, f]));
    const groups = [];
    data.features.forEach((f) => {
      let g = groups.find((x) => x.name === f.group);
      if (!g) groups.push(g = { name: f.group, items: [] });
      g.items.push(f);
    });
    const sync = () => Object.entries(boxes).forEach(([k, box]) => {  // a part that needs another one follows it
      const need = byKey[k].requires;
      if (need && boxes[need]) { box.disabled = !boxes[need].checked; if (box.disabled) box.checked = false; }
    });
    body.append(el("p", { class: "muted", "data-new": "0.60.103-features" }, "Activez ou désactivez des parties de la plateforme pour tous les "
      + "Spaces. Désactivée, une partie disparaît des menus et ses adresses répondent « désactivé » ; ses données sont gardées : "
      + "réactivée, tout est là. Par exemple, une plateforme d'étudiants du baccalauréat n'a souvent besoin ni des feuilles de temps "
      + "ni de l'évaluation annuelle."),
    groups.map((g) => el("section", { class: "ft-group" }, el("h2", null, g.name), g.items.map((f) => {
      const box = el("input", { type: "checkbox", checked: f.on });
      boxes[f.key] = box;
      box.addEventListener("change", sync);
      return el("label", { class: "ft-item" + (f.requires ? " ft-sub" : "") }, box, el("span", null, el("strong", null, f.label),
        el("span", { class: "muted" }, " — " + f.help + (f.requires ? " Demande « " + byKey[f.requires].label + " »." : ""))));
    }))),
    el("div", { class: "btn-row" }, el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
      const features = {};
      Object.entries(boxes).forEach(([k, box]) => { features[k] = box.checked; });
      try {
        const res = await api.put("/api/admin/features", { features });
        toast("Réglages enregistrés. Rechargez la page pour voir les menus à jour.", "success");
        draw(body, res);
      } catch (err) { toast(err.message, "error"); }
    } }, "Enregistrer")));
    sync();
  }

  DA.adminExtra = DA.adminExtra || {};
  DA.adminExtra.loaders = Object.assign(DA.adminExtra.loaders || {}, { features: render });
  /* the other screens ask: DA.feature("timesheet") -- true unless an administrator turned it off */
  DA.feature = (key) => !DA.session || !DA.session.features || DA.session.features[key] !== false;
})();
