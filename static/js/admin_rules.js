/* Administration - « Règles d'accès » (core lot v0.6, D-B-016): export and
   import of users and their project rights as a readable text script.
   Import is checked first (« Vérifier », nothing written), then applied. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;

  function download(url) {
    const frame = el("iframe", { src: url, class: "ag-hidden-frame", title: "téléchargement" });
    document.body.append(frame);
    setTimeout(() => frame.remove(), 60000);
  }

  function reportView(result) {
    const box = el("div", { class: "rules-report" });
    const s = result.summary;
    box.append(el("p", { class: s.problems ? "rules-bad" : "rules-good" },
      (result.dry_run ? "Vérification : " : "Import appliqué : ") + s.ok + " ligne(s) valide(s), "
      + s.problems + " à corriger." + (result.dry_run && !s.problems ? " Vous pouvez appliquer." : "")));
    if (result.created && result.created.length) {
      box.append(el("div", { class: "rules-passwords" },
        el("strong", null, "Mots de passe temporaires — à remettre en personne, affichés une seule fois :"),
        el("ul", null, result.created.map((c) => el("li", null, el("code", null, c.username), " : ",
          el("code", null, c.temp_password))))));
    }
    box.append(el("div", { class: "table-wrap" }, DA.table(["Ligne", "Résultat", "Détail"], result.report.map((r) =>
      el("tr", { class: r.ok ? null : "rules-row-bad" }, el("td", { class: "muted" }, String(r.line)),
        el("td", null, el("span", { class: "badge " + (r.ok ? "badge-ok" : "badge-off") }, r.action)),
        el("td", null, r.detail))))));
    return box;
  }

  async function render(body) {
    clear(body);
    const area = el("textarea", { class: "rules-text", spellcheck: "false", rows: 22,
      "aria-label": "Script des règles d'accès", placeholder: "utilisateur identifiant | Nom | utilisateur | actif\n"
        + "droit       identifiant | EQP | editeur" });
    const out = el("div");
    const file = el("input", { type: "file", accept: ".txt,text/plain", hidden: true, onchange: async () => {
      const f = file.files[0];
      file.value = "";
      if (f) area.value = await f.text();
    } });
    async function send(dry) {
      if (!area.value.trim()) { toast("Collez ou chargez d'abord un script.", "error"); return; }
      try {
        const res = await api.post("/api/admin/access-rules", { text: area.value, dry_run: dry });
        clear(out);
        out.append(reportView(res));
        if (!dry) toast("Règles d'accès appliquées.", "success");
      } catch (err) { toast(err.message, "error"); }
    }
    body.append(
      el("p", { class: "muted rules-intro" }, "Utilisateurs, fonction, expertise, « quand leur adresser une question » "
        + "et droits par Space, en texte lisible (et modifiable par un agent IA). Les Spaces eux-mêmes et les mots de "
        + "passe n'en font pas partie. L'import crée ou met à jour, ne supprime jamais un compte ; « aucun » retire un droit."),
      el("div", { class: "rules-actions" },
        el("button", { type: "button", class: "btn", onclick: () => download("/api/admin/access-rules") }, "Exporter (.txt)"),
        el("button", { type: "button", class: "btn", onclick: async () => {
          try { area.value = (await api.get("/api/admin/access-rules/default")).text; toast("Équipe d'exemple chargée : vérifiez puis appliquez.", "success"); }
          catch (err) { toast(err.message, "error"); }
        } }, "Charger la base d'exemple"),
        el("button", { type: "button", class: "btn", onclick: () => file.click() }, "Ouvrir un fichier…"), file),
      area,
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => send(true) }, "Vérifier (rien n'est écrit)"),
        el("button", { type: "button", class: "btn btn-primary", onclick: () => send(false) }, "Appliquer")),
      out);
  }

  DA.adminRules = { render };
})();
