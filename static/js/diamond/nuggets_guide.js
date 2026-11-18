/* Diamond · Golden Nuggets, the guide of each part (0.60.124, D-O-137): why the part exists and how to use it, in the same
   five headings everywhere -- Contexte, Problématique, Portée, Comment l'utiliser, Ce que contient chaque carte -- for the
   collection as a whole (intro) and for each of the four parts. Shown above the cards (nuggets.js) and put at the head of
   each part in the PDF and Word exports (nuggets_export.js). Static content; summaries in our own words, no quotation. */
(function () {
  "use strict";

  /* [key, heading]; context and problem are paragraphs, scope / use / cards are lists (use is numbered) */
  const HEADS = [["context", "Contexte"], ["problem", "Problématique"], ["scope", "Portée"], ["use", "Comment l'utiliser"],
    ["cards", "Ce que contient chaque carte"]];

  const GUIDE = {
    intro: {
      title: "Pourquoi Golden Nuggets",
      context: "Diamond mène une équipe de l'usage (Storyline) à l'arbre fonctionnel, aux briques technologiques, au DFMEA et aux "
        + "coûts. Ces méthodes disent quoi produire et comment le vérifier ; elles ne disent pas comment trouver une bonne idée, "
        + "ni comment juger qu'un concept est trop compliqué ou mal placé sur son marché. Golden Nuggets rassemble les principes "
        + "que l'industrie applique pour cela, en quatre parties.",
      problem: "Ces principes sont dispersés dans des livres, des entrevues et l'expérience de quelques personnes. Sans un "
        + "vocabulaire commun, une revue de concept devient une affaire d'opinions : « c'est trop cher », « c'est trop "
        + "compliqué », sans dire pourquoi ni quoi faire. Un principe nommé et codé (P5, A2, R1, D7) se cite, se discute et se "
        + "retrouve dans la justification d'un choix.",
      scope: [
        "First Principles (P) : au moment du concept et de l'architecture, pour trouver des solutions.",
        "L'algorithme en 5 étapes (A) : à la revue d'un design ou d'un procédé qui existe, pour l'alléger.",
        "Règles SpaceX et Tesla (R) : en conception pour la fabrication et les essais, et pour l'organisation de l'équipe.",
        "Disruptive Innovation (D, C) : pour la stratégie produit — quel marché, quels clients, quel modèle d'affaires.",
        "Le contenu est le même dans tous les Spaces et ne se modifie pas : ce sont des références, pas des données du projet.",
      ],
      use: [
        "Choisissez la partie qui correspond au moment du projet (liste ci-dessus).",
        "Lisez son guide, puis cherchez par mot (coût, pièce, client…) ou filtrez par famille de couleur.",
        "Ouvrez « Exemple et application » : le cas de l'industrie, puis ce que la carte donne sur votre projet.",
        "Citez le code de la carte dans une justification (feuille de concept, Pugh Matrix, DFMEA, requirement) : la décision reste traçable.",
        "Pour une formation ou une revue, exportez une partie ou les quatre en PDF ou en Word (boutons en haut à droite).",
      ],
      cards: [
        "Le code : la lettre de la partie et un numéro (P1, A1, R1, D1, C1), stable d'une version à l'autre.",
        "La famille, en couleur : le genre de problème que la carte aide à régler.",
        "Le titre et l'idée : le principe en une ou deux phrases.",
        "« Exemple et application », à ouvrir : un cas réel de l'industrie, puis comment s'en servir sur votre projet.",
      ],
    },
    principles: {
      context: "Une équipe hérite de solutions : la pièce du catalogue fournisseur, le dessin du projet précédent, ce que fait le "
        + "concurrent. Penser à partir des premiers principes, c'est ramener le problème à ce que la physique, les matières et "
        + "les coûts imposent vraiment, puis reconstruire la solution. Les principes inventifs de TRIZ (G. Altshuller, tirés de "
        + "l'étude d'un grand nombre de brevets) donnent des façons connues de lever une contradiction technique.",
      problem: "Raisonner par analogie donne des copies un peu meilleures, au même coût. On ajoute des pièces pour corriger un "
        + "défaut au lieu de supprimer sa cause ; une contradiction (plus léger mais plus rigide, plus puissant mais moins "
        + "chaud) se règle par un compromis, alors qu'un principe inventif permettrait souvent d'avoir les deux.",
      scope: [
        "Couvre : la phase concept et l'architecture — arbre fonctionnel, briques technologiques, feuilles de concept, Pugh Matrix, premier DFMEA.",
        "Vingt principes retenus pour la conception de produit, en cinq familles : Coût et matières, Méthode, Architecture, Fabrication, Essais.",
        "Ne couvre pas : la méthode TRIZ complète (matrice des contradictions, 40 principes, ARIZ).",
        "Ne remplace ni un calcul ni un essai : une carte donne une piste, la physique et le test la confirment.",
      ],
      use: [
        "Avant de choisir une brique ou un concept, écrivez le problème en une phrase, ou la contradiction (« plus léger sans perdre en rigidité »).",
        "Filtrez la famille qui touche ce problème : Coût et matières pour un coût cible, Architecture pour un nombre de pièces, Essais pour un risque.",
        "Choisissez deux ou trois cartes et lisez « Sur votre projet ».",
        "Proposez une variante par carte dans les feuilles de concept, puis comparez-les à la solution de référence dans une Pugh Matrix.",
        "Notez le code de la carte (P5…) dans la justification du concept retenu.",
      ],
      cards: [
        "P1 à P20, dans l'ordre du catalogue.",
        "La famille : Coût et matières, Méthode, Architecture, Fabrication ou Essais.",
        "Le badge TRIZ, quand la carte correspond à un des 40 principes inventifs (avec son numéro).",
        "« Dans l'industrie » : un cas connu. « Sur votre projet » : ce que le principe donne sur l'exemple de Diamond, et où l'appliquer dans la plateforme.",
      ],
    },
    algorithm: {
      context: "Elon Musk a décrit en public, notamment lors d'une visite de l'usine Starbase en 2021, la méthode en cinq étapes "
        + "que ses équipes appliquent chez SpaceX et Tesla : questionner les exigences, supprimer, simplifier, accélérer, "
        + "automatiser. Elle est née d'erreurs reconnues, comme une chaîne de production automatisée trop tôt.",
      problem: "L'ordre naturel d'une équipe est l'inverse : on optimise et on automatise ce qui existe, puis on découvre que la "
        + "pièce ou l'étape n'aurait pas dû exister. Le temps passé à optimiser une chose inutile est perdu, et une exigence "
        + "jamais remise en question fige le design pour longtemps.",
      scope: [
        "Couvre : la revue d'un design ou d'un procédé qui existe déjà — requirements (Goldmine), pièces, étapes de fabrication (Procédés, PFMEA), essais.",
        "Trois familles : Questionner et supprimer (A1, A2), Simplifier (A3), Accélérer et automatiser (A4, A5).",
        "Ne couvre pas : la recherche d'idées de départ (First Principles) ni la stratégie de marché (Disruptive Innovation).",
        "Un ordre de travail, pas un menu : les cinq étapes se font toutes, et dans cet ordre.",
      ],
      use: [
        "Prenez une pièce, un sous-système ou une étape de procédé.",
        "A1 : pour chaque exigence, trouvez la personne qui l'a posée et demandez-lui pourquoi ; une exigence sans nom est la première à questionner.",
        "A2 : supprimez tout ce qui peut l'être. Si vous ne remettez jamais rien, vous n'avez pas assez supprimé.",
        "A3 : simplifiez et optimisez seulement ce qui reste.",
        "A4, puis A5 : accélérez le cycle, et automatisez en dernier.",
        "Refaites le tour à chaque design review ; notez les suppressions et leurs raisons.",
      ],
      cards: [
        "A1 à A5 : les étapes, dans l'ordre où elles se font.",
        "La famille : Questionner et supprimer, Simplifier, Accélérer et automatiser.",
        "« Exemple » : comment l'étape s'est appliquée chez SpaceX ou Tesla.",
        "« Sur votre projet » : l'étape sur l'exemple de Diamond, et l'écran de la plateforme où la faire.",
      ],
    },
    rules: {
      context: "Les mêmes méthodes se traduisent en règles de conception que SpaceX et Tesla ont décrites en public : moins de "
        + "pièces, l'usine conçue comme un produit, fabriquer soi-même ce qui coûte trop cher à acheter, des essais tôt et "
        + "jusqu'à la rupture, et un ingénieur responsable de chaque pièce.",
      problem: "La conception, la fabrication et les essais sont souvent séparés par des murs : on dessine une pièce sans "
        + "penser à la cadence, on achète sans comparer au coût de faire, on teste tard pour se rassurer plutôt que pour "
        + "apprendre, et personne ne répond d'une pièce de bout en bout.",
      scope: [
        "Couvre : la conception pour la fabrication et l'assemblage, le choix faire ou acheter, la stratégie d'essai, l'organisation de l'équipe.",
        "Quatre familles : Conception, Fabrication, Essais, Organisation.",
        "Ne couvre pas : les règles propres à un procédé (tolérances, matériaux) ni les normes du produit.",
        "Ce sont des règles d'entreprise : elles se discutent selon la taille de l'équipe, le volume et le risque.",
      ],
      use: [
        "À l'allocation des pièces : appliquez R1, chaque pièce doit justifier sa présence par une fonction de l'arbre.",
        "Aux Procédés et au PFMEA : R2, concevez la cadence et le coût de fabrication en même temps que la pièce.",
        "Aux Coûts et budget : R3, comparez le prix d'achat au coût de fabriquer soi-même.",
        "Au plan d'essais (Test Base) : R4, prévoyez des essais tôt et jusqu'à la rupture.",
        "Dans Compétences et équipe : R5, nommez un responsable par pièce, qui répond aussi de sa fabrication et de son essai.",
      ],
      cards: [
        "R1 à R5 : une règle par carte, de la conception de la pièce à l'organisation de l'équipe.",
        "La famille : Conception, Fabrication, Essais ou Organisation.",
        "« Exemple » : la règle telle qu'elle a été appliquée.",
        "« Sur votre projet » : la règle sur l'exemple de Diamond.",
      ],
    },
    disruption: {
      context: "Clayton M. Christensen a étudié pourquoi des entreprises bien gérées perdent leur marché face à des produits plus "
        + "simples et moins chers (The Innovator's Dilemma, 1997). Ses concepts — sustaining et disruptive innovation, value "
        + "network, Jobs to be Done — sont toujours appliqués pour décider quels produits lancer, sur quel marché, et avec "
        + "quelle organisation.",
      problem: "Une entreprise qui écoute ses meilleurs clients et investit là où ses marges sont les plus hautes fait ce qu'il "
        + "faut… jusqu'au jour où un produit moins bon, mais suffisant et moins cher, prend le bas du marché puis monte. Une "
        + "équipe de conception fait la même erreur quand elle ajoute de la performance que personne n'utilise.",
      scope: [
        "Couvre : la stratégie produit — portefeuille de projets, choix du marché et des clients, modèle d'affaires, organisation d'un projet nouveau.",
        "Vingt concepts et pratiques en quatre familles (Marché et technologie, Clients, Organisation, Agir en entreprise), le livre et ses suites, et ses douze études de cas (C1 à C12).",
        "Ne couvre pas : le design technique du produit, ni l'évaluation financière d'un projet.",
        "Une grille de lecture, pas une prédiction : elle dit où regarder et quelles questions poser.",
      ],
      use: [
        "Classez votre projet : sustaining ou disruptive (D1). Les deux ne se gèrent ni avec les mêmes critères ni avec le même budget.",
        "Tracez la performance livrée et la performance utilisée par les clients : l'écart montre où un produit plus simple suffit.",
        "Cherchez les non-consommateurs et le job que le client veut faire faire au produit (famille Clients) : c'est votre Storyline.",
        "Choisissez l'organisation et la planification du projet (familles Organisation et Agir en entreprise).",
        "Lisez l'étude de cas la plus proche de votre secteur et sa leçon.",
      ],
      cards: [
        "D1 à D20 : les concepts et les pratiques, en quatre familles de couleur.",
        "« Exemple » : un cas de l'industrie. « En entreprise aujourd'hui » : ce qu'une entreprise fait de ce concept.",
        "C1 à C12 : les études de cas du livre ; la leçon visible, « Ce qui s'est passé » à ouvrir.",
        "« Le livre et ses suites » : la référence, les ouvrages qui ont suivi et un sommaire du livre.",
      ],
    },
  };

  DA.diamond = Object.assign(DA.diamond || {}, { NUGGETS: Object.assign((DA.diamond || {}).NUGGETS || {}, { GUIDE, GUIDE_HEADS: HEADS }) });
})();
