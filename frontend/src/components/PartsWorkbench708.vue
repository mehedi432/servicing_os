<script setup>
// SERVICING OS V7.08 — modal-first repair parts workspace.
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import StockReceipt712 from './StockReceipt712.vue'

const props = defineProps({
  jobName: { type: String, required: true },
  jobStatus: { type: String, default: '' },
})
const expanded = ref(true)
const sos712ReceiptOpen=ref(false)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const context = ref({ requests: [], manager: false })
const activeTab = ref('parts')
const lines = ref([])
const remarks = ref('')
const modal = ref('')
const search = ref('')
const searching = ref(false)
const searchComplete = ref(false)
const found = ref([])
const selected = ref(null)
const quantity = ref(1)
const preview = ref(null)
const selectedMR = ref('')
const expenseAccount = ref('')
const costCenter = ref('')
const showAccounting = ref(false)
const issueRemarks = ref('')
const draftEntry = ref('')
const confirmed = ref(false)
const resumeIssue = ref('')
let searchTimer = null
let searchSerial = 0
const closed = computed(() => ['Delivered','Cancelled','Canceled'].includes(props.jobStatus || context.value.job_status))
const totalQty = computed(() => lines.value.reduce((s, x) => s + Number(x.qty || 0), 0))
const requestedCount = computed(() => (context.value.requests || []).length)
const draftCount = computed(() => (context.value.requests || []).filter(r => r.docstatus === 0).length)
const issuedCount = computed(() => (context.value.requests || []).filter(r => (r.stock_entries || []).some(x => x.docstatus === 1)).length)
const requiresDesk = computed(() => preview.value?.items.some(item => item.serial_or_batch))
const shortages = computed(() => (preview.value?.items || []).filter(item =>
  Number(item.shortage ?? (item.qty - item.available)) > 0.000001
))
const stockElsewhere = computed(() => shortages.value.some(item => item.other_warehouses?.length))
const needsIncomingStock = computed(() => shortages.value.some(item => !item.other_warehouses?.length))
const number = value => Number(value ?? 0).toLocaleString('en-BD', {maximumFractionDigits: 6})

function csrf() {
  return window.frappe?.csrf_token || window.csrf_token ||
    decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('csrf_token='))?.split('=').slice(1).join('=') || '')
}
function parseError(data, fallback) {
  try {
    const messages = JSON.parse(data?._server_messages || '[]')
    if (messages.length) {
      const value = JSON.parse(messages.at(-1)).message
      const plain = document.createElement('div')
      plain.innerHTML = String(value)
      return plain.textContent || fallback
    }
  } catch (_) { /* fall back */ }
  return data?.message?.message || data?.exception || fallback
}
async function api(method, args = {}, post = false) {
  const url = new URL(`/api/method/servicing_os.api.parts_workbench_708.${method}`, window.location.origin)
  const opts = { method: post ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } }
  if (post) {
    opts.headers['Content-Type'] = 'application/json'
    opts.headers['X-Frappe-CSRF-Token'] = csrf()
    opts.body = JSON.stringify(args)
  } else {
    Object.entries(args).forEach(([key, value]) => { if (value !== undefined && value !== null) url.searchParams.set(key, String(value)) })
  }
  const response = await fetch(url, opts)
  const body = await response.json().catch(() => ({}))
  if (!response.ok || body.exc || body.exc_type || body.exception) throw new Error(parseError(body, `Server error ${response.status}`))
  return body.message || {}
}
async function refresh() {
  if (!props.jobName) return
  const current = props.jobName
  loading.value = true
  error.value = ''
  try {
    const data = await api('overview', { job_name: current })
    if (props.jobName === current) context.value = data
  } catch (e) { if (props.jobName === current) error.value = e.message || 'Could not load parts' }
  finally { if (props.jobName === current) loading.value = false }
}
async function doSearch(term) {
  const serial = ++searchSerial
  searching.value = true
  try {
    const data = await api('search_items', { job_name: props.jobName, search: term })
    if (serial === searchSerial) found.value = data.items || []
    if (serial === searchSerial) searchComplete.value = true
  } catch (e) { if (serial === searchSerial) error.value = e.message }
  finally { if (serial === searchSerial) searching.value = false }
}
watch(search, (value) => {
  clearTimeout(searchTimer)
  found.value = []
  selected.value = null
  searchComplete.value = false
  searching.value = false
  searchSerial++
  if (value.trim().length >= 2) searchTimer = setTimeout(() => doSearch(value.trim()), 240)
})
function openAdd() {
  error.value = ''
  selected.value = null
  search.value = ''
  quantity.value = 1
  modal.value = 'add'
}
function choose(item) { selected.value = item; found.value = []; clearTimeout(searchTimer); searchSerial++ }
function addLine() {
  if (!selected.value) { error.value = 'Select an item from search results'; return }
  const qty = Number(quantity.value)
  if (!Number.isFinite(qty) || qty <= 0 || qty > 100000) { error.value = 'Enter a positive quantity'; return }
  const existing = lines.value.find(x => x.item_code === selected.value.item_code)
  if (existing) existing.qty = Number(existing.qty) + qty
  else lines.value.push({ ...selected.value, qty })
  modal.value = ''
  error.value = ''
  selected.value = null
}
function validateLines() {
  return lines.value.length > 0 && lines.value.every(x => Number.isFinite(Number(x.qty)) && Number(x.qty) > 0 && Number(x.qty) <= 100000)
}
function openRequest() {
  if (!validateLines()) { error.value = 'Add at least one part with a valid quantity'; return }
  error.value = ''
  modal.value = 'request'
}
async function saveRequest() {
  if (busy.value || !validateLines()) return
  busy.value = true; error.value = ''; success.value = ''
  try {
    const out = await api('create_request', { job_name: props.jobName,
      items: lines.value.map(x => ({ item_code:x.item_code, qty:Number(x.qty) })), remarks:remarks.value }, true)
    lines.value = []; remarks.value = ''; modal.value = ''; activeTab.value = 'requests'
    success.value = `Draft Material Request ${out.material_request} created. Stock is unchanged.`
    await refresh()
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
async function approve(r) {
  if (busy.value || !context.value.manager || !window.confirm(`Approve Material Request ${r.name}? No stock is deducted.`)) return
  busy.value = true; error.value = ''; success.value = ''
  try { await api('approve_request', { material_request:r.name }, true)
    success.value = `${r.name} approved. Use Stock Entry to issue parts.`; await refresh() }
  catch (e) { error.value = e.message }
  finally { busy.value = false }
}
async function openStock(requestName, keepAccounting = false) {
  const job = props.jobName
  selectedMR.value = requestName; draftEntry.value = ''; confirmed.value = false; preview.value = null
  error.value = ''; success.value = ''; modal.value = 'stock'; busy.value = true
  try {
    const data = await api('issue_preview', { material_request:requestName })
    if (props.jobName !== job || selectedMR.value !== requestName || modal.value !== 'stock') return
    preview.value = data
    if (!keepAccounting) {
      expenseAccount.value = data.expense_account || ''
      costCenter.value = data.cost_center || ''
      showAccounting.value = !expenseAccount.value || !costCenter.value
      issueRemarks.value = ''
    }
    draftEntry.value = (preview.value.stock_entries || []).find(x => x.docstatus === 0)?.name || ''
  } catch (e) {
    if (props.jobName === job && selectedMR.value === requestName) error.value = e.message
  } finally { busy.value = false }
}
function receiveForIssue() {
  resumeIssue.value = selectedMR.value
  closeModal()
  sos712ReceiptOpen.value = true
}
function closeReceipt() {
  sos712ReceiptOpen.value = false
  const requestName = resumeIssue.value
  resumeIssue.value = ''
  if (requestName) openStock(requestName)
}
async function createDraft() {
  if (busy.value || !preview.value || draftEntry.value) return
  busy.value = true; error.value = ''; success.value = ''
  try {
    const result = await api('create_draft_stock_entry', {
      material_request:selectedMR.value, expense_account:expenseAccount.value,
      cost_center:costCenter.value, remarks:issueRemarks.value,
    }, true)
    draftEntry.value = result.stock_entry
    success.value = `Stock Entry ${result.stock_entry} saved as Draft. No stock deducted yet.`
    await refresh()
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
async function submitEntry() {
  if (busy.value || !draftEntry.value || !confirmed.value || requiresDesk.value || shortages.value.length) return
  const requestName = selectedMR.value
  const job = props.jobName
  busy.value = true; error.value = ''; success.value = ''
  try {
    const result = await api('submit_stock_entry', { stock_entry:draftEntry.value, confirm:draftEntry.value }, true)
    if (!result.stock_deducted) throw new Error('ERPNext did not confirm a posted Stock Entry')
    modal.value = ''; preview.value = null
    success.value = `Stock issued successfully in ${result.stock_entry}; ledger updated once.`
    await refresh()
  } catch (e) {
    if (props.jobName === job && selectedMR.value === requestName && modal.value === 'stock') {
      await openStock(requestName, true)
      if (props.jobName === job && selectedMR.value === requestName) error.value = e.message
    }
  }
  finally { busy.value = false }
}
function closeModal() { if (!busy.value) { modal.value = ''; preview.value = null; error.value = '' } }
function onKeydown(e) { if (e.key === 'Escape' && modal.value) closeModal() }
watch(() => props.jobName, () => {
  lines.value = []; remarks.value = ''; modal.value = ''; success.value = ''; error.value = ''; context.value = { requests:[], manager:false }
  resumeIssue.value = ''; sos712ReceiptOpen.value = false
  activeTab.value = 'parts'; expanded.value = true; refresh()
}, { immediate:true })
onBeforeUnmount(() => { clearTimeout(searchTimer) })
</script>

<template>
  <section v-if="jobName" :id="`repair-parts-${jobName}`" tabindex="-1" class="pw708" aria-label="Spare parts workspace" @keydown="onKeydown">
    <header class="pw708-top">
      <div><small class="pw708-kicker">REPAIR MATERIAL CONTROL · {{ jobName }}</small><h3>Spare Parts Required</h3><p>Request, approve and issue repair parts without leaving Counter.</p></div>
      <div class="sos712-parts-actions"><button type="button" class="pw708-light" :disabled="closed" @click="sos712ReceiptOpen=true">＋ Receive Stock</button><button type="button" class="pw708-light" @click="expanded = !expanded">{{ expanded ? 'Hide Parts' : 'Manage Parts' }}</button></div>
    </header>
    <StockReceipt712 v-if="sos712ReceiptOpen" :job-name="jobName" @close="closeReceipt" @received="refresh" />
    <template v-if="expanded">
      <div class="pw708-metrics">
        <div><small>Material requests</small><strong>{{ requestedCount }}</strong></div>
        <div><small>Draft requests</small><strong>{{ draftCount }}</strong></div>
        <div><small>Issued requests</small><strong>{{ issuedCount }}</strong></div>
      </div>
      <p v-if="error && !modal" class="pw708-alert error" role="alert">{{ error }}</p>
      <p v-if="success && !modal" class="pw708-alert success" role="status">{{ success }}</p>
      <p v-if="closed" class="pw708-alert error">This job is {{ jobStatus }}. No new parts can be requested.</p>
      <div class="pw708-tabs" role="tablist" aria-label="Parts navigation">
        <button type="button" role="tab" :aria-selected="activeTab === 'parts'" :class="{ active:activeTab === 'parts' }" @click="activeTab='parts'">Required Parts <span>{{ lines.length }}</span></button>
        <button type="button" role="tab" :aria-selected="activeTab === 'requests'" :class="{ active:activeTab === 'requests' }" @click="activeTab='requests'">Requests &amp; Stock Entries <span>{{ requestedCount }}</span></button>
      </div>
      <div v-if="activeTab === 'parts'" role="tabpanel" class="pw708-section">
        <div class="pw708-section-head"><div><strong>Parts request editor</strong><p>ERPNext-style line items · Quantity &amp; stock availability</p></div>
          <button type="button" class="pw708-primary" :disabled="closed" @click="openAdd"><span class="pw708-plus">+</span> Add Part</button>
        </div>
        <div class="pw708-scroll"><table class="pw708-table"><thead><tr><th>#</th><th>Item code / Item name</th><th>Available</th><th>Qty</th><th>Unit</th><th></th></tr></thead>
          <tbody><tr v-for="(row, i) in lines" :key="row.item_code"><td>{{ String(i + 1).padStart(2,'0') }}</td><td><strong>{{ row.item_name }}</strong><small>{{ row.item_code }}</small></td><td>{{ row.available_qty }}</td><td><input v-model.number="row.qty" type="number" min="0.001" step="any" :aria-label="`Quantity for ${row.item_code}`" /></td><td>{{ row.uom }}</td><td><button type="button" class="pw708-remove" :aria-label="`Remove ${row.item_code}`" @click="lines.splice(i,1)">×</button></td></tr>
          <tr v-if="!lines.length"><td colspan="6" class="pw708-empty">No parts selected. Use <strong>+ Add Part</strong> to build your request.</td></tr></tbody>
        </table></div>
        <footer class="pw708-footer"><span>{{ lines.length }} item(s) · {{ totalQty.toFixed(2) }} total quantity (mixed UOM)</span>
          <button type="button" class="pw708-primary" :disabled="closed || !validateLines()" @click="openRequest">Review Material Request</button></footer>
      </div>
      <div v-else role="tabpanel" class="pw708-section">
        <div class="pw708-section-head"><div><strong>Material Request register</strong><p>Actual ERPNext documents, approvals and linked Stock Entries</p></div><button type="button" class="pw708-light" :disabled="loading" @click="refresh">↻ Refresh</button></div>
        <div v-if="loading" class="pw708-empty">Loading requests…</div>
        <div v-else-if="!requestedCount" class="pw708-empty">No material requests for this Service Job yet.</div>
        <article v-for="r in context.requests" :key="r.name" class="pw708-record">
          <div class="pw708-record-head"><div><strong>{{ r.name }}</strong><small>{{ r.transaction_date }} · {{ r.owner }}</small></div><span class="pw708-status" :class="r.docstatus === 1 ? 'approved' : r.docstatus === 2 ? 'cancelled' : ''">{{ r.docstatus === 0 ? 'Draft' : r.docstatus === 1 ? 'Approved' : 'Cancelled' }}</span></div>
          <div class="pw708-scroll"><table class="pw708-table mini"><thead><tr><th>Part</th><th>Requested Qty</th></tr></thead><tbody><tr v-for="line in r.items" :key="line.name"><td>{{ line.item_name }} <small>{{ line.item_code }}</small></td><td>{{ line.qty }} {{ line.uom }}</td></tr></tbody></table></div>
          <div class="pw708-record-actions">
            <a :href="`/app/material-request/${encodeURIComponent(r.name)}`" target="_blank" rel="noopener">Open Material Request</a>
            <button v-if="context.manager && r.docstatus === 0 && !closed" type="button" class="pw708-light" :disabled="busy" @click="approve(r)">Approve Request</button>
            <button v-if="context.manager && r.docstatus === 1 && !(r.stock_entries || []).some(x => x.docstatus === 1) && !closed" type="button" class="pw708-primary" :disabled="busy" @click="openStock(r.name)">Stock Entry / Issue Parts</button>
            <span v-if="(r.stock_entries || []).some(x => x.docstatus === 1)" class="pw708-confirm">✓ Issued to repair</span>
          </div>
          <div v-if="r.stock_entries?.length" class="pw708-links"><span>Stock Entries:</span> <a v-for="entry in r.stock_entries" :key="entry.name" :href="`/app/stock-entry/${encodeURIComponent(entry.name)}`" target="_blank" rel="noopener">{{ entry.name }} ({{ entry.docstatus === 1 ? 'Submitted' : 'Draft' }})</a></div>
        </article>
      </div>
      <p class="pw708-disclaimer">Material Request approval does not deduct stock. Only a submitted native ERPNext Stock Entry posts the Stock Ledger. Never deduct the same part again through billing.</p>
    </template>
  </section>

  <Teleport to="body">
    <div v-if="modal" class="pw708-overlay" role="presentation" @click.self="closeModal" @keydown.esc.stop="closeModal">
      <section class="pw708-dialog" role="dialog" aria-modal="true" :aria-label="modal === 'add' ? 'Add repair part' : modal === 'request' ? 'Create Material Request' : 'Stock Entry review'">
        <header class="pw708-dialog-head"><div><small class="pw708-kicker">{{ jobName }} · SERVICING OS</small><h3>{{ modal === 'add' ? 'Add Required Part' : modal === 'request' ? 'New Material Request' : 'Stock Entry Studio' }}</h3><p>{{ modal === 'add' ? 'Find a product and enter the required quantity.' : modal === 'request' ? 'Review all parts before creating an ERPNext draft.' : 'Review accounting and stock details before posting.' }}</p></div><button type="button" class="pw708-close" :disabled="busy" aria-label="Close popup" @click="closeModal">×</button></header>
        <div class="pw708-dialog-body">
          <p v-if="error" class="pw708-alert error" role="alert">{{ error }}</p>
          <p v-if="success" class="pw708-alert success" role="status">{{ success }}</p>
          <template v-if="modal === 'add'">
            <label class="pw708-label">Search Stock Item <input v-model="search" autofocus type="search" placeholder="Item code / RAM / SSD / charger..." autocomplete="off" /></label>
            <p v-if="searching" class="pw708-muted">Searching active stock items…</p>
            <p v-else-if="searchComplete && !found.length && !selected" class="pw708-muted" role="status">No matching stock items. Try an Item Code or a shorter name.</p>
            <div v-if="found.length" class="pw708-results"><button v-for="part in found" :key="part.item_code" type="button" @click="choose(part)"><strong>{{ part.item_name }}</strong><small>{{ part.item_code }} · {{ part.available_qty }} {{ part.uom }} available</small></button></div>
            <div v-if="selected" class="pw708-selected"><strong>{{ selected.item_name }}</strong><small>{{ selected.item_code }} · {{ number(selected.available_qty) }} {{ selected.uom }} available in {{ context.warehouse || 'the parts warehouse' }}</small></div>
            <label class="pw708-label">Required quantity<input v-model.number="quantity" type="number" min="0.001" step="any" /></label>
            <p class="pw708-muted">Parts can be requested when out of stock; issuance requires available stock.</p>
          </template>
          <template v-else-if="modal === 'request'">
            <div class="pw708-formgrid"><div><small>Material Request Type</small><strong>Material Issue</strong></div><div><small>Company</small><strong>{{ context.company }}</strong></div><div><small>Linked Service Job</small><strong>{{ jobName }}</strong></div><div><small>Source Warehouse</small><strong>{{ context.warehouse }}</strong></div></div>
            <div class="pw708-scroll"><table class="pw708-table"><thead><tr><th>Item</th><th>Qty</th><th>UOM</th></tr></thead><tbody><tr v-for="part in lines" :key="part.item_code"><td>{{ part.item_name }} <small>{{ part.item_code }}</small></td><td>{{ part.qty }}</td><td>{{ part.uom }}</td></tr></tbody></table></div>
            <label class="pw708-label">Parts requirement notes<textarea v-model="remarks" rows="3" maxlength="500" placeholder="Diagnosis / reason for replacement / urgency"></textarea></label>
            <p class="pw708-muted">Creates a Draft Material Request only — no Stock Entry and no stock deduction.</p>
          </template>
          <template v-else-if="modal === 'stock'">
            <p v-if="busy && !preview" class="pw708-muted" role="status">Loading stock availability…</p>
            <button v-else-if="!preview" type="button" class="pw708-light" @click="openStock(selectedMR)">Retry</button>
            <template v-else>
              <div class="pw708-formgrid"><div><small>Issue from</small><strong>{{ preview.warehouse }}</strong></div><div><small>Material Request</small><strong>{{ preview.material_request }}</strong></div></div>
              <div class="pw708-scroll"><table class="pw708-table"><thead><tr><th>Item</th><th>Required</th><th>On hand</th><th>Reserved</th><th>Available</th></tr></thead><tbody>
                <tr v-for="part in preview.items" :key="part.item_code">
                  <td>{{ part.item_name }} <small>{{ part.item_code }}</small><small v-if="part.serial_or_batch">Serial/batch review required in ERPNext</small></td>
                  <td>{{ number(part.qty) }} {{ part.uom }}</td><td>{{ part.on_hand ?? '—' }}</td><td>{{ part.reserved ?? '—' }}</td>
                  <td :class="{ 'pw708-insufficient':part.available + 0.000001 < part.qty }">{{ number(part.available) }} {{ part.uom }}</td>
                </tr>
              </tbody></table></div>
              <div v-if="shortages.length" class="pw708-shortage" role="status">
                <strong>Stock needed before issue</strong>
                <ul><li v-for="part in shortages" :key="part.item_code">
                  <b>{{ part.item_code }}</b> · Short {{ number(part.shortage ?? (part.qty - part.available)) }} {{ part.uom }}
                  <span v-for="balance in part.other_warehouses" :key="balance.warehouse">{{ balance.warehouse }} · {{ number(balance.available) }} {{ part.uom }} available</span>
                </li></ul>
                <p v-if="stockElsewhere">For stock held elsewhere, submit a Material Transfer into <b>{{ preview.warehouse }}</b> in ERPNext, then refresh.</p>
                <p v-if="needsIncomingStock">For items without an available balance in the warehouses you can access, receive actual incoming stock or submit its supplier Purchase Receipt.</p>
                <div class="pw708-stock-actions">
                  <a v-if="stockElsewhere" href="/app/stock-entry" target="_blank" rel="noopener">Open Stock Entry</a>
                  <button v-if="needsIncomingStock" type="button" class="pw708-light" :disabled="busy" @click="receiveForIssue">Receive physical stock</button>
                </div>
              </div>
              <template v-if="!draftEntry">
                <button type="button" class="pw708-light pw708-accounting" :aria-expanded="showAccounting" @click="showAccounting = !showAccounting">Accounting details</button>
                <div v-if="showAccounting">
                  <div class="pw708-controls">
                    <label class="pw708-label">Expense Account<select v-model="expenseAccount"><option value="">Choose expense account</option><option v-for="x in preview.expense_accounts" :key="x" :value="x">{{ x }}</option></select></label>
                    <label class="pw708-label">Cost Center<select v-model="costCenter"><option value="">Choose cost center</option><option v-for="x in preview.cost_centers" :key="x" :value="x">{{ x }}</option></select></label>
                  </div>
                  <label class="pw708-label">Remarks <span class="pw708-muted">(optional)</span><textarea v-model="issueRemarks" rows="2" maxlength="500" /></label>
                </div>
                <p v-if="!expenseAccount || !costCenter" class="pw708-muted">Choose the missing accounting defaults before saving the draft.</p>
              </template>
              <template v-else>
                <div class="pw708-selected"><strong>Draft {{ draftEntry }}</strong><a :href="`/app/stock-entry/${encodeURIComponent(draftEntry)}`" target="_blank" rel="noopener">Open in ERPNext</a></div>
                <p v-if="requiresDesk" class="pw708-muted">Open the draft in ERPNext to select serial or batch numbers and issue these parts.</p>
                <label v-else-if="preview.can_submit && !shortages.length" class="pw708-confirm-issue"><input v-model="confirmed" :disabled="busy" type="checkbox" /> I checked the parts and quantities.</label>
              </template>
            </template>
          </template>
        </div>
        <footer class="pw708-dialog-footer"><button type="button" class="pw708-light" :disabled="busy" @click="closeModal">Close</button>
          <button v-if="modal === 'stock' && preview" type="button" class="pw708-light" :disabled="busy" @click="openStock(selectedMR, true)">Refresh availability</button>
          <button v-if="modal === 'add'" type="button" class="pw708-primary" :disabled="!selected || busy" @click="addLine">+ Add to Parts Table</button>
          <button v-else-if="modal === 'request'" type="button" class="pw708-primary" :disabled="busy || !validateLines()" @click="saveRequest">{{ busy ? 'Creating…' : 'Create Draft Material Request' }}</button>
          <button v-else-if="modal === 'stock' && preview && !draftEntry" type="button" class="pw708-primary" :disabled="busy || !expenseAccount || !costCenter || !preview.can_create || preview.stock_entries.length > 0" @click="createDraft">{{ busy ? 'Saving…' : 'Save Draft' }}</button>
          <button v-else-if="modal === 'stock' && draftEntry && preview?.can_submit && !requiresDesk" type="button" class="pw708-danger" :disabled="busy || !confirmed || !!shortages.length" @click="submitEntry">{{ busy ? 'Issuing…' : 'Issue Stock' }}</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.pw708-shortage{margin:10px 0;padding:10px 12px;border:1px solid #e7c8ac;border-radius:9px;background:#fff3e7;color:#6f412a}
.pw708-shortage ul{margin:6px 0;padding:0;list-style:none}
.pw708-shortage li+li{margin-top:5px}
.pw708-shortage li span{display:block;font-size:11px;color:#705341;margin:2px 0 0}
.pw708-stock-actions{margin-top:8px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pw708-stock-actions a{color:#6a4932;font-weight:750;text-decoration:underline}
.pw708-dialog-footer{flex-wrap:wrap}
.pw708-accounting{margin-top:9px}
.pw708-confirm-issue{display:flex;align-items:center;gap:8px;margin-top:9px;font-weight:650;cursor:pointer}
.pw708-confirm-issue input{width:16px;height:16px;accent-color:#735038}
/* SOS_CHECKOUT_STOCK_COMPACT_712 */
.sos712-parts-actions{display:flex;gap:6px;flex-wrap:wrap;align-items:center}.sos712-parts-actions .pw708-light{font-size:11px;padding:7px 9px}.pw708 .pw708-top{gap:10px}

.pw708 { background:#fbf7f1; color:#4b3425; border:1px solid #e2cdb8; border-radius:15px; padding:14px; margin:10px 0; font-family:inherit; font-size:12px; box-sizing:border-box }
.pw708 *, .pw708-overlay * { box-sizing:border-box }
.pw708-top,.pw708-section-head,.pw708-footer,.pw708-record-head,.pw708-record-actions,.pw708-dialog-head,.pw708-dialog-footer { display:flex; justify-content:space-between; gap:12px; align-items:center }
.pw708-kicker { color:#a68463; font-weight:800; font-size:10px; letter-spacing:.08em }
.pw708 h3,.pw708-dialog h3 { font-size:17px; line-height:1.3; margin:4px 0; color:#3d281b; font-weight:800 }
.pw708 p,.pw708-dialog p { margin:4px 0; line-height:1.45; color:#896d58 }
.pw708 button,.pw708-overlay button { font-family:inherit; cursor:pointer; font-weight:700 }
.pw708 button:disabled,.pw708-overlay button:disabled { cursor:not-allowed; opacity:.47 }
.pw708-primary,.pw708-light,.pw708-danger { padding:9px 12px; border-radius:9px; border:1px solid #d9c2ab; background:#fffdfa; color:#6a4932; font-size:12px; white-space:nowrap }
.pw708-primary { background:#78533b; border-color:#78533b; color:#fff }
.pw708-danger { background:#9b4337; border-color:#9b4337; color:#fff }
.pw708-plus { font-size:18px; font-weight:700; vertical-align:middle; padding-right:3px }
.pw708-metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; margin:12px 0 }
.pw708-metrics > div { padding:11px 12px; border:1px solid #ebdacb; background:#f4e9dd; border-radius:11px; display:grid; gap:4px }
.pw708-metrics small,.pw708-formgrid small { color:#866c56; font-size:10px }
.pw708-metrics strong { font-size:22px; line-height:1; color:#533722 }
.pw708-tabs { display:flex; border-bottom:1px solid #e1cdbb; gap:14px }
.pw708-tabs button { border:0; background:transparent; color:#957864; border-bottom:2px solid transparent; font-size:12px; padding:10px 4px }
.pw708-tabs button.active { color:#61402a; border-bottom-color:#875b3c }
.pw708-tabs span { background:#eee2d6; border-radius:20px; padding:1px 6px; margin-left:4px }
.pw708-section { background:#fffdf9; border:1px solid #eadcd0; border-radius:11px; padding:12px; margin:12px 0 }
.pw708-section-head { margin-bottom:10px; flex-wrap:wrap }
.pw708-section-head strong { font-size:13px }
.pw708-section-head p { font-size:11px }
.pw708-scroll { overflow-x:auto; min-width:0; width:100% }
.pw708-table { width:100%; border-collapse:collapse; min-width:520px; text-align:left }
.pw708-table th { font-size:10px; background:#f5ede4; color:#7b5e48; padding:9px; border-bottom:1px solid #e6d6c8 }
.pw708-table td { font-size:11px; color:#503a2b; padding:9px; border-bottom:1px solid #f1e7dc; vertical-align:middle }
.pw708-table td strong { display:block; font-size:11px }.pw708-table td small { display:block; color:#9b826b; font-size:10px }
.pw708-table input { width:86px; max-width:100%; padding:6px; border:1px solid #deccba; border-radius:7px; background:white }
.pw708-table.mini { min-width:320px }.pw708-table.mini td { padding:7px }
.pw708-empty { text-align:center; padding:22px; color:#9a8068; font-size:11px }
.pw708-remove { background:#fff4ee; color:#a65343; border:1px solid #f0d8c9; border-radius:7px; padding:3px 8px; font-size:18px }
.pw708-footer { margin-top:12px; flex-wrap:wrap }.pw708-footer span { color:#987f68; font-size:11px }
.pw708-record { background:#fcf9f4; border:1px solid #e8d9c9; border-radius:10px; padding:11px; margin-bottom:10px }
.pw708-record-head strong { color:#523723; font-size:13px }.pw708-record-head small { display:block; color:#947a67; margin-top:4px }
.pw708-status { padding:4px 8px; font-size:10px; font-weight:800; border-radius:20px; background:#f4e5d0; color:#7b583b }
.pw708-status.approved { background:#e9eee3; color:#466441 }.pw708-status.cancelled { background:#f6e7e4; color:#a45a4c }
.pw708-record-actions { justify-content:flex-start; flex-wrap:wrap; margin-top:10px }
.pw708-record-actions a,.pw708-links a { color:#805532; text-decoration:underline; font-size:11px }
.pw708-confirm { color:#3f694a; font-weight:800; font-size:11px }
.pw708-links { display:flex; flex-wrap:wrap; gap:8px; color:#93775b; margin-top:10px; font-size:11px }
.pw708-alert { padding:10px; border-radius:8px; margin:9px 0; border:1px solid }
.pw708-alert.error { color:#973b32; background:#fff0ec; border-color:#edcbc2 }
.pw708-alert.success { color:#386848; background:#f0f7ef; border-color:#c9e2ca }
.pw708-disclaimer { font-size:10px; padding:9px 2px; color:#987f67 }
.pw708-overlay { position:fixed; inset:0; z-index:100000; display:flex; align-items:center; justify-content:center; background:rgba(32,23,16,.55); padding:16px; overflow:auto }
.pw708-dialog { width:min(760px,100%); max-height:min(90vh,900px); display:flex; flex-direction:column; background:#fffcf7; border:1px solid #e2cbb7; border-radius:16px; box-shadow:0 30px 100px #26170a55; color:#4b3425; font-family:inherit }
.pw708-dialog-head { padding:16px 19px; border-bottom:1px solid #ecdfd0; align-items:flex-start }.pw708-dialog-head p { font-size:12px }
.pw708-close { background:#f7ecdf; border:0; border-radius:8px; width:34px; height:34px; font-size:21px; color:#74533d }
.pw708-dialog-body { overflow-y:auto; padding:16px 19px; display:grid; gap:12px }
.pw708-dialog-footer { padding:14px 19px; border-top:1px solid #ecdfd0; justify-content:flex-end; flex-wrap:wrap }
.pw708-label { font-size:11px; font-weight:800; color:#735743; display:grid; gap:5px }
.pw708-label input,.pw708-label select,.pw708-label textarea { background:white; color:#433123; font-size:12px; border:1px solid #d9c4b1; border-radius:8px; padding:10px; width:100%; min-width:0 }
.pw708-results { display:grid; border:1px solid #eadbce; border-radius:9px; overflow:auto; max-height:260px }
.pw708-results button { display:grid; gap:3px; text-align:left; padding:10px; border:0; border-bottom:1px solid #f2e8df; background:white; font-size:11px; color:#503522 }
.pw708-results button:hover { background:#f7eee4 }.pw708-results small,.pw708-selected small { font-size:10px; color:#91775f }
.pw708-selected { background:#f7ede2; border:1px solid #e4d0bc; border-radius:10px; padding:12px; display:grid; gap:4px }
.pw708-selected a { font-size:11px; color:#795336; text-decoration:underline }
.pw708-muted { color:#997d66; font-size:11px }
.pw708-formgrid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px }
.pw708-formgrid > div { background:#f7efe6; border:1px solid #e9dccc; border-radius:8px; padding:10px; display:grid; gap:3px; min-width:0; overflow-wrap:anywhere }
.pw708-formgrid strong { font-size:12px }
.pw708-controls { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px }
.pw708-insufficient { color:#b04e40!important; font-weight:800 }
@media(max-width:600px) { .pw708 { padding:10px }.pw708-metrics { gap:5px }.pw708-metrics > div { padding:8px }.pw708-metrics strong { font-size:17px }.pw708-formgrid,.pw708-controls { grid-template-columns:1fr }.pw708-dialog { max-height:95vh }.pw708-dialog-head,.pw708-dialog-body,.pw708-dialog-footer { padding:13px } }
</style>
