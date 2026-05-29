# WORKFLOW — La boucle quotidienne et événementielle

## Vue système (qui appelle quoi)

```
                    ┌──────────────────────────┐
                    │  GitHub Actions (cron)   │
                    └────────────┬─────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
  news-sync.yml          stats-sync.yml           wc-countdown.yml
  (*/30 min)             (daily 06:00 UTC)        (daily 00:00 UTC)
        │                        │                        │
        ▼                        ▼                        ▼
  news_aggregator.py      update_stats_v2.py      wc_countdown_update.py
  → public/news.json      → public/stats.json     → public/wc.json
        │                        │                        │
        ▼                        │                        │
  news_to_html.py               │                        │
  → public/news/{slug}.html     │                        │
        │                        │                        │
        └─────────┬──────────────┴────────────────────────┘
                  ▼
        sitemap_generator.py
        → public/sitemap.xml
                  │
                  ▼
        wrangler pages deploy
        → to1000.com
                  │
                  ▼
        IndexNow ping + telegram_poster.py + x_poster.py
```

## Phases de la journée éditoriale

### Phase A — Daily Brief (06:00 UTC / 07:00 Paris)
Déclenché automatiquement. Voir `playbooks/DAILY_BRIEF.md`.
- Sync stats CR7
- Sync news depuis 31 sources RSS
- Génère pages SEO pour les nouvelles news (top 20)
- Update WC countdown
- Régénère sitemap
- Deploy
- Poste un récap quotidien sur X + Telegram

### Phase B — Live monitoring (toutes les 30 min)
news_aggregator.py tourne en cron. Si nouvelle news détectée avec score ≥ 70 (importance haute) :
- Génère sa page SEO immédiatement
- Push direct sans attendre le batch quotidien
- Poste sur X/Telegram si score ≥ 85 (très important)

### Phase C — Match live (déclenchée par calendrier)
Quand un match Portugal / Maroc / Al Nassr commence :
- `goal_watcher_v2.py` passe en polling 60s
- Mise à jour stats.json en quasi-temps réel si but CR7
- Génère bandeau "MATCH EN COURS" sur home
- Voir `playbooks/WC_LIVE_MATCH.md` pour WC spécifiquement

### Phase D — Post-match (90 min après fin)
Voir `playbooks/POST_MATCH.md`.
- Article récap auto-généré depuis ESPN data
- Highlight CR7 si applicable
- Update bracket WC si match WC
- Poste résumé social

### Phase E — Breaking news (event-driven)
Voir `playbooks/BREAKING_NEWS.md`.
- Blessure star, transfert majeur, déclaration polémique
- Bypass de la file normale → priorité 1

## Cron des workflows GitHub Actions

| Workflow | Cron | But |
|---|---|---|
| `news-sync.yml` | `*/30 * * * *` | Aggrégation RSS + génération pages news |
| `stats-sync.yml` | `0 6 * * *` | Sync stats CR7 quotidienne |
| `wc-sync.yml` | `0 */6 * * *` | Mise à jour calendrier WC + standings |
| `goal-watcher.yml` | Manuel ou cron pendant fenêtres match | Polling buts CR7 |
| `social-poster.yml` | `0 9,15,21 * * *` | Posts X/Telegram 3×/jour |
| `seo-rebuild.yml` | `0 4 * * 0` | Rebuild hebdo sitemap + audit liens cassés |

## Quand le PC d'Omar est éteint
Tout ce qui est en GitHub Actions tourne. Donc le site se met à jour H24 même si Omar dort.

Ce qui **n'est pas autonome** sans Omar/Claude :
- Articles long format (analyse 1500+ mots)
- Création d'infographies originales
- Modération comments (notification email à Omar à mettre en place)
- Réponse aux DMs sur X

## Comment lancer un cycle manuel
```bash
cd C:\Users\serha\Desktop\To1000.com\to1000
python scripts/news_aggregator.py
python scripts/news_to_html.py
python scripts/sitemap_generator.py
scripts/deploy_now.bat
```

## État courant à vérifier
- `state/published_log.jsonl` : dernières publications
- `state/pending_topics.json` : idées en attente
- `public/news.json` `generated_at` : fraîcheur du dernier batch
- `public/stats.json` `last_updated` : fraîcheur des stats CR7
- `public/wc.json` `last_updated` : fraîcheur du calendrier WC

## Pour augmenter la fréquence pendant la WC
Pendant la Coupe du Monde (11 juin – 19 juillet 2026), tous les cron de news doivent passer à `*/15 * * * *` au lieu de `*/30`. Voir `playbooks/PRE_WC_BUILDUP.md` section "Switch frequencies".
