# Brancher Search Console + GA4 (trafic réel)

Deux leviers trafic. Le code est **déjà prêt** — il te reste à poser les tokens/secrets.

---

## 1) Google Search Console (requêtes de recherche + indexation) — ~5 min

C'est **l'outil n°1** pour le SEO : il te montre ce que les gens tapent pour te trouver, tes positions, et indexe tes pages.

1. Va sur **https://search.google.com/search-console** → **Ajouter une propriété** → **Préfixe d'URL** → `https://to1000.com`.
2. Méthode de validation → **Balise HTML** → copie la valeur `content="..."` (un long code).
3. Ouvre `public/index.html`, trouve la ligne :
   ```html
   <meta name="google-site-verification" content="REMPLACER_PAR_TON_TOKEN_GSC">
   ```
   Remplace `REMPLACER_PAR_TON_TOKEN_GSC` par ton code.
4. **Double-clic `scripts/publish.bat`** (déploie).
5. Reviens sur Search Console → **Valider**.
6. Une fois validé → menu **Sitemaps** → ajoute `https://to1000.com/sitemap.xml` (≈1900 pages à indexer).

> Résultat : sous ~48 h, tu vois les **requêtes**, **impressions**, **clics**, **position moyenne** et l'état d'indexation. C'est ça qui guide les améliorations SEO.

---

## 2) GA4 → Dashboard (visites réelles dans `/dashboard.html`) — ~15 min

Le dashboard a déjà le panneau « Trafic » et le connecteur. Il faut juste l'autoriser à **lire** ton GA4.

1. **Property ID** : GA4 → **Admin** → **Paramètres de la propriété** → copie le **numéro** (ex. `123456789`).
2. **Compte de service** (lecture seule) :
   - https://console.cloud.google.com → choisis/crée un projet.
   - Active l'**API « Google Analytics Data »** (APIs & Services → Enable APIs → cherche « Analytics Data »).
   - **IAM & Admin → Comptes de service → Créer** (aucun rôle nécessaire) → **Clés → Ajouter une clé → JSON** → télécharge le fichier.
3. **Donne-lui accès à GA4** : GA4 → Admin → **Gestion des accès à la propriété** → ajoute l'**e-mail du compte de service** (du JSON, finit en `…iam.gserviceaccount.com`) en rôle **Lecteur**.
4. **Secrets GitHub** (repo → Settings → Secrets and variables → Actions → New secret) :
   - `GA4_PROPERTY_ID` = le numéro de l'étape 1.
   - `GA4_SA_JSON` = **tout le contenu** du fichier JSON (copier-coller).
5. C'est tout. Au prochain run de `news-sync` (≤30 min), le dashboard se remplit : **visiteurs, sessions, pages vues, top pages, sources, pays** (30 derniers jours).

> **Alternative zéro-code** : **Looker Studio** (https://lookerstudio.google.com) → « Créer » → connecteur **Google Analytics** → choisis ta propriété → tu as un dashboard GA4 magnifique et auto-MAJ, sans rien coder. Idéal en complément.

---

## 3) MCP Google Analytics (analyser le trafic **directement dans Claude**) — ~5 min

Le §2 remplit le dashboard. Ce §3 permet en plus d'**interroger GA4 en langage naturel**
depuis Claude Code (« quelles pages ont le plus progresse cette semaine ? »).

Le serveur MCP est **deja configure** (`.mcp.json` + `scripts/mcp/analytics-mcp-launch.sh`).
Il reutilise **le meme compte de service** que le §2 — rien de nouveau a creer si tu l'as
deja fait.

### Ce qu'il te reste a faire

1. **Active la 2e API.** Le §2 n'active que « Google Analytics Data ». Le MCP a aussi
   besoin de **« Google Analytics Admin API »** (pour lister tes proprietes) :
   console.cloud.google.com → APIs & Services → Enable APIs → cherche
   « Google Analytics Admin API » → Enable.

2. **Pose la variable d'environnement.** Dans les reglages de ton environnement Claude
   Code (claude.ai/code → environnement → variables d'environnement) :

   | Variable | Valeur |
   |---|---|
   | `GA4_SA_JSON` | **tout le contenu** du fichier JSON du compte de service |
   | `GOOGLE_PROJECT_ID` | l'ID du projet GCP (optionnel — quota project) |
   | `GA4_PROPERTY_ID` | le numero de propriete (pratique, evite de le redonner) |

   > `GOOGLE_APPLICATION_CREDENTIALS` attend un **chemin de fichier**, or on ne peut
   > deposer aucun fichier dans un conteneur distant ephemere. Le lanceur ecrit donc
   > `GA4_SA_JSON` dans un fichier temporaire (mode 600) et pointe la variable dessus.
   > Si tu es en **local**, tu peux au contraire definir directement
   > `GOOGLE_APPLICATION_CREDENTIALS=/chemin/vers/sa.json` : le lanceur le detecte et
   > utilise ton fichier tel quel.

3. **Relance une session Claude Code.** Les serveurs MCP sont lus au demarrage : les
   outils n'apparaissent pas dans une session deja ouverte.

### Verifier que ca marche

Demande a Claude : « liste mes proprietes Google Analytics ». S'il repond avec
to1000.com, c'est branche.

| Message d'erreur | Cause |
|---|---|
| `Your default credentials were not found` | `GA4_SA_JSON` pas posee |
| `GA4_SA_JSON n'est pas un JSON valide` | copie tronquee — recolle tout le fichier |
| `403 ... PERMISSION_DENIED` | compte de service pas ajoute en **Lecteur** sur GA4 (§2 etape 3) |
| `403 ... API has not been used` | une des 2 API n'est pas activee |
| `401 Request had invalid authentication` | cle revoquee ou compte supprime |

### Outils disponibles

`get_account_summaries`, `get_property_details`, `run_report`, `run_realtime_report`,
`run_funnel_report`, `run_conversions_report`, `get_custom_dimensions_and_metrics`,
`list_property_annotations`, `list_google_ads_links`.

---

## Rappel
- Tout changement de fichier (token GSC, etc.) → **`scripts/publish.bat`** pour le mettre en ligne.
- Les secrets GitHub (GA4) ne nécessitent **pas** de déploiement — ils agissent au prochain workflow.
- `GEMINI_API_KEY` (résumés IA des news) se vérifie/pose au même endroit (Secrets Actions).
