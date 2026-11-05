#!/usr/bin/env python3
"""wc_pages.py — génère la section /coupe-du-monde/ (SEO statique, charte « journal du matin »).

Pages générées :
  /coupe-du-monde/                       hub (calendrier par tour + 48 équipes)
  /coupe-du-monde/matchs-du-jour/        page « habitude » (regénérée par cron)
  /coupe-du-monde/match/{slug}/          une page par match aux équipes connues
  /coupe-du-monde/equipe/{slug}/         une page par équipe (48)

Chaque page : title/description uniques, canonical, OG + Twitter Card, hreflang,
JSON-LD (SportsEvent / SportsTeam), consent.js + GA4, heure de l'Est rendue
serveur + conversion fuseau visiteur en JS progressif (pas de CSR).

Usage :  python wc_pages.py [--offline] [--live-only]
  --offline    : régénère depuis le cache data.json sans appel API
  --live-only  : sort immédiatement (code 0) si aucun match n'est dans sa
                 fenêtre live (kickoff-20min → +3h30) — utilisé par le cron */5
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from html import escape as h
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib.wc_data import (ET, ROUND_ORDER, date_fr_et, fetch_matches,
                         is_live_window, load_cache, round_label, time_fr_et)
from lib.wc_teams import TEAMS

PROJECT_DIR = SCRIPT_DIR.parent
OUT = PROJECT_DIR / "public" / "coupe-du-monde"
SITE = "https://to1000.com"
GA = "G-4V8Y6C38VN"

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900'
         '&family=Newsreader:ital,opsz,wght@0,6..72,400..700;1,6..72,400..700'
         '&family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">')
# Charte « journal du matin » partagée (public/css/edition.css) + règles propres
# à la section (wc.css). Changer CSS_V à chaque modif du CSS : /*.css est mis
# en cache longtemps (_headers).
CSS_V = "20261106"
STYLES = (f'<link rel="stylesheet" href="/css/edition.css?v={CSS_V}">'
          f'<link rel="stylesheet" href="/coupe-du-monde/wc.css?v={CSS_V}">')


def cr7_goals() -> int | None:
    """Compteur du bandeau : lu dans stats.json au moment de la génération
    (puis rafraîchi côté client), pour que le texte serveur ne soit jamais vide."""
    try:
        return int(json.loads((PROJECT_DIR / "public" / "stats.json")
                              .read_text(encoding="utf-8"))["goals"])
    except Exception:
        return None


def flag(team: dict, size: int = 24) -> str:
    if not team.get("iso2"):
        return "🏆"
    w = size * 3 // 2
    return (f'<img src="https://flagcdn.com/w{40 if size <= 24 else 80}/{team["iso2"]}.png" '
            f'alt="" width="{w}" height="{size}" loading="lazy" class="flag">')


def page(title: str, desc: str, path: str, body: str, jsonld: list[dict],
         og_title: str | None = None) -> str:
    url = f"{SITE}{path}"
    ld = "".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>'
                 for d in jsonld)
    goals = cr7_goals()
    count = (f'<a class="mast-count" href="/#compteur"><b id="mc-goals">{goals}</b>'
             '<span>buts sur 1000</span></a>') if goals is not None else ""
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
<title>{h(title)}</title>
<meta name="description" content="{h(desc)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="To1000.com">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{h(og_title or title)}">
<meta property="og:description" content="{h(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@to1000com">
<meta name="twitter:title" content="{h(og_title or title)}">
<meta name="twitter:description" content="{h(desc)}">
<meta name="twitter:image" content="{SITE}/og-image.png">
<meta name="theme-color" content="#f4f0e6">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="To1000 — Football News" href="/rss.xml">
{FONTS}
{STYLES}
{ld}
</head>
<body>
<a class="skip" href="#contenu">Aller au contenu</a>
<header>
  <div class="wrap mast-top">
    <span class="meta" id="today">Coupe du Monde 2026</span>
    <a class="meta mast-link" href="/coupe-du-monde/matchs-du-jour/">Matchs du jour</a>
  </div>
  <div class="wrap mast-name">
    <a class="nameplate" href="/" aria-label="To1000.com, accueil">TO1000<span class="dot">.</span></a>
    <p class="mast-tag">Le football, chaque jour. Et le compte à rebours du 1000e but de Cristiano Ronaldo.</p>
    {count}
  </div>
  <nav class="wrap sections" aria-label="Rubriques">
    <ul>
      <li><a href="/">À la une</a></li>
      <li><a href="/obrigado-cristiano/" class="hot">Obrigado, Cristiano</a></li>
      <li><a href="/#compteur">Le compteur</a></li>
      <li><a href="/goals.html">Tous les buts</a></li>
      <li><a href="/news.html">Actualités</a></li>
      <li><a href="/coupe-du-monde/" aria-current="page">Coupe du monde</a></li>
    </ul>
  </nav>
</header>
<main id="contenu" class="wrap wc">
{body}
</main>
<footer class="wrap foot">
  <div class="foot-grid">
    <a class="nameplate" href="/">TO1000<span class="dot">.</span></a>
    <nav aria-label="Liens de pied de page">
      <a href="/coupe-du-monde/">Coupe du Monde 2026</a>
      <a href="/coupe-du-monde/matchs-du-jour/">Matchs du jour</a>
      <a href="/news">Actu foot</a>
      <a href="/goals">Compteur CR7</a>
      <a href="/about.html">À propos</a>
      <a href="/privacy.html">Confidentialité</a>
      <a href="/contact.html">Contact</a>
    </nav>
  </div>
  <p class="disclaimer">Fan site non officiel — non affilié à la FIFA ni aux fédérations. Données de matchs factuelles.</p>
</footer>
<script>
// Heure locale du visiteur (progressif — le texte serveur reste en heure de l'Est)
document.querySelectorAll('time[data-utc]').forEach(function(t){{
  try{{
    var d=new Date(t.getAttribute('data-utc'));
    var s=d.toLocaleString('fr-FR',{{weekday:'long',day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'}});
    var el=document.querySelector(t.getAttribute('data-target')||'x');
    (el||t).textContent=s+' (votre heure)';
  }}catch(e){{}}
}});
// Bandeau : date du jour + compteur à jour (progressif, le texte serveur reste valable)
(function(){{
  var d=document.getElementById('today');
  if(d){{try{{var s=new Date().toLocaleDateString('fr-FR',{{weekday:'long',day:'numeric',month:'long',year:'numeric'}});d.textContent=s.charAt(0).toUpperCase()+s.slice(1);}}catch(e){{}}}}
  var b=document.getElementById('mc-goals');
  if(b&&window.fetch){{fetch('/stats.json',{{cache:'no-store'}}).then(function(r){{return r.json();}}).then(function(j){{if(j&&typeof j.goals==='number')b.textContent=j.goals;}}).catch(function(){{}});}}
}})();
</script>
</body>
</html>
"""


def match_line(m: dict, link: bool = True) -> str:
    """Ligne match réutilisable (hub, jour, équipe) — colonne de résultats de journal."""
    ht, at = m["home"], m["away"]
    done = m["state"] == "finished" and m["score_home"] is not None
    score = (f'<b class="sc">{m["score_home"]}–{m["score_away"]}</b>' if done
             else ('<b class="sc live">LIVE</b>' if m["state"] == "live"
                   else f'<span class="hr">{time_fr_et(m["date_iso"])} ET</span>'))
    wh = wa = ""
    if done and m["score_home"] != m["score_away"]:
        wh, wa = (" w", "") if m["score_home"] > m["score_away"] else ("", " w")
    inner = (f'<span class="teams"><span class="t{wh}">{flag(ht)}{h(ht["fr"])}</span>'
             f'<span class="dash"> – </span>'
             f'<span class="t{wa}">{flag(at)}{h(at["fr"])}</span></span>{score}'
             f'<span class="d">{date_fr_et(m["date_iso"])}</span>')
    if link and m.get("slug"):
        return f'<a class="mrow" href="/coupe-du-monde/match/{m["slug"]}/">{inner}</a>'
    return f'<div class="mrow">{inner}</div>'


def match_list(ms) -> str:
    return f'<div class="mlist">{"".join(match_line(m) for m in ms)}</div>'


def sports_event_ld(m: dict) -> dict:
    ht, at = m["home"], m["away"]
    ld = {
        "@context": "https://schema.org", "@type": "SportsEvent",
        "name": f'{ht["fr"]} vs {at["fr"]} — Coupe du Monde 2026, {round_label(m["round"])}',
        "startDate": m["date_iso"].replace("Z", "+00:00"),
        "sport": "Soccer",
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {"@type": "Place", "name": m["venue"] or "Stade à confirmer",
                     "address": {"@type": "PostalAddress",
                                 "addressLocality": m["city"] or "",
                                 "addressCountry": m["country"] or ""}},
        "homeTeam": {"@type": "SportsTeam", "name": ht["fr"]},
        "awayTeam": {"@type": "SportsTeam", "name": at["fr"]},
        "competitor": [{"@type": "SportsTeam", "name": ht["fr"]},
                       {"@type": "SportsTeam", "name": at["fr"]}],
        "organizer": {"@type": "SportsOrganization", "name": "FIFA"},
        "url": f'{SITE}/coupe-du-monde/match/{m["slug"]}/',
    }
    if m["state"] == "finished" and m["score_home"] is not None:
        ld["description"] = (f'Score final : {ht["fr"]} {m["score_home"]}–'
                             f'{m["score_away"]} {at["fr"]}. '
                             + (m.get("status_note") or ""))
    return ld


def render_match(m: dict, all_matches: list[dict]) -> str:
    ht, at = m["home"], m["away"]
    rl, dt, tm = round_label(m["round"]), date_fr_et(m["date_iso"]), time_fr_et(m["date_iso"])
    vs = f'{ht["fr"]} – {at["fr"]}'
    where = ", ".join(x for x in (m["venue"], m["city"], m["country"]) if x)

    if m["state"] == "finished" and m["score_home"] is not None:
        title = f'{vs} : {m["score_home"]}–{m["score_away"]} ({rl}) — Coupe du Monde 2026'
        desc = (f'Résultat {rl} : {ht["fr"]} {m["score_home"]}–{m["score_away"]} {at["fr"]}, '
                f'le {dt} au {m["venue"] or "stade"}. '
                + (m.get("status_note") or "Feuille de match, contexte et parcours des deux équipes."))
        score_block = (f'<div class="scorebig num">{m["score_home"]}<span>–</span>{m["score_away"]}</div>'
                       + (f'<p class="note">{h(m["status_note"])}</p>' if m.get("status_note") else "")
                       + '<p class="mut">Match terminé</p>')
    elif m["state"] == "live":
        title = f'{vs} EN DIRECT ({rl}) — Coupe du Monde 2026'
        desc = f'{vs} en cours, {rl} de la Coupe du Monde 2026 au {m["venue"]}. Score en direct.'
        score_block = (f'<div class="scorebig num live">{m["score_home"] or 0}<span>–</span>{m["score_away"] or 0}</div>'
                       '<p class="mut">Match en cours</p>')
    else:
        title = f'{vs} : heure, stade et contexte ({rl}) — Coupe du Monde 2026'
        desc = (f'{vs}, {rl} de la Coupe du Monde 2026 : le {dt} à {tm} heure de l\'Est '
                f'au {m["venue"] or "stade à confirmer"}{", " + m["city"] if m["city"] else ""}. '
                'Heure locale, stade et parcours des deux équipes.')
        score_block = (f'<div class="ko"><time datetime="{m["date_iso"]}" data-utc="{m["date_iso"]}" '
                       f'data-target="#localtime">{dt} · {tm} heure de l\'Est</time>'
                       '<p id="localtime" class="mut"></p></div>')

    def path_of(team_key: str) -> str:
        tid = m[team_key]["espn_id"]
        rows = [x for x in all_matches
                if tid in (x["home"]["espn_id"], x["away"]["espn_id"]) and x["id"] != m["id"]]
        return match_list(rows[-4:]) if rows else ""

    # matchs précédent / suivant dans le calendrier global (maillage)
    playable = [x for x in all_matches if x.get("slug")]
    idx = next((i for i, x in enumerate(playable) if x["id"] == m["id"]), None)
    prev_m = playable[idx - 1] if idx not in (None, 0) else None
    next_m = playable[idx + 1] if idx is not None and idx + 1 < len(playable) else None
    pn = ""
    if prev_m:
        pn += (f'<a class="prev" href="/coupe-du-monde/match/{prev_m["slug"]}/">← Match précédent : '
               f'<b>{h(prev_m["home"]["fr"])}–{h(prev_m["away"]["fr"])}</b></a>')
    if next_m:
        pn += (f'<a class="next" href="/coupe-du-monde/match/{next_m["slug"]}/">Match suivant : '
               f'<b>{h(next_m["home"]["fr"])}–{h(next_m["away"]["fr"])}</b> →</a>')

    body = f"""
<p class="crumb meta"><a href="/coupe-du-monde/">Coupe du Monde 2026</a> › {h(rl)}</p>
<div class="match-head">
<p class="eyebrow label red">{h(rl)} · {h(dt)}</p>
<h1 class="wc-title"><span class="tn">{flag(ht, 34)} {h(ht["fr"])}</span> – <span class="tn">{h(at["fr"])} {flag(at, 34)}</span></h1>
{score_block}
<p class="venue meta"><span class="label">Stade</span> {h(where) if where else "Stade à confirmer"}</p>
</div>
<div class="teams2">
  <section><h2><a href="/coupe-du-monde/equipe/{ht["slug"]}/">{flag(ht)} Parcours {'du ' if ht["fr"][0] not in 'AEÉIOU' else "de l'"}{h(ht["fr"])}</a></h2>{path_of("home") or '<p class="mut">Premier match du tournoi.</p>'}</section>
  <section><h2><a href="/coupe-du-monde/equipe/{at["slug"]}/">{flag(at)} Parcours {'du ' if at["fr"][0] not in 'AEÉIOU' else "de l'"}{h(at["fr"])}</a></h2>{path_of("away") or '<p class="mut">Premier match du tournoi.</p>'}</section>
</div>
<nav class="pn" aria-label="Matchs précédent et suivant">{pn}</nav>
<p class="backlinks"><a href="/coupe-du-monde/matchs-du-jour/">Matchs du jour</a> · <a href="/coupe-du-monde/">Calendrier complet</a></p>
"""
    og = f'{vs} · {rl} · {dt}, {tm} ET'
    return page(title, desc, f'/coupe-du-monde/match/{m["slug"]}/', body,
                [sports_event_ld(m)], og_title=og)


def render_team(tid: str, t: dict, all_matches: list[dict]) -> str:
    rows = [m for m in all_matches
            if tid in (m["home"]["espn_id"], m["away"]["espn_id"])]
    played = [m for m in rows if m["state"] == "finished"]
    upcoming = [m for m in rows if m["state"] != "finished"]
    alive = bool(upcoming)
    title = f'{t["fr"]} à la Coupe du Monde 2026 : calendrier, résultats, prochain match'
    desc = (f'Tous les matchs {"du " if t["fr"][0] not in "AEÉIOU" else "de l’"}{t["fr"]} à la Coupe du Monde 2026 : '
            f'{len(played)} match{"s" if len(played) > 1 else ""} joué{"s" if len(played) > 1 else ""}'
            + (f', prochain match le {date_fr_et(upcoming[0]["date_iso"])}' if upcoming else ", parcours terminé")
            + ". Heures, stades et résultats.")
    ld = {"@context": "https://schema.org", "@type": "SportsTeam", "name": t["fr"],
          "alternateName": t["en"], "sport": "Soccer",
          "memberOf": {"@type": "SportsOrganization", "name": "FIFA World Cup 2026"},
          "url": f'{SITE}/coupe-du-monde/equipe/{t["slug"]}/'}
    body = f"""
<p class="crumb meta"><a href="/coupe-du-monde/">Coupe du Monde 2026</a> › Équipes</p>
<h1 class="wc-title">{flag(t, 34)} {h(t["fr"])} — Coupe du Monde 2026</h1>
{'<section class="wc-sec"><div class="sec-head"><h2>Prochains matchs</h2></div>' + match_list(upcoming) + '</section>' if upcoming else ''}
{'<section class="wc-sec"><div class="sec-head"><h2>Résultats</h2></div>' + match_list(reversed(played)) + '</section>' if played else ''}
{'' if alive or not played else '<p class="mut end">Parcours terminé pour cette Coupe du Monde.</p>'}
<p class="backlinks"><a href="/coupe-du-monde/matchs-du-jour/">Matchs du jour</a> · <a href="/coupe-du-monde/">Toutes les équipes</a></p>
"""
    return page(title, desc, f'/coupe-du-monde/equipe/{t["slug"]}/', body, [ld])


def render_hub(all_matches: list[dict]) -> str:
    upcoming = [m for m in all_matches if m["state"] != "finished"]
    finished = [m for m in all_matches if m["state"] == "finished"]

    def by_round(ms):
        rounds: dict[str, list] = {}
        for m in ms:
            rounds.setdefault(m["round"], []).append(m)
        return sorted(rounds.items(),
                      key=lambda kv: ROUND_ORDER.index(kv[0]) if kv[0] in ROUND_ORDER else 99)

    up_html = "".join(f'<section class="round"><h3>{h(round_label(r))}</h3>{match_list(ms)}</section>'
                      for r, ms in by_round(upcoming))
    res_html = "".join(f'<details{" open" if i == 0 else ""}><summary><span>{h(round_label(r))}</span> '
                       f'<span class="n">{len(ms)} match{"s" if len(ms) > 1 else ""}</span></summary>'
                       f'{match_list(reversed(ms))}</details>'
                       for i, (r, ms) in enumerate(reversed(by_round(finished))))
    teams_html = "".join(
        f'<li><a href="/coupe-du-monde/equipe/{t["slug"]}/">{flag(t, 20)}{h(t["fr"])}</a></li>'
        for t in sorted(TEAMS.values(), key=lambda x: x["fr"]))

    title = "Coupe du Monde 2026 : calendrier complet, résultats et équipes"
    desc = ("Calendrier de la Coupe du Monde 2026 (États-Unis, Canada, Mexique) : "
            f"les {len(upcoming)} matchs à venir avec heure et stade, tous les résultats, "
            "et la page de chacune des 48 équipes. Mis à jour chaque jour.")
    ld = {"@context": "https://schema.org", "@type": "SportsEvent",
          "name": "Coupe du Monde de la FIFA 2026",
          "startDate": "2026-06-11", "endDate": "2026-07-19",
          "sport": "Soccer",
          "location": [{"@type": "Country", "name": c} for c in ("USA", "Canada", "Mexico")],
          "organizer": {"@type": "SportsOrganization", "name": "FIFA"},
          "url": f"{SITE}/coupe-du-monde/"}
    body = f"""
<div class="hub-head">
<h1 class="wc-title">Coupe du Monde 2026</h1>
<p class="eyebrow standfirst">Calendrier, résultats et équipes — mis à jour chaque jour · <a href="/coupe-du-monde/matchs-du-jour/">Voir les matchs du jour →</a></p>
</div>
<section class="wc-sec"><div class="sec-head"><h2>Matchs à venir</h2></div>
{up_html or '<p class="mut">Tournoi terminé.</p>'}
</section>
<section class="wc-sec"><div class="sec-head"><h2>Résultats</h2></div>
{res_html}
</section>
<section class="wc-sec"><div class="sec-head"><h2>Les 48 équipes</h2></div>
<ul class="teamgrid">{teams_html}</ul>
</section>
"""
    return page(title, desc, "/coupe-du-monde/", body, [ld])


def render_today(all_matches: list[dict]) -> str:
    today = datetime.now(timezone.utc).astimezone(ET).date()
    todays = [m for m in all_matches
              if datetime.fromisoformat(m["date_iso"].replace("Z", "+00:00")).astimezone(ET).date() == today]
    if todays:
        heading, ms = f"Les matchs du {today.day} {date_fr_et(todays[0]['date_iso']).split(' ', 1)[1]}", todays
        desc_head = f"{len(ms)} match{'s' if len(ms) > 1 else ''} de Coupe du Monde aujourd'hui"
    else:
        nxt = [m for m in all_matches if m["state"] != "finished"]
        ms = nxt[:6]
        heading = "Aucun match aujourd'hui — prochains matchs"
        desc_head = "Aucun match aujourd'hui ; voici les prochains matchs"
    title = "Matchs du jour — Coupe du Monde 2026 (heures et chaînes)"
    desc = (f"{desc_head} : heure du coup d'envoi (convertie à votre fuseau), stade et lien "
            "vers la fiche de chaque match. Page mise à jour tous les jours.")
    body = f"""
<p class="crumb meta"><a href="/coupe-du-monde/">Coupe du Monde 2026</a> › Matchs du jour</p>
<h1 class="wc-title">Matchs du jour</h1>
<p class="eyebrow standfirst">{h(heading)}</p>
{match_list(ms) if ms else '<p class="mut">Calendrier à venir.</p>'}
<p class="backlinks"><a href="/coupe-du-monde/">Calendrier complet et résultats →</a></p>
"""
    return page(title, desc, "/coupe-du-monde/matchs-du-jour/", body, [])


CSS = """/* Section Coupe du Monde — charte « journal du matin » (nov. 2026).
   Généré par scripts/wc_pages.py : ne pas éditer à la main.
   La base (papier, encre, rouge, bandeau, rubriques, pied) vient de
   /css/edition.css ; ici seulement ce qui est propre à la section :
   colonnes de résultats, fiche de match, index des équipes. */
.wc{padding-top:22px;padding-bottom:40px}
.wc a{text-decoration-color:var(--red);text-underline-offset:3px}
.crumb{margin-bottom:18px}
.crumb a{color:var(--ink);text-decoration:none;font-weight:600}
.crumb a:hover{color:var(--red);text-decoration:underline}
.mut{font-family:var(--sans);font-size:14px;color:var(--ink-2);padding:12px 0}
.mut.end{margin-top:4px}
.flag{display:inline-block;width:auto;height:.72em;vertical-align:baseline;outline:1px solid rgba(21,21,19,.14);outline-offset:0}

/* ---------- Titres de page ---------- */
.wc-title{
  font-family:var(--serif);font-weight:600;font-optical-sizing:auto;
  font-size:clamp(38px,6.4vw,76px);line-height:.98;letter-spacing:-.02em;
  overflow-wrap:break-word;
}
.wc-title .flag{height:.46em;vertical-align:.12em}
.wc-title .tn{display:inline-block;max-width:100%}
.eyebrow{margin-bottom:10px}
.eyebrow.standfirst{margin:14px 0 0;max-width:52ch}
.eyebrow.standfirst a{color:var(--red);font-family:var(--sans);font-weight:600;font-size:.82em;text-decoration:none;white-space:nowrap}
.eyebrow.standfirst a:hover{text-decoration:underline}
.hub-head{padding-top:16px;padding-bottom:6px}
.wc-sec{padding-top:34px}
.wc-sec .sec-head{margin-bottom:6px}
.wc-sec .sec-head h2{font-size:clamp(26px,3.4vw,36px)}

/* ---------- Colonne de résultats (une ligne = un match) ---------- */
.mlist{display:grid;border-top:1px solid var(--rule)}
@media (min-width:900px){
  .mlist{grid-template-columns:1fr 1fr;column-gap:36px}
  .teams2 .mlist,.match-col .mlist{grid-template-columns:1fr}
}
.mrow{
  display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:14px;row-gap:1px;
  align-items:baseline;padding:10px 0 9px;border-bottom:1px solid var(--rule-soft);
  color:var(--ink);text-decoration:none;
}
.mrow .teams{font-family:var(--sans);font-stretch:87.5%;font-weight:500;font-size:17px;line-height:1.25;min-width:0}
.mrow .t{white-space:nowrap}
.mrow .t .flag{margin-inline-end:6px}
.mrow .t.w{font-weight:800}
.mrow .dash{color:var(--ink-2)}
.mrow .sc,.mrow .hr{
  font-family:var(--sans);font-stretch:75%;font-weight:800;font-size:24px;line-height:1;
  font-variant-numeric:tabular-nums lining-nums;text-align:end;min-width:2.6ch;white-space:nowrap;
}
.mrow .hr{font-size:17px;font-weight:700;color:var(--ink-2)}
.mrow .sc.live{color:var(--red);font-size:13px;font-stretch:100%;letter-spacing:.08em}
.mrow .d{grid-column:1/-1;font-family:var(--sans);font-size:13px;color:var(--ink-2);line-height:1.35}
a.mrow:hover .teams{text-decoration:underline;text-decoration-color:var(--red);text-decoration-thickness:2px;text-underline-offset:4px}
a.mrow:hover .sc{color:var(--red)}

/* ---------- Tours (hub) : dépliables, sans fioriture ---------- */
.round h3{font-family:var(--sans);font-weight:700;font-size:12px;letter-spacing:.06em;text-transform:uppercase;padding:18px 0 8px}
details{border-bottom:1px solid var(--rule)}
details[open]{padding-bottom:22px}
summary{
  list-style:none;cursor:pointer;display:flex;align-items:baseline;gap:12px;
  padding:14px 0 12px;font-family:var(--sans);font-stretch:75%;font-weight:800;font-size:24px;line-height:1.1;
}
summary::-webkit-details-marker{display:none}
summary::after{content:"+";margin-inline-start:auto;font-stretch:100%;font-weight:600;font-size:22px;color:var(--red);line-height:1}
details[open] > summary::after{content:"–"}
summary .n{font-stretch:100%;font-weight:500;font-size:13px;color:var(--ink-2);font-variant-numeric:tabular-nums}
summary:hover > span:first-child{color:var(--red)}
details .mlist{border-top:1px solid var(--rule)}

/* ---------- Index des 48 équipes ---------- */
.teamgrid{list-style:none;columns:2;column-gap:24px;border-top:1px solid var(--rule);padding-top:4px}
@media (min-width:640px){.teamgrid{columns:3}}
@media (min-width:980px){.teamgrid{columns:4;column-gap:36px}}
.teamgrid li{break-inside:avoid;border-bottom:1px solid var(--rule-soft)}
.teamgrid a{display:block;padding:9px 0 8px;font-family:var(--sans);font-weight:600;font-size:15px;line-height:1.3;text-decoration:none;color:var(--ink)}
.teamgrid a .flag{margin-inline-end:8px;height:.8em}
.teamgrid a:hover{color:var(--red);text-decoration:underline}

/* ---------- Fiche de match ---------- */
.match-head{padding-bottom:4px}
.scorebig{
  display:flex;align-items:center;gap:.12em;margin:18px 0 10px;
  font-size:clamp(96px,22vw,200px);color:var(--ink);
}
.scorebig span{color:var(--ink-2);font-weight:500;font-size:.5em;line-height:1}
.scorebig.live{color:var(--red)}
.note{font-family:var(--serif);font-style:italic;font-size:18px;color:var(--ink);max-width:60ch;margin-bottom:4px}
.match-head .mut{padding:0 0 8px}
.ko{margin:18px 0 8px}
.ko time{display:block;font-family:var(--sans);font-stretch:75%;font-weight:800;font-size:clamp(26px,4vw,40px);line-height:1.05;font-variant-numeric:tabular-nums}
.ko .mut{padding:6px 0 0}
.venue{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px;border-top:1px solid var(--rule-soft);padding-top:10px;margin-top:8px;font-size:15px;color:var(--ink)}
.venue .label{color:var(--ink-2)}

.teams2{display:grid;grid-template-columns:1fr;gap:0 40px;margin-top:30px}
@media (min-width:760px){
  .teams2{grid-template-columns:1fr 1fr}
  .teams2 section + section{border-inline-start:1px solid var(--rule-soft);padding-inline-start:40px}
}
.teams2 section{padding-bottom:22px}
.teams2 h2{font-family:var(--sans);font-stretch:75%;font-weight:800;font-size:clamp(22px,2.6vw,28px);line-height:1.05;border-top:3px solid var(--rule);padding:8px 0 10px}
.teams2 h2 a{text-decoration:none;color:var(--ink)}
.teams2 h2 a:hover{color:var(--red);text-decoration:underline}
.teams2 h2 .flag{margin-inline-end:8px;height:.7em}

.pn{display:grid;grid-template-columns:1fr;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);margin-top:10px}
.pn a{display:block;padding:12px 0;font-family:var(--sans);font-size:14px;color:var(--ink-2);text-decoration:none}
.pn a b{color:var(--ink);font-weight:700}
.pn a:hover b{color:var(--red);text-decoration:underline}
.pn a + a{border-top:1px solid var(--rule-soft)}
@media (min-width:640px){
  .pn{grid-template-columns:1fr 1fr}
  .pn a + a{border-top:0;border-inline-start:1px solid var(--rule-soft);padding-inline-start:18px}
  .pn a.next{text-align:end}
  .pn a.next:only-child{grid-column:2}
}
.backlinks{margin-top:22px;font-family:var(--sans);font-size:14px;color:var(--ink-2)}
.backlinks a{color:var(--red);font-weight:600;text-decoration:none}
.backlinks a:hover{text-decoration:underline}
"""


def main() -> int:
    offline = "--offline" in sys.argv
    if "--live-only" in sys.argv:
        cached = load_cache() or []
        # Self-heal (fix 2026-07-04) : si le cron quotidien de 04:10 a été sauté
        # par GitHub, /matchs-du-jour/ reste sur la veille — on force alors un
        # run complet même hors fenêtre live.
        today_et = datetime.now(timezone.utc).astimezone(ET)
        stale_today = True
        try:
            html = (OUT / "matchs-du-jour" / "index.html").read_text(encoding="utf-8")
            from lib.wc_data import MONTHS_FR
            stale_today = f"{today_et.day} {MONTHS_FR[today_et.month]}" not in html
        except Exception:
            pass
        if not is_live_window(cached, datetime.now(timezone.utc)) and not stale_today:
            print("[wc] aucun match en fenêtre live et matchs-du-jour à jour — rien à faire")
            return 0
    matches = (load_cache() if offline else None) or fetch_matches()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wc.css").write_text(CSS, encoding="utf-8")

    (OUT / "index.html").write_text(render_hub(matches), encoding="utf-8")
    (OUT / "matchs-du-jour").mkdir(exist_ok=True)
    (OUT / "matchs-du-jour" / "index.html").write_text(render_today(matches), encoding="utf-8")

    n_match = 0
    for m in matches:
        if not m.get("slug"):
            continue
        d = OUT / "match" / m["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_match(m, matches), encoding="utf-8")
        n_match += 1

    n_team = 0
    for tid, t in TEAMS.items():
        d = OUT / "equipe" / t["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_team(tid, t, matches), encoding="utf-8")
        n_team += 1

    print(f"[wc] hub + matchs-du-jour + {n_match} pages match + {n_team} pages équipe → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
