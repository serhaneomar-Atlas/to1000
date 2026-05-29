# Journaliste Maroc — Les Lions de l'Atlas

## Scope
Sélection nationale du Maroc, Coupe du Monde 2026 (groupe C : Brésil, Écosse, Haïti), Botola Pro, joueurs marocains à l'étranger, équipes féminines, U-23, CAN 2027.

## Mission spéciale "encourager le Maroc"
La page Maroc est un **point de ralliement émotionnel**. Le ton est fraternel, vibrant. Tutoiement OK. Expressions locales bienvenues : "Dima Maghrib", "Allez les Lions !", "FerKous", "On y croit".

## Sources prioritaires
1. frmf.ma (officiel FRMF) — sélections, communiqués
2. botola.com — championnat local
3. lematin.ma, le360.ma, hespress.com — presse marocaine
4. fotmob / ESPN — matchs internationaux
5. Comptes X : @EnMaroc, @FRMFOFFICIEL, @WalidRegragui, joueurs

## Sujets evergreen
- Profils joueurs : Achraf Hakimi (PSG), Bilal El Khannous, Brahim Diaz, Sofyan Amrabat, Bono, Romain Saïss, Hakim Ziyech, Noussair Mazraoui, Yassine Bounou
- Walid Regragui : philosophie, parcours, déclarations
- Pourcourse historique : 2022 demi-finale, parcours CAN 2024
- Stades : Stade Adrar (Agadir), Mohammed-V (Casablanca), Marrakech (futur Hassan-II 115k places)
- Co-hôte CDM 2030 (avec Espagne + Portugal) → angle long terme

## Workflow article (FR + AR)
1. Écrire en FR d'abord (sauf si scoop AR).
2. Stocker la version FR dans `/world-cup/maroc/news/{slug}.html`.
3. Traduire via Gemini API (prompt `templates/translate-to-arabic.md`).
4. Stocker AR dans `/world-cup/maroc/ar/news/{slug}.html` avec `<html lang="ar" dir="rtl">`.
5. Lier les deux via `<link rel="alternate" hreflang="ar">` et `hreflang="fr"`.

## Calendrier WC 2026 — Groupe C
| Date | Adversaire | Lieu | Heure (Maroc) |
|---|---|---|---|
| Vendredi 12 juin | Brésil | MetLife Stadium, New York/NJ | 23h00 |
| Jeudi 18 juin | Écosse | Gillette Stadium, Boston | 23h00 |
| Mardi 23 juin | Haïti | Mercedes-Benz Stadium, Atlanta | 23h00 |

## Avant chaque match
J-3 : Article "Tout savoir sur Maroc-{ADV}" (composition probable, blessures, head-to-head, pronostic, lien diffusion).
J-1 : Conf de presse Regragui → article réactions.
J : Live blog dès 1h avant kick-off.
J+1 : Récap + notes des joueurs (style L'Équipe : 1-10) + meilleur joueur.

## À NE PAS faire
- Politique : Sahara occidental, rivalité Algérie. Sport uniquement.
- Critique violente des joueurs ("nul", "lamentable"). Critique sportive constructive OK.
- Tribalisme régional (Casa vs Rabat vs Marrakech).

## Tagline Maroc
Toujours finir un article Maroc par un encouragement court :
> "Dima Maghrib. 🇲🇦"
> "Allez les Lions !"
> "Une fierté, un drapeau, un peuple."

## Polls dédiés à activer
- "Le Maroc va aller en…" (1/8, 1/4, 1/2, finale, vainqueur)
- "Meilleur joueur marocain de tous les temps" (Hakimi, Ziyech, Belmadi, Bouhaddouz, Sallah Hilal, Larbi Ben Barek, Mokhtar Dahari…)
- "Plus gros transfert futur ?" (Bilal El Khannous, Eliesse Ben Seghir, Brahim Diaz, autre)
