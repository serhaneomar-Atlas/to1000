#!/usr/bin/env python3
"""wc_pages.py — génère la section /coupe-du-monde/ (SEO statique, style ESTÁDIO).

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
         '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@400;500;600;700'
         '&family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">')


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
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="To1000 — Football News" href="/rss.xml">
{FONTS}
<link rel="stylesheet" href="/coupe-du-monde/wc.css">
{ld}
</head>
<body>
<header class="topbar">
  <a class="brand" href="/">TO<span>1000</span></a>
  <nav>
    <a href="/">Accueil</a><a href="/news">News</a><a href="/goals">Buts CR7</a>
    <a href="/coupe-du-monde/" class="on">Coupe du Monde</a>
  </nav>
</header>
<main>
{body}
</main>
<footer class="foot">
  <p><a href="/coupe-du-monde/">Coupe du Monde 2026</a> · <a href="/coupe-du-monde/matchs-du-jour/">Matchs du jour</a> · <a href="/news">Actu foot</a> · <a href="/goals">Compteur CR7</a></p>
  <p class="mut">Fan site non officiel — non affilié à la FIFA ni aux fédérations. Données de matchs factuelles.
  <a href="/about.html">À propos</a> · <a href="/privacy.html">Confidentialité</a> · <a href="/contact.html">Contact</a></p>
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
</script>
</body>
</html>
"""


def match_line(m: dict, link: bool = True) -> str:
    """Ligne match réutilisable (hub, jour, équipe)."""
    ht, at = m["home"], m["away"]
    score = (f'<b class="sc">{m["score_home"]}–{m["score_away"]}</b>'
             if m["state"] == "finished" and m["score_home"] is not None
             else ('<b class="sc live">LIVE</b>' if m["state"] == "live"
                   else f'<span class="hr">{time_fr_et(m["date_iso"])} ET</span>'))
    inner = (f'<span class="t">{flag(ht)} {h(ht["fr"])}</span>{score}'
             f'<span class="t away">{h(at["fr"])} {flag(at)}</span>'
             f'<span class="d">{date_fr_et(m["date_iso"])}</span>')
    if link and m.get("slug"):
        return f'<a class="mrow" href="/coupe-du-monde/match/{m["slug"]}/">{inner}</a>'
    return f'<div class="mrow">{inner}</div>'


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
        score_block = (f'<div class="scorebig">{m["score_home"]}<span>–</span>{m["score_away"]}</div>'
                       + (f'<p class="note">{h(m["status_note"])}</p>' if m.get("status_note") else "")
                       + '<p class="mut">Match terminé</p>')
    elif m["state"] == "live":
        title = f'{vs} EN DIRECT ({rl}) — Coupe du Monde 2026'
        desc = f'{vs} en cours, {rl} de la Coupe du Monde 2026 au {m["venue"]}. Score en direct.'
        score_block = (f'<div class="scorebig live">{m["score_home"] or 0}<span>–</span>{m["score_away"] or 0}</div>'
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
        return "".join(match_line(x) for x in rows[-4:])

    # matchs précédent / suivant dans le calendrier global (maillage)
    playable = [x for x in all_matches if x.get("slug")]
    idx = next((i for i, x in enumerate(playable) if x["id"] == m["id"]), None)
    prev_m = playable[idx - 1] if idx not in (None, 0) else None
    next_m = playable[idx + 1] if idx is not None and idx + 1 < len(playable) else None
    pn = ""
    if prev_m:
        pn += (f'<a href="/coupe-du-monde/match/{prev_m["slug"]}/">← Match précédent : '
               f'{h(prev_m["home"]["fr"])}–{h(prev_m["away"]["fr"])}</a>')
    if next_m:
        pn += (f'<a href="/coupe-du-monde/match/{next_m["slug"]}/">Match suivant : '
               f'{h(next_m["home"]["fr"])}–{h(next_m["away"]["fr"])} →</a>')

    body = f"""
<p class="crumb"><a href="/coupe-du-monde/">Coupe du Monde 2026</a> › {h(rl)}</p>
<h1>{flag(ht, 34)} {h(vs)} {flag(at, 34)}</h1>
<p class="eyebrow">{h(rl)} · {h(dt)}</p>
{score_block}
<p class="venue">🏟️ {h(where) if where else "Stade à confirmer"}</p>
<div class="teams2">
  <section><h2><a href="/coupe-du-monde/equipe/{ht["slug"]}/">{flag(ht)} Parcours {'du ' if ht["fr"][0] not in 'AEÉIOU' else "de l'"}{h(ht["fr"])}</a></h2>{path_of("home") or '<p class="mut">Premier match du tournoi.</p>'}</section>
  <section><h2><a href="/coupe-du-monde/equipe/{at["slug"]}/">{flag(at)} Parcours {'du ' if at["fr"][0] not in 'AEÉIOU' else "de l'"}{h(at["fr"])}</a></h2>{path_of("away") or '<p class="mut">Premier match du tournoi.</p>'}</section>
</div>
<nav class="pn">{pn}</nav>
<p class="backlinks"><a href="/coupe-du-monde/matchs-du-jour/">📅 Matchs du jour</a> · <a href="/coupe-du-monde/">Calendrier complet</a></p>
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
<p class="crumb"><a href="/coupe-du-monde/">Coupe du Monde 2026</a> › Équipes</p>
<h1>{flag(t, 34)} {h(t["fr"])} — Coupe du Monde 2026</h1>
{'<section><h2>Prochains matchs</h2>' + ''.join(match_line(m) for m in upcoming) + '</section>' if upcoming else ''}
{'<section><h2>Résultats</h2>' + ''.join(match_line(m) for m in reversed(played)) + '</section>' if played else ''}
{'' if alive or not played else '<p class="mut">Parcours terminé pour cette Coupe du Monde.</p>'}
<p class="backlinks"><a href="/coupe-du-monde/matchs-du-jour/">📅 Matchs du jour</a> · <a href="/coupe-du-monde/">Toutes les équipes</a></p>
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

    up_html = "".join(f'<section><h3>{h(round_label(r))}</h3>{"".join(match_line(m) for m in ms)}</section>'
                      for r, ms in by_round(upcoming))
    res_html = "".join(f'<details{" open" if i == 0 else ""}><summary>{h(round_label(r))} ({len(ms)} matchs)</summary>'
                       f'{"".join(match_line(m) for m in reversed(ms))}</details>'
                       for i, (r, ms) in enumerate(reversed(by_round(finished))))
    teams_html = "".join(
        f'<a href="/coupe-du-monde/equipe/{t["slug"]}/">{flag(t, 20)} {h(t["fr"])}</a>'
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
<h1>Coupe du Monde 2026</h1>
<p class="eyebrow">Calendrier, résultats et équipes — mis à jour chaque jour · <a href="/coupe-du-monde/matchs-du-jour/">Voir les matchs du jour →</a></p>
<h2>Matchs à venir</h2>
{up_html or '<p class="mut">Tournoi terminé.</p>'}
<h2>Résultats</h2>
{res_html}
<h2>Les 48 équipes</h2>
<div class="teamgrid">{teams_html}</div>
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
<p class="crumb"><a href="/coupe-du-monde/">Coupe du Monde 2026</a> › Matchs du jour</p>
<h1>Matchs du jour</h1>
<p class="eyebrow">{h(heading)}</p>
{''.join(match_line(m) for m in ms) or '<p class="mut">Calendrier à venir.</p>'}
<p class="backlinks"><a href="/coupe-du-monde/">Calendrier complet et résultats →</a></p>
"""
    return page(title, desc, "/coupe-du-monde/matchs-du-jour/", body, [])


CSS = """/* ESTÁDIO — section Coupe du Monde */
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{background:#05070b;color:#eef2f6;font-family:'Hanken Grotesk',system-ui,sans-serif;line-height:1.55}
a{color:#f2c14e;text-decoration:none}a:hover{text-decoration:underline}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid rgba(242,193,78,.25)}
.brand{font-family:Anton,sans-serif;font-size:22px;color:#eef2f6;letter-spacing:.04em}.brand span{color:#f2c14e}
.topbar nav a{margin-left:16px;color:#9aa6b4;font-family:Oswald,sans-serif;text-transform:uppercase;font-size:13px;letter-spacing:.06em}
.topbar nav a.on,.topbar nav a:hover{color:#f2c14e}
main{max-width:860px;margin:0 auto;padding:28px 16px 60px}
h1{font-family:Anton,sans-serif;font-size:clamp(28px,5vw,44px);letter-spacing:.02em;margin:8px 0;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
h2{font-family:Oswald,sans-serif;font-size:20px;text-transform:uppercase;letter-spacing:.06em;color:#f2c14e;margin:28px 0 10px}
h3{font-family:Oswald,sans-serif;font-size:16px;color:#9aa6b4;text-transform:uppercase;margin:18px 0 8px}
.eyebrow{color:#9aa6b4;margin-bottom:14px}.mut{color:#9aa6b4;font-size:14px}
.crumb{font-size:13px;color:#9aa6b4;margin-bottom:6px}
.flag{border-radius:3px;vertical-align:-3px}
.mrow{display:grid;grid-template-columns:1fr auto 1fr auto;gap:10px;align-items:center;background:#0d1118;
 border:1px solid rgba(154,166,180,.15);border-radius:8px;padding:10px 14px;margin:6px 0;color:#eef2f6}
.mrow:hover{border-color:#f2c14e}
.mrow .t{display:flex;align-items:center;gap:8px;font-weight:600}.mrow .t.away{justify-content:flex-end}
.mrow .sc{font-family:Oswald,sans-serif;font-size:18px;color:#f2c14e}.sc.live{color:#ff5a5a;animation:pulse 1.6s infinite}
.mrow .hr{font-family:Oswald,sans-serif;color:#9aa6b4}
.mrow .d{grid-column:1/-1;font-size:12.5px;color:#9aa6b4}
@keyframes pulse{50%{opacity:.5}}
.scorebig{font-family:Anton,sans-serif;font-size:64px;color:#f2c14e;margin:10px 0}.scorebig span{color:#9aa6b4;margin:0 10px}
.scorebig.live{color:#ff5a5a}
.ko time{font-family:Oswald,sans-serif;font-size:22px;color:#f2c14e}
.venue{margin:10px 0 4px}
.note{color:#9aa6b4;font-style:italic}
.teams2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:24px}
@media(max-width:640px){.teams2{grid-template-columns:1fr}}
.teams2 h2{font-size:16px;margin:0 0 8px}
.teamgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px}
.teamgrid a{background:#0d1118;border:1px solid rgba(154,166,180,.15);border-radius:8px;padding:9px 12px;color:#eef2f6;display:flex;align-items:center;gap:8px;font-size:14px}
.teamgrid a:hover{border-color:#f2c14e;text-decoration:none}
details{margin:8px 0}summary{cursor:pointer;font-family:Oswald,sans-serif;color:#9aa6b4;text-transform:uppercase;font-size:15px;padding:6px 0}
.pn{display:flex;justify-content:space-between;gap:12px;margin:26px 0 8px;font-size:14px;flex-wrap:wrap}
.backlinks{margin-top:18px}
.foot{border-top:1px solid rgba(154,166,180,.2);padding:22px 16px;text-align:center;font-size:13.5px;color:#9aa6b4}
.foot p{margin:4px 0}
"""


def main() -> int:
    offline = "--offline" in sys.argv
    if "--live-only" in sys.argv:
        cached = load_cache() or []
        if not is_live_window(cached, datetime.now(timezone.utc)):
            print("[wc] aucun match en fenêtre live — rien à faire")
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
