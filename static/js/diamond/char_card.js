/* Diamond · the card of a characteristic C-n (0.60.102, D-O-110), #/diamond/KEY/chars/C-14 -- a page, not a dialog (it
   is taller than a dialog may be). Read: function, DFMEA line (S, O, AP), Diamond part and the second part of an interface,
   company PN (next increment), drawing (sheet, zone, datum), the dimension, the required Cpk and where it comes from, the
   key test. Edit (editors): every field; the specification as a nominal and its tolerance, or as limits LSL / USL. */
(function () {
  "use strict";

  const { el } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const num = (x, d) => (x == null ? "" : Number(x).toFixed(Math.max(0, d || 0)).replace(".", ","));

  function card(holder, state, code) {
    const ctx = state.ctx, d = state.data;
    const c = d.items.find((x) => x.code === code) || d.archived.find((x) => x.code === code);
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("a", { href: A.href(ctx, "chars") }, "Caractéristiques"), el("span", null, code)]));
    if (!c) {
      holder.append(el("p", { class: "form-error" }, code + " introuvable dans ce Space."), el("a", { class: "btn", href: A.href(ctx, "chars") + "/all" }, "← Toutes les caractéristiques"));
      return;
    }
    const f = c.dfmea;
    const rows = [
      ["Fonction", f && f.function_number ? "F" + f.function_number + " " + f.function_text : "—"],
      ["DFMEA", f ? el("a", { href: A.href(ctx, "dfmea") }, "ligne " + f.line + " · S " + (f.severity || "—") + " · O " + (f.occurrence || "—") + " · AP " + (f.ap || "—")) : "aucune ligne"],
      ["Pièce Diamond", c.part ? c.part + " " + (c.part_name || "") : el("span", { class: "dm-ch-miss" }, "à préciser")],
      ["Interface", c.part2 ? c.part + " ↔ " + c.part2 + " " + (c.part2_name || "") : "—"],
      ["# entreprise", (c.pns || []).length ? el("span", { class: "dm-ch-spec" }, c.pns.join(" · "))  // 0.60.103 (D-O-112)
        : el("a", { href: A.href(ctx, "chars") + "/pn" }, "aucun # relié : # de pièce de l'entreprise")],
      ["Plan de la pièce", [c.drawing, c.sheet ? "feuille " + c.sheet : "", c.zone ? "zone " + c.zone : "", c.datum ? "datum " + c.datum : ""].filter(Boolean).join(" · ") || el("span", { class: "dm-ch-miss" }, "à préciser")],
      ["Cote", c.spec ? el("strong", { class: "dm-ch-spec" }, c.spec) : el("span", { class: "dm-ch-miss" }, "à écrire")],
      ["Cpk exigé", c.control === "test100" ? "100 % (essai 100 %)" : c.cpk_req == null ? "—" : num(c.cpk_req, 2)
        + (c.cpk_required != null ? " (propre à " + c.code + ")" : " (client, classe " + c.class_code + ")")],
      ["Essai", c.test_code ? el("a", { href: "#/testing/" + ctx.key }, c.test_code + " " + (c.test_title || "")) : "—"],
      ["Contrôle", d.labels.controls[c.control] || c.control], ["Status", D.charStatus(c)]];
    holder.append(el("section", { class: "dm-ch-card", "data-new": "0.60.102-char-card" },
      el("h1", null, D.charChip(c), " " + c.code + " · " + c.label, c.archived ? el("span", { class: "badge badge-off" }, " retirée") : null),
      el("dl", { class: "dm-ch-dl" }, rows.flatMap(([k, v]) => [el("dt", null, k), el("dd", null, v)])),
      c.spec_text && c.spec ? el("p", { class: "muted" }, c.spec_text) : null, c.notes ? el("p", { class: "dm-ch-notes" }, c.notes) : null));
    if (state.editable) holder.append(form(state, c));
    holder.append(el("div", { class: "dm-actions" }, el("a", { class: "btn", href: A.href(ctx, "chars") }, "← Sommaire"),
      el("a", { class: "btn", href: A.href(ctx, "chars") + "/all" }, "Toutes les caractéristiques")));
  }

  function select(options, value, label) {
    return el("select", { "aria-label": label }, options.map(([v, text]) => el("option", { value: v, selected: String(value == null ? "" : value) === String(v) }, text)));
  }

  function form(state, c) {
    const d = state.data, o = d.options;
    const input = (k, attrs) => el("input", Object.assign({ type: "text", value: c[k] == null ? "" : c[k], "aria-label": k }, attrs || {}));
    const f = {
      label: input("label", { maxlength: 160 }), nature: select(Object.entries(d.labels.natures), c.nature, "Nature"),
      dfmea_id: select([["", "— aucune ligne —"]].concat(o.dfmea.map((r) => [r.id, "L" + r.line + (r.class_code ? " · " + r.class_code : "")
        + (r.function_number ? " · F" + r.function_number : "") + " · " + (r.failure_mode || "").slice(0, 60)])), c.dfmea_id, "Ligne du DFMEA"),
      part_id: select([["", "— pièce —"]].concat(o.parts.map((p) => [p.id, "P-" + p.number + " " + p.name])), c.part_id, "Pièce"),
      part2_id: select([["", "— aucune —"]].concat(o.parts.map((p) => [p.id, "P-" + p.number + " " + p.name])), c.part2_id, "Seconde pièce"),
      prefix: input("prefix", { maxlength: 4, class: "dm-ch-short", placeholder: "R, Ø" }), unit: input("unit", { maxlength: 16, class: "dm-ch-short", placeholder: "mm" }),
      nominal: input("nominal", { value: num(c.nominal, c.decimals), class: "dm-ch-short" }),
      tol_plus: input("tol_plus", { value: c.nominal != null && c.usl != null ? num(c.usl - c.nominal, c.decimals) : "", class: "dm-ch-short" }),
      tol_minus: input("tol_minus", { value: c.nominal != null && c.lsl != null ? num(c.nominal - c.lsl, c.decimals) : "", class: "dm-ch-short" }),
      lsl: input("lsl", { value: num(c.lsl, c.decimals), class: "dm-ch-short" }), usl: input("usl", { value: num(c.usl, c.decimals), class: "dm-ch-short" }),
      spec_text: input("spec_text", { maxlength: 400 }), drawing: input("drawing", { maxlength: 80, placeholder: "RVR-3140-02 rév. C" }),
      sheet: input("sheet", { maxlength: 16, class: "dm-ch-short" }), zone: input("zone", { maxlength: 16, class: "dm-ch-short" }), datum: input("datum", { maxlength: 40 }),
      control: select(Object.entries(d.labels.controls), c.control, "Contrôle"),
      cpk_required: input("cpk_required", { value: c.cpk_required == null ? "" : num(c.cpk_required, 2), class: "dm-ch-short", placeholder: c.cpk_req != null ? num(c.cpk_req, 2) : "" }),
      test_id: select([["", "— essai —"]].concat(o.tests.map((t) => [t.id, t.code + " · " + t.title])), c.test_id, "Essai"),
      notes: el("textarea", { rows: 3, maxlength: 2000, "aria-label": "Notes" }, c.notes || ""),
    };
    const limitsMode = c.nominal == null && (c.lsl != null || c.usl != null);
    const mode = select([["tol", "Nominal et tolérance"], ["limits", "Limites LSL / USL"]], limitsMode ? "limits" : "tol", "Forme de la spécification");
    const tolBox = el("div", { class: "dm-ch-row-f" }, DA.field("Tolérance +", f.tol_plus), DA.field("Tolérance −", f.tol_minus));
    const limBox = el("div", { class: "dm-ch-row-f" }, DA.field("LSL", f.lsl), DA.field("USL", f.usl));
    const show = () => { tolBox.hidden = mode.value !== "tol"; limBox.hidden = mode.value !== "limits"; };
    mode.addEventListener("change", show);
    show();
    const save = async () => {
      const body = {};
      ["label", "nature", "dfmea_id", "part_id", "part2_id", "prefix", "unit", "spec_text", "drawing", "sheet", "zone", "datum", "control", "cpk_required", "test_id"]
        .forEach((k) => { body[k] = f[k].value; });
      body.notes = f.notes.value;
      if (mode.value === "tol") Object.assign(body, { nominal: f.nominal.value, tol_plus: f.tol_plus.value, tol_minus: f.tol_minus.value });
      else Object.assign(body, { nominal: f.nominal.value, lsl: f.lsl.value, usl: f.usl.value });
      await state.send("patch", "/" + c.id, body, c.code + " enregistrée.");
    };
    const archive = () => {
      if (c.archived) { state.send("post", "/" + c.id + "/archive", { archived: false }, c.code + " rétablie."); return; }
      if (window.confirm("Retirer " + c.code + " ? Elle sort du sommaire ; son numéro n'est jamais redonné. L'action est journalisée.")) {
        state.send("post", "/" + c.id + "/archive", { archived: true }, c.code + " retirée.");
      }
    };
    return el("section", { class: "dm-ch-form", "data-new": "0.60.102-char-form" }, el("h2", null, "Modifier " + c.code),
      el("div", { class: "dm-ch-grid" },
        el("fieldset", null, el("legend", null, "Ce qu'elle est"), DA.field("Characteristic", f.label), DA.field("Nature", f.nature),
          DA.field("Ligne du DFMEA (la classe vient d'elle)", f.dfmea_id)),
        el("fieldset", null, el("legend", null, "Specification"), DA.field("Forme", mode),
          DA.field("Nominal", f.nominal, "Facultatif avec des limites ; une seule limite donne une caractéristique unilatérale."), tolBox, limBox,
          el("div", { class: "dm-ch-row-f" }, DA.field("Unité", f.unit), DA.field("Préfixe", f.prefix)),
          DA.field("Texte de spécification", f.spec_text, "Pour un attribut sans nombre, ou une précision (« par élément »)")),
        el("fieldset", null, el("legend", null, "Pièce et plan"), DA.field("Pièce qui porte la cote", f.part_id),
          DA.field("Seconde pièce (interface)", f.part2_id, "La cote se porte sur la pièce qui la fixe ; l'autre est citée."),
          DA.field("Plan de la pièce", f.drawing), el("div", { class: "dm-ch-row-f" }, DA.field("Feuille", f.sheet), DA.field("Zone", f.zone), DA.field("Datum", f.datum))),
        el("fieldset", null, el("legend", null, "Contrôle"), DA.field("Comment elle est tenue", f.control),
          DA.field("Cpk exigé", f.cpk_required, "Vide : la valeur du client pour sa classe (1,67 CC, 1,33 SC au départ)"),
          DA.field("Essai de la Test Base", f.test_id), DA.field("Notes", f.notes))),
      el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: save }, "Enregistrer"),
        el("button", { type: "button", class: "btn", onclick: archive }, c.archived ? "Rétablir" : "Retirer…")));
  }

  DA.diamond = Object.assign(DA.diamond || {}, { charCard: card });
})();
