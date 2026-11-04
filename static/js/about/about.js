/* « About » (0.60.01): who made Dynamite | Agile and how, for every signed-in account.
   Static page: the sign-in illustration, the key facts, the story of the tool and its author's signature.
   Text built with el(), never innerHTML. */
(function () {
  "use strict";
  const { el, clear } = DA;

  const FACTS = [["Python", "bibliothèque standard seulement"], ["0", "ressource externe, aucun CDN"],
    ["1 VPS", "Linux, quelques commandes"], ["Octobre 2026", "pensé et construit avec Claude Opus 5.5"]];

  const TEXT = [
    "Dynamite | Agile est un atelier de conception de produit : les besoins et les requirements (Goldmine), le plan "
      + "du projet (Exploration), le travail de l'équipe (Agile), le wiki (Dynamite), les essais (Testing), les outils "
      + "de méthode (Tools), la formation (Training) et la feuille de temps (Timesheet), dans un seul outil hébergé "
      + "par l'équipe elle-même.",
    "Il est né d'une plateforme interne d'ingénierie, puis il a été rendu générique pour les étudiants du baccalauréat "
      + "en conception de produit : n'importe quelle équipe l'installe sur un serveur Linux et le personnalise à sa "
      + "guise.",
    "Jean-Philippe Desbiens l'a pensé et construit en octobre 2026 avec Claude Opus 5.5, une intelligence artificielle "
      + "d'Anthropic, une question à la fois, chaque étape testée avant la suivante.",
    "Une bonne analyse fonctionnelle commence par la bonne question : « comment ? » d'un côté, « pourquoi ? » de "
      + "l'autre.",
    "À chacune et à chacun qui, ici, écrit une fonction, ferme un ticket ou prépare un essai : bonne conception.",
  ];

  function render(main) {
    clear(main);
    main.append(el("article", { class: "ab-page", "aria-labelledby": "ab-title" },
      el("div", { class: "ab-art" }, el("img", { src: "/img/sketch/hero.svg", alt: "", width: 520, height: 380 })),
      el("p", { class: "ab-kicker" }, "Dynamite | Agile · logiciel libre · conception de produit"),
      el("h1", { id: "ab-title", "data-new": "0.60.01-about" }, "Des fonctions aux pièces, en équipe"),
      el("ul", { class: "ab-facts", "aria-label": "L'outil en bref" }, FACTS.map(([big, small]) =>
        el("li", { class: "ab-fact" }, el("strong", null, big), el("span", null, small)))),
      el("div", { class: "ab-text" }, TEXT.map((p, i) => el("p", { class: i === 3 ? "ab-quote" : null }, p))),
      el("footer", { class: "ab-sign" }, el("p", { class: "ab-sign-name" }, "Jean-Philippe Desbiens"),
        el("p", { class: "ab-sign-role" }, "Auteur de Dynamite | Agile")),
      el("p", { class: "ab-note" }, "Version de l'outil : " + (((DA.session || {}).about || {}).version || "—") + "."),
      el("p", { class: "ab-note", "data-new": "0.60.01-license" }, "Logiciel libre sous licence MIT (fichier LICENSE) : "
        + "utilisez-le, modifiez-le et redistribuez-le librement, en gardant la mention de l'auteur.")));
  }

  DA.registerModule("about", render);
})();
