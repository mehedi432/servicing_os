export async function frappeGet(method) {
  const response = await fetch(
    `/api/method/${method}`,
    {
      method: 'GET',
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json'
      }
    }
  )

  if (!response.ok) {
    throw new Error(
      `Frappe API failed: ${response.status}`
    )
  }

  const result = await response.json()

  return result.message
}

export function getAppInfo() {
  return frappeGet(
    'servicing_os.api.system.get_app_info'
  )
}

export function getShopConfig() {
  return frappeGet('servicing_os.api.shop.get_shop_config')
}


export async function receiveServiceJob(data) {
  const token = window.csrf_token || window.frappe?.csrf_token || '';

  const response = await fetch(
    '/api/method/servicing_os.api.service.receive_service_job',
    {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Frappe-CSRF-Token': token
      },
      body: JSON.stringify({ data })
    }
  );

  const result = await response.json();

  if (!response.ok || result.exc) {
    let detail = 'Unable to save service job';
    try {
      const messages = JSON.parse(result._server_messages || '[]');
      if (messages.length) {
        detail = JSON.parse(messages[0]).message || detail;
      }
    } catch (_) {}
    throw new Error(detail);
  }

  return result.message;
}


export function getDashboard() {
  return frappeGet('servicing_os.api.dashboard.get_dashboard')
}


export async function searchCustomers(query, signal) {
  const url = new URL(
    '/api/method/servicing_os.api.customer.search_customers',
    window.location.origin
  );

  url.searchParams.set('q', query);

  const response = await fetch(url, {
    method: 'GET',
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
    signal
  });

  const result = await response.json();

  if (!response.ok || result.exc) {
    throw new Error('Customer search failed. Check Customer permissions.');
  }

  return result.message || [];
}

export async function getServiceReceipt(jobName) {
  const url = new URL("/api/method/servicing_os.api.receipt.get_service_receipt", window.location.origin);
  url.searchParams.set("job_name", jobName);
  const response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  const result = await response.json();
  if (!response.ok || result.exc) throw new Error(result.message || "Unable to load Service Job receipt");
  return result.message;
}
