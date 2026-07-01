# Plan marketing social — to1000.com

Objectif : faire monter les visites du site via les réseaux (FB / Instagram / X),
en s'appuyant sur le **hook CR7 vers 1000 buts** + l'**actu football en flash info**.

## 1. Identité visuelle (faite, automatique)
- **Charte ESTÁDIO** : fond navy `#05070b`, or `#f2c14e`, police Anton (titres).
- **Assets de marque** (générés, `public/social/brand/`) : avatar `TO1000`,
  bannière Facebook, header Twitter. → à poser sur les 3 pages.
- **Carte de marque par article** (auto, `public/social/cards/{id}.png`) : chaque
  post porte NOTRE visuel (titre flash-info + label + compteur + marque), pas
  l'image de la source. Cohérence = crédibilité = clics.
- **Légendes prêtes** (dans le flux RSS) : emoji + brève + 3-5 hashtags ciblés.

## 2. Piliers de contenu (le rythme éditorial)
1. **CR7 / le compteur** (le cœur émotionnel) — chaque but, chaque jalon vers 1000.
   → post « compteur » à chaque but + rappel hebdo « plus que X buts ».
2. **Résultats & temps forts** (Mondial 2026 en cours = pic d'audience) — brèves
   de match, buts, qualifications.
3. **Mercato & grands clubs** (Real, Barça, PSG, City, Maghreb…) — transferts.
4. **Angle Maghreb / Afrique / Brésil / Argentine / Saudi** — communautés très
   engagées, sous-servies par les gros médias FR.

## 3. Cadence & canaux
| Réseau | Fréquence | Format |
|---|---|---|
| **Twitter/X** | tous les articles importants (auto via RSS) | carte + brève + hashtags + lien |
| **Facebook** | 4-8/jour (auto) | idem, format « page média » |
| **Instagram** | 2-4/jour (auto, feed) + Stories manuelles les jours de match | carte 1080 + légende |

- Auto-post = **Make.com** branché sur `to1000.com/rss.xml` (CD le configure).
- Manuel (à forte valeur) : Stories les soirs de match, sondages, réactions live.

## 4. Hashtags (stratégie)
- **Larges** (portée) : `#Football` `#WorldCup2026` `#CDM2026`
- **Marque** : `#To1000` `#CR7` `#Ronaldo`
- **Spécifiques** (dérivés auto par article) : équipes/joueurs (`#France` `#Mbappe`…).
- Règle : 3-5 max sur X/FB, jusqu'à 10-15 sur IG (mettre les extra en 1er commentaire).

## 5. Tactiques de croissance
- **Réactivité match** : poster le but dans les 2-3 min (l'algo récompense la fraîcheur).
- **Le compteur = feuilleton** : « J-? buts avant l'histoire » crée du retour récurrent.
- **CTA discret** : finir chaque post par le lien → ramener au site (SEO + pub).
- **Engagement** : répondre aux commentaires, poser des questions (« Ronaldo marque
  ce soir ? »), sondages Stories.
- **Cross-post** : même carte sur les 3 réseaux (déjà automatisé).
- **Communautés** : partager dans les groupes FB foot/CR7/Maghreb (manuel, ciblé).

## 6. KPIs à suivre (dashboard + GA4)
- Trafic social → site (source « Social » dans GA4).
- Taux de clic des posts (impressions → clics).
- Croissance abonnés / semaine.
- Corrélation but de CR7 ↔ pic de trafic (préparer le buzz du 1000e).

## 7. Le grand rendez-vous : le 1000e but
Préparer **maintenant** un kit « milestone » (carte spéciale + posts multilingues
programmés + Story compte à rebours). Le jour J = pic viral énorme → le site
(statique + Cloudflare) encaisse, les réseaux amplifient.

---
*Assets & automatisation gérés par le pipeline (scripts/social_card.py + rss_generator.py).
Configuration Make = CD (Cowork). Optimisation continue = CC.*
