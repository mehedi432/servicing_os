<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import CustomerLedger from './CustomerLedger.vue'
import SupplierPurchaseOrderCard from './SupplierPurchaseOrderCard.vue'
import { moduleApi } from './extensionApi.js'

const props = defineProps({
  type: { type: String, required: true },
  record: { type: Object, required: true },
  canEdit: Boolean,
})
defineEmits(['edit'])
const profile = ref(null)
const overviewError = ref('')
const section = ref('')
const history = ref(null)
const loading = ref(false)
const historyError = ref('')
const historyHeading = useId()
const historyPanel = ref(null)
const profileHeading = useId()
let request = 0
let overviewRequest = 0

const isCustomer = computed(() => props.type === 'Customer')
const title = computed(() => props.record.display_name || props.record.name)
const addressLines = computed(() => {
  const address = profile.value?.address
  if (!address) return []
  return [address.address_line1, address.address_line2,
    [address.city, address.state, address.pincode].filter(Boolean).join(', '),
    address.country].filter(Boolean)
})
const initials = computed(() => title.value.trim().split(/\s+/).slice(0, 2)
  .map(word => Array.from(word)[0]).join('').toLocaleUpperCase())
const labels = computed(() => ({
  invoices: isCustomer.value ? 'Sales invoices' : 'Purchase invoices',
  open_invoices: 'Open invoices',
  orders: isCustomer.value ? 'Sales orders' : 'Purchase orders',
  payments: 'Payments',
  repairs: 'Service jobs',
  ledger: 'Ledger',
}))
const routes = computed(() => ({
  invoices: isCustomer.value ? 'sales-invoice' : 'purchase-invoice',
  open_invoices: 'sales-invoice',
  orders: isCustomer.value ? 'sales-order' : 'purchase-order',
  payments: 'payment-entry',
  repairs: 'service-job',
}))
const invoiceSection = computed(() => ['invoices', 'open_invoices'].includes(section.value))
const args = () => ({ party_type: props.type, party: props.record.name })
const formatter = new Intl.NumberFormat('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
function money(amount, currency = profile.value?.currency) {
  if (amount == null) return '—'
  return [currency, formatter.format(amount)].filter(Boolean).join(' ')
}
function recorded(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : ''
}
function paymentDirection(row) {
  return row.payment_type === 'Receive' ? 'Received' : 'Paid'
}

async function loadOverview() {
  const version = ++overviewRequest
  overviewError.value = ''
  try {
    const data = await moduleApi('get_party_profile', args())
    if (version !== overviewRequest) return
    profile.value = data
    const first = profile.value.sections[0]
    if (first) await loadHistory(first)
  } catch (error) {
    if (version === overviewRequest) overviewError.value = error.message
  }
}

async function loadHistory(tab = section.value, page = 1) {
  const version = ++request
  if (tab !== section.value) history.value = null
  section.value = tab
  historyError.value = ''
  loading.value = tab !== 'ledger'
  if (tab === 'ledger') return
  try {
    const result = await moduleApi('get_party_history', { ...args(), section: tab, page })
    if (version === request) history.value = result
  } catch (error) {
    if (version === request) historyError.value = error.message
  } finally {
    if (version === request) loading.value = false
  }
}
function showOrders() {
  loadHistory('orders')
  historyPanel.value?.scrollIntoView({block:'start'})
  historyPanel.value?.focus({preventScroll:true})
}
onMounted(loadOverview)
onBeforeUnmount(() => {
  request++
  overviewRequest++
})
</script>

<template>
  <section class="party-inline" :class="{ 'customer-profile': isCustomer }" :aria-labelledby="profileHeading">
    <header class="party-inline-heading">
      <span class="profile-avatar" aria-hidden="true">{{ initials }}</span>
      <div class="profile-identity">
        <small>{{ type }} 360</small>
        <h2 :id="profileHeading">{{ title }}</h2>
        <div class="profile-identifiers">
          <span v-if="record.name !== title">{{ record.name }}</span>
          <span v-if="record.group">{{ record.group }}</span>
        </div>
      </div>
      <button v-if="canEdit" type="button" class="profile-button profile-edit" @click="$emit('edit')">Edit supplier</button>
    </header>
    <div class="profile-details">
      <section class="profile-detail">
        <h3>Contact details</h3>
        <a v-if="record.mobile" :href="'tel:' + record.mobile" class="profile-detail-link">{{ record.mobile }}</a>
        <a v-if="record.email" :href="'mailto:' + record.email" class="profile-detail-link">{{ record.email }}</a>
        <p v-if="!record.mobile && !record.email">No contact details on file</p>
      </section>
      <section class="profile-detail profile-address">
        <h3>Billing address</h3>
        <address v-if="addressLines.length">
          <span v-for="(line, index) in addressLines" :key="index">{{ line }}</span>
        </address>
        <p v-else-if="profile">{{ profile.address_visible === false ? 'Address access restricted' : 'No address on file' }}</p>
        <p v-else-if="!overviewError">Loading address…</p>
        <p v-else>Address unavailable</p>
      </section>
    </div>
    <div v-if="overviewError" class="profile-state" role="alert">{{ overviewError }}
      <button type="button" class="profile-button" @click="loadOverview">Retry</button>
    </div>
    <p v-else-if="!profile" class="profile-state" role="status">Loading account history…</p>
    <template v-else>
      <div class="profile-summary-heading">
        <h3>Account summary</h3><p class="profile-company">{{ profile.company }} · Submitted transactions</p>
      </div>
      <dl class="profile-metrics">
        <div>
          <dt>{{ isCustomer ? 'Net sales income' : 'Net purchases' }}</dt>
          <dd>{{ money(profile.invoices?.net) }}</dd>
          <small v-if="profile.invoices">Before tax, after returns</small>
          <small v-else>Invoice access required</small>
        </div>
        <div>
          <dt>Total invoiced</dt>
          <dd>{{ money(profile.invoices?.billed) }}</dd>
          <small v-if="profile.invoices">{{ profile.invoices.count }} submitted</small>
        </div>
        <div class="profile-dues">
          <dt>{{ isCustomer ? 'Total due' : 'Total payable' }}</dt>
          <template v-if="profile.invoices && Object.keys(profile.invoices.due).length">
            <dd v-for="(amount, currency) in profile.invoices.due" :key="currency">{{ money(amount, currency) }}</dd>
          </template>
          <dd v-else>—</dd>
          <small>Open invoice balance</small>
        </div>
        <div>
          <dt>{{ isCustomer ? 'Net payments received' : 'Net payments sent' }}</dt>
          <dd>{{ money(profile.payments?.net) }}</dd>
          <small v-if="!profile.payments">Payment Entry access required</small>
        </div>
        <div><dt>Payments recorded</dt><dd>{{ profile.payments?.count ?? '—' }}</dd></div>
        <div>
          <dt>Latest payment</dt>
          <dd>{{ profile.payments?.latest?.posting_date || '—' }}</dd>
          <small v-if="profile.payments?.latest?.creation">Recorded {{ recorded(profile.payments.latest.creation) }}</small>
        </div>
      </dl>
      <SupplierPurchaseOrderCard v-if="profile.purchase_orders" :summary="profile.purchase_orders"
        :currency="profile.currency" @history="showOrders" />
      <section v-if="profile.sections.length" ref="historyPanel" class="profile-history" tabindex="-1" :aria-labelledby="historyHeading">
        <h3 :id="historyHeading">Transaction history</h3>
        <div class="profile-history-nav" role="group" aria-label="History views">
          <button v-for="tab in profile.sections" :key="tab" type="button" class="profile-button"
            :aria-pressed="section === tab" @click="loadHistory(tab)">{{ labels[tab] }}</button>
        </div>
        <KeepAlive><CustomerLedger v-if="section === 'ledger'" :customer="record.name" /></KeepAlive>
        <div v-if="section !== 'ledger'" :aria-busy="loading">
          <p v-if="loading" class="profile-state" role="status">Loading {{ labels[section]?.toLowerCase() }}…</p>
          <div v-else-if="historyError" class="profile-state" role="alert">{{ historyError }}
            <button type="button" class="profile-button" @click="loadHistory(section, history?.page || 1)">Retry</button>
          </div>
          <p v-else-if="!history?.rows.length" class="profile-state">No {{ labels[section]?.toLowerCase() }} found.</p>
          <ul v-else class="profile-records" :aria-label="labels[section]">
            <li v-for="row in history.rows" :key="row.name" class="profile-record">
              <div>
                <a :href="`/app/${routes[section]}/${encodeURIComponent(row.name)}`" target="_blank" rel="noopener">{{ row.name }}</a>
                <small v-if="row.bill_no">Supplier ref {{ row.bill_no }}</small>
                <small v-if="row.reference_no">Ref {{ row.reference_no }}</small>
              </div>
              <div>
                <span>{{ row.posting_date || row.transaction_date || row.received_date || '—' }}</span>
                <small v-if="section === 'payments' && row.creation">Recorded {{ recorded(row.creation) }}</small>
                <small v-if="invoiceSection && row.due_date">Due {{ row.due_date }}</small>
                <small v-if="!isCustomer && section === 'orders' && row.schedule_date">Required {{ row.schedule_date }}</small>
              </div>
              <div v-if="section === 'payments'"><span>{{ paymentDirection(row) }}</span><small v-if="row.mode_of_payment">{{ row.mode_of_payment }}</small></div>
              <div v-else>
                <span>{{ row.status || (row.docstatus === 0 ? 'Draft' : '—') }}</span>
                <small v-if="section === 'repairs'">{{ [row.brand, row.device_model || row.device_type].filter(Boolean).join(' ') }}</small>
                <small v-if="row.is_return">Return</small>
              </div>
              <div v-if="section !== 'repairs'" class="profile-amount">
                <strong>{{ money(row.amount ?? row.grand_total, row.currency) }}</strong>
                <small v-if="invoiceSection && row.docstatus === 1">Open {{ money(row.outstanding_amount, row.due_currency) }}</small>
              </div>
            </li>
          </ul>
          <div v-if="history && (history.page > 1 || history.has_next)" class="profile-pager">
            <button type="button" class="profile-button" :disabled="loading || history.page <= 1"
              @click="loadHistory(section, history.page - 1)">Previous</button>
            <span>Page {{ history.page }}</span>
            <button type="button" class="profile-button" :disabled="loading || !history.has_next"
              @click="loadHistory(section, history.page + 1)">Next</button>
          </div>
        </div>
      </section>
      <p v-else class="profile-state">Transaction history is restricted for this account.</p>
    </template>
  </section>
</template>

<style scoped>
.party-inline{--profile-rule:var(--os-border,#e5d5c4);--profile-muted:var(--os-muted,#6d5b4c);padding:clamp(12px,2vw,22px);border:1px solid var(--profile-rule);border-radius:16px;background:var(--os-surface,#fffefa);color:var(--os-ink,#38291f);container-type:inline-size;min-width:0}
.party-inline-heading{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:12px;padding:clamp(13px,2.8vw,24px);border:1px solid var(--profile-rule);border-radius:12px;background:linear-gradient(115deg,var(--os-tint,#f3ebe0),var(--os-surface,#fffefa))}
.profile-avatar{width:50px;height:50px;display:grid;place-items:center;border-radius:11px;background:var(--os-selection,#e8d9c6);color:var(--os-strong,#644229);font-weight:800}
.profile-identity{min-width:0}
.profile-identity small{color:var(--profile-muted);font-size:.76rem;font-weight:700}
.profile-identity h2{margin:3px 0;font:clamp(1.35rem,3vw,2rem)/1.15 Georgia,serif;overflow-wrap:anywhere}
.profile-identifiers{display:flex;gap:4px 12px;flex-wrap:wrap;font-size:.76rem;color:var(--profile-muted);overflow-wrap:anywhere}
.profile-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0 18px}
.profile-detail{padding:11px 13px;border:1px solid var(--profile-rule);border-radius:10px;min-width:0}
.profile-detail h3,.profile-summary-heading h3,.profile-history h3{font-size:.93rem;font-weight:770;margin:0}
.profile-detail :is(p,address,a){margin:5px 0 0;font-size:.8rem;line-height:1.5;overflow-wrap:anywhere}
.profile-detail address{font-style:normal}
.profile-detail address span,.profile-detail-link{display:block}
.profile-detail-link{color:var(--os-strong,#644229);text-underline-offset:3px}
.profile-detail p,.profile-company,.profile-pager,.profile-state{color:var(--profile-muted)}
.profile-summary-heading{display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:4px 12px;margin-bottom:8px}
.profile-company{margin:0;font-size:.77rem}
.profile-metrics{margin:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.profile-metrics div{min-width:0;padding:11px 12px;border:1px solid var(--profile-rule);border-radius:10px;background:var(--os-tint,#f3ebe0)}
.profile-metrics .profile-dues{background:var(--os-selection,#e8d9c6)}
.profile-metrics dt,.profile-metrics small,.profile-record small{display:block;color:var(--profile-muted);font-size:.74rem;overflow-wrap:anywhere}
.profile-metrics dd{margin:4px 0;font-weight:760;font-size:1rem;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.profile-history{margin-top:20px;scroll-margin-top:1rem}
.profile-history:focus-visible{outline:2px solid var(--os-accent,#785238);outline-offset:4px}
.profile-history-nav,.profile-pager{display:flex;flex-wrap:wrap;align-items:center;gap:5px}
.profile-history-nav{padding:8px 0;border-bottom:1px solid var(--profile-rule)}
.profile-pager{justify-content:space-between;margin-top:10px;font-size:.8rem}
.profile-button{padding:6px 10px;min-height:36px;border:1px solid var(--profile-rule);border-radius:8px;background:var(--os-surface,#fffefa);color:var(--os-ink,#38291f);font-size:.79rem;font-weight:680}
.profile-button:hover:not(:disabled){border-color:var(--os-accent,#785238)}
.profile-button[aria-pressed=true]{background:var(--os-accent,#785238);color:#fff;border-color:transparent}
.profile-button:focus-visible,.profile-detail a:focus-visible,.profile-record a:focus-visible{outline:2px solid var(--os-accent,#785238);outline-offset:2px}
.profile-button:disabled{opacity:.5}
.profile-state{margin:0;padding:14px 0;font-size:.84rem}
.profile-state[role=alert]{color:#8e362a}
.profile-records{margin:0;padding:0;list-style:none}
.profile-record{display:grid;grid-template-columns:minmax(0,1.3fr) repeat(3,minmax(0,1fr));gap:6px 12px;padding:10px 2px;border-bottom:1px solid var(--profile-rule);font-size:.83rem;overflow-wrap:anywhere}
.profile-record a{color:var(--os-strong,#644229);font-weight:750;text-decoration:underline;text-underline-offset:3px}
.profile-record small{margin-top:2px}
.profile-amount{text-align:right;font-variant-numeric:tabular-nums}
.customer-profile .party-inline-heading{background:linear-gradient(115deg,var(--os-selection,#e8d9c6),var(--os-tint,#f3ebe0) 65%,var(--os-surface,#fffefa))}
.customer-profile .profile-avatar{background:var(--os-accent,#785238);color:#fff}
.customer-profile .profile-detail h3{color:var(--os-strong,#644229)}
.customer-profile .profile-dues{border-color:var(--os-accent,#785238)}
@container(max-width:610px){.profile-metrics,.profile-record{grid-template-columns:repeat(2,minmax(0,1fr))}.profile-amount{text-align:left}}
@container(max-width:350px){.profile-details{grid-template-columns:1fr}.profile-edit{grid-column:2;justify-self:start}.party-inline-heading{grid-template-columns:auto minmax(0,1fr)}}
</style>
