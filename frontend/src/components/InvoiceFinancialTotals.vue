<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  totals: { type: Object, required: true },
  showRegisterScope: Boolean,
})
const title = useId()
const period = computed(() => {
  const { start_date: start, end_date: end } = props.totals
  if (start && end) return start + ' to ' + end
  if (start) return 'From ' + start
  if (end) return 'Through ' + end
  return 'All posting dates'
})
const rows = [
  {key: 'purchases', label: 'Total purchases', detail: 'Submitted purchase invoices, net of returns and before tax'},
  {key: 'sales', label: 'Total sales', detail: 'Submitted sales invoices, net of returns and before tax'},
  {key: 'cogs', label: 'Cost of goods sold', detail: 'Posted cost of goods sold'},
  {key: 'profit', label: 'Net profit', detail: 'Posted Profit and Loss income less expenses'},
]
const amounts = new Intl.NumberFormat('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
</script>

<template>
  <section class="invoice-financials" :aria-labelledby="title">
    <header>
      <h3 :id="title">Company totals</h3>
      <p>{{ period }} · {{ totals.currency }} · Records visible to your role</p>
      <p v-if="showRegisterScope">Posting dates set these totals. Other filters apply to the invoice register above.</p>
    </header>
    <dl>
      <div v-for="row in rows" :key="row.key" class="invoice-total-row" :class="{ 'invoice-total-profit': row.key === 'profit' }">
        <dt><strong>{{ row.label }}</strong><small>{{ row.detail }}</small></dt>
        <dd v-if="totals[row.key] != null">{{ totals.currency }} {{ amounts.format(totals[row.key]) }}</dd>
        <dd v-else class="invoice-total-empty">Unavailable</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.invoice-financials{border:1px solid var(--os-border,#e5d6c4);border-radius:12px;overflow:hidden}
.invoice-financials header{padding:12px 16px;background:var(--os-tint,#f3ebe0)}
.invoice-financials h3{margin:0;font-size:.96rem}
.invoice-financials header p{margin:4px 0 0;font-size:.77rem;color:var(--os-muted,#6d5b4c)}
.invoice-financials dl{margin:0}
.invoice-total-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 16px;border-top:1px solid var(--os-border,#e5d6c4)}
.invoice-total-row dt{min-width:0;font-size:.86rem}
.invoice-total-row small{display:block;margin-top:3px;color:var(--os-muted,#6d5b4c);font-size:.75rem}
.invoice-total-row dd{margin:0;text-align:right;font-weight:700;font-size:.88rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.invoice-total-profit{background:var(--os-selection,#e8d9c6);color:var(--os-ink,#38291f)}
.invoice-total-profit dd{font-size:1.04rem}
.invoice-total-empty{color:var(--os-muted,#6d5b4c)}
</style>
