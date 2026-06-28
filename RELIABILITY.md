# Pourquoi le site devenait périmé — et la solution définitive

## Le vrai problème (diagnostic)
Tout ce qui « n'était pas à jour » (compteur, dernier/prochain match, stats, news,
langues) avait **une seule cause de fond** : **les workflows GitHub Actions
s'arrêtaient en milieu de mois** parce qu'ils **épuisaient les 2000 minutes
gratuites** (repo privé).

Coupables (avant correction) :
- `update-cr7-goals` : **toutes les 5 min**, ~8 h/jour, ~6 j/sem → **~3000+ min/mois à lui seul**.
- `news-sync` : **toutes les 30 min** → **~3600 min/mois**.
- Total très au-dessus de 2000 → **plus de minutes → tous les crons stoppent → le site fige**.

Quand les workflows ne tournent plus : la news ne se rafraîchit plus, stats.json
ne se met plus à jour (compteur/match figés), rien ne se redéploie → tu vois du
vieux, et tu dois intervenir à la main.

## Corrections appliquées (code) ✅
1. **Fréquences réduites pour rester sous 2000 min/mois :**
   - `news-sync` : 30 min → **2 h** (`0 */2 * * *`).
   - `update-cr7-goals` : 5 min → **20 min** pendant les fenêtres de match.
2. **Robustesse** : les étapes non-critiques de `news-sync` (génération HTML,
   prérendu, sitemap, dashboard, GA4) sont en **`continue-on-error`** → une news
   fraîche est **toujours déployée** même si une sous-étape échoue (avant : une
   seule erreur tuait tout le run → news figée).
3. **Traduction réactivée** : `DISABLE_MYMEMORY` retiré → fallback MyMemory si
   Gemini indisponible (au lieu de zéro traduction).

## La solution DÉFINITIVE (1 action, à toi) — au choix

### Option A — **Rendre le repo PUBLIC** (recommandé, le plus définitif)
GitHub Actions est **illimité et gratuit sur les repos publics**. Plus jamais de
minutes épuisées, quelle que soit la fréquence.
- GitHub → repo `to1000` → **Settings → General → Danger Zone → Change visibility → Public**.
- Sans risque : aucun secret n'est dans le code (ils restent dans *Settings → Secrets*).
- C'est un site de fans, le code n'a rien de confidentiel.

### Option B — Garder privé
Les fréquences réduites ci-dessus suffisent à rester sous 2000 min/mois. Mais
si tu rajoutes des workflows ou des matchs fréquents, surveille la conso.
- Les minutes se **réinitialisent le 1er du mois** → si elles sont épuisées ce
  mois-ci, les crons reprennent tout seuls au prochain mois (avec les fréquences réduites).

## Pour que la traduction marche (indispensable)
La traduction des news EN/ES vers FR (et inversement) **exige une clé Gemini
valide** (MyMemory seul plafonne à ~9 items/jour). Gratuit, 2 min :
- https://aistudio.google.com/app/apikey → crée une clé.
- GitHub → repo → Settings → Secrets and variables → Actions → `GEMINI_API_KEY` = ta clé.
- Vérifie qu'elle est **valide** (celle posée semble invalide : « API key not valid »).

## Pour que le déploiement soit 100% auto (sans toi)
`news-sync` se **redéploie tout seul** sur Cloudflare **si** ces secrets sont posés :
- `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` (Settings → Secrets → Actions).
- Si présents : à chaque rafraîchissement, le site se met à jour **sans `publish.bat`**.

## Comment vérifier l'état (diagnostic en 30 s)
- **Runs des workflows** : https://github.com/serhaneomar-Atlas/to1000/actions
  - Des runs **rouges** = une étape échoue (me l'envoyer).
  - **Aucun run récent** = minutes épuisées → Option A (public).
- **Minutes restantes** : https://github.com/settings/billing

## En résumé — ce qu'il te reste à faire UNE fois
1. **Repo en Public** (Option A) → workflows illimités, plus jamais de gel.
2. **`GEMINI_API_KEY` valide** → news traduites automatiquement.
3. Vérifier `CLOUDFLARE_API_TOKEN`/`ACCOUNT_ID` → déploiement 100% auto.

Après ça : compteur, matchs, stats, news, traductions se mettent à jour **seuls**,
sans intervention.
