# Fiabilité des workflows — diagnostic & solution

> Note : un premier diagnostic (minutes Actions épuisées) était **faux**. Le repo
> est **déjà public** → minutes illimitées. La vraie cause était un **bug de code
> dans un workflow** (dépendance manquante). Corrigé par CD + CC ci-dessous.

## La vraie cause des échecs
`stats-sync.yml` lançait `update_stats_v2.py` (qui importe `requests` via
`espn_client`) **sans `pip install requests`** → **`ModuleNotFoundError: requests`**
→ le workflow **échouait chaque jour** → `stats.json` jamais rafraîchi → compteur,
dernier/prochain match figés. **C'était un bug de code, pas un quota.**

## Corrigé ✅
1. **`stats-sync.yml`** : `pip install requests` ajouté (CD) — maintenant **commité**
   (il n'était qu'en local, donc GitHub re-échouait à chaque run).
2. **`stats.json` v29** (prochain match **Portugal–Croatie**) commité — le live
   montrait encore l'ancien match.
3. **Robustesse `news-sync`** : les étapes non-critiques sont en `continue-on-error`
   → une news fraîche est **toujours déployée** même si une sous-étape échoue.
   (Vrai garde-fou : avant, une seule erreur tuait tout le run.)
4. **Traduction** : `DISABLE_MYMEMORY` retiré → fallback réactivé.
5. **Fréquences** (repo public = minutes illimitées, on privilégie la fraîcheur) :
   news **toutes les heures**, goals **toutes les 10 min** en fenêtre de match.

## Audit : tous les workflows ont-ils leurs dépendances ?
Vérifié — chaque script lancé par un workflow a bien son `pip install` (ou n'a
besoin que de la lib standard) :
- `news-sync` → feedparser ✅ · `stats-sync` → requests ✅ (corrigé)
- `update-cr7-goals` → requests ✅ · `kaizen` → stdlib seulement ✅

## Ce qu'il reste (indépendant du code)
1. **Clé `GEMINI_API_KEY` valide** (gratuit, https://aistudio.google.com/app/apikey)
   → traduction complète des news EN/ES↔FR/AR. *(L'actuelle renvoie « API key not valid ».)*
   Sans elle, MyMemory ne traduit que ~9 items/jour (plafond gratuit).
2. **Secrets `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`** → `news-sync` et
   `stats-sync` se **redéploient seuls** sur Cloudflare (sans `publish.bat`).
3. **Index git côté Windows/Cowork** : si `git` se bloque (mount), réparer avec
   `del .git\index` puis `git reset` (rebuild de l'index depuis HEAD). N'affecte
   pas l'historique. (Côté WSL l'index est sain.)

## Vérifier l'état en 30 s
- Runs : https://github.com/serhaneomar-Atlas/to1000/actions
  (un run **rouge** = me copier l'erreur ; ça vient quasi toujours d'une dépendance
  manquante ou d'un script qui change de signature).
- Le code lui-même tourne illimité (repo public).

## En résumé
La fiabilité ne dépend **pas** de la visibilité (déjà publique) mais de :
**(a)** chaque workflow a ses dépendances, **(b)** les étapes non-critiques ne
bloquent pas le deploy (`continue-on-error`), **(c)** les clés/secrets sont valides.
Les trois sont désormais en place côté code ; restent la clé Gemini + les secrets
Cloudflare (ton ressort).
