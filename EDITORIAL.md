# Comité éditorial — `scripts/editorial.py`

Un « comité éditorial » autonome qui **filtre, vérifie et valide** chaque news
**avant publication**, branché dans `news_aggregator.py` (donc actif à chaque run
du workflow `news-sync`). Objectif : un journal foot crédible — l'essentiel,
sourcé, sans clickbait, fidèle au source.

## Les rôles (2 couches)

### 1. Recherchiste — heuristique, **sans API** (toujours actif)
Écarte d'office les articles **non-news / utilitaires** :
« how to watch », « live stream », « for free », « tv channel », « what time »,
paris / cotes / « tips » / « prediction », « predicted line-ups », « team news »,
« streaming », « comment regarder », « à quelle heure »…
→ ces guides de diffusion / affiliation / SEO ne sont **jamais** publiés.
*(C'est ce qui a retiré l'article « How to watch Colombia vs Portugal for FREE ».)*

### 2. Rédacteur en chef — **Gemini** (actif si `GEMINI_API_KEY` valide)
Pour chaque candidat restant, **UN appel** qui réunit 3 rôles
(recherchiste → journaliste → rédacteur en chef) et renvoie un verdict :
```json
{ "publish": true|false, "reason": "...", "quality": 0-10,
  "i18n": { "fr": {"title","summary"}, "en": {...}, "es": {...}, "ar": {...} } }
```
Règles de **rejet** (`publish:false`) :
- **Pas une vraie news** (guide, preview creux, listicle, pub).
- **Divergence/infidélité** : le résumé n'est pas fidèle au source, ou doute sur
  le contenu réel → on ne publie pas (c'est le bug que tu as signalé).
- **Hors foot** ou sujet sans intérêt.
- **Périmé** (match déjà joué annoncé comme à venir).

Si publié : titre + **résumé essentiel fidèle** (1-2 phrases, ~35 mots, neutre)
dans les 4 langues, en un seul appel (mis en cache → coût maîtrisé).

## Dégradation gracieuse
- **Sans clé Gemini** : seul le recherchiste tourne (les guides/junk sont quand
  même écartés). Le pipeline **ne casse jamais**.
- **Avec clé Gemini valide** : le rédacteur en chef ajoute la vérification de
  fidélité, le rejet qualité, et les vrais résumés traduits.

## ⚠️ La clé est le cerveau du rédacteur en chef
Pour la **vérification de fidélité** et les **résumés fidèles traduits**, il faut
une **`GEMINI_API_KEY` valide** (gratuite : https://aistudio.google.com/app/apikey,
puis GitHub → Settings → Secrets → Actions). Sans elle, on filtre le junk évident
mais on ne vérifie pas la fidélité ligne par ligne.

## Régler la sévérité
- Motifs du recherchiste : `NON_EDITORIAL` dans `scripts/editorial.py`.
- Critères du rédacteur en chef : le `system` prompt de `chief_editor_review`.
- Seuil qualité : on peut filtrer aussi sur `quality` (ex. < 4 → rejet) dans
  `news_aggregator.py`.
