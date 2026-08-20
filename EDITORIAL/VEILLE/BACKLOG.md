# Backlog de veille — améliorations candidates

Tenu par le workflow `veille.yml` (lundi 05h UTC) et complété à la main.
Chaque entrée cite le défaut d'audit qu'elle attaque. La veille propose ;
une PR relue applique.

## Priorisé

| # | Recommandation | Défaut d'audit visé | Impact | Effort | État |
|---|---|---|---|---|---|
| 1 | Étendre `LEXIQUE_SPORT_AR` à partir des calques trouvés par l'audit (chaque `calque` [ar] récurrent devient une équivalence de prompt + une réparation) | `calque` [ar] | Fort | Faible | **En cours** — amorcé le 20/08 (قبطان، حارس البوابة) |
| 2 | Évaluer un contrôle terminologique automatique sur la sortie arabe (lexique + vérification par second appel modèle à froid) | `calque`, `latin_en_arabe` | Fort | Moyen | À évaluer |
| 3 | Étendre le lexique de registre aux autres langues (es : « cerrojo », « pichichi » ; en : idiomes tactiques) sur le même modèle que l'arabe | `calque` [es/en] | Moyen | Faible | À faire |
| 4 | Mesurer la rétention réelle par langue via GA4 (les pages AR retiennent-elles moins ? c'était invisible tant que l'article s'ouvrait en français) | — (stratégique) | Fort | Moyen | Bloqué : GA4 non branché (`CONNECT_ANALYTICS.md`) |

## Réalisé

| Date | Quoi | Effet mesuré |
|---|---|---|
| 2026-08-19 | Lecture de l'article source en entier + formats adaptatifs | Score 65,8 → 75,4 ; 43 % enrichis |
| 2026-08-19 | Glossaire noms propres + réparation calques (langues latines) | 6 calques FR détectés → réparés |
| 2026-08-20 | Consigne de translittération arabe + contrôle `latin_en_arabe` | 25 titres mi-latins détectés |
| 2026-08-20 | Lexique de registre sportif arabe (قبطان → قائد الفريق, féminin) | — (premier run à venir) |
| 2026-08-20 | Pages article multilingues (le titre arabe cliqué ouvrait du français) | Vérifié navigateur, 4 langues |

## Écarté

| Quoi | Pourquoi |
|---|---|
| Remplacer MyMemory par un service de traduction payant supplémentaire | Le problème n'est pas le moteur de secours mais le taux d'articles qui y retombent ; l'argent va d'abord à l'enrichissement Gemini qui couvre déjà les 4 langues |
