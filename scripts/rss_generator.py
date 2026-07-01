#!/usr/bin/env python3
"""rss_generator.py — flux RSS public/rss.xml depuis news.json.

But : alimenter l'auto-publication sociale (Make.com / Zapier / IFTTT → Facebook
/ Instagram / Twitter) SANS coder d'API. Ces outils lisent un flux RSS et postent
chaque nouvel article automatiquement. Le flux utilise les titres/résumés FR
« flash info » (rédacteur en chef) → des posts directs et propres.
"""
import html
import json
import re
import unicodedata
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


# Mots capitalisés (accents retirés, minuscule) à NE PAS transformer en hashtag
# — génériques, pas des entités. Le filtre compare _tag(mot).lower() à ce set.
_TAG_STOP = {
    "coupe", "monde", "mondial", "world", "cup", "ligue", "ligues", "league",
    "champions", "direct", "video", "info", "breaking", "selon", "apres", "avant",
    "cette", "face", "grace", "avec", "pour", "dans", "the", "with", "this",
    "cristiano", "titre", "titres", "saison", "saisons", "victoire", "defaite",
    "match", "but", "buts", "million", "millions", "dollars", "euros", "livres",
    "record", "blesse", "blessure", "confederation", "attaquant", "attaquante",
    "gardien", "milieu", "defenseur", "provenance", "montant", "double", "ballor",
    "ballon", "finale", "finales", "huitiemes", "quarts", "groupe",
}
_ENTITY_RE = re.compile(r"[A-ZÀ-Ý][\wÀ-ÿ'’-]{3,}")


def _tag(word: str) -> str:
    """Nom propre -> hashtag propre (sans accents ni apostrophes)."""
    w = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode()
    w = re.sub(r"[^A-Za-z0-9]", "", w)
    return (w[:1].upper() + w[1:]) if w else ""


def hashtags(item: dict) -> str:
    fr = (item.get("i18n", {}).get("fr", {}) or {})
    title = fr.get("title") or item.get("title", "")
    low = title.lower()
    tags, seen = [], set()

    def add(t):
        if t and t.lower() not in seen and len(tags) < 5:
            seen.add(t.lower())
            tags.append(t)

    if item.get("kind") == "cr7" or "ronaldo" in low:
        add("CR7"); add("Ronaldo")
    if any(k in low for k in ("coupe du monde", "mondial", "world cup", "wm 2026")):
        add("WorldCup2026")
    for e in _ENTITY_RE.findall(title):
        t = _tag(e)
        if t and t.lower() not in _TAG_STOP:
            add(t)
    add("Football"); add("To1000")
    return " ".join("#" + t for t in tags)


def social_caption(item: dict) -> str:
    """Légende prête à poster : hook emoji + brève flash-info + hashtags."""
    fr = (item.get("i18n", {}).get("fr", {}) or {})
    summary = fr.get("summary") or item.get("summary", "")
    emoji = "🔥" if item.get("kind") == "cr7" else "⚽"
    return f"{emoji} {summary}\n\n{hashtags(item)}"


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
      <description>{esc(social_caption(it))}</description>{encl}
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
