"""Régressions sans réseau : langue demandée, réponses partielles et faux succès."""
import copy, importlib.util, json, re, subprocess, sys, unittest
from pathlib import Path
from unittest.mock import patch
SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from news_locale import publishable, PENDING
from news_to_html import render_article, best_title, best_summary
from rss_generator import lang_ok, tr
from translator import Translator
import translator

def item():
    return {"id": "locale-test", "title": "Source original", "summary": "Source facts",
            "url": "https://example.test/story", "primary_source": {"lang": "de", "name": "Source"},
            "published_at": "2026-09-24T20:00:00Z",
            "i18n": {l: {"title": t, "summary": s, "engine": "gemini-editor", "needs_translation": False}
                     for l,t,s in [("fr","Victoire du Portugal","Un seul but validé."),
                                   ("en","Portugal wins","One goal was awarded."),
                                   ("es","Victoria de Portugal","Se concedió un gol."),
                                   ("ar","فوز البرتغال","تم احتساب هدف واحد.")]}}

class LocaleTests(unittest.TestCase):
    def test_ready_four_languages(self):
        for l in PENDING:
            self.assertTrue(publishable(item(), l))
            self.assertTrue(lang_ok(item(), l))
    def test_missing_never_falls_back(self):
        it=item(); del it["i18n"]["fr"]
        self.assertFalse(lang_ok(it,"fr"))
        self.assertEqual(tr(it,"fr","title"),"")
        self.assertEqual(best_title(it),PENDING["fr"][0])
        self.assertEqual(best_summary(it),PENDING["fr"][1])
    def test_partial_passthrough_rejected(self):
        for field in ("title","summary"):
            for value in ("", item()[field]):
                it=item(); it["i18n"]["fr"][field]=value
                self.assertFalse(publishable(it,"fr"))
    def test_draft_and_rejected(self):
        for engine in ("mymemory","unknown"):
            it=item(); it["i18n"]["fr"]["engine"]=engine
            self.assertFalse(publishable(it,"fr"))
        it=item(); it["editorial"]={"publish":False}
        self.assertFalse(publishable(it,"fr"))
    def test_arabic_requires_arabic_both_fields(self):
        it=item(); it["i18n"]["ar"]["summary"]="English sentence"
        self.assertFalse(publishable(it,"ar"))
    def test_article_pending_and_rtl(self):
        it=item(); del it["i18n"]["ar"]
        page=render_article(it,[it])
        self.assertIn(PENDING["ar"][0],page)
        self.assertNotIn("if(e.fallback)H.dir='ltr'",page)
        self.assertIn("apply(LANG)",page)
    def test_partial_gemini_not_accepted(self):
        t=Translator(); t.gemini_enabled=True; t.mymemory_enabled=False
        with patch.object(t,"_call_gemini",return_value='{"title":"Titre français"}'):
            out=t.translate_pair("English title","English facts","en",["fr"])
        self.assertTrue(out["fr"]["needs_translation"])
    def test_multilingual_partial_not_cached(self):
        t=Translator(); t.gemini_enabled=True
        with patch.object(t,"_call_gemini",return_value='{"en":{"title":"Title","summary":"Facts"},"fr":{"title":"Titre"}}'):
            self.assertIsNone(t.editorialize_pair("Title","Facts","en",["fr"]))
    def test_truncated_gemini_counts_failure(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*_): pass
            def read(self): return json.dumps({"candidates":[{"finishReason":"MAX_TOKENS","content":{"parts":[{"text":"{"}]}}]}).encode()
        t=Translator(); t.gemini_enabled=True; t.api_key="test-key"
        with patch.object(translator,"urlopen",return_value=Response()),patch.object(translator.time,"sleep"):
            self.assertIsNone(t._call_gemini("system","user"))
        self.assertEqual(t._failures,1)
    def test_retry_budget_counts_failed_requests(self):
        from urllib.error import HTTPError
        t=Translator(); t.gemini_enabled=True; t.api_key="test-key"; t.max_gemini_calls=2
        with patch.object(translator,"urlopen",side_effect=HTTPError("https://example.test",429,"rate",{},None)) as request,patch.object(translator.time,"sleep"):
            self.assertIsNone(t._call_gemini("system","user"))
            self.assertIsNone(t._call_gemini("system","user"))
        self.assertEqual(request.call_count,2)
        self.assertEqual(t.stats()["gemini_calls"],2)

    def test_node_python_contract_parity(self):
        cases=[item()]
        for f in ("title","summary"):
            for v in ("",item()[f]):
                it=item();it["i18n"]["fr"][f]=v;cases.append(it)
        it=item();it["editorial"]={"publish":False};cases.append(it)
        it=item();it["i18n"]={};cases.append(it)
        script="const L=require('./public/locale-news.js');const a="+json.dumps(cases,ensure_ascii=False)+";console.log(JSON.stringify(a.map(i=>['fr','en','es','ar'].map(l=>!!L.pick(i,l)))));"
        result=subprocess.run(["node","-e",script],cwd=SCRIPTS.parent,capture_output=True,text=True,encoding="utf-8",check=True)
        self.assertEqual(json.loads(result.stdout),[[publishable(i,l) for l in PENDING] for i in cases])

if __name__=="__main__": unittest.main()
