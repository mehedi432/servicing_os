

/* SERVICING_OS_AUTH_GUARD_679: Page-level session monitor. No Vue patch. */
;(() => {
  'use strict';
  if (window.__SOS_AUTH_GUARD_679__) return;
  window.__SOS_AUTH_GUARD_679__ = true;
  const login = '/login?redirect-to=%2Fservicing-os';
  let pending = false;
  let navigating = false;
  async function checkSession() {
    if (pending || navigating || !navigator.onLine) return;
    pending = true;
    try {
      const response = await fetch('/api/method/servicing_os.auth_guard_679.session_state', {
        credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }
      });
      if (!response.ok) return; // Network/5xx/403 alone do not prove logout.
      const state = await response.json();
      if (state && state.message && state.message.logged_in === false) {
        navigating = true;
        window.location.replace(login);
      }
    } catch (_) {
      // Offline or temporarily unreachable servers are not logged-out sessions.
    } finally { pending = false; }
  }
  function checkOnVisible() { if (document.visibilityState === 'visible') void checkSession(); }
  function start() {
    void checkSession();
    window.setInterval(checkSession, 30000);
    window.addEventListener('focus', checkSession);
    window.addEventListener('online', checkSession);
    document.addEventListener('visibilitychange', checkOnVisible);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else { start(); }
})();
