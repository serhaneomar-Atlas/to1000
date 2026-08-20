# Les deux conseils

Le fil News repose sur deux organes séparés. L'un **produit**, l'autre **relit**.
Les mélanger, c'est demander à quelqu'un de noter sa propre copie — et c'est
précisément comme ça qu'une dégradation peut durer trois mois sans que personne
la voie.

---

## Ce qui n'allait pas (constat du 19/08/2026)

Trois pannes cumulées, toutes invisibles depuis l'onglet Actions :

| Symptôme | Cause réelle |
|---|---|
| Aucun article de blog depuis le 21/05 | `ai-editorial.yml` sélectionnait sur `score >= 70`, or `score_importance()` plafonne vers 15. Seuil mathématiquement inatteignable. 249 runs « success », zéro production. |
| Résumés qui reformulent le premier paragraphe | La chaîne ne voyait que l'extrait RSS. On ne peut pas « cerner l'information » d'un article qu'on n'a pas lu. |
| « Real Madrid » → « Royal Madrid », « Córdoba » → « Cordoue » | Gemini écartait 90 % des dépêches au tri, et les articles écartés retombaient sur MyMemory, qui traduit mot à mot — noms de clubs compris. |
| 48 appels Gemini par run, 0 cache_hit, pendant des semaines | `enrich_news.py` ne sauvait le cache que si un article changeait. Un lot entièrement écarté jetait toutes ses décisions. |

Le point commun : **rien ne mesurait la qualité de ce qui sortait**. D'où le
second conseil.

---

## Conseil 1 — RÉDACTION (production)

`scripts/editorial.py` · `chief_editor_review()` · tourne dans `news-editorial.yml` (toutes les 30 min)

Cinq étapes. Chacune a un rôle, et le coût est engagé le plus tard possible.

### 1. Rédacteur en chef — tri
Un seul appel. L'article mérite-t-il publication ? Sont écartés : utilitaire
(comment regarder, cotes, compos probables), hors football, périmé, trop local,
creux, promotionnel. En cas de doute sérieux sur les faits : non.

**Pourquoi d'abord** : un rejet coûte un appel. Ni lecture, ni rédaction, ni
traduction payées pour rien.

### 2. Lecture du source — l'article en entier
`scripts/lib/article_fetch.py` récupère le corps de l'article (balises `<p>`,
scripts/nav/footer écartés, 6 000 caractères max). Si la récupération échoue, on
travaille sur l'amorce RSS — **et le prompt le dit au modèle**, qui reçoit alors
la consigne stricte de ne rien extrapoler.

**Pourquoi** : c'est la réponse directe à « au lieu de tout relire, analyser,
résumer puis rédiger ». On ne résume pas une amorce, on résume un article.

### 3. Expert en rédaction — LA nouvelle, puis le développement
Identifie l'information centrale — le fait le plus fort, pas le premier
paragraphe par défaut, pas une reformulation du titre. Puis choisit son format :

| Format | Quand | Longueur |
|---|---|---|
| `brief` | un seul fait clair | 1 paragraphe, 40-70 mots |
| `deep` | article riche, plusieurs angles | 2-3 paragraphes, 90-200 mots |
| `bullets` | plusieurs faits distincts, récap | 3-5 puces, 12-25 mots chacune |

**En cas de doute, le format le plus long.** Mieux vaut garder une information
que la perdre.

Sortie : `title`, `lead` (une phrase — c'est ce qu'on voit sur la carte du fil),
`body` (le développement, qui apporte ce que le lead ne dit pas).

### 4. Expert en traduction — transcréation
Quatre langues (fr/en/es/ar). Pas de mot-à-mot : phrasé de journaliste natif.

Les noms propres repérés dans le source (`scripts/lib/glossary.py`) sont injectés
dans le prompt avec ordre de les reproduire caractère pour caractère. L'arabe est
traité à part : la translittération y est légitime.

### 5. Rédacteur en chef — validation finale
Contrôle la fidélité aux faits, vérifie que le lead porte bien l'information
centrale, que le body ajoute au lead, que les noms propres sont intacts, que
chaque version sonne native. Corrige directement. Ne rejette que si le fond est
irrécupérable.

### Après le modèle : filet déterministe
`repair_calques()` corrige les calques connus sur toutes les sorties — y compris
celles de MyMemory. Même si un modèle dérape, « Royal Madrid » ne sort pas.

### Le registre, pas seulement l'orthographe
Le même mécanisme couvre les erreurs de SENS : « capitaine » traduit قبطان
(capitaine de navire) au lieu de قائد الفريق, « gardien » traduit حارس البوابة
(portier d'immeuble) au lieu de حارس المرمى. Trois couches :
`LEXIQUE_SPORT_AR` impose le registre de la presse sportive arabe dans le
prompt (avec l'accord au féminin pour le football féminin — أول قائدة, jamais
أول قبطان), `CALQUES["ar"]` répare les cas certains après coup, et l'audit les
détecte comme `calque`. Chaque erreur récurrente trouvée par l'audit doit
rejoindre ces trois couches — c'est le point 1 du backlog de veille.

### Humanisation
Consigne injectée aux étapes 3, 4 et 5. Interdits : « il convient de noter »,
« force est de constater », « en effet » en tête, « véritable »,
« incontournable », les triades d'adjectifs, les phrases toutes de même
longueur, les conclusions qui ouvrent sur l'avenir. Alterner court et long.
Nommer les gens et les chiffres au lieu de tourner autour.

---

## Conseil 2 — AUDIT (contrôle et amélioration)

`scripts/audit_editorial.py` · tourne dans `editorial-audit.yml` (1×/jour + à chaque
modification de la chaîne)

Sept contrôles, tous déterministes — aucun appel API, quelques secondes. Il peut
donc tourner souvent, gratuitement, et servir de garde-fou en intégration.

| Contrôle | Ce qu'il attrape | Points retirés |
|---|---|---|
| `calque` | nom propre traduit (« Royal Madrid ») | 40 |
| `nom_perdu` | ≥ 3 noms propres du source disparus | 15 |
| `echo_titre` | résumé qui paraphrase le titre (Jaccard ≥ 0,72) | 25 |
| `resume_court` | moins de 8 mots | 15 |
| `tic_ia` | tournure qui trahit un texte généré | 20 |
| `non_enrichi` | resté en traduction brute | 30 |
| `langue_absente` | une des 4 langues manque | 100 |

**Score** : chaque couple (article, langue) part de 100 et perd le poids de ses
défauts, plancher 0. Le score du fil est la moyenne. Une panne qui touche tout le
fil le fait donc vraiment chuter au lieu d'être diluée par le nombre d'articles.

**Un fil vide vaut 0, pas 100.** Une panne d'agrégation ne doit jamais se lire
comme une qualité parfaite — c'est le piège dans lequel on vient de passer trois
mois.

### Ce qu'il produit
- `EDITORIAL/state/audit_latest.json` — rapport complet, défaut par défaut
- `EDITORIAL/state/audit_history.jsonl` — une ligne par run, pour la tendance
- Une **issue GitHub** (label `audit-editorial`) quand le score passe sous le
  seuil, **mise à jour** au lieu d'être dupliquée, et fermée automatiquement
  quand la qualité revient.

### Veille stratégique et technologique
Le workflow `veille.yml` (lundi 05h UTC) complète la boucle : l'audit dit OÙ on
perd des points, la veille cherche COMMENT en gagner. Chaque semaine, un agent
part des défauts mesurés, compare notre production aux standards des grandes
rédactions sportives (L'Équipe, Marca, The Athletic, بي إن سبورتس، كووورة),
cherche les outils qui répondent à nos défauts dominants, et écrit un rapport
daté dans `EDITORIAL/VEILLE/` plus un backlog priorisé (`VEILLE/BACKLOG.md`).
La veille PROPOSE ; une PR relue APPLIQUE — l'agent de veille n'a pas le droit
de toucher aux scripts.

### Boucle d'amélioration
Le rapport n'est pas un bulletin, c'est une liste de travail :

1. `par_type` dit **quel** défaut domine.
2. `defauts` donne les cas concrets, avec identifiant d'article et langue.
3. Un défaut récurrent se corrige à la source :
   - calque répété → nouvelle règle dans `CALQUES` (`scripts/lib/glossary.py`)
   - `echo_titre` fréquent → durcir l'étape 3
   - `tic_ia` fréquent → enrichir la liste `ANTI_IA` (`scripts/editorial.py`)
   - `non_enrichi` massif → le problème est en amont (quota, tri trop sévère)
4. Modifier la chaîne déclenche l'audit au push : on voit l'effet tout de suite.

### Point de mesure
| Date | Score | Enrichis | Note |
|---|---|---|---|
| 2026-08-19 | **65,8/100** | 0 % | Avant réparation : 192 traductions brutes, 6 calques |

---

## Lancer à la main

```bash
# Audit du fil publié
python scripts/audit_editorial.py

# Rapport machine + échec sous 70
python scripts/audit_editorial.py --json rapport.json --seuil 70

# Tests des deux conseils
python -m pytest scripts/tests/test_editorial_pipeline.py \
                 scripts/tests/test_audit_editorial.py \
                 scripts/tests/test_article_fetch.py -q
```

---

## Ce qui reste à surveiller

- **Le tri de l'étape 1 est sévère** — à raison : le fil ramène beaucoup de
  Liga espagnole de 2e division hors périmètre. Mais si `non_enrichi` reste
  élevé après quelques runs, le problème est en amont : ce sont les **sources**
  (`scripts/sources.json`) qu'il faut resserrer, pas le rédacteur en chef qu'il
  faut assouplir. Publier mal vaut moins que publier peu.
- **Le fetch d'article dépend des sites tiers** (paywalls, rendu JS, 403). Le
  taux `source_lu_en_entier` du rapport dit s'il tient ; s'il stagne bas, la
  qualité des résumés plafonnera quoi qu'on fasse aux prompts.
