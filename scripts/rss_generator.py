#!/usr/bin/env python3
"""rss_generator.py — flux RSS public/rss.xml depuis news.json.

But : alimenter l'auto-publication sociale (Make.com / Zapier / IFTTT → Facebook
/ Instagram / Twitter) SANS coder d'API. Ces outils lisent un flux RSS et postent
chaque nouvel article automatiquement. Le flux utilise les titres/résumés FR
« flash info » (rédacteur en chef) → des posts directs et propres.
"""
import html
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

PUB = Path(__file__).resolve().parent.parent / "public"
SITE = "https://to1000.com"


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def rfc822(iso: str) -> str:
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt)
    except (ValueError, AttributeError):
        return format_datetime(datetime.now(timezone.utc))


def main() -> int:
    try:
        d = json.loads((PUB / "news.json").read_text(encoding="utf-8"))
    except OSError:
        print("[rss] news.json absent")
        return 0
    items = d.get("items", [])[:30]
    now = format_datetime(datetime.now(timezone.utc))
    parts = []
    for it in items:
        fr = (it.get("i18n", {}).get("fr", {}) or {})
        title = fr.get("title") or it.get("title", "")
        summary = fr.get("summary") or it.get("summary", "")
        link = f"{SITE}/news/{it.get('id')}"
        img = it.get("image_url", "")
        encl = f'\n      <enclosure url="{esc(img)}" type="image/jpeg"/>' if img else ""
        parts.append(
            f"""    <item>
      <title>{esc(title)}</title>
      <link>{esc(link)}</link>
      <guid isPermaLink="true">{esc(link)}</guid>
      <pubDate>{rfc822(it.get('published_at', ''))}</pubDate>
      <description>{esc(summary)}</description>{encl}
    </item>"""
        )
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>To1000.com — Actu football</title>\n"
        f"    <link>{SITE}</link>\n"
        f'    <atom:link href="{SITE}/rss.xml" rel="self" type="application/rss+xml"/>\n'
        "    <description>L'actu foot, droit au but. Le compteur de CR7 vers 1000 buts "
        "+ l'actu des grands clubs, en bref.</description>\n"
        "    <language>fr</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        + "\n".join(parts)
        + "\n  </channel>\n</rss>\n"
    )
    (PUB / "rss.xml").write_text(rss, encoding="utf-8")
    print(f"[rss] rss.xml écrit ({len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
