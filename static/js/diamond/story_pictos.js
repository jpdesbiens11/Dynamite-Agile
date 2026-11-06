/* Diamond · Storyline (0.60.51, D-O-060): the pictogram palette -- the French names and the groups of the 39 pictograms
   drawn by tools/story_pictos.py (sprites /img/story.svg and /img/story-term.svg, same keys; tests/test_story.py checks
   both lists). D.picto(key) returns the <svg><use> of the current theme. */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const GROUPS = [
    ["Personnes", [["adulte", "Adulte"], ["enfant", "Enfant"], ["aine", "Aîné"], ["technicien", "Technicien"], ["groupe", "Groupe"], ["main", "Main"]]],
    ["Lieux", [["maison", "Maison"], ["cuisine", "Cuisine"], ["atelier", "Atelier"], ["bureau", "Bureau"], ["exterieur", "Extérieur"],
      ["route", "Route"], ["magasin", "Magasin"]]],
    ["Objets", [["produit", "Le produit"], ["telephone", "Téléphone"], ["ordinateur", "Ordinateur"], ["batterie", "Batterie"],
      ["prise", "Prise"], ["outil", "Outil"], ["colis", "Colis"], ["voiture", "Voiture"], ["panier", "Panier"], ["argent", "Argent"],
      ["horloge", "Temps"], ["notice", "Notice"]]],
    ["Environnement", [["soleil", "Soleil, chaleur"], ["pluie", "Pluie"], ["froid", "Froid"], ["nuit", "Nuit"], ["bruit", "Bruit"],
      ["eau", "Eau"], ["poussiere", "Poussière"]]],
    ["Idées et ressentis", [["idee", "Idée"], ["question", "Question"], ["danger", "Danger"], ["content", "Content"],
      ["frustre", "Frustré"], ["coeur", "J'aime"], ["mouvement", "Mouvement"]]],
  ];
  const NAMES = {};
  GROUPS.forEach(([, items]) => items.forEach(([key, name]) => { NAMES[key] = name; }));

  const sprite = () => (document.documentElement.hasAttribute("data-term") ? "/img/story-term.svg" : "/img/story.svg");
  const refresh = DA.refreshIcons;  // a theme change redraws the pictograms already on screen with the other sprite
  DA.refreshIcons = function () {
    if (refresh) refresh();
    document.querySelectorAll("svg.dm-picto use").forEach((u) => u.setAttribute("href", sprite() + "#" + u.getAttribute("href").split("#")[1]));
  };

  function picto(key, cls) {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "dm-picto" + (cls ? " " + cls : ""));
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const use = document.createElementNS(NS, "use");
    use.setAttribute("href", sprite() + "#p-" + key);
    svg.append(use);
    return svg;
  }

  DA.diamond = Object.assign(DA.diamond || {}, { PICTO_GROUPS: GROUPS, PICTO_NAMES: NAMES, picto });
})();
