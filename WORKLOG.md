# WORKLOG — Journal partagé to1000.com

> Append-only. L'entrée la plus récente EN HAUT. Gabarit dans `HANDOFF.md` §6.
> Chaque membre (Claude Code / Cowork / Omar) ajoute une entrée en fin de session.

---

### [2026-07-06 ~15:30 UTC] — Claude Code (WSL) — **Travail de CD récupéré et shippé + avant-match Portugal–Espagne + vérifs pour Make**
- **Le rapport de session de CD est INTROUVABLE** (ni commit, ni WORKLOG local/origin — probablement resté dans son espace Cowork). J'ai retrouvé son travail par diff : **filtre `NON_FOOTBALL_BLOB`** dans news_aggregator local (drop des items nommant un événement non-football en plein texte — un item Tour de France était passé en prod). **Validé sur 8 cas et shippé** (`2e6a0853`). ⚠️ **CD : ton `espn_client.py` local est une base PÉRIMÉE (CRLF) qui annulerait le fix penalty du 976 — ne pas l'utiliser, repartir d'origin.** Merci de re-pousser ton entrée de session.
- **Vérifs demandées (pour Make) — TOUT VERT** : les 4 flux servent `max-age=0, must-revalidate` (cf DYNAMIC, plus de s-maxage 7 j), **rss-en = vrai anglais (16 items)**, rss-ar = 19 items. → **CD : plus aucun bloqueur pour finaliser le scénario AR (Pchaaakh TV, `5554400`) ni pour monter l'EN** ; **Omar : feu vert Make Core** si les 2 slots gratuits ne suffisent plus.
- **Avant-match Portugal–Espagne** (choc du jour, AT&T Stadium 19:00 GMT) publié en 4 langues → auto-post en cours. **Vigies armées** : compos officielles (~1 h avant) et rapport de fin de match, publiés automatiquement.
- Bâton → **CD** (finaliser Make AR, monter EN, page « To1000 English ») ; **Omar** (Make Core si besoin, ESP, GSC token).
- Commit : `2e6a0853` via API.

### [2026-07-03 ~05:15 UTC] — Claude Code (WSL) — **NUIT DU 976 : but crédité live, bug penalty tué, 5 publications rédaction (4 langues)**
- ⚽ **BUT #976 (penalty 68e vs Croatie)** crédité en direct. 🔴 **Bug critique découvert et corrigé dans la foulée : ESPN type les penaltys `Penalty - Scored` (sans « Goal ») → AUCUN penalty n'était détectable par le compteur.** Fix + 3 tests poussés (`7a8c632f`). La chaîne auto a ensuite fait son premier tour complet seule : `last_match` Portugal 2-1 Croatie, `cr7_scored: true`, deploy — zéro intervention.
- 📰 **Système d'items éditoriaux maison** (`scripts/custom_news.json` + `load_custom_items()`) : la rédaction publie dans le feed (expiration auto, survit aux régénérations) → pages articles + cartes + 4 flux + auto-post Make FB/IG. **5 publications cette nuit, toutes 4 langues** : duel Ronaldo–Modric, avant-match Algérie (AR fort), **événement 976 avec carte-photo célébration** (`make_photo_card()`, photo fournie par Omar, verrou `lock` dans le manifest — réutilisable pour le 1000e), rapport FT Portugal 2-1 Croatie (Ramos 90e+4), rapport FT Suisse 2-0 Algérie (« merci les Verts », AR digne).
- 🛠 **Leçon d'infra** : pendant les matchs, les bots poussent toutes les ~5 min et le FS /mnt/c rend git local impraticable (timeouts, locks, courses perdues). **Solution adoptée : commits via l'API Git de GitHub** (blobs→tree→commit→ref avec retry) — fiable, atomique, insensible aux courses. À privilégier pour tout hotfix en fenêtre de match.
- Repo local WSL : en retard/divergent (à resynchroniser à froid, rien d'urgent — main fait foi).
- Bâton → **CD** (inchangé : purge cache 3 flux + scénario Make Pchaaakh TV — le contenu AR est prêt et riche) ; **Omar** (matin : vérifier les posts FB/IG de la nuit, ESP, GSC).
- Commits : `a0a25aa6`, `2e5e5dd7`, `13c2f458`, `7a8c632f` + stats v34-35, via API.

### [2026-07-02 ~13:55 UTC] — Claude Code (WSL) — **FIX cache CDN des flux langue + filtre EN/ES (signalement CD traité)**
- **Headers corrigés et vérifiés live** : `rss-ar/en/es.xml` servent désormais `public, max-age=0, must-revalidate` comme rss.xml (règles `_headers` avec `!` détacheur ; l'ancien `s-maxage=604800` a disparu, cf=DYNAMIC). Les nouveaux articles apparaîtront en ~15 min dans les flux.
- **Filtre langue généralisé** (`lang_ok`) : rss-en/es n'incluent un item que si sa traduction existe ET diffère du texte source (fini l'espagnol dans rss-en) ; AR garde la détection d'écriture. Flux actuels : ~3 items chacun, grossissent à chaque passe Gemini (*/30). 12 tests rss verts.
- 🏳️ **CD — 2 étapes pour débloquer Make** :
  1. **Purge Cloudflare** (dashboard → Caching → Configuration → Purge Cache → *Custom purge*) des 3 URLs : `https://to1000.com/rss-ar.xml`, `rss-en.xml`, `rss-es.xml` — de vieux 404 (TTL 7 j) peuvent persister sur certains PoP dont celui de Make.
  2. Puis monter le scénario **RSS-ar → Page Pchaaakh TV**. **Plan B sans purge** : utiliser `https://to1000.pages.dev/rss-ar.xml` dans Make (même contenu, aucun cache de zone — vérifié 200).
- Bâton → **CD** (purge + scénario Make).
- Commit : `35657df` (+ cette entrée), poussés + déployés.

### [2026-07-02] — Cowork (CD) — **🔴 BLOQUEUR : cache CDN des flux langue (Make 404 + staleness 7j)**
- **Scénario Make AR construit** (`5554400` : RSS-ar → Facebook Pchaaakh TV, Page sélectionnée) mais **PAS finalisable** : au « Run once », Make renvoie **404 Not Found** sur `rss-ar.xml`, alors que `curl` (tout UA) obtient **200** avec XML valide.
- **Cause diagnostiquée (en-têtes)** : `rss.xml` (FR, marche dans Make) = `cache-control: max-age=0, must-revalidate` + `cf-cache-status: DYNAMIC`. MAIS **`rss-ar.xml` / `rss-en.xml` = `cache-control: public, s-maxage=604800`** (cache CDN **7 jours**) + `age: ~1992`. → (a) un **ancien 404 est resté en cache sur certains edges** (d'avant le déploiement) et y persiste à cause du long TTL → Make tape un edge 404, curl un edge 200 ; (b) même purgé, **un cache 7 j sur un flux d'ACTU = les nouveaux items n'apparaissent pas** → auto-post mort.
- 🔴 **TÂCHE CC** : (1) donner aux flux `rss-*.xml` (ar/en/es) les **mêmes en-têtes cache que `rss.xml`** (`max-age=0, must-revalidate`, court) dans `_headers` — actuellement ils tombent sous une règle générique s-maxage=604800 ; (2) **purger le cache Cloudflare** pour `rss-ar.xml`, `rss-en.xml`, `rss-es.xml` (dashboard Purge, ou wrangler) pour vider les 404 périmés. Puis me re-pinguer.
- ⏸️ **Make Core (paiement Omar) : à RETENIR** tant que les flux ne sont pas fetchables + frais (l'AR est bloqué par le cache, l'EN par l'espagnol + le cache). Dès que CC a corrigé, je finalise le scénario AR (mapping caption + filtre + activation), puis EN après le fix espagnol.
- 🏳️ Bâton → **CC** (cache headers + purge des flux langue ; fix rss-en espagnol) → **CD** (finaliser scénarios AR/EN).

### [2026-07-02] — Cowork (CD) — **Scénario AR Pchaaakh TV en cours + 🔴 BUG rss-en.xml (espagnol)**
- ✅ **rss-ar.xml vérifié bon** (4 items, vrai arabe) → je monte le 2e scénario Make **RSS-ar → Facebook Pchaaakh TV** (FB seul, « From now on », filtre image présente). Tient dans le gratuit (2e/2 slots).
- 🔴 **BUG `rss-en.xml` (→ CC)** : le flux « anglais » sert en réalité de l'**ESPAGNOL** — 6 premiers titres tous en espagnol (ex. « Croacia avisa: Cristiano Ronaldo no está acabado », « Mundial 2026, EN VIVO… »). Le filtre langue que tu as mis pour l'AR n'a pas été appliqué (ou est cassé) pour l'EN : les items sans `i18n.en` retombent sur le texte source ES en passthrough. **Fix : même filtre langue que rss-ar pour rss-en (ne garder que les items réellement anglais, ou forcer la traduction).** Tant que ce n'est pas corrigé, **on NE monte PAS le scénario anglais** (sinon on poste de l'espagnol sur la page "To1000 English").
- **Décisions Omar (notées)** : EN → nouvelle page **« To1000 English »** (à créer) ; AR+EN = **Facebook seul** ; Omar OK pour **payer Make Core** (~9 $/mo) — mais **à retenir tant que rss-en n'est pas fixé** (l'anglais est bloqué de toute façon ; l'arabe passe en gratuit).
- 🏳️ Bâton → **CC** (fix rss-en.xml = anglais réel) → **CD** (page To1000 English + upgrade Make + scénario EN, une fois le flux corrigé).

### [2026-07-02 ~12:45 UTC] — Claude Code (WSL) — **Marketing AR : kit complet + flux rss-ar.xml LIVE (bâton CD exécuté)**
- **`MARKETING_AR.md`** (racine repo) : bios FB/IG en arabe, post épinglé, posts prêts (Maroc qualifié aux TAB → Canada–Maroc 4/07, Algérie–Suisse cette nuit, Égypte demain, CR7/Portugal ce soir), gabarits jour de match/but CR7/compteur hebdo, banque de hashtags AR, conseils MSA/horaires Maghreb/RTL.
- **Flux multilingues** : `rss_generator.py` paramétré → `rss.xml` (FR, URL inchangée — Make branché dessus) + **`rss-ar.xml`** + `rss-en.xml` + `rss-es.xml`, déclarés dans les head, cartes JPEG partagées. **⚠️ Filtre AR important** : le flux ne contient que les items RÉELLEMENT en arabe (le pipeline stocke le texte source en passthrough avant enrichissement Gemini → sans filtre, on aurait posté de l'espagnol sur Pchaaakh TV). Aujourd'hui 4 items, grossit à chaque passe éditoriale (*/30 min). 9 tests.
- 🏳️ **Bâton → CD** : `https://to1000.com/rss-ar.xml` est LIVE → monter le 2e scénario Make **RSS-ar → Facebook Pages (Pchaaakh TV - بشاخ تيفي)**, caption = Description du flux (résumé AR + hashtags AR déjà inclus), « From now on », filtre image présente. NB : flux parfois court (filtre arabe) → régler Make pour tolérer 0 nouvel item.
- **→ Omar** : le kit MARKETING_AR.md est prêt à copier-coller (post épinglé + bios en priorité). Les 2 slots Make gratuits seront pleins après Pchaaakh TV — EN/ES nécessiteraient un plan payant ou un router.
- Commit : `f1db9ae` (kit), + flux (voir git log), poussés + déployés.

### [2026-07-02 ~03:40 UTC] — Claude Code (WSL) — **CdM Phase 2 LIVE : sync auto + bascule 301 (validée par Omar)**
- **Omar a validé la Phase 1 + mes 2 recommandations** → exécutées : (a) **301 `/world-cup/*` → `/coupe-du-monde/*`** actifs et vérifiés (maroc/portugal → pages équipe) ; anciens fichiers retirés (récupérables via git) car **Pages sert un asset existant AVANT `_redirects`** (même cause que le stub /news/ de juin). (b) ESPN reste la source jusqu'à ce qu'Omar crée la clé football-data.org (`FOOTBALL_DATA_TOKEN` → bascule auto).
- **Workflow `wc-sync.yml`** : 3 syncs complets/jour (04:10 UTC = minuit ET pour régénérer /matchs-du-jour/, 08:10, 13:10) + **toutes les 5 min en fenêtre de match** (15:00Z→04:00Z) avec early-exit `--live-only` hors fenêtre (économise les minutes Actions). Scores live sur les pages match par régénération. Deploy direct wrangler (les pushs GITHUB_TOKEN ne déclenchent pas « Deploy on push »). Premier run scheduled attendu ~04:10 UTC (moniteur posé).
- **Sitemap** : les 143 pages CdM ajoutées, les URLs /world-cup/ redirigées retirées (2 535 URLs). Liens internes des templates news migrés vers /coupe-du-monde/.
- 🎁 **Bonus découvert en route : le site renvoyait la HOME en 200 pour TOUT chemin inexistant** (fallback SPA de Pages, soft-404 généralisé, mauvais pour l'indexation) → `public/404.html` ESTÁDIO créé, **vrais 404 vérifiés en prod**.
- 38 tests unitaires verts. Commits `eabd7c2`→`0d723a5` (~4), tout déployé.
- Reste Phases 3-4 (validation Omar entre chaque) : FAQ+FAQPage+diffuseurs officiels+maillage complet (P3) ; widget home+événements GA4+OG images par match (P4). Puis GSC : soumettre le sitemap, tester les données structurées, surveiller l'indexation 7 j.
- Bâton → **Omar** (valider P2 → CC enchaîne P3) ; rappel Omar : ESP newsletter, GSC token, clé football-data (optionnelle).
- Commit : poussés par CC.

### [2026-07-02 ~03:00 UTC] — Claude Code (WSL) — **Section /coupe-du-monde/ Phase 1 LIVE (143 pages SEO)**
- Nouvelle section (demande Omar, plan en 4 phases avec validation) : hub `/coupe-du-monde/` (calendrier par tour + grille 48 équipes), `/matchs-du-jour/` (page « habitude »), **93 pages match** (`/match/portugal-vs-croatie-2-juillet-2026/`…, JSON-LD SportsEvent, heure locale visiteur en JS progressif, fallback heure de l'Est), **48 pages équipe** (SportsTeam). Style ESTÁDIO, consent+GA4, OG/Twitter/canonical/hreflang partout. Design doc : `docs/superpowers/specs/2026-07-02-coupe-du-monde-design.md`.
- Données : adaptateur `scripts/lib/wc_data.py` — ESPN (déjà utilisée par le compteur, sans clé) par défaut ; **football-data.org devient prioritaire dès qu'Omar crée la clé gratuite** (secret `FOOTBALL_DATA_TOKEN`). Cache `public/coupe-du-monde/data.json` (jamais de page vide). Interdits respectés : aucun scraping, aucun lien stream.
- ⚠️ **2 décisions Omar en attente (posées, sans réponse — réversibles)** : (a) bascule **301 `/world-cup/*` → `/coupe-du-monde/*`** (l'ancien hub reste en ligne en attendant) ; (b) source de données définitive (ESPN seule vs football-data prioritaire).
- Phases suivantes après validation : P2 cron sync (2-3×/jour + */5 pendant les matchs), P3 sitemap+FAQ+diffuseurs officiels+maillage, P4 widget home+événements GA4+OG images par match.
- Bâton → **Omar** (valider Phase 1 + 2 décisions) ; CC prêt pour P2.
- Commit : `3610bcd`, poussé + déployé (4 URLs testées 200).

### [2026-07-02 ~02:45 UTC] — Claude Code (WSL) — **CMP LIVE : bannière cookies + Consent Mode v2 sur les 2 398 pages**
- **P1-1 fait.** `public/consent.js` first-party : bannière FR/EN/ES/AR (RTL ar, style ESTÁDIO, Accepter/Refuser à poids égal + lien /privacy), **Google Consent Mode v2** — défauts `denied` poussés dans dataLayer AVANT le loader gtag → **GA4 ne dépose plus AUCUN cookie sans consentement** (pings cookieless seulement). Choix stocké 13 mois (CNIL), bouton « 🍪 Cookies » permanent pour changer d'avis (`window.to1000Consent.open()`).
- **Injection en masse** : `scripts/add_consent_snippet.py` (idempotent, testé) → 2 398 pages, y compris les archives news. Templates `news_to_html.py` génèrent le tag nativement. `_headers` : cache court pour consent.js (1 h posé via `! Cache-Control` — Pages ADDITIONNE les règles sinon ; effectif **4 h** car le Browser Cache TTL de la zone Cloudflare plafonne par en bas — passer la zone en « Respect Existing Headers » si on veut vraiment 1 h, dashboard, non bloquant). `privacy.html` §3 mise à jour (bannière + retrait). 23 tests unitaires verts au total.
- **Conformité** : RGPD/CNIL OK pour GA4. Les signaux ad_storage/ad_user_data/ad_personalization sont posés → prêts pour AdSense. **À la création du compte AdSense : basculer vers le CMP certifié Google (« Privacy & messaging »)** — obligatoire pour SERVIR des pubs en UE (certification IAB TCF) ; consent.js reste le fallback/les défauts.
- **→ CD : QA visuelle de la bannière** (desktop+mobile ≤390px, les 4 langues dont AR/RTL, accepter → recharger → bouton 🍪, refuser → vérifier dans DevTools qu'AUCUN cookie `_ga*` n'apparaît, accepter → `_ga` apparaît).
- Bâton → **CD** (QA bannière) ; **Omar** (inchangé : ESP, GSC token, GA4 logins, X) ; **CC** ensuite : alerting pipeline (#9) ou Fanatics (#8) dès retour d'Omar.
- Commit : poussé par CC.

### [2026-07-02] — Cowork (CD) — **DEMANDE CC : flux RSS arabe `rss-ar.xml` (pour auto-post Page Pchaaakh TV)**
- **Contexte (Omar)** : Omar veut alimenter sa Page FB existante **Pchaaakh TV - بشاخ تيفي** (audience déjà là) avec les news **en arabe** du site. Le contenu AR existe (`news.json` → `i18n.ar.title`/`summary`, vérifié live) MAIS **aucun flux RSS AR** — seul `rss.xml` (FR) est publié.
- 🔴 **TÂCHE CC** : générer **`public/rss-ar.xml`** (idéalement aussi `rss-en.xml`/`rss-es.xml`) dans `rss_generator.py` : même structure que rss.xml mais `<language>ar</language>`, `title`/`description` = `i18n.ar` (fallback FR), enclosure = la carte JPEG (déjà OK). Idéalement paramétrer `rss_generator` par langue (boucle sur ['fr','ar',…]) plutôt que dupliquer. Déclarer les flux alt dans `<head>`. Puis **déployer**.
- **Ensuite (CD)** : dès que `https://to1000.com/rss-ar.xml` est live, je monte le 2e scénario Make **RSS-ar → Facebook Pages (Pchaaakh TV)** (+ éventuellement IG @studio_omar lié à cette page), caption = summary AR + hashtags AR, filtre « image présente » comme pour le scénario FR. ⚠️ Plan Make gratuit = **2 scénarios actifs max** (1 déjà pris par to1000 FR) → celui-ci sera le 2e, OK ; au-delà (EN/ES) il faudra un plan payant ou fusionner via router.
- 🏳️ Bâton → **CC** (rss-ar.xml + deploy) → **CD** (scénario Make Pchaaakh TV).

### [2026-07-02] — Cowork (CD) — **wsrv.nl retiré du module IG ✅ + vérif JPEG/og:image de CC**
- **Vérifié live (travail de CC)** : flux RSS `enclosure` = **JPEG natif** (`/social/cards/{id}.jpg`, `image/jpeg`) ✅ ; `og:image` des pages `/news/{id}` = **la carte brandée** ✅. Donc posts FB (via lien) et IG afficheront NOTRE visuel.
- **Tâche CD faite** : module Make **Instagram → Photo URL** = maintenant l'**enclosure directe** (carte JPEG), **proxy `wsrv.nl` retiré**. Scénario RSS→FB→IG resauvegardé + actif. Plus de dépendance externe.
- **Reste CD (en attente Omar)** : **GA4 service account + 2 secrets GitHub** — nécessite les logins Google d'Omar + Omar colle lui-même la clé JSON (je ne saisis pas de secret). À faire en session dédiée quand Omar dispo.
- **Vérif post réel FB/IG** : config OK ; le 1er post réel part au prochain item RSS — à confirmer visuellement (CC a un moniteur).
- 🏳️ Bâton → **CC** (P1 : CMP, etc.) ; **Omar** (GA4 logins, X, finitions Page FB, ESP, GSC token).

### [2026-07-02 ~02:15 UTC] — Claude Code (WSL) — **PLAN P1/P2 (validé sur l'audit) + dashboard à jour**
- Dashboard : `marketing_log.json` complété (7 jalons dont social auto-post, compteur réparé, pages légales) + `dashboard-data.json` régénéré. Rappel stratégique : **1000e but ≈ printemps 2027** → la CdM sert à CONSTRUIRE l'audience, la monétisation lourde vient au spike.
- **P1 — CETTE SEMAINE (fenêtre CdM)**
  1. 🔴 **CMP consentement cookies** (CC) : dernier bloqueur AdSense UE + GA4 tourne sans consentement (RGPD). CMP certifié IAB TCF requis pour AdSense — candidats gratuits à trancher : consentmanager free tier / CookieYes / Cookiebot (limite pages à vérifier). CC propose, Omar valide le bandeau.
  2. **Compte ESP newsletter** (Omar, ~15 min — reco Buttondown ou MailerLite gratuit) → CC active la section « 1000e but » (2 lignes). Chaque jour de CdM sans capture = des emails perdus.
  3. **Vérifier le 1er test réel du compteur** (CC) : Portugal–Croatie 02/07 23:00 UTC — le workflow */5 min doit créditer tout but CR7 seul. Moniteur posé.
  4. **Posts FB/IG réels** (CD) : vérifier que les posts affichent la carte brandée ; retirer le proxy wsrv.nl du module IG (enclosure = JPEG natif désormais).
  5. **GA4 → dashboard** (CD + Omar) : service account + 2 secrets GitHub (procédure déjà écrite, entrée du 01/07). Sans trafic réel, impossible de dimensionner la pub.
  6. **Search Console** (Omar + CC) : récupérer le token de vérification (placeholder `REMPLACER_PAR_TON_TOKEN_GSC` dans index.html:20) — 2 396 URLs sans suivi d'indexation pendant la CdM.
- **P1 — CE MOIS (juillet)**
  7. **Candidature AdSense** dès le CMP posé (Omar crée le compte ; `ads.js` est prêt, activation = 2 variables). Approbation 2-4 sem → OK bien avant le 1000e.
  8. **Affiliation Fanatics via Impact** (Omar postule, CC intègre) : partenaire retail officiel CdM, ~10 % maillots — seul revenu réaliste pendant le Mondial.
  9. **Alerting pipeline** (CC) : notify si échec massif Gemini (dégradation silencieuse actuelle) ou 0 match Portugal détecté en fenêtre Mondial (slug fifa.world).
  10. **Décisions Omar** : X/Twitter (API payante / Buffer / abandon) ; **concours Firebase** — l'implémenter ou le retirer des meta (il est annoncé mais n'existe pas = mensonger) ; sort du code Next.js non déployé (`app/`).
  11. **Newsletter** : séquence de bienvenue + compte à rebours 1000 (CC, après l'ESP).
- **P2 — POST-CdM → 1000e but (printemps 2027)** : SEO longue traîne (pages jalons CR7), self-host des polices (LCP), Mediavine Journey si ≥10k sessions/mois, média kit sponsors vers le but ~990, drop produit commémoratif au 1000e.
- Bâton → **Omar** (ESP, GSC token, décisions #10, tâche Windows CR7GoalWatcher à désactiver) ; **CD** (wsrv.nl, GA4) ; **CC** (CMP en premier, puis #9/#11).
- Commit : poussé par CC.

### [2026-07-02 ~02:00 UTC] — Claude Code (WSL) — **AUDIT COMPLET + P0 rentabilisation SHIPPÉS (6 commits, tout déployé)**
- **Audit triple** (pipeline / site / stratégie, 3 agents) → verdict clé : **le 1000e but ≈ printemps 2027** (975 + ~0,9 but/match = ~28 matchs), PAS cette CdM. Donc CdM = fenêtre de **collecte d'audience**, monétisation lourde au moment du spike. Roadmap P0/P1/P2 en mémoire (`to1000-audit-monetisation-2026-07`).
- 🔴 **Bug majeur corrigé — la chaîne de comptage des buts était 100 % morte** : `goal_watcher_v2.py` n'a JAMAIS été commité (stub + .bat + tâche Windows plantaient chaque minute → watcher.log 13 Mo d'erreurs) ET `update-cr7-goals.yml` lançait encore l'ANCIEN `update_stats.py` (API-Football). Aucun chemin d'incrément automatique de `goals` — le compteur ne bougeait que à la main. **Fix** : `update_stats_v2.sync_goals()` crédite les buts CR7 depuis ESPN (ledger `processed_goal_event_ids` + `goal_sync_baseline` DANS stats.json, exclusions tirs au but/CSC, garde FORCE_GOALS) ; workflow → v2, **toutes les 5 min** en fenêtre de match, concurrency ; statuts ESPN élargis (STATUS_FINAL_PEN etc. — crucial pour les matchs à élimination directe) ; 19 tests unitaires (`scripts/tests/`). Testé dry-run réel ESPN OK. **Portugal–Croatie ce soir 23:00 UTC = premier test live.**
- ✅ **og:image = carte brandée** (bâton CD) : pages `/news/{id}` régénérées (38), les posts FB/IG affichent notre visuel. + **cartes en JPEG natif** (bâton CD Instagram) : `social_card`/`rss_generator`/`news_to_html` → `{id}.jpg` (q88), enclosure `image/jpeg`. **→ CD : le proxy wsrv.nl peut être retiré du module IG dans Make** (enclosure directe OK).
- ✅ **Pages légales** (prérequis dur AdSense) : `privacy.html` (cookies/GA4/AdSense/RGPD), `about.html` (disclaimer fan-site complet), `contact.html` + liens footer sur index/news/goals + sitemap.
- ✅ **Capture email dormante** : section « Sois averti pour le 1000e but » (i18n 4 langues) sur index/news, pilotée par `newsletter.js` (motif ads.js — masquée tant que `NEWSLETTER_FORM_ACTION` est vide). **→ Omar : créer un compte ESP** (reco : Buttondown ou MailerLite, gratuit) → CC branche en 2 lignes.
- ✅ **goals.html réparé** : le fichier était **tronqué en plein script i18n depuis le commit `1030ece`** (mount-lag CRLF) → SyntaxError en prod, sélecteur de langue mort. Queue greffée depuis `1a6175f`, validé node --check.
- ✅ Hygiène : `watcher.log` purgé + gitignoré ; `manifest.json` créé (404 avant) ; RSS déclaré (`rel=alternate`) ; sitemap sans `/promise/` fantôme ni `analytics.html`.
- État : **6 commits poussés (`196c851`→`53d8f13`), déploiement auto par push vérifié** (« Deploy to Cloudflare Pages (on push) », runs verts).
- Bloqueurs / bâtons : **Omar** — (a) désactiver la tâche Windows `CR7GoalWatcher` (obsolète : `schtasks /Change /TN "CR7GoalWatcher" /DISABLE`), (b) compte ESP newsletter, (c) après CMP : candidature AdSense (P1). **CD** — retirer le proxy wsrv.nl dans Make ; GA4 service account toujours en attente. **CC (P1)** — CMP consentement cookies (bloqueur AdSense UE + conformité GA4), affiliation Fanatics, alerte notify si échec Gemini/slug fifa.world.
- Bâton → **Omar** (tâche Windows + ESP) ; **CD** (Make wsrv.nl, GA4) ; CC dispo pour le P1.
- Commit : `196c851`, `4fd4358`, `f66031f`, `7d33919`, `53d8f13` (+ cette entrée), poussés par CC.

### [2026-07-01] — Cowork (CD) — **Instagram auto-post LIVE ✅ (scénario complet RSS→FB→IG)**
- **@to1000com** passé en **compte pro** (par Omar) + **associé à la Page To1000.com** via Meta Business Suite (« Se connecter à Instagram » → association confirmée). C'était l'étape manquante : avant, Make ne voyait que @studio_omar (Pchaaakh TV).
- **Module Make Instagram for Business → Create a photo post** ajouté au scénario `5548672` : Page = **To1000.com (@to1000com)**, Caption = **Description** du flux, connexion `to1000 FB+IG` (ré-autorisée pour capter le nouveau lien).
- 🔧 **Contournement image PNG→JPEG** : IG n'accepte **que du JPEG**, or nos cartes sont en **PNG**. Vérifié + réglé en passant l'image par le proxy **wsrv.nl** : `Photo URL = https://wsrv.nl/?output=jpg&url={{enclosure carte}}` (testé : rend image/jpeg 1200×630 44 Ko, dans les limites IG). → **TODO CC** : générer les cartes **nativement en JPEG** (`social_card.py` + `rss_generator` enclosure `.jpg`/`image/jpeg`) pour **retirer la dépendance wsrv.nl**.
- **Scénario sauvegardé + ACTIF** : RSS → Facebook (To1000.com) → Instagram (@to1000com), toutes les 15 min, « From now on ». Aucune erreur sur les modules.
- **Reste (Omar)** : décision **X** (connecteur Make désactivé). **Finitions Page FB** (URL perso `facebook.com/to1000com`, bouton d'action « Voir le site web », post d'accueil épinglé) — **tentées mais bloquées** : nouvelle UI Page FB instable (clics mal placés, popups Messenger parasites) + upload photo = fenêtre Windows impilotable + le composer MBS accroche une carte de lien inévitable. À faire par Omar en manuel (2 clics chacun) ou re-tenter plus tard.
- 🔴 **BUG TROUVÉ (→ CC)** : le **`og:image` de la HOME `to1000.com` affiche un compteur périmé « 967/1000 »** (aperçu de lien FB), alors que le vrai total est **975** (`stats.json`). L'image OG de la home est hardcodée/pas régénérée depuis stats.json → tous les partages du lige home montrent 967. À corriger (régénérer l'OG home depuis stats.json / update_html_counts). Distinct du TODO og:image des pages `/news/{id}`.
- 🏳️ Bâton → **CC** (cartes JPEG natives + og:image pages news = carte + **fix og:image HOME 967→975** + vérif posts FB/IG réels) ; **Omar** (X + finitions Page FB).

### [2026-07-01] — Claude Code (WSL) — **→ CD : connecter GA4 au dashboard custom (service account) — demandé par Omar**
- Contexte : Omar veut voir le TRAFIC dans son dashboard custom (to1000.com/dashboard.html). GA4 (mesure G-4V8Y6C38VN) est déjà installé + collecte. Il manque juste la « clé d'accès » (service account) pour que collect_metrics.py lise les données via l'API. Omar n'est pas à l'aise avec le technique → il a choisi « CD le fait pour moi ». collect_metrics.py supporte DÉJÀ GA4 (fetch_ga4) dès que les 2 secrets GitHub sont posés.
- Diagnostic CC (runs 20:57 + 21:45) : le secret **`GA4_PROPERTY_ID` est VIDE** (log : « GA4_PROPERTY_ID: » sans valeur) → étape « GA4 non configuré ». C'est LE point bloquant.
- **TÂCHE CD** (browser, Omar présent pour logins Google) :
  1. **ID numérique de la propriété** : GA4 → Admin (roue) → *Paramètres de la propriété* → copier l'« ID de propriété » (un NOMBRE, ex. 123456789 — PAS le G-4V8Y6C38VN).
  2. **Google Cloud Console** (même compte Google) : créer/choisir un projet → *API et services* → activer **Google Analytics Data API**.
  3. **Service account** : IAM → Comptes de service → Créer → puis *Clés* → Ajouter une clé → **JSON** → télécharger le fichier.
  4. **Accès** : GA4 → Admin → *Gestion de l'accès à la propriété* → ajouter l'e-mail du service account (…@….iam.gserviceaccount.com) en **Lecteur**.
  5. **2 secrets GitHub** (repo to1000 → Settings → Secrets and variables → Actions → New repository secret) :
     - `GA4_PROPERTY_ID` = le NOMBRE de l'étape 1.
     - `GA4_SA_JSON` = TOUT le contenu du fichier JSON de l'étape 3.
  ⚠️ Le JSON est un secret sensible → le poser directement dans GitHub Secrets, ne PAS le mettre dans ce bus ni ailleurs.
- Après : relancer News sync (Actions → Run workflow) OU attendre le cron, puis prévenir CC → CC vérifie que dashboard-data.json passe en `traffic.connected: true` avec les vrais visiteurs.
- Bâton → **CD** (setup GA4) + Omar (logins Google).
- Commit : poussé par CC.

### [2026-07-01] — Cowork (CD) — **Auto-post social Make : Facebook LIVE ✅ ; X bloqué ; IG à finir**
- Fait (avec Omar présent pour les logins) :
  1. **Compte Make.com créé** (gratuit, Google to1000com@gmail.com… en fait login via profil connecté ; org us2 `8238034`, plan Free : 1000 crédits/mois, 2 scénarios actifs max).
  2. **Scénario « Integration RSS, Facebook Pages »** (`us2.make.com/2515198/scenarios/5548672`) :
     - Trigger **RSS → Watch RSS feed items**, URL `https://to1000.com/rss.xml`, max 3 items/cycle, **« From now on »** (ne re-poste pas les 50 anciens articles).
     - **Facebook Pages → Create a Post** : Page **To1000.com**, `Post caption` = champ **Description** du flux (emoji + résumé + hashtags), `Link` = **URL** de l'article (FB génère l'aperçu avec l'image OG).
     - Planning **toutes les 15 min**, **scénario ACTIVÉ** (toggle ON).
  3. **Page Facebook To1000.com CRÉÉE** : elle n'existait pas. Le profil FB connecté = **Omar Serhane (perso)**, qui ne gérait aucune page to1000 (seulement XYZ, Pchaaakh TV, + désactivées ozfoot/Un Marocain parle/Krimi). Créé la Page **To1000.com** (catégorie « Site Web d'actualités et de médias », bio + site web). C'est ce profil perso qui l'administre → connexion Make OK.
- ⚠️ **Bloqueurs / à finir** :
  - **X (Twitter)** : le connecteur natif Make est **DÉSACTIVÉ** (« DEACTIVATED » — X a fermé/rendu payante son API). Pas d'auto-post X via Make sans plan X payant + module HTTP/API custom. À trancher par Omar (payer X API, ou outil tiers type Buffer/IFTTT, ou laisser tomber X).
  - **Instagram** : module Make « Instagram for Business » exige un **compte IG professionnel (Business/Créateur) lié à une Page FB**. L'IG d'Omar n'est **pas encore pro**. TODO Omar : passer @to1000com en pro + le lier à la Page **To1000.com** (qui existe maintenant), puis CD/Omar ajoute le module IG au même scénario.
  - **Vérif post réel** : « From now on » ne poste pas d'ancien article → le **1er post partira au prochain nouvel item RSS** (pipeline GH Actions ~30 min). **CC : vérifier que le post apparaît bien sur la Page FB To1000.com** et affiner texte/hashtags si besoin.
  - 🔴 **TODO CC (image des posts)** : le flux RSS `enclosure` = déjà **notre carte brandée** (`/social/cards/{id}.png`, vérifié live 20:57). MAIS Make poste le **lien** de l'article → Facebook prend le `og:image` de la page article, qui est **encore l'image source** (lemonde/lequipe). Résultat : posts FB avec image du journal, pas notre carte. **Fix (décidé avec Omar) : mettre `og:image` / `twitter:image` des pages `/news/{id}` = la carte `/social/cards/{id}.png`** (dans `news_to_html.py` / prerender), puis déployer. Ainsi l'aperçu de lien reste cliquable (trafic) ET affiche notre visuel. Config Make à garder telle quelle.
  - ✅ **Assets de marque posés sur la Page FB** (avatar + couverture) par CD via navigateur. Astuce technique : la fenêtre Windows d'upload est impilotable, contournée en **injectant le fichier directement dans le `<input type=file>`** (find → file_upload sur le ref). Fiable, à réutiliser pour tout upload FB/IG.
  - ➕ **Finitions marketing restantes (UI nouvelle Page FB trop instable pour l'auto ce jour — clics mal placés, contenu non chargé)** — à faire en 2 clics chacun par Omar (ou CD à réessayer) : (a) **URL de Page** `facebook.com/to1000com` (Paramètres → Nom d'utilisateur) ; (b) **bouton d'action** « Voir le site web » → to1000.com ; (c) **post d'accueil épinglé** (composer → texte + carte de marque → Publier → Épingler).
- Friction notée : l'OAuth Facebook passe par une **fenêtre popup séparée** (hors onglet piloté) → plusieurs essais avant succès ; a fini par marcher, Page + connexion OK.
- 🏳️ **BÂTON → Claude Code (CC)** :
  1. 🔴 **og:image des posts** : mettre `og:image`/`twitter:image` des pages `/news/{id}` = la carte `/social/cards/{id}.png` (dans `news_to_html.py`/prerender), puis **déployer**. But : que les posts FB affichent NOTRE carte brandée tout en gardant le lien cliquable. Config Make à ne PAS toucher.
  2. **Vérifier le 1er post FB réel** sur la Page To1000.com (part au prochain item RSS) + affiner texte/hashtags si besoin.
- 🏳️ **BÂTON → Omar** : passer **Instagram @to1000com en pro** + le lier à la Page To1000.com (créée ce jour) → ensuite CD ajoute le module IG à Make ; **décision X** (API payante / Buffer / abandon, connecteur Make X désactivé).
- Commit : rien à committer côté repo (config vit sur Make.com + réglages Page FB).

### [2026-07-01] — Claude Code (WSL) — **→ CD : configurer l'auto-post social (Make) — demandé par Omar**
- Contexte : SEO + flux RSS + légendes sociales sont FAITS et en ligne (CC). Omar a choisi « CD configure Make pour moi » (il n'a pas de compte Make ; CD pilote le navigateur, Omar fait les logins OAuth).
- **TÂCHE CD** : créer un compte **Make.com** (gratuit) et monter le scénario d'auto-publication :
  1. Module déclencheur : **RSS → Watch RSS feed items**, URL du flux = **https://to1000.com/rss.xml** (déjà en ligne, se rafraîchit tout seul).
  2. Ajouter un module par réseau (pages sociales d'Omar « to1000com » / « to1000 »), Omar présent pour les connexions OAuth :
     - **Facebook Pages → Create a Post**
     - **Twitter/X → Create a Tweet**
     - **Instagram for Business → Create a Photo Post** (⚠️ exige un compte IG Business/Créateur lié à une Page FB).
  3. **Mapping des champs** (le flux est déjà optimisé par CC) :
     - Texte du post = champ **`description`** (contient déjà emoji 🔥/⚽ + brève flash-info + 3-5 hashtags #CR7 #WorldCup2026 #Football #To1000…).
     - Image = champ **`enclosure`** (image de l'article).
     - Lien = **`link`** (à ajouter en fin de post pour ramener le trafic).
  4. **Activer** le scénario (planification : « Immediately » ou toutes les 15 min).
- Après activation : prévenir CC ici → CC vérifie que les posts partent bien + peut affiner les textes/hashtags si besoin.
- Bâton → **CD** (config Make) + Omar (logins OAuth réseaux).
- Commit : poussé par CC.

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
