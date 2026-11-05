/* « Testing » -- central lists (D-B-082), #/testing/lists: test equipment, test locations, product functions (F-XX).
   Everyone reads them; only an Admin du Space TESTING or an administrator adds, renames or deactivates an entry
   (a used entry is never deleted: deactivated, it stays where it is used and is no longer offered). The product
   functions are published in the « Base de connaissances (BDC) » (Dynamite page regenerated from this list).
   D-A-037: acronyms and definitions of the platform, same rules; published as the BDC pages Definitions, Acronyms and
   « Traduction des termes techniques (EN → FR) », and inserted in the Word exports of Goldmine and Testing. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const T = (DA.testing = DA.testing || {});
  const HINT = { equipment: "EQ- + 2 à 12 lettres ou chiffres (ex. EQ-VIB2)", location: "2 à 12 lettres / chiffres (ex. LAB)",
    function: "F + 1 à 3 chiffres, sous-fonction permise (ex. F12, F35.1)",
    acronym: "1 à 16 caractères sans espace, casse gardée (ex. RoHS, CdCF)",
    definition: "Terme anglais, 2 à 80 caractères (ex. Functional Tree)" };
  const GLOSSARY = ["acronym", "definition"];
  const NOUN = { equipment: "équipement", location: "test location", function: "fonction", acronym: "acronym",
    definition: "definition" };

  function editDialog(kind, item, reload) {
    const d = (item && item.details) || {};
    const f = {
      code: el("input", { type: "text", maxlength: 16, value: item ? item.code : "", disabled: !!item, placeholder: HINT[kind] }),
      label: el("input", { type: "text", maxlength: 160, value: item ? item.label : "" }),
      category: el("input", { type: "text", maxlength: 80, value: item ? item.category : "" }),
      primary: el("input", { type: "text", maxlength: 400, value: d.primary || "" }),
      supporting: el("input", { type: "text", maxlength: 400, value: d.supporting || "" }),
      notes: el("input", { type: "text", maxlength: 400, value: d.notes || "" }),
      fr: el("input", { type: "text", maxlength: 400, value: d.fr || "" }),
      source: el("input", { type: "text", maxlength: 400, value: d.source || "", placeholder: "ex. IEC 60335-1, ISO 12100, équipe" }),
      std_term: el("input", { type: "text", maxlength: 400, value: d.std_term || "" }),
      std_def: el("input", { type: "text", maxlength: 400, value: d.std_def || "" }),
    };
    if (kind === "definition") {
      f.label = el("textarea", { rows: 4, maxlength: 600 });
      f.label.value = item ? item.label : "";
    }
    const glossary = GLOSSARY.includes(kind);
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      const body = { kind, code: f.code.value, label: f.label.value, category: f.category.value,
        details: glossary ? { fr: f.fr.value, source: f.source.value, std_term: f.std_term.value, std_def: f.std_def.value }
          : { primary: f.primary.value, supporting: f.supporting.value, notes: f.notes.value } };
      try {
        if (item) await api.patch("/api/testing/lists/" + item.id, body); else await api.post("/api/testing/lists", body);
        close();
        toast(item ? "Entrée modifiée." : "Entrée ajoutée.", "success");
        reload();
      } catch (err) { error.textContent = err.message; }
    } }, el("div", { class: "form-row" }, field(kind === "acronym" ? "Acronym" : kind === "definition" ? "Term" : "Code", f.code,
      item ? "Ne change jamais (traçabilité) ; désactivez et ajoutez-en un autre au besoin" : HINT[kind]),
      field(kind === "function" ? "Function Name" : glossary ? "Definition" : "Libellé", f.label,
        glossary ? "En anglais (D-B-085)" : null)),
    kind === "equipment" ? field("Category", f.category) : null,
    glossary ? el("div", { class: "form-row" }, field("Domain", f.category, "ex. Conception de produit, Conformité grand public"),
      field("Équivalent FR", f.fr, "Pour la page de traduction")) : null,
    kind === "definition" ? [field("Source", f.source), el("div", { class: "form-row" }, field("Standard Term", f.std_term,
      "Seulement si ce terme de l'équipe remplace le terme d'une norme citée (table de nomenclature)"), field("Standard Definition", f.std_def))] : null,
    kind === "function" ? [field("Primary Component(s)", f.primary), field("Supporting Component(s)", f.supporting),
      field("Notes d'implémentation", f.notes)] : null, error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, item ? "Enregistrer" : "Ajouter")));
    close = modal((item ? "Modifier " : "Ajouter à la liste : ") + NOUN[kind], form);
  }

  T.listsView = async function (main) {
    const data = await api.get("/api/testing/lists");
    const reload = () => { clear(main); T.listsView(main); };
    const pages = Object.entries(data.glossary_pages || {}).map(([title, href]) => el("a", { class: "btn btn-small", href }, title));
    main.append(el("nav", { class: "tg-crumbs" }, el("a", { href: T.href("") }, "Testing"), " › Listes centrales"),
      T.head("Listes centrales", "Equipment, test locations et fonctions du produit : les tests et les requirements les choisissent "
        + "dans ces listes, jamais en texte libre. Acronyms et definitions : publiés dans la BDC et insérés automatiquement "
        + "dans les exports Word de Goldmine et Testing." + (data.can_manage ? "" : " Modification réservée aux Admin du Space "
        + "de référence (HeadLamp) et aux administrateurs."), [data.bdc_href ? el("a", { class: "btn btn-small", href: data.bdc_href },
        "Page BDC des fonctions") : null].concat(pages)));
    Object.entries(data.kinds).forEach(([kind, label]) => {
      const items = data.items.filter((x) => x.kind === kind);
      const glossary = GLOSSARY.includes(kind);
      const head = kind === "acronym" ? ["Acronym", "Definition", "Domain", "Équivalent FR", "État", ""]
        : kind === "definition" ? ["Term", "Definition", "Domain", "Source", "Équivalent FR", "État", ""]
        : kind === "function" ? ["Code", "Function", "Primary Component(s)", "Supporting Component(s)", "Notes", "Utilisée", "État", ""]
        : kind === "equipment" ? ["Code", "Test Equipment", "Category", "Utilisé", "État", ""] : ["Code", "Test Location", "Utilisé", "État", ""];
      const filter = glossary ? el("input", { type: "search", class: "tg-filter", placeholder: "Filtrer les " + label.toLowerCase() + "s…",
        "aria-label": "Filtrer les " + label.toLowerCase() + "s", oninput: () => {
          const q = filter.value.trim().toLowerCase();
          section.querySelectorAll("tbody tr").forEach((tr) => { tr.hidden = !!q && !tr.textContent.toLowerCase().includes(q); });
        } }) : null;
      const section = el("section", { class: "tg-group" }, el("div", { class: "tg-group-head" },
        el("h2", null,
          label === "Test Equipment" ? label : label + "s", el("span", { class: "muted tg-n" }, " · " + items.filter((x) => x.active).length + " actif(s)")),
        filter, data.can_manage ? el("button", { type: "button", class: "btn btn-small", onclick: () => editDialog(kind, null, reload) }, "+ Ajouter") : null),
      DA.table(head, items.map((x) => el("tr", { class: x.active ? null : "tg-obsolete" },
        el("td", { class: "nowrap" }, el("strong", null, x.code)), el("td", null, x.label),
        kind === "equipment" ? el("td", null, x.category) : null,
        kind === "function" ? [el("td", null, x.details.primary || ""), el("td", null, x.details.supporting || ""),
          el("td", null, x.details.notes || "")] : null,
        glossary ? el("td", null, x.category) : null,
        kind === "definition" ? el("td", null, x.details.source || "") : null,
        glossary ? el("td", null, x.details.fr || "") : el("td", { class: "tg-num" }, String(x.used)),
        el("td", null, x.active ? DA.badge("Active", "ok") : DA.badge("Désactivée", "neutral")),
        el("td", { class: "nowrap" }, data.can_manage ? [
          el("button", { type: "button", class: "link-btn", onclick: () => editDialog(kind, x, reload) }, "Modifier"), " ",
          el("button", { type: "button", class: "link-btn", onclick: async () => {
            try { await api.patch("/api/testing/lists/" + x.id, { active: !x.active }); reload(); }
            catch (err) { toast(err.message, "error"); }
          } }, x.active ? "Désactiver" : "Réactiver")] : null)))));
      main.append(section);
    });
  };
})();
