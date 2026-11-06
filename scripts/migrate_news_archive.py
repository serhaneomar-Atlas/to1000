"""
migrate_news_archive.py — passe les anciens articles (public/news/*.html) à la
charte « journal du matin », sans toucher au contenu, au SEO ni aux liens.

Pourquoi : news_to_html.py ne régénère que les items présents dans news.json
(~50). Les ~31 700 articles plus anciens gardaient le modèle sombre « ESTÁDIO »
et il n'existe pas d'archive JSON pour les re-rendre.

Méthode, page par page :
1. On lit l'ancienne page : titre (h1), chapô, développement, texte original,
   lien et nom de la source, image, dates, traductions embarquées (var D=…)
   et liens « À lire aussi ».
2. On reconstruit l'item et on le rend avec render_article() — le modèle
   actuel, donc exactement le rendu des nouveaux articles.
3. SEO : on remet À L'IDENTIQUE le bloc de l'ancienne page, du <title> au
   dernier JSON-LD (description, Open Graph, Twitter, canonical, hreflang,
   NewsArticle, BreadcrumbList). Seule la couleur theme-color change.
4. Liens : les « À lire aussi » de l'ancienne page sont conservés.
5. Contrôles : canonical, bloc SEO, lien source et titre doivent se retrouver
   dans la nouvelle page ; sinon la page n'est pas réécrite (rapport).

Usage :
  python scripts/migrate_news_archive.py --dry-run --limit 20
  python scripts/migrate_news_archive.py --ids 000e75cffedf 00056666beb8
  python scripts/migrate_news_archive.py            # toute l'archive
"""
from __future__ import annotations

import argparse
import html as htmlmod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import news_to_html as N  # noqa: E402

NEWS_DIR = ROOT / "public" / "news"
NEW_MARK = "/css/edition.css"
SECTION_KIND = {"CR7": "cr7", "MAROC": "maroc", "PORTUGAL": "portugal",
                "WC 2026": "wc", "FOOT": "foot"}


def txt(s: str) -> str:
    """Texte brut d'un fragment HTML (balises retirées, entités décodées)."""
    s = re.sub(r"<[^>]+>", "", s or "")
    return htmlmod.unescape(s).strip()


def first(pattern: str, s: str, flags=re.S) -> str:
    m = re.search(pattern, s, flags)
    return m.group(1) if m else ""


def seo_block(page: str) -> str:
    """Du <title> jusqu'à la fin du dernier JSON-LD de l'en-tête."""
    head = page.split("</head>", 1)[0]
    a = head.find("<title>")
    ends = [m.end() for m in re.finditer(
        r'<script type="application/ld\+json">.*?</script>', head, re.S)]
    if a < 0 or not ends or ends[-1] < a:
        return ""
    return head[a:ends[-1]]


def jsonld_news(page: str) -> dict:
    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            d = json.loads(blk)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("@type") == "NewsArticle":
            return d
    return {}


def payload(page: str) -> dict:
    i = page.find("var D=")
    if i < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(page[i + 6:])
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def related_links(page: str) -> list[tuple[str, str, str]]:
    """[(href, titre, source)] des « À lire aussi » de l'ancienne page."""
    m = re.search(r'<div class="related">(.*?)</div>\s*</article>', page, re.S)
    zone = m.group(1) if m else ""
    out = []
    for a in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', zone, re.S):
        href, inner = a.group(1), a.group(2)
        t = txt(first(r'<span class="rel-t">(.*?)</span>', inner) or inner)
        src = txt(first(r'<span class="rel-s">(.*?)</span>', inner))
        if href and t:
            out.append((href, t, src))
    return out[:4]


def extract(page: str, item_id: str) -> dict | None:
    body = page.split("<body", 1)[-1]
    title = txt(first(r"<h1[^>]*>(.*?)</h1>", body))
    lead = txt(first(r'<p class="lead"[^>]*>(.*?)</p>', body))
    m = re.search(r'<a href="([^"]+)" rel="noopener nofollow"[^>]*>(.*?)</a>', body, re.S)
    src_url = htmlmod.unescape(m.group(1)) if m else ""
    src_name = re.sub(r"\s*→\s*$", "", txt(m.group(2))) if m else ""
    if not title or not src_url:
        return None

    ld = jsonld_news(page)
    img = ""
    if isinstance(ld.get("image"), list) and ld["image"]:
        img = ld["image"][0]
    elif isinstance(ld.get("image"), str):
        img = ld["image"]
    if img.endswith("/og-image.png"):
        img = ""

    orig_zone = first(r'<details class="original">(.*?)</details>', body)
    orig_txt = txt(first(r"<p[^>]*>(.*?)</p>", orig_zone)) if orig_zone else ""
    orig_lang = first(r'<p[^>]*lang="([a-z]{2})"', orig_zone) if orig_zone else ""

    D = payload(page)
    src_lang = (D.get("src_lang") or orig_lang or "").lower()[:2]

    dev_zone = first(r'<div[^>]*id="art-dev"[^>]*>(.*?)</div>', body)
    dev_items = [txt(x) for x in re.findall(r"<(?:p|li)[^>]*>(.*?)</(?:p|li)>", dev_zone or "", re.S)]
    dev_items = [x for x in dev_items if x]
    dev_fmt = "bullets" if "<li" in (dev_zone or "") else "brief"

    i18n = {}
    for l, e in ((D.get("i18n") or {}).items()):
        if not isinstance(e, dict) or e.get("fallback"):
            continue
        if not (e.get("title") and e.get("summary")):
            continue
        i18n[l] = {"title": e["title"], "summary": e["summary"],
                   "body": [str(x) for x in (e.get("body") or [])],
                   "format": e.get("format") or "brief", "engine": "redaction"}
    # Le français affiché dans la page fait foi (c'est ce que Google a indexé).
    fr = i18n.get("fr", {})
    i18n["fr"] = {"title": title, "summary": lead or fr.get("summary") or title,
                  "body": fr.get("body") or dev_items,
                  "format": fr.get("format") or dev_fmt, "engine": "redaction"}

    return {
        "id": item_id,
        "slug": item_id,
        "url": src_url,
        "primary_source": {"name": src_name or "Source", "lang": src_lang},
        "summary": orig_txt,
        "image_url": img,
        "published_at": ld.get("datePublished") or "",
        "updated_at": ld.get("dateModified") or "",
        "i18n": i18n,
    }


def related_html(links: list[tuple[str, str, str]]) -> str:
    h = N.h
    lis = "".join(
        f'<li><a href="{h(href)}"><span class="rel-t">{h(t)}</span>'
        + (f'<span class="rel-s meta">{h(s)}</span>' if s else "")
        + "</a></li>"
        for href, t, s in links)
    return f'<ol class="rel">{lis}</ol>'


def migrate(path: Path) -> tuple[str, str]:
    """Renvoie (statut, nouveau_html). statut = ok | skip:<raison>."""
    page = path.read_text(encoding="utf-8", errors="replace")
    if NEW_MARK in page:
        return "skip:déjà-migrée", ""
    if 'http-equiv="refresh"' in page:
        return "skip:redirection", ""
    item = extract(page, path.stem)
    if not item:
        return "skip:extraction", ""
    old_seo = seo_block(page)
    if not old_seo:
        return "skip:seo-introuvable", ""

    # Rubrique d'origine (article:section) : le surtitre doit rester celui que
    # la page affichait, pas une reclassification sur le seul titre.
    section = first(r'<meta property="article:section" content="([^"]+)"', page)
    kind = SECTION_KIND.get(section.strip().upper())
    orig_classify = N.classify_kind
    if kind:
        N.classify_kind = lambda _it, _k=kind: _k
    try:
        new = N.render_article(item, [])
    finally:
        N.classify_kind = orig_classify
    new_seo = seo_block(new)
    if not new_seo:
        return "skip:seo-modèle", ""
    # Bloc SEO d'origine, à l'identique (sauf la couleur de thème du navigateur).
    keep = old_seo.replace('<meta name="theme-color" content="#05070b">',
                           '<meta name="theme-color" content="#f4f0e6">')
    new = new.replace(new_seo, keep, 1)

    links = related_links(page)
    if links:
        new = re.sub(r'<ol class="rel">.*?</ol>', lambda _: related_html(links), new, count=1, flags=re.S)

    # Contrôles avant écriture.
    canon = first(r'(<link rel="canonical"[^>]*>)', page)
    checks = {
        "canonical": canon and canon in new,
        "seo": keep in new,
        "source": N.h(item["url"]) in new,
        "titre": N.h(item["i18n"]["fr"]["title"]) in new,
        "modèle": NEW_MARK in new,
        "liens": all(N.h(hr) in new for hr, _, _ in links),
    }
    bad = [k for k, v in checks.items() if not v]
    if bad:
        return "skip:contrôle(" + ",".join(bad) + ")", ""
    return "ok", new


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    if args.ids:
        files = [NEWS_DIR / f"{i}.html" for i in args.ids]
    else:
        files = sorted(p for p in NEWS_DIR.glob("*.html") if p.name != "index.html")
    if args.limit:
        files = files[: args.limit]

    stats: dict[str, int] = {}
    skipped: list[str] = []
    for n, p in enumerate(files, 1):
        try:
            status, new = migrate(p)
        except Exception as e:  # une page cassée ne doit pas arrêter l'archive
            status, new = f"skip:erreur({type(e).__name__}: {e})", ""
        key = status.split("(")[0]
        stats[key] = stats.get(key, 0) + 1
        if status == "ok":
            if not args.dry_run:
                p.write_text(new, encoding="utf-8", newline="\n")
        elif status != "skip:déjà-migrée":
            skipped.append(f"{p.name}\t{status}")
        if n % 2000 == 0:
            print(f"  … {n}/{len(files)}", flush=True)

    print(("[dry-run] " if args.dry_run else "") + "résultat : " + json.dumps(stats, ensure_ascii=False))
    if args.report:
        Path(args.report).write_text("\n".join(skipped) + "\n", encoding="utf-8")
    elif skipped:
        print("\n".join(skipped[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
