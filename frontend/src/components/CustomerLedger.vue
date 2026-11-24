<script setup>
import { onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { moduleApi } from './extensionApi.js'

const props = defineProps({ customer: { type: String, required: true } })
const start = ref('')
const end = ref('')
const result = ref(null)
const loading = ref(true)
const error = ref('')
const heading = useId()
const amount = new Intl.NumberFormat('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const voucherRoutes = {
  'Sales Invoice': 'sales-invoice', 'POS Invoice': 'pos-invoice',
  'Payment Entry': 'payment-entry', 'Journal Entry': 'journal-entry',
}
const totals = { opening: 'Opening balance', debits: 'Debits', credits: 'Credits', closing: 'Closing balance' }
let request = 0
let applied = {}

function voucherLink(row) {
  const route = voucherRoutes[row.voucher_type]
  return route && row.voucher_no ? `/app/${route}/${encodeURIComponent(row.voucher_no)}` : ''
}

async function load(page = 1, filters = applied) {
  const version = ++request
  error.value = ''
  loading.value = true
  try {
    const data = await moduleApi('get_customer_ledger', { customer: props.customer, ...filters, page })
    if (version !== request) return
    result.value = data
    applied = filters
  } catch (err) {
    if (version === request) error.value = err.message
  } finally {
    if (version === request) loading.value = false
  }
}

function apply() {
  load(1, { from_date: start.value, to_date: end.value })
}

function clear() {
  start.value = end.value = ''
  apply()
}

onMounted(() => load())
onBeforeUnmount(() => { request++ })
</script>

<template>
  <section class="customer-ledger" :aria-labelledby="heading" :aria-busy="loading">
    <h4 :id="heading">Customer ledger</h4>
    <form class="ledger-filter" @submit.prevent="apply">
      <label>From<input v-model="start" type="date" :max="end || undefined"></label>
      <label>To<input v-model="end" type="date" :min="start || undefined"></label>
      <div class="ledger-filter-actions">
        <button type="submit" :disabled="loading">Apply</button>
        <button v-if="start || end || applied.from_date || applied.to_date" type="button" :disabled="loading" @click="clear">Clear</button>
      </div>
    </form>
    <p v-if="loading" class="ledger-state" role="status">Loading ledger entries…</p>
    <div v-else-if="error" class="ledger-state ledger-error" role="alert">{{ error }}
      <button type="button" @click="apply">Retry</button>
    </div>
    <template v-else-if="result">
      <dl class="ledger-totals" :aria-label="'Ledger totals in ' + result.currency">
        <div v-for="(label, key) in totals" :key="key" :class="{ 'ledger-closing': key === 'closing' }">
          <dt>{{ label }}</dt><dd>{{ result.currency }} {{ amount.format(result[key]) }}</dd>
        </div>
      </dl>
      <p v-if="!result.rows.length" class="ledger-state">No ledger entries in this period.</p>
      <div v-else class="ledger-scroll" tabindex="0" role="region" aria-label="Ledger entries">
        <table class="ledger-table">
          <thead><tr>
            <th scope="col">Voucher</th><th scope="col">Debit</th><th scope="col">Credit</th><th scope="col">Balance</th>
          </tr></thead>
          <tbody>
            <tr v-for="row in result.rows" :key="row.name">
              <th scope="row">
                <a v-if="voucherLink(row)" :href="voucherLink(row)" target="_blank" rel="noopener">{{ row.voucher_no }}</a>
                <span v-else>{{ row.voucher_no || row.name }}</span>
                <small>{{ row.posting_date }}<template v-if="row.account"> · {{ row.account }}</template></small>
              </th>
              <td>{{ row.debit ? amount.format(row.debit) : '—' }}</td>
              <td>{{ row.credit ? amount.format(row.credit) : '—' }}</td>
              <td>{{ amount.format(row.balance) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="result.page > 1 || result.has_next" class="ledger-pager">
        <button type="button" :disabled="result.page <= 1" @click="load(result.page - 1)">Previous</button>
        <span>Page {{ result.page }}</span>
        <button type="button" :disabled="!result.has_next" @click="load(result.page + 1)">Next</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.customer-ledger{min-width:0;font-size:.8rem;color:var(--os-ink,#39291f)}
.customer-ledger h4{font-size:.87rem;font-weight:750;margin:9px 0 6px}
.ledger-filter,.ledger-totals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.ledger-filter label{display:grid;gap:3px;min-width:0}
.ledger-filter input{width:100%;min-width:0;padding:4px;font-size:.74rem;min-height:30px;border:1px solid var(--os-border,#e5d6c4);border-radius:6px;background:var(--os-surface,#fffdf9);color:var(--os-ink,#39291f)}
.ledger-filter-actions,.ledger-pager{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ledger-filter-actions{grid-column:1/-1}
.customer-ledger button{min-height:29px;padding:4px 8px;border:1px solid var(--os-border,#e5d6c4);border-radius:6px;background:var(--os-surface,#fffdf9);color:var(--os-strong,#62402b);font-size:.75rem;font-weight:650}
.customer-ledger button:disabled{opacity:.5}
.customer-ledger :is(input,button,.ledger-scroll):focus-visible{outline:2px solid var(--os-accent,#855d43);outline-offset:1px}
.ledger-totals{margin:9px 0}
.ledger-totals div{min-width:0;padding:5px 7px;background:var(--os-tint,#f3ebe0);border-radius:6px}
.ledger-totals .ledger-closing{background:var(--os-selection,#e8d9c6)}
.ledger-totals dt,.ledger-table small,.ledger-state{color:var(--os-muted,#674a36);font-size:.72rem}
.ledger-totals dd{margin:2px 0 0;font-weight:750;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.ledger-scroll{overflow:auto}
.ledger-table{width:100%;min-width:300px;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:.73rem}
.ledger-table th,.ledger-table td{padding:6px 4px;border-bottom:1px solid var(--os-border,#e5d6c4)}
.ledger-table th:first-child{text-align:left;overflow-wrap:anywhere}
.ledger-table th:not(:first-child),.ledger-table td{text-align:right;white-space:nowrap}
.ledger-table thead{background:var(--os-tint,#f3ebe0)}
.ledger-table small{display:block;font-weight:400;line-height:1.2}
.ledger-table a{text-decoration:underline;text-underline-offset:2px;color:var(--os-strong,#62402b)}
.ledger-state,.ledger-pager{margin:8px 0 0}
.ledger-error{color:#8e362a}
.ledger-pager{justify-content:space-between}
</style>
