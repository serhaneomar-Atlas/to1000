# STYLE_GUIDE — Voix, ton, SEO, marque

## Voix
- **Passionnée mais factuelle.** On vibre, on n'invente pas.
- Tutoiement permis dans les news courtes / réseaux sociaux. Vouvoiement dans les long format.
- Phrases courtes. Active voice. Verbes forts.
- ❌ "Il convient de noter que..." / ✅ "Note bien :"
- ❌ "Ronaldo a réalisé une performance remarquable" / ✅ "Ronaldo a marqué deux fois, dont un coup-franc à 30 mètres"

## Ton selon le contexte
- **CR7 milestones** → célébration mesurée. Pas de fanboying gênant.
- **Maroc** → fierté, encouragement, fraternité. Page Maroc est un point de ralliement.
- **Portugal** → ferveur lusophone, histoire (Eusébio, Figo, CR7).
- **Foot général** → neutre journalistique. On rapporte, on n'éditorialise pas sauf rubrique "Analyse".
- **Polémiques (VAR, arbitrage, transferts douteux)** → présenter les deux côtés. Pas de prise de position.

## Règles SEO non-négociables

### Méta tags par page
- `<title>` ≤ 60 caractères, mot-clé en tête.
- `<meta name="description">` 140-160 caractères, accrocheur, comporte le mot-clé.
- `<meta name="keywords">` 8-15 mots-clés (Google s'en fout mais Bing/Yandex toujours).
- `<link rel="canonical">` toujours.
- `hreflang` pour chaque langue disponible + `x-default`.
- OG et Twitter Card complets (image 1200×630 minimum).

### Structure
- `<h1>` unique par page, contient le mot-clé principal.
- `<h2>` pour les sections. `<h3>` pour sous-sections. Pas de saut de niveau.
- Premier paragraphe : 50-80 mots, répond à la question implicite du titre.
- Liens internes : ≥ 3 par page vers d'autres pages du site.

### JSON-LD
Toujours au moins un type :
- News rapide : `NewsArticle`
- Long format : `Article`
- Match : `SportsEvent`
- Joueur : `Person`
- Page FAQ : `FAQPage`

### Performances
- Images en WebP (et PNG fallback). Lazy load (`loading="lazy"`) sauf hero.
- Pas de framework JS lourd. JS pur ou Alpine.js si vraiment besoin de reactivité.
- Inline le CSS critique. Le reste défer.

## Mots-clés cibles (top 30 à viser)

### Tier 1 — high volume, high relevance
1. Cristiano Ronaldo 1000 goals
2. CR7 goal counter
3. Coupe du monde 2026 Maroc
4. Coupe du monde 2026 Portugal
5. Calendrier Coupe du Monde 2026
6. Ronaldo career goals total
7. World Cup 2026 schedule
8. Lions de l'Atlas calendrier
9. Maroc Brésil Coupe du monde
10. Portugal World Cup squad 2026

### Tier 2 — long tail
11. when will Ronaldo score 1000
12. CR7 last goal
13. Maroc groupe C Coupe du monde
14. Portugal groupe K
15. Ronaldo sixth World Cup
16. Lions de l'Atlas joueurs
17. Achraf Hakimi WC 2026
18. Walid Regragui sélection
19. Bruno Fernandes Portugal
20. CR7 Saudi Pro League champion

### Tier 3 — événementiel à pousser le jour J
21. Ronaldo vs DR Congo
22. Maroc vs Brésil pronostic
23. Portugal Colombie résumé
24. Maroc Écosse score
25. Ronaldo but record
26. WC 2026 opening ceremony
27. Mexico South Africa June 11
28. Bracket Coupe du monde 2026
29. Lions de l'Atlas Achraf
30. CR7 1000eme but date

## Charte graphique

### Couleurs
- Background : `#060606` (noir profond)
- Texte principal : `#f5f5f5`
- Accent principal : `#D4AF37` / `#ffd700` (or CR7)
- Vert (Maroc) : `#006233` + `#C1272D` (drapeau)
- Vert/rouge (Portugal) : `#006600` + `#FF0000`
- Brésil : `#FEDF00` + `#009C3B` (page Maroc opposants)

### Typographie
- System UI stack : `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- Pas de webfonts custom (perf).
- Tailles fluides : `clamp(1rem, 2vw, 1.5rem)` pour le body.

### Composants réutilisables
- `.live-dot` : point rouge pulsant pour "LIVE"
- `.countdown` : bloc grand chiffre + unité en dessous
- `.flag-pill` : pastille avec emoji drapeau + nom équipe
- `.article-card` : carte article standard (cf. blog/index.html existant)

## Marque CR7 — règles légales

CR7 est une marque déposée de Cristiano Ronaldo. Donc :
- ❌ Logo "CR7" stylisé dans le branding du site
- ❌ "CR7™" dans nos textes (faux + abusif)
- ❌ Vente de produits avec branding CR7
- ✅ Mentionner "CR7" dans le contenu éditorial (fair use)
- ✅ Photos de presse avec crédit
- ✅ Disclaimer "fan site non officiel" visible dans le footer

## Maroc — sensibilités

- ✅ "Lions de l'Atlas" pour la sélection
- ✅ "Maroc" plutôt que "Maghreb" quand on parle de cette équipe
- ✅ Encouragement explicite OK ("Allez les Lions !", "Dima Maghrib")
- ⚠️ Sahara occidental : non. Sport seulement. Si débat politique en commentaire → modération.
- ⚠️ Pas de comparaison déplaisante avec d'autres sélections africaines (Algérie, Tunisie, Sénégal). Respect.

## Portugal — sensibilités

- ✅ "A Seleção", "Os Navegadores", "Portugal"
- ✅ Hommages à Eusébio (1942-2014), Figo, CR7
- ⚠️ Pas de rivalité tribale Brésil/Portugal en commentaires (modération)

## Disclaimer footer (à inclure partout)

```html
<footer class="footer">
  <p>To1000.com est un site de fans <strong>non officiel</strong>, sans affiliation avec Cristiano Ronaldo, la FIFA, l'UEFA, la FRMF, la FPF ou aucun club mentionné. Les marques et logos appartiennent à leurs propriétaires respectifs. Les statistiques sont vérifiées via ESPN, fotmob et les sites officiels. © 2026</p>
</footer>
```
