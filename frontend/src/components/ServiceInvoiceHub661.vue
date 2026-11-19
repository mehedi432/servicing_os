<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import UnifiedInvoicePrint684 from './UnifiedInvoicePrint684.vue'

// SERVICING_OS_SERVICE_INVOICE_661 — read-only linked invoices + job-aware invoice launcher.
const rows = ref([])
const jobs = ref([])
const selected = ref(null)
const jobInput = ref('')
const search = ref('')
const loading = ref(false)
const error = ref('')
const canCreate = ref(false)
const preview = ref(null)
let requestSeq = 0

const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return !q ? rows.value : rows.value.filter(r =>
    [r.name, r.service_job, r.customer, r.status].some(x => String(x || '').toLowerCase().includes(q))
  )
})
const money = (n, currency) => `${currency || 'BDT'} ${Number(n || 0).toLocaleString('en-BD', {minimumFractionDigits:2, maximumFractionDigits:2})}`
const currentInvoice = computed(() => selected.value?.active_invoice || null)
const complete = computed(() => selected.value && !currentInvoice.value)

async function refresh(jobName = '') {
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  try {
    const url = new URL('/api/method/servicing_os.api.service_invoice_661.get_service_invoice_hub', window.location.origin)
    url.searchParams.set('limit', '20')
    if (jobName) url.searchParams.set('job_name', jobName)
    const resp = await fetch(url, {credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'}})
    const data = await resp.json()
    if (!resp.ok || data.exc || data.exception) {
      let explanation = data.message || 'Failed to load Service Job invoices'
      if (typeof explanation !== 'string') explanation = 'Unable to fetch Service Job invoices'
      throw new Error(explanation)
    }
    if (seq !== requestSeq) return
    rows.value = data.message?.invoices || []
    jobs.value = data.message?.jobs || []
    selected.value = data.message?.selected_job || null
    canCreate.value = !!data.message?.can_create
  } catch (e) {
    if (seq === requestSeq) error.value = e?.message || 'Service invoice list unavailable'
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}
function findJob() {
  const id = jobInput.value.trim()
  if (!id) {selected.value = null;refresh();return}
  refresh(id)
}
function clearJob() {jobInput.value = ''; selected.value = null; refresh()}
function chooseJob(id) {jobInput.value = id;refresh(id)}
function printInvoice(row, duplicate=false) {preview.value = {name:row.name, doctype:row.doctype, duplicate, previewOnly: Number(row.docstatus) !== 1}}
function createForJob() {
  if (!selected.value?.name) {error.value = 'Select a saved Service Job first.'; return}
  if (currentInvoice.value) {
    error.value = `An invoice already exists for ${selected.value.name}. Print or open that invoice instead of creating a duplicate.`
    printInvoice(currentInvoice.value)
    return
  }
  if (!canCreate.value) {error.value = 'You do not have permission to create Sales Invoices.';return}
  window.dispatchEvent(new CustomEvent('servicing-os-create-service-invoice', {
    detail: {service_job: selected.value.name}
  }))
}
function onInvoiceSaved(evt) {
  const relevant = evt?.detail?.service_job || evt?.detail?.job_name || ''
  if (selected.value?.name) refresh(selected.value.name)
  else refresh()
}
onMounted(() => {refresh();window.addEventListener('servicing-os-invoice-draft-created',onInvoiceSaved);window.addEventListener('servicing-os-sale-completed',onInvoiceSaved)})
onUnmounted(() => {requestSeq++;window.removeEventListener('servicing-os-invoice-draft-created',onInvoiceSaved);window.removeEventListener('servicing-os-sale-completed',onInvoiceSaved)})
</script>

<template>
  <section class="sos661" aria-label="Service Job linked invoice register">
    <header class="sos661-head">
      <div class="sos661-heading">
        <span class="sos661-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/></svg></span>
        <div><h2>Service Job Invoices</h2><p>Live linked invoices · Print, reprint and create from an existing job</p></div>
      </div>
      <button class="sos661-secondary" type="button" :disabled="loading" @click="refresh(selected?.name || '')">↻ Refresh</button>
    </header>

    <div class="sos661-toolbar">
      <label class="sos661-jobinput"><span>Find Service Job</span>
        <input v-model.trim="jobInput" list="sos661-joblist" placeholder="Search or enter SRV-..." autocomplete="off" @keydown.enter.prevent="findJob" />
        <datalist id="sos661-joblist"><option v-for="job in jobs" :key="job.name" :value="job.name">{{ job.customer_name || job.customer }}</option></datalist>
      </label>
      <button type="button" class="sos661-secondary" @click="findJob">Find Job</button>
      <button type="button" class="sos661-secondary" @click="clearJob">Show Recent 20</button>
      <button type="button" class="sos661-primary" :disabled="!complete || !canCreate" @click="createForJob">+ Create Service Invoice</button>
    </div>

    <div v-if="selected" class="sos661-selected">
      <div><small>SELECTED SERVICE JOB</small><strong>{{ selected.name }}</strong><span>{{ selected.customer_name || selected.customer }} · {{ selected.status }}</span></div>
      <div v-if="currentInvoice" class="sos661-linked"><small>ALREADY INVOICED</small><strong>{{ currentInvoice.name }}</strong><button type="button" @click="printInvoice(currentInvoice)">Review Invoice</button></div>
      <div v-else class="sos661-notbilled"><small>BILLING STATUS</small><strong>Not yet invoiced</strong><span>Create an invoice for this job above</span></div>
    </div>
    <div v-else class="sos661-note">Select a Service Job to see its exact invoice history and create its draft invoice without re-entering the customer.</div>
    <div v-if="error" class="sos661-error" role="alert">{{ error }}</div>
    <div class="sos661-listhead"><strong>{{ selected ? 'Invoices linked to '+selected.name : 'Recent 20 Service Invoices' }}</strong><label>Filter list <input v-model="search" type="search" placeholder="Invoice or customer" /></label></div>
    <p v-if="loading" class="sos661-empty">Loading invoice records…</p>
    <p v-else-if="!visible.length" class="sos661-empty">No linked invoice found. If an older invoice exists, verify its Service Job link field in ERPNext.</p>
    <div v-else class="sos661-scroller">
      <table><thead><tr><th>Invoice</th><th>Service Job</th><th>Customer</th><th>Status</th><th>Amount</th><th>Actions</th></tr></thead>
        <tbody><tr v-for="item in visible" :key="item.doctype+':'+item.name">
          <td><strong>{{ item.name }}</strong><small>{{ item.posting_date }} · {{ item.doctype }}</small></td>
          <td><button type="button" class="sos661-joblink" @click="chooseJob(item.service_job)">{{ item.service_job }}</button></td>
          <td>{{ item.customer }}</td>
          <td><span class="sos661-badge" :class="{'is-submitted':item.docstatus===1,'is-cancelled':item.docstatus===2}">{{ item.status }}</span></td>
          <td class="sos661-total">{{ money(item.grand_total,item.currency) }}</td>
          <td><div class="sos661-buttons"><button type="button" @click="printInvoice(item)">Review</button><button v-if="Number(item.docstatus) === 1" type="button" @click="printInvoice(item,true)">Duplicate</button></div></td>
        </tr></tbody>
      </table>
    </div>
    <div class="sos661-foot">Existing Sales/POS Invoices only. Duplicate prints the same invoice and never creates a new transaction. Drafts are not submitted sales.</div>
    <UnifiedInvoicePrint684 v-if="preview" submit-draft :preview-only="preview.previewOnly" @submitted="onInvoiceSaved" :invoice-name="preview.name" :doctype="preview.doctype" :duplicate="preview.duplicate" :key="preview.doctype+preview.name+String(preview.duplicate)" @close="preview=null" />
  </section>
</template>

<style scoped>
.sos661,.sos661 *{box-sizing:border-box}.sos661{width:100%;min-width:0;background:#fffcf7;border:1px solid #e7d6c5;border-radius:14px;margin-bottom:16px;overflow:visible;color:#3c2c25;font-size:12px;box-shadow:0 3px 10px #4935220b}
.sos661-head{padding:15px 17px;display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid #eadbcf;flex-wrap:wrap}
.sos661-heading{display:flex;align-items:center;gap:11px}.sos661-heading svg{width:22px;height:22px}.sos661-mark{display:grid;place-items:center;color:#805a3e;background:#f4e3d3;border-radius:11px;width:39px;height:39px}
.sos661 h2{font-size:16px;font-weight:800;line-height:1.2;margin:0}.sos661 p{margin:3px 0 0;color:#8b725e;font-size:11px}.sos661 button{cursor:pointer}.sos661 button:disabled{opacity:.52;cursor:not-allowed}
.sos661-toolbar{display:flex;align-items:end;gap:9px;flex-wrap:wrap;padding:15px 17px;background:#fffaf4}
.sos661-jobinput{display:grid;flex:1 1 210px;gap:5px;min-width:170px}.sos661 label>span{font-size:11px;font-weight:700;color:#765642}
.sos661 input{border:1px solid #dcc3b0!important;background:white!important;color:#3c2c25!important;border-radius:9px!important;height:41px!important;min-height:41px!important;padding:9px 12px!important;width:100%;font-size:12px!important}
.sos661 input:focus{outline:2px solid #bc9476;outline-offset:1px}
.sos661-primary,.sos661-secondary,.sos661-buttons button,.sos661-linked button{border:1px solid #dfc9b8!important;background:#f4e3d3!important;color:#64442f!important;font-size:11px!important;font-weight:730!important;padding:10px 12px!important;border-radius:9px!important;min-height:40px}
.sos661-primary{background:#805a3e!important;border-color:#805a3e!important;color:white!important}
.sos661-selected{display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px;padding:13px 17px;border-block:1px solid #eadbcf;background:#f9f3ec}.sos661-selected>div{display:grid;gap:3px}
.sos661-selected small{font-size:9px;font-weight:800;color:#9d795e;letter-spacing:.7px}.sos661-selected strong{font-size:13px}.sos661-selected span{font-size:11px;color:#866852}.sos661-linked{display:flex!important;flex-direction:column;align-items:flex-start}.sos661-linked button{min-height:29px;padding:6px 9px!important}
.sos661-note{padding:11px 17px;font-size:11px;line-height:1.45;color:#8b725e}.sos661-error{padding:10px 14px;margin:10px 17px;background:#fff0eb;color:#9d4531;border:1px solid #eed4c8;border-radius:9px}
.sos661-listhead{display:flex;justify-content:space-between;align-items:center;gap:11px;flex-wrap:wrap;padding:12px 17px}.sos661-listhead strong{font-size:13px}.sos661-listhead label{display:flex;align-items:center;gap:7px;font-size:11px;color:#8b725e}.sos661-listhead input{width:170px;height:35px!important;min-height:35px!important}
.sos661-scroller{overflow-x:auto;margin:0 15px;border:1px solid #ebddcf;border-radius:10px}.sos661 table{border-collapse:collapse;min-width:790px;width:100%;font-size:11px}.sos661 th{background:#f4e3d3;text-align:left;color:#76513b;padding:10px;font-weight:800}.sos661 td{padding:11px 10px;border-top:1px solid #efe5db;vertical-align:middle}.sos661 td small{display:block;margin-top:3px;color:#927460;font-size:10px}.sos661 td strong{font-size:11px}.sos661 tr:hover td{background:#fffbf5}
.sos661-total{text-align:right;white-space:nowrap}.sos661-badge{display:inline-block;border-radius:20px;background:#f3e1d2;color:#715139;padding:5px 9px;font-size:10px;font-weight:700}.sos661-badge.is-submitted{background:#ecede3;color:#4f6247}.sos661-badge.is-cancelled{background:#fce4dc;color:#974a34}
.sos661-joblink{background:transparent!important;border:0!important;padding:0!important;color:#8a5f3f!important;text-decoration:underline;font-weight:700;white-space:nowrap}.sos661-buttons{display:flex;gap:6px;white-space:nowrap}.sos661-buttons button{padding:8px 10px!important;min-height:33px}.sos661-buttons button:last-child{background:#805a3e!important;color:white!important;border-color:#805a3e!important}
.sos661-empty{padding:15px 17px!important;color:#866852!important}.sos661-foot{margin-top:11px;padding:10px 17px;font-size:10px;color:#94755e;border-top:1px solid #ede0d3}
@media(max-width:700px){.sos661-head,.sos661-toolbar,.sos661-listhead{padding:11px}.sos661-scroller{margin:0 9px}.sos661-toolbar>button{flex:1}.sos661-listhead input{width:135px}}
</style>
