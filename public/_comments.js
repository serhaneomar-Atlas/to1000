/* _comments.js — Firebase-backed comments per page.
 * Login required (Google OAuth). Comments stored in: comments/{pageId}/items/{commentId}
 * Soft-moderation: spam filter (URLs limit, length, banlist), admin-only delete.
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

  // Admin UIDs — to populate after first Omar login
  const ADMIN_UIDS = []; // ex: ['xyz123abc']

  // Basic blocklist
  const BANNED_WORDS = ['viagra', 'casino', 'http://bit.ly', 'pornhub', 'spam', 'crypto pump'];

  let _app = null, _auth = null, _db = null, _authMod = null, _dbMod = null;
  let _user = null;
  let _pageId = null;
  let _container = null;

  async function loadFb() {
    if (_app) return;
    const [appMod, authMod, dbMod] = await Promise.all([
      import('https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js'),
      import('https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js'),
      import('https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js')
    ]);
    // Reuse default if contest already initialized; else use named
    try {
      _app = appMod.initializeApp(FIREBASE_CONFIG, 'commentsApp');
    } catch (e) {
      _app = appMod.getApp('commentsApp');
    }
    _auth = authMod.getAuth(_app);
    _db = dbMod.getFirestore(_app);
    _authMod = authMod;
    _dbMod = dbMod;
  }

  function isBanned(text) {
    const t = text.toLowerCase();
    if (BANNED_WORDS.some(w => t.includes(w))) return true;
    // URL spam : more than 2 URLs = spam
    const urls = (text.match(/https?:\/\//gi) || []).length;
    if (urls > 2) return true;
    // ALL CAPS spam : > 80% caps in messages > 20 chars
    if (text.length > 20) {
      const caps = (text.match(/[A-Z]/g) || []).length;
      const letters = (text.match(/[A-Za-z]/g) || []).length;
      if (letters > 0 && caps / letters > 0.8) return true;
    }
    return false;
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function relTime(iso) {
    const t = new Date(iso).getTime();
    const diff = (Date.now() - t) / 1000;
    if (diff < 60) return 'à l\'instant';
    if (diff < 3600) return `il y a ${Math.floor(diff/60)} min`;
    if (diff < 86400) return `il y a ${Math.floor(diff/3600)} h`;
    if (diff < 2592000) return `il y a ${Math.floor(diff/86400)} j`;
    return new Date(iso).toLocaleDateString('fr-FR');
  }

  async function renderList() {
    const listEl = _container.querySelector('#comments-list');
    const countEl = _container.querySelector('#comments-count');
    if (!listEl) return;
    try {
      const colRef = _dbMod.collection(_db, 'comments', _pageId, 'items');
      const q = _dbMod.query(colRef, _dbMod.orderBy('ts', 'desc'), _dbMod.limit(100));
      const snap = await _dbMod.getDocs(q);
      const items = [];
      snap.forEach(doc => items.push({ id: doc.id, ...doc.data() }));
      if (countEl) countEl.textContent = items.length;
      if (items.length === 0) {
        listEl.innerHTML = '<p style="color:#888;text-align:center;padding:2rem">Sois le premier à écrire un message !</p>';
        return;
      }
      const isAdmin = _user && ADMIN_UIDS.includes(_user.uid);
      listEl.innerHTML = items.map(c => `
        <div class="comment" data-id="${c.id}">
          <div class="head">
            ${c.photo ? `<img class="avatar" src="${escapeHtml(c.photo)}" alt="" loading="lazy">` : '<div class="avatar"></div>'}
            <div>
              <div class="author">${escapeHtml(c.author || 'Anonyme')}</div>
              <div class="when">${relTime(c.ts && c.ts.toDate ? c.ts.toDate().toISOString() : new Date().toISOString())}</div>
            </div>
            ${isAdmin ? `<button class="del" style="margin-left:auto;background:transparent;border:1px solid #444;color:#888;padding:0.2rem 0.5rem;border-radius:4px;cursor:pointer;font-size:0.7rem">Suppr.</button>` : ''}
          </div>
          <div class="body">${escapeHtml(c.text)}</div>
        </div>
      `).join('');
      // Admin delete handlers
      if (isAdmin) {
        listEl.querySelectorAll('.del').forEach(btn => {
          btn.addEventListener('click', async () => {
            const id = btn.closest('.comment').dataset.id;
            if (!confirm('Supprimer ce commentaire ?')) return;
            try {
              await _dbMod.deleteDoc(_dbMod.doc(_db, 'comments', _pageId, 'items', id));
              renderList();
            } catch (e) { console.warn(e); }
          });
        });
      }
    } catch (err) {
      console.warn('comments load failed', err);
      listEl.innerHTML = '<p style="color:#888;padding:1rem">Impossible de charger les commentaires.</p>';
    }
  }

  async function signIn() {
    await loadFb();
    const provider = new _authMod.GoogleAuthProvider();
    try {
      const result = await _authMod.signInWithPopup(_auth, provider);
      _user = result.user;
      showComposer();
      renderList();
    } catch (err) {
      console.warn('signin failed', err);
      alert('Connexion impossible : ' + err.message);
    }
  }

  function showComposer() {
    _container.querySelector('#comments-signin').style.display = 'none';
    const composer = _container.querySelector('#comments-composer');
    composer.style.display = 'block';
    _container.querySelector('#comment-user').textContent =
      `Connecté en tant que ${_user.displayName || _user.email}`;
    const textarea = _container.querySelector('#comment-text');
    const sendBtn = _container.querySelector('#comment-send');
    textarea.addEventListener('input', () => {
      sendBtn.disabled = textarea.value.trim().length < 2;
    });
    sendBtn.addEventListener('click', async () => {
      const text = textarea.value.trim();
      if (text.length < 2) return;
      if (isBanned(text)) {
        alert('Ton message a été détecté comme spam. Réessaie sans liens et sans MAJUSCULES.');
        return;
      }
      sendBtn.disabled = true;
      try {
        await _dbMod.addDoc(
          _dbMod.collection(_db, 'comments', _pageId, 'items'),
          {
            text: text,
            author: _user.displayName || _user.email.split('@')[0],
            authorUid: _user.uid,
            photo: _user.photoURL || null,
            ts: _dbMod.serverTimestamp(),
            pageId: _pageId,
          }
        );
        textarea.value = '';
        renderList();
        if (window.gtag) gtag('event', 'comment_post', { page: _pageId });
      } catch (err) {
        console.warn('post failed', err);
        alert('Échec de publication : ' + err.message);
      }
      sendBtn.disabled = false;
    });
  }

  async function init(containerId) {
    _container = document.getElementById(containerId);
    if (!_container) return;
    _pageId = _container.dataset.pageId || containerId;
    // Render existing comments without login
    loadFb().then(renderList).catch(err => console.warn(err));
    // Wire sign-in button
    const signinBtn = _container.querySelector('#signin-btn');
    if (signinBtn) signinBtn.addEventListener('click', signIn);
    // Auto-detect if already signed in
    await loadFb();
    _authMod.onAuthStateChanged(_auth, (user) => {
      if (user) {
        _user = user;
        showComposer();
        renderList();
      }
    });
  }

  window.To1000Comments = { init };
})();
