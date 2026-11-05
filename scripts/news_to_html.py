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
from urllib.parse import quote

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


from news_locale import publishable, PENDING

def best_title(item: dict, lang: str = "fr") -> str:
    if publishable(item, lang):
        return item["i18n"][lang]["title"]
    return PENDING.get(lang, PENDING["fr"])[0]

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
    entry = ((item.get("i18n", {}) or {}).get(lang) or {}) if publishable(item, lang) else {}
    parts = [str(p).strip() for p in (entry.get("body") or []) if str(p).strip()]
    fmt = entry.get("format") or "brief"
    return (fmt if fmt in ("brief", "deep", "bullets") else "brief"), parts


def best_summary(item: dict, lang: str = "fr") -> str:
    if publishable(item, lang):
        return item["i18n"][lang]["summary"]
    return PENDING.get(lang, PENDING["fr"])[1]


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

# Liens de repli quand aucun article du fil ne partage de mots-clés.
# Pas d'emoji, pas de compteur écrit en dur (« 975/1000 » restait figé dans
# des milliers de pages) : le chiffre vivant est dans l'encart compteur.
_NEWS = ("/news.html", "Toute l'actualité du football")
_COUNTER = ("/#compteur", "Le compteur CR7")
_GOALS = ("/goals.html", "Tous les buts de Cristiano Ronaldo")
_WC = ("/coupe-du-monde/", "Coupe du monde 2026")
_MAR = ("/coupe-du-monde/equipe/maroc/", "Le Maroc à la Coupe du monde")
_POR = ("/coupe-du-monde/equipe/portugal/", "Le Portugal à la Coupe du monde")
GENERIC_RELATED = {
    "cr7": [_COUNTER, _GOALS, _NEWS],
    "wc": [_WC, _MAR, _NEWS],
    "maroc": [_MAR, _WC, _NEWS],
    "portugal": [_POR, _COUNTER, _NEWS],
    "foot": [_NEWS, _WC, _COUNTER],
}

NEWS_INDEX_REDIRECT = (
    '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
    '<meta http-equiv="refresh" content="0; url=/news">'
    '<link rel="canonical" href="https://to1000.com/news">'
    '<meta name="robots" content="noindex"><title>News — To1000.com</title>'
    '<script>location.replace("/news")</script></head>'
    '<body style="background:#f4f0e6;color:#151513;font-family:Georgia,serif;padding:2rem">'
    'Redirection vers <a href="/news" style="color:#c8102e">/news</a>…</body></html>'
)

FONTS_URL = ("https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900"
             "&family=Newsreader:ital,opsz,wght@0,6..72,400..700;1,6..72,400..700"
             "&family=Cairo:wght@400;700;900&display=swap")
EDITION_CSS = "/css/edition.css?v=20261105"

MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]
DAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def date_fr(d: datetime) -> str:
    """« 5 novembre 2026 » sans dépendre de la locale du système.

    strftime('%B') rendait « November » sur le runner Linux (locale C) et
    '%-d' n'existe pas sous Windows : la date d'une page française dépendait
    de la machine qui l'avait générée.
    """
    return f"{'1er' if d.day == 1 else d.day} {MONTHS_FR[d.month - 1]} {d.year}"


_STATS_CACHE: dict = {}


def site_counter() -> tuple[str, str]:
    """(buts, restants) depuis public/stats.json, pour le rendu sans JS.

    La page relit /stats.json au chargement : le chiffre gravé ici ne sert
    qu'aux robots et aux lecteurs sans JavaScript.
    """
    if "v" not in _STATS_CACHE:
        try:
            s = json.loads((PROJECT_DIR / "public" / "stats.json").read_text(encoding="utf-8"))
            g = int(s["goals"])
            rem = int(s["remaining"]) if s.get("remaining") is not None else int(s.get("target") or 1000) - g
            _STATS_CACHE["v"] = (str(g), str(max(0, rem)))
        except Exception:
            _STATS_CACHE["v"] = ("—", "—")
    return _STATS_CACHE["v"]


KIND_LABELS = {
    "fr": {"cr7": "Cristiano Ronaldo", "wc": "Coupe du monde 2026", "maroc": "Maroc", "portugal": "Portugal", "foot": "Football"},
    "en": {"cr7": "Cristiano Ronaldo", "wc": "World Cup 2026", "maroc": "Morocco", "portugal": "Portugal", "foot": "Football"},
    "es": {"cr7": "Cristiano Ronaldo", "wc": "Mundial 2026", "maroc": "Marruecos", "portugal": "Portugal", "foot": "Fútbol"},
    "ar": {"cr7": "كريستيانو رونالدو", "wc": "كأس العالم 2026", "maroc": "المغرب", "portugal": "البرتغال", "foot": "كرة القدم"},
}

# Textes d'interface de la page article, par langue. Le français est gravé
# dans le HTML ; le script remplace les éléments [data-i18n] pour les autres.
ARTICLE_UI = {
    "fr": {
        "orig": "Voir le texte original", "related": "À lire aussi", "src": "Source",
        "ln": {"en": "anglais", "es": "espagnol", "fr": "français", "ar": "arabe",
               "de": "allemand", "it": "italien", "pt": "portugais"},
        "skip": "Aller à l'article",
        "tag": "Le football, chaque jour. Et le compte à rebours du 1000e but de Cristiano Ronaldo.",
        "count_lbl": "buts sur 1000",
        "nav_home": "À la une", "nav_tribute": "Obrigado, Cristiano", "nav_counter": "Le compteur",
        "nav_goals": "Tous les buts", "nav_news": "Actualités", "nav_wc": "Coupe du monde",
        "nav_about": "À propos", "nav_privacy": "Confidentialité", "nav_contact": "Contact",
        "by": "D'après", "photo": "Photo via",
        "src_txt": "Ce texte résume un article publié par",
        "read_orig": "Lire l'article original",
        "share": "Partager", "copy": "Copier le lien", "copied": "Lien copié",
        "cb_lbl": "Le compteur", "cb_goals": "buts en carrière pour Cristiano Ronaldo",
        "cb_rem": "à marquer pour atteindre 1000", "cb_link": "Suivre le compteur →",
        "disclaimer": "Site de fans non officiel, ni affilié ni approuvé par Cristiano Ronaldo, ses clubs ou la FIFA. Cet article est un résumé automatique d'une source externe, traduit et mis en forme par To1000.com ; le texte original appartient à son éditeur, cité et lié ci-dessus.",
    },
    "en": {
        "orig": "View the original text", "related": "Also read", "src": "Source",
        "ln": {"en": "English", "es": "Spanish", "fr": "French", "ar": "Arabic",
               "de": "German", "it": "Italian", "pt": "Portuguese"},
        "skip": "Skip to article",
        "tag": "Football, every day. And the countdown to Cristiano Ronaldo's 1000th goal.",
        "count_lbl": "goals of 1000",
        "nav_home": "Front page", "nav_tribute": "Obrigado, Cristiano", "nav_counter": "The counter",
        "nav_goals": "All goals", "nav_news": "News", "nav_wc": "World Cup",
        "nav_about": "About", "nav_privacy": "Privacy", "nav_contact": "Contact",
        "by": "Based on", "photo": "Photo via",
        "src_txt": "This story summarises an article published by",
        "read_orig": "Read the original article",
        "share": "Share", "copy": "Copy link", "copied": "Link copied",
        "cb_lbl": "The counter", "cb_goals": "career goals for Cristiano Ronaldo",
        "cb_rem": "still needed to reach 1000", "cb_link": "Follow the counter →",
        "disclaimer": "Unofficial fan site, not affiliated with or endorsed by Cristiano Ronaldo, his clubs or FIFA. This story is an automatic summary of an external source, translated and edited by To1000.com; the original text belongs to its publisher, credited and linked above.",
    },
    "es": {
        "orig": "Ver el texto original", "related": "Leer también", "src": "Fuente",
        "ln": {"en": "inglés", "es": "español", "fr": "francés", "ar": "árabe",
               "de": "alemán", "it": "italiano", "pt": "portugués"},
        "skip": "Ir al artículo",
        "tag": "Fútbol, cada día. Y la cuenta atrás hacia el gol 1000 de Cristiano Ronaldo.",
        "count_lbl": "goles de 1000",
        "nav_home": "Portada", "nav_tribute": "Obrigado, Cristiano", "nav_counter": "El contador",
        "nav_goals": "Todos los goles", "nav_news": "Noticias", "nav_wc": "Mundial",
        "nav_about": "Quiénes somos", "nav_privacy": "Privacidad", "nav_contact": "Contacto",
        "by": "Según", "photo": "Foto vía",
        "src_txt": "Este texto resume un artículo publicado por",
        "read_orig": "Leer el artículo original",
        "share": "Compartir", "copy": "Copiar el enlace", "copied": "Enlace copiado",
        "cb_lbl": "El contador", "cb_goals": "goles en la carrera de Cristiano Ronaldo",
        "cb_rem": "le faltan para llegar a 1000", "cb_link": "Seguir el contador →",
        "disclaimer": "Sitio de fans no oficial, sin afiliación ni respaldo de Cristiano Ronaldo, sus clubes o la FIFA. Esta noticia es un resumen automático de una fuente externa, traducido y editado por To1000.com; el texto original pertenece a su editor, citado y enlazado arriba.",
    },
    "ar": {
        "orig": "عرض النص الأصلي", "related": "اقرأ أيضاً", "src": "المصدر",
        "ln": {"en": "الإنجليزية", "es": "الإسبانية", "fr": "الفرنسية", "ar": "العربية",
               "de": "الألمانية", "it": "الإيطالية", "pt": "البرتغالية"},
        "skip": "انتقل إلى المقال",
        "tag": "كرة القدم، كل يوم. والعد التنازلي نحو الهدف الألف لكريستيانو رونالدو.",
        "count_lbl": "هدفاً من 1000",
        "nav_home": "الرئيسية", "nav_tribute": "شكراً كريستيانو", "nav_counter": "العدّاد",
        "nav_goals": "كل الأهداف", "nav_news": "الأخبار", "nav_wc": "كأس العالم",
        "nav_about": "من نحن", "nav_privacy": "الخصوصية", "nav_contact": "اتصل بنا",
        "by": "نقلاً عن", "photo": "الصورة عبر",
        "src_txt": "يلخّص هذا النص مقالاً نشره",
        "read_orig": "اقرأ المقال الأصلي",
        "share": "مشاركة", "copy": "انسخ الرابط", "copied": "تم نسخ الرابط",
        "cb_lbl": "العدّاد", "cb_goals": "هدفاً في مسيرة كريستيانو رونالدو",
        "cb_rem": "هدفاً متبقياً لبلوغ الألف", "cb_link": "تابع العدّاد ←",
        "disclaimer": "موقع جماهيري غير رسمي، غير مرتبط بكريستيانو رونالدو أو أنديته أو الفيفا ولا يحظى بموافقتهم. هذا الخبر ملخّص آلي لمصدر خارجي، ترجمه وحرّره To1000.com؛ النص الأصلي ملك لناشره المذكور أعلاه مع الرابط.",
    },
}
for _l, _k in KIND_LABELS.items():
    ARTICLE_UI[_l]["kinds"] = _k

# CSS propre à la page article. Le socle (papier, encre, masthead, rubriques,
# pied de page, .label/.meta/.standfirst/.prose/.btn/figure.photo) vient de
# /css/edition.css, partagé avec l'accueil.
ARTICLE_CSS = """
.mast-name .nameplate{font-size:clamp(46px,7.4vw,78px)}
.mast-tag{font-size:14px}
.art-head{padding-top:26px;padding-bottom:22px;border-bottom:1px solid var(--rule)}
.art-head .kicker{margin-bottom:12px}
.art-title{
  font-family:var(--sans);font-stretch:75%;font-weight:800;
  font-size:clamp(34px,5.4vw,64px);line-height:1.02;letter-spacing:-.012em;
  max-width:24ch;text-wrap:balance;overflow-wrap:break-word;
}
html[dir="rtl"] .art-title{font-family:'Cairo',sans-serif;font-weight:800;letter-spacing:0;line-height:1.3;font-size:clamp(30px,4.4vw,52px)}
.art-head .standfirst{margin-top:18px;max-width:54ch}
.art-head .byline{margin-top:16px}
.byline b{color:var(--ink);font-weight:600}
.art-grid{display:grid;gap:34px;padding-top:24px;padding-bottom:12px}
.art-grid > *{min-width:0}
@media (min-width:960px){
  .art-grid{grid-template-columns:minmax(0,1fr) 320px;gap:56px}
  .art-side{border-left:1px solid var(--rule-soft);padding-left:28px}
  html[dir="rtl"] .art-side{border-left:0;padding-left:0;border-right:1px solid var(--rule-soft);padding-right:28px}
}
.art-main{max-width:760px}
.art-main figure.photo{margin-bottom:24px}
.art-main figure.photo img{aspect-ratio:3/2;object-fit:cover;object-position:50% 30%}
.prose{font-size:19px;line-height:1.6}
.prose:empty{display:none}
.essentiel{list-style:square;padding-inline-start:1.1em}
.essentiel li{margin-bottom:.6em}
.essentiel li::marker{color:var(--red)}
details.original{margin-top:28px;border-top:1px solid var(--rule-soft);border-bottom:1px solid var(--rule-soft)}
details.original summary{
  cursor:pointer;list-style:none;display:flex;justify-content:space-between;gap:12px;
  font-family:var(--sans);font-weight:600;font-size:14px;padding:12px 0;
}
details.original summary::-webkit-details-marker{display:none}
details.original summary::after{content:"+";font-weight:800;color:var(--red)}
details.original[open] summary::after{content:"\\2013"}
details.original p{padding-bottom:14px;font-size:17px;line-height:1.55;color:var(--ink-2)}
.src-box{margin-top:30px;border-top:3px solid var(--rule);padding-top:10px}
.src-line{margin-top:8px;font-family:var(--sans);font-size:15px;line-height:1.45}
.src-line b{font-weight:700}
.src-box .btn{margin-top:14px}
.art-side > * + *{margin-top:30px}
.box{border-top:3px solid var(--rule);padding-top:10px}
.box > .label{margin-bottom:12px}
.share{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.share a,.share button{
  display:block;text-align:center;text-decoration:none;cursor:pointer;
  font-family:var(--sans);font-weight:700;font-size:14px;padding:11px 8px;
  border:2px solid var(--ink);background:transparent;color:var(--ink);
}
.share a:hover,.share button:hover{background:var(--ink);color:var(--paper)}
.share .wide{grid-column:1/-1;background:var(--ink);color:var(--paper)}
.share .wide:hover{background:var(--red);border-color:var(--red)}
.cbox .pair{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--rule-soft)}
.cbox .pair > div{padding:12px 12px 4px 0}
.cbox .pair > div + div{padding-left:12px;border-left:1px solid var(--rule-soft)}
html[dir="rtl"] .cbox .pair > div{padding:12px 0 4px 12px}
html[dir="rtl"] .cbox .pair > div + div{padding-left:0;padding-right:12px;border-left:0;border-right:1px solid var(--rule-soft)}
.cbox .num{font-size:56px;display:block}
.cbox .pair div:last-child .num{color:var(--red)}
.cbox .pair span:not(.num){display:block;margin-top:6px;font-family:var(--sans);font-size:13px;line-height:1.35;color:var(--ink-2)}
.cbox a{display:inline-block;margin-top:12px;font-family:var(--sans);font-weight:600;font-size:14px;color:var(--red);text-decoration:none}
.cbox a:hover{text-decoration:underline}
.rel{list-style:none;border-top:1px solid var(--rule)}
.rel li{border-bottom:1px solid var(--rule-soft)}
.rel a{display:block;padding:11px 0 12px;text-decoration:none}
.rel-t{display:block;font-family:var(--sans);font-stretch:87.5%;font-weight:700;font-size:17px;line-height:1.22}
.rel a:hover .rel-t{color:var(--red);text-decoration:underline;text-underline-offset:3px}
.rel-s{display:block;margin-top:4px}
html[dir="rtl"] .rel-t{font-family:'Cairo',sans-serif}
"""

# Script de la page : langue (clé localStorage `to1000_lang`, ?lang=), chiffres
# vivants (/stats.json), partage. __PAYLOAD__ est remplacé par les données.
ARTICLE_JS = r"""(function(){
  var D=__PAYLOAD__;
  var SUP=['fr','en','es','ar'];
  function detect(){var u=new URLSearchParams(location.search).get('lang');if(u&&SUP.indexOf(u)>=0)return u;try{var s=localStorage.getItem('to1000_lang');if(s&&SUP.indexOf(s)>=0)return s;}catch(e){}var n=(navigator.language||'fr').slice(0,2).toLowerCase();return SUP.indexOf(n)>=0?n:'fr';}
  function esc(t){var d=document.createElement('div');d.textContent=t==null?'':t;return d.innerHTML;}
  var LANG='fr',STATS=null;
  function ui(){return D.ui[LANG]||D.ui.fr;}
  function loc(){return LANG==='ar'?'ar-u-nu-latn':LANG;}
  function pageUrl(){return D.url+(LANG!=='fr'?'?lang='+LANG:'');}
  function renderDates(){
    var td=document.getElementById('today');
    if(td){try{var s=new Date().toLocaleDateString(loc(),{weekday:'long',day:'numeric',month:'long',year:'numeric'});td.textContent=s.charAt(0).toUpperCase()+s.slice(1);}catch(e){}}
    var ad=document.getElementById('art-date');
    if(ad&&D.pub){try{var d=new Date(D.pub);if(!isNaN(d)){ad.textContent=d.toLocaleDateString(loc(),{day:'numeric',month:'long',year:'numeric'})+(LANG==='ar'?'، ':', ')+d.toLocaleTimeString(loc(),{hour:'2-digit',minute:'2-digit'});}}catch(e){}}
  }
  function renderLive(){
    if(!STATS)return;
    var g=STATS.goals,rem=STATS.remaining!=null?STATS.remaining:(STATS.target||1000)-g;
    document.querySelectorAll('[data-live="goals"]').forEach(function(x){x.textContent=g;});
    document.querySelectorAll('[data-live="remaining"]').forEach(function(x){x.textContent=Math.max(0,rem);});
  }
  function bindShare(){
    var e=D.i18n[LANG]||{},t=document.getElementById('art-title');
    var txt=(!e.fallback&&e.title)||(t?t.textContent:document.title);
    var u=encodeURIComponent(pageUrl()),m=encodeURIComponent(txt);
    var links={whatsapp:'https://wa.me/?text='+m+'%20'+u,x:'https://x.com/intent/post?text='+m+'&url='+u,
      facebook:'https://www.facebook.com/sharer/sharer.php?u='+u,telegram:'https://t.me/share/url?url='+u+'&text='+m};
    document.querySelectorAll('[data-share] a[data-net]').forEach(function(a){var h=links[a.getAttribute('data-net')];if(h)a.href=h;});
  }
  function apply(l){
    var e=D.i18n[l];if(!e)return;
    LANG=l;
    var H=document.documentElement;H.lang=l;H.dir=(l==='ar')?'rtl':'ltr';
    var t=document.getElementById('art-title');if(t&&e.title){t.textContent=e.title;t.setAttribute('dir','auto');}
    var ld=document.getElementById('art-lead');if(ld&&e.summary){ld.textContent=e.summary;ld.setAttribute('dir','auto');}
    var dev=document.getElementById('art-dev');
    if(dev){
      if(e.body&&e.body.length){
        dev.innerHTML=(e.format==='bullets')
          ?'<ul class="essentiel">'+e.body.map(function(p){return '<li>'+esc(p)+'</li>';}).join('')+'</ul>'
          :e.body.map(function(p){return '<p>'+esc(p)+'</p>';}).join('');
        dev.setAttribute('dir','auto');
      }else{dev.innerHTML='';}
    }
    var U=ui();
    document.querySelectorAll('[data-i18n]').forEach(function(x){var v=U[x.getAttribute('data-i18n')];if(v!=null)x.textContent=v;});
    var k=document.getElementById('art-kicker');if(k&&U.kinds&&U.kinds[D.kind])k.textContent=U.kinds[D.kind];
    var ol=document.getElementById('art-orig-label');
    if(ol){var n=U.ln[D.src_lang];ol.textContent=U.orig+(n?' ('+n+')':'');}
    // Les titres « À lire aussi » n'existent qu'en français.
    var rb=document.querySelector('.related');if(rb)rb.hidden=l!=='fr';
    document.querySelectorAll('.lang-sw button').forEach(function(b){var on=b.getAttribute('data-l')===l;b.classList.toggle('active',on);b.setAttribute('aria-pressed',on?'true':'false');});
    document.title=(e.title||document.title.split(' | ')[0])+' | To1000.com';
    renderDates();bindShare();renderLive();
  }
  LANG=detect();
  apply(LANG);
  fetch('/stats.json?_='+Date.now(),{cache:'no-store'}).then(function(r){return r.json();})
    .then(function(s){if(s&&typeof s.goals==='number'){STATS=s;renderLive();}}).catch(function(){});
  document.addEventListener('click',function(ev){
    var tg=ev.target;if(!tg||!tg.closest)return;
    var b=tg.closest('.lang-sw button');
    if(b){var nl=b.getAttribute('data-l');if(SUP.indexOf(nl)>=0&&nl!==LANG){try{localStorage.setItem('to1000_lang',nl);}catch(e){}apply(nl);}return;}
    var c=tg.closest('[data-net="copy"]');
    if(c){
      var link=pageUrl();
      var done=function(){c.textContent=ui().copied;setTimeout(function(){c.textContent=ui().copy;},2200);};
      if(navigator.share&&matchMedia('(pointer:coarse)').matches){navigator.share({title:document.title,url:link}).catch(function(){});return;}
      if(navigator.clipboard){navigator.clipboard.writeText(link).then(done,function(){prompt('',link);});}else{prompt('',link);}
      return;
    }
    var a=tg.closest('[data-share] a[data-net]');
    if(a&&typeof gtag==='function'){gtag('event','share',{method:a.getAttribute('data-net'),content_type:'article',item_id:D.id});}
  });
})();"""


def render_article(item: dict, all_items: list | None = None) -> str:
    kind = classify_kind(item)
    title_fr = best_title(item, "fr")
    summary_fr = best_summary(item, "fr")
    img = best_image(item)
    pub = parse_date(item.get("published_at") or item.get("published"))
    pub_iso = pub.isoformat() if pub else datetime.now(timezone.utc).isoformat()
    mod = parse_date(item.get("updated_at") or item.get("fetched_at"))
    mod_iso = mod.isoformat() if mod else pub_iso
    pub_human = date_fr(pub) if pub else ""
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

    # Valeur SEO (articleSection) inchangée ; le surtitre affiché est traduit.
    kind_label = {"cr7":"CR7","wc":"WC 2026","maroc":"MAROC","portugal":"PORTUGAL","foot":"FOOT"}[kind]
    kicker_fr = KIND_LABELS["fr"][kind]

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
                "title": PENDING[_l][0],
                "summary": PENDING[_l][1],
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
    # json.dumps puis neutralisation de </script> — un titre contenant cette
    # séquence casserait la page entière.
    _payload_js = json.dumps({"i18n": _i18n_payload, "src_lang": _src_l, "ui": ARTICLE_UI,
                              "kind": kind, "url": url, "pub": pub_iso if pub else "",
                              "id": item_id or slug},
                             ensure_ascii=False).replace("</", "<\\/")
    script_js = ARTICLE_JS.replace("__PAYLOAD__", _payload_js, 1)

    # Chapô (lead) : sous le titre, comme dans un journal.
    lead_html = f'<p class="standfirst" id="art-lead">{h(summary_fr)}</p>' if summary_fr else ""

    # Développement rédigé (2-3 paragraphes ou puces) quand le conseil de
    # rédaction l'a produit — c'est ce qui distingue une brève d'une carte.
    # Le conteneur a un id : le script de langue le re-rend dans la langue
    # choisie par le lecteur.
    _fmt, _parts = body_parts(item, "fr")
    dev_inner = ""
    if _parts:
        if _fmt == "bullets":
            dev_inner = '<ul class="essentiel">' + "".join(f"<li>{h(p)}</li>" for p in _parts) + "</ul>"
        else:
            dev_inner = "".join(f"<p>{h(p)}</p>" for p in _parts)
    dev_html = f'<div class="prose" id="art-dev">{dev_inner}</div>'

    original_html = ""
    source_summary = item.get("summary") or ""
    if source_summary and source_summary != summary_fr:
        _lang = source_lang_label(item)
        _label = f"Voir le texte original ({_lang})" if _lang else "Voir le texte original"
        _lang_attr = f' lang="{h(_src_l)}"' if _src_l else ""
        original_html = (
            f'<details class="original"><summary id="art-orig-label">{h(_label)}</summary>'
            f'<p dir="auto"{_lang_attr}>{h(source_summary)}</p></details>'
        )

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

    # Encadré source : nom du média + lien vers l'article d'origine.
    _orig_btn = (
        f'<a class="btn line" href="{h(original_url)}" rel="noopener nofollow" target="_blank">'
        f'<span data-i18n="read_orig">Lire l\'article original</span> <span aria-hidden="true">↗</span></a>'
    ) if original_url else ""
    source_html = (
        f'<div class="src-box">'
        f'<h2 class="label" data-i18n="src">Source</h2>'
        f'<p class="src-line"><span data-i18n="src_txt">Ce texte résume un article publié par</span> <b><bdi>{h(source)}</bdi></b>.</p>'
        f'{_orig_btn}</div>'
    )

    # Photo pleine colonne, avec crédit (anti-CLS : dimensions + ratio fixe).
    # Image servie par le média source : si elle disparaît, on retire la figure
    # plutôt que d'afficher un cadre vide.
    hero_html = ""
    if img:
        hero_html = (
            f'<figure class="photo">'
            f'<img src="{h(img)}" alt="{h(title_fr)}" width="1200" height="800" '
            f'loading="eager" fetchpriority="high" decoding="async" referrerpolicy="no-referrer" '
            f'onerror="var f=this.closest(\'figure\');if(f)f.remove();">'
            f'<figcaption><span data-i18n="photo">Photo via</span> <bdi>{h(source)}</bdi></figcaption>'
            f'</figure>'
        )

    # Related ARTICLES on our site (keyword overlap) + generic nav fallback
    _rel = find_related(item, [it for it in (all_items or []) if publishable(it, "fr")], 4)
    if _rel:
        _lis = "".join(
            f'<li><a href="/news/{(ri.get("slug") or ri.get("id"))}.html">'
            f'<span class="rel-t">{h(best_title(ri, "fr"))}</span>'
            f'<span class="rel-s meta">{h((ri.get("primary_source") or {}).get("name", "") if isinstance(ri.get("primary_source"), dict) else "")}</span>'
            f'</a></li>' for ri in _rel
        )
    else:
        _lis = "".join(
            f'<li><a href="{href}"><span class="rel-t">{h(label)}</span></a></li>'
            for href, label in GENERIC_RELATED[kind]
        )
    related = f'<ol class="rel">{_lis}</ol>'

    goals_txt, rem_txt = site_counter()
    disclaimer_fr = h(ARTICLE_UI["fr"]["disclaimer"])
    _now = datetime.now(timezone.utc)
    today_fr = f"{DAYS_FR[_now.weekday()]} {date_fr(_now)}"

    # Partage : liens prêts sans JavaScript (le script les ajuste à la langue).
    _qu, _qt = quote(url, safe=""), quote(title_fr, safe="")
    share_html = (
        '<div class="share" data-share>'
        f'<a data-net="whatsapp" href="https://wa.me/?text={_qt}%20{_qu}" rel="noopener" target="_blank">WhatsApp</a>'
        f'<a data-net="x" href="https://x.com/intent/post?text={_qt}&amp;url={_qu}" rel="noopener" target="_blank">X</a>'
        f'<a data-net="facebook" href="https://www.facebook.com/sharer/sharer.php?u={_qu}" rel="noopener" target="_blank">Facebook</a>'
        f'<a data-net="telegram" href="https://t.me/share/url?url={_qu}&amp;text={_qt}" rel="noopener" target="_blank">Telegram</a>'
        '<button type="button" class="wide" data-net="copy" data-i18n="copy">Copier le lien</button>'
        '</div>'
    )

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
<link href="{FONTS_URL}" rel="stylesheet">
<link rel="stylesheet" href="{EDITION_CSS}">
<title>{h(title_fr)} | To1000.com</title>
<meta name="description" content="{meta_desc}">
<meta name="keywords" content="{keywords}">
<meta name="author" content="To1000.com">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#f4f0e6">
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
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<script type="application/ld+json">
{ld_json}
</script>
<script type="application/ld+json">
{breadcrumb_json}
</script>
<style>{ARTICLE_CSS}</style>
</head>
<body>
<a class="skip" href="#article" data-i18n="skip">Aller à l'article</a>
<header>
  <div class="wrap mast-top">
    <span class="meta" id="today">{today_fr}</span>
    <div class="lang-sw" role="group" aria-label="Langue / Language"><button type="button" data-l="fr" aria-pressed="true" class="active">FR</button><button type="button" data-l="en" aria-pressed="false">EN</button><button type="button" data-l="es" aria-pressed="false">ES</button><button type="button" data-l="ar" aria-pressed="false">AR</button></div>
  </div>
  <div class="wrap mast-name">
    <a class="nameplate" href="/" aria-label="To1000.com, accueil">TO1000<span class="dot">.</span></a>
    <p class="mast-tag" data-i18n="tag">Le football, chaque jour. Et le compte à rebours du 1000e but de Cristiano Ronaldo.</p>
    <a class="mast-count" href="/#compteur"><b data-live="goals">{goals_txt}</b><span data-i18n="count_lbl">buts sur 1000</span></a>
  </div>
  <nav class="wrap sections" aria-label="Rubriques">
    <ul>
      <li><a href="/" data-i18n="nav_home">À la une</a></li>
      <li><a href="/obrigado-cristiano/" class="hot" data-i18n="nav_tribute">Obrigado, Cristiano</a></li>
      <li><a href="/#compteur" data-i18n="nav_counter">Le compteur</a></li>
      <li><a href="/goals.html" data-i18n="nav_goals">Tous les buts</a></li>
      <li><a href="/news.html" aria-current="page" data-i18n="nav_news">Actualités</a></li>
      <li><a href="/coupe-du-monde/" data-i18n="nav_wc">Coupe du monde</a></li>
    </ul>
  </nav>
</header>
<main id="article">
<article class="wrap">
  <header class="art-head">
    <p class="label red kicker" id="art-kicker">{h(kicker_fr)}</p>
    <h1 class="art-title" id="art-title">{h(title_fr)}</h1>
    {lead_html}
    <p class="meta byline"><span data-i18n="by">D'après</span> <b><bdi>{h(source)}</bdi></b> · <time id="art-date" datetime="{pub_iso}">{h(pub_human or 'Récent')}</time></p>
  </header>
  <div class="art-grid">
    <div class="art-main">
      {hero_html}
      {dev_html}
      {original_html}
      {source_html}
    </div>
    <aside class="art-side">
      <section class="box">
        <h2 class="label" data-i18n="share">Partager</h2>
        {share_html}
      </section>
      <section class="box cbox">
        <h2 class="label red" data-i18n="cb_lbl">Le compteur</h2>
        <div class="pair">
          <div><span class="num" data-live="goals">{goals_txt}</span><span data-i18n="cb_goals">buts en carrière pour Cristiano Ronaldo</span></div>
          <div><span class="num" data-live="remaining">{rem_txt}</span><span data-i18n="cb_rem">à marquer pour atteindre 1000</span></div>
        </div>
        <a href="/#compteur" data-i18n="cb_link">Suivre le compteur →</a>
      </section>
      <section class="box related">
        <h2 class="label" data-i18n="related">À lire aussi</h2>
        {related}
      </section>
    </aside>
  </div>
</article>
</main>
<footer class="wrap foot">
  <div class="foot-grid">
    <a class="nameplate" href="/" aria-label="To1000.com, accueil">TO1000<span class="dot">.</span></a>
    <nav aria-label="Pied de page">
      <a href="/" data-i18n="nav_home">À la une</a><a href="/news.html" data-i18n="nav_news">Actualités</a><a href="/goals.html" data-i18n="nav_goals">Tous les buts</a><a href="/coupe-du-monde/" data-i18n="nav_wc">Coupe du monde</a><a href="/about.html" data-i18n="nav_about">À propos</a><a href="/privacy.html" data-i18n="nav_privacy">Confidentialité</a><a href="/contact.html" data-i18n="nav_contact">Contact</a>
    </nav>
  </div>
  <p class="disclaimer" data-i18n="disclaimer">{disclaimer_fr}</p>
</footer>
<script>
{script_js}
</script>
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
