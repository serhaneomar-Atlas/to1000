# Kaizen — audit live to1000.com — 2026-11-09

> Audit automatique read-only (généré 2026-11-09 17:18 UTC). **Aucune correction appliquée** — ce rapport PROPOSE, il ne modifie pas le site. Source de vérité = le live `https://to1000.com`.

## 🔴 Priorité
- `stats.json` périmé — 5.7 jours (2026-11-04T01:40:03.255068Z). Relancer `update_stats_v2.py`.
- Pages clés en erreur: /blog/ → 404

## 🟠 À surveiller
- Schema FAQPage présent — Google a retiré les rich results FAQ (mai 2026); inerte, retirable.

## 🟢 Sain
- `news.json` frais — généré il y a 11.0h (2026-11-09T06:15:48.601803Z).
- Compteur cohérent partout: 985.
- Sitemap: 17838 URLs.

## 💡 Quick wins
_—_

## 📊 Métriques
- **news_generated_at**: 2026-11-09T06:15:48.601803Z
- **news_items**: 49
- **news_with_image**: 49
- **news_feeds_failed**: None
- **stats_goals**: 985
- **stats_remaining**: 15
- **stats_last_updated**: 2026-11-04T01:40:03.255068Z
- **next_match**: Al Nassr vs Al Qadsiah (2026-11-20T20:00Z)
- **home_goals_seen**: ['985']
- **goals_page_title**: All 985 Goals
- **sitemap_urls**: 17838
- **hreflang**: 2
- **jsonld_blocks**: 7
- **img_lazy**: 0/1

---
_Prochain audit automatique: lundi suivant. Lancer à la demande: `python scripts/kaizen_audit.py`._