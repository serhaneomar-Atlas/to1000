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

# Cartes de marque par article (Pillow) — dégrade proprement si indispo.
CARDS_DIR = PUB / "social" / "cards"
_MANIFEST = CARDS_DIR / "manifest.json"
try:
    import hashlib
    from social_card import make_card  # noqa: E402
    _CARDS_OK = True
except Exception:
    _CARDS_OK = False

_KIND_LABEL = {"cr7": "CR7", "wc": "MONDIAL 2026", "maroc": "MAROC",
               "portugal": "PORTUGAL", "foot": "FOOTBALL"}


def _load_stats_counter():
    try:
        s = json.loads((PUB / "stats.json").read_text(encoding="utf-8"))
        return f"{s.get('goals', 975)}/{s.get('target', 1000)}"
    except Exception:
        return "975/1000"


def card_url_for(item, counter, manifest):
    """Génère/réutilise la carte de marque de l'article ; retourne son URL (ou None)."""
    if not _CARDS_OK:
        return None
    fr = (item.get("i18n", {}).get("fr", {}) or {})
    title = fr.get("title") or item.get("title", "")
    iid = item.get("id")
    if not title or not iid:
        return None
    # JPEG natif depuis 2026-07-01 : Instagram (auto-post Make) refuse le PNG ;
    # avant, la conversion passait par un proxy wsrv.nl. Les anciens .png restent
    # en place pour les og:image déjà publiés.
    h = hashlib.sha256(f"{title}|{counter}".encode("utf-8")).hexdigest()[:10]
    if manifest.get(iid) != h or not (CARDS_DIR / f"{iid}.jpg").exists():
        try:
            make_card(title, _KIND_LABEL.get(item.get("kind"), "FOOTBALL"),
                      counter, CARDS_DIR / f"{iid}.jpg")
            manifest[iid] = h
        except Exception:
            return None
    return f"{SITE}/social/cards/{iid}.jpg"


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


# ─── Multilingue (fix 2026-07-02, demande WORKLOG : Page FB arabe Pchaaakh TV) ──
# rss.xml (FR) garde son URL historique — le scénario Make to1000 y est branché.
FEEDS = {
    "fr": {"file": "rss.xml",    "language": "fr",
           "title": "To1000.com — Actu football",
           "desc": "L'actu foot, droit au but. Le compteur de CR7 vers 1000 buts "
                   "+ l'actu des grands clubs, en bref."},
    "ar": {"file": "rss-ar.xml", "language": "ar",
           "title": "To1000.com — أخبار كرة القدم",
           "desc": "أخبار الكرة مباشرة إلى الهدف: عدّاد رونالدو نحو الهدف 1000 "
                   "وأهم أخبار الأندية الكبرى، باختصار."},
    "en": {"file": "rss-en.xml", "language": "en",
           "title": "To1000.com — Football News",
           "desc": "Football news, straight to the goal: CR7's countdown to 1000 "
                   "career goals + top clubs news, in brief."},
    "es": {"file": "rss-es.xml", "language": "es",
           "title": "To1000.com — Noticias de fútbol",
           "desc": "El fútbol, directo al gol: la cuenta atrás de CR7 hacia los 1000 "
                   "goles + la actualidad de los grandes clubes, en breve."},
}

# Hashtags arabes par thème (banque du kit MARKETING_AR.md) — l'extraction
# d'entités de hashtags() est latine, inutilisable sur un titre arabe.
_AR_TAGS = {
    "cr7":      "#رونالدو #CR7 #هدف_1000",
    "wc":       "#كأس_العالم_2026 #مونديال_2026",
    "maroc":    "#المغرب #أسود_الأطلس #كأس_العالم_2026",
    "portugal": "#البرتغال #رونالدو #كأس_العالم_2026",
    "foot":     "#كرة_القدم #أخبار_الكرة",
}


_ARABIC_RE = re.compile(r"[؀-ۿ]")


def has_arabic(text: str) -> bool:
    """Vrai si le texte contient de l'écriture arabe. Nécessaire car le pipeline
    stocke le texte SOURCE en passthrough dans i18n.ar tant que l'enrichissement
    Gemini n'est pas passé — le flux AR ne doit publier que du vrai arabe."""
    return bool(_ARABIC_RE.search(text or ""))


def lang_ok(item: dict, lang: str) -> bool:
    """Un item n'entre dans un flux traduit que si sa traduction est réelle.
    Le pipeline stocke le texte SOURCE en passthrough tant que Gemini n'a pas
    enrichi : sans ce filtre, rss-en/es publieraient de l'espagnol, etc.
      - fr : flux historique, toujours inclus (fallback assumé)
      - ar : détection d'écriture arabe (fiable)
      - en/es : la traduction existe ET diffère du titre source (l'écriture
        latine ne distingue pas les langues entre elles)"""
    if lang == "fr":
        return True
    title = ((item.get("i18n") or {}).get(lang) or {}).get("title") or ""
    if lang == "ar":
        return has_arabic(title)
    return bool(title) and title != (item.get("title") or "")


def tr(item: dict, lang: str, field: str) -> str:
    """Champ traduit avec cascade : langue demandée → FR → texte source."""
    i18n = item.get("i18n", {}) or {}
    v = (i18n.get(lang) or {}).get(field)
    if not v and lang != "fr":
        v = (i18n.get("fr") or {}).get(field)
    return v or item.get(f"{field}_fr") or item.get(field, "")


def social_caption(item: dict, lang: str = "fr") -> str:
    """Légende prête à poster : hook emoji + brève flash-info + hashtags."""
    summary = tr(item, lang, "summary")
    emoji = "🔥" if item.get("kind") == "cr7" else "⚽"
    if lang == "ar":
        tags = _AR_TAGS.get(item.get("kind"), _AR_TAGS["foot"]) + " #To1000"
    else:
        tags = hashtags(item)
    return f"{emoji} {summary}\n\n{tags}"


def main() -> int:
    try:
        d = json.loads((PUB / "news.json").read_text(encoding="utf-8"))
    except OSError:
        print("[rss] news.json absent")
        return 0
    items = d.get("items", [])[:30]
    now = format_datetime(datetime.now(timezone.utc))
    counter = _load_stats_counter()
    manifest = {}
    if _MANIFEST.exists():
        try:
            manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    # La carte de marque est générée une fois (manifest partagé) et réutilisée
    # par les 4 flux — image identique quelle que soit la langue du post.
    cards = {it.get("id"): card_url_for(it, counter, manifest) for it in items}

    for lang, feed in FEEDS.items():
        parts = []
        for it in items:
            if not lang_ok(it, lang):
                continue
            link = f"{SITE}/news/{it.get('id')}"
            img = cards.get(it.get("id")) or it.get("image_url", "")
            encl = f'\n      <enclosure url="{esc(img)}" type="image/jpeg"/>' if img else ""
            parts.append(
                f"""    <item>
      <title>{esc(tr(it, lang, "title"))}</title>
      <link>{esc(link)}</link>
      <guid isPermaLink="true">{esc(link)}</guid>
      <pubDate>{rfc822(it.get('published_at', ''))}</pubDate>
      <description>{esc(social_caption(it, lang))}</description>{encl}
    </item>"""
            )
        rss = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
            "  <channel>\n"
            f"    <title>{esc(feed['title'])}</title>\n"
            f"    <link>{SITE}</link>\n"
            f'    <atom:link href="{SITE}/{feed["file"]}" rel="self" type="application/rss+xml"/>\n'
            f"    <description>{esc(feed['desc'])}</description>\n"
            f"    <language>{feed['language']}</language>\n"
            f"    <lastBuildDate>{now}</lastBuildDate>\n"
            + "\n".join(parts)
            + "\n  </channel>\n</rss>\n"
        )
        (PUB / feed["file"]).write_text(rss, encoding="utf-8")

    if _CARDS_OK and manifest:
        CARDS_DIR.mkdir(parents=True, exist_ok=True)
        _MANIFEST.write_text(json.dumps(manifest), encoding="utf-8")
    print(f"[rss] {len(FEEDS)} flux écrits (rss.xml + ar/en/es · {len(items)} items · "
          f"cartes de marque: {'oui' if _CARDS_OK else 'non'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
