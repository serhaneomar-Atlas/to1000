# EDITORIAL/ — Le journal autonome de to1000.com

> **Ceci est le point d'entrée pour tout agent (Claude ou humain) qui travaille sur le contenu du site.**
> Lis ce fichier en PREMIER à chaque session "contenu / news / WC / réseaux sociaux".
> Pour le code/infra, le `CLAUDE.md` à la racine reste la référence.

## Métaphore : une rédaction électronique

to1000.com fonctionne comme un journal sportif numérique avec des rôles distincts, chacun ayant son propre playbook. Quand tu travailles sur le site, tu **incarnes un rôle**. Tu ne fais pas tout en même temps.

```
Rédacteur en chef    ─► priorise les sujets, valide la ligne éditoriale
Journalistes (5)     ─► écrivent les articles selon leur beat
SEO-optimiseur       ─► transforme un brouillon en page indexable
Infographiste        ─► images, alt-text, OG cards
Social media         ─► publie sur X, IG, Threads, Telegram
DevOps               ─► fait tourner les workflows (cron, deploy)
```

## Carte du dossier

```
EDITORIAL/
├── README.md                    ← tu es ici
├── ROLES.md                     vue d'ensemble des 8 rôles
├── WORKFLOW.md                  la boucle quotidienne / live
├── EDITORIAL_CALENDAR.md        plan de contenu (semaine + mois)
├── STYLE_GUIDE.md               voix, ton, règles SEO, marque
├── roles/                       1 fichier par rôle = sa "fiche poste"
│   ├── REDACTEUR_CHEF.md
│   ├── JOURNALISTE_CR7.md
│   ├── JOURNALISTE_FOOT.md
│   ├── JOURNALISTE_PORTUGAL.md
│   ├── JOURNALISTE_MAROC.md
│   ├── SEO_OPTIMISEUR.md
│   ├── INFOGRAPHISTE.md
│   └── SOCIAL_MEDIA.md
├── playbooks/                   procédures réutilisables
│   ├── DAILY_BRIEF.md           ce qui doit tourner chaque jour
│   ├── BREAKING_NEWS.md         déclenchement d'une news urgente
│   ├── POST_MATCH.md            après un match Portugal/Maroc/Al Nassr
│   ├── PRE_WC_BUILDUP.md        contenu pré-Coupe du Monde
│   └── WC_LIVE_MATCH.md         live-blogging pendant un match WC
├── templates/                   structures à copier-coller
│   ├── article-news.html        page news individuelle
│   ├── article-blog.html        article long format
│   ├── og-image-prompt.md       prompt pour générer une OG card
│   └── seo-checklist.md         checklist à valider avant publish
└── state/                       ce qui change entre runs
    ├── pending_topics.json      backlog d'idées
    ├── published_log.jsonl      audit trail des publications
    └── social_schedule.json     posts X/IG planifiés
```

## Première chose à faire à chaque session

1. Lire ce fichier.
2. Lire `WORKFLOW.md` pour comprendre dans quelle phase tu te trouves (daily, breaking, post-match, WC live).
3. Lire `EDITORIAL_CALENDAR.md` pour voir ce qui est prévu cette semaine.
4. Vérifier `state/published_log.jsonl` (dernières 10 lignes) pour ne pas dupliquer.
5. Choisir UN rôle. Lire son `roles/*.md`. Exécuter.

## Règles non-négociables (lis aussi `STYLE_GUIDE.md`)

- ❌ Jamais affirmer un chiffre live (buts, prochain match) sans avoir vérifié `public/stats.json` ou la source officielle.
- ❌ Jamais utiliser le branding "CR7™" — c'est une marque déposée. Fair use éditorial OK.
- ❌ Jamais inventer une déclaration, un score, une blessure. Si pas de source, on n'écrit pas.
- ✅ Toujours mettre un disclaimer "fan site non officiel" dans le footer.
- ✅ Toujours mettre `lang=` correct sur `<html>` (en/fr/es/ar) + `dir="rtl"` pour AR.
- ✅ Toujours mettre `<link rel="canonical">` + JSON-LD `NewsArticle` ou `Article` ou `SportsEvent`.
- ✅ Toujours respecter le scope : foot général + CR7, pas mono-CR7 (cf. CLAUDE.md racine).

## Quand demander à Omar

- Décisions de design qui changent l'identité (couleurs, logo, layout home).
- Achat de domaine, signing de partenariat, dépense ≥ 10 €.
- Publication d'un contenu controversé (politique, religion, droits humains).
- Doute sur le respect des règles de marque CR7 ou FIFA.

Sinon : **agis**. Mieux vaut publier vite et corriger qu'attendre la perfection.
