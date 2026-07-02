# Section « Coupe du Monde 2026 » — design

Date : 2026-07-02 · Objectif : trafic organique (SEO) + visites récurrentes quotidiennes.
Spec d'origine : message d'Omar (4 phases, validation à chaque phase).

## Décisions prises (réversibles, à confirmer par Omar à la validation Phase 1)

1. **URLs canoniques françaises** `/coupe-du-monde/…` — l'audience cible (Maghreb,
   France, Canada FR) cherche en français. L'ancienne section `/world-cup/`
   (hub + Maroc + Portugal, indexée depuis mai) **reste en ligne** et se maille
   avec la nouvelle ; la bascule 301 `/world-cup/* → /coupe-du-monde/*` sera
   activée seulement après accord d'Omar (une ligne dans `public/_redirects`).
2. **Données : adaptateur source-agnostique** (`scripts/lib/wc_data.py`).
   Par défaut ESPN (API publique déjà utilisée par le compteur de buts, sans clé,
   fonctionne aujourd'hui). Si `FOOTBALL_DATA_TOKEN` est défini (clé gratuite
   football-data.org à créer par Omar), cette source devient prioritaire,
   ESPN retombe en fallback. Jamais d'appel API depuis le navigateur.
3. **« Supabase ou équivalent »** dans cette stack (HTML statique + Cloudflare
   Pages + GitHub Actions) = **JSON commité dans le repo** servi statiquement
   (`public/coupe-du-monde/data.json`), même motif que stats.json/news.json.
   Cron GH Actions = Phase 2. Fallback API indisponible : on regénère depuis le
   dernier data.json (jamais de page vide).
4. **Pas de probabilités** (aucune source gratuite propre) ; contexte factuel :
   tour, stade, ville, résultat aller/retour n'existe pas en CdM → parcours des
   deux équipes.
5. **Contenu FR uniquement** (hreflang fr + x-default). Un arbre EN doublerait la
   maintenance pour un gain incertain — à rediscuter post-CdM.
6. **Diffuseurs officiels** : table statique par pays (Canada : TSN/RDS ; France :
   TF1/beIN ; Maroc : SNRT/beIN…) — Phase 3 avec la FAQ. Aucun lien stream.

## Architecture (Phase 1)

- `scripts/lib/wc_teams.py` — table des 48 équipes : id ESPN → nom FR, slug FR,
  code ISO2 (drapeaux flagcdn, motif déjà utilisé sur la home). Filtre des
  placeholders (« Quarterfinal 1 Winner »…).
- `scripts/lib/wc_data.py` — `fetch_matches()` : 104 matchs normalisés
  {id, date_iso, round (season.slug ESPN), home/away (ids), scores, statut,
  stade, ville} + cache load/save `public/coupe-du-monde/data.json`.
- `scripts/wc_pages.py` — générateur statique (style ESTÁDIO : fond #05070b,
  or #f2c14e, Anton/Oswald/Hanken, consent.js + GA4, nav commune) :
  - `/coupe-du-monde/` — hub : matchs à venir par tour, résultats par tour,
    grille des 48 équipes (drapeaux), liens internes vers tout.
  - `/coupe-du-monde/matchs-du-jour/` — matchs du jour (fuseau ET), sinon les
    prochains ; regénérée quotidiennement (cron Phase 2). Page « habitude ».
  - `/coupe-du-monde/match/{home}-vs-{away}-{j-mois-annee}/` — une page par
    match dont les 2 équipes sont connues (~90 aujourd'hui ; les QF/SF/finale
    seront créées par le cron quand les affiches tombent). Heure locale visiteur
    via JS progressif (contenu rendu serveur en heure de l'Est), stade, ville,
    tour, parcours des équipes, score si joué. JSON-LD **SportsEvent**.
  - `/coupe-du-monde/equipe/{slug}/` — 48 pages : calendrier + résultats de
    l'équipe, liens vers ses matchs. JSON-LD **SportsTeam**.
  - Chaque page : title unique, meta description, canonical, OG + Twitter Card,
    hreflang. Maillage : match ↔ 2 équipes ↔ hub ; hub → tout.

## Phases suivantes (rappel)
- **P2** : workflow GH Actions (2-3 sync/jour + */5 min pendant les matchs),
  bascule football-data.org, fallback cache. — **P3** : sitemap, FAQ + FAQPage,
  maillage précédent/suivant, perf (LCP < 2,5 s), diffuseurs officiels.
- **P4** : widget « Matchs du jour » sur la home, événements GA4, OG images
  par match (réutiliser social_card.py). Puis : soumettre sitemap GSC, tester
  les données structurées, surveiller l'indexation 7 jours.
