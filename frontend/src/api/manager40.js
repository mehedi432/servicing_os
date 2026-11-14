// Private same-origin Frappe APIs; standard CSRF/session authentication is retained.
const PREFIX = '/api/method/servicing_os.api.counter40.';

function token() {
  return window.csrf_token || window.frappe?.csrf_token || '';
}
async function rpc(url, payload = null) {
  const options = {credentials:'same-origin', headers:{Accept:'application/json'}};
  if (payload !== null) {
    options.method = 'POST';
    options.headers['Content-Type'] = 'application/json';
    if (token()) options.headers['X-Frappe-CSRF-Token'] = token();
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The server returned an invalid response.'); }
  if (!response.ok || data.exc || data.exc_type) {
    const msg = Array.isArray(data._server_messages) ? data._server_messages[0] : null;
    let detail = data.message;
    if (!detail && msg) {
      try { detail = JSON.parse(msg).message; } catch { detail = msg; }
    }
    throw new Error(typeof detail === 'string' ? detail : (data.exception || `Request failed (${response.status})`));
  }
  return data.message;
}
export const getOverview40 = () => rpc(PREFIX + 'overview');
export const getBillPreview40 = (job) => rpc(PREFIX + 'job_bill_preview?job_name=' + encodeURIComponent(job));
export const findParts40 = (term) => rpc(PREFIX + 'part_search?query=' + encodeURIComponent(term));
export const createBill40 = (job, labour, parts, submitInvoice = false) => rpc(PREFIX + 'create_job_invoice', {
  job_name: job, labour_amount: labour, parts, submit_invoice: submitInvoice ? 1 : 0
});
export const registerJob40 = (payload) => rpc('/api/method/servicing_os.api.service.receive_service_job', {data: payload});
