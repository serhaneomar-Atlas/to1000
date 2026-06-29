#!/usr/bin/env python3
"""
news_aggregator.py — Football news ingestion pipeline for to1000.com

Reads sources.json, fetches each RSS feed, filters for CR7 + football-relevant items,
de-duplicates by title similarity, clusters multi-source coverage, applies anti-clickbait
cleanup, and writes public/news.json.

Run locally:
    python scripts/news_aggregator.py [--dry-run] [--verbose]

CI usage:
    GitHub Actions invokes this on a cron; commits news.json if changed.

Design choices:
    - Pure stdlib + feedparser, no LLM (zero cost).
    - Defensive: any unreachable feed is skipped, never crashes the run.
    - Output is sorted recency-first, limited to MAX_ITEMS.
    - Each cluster cites its most authoritative source as canonical, lists all sources.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    import feedparser  # type: ignore
except ImportError:
    sys.stderr.write(
        "ERROR: feedparser not installed.\n"
        "Install with: pip install --break-system-packages feedparser\n"
    )
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
SOURCES_FILE = SCRIPT_DIR / "sources.json"
OUTPUT_FILE = PROJECT_DIR / "public" / "news.json"
TRANSLATIONS_CACHE = PROJECT_DIR / "public" / "translations_cache.json"

# Site languages — every news item is rendered in the user's chosen language
SITE_LANGS = ["en", "fr", "es", "ar"]

# Optional translator (degrades to no-op if CF token missing)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from translator import Translator  # type: ignore
except ImportError:
    Translator = None  # type: ignore

# Comité éditorial (recherchiste heuristique + rédacteur en chef Gemini)
try:
    from editorial import is_non_editorial, chief_editor_review  # type: ignore
except ImportError:
    def is_non_editorial(_t):  # type: ignore
        return False
    chief_editor_review = None  # type: ignore

# Tunables
MAX_ITEMS = 50                    # Hard cap on rendered items
MAX_AGE_HOURS = 72                # Drop items older than 3 days
SIMILARITY_THRESHOLD = 0.55       # Jaccard token overlap to treat as same story
REQUEST_TIMEOUT = 20              # Seconds per feed
USER_AGENT = "to1000-news-bot/1.0 (+https://to1000.com)"

# Compiled regex caches
_WORD_RE = re.compile(r"[a-z0-9àâäéèêëîïôöùûüçñáéíóúßẞäöü]+", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"\s+")

# Multilingual stopwords (shortlist — enough to improve clustering without heavy lib)
STOPWORDS = {
    # EN
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "but",
    "is", "are", "was", "were", "has", "have", "had", "will", "would", "could",
    "with", "from", "by", "at", "as", "this", "that", "these", "those", "it",
    # FR
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "à", "au",
    "aux", "ce", "ces", "cette", "qui", "que", "quoi", "dont", "où", "est",
    "sont", "été", "avec", "pour", "par", "sur", "sans", "en", "dans", "il",
    "elle", "ils", "elles", "ne", "pas", "plus", "se",
    # ES
    "el", "los", "las", "y", "o", "pero", "es", "son", "del", "al",
    "que", "como", "para", "por", "con", "sin", "muy", "ya", "este", "esta", "uno", "una",
    # IT
    "il", "lo", "gli", "e", "ed", "è", "sono", "del", "della", "delle",
    "che", "non", "con", "per", "tra", "fra", "ma",
    # DE
    "der", "die", "das", "ein", "eine", "und", "oder", "aber", "ist", "sind",
    "war", "waren", "mit", "von", "zu", "für", "auf", "in", "im", "den",
    # PT
    "o", "os", "as", "um", "uma", "uns", "umas", "e", "ou", "mas", "do", "da",
    "dos", "das", "no", "na", "nos", "nas", "com", "sem", "para", "por", "se",
}


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        sys.stderr.write(f"[news] {msg}\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_html(s: str) -> str:
    """Strip HTML tags + decode entities + collapse whitespace."""
    if not s:
        return ""
    s = _HTML_TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return _MULTI_SPACE_RE.sub(" ", s).strip()


def normalize_title(title: str) -> str:
    """Lowercase, strip prefixes ('VIDEO:', 'Photos:'), collapse spaces."""
    if not title:
        return ""
    t = title.strip()
    # Drop common clickbait prefixes
    t = re.sub(r"^\s*(video|vidéo|photos?|en images?|gallery|breaking|alerte|alerta)\s*:\s*",
               "", t, flags=re.IGNORECASE)
    t = _MULTI_SPACE_RE.sub(" ", t).strip()
    return t


def is_clickbait(title: str, drop_patterns: list[re.Pattern]) -> bool:
    for p in drop_patterns:
        if p.search(title):
            return True
    # All-caps title longer than 40 chars
    if len(title) > 40 and title == title.upper():
        return True
    return False


def tokens(text: str) -> set[str]:
    """Extract content tokens (lowercased, no stopwords, len > 2)."""
    return {w for w in _WORD_RE.findall(text.lower())
            if len(w) > 2 and w not in STOPWORDS}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_date(entry) -> Optional[datetime]:
    """Try several date fields, return UTC datetime or None."""
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        v = getattr(entry, field, None) or entry.get(field) if isinstance(entry, dict) else None
        if v is None:
            v = entry.get(field) if hasattr(entry, "get") else getattr(entry, field, None)
        if v:
            try:
                return datetime(*v[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None






# Cache for og:image scraping — survives within a single run, doesn't refetch
_OG_CACHE: dict = {}

def scrape_og_image(url: str, timeout: int = 6) -> Optional[str]:
    """Lightweight og:image scrape — only the first 8KB of HTML head.
    Returns None on any failure (network, 403, malformed HTML).
    Result cached per-run by URL.
    """
    if not url or url in _OG_CACHE:
        return _OG_CACHE.get(url)
    try:
        req = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Range": "bytes=0-8191",  # head only — most outlets put OG tags in first 4KB
        })
        with urlopen(req, timeout=timeout) as resp:
            html_bytes = resp.read(8192)
        text = html_bytes.decode("utf-8", errors="ignore")
        # Match <meta property="og:image" content="..."> in any quote/order
        m = re.search(
            r'<meta[^>]+(?:property|name)=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
            text, re.IGNORECASE
        )
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image',
                text, re.IGNORECASE
            )
        url_img = m.group(1).strip() if m else None
        if url_img and not url_img.startswith(("http://", "https://")):
            # Resolve relative URLs against the article URL
            from urllib.parse import urljoin
            url_img = urljoin(url, url_img)
        _OG_CACHE[url] = url_img
        return url_img
    except Exception:
        _OG_CACHE[url] = None
        return None

def extract_image(entry) -> Optional[str]:
    """Try the standard RSS image fields used by major outlets.
    Returns first usable image URL or None.
    """
    # 1) media:content (most common: BBC, Sportschau, Marca, Sport.es, Le Monde)
    media = entry.get('media_content') or []
    for m in media:
        url = m.get('url') if isinstance(m, dict) else None
        if url and url.startswith(('http://', 'https://')):
            return url
    # 2) media:thumbnail
    thumbs = entry.get('media_thumbnail') or []
    for t in thumbs:
        url = t.get('url') if isinstance(t, dict) else None
        if url and url.startswith(('http://', 'https://')):
            return url
    # 3) enclosures (some feeds use <enclosure type="image/...">)
    encs = entry.get('enclosures') or []
    for e in encs:
        url = e.get('href') or e.get('url') if isinstance(e, dict) else None
        typ = (e.get('type') or '') if isinstance(e, dict) else ''
        if url and 'image' in typ.lower():
            return url
    # 4) parse summary for first <img src=...>
    summary = entry.get('summary', '') or entry.get('description', '') or ''
    if '<img' in summary:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
        if m:
            url = m.group(1)
            if url.startswith(('http://', 'https://')):
                return url
    # 5) Last resort: scrape og:image from the article URL itself
    link = entry.get('link', '').strip()
    if link.startswith(('http://', 'https://')):
        og = scrape_og_image(link)
        if og:
            return og
    return None



def score_importance(title: str, summary: str) -> int:
    """Heuristic importance scoring (0-15+).
    HIGH signals = factual, decisive (champion, lifts, scores, signs for).
    LOW signals = filler (rumour, linked with, could, reportedly).
    Goal: float the journalism-worthy items above the noise.
    """
    blob = (title + " " + summary).lower()
    score = 0
    high = [
        ("champion", 5), ("lifts", 5), ("soulève", 5), ("levanta", 5),
        ("record", 5), ("trophy", 5), ("trophée", 5), ("trofeo", 5),
        ("wins", 4), ("beats", 4), ("clinch", 4), ("victoire", 4), ("vencer", 4),
        ("final", 4), ("finale", 4), ("hat-trick", 5), ("hat trick", 5),
        ("doublé", 4), ("brace", 4), ("doblete", 4),
        ("first goal", 4), ("first title", 5), ("erster titel", 5),
        ("transfer", 4), ("signs for", 5), ("signing", 3), ("moves to", 3),
        ("ficha por", 4), ("rejoint", 4), ("calciomercato", 3),
        ("selected", 3), ("convoqué", 3), ("convocado", 3), ("called up", 3),
        ("injury", 3), ("blessure", 3), ("lesión", 3), ("infortunio", 3),
        ("debut", 3), ("first match", 3),
        ("world cup", 3), ("champions league", 3), ("ballon d", 5),
        ("scored", 3), ("scores", 3), ("marque", 2), ("marca", 2), ("gol", 2),
        ("sacked", 4), ("fired", 4), ("limogé", 4),
    ]
    low = [
        ("rumour", -3), ("rumor", -3), ("linked with", -4), ("could move", -3),
        ("reportedly", -2), ("according to reports", -2), ("explains", -2),
        ("reveals", -2), ("admits", -2), ("opens up", -2),
        ("may sign", -2), ("might sign", -2), ("could sign", -2),
        ("relegation", -1), ("friendly", -1), ("amistoso", -1),
    ]
    for kw, pts in high:
        if kw in blob:
            score += pts
    for kw, pts in low:
        if kw in blob:
            score += pts
    return max(0, score)

def fetch_feed(url: str) -> Optional[object]:
    """Fetch and parse a feed defensively. Returns None on failure."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()
        return feedparser.parse(data)
    except (URLError, TimeoutError, ConnectionError) as e:
        log(f"  → fetch failed: {e}")
        return None
    except Exception as e:
        log(f"  → unexpected error: {type(e).__name__}: {e}")
        return None


# Non-football sports — if the TITLE leads with one of these, drop the item.
# (Le Figaro & co. prefix the discipline: "Surf : …", "Tennis : …".)
NON_FOOTBALL = [
    "surf", "tennis", "rugby", "basket", "basketball", "nba", "golf", "cyclisme",
    "natation", "handball", "volley", "volleyball", "ski", "snowboard", "boxe",
    "mma", "ufc", "athlétisme", "athletisme", "padel", "escrime", "aviron",
    "triathlon", "nfl", "baseball", "hockey", "cricket", "badminton", "motogp",
    "biathlon", "formule 1", "formula 1", "f1", "jeux olympiques", "skateboard",
    "water-polo", "judo", "karaté", "taekwondo", "haltérophilie",
]

# Word-boundary keyword matching (cached compiled regex per list).
# Substring matching wrongly kept "Osaka" (saka), "Homburg" (om), "interruption"
# (inter) — word boundaries kill those false positives.
_kw_re_cache: dict = {}

def _kw_regex(keywords: list[str]):
    key = id(keywords)
    rx = _kw_re_cache.get(key)
    if rx is None:
        parts = sorted((re.escape(k.lower()) for k in keywords if k), key=len, reverse=True)
        rx = re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)", re.UNICODE) if parts else None
        _kw_re_cache[key] = rx
    return rx

def match_any(text: str, keywords: list[str]) -> bool:
    rx = _kw_regex(keywords)
    return bool(rx and rx.search(text.lower()))


def classify(title: str, summary: str, kw_cr7_high: list,
             kw_cr7_ctx: list, kw_clubs: list, kw_players: list,
             kw_comps: list, kw_ctx: list) -> Optional[str]:
    """Return 'cr7', 'football' or None (drop).

    Strict whitelist: an item is kept only if it mentions a big club OR a star player.
    Random local news (3rd-division transfers, lower-league gossip, irrelevant figures)
    is dropped — keeps the feed focused on what readers actually click on.
    """
    # Hard drop: the title clearly belongs to another sport.
    if match_any(title, NON_FOOTBALL):
        return None
    blob = f"{title} {summary}"
    if match_any(blob, kw_cr7_high):
        return "cr7"
    if match_any(blob, kw_cr7_ctx) and ("ronaldo" in blob.lower() or "cr7" in blob.lower()):
        return "cr7"
    # Keep real football: a big club / star player, OR a named football
    # competition (World Cup, Champions League, Ligue 1, CAN…). Generic context
    # alone (goal/final/transfer) is NOT enough — a tennis "finale" must not pass.
    has_protagonist = match_any(blob, kw_clubs) or match_any(blob, kw_players)
    has_competition = match_any(blob, kw_comps)
    if has_protagonist or has_competition:
        return "football"
    return None


def pick_canonical_title(titles: list[str]) -> str:
    """From candidate titles for the same story, pick the cleanest.
    Heuristic: shortest title with the lowest punctuation/caps density wins.
    """
    if not titles:
        return ""

    def score(t: str) -> tuple:
        # Lower score = better
        length_pen = abs(len(t) - 75)  # ~75 chars is ideal headline length
        caps = sum(1 for c in t if c.isupper()) / max(len(t), 1)
        punct = sum(1 for c in t if c in "!?…") * 5
        return (length_pen + punct, caps)

    return sorted(titles, key=score)[0]


def pick_canonical_summary(summaries: list[str], max_chars: int = 280) -> str:
    """Pick the most informative summary: first non-empty, trim to 1-2 sentences."""
    for s in summaries:
        if s and len(s.strip()) > 20:
            # Trim to end of second sentence or max_chars
            sentences = re.split(r"(?<=[.!?])\s+", s.strip())
            out = ""
            for sent in sentences[:2]:
                if len(out) + len(sent) > max_chars:
                    break
                out += (sent + " ")
            out = out.strip()
            if len(out) < 30 and sentences:
                out = sentences[0]
            if len(out) > max_chars:
                out = out[:max_chars - 1].rsplit(" ", 1)[0] + "…"
            return out
    return ""


def fingerprint_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Do not write news.json")
    ap.add_argument("--verbose", "-v", action="store_true", default=True)
    ap.add_argument("--quiet", "-q", action="store_true")
    args = ap.parse_args()
    verbose = args.verbose and not args.quiet

    # Load sources config
    with open(SOURCES_FILE, encoding="utf-8") as f:
        config = json.load(f)
    sources = [s for s in config["sources"] if s.get("enabled", True)]
    kw_cr7_high = config["cr7_keywords"]["high_confidence"]
    kw_cr7_ctx = config["cr7_keywords"]["context_required"]
    gen = config["general_football_keywords"]
    kw_clubs = gen.get("big_clubs", [])
    kw_players = gen.get("star_players", [])
    kw_comps = gen.get("major_competitions", []) or gen.get("competitions", [])
    kw_ctx = gen.get("context_words", []) or (gen.get("transfer_words", []) + gen.get("topics", []))
    drop_patterns = [re.compile(p) for p in config["antispam"]["drop_patterns"]]

    log(f"Loaded {len(sources)} enabled sources", verbose)

    # Fetch all feeds
    raw_items: list[dict] = []
    stats_fetched = 0
    stats_failed = 0
    cutoff = datetime.now(timezone.utc).timestamp() - MAX_AGE_HOURS * 3600

    for src in sources:
        log(f"Fetching {src['name']} ({src['rss']})", verbose)
        feed = fetch_feed(src["rss"])
        if not feed or not getattr(feed, "entries", None):
            stats_failed += 1
            continue

        count = 0
        for entry in feed.entries[:50]:  # cap per-source to avoid one feed dominating
            title = clean_html(entry.get("title", "") or "")
            summary = clean_html(entry.get("summary", "") or entry.get("description", "") or "")
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue

            # Date filter
            pub = parse_date(entry)
            if pub:
                if pub.timestamp() < cutoff:
                    continue
                pub_iso = pub.isoformat().replace("+00:00", "Z")
            else:
                pub_iso = now_iso()

            # Skip if obviously clickbait
            if is_clickbait(title, drop_patterns):
                continue

            # Classification: cr7 / football / drop (strict whitelist)
            kind = classify(title, summary, kw_cr7_high, kw_cr7_ctx,
                           kw_clubs, kw_players, kw_comps, kw_ctx)
            if kind is None:
                continue
            # Recherchiste éditorial (sans API) : écarte les articles utilitaires
            # (how to watch / livestream / paris / compo probable) — pas de la news.
            if is_non_editorial(title):
                continue

            normalized_title = normalize_title(title)
            raw_items.append({
                "title": normalized_title,
                "summary": summary,
                "url": link,
                "image_url": extract_image(entry),
                "published_at": pub_iso,
                "kind": kind,
                "score": score_importance(normalized_title, summary),
                "source": {
                    "id": src["id"],
                    "name": src["name"],
                    "flag": src["flag"],
                    "country": src["country"],
                    "lang": src["lang"],
                    "weight": src["weight"],
                    "homepage": src["homepage"],
                },
                # Clustering uses title + first 200 chars of summary; same-lang only
                "tokens": tokens(title + " " + summary[:200]),
            })
            count += 1
        stats_fetched += 1
        log(f"  → kept {count} relevant items", verbose)

    log(f"Total relevant items: {len(raw_items)} from {stats_fetched} feeds ({stats_failed} failed)", verbose)

    # ─── Clustering ──────────────────────────────────────────────────────────
    # Greedy: sort by weight desc + recency desc, then merge similar.
    raw_items.sort(key=lambda it: (-it["source"]["weight"], it["published_at"]), reverse=False)
    raw_items.sort(key=lambda it: (it["source"]["weight"], it["published_at"]), reverse=True)

    # Cluster same-language items only — Jaccard on tokens across languages
    # would need translation. Cross-lang stories stay as separate items, which
    # is acceptable: a Spanish reader trusts Marca, a French reader trusts L'Équipe.
    clusters: list[dict] = []
    for item in raw_items:
        merged = False
        for cluster in clusters:
            same_lang = cluster["primary_source"]["lang"] == item["source"]["lang"]
            threshold = SIMILARITY_THRESHOLD if same_lang else 0.85  # cross-lang demands very high overlap (proper names)
            if jaccard(item["tokens"], cluster["_tokens"]) >= threshold:
                # Same story — merge as additional source
                cluster["sources"].append({
                    "id": item["source"]["id"],
                    "name": item["source"]["name"],
                    "flag": item["source"]["flag"],
                    "url": item["url"],
                })
                cluster["_titles"].append(item["title"])
                cluster["_summaries"].append(item["summary"])
                # Pool tokens so future merges see the full vocabulary of the cluster
                cluster["_tokens"] = cluster["_tokens"] | item["tokens"]
                if item["published_at"] > cluster["latest_at"]:
                    cluster["latest_at"] = item["published_at"]
                # If cluster has no image yet, take the merged item's image
                if not cluster.get("image_url") and item.get("image_url"):
                    cluster["image_url"] = item["image_url"]
                cluster["score"] = max(cluster.get("score", 0), item.get("score", 0))
                # Promote to cr7 if any source flagged cr7
                if item["kind"] == "cr7":
                    cluster["kind"] = "cr7"
                merged = True
                break

        if not merged:
            clusters.append({
                "_tokens": set(item["tokens"]),
                "_titles": [item["title"]],
                "_summaries": [item["summary"]],
                "kind": item["kind"],
                "published_at": item["published_at"],
                "latest_at": item["published_at"],
                "primary_url": item["url"],
                "primary_source": item["source"],
                "image_url": item.get("image_url"),
                "score": item.get("score", 0),
                "sources": [{
                    "id": item["source"]["id"],
                    "name": item["source"]["name"],
                    "flag": item["source"]["flag"],
                    "url": item["url"],
                }],
            })

    log(f"Clustered into {len(clusters)} unique stories", verbose)

    # Pre-translation cap: sort clusters by the same key used for final sort,
    # then drop everything beyond MAX_ITEMS. This avoids paying the translation
    # cost (MyMemory ~0.5-1s/call × 3 langs × 2 fields) on items that will be
    # discarded at the cap. Cut from 233 → 50 typical = 4-5× fewer API calls.
    clusters.sort(
        key=lambda c: (
            1 if c["kind"] == "cr7" else 0,
            c.get("score", 0),
            min(len(c["sources"]), 3),
            c["latest_at"],
        ),
        reverse=True,
    )
    if len(clusters) > MAX_ITEMS:
        log(f"Pre-translation cap: {len(clusters)} → {MAX_ITEMS}", verbose)
        clusters = clusters[:MAX_ITEMS]

    # Initialize translator (no-op if creds missing)
    translator = Translator(cache_path=TRANSLATIONS_CACHE) if Translator else None

    # Build final items with multilingual title+summary
    # Budget d'appels éditoriaux Gemini PAR RUN. Free tier ~15 req/min + ~50
    # articles = passe > 20 min → timeout GitHub (run tué, news figée). On traite
    # ~25 NOUVEAUX articles/run au rédacteur en chef ; le reste passe en MyMemory.
    # Le cache (clé edt:) accumule → tous couverts en ~2 runs, et chaque run finit
    # en ~5 min. Configurable via EDITORIAL_BUDGET.
    # Garde-fous anti-timeout (le run plantait à 20 min dans la passe Gemini) :
    # budget de NOUVEAUX appels + PLAFOND wall-clock dur. Au-delà → MyMemory.
    editorial_budget = int(os.environ.get("EDITORIAL_BUDGET", "15"))
    editorial_max_s = int(os.environ.get("EDITORIAL_MAX_SECONDS", "420"))  # 7 min « mur » (+ MyMemory) < timeout 20
    editorial_calls = 0
    editorial_t0 = time.monotonic()
    # Mode CACHE-ONLY (news-sync) : ZÉRO appel Gemini live → publication toujours
    # rapide, jamais de timeout. Les hits de cache (alimentés par news-editorial,
    # le « cerveau » éditorial) restent servis. C'est l'archi découplée recommandée.
    if os.environ.get("EDITORIAL_CACHE_ONLY") == "1" and translator:
        translator.gemini_enabled = False
        print("[news] cache-only : éditorial Gemini live OFF (news-editorial enrichit à part)")

    final_items = []
    for c in clusters:
        title = pick_canonical_title(c["_titles"])
        summary = pick_canonical_summary(c["_summaries"])
        if not title or not summary:
            continue

        src_lang = c["primary_source"]["lang"]
        targets = [l for l in SITE_LANGS if l != src_lang]

        # i18n payload: {lang: {title, summary, needs_translation}}
        # Always includes the source lang as authoritative original.
        # Preferred path (Gemini): editorialize_pair rewrites a concise NEUTRAL
        # "essential" summary in every language in one call (no clickbait, the
        # facts to retain) and translates the title. Falls back to literal
        # translation, then to source-language passthrough.
        # ── RÉDACTEUR EN CHEF (Gemini) : vérifie fidélité/valeur/positionnement,
        #    décide PUBLIER/REJETER, fournit titre+résumé essentiel en 4 langues.
        # ── COUPE-CIRCUIT éditorial (AVANT toute logique par-item) : dès que le
        #    budget OU le mur de temps est franchi, on coupe TOUT Gemini — chief
        #    ET le fallback editorialize_pair — pour le reste du run. C'était LE
        #    bug : avant, le cutoff ne coupait que chief, editorialize_pair
        #    continuait d'appeler Gemini → le run timeoutait quand même.
        if (translator and getattr(translator, "gemini_enabled", False)
                and (editorial_calls >= editorial_budget
                     or (time.monotonic() - editorial_t0) >= editorial_max_s)):
            translator.gemini_enabled = False
            print(f"[news] cap éditorial atteint ({editorial_calls} appels / "
                  f"{int(time.monotonic() - editorial_t0)}s) → MyMemory pour le reste du run")

        # ── RÉDACTEUR EN CHEF : appelé si Gemini live actif OU si un cache existe
        #    (les hits de cache sont servis même en mode cache-only, Gemini OFF).
        review = None
        if (translator and chief_editor_review
                and (getattr(translator, "gemini_enabled", False)
                     or getattr(translator, "cache", None))):
            before = translator._calls_gemini
            review = chief_editor_review(translator, title, summary, src_lang, targets)
            editorial_calls += translator._calls_gemini - before   # compte les vrais appels (pas les hits cache)
        if review is not None:
            if not review["publish"]:
                continue   # rejeté par le rédacteur en chef (non-news, divergence, périmé…)
            if review["i18n"]:
                i18n = review["i18n"]
                essential = (i18n.get(src_lang) or {}).get("summary")
                if essential:
                    summary = essential
            else:
                i18n = translator.translate_pair(title, summary, src=src_lang, targets=targets)
        elif translator and getattr(translator, "gemini_enabled", False):
            i18n = translator.editorialize_pair(title, summary, src=src_lang, targets=targets)
            if i18n:
                essential = (i18n.get(src_lang) or {}).get("summary")
                if essential:
                    summary = essential   # canonical summary = the essential digest
            else:
                i18n = translator.translate_pair(title, summary, src=src_lang, targets=targets)
        elif translator:
            i18n = translator.translate_pair(title, summary, src=src_lang, targets=targets)
        else:
            i18n = {l: {"title": title, "summary": summary, "needs_translation": (l != src_lang)}
                    for l in SITE_LANGS}
            if src_lang in i18n:
                i18n[src_lang]["needs_translation"] = False

        final_items.append({
            "id": fingerprint_id(title.lower()),
            "title": title,            # canonical (source lang) — kept for SEO/sitemap
            "summary": summary,        # canonical (source lang)
            "i18n": i18n,              # frontend picks i18n[pageLang]
            "url": c["primary_url"],
            "image_url": c.get("image_url"),
            "score": c.get("score", 0),
            "published_at": c["latest_at"],
            "kind": c["kind"],
            "primary_source": {
                "id": c["primary_source"]["id"],
                "name": c["primary_source"]["name"],
                "flag": c["primary_source"]["flag"],
                "lang": src_lang,
            },
            "sources": c["sources"][:8],  # cap displayed badges
            "source_count": len(c["sources"]),
        })

    # Persist translation cache for next run
    if translator and translator.cache:
        translator.cache.save()
        log(f"Translator stats: {translator.stats()}", verbose)

    # Sort: CR7 first, then multi-source confirmation, then recency
    final_items.sort(
        key=lambda it: (
            1 if it["kind"] == "cr7" else 0,
            it.get("score", 0),                  # importance score (champion, signs for, scores...)
            min(it["source_count"], 3),
            it["published_at"],
        ),
        reverse=True,
    )
    final_items = final_items[:MAX_ITEMS]

    # Persistance de l'enrichissement : réutilise l'i18n « gemini-editor » déjà
    # produit (par news-editorial) pour un article au même id — sinon news-sync
    # (cache-only) le perdrait au refetch. → la qualité éditoriale ne régresse pas.
    try:
        _prev = json.load(open(OUTPUT_FILE, encoding="utf-8"))
        _enriched = {it.get("id"): it.get("i18n")
                     for it in _prev.get("items", [])
                     if ((it.get("i18n", {}) or {}).get("fr", {}) or {}).get("engine") == "gemini-editor"}
        _kept = 0
        for it in final_items:
            cur = ((it.get("i18n", {}) or {}).get("fr", {}) or {}).get("engine")
            if cur != "gemini-editor" and it.get("id") in _enriched:
                it["i18n"] = _enriched[it["id"]]
                _kept += 1
        if _kept:
            log(f"Enrichissement éditorial préservé pour {_kept} articles (par id)", verbose)
    except (OSError, json.JSONDecodeError):
        pass

    payload = {
        "generated_at": now_iso(),
        "tagline": "Le foot, droit au but.",
        "stats": {
            "feeds_fetched": stats_fetched,
            "feeds_failed": stats_failed,
            "raw_items": len(raw_items),
            "clusters": len(clusters),
            "published": len(final_items),
            "cr7_count": sum(1 for it in final_items if it["kind"] == "cr7"),
        },
        "items": final_items,
    }

    if args.dry_run:
        log("DRY RUN — not writing news.json", verbose)
        print(json.dumps(payload["stats"], indent=2))
        return 0

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"Wrote {OUTPUT_FILE} ({len(final_items)} items, {payload['stats']['cr7_count']} CR7)", verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
