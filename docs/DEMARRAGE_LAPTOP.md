# Lancer Dynamite | Agile sur son poste (essai local)

Python 3.10 ou plus récent suffit : bibliothèque standard seulement, aucun `pip`, aucun accès internet.
L'installation sur un serveur (VPS Linux) est décrite sur le site du projet (`site/installation.html`) et dans
`deploy/DEPLOIEMENT_VPS.md`.

## 1. Démarrer en mode développement

```text
cd Dynamite_Agile
python3 app_dynamite_agile.py --dev-admin
```

Ouvrir <http://127.0.0.1:8080> et se connecter avec `admin` / `admin` (mode développement seulement). Sous Windows :
double-clic sur `Lancer_dev_local.bat`.

Au premier démarrage, le mode développement crée l'exemple :

- le Space **EQP · Projet d'équipe**, avec 12 besoins et 35 requirements génériques dans Goldmine ;
- l'équipe d'exemple **Nina, Léa, Hugo et Alexis** (mot de passe temporaire `admin`, à changer à la connexion) ;
- les Spaces **INT** (temps interne et congés), **HEADLAMP** (bac à sable de Help), **TESTING**, **TOOLS** et
  **TRAINING**.

## 2. Vérifier que tout fonctionne

```text
python3 -m unittest discover -s tests -t .
node tests/js/ai_markdown.js
node tests/js/editor_roundtrip.js
```

Les tests utilisent un dossier temporaire et ne touchent pas `data/`.

## 3. Repartir de zéro

Arrêter le serveur, supprimer le dossier `data/`, relancer. Tout est recréé.

## 4. Un premier tour

- Help → le tour du site, un chapitre par onglet, avec son exercice dans HEADLAMP.
- Goldmine → EQP : les besoins (GN-xxx) et les requirements (GR-xxx) reliés à leurs essais de la Test Base.
- Agile → EQP : créer un ticket, le faire avancer sur le Board.
- Timesheet : saisir une plage sur une étape du PDP (ex. B-09 · Recherche des fonctions), puis soumettre la semaine.
