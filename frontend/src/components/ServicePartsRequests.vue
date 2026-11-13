<script setup>
// SERVICING_PARTS_UI_615C4
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';

const jobs = ref([]);
const requests = ref([]);
const catalog = ref([]);
const permissions = ref({ manager: false, can_edit: false, can_delete: false, can_cancel: false });
const jobName = ref('');
const search = ref('');
const showingResults = ref(true);
const searching = ref(false);
const highlighted = ref(0);
const chosen = ref(null);
const qty = ref(1);
const cart = ref([]);
const notes = ref('');
const loading = ref(false);
const saving = ref(false);
const action = ref('');
const error = ref('');
const notice = ref('');
const expanded = ref('');
const details = ref({});
const requestSearch = ref('');
let searchTimer = null;
let searchSerial = 0;

const visibleRequests = computed(() => requests.value.filter(r =>
  [r.name, r.custom_service_job, r.status].some(v => String(v || '').toLowerCase().includes(requestSearch.value.toLowerCase()))));
const selectedJob = computed(() => jobs.value.find(j => j.name === jobName.value));

function csrf() {
  return window.frappe?.csrf_token || window.csrf_token ||
    decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('csrf_token='))?.split('=').slice(1).join('=') || '');
}
function errMessage(body, fallback) {
  if (body?._server_messages) {
    try {
      const messages = JSON.parse(body._server_messages);
      const last = JSON.parse(messages[messages.length - 1]);
      if (last?.message) return String(last.message).replace(/<[^>]*>/g, '');
    } catch (_) {}
  }
  return body?.exception || body?.message?.message || fallback;
}
async function api(module, name, data = {}, post = false) {
  const url = new URL(`/api/method/servicing_os.api.${module}.${name}`, window.location.origin);
  const opts = { method: post ? 'POST' : 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } };
  if (post) {
    opts.headers['Content-Type'] = 'application/json';
    opts.headers['X-Frappe-CSRF-Token'] = csrf();
    opts.body = JSON.stringify(data);
  } else {
    Object.entries(data).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url, opts);
  let body;
  try { body = await res.json(); } catch (_) { throw Error(`Unexpected server response (${res.status})`); }
  if (!res.ok || body.exc || body.exc_type) throw Error(errMessage(body, 'Request failed'));
  return body.message;
}
async function loadParts(q = '') {
  const serial = ++searchSerial;
  searching.value = true;
  try {
    const response = await api('parts_request_manage', 'search_saleable_parts', { search: q });
    if (serial === searchSerial) {
      catalog.value = response?.items || [];
      highlighted.value = 0;
    }
  } catch (e) {
    if (serial === searchSerial) error.value = e.message;
  } finally {
    if (serial === searchSerial) searching.value = false;
  }
}
watch(search, (v) => {
  if (chosen.value && v !== `${chosen.value.item_name} (${chosen.value.item_code})`) chosen.value = null;
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadParts(v), 220);
});
onBeforeUnmount(() => { if (searchTimer) clearTimeout(searchTimer); });

async function refresh() {
  loading.value = true; error.value = '';
  try {
    const [w, r, p] = await Promise.all([
      api('workstation', 'get_workstation'),
      api('parts_request', 'list_parts_requests'),
      api('parts_request_manage', 'manage_permissions'),
    ]);
    jobs.value = (w?.jobs || []).filter(j => !['Delivered', 'Cancelled'].includes(j.status));
    requests.value = r?.requests || [];
    permissions.value = p || permissions.value;
    if (!jobs.value.some(j => j.name === jobName.value)) jobName.value = jobs.value[0]?.name || '';
  } catch (e) { error.value = e.message; }
  finally { loading.value = false; }
}
function choosePart(part) {
  chosen.value = part;
  search.value = `${part.item_name} (${part.item_code})`;
  showingResults.value = false;
}
function moveHighlight(delta) {
  if (!showingResults.value) showingResults.value = true;
  if (catalog.value.length) highlighted.value = (highlighted.value + delta + catalog.value.length) % catalog.value.length;
}
function chooseHighlight() {
  if (showingResults.value && catalog.value[highlighted.value]) choosePart(catalog.value[highlighted.value]);
  else showingResults.value = true;
}
function addPart() {
  error.value = ''; notice.value = '';
  if (!chosen.value) { error.value = 'Select an Item from the results list below the search box.'; showingResults.value = true; return; }
  if (!Number.isFinite(Number(qty.value)) || Number(qty.value) <= 0) { error.value = 'Enter a valid positive quantity.'; return; }
  const quantity = Number(qty.value);
  const existing = cart.value.find(x => x.item_code === chosen.value.item_code);
  if (existing) existing.qty += quantity;
  else cart.value.push({ ...chosen.value, qty: quantity });
  chosen.value = null; search.value = ''; qty.value = 1; showingResults.value = true;
}
function removeCart(code) { cart.value = cart.value.filter(x => x.item_code !== code); }
async function createRequest() {
  error.value = ''; notice.value = '';
  if (!jobName.value || !cart.value.length) { error.value = 'Select a Service Job and add one or more parts.'; return; }
  if (cart.value.some(x => !(Number(x.qty) > 0) || !Number.isFinite(Number(x.qty)))) {
    error.value = 'All quantities must be positive numbers.'; return;
  }
  if (!window.confirm(`Create one Draft Material Request with ${cart.value.length} Item(s) for ${jobName.value}?`)) return;
  saving.value = true;
  try {
    const result = await api('parts_request', 'create_multi_parts_request', {
      job_name: jobName.value,
      items: cart.value.map(x => ({ item_code: x.item_code, qty: Number(x.qty) })),
      remarks: notes.value,
    }, true);
    cart.value = []; notes.value = '';
    await refresh();
    notice.value = `Draft ${result.material_request} created. No stock has been deducted.`;
  } catch (e) { error.value = e.message; }
  finally { saving.value = false; }
}
async function detailsFor(r, force = false) {
  if (!force && expanded.value === r.name) { expanded.value = ''; return; }
  error.value = '';
  try {
    details.value[r.name] = await api('parts_request_manage', 'request_details', { material_request: r.name });
    expanded.value = r.name;
  } catch (e) { error.value = e.message; }
}
async function approve(r) {
  if (action.value) return;
  if (!window.confirm(`Approve ${r.name}? This submits the Material Request, but does not deduct stock.`)) return;
  action.value = r.name; error.value = ''; notice.value = '';
  try {
    await api('parts_request', 'approve_parts_request', { material_request: r.name }, true);
    await refresh(); expanded.value = '';
    notice.value = `${r.name} approved. No stock deducted.`;
  } catch (e) { error.value = e.message; }
  finally { action.value = ''; }
}
async function manage(r, kind, row = null) {
  if (action.value) return;
  error.value = ''; notice.value = '';
  let d = details.value[r.name];
  try {
    if (!d) d = await api('parts_request_manage', 'request_details', { material_request: r.name });
    details.value[r.name] = d;
    const choices = {
      remove: `Remove ${row?.item_name || row?.item_code} from ${r.name}?`,
      delete: `Permanently DELETE Draft ${r.name}? This cannot be undone.`,
      cancel: `CANCEL submitted ${r.name}? ERPNext will preserve its history.`,
    };
    if (!window.confirm(choices[kind])) return;
    action.value = r.name;
    const params = { material_request: r.name, expected_modified: d.modified };
    if (kind === 'remove') params.row_name = row.row_name;
    const method = { remove: 'remove_draft_part', delete: 'delete_draft_request', cancel: 'cancel_submitted_request' }[kind];
    await api('parts_request_manage', method, params, true);
    delete details.value[r.name]; expanded.value = '';
    await refresh();
    notice.value = kind === 'remove' ? 'Part removed from Draft.' : kind === 'delete' ? `${r.name} deleted.` : `${r.name} cancelled.`;
  } catch (e) { error.value = e.message; }
  finally { action.value = ''; }
}
function desk(r) { window.open(`/app/material-request/${encodeURIComponent(r.name)}`, '_blank', 'noopener,noreferrer'); }
function date(v) { return v ? String(v).slice(0, 10) : '—'; }
onMounted(async () => { await Promise.all([refresh(), loadParts()]); });
</script>

<template>
  <section class="mpr-root" aria-label="Repair spare parts requests">
    <header class="mpr-header">
      <div>
        <p class="mpr-eyebrow">SERVICING OS · ERPNext MATERIAL REQUEST</p>
        <h2>Spare Parts Requests</h2>
        <p>Choose a repair, add multiple selling Items, then create one draft request.</p>
      </div>
      <button type="button" class="mpr-btn mpr-btn-outline" :disabled="loading" @click="refresh">{{ loading ? 'Refreshing…' : 'Refresh' }}</button>
    </header>
    <p v-if="error" role="alert" class="mpr-alert mpr-error">{{ error }}</p>
    <p v-if="notice" role="status" class="mpr-alert mpr-success">{{ notice }}</p>

    <div class="mpr-columns">
      <form class="mpr-panel" @submit.prevent="createRequest">
        <div class="mpr-title"><span class="mpr-round">01</span><h3>Request parts</h3></div>
        <label class="mpr-label">Assigned Service Job
          <select v-model="jobName" required>
            <option value="" disabled>Choose a repair job</option>
            <option v-for="j in jobs" :key="j.name" :value="j.name">{{ j.name }} · {{ j.brand }} {{ j.device_model }} · {{ j.status }}</option>
          </select>
        </label>
        <p v-if="!jobs.length" class="mpr-muted">There are no open Service Jobs available to this account.</p>
        <div v-if="selectedJob" class="mpr-job"><strong>{{ selectedJob.name }}</strong><span>{{ selectedJob.customer_name }} · {{ selectedJob.brand }} {{ selectedJob.device_model }}</span></div>

        <label class="mpr-label" for="mpr-part-search">Find a sales-enabled stock Item</label>
        <div class="mpr-search">
          <span class="mpr-search-icon" aria-hidden="true">⌕</span>
          <input id="mpr-part-search" v-model="search" autocomplete="off" role="combobox"
            :aria-expanded="showingResults" aria-controls="mpr-parts-results"
            aria-autocomplete="list" placeholder="Search SSD, RAM, item code…"
            @focus="showingResults=true" @input="showingResults=true" @keydown.down.prevent="moveHighlight(1)"
            @keydown.up.prevent="moveHighlight(-1)" @keydown.enter.prevent="chooseHighlight"
            @keydown.esc.prevent="showingResults=false" />
        </div>
        <div v-if="chosen" class="mpr-picked"><span>Selected: <strong>{{ chosen.item_name }}</strong> · {{ chosen.item_code }}</span><button type="button" @click="chosen=null;search='';showingResults=true">Change</button></div>
        <div v-if="showingResults" id="mpr-parts-results" class="mpr-results" role="listbox" aria-label="Matching spare parts">
          <p v-if="searching" class="mpr-result-empty">Searching…</p>
          <p v-else-if="!catalog.length" class="mpr-result-empty">No matching stock Items. Create an Item in ERPNext with Maintain Stock and Is Sales Item enabled.</p>
          <template v-else>
            <button v-for="(p,i) in catalog" :key="p.item_code" type="button" role="option"
              :aria-selected="highlighted===i" :class="['mpr-result', {'mpr-result-active':highlighted===i}]"
              @mouseenter="highlighted=i" @click="choosePart(p)">
              <span><strong>{{ p.item_name }}</strong><small>{{ p.item_code }}</small></span>
              <span class="mpr-qty-label">{{ p.available_qty }} {{ p.uom }}<small>available</small></span>
            </button>
          </template>
        </div>
        <p class="mpr-muted">Zero-stock Items can be requested; stock will be checked again before issuing.</p>

        <div class="mpr-add-row">
          <label class="mpr-label">Quantity
            <input v-model.number="qty" type="number" min="0.001" step="any" />
          </label>
          <button class="mpr-btn mpr-btn-outline" type="button" @click="addPart" :disabled="!jobs.length">+ Add Part</button>
        </div>
        <div class="mpr-cart">
          <div class="mpr-cart-head"><strong>Parts in this request</strong><span>{{ cart.length }} Items</span></div>
          <p v-if="!cart.length" class="mpr-empty">Select an Item above and click Add Part.</p>
          <div v-for="p in cart" :key="p.item_code" class="mpr-cart-row">
            <span class="mpr-cart-name"><strong>{{ p.item_name }}</strong><small>{{ p.item_code }}</small></span>
            <input v-model.number="p.qty" type="number" step="any" min="0.001" :aria-label="'Quantity for '+p.item_code" />
            <button type="button" class="mpr-link-danger" @click="removeCart(p.item_code)">Remove</button>
          </div>
        </div>
        <label class="mpr-label">Reason / symptoms
          <textarea v-model="notes" maxlength="500" rows="2" placeholder="Why are these parts required?"></textarea>
        </label>
        <button class="mpr-btn mpr-btn-primary mpr-submit" type="submit" :disabled="saving || !jobName || !cart.length">
          {{ saving ? 'Creating…' : `Create Draft Request · ${cart.length} part${cart.length===1?'':'s'}` }}
        </button>
        <p class="mpr-muted">Requests do not reduce stock or post accounting entries.</p>
      </form>

      <section class="mpr-panel">
        <div class="mpr-title"><span class="mpr-round">02</span><h3>Requests & approvals</h3><span class="mpr-count">{{ requests.length }}</span></div>
        <label class="mpr-label">Find a request
          <input v-model="requestSearch" placeholder="Request number, job, status…" />
        </label>
        <p v-if="!visibleRequests.length" class="mpr-empty">No matching requests yet.</p>
        <div v-for="r in visibleRequests" :key="r.name" class="mpr-request">
          <div class="mpr-request-top"><strong>{{ r.name }}</strong>
            <span :class="['mpr-badge',r.docstatus===0?'mpr-badge-draft':r.docstatus===1?'mpr-badge-approved':'mpr-badge-cancel']">
              {{ r.docstatus===0?'Draft':r.docstatus===1?'Approved':'Cancelled' }}
            </span>
          </div>
          <p class="mpr-muted">{{ r.custom_service_job }} · {{ date(r.transaction_date) }}</p>
          <div class="mpr-actions">
            <button type="button" class="mpr-btn mpr-btn-outline" @click="detailsFor(r)">{{ expanded===r.name?'Hide parts':'View / Edit parts' }}</button>
            <button type="button" class="mpr-btn mpr-btn-outline" @click="desk(r)">Open in ERPNext ↗</button>
            <button v-if="permissions.manager && r.docstatus===0" type="button" class="mpr-btn mpr-btn-primary" :disabled="!!action" @click="approve(r)">Approve</button>
          </div>
          <div v-if="expanded===r.name && details[r.name]" class="mpr-request-details">
            <p v-if="details[r.name].stock_entry_links.length" class="mpr-warn">Linked Stock Entry: {{ details[r.name].stock_entry_links.join(', ') }}. Resolve it in ERPNext before cancelling or deleting.</p>
            <div v-for="line in details[r.name].items" :key="line.row_name" class="mpr-detail-row">
              <span><strong>{{ line.item_name || line.item_code }}</strong><small>{{ line.qty }} {{ line.uom }}</small></span>
              <button v-if="permissions.can_edit && r.docstatus===0 && details[r.name].items.length>1" type="button"
                class="mpr-link-danger" :disabled="!!action || !!details[r.name].stock_entry_links.length" @click="manage(r,'remove',line)">Remove Part</button>
            </div>
          </div>
          <div v-if="permissions.manager" class="mpr-admin-actions">
            <button v-if="r.docstatus===0 && permissions.can_delete" type="button" class="mpr-link-danger" :disabled="!!action" @click="manage(r,'delete')">Delete Draft</button>
            <button v-if="r.docstatus===1 && permissions.can_cancel" type="button" class="mpr-link-danger" :disabled="!!action" @click="manage(r,'cancel')">Cancel Request</button>
            <span v-if="r.docstatus===0 && !permissions.can_delete" class="mpr-muted">Delete requires Material Request Delete permission.</span>
            <span v-if="r.docstatus===1 && !permissions.can_cancel" class="mpr-muted">Cancel requires Material Request Cancel permission.</span>
          </div>
        </div>
        <p class="mpr-muted mpr-foot">Drafts can be deleted. Submitted requests must be cancelled through ERPNext rules; linked Stock Entries block unsafe changes. Issued stock is never reversed by deleting a request.</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.mpr-root{background:#faf8f4;color:#493d30;border:1px solid #e9e0d3;border-radius:18px;padding:20px;margin:0 0 18px;min-width:0}
.mpr-root *{box-sizing:border-box}.mpr-header{display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #e6ded1;padding-bottom:16px;margin-bottom:16px}
.mpr-header h2{font-size:21px;font-weight:750;letter-spacing:-.035em;margin:3px 0}.mpr-header p{font-size:12px;color:#8b7d6b}.mpr-eyebrow{font-size:10px!important;letter-spacing:.14em;font-weight:800;color:#a68a62!important}
.mpr-columns{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;align-items:start}.mpr-panel{background:#fffdfa;border:1px solid #e8ded0;border-radius:14px;padding:17px;min-width:0}
.mpr-title{display:flex;align-items:center;gap:9px;margin-bottom:16px}.mpr-title h3{font-size:15px;font-weight:760}.mpr-round{display:grid;place-items:center;width:29px;height:29px;border-radius:9px;background:#eee3d3;color:#725739;font-weight:800;font-size:12px}.mpr-count{margin-left:auto;color:#9c896f;font-size:12px}
.mpr-label{display:grid;gap:7px;margin-bottom:14px;color:#675743;font-size:12px;font-weight:700}.mpr-root input,.mpr-root select,.mpr-root textarea{border:1px solid #ded2c1;background:#fff;color:#423729;border-radius:10px;padding:11px 12px;width:100%;min-width:0;font-size:13px;line-height:1.3}.mpr-root select{appearance:auto}.mpr-root textarea{resize:vertical}
.mpr-job{background:#f8f1e6;border:1px solid #e6d8c3;border-radius:10px;padding:10px 12px;margin:-2px 0 15px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12px}.mpr-job span{color:#8e7b64}
.mpr-search{display:flex;position:relative;align-items:center}.mpr-search input{padding-left:34px!important}.mpr-search-icon{position:absolute;left:12px;font-size:22px;color:#9b876b;pointer-events:none}
.mpr-results{display:block!important;position:relative!important;z-index:1;background:#fff;max-height:245px;overflow-y:auto;border:1px solid #d9ccb7;border-radius:12px;margin:-5px 0 10px;padding:5px;box-shadow:0 3px 14px #78604810}
.mpr-result{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;text-align:left;border:0;border-radius:8px;background:#fff;color:#53432e;padding:9px 10px;cursor:pointer;font-size:12px}.mpr-result:hover,.mpr-result-active{background:#f4ecde}.mpr-result strong,.mpr-result small{display:block;overflow-wrap:anywhere}.mpr-result small,.mpr-qty-label small{color:#94836d;font-size:10px;margin-top:3px}.mpr-qty-label{flex:0 0 auto;font-weight:700;text-align:right;white-space:nowrap;font-size:11px}.mpr-result-empty{padding:17px 10px;color:#988774;font-size:12px}
.mpr-picked{display:flex;justify-content:space-between;align-items:center;gap:10px;border:1px solid #d2e6d4;background:#f0f8ef;border-radius:9px;padding:9px 11px;font-size:12px;margin-top:8px}.mpr-picked button{font-weight:750;text-decoration:underline;color:#536e43}
.mpr-muted{font-size:11px;color:#958570;line-height:1.55;margin:8px 0}.mpr-add-row{display:flex;align-items:end;gap:10px;margin:12px 0}.mpr-add-row label{flex:0 1 170px;margin:0}.mpr-btn{border:1px solid #dacbb6;border-radius:10px;padding:10px 14px;font-size:12px;font-weight:750;cursor:pointer;white-space:normal}.mpr-btn-outline{background:#fffdf8;color:#6f5738}.mpr-btn-primary{background:#765d3e;color:#fff;border-color:#765d3e}.mpr-btn:disabled,.mpr-link-danger:disabled{opacity:.5;cursor:not-allowed}.mpr-btn:hover:not(:disabled){filter:brightness(.97)}
.mpr-cart{border:1px solid #e6ddcf;background:#fbf7f0;border-radius:12px;padding:11px;margin:10px 0 15px}.mpr-cart-head{display:flex;justify-content:space-between;font-size:12px;color:#78664f}.mpr-empty{text-align:center;padding:16px;color:#9d8b76;font-size:12px}.mpr-cart-row{display:grid;grid-template-columns:minmax(0,1fr) 78px auto;gap:8px;align-items:center;border-top:1px solid #e8dfd0;margin-top:10px;padding-top:10px}.mpr-cart-name strong,.mpr-cart-name small{display:block;font-size:12px}.mpr-cart-name small{color:#96836b;font-size:10px;margin-top:3px}.mpr-cart-row input{padding:8px}.mpr-link-danger{background:transparent;border:0;padding:5px;color:#a24c3d;font-weight:750;font-size:11px;cursor:pointer;text-decoration:underline}.mpr-submit{width:100%;padding:13px}
.mpr-alert{border-radius:10px;padding:12px 14px;font-size:13px;margin-bottom:14px}.mpr-error{background:#fce7e4;color:#8a352b}.mpr-success{background:#e5f3e7;color:#2f7045}
.mpr-request{padding:13px 0;border-top:1px solid #eee5d9}.mpr-request-top,.mpr-actions,.mpr-admin-actions{display:flex;align-items:center;flex-wrap:wrap;gap:8px}.mpr-request-top{justify-content:space-between}.mpr-request-top strong{font-size:12px;overflow-wrap:anywhere}.mpr-actions{margin:10px 0}.mpr-actions .mpr-btn{padding:8px 10px}.mpr-badge{border-radius:20px;padding:4px 9px;font-size:10px;font-weight:700}.mpr-badge-draft{background:#efe6d8;color:#806140}.mpr-badge-approved{background:#e3f1e6;color:#39714f}.mpr-badge-cancel{background:#f4e5e2;color:#96503e}
.mpr-request-details{background:#f9f5ef;padding:10px;border-radius:10px;margin:9px 0}.mpr-detail-row{display:flex;align-items:center;justify-content:space-between;gap:9px;padding:9px 0;border-top:1px solid #e9ded0}.mpr-detail-row:first-of-type{border-top:0}.mpr-detail-row strong,.mpr-detail-row small{display:block;font-size:11px}.mpr-detail-row small{color:#94816a;margin-top:4px}.mpr-admin-actions{border-top:1px dashed #e2d8cb;padding-top:9px}.mpr-warn{font-size:11px;color:#a65c34}.mpr-foot{border-top:1px solid #ece4d8;padding-top:12px}
@media(max-width:900px){.mpr-columns{grid-template-columns:1fr}.mpr-root{padding:12px}.mpr-panel{padding:13px}}@media(max-width:480px){.mpr-add-row{align-items:stretch;flex-wrap:wrap}.mpr-cart-row{grid-template-columns:minmax(0,1fr) 65px auto}.mpr-btn{font-size:11px}}
</style>
