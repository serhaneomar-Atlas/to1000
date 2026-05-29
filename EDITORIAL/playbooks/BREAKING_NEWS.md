# Playbook : Breaking News (event-driven)

Déclencheur : événement détecté avec score ≥ 85 dans news_aggregator OU décision manuelle (Omar / Claude).

## Critères "breaking"
- Décès d'une figure majeure du foot
- Blessure grave d'une star (Mbappé, CR7, Messi, Haaland, Vinicius, Hakimi…) annoncée par club/sélection
- Transfert XL (>100M€)
- Démission / licenciement d'un sélectionneur (Regragui, Martínez, Tite, etc.)
- Incident violent (stade, agression, scandale)
- Décision FIFA/UEFA majeure (sanction, changement règle)
- But CR7 #999, #1000 → playbook spécial `MILESTONE_999_1000.md`

## Workflow rapide (< 15 min entre détection et publish)

1. **Vérifier sur 2 sources indépendantes** (ex : ESPN + Reuters, ou L'Équipe + RMC)
2. **Drafter** un article 200-300 mots
   - H1 percutant, factuel, sans clickbait
   - Lead : qui-quoi-où-quand
   - 2 paragraphes de contexte
   - "Plus à venir" en bas si info évolutive
3. **Publier** :
   - `/news/breaking-{slug}.html`
   - Bandeau rouge "BREAKING" en haut
   - Push notif PWA via service worker
4. **Indexer** : IndexNow ping immédiat
5. **Diffuser** :
   - Post X immédiat avec image
   - Telegram canal
   - Mise à jour `state/featured.json` → carte 1 = breaking
6. **Suivre** : si info évolue dans les 6h, éditer la page (pas créer une nouvelle)

## Sources rapides recommandées
- @FabrizioRomano (transferts)
- @David_Ornstein (Premier League / officiel)
- @MatteMoretto (Italie)
- @diMarzio (Italie / officiel)
- ESPN.com breaking
- Reuters Sports

## NE PAS publier
- Une rumeur sans vérif (sauf si on titre clairement "Rumeur : …")
- Une info venant uniquement d'un compte tabloïd
- Une info concernant la vie privée non sourcée

## Template push notif
```js
{
  "title": "🚨 Breaking — {COURT 60 char}",
  "body": "{LEAD 120 char}",
  "icon": "/icon-192.png",
  "badge": "/icon-192.png",
  "url": "/news/breaking-{slug}.html",
  "tag": "breaking"
}
```
