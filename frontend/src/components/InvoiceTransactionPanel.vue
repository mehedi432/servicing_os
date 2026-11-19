<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  invoiceName: { type: String, required: true },
  mode: { type: String, required: true },
})
const emit = defineEmits(['back', 'busy', 'changed'])
const context = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const amount = ref('')
const method = ref('')
const referenceNo = ref('')
const referenceDate = ref('')
const requestKey = ref('')
const controller = new AbortController()
const isDraft = computed(() => props.mode === 'edit')
const selectedMethod = computed(() => context.value?.methods?.find(entry => entry.name === method.value))
const money = value => new Intl.NumberFormat('en-BD', {
  style: 'currency', currency: context.value?.currency || 'BDT',
}).format(Number(value || 0))
const step = precision => 10 ** -Number(precision || 0)

async function rpc(module, action, payload) {
  const url = new URL(`/api/method/servicing_os.api.${module}.${action}`, window.location.origin)
  const headers = { Accept: 'application/json' }
  const options = { headers, credentials: 'same-origin', cache: 'no-store' }
  if (payload) {
    headers['Content-Type'] = 'application/json'
    headers['X-Frappe-CSRF-Token'] = window.frappe?.csrf_token || window.csrf_token ||
      document.querySelector('meta[name="csrf-token"]')?.content || ''
    options.method = 'POST'
    options.body = JSON.stringify({ invoice_name: props.invoiceName, ...payload })
  } else {
    url.searchParams.set('invoice_name', props.invoiceName)
    options.signal = controller.signal
  }
  const response = await fetch(url, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok || data.exc || data.exception || !data.message) {
    let message = typeof data.message === 'string' ? data.message : 'The transaction could not be completed.'
    try {
      const [entry] = JSON.parse(data._server_messages || '[]')
      if (entry) {
        const element = document.createElement('div')
        element.innerHTML = JSON.parse(entry).message || ''
        message = element.textContent || message
      }
    } catch {}
    throw new Error(message)
  }
  return data.message
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    context.value = isDraft.value
      ? await rpc('invoice_review', 'get_draft_editor')
      : await rpc('invoice_payment', 'get_payment_context')
    if (!isDraft.value) {
      amount.value = context.value.outstanding
      method.value = context.value.methods[0]?.name || ''
      referenceDate.value = context.value.posting_date
      requestKey.value = Array.from(crypto.getRandomValues(new Uint8Array(16)),
        byte => byte.toString(16).padStart(2, '0')).join('')
    }
  } catch (failure) {
    if (failure.name !== 'AbortError') error.value = failure.message
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value || !context.value) return
  const doc = context.value
  const payload = isDraft.value ? {
    expected_modified: doc.modified,
    items: doc.items.map(row => ({ name: row.name, qty: row.qty, rate: row.rate })),
    due_date: doc.due_date,
    discount_mode: doc.discount_mode,
    discount_value: doc.discount_mode === 'none' ? 0 : doc.discount_value,
    discount_basis: doc.discount_basis,
  } : {
    amount: String(amount.value),
    mode_of_payment: method.value,
    reference_no: selectedMethod.value?.needs_reference ? referenceNo.value : '',
    reference_date: selectedMethod.value?.needs_reference ? referenceDate.value : '',
    expected_outstanding: doc.outstanding,
    request_key: requestKey.value,
  }
  if (!isDraft.value && !window.confirm(`Record ${money(amount.value)} received by ${method.value} for ${props.invoiceName}?`)) {
    return
  }
  saving.value = true
  error.value = ''
  emit('busy', true)
  let result
  try {
    result = isDraft.value
      ? await rpc('invoice_review', 'save_reviewed_draft', payload)
      : await rpc('invoice_payment', 'receive_invoice_payment', payload)
  } catch (failure) {
    error.value = failure.message
  } finally {
    saving.value = false
    emit('busy', false)
  }
  if (result) emit('changed', result)
}

onMounted(load)
onBeforeUnmount(() => controller.abort())
</script>

<template>
  <article class="invoice-transaction">
    <header class="transaction-header">
      <div><h3>{{ isDraft ? 'Edit draft' : 'Record payment' }}</h3><p>{{ invoiceName }}</p></div>
      <button type="button" :disabled="saving" @click="emit('back')">Back to invoice</button>
    </header>
    <p v-if="loading" role="status">Loading…</p>
    <p v-if="error" class="transaction-error" role="alert">{{ error }}</p>
    <form v-if="context && !loading" @submit.prevent="save">
      <fieldset :disabled="saving">
        <template v-if="isDraft">
          <p>Adjust quantities and selling rates on the saved invoice items.</p>
          <div class="transaction-table">
            <table>
              <thead><tr><th scope="col">Item</th><th scope="col">Quantity</th><th scope="col">Unit selling rate</th></tr></thead>
              <tbody>
                <tr v-for="row in context.items" :key="row.name">
                  <td><strong>{{ row.item }}</strong><small v-if="row.code">{{ row.code }}</small></td>
                  <td><input v-model="row.qty" type="number" :step="step(row.qty_precision)"
                    :min="step(row.qty_precision)" max="100000" :readonly="row.quantity_locked"
                    :aria-label="`Quantity for ${row.item}`" required />
                    <small v-if="row.quantity_locked">Linked stock quantity</small>
                  </td>
                  <td><input v-model="row.rate" type="number" :step="step(row.rate_precision)" min="0"
                    :aria-label="`Selling rate for ${row.item}`" required /></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="transaction-grid">
            <label>Due date<input v-model="context.due_date" type="date" required /></label>
            <label>Additional discount
              <select v-model="context.discount_mode">
                <option value="none">None</option><option value="percent">Percentage</option><option value="amount">Amount</option>
              </select>
            </label>
            <label v-if="context.discount_mode !== 'none'">Discount value
              <input v-model="context.discount_value" type="number" min="0" step="any" required />
            </label>
            <label v-if="context.discount_mode !== 'none'">Discount applies to
              <select v-model="context.discount_basis"><option>Grand Total</option><option>Net Total</option></select>
            </label>
          </div>
        </template>
        <template v-else>
          <p class="transaction-balance">Outstanding balance <strong>{{ money(context.outstanding) }}</strong></p>
          <div class="transaction-grid">
            <label>Amount received
              <input v-model="amount" type="number" :min="step(context.precision)" :step="step(context.precision)"
                :max="context.outstanding" required />
            </label>
            <label>Mode of payment
              <select v-model="method" required>
                <option v-for="entry in context.methods" :key="entry.name" :value="entry.name">{{ entry.name }}</option>
              </select>
            </label>
            <label v-if="selectedMethod?.needs_reference">Transaction reference
              <input v-model.trim="referenceNo" type="text" maxlength="140" required />
            </label>
            <label v-if="selectedMethod?.needs_reference">Transaction date
              <input v-model="referenceDate" type="date" :max="context.posting_date" required />
            </label>
          </div>
          <p v-if="selectedMethod">Receiving account <strong>{{ selectedMethod.account }}</strong></p>
        </template>
        <footer><button class="transaction-primary" type="submit">{{ saving ? 'Saving…' : isDraft ? 'Save Draft Changes' : 'Record Payment' }}</button></footer>
      </fieldset>
    </form>
  </article>
</template>

<style scoped>
.invoice-transaction{padding:18px;border:1px solid #dfcdbc;border-radius:12px;background:#fffaf4;color:#493626}
.transaction-header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;border-bottom:1px solid #eadbd0;padding-bottom:12px}
.transaction-header h3{margin:0;font-size:21px}.transaction-header p{margin:4px 0 0;color:#765d49}
fieldset{min-width:0;margin:0;padding:0;border:0}
.transaction-table{overflow:auto;margin:12px 0}
table{width:100%;min-width:340px;border-collapse:collapse}
td,th{padding:7px 8px;text-align:left;border-bottom:1px solid #eee1d5}
th{background:#f7eee5}td:nth-child(n+2){width:24%}
td small{display:block;color:#765d49}
.transaction-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(150px,100%),1fr));gap:10px;margin:12px 0}
label{display:grid;gap:4px;font-weight:650}
input,select,button{font:inherit;border:1px solid #ddc8b5;border-radius:8px;min-height:35px;padding:6px 8px;color:inherit;background:#fffdf9}
input,select{width:100%;min-width:0}
button{cursor:pointer;font-weight:700}
button:disabled{opacity:.55;cursor:default}
input:read-only:not(:focus){background:#f5ece1}
.transaction-primary{background:#735037;color:#fff;border-color:#735037}
footer{display:flex;justify-content:flex-end;margin-top:14px}
.transaction-balance{padding:10px;background:#f2e8dd;border-radius:8px}.transaction-balance strong{margin-left:8px}
.transaction-error{padding:9px;background:#faeee8;color:#9f3c2c;border-radius:6px}
</style>
