/**
 * to1000.com — Goal Notification Service Worker
 * Polls stats.json every 10 minutes.
 * Fires a browser notification when CR7 scores a new goal.
 */

const POLL_INTERVAL = 10 * 60 * 1000; // 10 minutes
const STATS_URL     = '/stats.json';
const CACHE_KEY     = 'to1000-last-goals';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
  schedulePoll();
});

// ─── Polling via alarms-like setInterval inside SW ──────────────────────────
let _pollTimer = null;

function schedulePoll() {
  if (_pollTimer) clearInterval(_pollTimer);
  _pollTimer = setInterval(poll, POLL_INTERVAL);
  // Also run once immediately on activation
  poll();
}

async function poll() {
  try {
    const res  = await fetch(STATS_URL + '?t=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    const current = data.goals_scored ?? data.goals ?? 0;
    if (!current) return;

    const stored = await getLastGoals();

    if (stored !== null && current > stored) {
      const added = current - stored;
      await fireNotification(current, added);
    }

    await setLastGoals(current);
  } catch (e) {
    // silent — network offline etc.
  }
}

// ─── Notification ────────────────────────────────────────────────────────────
async function fireNotification(total, added) {
  const remaining = 1000 - total;
  const title = added === 1
    ? `⚽ CR7 just scored! ${total}/1000`
    : `⚽ CR7 scored ${added} goals! Now ${total}/1000`;
  const body = remaining > 0
    ? `Only ${remaining} goal${remaining === 1 ? '' : 's'} left to reach 1000. History is close! 🔥`
    : `🏆 CRISTIANO RONALDO HAS SCORED HIS 1000th GOAL! HISTORY MADE!`;
  const icon  = '/images/cr7-era-03.jpg';
  const badge = '/favicon.png';

  const clients = await self.clients.matchAll({ type: 'window' });

  // Prefer showing in-page toast if tab is already open
  for (const client of clients) {
    client.postMessage({ type: 'NEW_GOAL', total, added, remaining });
  }

  // Always fire system notification
  await self.registration.showNotification(title, {
    body,
    icon,
    badge,
    tag:    'cr7-goal',
    renotify: true,
    vibrate: [200, 100, 200],
    data:   { url: 'https://to1000.com' },
    actions: [
      { action: 'open', title: '🚀 See it now' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  });
}

// ─── Notification click ──────────────────────────────────────────────────────
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      for (const c of clients) {
        if (c.url.includes('to1000.com') && 'focus' in c) return c.focus();
      }
      return self.clients.openWindow('https://to1000.com');
    })
  );
});

// ─── Storage helpers (IDB-lite via Cache API as KV) ─────────────────────────
async function getLastGoals() {
  try {
    const cache = await caches.open('to1000-meta');
    const r     = await cache.match(CACHE_KEY);
    if (!r) return null;
    const txt = await r.text();
    return parseInt(txt, 10) || null;
  } catch { return null; }
}

async function setLastGoals(n) {
  try {
    const cache = await caches.open('to1000-meta');
    await cache.put(CACHE_KEY, new Response(String(n)));
  } catch { /* */ }
}

// ─── Message channel from main thread ────────────────────────────────────────
self.addEventListener('message', (e) => {
  if (e.data?.type === 'FORCE_POLL')  { poll(); }
  if (e.data?.type === 'SET_GOALS')   { setLastGoals(e.data.goals); }
  if (e.data?.type === 'START_POLL')  { schedulePoll(); }
});
