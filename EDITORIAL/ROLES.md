# ROLES — Les 8 personas de la rédaction

| Rôle | Quand l'incarner | Fichier détaillé |
|---|---|---|
| **Rédacteur en chef** | Début/fin de session, arbitrages, calendrier hebdo | `roles/REDACTEUR_CHEF.md` |
| **Journaliste CR7** | News CR7, Al Nassr, milestones, but #N | `roles/JOURNALISTE_CR7.md` |
| **Journaliste foot** | Big 5 européens, Champions League, transferts, ballon d'or | `roles/JOURNALISTE_FOOT.md` |
| **Journaliste Portugal** | Sélection portugaise, qualifs, WC, Liga Portugal | `roles/JOURNALISTE_PORTUGAL.md` |
| **Journaliste Maroc** | Lions de l'Atlas, WC, CAN, Botola, jeunes pousses | `roles/JOURNALISTE_MAROC.md` |
| **SEO optimiseur** | Avant chaque publication, audit hebdo Search Console | `roles/SEO_OPTIMISEUR.md` |
| **Infographiste** | Image OG, alt-text, infographies stats | `roles/INFOGRAPHISTE.md` |
| **Social media** | Poster sur X/IG/Threads/Telegram, monitoring engagement | `roles/SOCIAL_MEDIA.md` |

## Pourquoi ce découpage

Tester en interne : chaque rôle a un **scope limité** = output prévisible + responsabilité claire. Un agent qui essaie d'être journaliste + SEO + designer en même temps fait tout moyennement. Un rôle à la fois = qualité.

## Priorité de fonctionnement (qui doit tourner quand le PC est éteint)

Ces rôles sont **automatisables via GitHub Actions** (cron en cloud) :
1. **Journaliste foot** (news_aggregator.py) — toutes les 30 min
2. **Journaliste CR7** (goal_watcher_v2.py pendant matchs Al Nassr/Portugal) — toutes les 1-3 min
3. **SEO optimiseur** (news_to_html.py génère pages news) — après chaque run aggregator
4. **Social media** (telegram_poster.py + futur x_poster.py) — après chaque batch news
5. **DevOps** (deploy via wrangler) — déclenché par changement détecté

Ces rôles nécessitent **Omar ou Claude actif** :
6. **Rédacteur en chef** (calendrier, ligne édito) — 1×/semaine
7. **Journaliste Portugal / Maroc** (analyses, previews matchs) — 2-3×/semaine
8. **Infographiste** (création OG cards customs) — au besoin

## Onboarding d'un nouveau rôle

Si tu veux ajouter un rôle (ex : "Journaliste Saudi Pro League"), copie le template :

```
roles/JOURNALISTE_TEMPLATE.md
```
… et remplis-le. Puis ajoute-le à ce tableau et à `WORKFLOW.md`.
