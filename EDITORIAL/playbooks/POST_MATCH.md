# Playbook : Post-match (90 min après fin)

Déclenché après chaque match Portugal / Maroc / Al Nassr / match WC majeur.

## Workflow

### J+0 (90 min après coup de sifflet final)
1. **Vérifier le score final** sur ESPN ou fotmob (parfois changement par décision arbitre/VAR post-match).
2. **Lancer** `python scripts/update_stats_v2.py` pour rafraîchir `last_match`.
3. **Récupérer** depuis ESPN summary :
   - Buteurs + minutes
   - Cartons
   - Notes individuelles (si dispo)
   - Statistiques (poss, tirs cadrés, xG, fautes)
   - Highlights URL
4. **Écrire** article récap 400-600 mots :
   - H1 : "{TEAM_W} {SCORE} {TEAM_L} : {ANGLE_PRINCIPAL}"
     - Ex : "Maroc 2-1 Brésil : exploit historique à New York"
   - Lead : 60 mots — résultat, événement clé, conséquence
   - "Les faits du match" : 3 moments clés, chronologique
   - "L'homme du match" : 100 mots sur le MVP
   - "Ce qu'on retient" : 80 mots de conclusion + ce qui suit
   - Stats en bas (tableau HTML simple)
5. **JSON-LD** type `SportsEvent` complet :
```json
{
  "@type": "SportsEvent",
  "name": "Maroc vs Brésil — Groupe C Coupe du Monde 2026",
  "startDate": "2026-06-12T22:00:00-04:00",
  "location": {"@type": "Place", "name": "MetLife Stadium, East Rutherford, NJ"},
  "competitor": [
    {"@type": "SportsTeam", "name": "Maroc"},
    {"@type": "SportsTeam", "name": "Brésil"}
  ],
  "homeTeam": {"@type": "SportsTeam", "name": "Maroc"},
  "awayTeam": {"@type": "SportsTeam", "name": "Brésil"}
}
```
6. **Publier** dans `/world-cup/{country}/news/post-{slug}.html`
7. **Diffuser** X + Telegram + push si match important
8. **Update bracket** WC si concerné

### J+1 (lendemain matin)
- "À chaud" article : 800 mots avec angle d'analyse, citations conf de presse
- Slug `/world-cup/{country}/news/analyse-{slug}.html`

### J+2 / J+3
- Si polémique arbitrage / déclaration controversée → article dédié

## Notes individuelles : grille
- **10** : sublime, match de carrière
- **9** : exceptionnel, joueur du match
- **8** : très bon, contribution majeure
- **7** : bon, solide
- **6** : correct, sans plus
- **5** : moyen
- **4** : insuffisant
- **3** : faute caractérisée (penalty, expulsion)
- **2-1** : catastrophique
- N/A : moins de 20 min de jeu

Distribution attendue par match : 1 note ≥ 8, 4-5 notes 6-7, 1-2 notes ≤ 5.

## Ton de la conclusion

- **Victoire** : célébration mesurée. Pas "ils ont écrasé X". Préférer "ils ont dominé". 
- **Défaite étriquée** : "déçus mais pas humiliés", "encore en course". Encourager.
- **Défaite lourde** : factuel, sans charge ("ils s'inclinent largement"). Souligner les points positifs même minimes.
- **Match nul** : neutre, analyse de ce qu'il manque.
