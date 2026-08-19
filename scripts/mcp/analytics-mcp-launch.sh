#!/usr/bin/env bash
# Lanceur du serveur MCP Google Analytics (analytics-mcp).
#
# Pourquoi un wrapper plutot que "command": "pipx" directement ?
#   1. GOOGLE_APPLICATION_CREDENTIALS attend un CHEMIN de fichier. Dans un
#      conteneur distant ephemere on ne peut configurer que des VARIABLES
#      d'environnement — jamais deposer un fichier. Ce script materialise donc
#      le JSON du compte de service (GA4_SA_JSON) sur disque au demarrage.
#   2. Le runner disponible varie : uvx est preinstalle sur les conteneurs
#      distants, pipx est plus courant en local. On prend ce qui est la.
#
# Le meme secret GA4_SA_JSON alimente deja scripts/collect_metrics.py via les
# secrets GitHub Actions (voir CONNECT_ANALYTICS.md) : un seul compte de
# service pour le dashboard ET pour le MCP.
set -euo pipefail

log() { printf 'analytics-mcp: %s\n' "$1" >&2; }

# --- 1. Credentials -----------------------------------------------------
# Une variable non definie dans .mcp.json arrive litteralement ("${FOO}") :
# on ne la considere valide que si elle pointe sur un fichier reel.
if [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ] && [ -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]; then
  log "credentials : fichier fourni (${GOOGLE_APPLICATION_CREDENTIALS})"
elif [ -n "${GA4_SA_JSON:-}" ]; then
  cred_dir="${TMPDIR:-/tmp}/ga4-mcp"
  mkdir -p "$cred_dir" && chmod 700 "$cred_dir"
  cred_file="$cred_dir/service-account.json"
  # umask avant l'ecriture : la cle privee ne doit jamais etre lisible par
  # d'autres, meme pendant la fraction de seconde avant le chmod.
  ( umask 077 && printf '%s' "$GA4_SA_JSON" > "$cred_file" )
  if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$cred_file" 2>/dev/null; then
    log "ERREUR : GA4_SA_JSON n'est pas un JSON valide (copie tronquee ?)"
    rm -f "$cred_file"
    exit 1
  fi
  export GOOGLE_APPLICATION_CREDENTIALS="$cred_file"
  log "credentials : materialisees depuis GA4_SA_JSON"
else
  # On demarre quand meme : le serveur repondra une erreur d'auth explicite,
  # bien plus lisible qu'un serveur MCP absent de la liste des outils.
  unset GOOGLE_APPLICATION_CREDENTIALS
  log "AUCUNE credential (ni GOOGLE_APPLICATION_CREDENTIALS ni GA4_SA_JSON)"
  log "-> voir CONNECT_ANALYTICS.md section 3"
fi

# Idem : un GOOGLE_PROJECT_ID non substitue casserait le quota project.
case "${GOOGLE_PROJECT_ID:-}" in
  ''|'${GOOGLE_PROJECT_ID}') unset GOOGLE_PROJECT_ID ;;
esac

# --- 2. Runner ----------------------------------------------------------
if command -v uvx >/dev/null 2>&1; then
  exec uvx --from analytics-mcp analytics-mcp "$@"
elif command -v pipx >/dev/null 2>&1; then
  exec pipx run analytics-mcp "$@"
else
  log "ERREUR : ni uvx ni pipx trouve. Installe l'un des deux :"
  log "  pip install uv     (puis uvx)"
  log "  pip install pipx   (puis pipx)"
  exit 127
fi
