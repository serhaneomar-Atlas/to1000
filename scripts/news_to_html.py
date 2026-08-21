#!/usr/bin/env python3
"""
news_to_html.py — Génère une page HTML SEO-ready par item de news.json.

Lance automatiquement après news_aggregator.py (cf. EDITORIAL/playbooks/DAILY_BRIEF.md).

Input  : public/news.json (50 items max)
Output : public/news/{slug}.html × N
         public/news/index.html (liste de toutes les news, paginée)

Format SEO complet :
- <title>, <meta description, keywords>
- <link rel="canonical">, hreflang
- OG + Twitter card
- JSON-LD NewsArticle
- Image hero si dispo dans l'item
- Lien retour vers /coupe-du-monde/, /goals.html
- Disclaimer fan site

Usage:
  python scripts/news_to_html.py             # full rebuild
  python scripts/news_to_html.py --dry-run   # n'écrit pas
"""

from __future__ import annotations
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from html import escape as h

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
NEWS_JSON = PROJECT_DIR / "public" / "news.json"
NEWS_DIR = PROJECT_DIR / "public" / "news"
SITE = "https://to1000.com"
GA = "G-4V8Y6C38VN"


# ─── Helpers ─────────────────────────────────────────────────────────

def slugify(s: str, maxlen: int = 80) -> str:
    """Produce stable, ascii-only, URL-safe slug."""
    s = s.lower()
    # Replace accented characters (rough — for FR/EN/AR mix)
    repl = str.maketrans({
        "à":"a","á":"a","â":"a","ã":"a","ä":"a","å":"a","ą":"a",
        "ç":"c","č":"c","ć":"c",
        "é":"e","è":"e","ê":"e","ë":"e","ę":"e",
        "í":"i","ì":"i","î":"i","ï":"i",
        "ñ":"n","ń":"n",
        "ó":"o","ò":"o","ô":"o","õ":"o","ö":"o","ø":"o",
        "ß":"ss","š":"s","ś":"s",
        "ú":"u","ù":"u","û":"u","ü":"u",
        "ý":"y","ÿ":"y",
        "ž":"z","ź":"z","ż":"z",
        "Œ":"oe","œ":"oe","Æ":"ae","æ":"ae",
        "‘":"-","’":"-","ʼ":"-",
        "“":"","”":"","«":"","»":"",
    })
    s = s.translate(repl)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if len(s) > maxlen:
        s = s[:maxlen].rstrip("-")
    return s or "untitled"


def classify_kind(item: dict) -> str:
    t = ((item.get("title_fr") or item.get("title") or "")
         + " " + (item.get("summary") or "")).lower()
    if re.search(r"ronaldo|cr7|al nassr|al-nassr", t):
        return "cr7"
    if re.search(r"maroc|morocco|hakimi|regragui|lions de l['']atlas", t):
        return "maroc"
    if re.search(r"portugal|seleção|fernandes(?! belga)|martinez portugal", t):
        return "portugal"
    if re.search(r"coupe du monde|world cup|wc 2026|cdm 2026|mondial", t):
        return "wc"
    return "foot"


def best_image(item: dict) -> str | None:
    return item.get("image_url") or item.get("image") or None


# Moteurs dont la sortie est montrable : la chaîne éditoriale complète, son
# raccourci, et la traduction Gemini avec glossaire. MyMemory traduit mot à
# mot (« أول قبطان لبرجة », « première capitaine … et Aitana et Graham
# entrent ») : ce brouillon sert de matière première, jamais d'affichage.
# `redaction` = articles écrits par la rédaction To1000 (custom_news.json) —
# du travail humain validé, jamais à masquer.
ENGINES_AFFICHABLES = {"gemini-editor", "gemini-edi", "gemini", "redaction"}


def publishable(item: dict, lang: str) -> bool:
    """La version `lang` peut-elle être montrée à un lecteur ?"""
    e = (item.get("i18n") or {}).get(lang) or {}
    if not (e.get("title") or e.get("summary")):
        return False
    src = ((item.get("primary_source") or {}).get("lang") or "")[:2].lower()
    if lang == src:
        return True                      # texte original de la source
    return (not e.get("needs_translation")
            and e.get("engine") in ENGINES_AFFICHABLES)


def best_title(item: dict, lang: str = "fr") -> str:
    if lang == "fr":
        if publishable(item, "fr"):
            return (item.get("title_fr")
                    or (item.get("i18n", {}).get("fr") or {}).get("title")
                    or item.get("title") or "Sans titre")
        # Brouillon machine → texte original de la source, jamais le mot-à-mot.
        return item.get("title") or "Sans titre"
    return item.get("title") or "Untitled"


# Le fil agrège de l'espagnol, de l'anglais, de l'arabe, de l'allemand, du
# portugais… Écrire « texte original (anglais) » en dur était faux dans la
# majorité des cas — et un lecteur qui déplie un texte espagnol sous un label
# « anglais » n'a plus de raison de nous croire sur le reste.
SOURCE_LANG_LABELS = {
    "en": "anglais", "es": "espagnol", "fr": "français", "ar": "arabe",
    "de": "allemand", "it": "italien", "pt": "portugais", "nl": "néerlandais",
}


def source_lang_label(item: dict) -> str:
    """« espagnol », « arabe »… ou chaîne vide si la langue est inconnue."""
    lang = ((item.get("primary_source") or {}).get("lang")
            or item.get("source_lang") or "").lower()[:2]
    return SOURCE_LANG_LABELS.get(lang, "")


def body_parts(item: dict, lang: str = "fr") -> tuple[str, list]:
    """(format, éléments) du développement rédigé par le conseil de rédaction.

    Format vaut "brief" / "deep" (paragraphes) ou "bullets" (puces). Un article
    non encore enrichi renvoie une liste vide — la page se rend alors comme
    avant, avec le seul lead.
    """
    entry = (item.get("i18n", {}) or {}).get(lang) or {}
    parts = [str(p).strip() for p in (entry.get("body") or []) if str(p).strip()]
    fmt = entry.get("format") or "brief"
    return (fmt if fmt in ("brief", "deep", "bullets") else "brief"), parts


def best_summary(item: dict, lang: str = "fr") -> str:
    if lang == "fr":
        if publishable(item, "fr"):
            return (item.get("summary_fr")
                    or (item.get("i18n", {}).get("fr") or {}).get("summary")
                    or item.get("summary") or "")
        return item.get("summary") or ""
    return item.get("summary") or ""


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except Exception:
            return None


# ─── Page generation ─────────────────────────────────────────────────

_STOP = set("le la les un une des de du et à au aux pour avec sur dans par the of in on for and to vs his her into over after".split())
def _kw(it):
    t = (best_title(it, "fr") + " " + best_title(it, "en")).lower()
    return set(w for w in re.findall(r"[a-zà-ÿ0-9]{4,}", t) if w not in _STOP)

def find_related(item: dict, all_items: list, n: int = 4) -> list:
    """Other articles on OUR site sharing keywords (same topic boosted)."""
    mid = item.get("id"); mine = _kw(item); k0 = classify_kind(item)
    scored = []
    for o in all_items or []:
        if o.get("id") == mid:
            continue
        s = len(mine & _kw(o))
        if classify_kind(o) == k0:
            s += 1
        if s > 0:
            scored.append((s, o))
    scored.sort(key=lambda x: -x[0])
    return [o for _, o in scored[:n]]

GENERIC_RELATED = {
    "cr7":  '<a href="/goals.html">📊 Compteur CR7 (975/1000)</a> · <a href="/news.html">📰 Toute l\'actu foot</a> · <a href="/coupe-du-monde/equipe/portugal/">🇵🇹 Portugal WC 2026</a>',
    "wc":   '<a href="/coupe-du-monde/">🌍 Hub Coupe du Monde 2026</a> · <a href="/news.html">📰 News</a> · <a href="/coupe-du-monde/equipe/maroc/">🇲🇦 Maroc</a>',
    "maroc":'<a href="/coupe-du-monde/equipe/maroc/">🇲🇦 Page Maroc WC</a> · <a href="/news.html">📰 News</a> · <a href="/coupe-du-monde/">Hub WC</a>',
    "portugal":'<a href="/coupe-du-monde/equipe/portugal/">🇵🇹 Page Portugal WC</a> · <a href="/goals.html">Compteur CR7</a> · <a href="/news.html">📰 News</a>',
    "foot": '<a href="/news.html">📰 Toute l\'actu foot</a> · <a href="/coupe-du-monde/">🌍 Hub WC 2026</a> · <a href="/goals.html">Compteur CR7</a>',
}

NEWS_INDEX_REDIRECT = (
    '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
    '<meta http-equiv="refresh" content="0; url=/news">'
    '<link rel="canonical" href="https://to1000.com/news">'
    '<meta name="robots" content="noindex"><title>News — To1000.com</title>'
    '<script>location.replace("/news")</script></head>'
    '<body style="background:#05070b;color:#eef2f6;font-family:sans-serif;padding:2rem">'
    'Redirection vers <a href="/news" style="color:#f2c14e">/news</a>…</body></html>'
)


def render_article(item: dict, all_items: list | None = None) -> str:
    kind = classify_kind(item)
    title_fr = best_title(item, "fr")
    summary_fr = best_summary(item, "fr")
    title_en = best_title(item, "en")
    summary_en = best_summary(item, "en")
    img = best_image(item)
    pub = parse_date(item.get("published_at") or item.get("published"))
    pub_iso = pub.isoformat() if pub else datetime.now(timezone.utc).isoformat()
    mod = parse_date(item.get("updated_at") or item.get("fetched_at"))
    mod_iso = mod.isoformat() if mod else pub_iso
    pub_human = pub.strftime("%-d %B %Y") if pub and sys.platform != "win32" else (pub.strftime("%d %B %Y") if pub else "")
    slug = item.get("slug") or item.get("id") or slugify(title_fr)
    url = f"{SITE}/news/{slug}"  # URL propre (Cloudflare sert {slug}.html)
    original_url = item.get("url") or ""
    _src = item.get("primary_source") or item.get("source") or "Source"
    if isinstance(_src, dict):
        source = _src.get("name") or _src.get("title") or _src.get("url") or "Source"
    else:
        source = str(_src)

    # OG/Twitter image : carte brandée (social_card.py, 1200x630) si elle existe,
    # pour que les auto-posts du LIEN (Make.com → Facebook) affichent NOTRE carte
    # et pas l'image du journal source. JPEG d'abord (natif depuis 2026-07-01,
    # exigence Instagram), .png legacy sinon. Fallback : image de l'article.
    item_id = item.get("id") or ""
    cards_dir = PROJECT_DIR / "public" / "social" / "cards"
    if item_id and (cards_dir / f"{item_id}.jpg").exists():
        og_img = f"{SITE}/social/cards/{item_id}.jpg"
    elif item_id and (cards_dir / f"{item_id}.png").exists():
        og_img = f"{SITE}/social/cards/{item_id}.png"
    else:
        og_img = img or f"{SITE}/og-image.png"

    # Truncate description for meta — cut on a word boundary (~155 chars) + "…"
    _raw_desc = re.sub(r"\s+", " ", (summary_fr or title_fr)).strip()
    if len(_raw_desc) > 155:
        _cut = _raw_desc[:155]
        _sp = _cut.rfind(" ")
        if _sp > 60:  # avoid an absurdly short cut if no early space is found
            _cut = _cut[:_sp]
        meta_desc = h(_cut.rstrip(" ,.;:—-") + "…")
    else:
        meta_desc = h(_raw_desc)
    # headline ≤ 110 chars (Google NewsArticle guideline)
    _headline = title_fr if len(title_fr) <= 110 else title_fr[:109].rstrip() + "…"

    # Keywords from kind + title words
    kw_base = {
        "cr7":  "Cristiano Ronaldo, CR7, Al Nassr, but Ronaldo, compteur 1000",
        "wc":   "Coupe du Monde 2026, World Cup 2026, FIFA, USA Canada Mexique",
        "maroc":"Maroc Coupe du Monde 2026, Lions de l'Atlas, Hakimi, Regragui",
        "portugal":"Portugal Coupe du Monde 2026, A Seleção, Ronaldo, Bruno Fernandes",
        "foot": "football, news foot, transferts, Champions League, Ligue 1",
    }[kind]
    keywords = h(kw_base + ", to1000.com")

    kind_label = {"cr7":"CR7","wc":"WC 2026","maroc":"MAROC","portugal":"PORTUGAL","foot":"FOOT"}[kind]

    # La page est rendue en français (canonique SEO), mais le lecteur qui
    # arrive depuis /news en arabe, espagnol ou anglais doit la lire dans SA
    # langue : on embarque les 4 versions et un script les permute côté client
    # (même clé localStorage `to1000_lang` que news.html). Avant ça, un titre
    # arabe cliqué ouvrait une page française — rupture immédiate.
    _i18n_payload = {}
    for _l in ("fr", "en", "es", "ar"):
        _e = (item.get("i18n") or {}).get(_l) or {}
        if not publishable(item, _l):
            # Jamais de brouillon machine à l'écran : la langue non prête
            # affiche le texte ORIGINAL de la source (dir=auto côté client).
            _i18n_payload[_l] = {
                "title": item.get("title") or "",
                "summary": item.get("summary") or "",
                "body": [], "format": "brief", "fallback": True,
            }
            continue
        _i18n_payload[_l] = {
            "title": _e.get("title") or "",
            "summary": _e.get("summary") or "",
            "body": [str(x) for x in (_e.get("body") or [])],
            "format": _e.get("format") or "brief",
        }
    _src_l = ((item.get("primary_source") or {}).get("lang") or "")[:2].lower()
    _ui = {
        "fr": {"orig": "Voir le texte original", "related": "À lire aussi", "src": "Source",
               "ln": {"en": "anglais", "es": "espagnol", "fr": "français", "ar": "arabe",
                       "de": "allemand", "it": "italien", "pt": "portugais"}},
        "en": {"orig": "View the original text", "related": "Also read", "src": "Source",
               "ln": {"en": "English", "es": "Spanish", "fr": "French", "ar": "Arabic",
                       "de": "German", "it": "Italian", "pt": "Portuguese"}},
        "es": {"orig": "Ver el texto original", "related": "Leer también", "src": "Fuente",
               "ln": {"en": "inglés", "es": "español", "fr": "francés", "ar": "árabe",
                       "de": "alemán", "it": "italiano", "pt": "portugués"}},
        "ar": {"orig": "عرض النص الأصلي", "related": "اقرأ أيضاً", "src": "المصدر",
               "ln": {"en": "الإنجليزية", "es": "الإسبانية", "fr": "الفرنسية", "ar": "العربية",
                       "de": "الألمانية", "it": "الإيطالية", "pt": "البرتغالية"}},
    }
    # json.dumps puis neutralisation de </script> — un titre contenant cette
    # séquence casserait la page entière.
    _payload_js = json.dumps({"i18n": _i18n_payload, "src_lang": _src_l, "ui": _ui},
                             ensure_ascii=False).replace("</", "<\\/")

    # Body (use English summary too if available, like a richer page)
    body_html = ""
    if summary_fr:
        body_html += f"<p class=\"lead\" id=\"art-lead\">{h(summary_fr)}</p>"

    # Développement rédigé (2-3 paragraphes ou puces) quand le conseil de
    # rédaction l'a produit — c'est ce qui distingue une brève d'une carte.
    # Le conteneur a un id : le script de langue le re-rend dans la langue
    # choisie par le lecteur.
    _fmt, _parts = body_parts(item, "fr")
    body_html += "<div id=\"art-dev\">"
    if _parts:
        if _fmt == "bullets":
            _lis = "".join(f"<li>{h(p)}</li>" for p in _parts)
            body_html += f"<ul class=\"essentiel\">{_lis}</ul>"
        else:
            body_html += "".join(f"<p>{h(p)}</p>" for p in _parts)
    body_html += "</div>"

    if summary_en and summary_en != summary_fr:
        _lang = source_lang_label(item)
        _label = f"Voir le texte original ({_lang})" if _lang else "Voir le texte original"
        body_html += f"<details class=\"original\"><summary id=\"art-orig-label\">{h(_label)}</summary><p>{h(summary_en)}</p></details>"

    # JSON-LD NewsArticle (enriched)
    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": _headline,
        "description": meta_desc,
        "image": [img] if img else [f"{SITE}/og-image.png"],
        "author": {"@type": "Organization", "name": "To1000.com", "url": SITE},
        "publisher": {
            "@type": "Organization", "name": "To1000.com", "url": SITE,
            "logo": {"@type": "ImageObject", "url": f"{SITE}/favicon.png", "width": 512, "height": 512}
        },
        "datePublished": pub_iso,
        "dateModified": mod_iso,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "articleSection": kind_label,
        "inLanguage": "fr-FR",
    }
    if original_url:
        ld["isBasedOn"] = original_url
    ld_json = json.dumps(ld, ensure_ascii=False, indent=2)

    # JSON-LD BreadcrumbList (Accueil > News > article)
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "News", "item": SITE + "/news"},
            {"@type": "ListItem", "position": 3, "name": title_fr, "item": url},
        ],
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # Source link section
    source_html = ""
    if original_url:
        source_html = (
            f'<p class="source-link">📎 Source originale : '
            f'<a href="{h(original_url)}" rel="noopener nofollow" target="_blank">{h(source)} →</a></p>'
        )

    # Image hero (anti-CLS: dimensions + aspect-ratio, prioritised LCP)
    hero_html = ""
    if img:
        hero_html = (
            f'<figure class="hero-img">'
            f'<img src="{h(img)}" alt="{h(title_fr)}" width="1200" height="630" '
            f'style="aspect-ratio:1200/630" loading="eager" fetchpriority="high" decoding="async">'
            f'</figure>'
        )

    # Related ARTICLES on our site (keyword overlap) + generic nav fallback
    _rel = find_related(item, all_items or [], 4)
    if _rel:
        _cards = "".join(
            f'<a class="rel-card" href="/news/{(ri.get("slug") or ri.get("id"))}.html">'
            f'<span class="rel-t">{h(best_title(ri, "fr"))}</span>'
            f'<span class="rel-s">{h((ri.get("primary_source") or {}).get("name", "") if isinstance(ri.get("primary_source"), dict) else "")}</span>'
            f'</a>' for ri in _rel
        )
        related = f'<div class="rel-grid">{_cards}</div>'
    else:
        related = GENERIC_RELATED[kind]

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<script src="/consent.js"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA}');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="dns-prefetch" href="https://fonts.googleapis.com">
<link rel="dns-prefetch" href="https://fonts.gstatic.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@400;500;600;700&family=Hanken+Grotesk:wght@400;500;600;700&family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
<title>{h(title_fr)} | To1000.com</title>
<meta name="description" content="{meta_desc}">
<meta name="keywords" content="{keywords}">
<meta name="author" content="To1000.com">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#05070b">
<meta property="og:type" content="article">
<meta property="og:title" content="{h(title_fr)}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{h(og_img)}">
<meta property="og:image:secure_url" content="{h(og_img)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{h(title_fr)}">
<meta property="og:site_name" content="To1000.com">
<meta property="og:locale" content="fr_FR">
<meta property="article:published_time" content="{pub_iso}">
<meta property="article:modified_time" content="{mod_iso}">
<meta property="article:section" content="{kind_label}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@to1000com">
<meta name="twitter:title" content="{h(title_fr)}">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="{h(og_img)}">
<meta name="twitter:image:alt" content="{h(title_fr)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.png" type="image/png" sizes="32x32">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<script type="application/ld+json">
{ld_json}
</script>
<script type="application/ld+json">
{breadcrumb_json}
</script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #05070b; color: #eef2f6;
  font-family: 'Hanken Grotesk', -apple-system, sans-serif;
  line-height: 1.7;
}}
.nav {{
  padding: 1rem 1.5rem; border-bottom: 1px solid #1d2530;
  display: flex; justify-content: space-between; align-items: center;
  position: sticky; top: 0; background: rgba(6,6,6,0.95); backdrop-filter: blur(10px); z-index: 100;
  flex-wrap: wrap; gap: 0.5rem;
}}
.nav .logo {{font-family:'Anton',sans-serif; font-weight: 900; font-size: 1.2rem; letter-spacing: -0.02em; color: #fff; text-decoration: none; }}
.nav .logo .accent {{ color: #f2c14e; }}
.nav .links {{ display: flex; gap: 1rem; flex-wrap: wrap; }}
.nav .links a {{ color: #aaa; text-decoration: none; font-size: 0.9rem; font-weight: 600; }}
.nav .links a:hover {{ color: #f2c14e; }}
article {{ max-width: 760px; margin: 2rem auto; padding: 0 1.5rem; }}
.kind {{ display: inline-block; padding: 0.2rem 0.7rem; background: rgba(242,193,78,0.15); color: #f2c14e; border-radius: 4px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; }}
.kind.maroc {{ background: rgba(193,39,45,0.15); color: #ff6b6b; }}
.kind.portugal {{ background: rgba(0,102,0,0.15); color: #4caf50; }}
.kind.wc {{ background: rgba(0,153,255,0.15); color: #4eb3ff; }}
h1 {{ font-size: clamp(1.6rem, 4.5vw, 2.6rem); font-weight: 900; line-height: 1.2; margin: 1rem 0; letter-spacing: -0.02em; }}
.meta {{ color: #9aa6b4; font-size: 0.85rem; margin-bottom: 1.5rem; display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap; }}
.hero-img {{ margin: 0 0 1.5rem; }}
.hero-img img {{ width: 100%; height: auto; border-radius: 10px; }}
.lead {{ font-size: 1.1rem; color: #ddd; margin-bottom: 1rem; }}
.essentiel {{ margin: 1.2rem 0; padding-left: 1.15rem; color: #d6dde5; }}
[dir="rtl"] body, [dir="rtl"] article {{ font-family: 'Cairo', 'Hanken Grotesk', sans-serif; }}
[dir="rtl"] .essentiel {{ padding-left: 0; padding-right: 1.15rem; }}
.essentiel li {{ margin-bottom: 0.55rem; line-height: 1.6; }}
.essentiel li::marker {{ color: #f2c14e; }}
.original {{ background: #0d1118; border: 1px solid #1d2530; border-radius: 8px; padding: 1rem; margin: 1.5rem 0; }}
.original summary {{ cursor: pointer; color: #f2c14e; font-weight: 700; }}
.original p {{ margin-top: 0.6rem; color: #bbb; }}
.source-link {{ color: #9aa6b4; font-size: 0.9rem; margin: 1.5rem 0; padding-top: 1rem; border-top: 1px solid #1d2530; }}
.source-link a {{ color: #f2c14e; }}
.related {{ background: linear-gradient(180deg, #0d1118 0%, #0a0d13 100%); border: 1px solid #1d2530; border-radius: 12px; padding: 1.2rem; margin: 2rem 0; }}
.related h2 {{ font-size: 1rem; color: #f2c14e; margin-bottom: 0.6rem; text-transform: uppercase; letter-spacing: 0.05em; }}
.related a {{ color: #ddd; text-decoration: none; }}
.related a:hover {{ color: #f2c14e; }}
.rel-grid {{ display:grid; grid-template-columns:1fr; gap:0.6rem; margin-top:0.5rem; }}
@media(min-width:560px){{ .rel-grid {{ grid-template-columns:1fr 1fr; }} }}
.rel-card {{ display:flex; flex-direction:column; gap:0.3rem; padding:0.7rem 0.85rem; border:1px solid #1d2530; border-radius:10px; background:#0d1118; text-decoration:none; transition:border-color .2s; }}
.rel-card:hover {{ border-color:#f2c14e; }}
.rel-t {{ color:#eaeaea; font-size:0.9rem; line-height:1.3; }}
.rel-s {{ color:#9aa6b4; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em; }}
.footer {{ border-top: 1px solid #1d2530; padding: 2rem 1.5rem; text-align: center; font-size: 0.85rem; color: #8a93a0; margin-top: 4rem; }}
.footer a {{ color: #aaa; }}
</style>
</head>
<body>
<nav class="nav">
  <a class="logo" href="/">To<span class="accent">1000</span>.com</a>
  <div class="links">
    <a href="/">Accueil</a>
    <a href="/coupe-du-monde/">CDM 2026</a>
    <a href="/coupe-du-monde/equipe/maroc/">🇲🇦 Maroc</a>
    <a href="/coupe-du-monde/equipe/portugal/">🇵🇹 Portugal</a>
    <a href="/goals.html">Compteur CR7</a>
  </div>
</nav>
<article>
  <span class="kind {kind}">{kind_label}</span>
  <h1 id="art-title">{h(title_fr)}</h1>
  <div class="meta">
    <span>📅 {h(pub_human or 'Récent')}</span>
    <span>· Source : {h(source)}</span>
  </div>
  {hero_html}
  {body_html}
  {source_html}
  <div class="related">
    <h2>À lire aussi</h2>
    <p>{related}</p>
  </div>
</article>
<script>
(function(){{
  var D={_payload_js};
  var SUP=['fr','en','es','ar'];
  function detect(){{var u=new URLSearchParams(location.search).get('lang');if(u&&SUP.indexOf(u)>=0)return u;try{{var s=localStorage.getItem('to1000_lang');if(s&&SUP.indexOf(s)>=0)return s;}}catch(e){{}}var n=(navigator.language||'fr').slice(0,2).toLowerCase();return SUP.indexOf(n)>=0?n:'fr';}}
  function esc(t){{var d=document.createElement('div');d.textContent=t==null?'':t;return d.innerHTML;}}
  function apply(l){{
    var e=D.i18n[l];if(!e)return;
    var H=document.documentElement;H.lang=l;H.dir=(l==='ar')?'rtl':'ltr';
    if(e.fallback)H.dir='ltr';
    var t=document.getElementById('art-title');if(t&&e.title){{t.textContent=e.title;t.setAttribute('dir','auto');}}
    var ld=document.getElementById('art-lead');if(ld&&e.summary){{ld.textContent=e.summary;ld.setAttribute('dir','auto');}}
    var dev=document.getElementById('art-dev');
    if(dev){{
      if(e.body&&e.body.length){{
        dev.innerHTML=(e.format==='bullets')
          ?'<ul class="essentiel">'+e.body.map(function(p){{return '<li>'+esc(p)+'</li>';}}).join('')+'</ul>'
          :e.body.map(function(p){{return '<p>'+esc(p)+'</p>';}}).join('');
      }}else if(l!=='fr'){{dev.innerHTML='';}}
    }}
    var ui=D.ui[l]||D.ui.fr;
    var ol=document.getElementById('art-orig-label');
    if(ol){{var n=ui.ln[D.src_lang];ol.textContent=ui.orig+(n?' ('+n+')':'');}}
    var rel=document.querySelector('.related h2');if(rel)rel.textContent=ui.related;
    document.title=(e.title||document.title.split(' | ')[0])+' | To1000.com';
  }}
  var LANG=detect();
  if(LANG!=='fr')apply(LANG);
  // Mini-sélecteur : changer de langue sans repasser par /news.
  var nav=document.querySelector('.nav .links');
  if(nav){{SUP.forEach(function(l){{
    var a=document.createElement('a');a.href='#';a.textContent=l.toUpperCase();a.setAttribute('data-lang',l);
    a.style.cssText='font-size:0.8rem'+(l===LANG?';color:#f2c14e':'');
    a.onclick=function(ev){{ev.preventDefault();try{{localStorage.setItem('to1000_lang',l);}}catch(e){{}}
      if(l==='fr'){{location.reload();}}else{{LANG=l;apply(l);
        nav.querySelectorAll('a[data-lang]').forEach(function(x){{x.style.color=x.getAttribute('data-lang')===l?'#f2c14e':'';}});}}
    }};nav.appendChild(a);
  }});}}
}})();
</script>
<footer class="footer">
  <p>To1000.com est un site de fans <strong>non officiel</strong>. Cet article est un résumé automatique d'une source externe, traduit et structuré pour l'indexation. Pour le contenu original, suivre le lien source ci-dessus.</p>
  <p>© 2026 · <a href="/">Accueil</a> · <a href="/coupe-du-monde/">Hub WC</a> · <a href="/goals.html">Compteur CR7</a></p>
</footer>
</body>
</html>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args()

    if not NEWS_JSON.exists():
        print(f"⚠ {NEWS_JSON} introuvable — run news_aggregator.py first.")
        return 1

    with open(NEWS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    items = (data.get("items") or [])[:args.limit]
    if not items:
        print("⚠ No items in news.json")
        return 1

    NEWS_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    valid_slugs: set[str] = set()
    for item in items:
        title = best_title(item, "fr")
        slug = item.get("slug") or item.get("id") or slugify(title)
        valid_slugs.add(slug)
        out = NEWS_DIR / f"{slug}.html"
        html = render_article(item, items)
        if args.dry_run:
            print(f"  [dry] {out.name} ({len(html)} bytes)")
            continue
        # Skip if identical (avoid touching files unnecessarily)
        if out.exists() and out.read_text(encoding="utf-8") == html:
            skipped += 1
            continue
        out.write_text(html, encoding="utf-8")
        written += 1

    # Clean up old slugs (not in current top 50) — but keep an "archive" dir
    # Conservative : only delete files older than 60 days
    # ... For now, just leave them. SEO-wise, having old indexed pages is fine.

    # news/index.html = redirection vers /news (la page liste ESTÁDIO avec photos).
    # On évite une 2e liste concurrente sans photos (contenu dupliqué = mauvais SEO).
    if not args.dry_run:
        (NEWS_DIR / "index.html").write_text(NEWS_INDEX_REDIRECT, encoding="utf-8")

    print(f"✅ {written} written, {skipped} unchanged, {len(items)} total")
    return 0


def render_index(items: list[dict]) -> str:
    cards = []
    for item in items:
        title = best_title(item, "fr")
        slug = item.get("slug") or item.get("id") or slugify(title)
        kind = classify_kind(item)
        kind_label = {"cr7":"CR7","wc":"WC 2026","maroc":"MAROC","portugal":"PORTUGAL","foot":"FOOT"}[kind]
        pub = parse_date(item.get("published_at"))
        date_h = pub.strftime("%d/%m") if pub else ""
        cards.append(f'<a class="card" href="/news/{slug}.html"><span class="k {kind}">{kind_label}</span><h3>{h(title)}</h3><time>{date_h}</time></a>')
    cards_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<script src="/consent.js"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}};gtag('js',new Date());gtag('config','{GA}');</script>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@400;500;600;700&family=Hanken+Grotesk:wght@400;500;600;700&family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
<title>News · Toutes les actus foot, CR7, Coupe du Monde 2026 | To1000.com</title>
<meta name="description" content="Les dernières actualités foot agrégées 24h/24 : CR7, Coupe du Monde 2026, Maroc, Portugal, transferts, Champions League. Mises à jour toutes les 30 minutes.">
<link rel="canonical" href="{SITE}/news/">
<meta property="og:title" content="News foot live · CR7 · CDM 2026 · Maroc · Portugal">
<meta property="og:description" content="Toutes les actus foot, mises à jour H24.">
<meta property="og:url" content="{SITE}/news/">
<meta property="og:image" content="{SITE}/og-image.png">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#05070b;color:#eef2f6;font-family:'Hanken Grotesk',-apple-system,sans-serif;line-height:1.6}}
.nav{{padding:1rem 1.5rem;border-bottom:1px solid #1d2530;display:flex;gap:1rem;align-items:center;position:sticky;top:0;background:rgba(6,6,6,0.95);backdrop-filter:blur(10px);z-index:100}}
.nav a{{color:#aaa;text-decoration:none;font-weight:600}}
.nav .logo{{font-family:'Anton',sans-serif;color:#fff;font-weight:400;font-size:1.2rem}}.nav .logo span{{color:#f2c14e}}
header{{padding:3rem 1.5rem 1rem;text-align:center;max-width:800px;margin:0 auto}}
h1{{font-family:'Anton',sans-serif;font-size:clamp(2rem,5vw,3.4rem);font-weight:400;margin-bottom:1rem;background:linear-gradient(135deg,#fff 0%,#f2c14e 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.grid{{max-width:1100px;margin:2rem auto 4rem;padding:0 1.5rem;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}}
.card{{background:linear-gradient(180deg,#0d1118 0%,#0a0d13 100%);border:1px solid #1d2530;border-radius:10px;padding:1rem;text-decoration:none;color:inherit;display:flex;flex-direction:column;transition:all 0.2s}}
.card:hover{{border-color:#f2c14e;transform:translateY(-2px)}}
.k{{display:inline-block;background:rgba(242,193,78,0.15);color:#f2c14e;padding:0.15rem 0.5rem;border-radius:4px;font-size:0.7rem;font-weight:800;letter-spacing:0.05em;align-self:flex-start;margin-bottom:0.6rem}}
.k.maroc{{background:rgba(193,39,45,0.15);color:#ff6b6b}}.k.portugal{{background:rgba(0,102,0,0.15);color:#4caf50}}.k.wc{{background:rgba(0,153,255,0.15);color:#4eb3ff}}
h3{{font-size:0.95rem;font-weight:700;line-height:1.35;flex:1}}
time{{color:#8a93a0;font-size:0.75rem;margin-top:0.6rem}}
footer{{border-top:1px solid #1d2530;padding:2rem;text-align:center;font-size:0.85rem;color:#8a93a0}}
</style>
</head>
<body>
<nav class="nav">
  <a class="logo" href="/">To<span>1000</span>.com</a>
  <a href="/">Accueil</a><a href="/coupe-du-monde/">CDM 2026</a><a href="/coupe-du-monde/equipe/maroc/">🇲🇦 Maroc</a><a href="/coupe-du-monde/equipe/portugal/">🇵🇹 Portugal</a><a href="/goals.html">Compteur CR7</a>
</nav>
<header>
  <h1>📰 Toutes les actus foot</h1>
  <p style="color:#aaa">Aggrégées toutes les 30 minutes depuis 32 sources. CR7, Coupe du Monde 2026, Maroc, Portugal, big 5 européens.</p>
</header>
<div class="grid">
{cards_html}
</div>
<footer><p>© 2026 To1000.com · Site de fans non officiel. <a href="/coupe-du-monde/" style="color:#aaa">CDM 2026</a></p></footer>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
# end of file
