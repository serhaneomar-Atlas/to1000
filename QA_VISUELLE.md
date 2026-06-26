# QA VISUELLE — refonte ESTÁDIO (pour CD / Cowork)

> Omar autorise **Chrome / computer-use**. Claude Code (WSL) ne peut pas voir le rendu
> (chromium installé mais libs système manquantes + pas de sudo). Merci à CD de faire
> cette passe à l'œil sur **https://to1000.com** et de noter chaque souci dans `WORKLOG.md`
> → Claude Code corrige ensuite.
>
> Méthode : 1 onglet desktop (~1280px) + 1 onglet mobile (DevTools, **iPhone ~390px**).
> Pour chaque point : OK / KO + capture si KO.

## 1. Accueil `/` (desktop)
- [ ] **Polices chargées** : le grand compteur est en **Anton** (gros, condensé), pas une police système.
- [ ] **Hero** : Ronaldo (Siuu) détouré, pas de carré/halo moche autour ; le **compteur 975/1000** juste en dessous ; ligne **« THE G.O.A.T.? »** avec le « ? » qui pulse.
- [ ] **Compteur live** = 975, barre ~97,5 %.
- [ ] **Nav** : « Compteur · Tous les buts · Parcours · Coupe du Monde · Stats · News » lisibles ; **« Tous les buts »** présent.
- [ ] **Prochain match** : drapeaux **Colombie 🇨🇴 / Portugal 🇵🇹** ronds et nets (pas « CO »/« PT »).
- [ ] **Section News** (bas) : cartes avec photo + résumé + source ; clic → ouvre **notre page** `/news/...` (pas la source directement).
- [ ] **Sélecteur de langue** FR/EN/ES/AR change tout (compteur + news inclus) ; **AR** bascule en RTL sans casser.

## 2. Accueil `/` (mobile ~390px) — **point critique signalé par Omar**
- [ ] **Menu hamburger (☰)** en haut à droite → l'ouvrir affiche toutes les sections + « Tous les buts ».
- [ ] Le **compteur + Siuu** tiennent à l'écran, lisibles, sans débordement horizontal.
- [ ] « THE G.O.A.T.? » lisible, pas coupé.

## 3. Page News `/news`
- [ ] Design ESTÁDIO (sombre, doré `#f2c14e`, Anton/Oswald).
- [ ] **Filtres** : Tout / CR7, sélecteur par source, recherche → la grille et le compteur réagissent.
- [ ] **Aucun sport hors-foot** (pas de surf/tennis/rugby).
- [ ] Clic sur une carte → page article interne (pas la source).

## 4. Page article `/news/{id}` (cliquer une news)
- [ ] Thème **ESTÁDIO** (plus l'ancien or/noir).
- [ ] Résumé lisible ; **source = lien discret** (« 📎 Source originale ») en secondaire.
- [ ] Section **« À lire aussi »** = autres articles de notre site (cartes cliquables).

## 5. Base des buts `/goals`
- [ ] Thème **ESTÁDIO** (tableau, filtres, en-têtes en Anton/Oswald).
- [ ] **Filtres** (club, type, recherche, tri) fonctionnent.
- [ ] **Clic sur un but** → modal vidéo : pour un but ≤964, lien vers la compilation au bon timestamp ; pour un but récent, bouton **« Chercher sur YouTube »**.
- [ ] Bandeau « base / total live » cohérent.

## 6. Dashboard `/dashboard.html`
- [ ] KPIs (buts, news, sources, pages) + graphiques (doughnut 1000ᵉ, courbes) s'affichent.
- [ ] Panneau **Trafic** = « à connecter » (normal tant que GA4 n'est pas branché).
- [ ] Santé SEO + journal marketing visibles.

## Points de vigilance (risques connus du re-skin)
- **Anton trop massif** sur des titres longs ou des libellés → noter si illisible/écrasé.
- **Contraste** : doré sur fond clair, ou texte sombre resté sur fond sombre.
- **Drapeaux** flagcdn qui ne chargent pas (réseau).
- **Duotone Siuu** trop fantôme ou trop présent.
- **RTL arabe** : flèches/alignements inversés correctement.

---
_À remplir par CD, puis Claude Code corrige les KO._
