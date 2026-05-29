#!/usr/bin/env python3
"""
sitemap_generator.py — Régénère public/sitemap.xml à partir du contenu actuel.

Couvre :
  - Pages statiques (index, goals, blog, world-cup/*)
  - Blog posts (public/blog/*.html)
  - News pages (public/news/*.html) — générées par news_to_html.py
  - Pages WC (hub, portugal, maroc + ar)

Cron : déclenché après news_to_html.py et chaque fois qu'une page change.
"""

from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path
from html import escape as h

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
PUBLIC = PROJECT_DIR / "public"
SITE = "https://to1000.com"


# Pages statiques principales — priorité 1.0 / 0.9
HIGH_PRIORITY = [
    ("/",                          1.0, "daily"),
    ("/world-cup/",                1.0, "hourly"),
    ("/world-cup/maroc/",          0.95, "hourly"),
    ("/world-cup/maroc/ar/",       0.95, "hourly"),
    ("/world-cup/portugal/",       0.95, "hourly"),
    ("/goals.html",                0.9, "daily"),
    ("/blog/",                     0.8, "weekly"),
    ("/news/",                     0.85, "hourly"),
    ("/promise/",                  0.7, "weekly"),
    ("/analytics.html",            0.4, "monthly"),
]


def fmt_url(loc: str, lastmod: str, changefreq: str, priority: float,
            alternates: dict[str,str] | None = None) -> str:
    alt = ""
    if alternates:
        for lang, url in alternates.items():
            alt += f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{url}"/>\n'
    return f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
{alt}  </url>"""


def collect_blog() -> list[tuple[str, str]]:
    blog_dir = PUBLIC / "blog"
    out = []
    if not blog_dir.exists(): return out
    for p in sorted(blog_dir.glob("*.html")):
        if p.name in ("index.html", "_widgets.js", "posts.json"): continue
        rel = "/" + p.relative_to(PUBLIC).as_posix()
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
        out.append((SITE + rel, mtime))
    return out


def collect_news() -> list[tuple[str, str]]:
    news_dir = PUBLIC / "news"
    out = []
    if not news_dir.exists(): return out
    for p in sorted(news_dir.glob("*.html")):
        if p.name == "index.html": continue
        rel = "/" + p.relative_to(PUBLIC).as_posix()
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
        out.append((SITE + rel, mtime))
    return out


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    urls = []

    # 1. High-priority static pages
    for loc, prio, freq in HIGH_PRIORITY:
        url = SITE + loc
        alts = None
        # Add hreflang for maroc pages
        if loc == "/world-cup/maroc/":
            alts = {
                "fr": SITE + "/world-cup/maroc/",
                "ar": SITE + "/world-cup/maroc/ar/",
                "x-default": SITE + "/world-cup/maroc/",
            }
        elif loc == "/world-cup/maroc/ar/":
            alts = {
                "fr": SITE + "/world-cup/maroc/",
                "ar": SITE + "/world-cup/maroc/ar/",
                "x-default": SITE + "/world-cup/maroc/",
            }
        urls.append(fmt_url(url, today, freq, prio, alts))

    # 2. Blog posts
    for url, mtime in collect_blog():
        urls.append(fmt_url(url, mtime, "monthly", 0.8))

    # 3. News pages
    news_items = collect_news()
    for url, mtime in news_items:
        urls.append(fmt_url(url, mtime, "weekly", 0.6))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(urls) + "\n"
        '</urlset>\n'
    )

    out = PUBLIC / "sitemap.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"✅ sitemap.xml written: {len(urls)} URLs ({len(news_items)} news pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
