# SEO optimiseur

## Mission
Maximiser la visibilité Google + Bing + Yandex + DuckDuckGo. Audit hebdo + validation avant chaque publication.

## Checklist par article (à passer en revue avant publish)

Voir `templates/seo-checklist.md` (version exécutable courte).

### Niveau 1 — bloquants (NE PAS publier sans)
- [ ] `<title>` ≤ 60 caractères avec mot-clé principal
- [ ] `<meta name="description">` 140-160 caractères
- [ ] `<link rel="canonical">` pointant vers l'URL finale (https://)
- [ ] `<h1>` unique présent
- [ ] Au moins 1 JSON-LD valide
- [ ] OG image existante (1200×630 ou plus)
- [ ] hreflang pour les langues disponibles
- [ ] Image hero avec `alt=""`

### Niveau 2 — important (warn, mais publier)
- [ ] 3+ liens internes vers d'autres pages du site
- [ ] 1+ lien externe vers source autorisée (fpf.pt, espn.com, fotmob.com)
- [ ] `<meta name="keywords">` 8-15 mots
- [ ] Twitter Card complète
- [ ] Image `loading="lazy"` sauf hero

### Niveau 3 — nice to have
- [ ] Breadcrumb JSON-LD si > niveau 1
- [ ] FAQ JSON-LD si Q/R présentes
- [ ] Video JSON-LD si vidéo embed
- [ ] Article ≥ 600 mots
- [ ] Score lisibilité (Flesch FR > 60)

## Audit hebdomadaire (dimanche soir)

```bash
# 1. Sitemap valide
curl -s https://to1000.com/sitemap.xml | xmllint --noout -

# 2. Liens cassés (à scripter)
python scripts/seo_audit.py --check-links

# 3. Pages sans canonical
python scripts/seo_audit.py --check-canonical

# 4. Pages > 100 KB (perf warning)
python scripts/seo_audit.py --check-size

# 5. Google Search Console : nouvelles erreurs ?
# (Manuel — onglet Coverage → Errors)
```

## IndexNow ping après chaque publish

```python
import requests, json
body = {
  "host": "to1000.com",
  "key": "a7f3b91c4d8e4f2a9b6c1d5e8f0a3b7c",
  "keyLocation": "https://to1000.com/a7f3b91c4d8e4f2a9b6c1d5e8f0a3b7c.txt",
  "urlList": [
    "https://to1000.com/news/new-page-1.html",
    "https://to1000.com/news/new-page-2.html",
  ]
}
r = requests.post("https://api.indexnow.org/IndexNow", json=body, timeout=10)
```

Google Search Console : utiliser l'URL inspector et "Request indexing" pour les top 3 articles de la journée.

## Mots-clés haute valeur à monitorer

Top 10 à tracker dans Search Console weekly :
1. cristiano ronaldo 1000 goals
2. coupe du monde 2026 maroc
3. coupe du monde 2026 portugal
4. cr7 last goal
5. ronaldo goal counter
6. calendrier coupe du monde 2026
7. world cup 2026 schedule
8. lions de l'atlas wc 2026
9. portugal squad 2026
10. ronaldo career goals total

## Génération auto des pages news

Script `scripts/news_to_html.py` (à créer) :
- Input : `public/news.json`
- Output : `public/news/{slug}.html` × 50
- Template : `EDITORIAL/templates/article-news.html`
- Update : `public/sitemap.xml` (ajoute / supprime entrées)
- Cron : déclenché après chaque `news_aggregator.py`
