# KAIZEN — Amélioration continue de to1000.com

> "改善" : un petit pas, chaque jour, sans relâche.
> Ce fichier liste les améliorations en cours et planifiées.
> À relire en début de chaque session de pilotage hebdomadaire.

## Principe
Chaque semaine, on regarde :
1. **Quoi mesurer** — métriques de la semaine passée
2. **Quoi corriger** — bugs / friction utilisateur
3. **Quoi tenter** — 1 expérimentation max par semaine

Pas de big-bang. Petites livraisons. Mesures.

---

## Métriques hebdomadaires (dimanche soir)

À tracker dans une feuille de calcul ou Google Sheets :

| Métrique | Source | Objectif S1 (juin 2026) | Objectif S4 (post-WC) |
|---|---|---|---|
| Visiteurs uniques / jour | Google Analytics | 500 | 5 000 |
| Pages vues / jour | GA | 1 500 | 25 000 |
| Sessions WC hub | GA segmenté URL | 100 | 1 500 |
| Articles publiés / sem | `published_log.jsonl` | 15 (auto+manuel) | 25 |
| News indexées Google | Search Console | 30 | 200 |
| Followers @To1000com X | manuel | +50 | +500 |
| Comments par jour | Firestore | 5 | 50 |
| Votes polls par jour | Firestore | 20 | 200 |

---

## Backlog priorisé (vague 2 — après le push initial)

### Cette semaine
- [ ] **Bannière WC sur la home** — pousser le trafic depuis index.html vers /world-cup/
- [ ] **Vérifier sentinel I/J groups** — placeholder dans wc.json à corriger après confirmation FIFA
- [ ] **OG cards customs** pour /world-cup/, /portugal/, /maroc/ (4 images 1200×630)
- [ ] **Tester le journaliste IA** en local 1 fois avant push (lance `python scripts/claude_journalist.py` avec ANTHROPIC_API_KEY local)
- [ ] **Activer telegram_poster.py** en sortant du dry-run (mettre le `.env`)

### Semaine 23 (2-8 juin)
- [ ] Bracket WC SVG complet à `/world-cup/bracket.html`
- [ ] Live blog Maroc-Brésil template prêt
- [ ] X auto-posting : décider Buffer (~6€/mois) vs computer-use
- [ ] Email digest hebdo aux abonnés (Newsletter via Resend ou Buttondown ~9€/mois)
- [ ] Page "Coupe du Monde — résultats live" à mettre à jour quotidiennement

### Semaine 24+ (CDM en cours)
- [ ] News-sync passe à `*/15 min` au lieu de `*/30`
- [ ] AI-editorial passe à 5×/jour au lieu de 3
- [ ] Goal watcher actif pendant tous les matchs Maroc/Portugal/Al Nassr
- [ ] Push notifs PWA testées et activées

### Long terme (post-WC)
- [ ] Refonte mobile UX si métriques montrent friction
- [ ] Ajout d'une langue (EN ou ES) sur tout le site
- [ ] Monétisation light (Google AdSense ou affiliation paris OK ? — Omar à valider)
- [ ] Communauté Discord/Telegram dédiée

---

## Backlog "améliorations IA"

### Court terme
- [ ] **Diversifier les sujets** — modifier `claude_journalist.py` pour ne pas toujours prendre le top score (alterner CR7/Maroc/Portugal/foot)
- [ ] **Éviter les doublons sémantiques** — comparaison cosinus entre nouvelles dépêches et articles déjà publiés
- [ ] **Multi-lang** — générer EN + FR pour chaque article au lieu de FR seul
- [ ] **Cite-checker** — agent secondaire qui vérifie que les chiffres cités dans l'article sont cohérents avec les sources

### Moyen terme
- [ ] **Image AI-générée par article** via DALL-E ou Imagen API (~0,02€/img)
- [ ] **Audio TTS** des articles (ElevenLabs, ~0,10€/article) → mode "écoute"
- [ ] **Newsletter auto** : top 5 articles de la semaine → email aux abonnés

---

## Retours utilisateur (à remplir au fil de l'eau)

| Date | Source | Retour | Action |
|---|---|---|---|
| 2026-05-28 | Omar | "Pas de nouvelles publications depuis création rubrique" | ✓ Mis en place pipeline GH Actions + AI journalist |
|  |  |  |  |

---

## Checklist d'amélioration continue (chaque dimanche soir)

```
[ ] Lire métriques de la semaine (Google Analytics + Search Console)
[ ] Lire EDITORIAL/state/published_log.jsonl — y a-t-il eu des bugs/échecs ?
[ ] Lire les 5 derniers commentaires Firestore — modérer si besoin
[ ] Lire les 5 derniers retours @To1000com mentions sur X
[ ] Identifier 1 amélioration prioritaire pour la semaine à venir
[ ] L'ajouter au backlog ci-dessus avec date cible
[ ] Mettre à jour EDITORIAL/EDITORIAL_CALENDAR.md
```

---

## Indicateurs d'alerte (rouge si déclenché)

- 🔴 News.json plus mis à jour depuis > 2h → cron cassé
- 🔴 Aucun article IA publié depuis > 24h → API key/quota
- 🔴 Page WC charge > 3s → perf à investiguer
- 🔴 Comments spam volume > 10/jour → durcir banlist
- 🔴 Visiteurs uniques < 100/jour pendant la WC → SEO problem
