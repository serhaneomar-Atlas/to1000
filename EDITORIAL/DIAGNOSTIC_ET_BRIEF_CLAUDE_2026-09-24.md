# to1000 — Diagnostic éditorial et mandat Claude
Auteur : ChatGPT / Atlas — 24 septembre 2026
Statut : diagnostic fondé sur le code, le flux public et les journaux de production. Première réparation déployée par PR43 ; complément de contrôle préparé. Pas une validation générale de la rédaction.

## Complément de contrôle — 24 septembre, après déploiement
- PR43 fusionnée : https://github.com/serhaneomar-Atlas/to1000/pull/43 ; déploiement réussi : https://github.com/serhaneomar-Atlas/to1000/actions/runs/36067568389 . Le garde de langue est servi publiquement. Ne pas confondre ce résultat et une rédaction multilingue rétablie.
- Cache examiné : 925 verdicts edtv8, dont 896 refus et 29 acceptations. Plusieurs motifs opposent la mémoire du modèle au média sur des affiliations actuelles ; cela ne constitue pas une vérification factuelle. Le complément recentre le tri sur la pertinence mondiale, fournit la date actuelle et invalide les anciens verdicts. Il ne garantit pas la véracité des médias.
- Rédaction Claude du blog : run36064229787, étape « Token Claude absent — blog en pause (pas un echec) ». Les étapes Claude et publication sont sautées malgré un statut global réussi. Connexion à rétablir par le propriétaire, sans communiquer de secret dans une conversation.
- RSS : les flux AR/EN/ES étaient générés mais non enregistrés par news-sync ; news-editorial ne les régénérait pas après enrichissement. Le complément corrige ces deux chemins. Make et la livraison sociale restent non vérifiés ; aucune publication sociale lancée.
- Le complément borne les requêtes Gemini réelles, reprises sur erreur incluses, au budget existant de50 par exécution. Pas d'augmentation du budget.
- Contrôle complet initial : 201 tests réussis,9échecs. Huit anciens tests exigeaient ou supposaient des replis désormais interdits ; ils sont adaptés avec des cas positifs complets et des refus explicites. Le neuvième cherchait littéralement « set -o pipefail » alors que le workflow utilisait « set -euo pipefail », équivalent : écriture explicitée, sans changement de protection. Les66tests ciblés locaux passent après correction ; attendre le contrôle complet distant du complément.
- Les archives anciennes, les menus de la page article, la qualité des extraits natifs, la diversité des sources et les faits des traductions restent à contrôler. Le tri lexical ne remplace pas une relecture éditoriale.

## Ce qui est prouvé
- Le flux de 21:37:58 UTC contient 48 nouvelles. Aucune entrée FR/EN/ES/AR ne porte un moteur Gemini/rédaction : les entrées sont MyMemory ou sans moteur.
- La page News, l’accueil et les pages article remplacent volontairement une traduction refusée par la langue originale. Ce choix explique le mélange malgré le sélecteur de langue.
- Des réponses IA incomplètes sont complétées avec le titre/résumé original puis marquées traduites. Le cache peut prolonger le défaut.
- Le traitement https://github.com/serhaneomar-Atlas/to1000/actions/runs/36055310316 affiche succès ; son journal compte 54 appels Gemini, 8 modifications, zéro candidat pour le contrôle sémantique. « Appel réussi » ne veut pas dire « article utilisable ». Les logs anciens ne donnent ni le motif de fin Gemini ni les erreurs de JSON : cause exacte du rendement nul non démontrée. Hypothèse à tester : réponse tronquée/plafond de sortie ou format inattendu, pas à annoncer comme cause certaine.
- Le budget nommé appels comptait les articles ayant appelé Gemini, pas les appels réels.
- Le flux social français admet tout et les autres flux utilisent des cascades de langues. La chaîne du site génère du RSS destiné à Make.
- Les scripts telegram_poster.py / x_poster.py et social-poster.yml annoncés par EDITORIAL/WORKFLOW.md ne figurent pas dans l’arbre actuel. MARKETING_SOCIAL.md désigne Make, à contrôler dans ce service. Aucune preuve de livraison sociale récente n’a été obtenue.
- Le workflow AI Editorial demande encore 600–900 mots, des sections et une conclusion. Contradiction avec la nouvelle demande d’Omar.
- Aucune donnée de fréquentation n’a été lue : perte ou départ des visiteurs non démontrés.

## Correctif préparé dans cette passe
Contrat de langue commun Python/JS pour accueil, liste, articles et RSS : titre et résumé complets, moteur accepté pour une traduction, rejet des copies évidentes du source, respect des rejets éditoriaux, garde d’écriture arabe. Un message dans la langue choisie remplace une version absente ; aucun texte étranger présenté comme traduction.
Cache incomplet ignoré, réponses partielles non complétées par la source. Motif de fin Gemini et JSON invalide signalés sans clé ni corps complet dans les logs. Compteur de vrais appels corrigé et rejet éditorial sans traduction de remplissage. Brèves de 40–130 mots, 180 maximum si plusieurs faits essentiels, au lieu de 600–900 mots dans AI Editorial.
Badge automatique « Vérifié » retiré des cartes : un nombre de sources ne prouve pas leur indépendance.
53 tests sans réseau passent (10 nouveaux +26 chaîne éditoriale +17 existants). Vérification de syntaxe de9blocs JS et navigation locale FR/EN/AR, accueil et article indisponible. Sur le flux figé, disponibilité après garde : FR21 EN2 ES15 AR0. Ces nombres ne mesurent PAS la qualité rédactionnelle. Les archives anciennes ne sont pas toutes régénérées.
Limites : garde lexical/structurel, pas détecteur linguistique complet ; extraits RSS natifs encore publiables et parfois creux ; le modèle n’a pas été testé en direct ici ; pas de nouveau fournisseur ou dépense manuelle.

## Lecture critique du document Gemini
Source lue sans modification : https://docs.google.com/document/d/1JhioV1exXHlvSF-kyeZG69h3Bg_V-t6Qhz2FKvlLLjQ/edit
À retenir : le fait avant la vitesse, titre informatif, faits sourcés, lecture de l’article plutôt que seul RSS quand accessible, dédoublonnage d’un événement, relecture des4langues, correction traçable, droit à l’abstention.
À ajuster :
- Le chiffre «80%» d’erreurs liées à la course au scoop n’est pas sourcé : ne pas le reprendre comme mesure.
- Une source officielle prouve une annonce, pas automatiquement toutes ses affirmations. Deux reprises d’une dépêche ne sont pas deux confirmations indépendantes.
- Ne pas imposer titre+3puces+2paragraphes à un fait simple : conserver la matière utile, sans rallonger pour le SEO.
- Ne pas contourner les accès protégés. Marquer lecture partielle, abandonner si l’information utile manque.
- Un crédit photo ne remplace pas une licence. Une image trouvée dans les métadonnées d’un média n’est pas libre par défaut.
- Ne pas confondre «4 versions présentes» et fidélité/qualité. Prévoir contrôle des noms, scores, négations, rumeurs, dates, contexte et langue réelle.
- Distinguer horaire de l’événement, première publication et dernière correction ; un nouvel import RSS n’est pas une nouvelle information.

## Offre recommandée
« Le tour du foot, dans votre langue, sans vous faire perdre votre temps. »
Une édition courte des nouvelles importantes : le fait principal immédiatement visible, son contexte utile, les sources consultables, les mises à jour regroupées. Le compteur Ronaldo reste une signature et une entrée dédiée, pas un filtre qui efface le football mondial.
Accueil : essentiels du moment + compteur compact + accès compétitions/régions. News : fil chronologique et sélection éditoriale distincts. Article : brève complète, sources et corrections dépliables. Europe, Afrique, Amérique latine : mesurer la diversité des sources et des sujets ; pas de quota artificiel de remplissage.

## Pilotage proposé — responsabilités et preuves
| Travail | Responsable proposé | Preuve de fin |
|---|---|---|
| Restaurer la génération multilingue | Claude Code pour correctif, Atlas pour contre-test | Sur un lot figé, faits identiques et4langues correctes, résultat réel documenté |
| Rédacteur en chef | Étape explicite du pipeline, relecture humaine d’Omar par échantillon au démarrage | Aucun ajout inventé, résumé utile, titre sans piège, sources consultables |
| Dédoublonnage | Code déterministe + contrôle des événements | Plusieurs articles du même fait regroupés ; faits voisins distincts préservés |
| Publication et surveillance | GitHub Actions + contrôles de sortie | Suivi fraîcheur ET couverture linguistique ET erreurs, pas seulement job vert |
| Réseaux sociaux | Reprise Make à auditer | Brouillon/aperçu puis publication autorisée avec identifiant et URL prouvant la livraison |
| Design | Claude, après brief ci-dessous |5prototypes réellement différents, testables sur téléphone, puis choix Omar |
Ces rôles sont une proposition de fonctionnement, pas des agents permanents déjà actifs.

## Suite priorisée
1. Lire les nouveaux motifs d’échec Gemini. Tester au maximum un petit lot contrôlé avec le compte déjà autorisé et un plafond explicite ; ne pas lancer50articles en boucle. Comparer sortie brute structurée/parse/cache/publication. Ne pas augmenter les coûts ou changer de modèle au hasard.
2. Produire des brèves qui répondent au titre même lorsque le RSS n’est qu’une amorce. Préserver les mots «annulé», «selon», «rumeur», «dément» ; pas d’invention de score.
3. Contrôler un échantillon réel multilingue avant de déclarer la panne résolue. Les sources natives seules ne suffisent pas.
4. Vérifier dans Make : scénario, activé ou non, connexions expirées, historique des derniers succès/échecs, correspondance canal-langue. Pas de publication ni réactivation aveugle ; préparer un post test à approuver.
5. Conserver un registre unique des tâches avec responsable, dépendance, preuve et point de reprise. Ajouter une alerte qualité quand le travail technique réussit mais aucune brève traduite ne sort.

## Brief à donner à Claude Code —5directions
Tu interviens sur https://github.com/serhaneomar-Atlas/to1000 . Lis ce diagnostic, le document Gemini et les règles du dépôt. Repars d’une révision vérifiée dans une branche isolée ; préserve les changements des autres. Vérifie quel modèle est réellement actif ; n’affirme pas utiliser Opus5.5 si l’interface ne le confirme pas.
Priorité1 : terminer le diagnostic/réparation de la rédaction multilingue, avec preuve sur des sorties réelles, sans hausse implicite de budget.
Puis agis comme directeur artistique ET chef de produit : livre5prototypes navigables, pas5palettes du même template. Ils doivent différer par architecture de page, typographie, hiérarchie et expérience de lecture. Même lot d’articles de démonstration clairement étiqueté pour comparer équitablement.
Directions proposées (tu peux les améliorer avec justification) :
1. Le Quotidien : papier clair, typographie de journal, densité maîtrisée, Une hiérarchisée.
2. Tribune : énergie du stade, typographie expressive, score et chronologie, couleurs franches sans dégradé décoratif automatique.
3. Le Monde du foot : régions/compétitions, regards croisés Europe–Afrique–Amérique latine, carte optionnelle accessible.
4. Le Vestiaire : magazine photographique, portraits/histoires, photos autorisées, signatures et espace.
5. L’Essentiel : lecteur mobile rapide, briefing du jour, ce qui a changé depuis ma visite, développement à la demande.
Pour chaque direction : accueil, liste News, article, compteur Ronaldo intégré, mobile et bureau, état vide/chargement/erreur, FR et AR RTL au minimum en prototype, navigation des4langues prévue. Pas de carrousel bloquant, défilement forcé, titres mystères, popup agressive ni clone d’un média existant.
Livrer une galerie avec5liens, captures, différences expliquées, avantages/limites et recommandation. Omar choisit avant remplacement du site public. Garder performance, SEO, URLs existantes, accessibilité, lisibilité et sources. Ne pas réécrire la pile technique pour une maquette.

### Outils vérifiés dans les catalogues officiels le24septembre
- Frontend Design (Anthropic) : https://claude.com/marketplace/plugins/frontend-design — direction graphique et frontend ; ne dispense pas d’un brief distinctif.
- Playwright (Microsoft, catalogue Claude) : https://claude.com/marketplace/plugins/playwright — navigation, captures, tests ; complément de qualité, pas générateur de goût.
- Figma : https://claude.com/marketplace/plugins/figma — utile si nous choisissons de travailler avec de vrais fichiers Figma/tokens ; facultatif pour5prototypes HTML. Pas d’abonnement supplémentaire implicite.
- Claude dans Chrome : https://code.claude.com/docs/en/chrome — alternative pour examiner les références et le rendu avec la session existante.
- GitHub pour branches/diff/revue ; Google Drive pour lire le document Gemini, sans le modifier.
Vérifier les extensions déjà présentes dans Claude avant toute installation. Aucun outil n’a été installé ni nouvelle permission accordée durant cet audit.

### Références à étudier sans copier
- https://www.theguardian.com/football : sections, hiérarchie, liens scores/calendriers.
- https://ge.globo.com/futebol/ : navigation football brésilienne et couverture locale.
- https://www.cafonline.com/ : source officielle pour football africain, pas étalon journalistique indépendant.
- https://www.bbc.com/sport/football : à consulter dans le navigateur ; lecture web automatisée bloquée ici.
Ces références ne prouvent ni leur performance commerciale ni une hausse future de notre audience. Tester les choix avec Omar et mesurer ensuite le retour des lecteurs.
