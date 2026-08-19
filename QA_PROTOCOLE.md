# Protocole de vérification avant validation

À passer avant de considérer une session terminée, et avant tout déploiement
qui touche aux données ou au contenu.

Trois outils, trois périmètres. Aucun ne remplace les autres.

| Outil | Répond à | Durée |
|---|---|---|
| `node qa-check.js` | Les compteurs de buts se contredisent-ils ? | ~1 s |
| `python scripts/qa_site.py` | Reste-t-il une coquille, une donnée périmée, un lien mort ? | ~5 s |
| `python scripts/audit_editorial.py` | Le fil News est-il bien écrit et bien traduit ? | ~3 s |
| `python -m pytest scripts/tests/ -q` | Le code tient-il ? | ~1 s |

---

## La passe complète

```bash
python -m pytest scripts/tests/ -q          # 1. le code
node qa-check.js                            # 2. les compteurs de buts
python scripts/qa_site.py                   # 3. le site
python scripts/audit_editorial.py           # 4. le fil News
```

Tout doit sortir en code 0. Une erreur bloque la validation ; une alerte se
lit et se tranche.

Pour un rapport machine (CI, archivage) :

```bash
python scripts/qa_site.py --json EDITORIAL/state/qa_latest.json
python scripts/audit_editorial.py --json EDITORIAL/state/audit_latest.json --seuil 70
```

---

## Ce que chaque contrôle attrape

### `qa_site.py` — sept familles

| Famille | Exemple réel trouvé |
|---|---|
| `fraicheur` | `stats.json` vieux de 24 jours — la synchro ESPN était morte depuis le 12/08 |
| `coherence` | 967 buts en base pour un compteur à 976 : 9 buts sans fiche |
| `placeholder` | `REMPLACER_PAR_TON_TOKEN_GSC` encore dans `index.html` |
| `json` | fichier de données ou JSON-LD illisible |
| `lien_mort` | lien interne, ou redirection 301 vers une cible inexistante |
| `seo` | `og:title` et `og:image` absents de `about.html` et `contact.html` |
| `langue` | page qui annonce « texte original (anglais) » sur une source espagnole |

Options : `--verbeux` liste tous les cas, `--strict` rend les alertes
bloquantes, `--echantillon N` règle le nombre d'articles inspectés (25 par
défaut ; le site en compte plus de 16 000).

### `audit_editorial.py` — qualité rédactionnelle
Voir `EDITORIAL/COUNCILS.md`. Score sur 100, seuil conseillé à 70.

### `qa-check.js` — compteurs de buts
Cohérence entre `stats.json`, `goals.html` et les bundles de traduction.

---

## Les faux positifs, et pourquoi ils comptent

Un audit qui signale à tort finit par ne plus être lu — et c'est là qu'on rate
la vraie coquille. Trois cas ont été neutralisés explicitement, chacun couvert
par un test :

- **« Todo el fútbol »** n'est pas un `TODO` oublié. Le motif est sensible à la
  casse.
- **Un `TODO` en commentaire HTML** n'est pas visible du lecteur : c'est une
  note interne. Les commentaires sont retirés avant le scan.
- **2 335 pages pointent vers `/world-cup/*`**, toutes redirigées en 301 vers
  `/coupe-du-monde/`. L'audit lit `public/_redirects` avant de conclure. Il
  vérifie en revanche que la cible de chaque redirection existe — une 301 vers
  un 404 est pire qu'un lien mort.

Si un contrôle produit un faux positif, la correction se fait **dans le
contrôle**, avec un test qui fige le cas. Jamais en ignorant le rapport.

---

## Automatisation

`.github/workflows/editorial-audit.yml` fait tourner la passe complète chaque
jour à 06h UTC, et à chaque modification de la chaîne éditoriale. Il commite les
rapports, tient une série historique, et ouvre une issue GitHub quand le score
éditorial décroche — mise à jour plutôt que dupliquée, refermée quand la qualité
revient.

---

## État au 19/08/2026

Après réparation de la chaîne éditoriale et de la synchro stats :

```
pytest              125 tests, tous verts
qa_site.py          3 erreurs, 0 alerte
audit_editorial.py  65,8/100 (mesure de départ, avant le premier run réparé)
qa-check.js         2 erreurs (les 9 buts sans fiche)
```

Les trois erreurs restantes de `qa_site.py` sont connues et attribuées :

1. **`stats.json` périmé** — le correctif d'isolation est poussé ; le prochain
   run de `stats-sync` remettra la donnée à jour tout seul.
2. **9 buts sans fiche** — la base `goals-data.json` s'arrête au but 967 alors
   que le compteur est à 976. Chantier « page des buts ».
3. **Jeton Search Console** — `REMPLACER_PAR_TON_TOKEN_GSC` est toujours dans
   `index.html` : la propriété n'a jamais été validée, donc aucune donnée de
   recherche ne remonte. Demande la valeur dans Search Console → Balise HTML,
   puis remplace-la (procédure dans `CONNECT_ANALYTICS.md` §1). **Action Omar :
   personne d'autre n'a accès au compte.**
