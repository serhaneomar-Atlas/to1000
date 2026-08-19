# MCP Google Analytics — suivi de l'activité de to1000.com

Le serveur MCP officiel [`googleanalytics/google-analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp)
est déclaré dans `.mcp.json` (portée projet). Claude le propose au démarrage
d'une session dans ce dépôt ; il suffit d'approuver une fois.

Il donne accès aux données GA4 de to1000.com directement en conversation :
visiteurs, sessions, pages vues, sources de trafic, pays, temps réel, entonnoirs.

## Ce qui est déjà fait

`.mcp.json` :

```json
{
  "mcpServers": {
    "analytics-mcp": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "${GOOGLE_APPLICATION_CREDENTIALS}",
        "GOOGLE_PROJECT_ID": "${GOOGLE_PROJECT_ID}"
      }
    }
  }
}
```

Les identifiants ne sont **pas** dans le dépôt : les deux valeurs sont lues
depuis les variables d'environnement de ta machine.

## Ce qu'il reste à poser (une seule fois, ~10 min)

### 1. Activer les APIs

Sur https://console.cloud.google.com (même projet que le compte de service GA4
créé dans `CONNECT_ANALYTICS.md`, ou un nouveau) → **APIs & Services → Enable APIs** :

- **Google Analytics Admin API**
- **Google Analytics Data API**

### 2. Créer les identifiants (ADC)

Installe `gcloud` (https://cloud.google.com/sdk/docs/install), puis :

```bash
gcloud auth application-default login \
  --scopes https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
```

Le fichier produit se trouve à :

- macOS / Linux : `~/.config/gcloud/application_default_credentials.json`
- Windows : `%APPDATA%\gcloud\application_default_credentials.json`

> Alternative : réutiliser le JSON du compte de service déjà créé pour le
> dashboard GA4 (voir `CONNECT_ANALYTICS.md`, étape 2) et pointer
> `GOOGLE_APPLICATION_CREDENTIALS` dessus. Ce compte doit avoir le rôle
> **Lecteur** sur la propriété GA4.

### 3. Exporter les deux variables

Dans ton `~/.zshrc` / `~/.bashrc` (macOS/Linux) :

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
export GOOGLE_PROJECT_ID="ton-project-id"
```

Sur Windows (PowerShell) :

```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "$env:APPDATA\gcloud\application_default_credentials.json"
setx GOOGLE_PROJECT_ID "ton-project-id"
```

Ouvre un nouveau terminal pour que les variables soient prises en compte.

### 4. Prérequis `pipx`

```bash
python3 -m pip install --user pipx && python3 -m pipx ensurepath
```

Si tu utilises `uv` plutôt que `pipx`, remplace dans `.mcp.json` :
`"command": "uvx"` et `"args": ["analytics-mcp"]` — testé, ça fonctionne aussi.

## Vérifier

Relance Claude Code dans ce dossier, approuve le serveur, puis :

```
/mcp
```

`analytics-mcp` doit apparaître comme **connected**. Ensuite, en langage naturel :

- « Quelles sont mes pages les plus vues sur to1000.com ces 30 derniers jours ? »
- « D'où vient mon trafic cette semaine ? »
- « Combien de visiteurs en temps réel ? »

## Outils exposés

| Outil | Usage |
|---|---|
| `get_account_summaries` | Lister les comptes et propriétés GA4 accessibles |
| `get_property_details` | Détails d'une propriété (fuseau, devise, date de création) |
| `run_report` | Rapport GA4 personnalisé (dimensions + métriques + plage de dates) |
| `run_realtime_report` | Activité des 30 dernières minutes |
| `get_custom_dimensions_and_metrics` | Dimensions/métriques personnalisées de la propriété |
| `run_funnel_report` | Entonnoirs de conversion |
| `list_google_ads_links` | Liens Google Ads associés |

## Rappel

Ce MCP **lit** GA4, il ne le configure pas. Si GA4 n'est pas encore branché sur
to1000.com, commence par `CONNECT_ANALYTICS.md`.
