"""article_fetch.py — récupère le TEXTE COMPLET d'un article source.

Pourquoi : jusqu'ici le pipeline ne voyait que l'extrait RSS (souvent le premier
paragraphe, parfois le seul chapô). Résumer ça revient à reformuler une amorce —
d'où des brèves qui répètent le titre sans jamais donner l'information. Pour
« tout relire, analyser, résumer puis rédiger », il faut le corps de l'article.

Contraintes : tourne sur un runner GitHub, sans dépendance lourde (pas de
trafilatura/bs4 installés). Extraction maison sur les balises <p>, bornée en
temps, tolérante à l'échec — si la récupération rate, l'appelant retombe sur
l'extrait RSS et le pipeline continue.
"""
from __future__ import annotations

import gzip
import re
import zlib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TIMEOUT = 12
MAX_BYTES = 900_000
MIN_PARAGRAPH = 60      # sous ce seuil, c'est une légende ou un lien, pas du corps
MAX_CHARS = 6000        # plafond envoyé au modèle

_UA = ("Mozilla/5.0 (compatible; To1000Bot/1.0; +https://to1000.com) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")

# Blocs à jeter avant extraction : scripts, styles, nav, pied de page, asides.
_STRIP_BLOCKS = re.compile(
    r"<(script|style|noscript|nav|header|footer|aside|form|figure|figcaption)\b[^>]*>"
    r".*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_P_BLOCK = re.compile(r"<p\b[^>]*>(.*?)</p>", re.I | re.S)
_ARTICLE = re.compile(
    r"<(?:article|main)\b[^>]*>(.*?)</(?:article|main)>", re.I | re.S)
_WS = re.compile(r"[ \t ]+")

# Phrases parasites fréquentes en fin/début de corps d'article.
_BOILERPLATE = re.compile(
    r"(abonnez[- ]vous|suscr[íi]bete|subscribe|newsletter|cookie|"
    r"lire aussi|leer m[áa]s|read more|t[ée]l[ée]charge[zr] l'app|"
    r"suivez[- ]nous|s[íi]guenos|follow us|copyright|tous droits r[ée]serv[ée]s|"
    r"todos los derechos|all rights reserved|partager|compartir|share this)", re.I)

_ENTITIES = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&#39;": "'", "&apos;": "'", "&rsquo;": "’", "&lsquo;": "‘",
    "&ldquo;": "“", "&rdquo;": "”", "&hellip;": "…", "&mdash;": "—",
    "&ndash;": "–", "&eacute;": "é", "&egrave;": "è", "&agrave;": "à",
    "&ccedil;": "ç", "&ocirc;": "ô", "&uuml;": "ü", "&ouml;": "ö",
    "&auml;": "ä", "&ntilde;": "ñ", "&oacute;": "ó", "&iacute;": "í",
    "&aacute;": "á", "&uacute;": "ú", "&euro;": "€",
}


def _unescape(text: str) -> str:
    for ent, char in _ENTITIES.items():
        text = text.replace(ent, char)
    text = re.sub(r"&#x([0-9a-fA-F]+);",
                  lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    return text


def _decode_body(raw: bytes, headers) -> str:
    encoding = (headers.get("Content-Encoding") or "").lower()
    if "gzip" in encoding:
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif "deflate" in encoding:
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except zlib.error:
            pass
    charset = "utf-8"
    ctype = headers.get("Content-Type") or ""
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    if m:
        charset = m.group(1)
    else:
        head = raw[:2048].decode("latin-1", "ignore")
        m = re.search(r'charset=["\']?([\w\-]+)', head, re.I)
        if m:
            charset = m.group(1)
    try:
        return raw.decode(charset, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def fetch_html(url: str) -> str | None:
    if not url or not url.startswith(("http://", "https://")):
        return None
    req = Request(url, headers={
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr,en;q=0.8,es;q=0.6",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and ctype:
                return None
            return _decode_body(resp.read(MAX_BYTES), resp.headers)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None


def extract_text(html: str) -> str:
    """Corps de l'article, paragraphes propres joints par des sauts de ligne."""
    if not html:
        return ""
    cleaned = _STRIP_BLOCKS.sub(" ", html)
    # On privilégie <article>/<main> quand ils existent : bien moins de bruit.
    scoped = _ARTICLE.search(cleaned)
    zone = scoped.group(1) if scoped else cleaned

    paragraphs: list[str] = []
    for raw in _P_BLOCK.findall(zone):
        text = _WS.sub(" ", _unescape(_TAG.sub(" ", raw))).strip()
        if len(text) < MIN_PARAGRAPH or _BOILERPLATE.search(text):
            continue
        if text not in paragraphs:
            paragraphs.append(text)

    # Une page qui ne rend ses <p> qu'en JS : on se rabat sur le texte brut.
    if not paragraphs:
        flat = _WS.sub(" ", _unescape(_TAG.sub(" ", zone))).strip()
        return flat[:MAX_CHARS] if len(flat) > 400 else ""

    return "\n\n".join(paragraphs)[:MAX_CHARS]


def article_text(url: str, fallback: str = "") -> tuple[str, str]:
    """(texte, origine) — origine vaut 'full' (article récupéré) ou 'rss'.

    L'appelant sait ainsi s'il résume l'article ou seulement son amorce, et peut
    l'indiquer au modèle : on ne demande pas la même rigueur d'analyse dans les
    deux cas.
    """
    html = fetch_html(url)
    body = extract_text(html) if html else ""
    # Un corps plus court que l'extrait RSS = extraction ratée.
    if body and len(body) > max(400, len(fallback or "")):
        return body, "full"
    return (fallback or ""), "rss"
