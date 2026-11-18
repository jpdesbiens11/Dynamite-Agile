/* Diamond · profiles of the competency grid (0.60.119, D-O-132): « Profil de grille ▾ » under the tree and at the top of
   « Compétences et équipe ». A profile replaces the columns of the grid of the Space in one go (mechatronics, electronics and
   power, embedded software…); before it does, the page says how many ratings of the columns that leave are erased. */
(function () {
  "use strict";

  const { el } = DA;
  const D = DA.diamond;

  /* comp: the payload of /competencies; onPick(key): applies the profile (after the confirmation) */
  function profilePicker(comp, onPick) {
    const names = Object.fromEntries(comp.catalog.map((c) => [c.code, c.name]));
    const current = (comp.profiles || []).find((p) => p.current);
    const pick = el("select", { class: "dm-cg-profile", "aria-label": "Profil de grille", "data-new": "0.60.119-competency-profile",
      "data-tip": "Remplacer les colonnes de la grille par celles d'un profil" },
    el("option", { value: "" }, current ? "Profil : " + current.name : "Profil de grille…"),
    (comp.profiles || []).filter((p) => p.codes.length).map((p) => el("option", { value: p.key, disabled: p.current ? "disabled" : null },
      p.name + " — " + p.codes.join(", "))));
    pick.addEventListener("change", () => {
      const p = comp.profiles.find((x) => x.key === pick.value);
      if (!p) return;
      const keep = new Set(p.codes);
      const lost = comp.lines.reduce((n, ln) => n + Object.keys(ln.ratings).filter((c) => !keep.has(c)).length, 0);
      const leaving = [...new Set(comp.lines.flatMap((ln) => Object.keys(ln.ratings)).concat(comp.columns))].filter((c) => !keep.has(c));
      const text = "Appliquer le profil « " + p.name + " » ? La grille aura " + p.codes.length + " colonnes : "
        + p.codes.map((c) => names[c] || c).join(", ") + "."
        + (lost ? "\n\n" + lost + " note" + (lost > 1 ? "s" : "") + " des colonnes qui partent (" + leaving.join(", ") + ") "
          + (lost > 1 ? "sont effacées" : "est effacée") + " ; les personnes prévues restent dans la synthèse." : "");
      if (!window.confirm(text)) { pick.value = ""; return; }
      onPick(p.key);
    });
    return pick;
  }

  D.profilePicker = profilePicker;
})();
