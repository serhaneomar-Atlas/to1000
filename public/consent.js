/* =========================================================================
   consent.js — Bannière cookies + Google Consent Mode v2 pour to1000.com

   Chargé en SYNCHRONE avant le loader gtag.js (injection : voir
   scripts/add_consent_snippet.py). Pose les défauts de consentement dans
   dataLayer AVANT l'initialisation de GA4 : sans choix de l'utilisateur,
   tout est "denied" → GA4 ne dépose AUCUN cookie (pings sans cookie
   uniquement, comportement documenté de Consent Mode v2).

   - Choix stocké 13 mois dans localStorage (to1000_consent_v1), re-demandé
     après expiration (recommandation CNIL).
   - Bouton "Cookies" discret en bas de page pour changer d'avis à tout
     moment (window.to1000Consent.open()).
   - i18n FR/EN/ES/AR via localStorage['to1000_lang'] (clé partagée du site),
     RTL pour l'arabe.
   - Quand le compte AdSense existera : remplacer cette bannière par le CMP
     certifié Google (Privacy & messaging). Les signaux Consent Mode v2
     posés ici (ad_storage, ad_user_data, ad_personalization,
     analytics_storage) sont exactement ceux qu'il utilisera.
   ========================================================================= */
(function () {
  'use strict';

  var KEY = 'to1000_consent_v1';
  var MAX_AGE_MS = 13 * 30 * 24 * 3600 * 1000; // ~13 mois (CNIL)

  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }

  function readChoice() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return null;
      var c = JSON.parse(raw);
      if (!c || typeof c.analytics !== 'boolean' || !c.ts) return null;
      if (Date.now() - c.ts > MAX_AGE_MS) { localStorage.removeItem(KEY); return null; }
      return c;
    } catch (e) { return null; }
  }

  function saveChoice(analytics, ads) {
    try { localStorage.setItem(KEY, JSON.stringify({ analytics: analytics, ads: ads, ts: Date.now() })); } catch (e) {}
  }

  function signals(analytics, ads) {
    var g = function (b) { return b ? 'granted' : 'denied'; };
    return {
      analytics_storage: g(analytics),
      ad_storage: g(ads),
      ad_user_data: g(ads),
      ad_personalization: g(ads),
      functionality_storage: 'granted',
      security_storage: 'granted'
    };
  }

  var stored = readChoice();
  // Défauts AVANT gtag('js') : denied sans choix, sinon le choix mémorisé.
  gtag('consent', 'default', signals(stored ? stored.analytics : false, stored ? stored.ads : false));
  gtag('set', 'url_passthrough', true);

  /* ── UI ─────────────────────────────────────────────────────────────── */
  var I18N = {
    fr: { msg: 'On utilise des cookies pour mesurer l’audience (Google Analytics) et, plus tard, financer le site par la publicité. Vous choisissez.',
          accept: 'Tout accepter', refuse: 'Refuser', more: 'En savoir plus', cookies: 'Cookies' },
    en: { msg: 'We use cookies to measure our audience (Google Analytics) and, later, to fund the site with ads. Your call.',
          accept: 'Accept all', refuse: 'Refuse', more: 'Learn more', cookies: 'Cookies' },
    es: { msg: 'Usamos cookies para medir la audiencia (Google Analytics) y, más adelante, financiar el sitio con publicidad. Tú decides.',
          accept: 'Aceptar todo', refuse: 'Rechazar', more: 'Más información', cookies: 'Cookies' },
    ar: { msg: 'نستخدم ملفات تعريف لقياس الجمهور (Google Analytics) ولاحقًا لتمويل الموقع بالإعلانات. القرار لك.',
          accept: 'قبول الكل', refuse: 'رفض', more: 'المزيد', cookies: 'ملفات تعريف' }
  };

  function lang() {
    var l = '';
    try { l = localStorage.getItem('to1000_lang') || ''; } catch (e) {}
    if (!I18N[l]) l = (document.documentElement.lang || 'fr').slice(0, 2);
    return I18N[l] ? l : 'fr';
  }

  var CSS =
    '#t1k-consent{position:fixed;z-index:99990;left:16px;right:16px;bottom:16px;max-width:680px;margin:0 auto;' +
    'background:#0d1118;border:1px solid rgba(242,193,78,.35);border-top:3px solid #f2c14e;border-radius:10px;' +
    'padding:18px 20px;box-shadow:0 12px 40px rgba(0,0,0,.6);color:#eef2f6;' +
    'font-family:"Hanken Grotesk",system-ui,sans-serif;font-size:14.5px;line-height:1.5}' +
    '#t1k-consent p{margin:0 0 14px}' +
    '#t1k-consent .t1k-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}' +
    '#t1k-consent button{cursor:pointer;border-radius:6px;padding:10px 18px;font-weight:700;' +
    'font-family:"Oswald","Hanken Grotesk",sans-serif;font-size:14px;letter-spacing:.04em;text-transform:uppercase;border:1px solid #f2c14e}' +
    '#t1k-accept{background:#f2c14e;color:#05070b}' +
    '#t1k-refuse{background:transparent;color:#f2c14e}' +
    '#t1k-consent a{color:#9aa6b4;text-decoration:underline;font-size:13px;margin-left:auto}' +
    '[dir="rtl"] #t1k-consent a{margin-left:0;margin-right:auto}' +
    '#t1k-reopen{position:fixed;z-index:99989;left:12px;bottom:12px;background:#0d1118;color:#9aa6b4;' +
    'border:1px solid rgba(154,166,180,.35);border-radius:999px;padding:6px 12px;font-size:12px;cursor:pointer;' +
    'font-family:"Hanken Grotesk",system-ui,sans-serif;opacity:.75}' +
    '#t1k-reopen:hover{opacity:1;color:#f2c14e;border-color:#f2c14e}' +
    '@media (max-width:480px){#t1k-consent{left:8px;right:8px;bottom:8px;padding:14px 14px}}';

  function ensureCss() {
    if (document.getElementById('t1k-consent-css')) return;
    var s = document.createElement('style');
    s.id = 't1k-consent-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function removeBanner() {
    var el = document.getElementById('t1k-consent');
    if (el) el.parentNode.removeChild(el);
  }

  function decide(analytics, ads) {
    saveChoice(analytics, ads);
    gtag('consent', 'update', signals(analytics, ads));
    removeBanner();
    showReopen();
  }

  function showBanner() {
    if (document.getElementById('t1k-consent')) return;
    ensureCss();
    var t = I18N[lang()];
    var box = document.createElement('div');
    box.id = 't1k-consent';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-live', 'polite');
    box.setAttribute('aria-label', t.cookies);
    box.innerHTML =
      '<p>🍪 ' + t.msg + '</p>' +
      '<div class="t1k-row">' +
      '<button id="t1k-accept" type="button">' + t.accept + '</button>' +
      '<button id="t1k-refuse" type="button">' + t.refuse + '</button>' +
      '<a href="/privacy">' + t.more + '</a>' +
      '</div>';
    document.body.appendChild(box);
    document.getElementById('t1k-accept').addEventListener('click', function () { decide(true, true); });
    document.getElementById('t1k-refuse').addEventListener('click', function () { decide(false, false); });
  }

  function showReopen() {
    if (document.getElementById('t1k-reopen')) return;
    ensureCss();
    var b = document.createElement('button');
    b.id = 't1k-reopen';
    b.type = 'button';
    b.textContent = '🍪 ' + I18N[lang()].cookies;
    b.addEventListener('click', function () {
      b.parentNode.removeChild(b);
      showBanner();
    });
    document.body.appendChild(b);
  }

  function init() {
    if (readChoice()) { showReopen(); } else { showBanner(); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.to1000Consent = {
    open: function () { removeBanner(); showBanner(); },
    status: readChoice
  };
})();
