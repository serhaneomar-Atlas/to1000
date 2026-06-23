# DESIGN_AUDIT — to1000.com (Phase 1 du DESIGN_BRIEF)

> Livrable de la PHASE 1 (AUDIT) avant toute ligne de code de refonte.
> Auteur : Claude Code (WSL) · Date : 2026-06-23 · Statut : **à valider par Omar**.
> Méthode : lecture intégrale de `public/index.html` (4316 lignes), mesures objectives
> (grep/wc), audit des `_headers`, recherche outillage + benchmark via agents.
> ⚠️ Pas de Lighthouse réel : le sandbox WSL n'a pas les libs navigateur
> (`libnspr4.so` absent) → métriques perf = analyse statique du chemin de rendu,
> à confirmer par un run Lighthouse réel côté Omar/CI.

---

## 0. TL;DR (pour décision rapide)

- **Le problème n°1 n'est pas esthétique, c'est structurel** : `index.html` = **un seul fichier de 4316 lignes / 200 Ko** (≈2000 lignes de CSS inline + ≈800 de markup + ≈1250 de JS + i18n). Tout changement est risqué, rien n'est réutilisable, le cache navigateur ne sert quasiment à rien.
- **3 chiffres différents pour le même compteur dans un seul fichier** : le live (`stats.json`) = **975 / 25 restants** (v30, doublé vs Ouzbékistan le 23/06), mais le SEO statique code en dur **973 / 27**, et le JS initialise **973 / 32**. Désynchronisation = bug de fond, pas un détail (et le live bouge vite : 973→974→975 en une journée).
- **Le live update est fragile** : `applyLiveUpdate()` cible des sélecteurs couplés à des nombres en dur (`[data-target="973"]`, `"29"`, `"23"`) → ça casse en silence dès qu'on touche au markup. À sécuriser dans la refonte.
- **L'acquis est réel et à préserver** : SEO très soigné (6 blocs JSON-LD), CSP/HSTS propres, i18n 4 langues + RTL fonctionnel, polling live avec pause onglet caché.
- **Direction visuelle** : 2 maquettes hero livrées (A = évolution or/noir ; B = rupture scoreboard), registre **broadcast premium**, hero **hybride**. → **STOP, choix d'Omar requis.**

---

## 1. Inventaire page par page

| Page | Lignes | Rôle | État |
|---|---|---|---|
| `index.html` | 4316 | Hero + compteur + journey + worldcup + stats + clubs + records + contest + share + news + blog + FAQ + about | Monolithe, riche, dette maximale |
| `goals.html` | 1253 (333 Ko) | Base de tous les buts | Très lourd, à auditer séparément (hors périmètre immédiat) |
| `analytics.html` | 503 | Dashboard interne | Outil, pas public |
| `admin.html` | 269 | Admin | Outil |
| `utm-generator.html` | 237 | Outil marketing | Outil |
| `to1000-preview.html` | 3492 | Ancienne préversion (?) | **Mort probable — à confirmer/supprimer** |
| `blog/*.html` | — | 3 articles | OK, cohérence visuelle à vérifier |
| `news/*.html` | — | ~50 pages news générées | Gabarit à intégrer au design system |

**Sections de `index.html`** (par `id`) : `wc-banner`, hero/`countdown`/`remaining`, `homeNews`, `nextMatchWrap`/`lastMatchBand`/`nextMatchCard`, `journey`, `worldcup`, `stats`, `clubs`, `records`, `predict` (contest Firebase), `share`, `subscribeForm`/`notifBtn`, `goal-toast`, `faq`, `news`, `latestBlogGrid`, `about`, footer. → **beaucoup de sections** : la refonte devra hiérarchiser (le compteur reste le héros, le reste se subordonne).

---

## 2. Dette technique (le vrai chantier)

1. **Monolithe inline.** 1 fichier, CSS dans 2 balises `<style>` (lignes 243→2231 ≈ 1988 lignes) + JS inline (≈3068→4316). Conséquences :
   - Aucune séparation des préoccupations, diff illisible, collisions Cowork/Claude Code probables.
   - **Les `_headers` mettent en cache `*.css` et `*.js` 30 jours `immutable`… mais il n'existe aucun fichier CSS/JS externe.** Le cache long terme ne s'applique qu'aux SVG/images. Le HTML lui-même n'est caché qu'1 h. → extraire CSS/JS = gain de cache immédiat.
2. **Données en dur dupliquées et désynchronisées** (cf. TL;DR) : `CURRENT_GOALS = 973`, `GOALS_REMAINING = 32` (l.3069-3071) ; SEO meta/OG/Twitter/JSON-LD = 973 / 27 ; live = 975 / 25 (v30). Trois sources de vérité pour un seul nombre, qui divergent d'autant plus que CR7 marque.
3. **Couplage JS ↔ markup par valeurs magiques.** `applyLiveUpdate()` (l.3124+) fait `querySelectorAll('.count-up[data-target="973"]')`, `"29"`, `"23"`. Si un futur edit change ces nombres, les hooks live cessent silencieusement de fonctionner. → la refonte doit cibler par `data-role`/`id` stables, jamais par valeur.
4. **i18n maison** : objet `PAGE_TRANSLATIONS` (l.4048+), 127 attributs `data-i18n`. Fonctionnel mais monolithique ; à externaliser proprement (JSON par langue).
5. **Fichiers parasites dans `public/`** : `__persist_test.txt`, `_mount_probe.txt`, `_mtest.txt`, `.__write_test`, `.__wtest`, `news_before_2.json`, `news_before_run.json`. → à nettoyer (ils sont servis publiquement).
6. **Code Next.js parallèle** (`app/`, `components/`, `lib/`) non déployé → **décision en attente** (cf. §8).

---

## 2bis. Bugs & intégrité repo (vérifiés en prod, pas seulement dans le code)

> ⚠️ Un agent avait conclu « sélecteur de langue mort en prod ». **Vérification : faux.** La réalité est plus subtile (et plus dangereuse pour le déploiement). Faits confirmés :

1. **`_engage.js` est ABSENT du repo (CRITIQUE — intégrité).** Prod sert `/_engage.js` (HTTP 200, **~200 Ko**, contient `setLang` + la logique i18n/engagement). Mais ce fichier **n'est ni dans `public/` ni suivi par git.** Conséquence : `setLang()` est appelé dans `index.html` (l.2281-2284) sans être défini localement ; **en prod ça marche** grâce à `_engage.js`, mais **un redeploy depuis le repo casserait le sélecteur de langue + tout le RTL de l'accueil.** → Bombe à retardement. **Action : récupérer `_engage.js` depuis prod et le committer** (ou réintégrer proprement sa logique dans la refonte) avant tout redeploy.
2. **Prod est périmé de 2 buts.** `to1000.com/stats.json` (live) = **973**, alors que le local = **975**. Le déploiement #974/#975 n'a jamais eu lieu (cf. HANDOFF §5). Le site public affiche donc 973. → action Omar : `deploy_now.bat`.
3. **`973` codé en dur à 7 endroits** d'`index.html` (nav l.2279/2305, hero l.2329, journey l.2403, CTA l.2719/2721, toast l.2973) + dict i18n. Fallback statique périmé ; c'est `_engage.js` (live) qui les réécrit — d'où la dépendance critique au point 1.
4. **`FAQPage` JSON-LD désormais inerte** : Google a retiré les rich results FAQ pour la plupart des sites (mai 2026). Pas nuisible, mais poids mort → à reconsidérer.
5. **RTL en propriétés physiques** : ~46 règles `margin-left`/`left`/`float`, zéro propriété logique → fragile. À migrer en `margin-inline`/`inset-inline` dans la refonte.

> **Bon point confirmé** : les pages `news/*.html` ont un excellent structured-data (`NewsArticle` + `ImageObject` + `Organization` + OG/Twitter + hreflang) ; la page arabe `world-cup/maroc/ar/` est correcte (`<html lang="ar" dir="rtl">` + hreflang réciproque). → le skill `claude-seo` serait **redondant** ici (raison de plus de le skipper, cf. §11).

---

## 3. Performance (analyse du chemin de rendu)

**Points positifs :**
- Hero image en `loading="eager" fetchpriority="high"` + `<picture>` webp/jpg sur les vignettes (lazy).
- `display=swap` sur les fonts ; `preconnect` vers Google Fonts.
- Polling live en pause quand l'onglet est caché (économie réseau).

**Points à corriger :**
- **Fonts render-blocking lourdes** : 3 familles, **15 graisses** au total (Inter 7 + Playfair 3 + Cairo 5) via une seule requête CSS bloquante. → réduire aux graisses réellement utilisées, voire `preload` + `font-display:swap` ciblé.
- **Canvas de particules** : `canvas.height = window.innerHeight * 3` (l.3273) → grande surface + boucle d'animation JS continue = coût CPU/batterie sur mobile. À questionner (effet vs coût Lighthouse).
- **13 `@keyframes`** + `backdrop-filter: blur()` multiples → coût de composition sur mobile bas de gamme.
- **200 Ko de HTML** parsés avant tout (CSS+JS inline). Extraire = parse plus court + cache.
- GA4 chargé tôt dans `<head>` (async, OK) — mais à confirmer qu'il ne retarde pas le LCP.

**LCP probable** : le grand nombre du compteur (`.hero-score-current`) ou l'image hero. Le rendre **texte** (compteur typographique) sécurise le LCP — cohérent avec le hero hybride retenu.

> 🎯 Objectif brief : Lighthouse mobile ≥ 90. **Non mesuré ici** (pas de navigateur). Mesure réelle à faire avant/après refonte.

---

## 4. Accessibilité

- **Contrastes texte faibles** : usage répété de `rgba(255,255,255,0.5)`, `0.45`, `0.35` (hero-sub, nav-links, labels) sur fond `#060606`. Le blanc à 50 % d'opacité ≈ #808080 sur noir → **échoue AA** pour le texte courant. À reprendre dans les tokens (opacité plancher ~0.7 pour le texte).
- Or `#D4AF37` sur noir : OK en grand/gras, limite en petit corps.
- **RTL arabe géré** (l.2160+ : `html[dir="rtl"]`, réalignements ciblés, compteur recentré) — bon point, à conserver/systématiser via **propriétés logiques** (`margin-inline`, `inset-inline`) plutôt que des overrides manuels.
- À vérifier dans la refonte : focus visibles clavier, `prefers-reduced-motion` (les maquettes l'intègrent déjà), labels de formulaire (contest/subscribe), ordre de tabulation.

---

## 5. Responsive

- **Breakpoints incohérents** : `max-width` 480 / 600 / 640 / 768 et `min-width` 640 / 1024 cohabitent sans système. → définir une échelle unique (ex. 480 / 768 / 1024 / 1280) dans les tokens.
- Compteur en `clamp()` (bien) mais ombres/halos non réduits sur petit écran.
- Mobile-first à réaffirmer : le compteur doit rester LE héros sur 360–390 px.

---

## 6. SEO & contrat de données — À PRÉSERVER (non négociable)

- **6 blocs JSON-LD** : WebSite+SearchAction, Person (CR7), BreadcrumbList, WebApplication, FAQPage (10 Q/R), +1 (l.224). Très bon pour les rich snippets. **À conserver et à brancher sur les vrais chiffres** (aujourd'hui figés à 973).
- OG/Twitter complets, canonical + hreflang EN/FR/ES/AR + x-default.
- `stats.json` (champs `goals`, `remaining`, `last_goal_*`, `last_match`, `next_match`, `last_updated`) lu par `fetchLiveStats()` (poll 60 s, cache-bust) → **contrat à ne pas casser**.
- `news.json` (cap 50) alimente la section news ; contest = Firebase (`to1000-contest`).
- **Reco** : générer les chiffres SEO (meta/JSON-LD) au build/déploiement depuis `stats.json` pour ne plus jamais être périmé.

---

## 7. Sécurité & légal

- **CSP/HSTS solides** (`_headers`) : `default-src 'self'`, sources GA/Firebase/Fonts/YouTube whitelistées, `object-src 'none'`, `base-uri 'self'`. Bon.
- Disclaimer « fan site non officiel » : **à vérifier présent dans le footer** de la refonte (obligatoire). Aucun branding **CR7™** dans le logo/design — les maquettes respectent (typo « to1000 », pas de marque déposée).
- Config Firebase exposée côté client = normal (clé publique), rien à corriger.

---

## 8. Décisions à remonter à Omar (queue HANDOFF)

1. **Choix de la direction visuelle** : A (évolution or/noir) ou B (rupture scoreboard) — voir §10 + maquettes.
2. **Code Next.js parallèle** : garder ou supprimer ? Reco Claude Code : **supprimer** si la refonte reste en statique pur (Cloudflare Pages, pas de build) — cohérent avec la stack prod et ça réduit la surface de confusion. À trancher avant la Phase 2.
3. **Canvas particules** : on garde l'effet (coût perf) ou on le remplace par un fond CSS plus léger ?
4. **`to1000-preview.html`** (3492 lignes) : mort ? → suppression.

---

## 9. Benchmark — sites de référence

> Synthèse d'un agent (23 sites, fetches first-hand sur la majorité). **Découverte clé : un concurrent direct existe — `howmanygoalsronaldo.com`** (mêmes valeurs : `#050607` / or `#f0d48b`, compteur `clamp(72px,18vw,240px)`, count-up rAF ease-out quartic ~3,4 s, `aria-live`). **Sa faille mortelle : le count-up ne joue qu'une fois, puis la page est figée.** → notre différenciateur = fabriquer une vie continue **sans mentir** sur le compteur.

| Référence | À voler |
|---|---|
| **UEFA "Kick of Light"** | Champ sombre unique + un trait de lumière qui *court le long des bords* (adapter : balayage doré autour de l'anneau du compteur) ; verre dépoli pour la profondeur ; animer *la lumière*, pas les éléments. |
| **Apple Sports** | Fond gradient vivant (ancres qui dérivent + shimmer) = façon la moins chère de rendre un compteur statique « vivant » ; chiffres en variable font condensée-bold, on pousse l'axe poids/largeur au tick. |
| **FotMob / FlashScore** | Point pulsé + minute qui compte = signal LIVE canonique ; **rouge réservé STRICTEMENT à l'in-play** ; notation `72′`. |
| **OneFootball** | Système de pastilles 3 états : **or "LIVE" / gris "NEXT MATCH" / "OFF-SEASON"** (colle à notre `next_match` qui peut être `off_season`). |
| **Real Madrid / F1 / PSG** | **Records = plaques** (icône + chiffre géant + label all-caps fin : 5 Ballons d'Or, 5 LDC, ~140 buts sélection) ; cutout CR7 net sur gradient sombre ; **chip d'honneur permanent en header** ("1000 WATCH") ; lignes/étoiles dorées qui encadrent l'achievement. |
| **Broadcast scorebugs (Fox/CBS/NBC)** | **La typo du score EST le héros** ; bar de fond **solide** (jamais transparente sur image claire — erreur documentée de Fox) ; au but : la bug s'agrandit ~2 s puis se pose (hiérarchie temporaire). |
| **Worldometer** *(anti-pattern)* | Surtout : **NE PAS** simuler une progression à la seconde sur une valeur qui bouge une fois/mois → ça tue la crédibilité d'un tracker. |

**Principes décision-ready (les 8 essentiels) :**
1. **Un seul héros, retenue maximale** : 1er écran = compteur + prochain match + 1 ligne de record. Tout le reste se subordonne.
2. **Le compteur = le score bug** : typo géante condensée/variable, plus fort contraste, sur barre **solide** ; `tabular-nums` + `clamp(72px,18vw,240px)` + `line-height:.95` → jamais de reflow (les 2 maquettes appliquent `tabular-nums`).
3. **Reveal cinématique au load** (count-up 0→975, ease-out quartic ~3 s) **puis n'animer que le delta** (975→976, ~800 ms, expand-pulse-settle).
4. **Fabriquer une vie continue — notre problème n°1** (le nombre bouge rarement) : point doré pulsé, « vérifié il y a X », shimmer doré lent sur le nombre, **et un vrai sous-compte à rebours "prochain match dans HH:MM:SS"** qui tique toujours. **Jamais** d'incrément à la seconde simulé.
5. **Toujours afficher courant / cible / % ensemble** (975 / 1000 / 97,5 %) + barre ou anneau avec lueur de bord mobile + `transition:width` ; jalons de buts comme marqueurs (récit, pas jauge).
6. **Pastille 3 états + sémantique couleur réservée** : or "LIVE" (in-play) / gris "NEXT" / "OFF-SEASON".
7. **Lumière = mouvement, pas les meubles** : gradients qui dérivent + balayage ; **charcoal chaud, pas `#000` pur**, pour que l'or paraisse métallique (gradient directionnel + sweep sur "1000").
8. **Records en plaques + système qui scale au social** : verrouiller compteur + cartes news + images de partage dans un même template (ratios wide/carré/tall), mobile-first. RTL arabe : miroiter le sens de remplissage de la barre, garder les chiffres en LTR.

**Tokens repérés en conditions réelles (point de départ Phase 2) :** `--bg:#050607` ou charcoal chaud ; or `#f0d48b` / métallique `#C8A24B` ; lueur `box-shadow:0 0 16px rgba(or,.65)` ; relief `text-shadow:0 8px 36px rgba(0,0,0,.4)` ; compteur `clamp(72px,18vw,240px); font-weight:700; tabular-nums; line-height:.95`. Toute animation sous `prefers-reduced-motion`.

---

## 10. Deux directions visuelles (maquettes hero livrées)

Registre commun retenu avec Omar : **broadcast premium / live** · hero **hybride** (compteur dominant + CR7 cadré, pas de photo plein écran). Fichiers ouvrables au double-clic :

### Direction A — « Évolution Or/Noir » → `design/mockups/direction-A-evolution.html`
- On **garde l'ADN or/noir** (reconnaissance + SEO + cohérence marque) mais on le pousse en cinématique : halos dorés, grain, profondeur, compteur géant en serif **Fraunces** (gravité « grandeur »), UI en **Archivo**.
- Compteur `975 / 1000` en `tabular-nums`, barre de progression dorée, ruban records discret, panneau CR7 cadré à droite, bandeau « Next ▸ Portugal v Uzbekistan ».
- **Risque faible**, continuité de marque. Le plus sûr.

### Direction B — « Rupture / Scoreboard » → `design/mockups/direction-B-rupture.html`
- **Nouvelle identité** : on quitte l'or pour une ambiance **broadcast nocturne** — encre profonde + platine + accent rouge « signal ». Compteur = **tableau d'affichage LED** (digits mono DM Mono, lueur rouge), titre **Bricolage Grotesque**, ticker de records défilant, panneau CR7 en duotone.
- Plus audacieux, plus « événement TV », plus ownable. **Risque** : on perd la reconnaissance or/noir et le rouge demande de la rigueur (contraste, fatigue visuelle).

> ⚠️ Les maquettes n'ont **pas pu être capturées automatiquement** (pas de navigateur dans le sandbox WSL). Elles sont autonomes : **ouvre-les directement dans ton navigateur** (`to1000\design\mockups\`). Valeurs 975/25 en dur = snapshot ; le vrai site lira `stats.json`.

---

## 11. Outillage recommandé (recherche agent — décision-ready)

> Signal majeur de la recherche : étude **Snyk *ToxicSkills* (fév. 2026)** — ~36 % des skills communautaires contiennent des techniques d'injection de prompt, 76 payloads malveillants confirmés en marketplace. **Règle : privilégier le first-party (Anthropic, Vercel, GreenSock) et les skills « instructions seules » ; lire tout `SKILL.md` + scripts `.py`/`.sh`/`install.sh` avant d'activer un skill communautaire. Ne jamais pointer un MCP qui pilote un navigateur vers une URL non fiable.** Décision d'installation = Omar (accès + risque supply-chain).

**À installer — 3 skills first-party, vérifiés sûrs (via `/plugin`, PAS `npx skills add` qui est un CLI tiers Vercel) :**
1. **GSAP Official AI Skills** — `/plugin marketplace add greensock/gsap-skills` puis `/plugin`. Motion/ScrollTrigger pour le compteur et les reveals. Instructions seules, **confiance maximale**, CDN (no build). ✅ idéal stack statique.
2. **Vercel `web-design-guidelines`** — `/plugin marketplace add vercel-labs/agent-skills` puis `/plugin` (sélectionner uniquement `web-design-guidelines`, pas les `react-*`). Audit a11y/UX framework-agnostic. First-party MIT. *Caveat : fetch un ruleset live (URL GitHub Vercel, source fiable mais non pinnée).*
3. **Anthropic `theme-factory`** — `/plugin marketplace add anthropics/skills` puis `/plugin`. Le plus proche d'un helper **design-tokens** first-party. Instructions seules, **risque nul** (Apache-2.0, audits Snyk/Socket OK).

**❌ Désormais déconseillé — claude-seo** (AgriciDaniel) : après vérif, mono-mainteneur, `install.sh` lance `pip install`, télécharge Chromium en silence et copie hooks/scripts dans `~/.claude/` ; réputation tracée au blog de l'auteur (pas de revue indépendante) = profil exact flaggé par Snyk. **Et** redondant : le SEO `NewsArticle`/hreflang du site est déjà excellent (cf. §2bis). Le risque n'achète plus rien → **skip**.

**À utiliser en code direct (pas de MCP) :**
- **sharp** (npm) pour les images : le site **ship déjà du WebP** (vérifié par l'agent), donc le gain restant = **générer l'AVIF** (hero/era/banner) + **les WebP manquants** (`cr7-alnassr.jpg`, `cr7-alnassr-alt.jpg`). Script one-off ; ⚠️ ajoute `sharp` en dép. dev (la prod n'a pas de build).
- **CSS logical properties** (`margin-inline`, `inset-inline`) + `dir="rtl"` pour le RTL — zéro dépendance, mieux qu'installer rtlcss (qui exige un build).
- **Chart.js / D3** écrits directement pour la dataviz (timeline buts, comparaisons). ⚠️ **Éviter `@antv/mcp-server-chart`** (envoie les données à un backend Alipay par défaut).
- Perf : run **`@lhci/cli`** / scripts **axe-core** via le Playwright MCP déjà présent ; sinon **pagespeed-insights-mcp** (audite l'URL live, pas de Chrome local).

**À éviter :** `web-artifacts-builder` (impose React+Vite+Tailwind), `UI/UX Pro Max` (pattern script+input flaggé par Snyk, redondant avec `frontend-design`), packs 3D/WebGL (hostiles au Lighthouse), wrappers MCP 2-3 étoiles.

---

## 12. Recommandation & prochaine étape

- **Reco de direction** : si l'objectif business prime (SEO, reconnaissance, risque bas), **A**. Si l'objectif est de marquer les esprits / repositionner « événement live », **B** — quitte à garder une touche dorée comme accent secondaire. Une **voie médiane** est possible (structure scoreboard de B + chaleur dorée de A) si tu hésites.
- **STOP — j'attends ton arbitrage** sur : (1) direction A vs B (vs hybride A+B), (2) Next.js garder/supprimer, (3) particules garder/alléger, (4) feu vert pour installer les skills §11.
- **Ensuite seulement** : Phase 2 (design system / tokens dans `DESIGN_SYSTEM.md`), puis Phase 3 (implémentation en branche `redesign/*`, une page à la fois, contrat de données intact).

---

_Aucune modification du site de prod n'a été faite. Maquettes et ce document sont des artefacts d'exploration (dossier `design/`, racine), non déployés._
