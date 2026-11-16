<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

// Inventory view uses posted ERPNext balances; no local/demo stock or artificial quantities.
const bn = computed(() => currentLanguage.value === 'bn')
const dictionary = {
  inventory: ['Inventory', 'ইনভেন্টরি'], subtitle: ['Products, spare parts and real-time stock balances', 'পণ্য, যন্ত্রাংশ ও স্টকের হালনাগাদ হিসাব'],
  live: ['ERPNext stock ledger', 'ইআরপিনেক্সট স্টক লেজার'], refresh: ['Refresh', 'রিফ্রেশ'], export: ['Export CSV', 'সিএসভি রপ্তানি'],
  stockIn: ['Receive Stock', 'স্টক গ্রহণ'], stockOut: ['Issue Stock', 'স্টক ইস্যু'],
  products: ['Active products', 'সক্রিয় পণ্য'], totalUnits: ['Units in stock', 'মোট স্টক'], lowStock: ['Low stock', 'স্বল্প স্টক'], value: ['Stock value', 'স্টকের মূল্য'],
  catalog: ['Product inventory', 'পণ্য ইনভেন্টরি'], countNote: ['Live quantities by warehouse', 'গুদামভিত্তিক বর্তমান পরিমাণ'],
  search: ['Search name or item code...', 'পণ্যের নাম বা কোড খুঁজুন...'], allWarehouses: ['All warehouses', 'সব গুদাম'],
  allGroups: ['All categories', 'সব ক্যাটাগরি'], allStatus: ['All stock', 'সব স্টক'], inStock: ['In stock', 'স্টক আছে'],
  low: ['Low stock', 'কম স্টক'], out: ['Out of stock', 'স্টক শেষ'], stock: ['Stock', 'স্টক'],
  item: ['Product / Item', 'পণ্য'], sku: ['Item code', 'আইটেম কোড'], group: ['Category', 'ক্যাটাগরি'],
  qty: ['Available', 'মজুত'], warranty: ['Warranty', 'ওয়ারেন্টি'], amount: ['Value', 'মূল্য'], status: ['Status', 'অবস্থা'],
  days: ['days', 'দিন'], none: ['Not set', 'সেট করা নেই'],
  empty: ['No products match your filters.', 'আপনার ফিল্টারে কোনো পণ্য পাওয়া যায়নি।'],
  loading: ['Loading stock balances...', 'স্টকের হিসাব লোড হচ্ছে...'],
  failed: ['Unable to load inventory', 'ইনভেন্টরি লোড করা যায়নি'],
  retry: ['Try again', 'আবার চেষ্টা করুন'],
  threshold: ['Low-stock alert at', 'কম স্টক সতর্কতা'],
  limited: ['Only the first 2,500 accessible items are shown. Narrow the inventory scope for larger catalogs.', 'প্রথম ২,৫০০টি আইটেম দেখানো হচ্ছে।'],
  movement: ['Stock movement', 'স্টক লেনদেন'], chooseItem: ['Select a product', 'পণ্য নির্বাচন করুন'], chooseWarehouse: ['Select a warehouse', 'গুদাম নির্বাচন করুন'],
  quantity: ['Quantity', 'পরিমাণ'], unitRate: ['Unit valuation rate', 'একক মূল্য'],
  remarks: ['Remarks (optional)', 'মন্তব্য (ঐচ্ছিক)'], submit: ['Submit stock entry', 'স্টক এন্ট্রি সাবমিট'],
  cancel: ['Cancel', 'বাতিল'], close: ['Close', 'বন্ধ'], processing: ['Submitting...', 'সাবমিট হচ্ছে...'],
  submitted: ['Stock Entry submitted:', 'স্টক এন্ট্রি সাবমিট হয়েছে:'],
  serialNote: ['Serial/batch-controlled products must use the dedicated serial/batch workflow.', 'সিরিয়াল/ব্যাচ পণ্যের জন্য আলাদা স্টক প্রক্রিয়া ব্যবহার করুন।'],
  receiptNote: ['A receipt updates stock valuation, not supplier payables.', 'স্টক গ্রহণে মজুত পরিবর্তন হয়, সরবরাহকারীর বকেয়া নয়।'],
  refreshed: ['Last refreshed', 'সর্বশেষ আপডেট'],
  permission: ['Posting requires ERPNext Stock Entry create and submit permissions.', 'সাবমিটের জন্য স্টক এন্ট্রি অনুমতি প্রয়োজন।'],
  availableAt: ['Available in selected warehouse', 'নির্বাচিত গুদামে মজুত'],
}
const t = (key) => dictionary[key]?.[bn.value ? 1 : 0] ?? key

const loading = ref(false)
const error = ref('')
const success = ref('')
const inventory = ref({ company: '', currency: 'BDT', items: [], warehouses: [], truncated: false })
const warehouse = ref('')
const group = ref('')
const stockFilter = ref('all')
const search = ref('')
const threshold = ref(5)
const lastRefreshed = ref(null)
let poller
let requestSeq = 0

function apiError(result, fallback) {
  try {
    const messages = JSON.parse(result?._server_messages || '[]')
    if (messages.length) {
      const msg = JSON.parse(messages[0])
      if (msg.message) return String(msg.message).replace(/<[^>]*>/g, '')
    }
  } catch (_) { /* return fallback */ }
  return result?.message && typeof result.message === 'string' ? result.message : fallback
}

async function api(method, params={}, post=false) {
  const url = new URL('/api/method/servicing_os.api.inventory_workspace.' + method, window.location.origin)
  const options = { credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (post) {
    options.method = 'POST'
    options.headers['Content-Type'] = 'application/json'
    const csrf = window.csrf_token || window.frappe?.csrf_token
    if (csrf) options.headers['X-Frappe-CSRF-Token'] = csrf
    options.body = JSON.stringify(params)
  } else {
    options.method = 'GET'
    options.cache = 'no-store'
    if (params.warehouse) url.searchParams.set('warehouse', params.warehouse)
  }
  const response = await fetch(url, options)
  let payload
  try { payload = await response.json() } catch { throw new Error('ERPNext returned an invalid response') }
  if (!response.ok || payload.exc || payload.exception) throw new Error(apiError(payload, 'ERPNext request failed (' + response.status + ')'))
  return payload.message
}

async function reload() {
  if (loading.value) return
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  try {
    const data = await api('get_inventory', { warehouse: warehouse.value })
    if (seq !== requestSeq) return
    inventory.value = { company: data.company || '', currency: data.currency || 'BDT', items: data.items || [], warehouses: data.warehouses || [], truncated: !!data.truncated }
    lastRefreshed.value = new Date()
  } catch (e) {
    if (seq === requestSeq) error.value = e?.message || String(e)
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}
watch(warehouse, () => { group.value = ''; reload() })
onMounted(() => {
  reload()
  poller = window.setInterval(() => { if (!document.hidden && !modalOpen.value) reload() }, 45000)
  window.addEventListener('focus', onFocus)
})
onUnmounted(() => { window.clearInterval(poller); window.removeEventListener('focus', onFocus) })
function onFocus() { if (!modalOpen.value) reload() }

const items = computed(() => inventory.value.items || [])
const groups = computed(() => [...new Set(items.value.map(i => i.item_group).filter(Boolean))].sort())
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return items.value.filter(i => {
    const qty = Number(i.actual_qty || 0)
    if (q && ![i.item_name, i.item_code, i.item_group].some(s => String(s || '').toLowerCase().includes(q))) return false
    if (group.value && i.item_group !== group.value) return false
    if (stockFilter.value === 'in' && qty <= 0) return false
    if (stockFilter.value === 'low' && !(qty > 0 && qty <= threshold.value)) return false
    if (stockFilter.value === 'out' && qty > 0) return false
    return true
  })
})
const totals = computed(() => ({
  items: items.value.length,
  units: items.value.reduce((s, i) => s + Number(i.actual_qty || 0), 0),
  low: items.value.filter(i => Number(i.actual_qty) > 0 && Number(i.actual_qty) <= threshold.value).length,
  value: items.value.reduce((s, i) => s + Number(i.stock_value || 0), 0),
}))
function stockStatus(i) {
  const q = Number(i.actual_qty || 0)
  return q <= 0 ? 'out' : q <= threshold.value ? 'low' : 'in'
}
function number(value) { return Number(value || 0).toLocaleString(bn.value ? 'bn-BD' : 'en-BD', { maximumFractionDigits: 2 }) }
function money(value) { return `${inventory.value.currency || 'BDT'} ${number(value)}` }
function csvCell(value) {
  let v = String(value ?? '')
  if (/^[\s]*[=+@\-]/.test(v)) v = "'" + v
  return '"' + v.replace(/"/g, '""') + '"'
}
function exportCsv() {
  const head = ['Item Code', 'Product', 'Category', 'Warehouse', 'Actual Qty', 'Reserved Qty', 'UOM', 'Warranty Days', 'Stock Value']
  const rows = filtered.value.map(i => [i.item_code, i.item_name, i.item_group, warehouse.value || 'All warehouses', i.actual_qty, i.reserved_qty, i.stock_uom, i.warranty_days, i.stock_value])
  const csv = '\ufeff' + [head, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], {type:'text/csv;charset=utf-8'}))
  const a = document.createElement('a'); a.href = url; a.download = 'servicing-os-inventory.csv'; a.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const modalOpen = ref(false)
const submitting = ref(false)
const formError = ref('')
const movement = ref('receive')
const form = ref({ item_code: '', warehouse: '', qty: 1, basic_rate: '', remarks: '' })
const selected = computed(() => items.value.find(i => i.item_code === form.value.item_code))
const availableHere = computed(() => {
  if (!selected.value || !form.value.warehouse) return null
  if (warehouse.value && warehouse.value !== form.value.warehouse) return null
  const b = (selected.value.by_warehouse || []).find(w => w.warehouse === form.value.warehouse)
  return Number(b?.qty || 0)
})
function openMovement(type, item='') {
  movement.value = type
  form.value = { item_code: item, warehouse: warehouse.value || (inventory.value.warehouses?.[0]?.name || ''), qty: 1, basic_rate: '', remarks: '' }
  formError.value = ''
  success.value = ''
  modalOpen.value = true
}
async function submitMovement() {
  formError.value = ''
  if (!form.value.item_code || !form.value.warehouse || !(Number(form.value.qty) > 0)) {
    formError.value = bn.value ? 'পণ্য, গুদাম ও সঠিক পরিমাণ দিন।' : 'Choose an item, warehouse and positive quantity.'; return
  }
  if (selected.value?.has_serial_no || selected.value?.has_batch_no) { formError.value = t('serialNote'); return }
  if (movement.value === 'receive' && !(Number(form.value.basic_rate) > 0)) { formError.value = bn.value ? 'প্রাপ্তির একক মূল্য দিন।' : 'Enter the receipt unit valuation rate.'; return }
  submitting.value = true
  try {
    const data = await api('post_stock_movement', { ...form.value, movement: movement.value }, true)
    modalOpen.value = false
    success.value = `${t('submitted')} ${data.stock_entry}`
    await reload()
  } catch (e) { formError.value = e?.message || String(e) }
  finally { submitting.value = false }
}
</script>

<template>
  <section class="inv-root sos-inventory-view-root" :lang="bn ? 'bn' : 'en'">
    <header class="inv-head">
      <div>
        <div class="inv-eyebrow"><span class="inv-live-dot"></span>{{ t('live') }}</div>
        <h1>{{ t('inventory') }}</h1>
        <p>{{ t('subtitle') }}</p>
      </div>
      <div class="inv-actions">
        <button type="button" class="inv-btn inv-outline" :disabled="loading" @click="reload">↻ <span>{{ t('refresh') }}</span></button>
        <button type="button" class="inv-btn inv-outline" :disabled="!items.length" @click="exportCsv">⇩ <span>{{ t('export') }}</span></button>
        <button type="button" class="inv-btn inv-primary" :disabled="!items.length" @click="openMovement('receive')">＋ <span>{{ t('stockIn') }}</span></button>
      </div>
    </header>

    <p v-if="error" class="inv-alert inv-error" role="alert"><strong>{{ t('failed') }}:</strong> {{ error }} <button type="button" @click="reload">{{ t('retry') }}</button></p>
    <p v-if="success" class="inv-alert inv-success" role="status">{{ success }}</p>
    <p v-if="inventory.truncated" class="inv-alert">{{ t('limited') }}</p>

    <div class="inv-metrics">
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">▦</span><span class="inv-stat-tag">ITEMS</span></div><div class="inv-stat-number">{{ number(totals.items) }}</div><span>{{ t('products') }}</span></div>
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">▥</span><span class="inv-stat-tag">QUANTITY</span></div><div class="inv-stat-number">{{ number(totals.units) }}</div><span>{{ t('totalUnits') }}</span></div>
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">!</span><span class="inv-stat-tag">ALERTS</span></div><div class="inv-stat-number">{{ number(totals.low) }}</div><span>{{ t('lowStock') }}</span></div>
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">৳</span><span class="inv-stat-tag">VALUATION</span></div><div class="inv-stat-number inv-amount">{{ money(totals.value) }}</div><span>{{ t('value') }}</span></div>
    </div>

    <div class="inv-panel">
      <div class="inv-panel-head">
        <div><h2>{{ t('catalog') }}</h2><p>{{ t('countNote') }}<span v-if="lastRefreshed"> · {{ t('refreshed') }} {{ lastRefreshed.toLocaleTimeString(bn ? 'bn-BD':'en-BD', {hour:'2-digit',minute:'2-digit'}) }}</span></p></div>
        <button type="button" class="inv-btn inv-small" :disabled="!items.length" @click="openMovement('issue')">− {{ t('stockOut') }}</button>
      </div>
      <div class="inv-toolbar">
        <label class="inv-search"><span aria-hidden="true">⌕</span><input v-model="search" type="search" :placeholder="t('search')" :aria-label="t('search')" /></label>
        <select v-model="warehouse" :aria-label="t('allWarehouses')"><option value="">{{ t('allWarehouses') }}</option><option v-for="w in inventory.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select>
        <select v-model="group" :aria-label="t('allGroups')"><option value="">{{ t('allGroups') }}</option><option v-for="g in groups" :key="g" :value="g">{{ g }}</option></select>
        <select v-model="stockFilter" :aria-label="t('allStatus')"><option value="all">{{ t('allStatus') }}</option><option value="in">{{ t('inStock') }}</option><option value="low">{{ t('low') }}</option><option value="out">{{ t('out') }}</option></select>
      </div>
      <div class="inv-summary"><span>{{ number(filtered.length) }} / {{ number(items.length) }} {{ t('products').toLowerCase() }}</span><label>{{ t('threshold') }} <input v-model.number="threshold" type="number" min="1" max="100000" step="1" /></label></div>
      <div class="inv-table-wrap">
        <table class="inv-table"><thead><tr><th>{{ t('item') }}</th><th>{{ t('sku') }}</th><th>{{ t('group') }}</th><th class="inv-right">{{ t('qty') }}</th><th>{{ t('warranty') }}</th><th class="inv-right">{{ t('amount') }}</th><th>{{ t('status') }}</th><th aria-label="Actions"></th></tr></thead>
          <tbody>
            <tr v-if="loading && !items.length"><td colspan="8" class="inv-empty">{{ t('loading') }}</td></tr>
            <tr v-else-if="!filtered.length"><td colspan="8" class="inv-empty">{{ t('empty') }}</td></tr>
            <tr v-for="i in filtered" :key="i.item_code">
              <td><div class="inv-product"><div class="inv-thumb"><img v-if="i.image" :src="i.image" alt="" loading="lazy" /><span v-else>{{ (i.item_name || '?').slice(0,1).toUpperCase() }}</span></div><div class="inv-itemname" :title="i.item_name"><strong>{{ i.item_name }}</strong><small>{{ i.stock_uom }}<template v-if="i.has_serial_no"> · Serial tracked</template></small></div></div></td>
              <td class="inv-code">{{ i.item_code }}</td><td class="inv-muted">{{ i.item_group || '—' }}</td>
              <td class="inv-right"><strong>{{ number(i.actual_qty) }}</strong></td>
              <td>{{ Number(i.warranty_days) > 0 ? number(i.warranty_days) + ' ' + t('days') : t('none') }}</td>
              <td class="inv-right inv-money">{{ money(i.stock_value) }}</td>
              <td><span class="inv-chip" :class="'inv-' + stockStatus(i)">{{ stockStatus(i) === 'in' ? t('inStock') : stockStatus(i) === 'low' ? t('low') : t('out') }}</span></td>
              <td><button type="button" class="inv-rowaction" :disabled="!!i.has_serial_no || !!i.has_batch_no" :title="i.has_serial_no || i.has_batch_no ? t('serialNote') : t('stockIn')" :aria-label="t('stockIn') + ': ' + i.item_name" @click="openMovement('receive', i.item_code)">＋</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="modalOpen" class="inv-modal-backdrop" @click.self="!submitting && (modalOpen = false)" @keydown.esc="!submitting && (modalOpen = false)">
      <div class="inv-modal" role="dialog" aria-modal="true" :aria-label="t('movement')">
        <div class="inv-modal-header"><div><div class="inv-eyebrow">{{ t('movement') }}</div><h2>{{ movement === 'receive' ? t('stockIn') : t('stockOut') }}</h2></div><button type="button" class="inv-close" :disabled="submitting" :aria-label="t('close')" @click="modalOpen=false">×</button></div>
        <form @submit.prevent="submitMovement" class="inv-modal-form">
          <label>{{ t('chooseItem') }}<select v-model="form.item_code" required><option value="">—</option><option v-for="i in items" :key="i.item_code" :value="i.item_code">{{ i.item_name }} · {{ i.item_code }}</option></select></label>
          <p v-if="selected && (selected.has_serial_no || selected.has_batch_no)" class="inv-alert inv-error">{{ t('serialNote') }}</p>
          <label>{{ t('chooseWarehouse') }}<select v-model="form.warehouse" required><option value="">—</option><option v-for="w in inventory.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></label>
          <div class="inv-modal-pair"><label>{{ t('quantity') }}<input v-model.number="form.qty" type="number" min="0.001" step="0.001" required /></label><label v-if="movement === 'receive'">{{ t('unitRate') }} ({{ inventory.currency }})<input v-model.number="form.basic_rate" type="number" min="0.01" step="0.01" required /></label></div>
          <p v-if="movement === 'issue' && availableHere !== null" class="inv-helper">{{ t('availableAt') }}: {{ number(availableHere) }} {{ selected?.stock_uom }}</p>
          <label>{{ t('remarks') }}<textarea v-model="form.remarks" rows="2" maxlength="1000"></textarea></label>
          <p class="inv-helper">{{ movement === 'receive' ? t('receiptNote') : t('permission') }}</p>
          <p v-if="formError" class="inv-alert inv-error" role="alert">{{ formError }}</p>
          <div class="inv-modal-foot"><button type="button" class="inv-btn inv-outline" :disabled="submitting" @click="modalOpen=false">{{ t('cancel') }}</button><button type="submit" class="inv-btn inv-primary" :disabled="submitting || selected?.has_serial_no || selected?.has_batch_no">{{ submitting ? t('processing') : t('submit') }}</button></div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.inv-root,.inv-root *{box-sizing:border-box}.inv-root{--ink:#443429;--muted:#877869;--line:#e9ddcf;--cream:#fffdf9;--sand:#f5eee5;--espresso:#674a30;color:var(--ink);font-family:inherit;width:100%;max-width:100%;padding:27px clamp(14px,2.3vw,34px) 44px;background:#faf7f2;min-height:calc(100vh - 70px)}
.inv-head{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:26px}.inv-eyebrow{font-size:10px;font-weight:800;letter-spacing:.12em;color:#977b59;text-transform:uppercase;display:flex;align-items:center;gap:8px}.inv-live-dot{width:8px;height:8px;border-radius:50%;background:#c39b67;display:inline-block}.inv-head h1{margin:7px 0 3px;font-size:clamp(24px,2.2vw,32px);font-weight:800;letter-spacing:-.035em;color:#392b21;line-height:1.25}.inv-head p{margin:0;color:var(--muted);font-size:13px}.inv-company{margin-top:7px;font-size:10px;letter-spacing:.05em;font-weight:700;color:#ae9580}.inv-actions{display:flex;align-items:center;justify-content:flex-end;gap:9px;flex-wrap:wrap}.inv-btn{appearance:none;border:1px solid #dbcbb7;background:#fffdf9;color:#705943;display:inline-flex;align-items:center;justify-content:center;gap:6px;border-radius:10px;padding:11px 15px;min-height:41px;white-space:nowrap;cursor:pointer;font-size:12px;font-weight:750;box-shadow:none}.inv-btn:hover:not(:disabled){background:#f4ebdf}.inv-btn:disabled{opacity:.45;cursor:not-allowed}.inv-btn.inv-primary{background:#6e4e34;color:#fffaf2;border-color:#6e4e34}.inv-btn.inv-primary:hover:not(:disabled){background:#523824}.inv-btn.inv-small{padding:9px 12px;min-height:37px}.inv-btn:focus-visible,.inv-rowaction:focus-visible{outline:3px solid #c8a674;outline-offset:2px}
.inv-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:22px}.inv-stat{min-width:0;padding:17px 19px 18px;background:var(--cream);border:1px solid var(--line);border-radius:15px;box-shadow:0 4px 14px #6d513509}.inv-stat-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.inv-stat-symbol{height:38px;width:38px;display:grid;place-items:center;background:#f0e3d3;color:#77553b;font-weight:800;font-size:19px;border-radius:11px}.inv-stat-tag{font-size:9px;font-weight:800;color:#b5a594;letter-spacing:.09em}.inv-stat-number{font-weight:800;font-size:26px;line-height:1.2;color:#453226;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}.inv-stat-number.inv-amount{font-size:19px}.inv-stat>span{font-size:12px;color:#988676;display:block;margin-top:5px}
.inv-panel{background:#fffefb;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 5px 24px #8f75550b}.inv-panel-head{padding:19px 20px;display:flex;justify-content:space-between;gap:20px;align-items:center}.inv-panel-head h2,.inv-modal h2{font-size:17px;font-weight:800;color:#47362a;margin:0 0 5px;letter-spacing:-.025em}.inv-panel-head p{font-size:11px;color:#998c7d;margin:0}.inv-toolbar{display:grid;grid-template-columns:minmax(190px,1.7fr) repeat(3,minmax(110px,1fr));gap:10px;padding:15px 20px;background:#fcf9f5;border-block:1px solid #eee5d9}.inv-toolbar select,.inv-search,input,textarea,.inv-modal select{font-family:inherit}.inv-toolbar select,.inv-search{height:40px;width:100%;border:1px solid #e5d9ca;border-radius:9px;background:white;color:#6b594a;padding:0 11px;min-width:0;font-size:12px;outline-color:#bfa17e}.inv-search{display:flex;align-items:center;gap:8px;padding:0 11px}.inv-search span{font-size:23px;color:#aa9075;line-height:1}.inv-search input{width:100%;min-width:0;border:0;outline:0;color:#48392f;background:transparent;font-size:12px}.inv-summary{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 20px;color:#9a8a7b;font-size:11px}.inv-summary label{display:flex;align-items:center;gap:8px}.inv-summary input{width:53px;height:28px;border:1px solid #e5d8c8;border-radius:6px;padding:3px 5px;color:#65503d;background:#fff}
.inv-table-wrap{overflow-x:auto}.inv-table{width:100%;border-collapse:collapse;min-width:920px;text-align:left}.inv-table thead{background:#f8f1e8}.inv-table th{padding:13px 15px;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:#8d7660;font-weight:800;white-space:nowrap}.inv-table td{padding:13px 15px;border-top:1px solid #f0e9df;vertical-align:middle;font-size:12px;color:#645347;max-width:260px}.inv-table tbody tr:hover{background:#fffcf8}.inv-product{display:flex;align-items:center;gap:11px;min-width:165px}.inv-thumb{height:39px;width:39px;border-radius:10px;display:grid;place-items:center;background:#f1e5d7;color:#936c47;font-size:17px;font-weight:800;flex:0 0 39px;overflow:hidden}.inv-thumb img{width:100%;height:100%;object-fit:cover}.inv-itemname{display:flex;flex-direction:column;gap:3px;min-width:0}.inv-itemname strong{font-size:12px;color:#443429;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:235px}.inv-itemname small{font-size:10px;color:#a3907d}.inv-right{text-align:right !important;font-variant-numeric:tabular-nums}.inv-code{font-size:11px !important;color:#846d59 !important}.inv-muted{color:#938273 !important}.inv-money{font-size:11px !important;white-space:nowrap}.inv-chip{display:inline-flex;align-items:center;border:1px solid #e5dbcc;border-radius:999px;background:#f6f0e8;color:#876c51;padding:5px 9px;font-size:10px;font-weight:750;white-space:nowrap}.inv-chip.inv-low{background:#fff2de;border-color:#f0dcba;color:#a16c2f}.inv-chip.inv-out{background:#f5e7e5;border-color:#ebd4cd;color:#9a584c}.inv-rowaction{height:29px;width:29px;border-radius:8px;border:1px solid #e4d9cb;background:#fffcf8;color:#815e41;font-size:16px;cursor:pointer}.inv-rowaction:disabled{opacity:.3;cursor:not-allowed}.inv-empty{text-align:center !important;padding:55px 20px !important;color:#a19283 !important}.inv-alert{margin:0 0 16px;padding:12px 15px;border:1px solid #e6d8c3;background:#fff8ec;color:#7e6041;border-radius:10px;font-size:12px}.inv-error{background:#fff0ea;border-color:#edd3c7;color:#9c493d}.inv-success{background:#f2eee7;border-color:#ded0bc;color:#68523a}.inv-alert button{margin-left:10px;cursor:pointer;border:none;text-decoration:underline;color:inherit;background:none;font-weight:750}
.inv-modal-backdrop{position:fixed;inset:0;z-index:10000;background:#24190f91;display:flex;align-items:center;justify-content:center;padding:15px}.inv-modal{width:min(510px,100%);max-height:calc(100vh - 30px);overflow:auto;background:#fffdf9;border-radius:18px;border:1px solid #e4d5c1;box-shadow:0 18px 65px #1e130e43}.inv-modal-header{padding:23px 25px 17px;display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid #eee3d6}.inv-modal-header h2{font-size:21px;margin-top:7px}.inv-close{width:33px;height:33px;display:grid;place-items:center;border:1px solid #e8dac9;border-radius:9px;background:#fff8f1;font-size:22px;color:#886b52;cursor:pointer}.inv-modal-form{padding:20px 25px 25px;display:flex;flex-direction:column;gap:14px}.inv-modal-form label{display:flex;flex-direction:column;gap:6px;font-size:11px;color:#69513e;font-weight:750}.inv-modal-form input,.inv-modal-form select,.inv-modal-form textarea{width:100%;min-width:0;border:1px solid #e1d2bf;background:#fff;border-radius:9px;color:#4c382a;font-size:13px;padding:10px 11px;outline-color:#bb9b74}.inv-modal-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.inv-helper{color:#927c69;font-size:11px;line-height:1.5;margin:0}.inv-modal-foot{display:flex;justify-content:flex-end;gap:9px;margin-top:3px}
@media(max-width:1160px){.inv-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.inv-toolbar{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:680px){.inv-root{padding:16px 12px 35px}.inv-head{flex-direction:column;align-items:flex-start;gap:13px}.inv-actions{justify-content:flex-start}.inv-metrics{gap:9px}.inv-stat{padding:14px 13px}.inv-stat-number{font-size:22px}.inv-stat-number.inv-amount{font-size:16px}.inv-panel-head{padding:15px;align-items:flex-start}.inv-toolbar{padding:12px;grid-template-columns:minmax(0,1fr)}.inv-summary{padding:10px 12px;flex-wrap:wrap}.inv-modal-form{padding:17px}.inv-modal-header{padding:17px}.inv-modal-pair{grid-template-columns:1fr}.inv-btn{padding:10px 11px}}
</style>
