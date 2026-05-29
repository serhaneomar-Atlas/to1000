# Social Media

## Comptes
- X : @To1000com
- Instagram : @to1000com
- Threads : @to1000com
- Facebook : @to1000com
- Telegram : @to1000com (bot/canal)
- Email : to1000com@gmail.com

## Cadence de publication

| Canal | Fréquence | Type |
|---|---|---|
| X | 3-6 posts/jour | Réactif (news instant) + 1 graphic/jour |
| IG | 1-2 posts/jour | Image + reel post-match |
| Threads | Mirror de X | Auto via cross-poster |
| Facebook | 1 post/jour | Article featured |
| Telegram | Tous les push d'articles | Auto via telegram_poster.py |

## Pendant la WC : monter à
- X : 8-12 posts/jour les jours de match
- IG : 3-4 stories par match + 1 reel résumé

## Auto-posting

### Telegram (déjà en place)
`scripts/telegram_poster.py` — actuellement en dry-run car `to1000/.env` manquant.

À configurer (Omar à faire une fois) :
```
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=@to1000com
```

### X (à mettre en place)
Soit :
**Option A — Computer use** : Claude pilote le navigateur (Chrome MCP) pour poster sur x.com. Plus lent, moins fiable, mais zero setup.
**Option B — API X** : 200 USD/mois minimum (X Basic). Pas worth pour ce volume.
**Option C — Buffer / Hypefury** : ~6 USD/mois, cross-post X+IG+Threads+FB depuis une queue Google Sheets ou webhook.

Recommandation : **Option C** (Buffer) si Omar peut budgéter ~6 €/mois. Sinon Option A en dépannage.

## Template post X — news factuelle

```
{EMOJI_DRAPEAU} {TITRE}

{1-2 phrases clés - 200 char max}

{URL}

#WorldCup2026 #{HASHTAG_PAYS} #Football
```

Exemple :
```
🇲🇦 Walid Regragui annonce ses 26 Lions pour la Coupe du Monde !

Hakimi capitaine, Ziyech présent. Bilal El Khannous, la révélation du dernier CAN, fait son retour.

https://to1000.com/world-cup/maroc/news/squad-26-cdm-2026

#WorldCup2026 #Maroc #LionsDeLAtlas #DimaMaghrib
```

## Template post X — but CR7

```
⚽️ GOAL — Cristiano Ronaldo (#{N})

vs {OPPONENT} ({COMP}) — minute {MIN}'

🎯 {DISTANCE}/{TARGET} buts pour la légende

{URL}

#CR7 #Ronaldo #To1000
```

## Hashtags
Variables :
- `#WorldCup2026` ou `#CDM2026`
- Pays : `#Maroc` `#DimaMaghrib` `#LionsDeLAtlas` `#Portugal` `#PRTvsCOD` etc.
- CR7 : `#CR7` `#Ronaldo` `#GOAT` (utiliser GOAT avec parcimonie)
- Branding : `#To1000` `#RoadTo1000`

## Engagement
- Répondre aux DMs OK (mais pas d'aide légale, financière, paris)
- Répondre aux commentaires : sourires, faits, jamais d'insulte
- Modération : insulte / racisme / spam → block immédiat
- Pas de RT politique (sauf si sport ↔ politique inévitable, ex : Hakimi déclaration sociale)

## Métriques à tracker (1×/sem, dimanche soir)
- Nb followers par canal
- Top 3 posts de la semaine (impressions)
- Tx clic vers le site (UTM dans URLs)
- Mentions / DM positives vs négatives

## UTM standard sur tous les liens partagés
```
?utm_source={CANAL}&utm_medium=social&utm_campaign={SLUG_ARTICLE}
```

Exemple : `https://to1000.com/world-cup/maroc/?utm_source=x&utm_medium=social&utm_campaign=launch_morocco_page`
