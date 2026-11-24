<script setup>
import { onMounted, ref } from 'vue'
import InventoryReceiptBilling from './InventoryReceiptBilling.vue'
import { servicingApi } from './extensionApi.js'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({ purchaseOrder: { type: String, default: '' } })
const emit = defineEmits(['open-order', 'clear-order'])
const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const mode = ref(props.purchaseOrder ? 'history' : 'orders')
const search = ref('')
const applied = ref('')
const page = ref(1)
const result = ref(null)
const loading = ref(false)
const error = ref('')
const selectedReceipt = ref('')
let request = 0

async function load(nextPage = 1) {
  const version = ++request
  loading.value = true
  error.value = ''
  const history = mode.value === 'history'
  const args = { search: applied.value, page: nextPage }
  if (history && props.purchaseOrder) args.purchase_order = props.purchaseOrder
  try {
    const response = await servicingApi('inventory_purchase_order',
      history ? 'list_supplier_receipts' : 'list_purchase_orders_to_receive', args)
    if (version !== request) return
    result.value = response
    page.value = nextPage
  } catch (err) {
    if (version === request) error.value = err.message
  } finally {
    if (version === request) loading.value = false
  }
}

function switchMode(next) {
  mode.value = next
  search.value = ''
  applied.value = ''
  result.value = null
  load()
}

function find() {
  applied.value = search.value.trim()
  load()
}

onMounted(() => load())
</script>

<template>
  <section class="inv-desk" :aria-label="tr('Purchase receipts', 'ক্রয় রসিদ')">
    <header class="desk-head">
      <h2>{{ tr('Purchase receipts', 'ক্রয় রসিদ') }}</h2>
      <a v-if="result?.can_create" class="desk-btn" href="/app/purchase-receipt" target="_blank" rel="noopener">{{ tr('Open ERPNext receipts', 'ইআরপিনেক্সটে রসিদ খুলুন') }}</a>
    </header>
    <nav :aria-label="tr('Receiving views', 'পণ্য গ্রহণের তালিকা')">
      <button type="button" :aria-pressed="mode === 'orders'" :aria-current="mode === 'orders' ? 'true' : undefined" @click="switchMode('orders')">{{ tr('Orders to receive', 'গ্রহণের অপেক্ষায়') }}</button>
      <button type="button" :aria-pressed="mode === 'history'" :aria-current="mode === 'history' ? 'true' : undefined" @click="switchMode('history')">{{ tr('Receipt history', 'রসিদের ইতিহাস') }}</button>
    </nav>
    <div v-if="mode === 'history' && purchaseOrder" class="receipt-order-filter">
      <p>{{ tr('Receipts for', 'এই অর্ডারের রসিদ') }} <strong>{{ purchaseOrder }}</strong></p>
      <button type="button" @click="emit('clear-order')">{{ tr('Show all receipts', 'সব রসিদ দেখুন') }}</button>
    </div>
    <form @submit.prevent="find">
      <label class="desk-search">{{ mode === 'orders' ? tr('Purchase Order or supplier', 'ক্রয়াদেশ বা সরবরাহকারী') : tr('Receipt or supplier', 'রসিদ বা সরবরাহকারী') }}<input v-model="search" type="search" maxlength="140" /></label>
      <button type="submit" :disabled="loading">{{ tr('Search', 'খুঁজুন') }}</button>
      <button type="button" :disabled="loading" @click="load(page)">{{ tr('Refresh', 'রিফ্রেশ') }}</button>
    </form>
    <p v-if="error" class="desk-alert" role="alert">{{ error }}</p>
    <p v-else-if="loading" role="status">{{ tr('Loading…', 'লোড হচ্ছে…') }}</p>
    <p v-else-if="result?.can_read === false">{{ tr('Purchase Order read permission is required.', 'ক্রয়াদেশ দেখার অনুমতি প্রয়োজন।') }}</p>
    <p v-else-if="result && !result.rows.length">{{ mode === 'orders' ? tr('No open Purchase Orders waiting to be received.', 'গ্রহণের অপেক্ষায় কোনো ক্রয়াদেশ নেই।') : tr('No purchase receipts found.', 'কোনো ক্রয় রসিদ পাওয়া যায়নি।') }}</p>
    <template v-else-if="result">
      <div v-if="mode === 'orders'" class="desk-table-wrap">
        <table>
          <thead><tr><th>{{ tr('Purchase Order', 'ক্রয়াদেশ') }}</th><th>{{ tr('Supplier', 'সরবরাহকারী') }}</th><th>{{ tr('Required by', 'প্রয়োজনের তারিখ') }}</th><th>{{ tr('Received', 'গৃহীত') }}</th><th>{{ tr('Action', 'করণীয়') }}</th></tr></thead>
          <tbody><tr v-for="row in result.rows" :key="row.name">
            <td><strong>{{ row.name }}</strong></td><td>{{ row.supplier_name || row.supplier }}</td>
            <td>{{ row.schedule_date || '—' }}</td>
            <td>{{ Number(row.per_received || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) }}%</td>
            <td><button type="button" @click="emit('open-order', row.name)">{{ tr('Review order', 'অর্ডার যাচাই করুন') }}</button></td>
          </tr></tbody>
        </table>
      </div>
      <div v-else class="desk-table-wrap">
        <table>
          <thead><tr><th>{{ tr('Receipt', 'রসিদ') }}</th><th>{{ tr('Purchase Order', 'ক্রয়াদেশ') }}</th><th>{{ tr('Supplier', 'সরবরাহকারী') }}</th><th>{{ tr('Warehouse', 'গুদাম') }}</th><th>{{ tr('Posting date', 'তারিখ') }}</th><th>{{ tr('Status', 'অবস্থা') }}</th><th>{{ tr('Action', 'করণীয়') }}</th></tr></thead>
          <tbody><tr v-for="row in result.rows" :key="row.name">
            <td><a :href="'/app/purchase-receipt/' + encodeURIComponent(row.name)" target="_blank" rel="noopener">{{ row.name }}</a></td>
            <td><button v-for="order in row.purchase_orders" :key="order" class="receipt-order-link" type="button" @click="emit('open-order', order)">{{ order }}</button><span v-if="!row.purchase_orders?.length">—</span></td>
            <td>{{ row.supplier_name || row.supplier }}</td><td>{{ row.set_warehouse || '—' }}</td>
            <td>{{ row.posting_date }}</td><td>{{ row.status }}<small v-if="row.is_return">{{ tr('Return', 'ফেরত') }}</small></td>
            <td><button type="button" @click="selectedReceipt = row.name">{{ tr('Invoice & payment', 'চালান ও পেমেন্ট') }}</button></td>
          </tr></tbody>
        </table>
      </div>
      <footer v-if="page > 1 || result.has_next" class="desk-pager">
        <button type="button" :disabled="page === 1" @click="load(page - 1)">{{ tr('Previous', 'আগের') }}</button>
        <span>{{ page }}</span>
        <button type="button" :disabled="!result.has_next" @click="load(page + 1)">{{ tr('Next', 'পরের') }}</button>
      </footer>
    </template>
    <InventoryReceiptBilling v-if="selectedReceipt" :receipt-name="selectedReceipt" @close="selectedReceipt = ''; load(page)" />
  </section>
</template>

<style scoped src="./inventoryDesk.css"></style>
<style scoped>
.receipt-order-filter{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.inv-desk td .receipt-order-link{display:block;text-align:left;border:0;padding:0;min-height:28px;text-decoration:underline;white-space:normal}
</style>
