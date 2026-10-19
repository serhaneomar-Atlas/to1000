# Kaizen — audit live to1000.com — 2026-10-19

> Audit automatique read-only (généré 2026-10-19 14:27 UTC). **Aucune correction appliquée** — ce rapport PROPOSE, il ne modifie pas le site. Source de vérité = le live `https://to1000.com`.

## 🔴 Priorité
- `stats.json` périmé — 6.7 jours (2026-10-12T21:34:02.131209Z). Relancer `update_stats_v2.py`.
- Pages clés en erreur: /blog/ → 404

## 🟠 À surveiller
- Schema FAQPage présent — Google a retiré les rich results FAQ (mai 2026); inerte, retirable.

## 🟢 Sain
- `news.json` frais — généré il y a 6.7h (2026-10-19T07:46:49.241110Z).
- Compteur cohérent partout: 981.
- Sitemap: 17849 URLs.

## 💡 Quick wins
_—_

## 📊 Métriques
- **news_generated_at**: 2026-10-19T07:46:49.241110Z
- **news_items**: 47
- **news_with_image**: 45
- **news_feeds_failed**: None
- **stats_goals**: 981
- **stats_remaining**: 19
- **stats_last_updated**: 2026-10-12T21:34:02.131209Z
- **home_goals_seen**: ['981']
- **goals_page_title**: All 981 Goals
- **sitemap_urls**: 17849
- **hreflang**: 2
- **jsonld_blocks**: 7
- **img_lazy**: 0/1

---
_Prochain audit automatique: lundi suivant. Lancer à la demande: `python scripts/kaizen_audit.py`._