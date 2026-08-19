"""Conseil d'audit — chaque contrôle doit attraper son défaut, et seulement lui.

Un audit qui crie au loup partout ne sert à rien : on teste aussi qu'un article
correct sort sans défaut.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_editorial import audite, audite_item, similarite  # noqa: E402

LANGS = ("fr", "en", "es", "ar")


def _entry(title, summary, engine="gemini-editor", **extra):
    e = {"title": title, "summary": summary, "engine": engine,
         "needs_translation": False}
    e.update(extra)
    return e


def _item(fr_title="Le Real Madrid renverse Girona en fin de match",
          fr_summary="Deux buts en huit minutes offrent la victoire au Real Madrid, "
                     "revenu de 0-2 à Montilivi.",
          engine="gemini-editor", **kw):
    """Article de référence : propre sur les quatre langues."""
    item = {
        "id": "abc123",
        "primary_source": {"lang": "es"},
        "i18n": {
            "fr": _entry(fr_title, fr_summary, engine),
            "en": _entry("Real Madrid turn it around against Girona",
                         "Two goals in eight minutes give Real Madrid the win after "
                         "trailing 0-2 at Montilivi.", engine),
            "es": _entry("El Real Madrid remonta ante el Girona",
                         "Dos goles en ocho minutos dan la victoria al Real Madrid "
                         "tras ir 0-2 abajo en Montilivi.", engine),
            "ar": _entry("ريال مدريد يقلب الطاولة على جيرونا",
                         "هدفان في ثماني دقائق يمنحان ريال مدريد الفوز بعد تأخره "
                         "بهدفين في مونتيليفي.", engine),
        },
    }
    item.update(kw)
    return item


def _types(defauts):
    return {d["type"] for d in defauts}


def test_un_article_propre_ne_produit_aucun_defaut():
    assert audite_item(_item()) == []


def test_detecte_le_calque_sur_un_nom_de_club():
    item = _item(fr_title="Le Royal Madrid renverse Gérone en fin de match")
    defauts = [d for d in audite_item(item) if d["type"] == "calque"]
    assert len(defauts) == 2          # Royal Madrid + Gérone
    assert "Real Madrid" in defauts[0]["detail"]


def test_detecte_le_resume_qui_repete_le_titre():
    item = _item(fr_title="Le Real Madrid renverse Girona en fin de match",
                 fr_summary="Le Real Madrid renverse Girona en toute fin de match.")
    assert "echo_titre" in _types(audite_item(item))


def test_detecte_un_resume_trop_court():
    item = _item(fr_summary="Victoire du Real Madrid.")
    assert "resume_court" in _types(audite_item(item))


def test_detecte_les_tics_de_redaction_ia():
    item = _item(fr_summary="Il convient de noter que le Real Madrid s'est imposé "
                            "dans les dernières minutes de la rencontre.")
    assert "tic_ia" in _types(audite_item(item))


def test_detecte_les_tics_dans_le_developpement_aussi():
    item = _item()
    item["i18n"]["fr"]["body"] = ["Reste à savoir si le club tiendra le rythme."]
    assert "tic_ia" in _types(audite_item(item))


def test_detecte_la_traduction_brute():
    item = _item(engine="mymemory")
    defauts = [d for d in audite_item(item) if d["type"] == "non_enrichi"]
    assert len(defauts) == len(LANGS)
    assert "mymemory" in defauts[0]["detail"]


def test_needs_translation_compte_comme_non_enrichi():
    item = _item()
    item["i18n"]["fr"]["needs_translation"] = True
    assert "non_enrichi" in _types(audite_item(item))


def test_detecte_une_langue_manquante():
    item = _item()
    del item["i18n"]["ar"]
    defauts = [d for d in audite_item(item) if d["type"] == "langue_absente"]
    assert len(defauts) == 1
    assert defauts[0]["lang"] == "ar"


def test_l_arabe_n_est_pas_penalise_pour_translitterer():
    """Les noms propres y sont translittérés : ce n'est pas une perte."""
    assert not [d for d in audite_item(_item())
                if d["type"] == "nom_perdu" and d["lang"] == "ar"]


def test_le_score_chute_quand_tout_le_fil_est_en_traduction_brute():
    propre = audite({"items": [_item()]})
    brut = audite({"items": [_item(engine="mymemory")]})
    assert propre["score"] == 100.0
    assert brut["score"] == 70.0          # 30 points de pénalité sur chaque couple
    assert brut["couverture"]["enrichis"] == 0


def test_un_fil_vide_vaut_zero_pas_cent():
    """Une panne d'agrégation ne doit pas se lire comme une qualité parfaite."""
    assert audite({"items": []})["score"] == 0.0


def test_la_penalite_par_couple_est_plafonnee_a_cent():
    """Un article catastrophique ne peut pas faire passer le score sous zéro."""
    casse = _item(fr_title="Le Royal Madrid et Gérone",
                  fr_summary="Le Royal Madrid.", engine="mymemory")
    rapport = audite({"items": [casse]})
    assert rapport["score"] >= 0.0


def test_le_rapport_compte_la_lecture_du_source_et_le_developpement():
    item = _item(editorial={"publish": True, "quality": 8, "source_read": "full"})
    item["i18n"]["fr"]["body"] = ["Un paragraphe de développement."]
    rapport = audite({"items": [item]})
    assert rapport["couverture"]["source_lu_en_entier"] == 1
    assert rapport["couverture"]["avec_developpement"] == 1


def test_similarite_reconnait_la_paraphrase_et_ignore_le_vrai_apport():
    assert similarite("Le Real gagne 2-0", "Le Real gagne 2-0") == 1.0
    assert similarite("Le Real gagne", "Mbappé absent trois semaines") < 0.2
