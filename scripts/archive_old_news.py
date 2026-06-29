#!/usr/bin/env python3
"""archive_old_news.py — Section « Archives » SEO-safe pour alléger le site.

Politique de rétention (choix Omar : ARCHIVER, pas supprimer) :
- Les articles de PLUS de ARCHIVE_AFTER_DAYS (défaut 7) jours sortent de la page
  d'accueil / liste active (déjà cappée à 50) et sont regroupés dans une page
  /news/archive (par mois). Les pages article restent EN PLACE (URLs stables,
  toujours indexées) → aucune perte SEO, aucune redirection, aucun 404.
- Lightening « ordinateur » : on ne réécrit que la page archive si son contenu
  change. Le pruning destructif (suppression de fichiers) reste OPT-IN via
  PRUNE_AFTER_DAYS (défaut 0 = désactivé) — à activer en connaissance du
  compromis SEO (un article supprimé = 404 / perte du référencement acquis).

Sortie : public/news/archive/index.html (ESTÁDIO, crawlable).
"""
from __future__ import annotations

import html
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_DIR = ROOT / "public" / "news"
ARCHIVE_DIR = NEWS_DIR / "archive"

ARCHIVE_AFTER_DAYS = int(os.environ.get("ARCHIVE_AFTER_DAYS", "7"))
PRUNE_AFTER_DAYS = int(os.environ.get("PRUNE_AFTER_DAYS", "0"))  # 0 = jamais supprimer

_DATE_RE = re.compile(r'"datePublished":\s*"([^"]+)"')
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
_OG_TITLE_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', re.I)

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _now() -> datetime:
    # Date passée via env pour rester déterministe en CI ; sinon UTC courant.
    iso = os.environ.get("NOW_ISO")
    if iso:
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def parse_iso(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def clean_title(raw: str) -> str:
    t = html.unescape(re.sub(r"\s+", " ", raw or "").strip())
    # retire les suffixes de marque courants
    for sep in (" — To1000", " | To1000", " - To1000", " · To1000"):
        i = t.find(sep)
        if i > 0:
            t = t[:i]
            break
    return t.strip()


def scan_articles():
    """Retourne [(date, slug, title)] pour chaque page article datée."""
    out = []
    for f in NEWS_DIR.glob("*.html"):
        if f.name == "index.html":
            continue
        try:
            raw = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = _DATE_RE.search(raw)
        if not m:
            continue
        dt = parse_iso(m.group(1))
        if not dt:
            continue
        tm = _OG_TITLE_RE.search(raw) or _TITLE_RE.search(raw)
        title = clean_title(tm.group(1)) if tm else f.stem
        out.append((dt, f.stem, title))
    return out


def render_archive(by_month: dict, total: int) -> str:
    sections = []
    for key in sorted(by_month.keys(), reverse=True):
        y, mo = key
        items = sorted(by_month[key], key=lambda x: x[0], reverse=True)
        rows = "\n".join(
            f'<li><a href="/news/{html.escape(slug)}">{html.escape(title)}</a>'
            f'<time datetime="{dt.date().isoformat()}">{dt.day:02d}/{mo:02d}</time></li>'
            for dt, slug, title in items
        )
        sections.append(
            f'<section class="mo"><h2>{MONTHS_FR[mo].capitalize()} {y} '
            f'<span>{len(items)}</span></h2><ul>{rows}</ul></section>'
        )
    body = "\n".join(sections) or '<p class="empty">Aucun article archivé pour le moment.</p>'
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archives — To1000.com</title>
<meta name="description" content="Toutes les actualités football archivées de To1000.com, classées par mois. {total} articles.">
<link rel="canonical" href="https://to1000.com/news/archive">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@400;600&family=Hanken+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#05070b;--gold:#f2c14e;--ink:#eef2f6;--muted:#8a93a0;--line:#1a1f29;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:'Hanken Grotesk',system-ui,sans-serif;line-height:1.5;padding:0 0 4rem}}
header{{padding:2.5rem 1.25rem 1.5rem;max-width:980px;margin:0 auto;border-bottom:1px solid var(--line)}}
.eyebrow{{font-family:'Oswald',sans-serif;letter-spacing:.18em;text-transform:uppercase;font-size:.72rem;color:var(--gold)}}
h1{{font-family:'Anton',sans-serif;font-size:clamp(2.2rem,6vw,3.6rem);letter-spacing:.01em;line-height:1;margin:.35rem 0 .5rem}}
.sub{{color:var(--muted);font-size:.95rem}}
.back{{display:inline-block;margin-top:1rem;color:var(--gold);text-decoration:none;font-family:'Oswald',sans-serif;text-transform:uppercase;letter-spacing:.1em;font-size:.8rem}}
main{{max-width:980px;margin:0 auto;padding:1.5rem 1.25rem}}
.mo{{margin:0 0 2rem}}
.mo h2{{font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:.06em;font-size:1.05rem;color:var(--ink);padding-bottom:.4rem;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:.6rem}}
.mo h2 span{{font-size:.75rem;color:var(--muted);font-weight:400}}
.mo ul{{list-style:none;margin:.6rem 0 0}}
.mo li{{display:flex;justify-content:space-between;gap:1rem;align-items:baseline;padding:.45rem 0;border-bottom:1px solid rgba(26,31,41,.5)}}
.mo li a{{color:var(--ink);text-decoration:none;font-size:.98rem}}
.mo li a:hover{{color:var(--gold)}}
.mo li time{{color:var(--muted);font-variant-numeric:tabular-nums;font-size:.82rem;flex:none}}
.empty{{color:var(--muted)}}
a:focus-visible{{outline:2px solid var(--gold);outline-offset:2px;border-radius:2px}}
</style>
</head>
<body>
<header>
<p class="eyebrow">To1000.com</p>
<h1>Archives</h1>
<p class="sub">{total} articles football classés par mois.</p>
<a class="back" href="/news">← Actualités récentes</a>
</header>
<main>
{body}
</main>
</body>
</html>"""


def main() -> int:
    if not NEWS_DIR.exists():
        print("[archive] public/news introuvable")
        return 0
    now = _now()
    arts = scan_articles()
    cutoff_days = ARCHIVE_AFTER_DAYS
    archived = [a for a in arts if (now - a[0]).days >= cutoff_days]

    by_month = defaultdict(list)
    for dt, slug, title in archived:
        by_month[(dt.year, dt.month)].append((dt, slug, title))

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    out = ARCHIVE_DIR / "index.html"
    html_out = render_archive(by_month, len(archived))
    prev = out.read_text(encoding="utf-8") if out.exists() else ""
    if prev != html_out:
        out.write_text(html_out, encoding="utf-8")
        print(f"[archive] /news/archive régénéré : {len(archived)} articles, {len(by_month)} mois")
    else:
        print(f"[archive] /news/archive inchangé ({len(archived)} articles)")

    # Pruning destructif — OPT-IN uniquement (compromis SEO assumé par Omar).
    if PRUNE_AFTER_DAYS > 0:
        pruned = 0
        for dt, slug, _ in arts:
            if (now - dt).days >= PRUNE_AFTER_DAYS:
                p = NEWS_DIR / f"{slug}.html"
                try:
                    p.unlink()
                    pruned += 1
                except OSError:
                    pass
        if pruned:
            print(f"[archive] PRUNE : {pruned} pages > {PRUNE_AFTER_DAYS}j supprimées")
    return 0


if __name__ == "__main__":
    sys.exit(main())
