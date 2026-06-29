# Publicité — to1000.com (ESTÁDIO)

Intégration pub **discrète et premium**, anti-CLS, branchable régie tierce.
Par défaut **tout est OFF** : les espaces sont réservés (0 décalage) mais aucun
script tiers n'est chargé tant que le go-live n'est pas décidé.

## 1. Fichiers
| Fichier            | Rôle                                                        |
|--------------------|-------------------------------------------------------------|
| `public/ads.css`   | Styles des emplacements (formats IAB, sticky, placeholders) |
| `public/ads.js`    | Init : flag global, lazy-load, sticky, hook AdSense         |

## 2. Carte des emplacements (slots à intégrer dans les pages)
| Page                  | Slot                | Format(s)                  | unit-id (à remplir) |
|-----------------------|---------------------|----------------------------|---------------------|
| `index.html` (#data)  | `ad-leaderboard`    | 320x100 / 728x90 / 970x250 | `0000000000`        |
| `index.html` (mobile) | `ad-sticky`         | 320x50 (dismissable)       | `0000000001`        |
| `news.html`           | `ad-infeed` ×N      | fluid native (tous les 6)  | `0000000002`        |
| article (`/news/*`)   | `ad-slot` in-article| 300x250 / 336x280          | `0000000003`        |

**Règle d'or** : jamais de slot dans le hero ni *entre* deux `section.frame`
(scroll-snap de la home). Sur la home, la pub vit dans la frame Stats/News +
sticky mobile.

## 3. Activer la pub (go-live)
Avant le chargement de `ads.js` (ou en tête de `ads.js`) :
```js
window.ADS_ENABLED   = true;
window.ADS_NETWORK   = 'adsense';
window.ADSENSE_CLIENT = 'ca-pub-XXXXXXXXXXXXXXXX'; // ID éditeur AdSense
```
Puis renseigner chaque `data-ad-unit-id="..."` avec l'ID de bloc AdSense. Tant
qu'`ADS_ENABLED=false` ou qu'`ADSENSE_CLIENT` est vide, **aucun** appel réseau
tiers n'est fait.

## 4. Brancher Google AdSense
1. Créer le compte AdSense, faire valider le domaine `to1000.com`.
2. `ads.js` injecte automatiquement la lib au premier slot visible (lazy → bon LCP) — ne pas ajouter le script global dans le `<head>`.
3. Créer 4 blocs (Display responsive + In-feed) et coller leurs `data-ad-slot` dans les `data-ad-unit-id`.
4. **`ads.txt` obligatoire** : déposer `public/ads.txt` avec la ligne fournie par AdSense (`google.com, pub-XXXX, DIRECT, f08c47fec0942fa0`), sinon revenus bloqués.

## 5. Bonnes pratiques (densité, RGPD, SEO/CLS)
- **Densité** : 1 leaderboard + 1 sticky sur la home ; 1 in-feed / 6 cartes ; 1 MPU / article. Pas de pop-up, pas d'interstitiel, pas d'auto-refresh.
- **CLS = 0** : chaque slot a une `min-height` fixe par breakpoint. Ne jamais la retirer.
- **Viewability** : lazy-load via IntersectionObserver (`rootMargin:320px`).
- **RGPD / UE** : AdSense exige une CMP certifiée IAB TCF v2 en EEA/UK. Audience FR/EN/ES/AR = forte UE. **Ne pas activer `ADS_ENABLED=true` sans CMP** (risque suspension). Le flag OFF par défaut protège.
- **SEO** : pas de pub au-dessus du H1, pas dans le hero, label « Publicité » discret obligatoire (policy + UX).

## 6. Désactiver rapidement
`window.ADS_ENABLED = false;` (ou retirer `ads.js`) → `<html class="ads-off">` masque tout proprement.

## 7. Statut
- ✅ Fondation livrée : `ads.css`, `ads.js`, ce doc.
- ⏳ À intégrer dans les pages (slots HTML) : home (#data + sticky), news.html (in-feed via le rendu JS), template article (`scripts/news_to_html.py`). Voir les emplacements §2 — à activer quand le trafic justifie la pub.
