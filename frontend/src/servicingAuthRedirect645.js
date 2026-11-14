// S645_AUTH_LOGOUT: only handle SERVICING OS logout clicks; preserve all other UI.
// Frappe v15 documents GET /api/method/logout as returning JSON, not a page redirect.
let so645LoggingOut = false;
const so645LogoutNames = new Set([
  'logout', 'log out', 'sign out', 'signout', 'লগ আউট', 'লগআউট', 'সাইন আউট'
]);

function so645IsLogout(target) {
  if (!(target instanceof Element)) return false;
  const control = target.closest('a,button,[role="button"]');
  if (!control) return false;
  const href = (control.getAttribute('href') || '').trim();
  if (/\/api\/(?:v\d+\/)?method\/logout(?:[/?#]|$)/i.test(href)) return true;
  if (/^\/?(?:logout|sign-out)(?:[?#]|$)/i.test(href)) return true;
  const content = (control.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const label = (control.getAttribute('aria-label') || control.getAttribute('title') || '')
    .replace(/\s+/g, ' ').trim().toLowerCase();
  return so645LogoutNames.has(content) || so645LogoutNames.has(label);
}

async function so645Logout() {
  try {
    const response = await fetch('/api/method/logout', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      redirect: 'follow',
    });
    if (!response.ok) throw new Error('Logout request failed (' + response.status + ')');
    // Frappe responds with JSON; only navigate after successful server logout.
    window.location.replace('/servicing-login');
  } catch (error) {
    so645LoggingOut = false;
    console.error('SERVICING OS logout failed', error);
    window.alert('Could not complete logout. Check the connection and try again.');
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', (event) => {
    if (!so645IsLogout(event.target)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (so645LoggingOut) return;
    so645LoggingOut = true;
    void so645Logout();
  }, true);
}
