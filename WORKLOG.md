# WORKLOG — Journal partagé to1000.com

> Append-only. L'entrée la plus récente EN HAUT. Gabarit dans `HANDOFF.md` §6.
> Chaque membre (Claude Code / Cowork / Omar) ajoute une entrée en fin de session.

---

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
