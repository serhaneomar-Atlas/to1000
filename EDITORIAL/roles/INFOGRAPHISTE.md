# Infographiste

## Mission
Visuel cohérent à travers le site : OG cards (1200×630), images hero, infographies stats, bracket WC, drapeaux.

## Ressources existantes
- `public/images/_masters/` — sources haute résolution
- `public/images/cr7-*.{jpg,webp}` — hero CR7
- `public/og-image.png` — fallback OG par défaut
- `public/images/logo-*.svg` — logos clubs (Sporting, etc.)

## OG card par page importante
Chaque page de niveau 1 (home, hub WC, Maroc, Portugal, goals, blog index) doit avoir sa propre OG card. Sinon → utilise `og-image.png`.

Format :
- 1200 × 630 px
- < 200 KB (compressé)
- Texte 60+ pt minimum (lisible en preview sociale)
- Branding to1000.com en bas-droite (logo + URL)

## Prompt pour génération AI (Midjourney / Imagen / DALL-E)

Voir `templates/og-image-prompt.md`.

Base :
> "Wide cinematic shot, dark moody atmosphere, deep black background with gold accent lighting at 35deg from top-right, hero subject [TEAM/PLAYER] centered, slight motion blur from action, no text overlay (will be added in post), 1200×630 aspect ratio, photo-realistic style"

## Alt-text — règles
- Décrit la scène, pas le marketing
- ❌ "Le meilleur joueur du monde"
- ✅ "Cristiano Ronaldo célébrant un but avec Al Nassr face à Damac, mai 2026"
- Si décoratif pur : `alt=""` (laisser vide, pas omettre)

## Drapeaux
Utiliser emoji Unicode : 🇲🇦 🇵🇹 🇧🇷 🇫🇷 🇪🇸 — taille fixe via CSS.
Pour drapeau plus grand : SVG depuis https://flagicons.lipis.dev/ (CC0).

## Bracket WC 2026 (à créer une fois)
SVG 1600×900, fond noir, accents or, 4 tiers : 1/16 → 1/8 → 1/4 → 1/2 → Finale.
À placer dans `/world-cup/bracket.html` avec mise à jour scriptée des résultats au fur et à mesure.

## Style cards de match
Background : dégradé bicolore drapeaux des deux équipes (Portugal vert + drapeau adversaire).
Format : 1080×1080 (carré Instagram) + 1200×630 (Twitter/Facebook).
Inclure : date, heure (TZ Paris ou Maroc), score si fini, scorers (mini avatar).

## Photos copyright
- Photos officielles FRMF / FPF : usage éditorial OK avec crédit
- Photos clubs : crédit + lien source
- Photos Getty / AP : nécessite licence (ne pas utiliser)
- Photos persos joueurs (X, IG) : éviter sauf reprise factuelle avec lien
