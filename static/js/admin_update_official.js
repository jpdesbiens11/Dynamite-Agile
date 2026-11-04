/* Admin → Update → Framework: « Versions officielles » (0.60.12, D-O-024). The server never calls the Internet: this
   block links to the project's « Mises à jour » page with the installed version (#depuis=0.60.xx), where the page shows
   the newer versions and the package to download; the package is then checked here like any update zip, with one
   review step per version it brings, its SHA-256 to compare with the page, the files edited by hand that it replaces,
   and « Plus tard » to leave everything as it is. */
(function () {
  "use strict";
  const { api, el, toast } = DA;

  function block(s) {
    const r = s.release || {};
    const lang = DA.lang ? DA.lang() : "fr";
    const page = (r.pages && (r.pages[lang] || r.pages.fr)) || "";
    return el("section", { class: "up-step up-official", "data-new": "0.60.12-official" },
      el("h2", null, "Versions officielles"),
      el("p", null, "Version installée : ", el("strong", null, s.version), ". Les versions publiées par le projet se téléchargent sur "
        + "son site : la page montre celles qui sont plus récentes que la vôtre. Le serveur, lui, ne va jamais sur Internet."),
      el("ol", { class: "up-official-steps" },
        el("li", null, "Ouvrez la page des versions et téléchargez le paquet de la dernière version (un seul fichier, même si "
          + "vous sautez plusieurs versions)."),
        el("li", null, "Déposez-le ci-dessous avec « Vérifier un zip de mise à jour… » : une étape de revue par version, puis "
          + "« Appliquer », ou « Plus tard »."),
        el("li", null, "Vos données, vos comptes, vos Spaces et les réglages de la plateforme ne changent pas ; le code d'avant "
          + "reste disponible (« Revenir à la … »).")),
      page ? el("a", { class: "btn btn-primary", href: page, target: "_blank", rel: "noopener" }, "Voir les versions publiées ↗") : null,
      r.git ? el("p", { class: "muted up-git" }, "Ce portail a été installé avec git (commande d'installation). Relancer la même "
        + "commande donne le même résultat ; un paquet appliqué ici ne la bloque pas.") : null);
  }

  /* lines added to the technical report of a checked zip */
  function report(r) {
    const out = [];
    if (r.official) {
      out.push(el("p", { class: "up-ok" }, "✓ Paquet officiel " + r.official.version + " (" + r.official.date + ") : ses "
        + r.official.files + " fichiers sont ceux du paquet publié."));
    }
    if (r.sha256) {
      out.push(el("p", { class: "muted up-sha" }, "Empreinte SHA-256 : ", el("code", null, r.sha256),
        " — elle doit être identique à celle de la page des versions."));
    }
    if (r.series && r.series.length) {
      out.push(el("details", { open: true }, el("summary", null, "Versions apportées (" + r.series.length + ")"),
        el("ul", null, r.series.map((v) => el("li", null, el("strong", null, v.version), " · " + v.date + " — "
          + ((v.summary && (v.summary[DA.lang ? DA.lang() : "fr"] || v.summary.fr)) || ""))))));
    }
    if (r.local && r.local.count) {
      out.push(el("div", { class: "ag-import-advice up-local" }, el("strong", null, r.local.count
        + " fichier(s) modifié(s) à la main sur ce serveur seront remplacés :"),
      el("ul", null, r.local.sample.map((f) => el("li", null, f))),
      el("p", { class: "muted" }, "La copie du code d'avant la mise à jour est gardée : vous pourrez y reprendre vos modifications.")));
    }
    return out;
  }

  function later(r, done) {
    return el("button", { type: "button", class: "btn", "data-new": "0.60.12-later", onclick: async () => {
      try {
        await api.post("/api/update/later", { token: r.token });
        toast("Rien n'a changé. Vous pourrez appliquer cette version, ou une plus récente, plus tard.", "success");
        done();
      } catch (err) { toast(err.message, "error"); }
    } }, "Plus tard");
  }

  DA.adminUpdateOfficial = { block, report, later };
})();
