<script setup>
// SERVICING_OS_CASH_UI_617B
import { ref, computed } from 'vue'

const open = ref(false)
const busy = ref(false)
const saving = ref(false)
const invoices = ref([])
const canCreate = ref(false)
const selected = ref('')
const search = ref('')
const amount = ref('')
const error = ref('')
const success = ref('')
const created = ref('')

const matching = computed(() => invoices.value.filter(inv =>
  [inv.name, inv.customer, inv.custom_service_job, inv.status]
    .join(' ').toLowerCase().includes(search.value.trim().toLowerCase())
))
const invoice = computed(() => invoices.value.find(inv => inv.name === selected.value) || null)
const valid = computed(() => {
  const n = Number(amount.value)
  return invoice.value && Number.isFinite(n) && amount.value !== '' && n > 0 &&
    Math.abs(Math.round(n * 100) - n * 100) < 1e-7 && n <= Number(invoice.value.outstanding_amount) &&
    Number(invoice.value.outstanding_amount) > 0 && canCreate.value && !saving.value && !created.value
})
const fmt = n => '৳' + Number(n || 0).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const csrf = () => window.frappe?.csrf_token || window.csrf_token ||
  decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('csrf_token='))?.split('=').slice(1).join('=') || '')
function parseError(data) {
  if (data._server_messages) {
    try {
      const rows = JSON.parse(data._server_messages)
      const last = JSON.parse(rows[rows.length - 1])
      return String(last.message || 'Request failed').replace(/<[^>]*>/g, '')
    } catch { /* fallback below */ }
  }
  return data.message?.message || data.exception || data.exc_type || 'ERPNext request failed'
}
async function call(method, args = {}, post = false) {
  const url = new URL('/api/method/servicing_os.api.cash_collection.' + method, window.location.origin)
  const options = { method: post ? 'POST' : 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (post) {
    options.headers['Content-Type'] = 'application/json'
    options.headers['X-Frappe-CSRF-Token'] = csrf()
    options.body = JSON.stringify(args)
  } else {
    for (const [key, value] of Object.entries(args)) url.searchParams.set(key, String(value))
  }
  const response = await fetch(url, options)
  let body
  try { body = await response.json() } catch { throw new Error('Unexpected server response (' + response.status + ')') }
  if (!response.ok || body.exc || body.exc_type) throw new Error(parseError(body))
  return body.message
}
async function load() {
  error.value = ''
  busy.value = true
  try {
    const data = await call('get_cash_collection_overview', { limit: 200 })
    invoices.value = data?.invoices || []
    canCreate.value = Boolean(data?.can_create_payment)
    if (selected.value && !invoices.value.some(i => i.name === selected.value)) {
      selected.value = ''
      amount.value = ''
    }
  } catch (e) { error.value = e.message || String(e) }
  finally { busy.value = false }
}
function show() {
  open.value = true
  error.value = ''
  success.value = ''
  created.value = ''
  load()
}
function close() {
  if (!saving.value) open.value = false
}
function selectInvoice(name) {
  selected.value = name
  const item = invoices.value.find(i => i.name === name)
  amount.value = item ? String(Number(item.outstanding_amount).toFixed(2)) : ''
  error.value = ''
  success.value = ''
  created.value = ''
}
async function prepare() {
  if (!valid.value) return
  const chosen = invoice.value
  if (!window.confirm('Create a DRAFT cash Payment Entry for ' + chosen.name + ' of ' + fmt(amount.value) + '? No cash or ledger will be posted until ERPNext submission.')) return
  saving.value = true
  error.value = ''
  try {
    const result = await call('create_cash_payment_draft', { invoice_name: chosen.name, amount: amount.value }, true)
    created.value = result.payment_entry
    success.value = 'Draft ' + result.payment_entry + ' created. Confirm receipt of cash, then review and submit it in ERPNext.'
  } catch (e) { error.value = e.message || String(e) }
  finally { saving.value = false }
}
function openDesk(doctype, name) {
  const route = doctype === 'Payment Entry' ? 'payment-entry' : 'sales-invoice'
  window.open('/app/' + route + '/' + encodeURIComponent(name), '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <button type="button" class="pay-launch" @click="show">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20M16 15h3"/></svg>
    Collect Payment
  </button>
  <Teleport to="body">
    <div v-if="open" class="pay-shade" @click.self="close">
      <section class="pay-dialog" role="dialog" aria-modal="true" aria-labelledby="pay-dialog-title">
        <header class="pay-header">
          <div><div class="pay-eyebrow">SERVICING OS / ACCOUNTS</div><h2 id="pay-dialog-title">Cash Collection</h2><p>Submitted repair invoices only · Full and partial payments</p></div>
          <button type="button" class="pay-close" aria-label="Close" :disabled="saving" @click="close">✕</button>
        </header>
        <div class="pay-content">
          <p v-if="error" class="pay-alert pay-error" role="alert">{{ error }}</p>
          <p v-if="success" class="pay-alert pay-success" role="status">{{ success }}</p>
          <div v-if="created" class="pay-created"><strong>Draft payment prepared</strong><p>Do not mark cash as received until the actual payment is collected and the Payment Entry is submitted.</p><button type="button" @click="openDesk('Payment Entry', created)">Open {{ created }} in ERPNext ↗</button></div>
          <div v-else class="pay-columns">
            <section class="pay-list">
              <div class="pay-section-head"><div><span>01 · SELECT</span><h3>Outstanding repair invoices</h3></div><button type="button" class="pay-textbutton" :disabled="busy" @click="load">{{ busy ? 'Loading…' : 'Refresh' }}</button></div>
              <input v-model="search" class="pay-input" type="search" placeholder="Search invoice, job, customer…" aria-label="Find invoice" />
              <div class="pay-list-scroll">
                <button v-for="i in matching" :key="i.name" type="button" class="pay-invoice" :class="{ active: selected === i.name }" @click="selectInvoice(i.name)">
                  <span class="pay-invoice-line"><strong>{{ i.name }}</strong><span>{{ fmt(i.outstanding_amount) }} due</span></span>
                  <span class="pay-invoice-sub">{{ i.custom_service_job }} · {{ i.customer }}</span>
                  <small>{{ i.status }} · {{ i.posting_date }}</small>
                </button>
                <p v-if="!matching.length && !busy" class="pay-empty">No submitted repair invoices match. First submit a Sales Invoice in ERPNext.</p>
              </div>
            </section>
            <section class="pay-form">
              <div class="pay-section-head"><div><span>02 · PREPARE</span><h3>Cash payment</h3></div></div>
              <template v-if="invoice">
                <div class="pay-details"><div><span>Invoice</span><strong>{{ invoice.name }}</strong></div><div><span>Repair</span><strong>{{ invoice.custom_service_job }}</strong></div><div><span>Customer</span><strong>{{ invoice.customer }}</strong></div><div><span>Invoice total</span><strong>{{ fmt(invoice.grand_total) }}</strong></div><div class="pay-due"><span>Outstanding due</span><strong>{{ fmt(invoice.outstanding_amount) }}</strong></div></div>
                <label class="pay-label" for="pay-amount">Cash received / to collect (BDT)</label>
                <div class="pay-input-row"><input id="pay-amount" class="pay-input" v-model="amount" type="number" min="0.01" step="0.01" inputmode="decimal" /><button type="button" @click="amount=String(Number(invoice.outstanding_amount).toFixed(2))">Pay full</button></div>
                <p class="pay-hint">For partial collection, enter an amount smaller than the outstanding balance.</p>
                <div class="pay-account">Payment mode: <strong>Cash</strong><span>Cash - AMCL</span></div>
                <button type="button" class="pay-primary" :disabled="!valid" @click="prepare">{{ saving ? 'Preparing…' : 'Prepare Draft Payment Entry' }}</button>
                <p v-if="!canCreate" class="pay-hint">Your account cannot create Payment Entries. Ask your accounts manager to grant the appropriate ERPNext permission.</p>
                <p class="pay-hint">This action creates a draft only. Review and submit the payment in ERPNext after receiving the money.</p>
                <button type="button" class="pay-textbutton" @click="openDesk('Sales Invoice',invoice.name)">Open Sales Invoice ↗</button>
              </template>
              <div v-else class="pay-empty pay-empty-selection"><strong>Select an invoice</strong><p>Only submitted repair invoices can receive payments. If no invoice appears, finish invoice review and submission first.</p></div>
            </section>
          </div>
        </div>
        <footer class="pay-footer"><span>BDT · ERPNext Payment Entry · Draft only</span><button type="button" @click="close" :disabled="saving">Close</button></footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.pay-launch{display:inline-flex;align-items:center;justify-content:center;gap:9px;min-height:40px;background:#fffdf9;color:#745938;border:1px solid #d9c7ad;border-radius:11px;padding:10px 14px;font-size:12px;font-weight:750;cursor:pointer}.pay-launch:hover{background:#f4eadc}
.pay-shade{position:fixed;inset:0;z-index:100500;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(37,31,24,.58);backdrop-filter:blur(3px)}
.pay-dialog{display:flex;flex-direction:column;width:min(930px,100%);max-height:92dvh;min-height:320px;border-radius:20px;background:#fffdf9;color:#44392d;border:1px solid #e6d9c6;box-shadow:0 30px 90px rgba(22,17,11,.33);overflow:hidden}
.pay-header{padding:22px 26px 18px;border-bottom:1px solid #e5d9ca;display:flex;justify-content:space-between;gap:15px;align-items:flex-start}.pay-eyebrow{font-size:10px;letter-spacing:1.3px;font-weight:800;color:#9c7a4c}.pay-header h2{font-size:23px;font-weight:800;margin:4px 0}.pay-header p{color:#8c7c68;font-size:12px}.pay-close{width:36px;height:36px;flex-shrink:0;display:grid;place-items:center;background:#f3ebdf;border:1px solid #e2d5c5;border-radius:10px;cursor:pointer}
.pay-content{padding:20px 26px;min-height:0;overflow-y:auto}.pay-columns{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px}.pay-list,.pay-form{min-width:0;border:1px solid #e8dfd3;background:#fffefa;border-radius:14px;padding:16px}.pay-section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:13px}.pay-section-head span{font-size:10px;font-weight:800;color:#9d8058;letter-spacing:1px}.pay-section-head h3{font-size:15px;font-weight:750;margin-top:4px}.pay-textbutton{border:0;background:transparent;color:#80603d;font-weight:700;font-size:12px;cursor:pointer}.pay-input{width:100%;padding:11px 12px;border:1px solid #decfbc;background:white;border-radius:10px;font-size:13px;color:#40352a;min-width:0}.pay-list-scroll{max-height:390px;overflow:auto;margin-top:12px}.pay-invoice{display:flex;flex-direction:column;gap:5px;width:100%;text-align:left;padding:11px;border-radius:10px;border:1px solid #e7ddd0;background:white;margin-bottom:8px;cursor:pointer}.pay-invoice:hover,.pay-invoice.active{border-color:#c9ae8c;background:#f6edde}.pay-invoice-line{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12px}.pay-invoice-line span{color:#846442;font-weight:800;white-space:nowrap}.pay-invoice-sub,.pay-invoice small{font-size:11px;color:#8e7e6b}.pay-details{border:1px solid #e5ddcf;border-radius:12px;background:#f9f5ee;padding:12px;margin-bottom:16px}.pay-details>div{display:flex;justify-content:space-between;gap:10px;margin-bottom:8px;font-size:12px}.pay-details>div:last-child{margin-bottom:0}.pay-details span{color:#80735f}.pay-details strong{text-align:right;overflow-wrap:anywhere}.pay-details .pay-due{border-top:1px solid #ddd1bf;padding-top:10px;color:#73512e}.pay-label{font-size:12px;font-weight:700;display:block;margin:12px 0 7px}.pay-input-row{display:flex;gap:8px}.pay-input-row button{border:1px solid #d6c5ad;border-radius:10px;padding:0 11px;white-space:nowrap;font-size:12px;font-weight:700;background:#f2e8da;color:#795734}.pay-hint{font-size:11px;line-height:1.5;color:#8e7d69;margin:8px 0}.pay-account{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;background:#f4eddf;border:1px solid #e5d7c2;border-radius:10px;padding:11px;font-size:12px;margin:15px 0}.pay-primary{border-radius:11px;background:#80613e;color:white;border:1px solid #80613e;min-height:43px;width:100%;padding:11px;font-size:12px;font-weight:800;cursor:pointer}.pay-primary:disabled{opacity:.5;cursor:not-allowed}.pay-empty{text-align:center;color:#94836e;font-size:12px;padding:30px 10px;line-height:1.6}.pay-empty-selection{background:#f9f6ef;border-radius:10px;margin-top:15px}.pay-empty-selection strong{display:block;font-size:14px}.pay-alert{padding:12px;border-radius:10px;margin-bottom:14px;font-size:12px}.pay-error{background:#fbe9e5;color:#a03a33}.pay-success{background:#e5f2e5;color:#2c713d}.pay-created{border-radius:13px;background:#f4f6ed;border:1px solid #cfdcc3;padding:18px;font-size:13px}.pay-created p{margin:9px 0;color:#58634e}.pay-created button{border:1px solid #b8cbb1;border-radius:9px;background:#fff;padding:10px 12px;font-weight:700;cursor:pointer}.pay-footer{padding:12px 26px;border-top:1px solid #e5d9ca;display:flex;align-items:center;justify-content:space-between;gap:10px}.pay-footer span{font-size:11px;color:#a08b71}.pay-footer button{border:1px solid #e0d5c4;border-radius:9px;padding:9px 14px;background:white;font-weight:700;cursor:pointer}
@media(max-width:740px){.pay-columns{grid-template-columns:1fr}.pay-header,.pay-content,.pay-footer{padding-left:16px;padding-right:16px}.pay-dialog{max-height:96dvh}.pay-shade{padding:8px}}
</style>
