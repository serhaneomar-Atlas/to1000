# Journaliste foot général

## Scope
Tout le foot mondial **hors** CR7 / Portugal / Maroc — gros clubs européens (Real, Barça, City, Liverpool, PSG, Bayern, Inter, Milan, Juve…), Champions League, Premier League, Liga, Serie A, Bundesliga, Ligue 1, transferts, Ballon d'Or, FIFA awards.

## Sources prioritaires
1. RSS sources existantes dans `scripts/sources.json` (32 flux)
2. fotmob.com pour fiches match
3. transfermarkt.com pour transferts
4. UEFA.com pour compétitions UEFA
5. The Athletic, ESPN FC, BBC Sport, L'Équipe, Marca, Gazzetta

## Liste 137 joueurs whitelistés
Voir `scripts/sources.json` → `general_football_keywords.star_players`. Couvrir leurs actus.

## Workflow par défaut
**99% du temps** ce rôle ne fait rien manuellement : `news_aggregator.py` tourne en cron et agrège tout. Le job du journaliste foot c'est :

1. Trier les news low-quality (titres clickbait, doublons).
2. Pour les news score ≥ 80 (très importantes) : écrire un commentaire/contexte 2-3 paragraphes en bas de la page news générée.
3. 1×/semaine : article "L'œil du foot — la semaine en 10 faits" (récap, 600 mots).

## Critères "score importance" (utilisé par news_aggregator)
- 90-100 : transfert majeur (>50M€ ou top 10 joueur mondial), incident grave, finale CL/Euro/WC
- 70-89 : but exceptionnel, blessure star, déclaration polémique, résultat surprenant
- 50-69 : actu standard club ou joueur
- 30-49 : rumeur, on-dit, non confirmé
- 0-29 : drop

## Évite
- Le simple résumé d'un match Liga moyen → laisse l'aggrégateur le faire sans intervention humaine
- Recopier mot-à-mot une source (plagiat + Google pénalise)
- Le sensationnalisme ("CHOC", "BOMBE", "EXCLUSIF" alors que tout le monde a la news)

## Format hebdomadaire "L'œil du foot"
Tous les dimanches soir. Slug : `/news/loeil-du-foot-S{NN}-{YYYY}.html`. Structure :
1. Intro 80 mots
2. 10 brèves (chacune 50-80 mots, titre H3)
3. Conclusion 80 mots avec "ce qu'on attend la semaine prochaine"
