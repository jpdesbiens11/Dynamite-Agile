# Format Project Starter (`dynamite-project-starter`, version 1)

Fichier JSON qu'un assistant IA prépare avec une personne, à partir de `site/starter.md` (0.60.18 ; dans l'outil : Commencer → « Copier le prompt »). Le bouton
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
| `project` | `key` (2 à 10 majuscules ou chiffres), `name`, `description`, `industry`, `product_type`, `start_date` et `weeks` (0.60.22 : le plan de référence d'Exploration, défaut lundi prochain et 15 semaines), `markets` (`CA`, `US`, `EU`, `UK`, `MX`, `AU`, `JP`, `CN`, `KR`, `IN`, `BR`, `INT`) | requis |
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

## Diamond et plan de référence (0.60.22, D-O-032)

`diamond` (facultatif) porte l'analyse fonctionnelle préliminaire, créée dans le Space en « Brouillon IA » (note de chaque
fonction et de chaque risque) : `functions` (arbre : la première fonction sans parent est la primaire, trois niveaux,
une fonction `technique` au niveau 4, une fonction sans parent de plus reste hors de l'arbre), `ports` (entrées `in` et
sorties `out` du système), `flows` (`general` entre fonctions secondaires, `detail` entre fonctions tertiaires sans les
techniques ; d'une entrée ou d'une fonction vers une fonction ou une sortie), `parts` (sur des fonctions secondaires
ou tertiaires), `risks` (P et I de 1 à 5) et `dfmea` (S, O, D de 1 à 10, un Failure Mode par ligne) ; un risque ou une
ligne du DFMEA peut nommer `owner` (le `username` d'une personne de `team`, qui porte l'action) et `due` (AAAA-MM-JJ,
0.60.38). Les règles sont
celles des écrans de Diamond (`core/starter_diamond.py` les lit dans `modules/diamond/`). L'exemple
`deploy/starter_exemples/lampe_bureau.json` reprend l'exemple de Diamond (`tools/make_starter_diamond_example.py`).

Le Space reçoit aussi un **plan de référence** dans Exploration (`modules/exploration/reference.py`) : les 19 étapes du
PDP (mêmes codes que Timesheet), les revues Lean Canvas, Concept Review, PDR, CDR et Validation Report en jalons, les
quatre phases sur `project.weeks` (20 / 25 / 30 / 25 %), et des étapes en parallèle selon la taille de l'équipe (1 piste
jusqu'à 2 personnes, 2 pour 3 ou 4, 3 dès 5) ; les responsables prennent les pistes à tour de rôle.


## Backlog, livrables et Space éprouvé (0.60.43, D-O-052)

`backlog` (facultatif, 150 au plus) remplit Agile : `{ref, type: epic | story | task | bug, title, description, parent (la
ref d'un epic plus haut), mvp (MVP0 à MVP9), assignee (username de team), priority, points}`. Chaque MVP devient une
Version d'Agile ; chaque ticket du MVP la porte, avec le label du MVP. `deliverables` (facultatif, 40 au plus) réserve les
références du Generator : `{doc_type (LCV, CRV, CDCF, PUGH, PDR, CDR, VVR, MVP, BML…), title, step, sub}` ; sans `step`,
l'étape du PDP est celle du type. Les règles sont dans `core/starter_more.py`.

Un **Space éprouvé** se relit au même format : `GET /api/starter/export?space=KEY` (administrateurs et Admin du Space ;
⚙ Admin → Spaces → « Exporter comme modèle (IA) »), et `GET /api/starter/prompt?source=KEY` ajoute ce fichier au prompt comme
exemple à suivre (⚙ Admin → Spaces → Commencer → « Modèle »). Le fichier relu passe `core/starter.parse`.


## Méthodes de conception et exemple Rover (0.60.46, D-O-055)

`tools` (facultatif) remplit les méthodes avec lesquelles le concept a été choisi, dans les outils eux-mêmes :
`ideation` (Tools → Idéation : une séance de brainstorming et ses idées), `pugh` (Goldmine → Pugh : les concepts, le premier
étant la référence, les critères pris dans les requirements et besoins du fichier, notés `+`, `S` ou `-`, et la décision) et
`kt` (Tools → Kepner-Tregoe : alternatives, critères MUST notés 0 ou 1 et WANT pondérés de 1 à 10 notés de 1 à 10, risques
de 1 à 3, décision). Les règles sont dans `core/starter_tools.py` ; un Space éprouvé les relit (`core/starter_export_tools.py`).

L'exemple académique complet **Rover** (véhicule autonome sur une auto téléguidée, Raspberry Pi, application web) est
`deploy/spaces_exemples/rover.json`, écrit par `tools/make_rover_example.py` à partir de `tools/rover/`. Il ne fait **pas**
partie de la plateforme (D-O-050) : le site le publie sur la page d'installation (`site/spaces/rover.json`), et une équipe le
charge si elle le veut, par Commencer.
