<script setup>
// STEP644_DIRECT_INVOICE: standalone invoice dialog; it does not alter the existing sidebar or job register.
import { ref, watch, computed, nextTick } from 'vue';
import UnifiedInvoicePrint684 from './UnifiedInvoicePrint684.vue';
const invoicePreview = ref('');

const props = defineProps({ open: Boolean, initialJob: { type: String, default: '' } });
const emit = defineEmits(['close', 'created']);
const query = ref('');
const candidates = ref([]);
const selected = ref(null);
const lines = ref([]);
const error = ref('');
const loading = ref(false);
const saving = ref(false);
const done = ref(null);
let searchSeq = 0;
let searchTimer = null;

function messageOf(value) {
  if (typeof value === 'string') return value;
  if (value?._server_messages) {
    try {
      const a = JSON.parse(value._server_messages);
      if (a.length) return JSON.parse(a[0]).message || 'Server error';
    } catch (_) { /* use fallback */ }
  }
  return value?.message || 'Request failed. Check permissions and billing configuration.';
}
async function call(method, params = {}, post = false) {
  const target = new URL(`/api/method/servicing_os.api.job_billing_644.${method}`, window.location.origin);
  const opts = { credentials: 'same-origin', headers: { Accept: 'application/json' } };
  if (post) {
    opts.method = 'POST';
    opts.headers['Content-Type'] = 'application/json';
    opts.headers['X-Frappe-CSRF-Token'] = window.csrf_token || window.frappe?.csrf_token || '';
    opts.body = JSON.stringify(params);
  } else {
    for (const [k, v] of Object.entries(params)) target.searchParams.set(k, String(v ?? ''));
  }
  const resp = await fetch(target, opts);
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok || json.exc || json.exception) throw new Error(messageOf(json));
  return json.message;
}

async function searchJobs() {
  const sequence = ++searchSeq;
  try {
    const data = await call('search_jobs', { q: query.value.trim() });
    if (sequence === searchSeq) candidates.value = data || [];
  } catch (e) {
    if (sequence === searchSeq) error.value = e.message;
  }
}
watch(query, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(searchJobs, 250);
});
async function loadJob(name) {
  name = String(name || '').trim();
  if (!name) return;
  selected.value = null;
  done.value = null;
  error.value = '';
  loading.value = true;
  try {
    const context = await call('invoice_preview', { service_job: name });
    selected.value = context;
    query.value = context.job;
    candidates.value = [];
    lines.value = [
      { item_code: '', item_name: 'Service / Labour Charge', qty: 1,
        rate: (context.parts || []).length ? 0 : (context.estimate > 0 ? context.estimate : 0) },
      ...(context.parts || []).map(p => ({ item_code: p.item_code, item_name: p.item_name,
        qty: Number(p.qty || 1), rate: Number(p.rate || 0), source: p.source })),
    ];
  } catch (e) { error.value = e.message; }
  finally { loading.value = false; }
}
watch(() => props.open, async open => {
  if (!open) return;
  invoicePreview.value = '';
  selected.value = null; done.value = null; error.value = ''; lines.value = [];
  query.value = props.initialJob || '';
  await nextTick();
  if (props.initialJob) await loadJob(props.initialJob);
  else await searchJobs();
}, { immediate: true });
const amount = computed(() => lines.value.reduce((sum, row) => sum + Number(row.qty || 0) * Number(row.rate || 0), 0));
async function onReviewedSubmitted(result) {
  const job = selected.value?.job;
  const previous = selected.value?.existing_invoice;
  emit('created', result);
  if (job) await loadJob(job);
  done.value = { ...result, submitted: true, grand_total: previous?.grand_total,
    currency: selected.value?.currency };
}
function addCharge() { lines.value.push({ item_code: '', item_name: '', qty: 1, rate: 0 }); }
function addPart() { lines.value.push({ item_code: '', item_name: '', qty: 1, rate: 0, chooseItem: true }); }
async function create(review) {
  if (saving.value || !selected.value) return;
  if (selected.value.existing_invoice) { error.value = 'An invoice already exists for this job.'; return; }
  error.value = '';
  saving.value = true;
  try {
    const clean = lines.value.filter(r => Number(r.qty) > 0 && (r.item_code || r.item_name)).map(r => ({
      item_code: r.item_code || '', item_name: r.item_name || '',
      qty: Number(r.qty), rate: Number(r.rate), description: r.item_name || '',
    }));
    const result = await call('create_invoice', { service_job: selected.value.job, lines: clean, submit: 0 }, true);
    done.value = result;
    emit('created', result);
    await loadJob(selected.value.job);
    done.value = result;
    if (review) invoicePreview.value = result.invoice;
  } catch (e) { error.value = e.message; }
  finally { saving.value = false; }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="s44-overlay" @click.self="!saving && $emit('close')">
      <section class="s44-dialog" role="dialog" aria-modal="true" aria-label="Create Service Job Invoice">
        <header class="s44-head">
          <div>
            <small>SERVICING OS · SERVICE JOBS</small>
            <h2>Quick Invoice <span>· দ্রুত বিল</span></h2>
            <p>Direct billing · No mandatory repair-stage changes</p>
          </div>
          <button type="button" class="s44-exit" :disabled="saving" @click="$emit('close')">×</button>
        </header>
        <div class="s44-body">
          <label class="s44-label">Find Service Job · সার্ভিস জব খুঁজুন</label>
          <div class="s44-search">
            <input v-model="query" class="s44-field" placeholder="SRV-2026-00004" @keydown.enter.prevent="loadJob(query)" />
            <button type="button" class="s44-muted" @click="loadJob(query)">Load Job</button>
          </div>
          <div v-if="!selected && candidates.length" class="s44-results">
            <button v-for="job in candidates" :key="job.name" type="button" @click="loadJob(job.name)">
              <strong>{{ job.name }}</strong><span>{{ job.customer_name }} · {{ job.status }}</span>
            </button>
          </div>
          <p v-if="loading" class="s44-info">Loading job...</p>
          <p v-if="error" role="alert" class="s44-error">{{ error }}</p>
          <div v-if="selected" class="s44-section">
            <div class="s44-jobline">
              <div><small>JOB</small><strong>{{ selected.job }}</strong></div>
              <div><small>CUSTOMER</small><strong>{{ selected.customer_name || selected.customer }}</strong></div>
              <div><small>STATUS</small><strong>{{ selected.status }}</strong></div>
            </div>
            <p v-if="selected.existing_invoice" class="s44-info">
              An invoice already exists: <strong>{{ selected.existing_invoice.name }}</strong>.
              This job cannot be invoiced twice while that invoice is active.
              <button type="button" class="s44-primary" :disabled="saving"
                @click="invoicePreview = selected.existing_invoice.name">Review invoice</button>
            </p>
            <template v-else>
              <div class="s44-subhead"><h3>Labour & consumed parts</h3><div class="s44-subhead-actions"><button type="button" class="s44-link" @click="addCharge">＋ Add charge</button><button type="button" class="s44-link" @click="addPart">＋ Add part by Item Code</button></div></div>
              <div class="s44-table-wrap"><table class="s44-table">
                <thead><tr><th>Item / Charge</th><th>Qty</th><th>Rate ({{ selected.currency }})</th><th>Amount</th><th></th></tr></thead>
                <tbody><tr v-for="(row, i) in lines" :key="i">
                  <td>
                    <input v-if="row.chooseItem" v-model.trim="row.item_code" class="s44-field" placeholder="ERPNext Item Code (existing item)" />
                    <input v-model="row.item_name" class="s44-field" :readonly="!!row.item_code && !row.chooseItem" placeholder="Service labour / additional charge" />
                    <small v-if="row.item_code && !row.chooseItem">{{ row.item_code }} <span v-if="row.source">· {{ row.source }}</span></small></td>
                  <td><input v-model.number="row.qty" class="s44-field s44-num" type="number" min="0.001" step="0.001" /></td>
                  <td><input v-model.number="row.rate" class="s44-field s44-num" type="number" min="0" step="0.01" /></td>
                  <td class="s44-amount">{{ (Number(row.qty || 0) * Number(row.rate || 0)).toFixed(2) }}</td>
                  <td><button type="button" class="s44-remove" title="Remove row" @click="lines.splice(i, 1)">×</button></td>
                </tr></tbody>
              </table></div>
              <div class="s44-total"><span>Total</span><strong>{{ selected.currency }} {{ amount.toFixed(2) }}</strong></div>
              <p class="s44-note">Estimated cost is a reference, not a confirmed labour charge. Check all rates before submitting. Already-issued spare parts are listed for billing. This invoice does not deduct inventory again. If parts have not been issued, record their stock movement separately. Rates can be edited before saving.</p>
              <div class="s44-actions">
                <button type="button" class="s44-muted" :disabled="saving || amount <= 0" @click="create(false)">Save Draft</button>
                <button type="button" class="s44-primary" :disabled="saving || amount <= 0" @click="create(true)">{{ saving ? 'Creating...' : 'Save & Review Invoice' }}</button>
              </div>
            </template>
          </div>
          <div v-if="done" class="s44-done">
            Invoice <strong>{{ done.invoice }}</strong> {{ done.submitted ? 'submitted' : 'saved as draft' }}. Total: {{ done.currency }} {{ done.grand_total }}.
            <button type="button" class="s44-primary" @click="invoicePreview = done.invoice">View invoice</button>
          </div>
        </div>
      </section>
    </div>
  </Teleport>
  <UnifiedInvoicePrint684 v-if="open && invoicePreview" :invoice-name="invoicePreview" submit-draft
    @close="invoicePreview = ''" @submitted="onReviewedSubmitted" />
</template>

<style>
.s44-overlay { position:fixed; inset:0; z-index:10080; padding:12px; display:flex; align-items:center; justify-content:center; overflow:auto; background:rgba(42,34,24,.50); backdrop-filter:blur(3px); }
.s44-dialog { background:#fffcf7; color:#302b25; border:1px solid #e6dcd0; border-radius:17px; box-shadow:0 32px 90px #1f1b173f; width:min(980px,100%); max-height:calc(100dvh - 24px); overflow:auto; }
.s44-head { display:flex; justify-content:space-between; gap:16px; padding:21px 26px; border-bottom:1px solid #eee4d8; }
.s44-head small {font-size:10px; color:#927b5e; font-weight:700;letter-spacing:.1em;}
.s44-head h2 {font-size:22px;font-weight:700;margin:6px 0;}.s44-head h2 span {font-size:14px;font-weight:450;}
.s44-head p,.s44-note {font-size:12px;color:#796e60;}
.s44-exit {height:35px;width:35px;border:1px solid #e4d9cb;border-radius:9px;background:#fff;font-size:24px;}
.s44-body {padding:20px 26px 28px;}.s44-label {font-size:12px;font-weight:650;display:block;margin-bottom:8px;}
.s44-search {display:flex;gap:9px;}.s44-field {border:1px solid #d9d0c3;border-radius:8px;padding:9px 10px;background:#fff;color:#2d2925;width:100%;font-size:13px;}
.s44-muted {padding:9px 16px;background:#fff;border:1px solid #d9cbb8;border-radius:8px;color:#453b2e;font-weight:650;white-space:nowrap;}
.s44-primary {padding:10px 20px;background:#6c5235;color:white;border:1px solid #6c5235;border-radius:8px;font-weight:700;}
.s44-primary:disabled,.s44-muted:disabled {opacity:.45;cursor:not-allowed;}
.s44-results {display:grid;gap:5px;border:1px solid #ebe2d8;background:#fff;border-radius:9px;padding:8px;margin:8px 0 0;max-height:200px;overflow:auto;}
.s44-results button {text-align:left;display:flex;justify-content:space-between;gap:12px;padding:8px;border-radius:6px;font-size:12px;}
.s44-results button:hover {background:#f7f0e4;}.s44-results span {color:#776b60;}
.s44-error {color:#a13a31;background:#fff0ec;border:1px solid #f2c5b9;padding:10px;border-radius:8px;margin-top:10px;font-size:12px;}
.s44-info {font-size:12px;background:#f1e9dc;border-radius:8px;padding:10px;margin:12px 0;}
.s44-section {margin-top:20px;}.s44-jobline {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;background:#f7f0e5;padding:12px;border-radius:9px;}
.s44-jobline div {display:flex;flex-direction:column;gap:4px;min-width:0;overflow-wrap:anywhere;}.s44-jobline small {font-size:10px;color:#92795d;}.s44-jobline strong {font-size:12px;}
.s44-subhead {display:flex;align-items:center;justify-content:space-between;margin:22px 0 8px;}.s44-subhead h3 {font-size:14px;font-weight:700;}.s44-link {font-size:12px;color:#795531;font-weight:700;}
.s44-table-wrap {overflow-x:auto;}.s44-table {width:100%;border-collapse:collapse;min-width:610px;font-size:12px;}.s44-table th {text-align:left;font-weight:700;color:#756655;background:#f8f0e6;padding:9px 8px;}
.s44-table td {padding:9px 6px;border-bottom:1px solid #eee4d8;vertical-align:top;}.s44-table td:first-child {min-width:230px;}.s44-table td:first-child small {display:block;color:#827466;margin-top:4px;}
.s44-table .s44-num {min-width:76px;max-width:115px;}.s44-amount {min-width:70px;padding-top:16px!important;}.s44-remove {font-size:20px;color:#9b5c54;}
.s44-total {margin-top:18px;display:flex;justify-content:space-between;font-size:18px;}.s44-total strong {font-weight:750;}.s44-note {margin:16px 0;line-height:1.65;}
.s44-actions {display:flex;gap:10px;justify-content:flex-end;}.s44-done {margin-top:14px;border:1px solid #c8dfcc;background:#f0f8f0;color:#2b6032;padding:12px;border-radius:9px;font-size:13px;}
.s44-done a {margin-left:10px;text-decoration:underline;}
@media(max-width:640px){.s44-body,.s44-head {padding:15px;}.s44-jobline {grid-template-columns:1fr;}.s44-actions {flex-direction:column;}.s44-search {flex-direction:column;}}
</style>
