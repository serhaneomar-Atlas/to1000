# Playbook : WC Live Match (pendant un match)

## Pré-match (H-2 à H-0)
1. Confirmer compositions officielles depuis fpf.pt / frmf.ma / ESPN
2. Mettre à jour la page live `/world-cup/{country}/live-{slug}.html` avec compos
3. Push notif PWA "Le match commence dans 30 minutes"
4. Post X "Compos confirmées !" avec image équipe
5. Activer goal_watcher_v2.py en mode WC (poll 60s sur events ESPN)

## En direct (H-0 à H+90+)
Le live blog auto-update via JS fetchant `/wc-live.json` toutes les 30s.

Contenu du live blog :
- Chronologie : but, carton, remplacement, gros événement
- Tweet quotes (si on a une intégration) ou citations manuelles
- Réactions polls live (Firebase Polls)
- Stats live (poss, tirs cadrés, xG) — si fournisseur dispo

Posts X **réactifs** pendant le match :
- But adverse : 1 post sobre, factuel
- But favoris : 1 post enthousiaste avec emoji
- Penalty : 1 post avant la frappe + 1 après
- Carton rouge : 1 post immédiat
- Mi-temps : 1 post avec le score + analyse 50 mots
- Coup de sifflet final : 1 post résultat

## Mi-temps (H+45 à H+60)
- Article express "À la pause : {SCORE}" — 200 mots
- Push notif PWA aux abonnés
- Story IG si match Maroc/Portugal

## Coup de sifflet final
Voir `POST_MATCH.md`. À déclencher immédiatement.

## En cas de problème technique pendant le match
- ESPN down → fallback fotmob
- fotmob down → twitter live de @fifaworldcup ou compte officiel équipe
- Cloudflare 5xx → vérifier deploy précédent, rollback si besoin
- News.json freeze → relancer manuellement scripts/news_aggregator.py

## Engagement
Pendant un match, le canal Telegram et X doivent être actifs en quasi-real-time. Si Omar regarde le match, c'est lui qui poste en réactif. Sinon, Claude (computer use) ou scheduled poster auto.

## Particularité matchs Maroc
La page Maroc en live doit avoir un encart "VOS COMMENTAIRES" très visible avec un compteur "{N} supporters en ligne". Les supporters marocains commentent BEAUCOUP — il faut être prêt à modérer en quasi-temps réel.

Comments à supprimer immédiatement :
- Insultes envers joueurs (les deux camps)
- Racisme
- Provocations politiques (cf. STYLE_GUIDE.md sensibilités Maroc)
- Spam liens externes
