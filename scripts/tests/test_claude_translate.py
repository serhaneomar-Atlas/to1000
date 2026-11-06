"""Traduction par Claude : validation, magasin, survie au rafraîchissement du fil."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import claude_translate as ct  # noqa: E402
from news_locale import publishable  # noqa: E402


def _item(iid="a1", lang="es"):
    return {
        "id": iid, "title": "El Real Madrid gana al Getafe", "summary": "El Real Madrid venció 2-0 al Getafe en el Bernabéu.",
        "primary_source": {"lang": lang, "name": "Marca"},
        "i18n": {lang: {"title": "El Real Madrid gana al Getafe",
                        "summary": "El Real Madrid venció 2-0 al Getafe en el Bernabéu."}},
    }


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(ct, "NEWS", tmp_path / "news.json")
    monkeypatch.setattr(ct, "STORE", tmp_path / "store.json")
    monkeypatch.setattr(ct, "WORK", tmp_path / "work")
    ct.save(ct.NEWS, {"items": [_item()]})
    return tmp_path


GOOD = {
    "fr": {"title": "Le Real Madrid bat Getafe", "summary": "Le Real Madrid a battu Getafe 2-0 au Bernabéu."},
    "en": {"title": "Real Madrid beat Getafe", "summary": "Real Madrid beat Getafe 2-0 at the Bernabéu."},
    "ar": {"title": "ريال مدريد يفوز على خيتافي", "summary": "فاز ريال مدريد على خيتافي 2-0 في ملعب برنابيو."},
}


def _done(items):
    ct.save(ct.WORK / "done.json", {"items": items})


def test_prepare_liste_les_langues_manquantes(env):
    ct.cmd_prepare(10)
    todo = json.loads((ct.WORK / "todo.json").read_text(encoding="utf-8"))["items"]
    assert todo[0]["missing"] == ["fr", "en", "ar"]
    assert todo[0]["src_lang"] == "es"


def test_ingest_rend_l_article_publiable(env):
    ct.cmd_prepare(10)
    _done([{"id": "a1", "i18n": GOOD}])
    ct.cmd_ingest()
    it = json.loads(ct.NEWS.read_text(encoding="utf-8"))["items"][0]
    for l in ("fr", "en", "es", "ar"):
        assert publishable(it, l), l


def test_traductions_douteuses_rejetees(env):
    ct.cmd_prepare(10)
    bad = {"fr": {"title": "El Real Madrid gana al Getafe", "summary": "El Real Madrid venció 2-0 al Getafe en el Bernabéu."},
           "ar": {"title": "Real Madrid beat Getafe", "summary": "Real Madrid beat Getafe 2-0 at home."},
           "en": {"title": "ok", "summary": "x"}}
    _done([{"id": "a1", "i18n": bad}])
    ct.cmd_ingest()
    it = json.loads(ct.NEWS.read_text(encoding="utf-8"))["items"][0]
    assert not publishable(it, "fr") and not publishable(it, "ar") and not publishable(it, "en")


def test_survit_au_rafraichissement_du_fil(env):
    """news-sync reconstruit news.json chaque heure : merge doit tout remettre."""
    ct.cmd_prepare(10)
    _done([{"id": "a1", "i18n": GOOD}])
    ct.cmd_ingest()
    ct.save(ct.NEWS, {"items": [_item()]})       # fil reconstruit, traductions perdues
    assert not publishable(_item(), "fr")
    ct.cmd_merge()
    it = json.loads(ct.NEWS.read_text(encoding="utf-8"))["items"][0]
    assert publishable(it, "fr") and publishable(it, "ar")


def test_article_modifie_ne_recoit_pas_l_ancienne_traduction(env):
    ct.cmd_prepare(10)
    _done([{"id": "a1", "i18n": GOOD}])
    ct.cmd_ingest()
    changed = _item()
    changed["i18n"]["es"]["summary"] = "Otro texto completamente distinto sobre el partido."
    ct.save(ct.NEWS, {"items": [changed]})
    ct.cmd_merge()
    it = json.loads(ct.NEWS.read_text(encoding="utf-8"))["items"][0]
    assert not publishable(it, "fr")


def test_non_article_ecarte_et_plus_redemande(env):
    ct.cmd_prepare(10)
    _done([{"id": "a1", "skip": "direct minute par minute"}])
    ct.cmd_ingest()
    it = json.loads(ct.NEWS.read_text(encoding="utf-8"))["items"][0]
    assert it["editorial"]["publish"] is False
    ct.save(ct.NEWS, {"items": [_item()]})
    ct.cmd_prepare(10)
    assert json.loads((ct.WORK / "todo.json").read_text(encoding="utf-8"))["items"] == []
