<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import InvoiceFinancialTotals from './InvoiceFinancialTotals.vue'
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
const income = computed(() => result.value?.income_summary)
const dailyLimit = ref(7)
const dailyRows = computed(() => income.value?.daily?.slice(0, dailyLimit.value) || [])
const totals = computed(() => result.value?.financial_totals)
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
    if (applied !== filters) dailyLimit.value = 7
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

function showInvoice(row, checkout = false, pay = false) {
  preview.value = { name: row.name, doctype: selectedType.value, previewOnly: Number(row.docstatus) !== 1, checkout, pay }
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

    <form class="invoice-filters workspace-filters" :class="{'with-stream':showStream}" @submit.prevent="apply">
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

    <section v-if="income && !loading && !error" class="invoice-income" aria-label="Income for the current filters">
      <div class="invoice-income-lead">
        <h3>Net invoice income</h3>
        <strong>{{ income.currency }} {{ formatAmount.format(income.total) }}</strong>
        <p>{{ income.invoice_count }} submitted {{ income.invoice_count === 1 ? 'invoice' : 'invoices' }} across all matching pages</p>
      </div>
      <div class="invoice-income-breakdown">
        <dl>
          <div v-for="(amount, label) in income.streams" :key="label">
            <dt>{{ label }}</dt>
            <dd>{{ income.currency }} {{ formatAmount.format(amount) }}</dd>
          </div>
        </dl>
        <small>Before tax, after returns</small>
      </div>
      <div v-if="income.daily" class="invoice-income-daily">
        <div class="invoice-daily-head">
          <div>
            <h4>Daily invoice and cost breakdown</h4>
            <p>Invoice sales and counts follow your filters. Purchase invoices, posted costs, and net profit cover the company by posting date.</p>
          </div>
          <span v-if="income.daily.length">{{ income.daily.length }} {{ income.daily.length === 1 ? 'day' : 'days' }}</span>
        </div>
        <p v-if="!dailyRows.length" class="invoice-daily-empty">No daily activity matches these filters.</p>
        <template v-else>
          <div class="invoice-daily-scroll" role="region" aria-label="Daily invoice and cost breakdown" tabindex="0">
            <table class="invoice-daily-table">
              <thead><tr>
                <th scope="col">Posting date</th><th scope="col">Invoices</th><th scope="col">Net invoiced</th>
                <th scope="col">Purchase invoices</th><th scope="col">Posted COGS</th><th scope="col">Net profit</th>
              </tr></thead>
              <tbody>
                <tr v-for="row in dailyRows" :key="row.date">
                  <th scope="row"><time :datetime="row.date">{{ row.date }}</time></th>
                  <td>{{ row.count }}</td><td>{{ income.currency }} {{ formatAmount.format(row.sales) }}</td>
                  <td v-for="key in ['purchases', 'cogs', 'profit']" :key="key" :class="{ 'invoice-daily-loss': key === 'profit' && row[key] < 0 }">
                    <template v-if="row[key] != null">{{ income.currency }} {{ formatAmount.format(row[key]) }}</template>
                    <span v-else class="invoice-daily-unavailable">Unavailable</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <button v-if="dailyRows.length < income.daily.length" type="button" class="invoice-button invoice-daily-more"
            @click="dailyLimit += 7">Show more days</button>
        </template>
      </div>
    </section>

    <p v-if="labelMessage" class="invoice-message" role="status">{{ labelMessage }}</p>
    <p v-if="labelError" class="invoice-message invoice-error" role="alert">{{ labelError }}</p>
    <div class="invoice-results" :aria-busy="loading">
      <p v-if="loading" class="invoice-message" role="status">Loading invoices…</p>
      <p v-else-if="error" class="invoice-message invoice-error" role="alert">{{ error }}</p>
      <div v-else-if="result" class="invoice-table-scroll" tabindex="0" role="region" aria-label="Invoice records">
        <table class="invoice-table">
          <thead><tr><th scope="col">Invoice</th><th scope="col">Customer</th><th scope="col">Posting date</th><th scope="col">Status</th><th v-if="showStream" scope="col">Revenue stream</th><th scope="col" class="amount">Total</th><th scope="col">Actions</th></tr></thead>
          <tbody>
            <tr v-if="!rows.length"><td :colspan="showStream ? 7 : 6">No invoices match these filters.</td></tr>
            <tr v-for="row in rows" :key="row.name">
              <td>
                <button type="button" class="invoice-link" @click="showInvoice(row, true)">{{ row.name }}</button>
                <small v-if="row.custom_service_job">{{ row.custom_service_job }}</small>
                <small v-if="row.is_return">Return</small>
              </td>
              <td>{{ row.customer_name || row.customer || '—' }}</td>
              <td><time v-if="row.posting_date" :datetime="row.posting_date">{{ row.posting_date }}</time></td>
              <td><span class="invoice-status">{{ row.status || documentStates[row.docstatus] || '—' }}</span>
                <small v-if="showStream && Number(row.docstatus) === 1 && Number(row.outstanding_amount) > 0">
                  Due {{ row.currency }} {{ formatAmount.format(row.outstanding_amount) }}
                </small>
              </td>
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
              <td><div class="row-invoice-actions">
                <button type="button" class="invoice-button" :aria-label="'Preview ' + row.name" @click="showInvoice(row)">Preview</button>
                <button v-if="result?.can_receive_payment && Number(row.docstatus) === 1 && !Number(row.is_return) && Number(row.outstanding_amount) > 0"
                  type="button" class="invoice-button primary" :aria-label="'Receive payment for ' + row.name" @click="showInvoice(row, true, true)">Receive payment</button>
              </div></td>
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
    <InvoiceFinancialTotals class="invoice-register-totals" v-if="totals && !loading && !error" :totals="totals" show-register-scope />
    <UnifiedInvoicePrint684 v-if="preview" :key="preview.doctype + preview.name" :invoice-name="preview.name"
      :doctype="preview.doctype" :preview-only="preview.previewOnly" :checkout="preview.checkout" :start-payment="preview.pay" :submit-draft="preview.checkout" @close="preview = null" />
  </section>
</template>

<style scoped src="./workspaceFilters.css"></style>
<style scoped>
.invoices{container-type:inline-size;color:var(--os-ink,#382820);background:var(--os-surface,#fffdf9);border:1px solid var(--os-border,#e7d7c7);border-radius:18px;overflow:hidden}
.invoice-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:24px;background:var(--os-tint,#f7eee4);border-bottom:1px solid var(--os-border,#e7d7c7)}
.invoice-header h2{margin:0;font:clamp(1.9rem,4vw,2.6rem)/1.12 Georgia,serif}
.invoice-header p{margin:5px 0 0;color:var(--os-muted,#705743);font-size:.82rem}
.invoice-types,.invoice-filters{padding:14px 24px;border-bottom:1px solid var(--os-border,#ebded0)}
.invoice-types,.filter-actions{display:flex;flex-wrap:wrap;gap:8px}
.invoice-filters{display:grid;grid-template-columns:minmax(140px,1.6fr) repeat(3,minmax(110px,1fr)) auto;gap:10px;align-items:end}
.invoice-filters.with-stream{grid-template-columns:minmax(140px,1.6fr) repeat(4,minmax(110px,1fr)) auto}
.invoice-filters label{display:grid;gap:5px;min-width:0;font-size:.76rem;font-weight:650;color:var(--os-muted,#624a38)}
.invoice-filters input,.invoice-filters select,.invoice-button{min-width:0;min-height:38px;background:var(--os-surface,#fffdf9);border:1px solid var(--os-border,#d9c4af);border-radius:8px;padding:7px 11px;color:var(--os-ink,#382820);font-size:.82rem}
.invoice-filters input,.invoice-filters select{font:inherit;font-size:.82rem;font-weight:450;line-height:1.25}
.row-invoice-actions{display:flex;flex-wrap:wrap;gap:6px}
.invoice-button{font-weight:650;white-space:nowrap}
.invoice-button:not(:disabled):hover{border-color:var(--os-accent,#795337)}
.invoice-button:focus-visible,.invoice-filters input:focus-visible,.invoice-filters select:focus-visible,.invoice-link:focus-visible,.invoice-label-editor select:focus-visible{outline:2px solid var(--os-accent,#8b5d3c);outline-offset:2px}
.invoice-button.primary,.invoice-button[aria-pressed="true"]{background:var(--os-accent,#765239);border-color:var(--os-accent,#765239);color:#fff}
.invoice-button:disabled{opacity:.48;cursor:default}
.invoice-table-scroll{overflow:auto}
.invoice-table{width:100%;border-collapse:collapse;text-align:left;font-size:.86rem}
.invoice-table th,.invoice-table td{padding:12px 16px;border-bottom:1px solid var(--os-border,#ebded0)}
.invoice-table th{background:var(--os-tint,#f8f1e8);color:var(--os-ink,#694f3c);font-size:.75rem;white-space:nowrap}
.invoice-link{border:0;background:none;padding:0;cursor:pointer;text-align:left;color:var(--os-strong,#5b3a25);font-weight:700;text-decoration:underline;text-underline-offset:3px}
.invoice-label-link{display:block;font-size:.75rem;margin-top:3px}
.invoice-label-editor{min-width:155px;padding-top:5px}
.invoice-label-editor label{display:grid;gap:4px;font-size:.75rem;margin:0}
.invoice-label-editor select{width:100%;min-height:34px;border:1px solid var(--os-border,#d9c4af);border-radius:8px;background:var(--os-surface,#fffdfa);padding:4px 7px}
.invoice-label-editor button{min-height:32px;font-size:.75rem;margin:5px 4px 0 0}
.invoice-table td small{display:block;color:var(--os-muted,#745943)}
.invoice-table .amount{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.invoice-status{display:inline-block;padding:4px 8px;background:var(--os-selection,#f2e8dc);border-radius:6px;color:var(--os-ink,#644834);white-space:nowrap}
.invoice-income{display:grid;grid-template-columns:minmax(210px,1fr) minmax(0,3fr);margin:16px 24px;border:1px solid var(--os-border,#e3cfbd);border-radius:12px;overflow:hidden;background:var(--os-tint,#fff9f1)}
.invoice-income-lead{padding:14px 18px;background:var(--os-accent,#6b4b37);color:#fff}
.invoice-income-lead h3,.invoice-income-lead p{margin:0;font-size:.75rem}
.invoice-income-lead strong{display:block;margin:4px 0;font-size:clamp(1.18rem,2.3vw,1.7rem);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.invoice-income-lead p{color:#fff}
.invoice-income-breakdown{display:grid;align-content:center;gap:8px;padding:12px 16px}
.invoice-income-breakdown dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,116px),1fr));gap:8px 13px;margin:0}
.invoice-income-breakdown dt,.invoice-income-breakdown small{font-size:.73rem;color:var(--os-muted,#694b36)}
.invoice-income-breakdown dd{margin:3px 0 0;font-weight:750;font-size:.85rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.invoice-register-totals{margin:8px 24px 24px}
.invoice-income-daily{grid-column:1/-1;padding:14px 16px;border-top:1px solid var(--os-border,#e3cfbd);background:var(--os-surface,#fffefa);min-width:0}
.invoice-daily-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.invoice-daily-head h4{margin:0;font-size:.94rem;font-weight:770}
.invoice-daily-head p,.invoice-daily-head>span,.invoice-daily-empty{margin:4px 0 10px;font-size:.76rem;color:var(--os-muted,#6d5b4c)}
.invoice-daily-head>span{white-space:nowrap}
.invoice-daily-scroll{overflow:auto;border:1px solid var(--os-border,#e3cfbd);border-radius:9px}
.invoice-daily-scroll:focus-visible{outline:2px solid var(--os-accent,#785238);outline-offset:2px}
.invoice-daily-table{width:100%;border-collapse:collapse;font-size:.8rem;font-variant-numeric:tabular-nums}
.invoice-daily-table :is(th,td){padding:8px 9px;white-space:nowrap;text-align:right}
.invoice-daily-table th:first-child{text-align:left}
.invoice-daily-table thead{background:var(--os-tint,#f3ebe0)}
.invoice-daily-table tbody tr{border-top:1px solid var(--os-border,#e3cfbd)}
.invoice-daily-table tbody td:last-child{font-weight:750;background:var(--os-tint,#f3ebe0)}
.invoice-daily-loss{color:#9c362e}
.invoice-daily-unavailable{font-size:.73rem;color:var(--os-muted,#6d5b4c);font-weight:500}
.invoice-daily-more{margin-top:8px}
.invoice-pager{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;padding:14px 24px;font-size:.82rem;color:var(--os-muted,#624a38)}
.invoice-message{margin:0;padding:22px 24px;color:var(--os-muted,#65503e);font-size:.9rem}
.invoice-error{color:#9c362e}
@container(max-width:840px){.invoice-filters,.invoice-filters.with-stream{grid-template-columns:repeat(3,minmax(0,1fr))}}
@container(max-width:590px){.invoice-filters,.invoice-filters.with-stream{grid-template-columns:repeat(2,minmax(0,1fr))}.invoice-filters label:first-child,.invoice-filters .filter-actions{grid-column:1/-1}}
@container(max-width:330px){.invoice-filters,.invoice-filters.with-stream{grid-template-columns:1fr}}
@container(max-width:575px){.invoice-income{grid-template-columns:minmax(0,1fr);margin-inline:12px}.invoice-register-totals{margin-inline:12px}}
@media(max-width:520px){.invoice-header,.invoice-types,.invoice-filters,.invoice-pager{padding-inline:12px}.invoice-table th,.invoice-table td{padding-inline:12px}}
</style>
