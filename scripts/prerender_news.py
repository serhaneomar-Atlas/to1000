#!/usr/bin/env python3
"""Prerender the news cards into public/news.html so crawlers (and no-JS users)
see real content instead of "Chargement…". The client JS re-renders on load in
the user's language; this bakes a French baseline into the static HTML for SEO.

Run after news_aggregator.py, before commit/deploy (see news-sync.yml).
"""
import json, re, html as _html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent / "public"
NEWS = ROOT / "news.json"
PAGE = ROOT / "news.html"
PLACEHOLDER = "/images/mockups/stadium-night.jpg"

def esc(s): return _html.escape(str(s or ""), quote=True)

def safe_url(u):
    u = str(u or "")
    return u if re.match(r"^https?://", u, re.I) else "#"

def css_url(u):
    # neutralize quotes/parens/spaces inside url('…')
    return re.sub(r"['\"()\s]", lambda m: "%%%02X" % ord(m.group(0)), str(u or ""))

def rel_time_fr(iso):
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        secs = (datetime.now(timezone.utc) - d).total_seconds()
        if secs < 3600:  return f"il y a {max(1, round(secs/60))} min"
        if secs < 86400: return f"il y a {round(secs/3600)} h"
        return f"il y a {round(secs/86400)} j"
    except Exception:
        return ""

def card(it):
    L = (it.get("i18n") or {}).get("fr") or {}
    title = L.get("title") or it.get("title") or ""
    summ = L.get("summary") or it.get("summary") or ""
    ps = it.get("primary_source") or {}
    sname = (ps.get("flag", "") + " " if ps.get("flag") else "") + (ps.get("name") or "Football")
    sc = int(it.get("source_count") or len(it.get("sources") or []) or 1)
    cred = (f'<span class="verif">✓</span>Vérifié · {sc} sources' if sc > 1 else esc(sname))
    img = it.get("image_url") if safe_url(it.get("image_url")) != "#" else PLACEHOLDER
    kind = '<span class="kindtag">CR7</span>' if it.get("kind") == "cr7" else ""
    return (
        f'<a class="card" href="/news/{esc(it.get("id"))}.html">'
        f'<span class="thumb" style="background-image:url(\'{css_url(img)}\')" aria-hidden="true">{kind}</span>'
        f'<span class="body"><span class="cat">{esc(sname)}</span><h4>{esc(title)}</h4>'
        + (f'<span class="sum">{esc(summ)}</span>' if summ else "")
        + f'<span class="meta"><span class="src">{cred}</span>'
        f'<time datetime="{esc(it.get("published_at"))}">{rel_time_fr(it.get("published_at"))}</time></span>'
        f'<span class="orig">Lire l\'article →</span></span></a>'
    )

def main():
    data = json.loads(NEWS.read_text(encoding="utf-8"))
    items = (data.get("items") or [])[:50]
    cards = "\n".join(card(it) for it in items)
    page = PAGE.read_text(encoding="utf-8")
    new_grid = f'<div class="news-grid" id="grid">\n{cards}\n</div>'
    page2 = re.sub(r'<div class="news-grid" id="grid">.*?</div>', lambda m: new_grid, page, count=1, flags=re.S)
    if page2 == page:
        print("prerender: grid container not found — no change"); return 1
    PAGE.write_text(page2, encoding="utf-8")
    print(f"prerender: baked {len(items)} news cards into news.html")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
