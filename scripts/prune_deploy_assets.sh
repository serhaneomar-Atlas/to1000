#!/usr/bin/env bash
# Allege le paquet envoye a Cloudflare Pages, sans jamais modifier le depot.
#
# Contexte : Cloudflare Pages plafonne un deploiement a 20 000 fichiers sur le
# plan gratuit. Un deploiement Pages est atomique : des que le seuil est franchi
# wrangler refuse la TOTALITE du paquet. Le site reste alors fige alors que la
# generation, le commit et le push sont verts — la panne est invisible partout
# sauf sur le site lui-meme.
#
# Deux incidents ont suivi exactement ce scenario :
#   - 04/08/2026 : les cartes de partage (public/social/cards, ~250/jour) ont
#     franchi le seuil. Site fige douze jours.
#   - 09/09/2026 : public/news/ a franchi le seuil a lui seul (21 111 pages SEO
#     pour 20 000 autorisees). Les six workflows echouaient a l'etape deploy
#     depuis plusieurs jours ; le fil d'actualite continuait pourtant a se
#     remplir dans le depot.
#
# Ce script s'execute juste avant l'upload, apres le commit. Il ne retire rien
# du depot : les fichiers restent versionnes, seule la copie de travail du
# runner est allegee.
#
# Strategie : un BUDGET, pas une fenetre de temps. On garde toujours les
# articles encore listes dans news.json, puis on complete avec les plus recents
# jusqu'a remplir le budget. La volumetrie peut doubler sans recasser le
# deploiement — c'est ce qui manquait aux deux corrections precedentes.

set -uo pipefail

CARDS_DIR="public/social/cards"
NEWS_JSON="public/news.json"

# Plafond Cloudflare = 20 000. On vise 18 000 pour absorber la croissance entre
# deux deploiements sans jamais froler le mur.
export DEPLOY_MAX_FILES="${DEPLOY_MAX_FILES:-18000}"
# PRUNE_DRY_RUN=1 -> on rapporte sans rien supprimer (debug local).
export PRUNE_DRY_RUN="${PRUNE_DRY_RUN:-0}"

# ---------------------------------------------------------------------------
# 1) Cartes de partage : on ne garde que celles des articles encore en ligne.
# ---------------------------------------------------------------------------
if [ -d "$CARDS_DIR" ]; then
  if [ -f "$NEWS_JSON" ]; then
    python3 - "$NEWS_JSON" "$CARDS_DIR" <<'PY'
import json
import os
import sys

news_json, cards_dir = sys.argv[1], sys.argv[2]
dry = os.environ.get("PRUNE_DRY_RUN") == "1"

keep = set()


def walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("id", "slug", "hash") and isinstance(value, str):
                keep.add(value)
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)


try:
    with open(news_json, encoding="utf-8") as handle:
        walk(json.load(handle))
except Exception as exc:
    print(f"prune: lecture de {news_json} impossible ({exc})")

removed = kept = 0
for name in os.listdir(cards_dir):
    path = os.path.join(cards_dir, name)
    if not os.path.isfile(path):
        continue
    if os.path.splitext(name)[0] in keep:
        kept += 1
    else:
        if not dry:
            os.remove(path)
        removed += 1

print(f"prune: {kept} cartes conservees, {removed} ecartees du deploiement")
PY
  else
    rm -rf "$CARDS_DIR"
    echo "prune: news.json absent, dossier des cartes entierement ecarte"
  fi
fi

# ---------------------------------------------------------------------------
# 2) Pages d'articles : retention par budget (correctif du 09/09/2026).
# ---------------------------------------------------------------------------
NEWS_DIR="public/news"
SITEMAP="public/sitemap.xml"

if [ -d "$NEWS_DIR" ]; then
  python3 - "$NEWS_DIR" "$NEWS_JSON" "$SITEMAP" <<'PY'
import json
import os
import re
import sys

news_dir, news_json, sitemap = sys.argv[1], sys.argv[2], sys.argv[3]
budget_total = int(os.environ.get("DEPLOY_MAX_FILES", "18000"))
dry = os.environ.get("PRUNE_DRY_RUN") == "1"

# Inventaire : tout ce qui n'est pas une page d'article est intouchable
# (index, archive, coupe du monde, images, cartes deja filtrees ci-dessus).
pages = []
fixed = 0
for root, _dirs, files in os.walk("public"):
    for name in files:
        path = os.path.join(root, name)
        same_dir = os.path.normpath(root) == os.path.normpath(news_dir)
        if same_dir and name.endswith(".html") and name != "index.html":
            pages.append(path)
        else:
            fixed += 1

budget = max(budget_total - fixed, 0)

# Les articles encore listes dans news.json sont prioritaires : ce sont les
# seuls lies depuis la page d'accueil, les perdre casserait le fil visible.
live_ids = set()
try:
    with open(news_json, encoding="utf-8") as handle:
        for item in json.load(handle).get("items", []):
            ident = item.get("id")
            if isinstance(ident, str):
                live_ids.add(ident)
except Exception as exc:
    print(f"prune: news.json illisible ({exc}) — retention par date seule")

DATE_RX = re.compile(
    r"article:published_time[^>]{0,24}content=.([0-9]{4}-[0-9]{2}-[0-9]{2}[^\"']*)"
)


def published(path):
    """Date de publication lue dans le <head> (chaine vide si absente)."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            head = handle.read(6000)
    except OSError:
        return ""
    found = DATE_RX.search(head)
    return found.group(1) if found else ""


live_pages, others = [], []
for path in pages:
    if os.path.splitext(os.path.basename(path))[0] in live_ids:
        live_pages.append(path)
    else:
        others.append((published(path), path))

# Les plus recents d'abord ; les pages sans date passent en dernier.
others.sort(reverse=True)
ordered = live_pages + [path for _date, path in others]
keep = set(ordered[:budget])

dropped_names = set()
removed = 0
for path in pages:
    if path in keep:
        continue
    dropped_names.add(os.path.basename(path))
    if not dry:
        os.remove(path)
    removed += 1

# Le sitemap ne doit pas annoncer des pages absentes du deploiement, sinon
# Search Console se remplit de 404. On le filtre dans la copie du runner.
if dropped_names and os.path.isfile(sitemap):
    with open(sitemap, encoding="utf-8", errors="ignore") as handle:
        xml = handle.read()

    def keep_url(match):
        loc = match.group(1)
        if "/news/" in loc and loc.rsplit("/", 1)[-1] in dropped_names:
            return ""
        return match.group(0)

    trimmed = re.sub(
        r"<url>\s*<loc>([^<]+)</loc>.*?</url>\s*", keep_url, xml, flags=re.S
    )
    if not dry:
        with open(sitemap, "w", encoding="utf-8") as handle:
            handle.write(trimmed)
    kept_urls = trimmed.count("<loc>")
    print(f"prune: sitemap ramene a {kept_urls} URL")

projected = fixed + len(keep)
print(f"prune: {len(keep)} pages d'articles conservees, {removed} ecartees")
print(f"prune: {projected} fichiers seront envoyes a Cloudflare Pages (limite 20000)")

if dry:
    print("prune: simulation — rien n'a ete supprime, le total reel sera plus bas")
elif projected >= 20000:
    print("::error::prune: plafond Cloudflare toujours depasse — baisser DEPLOY_MAX_FILES")
    sys.exit(1)
PY
fi
