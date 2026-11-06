#!/usr/bin/env python3
"""
translator.py — Editorial translation via Gemini API + MyMemory fallback.

Strategy:
    1. If GEMINI_API_KEY is set → use Gemini 2.0 Flash (editorial quality, 1500 RPD free).
    2. Otherwise (or if Gemini fails on an item) → fallback to MyMemory free API
       (anonymous, ~5000 words/day/IP; set MYMEMORY_EMAIL to lift to ~50k).
    3. If both fail → keep source-language original with needs_translation=true flag,
       frontend shows original with "Original DE" badge.

The cache (public/translations_cache.json) is shared across both engines,
keyed by sha1(text + src + dst). It survives across runs (committed to repo).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from news_locale import publishable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from lib.glossary import prompt_block, protected_terms, repair_calques
except ImportError:  # exécution hors arborescence scripts/ → dégradation douce
    def prompt_block(_terms, _langs=None): return ""
    def protected_terms(*_t, **_k): return []
    def repair_calques(text, _lang): return text


# Alias "latest" maintenu par Google → pointe toujours sur le dernier flash,
# ne déprécie jamais (gemini-2.0-flash a disparu et cassait le pipeline).
# Surchargeable par variable d'env GEMINI_MODEL si besoin de figer une version.
# Fix 2026-10-12 : l'alias « gemini-flash-latest » a basculé sur gemini-3.8-flash,
# qui « réfléchit » avant de répondre. Ces jetons de réflexion comptent dans
# maxOutputTokens (doc Google « thinking ») : avec 500 jetons, 47 appels sur 50
# finissaient en MAX_TOKENS → repli MyMemory → traductions rejetées par le contrat
# de langue → pages EN/ES/AR vides. On fige le modèle et on laisse de la marge.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
THINKING_HEADROOM_TOKENS = int(os.environ.get("GEMINI_THINKING_HEADROOM", "6000"))
GEMINI_URL_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "").strip()

# Fix 2026-11-06 : un modèle qui « réfléchit » dépasse souvent 30 s ; le
# TimeoutError était avalé sans trace → rédaction muette depuis le 23/10.
REQUEST_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "75"))
# Si le modèle figé disparaît (404) ou est refusé (400 « model »), on bascule
# sur l'alias stable de Google plutôt que de couper toute la rédaction.
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-flash-latest")

_WARNED: set = set()


def gh_warn(kind: str, msg: str) -> None:
    """Annotation GitHub Actions (lisible sans connexion), une fois par type.

    Avant, les échecs Gemini n'allaient que dans stderr : le run était « vert »,
    rien n'était traduit, et personne ne le voyait. Jamais la clé dans le texte.
    """
    if kind in _WARNED:
        return
    _WARNED.add(kind)
    print(f"::warning title=Gemini {kind}::{msg[:400]}", flush=True)
RATE_LIMIT_SLEEP = float(os.environ.get("GEMINI_RATE_SLEEP", "0.4"))  # palier PAYANT (haut débit) : plus besoin de brider
MYMEMORY_RATE_SLEEP = 0.3

LANG_NAMES = {
    "en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic",
    "de": "German", "it": "Italian", "pt": "Portuguese",
}


def log(msg: str) -> None:
    sys.stderr.write(f"[tr] {msg}\n")


def hash_key(text: str, src: str, dst: str) -> str:
    return hashlib.sha1(f"{src}>{dst}|{text}".encode("utf-8")).hexdigest()[:14]


class TranslationCache:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {}
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def get(self, key: str) -> Optional[dict]:
        return self.data.get(key)

    def set(self, key: str, value: dict) -> None:
        self.data[key] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if len(self.data) > 5000:
            keys = list(self.data.keys())
            for k in keys[:-5000]:
                del self.data[k]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=0)


class Translator:
    def __init__(self, cache_path: Optional[Path] = None):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.gemini_enabled = bool(self.api_key)
        # Allow disabling MyMemory (slow) when frontend client-side translation
        # is preferred. Set DISABLE_MYMEMORY=1 to skip server-side fallback.
        self.mymemory_enabled = os.environ.get("DISABLE_MYMEMORY", "").strip() != "1"
        self.enabled = self.gemini_enabled or self.mymemory_enabled
        self.cache = TranslationCache(cache_path) if cache_path else None
        self._calls_gemini = 0
        self._calls_mymemory = 0
        self._cache_hits = 0
        self._failures = 0
        if self.gemini_enabled:
            log("Gemini API enabled (editorial quality)")
        else:
            log("GEMINI_API_KEY not set — using MyMemory (free, ~5k words/day/IP)")

    def stats(self) -> dict:
        return {
            "gemini_calls": self._calls_gemini,
            "mymemory_calls": self._calls_mymemory,
            "cache_hits": self._cache_hits,
            "failures": self._failures,
            "gemini_enabled": self.gemini_enabled,
        }

    def _call_gemini(self, system: str, user: str, max_tokens: int = 500) -> Optional[str]:
        if not self.gemini_enabled:
            return None
        model = getattr(self, "model", GEMINI_MODEL)
        url = GEMINI_URL_TMPL.format(model=model, key=self.api_key)
        body = json.dumps({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.3, "maxOutputTokens": max_tokens + THINKING_HEADROOM_TOKENS,
                "responseMimeType": "application/json",
            },
        }).encode("utf-8")
        req = Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json",
            "User-Agent": "to1000-translator/1.0",
        })
        # Retry sur 429 : le free tier Gemini ≈ 15 req/min ; avec ~50 articles à
        # reviewer, on dépasse la fenêtre → backoff + retry au lieu d'abandonner
        # (sinon la plupart des items perdent le rédacteur en chef et retombent
        # sur MyMemory). Le backoff cale aussi le débit sous la limite.
        for attempt in range(4):
            limit = getattr(self, "max_gemini_calls", None)
            if limit is not None and self._calls_gemini >= limit:
                log("Budget d’appels atteint — arrêt sans nouvelle requête")
                return None
            self._calls_gemini += 1
            try:
                with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(8.0 * (attempt + 1))   # 8s, 16s, 24s
                    continue
                try:
                    detail = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
                except Exception:
                    detail = ""
                detail = detail.replace(self.api_key, "***") if self.api_key else detail
                # Modèle retiré/renommé : bascule une fois sur l'alias stable.
                if (e.code == 404 or (e.code == 400 and "model" in detail.lower())) \
                        and model != GEMINI_FALLBACK_MODEL:
                    gh_warn(f"modèle {model} indisponible",
                            f"HTTP {e.code} — {detail} → bascule sur {GEMINI_FALLBACK_MODEL}")
                    self.model = GEMINI_FALLBACK_MODEL
                    return self._call_gemini(system, user, max_tokens)
                self._failures += 1
                gh_warn(f"HTTP {e.code}", f"modèle {model} : {detail or e.reason}")
                log(f"  → Gemini HTTPError {e.code} {detail}")
                return None
            except (URLError, TimeoutError) as e:
                self._failures += 1
                gh_warn(type(e).__name__, f"modèle {model}, délai {REQUEST_TIMEOUT}s : {getattr(e, 'reason', e)}")
                log(f"  → Gemini {type(e).__name__}: {e}")
                return None
            except json.JSONDecodeError:
                self._failures += 1
                gh_warn("réponse illisible", f"modèle {model} : corps non JSON")
                return None
            time.sleep(RATE_LIMIT_SLEEP)
            try:
                candidates = payload.get("candidates") or []
                candidate = candidates[0] if candidates else {}
                reason = candidate.get("finishReason") or "NO_CANDIDATE"
                parts = candidate.get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                if reason != "STOP" or not text:
                    self._failures += 1
                    _usage = payload.get("usageMetadata") or {}
                    gh_warn(f"fin {reason}",
                            f"modèle {payload.get('modelVersion', model)} : texte={bool(text)}, "
                            f"jetons réflexion={_usage.get('thoughtsTokenCount')}, "
                            f"sortie={_usage.get('candidatesTokenCount')}, plafond={max_tokens + THINKING_HEADROOM_TOKENS}"
                            + (f", blocage={payload.get('promptFeedback')}" if payload.get('promptFeedback') else ""))
                    log(f"Gemini réponse inutilisable: finish={reason}, texte={bool(text)}, model={payload.get('modelVersion', model)}")
                    return None
                return text
            except (KeyError, IndexError, AttributeError):
                return None
        return None

    def _call_mymemory(self, text: str, src: str, dst: str) -> Optional[str]:
        if not text:
            return None
        params = {"q": text[:500], "langpair": f"{src}|{dst}"}
        if MYMEMORY_EMAIL:
            params["de"] = MYMEMORY_EMAIL
        url = f"{MYMEMORY_URL}?{urlencode(params)}"
        try:
            req = Request(url, headers={"User-Agent": "to1000-translator/1.0"})
            with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            self._failures += 1
            return None
        self._calls_mymemory += 1
        time.sleep(MYMEMORY_RATE_SLEEP)
        try:
            rd = payload.get("responseData", {})
            result = rd.get("translatedText", "").strip()
            if not result or result.lower() == text.lower():
                return None
            if result.startswith("MYMEMORY WARNING") or "QUERY LENGTH LIMIT" in result.upper():
                return None
            return result
        except (KeyError, AttributeError):
            return None

    def _parse_json_block(self, text: str) -> Optional[dict]:
        if not text:
            return None
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        if start < 0:
            return None
        depth, end, in_str, esc = 0, -1, False, False
        for i, c in enumerate(text[start:], start=start):
            if esc:
                esc = False
                continue
            if c == "\\":
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end < 0:
            return None
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            return None

    def editorialize_pair(self, title: str, summary: str, src: str,
                          targets: list) -> Optional[dict]:
        """One Gemini call → {lang: {title, summary, ...}} for src + targets.

        `summary` is a concise, NEUTRAL 'essential' rewrite (the key facts to
        retain), not a literal translation — this is the editorial digest the
        reader gets so they don't need to open the article. Returns None if
        Gemini is disabled, fails, or comes back incomplete, so the caller can
        fall back to literal translate_pair().
        """
        if not self.gemini_enabled:
            return None
        title = (title or "").strip()
        summary = (summary or "").strip()
        if not title:
            return None
        langs = list(dict.fromkeys([src] + [t for t in targets if t != src]))
        # v2 : même raison que edtv6 — la consigne de translittération arabe a
        # changé, les paquets en cache doivent être refaits.
        cache_key = "edi4:" + hash_key(title + "|" + summary[:200], src, ",".join(langs))
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached and all(publishable({"title": title, "summary": summary,
                    "primary_source": {"lang": src}, "i18n": cached}, l) for l in langs):
                self._cache_hits += 1
                return cached
        names = ", ".join(f'"{l}" ({LANG_NAMES.get(l, l)})' for l in langs)
        system = (
            "You are a senior multilingual football news editor. From the source "
            "title and text, output a JSON object with ONE key per language code "
            f"({names}). For each language provide: \"title\" = a faithful, natural "
            "translation of the title; \"summary\" = the ESSENTIAL information to "
            "retain, rewritten concisely. Summary rules: 1 to 2 sentences, ~35 words "
            "max, neutral and factual, straight to the point — the reader should not "
            "need to open the article. Forbidden: clickbait, hype adjectives, "
            "exclamation marks, rhetorical questions, 'read more' calls, filler. "
            "Keep only key facts (who, what, numbers, stakes). Preserve proper nouns. "
            'Respond with valid JSON only: {"fr":{"title":"...","summary":"..."}, ...}'
            + prompt_block(protected_terms(title, summary), langs)
        )
        user = json.dumps({"source_lang": src, "title": title,
                           "text": (summary or title)[:800]}, ensure_ascii=False)
        raw = self._call_gemini(system, user, max_tokens=1100)
        parsed = self._parse_json_block(raw) if raw else None
        if not parsed:
            return None
        out: dict = {}
        for l in langs:
            e = parsed.get(l) or {}
            t = str(e.get("title", "")).strip()[:300]
            s = str(e.get("summary", "")).strip()[:600]
            if t and s:
                out[l] = {"title": repair_calques(t, l),
                          "summary": repair_calques(s, l),
                          "needs_translation": False, "engine": "gemini-edi"}
        if len(out) < len(langs):   # incomplete → let caller fall back
            return None
        if self.cache:
            self.cache.set(cache_key, out)
        return out

    def translate_pair(self, title: str, summary: str, src: str,
                       targets: list) -> dict:
        out: dict = {src: {"title": title, "summary": summary, "needs_translation": False}}
        title = (title or "").strip()
        summary = (summary or "").strip()
        if not title:
            return out

        for dst in targets:
            if dst == src:
                continue

            cache_key = hash_key(title + "|" + summary[:200], src, dst)
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached and cached.get("title") and cached.get("summary") and not cached.get("needs_translation") and cached.get("title") != title and cached.get("summary") != summary:
                    self._cache_hits += 1
                    # Les entrées mises en cache AVANT une nouvelle règle de
                    # réparation resserviraient l'erreur à chaque refresh
                    # (un « قبطان » MyMemory de juillet reviendrait sans fin).
                    # On répare aussi à la lecture — idempotent sur une entrée
                    # déjà propre.
                    for _f in ("title", "summary"):
                        if cached.get(_f):
                            cached[_f] = repair_calques(cached[_f], dst)
                    out[dst] = cached
                    continue

            translated = None

            # Try Gemini first
            if self.gemini_enabled:
                src_name = LANG_NAMES.get(src, src)
                dst_name = LANG_NAMES.get(dst, dst)
                system = (
                    f"You are the editor-in-chief of a European electronic football "
                    f"magazine. Translate from {src_name} to {dst_name}: clear, direct, "
                    f"idiomatic prose with zero clickbait. Translate the meaning, not "
                    f"word-for-word. Preserve all proper nouns. Respond with valid JSON "
                    f'only: {{"title": "...", "summary": "..."}}'
                    + prompt_block(protected_terms(title, summary), [dst])
                )
                user = json.dumps({"title": title, "summary": summary[:600]}, ensure_ascii=False)
                raw = self._call_gemini(system, user)
                parsed = self._parse_json_block(raw) if raw else None
                if parsed and parsed.get("title") and (not summary or parsed.get("summary")):
                    translated = {
                        "title": str(parsed.get("title", title)).strip()[:300],
                        "summary": str(parsed.get("summary", "")).strip()[:600],
                        "needs_translation": False,
                        "engine": "gemini",
                    }

            # Fallback to MyMemory
            if translated is None and self.mymemory_enabled:
                t_title = self._call_mymemory(title, src, dst)
                t_summary = self._call_mymemory(summary[:500], src, dst) if summary else ""
                if t_title and (not summary or t_summary):
                    translated = {
                        "title": t_title[:300],
                        "summary": (t_summary or "")[:600],
                        "needs_translation": False,
                        "engine": "mymemory",
                    }

            # Last resort: source-language fallback
            if translated is None:
                translated = {
                    "title": title,
                    "summary": summary,
                    "needs_translation": True,
                }

            # Filet déterministe : même une traduction MyMemory mot-à-mot ne
            # doit pas laisser passer « Royal Madrid » ou « Cordoue CF ».
            for _f in ("title", "summary"):
                if translated.get(_f):
                    translated[_f] = repair_calques(translated[_f], dst)

            out[dst] = translated
            if self.cache and not translated.get("needs_translation"):
                self.cache.set(cache_key, translated)

        return out


if __name__ == "__main__":
    cache = Path(__file__).parent.parent / "public" / "translations_cache.json"
    tr = Translator(cache_path=cache)
    res = tr.translate_pair(
        "Rekord - Ronaldo zum sechsten Mal bei einer WM",
        "Der Portugiese wird mit 41 Jahren bei der Weltmeisterschaft 2026 dabei sein.",
        src="de", targets=["en", "fr", "es", "ar"],
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("\nStats:", tr.stats())
    if tr.cache:
        tr.cache.save()
