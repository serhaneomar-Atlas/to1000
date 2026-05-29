/* world-cup/_wc.js — shared logic for hub + country pages
 * - Countdown to opening match
 * - Live ticker fetch + filter
 * - Match card relative time
 */

(function() {
  'use strict';

  // ─── Countdown ────────────────────────────────────────────────────
  function fmt2(n) { return String(n).padStart(2, '0'); }

  function updateCountdown(targetIso, opts = {}) {
    const el = document.getElementById(opts.id || 'wc-countdown');
    if (!el) return;
    const target = new Date(targetIso).getTime();
    function tick() {
      const now = Date.now();
      const diff = target - now;
      if (diff <= 0) {
        el.classList.add('live');
        el.innerHTML = '<div class="live-msg">🔴 LE MATCH A COMMENCÉ — Suivez en direct !</div>';
        clearInterval(timer);
        return;
      }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      el.innerHTML = `
        <div class="unit"><div class="num">${d}</div><div class="label">Jours</div></div>
        <div class="unit"><div class="num">${fmt2(h)}</div><div class="label">Heures</div></div>
        <div class="unit"><div class="num">${fmt2(m)}</div><div class="label">Min</div></div>
        <div class="unit"><div class="num">${fmt2(s)}</div><div class="label">Sec</div></div>`;
    }
    tick();
    const timer = setInterval(tick, 1000);
  }

  // ─── Live ticker ──────────────────────────────────────────────────
  function classifyKind(item) {
    const t = ((item.title_fr || item.title || '') + ' ' + (item.summary || '')).toLowerCase();
    if (/ronaldo|cr7|al nassr/.test(t)) return 'cr7';
    if (/maroc|morocco|hakimi|regragui|lions de l'atlas/.test(t)) return 'maroc';
    if (/portugal|seleção|fernandes|martinez/.test(t)) return 'portugal';
    if (/coupe du monde|world cup|wc 2026|cdm 2026|mondial/.test(t)) return 'wc';
    return 'foot';
  }

  function loadLiveTicker(filter) {
    const el = document.getElementById('live-ticker-scroll');
    if (!el) return;
    fetch('/news.json?_=' + Date.now())
      .then(r => r.json())
      .then(data => {
        let items = (data.items || []).map(it => ({...it, _kind: classifyKind(it)}));
        if (filter) items = items.filter(it => filter.includes(it._kind));
        items = items.slice(0, 20);
        if (items.length === 0) {
          el.innerHTML = '<a>Aucune actu pour le moment</a>';
          return;
        }
        // Duplicate for seamless marquee loop
        const html = items.map(it => {
          const title = it.title_fr || (it.i18n && it.i18n.fr && it.i18n.fr.title) || it.title;
          const slug = it.id || it.slug || '';
          const url = slug ? `/news/${slug}.html` : (it.url || '#');
          return `<a href="${url}">${escapeHtml(title)}</a><span class="sep">•</span>`;
        }).join(' ');
        el.innerHTML = html + html; // double for marquee
      })
      .catch(err => {
        console.warn('news.json fetch failed', err);
        el.innerHTML = '<a>Chargement des news…</a>';
      });
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  // ─── News grid (filtered list of cards) ───────────────────────────
  function loadNewsGrid(containerId, opts = {}) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const limit = opts.limit || 9;
    const filterKinds = opts.kinds || null; // ['wc', 'maroc'] etc.
    fetch('/news.json?_=' + Date.now())
      .then(r => r.json())
      .then(data => {
        let items = (data.items || []).map(it => ({...it, _kind: classifyKind(it)}));
        if (filterKinds) items = items.filter(it => filterKinds.includes(it._kind));
        items = items.slice(0, limit);
        if (items.length === 0) {
          el.innerHTML = '<p style="color:#888;text-align:center;padding:2rem">Aucune actu pour le moment. Reviens dans 30 min !</p>';
          return;
        }
        el.innerHTML = items.map(it => {
          const title = it.title_fr || (it.i18n && it.i18n.fr && it.i18n.fr.title) || it.title;
          const slug = it.id || it.slug || '';
          const url = slug ? `/news/${slug}.html` : (it.url || '#');
          const kindLabel = {cr7:'CR7', wc:'WC 2026', maroc:'MAROC', portugal:'PORTUGAL', foot:'FOOT'}[it._kind] || 'FOOT';
          const date = it.published_at ? new Date(it.published_at).toLocaleDateString('fr-FR', {day:'2-digit', month:'short'}) : '';
          return `
            <a class="news-card" href="${url}">
              <div class="news-meta">
                <span class="kind ${it._kind}">${kindLabel}</span>
                <span>${date}</span>
              </div>
              <div class="news-title">${escapeHtml(title)}</div>
            </a>`;
        }).join('');
      })
      .catch(err => {
        console.warn('news grid fetch failed', err);
        el.innerHTML = '<p style="color:#888">Erreur de chargement.</p>';
      });
  }

  // ─── Match card formatting ─────────────────────────────────────────
  function relativeTime(iso) {
    const now = Date.now();
    const t = new Date(iso).getTime();
    const diff = t - now;
    const abs = Math.abs(diff);
    const d = Math.floor(abs / 86400000);
    const h = Math.floor((abs % 86400000) / 3600000);
    if (diff > 0) {
      if (d > 0) return `dans ${d}j ${h}h`;
      return `dans ${h}h`;
    }
    return 'passé';
  }

  // ─── Expose globally ───────────────────────────────────────────────
  window.WC = {
    updateCountdown,
    loadLiveTicker,
    loadNewsGrid,
    relativeTime,
    classifyKind,
  };
})();
