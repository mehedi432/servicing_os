<script setup>
import { computed, useId } from 'vue'

const props = defineProps({ summary: { type: Object, required: true }, currency: String })
defineEmits(['history'])
const heading = useId()
const format = new Intl.NumberFormat('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const percentage = new Intl.NumberFormat('en-BD', { maximumFractionDigits: 1 })
const metrics = computed(() => [
  { label: 'Open orders', value: props.summary.open,
    detail: props.summary.on_hold ? props.summary.on_hold + ' on hold' : '' },
  { label: 'Awaiting receipt', value: props.summary.receiving,
    detail: props.summary.overdue ? props.summary.overdue + ' overdue' : '' },
  { label: 'Awaiting billing', value: props.summary.billing },
  { label: 'Submitted order value', value: money(props.summary.ordered_value, props.currency),
    detail: props.summary.submitted + ' submitted' },
])

function money(value, currency) {
  return value == null ? '—' : [currency, format.format(value)].filter(Boolean).join(' ')
}
function progress(value) {
  return value == null ? '—' : percentage.format(value) + '%'
}
</script>

<template>
  <section class="supplier-orders" :aria-labelledby="heading">
    <header class="supplier-orders-header">
      <h3 :id="heading">Purchase orders</h3>
      <button type="button" @click="$emit('history')">View all purchase orders <span aria-hidden="true">↓</span></button>
    </header>
    <dl class="supplier-orders-metrics">
      <div v-for="metric in metrics" :key="metric.label">
        <dt>{{ metric.label }}</dt><dd>{{ metric.value }}</dd>
        <small v-if="metric.detail">{{ metric.detail }}</small>
      </div>
    </dl>
    <div v-if="summary.orders.length" class="supplier-orders-list">
      <h4>{{ summary.open > summary.orders.length ? 'Next ' + summary.orders.length + ' open orders' : 'Open orders by required date' }}</h4>
      <ul>
        <li v-for="order in summary.orders" :key="order.name">
          <div>
            <a :href="'/app/purchase-order/' + encodeURIComponent(order.name)" target="_blank" rel="noopener">{{ order.name }}</a>
            <small>Required {{ order.schedule_date || '—' }}<strong v-if="order.receipt_overdue" class="supplier-order-late">Overdue</strong></small>
          </div>
          <div><span>{{ order.status }}</span><small>Received {{ progress(order.per_received) }} · Billed {{ progress(order.per_billed) }}</small></div>
          <strong class="supplier-order-amount">{{ money(order.grand_total, order.currency || currency) }}</strong>
        </li>
      </ul>
    </div>
    <p v-else class="supplier-orders-empty">No open purchase orders for this supplier.</p>
  </section>
</template>

<style scoped>
.supplier-orders{margin-top:18px;border:1px solid var(--os-border,#e5d5c4);border-radius:12px;background:var(--os-surface,#fffefa);min-width:0;overflow:hidden}
.supplier-orders-header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;padding:11px 13px;background:var(--os-tint,#f3ebe0)}
.supplier-orders-header h3,.supplier-orders-list h4{margin:0;font-size:.95rem;font-weight:770}
.supplier-orders-header button{padding:6px 9px;min-height:36px;border:1px solid var(--os-border,#e5d5c4);border-radius:8px;background:var(--os-surface,#fffefa);color:var(--os-strong,#644229);font-size:.76rem;font-weight:730}
.supplier-orders :is(a,button):focus-visible{outline:2px solid var(--os-accent,#785238);outline-offset:2px}
.supplier-orders-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin:10px 12px}
.supplier-orders-metrics>div{min-width:0;padding:8px 9px;border:1px solid var(--os-border,#e5d5c4);border-radius:8px}
.supplier-orders-metrics dt,.supplier-orders small,.supplier-orders-empty{color:var(--os-muted,#6d5b4c);font-size:.73rem}
.supplier-orders-metrics dd{margin:3px 0;font-weight:770;font-size:.94rem;overflow-wrap:anywhere}
.supplier-orders-list h4{margin:12px 12px 4px;font-size:.77rem;color:var(--os-muted,#6d5b4c)}
.supplier-orders-list ul{list-style:none;margin:0;padding:0}
.supplier-orders-list li{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr) auto;gap:8px;padding:9px 12px;border-top:1px solid var(--os-border,#e5d5c4);font-size:.8rem;overflow-wrap:anywhere}
.supplier-orders-list a{color:var(--os-strong,#644229);text-decoration:underline;text-underline-offset:2px;font-weight:730}
.supplier-orders-list small{display:block;margin-top:3px}
.supplier-order-late{margin-inline-start:6px;color:#913924}
.supplier-order-amount{text-align:right;font-variant-numeric:tabular-nums}
.supplier-orders-empty{margin:0;padding:2px 12px 12px}
@container(max-width:560px){.supplier-orders-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.supplier-orders-list li{grid-template-columns:repeat(2,minmax(0,1fr))}.supplier-order-amount{text-align:start}}
</style>
