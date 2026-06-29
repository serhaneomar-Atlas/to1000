#!/usr/bin/env python3
"""
kaizen_audit.py — Boucle d'amélioration continue (read-only) pour to1000.com.

Sonde le SITE LIVE (https://to1000.com), mesure des métriques objectives, et
génère un rapport markdown au format des audit_logs existants
(🟢 Sain / 🟠 À surveiller / 🔴 Priorité / 💡 Quick wins / 📊 Métriques).

PRINCIPE: ce script NE MODIFIE JAMAIS le site. Il PROPOSE, ne corrige pas.
Il écrit deux fichiers:
  - KAIZEN.md                       (à la racine — dernier rapport, écrasé)
  - scripts/audit_logs/AAAA-MM-JJ.md (archive datée)

Il imprime aussi un résumé court sur stdout (utilisé pour l'issue GitHub).

Cloudflare bloque les User-Agents non-navigateur (403). On envoie donc un UA
navigateur. Aucune authentification requise (tout est public).

USAGE
=====
  python scripts/kaizen_audit.py            # audit complet, écrit les fichiers
  python scripts/kaizen_audit.py --summary  # n'imprime que le résumé (stdout)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOGS_DIR = SCRIPT_DIR / "audit_logs"
BASE = "https://to1000.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
FRESH_HOURS = 24          # seuil de fraîcheur news.json
STATS_STALE_DAYS = 3      # seuil au-delà duquel stats.json est jugé périmé


def fetch(path: str, as_json: bool = False, timeout: int = 20):
    """Retourne (status_code, body_text|dict|None, error|None)."""
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            if as_json:
                return r.status, json.loads(raw), None
            return r.status, raw, None
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, None, str(e)


def hours_since(iso_ts: str) -> float | None:
    try:
        ts = iso_ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:  # noqa: BLE001
        return None


def run_audit() -> dict:
    """Collecte tous les faits. Retourne un dict de findings classés."""
    green, amber, red, wins, metrics = [], [], [], [], {}
    now = datetime.now(timezone.utc)

    # --- news.json ---
    st, news, err = fetch("/news.json", as_json=True)
    if news:
        gen = news.get("generated_at", "")
        h = hours_since(gen)
        items = news.get("items") or news.get("published_items") or []
        n_items = news.get("published") or len(items)
        with_img = sum(1 for i in items if (i.get("image_url") or i.get("image")))
        metrics["news_generated_at"] = gen
        metrics["news_items"] = n_items
        metrics["news_with_image"] = with_img
        metrics["news_feeds_failed"] = news.get("feeds_failed")
        if h is not None and h < FRESH_HOURS:
            green.append(f"`news.json` frais — généré il y a {h:.1f}h ({gen}).")
        elif h is not None:
            red.append(f"`news.json` périmé — {h/24:.1f} jours ({gen}). Pipeline news bloqué ?")
        if isinstance(news.get("feeds_failed"), int) and news["feeds_failed"] >= 12:
            amber.append(f"{news['feeds_failed']} flux RSS en échec — nettoyer `sources.json`.")
        if n_items and with_img / max(n_items, 1) < 0.5:
            amber.append(f"Seulement {with_img}/{n_items} news avec image (<50%).")
    else:
        red.append(f"`news.json` inaccessible ({err}).")

    # --- stats.json + cohérence compteur ---
    st, stats, err = fetch("/stats.json", as_json=True)
    live_goals = None
    if stats:
        live_goals = stats.get("goals")
        rem = stats.get("remaining")
        lu = stats.get("last_updated", "")
        h = hours_since(lu)
        metrics["stats_goals"] = live_goals
        metrics["stats_remaining"] = rem
        metrics["stats_last_updated"] = lu
        if h is not None and h / 24 > STATS_STALE_DAYS:
            red.append(f"`stats.json` périmé — {h/24:.1f} jours ({lu}). "
                       f"Relancer `update_stats_v2.py`.")
        elif h is not None:
            green.append(f"`stats.json` à jour — il y a {h/24:.1f} jours ({lu}).")
        # next_match passé ?
        nm = stats.get("next_match") or {}
        ko = nm.get("kickoff_utc")
        if ko:
            kh = hours_since(ko)
            metrics["next_match"] = f"{nm.get('home_team','?')} vs {nm.get('away_team','?')} ({ko})"
            if kh is not None and kh > 6:  # >6h dans le passé
                red.append(f"`next_match` périmé — annonce {nm.get('home_team')} vs "
                           f"{nm.get('away_team')} du {ko} (déjà joué il y a {kh/24:.1f}j). "
                           f"Mettre à jour ou passer en `off_season`.")
    else:
        red.append(f"`stats.json` inaccessible ({err}).")

    # --- cohérence du compteur entre pages ---
    st, home, _ = fetch("/")
    home_nums = set()
    if home:
        for m in re.findall(r"\b(9[0-9]{2})\s*(?:scored|/1000|official career goals|Goals\.)", home):
            home_nums.add(m)
        # nombre dans le hero
        hero = re.search(r'hero-score-current">(\d{3,4})<', home)
        if hero:
            home_nums.add(hero.group(1))
        metrics["home_goals_seen"] = sorted(home_nums)
    st, goals_page, _ = fetch("/goals")
    goals_title_num = None
    if goals_page:
        m = re.search(r"All (\d{3,4}) Goals", goals_page)
        if m:
            goals_title_num = m.group(1)
            metrics["goals_page_title"] = f"All {goals_title_num} Goals"

    # verdict cohérence
    all_counts = set()
    if live_goals is not None:
        all_counts.add(str(live_goals))
    all_counts |= home_nums
    if goals_title_num:
        all_counts.add(goals_title_num)
    if len(all_counts) > 1:
        red.append(f"Compteur INCOHÉRENT entre pages: valeurs vues = "
                   f"{sorted(all_counts)} (stats.json={live_goals}, "
                   f"home={sorted(home_nums)}, goals='{goals_title_num}'). "
                   f"Unifier depuis stats.json via update_html_counts.py au deploy.")
        wins.append("Régénérer home + /goals depuis stats.json pour un compteur unique.")
    elif all_counts:
        green.append(f"Compteur cohérent partout: {all_counts.pop()}.")

    # --- pages clés (codes HTTP) ---
    pages = ["/", "/news/", "/blog/", "/goals", "/sitemap.xml", "/robots.txt", "/manifest.json"]
    broken = []
    for p in pages:
        code, _, _ = fetch(p)
        if code not in (200, 301, 308):
            broken.append(f"{p} → {code}")
    if broken:
        red.append("Pages clés en erreur: " + ", ".join(broken))
    else:
        green.append(f"Toutes les pages clés répondent (codes 200/redir) : {', '.join(pages)}.")

    # --- sitemap volume ---
    code, sm, _ = fetch("/sitemap.xml")
    if sm:
        n_urls = sm.count("<loc>")
        metrics["sitemap_urls"] = n_urls
        green.append(f"Sitemap: {n_urls} URLs.")

    # --- SEO/perf homepage ---
    if home:
        metrics["hreflang"] = len(re.findall(r'hreflang="', home))
        metrics["jsonld_blocks"] = home.count("application/ld+json")
        imgs = re.findall(r"<img\b[^>]*>", home)
        lazy = sum(1 for i in imgs if "loading" in i)
        metrics["img_lazy"] = f"{lazy}/{len(imgs)}"
        blanks = re.findall(r'target="_blank"', home)
        noopen = home.count("noopener")
        if blanks and noopen < len(blanks):
            amber.append(f"{len(blanks)-noopen} lien(s) _blank sans rel=noopener.")
        if "FAQPage" in home:
            amber.append("Schema FAQPage présent — Google a retiré les rich results FAQ "
                         "(mai 2026); inerte, retirable.")

    return {"green": green, "amber": amber, "red": red, "wins": wins,
            "metrics": metrics, "now": now}


def render(report: dict) -> str:
    now = report["now"].strftime("%Y-%m-%d %H:%M UTC")
    day = report["now"].strftime("%Y-%m-%d")
    L = [f"# Kaizen — audit live to1000.com — {day}", "",
         f"> Audit automatique read-only (généré {now}). **Aucune correction "
         f"appliquée** — ce rapport PROPOSE, il ne modifie pas le site. "
         f"Source de vérité = le live `https://to1000.com`.", ""]

    def section(title, items, empty):
        L.append(f"## {title}")
        if items:
            L.extend(f"- {x}" for x in items)
        else:
            L.append(f"_{empty}_")
        L.append("")

    section("🔴 Priorité", report["red"], "Rien de critique. 🎉")
    section("🟠 À surveiller", report["amber"], "RAS.")
    section("🟢 Sain", report["green"], "—")
    section("💡 Quick wins", report["wins"], "—")

    L.append("## 📊 Métriques")
    for k, v in report["metrics"].items():
        L.append(f"- **{k}**: {v}")
    L.append("")
    L.append("---")
    L.append(f"_Prochain audit automatique: lundi suivant. Lancer à la demande: "
             f"`python scripts/kaizen_audit.py`._")
    return "\n".join(L)


def short_summary(report: dict) -> str:
    r, a = len(report["red"]), len(report["amber"])
    head = f"{r} priorité, {a} à surveiller, {len(report['green'])} sain."
    lines = [head, ""]
    if report["red"]:
        lines.append("🔴 Priorités:")
        lines.extend(f"- {x}" for x in report["red"])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true",
                    help="n'imprime que le résumé court (pour l'issue GitHub)")
    args = ap.parse_args()

    report = run_audit()

    if args.summary:
        print(short_summary(report))
        return 0

    md = render(report)
    (PROJECT_DIR / "KAIZEN.md").write_text(md, encoding="utf-8")
    LOGS_DIR.mkdir(exist_ok=True)
    day = report["now"].strftime("%Y-%m-%d")
    (LOGS_DIR / f"{day}.md").write_text(md, encoding="utf-8")

    print(f"OK — rapport écrit dans KAIZEN.md et scripts/audit_logs/{day}.md")
    print()
    print(short_summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
