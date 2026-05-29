# Playbook : Pre-WC build-up (J-14 → J-1)

Période : du 28 mai 2026 au 11 juin 2026.

## Objectif
Préparer le site pour absorber le pic de trafic WC (estimé ×5 à ×10 du trafic normal).

## Switch frequencies
À J-7 (5 juin) :
- news-sync.yml passe de `*/30` à `*/15`
- social-poster.yml passe de 3 à 6 posts/jour

## Contenu à publier (calendrier détaillé)

### Sem 22 (déjà en cours)
- [x] Hub WC `/world-cup/`
- [x] Page Portugal
- [x] Page Maroc bilingue
- [ ] Article : "WC 2026 : format à 48 équipes expliqué"
- [ ] Article : "Les 16 stades de la WC 2026 — guide complet"
- [ ] Infographie bracket vide

### Sem 23 (2-8 juin)
- [ ] Liste 26 squads (un article par équipe favori + Maroc + Portugal)
- [ ] Preview groupe A à L (12 articles brefs, 1/jour)
- [ ] Poll "Vainqueur prédit"
- [ ] Article CR7 : "À 41 ans, sa 6ème WC : ce qui attend Ronaldo"

### Sem 24 (9-11 juin)
- [ ] Article : "Les 10 joueurs à suivre absolument"
- [ ] Article : "Tout ce qu'il faut savoir avant le coup d'envoi"
- [ ] Live page : Mexico vs RSA (11/6)
- [ ] Cérémonie ouverture × 3 (Mexico, Toronto, LA) — récap

## Optimisations techniques à faire avant J-day
- [ ] Tester performance home + hub WC sous Lighthouse → score ≥ 90
- [ ] Préchauffer le CDN Cloudflare (visite manuelle de chaque page principale)
- [ ] Vérifier que le service worker (PWA) cache bien les pages WC
- [ ] Backup news.json + stats.json (le cas où)
- [ ] Tester push notif sur mobile + desktop
- [ ] Préparer 5 templates OG cards (Brésil, Argentine, France, Espagne, Portugal/Maroc)

## SEO buildup
- Pinger IndexNow tous les jours avec les nouvelles pages WC
- Soumettre `/sitemap.xml` à Google Search Console manuellement
- Demander indexation des 10 pages les plus importantes via Search Console "Inspector"
- Internal linking massif : chaque page WC link vers hub + bracket + page équipe

## Coordination Maroc spéciale
J-3 du premier match Maroc (= 9 juin) :
- [ ] Article featured "Comment supporter le Maroc depuis France/Belgique/Pays-Bas/UK"
- [ ] Section comments ouverte avec post épinglé "Allez les Lions !"
- [ ] Live blog créé `/world-cup/maroc/live-mar-bra.html`, encore vide
- [ ] Image OG dédiée

## Monitoring J-day
Setup à valider la veille :
- Cloudflare Analytics ouvert sur 2 onglets
- Google Search Console alertes activées
- Telegram canal admin actif pour erreurs
- Test push notif J-1 fait sur ton mobile
