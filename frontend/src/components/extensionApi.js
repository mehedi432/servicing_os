// SERVICING OS 6.21-6.23. Session-authenticated Frappe calls; no external UI.
export async function moduleApi(method, args = {}, post = false) {
  return servicingApi('menu_extensions', method, args, post);
}

export async function servicingApi(namespace, method, args = {}, post = false) {
  const path = '/api/method/servicing_os.api.' + namespace + '.' + method;
  const url = new URL(path, window.location.origin);
  const options = { method: post ? 'POST' : 'GET', credentials: 'same-origin',
    headers: { Accept: 'application/json' } };
  if (post) {
    const cookie = (document.cookie.split('; ').find(v => v.startsWith('csrf_token=')) || '').split('=').slice(1).join('=');
    const csrf = window.frappe?.csrf_token || window.csrf_token || (cookie ? decodeURIComponent(cookie) : '');
    options.headers['Content-Type'] = 'application/json';
    if (csrf) options.headers['X-Frappe-CSRF-Token'] = csrf;
    options.body = JSON.stringify(args);
  } else {
    Object.entries(args).forEach(([k,v]) => {
      if (v !== '' && v !== null && v !== undefined) url.searchParams.set(k, String(v));
    });
  }
  let response;
  try { response = await fetch(url.toString(), options); }
  catch { throw new Error('Cannot connect to SERVICING OS. Check your connection.'); }
  let data;
  try { data = await response.json(); }
  catch { throw new Error(`Server returned an unexpected response (${response.status}).`); }
  if (!response.ok || data.exc || data.exc_type) {
    let msg = null;
    try {
      const messages = JSON.parse(data._server_messages || '[]');
      if (messages.length) msg = JSON.parse(messages[messages.length - 1]).message;
    } catch { /* preserve fallback */ }
    throw new Error(msg || data.message?.message || data.exception || 'Server request failed.');
  }
  return data.message;
}
