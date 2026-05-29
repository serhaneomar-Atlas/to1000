# EDITORIAL_CALENDAR — Plan de contenu

Mise à jour : 2026-05-28
Prochaine review : 2026-06-04 (Rédacteur en chef)

## Vue d'ensemble — 8 prochaines semaines

```
Sem 22 (26 mai – 1er juin)  → BUILD-UP WC : pages hub + Portugal + Maroc, polls, comments
Sem 23 (2 – 8 juin)         → AMICAUX : Portugal vs Chili (6/6), Portugal vs Nigéria (10/6)
Sem 24 (9 – 15 juin)        → CDM KICK-OFF : Mexico-RSA (11/6), Maroc-Brésil (12/6)
Sem 25 (16 – 22 juin)       → PHASE DE GROUPES J2 : Portugal-DRC (17/6), Maroc-Écosse (18/6), Portugal-Uzbekistan (23/6)
Sem 26 (23 – 29 juin)       → PHASE DE GROUPES J3 : Maroc-Haïti (23/6), Colombia-Portugal (27/6)
Sem 27 (30 juin – 6 juil)   → 16ÈMES (32→16)
Sem 28 (7 – 13 juil)        → 8ÈMES → QUARTS
Sem 29 (14 – 19 juil)       → DEMI + FINALE (19/7)
```

## Sem 22 — Cette semaine (action immédiate)

### Lundi 26 mai (✓ rétro)
- ✓ Sync stats quotidienne
- ✓ Aggrégation news 30 min

### Jeudi 28 mai (aujourd'hui)
- [ ] Publier hub `/world-cup/` (Claude — en cours)
- [ ] Publier `/world-cup/portugal/`
- [ ] Publier `/world-cup/maroc/` (FR + AR)
- [ ] Activer Firebase polls + comments
- [ ] Push live news ticker sur home
- [ ] Activer SEO HTML generator (news_to_html.py)

### Vendredi 29 mai
- [ ] Article : "Coupe du Monde 2026 — tout savoir : format, stades, dates clés" (1200 mots, blog)
- [ ] Article : "Les 26 Lions de l'Atlas pour la Coupe du Monde 2026" (squad annoncé entre 28 mai et 2 juin attendu — vérifier date officielle)
- [ ] Post X : countdown image "14 jours avant le coup d'envoi"

### Samedi 30 mai
- [ ] Article : "Portugal vs Maroc : qui a le meilleur tirage ?" (analyse 800 mots)
- [ ] Infographie : bracket complet WC 2026
- [ ] Poll #1 : "Quel pays va le plus loin ?" (Portugal, Maroc, Brésil, Argentine, France, Espagne, Allemagne, Autres)

### Dimanche 31 mai
- [ ] Article : "Top 5 candidats au Soulier d'Or de la WC 2026" (CR7, Mbappé, Haaland, Vinicius, Lautaro)
- [ ] Récap hebdo X/Telegram

## Sem 23 — Amicaux Portugal

### Vendredi 5 juin
- [ ] Preview Portugal vs Chili (J-1)
- [ ] Article : "Hakimi blessé ?" (à vérifier — placeholder)

### Samedi 6 juin (Portugal vs Chili, Jamor)
- [ ] Live tweet (X)
- [ ] Post-match : `playbooks/POST_MATCH.md` → article récap auto + édité
- [ ] Update stats CR7 si but

### Mercredi 10 juin (Portugal vs Nigéria, Leiria)
- [ ] Live tweet
- [ ] Post-match

## Sem 24 — Coup d'envoi

### Mercredi 10 juin
- [ ] Preview "WC 2026 J-1" — hub mis à jour avec all 48 équipes

### Jeudi 11 juin (J-day)
- [ ] Live home : countdown → 0 → "C'EST PARTI"
- [ ] Mexico vs Afrique du Sud (Estadio Azteca) — récap
- [ ] Ouverture cérémonie : article + photos
- [ ] Push notif (PWA) à tous les abonnés

### Vendredi 12 juin (00h heure Maroc / 23h locale = jeudi soir USA)
- [ ] **MAROC vs BRÉSIL** — gros gros sujet
  - Live blog dédié `/world-cup/maroc/live-bra-mar.html`
  - Polls réactions en direct
  - Section commentaires ouverte avant le coup d'envoi

### Mardi 17 juin
- [ ] **PORTUGAL vs DR CONGO** — gros sujet CR7
  - Live blog `/world-cup/portugal/live-por-cod.html`

## Idées en stock (pas encore datées)

Voir `state/pending_topics.json` pour le format machine-lisible.

- "CR7 vs Pelé : qui a le record du nombre de WC ?" → posté quand CR7 joue son 1er match WC 2026 = son 6ème
- "Coup-franc CR7 : le grand déclin des stats" → analyse data 2018-2026
- "Hakimi en Champions League : retour sur sa saison 2025-26 au PSG"
- "Les jeunes pousses marocaines à suivre" (Brahim Diaz, Ounahi, Bilal El Khannous…)
- "Anniversaire 5 ans depuis Maroc demi-finaliste 2022" (4 décembre 2027 — à programmer)

## Règle d'or

Si tu prends une idée du backlog → tu **dois** mettre à jour `state/pending_topics.json` (passer status à "in_progress" puis "published" avec URL).
