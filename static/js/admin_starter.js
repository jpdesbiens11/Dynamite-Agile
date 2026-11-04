/* Dynamite | Agile - Admin → Spaces → « Commencer » (0.60.07, D-O-019): a Project Starter file becomes a new Space.
   1. choose the .json file the AI assistant gave (or an example); 2. preview what will be created, adjust the Space key
   and the time codes, see what blocks; 3. create, in one transaction, and read the temporary passwords once. */
(function () {
  "use strict";

  const { api, el, clear, field, badge, table, toast } = DA;
  const ROLES = { manager: "Admin du Space", editor: "Éditeur", reader: "Lecteur" };
  const COUNTS = [["team", "Membres de l'équipe"], ["needs", "Besoins (Needs)"], ["requirements", "Requirements"],
    ["tests", "Essais (Test Base)"], ["time_codes", "Codes de temps"], ["pages", "Pages Dynamite"],
    ["plan_weeks", "Exploration : plan de référence du PDP (semaines)"], ["diamond_functions", "Diamond : fonctions de l'arbre"], ["diamond_flows", "Diamond : flux de la structure"],
    ["diamond_parts", "Diamond : pièces"], ["diamond_risks", "Diamond : risques projet"], ["diamond_dfmea", "Diamond : lignes du DFMEA"]];

  async function render(body) {
    const examples = (await api.get("/api/starter/examples")).examples;
    const state = { text: "", key: "", renames: {}, drop: new Set() };
    const out = el("div", { "data-new": "0.60.07-starter-preview" });
    const fileInput = el("input", { type: "file", accept: ".json,application/json", "aria-label": "Fichier Project Starter" });
    const example = el("select", { "aria-label": "Exemple" }, el("option", { value: "" }, "— Choisir un exemple —"),
      examples.map((x) => el("option", { value: x.id }, x.name)));

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      if (file.size > 1536 * 1024) { show(out, error("Fichier de plus de 1,5 Mo. Correctif : demandez à l'assistant un fichier plus court.")); return; }
      start(await file.text());
    });
    example.addEventListener("change", () => {
      const x = examples.find((e) => e.id === example.value);
      if (x) start(x.text);
    });

    function start(text) {
      Object.assign(state, { text, key: "", renames: {}, drop: new Set() });
      check();
    }

    function payload() {
      return { file: state.text, key: state.key || null, renames: state.renames, drop: Array.from(state.drop) };
    }

    async function check() {
      show(out, el("p", { class: "muted" }, "Vérification du fichier…"));
      try {
        const data = await api.post("/api/starter/check", payload());
        if (!state.key) state.key = data.summary.key;
        show(out, preview(data, state, check, create));
      } catch (err) {
        show(out, error(err.message));
      }
    }

    async function create(button) {
      button.disabled = true;
      try {
        const result = await api.post("/api/starter/apply", payload());
        toast("Space " + result.project.key + " créé.", "success");
        fileInput.value = "";
        example.value = "";
        show(out, done(result));
      } catch (err) {
        button.disabled = false;
        toast(err.message, "error");
      }
    }

    body.append(
      el("h2", null, "Commencer un projet"),
      el("p", { class: "muted" }, "Un assistant IA (Claude ou un autre) vous pose des questions sur votre produit, votre "
        + "industrie et votre marché, puis vous donne un fichier .json. Ce fichier crée ici un nouveau Space, à côté des "
        + "exemples : l'équipe, les besoins et requirements, les essais, les codes de temps et les premières pages."),
      promptBox(),
      el("h3", null, "2. Déposer le fichier"),
      el("div", { class: "form-row", "data-new": "0.60.07-starter" },
        field("Fichier Project Starter (.json)", fileInput, "Rien n'est créé avant votre confirmation."),
        field("Ou essayer avec un exemple", example)),
      out);
  }

  /* 0.60.18: step 1 spelled out for a beginner -- the prompt is served by the tool itself, so it works offline too. */
  function promptBox() {
    async function copy(lang) {
      try {
        const data = await api.get("/api/starter/prompt?lang=" + lang);
        await navigator.clipboard.writeText(data.text);
        toast("Prompt copié : collez-le dans une nouvelle conversation avec l'assistant IA.", "success");
      } catch (err) {
        toast("Copie impossible ici. Correctif : utilisez « Télécharger », puis copiez le texte du fichier.", "error");
      }
    }
    return el("div", { class: "panel starter-prompt", "data-new": "0.60.18-starter-prompt" },
      el("h3", null, "1. Préparer le fichier avec un assistant IA"),
      el("ol", null,
        el("li", null, "Copiez le prompt (bouton ci-dessous)."),
        el("li", null, "Ouvrez une nouvelle conversation avec Claude.ai, ChatGPT, Gemini ou Copilot, collez le prompt et envoyez-le."),
        el("li", null, "Répondez aux questions, une à la fois : environ 26, de 45 à 60 minutes. « Je ne sais pas » est une "
          + "bonne réponse : l'assistant proposera un choix raisonnable. Ne lui donnez jamais de mot de passe."),
        el("li", null, "Enregistrez le fichier .json qu'il vous donne, puis déposez-le à l'étape 2.")),
      el("div", { class: "actions" },
        el("button", { type: "button", class: "btn btn-primary", onclick: () => copy("fr") }, "Copier le prompt"),
        el("a", { class: "btn", href: "/api/starter/prompt?lang=fr&download=1", download: "" }, "Télécharger (.md)"),
        el("button", { type: "button", class: "btn", onclick: () => copy("en") }, "Copy the English prompt")),
      el("p", { class: "muted" }, "Le prompt contient les questions, les règles de l'entrevue et le format exact du fichier, "
        + "avec les valeurs que l'outil accepte."));
  }

  function show(out, node) { clear(out); out.append(node); }

  /* Rebuild after the change event has finished: removing the focused input inside its own handler breaks its blur. */
  function later(fn) { setTimeout(fn, 0); }

  function error(message) { return el("p", { class: "form-error", role: "alert" }, message); }

  function preview(data, state, recheck, create) {
    const s = data.summary;
    const blockedCodes = new Set(data.blocking.filter((b) => b.what === "code").map((b) => b.value));
    const keyBlocked = data.blocking.some((b) => b.what === "key");
    const warnings = data.warnings.filter((w) => !(s.standards.length && w.indexOf("« À vérifier »") >= 0));  // own section below
    const keyInput = el("input", { type: "text", class: "starter-key", value: state.key, maxlength: 10, "aria-label": "Clé du Space", "aria-invalid": keyBlocked ? "true" : null });
    keyInput.addEventListener("change", () => { state.key = keyInput.value.trim().toUpperCase(); later(recheck); });
    const createBtn = el("button", { type: "button", class: "btn btn-primary", disabled: !data.ready,
      onclick: (ev) => create(ev.currentTarget) }, "Créer le Space " + s.key);
    return el("div", null,
      el("h2", null, s.project),
      el("div", { class: "form-row" }, field("Clé du Space", keyInput, "2 à 10 majuscules ou chiffres ; elle préfixe les tickets (" + s.key + "-1…).")),
      table(["Ce qui sera créé", "Nombre"], COUNTS.map(([k, label]) => el("tr", null, el("td", null, label), el("td", null, String(s[k] || 0))))),
      data.blocking.length ? el("div", { role: "alert" }, el("h3", null, "À régler avant de créer"),
        el("ul", null, data.blocking.map((b) => el("li", null, badge("Bloquant", "danger"), " ", b.message, " Correctif : " + b.fix)))) : null,
      warnings.length ? el("div", null, el("h3", null, "À savoir"),
        el("ul", null, warnings.map((w) => el("li", null, badge("Attention", "warn"), " ", w)))) : null,
      s.standards.length ? el("div", null, el("h3", null, "Normes nommées par l'assistant"),
        el("p", { class: "muted" }, "Chacune arrive « À vérifier » : un requirement ne passe à « Accepted », un essai à « Approved », "
          + "qu'après confirmation de l'édition en vigueur et de la clause."),
        el("ul", null, s.standards.map((n) => el("li", null, badge("À vérifier", "warn"), " ", n)))) : null,
      teamTable(data.team),
      codesTable(data.codes, blockedCodes, state, recheck),
      details("Requirements et besoins", data.requirements.map((r) => [r.ref, r.kind === "need" ? "Need" : "Requirement", r.statement, r.standard || "—"]),
        ["Réf.", "Kind", "Statement", "Norme"]),
      details("Essais", data.tests.map((t) => [t.ref, t.title, t.standard || "—"]), ["Réf.", "Titre", "Norme"]),
      details("Pages Dynamite (Brouillon IA)", data.pages.map((p) => [p.ref, p.title, p.parent || "(accueil)"]), ["Réf.", "Titre", "Sous"]),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: recheck }, "Revérifier"), createBtn));
  }

  function teamTable(team) {
    if (!team.length) return el("p", { class: "muted" }, "Aucun membre dans le fichier : vous ajouterez l'équipe dans Comptes.");
    return el("div", null, el("h3", null, "Équipe"),
      el("p", { class: "muted" }, "Chaque nouveau compte reçoit un mot de passe temporaire, affiché une seule fois après la "
        + "création. Aucun n'est administrateur ; un compte existant est réutilisé tel quel."),
      table(["Identifiant", "Nom", "Profil d'études", "Rôle dans le Space", ""], team.map((m) => el("tr", null,
        el("td", null, el("code", null, m.username)), el("td", null, m.display_name), el("td", null, m.study_profile || "—"),
        el("td", null, ROLES[m.role] || m.role), el("td", null, m.exists ? badge("Existant", "neutral") : badge("Nouveau", "ok"))))));
  }

  function codesTable(codes, blocked, state, recheck) {
    const all = codes.concat(Array.from(state.drop).map((key) => ({ key, from: key, label: "", dropped: true })));
    if (!all.length) return el("p", { class: "muted" }, "Aucun code de temps : le Space utilisera les codes du PDP (A-01 … D-21).");
    return el("div", null, el("h3", null, "Codes de temps (Timesheet)"),
      el("p", { class: "muted" }, "Un code est unique sur tout le site : renommez celui qui est déjà pris, ou retirez-le."),
      table(["Code", "Libellé", "Garder", ""], all.map((c) => {
        const input = el("input", { type: "text", class: "starter-code", value: c.key, maxlength: 10, disabled: c.dropped, "aria-label": "Code " + c.from });
        input.addEventListener("change", () => {
          const value = input.value.trim().toUpperCase();
          if (value === c.from) delete state.renames[c.from]; else state.renames[c.from] = value;
          later(recheck);
        });
        const keep = el("input", { type: "checkbox", checked: !c.dropped, "aria-label": "Garder " + c.from });
        keep.addEventListener("change", () => {
          if (keep.checked) state.drop.delete(c.from); else { state.drop.add(c.from); delete state.renames[c.from]; }
          later(recheck);
        });
        return el("tr", null, el("td", null, input), el("td", null, c.label || "(retiré)"), el("td", null, keep),
          el("td", null, blocked.has(c.key) ? badge("Déjà pris", "danger") : c.dropped ? badge("Retiré", "off") : badge("OK", "ok")));
      })));
  }

  function details(title, rows, headers) {
    if (!rows.length) return null;
    return el("details", null, el("summary", null, title + " (" + rows.length + ")"),
      table(headers, rows.map((r) => el("tr", null, r.map((cell) => el("td", null, cell))))));
  }

  function done(result) {
    const key = result.project.key;
    const lines = result.accounts.map((a) => a.username + " : " + a.temp_password).join("\n");
    const copy = el("button", { type: "button", class: "btn", onclick: async () => {
      try { await navigator.clipboard.writeText(lines); toast("Mots de passe copiés.", "success"); }
      catch (err) { toast("Copie automatique indisponible : sélectionnez le texte.", "error"); }
    } }, "Copier les mots de passe");
    return el("div", { "data-new": "0.60.07-starter-done" },
      el("h2", null, "Space " + key + " créé"),
      el("p", null, result.counts.requirements + " requirements et besoins, " + result.counts.tests + " essais, "
        + result.counts.time_codes + " codes de temps, " + result.counts.pages + " pages"
        + (result.counts.diamond_functions ? " ; Diamond : " + result.counts.diamond_functions + " fonctions, " + result.counts.diamond_flows
          + " flux, " + result.counts.diamond_parts + " pièces, " + result.counts.diamond_risks + " risques, " + result.counts.diamond_dfmea
          + " lignes de DFMEA." : ".")),
      result.accounts.length ? el("div", null, el("h3", null, "Mots de passe temporaires"),
        el("p", { class: "muted" }, "Affichés une seule fois. Transmettez-les de vive voix ou par un canal sûr ; chaque "
          + "personne choisit le sien à sa première connexion."),
        table(["Identifiant", "Nom", "Mot de passe temporaire"], result.accounts.map((a) => el("tr", null,
          el("td", null, el("code", null, a.username)), el("td", null, a.display_name), el("td", null, el("span", { class: "temp-password" }, a.temp_password))))),
        el("div", { class: "form-actions" }, copy)) : null,
      result.reused.length ? el("p", { class: "muted" }, "Comptes existants ajoutés au Space : " + result.reused.join(", ") + ".") : null,
      result.placeholder_for.length ? el("p", null, badge("À faire", "warn"), " Requirements sans essai, liés à « Essai à définir » : "
        + result.placeholder_for.join(", ") + ".") : null,
      el("div", { class: "form-actions" },
        el("a", { class: "btn", href: "#/dynamite/" + key }, "Wiki Dynamite"),
        el("a", { class: "btn", href: "#/testing/" + key }, "Testing"),
        el("a", { class: "btn", href: "#/diamond/" + key + "/ftree", "data-new": "0.60.22-starter-diamond" }, "Diamond"),
        el("a", { class: "btn", href: "#/exploration/" + key + "/plan" }, "Plan (Gantt)"),
        el("a", { class: "btn btn-primary", href: "#/goldmine/" + key }, "Ouvrir Goldmine")));
  }

  DA.adminStarter = { render };
})();
