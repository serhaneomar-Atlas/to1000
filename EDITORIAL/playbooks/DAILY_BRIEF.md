# Playbook : Daily Brief (06:00 UTC quotidien)

Déclencheur : cron GitHub Actions `stats-sync.yml` + `news-sync.yml` à 06:00 UTC.

## Étapes (exécution automatique)

```
1. python scripts/update_stats_v2.py
   → Sync stats CR7 + last_match + next_match depuis ESPN
   → Met à jour public/stats.json si changement détecté
   → Sync HTML counts (update_html_counts.py)

2. python scripts/news_aggregator.py
   → Lit les 32 RSS sources
   → Filtre, traduit (Gemini ou MyMemory), scoore, dédupe
   → Cap 50 items max dans public/news.json

3. python scripts/news_to_html.py  # NOUVEAU (à créer)
   → Pour chaque item nouveau (vs run précédent) : génère public/news/{slug}.html
   → Format SEO complet (meta, JSON-LD NewsArticle)

4. python scripts/wc_countdown_update.py  # NOUVEAU
   → Update public/wc.json (jours/heures/min restants avant 11/6/2026 19:00 UTC)
   → Update standings WC si phase en cours

5. python scripts/sitemap_generator.py  # NOUVEAU (à créer)
   → Régénère public/sitemap.xml avec toutes les pages news, blog, world-cup

6. npx wrangler pages deploy public/ --project-name to1000 --branch main
   → Deploy Cloudflare Pages
   → Réservé aux runners GH Actions (auth via secret CLOUDFLARE_API_TOKEN)

7. python scripts/indexnow_ping.py  # à créer
   → Ping IndexNow avec liste des URLs nouvellement publiées

8. python scripts/telegram_poster.py
   → Top 1-3 news du jour → message Telegram canal @to1000com

9. python scripts/social_poster.py  # à créer
   → 1 post X récap "Brief du jour" avec image OG du top article
```

## Étapes manuelles (Omar / Claude active)

- Mettre à jour `EDITORIAL/state/featured.json` avec les 4 cartes Une si nécessaire
- Vérifier les analytics du jour (UA, sessions, top pages)
- Lire les commentaires Firestore — modérer si besoin

## Échec / retry policy

- Si étape 1 (stats) échoue : continuer (les autres ne dépendent pas)
- Si étape 2 (news) échoue : abort le reste (sans news, rien à publier)
- Si étape 6 (deploy) échoue : log + retry 1× après 5 min, sinon notifier Telegram canal admin

## Log de succès

À la fin, écrire dans `state/published_log.jsonl` :
```jsonl
{"ts":"2026-05-28T06:05:23Z","kind":"daily_brief","items_added":12,"stats_updated":true,"deploy_ok":true}
```
