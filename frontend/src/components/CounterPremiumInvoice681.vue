<script setup>
// SOS_COUNTER_PREMIUM_INVOICE_681 — read-only bridge to the exact shared print studio.
import { ref, watch, onUnmounted } from 'vue'
import SalesInvoiceStudio from './SalesInvoiceStudio.vue'
const props = defineProps({
  invoiceName: { type: String, required: true },
  duplicate: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])
const receipt = ref(null)
const error = ref('')
let sequence = 0
let controller = null
async function load() {
  const seq = ++sequence
  if (controller) controller.abort()
  controller = new AbortController()
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
  }
}
watch(() => props.invoiceName, load, { immediate: true })
onUnmounted(() => { sequence++; if (controller) controller.abort() })
</script>

<template>
  <SalesInvoiceStudio :key="invoiceName" :receipt="receipt" :invoice-name="invoiceName"
    :duplicate="duplicate" :error="error" @close="emit('close')" @retry="load" />
</template>
