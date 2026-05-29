#!/usr/bin/env python3
"""
claude_journalist.py — Journaliste IA autonome pour to1000.com.

Tourne en GitHub Actions toutes les 8h (3×/jour). Pour chaque batch :

  1. Lit public/news.json (50 items fresh)
  2. Filtre les items "scoop" : score ≥ 70 + non encore couverts
  3. Pour les TOP 1-2 : appelle Claude Sonnet via API
  4. Génère un article original 600-900 mots respectant EDITORIAL/STYLE_GUIDE.md
  5. Sauvegarde dans public/blog/ avec slug daté + JSON-LD NewsArticle
  6. Met à jour public/blog/posts.json
  7. Append dans EDITORIAL/state/published_log.jsonl
  8. Commit + push via le workflow parent

Env requises :
  ANTHROPIC_API_KEY        — secret GitHub Actions
  GITHUB_ACTIONS=true      — auto-set par GH

Coût estimé : ~0,02 USD par article (Sonnet, ~3k tokens out).
3 runs/jour × 2 articles = 6 articles/jour = ~0,12 USD/jour = ~3,6 USD/mois.
"""
from __future__ import annotations
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("⚠ anthropic SDK non installé. pip install anthropic")
    sys.exit(1)

PROJECT_DIR = Path(__file__).parent.parent
NEWS_JSON   = PROJECT_DIR / "public" / "news.json"
BLOG_DIR    = PROJECT_DIR / "public" / "blog"
POSTS_JSON  = BLOG_DIR / "posts.json"
LOG_FILE    = PROJECT_DIR / "EDITORIAL" / "state" / "published_log.jsonl"
STYLE_GUIDE = PROJECT_DIR / "EDITORIAL" / "STYLE_GUIDE.md"

MODEL = "claude-sonnet-4-5"  # bon ratio coût/qualité pour de l'éditorial
MAX_ARTICLES_PER_RUN = 2
MIN_SCORE = 70
GA = "G-4V8Y6C38VN"
SITE = "https://to1000.com"


def slugify(s: str, maxlen: int = 70) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s[:maxlen].rstrip("-") or "article")[:maxlen]


def already_covered() -> set[str]:
    """Retourne l'ensemble des IDs news déjà couverts."""
    covered = set()
    if not LOG_FILE.exists():
        return covered
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if e.get("source_news_id"):
                covered.add(e["source_news_id"])
        except Exception:
            continue
    return covered


def pick_candidates(items: list[dict], covered: set[str], limit: int) -> list[dict]:
    cands = []
    for it in items:
        if it.get("id") in covered:
            continue
        if (it.get("score") or 0) < MIN_SCORE:
            continue
        cands.append(it)
    cands.sort(key=lambda x: x.get("score", 0), reverse=True)
    return cands[:limit]


def call_claude(item: dict, style_excerpt: str) -> tuple[str, str, str]:
    """Retourne (title_fr, lead_fr, body_html)."""
    client = anthropic.Anthropic()
    title = item.get("title_fr") or (item.get("i18n", {}).get("fr") or {}).get("title") or item.get("title", "")
    summary = item.get("summary_fr") or (item.get("i18n", {}).get("fr") or {}).get("summary") or item.get("summary", "")
    src_url = item.get("url", "")
    src_name = item.get("primary_source") or item.get("source") or "source externe"
    if isinstance(src_name, dict):
        src_name = src_name.get("name") or "source externe"

    prompt = f"""Tu es journaliste sportif pour to1000.com, un site fan de Cristiano Ronaldo et de la Coupe du Monde 2026.

# Charte éditoriale (extrait)
{style_excerpt[:2500]}

# News à traiter
TITRE : {title}
RÉSUMÉ : {summary}
SOURCE : {src_name} — {src_url}

# Mission
Écris un article ORIGINAL en français (600-900 mots) basé sur cette info. PAS de plagiat — reformule, ajoute du contexte, des stats si tu en connais (sans inventer), des liens d'analyse.

# Contraintes strictes
- N'invente AUCUNE déclaration, AUCUN score, AUCUNE statistique.
- Cite la source à la fin avec un lien.
- Style factuel mais vibrant (cf. charte).
- Si c'est un sujet Maroc → ton fraternel, ajoute "Dima Maghrib" ou similaire en conclusion.
- Si c'est un sujet CR7 → célébration mesurée.
- Si c'est un sujet WC 2026 → contextualise avec la date du coup d'envoi (11 juin 2026).

# Format de sortie — RESPECTE EXACTEMENT cette structure JSON
{{
  "title_fr": "Titre 50-60 caractères max, mot-clé en début",
  "title_meta": "Titre méta (peut être le même)",
  "lead_fr": "Chapeau de 50-80 mots qui répond à qui-quoi-quand-où",
  "kicker": "MAROC|PORTUGAL|CR7|WC 2026|FOOT",
  "h1": "Titre H1 affiché en page (peut être plus long que title_fr)",
  "body_html": "<h2>Section 1</h2><p>...</p><h2>Section 2</h2><p>...</p>...",
  "keywords": "mot-clé1, mot-clé2, ... (8-12)",
  "tag_emoji": "⚽|🏆|🇲🇦|🇵🇹|🌍"
}}

UNIQUEMENT le JSON, pas de markdown autour, pas d'explication."""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    # Strip ```json ... ``` if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    return data


def build_html_page(data: dict, item: dict, slug: str) -> str:
    title = data["title_fr"]
    lead = data["lead_fr"]
    body = data["body_html"]
    kicker = data["kicker"]
    h1 = data.get("h1", title)
    keywords = data["keywords"]
    emoji = data.get("tag_emoji", "⚽")
    url = f"{SITE}/blog/{slug}.html"
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    src_url = item.get("url", "")
    src_name = item.get("primary_source") or item.get("source") or "source"
    if isinstance(src_name, dict):
        src_name = src_name.get("name") or "source"

    meta_desc = re.sub(r"\s+", " ", lead).strip()[:158]
    from html import escape as h

    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "description": meta_desc,
        "image": item.get("image_url") or f"{SITE}/og-image.png",
        "author": {"@type": "Organization", "name": "To1000.com"},
        "publisher": {
            "@type": "Organization", "name": "To1000.com",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/favicon.png"}
        },
        "datePublished": now_iso,
        "dateModified": now_iso,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "articleSection": kicker,
        "inLanguage": "fr-FR",
    }
    if src_url:
        ld["isBasedOn"] = src_url

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}};gtag('js',new Date());gtag('config','{GA}');</script>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h(title)} | To1000.com</title>
<meta name="description" content="{h(meta_desc)}">
<meta name="keywords" content="{h(keywords)}">
<meta name="author" content="To1000.com"><meta name="robots" content="index, follow">
<meta name="theme-color" content="#060606">
<meta property="og:type" content="article">
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(meta_desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{h(item.get('image_url') or SITE + '/og-image.png')}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:site_name" content="To1000.com"><meta property="og:locale" content="fr_FR">
<meta property="article:published_time" content="{now_iso}">
<meta property="article:section" content="{h(kicker)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{h(title)}"><meta name="twitter:description" content="{h(meta_desc)}">
<meta name="twitter:image" content="{h(item.get('image_url') or SITE + '/og-image.png')}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{url}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, indent=2)}</script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#060606;color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,sans-serif;line-height:1.7}}
.nav{{padding:1rem 1.5rem;border-bottom:1px solid #222;display:flex;gap:1rem;align-items:center;position:sticky;top:0;background:rgba(6,6,6,0.95);backdrop-filter:blur(10px);z-index:100;flex-wrap:wrap}}
.nav a{{color:#aaa;text-decoration:none;font-weight:600;font-size:0.9rem}}.nav .logo{{color:#fff;font-weight:900;font-size:1.2rem}}.nav .logo span{{color:#D4AF37}}
article{{max-width:760px;margin:2rem auto;padding:0 1.5rem}}
.kicker{{display:inline-block;background:rgba(212,175,55,0.15);color:#D4AF37;padding:0.2rem 0.7rem;border-radius:4px;font-size:0.75rem;font-weight:800;letter-spacing:0.05em;text-transform:uppercase}}
h1{{font-size:clamp(1.6rem,4.5vw,2.6rem);font-weight:900;line-height:1.2;margin:1rem 0;letter-spacing:-0.02em}}
.lead{{font-size:1.15rem;color:#ddd;margin:1.2rem 0;font-weight:500}}
.meta{{color:#888;font-size:0.85rem;margin-bottom:1.5rem;display:flex;gap:0.8rem;align-items:center;flex-wrap:wrap}}
.body h2{{margin-top:2rem;margin-bottom:0.6rem;font-size:1.3rem;font-weight:800;color:#fff}}
.body h3{{margin-top:1.5rem;margin-bottom:0.5rem;font-size:1.1rem;font-weight:700;color:#D4AF37}}
.body p{{margin-bottom:1rem;color:#ddd}}
.body a{{color:#D4AF37}}
.disclaimer{{background:#111;border:1px solid #222;border-radius:8px;padding:1rem;margin:2rem 0;font-size:0.85rem;color:#888}}
.source-link{{color:#888;margin:1.5rem 0;padding-top:1rem;border-top:1px solid #222;font-size:0.9rem}}
.footer{{border-top:1px solid #222;padding:2rem;text-align:center;font-size:0.85rem;color:#777}}
</style>
</head>
<body>
<nav class="nav">
  <a class="logo" href="/">To<span>1000</span>.com</a>
  <a href="/">Accueil</a><a href="/world-cup/">CDM 2026</a><a href="/world-cup/maroc/">🇲🇦 Maroc</a><a href="/world-cup/portugal/">🇵🇹 Portugal</a><a href="/goals.html">Compteur CR7</a><a href="/blog/">Blog</a>
</nav>
<article>
  <span class="kicker">{emoji} {h(kicker)}</span>
  <h1>{h(h1)}</h1>
  <div class="meta">
    <span>📅 {datetime.now().strftime('%d %B %Y')}</span>
    <span>· Article rédigé par notre IA éditoriale</span>
  </div>
  <p class="lead">{h(lead)}</p>
  <div class="body">
{body}
  </div>
  <p class="source-link">📎 Sur la base d'une dépêche {h(str(src_name))} : <a href="{h(src_url)}" rel="noopener nofollow" target="_blank">consulter la source →</a></p>
  <div class="disclaimer">
    <strong>À propos de cette analyse</strong> — Cet article a été rédigé par notre système éditorial automatisé (Claude API) sur la base d'une dépêche externe sourcée ci-dessus. Toute information factuelle est susceptible d'évoluer. Pas d'affiliation officielle.
  </div>
</article>
<footer class="footer"><p>© 2026 To1000.com · <a href="/" style="color:#aaa">Accueil</a> · <a href="/world-cup/" style="color:#aaa">Hub CDM 2026</a></p></footer>
</body>
</html>
"""


def append_to_posts_json(data: dict, slug: str):
    """Met à jour public/blog/posts.json pour que l'article apparaisse sur /blog/."""
    if not POSTS_JSON.exists():
        return
    try:
        with open(POSTS_JSON, encoding="utf-8") as f:
            posts_data = json.load(f)
    except Exception:
        return
    new_post = {
        "slug": slug,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "tag": data.get("kicker", "FOOT"),
        "tagColor": "#000",
        "tagBg": "#d4af37",
        "emoji": data.get("tag_emoji", "⚽"),
        "title_i18n": {"fr": data["title_fr"], "en": data["title_fr"], "es": data["title_fr"], "ar": data["title_fr"]},
        "excerpt_i18n": {"fr": data["lead_fr"], "en": data["lead_fr"], "es": data["lead_fr"], "ar": data["lead_fr"]},
        "ai_generated": True,
    }
    posts_data.setdefault("posts", []).insert(0, new_post)
    # Cap at 50 to avoid bloat
    posts_data["posts"] = posts_data["posts"][:50]
    POSTS_JSON.write_text(json.dumps(posts_data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_publication(item: dict, slug: str, words: int):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "role": "claude_journalist",
        "slug": slug,
        "url": f"/blog/{slug}.html",
        "source_news_id": item.get("id"),
        "source_url": item.get("url"),
        "score": item.get("score"),
        "words": words,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    if not NEWS_JSON.exists():
        print(f"⚠ {NEWS_JSON} introuvable — run news_aggregator.py first")
        return 1
    if not STYLE_GUIDE.exists():
        print(f"⚠ {STYLE_GUIDE} introuvable")
        return 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠ ANTHROPIC_API_KEY non set — pas d'appel API possible")
        return 1

    with open(NEWS_JSON, encoding="utf-8") as f:
        news = json.load(f)
    items = news.get("items", [])
    style = STYLE_GUIDE.read_text(encoding="utf-8")

    covered = already_covered()
    candidates = pick_candidates(items, covered, MAX_ARTICLES_PER_RUN)

    if not candidates:
        print(f"  ℹ Aucun item score ≥ {MIN_SCORE} non encore couvert. Skip.")
        return 0

    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for item in candidates:
        title = item.get("title_fr") or item.get("title", "")[:60]
        print(f"  → rédaction de : {title[:70]}...")
        try:
            data = call_claude(item, style)
        except Exception as e:
            print(f"    ✗ erreur API : {e}")
            continue

        # Slug daté pour éviter collisions
        base_slug = slugify(data["title_fr"])
        slug = f"{datetime.now().strftime('%Y%m%d')}-{base_slug}"[:80]
        html = build_html_page(data, item, slug)
        out = BLOG_DIR / f"{slug}.html"
        out.write_text(html, encoding="utf-8")
        word_count = len(re.sub(r"<[^>]+>", " ", data["body_html"]).split())
        log_publication(item, slug, word_count)
        append_to_posts_json(data, slug)
        print(f"    ✓ /blog/{slug}.html ({word_count} mots)")
        written += 1

    print(f"\n✅ {written}/{len(candidates)} articles publiés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
