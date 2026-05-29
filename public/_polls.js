/* _polls.js — Firebase-backed polls.
 * Anonymous voting (1 vote per browser per poll, stored in localStorage).
 * Reuses to1000-contest Firebase project.
 * Aggregates stored in: polls/{pollId} { total: N, options: {key: count, ...} }
 */
(function() {
  'use strict';
  const FIREBASE_CONFIG = {
    apiKey: "AIzaSyBMZ8K29mhYSBNJDioJfaC7pDnEZA-kFwM",
    authDomain: "to1000-contest.firebaseapp.com",
    projectId: "to1000-contest",
    storageBucket: "to1000-contest.firebasestorage.app",
    messagingSenderId: "971084967012",
    appId: "1:971084967012:web:4a0f70f54e489d2dbec371"
  };
  let _app = null, _db = null, _dbMod = null;
  async function loadFb() {
    if (_app) return;
    const [appMod, dbMod] = await Promise.all([
      import('https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js'),
      import('https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js')
    ]);
    _app = appMod.initializeApp(FIREBASE_CONFIG, 'pollsApp');
    _db = dbMod.getFirestore(_app);
    _dbMod = dbMod;
  }

  function getVotedKey(pollId) { return `to1000_poll_voted_${pollId}`; }
  function hasVoted(pollId) { return !!localStorage.getItem(getVotedKey(pollId)); }
  function markVoted(pollId, option) { localStorage.setItem(getVotedKey(pollId), option); }
  function getVote(pollId) { return localStorage.getItem(getVotedKey(pollId)); }

  async function renderResults(container, pollId, data) {
    const total = data.total || 0;
    const options = data.options || {};
    container.querySelectorAll('.poll-option').forEach(btn => {
      const opt = btn.dataset.option;
      const count = options[opt] || 0;
      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
      btn.classList.add('voted');
      btn.querySelector('.bar').style.width = pct + '%';
      btn.querySelector('.pct').textContent = pct + '%';
      if (getVote(pollId) === opt) {
        btn.style.borderColor = '#D4AF37';
        btn.style.background = 'rgba(212,175,55,0.1)';
      }
    });
    const totalEl = container.querySelector('#poll-total-votes') || container.querySelector('.poll-total span');
    if (totalEl) totalEl.textContent = total.toLocaleString('fr-FR');
  }

  async function fetchAndRender(container, pollId) {
    await loadFb();
    const ref = _dbMod.doc(_db, 'polls', pollId);
    const snap = await _dbMod.getDoc(ref);
    const data = snap.exists() ? snap.data() : { total: 0, options: {} };
    await renderResults(container, pollId, data);
  }

  async function vote(container, pollId, option) {
    if (hasVoted(pollId)) return;
    markVoted(pollId, option);
    await loadFb();
    const ref = _dbMod.doc(_db, 'polls', pollId);
    // Atomic increment with create-if-missing
    try {
      await _dbMod.setDoc(ref, {
        total: _dbMod.increment(1),
        [`options.${option}`]: _dbMod.increment(1),
        last_vote_at: _dbMod.serverTimestamp(),
      }, { merge: true });
    } catch (err) {
      console.warn('poll vote failed', err);
      localStorage.removeItem(getVotedKey(pollId));
      return;
    }
    await fetchAndRender(container, pollId);
    if (window.gtag) gtag('event', 'poll_vote', { poll_id: pollId, option });
  }

  function init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const pollId = container.dataset.pollId || containerId;
    // Always show current results
    fetchAndRender(container, pollId).catch(err => {
      console.warn('poll load failed', err);
      // Still allow voting offline-first
    });
    // Click handlers
    container.querySelectorAll('.poll-option').forEach(btn => {
      btn.addEventListener('click', () => {
        if (hasVoted(pollId)) return;
        const opt = btn.dataset.option;
        vote(container, pollId, opt);
      });
    });
  }

  window.To1000Polls = { init };
})();
