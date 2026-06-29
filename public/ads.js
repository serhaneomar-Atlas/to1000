/* =========================================================================
   ads.js — Init publicitaire to1000.com (voir ADS.md)
   - Flag global ON/OFF (défaut OFF : espaces réservés mais aucun script tiers)
   - Lazy-load (IntersectionObserver), viewability-friendly
   - N'affiche un slot QUE si une régie est branchée ; sinon état "empty"
   - Sticky-bottom mobile dismissable
   - Hook AdSense prêt
   ========================================================================= */
(function () {
  'use strict';

  var ADS_ENABLED = (typeof window.ADS_ENABLED === 'boolean') ? window.ADS_ENABLED : false;
  var AD_NETWORK = window.ADS_NETWORK || 'none';
  var ADSENSE_CLIENT = window.ADSENSE_CLIENT || ''; // ex: 'ca-pub-XXXXXXXXXXXXXXXX'
  var html = document.documentElement;

  function markEmpty() {
    document.querySelectorAll('.ad-slot').forEach(function (s) {
      if (!s.getAttribute('data-ad-state')) s.setAttribute('data-ad-state', 'empty');
    });
  }

  if (!ADS_ENABLED || AD_NETWORK === 'none' || !ADSENSE_CLIENT) {
    html.classList.toggle('ads-off', !ADS_ENABLED);
    markEmpty();
    return; // aucun script tiers tant que la pub n'est pas branchée
  }

  var libLoaded = false;
  function loadAdsenseLib() {
    if (libLoaded) return;
    libLoaded = true;
    var s = document.createElement('script');
    s.async = true; s.crossOrigin = 'anonymous';
    s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + ADSENSE_CLIENT;
    document.head.appendChild(s);
  }

  function fillSlot(slot) {
    if (slot.getAttribute('data-ad-state') === 'filled') return;
    if (AD_NETWORK === 'adsense') {
      loadAdsenseLib();
      var unit = slot.querySelector('.ad-unit');
      if (!unit) return;
      var ins = document.createElement('ins');
      ins.className = 'adsbygoogle';
      ins.style.display = 'block';
      ins.setAttribute('data-ad-client', ADSENSE_CLIENT);
      ins.setAttribute('data-ad-slot', slot.getAttribute('data-ad-unit-id') || '');
      var fmt = slot.getAttribute('data-ad-format');
      if (fmt) ins.setAttribute('data-ad-format', fmt);
      if (slot.getAttribute('data-full-width') === '1') ins.setAttribute('data-full-width-responsive', 'true');
      unit.appendChild(ins);
      try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) {}
    }
    slot.setAttribute('data-ad-state', 'filled');
  }

  function observe() {
    var slots = [].slice.call(document.querySelectorAll('.ad-slot:not([data-ad-state="filled"])'));
    if (!('IntersectionObserver' in window)) { slots.forEach(fillSlot); return; }
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (e) { if (e.isIntersecting) { fillSlot(e.target); obs.unobserve(e.target); } });
    }, { rootMargin: '320px 0px' });
    slots.forEach(function (s) { io.observe(s); });
  }

  function initSticky() {
    var bar = document.querySelector('.ad-sticky');
    if (!bar) return;
    if (sessionStorage.getItem('to1000_ad_sticky_closed') === '1') { bar.style.display = 'none'; return; }
    setTimeout(function () { bar.classList.add('ad-in'); }, 1200);
    var btn = bar.querySelector('.ad-close');
    if (btn) btn.addEventListener('click', function () {
      bar.classList.remove('ad-in');
      try { sessionStorage.setItem('to1000_ad_sticky_closed', '1'); } catch (e) {}
      setTimeout(function () { bar.style.display = 'none'; }, 360);
    });
  }

  function boot() { markEmpty(); observe(); initSticky(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.To1000Ads = { refresh: function () { markEmpty(); observe(); } };
})();
