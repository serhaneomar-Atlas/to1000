/* Contrat de langue : une traduction absente ne devient jamais le texte source. */
(function(root){
  var engines={'gemini-editor':1,'gemini-edi':1,'gemini':1,'redaction':1};
  var pending={
    fr:['Version française indisponible','Cette nouvelle n’est pas encore disponible en français. Vous pouvez consulter la source originale.','Aucune nouvelle disponible en français pour cette sélection.'],
    en:['English version unavailable','This story is not yet available in English. You can read the original source.','No English stories are available for this selection.'],
    es:['Versión en español no disponible','Esta noticia aún no está disponible en español. Puedes consultar la fuente original.','No hay noticias en español para esta selección.'],
    ar:['النسخة العربية غير متاحة','هذا الخبر غير متاح بالعربية بعد. يمكنك الاطلاع على المصدر الأصلي.','لا توجد أخبار متاحة بالعربية ضمن هذا الاختيار.']
  };
  function pick(it,l){
    if(it.editorial&&it.editorial.publish===false)return null;
    var e=(it.i18n||{})[l],src=String((it.primary_source||{}).lang||'').slice(0,2).toLowerCase();
    if(!e||typeof e.title!=='string'||!e.title.trim()||typeof e.summary!=='string'||!e.summary.trim()||e.needs_translation)return null;
    if(l!==src&&!engines[e.engine])return null;
    if(l!==src&&((it.title&&e.title.trim()===it.title.trim())||(it.summary&&e.summary.trim()===it.summary.trim())))return null;
    if(l==='ar'&&(!/[\u0600-\u06ff]/.test(e.title)||!/[\u0600-\u06ff]/.test(e.summary)))return null;
    return e;
  }
  var api={pick:pick,pending:pending};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.To1000Locale=api;
})(typeof window!=='undefined'?window:this);
