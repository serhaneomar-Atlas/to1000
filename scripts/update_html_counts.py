"""
update_html_counts.py — Synchronise les nombres hardcodes (compteur, remaining,
date "As of X") dans les fichiers HTML statiques avec public/stats.json.

Pourquoi: public/index.html sert le compteur live via fetch(stats.json), mais
les meta tags, le JSON-LD Schema.org, les i18n bundles JS et plusieurs spans
HTML visibles sont en dur. Sans ce script, Google et tous les partages
sociaux voient une valeur figee.

A executer apres update_stats_v2.py et avant le deploiement.

USAGE
=====
  python update_html_counts.py             # applique les changements
  python update_html_counts.py --dry-run   # affiche le diff sans ecrire
  python update_html_counts.py --verbose   # liste chaque substitution
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
PUBLIC_DIR = PROJECT_DIR / "public"
STATS_FILE = PUBLIC_DIR / "stats.json"

MONTHS_EN = ["January","February","March","April","May","June",
             "July","August","September","October","November","December"]
MONTHS_FR = ["janvier","fevrier","mars","avril","mai","juin",
             "juillet","aout","septembre","octobre","novembre","decembre"]
MONTHS_ES = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]


def load_stats() -> dict:
    with STATS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def parse_month_year(iso_ts: str):
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    return dt.month, dt.year


def build_patterns(goals, remaining, month, year):
    g, r = str(goals), str(remaining)
    me, mf, mes = MONTHS_EN[month-1], MONTHS_FR[month-1], MONTHS_ES[month-1]

    return [
        # Meta English
        (re.compile(r"\b\d{3,4} scored, \d{1,3} to go"), f"{g} scored, {r} to go", "meta-en"),
        (re.compile(r"\xe2\x80\x94 \d{3,4}/1000 Goals".encode().decode()), f"— {g}/1000 Goals", "og-title-dash"),
        (re.compile(r"— \d{3,4}/1000 Goals"), f"— {g}/1000 Goals", "og-title"),
        (re.compile(r"— \d{3,4}/1000 \| Road to 1000"), f"— {g}/1000 | Road to 1000", "twitter-title"),
        (re.compile(r"\b\d{3,4} out of 1000 (career goals|goals)"), lambda m: f"{g} out of 1000 {m.group(1)}", "out-of-1000"),
        (re.compile(r"all \d{3,4} goals"), f"all {g} goals", "all-N-goals-en"),
        (re.compile(r"Complete database of all \d{3,4} goals"), f"Complete database of all {g} goals", "complete-db"),
        (re.compile(r"\d{3,4} official career goals"), f"{g} official career goals", "official-career"),
        (re.compile(r"Ronaldo \(\d{3,4} goals\)"), f"Ronaldo ({g} goals)", "ronaldo-paren"),
        (re.compile(r"Ronaldo has <strong>\d{3,4} goals</strong>"), f"Ronaldo has <strong>{g} goals</strong>", "has-strong"),
        (re.compile(r"is currently at \d{3,4} goals"), f"is currently at {g} goals", "currently-at"),
        (re.compile(r"at \d{3,4} goals and counting"), f"at {g} goals and counting", "and-counting"),
        (re.compile(r"\d{3,4} goals scored\. \d{1,3} to go"), f"{g} goals scored. {r} to go", "scored-to-go"),
        (re.compile(r"<strong>\d{3,4} official career goals</strong>"), f"<strong>{g} official career goals</strong>", "strong-official"),
        (re.compile(r"Ronaldo needs \d{1,3} more goals"), f"Ronaldo needs {r} more goals", "needs-more"),

        # i18n bundles 4 langues
        (re.compile(r"\U0001F3AC \d{3,4} Goals \xb7 Watch Each One".encode().decode()), f"\U0001F3AC {g} Goals \xb7 Watch Each One", "nav-en"),
        (re.compile(r"\U0001F3AC \d{3,4} Buts \xb7 Voir Chacun"), f"\U0001F3AC {g} Buts \xb7 Voir Chacun", "nav-fr"),
        (re.compile(r"\U0001F3AC \d{3,4} Goles \xb7 Ver Cada Uno"), f"\U0001F3AC {g} Goles \xb7 Ver Cada Uno", "nav-es"),
        (re.compile(r"\U0001F3AC \d{3,4} هدفاً \xb7 شاهد كلّ واحد"), f"\U0001F3AC {g} هدفاً \xb7 شاهد كلّ واحد", "nav-ar"),

        (re.compile(r"7 Eras \xb7 \d{3,4} Goals"), f"7 Eras \xb7 {g} Goals", "journey-en"),
        (re.compile(r"7 \xc9poques \xb7 \d{3,4} Buts"), f"7 \xc9poques \xb7 {g} Buts", "journey-fr"),
        (re.compile(r"7 \xc9pocas \xb7 \d{3,4} Goles"), f"7 \xc9pocas \xb7 {g} Goles", "journey-es"),
        (re.compile(r"7 حقب \xb7 \d{3,4} هدفاً"), f"7 حقب \xb7 {g} هدفاً", "journey-ar"),

        (re.compile(r"\d{3,4} Goals\. Watch every single one\."), f"{g} Goals. Watch every single one.", "cta-en"),
        (re.compile(r"\d{3,4} Buts\. Regardez chacun d'eux\."), f"{g} Buts. Regardez chacun d'eux.", "cta-fr"),
        (re.compile(r"\d{3,4} Buts\. Regardez chacun d\\'eux\."), f"{g} Buts. Regardez chacun d\\'eux.", "cta-fr-esc"),
        (re.compile(r"\d{3,4} Goles\. Mira cada uno\."), f"{g} Goles. Mira cada uno.", "cta-es"),
        (re.compile(r"\d{3,4} هدفاً\. شاهد كلّ واحد منها\."), f"{g} هدفاً. شاهد كلّ واحد منها.", "cta-ar"),

        # Spans HTML visibles
        (re.compile(r'<span class="hero-score-current">\d{3,4}</span>'), f'<span class="hero-score-current">{g}</span>', "hero-score"),
        (re.compile(r'<span id="toast-count">\d{3,4}</span>'), f'<span id="toast-count">{g}</span>', "toast-count"),
        (re.compile(r'<span class="goals-cta-num">\d{3,4}</span>'), f'<span class="goals-cta-num">{g}</span>', "cta-num"),
        # rec-value Most Career Goals UNIQUEMENT
        (re.compile(r'(<div class="rec-title" data-i18n="rec_career_title">Most Career Goals</div>\s*<div class="rec-value">)\d{3,4}\+(</div>)', re.DOTALL),
            lambda m: f'{m.group(1)}{g}+{m.group(2)}', "rec-value-career"),
        # data-target ancres avec lookahead
        (re.compile(r'data-target="\d{3,4}"(?=>0</p>\s*<p class="stat-label" data-i18n="stat_total_label")', re.DOTALL),
            f'data-target="{g}"', "data-target-total"),
        (re.compile(r'data-target="\d{1,3}" id="statRemaining"'),
            f'data-target="{r}" id="statRemaining"', "data-target-remain"),
        # selecteurs JS
        (re.compile(r'\.count-up\[data-target="\d{3,4}"\]'),
            f'.count-up[data-target="{g}"]', "js-selector-total"),
        (re.compile(r'\.count-up\[data-target="\d{1,3}"\](?=[^a-zA-Z]*newRemaining)', re.DOTALL),
            f'.count-up[data-target="{r}"]', "js-selector-remain"),
        (re.compile(r'<a href="\./goals\.html" style="color:rgba\(212,175,55,0\.5\);text-decoration:none;font-size:0\.72rem;letter-spacing:0\.05em">ALL \d{3,4} GOALS</a>'),
            f'<a href="./goals.html" style="color:rgba(212,175,55,0.5);text-decoration:none;font-size:0.72rem;letter-spacing:0.05em">ALL {g} GOALS</a>', "all-goals-link"),
        (re.compile(r'<span class="hero-remain-num" id="remaining">\d{1,3}</span>'),
            f'<span class="hero-remain-num" id="remaining">{r}</span>', "hero-remain"),

        # JS state
        (re.compile(r"let CURRENT_GOALS\s*=\s*\d{3,4}"), f"let CURRENT_GOALS   = {g}", "js-current-goals"),
        (re.compile(r"cr7_goal_num:\s*\d{3,4}"), f"cr7_goal_num: {g}", "js-goal-num"),

        # Date "As of"
        (re.compile(r"As of (January|February|March|April|May|June|July|August|September|October|November|December) 2026"),
            f"As of {me} {year}", "as-of-en"),
    ]


def apply_patterns(text, patterns, verbose=False):
    counts = {}
    for regex, repl, label in patterns:
        new_text, n = regex.subn(repl, text)
        if n > 0:
            counts[label] = n
            if verbose:
                print(f"    {label}: {n} substitution(s)")
        text = new_text
    return text, counts


def process_file(path, patterns, dry_run, verbose):
    if not path.exists():
        return 0
    original = path.read_text(encoding="utf-8")
    updated, counts = apply_patterns(original, patterns, verbose=verbose)
    total = sum(counts.values())
    if total == 0:
        print(f"  {path.relative_to(PROJECT_DIR)}: no change")
        return 0
    if dry_run:
        print(f"  [dry-run] {path.relative_to(PROJECT_DIR)}: {total} substitutions would be applied")
        if not verbose:
            for label, n in counts.items():
                print(f"      {label}: {n}")
    else:
        path.write_text(updated, encoding="utf-8")
        print(f"  OK {path.relative_to(PROJECT_DIR)}: {total} substitution(s) appliquees")
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not STATS_FILE.exists():
        print(f"ERREUR: stats.json introuvable a {STATS_FILE}", file=sys.stderr)
        return 1

    stats = load_stats()
    goals = int(stats.get("goals", 0))
    remaining = int(stats.get("remaining", 1000 - goals))
    last_updated = stats.get("last_updated", datetime.utcnow().isoformat() + "Z")
    month, year = parse_month_year(last_updated)

    print(f"Stats source: goals={goals}, remaining={remaining}, date={MONTHS_EN[month-1]} {year}")
    print()

    patterns = build_patterns(goals, remaining, month, year)

    targets = [PUBLIC_DIR / "index.html"]
    blog_dir = PUBLIC_DIR / "blog"
    if blog_dir.exists():
        targets.extend(sorted(blog_dir.glob("*.html")))

    total = 0
    for target in targets:
        total += process_file(target, patterns, dry_run=args.dry_run, verbose=args.verbose)

    print()
    if args.dry_run:
        print(f"[dry-run] Total: {total} substitution(s) seraient appliquees sur {len(targets)} fichier(s)")
    else:
        print(f"OK Total: {total} substitution(s) appliquees sur {len(targets)} fichier(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
