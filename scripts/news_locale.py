"""Contrat partagé des articles, cartes et flux : pas de repli vers une autre langue.
Ce garde vérifie la complétude/provenance, pas la qualité linguistique sémantique.
"""
import re
ENGINES_AFFICHABLES = {"gemini-editor", "gemini-edi", "gemini", "redaction"}
PENDING = {
    "fr": ("Version française indisponible", "Cette nouvelle n’est pas encore disponible en français. Vous pouvez consulter la source originale."),
    "en": ("English version unavailable", "This story is not yet available in English. You can read the original source."),
    "es": ("Versión en español no disponible", "Esta noticia aún no está disponible en español. Puedes consultar la fuente original."),
    "ar": ("النسخة العربية غير متاحة", "هذا الخبر غير متاح بالعربية بعد. يمكنك الاطلاع على المصدر الأصلي."),
}
def publishable(item, lang):
    if (item.get("editorial") or {}).get("publish") is False:
        return False
    e = (item.get("i18n") or {}).get(lang) or {}
    if not all(isinstance(e.get(f), str) and e[f].strip() for f in ("title", "summary")) or e.get("needs_translation"):
        return False
    src = str((item.get("primary_source") or {}).get("lang") or "")[:2].lower()
    if lang != src:
        if e.get("engine") not in ENGINES_AFFICHABLES:
            return False
        if any(item.get(f) and e[f].strip() == str(item[f]).strip() for f in ("title", "summary")):
            return False
    if lang == "ar" and not all(re.search(r"[\u0600-\u06ff]", e[f]) for f in ("title", "summary")):
        return False
    return True
