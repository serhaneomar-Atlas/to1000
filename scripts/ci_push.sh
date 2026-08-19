#!/usr/bin/env bash
# ci_push.sh — pousser le travail d'un bot sans le perdre en cas de collision.
#
# Le problème observé le 19/08/2026 : news-editorial a produit un enrichissement
# réel (35 fichiers, 1096 insertions), l'a commité sur le runner, puis a tenté
#   git push origin HEAD:main 2>/dev/null || git push 2>/dev/null || true
# Un autre workflow (update-cr7-goals) avait poussé à la même seconde. Le push a
# été rejeté en non-fast-forward, la sortie était envoyée vers /dev/null, et le
# `|| true` a rendu l'étape verte. Le commit n'a jamais atteint le dépôt : le
# site déployé sur Cloudflare avait l'enrichissement, le dépôt non. Aucune trace
# dans les logs — encore une panne silencieuse.
#
# Ici : on rebase sur l'état distant et on réessaie, et si ça ne passe toujours
# pas, on le DIT et on sort en erreur. Perdre le travail est acceptable ; le
# perdre sans le savoir ne l'est pas.
#
#   bash scripts/ci_push.sh [branche]     (défaut : main)
set -u -o pipefail

BRANCHE="${1:-main}"
TENTATIVES="${CI_PUSH_TENTATIVES:-4}"

for i in $(seq 1 "$TENTATIVES"); do
    if git push origin "HEAD:${BRANCHE}"; then
        echo "::notice::push réussi (tentative ${i}/${TENTATIVES})"
        exit 0
    fi

    echo "::warning::push refusé (tentative ${i}/${TENTATIVES}) — rebase sur origin/${BRANCHE}"
    if ! git fetch origin "$BRANCHE"; then
        echo "::warning::fetch impossible — nouvelle tentative"
        sleep $((i * 3))
        continue
    fi

    # --autostash : le déploiement qui suit peut avoir laissé des fichiers
    # non suivis ou modifiés (assets élagués, caches) ; on ne veut pas que
    # le rebase échoue pour ça.
    if ! git rebase --autostash "origin/${BRANCHE}"; then
        git rebase --abort 2>/dev/null || true
        echo "::error::rebase impossible sur origin/${BRANCHE} — conflit à traiter à la main."
        echo "::error::Le travail de ce run n'est PAS dans le dépôt."
        exit 1
    fi
    sleep $((i * 3))
done

echo "::error::push impossible après ${TENTATIVES} tentatives."
echo "::error::Le travail de ce run n'est PAS dans le dépôt — il sera refait au run suivant."
exit 1
