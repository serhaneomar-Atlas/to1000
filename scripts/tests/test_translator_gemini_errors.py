"""Échecs Gemini : visibles (annotation GitHub) et rattrapés (repli de modèle).

Contexte : du 23/10 au 06/11/2026, chaque appel Gemini échouait et le workflow
restait « vert » ; plus aucune traduction n'était produite, sans aucune trace.
"""
import io
import json
import sys
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import translator  # noqa: E402


def _tr():
    with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "SECRET-KEY"}):
        t = translator.Translator()
    translator._WARNED.clear()
    return t


def _ok_response(text='{"ok": true}'):
    body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
    r = mock.MagicMock()
    r.read.return_value = json.dumps(body).encode()
    r.__enter__.return_value = r
    return r


def _http_error(code, message):
    payload = json.dumps({"error": {"message": message}}).encode()
    return HTTPError("https://x?key=SECRET-KEY", code, "err", {}, io.BytesIO(payload))


def test_modele_retire_bascule_sur_l_alias(capsys):
    t = _tr()
    calls = []

    def fake(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise _http_error(404, "models/gemini-3.8-flash is not found")
        return _ok_response()

    with mock.patch.object(translator, "urlopen", side_effect=fake), \
         mock.patch.object(translator.time, "sleep"):
        out = t._call_gemini("sys", "user", 100)
    assert out == '{"ok": true}'
    assert translator.GEMINI_FALLBACK_MODEL in calls[1]
    printed = capsys.readouterr().out
    assert "::warning" in printed and "SECRET-KEY" not in printed


def test_timeout_signale_au_lieu_d_etre_avale(capsys):
    t = _tr()
    with mock.patch.object(translator, "urlopen", side_effect=URLError("timed out")), \
         mock.patch.object(translator.time, "sleep"):
        assert t._call_gemini("sys", "user", 100) is None
    assert "::warning title=Gemini URLError" in capsys.readouterr().out


def test_cle_refusee_signalee_sans_fuite(capsys):
    t = _tr()
    err = _http_error(403, "API key SECRET-KEY has been suspended")
    with mock.patch.object(translator, "urlopen", side_effect=err), \
         mock.patch.object(translator.time, "sleep"):
        assert t._call_gemini("sys", "user", 100) is None
    out = capsys.readouterr().out
    assert "HTTP 403" in out and "SECRET-KEY" not in out
