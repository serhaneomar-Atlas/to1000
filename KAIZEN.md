# Kaizen — audit live to1000.com — 2026-11-16

> Audit automatique read-only (généré 2026-11-16 16:52 UTC). **Aucune correction appliquée** — ce rapport PROPOSE, il ne modifie pas le site. Source de vérité = le live `https://to1000.com`.

## 🔴 Priorité
- `stats.json` périmé — 6.7 jours (2026-11-10T00:33:31.322290Z). Relancer `update_stats_v2.py`.
- Pages clés en erreur: /blog/ → 404

## 🟠 À surveiller
- Schema FAQPage présent — Google a retiré les rich results FAQ (mai 2026); inerte, retirable.

## 🟢 Sain
- `news.json` frais — généré il y a 5.8h (2026-11-16T11:07:17.921004Z).
- Compteur cohérent partout: 985.
- Sitemap: 17855 URLs.

## 💡 Quick wins
_—_

## 📊 Métriques
- **news_generated_at**: 2026-11-16T11:07:17.921004Z
- **news_items**: 46
- **news_with_image**: 42
- **news_feeds_failed**: None
- **stats_goals**: 985
- **stats_remaining**: 15
- **stats_last_updated**: 2026-11-10T00:33:31.322290Z
- **next_match**: Al Ahli vs Al Nassr (2026-11-20T17:30Z)
- **home_goals_seen**: ['985']
- **goals_page_title**: All 985 Goals
- **sitemap_urls**: 17855
- **hreflang**: 2
- **jsonld_blocks**: 7
- **img_lazy**: 0/1

---
_Prochain audit automatique: lundi suivant. Lancer à la demande: `python scripts/kaizen_audit.py`._