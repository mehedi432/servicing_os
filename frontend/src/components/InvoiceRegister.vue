<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import UnifiedInvoicePrint684 from './UnifiedInvoicePrint684.vue'

const invoiceTypes = {
  'Sales Invoice': { label: 'Sales invoices' },
  'POS Invoice': { label: 'POS invoices' },
}
const documentStates = ['Draft', 'Submitted', 'Cancelled']
const revenueStreams = ['Servicing', 'Retail Stock', 'Used Laptops', 'Unclassified']
const selectedType = ref('Sales Invoice')
const query = ref('')
const status = ref('')
const stream = ref('')
const showStream = computed(() => selectedType.value === 'Sales Invoice')
const from = ref('')
const to = ref('')
const result = ref(null)
const preview = ref(null)
const labelEditor = ref(null)
const labeling = ref(false)
const labelMessage = ref('')
const labelError = ref('')
const loading = ref(false)
const error = ref('')
const page = computed(() => result.value?.page || 1)
const rows = computed(() => result.value?.rows || [])
const formatAmount = new Intl.NumberFormat('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
let request = null
let applied = {}

async function load(nextPage = 1, filters = applied) {
  request?.abort()
  const controller = new AbortController()
  request = controller
  loading.value = true
  error.value = ''
  try {
    if (filters.start_date && filters.end_date && filters.start_date > filters.end_date) {
      throw new Error('From date must be on or before To date.')
    }
    const url = new URL('/api/method/servicing_os.api.billing_command_700.get_invoice_documents', window.location.origin)
    const params = { ...filters, doctype: selectedType.value, page: nextPage }
    for (const [key, value] of Object.entries(params)) {
      if (value !== '') url.searchParams.set(key, String(value))
    }
    const response = await fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: controller.signal
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok || !Array.isArray(body.message?.rows)) {
      let detail = response.status === 403 ? 'You do not have read permission for this invoice type.' : 'Unable to load invoices.'
      try {
        const [message] = JSON.parse(body._server_messages || '[]')
        if (message) detail = JSON.parse(message).message || detail
      } catch {}
      throw new Error(detail)
    }
    if (request !== controller) return
    result.value = body.message
    applied = filters
  } catch (err) {
    if (request !== controller || err.name === 'AbortError') return
    error.value = err.message || 'Unable to load invoices.'
  } finally {
    if (request === controller) loading.value = false
  }
}

function apply() {
  load(1, {
    q: query.value.trim(), docstatus: status.value,
    start_date: from.value, end_date: to.value,
    revenue_stream: showStream.value ? stream.value : '',
  })
}

function reset() {
  query.value = status.value = from.value = to.value = stream.value = ''
  apply()
}

function switchType(doctype) {
  if (doctype === selectedType.value) return
  selectedType.value = doctype
  labelEditor.value = null
  labelMessage.value = labelError.value = ''
  result.value = null
  apply()
}

function showInvoice(row) {
  preview.value = { name: row.name, doctype: selectedType.value, previewOnly: Number(row.docstatus) !== 1 }
}

function startLabel(row) {
  labelMessage.value = labelError.value = ''
  labelEditor.value = { name: row.name, stream: row.revenue_basis === 'manual' ? row.revenue_stream : '' }
}

async function saveLabel() {
  const editor = labelEditor.value
  if (labeling.value || !editor) return
  labeling.value = true
  labelError.value = ''
  try {
    const token = window.frappe?.csrf_token || window.csrf_token ||
      document.querySelector('meta[name="csrf-token"]')?.content || ''
    const response = await fetch('/api/method/servicing_os.api.billing_command_700.set_reporting_stream', {
      method: 'POST', credentials: 'same-origin',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': token },
      body: JSON.stringify({ invoice_name: editor.name, revenue_stream: editor.stream }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok || data.message?.name !== editor.name) {
      let message = 'The reporting label could not be saved.'
      try {
        const [entry] = JSON.parse(data._server_messages || '[]')
        if (entry) message = JSON.parse(entry).message || message
      } catch {}
      throw new Error(message)
    }
    labelEditor.value = null
    labelMessage.value = `${editor.name} · ${data.message.revenue_stream}`
    await load(1)
    window.dispatchEvent(new CustomEvent('servicing-os-reporting-stream-updated'))
  } catch (err) {
    labelError.value = err.message
  } finally {
    labeling.value = false
  }
}

const updateEvents = [
  'servicing-os-invoice-draft-created', 'servicing-os-invoice-finalized',
  'servicing-os-invoice-completed', 'servicing-os-sale-completed',
  'servicing-os-invoice-updated', 'servicing-os-invoice-payment-recorded'
]
function refreshRegister() {
  load(page.value)
}
onMounted(() => {
  apply()
  for (const event of updateEvents) window.addEventListener(event, refreshRegister)
})
onBeforeUnmount(() => {
  for (const event of updateEvents) window.removeEventListener(event, refreshRegister)
  request?.abort()
  request = null
})
</script>

<template>
  <section class="invoices" aria-labelledby="invoice-title">
    <header class="invoice-header">
      <div>
        <h2 id="invoice-title">All invoices</h2>
        <p v-if="result?.company">{{ result.company }}</p>
      </div>
      <button type="button" class="invoice-button" :disabled="loading" @click="load(page)">Refresh</button>
    </header>

    <div class="invoice-types" role="group" aria-label="Invoice type">
      <button v-for="(type, name) in invoiceTypes" :key="name" type="button" class="invoice-button"
        :aria-pressed="selectedType === name" @click="switchType(name)">{{ type.label }}</button>
    </div>

    <form class="invoice-filters" :class="{'with-stream':showStream}" @submit.prevent="apply">
      <label>Find an invoice
        <input v-model="query" type="search" maxlength="90"
          :placeholder="selectedType === 'Sales Invoice' ? 'Invoice no. / customer / service job' : 'Invoice no. / customer'" />
      </label>
      <label>Document status
        <select v-model="status" @change="apply">
          <option value="">All statuses</option>
          <option v-for="(state, index) in documentStates" :key="state" :value="String(index)">{{ state }}</option>
        </select>
      </label>
      <label v-if="showStream">Revenue stream
        <select v-model="stream" @change="apply">
          <option value="">All streams</option>
          <option v-for="name in revenueStreams" :key="name" :value="name">{{ name }}</option>
        </select>
      </label>
      <label>Posting date from<input v-model="from" type="date" :max="to || undefined" /></label>
      <label>Posting date to<input v-model="to" type="date" :min="from || undefined" /></label>
      <div class="filter-actions">
        <button type="submit" class="invoice-button primary">Apply</button>
        <button type="button" class="invoice-button" @click="reset">Clear</button>
      </div>
    </form>

    <p v-if="labelMessage" class="invoice-message" role="status">{{ labelMessage }}</p>
    <p v-if="labelError" class="invoice-message invoice-error" role="alert">{{ labelError }}</p>
    <div class="invoice-results" :aria-busy="loading">
      <p v-if="loading" class="invoice-message" role="status">Loading invoices…</p>
      <p v-else-if="error" class="invoice-message invoice-error" role="alert">{{ error }}</p>
      <p v-else-if="!rows.length" class="invoice-message" role="status">No invoices match these filters.</p>
      <div v-else class="invoice-table-scroll" tabindex="0" role="region" aria-label="Invoice records">
        <table class="invoice-table">
          <thead><tr><th scope="col">Invoice</th><th scope="col">Customer</th><th scope="col">Posting date</th><th scope="col">Status</th><th v-if="showStream" scope="col">Revenue stream</th><th scope="col" class="amount">Total</th><th scope="col">View</th></tr></thead>
          <tbody>
            <tr v-for="row in rows" :key="row.name">
              <td>
                <button type="button" class="invoice-link" @click="showInvoice(row)">{{ row.name }}</button>
                <small v-if="row.custom_service_job">{{ row.custom_service_job }}</small>
                <small v-if="row.is_return">Return</small>
              </td>
              <td>{{ row.customer_name || row.customer || '—' }}</td>
              <td><time v-if="row.posting_date" :datetime="row.posting_date">{{ row.posting_date }}</time></td>
              <td><span class="invoice-status">{{ row.status || documentStates[row.docstatus] || '—' }}</span></td>
              <td v-if="showStream">
                <span>{{ row.revenue_stream || 'Unclassified' }}</span>
                <small v-if="row.revenue_basis === 'historical'">From invoice history</small>
                <small v-if="row.revenue_basis === 'manual'">Reporting label</small>
                <form v-if="labelEditor?.name === row.name" class="invoice-label-editor" @submit.prevent="saveLabel">
                  <label>Reporting stream
                    <select v-model="labelEditor.stream" :disabled="labeling">
                      <option value="">{{ row.revenue_basis === 'manual' ? 'Clear reporting label' : 'Choose a stream' }}</option>
                      <option v-for="choice in revenueStreams.slice(0, -1)" :key="choice" :value="choice">{{ choice }}</option>
                    </select>
                  </label>
                  <small>Applies to reports only.</small>
                  <button type="submit" class="invoice-button" :disabled="labeling || (!labelEditor.stream && row.revenue_basis !== 'manual')">Save label</button>
                  <button type="button" class="invoice-button" :disabled="labeling" @click="labelEditor = null; labelError = ''">Close</button>
                </form>
                <button v-else-if="result?.can_label_stream && Number(row.docstatus) === 1 &&
                    ['unclassified', 'manual'].includes(row.revenue_basis)" class="invoice-link invoice-label-link"
                  type="button" @click="startLabel(row)">{{ row.revenue_basis === 'manual' ? 'Change label' : 'Classify' }}</button>
              </td>
              <td class="amount">{{ row.currency }} {{ formatAmount.format(row.grand_total ?? 0) }}</td>
              <td><button type="button" class="invoice-button" :aria-label="'Preview ' + row.name" @click="showInvoice(row)">Preview</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer v-if="result && !error" class="invoice-pager">
        <button type="button" class="invoice-button" :disabled="loading || page <= 1" @click="load(page - 1)">Previous</button>
        <span>Page {{ page }} · {{ result.page_size }} per page</span>
        <button type="button" class="invoice-button" :disabled="loading || !result.has_next" @click="load(page + 1)">Next</button>
      </footer>
    </div>
    <UnifiedInvoicePrint684 v-if="preview" :key="preview.doctype + preview.name" :invoice-name="preview.name"
      :doctype="preview.doctype" :preview-only="preview.previewOnly" submit-draft @close="preview = null" />
  </section>
</template>

<style scoped>
.invoices{color:#382820;background:#fffdf9;border:1px solid #e7d7c7;border-radius:18px;overflow:hidden}
.invoice-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:24px;background:#f7eee4;border-bottom:1px solid #e7d7c7}
.invoice-header h2{margin:0;font:clamp(1.9rem,4vw,2.6rem)/1.12 Georgia,serif}
.invoice-header p{margin:5px 0 0;color:#705743;font-size:.82rem}
.invoice-types,.invoice-filters{padding:14px 24px;border-bottom:1px solid #ebded0}
.invoice-types,.filter-actions{display:flex;flex-wrap:wrap;gap:8px}
.invoice-filters{display:grid;grid-template-columns:minmax(180px,2fr) repeat(3,minmax(126px,1fr)) auto;gap:10px;align-items:end}
.invoice-filters.with-stream{grid-template-columns:minmax(154px,1.7fr) repeat(4,minmax(120px,1fr)) auto}
.invoice-filters label{display:grid;gap:5px;min-width:0;font-size:.76rem;font-weight:650;color:#624a38}
.invoice-filters input,.invoice-filters select,.invoice-button{min-width:0;min-height:38px;background:#fffdf9;border:1px solid #d9c4af;border-radius:8px;padding:7px 11px;color:#382820;font-size:.82rem}
.invoice-filters input,.invoice-filters select{width:100%;height:38px;margin:0;font:inherit;font-size:.82rem;font-weight:450;line-height:1.25}
.invoice-button{font-weight:650;white-space:nowrap}
.invoice-button:not(:disabled):hover{border-color:#795337}
.invoice-button:focus-visible,.invoice-filters input:focus-visible,.invoice-filters select:focus-visible,.invoice-link:focus-visible,.invoice-label-editor select:focus-visible{outline:2px solid #8b5d3c;outline-offset:2px}
.invoice-button.primary,.invoice-button[aria-pressed="true"]{background:#765239;border-color:#765239;color:#fffdf9}
.invoice-button:disabled{opacity:.48;cursor:default}
.invoice-table-scroll{overflow:auto}
.invoice-table{width:100%;border-collapse:collapse;text-align:left;font-size:.86rem}
.invoice-table th,.invoice-table td{padding:12px 16px;border-bottom:1px solid #ebded0}
.invoice-table th{background:#f8f1e8;color:#694f3c;font-size:.75rem;white-space:nowrap}
.invoice-link{border:0;background:none;padding:0;cursor:pointer;text-align:left;color:#5b3a25;font-weight:700;text-decoration:underline;text-underline-offset:3px}
.invoice-label-link{display:block;font-size:.75rem;margin-top:3px}
.invoice-label-editor{min-width:155px;padding-top:5px}
.invoice-label-editor label{display:grid;gap:4px;font-size:.75rem;margin:0}
.invoice-label-editor select{width:100%;min-height:34px;border:1px solid #d9c4af;border-radius:8px;background:#fffdfa;padding:4px 7px}
.invoice-label-editor button{min-height:32px;font-size:.75rem;margin:5px 4px 0 0}
.invoice-table td small{display:block;color:#745943}
.invoice-table .amount{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.invoice-status{display:inline-block;padding:4px 8px;background:#f2e8dc;border-radius:6px;color:#644834;white-space:nowrap}
.invoice-pager{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;padding:14px 24px;font-size:.82rem;color:#624a38}
.invoice-message{margin:0;padding:22px 24px;color:#65503e;font-size:.9rem}
.invoice-error{color:#9c362e}
@media(max-width:1280px){.invoice-filters,.invoice-filters.with-stream{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:520px){.invoice-header,.invoice-types,.invoice-filters,.invoice-pager{padding-inline:12px}.invoice-table th,.invoice-table td{padding-inline:12px}}
</style>
