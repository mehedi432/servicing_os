<script setup>
// SOS_COUNTER_PREMIUM_INVOICE_681 — read-only bridge to the exact shared print studio.
import { ref, watch, onUnmounted } from 'vue'
import SalesInvoiceStudio from './SalesInvoiceStudio.vue'
const props = defineProps({ invoiceName: { type: String, required: true } })
const emit = defineEmits(['close'])
const receipt = ref(null)
const busy = ref(false)
const error = ref('')
let sequence = 0
let controller = null
async function load() {
  const seq = ++sequence
  if (controller) controller.abort()
  controller = new AbortController()
  busy.value = true
  error.value = ''
  receipt.value = null
  try {
    const url = new URL('/api/method/servicing_os.api.invoice_warranty_659.get_invoice_with_warranty', window.location.origin)
    url.searchParams.set('invoice_name', props.invoiceName)
    url.searchParams.set('doctype', 'Sales Invoice')
    const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }, signal: controller.signal })
    const data = await response.json()
    if (!response.ok || data.exc || data.exception || !data.message || !Array.isArray(data.message.items)) {
      throw new Error(typeof data.message === 'string' ? data.message : 'Unable to load the saved invoice. Check invoice read permissions.')
    }
    if (seq !== sequence) return
    const d = data.message
    // Retain all server fields, only alias names used by the shared Studio.
    receipt.value = {
      ...d,
      invoice: d.name,
      customer_mobile: d.customer_phone || d.customer_mobile || '',
      mode_of_payment: Array.isArray(d.payments) ? d.payments.map(x => x.mode_of_payment).filter(Boolean).join(', ') : '',
      items: d.items.map(item => ({
        ...item,
        warranty_days: item.warranty_recorded && item.warranty_type !== 'No Warranty'
          ? (Number(item.warranty_period_days) > 0 ? Number(item.warranty_period_days) : null)
          : null
      }))
    }
  } catch (e) {
    if (seq === sequence && e?.name !== 'AbortError') error.value = e?.message || 'Invoice could not be loaded.'
  } finally { if (seq === sequence) busy.value = false }
}
watch(() => props.invoiceName, load, { immediate: true })
onUnmounted(() => { sequence++; if (controller) controller.abort() })
</script>

<template>
  <SalesInvoiceStudio v-if="receipt" :receipt="receipt" @close="emit('close')" />
  <div v-else class="sos681-overlay" role="dialog" aria-modal="true" aria-label="Premium invoice">
    <div class="sos681-panel">
      <div class="sos681-top"><div><small>AL MODINA · INVOICE STUDIO</small><h2>Premium Invoice</h2></div><button type="button" @click="emit('close')">Close</button></div>
      <p v-if="busy">Loading saved ERPNext invoice…</p>
      <template v-else-if="error"><p role="alert">{{ error }}</p><button type="button" @click="load">Retry</button></template>
    </div>
  </div>
</template>

<style scoped>
.sos681-overlay{position:fixed;inset:0;z-index:11010;display:grid;place-items:center;background:#2b1d14aa;padding:20px}
.sos681-panel{background:#fffaf3;border:1px solid #e6d9c9;border-radius:18px;padding:24px;width:min(460px,100%);color:#3e3025;box-shadow:0 20px 60px #24170c55}
.sos681-top{display:flex;justify-content:space-between;gap:16px;align-items:center}.sos681-top h2{margin:5px 0;font-size:20px}.sos681-top small{color:#947454;letter-spacing:1px;font-weight:700}.sos681-panel p{font-size:13px;line-height:1.5}.sos681-panel button{background:#f0e3d5;border:1px solid #ddc9b4;border-radius:9px;padding:9px 14px;color:#614c37;cursor:pointer}
</style>
