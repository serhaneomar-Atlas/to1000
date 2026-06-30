# WORKLOG — Journal partagé to1000.com

> Append-only. L'entrée la plus récente EN HAUT. Gabarit dans `HANDOFF.md` §6.
> Chaque membre (Claude Code / Cowork / Omar) ajoute une entrée en fin de session.

---

### [2026-06-30] — Claude Code (WSL) — **Pipeline news fiabilisé + flash info + dedup + palier payant**
- Fait (gros débogage + kaizen, autonome push/deploy via PAT + gh) :
  1. **Bug `git add` (cause racine « plus d'articles publiés »)** : `notify_sent.json` (absent sauf si alerte) dans le `git add` de news-sync → git atomique → « No staged changes » → 0 commit/deploy depuis 05:51. Fix : stage par-fichier + `push HEAD:main` (detached HEAD des runs push). Le site republie + commite à nouveau.
  2. **Timeout 20 min** : code (cascade d'appels Gemini/article), pas le quota. Fix : coupe-circuit éditorial. Archi **découplée** : news-sync publie vite (cache-only), **news-editorial** (nouveau workflow, */30) enrichit via Gemini, préservation par id. + `enrich_news.py`.
  3. **Prompt « flash info »** (rédacteur en chef + prompt engineer + traducteur polyglotte, few-shot) : brèves TV/radio 15-28 mots, plus de recopie du source. Cache bumpé edtv2:.
  4. **Fusion des doublons d'événement** (2e passe clustering par noms propres, invariants langue) → 1 article multi-sources.
  5. **Palier PAYANT confirmé** (screenshot AI Studio : « Payant 1 », ~12$/mois) → le « quota » n'a JAMAIS été le souci. Bridage retiré : pacing 5s→0.4s, batch 12→50 → 50 articles enrichis/run, 0 échec/429.
  6. GA4 déjà installé live (G-4V8Y6C38VN). Dashboard live : https://to1000.com/dashboard.html
- État : tout déployé + vérifié live. ~31/50 articles en flash-info, converge à chaque run.
- Bloqueurs / à la main d'Omar : GA4→dashboard custom (service account, optionnel) ; accès social (FB/IG/Twitter) pour auto-post ; SEO avancé (livrables agent SEO prêts : OG/Twitter cards, JSON-LD, hreflang) à intégrer.
- Autonomie CC : peut désormais commit+push+deploy+lire les logs Actions seul (PAT Contents+Workflows+Actions, gh authentifié). Manque Actions:Write pour déclencher/annuler des runs.
- Bâton → Omar (décisions GA/social/SEO) ; CC dispo pour exécuter.
- Commit : poussé (série de fix sur main).

### [2026-06-29 ~04:10] — Claude Code (WSL) — **Push autonome configuré + workflow news vivant**
- Fait : (1) **Autonomie push** : Omar a créé un PAT fine-grained (repo to1000, Contents+Workflows write) et configuré le remote ; `git push` testé OK depuis WSL → **CC peut désormais commit+push seul** (fini le `publish.bat` systématique). (2) **Workflow news VIVANT** : commit bot `refresh feed 2026-06-29 03:55` → le pipeline tourne (horaire). Recherchiste éditorial actif (news propres, junk filtré). (3) **Comité éditorial** : code en prod, mais **rédacteur en chef PAS actif** (engines = mymemory/aucun, **0 gemini-editor**) → **la clé GEMINI_API_KEY GitHub est encore invalide** (à re-vérifier/recréer côté Omar).
- État : synchro origin (0/0). Cette entrée poussée par CC en autonome (preuve).
- Bloqueurs : **clé Gemini valide** = dernier verrou du rédacteur en chef + traduction complète. Déploiement live = à confirmer (Cloudflare connecté au repo ? sinon les news bot restent sur GitHub sans atterrir en prod).
- Prochain pas : Omar vérifie/recrée la clé Gemini ; CC vérifie ensuite l'apparition de `gemini-editor`.
- Bâton → **Omar** (clé Gemini) → CC (vérif)
- Commit : poussé par CC.

### [2026-06-29 ~02:30] — Claude Code (WSL) — **Commit des 2 fix de CD (next_match + /news/)**
- Fait : (1) 🔴 **next_match** : commit `public/stats.json` v31 (next = Portugal–Croatie 02/07 23:00 BMO Field) + `scripts/update_stats_v2.py` (garde-fous anti-régression de CD). Syntaxe validée (238 l. ; tronquage 204 l. = mount-lag). Commit `8a8ca27`. (2) 🟠 **/news/ sans photos** : tranché **redirection `/news/` → `/news`** (éviter 2e liste = contenu dupliqué). `public/_redirects` (301 edge) + `news_to_html.py` génère un stub de redirection (meta-refresh+canonical+noindex) ; `public/news/index.html` remplacé par le stub. Articles `/news/{id}` intacts. Commit `c2e23f8`.
- État : **2 commits en local, NON poussés** (WSL ne push pas). Lock `.git/index.lock` périmé retiré.
- Bloqueurs : push/deploy = **Omar** (`publish.bat`).
- Prochain pas : Omar `publish.bat` → vérifier `to1000.com/stats.json` = Portugal–Croatie + `/news/` redirige. Reste : QA mobile/goals/dashboard (CD) ; clé Gemini valide + secrets Cloudflare (Omar).
- Bâton → **Omar** (publish.bat) → CC/CD (vérif)
- Commit : `8a8ca27`, `c2e23f8` (non push)

### [2026-06-29 ~01:40] — Cowork (CD) — **Fix régression next_match + bug photos /news/**
- Fait : (1) **BUG `next_match` (signalé par Omar)** — le live affichait « Saison SPL terminée — off_season » alors que CR7 est en Coupe du Monde. Cause : le run GH Actions `stats-sync` de 22:05 a eu un **fetch ESPN Portugal échoué (transitoire)** → `_portugal_matches()` a renvoyé `[]` → fallback Al Nassr intersaison → écriture du sentinel `off_season` (v30) déployé, **écrasant les bonnes données Mondial** (last = Colombie–Portugal 27/06, next = **Portugal–Croatie 02/07 23:00 BMO Field**). ESPN re-testé depuis le sandbox : fonctionne, trouve bien les 2 matchs.
  (2) **Fix code anti-régression** dans `scripts/update_stats_v2.py` : `refresh_next_match` ne réécrit plus `off_season` si le `next_match` courant a un `kickoff_utc` **dans le futur** (= fetch raté, pas vraie intersaison) ; `refresh_last_match` ne **recule plus dans le temps** (compare `date_iso`, nouvellement stocké dans le bloc). → empêche que ce bug se reproduise au prochain fetch raté.
  (3) **`public/stats.json` corrigé en local** : next_match = Portugal–Croatie 02/07, last_match = Colombie–Portugal 27/06, **version 31** (supersède la v30 régressée en prod). Compteur `goals` **non touché** (975).
  (4) **Bug design /news (signalé par Omar)** : `/news` (sans slash) = bon design ESTÁDIO **avec photos** (48 thumbs, `news.html`/`prerender_news.py`) ✅ MAIS `/news/` (avec slash) = **ancienne liste SANS photos** (47 cartes nues, `news/index.html`/`news_to_html.py`). Deux pages liste concurrentes en prod. La nav home pointe vers `/news.html` (bon), mais `/news/` reste accessible et moche. → **à trancher/corriger par CC** (voir HANDOFF §5).
  (5) Pipeline news horaire (tâche planifiée Cowork) lancée : 47 items / 43 photos / 4 CR7, news.json local à jour. **Non déployé** (sandbox sans wrangler). NB : GH Actions every-30min reste la vraie source prod → cette tâche horaire fait doublon, à retirer (proposé à Omar).
- État : `update_stats_v2.py` (guards) + `stats.json` (v31) corrigés **en local, NON déployés/commités**. Live prod toujours sur la régression off_season jusqu'au deploy.
- Bloqueurs : déploiement + commit/push = **Omar ou CC** (Cowork ne push/déploie pas). Mount-lag Cowork toujours actif (bash voyait `update_stats_v2.py` tronqué à 204 l. / WORKLOG à 61 l. ; édité via les outils fichier canoniques, OK pour commit).
- Prochain pas : **CC** commit+push le fix `update_stats_v2.py` + `stats.json` v31 (déclenche redeploy GH Actions) OU **Omar** `publish.bat`. Puis **CC** règle le `/news/` sans photos.
- Bâton → **Omar / Claude Code** (deploy + commit) puis **Claude Code** (design /news/)
- Commit : non push
- Fait : QA visuelle du design ESTÁDIO en prod via Chrome (réponse à la demande CC du 26/06). Pages vues : **home** (hero, prochain match, parcours, stats, news). Vérifié OK : **compteur 975/1000 cohérent partout** (hero, badge nav « LIVE · 975 », carte stats, barre de progression 97,5 %, « 25 buts avant l'histoire »), dernier but « vs Uzbekistan · FIFA World Cup », **prochain match Colombia–Portugal 27 juin 19:30**, news fraîche (il y a 5–15 h) **mix CR7 + foot général** (Como/Real Madrid, Nicolas Pépé/Côte d'Ivoire), badges « Vérifié », i18n FR/EN/ES/AR, **footer disclaimer « fan site non officiel » présent**, **zéro erreur console**.
- Corrigé en local : section **« Parcours » sommait à 941 ≠ 975** → **Al Nassr 99→129** et **Portugal 141→145** dans `public/index.html` (chiffres vérifiés via web : 5+145+450+101+129+145 = 975). Les valeurs étaient hardcodées/découplées de stats.json.
- À corriger (→ CC) : (a) **contraste faible** sur sections sombres — bloc « Prochain rendez-vous » (gris sur noir, limite lisible) + petits intitulés eyebrow ; a11y. (b) JSON-LD `index.html` (~l.168) dit encore « Al Nassr with 80+ goals » (sous-estimé). (c) « Ratio buts/match 0,74 » semble hardcodé (stats.json = goals_per_90 1.03, métrique différente).
- Aussi : ce matin (session Cowork) j'avais aligné `public/stats.json` à goals 975 / remaining 25 / cr7_goal_num 975 / version 28, **déployé et vérifié live** (le live était resté à v25 du 7 juin un moment, puis a propagé à 975/v28). NB : divergence de `version` entre copies (CC notait v30/31 le 23/06) → à surveiller, voir [[to1000_cowork_mount_lag]].
- État : `index.html` (fix parcours) corrigé **en local, NON déployé**. Reste du live sain.
- Bloqueurs : déploiement = Omar (`publish.bat`). Minute du 2e but du doublé toujours inconnue. QA mobile (≤390px), `/news`, `/goals`, `/news/{id}`, `/dashboard.html` **pas encore faite** (je peux enchaîner).
- Prochain pas : Omar déploie le fix parcours ; CC corrige contraste/a11y + JSON-LD ; CD finit la QA (mobile + pages restantes).
- Bâton → **Omar** (deploy) + **Claude Code** (contraste/a11y) ; CD dispo pour finir la QA.
- Commit : non push

### [2026-06-26] — Claude Code (WSL) — **REFONTE ESTÁDIO SHIPPÉE EN PROD**
- Fait : grosse session. (1) **Refonte design** : 5 maquettes proposées → Omar choisit **ESTÁDIO** (broadcast cinéma, sombre, Anton/Oswald/Hanken). Portée en prod sur `public/index.html` (remplace l'azulejo). Hero = **Ronaldo Siuu détouré** (U²-Net/onnxruntime) incrusté sur stade + **GRAND compteur 975/1000** + ligne créative **« THE G.O.A.T.? »**. (2) **Pages** : `news.html` dédiée (cartes « l'essentiel sourcé », filtres, i18n FR/EN/ES/AR + RTL) ; `goals.html` re-skin ESTÁDIO ; **toutes les pages article** `news/*.html` (1941) re-skinnées ESTÁDIO (template `news_to_html.py` + bulk). (3) **Pipeline news** : filtre **football-only** (match en limites de mots + blocklist autres sports — réglait surf/tennis qui passaient) ; **résumés IA** `editorialize_pair` (1 appel Gemini → titre+résumé essentiel 4 langues, sans clickbait, fallback gracieux) ; **prérendu SEO** des cartes ; la carte news ouvre **NOTRE page article** (source = lien discret) + « À lire aussi » d'articles internes. (4) **UX** : menu **mobile (hamburger)**, lien **« Tous les buts »** restauré dans la nav, **drapeaux** uniformes du prochain match (flagcdn), « Portugal » retiré du hero. (5) **Dashboard marketing** `public/dashboard.html` (noindex, Chart.js, auto-MAJ via `scripts/collect_metrics.py` + `metrics_history.json`, branché à news-sync) — trafic GA4 prêt mais à connecter. (6) **SEO** : canonical en URLs propres (/news, /goals, /news/{id}), prérendu crawlable. (7) **Boucle de critique** (agents) : 3+1 passes → P0 polices (lien Google Fonts chargeait Piazzolla au lieu d'Anton → toute la typo cassée, corrigé), archives non re-skinnées (1890 pages), a11y, sécurité.
- État : **EN LIGNE et vérifié via curl** (Anton, compteur, GOAT, menu mobile, drapeaux, news propre, 975, dashboard 200). Régression réglée : les workflows redéployaient l'ANCIEN depuis GitHub (repo non synchro car je ne peux pas push) → créé **`scripts/publish.bat`** (force-push + deploy en 1 double-clic) ; Omar l'a lancé, repo + site synchros.
- Bloqueurs : (a) **QA VISUELLE** — je n'ai pas de navigateur (WSL), tout est vérifié au `curl` mais pas à l'œil. (b) clé **`GEMINI_API_KEY`** GitHub à valider (sandbox = invalide → résumés IA en fallback). (c) **GA4** à connecter pour le trafic réel du dashboard. (d) déploiement = action Omar (`publish.bat`).
- **DEMANDE À CD (Cowork)** : Omar **autorise Chrome / computer-use**. Merci de faire la **QA visuelle** sur https://to1000.com : (1) hero (Siuu+compteur+GOAT, polices Anton bien chargées), (2) **mobile** (≤390px : hamburger ouvre la nav, compteur lisible), (3) `/news` (cartes, filtres, clic → notre page article), (4) `/goals` (tableau ESTÁDIO, modal vidéo), (5) une page `/news/{id}` (thème ESTÁDIO, source discrète, « À lire aussi »), (6) `/dashboard.html`. Note tout glitch visuel (contraste, débordement, Anton trop massif) ici dans le WORKLOG → Claude Code corrige.
- Prochain pas : QA visuelle (CD) → correctifs (CC) ; connecter GA4 + Search Console ; valider clé Gemini.
- Bâton → **CD** (QA visuelle, Chrome autorisé) + **Omar** (clé Gemini, GA4) → Claude Code (correctifs)
- Commit : ~24 commits ESTÁDIO (voir git log, HEAD `1a6175f`), poussés via publish.bat.

### [2026-06-23 ~18:20] — Claude Code _(horloge WSL 14:16 ; décalée vs Cowork — entrée la plus récente)_
- Fait : **PHASE 1 — AUDIT terminé.** (1) Lecture intégrale `index.html` (4316 l.) + mesures objectives + `_headers`. (2) `DESIGN_AUDIT.md` produit (inventaire page/page, dette, perf, a11y, responsive, SEO, sécurité, benchmark, outillage, 2 directions, reco). (3) **2 maquettes hero** dans `design/mockups/` : **A = évolution or/noir**, **B = rupture scoreboard** — registre broadcast premium, hero hybride (réponses d'Omar via questionnaire). (4) 2 agents lancés (recherche skills + benchmark) ; outillage intégré : reco **GSAP / Vercel web-design-guidelines / theme-factory / claude-seo** + **alerte sécurité Snyk ToxicSkills** (36 % des skills communautaires = injection de prompt → first-party priorité).
- État : Audit + maquettes livrés. **Site prod NON touché** (tout dans `design/` + 3 .md racine). Maquettes ouvrables au double-clic. Compteur resynchronisé sur le live **975/25** (pris en compte le doublé d'aujourd'hui). Screenshots auto impossibles (sandbox WSL sans libs navigateur).
- Bloqueurs : **en attente arbitrage Omar** (rien ne bloque la suite côté technique).
- Prochain pas : Omar tranche direction (A / B / hybride) + Next.js + particules + install skills → Phase 2 (`DESIGN_SYSTEM.md`, tokens).
- Bâton → **Omar** (validation direction) puis Claude Code (Phase 2)
- Commit : voir git log (fin de session)

### [2026-06-23 18:25] — Cowork
- Fait : Match terminé **Portugal 5–0 Ouzbékistan** (CR7 doublé, count confirmé 975 = 973+2). `stats.json` : last_match = 5–0 (W, cr7_scored, goal #975), next_match = **Colombie–Portugal 27 juin** (Miami), version 31. Dashboard mis à jour (carte « Dernier match » 5–0 + prochain match, timeline, snapshot + fetch live sur last_match/next_match).
- État : à jour en local, NON déployé.
- Bloqueurs : déploiement = Omar ; minute du 2e but toujours inconnue.
- Prochain pas : Omar déploie ; Claude Code → audit design.
- Bâton → Claude Code (audit) + Omar (déploiement)
- Commit : non push

### [2026-06-23 18:11] — Cowork
- Fait : (1) **Correction but → 975** : le news.json (régén. 18:05) + Le Monde/L'Équipe/Le Figaro confirment un **doublé** de CR7 vs Ouzbékistan (record : 1er joueur à marquer dans 6 CdM). `stats.json` passé à goals 975 / remaining 25 / version 30. (2) Ajouté `Access-Control-Allow-Origin: *` sur stats.json / news.json / goals-data.json dans `public/_headers` (pour dashboard live). (3) Créé `PROJECT_DASHBOARD.html` (dashboard interne dyslexie-friendly, hors `public/` donc non déployé).
- État : Tout à jour en local. NON déployé. Le dashboard tourne en mode « instantané » tant que le CORS n'est pas en prod ; il passera « en direct » après déploiement.
- Bloqueurs : déploiement = Omar. Minute du 2e but inconnue (à confirmer).
- Prochain pas : Omar déploie (#975 + CORS) ; Claude Code démarre l'audit design.
- Bâton → Claude Code (audit) + Omar (déploiement + confirmation 2e but)
- Commit : non push

### [2026-06-23 17:45] — Cowork
- Fait : (1) Crédité le **but live #974** de CR7 dans `public/stats.json` (vs Uzbekistan, 6', pied droit, passe de João Cancelo, FIFA World Cup) → goals 974 / remaining 26 / version 29. (2) Lancé le pipeline news (`news_aggregator.py`, DISABLE_MYMEMORY=1) → `news.json` rafraîchi : 50 items, 47 avec image, 12 CR7. (3) Créé `HANDOFF.md`, `DESIGN_BRIEF.md`, ce `WORKLOG.md`.
- État : Fichiers à jour **en local**. NON déployés (sandbox sans auth Cloudflare). Compteur du site s'animera dès que prod servira le nouveau `stats.json`.
- Bloqueurs : Déploiement = action Omar (`deploy_now.bat`).
- Prochain pas : Omar déploie le but live ; Claude Code démarre la PHASE 1 (AUDIT) de `DESIGN_BRIEF.md`.
- Bâton → Claude Code (pour l'audit design) + Omar (pour le déploiement immédiat du but)
- Commit : non push (à committer par Claude Code ou Omar)
```
```
```
