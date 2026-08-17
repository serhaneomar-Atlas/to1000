#!/usr/bin/env bash
# Allege le paquet envoye a Cloudflare Pages, sans jamais modifier le depot.
#
# Contexte : Cloudflare Pages plafonne un deploiement a 20 000 fichiers sur le
# plan gratuit. Les cartes de partage (public/social/cards) s'accumulent d'environ
# 250 par jour. Le 4 aout 2026 le seuil a ete franchi : wrangler a refuse la
# totalite du paquet (un deploiement Pages est atomique) et le site est reste
# fige douze jours alors que la generation et le push fonctionnaient.
#
# Ce script s'execute juste avant l'upload, apres le commit. Il ne retire donc
# rien du depot : les fichiers restent versionnes, seule la copie de travail du
# runner est allegee. On conserve les cartes des articles encore listes dans
# news.json (les seules reellement partageables) et on ecarte les autres.

set -uo pipefail

CARDS_DIR="public/social/cards"
NEWS_JSON="public/news.json"

if [ -d "$CARDS_DIR" ]; then
  if [ -f "$NEWS_JSON" ]; then
    python3 - "$NEWS_JSON" "$CARDS_DIR" <<'PY'
import json
import os
import sys

news_json, cards_dir = sys.argv[1], sys.argv[2]

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
        os.remove(path)
        removed += 1

print(f"prune: {kept} cartes conservees, {removed} ecartees du deploiement")
PY
  else
    rm -rf "$CARDS_DIR"
    echo "prune: news.json absent, dossier des cartes entierement ecarte"
  fi
fi

TOTAL=$(find public -type f | wc -l)
echo "prune: $TOTAL fichiers seront envoyes a Cloudflare Pages (limite 20000)"

if [ "$TOTAL" -ge 19000 ]; then
  echo "prune: ATTENTION, on approche de nouveau du plafond de 20 000 fichiers."
  echo "prune: prevoir une retention sur public/news/ ou le plan payant"
  echo "prune: (100 000 fichiers, exige PAGES_WRANGLER_MAJOR_VERSION=4)."
fi
