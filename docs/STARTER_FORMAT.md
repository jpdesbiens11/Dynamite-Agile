# Format Project Starter (`dynamite-project-starter`, version 1)

Fichier JSON qu'un assistant IA prépare avec une personne, à partir de `site/starter.md` (0.60.07). Le bouton
« Commencer » de l'outil (0.60.06) le lit et crée un nouveau Space, à côté des exemples. Le validateur est
`core/starter.py` (D-O-019). Pour vérifier un fichier sans rien créer :

```
python3 tools/check_starter.py mon_projet.json
```

Trois exemples complets : `deploy/starter_exemples/` (lampe de bureau connectée, tensiomètre de poignet, convoyeur
de table modulaire).

## Ce que le fichier ne décide jamais

Le fichier vient d'un assistant IA : rien n'y est cru sur parole.

- Tout requis et tout essai arrive **« À vérifier »**. Une norme nommée par une IA peut avoir la mauvaise édition ou
  la mauvaise clause : une personne la confirme avant qu'un requis passe à « Approuvé ».
- Les essais arrivent en **Draft** ; chaque page arrive en **Brouillon IA**, avec un panneau qui le dit en tête.
- Aucun membre n'est administrateur ; aucun mot de passe dans le fichier (le site crée un mot de passe temporaire,
  affiché une seule fois). Un nom d'utilisateur qui existe déjà est réutilisé tel quel.
- Du texte seulement : aucune balise HTML ; les pages suivent la liste blanche de Dynamite, sans image ni ticket.

## Structure

| Clé | Contenu | Limite |
|---|---|---|
| `format`, `format_version` | `"dynamite-project-starter"`, `1` | requis |
| `language` | `fr` ou `en` | défaut `fr` |
| `generated_by`, `generated_at` | assistant utilisé, date `AAAA-MM-JJ` | facultatif |
| `project` | `key` (2 à 10 majuscules ou chiffres), `name`, `description`, `industry`, `product_type`, `markets` (`CA`, `US`, `EU`, `UK`, `MX`, `AU`, `JP`, `CN`, `KR`, `IN`, `BR`, `INT`) | requis |
| `team` | `username`, `display_name`, `study_profile`, `title`, `role` (`editor`, `manager`, `reader`) | 12 personnes |
| `requirements` | `ref`, `kind` (`need` / `requirement`), `statement`, `rationale`, `category`, `lifecycle`, `stakeholder`, `source`, `standard`, `edition`, `clause`, `verification_method` (`I`, `A`, `D`, `T`), `acceptance_criteria`, `criticality` (`A` à `E`), `derived_from` (refs déclarées plus haut) | 300 |
| `tests` | `ref`, `title`, `subject` (`func`, `elec`, `emc`, `therm`, `env`, `ingress`, `mech`, `life`, `mat`, `sw`, `usab`, `prod`, `ver` ; défaut `func`), `category` (`standard`, `industry`, `custom`), `standard`, `section`, `level`, `method`, `objective`, `acceptance`, `means`, `verifies` (refs de requis) | 300 |
| `time_codes` | groupes `{key, label, codes: [{key, label}]}` ; deux niveaux. Un code s'écrit comme dans Timesheet : 1 à 5 majuscules, un tiret, 2 à 4 majuscules ou chiffres (`LA-MAR`, `C-BOI`), unique sur tout le site. Un groupe qui a des codes sert seulement d'intitulé (« groupe · code ») ; un groupe sans codes est lui-même un code | 40 codes |
| `pages` | `ref`, `title`, `parent` (ref d'une page plus haut, ou `null`), `body` (page Dynamite `{"type": "doc", …}`) | 30 pages, deux niveaux |

Les valeurs de `category`, `lifecycle`, `stakeholder`, `source`, `subject`, `level` sont celles de Goldmine et de
Testing (`modules/agile/goldmine.py`, `modules/testing/data_tests.py`), et la forme d'un code celle de Timesheet
(`modules/timesheet/budget.py`) : le validateur les lit là, ils ne peuvent pas diverger.
Un requis de `source` `standard` doit nommer sa norme. Sans `time_codes`, le Space prend les codes du PDP (A-01 … D-21).

Chaque refus donne le chemin de la valeur en cause et le correctif, par exemple :
`Fichier Project Starter refusé (tests[2].verifies[0]) : requis « REQ-9 » introuvable. Correctif : utilisez le champ
ref d'un élément déjà déclaré plus haut dans le fichier.`
