# DESIGN_BRIEF — Refonte visuelle complète de to1000.com

> Source de vérité unique pour la refonte. Tenu à jour par Claude Code, validé par Omar.
> Décision Omar (2026-06-23) : **refonte visuelle COMPLÈTE** (nouvelle identité possible, structure des pages repensable), précédée d'un **AUDIT**.

---

## 0. Pitch en une phrase

to1000.com = hub football général dont le **cœur émotionnel** est le compte à rebours du **1000e but de Cristiano Ronaldo** (actuellement 974/1000). Audience large maintenant → trafic prêt à exploser quand CR7 approche 1000.

---

## 1. État actuel (le point de départ honnête)

- **`public/index.html` = 4316 lignes**, tout en un seul fichier (HTML + CSS inline + JS inline). Maintenance pénible, c'est la dette n°1.
- Pages : `index.html` (hero + compteur + stats + next/last match + news), `goals.html` (base de tous les buts, 1253 lignes), `admin.html`, `analytics.html`.
- Thème **or/noir**, 4 langues **EN/FR/ES/AR** (AR en RTL), i18n maison via objets JS.
- Données live : `public/stats.json` (compteur, dernier but, prochain match) lu en JS avec animation + toast ; `public/news.json` (flux 50 items) ; contest via **Firebase** (Auth Google + Firestore).
- Stack prod : **HTML/CSS/JS statique** sur **Cloudflare Pages** (projet `to1000`). Un code **Next.js parallèle non déployé** existe (`app/`, `components/`, `lib/`) — sort à trancher.
- SEO très travaillé : JSON-LD (FAQ, WebSite, SoftwareApp), OG/Twitter, plein de mots-clés. **À NE PAS casser.**

---

## 2. Objectifs de la refonte

1. **Identité visuelle forte et mémorable** — le site doit « claquer » dès le hero, donner envie de revenir pour le compteur.
2. **Maintenabilité** — sortir du monolithe 4316 lignes : composants/partials, CSS séparé et tokenisé (design tokens), JS modulaire.
3. **Performance** — Lighthouse mobile ≥ 90 (LCP, CLS, JS bloquant). Le site doit tenir un pic de trafic.
4. **Responsive impeccable** — mobile-first, le compteur reste le héros sur petit écran.
5. **Accessibilité** — contraste AA, focus visibles, RTL arabe nickel, navigation clavier.
6. **Préserver l'acquis** : compteur live (`stats.json`), news, contest Firebase, SEO/JSON-LD, 4 langues.

---

## 3. Non-négociables (ne RIEN casser)

- Le compteur DOIT continuer à lire `stats.json` en live (champs : `goals`, `remaining`, `last_goal_*`, `last_match`, `next_match`, `last_updated`). Voir le JS actuel `fetchLiveStats()` dans `index.html`.
- `news.json` continue d'alimenter la section news (cap 50 items).
- Contest Firebase fonctionnel (projet `to1000-contest`).
- SEO : conserver/améliorer les JSON-LD, balises OG/Twitter, sitemap, IndexNow.
- 4 langues EN/FR/ES/AR avec RTL.
- **Marque & légal** : aucun branding **CR7™**, disclaimer « fan site non officiel » dans le footer.
- Déploiement reste Cloudflare Pages, dossier `public/` (Windows `deploy_now.bat` ou GH Actions).

---

## 4. Process imposé (avec superpowers)

**PHASE 1 — AUDIT (livrable avant tout code).** Produire `DESIGN_AUDIT.md` :
- Inventaire UI/UX page par page, captures, ce qui marche / ce qui cloche.
- Audit perf (Lighthouse), accessibilité (contrastes, RTL), responsive (points de rupture cassés).
- Analyse de la dette technique (monolithe, duplication, i18n).
- Benchmark : 3-5 sites de référence (compteurs/live sport, fan hubs) — quoi s'inspirer.
- **Sortie : 2-3 DIRECTIONS visuelles** (moodboard/maquette de hero par direction). → **STOP, validation Omar.**

**PHASE 2 — SYSTÈME DE DESIGN.** Une fois la direction choisie : design tokens (couleurs, typo, espacements, rayons, ombres), composants de base, grille, états (hover/focus/live/loading). Documenter dans `DESIGN_SYSTEM.md`.

**PHASE 3 — IMPLÉMENTATION** (en TDD/itératif, branche git dédiée `redesign/*`). Sortir le monolithe vers une structure maintenable SANS changer le contrat de données. Une page à la fois, en gardant le site déployable à chaque étape.

**PHASE 4 — QA.** Lighthouse, test 4 langues + RTL, test mobile réel, vérif compteur live + news + contest, vérif SEO (JSON-LD valides). Captures avant/après. → validation Omar avant merge `main`.

---

## 5. Décisions à remonter à Omar (queue dans HANDOFF.md)

- Choix de la direction visuelle (fin phase 1).
- Garde-t-on le code Next.js parallèle, ou refonte en statique pur ? (impacte toute l'archi)
- Tout changement de marque/nom/ton, ou tout ce qui touche aux comptes/clés/budget.

---

## 6. Définition de « terminé »

Refonte mergée sur `main`, déployée, Lighthouse mobile ≥ 90, 4 langues OK, compteur/news/contest live OK, SEO préservé, captures avant/après dans `WORKLOG.md`, et Omar a validé visuellement.
