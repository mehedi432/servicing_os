<script setup>
// SOS_COUNTER_PREMIUM_INVOICE_681 — read-only bridge to the exact shared print studio.
import { computed, ref, watch, onUnmounted } from 'vue'
import InvoiceTransactionPanel from './InvoiceTransactionPanel.vue'
import SalesInvoiceStudio from './SalesInvoiceStudio.vue'
import SavedInvoiceCheckout from './SavedInvoiceCheckout.vue'
const props = defineProps({
  invoiceName: { type: String, required: true },
  doctype: { type: String, default: 'Sales Invoice' },
  checkout: Boolean,
  duplicate: { type: Boolean, default: false },
  previewOnly: { type: Boolean, default: false },
  startPayment: Boolean,
  submitDraft: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'submitted'])
const receipt = ref(null)
const error = ref('')
const submitting = ref(false)
const submitError = ref('')
const submitMessage = ref('')
const view = ref(props.startPayment ? 'pay' : '')
const transactionBusy = ref(false)
const actionHeading = computed(() => view.value === 'edit' ? 'Edit sales invoice' :
  view.value === 'pay' ? 'Record invoice payment' : '')
async function onTransactionChanged(result) {
  view.value = ''
  submitError.value = ''
  const payment = result.payment_entry
  submitMessage.value = payment ? `${payment} recorded · Remaining ${receipt.value.currency} ${result.outstanding}`
    : `${result.invoice} draft saved.`
  window.dispatchEvent(new CustomEvent(payment ? 'servicing-os-invoice-payment-recorded' : 'servicing-os-invoice-updated',
    { detail: result }))
  await load()
}
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
    url.searchParams.set('doctype', props.doctype)
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
function refresh() {
  submitError.value = ''
  load()
}
async function submitInvoice() {
  const invoice = receipt.value
  if (!props.submitDraft || !invoice?.can_submit || !invoice.modified || submitting.value) return
  if (!window.confirm(`Submit Sales Invoice ${invoice.name}? ERPNext will post the saved invoice. Any required approved spare-part issues will be processed.`)) return
  submitting.value = true
  submitError.value = ''
  try {
    const token = window.frappe?.csrf_token || window.csrf_token ||
      document.querySelector('meta[name="csrf-token"]')?.content ||
      decodeURIComponent(document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1] || '')
    const response = await fetch('/api/method/servicing_os.api.invoice_review.submit_reviewed_invoice', {
      method: 'POST', credentials: 'same-origin',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': token },
      body: JSON.stringify({ invoice_name: invoice.name, expected_modified: invoice.modified }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok || Number(data.message?.docstatus) !== 1 || data.message.invoice !== invoice.name) {
      let detail = typeof data.message === 'string' ? data.message : 'Unable to submit the draft invoice.'
      try {
        const [message] = JSON.parse(data._server_messages || '[]')
        if (message) {
          const paragraph = document.createElement('div')
          paragraph.innerHTML = JSON.parse(message).message || ''
          detail = paragraph.textContent || detail
        }
      } catch {}
      throw new Error(detail)
    }
    submitMessage.value = `${invoice.name} submitted.`
    emit('submitted', data.message)
    window.dispatchEvent(new CustomEvent('servicing-os-invoice-finalized', { detail: data.message }))
    await load()
  } catch (failure) {
    submitError.value = failure.message
  } finally {
    submitting.value = false
  }
}
watch(() => [props.invoiceName, props.doctype], () => {
  submitMessage.value = submitError.value = ''
  view.value = props.startPayment ? 'pay' : ''
  load()
}, { immediate: true })
onUnmounted(() => { sequence++; if (controller) controller.abort() })
</script>

<template>
  <SavedInvoiceCheckout v-if="checkout" :invoice-name="invoiceName" :invoice="receipt" :error="error"
    :action-error="submitError" :message="submitMessage" :busy="submitting || transactionBusy" :mode="view"
    @close="emit('close')" @retry="refresh" @edit="view = 'edit'" @pay="view = 'pay'" @submit="submitInvoice">
    <template #transaction>
      <InvoiceTransactionPanel :key="view" :invoice-name="invoiceName" :mode="view"
        back-label="Back to checkout" @back="view = ''; refresh()" @busy="transactionBusy = $event" @changed="onTransactionChanged" />
    </template>
  </SavedInvoiceCheckout>
  <SalesInvoiceStudio v-else :key="invoiceName" :receipt="receipt" :invoice-name="invoiceName"
    :duplicate="duplicate" :preview-only="previewOnly && Number(receipt?.docstatus) !== 1" :error="error"
    :draft-action="submitDraft && !view" :can-submit="!!receipt?.can_submit" :submitting="submitting || transactionBusy"
    :action-heading="actionHeading"
    :submit-error="submitError" :submit-message="submitMessage"
    @close="emit('close')" @retry="refresh" @submit="submitInvoice">
    <template v-if="submitDraft && !view" #actions>
      <div class="invoice-transaction-actions">
        <button v-if="receipt?.can_edit" type="button" :disabled="submitting" @click="view = 'edit'">Edit Draft</button>
        <button v-if="receipt?.can_pay" type="button" :disabled="submitting" @click="view = 'pay'">Receive payment</button>
      </div>
    </template>
    <template v-if="view" #workspace>
      <InvoiceTransactionPanel :key="view" :invoice-name="invoiceName" :mode="view"
        @back="view = ''; refresh()" @busy="transactionBusy = $event" @changed="onTransactionChanged" />
    </template>
  </SalesInvoiceStudio>
</template>

<style scoped>
.invoice-transaction-actions{grid-column:1/-1;display:flex;gap:7px;flex-wrap:wrap;margin-bottom:5px}
.invoice-transaction-actions:empty{display:none}
.invoice-transaction-actions button{border:1px solid #cfb59d;border-radius:8px;background:#f7ecdf;color:#553b27;padding:6px 10px;font-weight:700;min-height:35px;cursor:pointer}
</style>
