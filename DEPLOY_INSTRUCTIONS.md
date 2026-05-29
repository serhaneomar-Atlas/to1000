# 🚀 Déploiement — Refonte du 28 mai 2026

Tout ce qui a été créé/modifié dans cette session est **prêt mais non déployé**. La sandbox Claude n'a pas l'auth git/wrangler, donc tu dois faire le push toi-même depuis Windows.

---

## 1. Vérifier ce qui a été créé

Depuis PowerShell ou Git Bash :

```powershell
cd C:\Users\serha\Desktop\To1000.com\to1000
git status --short
```

Tu devrais voir (entre autres) :

```
?? .github/workflows/news-sync.yml         ← le manquant historique, ENFIN !
?? .github/workflows/stats-sync.yml        ← nouveau
?? .github/workflows/indexnow-ping.yml     ← nouveau
?? EDITORIAL/                              ← le cerveau du newsroom (18+ fichiers .md)
?? public/world-cup/                       ← hub WC + Portugal + Maroc + Maroc/ar
?? public/wc.json                          ← données WC 2026
?? public/_polls.js                        ← module sondages Firebase
?? public/_comments.js                     ← module commentaires Firebase
?? public/news/                            ← 49 pages SEO HTML (auto-générées)
?? scripts/news_to_html.py                 ← générateur SEO pages news
?? scripts/sitemap_generator.py            ← régénérateur sitemap
?? scripts/wc_countdown_update.py          ← maintien wc.json
?? firestore.rules                         ← règles Firebase polls + comments
?? DEPLOY_INSTRUCTIONS.md                  ← ce fichier
 M public/sitemap.xml                      ← regénéré (67 URLs au lieu de ~10)
 M public/wc.json                          ← timestamp + morocco_next / portugal_next
```

## 2. Tester localement avant push

```powershell
cd C:\Users\serha\Desktop\To1000.com\to1000
# Test pages générées localement (Python intégré)
python -m http.server 8000 --directory public
```

Ouvre `http://localhost:8000/world-cup/` et `http://localhost:8000/world-cup/maroc/` et `/portugal/`.

**À vérifier visuellement :**
- [ ] Countdown anime correctement (4 cases jours/h/min/sec)
- [ ] Live ticker scrolle horizontalement
- [ ] Polls : clic = vote enregistré (Firebase ne marchera qu'après update rules → cf. § 4)
- [ ] Comments : "Connecter avec Google" affiche popup
- [ ] Mobile : ouvre devtools, mode mobile, scroll = pas de débordement horizontal
- [ ] /world-cup/maroc/ar/ : RTL bien rendu, polices arabes lisibles

## 3. Push sur GitHub

```powershell
cd C:\Users\serha\Desktop\To1000.com\to1000

# Add les nouveautés (vérifie d'abord ce qui est listé)
git add .github/workflows/ EDITORIAL/ public/world-cup/ public/news/ public/wc.json public/_polls.js public/_comments.js scripts/news_to_html.py scripts/sitemap_generator.py scripts/wc_countdown_update.py firestore.rules DEPLOY_INSTRUCTIONS.md public/sitemap.xml

git commit -m "feat: WC 2026 hub + Portugal/Maroc pages, SEO HTML news generator, EDITORIAL newsroom, GH Actions cron"
git push
```

**Au moment du push :** GitHub Actions va déclencher `news-sync.yml` pour la première fois. Va sur https://github.com/[ton-repo]/actions et regarde le run. Il doit être vert (~ 3-5 min).

## 4. Activer Firebase polls + comments

Les modules `_polls.js` et `_comments.js` utilisent le projet Firebase existant `to1000-contest`. **Mais** les règles Firestore actuelles n'autorisent que la collection `predictions`. Il faut publier les nouvelles règles.

### 4.a Mettre à jour les règles Firestore

1. Ouvrir [console.firebase.google.com](https://console.firebase.google.com) → projet `to1000-contest`
2. **Firestore Database → Rules**
3. Coller le contenu de `firestore.rules` (à la racine `to1000/`)
4. **Avant publier**, dans la section `comments`, remplacer `'REPLACE_WITH_OMAR_UID'` par ton vrai UID :
   - Authentication → Users → ton email Google → copier "User UID"
5. Cliquer **Publier**

### 4.b (Optionnel) Si tu veux mettre `to1000-contest` Firestore en région autre que `us-central` pour réduire la latence Maroc/France, le faire AVANT que les polls accumulent des votes (sinon il faudra migrer).

### 4.c Tester de bout en bout
1. Va sur `https://to1000.com/world-cup/maroc/`
2. Clique un option de sondage → tu dois voir tes votes refléter en %
3. "Se connecter Google" → poster un commentaire test
4. Va sur la console Firebase → Firestore → tu dois voir :
   - `polls/wc2026-morocco-runs` avec `total: 1` et tes options
   - `comments/world-cup-maroc/items/...` avec ton commentaire

## 5. Configurer les secrets GitHub Actions

Sur GitHub → repo → **Settings → Secrets and variables → Actions** :

| Secret | Valeur | Pourquoi |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Généré par `claude setup-token` sur ton PC | **Active le journaliste IA autonome via ton plan Max** — pas besoin de crédits API en plus. Voir §11. |
| `GEMINI_API_KEY` | (déjà setup ?) | Traduction FR auto des news. Gratuit sur [aistudio.google.com](https://aistudio.google.com/app/apikey). Sans, les news restent en EN. |
| `CLOUDFLARE_API_TOKEN` | À créer dans CF dashboard | Permet le deploy auto-CF Pages. **Sans ça, le deploy se fait via le push git** (si tu as connecté ton repo à Cloudflare Pages via leur Git integration). |
| `CLOUDFLARE_ACCOUNT_ID` | Voir CF dashboard → URL ou Account Home | Idem |

**Si Cloudflare Pages est déjà connecté à ton repo GitHub via leur intégration native, tu n'as PAS besoin des secrets CF — le push git suffit à déclencher le deploy.** Vérifie : Cloudflare dashboard → Pages → projet `to1000` → Settings → Git integration.

## 6. Désactiver les scheduled tasks Windows redondantes

Avec GH Actions actif, ces tâches Windows deviennent inutiles (et risquent de doubler les commits) :

- `cr7-daily-sync` (remplacée par `stats-sync.yml`)
- Tout cron local qui appelait `news_aggregator.py` (remplacé par `news-sync.yml`)

**Mais garde** la tâche `goal-watcher` quand un match commence — elle n'est pas encore couverte par GH Actions.

Dans Cowork, va dans Settings → Scheduled tasks → désactive les redondants.

## 7. Smoke tests après déploiement Cloudflare

Une fois `https://to1000.com/world-cup/` accessible :

```bash
# Sitemap doit lister 67 URLs (au lieu de ~10 avant)
curl -s https://to1000.com/sitemap.xml | grep -c "<loc>"
# Devrait dire : 67

# wc.json doit être présent
curl -s https://to1000.com/wc.json | python -c "import json,sys; d=json.load(sys.stdin); print('days_to_opening:', d.get('days_to_opening'))"

# Une page news doit retourner 200 + avoir JSON-LD
curl -s -o /dev/null -w "%{http_code}\n" https://to1000.com/news/index.html
```

Manuellement dans [PageSpeed Insights](https://pagespeed.web.dev/?url=https%3A%2F%2Fto1000.com%2Fworld-cup%2F) :
- `/world-cup/` doit scorer Performance ≥ 85 mobile, SEO 100
- `/world-cup/maroc/` idem

Dans [Google Search Console](https://search.google.com/search-console) :
- Sitemaps → soumettre `https://to1000.com/sitemap.xml` (re-soumettre — le contenu est nouveau)
- URL Inspection → tester `/world-cup/maroc/` et `/world-cup/portugal/` → cliquer "Request indexing"

## 8. Annonce sur réseaux sociaux (optionnel mais recommandé)

Voir `EDITORIAL/roles/SOCIAL_MEDIA.md` pour les templates. Suggestion immédiate :

**Tweet X @To1000com :**
```
🌍 Le hub Coupe du Monde 2026 est en ligne !

✅ Compte à rebours live (J-14)
✅ Pages 🇵🇹 Portugal & 🇲🇦 Maroc (FR/AR)
✅ Calendrier, groupes, brackets
✅ Sondages, commentaires
✅ News live 24/7

https://to1000.com/world-cup/

#WorldCup2026 #CDM2026 #DimaMaghrib
```

**Post Telegram canal :**
```
🌍 Le hub Coupe du Monde 2026 est disponible sur to1000.com !

→ Hub principal : https://to1000.com/world-cup/
→ 🇲🇦 Page Maroc (FR) : https://to1000.com/world-cup/maroc/
→ 🇲🇦 صفحة المغرب (AR) : https://to1000.com/world-cup/maroc/ar/
→ 🇵🇹 Page Portugal : https://to1000.com/world-cup/portugal/

14 jours avant le coup d'envoi. Allez les Lions ! 🦁
```

## 9. Roadmap restante (pas dans cette session)

Cf. `EDITORIAL/EDITORIAL_CALENDAR.md` pour le détail. Highlights :

- [ ] OG cards customs par page (générer 4 images 1200×630 — voir `EDITORIAL/templates/og-image-prompt.md`)
- [ ] Bracket WC SVG complet à `/world-cup/bracket.html`
- [ ] Live blog Maroc-Brésil (`/world-cup/maroc/live-bra-mar.html`) à créer avant 12 juin
- [ ] Connecter l'auto-posting X (Buffer recommandé — 6€/mois)
- [ ] Configurer `to1000/.env` avec `TELEGRAM_BOT_TOKEN` pour sortir le poster Telegram du dry-run
- [ ] Page **Coupe du Monde — résultats live** (mise à jour quotidienne pendant le tournoi)
- [ ] Bannière "Hub WC" sur la home `index.html` (pour pousser le trafic depuis la page la plus visitée)

## 10. Si quelque chose casse

**Polls cassent (rules error)** → vérifier que `firestore.rules` est bien publié (Console Firebase).

**Comments : "Permission denied"** → idem.

**News pages 404** → vérifier que `news_to_html.py` s'est bien exécuté dans GH Actions. Run manuel : Actions → "News sync" → Run workflow.

**Countdown reste à `–`** → vérifier que `/world-cup/_wc.js` se charge bien (devtools → Network).

**Le ticker live est vide** → `/news.json` n'est pas accessible ou est vide. Vérifier `https://to1000.com/news.json` directement.

---

## 11. Activer le journaliste IA autonome via ton plan Max (PAS d'API à payer)

Ton plan Claude Max inclut **~200$/mois** dédiés à l'Agent SDK / appels automatisés (en plus du quota interactif que tu utilises dans Cowork). Donc le journaliste IA peut tourner H24 en GitHub Actions **sans coût supplémentaire**.

### 11.a Générer un OAuth token avec ton compte Max

```powershell
# Sur ton PC Windows, dans n'importe quel dossier :
claude setup-token
```

Ça ouvre une page de login Anthropic, tu valides avec ton compte Max, et la commande affiche un token (string commençant par `sk-ant-oat...`).

### 11.b Stocker dans les secrets GitHub

GitHub → repo to1000 → **Settings → Secrets and variables → Actions → New repository secret** :
- Name : `CLAUDE_CODE_OAUTH_TOKEN`
- Value : le token de l'étape précédente

### 11.c C'est fini

Le workflow `ai-editorial.yml` tournera 3×/jour (07h / 13h / 19h UTC), pickera la news la plus chaude non encore couverte, et publiera un article original ~700 mots dans `/blog/`. Tu peux aussi le déclencher manuellement : Actions → "AI Editorial" → Run workflow.

### 11.d Coût réel

- Plan Max (~100$/mois) : tu paies déjà, l'IA tourne dans cette enveloppe
- ~6 articles/jour à ~3k tokens out chacun = consommation modeste
- Reste largement dans l'allocation Max Agent SDK

### 11.e Fallback si OAuth Max ne marche pas

Si pour une raison X le secret `CLAUDE_CODE_OAUTH_TOKEN` est rejeté (auth expirée), tu peux toujours :
- Soit re-lancer `claude setup-token` et update le secret
- Soit basculer sur l'API directe : créer une clé API sur [console.anthropic.com](https://console.anthropic.com), la stocker comme `ANTHROPIC_API_KEY`, modifier le workflow pour utiliser `scripts/claude_journalist.py` à la place de la `claude-code-action`. Coût ~5-10€/mois en sus du Max.

---

**Récap visuel de ce qui a changé** : voir `EDITORIAL/README.md` pour comprendre le nouveau système éditorial, ou `EDITORIAL/WORKFLOW.md` pour comprendre comment la boucle quotidienne tourne maintenant.

Bon push, et bonne CDM 2026. **Allez les Lions 🦁 e Força Portugal 🇵🇹**.
