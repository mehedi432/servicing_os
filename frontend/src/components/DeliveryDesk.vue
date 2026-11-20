<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import CounterCheckout670 from './CounterCheckout670.vue'
import InvoiceTransactionPanel from './InvoiceTransactionPanel.vue'

const props = defineProps({
  jobName: { type: String, required: true },
  printOpen: Boolean,
})
const emit = defineEmits(['close', 'delivered', 'print'])
const dialog = ref(null)
const stepHeading = ref(null)
const context = ref(null)
const invoice = ref(null)
const parts = ref(null)
const posts = ref([])
const step = ref(0)
const loading = ref(false)
const loadingParts = ref(false)
const submitting = ref(false)
const editing = ref(false)
const consent = ref(false)
const leaveBalance = ref(false)
const takingPayment = ref(false)
const paymentBusy = ref(false)
const paymentReceipt = ref('')
const loadError = ref('')
const partsError = ref('')
const submitError = ref('')
const steps = ['Review invoice', 'Check spare parts', 'Receive payment', 'Confirm handover', 'Print documents']
const requestLabels = {
  approval: 'Awaiting approval',
  duplicates: 'Multiple entries',
  issued: 'Issued',
  stopped: 'Stopped',
  pending: 'Approved · awaiting issue',
}
const deviceName = computed(() => {
  const device = context.value?.device || {}
  return [device.brand, device.device_model].filter(Boolean).join(' ') || device.device_type || 'Device details unavailable'
})
const submitted = computed(() => invoice.value?.docstatus === 1)
const balance = computed(() => invoice.value?.outstanding_amount)
const amountDue = computed(() => submitted.value && Number(balance.value) > 0)
const canClose = computed(() => !submitting.value && !paymentBusy.value)
const canCollect = computed(() => amountDue.value && context.value?.allow_payment)
const hasBlockingRequests = computed(() => (parts.value?.requests || []).some(request =>
  submitted.value ? request.state !== 'issued' : ['approval', 'duplicates', 'stopped'].includes(request.state)))
const hasBlockingItems = computed(() => (parts.value?.items || []).some(item => item.shortage > 0 || item.manual_issue))
const partsBlocked = computed(() => hasBlockingRequests.value || hasBlockingItems.value)
const canHandover = computed(() => submitted.value && balance.value != null
  && (!amountDue.value || leaveBalance.value) && consent.value && !submitting.value && !loading.value
  && !loadingParts.value && !partsError.value && !partsBlocked.value
  && invoice.value?.name && context.value?.can_write && !context.value?.issue)
const formatMoney = amount => amount == null ? '—' :
  `${invoice.value?.currency || 'BDT'} ${Number(amount).toLocaleString('en-BD', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
const formatQty = amount => Number(amount).toLocaleString('en-BD', {maximumFractionDigits: 6})
const deskLink = (type, id) => `/app/${type}/${encodeURIComponent(id)}`

function errorMessage(payload, fallback) {
  try {
    const messages = JSON.parse(payload?._server_messages || '[]').reverse()
    for (const entry of messages) {
      const message = (typeof entry === 'string' ? JSON.parse(entry) : entry)?.message
      if (typeof message === 'string' && message.trim()) return message.replace(/<[^>]*>/g, '')
    }
  } catch (_) {}
  const message = payload?.message?.message || payload?.message
  return typeof message === 'string' ? message.replace(/<[^>]*>/g, '') : fallback
}
async function request(method, fallback, { params = {}, body } = {}) {
  const url = new URL(`/api/method/servicing_os.api.${method}`, window.location.origin)
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value)
  const headers = { Accept: 'application/json' }
  if (body) {
    headers['Content-Type'] = 'application/json'
    headers['X-Frappe-CSRF-Token'] = window.frappe?.csrf_token || window.csrf_token
      || document.querySelector('meta[name="csrf-token"]')?.content
      || decodeURIComponent(document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1] || '')
  }
  const response = await fetch(url, {
    method: body ? 'POST' : 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers,
    ...(body ? {body: JSON.stringify(body)} : {}),
  })
  const payload = await response.json().catch(() => null)
  if (!payload || !response.ok || payload.exc || payload.exc_type || payload.exception) {
    throw Error(errorMessage(payload, fallback))
  }
  return payload.message
}

async function load() {
  if (loading.value || submitting.value) return
  loading.value = true
  loadError.value = ''
  consent.value = false
  try {
    const data = await request('checkout_712.handover_context', 'Could not load the selected Service Job.', {
      params: {job_name: props.jobName},
    })
    if (data?.service_job !== props.jobName) throw Error('The selected Service Job changed. Reopen the Delivery Desk.')
    context.value = data
    invoice.value = data.invoice
    if (data.already_delivered) step.value = 4
    else if (!invoice.value || data.issue) step.value = 0
    if (invoice.value && step.value === 0) {
      const detail = await request('counter_invoice_654.get_counter_invoice_detail', 'Could not load the invoice lines.', {
        params: {invoice_name: invoice.value.name},
      })
      if (detail?.name !== invoice.value.name || detail.service_job !== props.jobName || detail.customer !== data.customer || detail.docstatus === 2) {
        throw Error('The invoice changed or belongs to a different job or customer. Reload and check the invoice in ERPNext.')
      }
      invoice.value = {...invoice.value, ...detail}
    }
  } catch (failure) {
    loadError.value = failure.message
  } finally {
    loading.value = false
  }
}
async function loadParts() {
  if (loadingParts.value || submitting.value) return
  loadingParts.value = true
  partsError.value = ''
  consent.value = false
  try {
    const data = await request('checkout_712.handover_parts', 'Could not check spare parts.', {params: {job_name: props.jobName}})
    if (typeof data?.checked !== 'boolean') throw Error('Spare-parts availability could not be verified. Refresh and try again.')
    parts.value = data
  } catch (failure) {
    partsError.value = failure.message
    parts.value = null
  } finally {
    loadingParts.value = false
  }
}
function goTo(next) {
  if (paymentBusy.value) return
  takingPayment.value = false
  leaveBalance.value = false
  consent.value = false
  submitError.value = ''
  step.value = next
  if (next === 1) loadParts()
}
async function resumeSaved() {
  editing.value = false
  await load()
}
async function submitInvoice() {
  if (!invoice.value || submitted.value || submitting.value) return
  submitting.value = true
  submitError.value = ''
  try {
    const result = await request('checkout_712.submit_for_payment', 'Could not submit the invoice.', {
      body: {job_name: props.jobName, invoice_name: invoice.value.name, expected_modified: invoice.value.modified},
    })
    if (result?.invoice !== invoice.value.name || Number(result.docstatus) !== 1) {
      throw Error('Invoice submission could not be verified. Reload and check its status.')
    }
    posts.value = result.stock_entries || []
    window.dispatchEvent(new CustomEvent('servicing-os-invoice-finalized', {detail: result}))
  } catch (failure) {
    submitError.value = failure.message
  } finally {
    submitting.value = false
  }
  if (!submitError.value) {
    await load()
    if (canCollect.value) takingPayment.value = true
  }
}

async function paymentRecorded(result) {
  takingPayment.value = false
  paymentReceipt.value = result.payment_entry
  window.dispatchEvent(new CustomEvent('servicing-os-invoice-payment-recorded', {detail: result}))
  await load()
  focusHeading()
}

async function complete() {
  if (!canHandover.value) return
  submitting.value = true
  submitError.value = ''
  const invoiceName = invoice.value.name
  try {
    const result = await request('checkout_712.deliver_with_existing_invoice', 'Could not complete handover.', {
      body: {
        job_name: props.jobName, invoice_name: invoiceName, confirmation: props.jobName,
        expected_modified: invoice.value.modified, expected_outstanding: balance.value,
        allow_outstanding: Number(leaveBalance.value),
      },
    })
    if (result?.service_job !== props.jobName || result.invoice !== invoiceName || result.status !== 'Delivered') {
      throw Error('Handover status could not be confirmed. Check the record before trying again.')
    }
    context.value = {...context.value, status: 'Delivered', already_delivered: true}
    step.value = 4
    emit('delivered', result)
    emit('print', invoiceName)
  } catch (failure) {
    submitError.value = failure.message
  } finally {
    submitting.value = false
  }
}

const focusHeading = async () => {
  await nextTick()
  if (!props.printOpen) (stepHeading.value || dialog.value)?.focus()
}
watch([step, () => props.printOpen], focusHeading)
function onKeydown(event) {
  if (props.printOpen) return
  if (event.key === 'Escape' && canClose.value) {
    event.stopPropagation()
    emit('close')
  }
  if (event.key !== 'Tab') return
  const controls = [...(dialog.value?.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])') || [])]
    .filter(control => control.getClientRects().length > 0)
  const first = controls[0], last = controls.at(-1)
  if (!first) return
  if (event.shiftKey && (document.activeElement === first || !controls.includes(document.activeElement))) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
let restoreFocus
onMounted(() => {
  restoreFocus = document.activeElement
  focusHeading()
  load()
})
onUnmounted(() => {
  if (restoreFocus?.isConnected) restoreFocus.focus()
})
</script>

<template>
  <div v-show="!printOpen" class="delivery-mask" @click.self="canClose && emit('close')">
    <section ref="dialog" class="delivery-desk" role="dialog" aria-modal="true" aria-labelledby="delivery-title" tabindex="-1" @keydown="onKeydown">
      <header class="delivery-header">
        <div>
          <p>Service counter</p>
          <h2 id="delivery-title">Delivery Desk</h2>
        </div>
        <div class="delivery-header-actions">
          <span class="delivery-status" :class="{complete: step === 4}">{{ context?.status || 'Loading job…' }}</span>
          <button type="button" aria-label="Close Delivery Desk" class="delivery-close" :disabled="!canClose" @click="emit('close')">×</button>
        </div>
      </header>

      <ol class="delivery-steps" aria-label="Handover progress">
        <li v-for="(label, index) in steps" :key="label" :aria-current="index === step ? 'step' : undefined" :class="{ complete: index < step || step === 4 }">
          <span class="delivery-marker" aria-hidden="true">{{ index < step ? '✓' : index + 1 }}</span>
          <span>{{ label }}</span>
        </li>
      </ol>

      <div class="delivery-content">
        <div v-if="context" class="delivery-ticket">
          <dl>
            <div><dt>Service job</dt><dd>{{ jobName }}</dd></div>
            <div><dt>Customer</dt><dd>{{ context.customer_name || context.customer || '—' }}</dd></div>
            <div><dt>Device</dt><dd>{{ deviceName }}</dd><dd v-if="context.device?.serial_number" class="delivery-muted">{{ context.device.serial_number }}</dd></div>
          </dl>
          <div class="delivery-amount"><span>{{ submitted ? 'Submitted invoice' : invoice ? 'Draft total' : 'Invoice total' }}</span><strong>{{ formatMoney(invoice?.grand_total) }}</strong></div>
        </div>

        <p v-if="loading" class="delivery-notice" role="status">Loading job and invoice…</p>
        <div v-else-if="loadError" class="delivery-alert" role="alert">
          <p>{{ loadError }}</p><button type="button" class="delivery-button" @click="load">Reload job and invoice</button>
        </div>
        <template v-else-if="context">
          <div v-if="step === 4" class="delivery-receipt" role="status">
            <span class="delivery-done-icon" aria-hidden="true">✓</span>
            <h3 ref="stepHeading" tabindex="-1">Device delivered</h3>
            <p v-if="invoice?.name">Sales Invoice <strong>{{ invoice.name }}</strong></p>
            <p v-else>Ask an authorized colleague to open the linked invoice.</p>
            <p v-if="posts.length">Stock entries submitted <strong>{{ posts.join(', ') }}</strong></p>
            <p v-if="amountDue">Outstanding balance <strong>{{ formatMoney(balance) }}</strong></p>
            <p v-else-if="submitted && balance != null">No outstanding balance.</p>
            <p v-if="paymentReceipt">Payment recorded <strong>{{ paymentReceipt }}</strong></p>
            <button v-if="canCollect && !takingPayment" type="button" class="delivery-button primary" @click="takingPayment = true">Receive payment</button>
            <InvoiceTransactionPanel v-if="takingPayment && invoice" :invoice-name="invoice.name" mode="pay"
              back-label="Back to delivery" @back="takingPayment = false" @busy="paymentBusy = $event" @changed="paymentRecorded" />
          </div>

          <p v-else-if="context.issue || !context.can_write" class="delivery-alert" role="alert">
            {{ context.issue || 'This account needs Service Job write permission to complete handover.' }}
          </p>

          <div v-else-if="step === 0" class="delivery-stage">
            <div class="delivery-stage-head">
              <div>
                <h3 ref="stepHeading" tabindex="-1">{{ invoice ? 'Review the saved invoice' : 'Prepare the invoice' }}</h3>
                <p v-if="invoice">{{ invoice.name }} · {{ submitted ? 'Submitted' : 'Draft' }}</p>
              </div>
              <div v-if="invoice" class="delivery-row-actions">
                <a :href="deskLink('sales-invoice', invoice.name)" target="_blank" rel="noopener">Open in ERPNext ↗</a>
                <button v-if="!submitted && !editing" type="button" class="delivery-button" @click="editing=true">Edit charges</button>
                <button v-if="!editing" type="button" class="delivery-button" @click="load">Reload invoice</button>
              </div>
            </div>
            <CounterCheckout670 v-if="editing && invoice" :invoice-name="invoice.name" draft-only @updated="resumeSaved" @close="editing=false" />
            <div v-else-if="invoice?.items?.length" class="delivery-table-wrap">
              <table class="delivery-table">
                <thead><tr><th scope="col">Invoice line</th><th scope="col">Qty</th><th scope="col">Rate</th><th scope="col">Amount</th></tr></thead>
                <tbody>
                  <tr v-for="(item, index) in invoice.items" :key="index">
                    <td><strong>{{ item.item_name || item.item_code }}</strong><small v-if="item.item_name && item.item_code !== item.item_name">{{ item.item_code }}</small></td>
                    <td>{{ formatQty(item.qty) }}</td><td>{{ formatMoney(item.rate) }}</td><td>{{ formatMoney(item.amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <slot v-if="!invoice" name="invoice" :job-name="jobName" :on-saved="resumeSaved" :on-close="() => emit('close')" />
          </div>

          <div v-else-if="step === 1" class="delivery-stage">
            <div class="delivery-stage-head">
              <div><h3 ref="stepHeading" tabindex="-1">Check spare parts</h3><p v-if="parts?.warehouse">{{ parts.warehouse }}</p></div>
              <button type="button" class="delivery-button" :disabled="loadingParts" @click="loadParts">{{ loadingParts ? 'Checking…' : 'Refresh availability' }}</button>
            </div>
            <p v-if="loadingParts" class="delivery-notice" role="status">Checking Material Requests and available stock…</p>
            <p v-else-if="partsError" class="delivery-alert" role="alert">{{ partsError }}</p>
            <p v-else-if="!parts?.checked" class="delivery-notice">Stock details are restricted for this account. ERPNext checks any stock issue during finalization.</p>
            <template v-else>
              <p v-if="!parts.requests.length" class="delivery-notice">This job has no active parts requests.</p>
              <p v-else-if="submitted && hasBlockingRequests" class="delivery-alert" role="alert">This invoice is already submitted. Ask Stores to resolve the pending parts requests before handover.</p>
              <p v-else-if="partsBlocked" class="delivery-alert" role="alert">Resolve the highlighted stock or request issues, then refresh availability.</p>
              <p v-else-if="parts.items.length" class="delivery-notice">Approved pending quantities can be issued. Any valid draft Stock Entry will be reused.</p>
              <p v-else class="delivery-notice">All linked parts have been issued.</p>
              <ul v-if="parts.requests.length" class="delivery-requests">
                <li v-for="request in parts.requests" :key="request.name">
                  <a :href="deskLink('material-request', request.name)" target="_blank" rel="noopener">{{ request.name }} ↗</a>
                  <span class="delivery-pill" :class="{warning: request.state !== 'issued' && (submitted || request.state !== 'pending')}">{{ requestLabels[request.state] }}</span>
                  <div v-if="request.entries.length" class="delivery-entry-links">
                    <a v-for="entry in request.entries" :key="entry.name" :href="deskLink('stock-entry', entry.name)" target="_blank" rel="noopener">{{ entry.name }} · {{ entry.docstatus === 1 ? 'Submitted' : 'Draft' }} ↗</a>
                  </div>
                </li>
              </ul>
              <div v-if="parts.items.length" class="delivery-table-wrap">
                <table class="delivery-table">
                  <thead><tr><th scope="col">Part</th><th scope="col">Required</th><th scope="col">Available</th><th scope="col">Status</th></tr></thead>
                  <tbody>
                    <tr v-for="item in parts.items" :key="item.item_code">
                      <td><strong>{{ item.item_name || item.item_code }}</strong><small>{{ item.item_code }}</small></td>
                      <td>{{ formatQty(item.required) }} {{ item.uom }}</td><td>{{ formatQty(item.available) }} {{ item.uom }}</td>
                      <td :class="{ 'delivery-stock-warning': item.shortage || item.manual_issue }">
                        <div v-if="item.shortage">Short {{ formatQty(item.shortage) }} {{ item.uom }}</div>
                        <div v-if="item.manual_issue">Issue serial or batch in ERPNext</div>
                        <div v-if="!item.shortage && !item.manual_issue">Available</div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>

          <div v-else-if="step === 2" class="delivery-stage">
            <div class="delivery-stage-head">
              <div><h3 ref="stepHeading" tabindex="-1">Receive payment</h3><p>{{ invoice.name }}</p></div>
              <button v-if="submitted && !takingPayment" type="button" class="delivery-button" @click="load">Refresh balance</button>
            </div>
            <p v-if="!submitted" class="delivery-notice">Submit the invoice and issue approved parts to open payment collection. Device handover is confirmed in the next step.</p>
            <p v-else-if="amountDue" class="delivery-notice">Outstanding balance <strong>{{ formatMoney(balance) }}</strong></p>
            <p v-else-if="balance != null" class="delivery-notice">No outstanding balance.</p>
            <p v-if="paymentReceipt" class="delivery-notice" role="status">Payment recorded <strong>{{ paymentReceipt }}</strong></p>
            <button v-if="canCollect && !takingPayment" type="button" class="delivery-button primary" @click="takingPayment = true">Receive payment</button>
            <p v-else-if="amountDue && !canCollect" class="delivery-notice">A user with Payment Entry create and submit permissions can record payment.</p>
            <InvoiceTransactionPanel v-if="takingPayment" :invoice-name="invoice.name" mode="pay"
              back-label="Back to payment options" @back="takingPayment = false" @busy="paymentBusy = $event" @changed="paymentRecorded" />
            <p v-if="submitError" class="delivery-alert" role="alert">{{ submitError }}</p>
          </div>

          <div v-else class="delivery-stage">
            <div class="delivery-stage-head"><div><h3 ref="stepHeading" tabindex="-1">Confirm device handover</h3><p>{{ invoice.name }} · {{ formatMoney(invoice.grand_total) }}</p></div></div>
            <label class="delivery-consent"><input v-model="consent" type="checkbox" :disabled="submitting" />
              <span>I verified the customer, device, and invoice, and authorize handover.</span>
            </label>
            <label v-if="amountDue" class="delivery-consent"><input v-model="leaveBalance" type="checkbox" :disabled="submitting" />
              <span>Deliver with <strong>{{ formatMoney(balance) }}</strong> still due.</span>
            </label>
            <div v-if="submitError" class="delivery-alert" role="alert">
              <p>{{ submitError }}</p>
              <button type="button" class="delivery-button" @click="goTo(1)">Back to spare parts</button>
              <button type="button" class="delivery-button" @click="goTo(0); load()">Reload invoice status</button>
            </div>
          </div>
        </template>
      </div>

      <footer class="delivery-footer">
        <button v-if="step > 0 && step < 4" type="button" class="delivery-button" :disabled="!canClose" @click="goTo(step - 1)">‹ Back</button>
        <button v-else type="button" class="delivery-button" :disabled="!canClose" @click="emit('close')">Back to Service Jobs</button>
        <button v-if="step === 4 && submitted && !takingPayment" type="button" class="delivery-button primary" @click="emit('print', invoice.name)">Print / Reprint</button>
        <template v-else-if="context?.can_write && !context.issue && !loading && !loadError">
          <button v-if="step === 0 && invoice" type="button" class="delivery-button primary" :disabled="editing" @click="goTo(1)">Check spare parts ›</button>
          <button v-if="step === 1" type="button" class="delivery-button primary" :disabled="loadingParts || !!partsError || !parts || partsBlocked" @click="goTo(2)">Continue to payment ›</button>
          <button v-if="step === 2 && !submitted" type="button" class="delivery-button primary" :disabled="submitting || !invoice?.modified" @click="submitInvoice">
            {{ submitting ? 'Submitting invoice…' : 'Submit invoice' }}
          </button>
          <button v-if="step === 2 && submitted && !takingPayment && balance != null" type="button" class="delivery-button"
            :class="{primary: !amountDue}" @click="goTo(3)">{{ amountDue ? 'Continue with balance due ›' : 'Continue to handover ›' }}</button>
          <button v-if="step === 3" type="button" class="delivery-button primary" :disabled="!canHandover" @click="complete">
            {{ submitting ? 'Recording handover…' : submitError ? 'Retry handover' : 'Deliver & print' }}
          </button>
        </template>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.delivery-mask{position:fixed;inset:0;z-index:200300;display:grid;place-items:center;padding:20px;background:#2a1d15a8;backdrop-filter:blur(5px)}
.delivery-desk{--dd-ink:#35251d;--dd-muted:#745d4b;--dd-rule:#e5d7c8;--dd-accent:#734b32;width:min(1060px,100%);max-height:min(93dvh,920px);display:flex;flex-direction:column;overflow:hidden;background:#fffdf9;border:1px solid #e2ceb9;border-radius:23px;color:var(--dd-ink);box-shadow:0 25px 95px #2a1b1490;font:14px/1.5 system-ui,sans-serif}
.delivery-desk:focus,.delivery-stage h3:focus,.delivery-receipt h3:focus{outline:none}
.delivery-desk button:focus-visible,.delivery-desk a:focus-visible,.delivery-desk input:focus-visible{outline:2px solid #955b36;outline-offset:3px}
.delivery-header{flex:none;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:21px 30px;background:linear-gradient(112deg,#3d2a20,#563d2e);color:#fff8ed}
.delivery-header p{margin:0;color:#e1c6ab;font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
.delivery-header h2{margin:2px 0 0;color:inherit;font:normal clamp(1.7rem,4vw,2.3rem)/1.12 Georgia,serif}
.delivery-header-actions,.delivery-row-actions,.delivery-entry-links{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.delivery-status{padding:5px 10px;border:1px solid #d8b79966;border-radius:30px;background:#fff4e31c;font-size:.76rem;font-weight:700}
.delivery-close{border:1px solid #e1c6ab77;border-radius:50%;width:34px;height:34px;background:none;color:inherit;line-height:1;font-size:24px;cursor:pointer}
.delivery-steps{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:2px;margin:0;padding:0 21px;background:#f6eee3;border-bottom:1px solid var(--dd-rule);list-style:none}
.delivery-steps li{display:flex;align-items:center;gap:8px;padding:12px 8px;border-bottom:3px solid transparent;color:var(--dd-muted);font-size:.78rem;font-weight:650}
.delivery-steps li[aria-current]{border-color:#a06844;color:#59361f;font-weight:800}
.delivery-marker{display:grid;place-items:center;flex:none;width:25px;height:25px;border-radius:50%;border:1px solid #d5bea8;background:#fffaf3;font-size:.73rem}
.delivery-steps li[aria-current] .delivery-marker,.delivery-steps li.complete .delivery-marker{border-color:#7a5036;background:#7a5036;color:#fff9ee}
.delivery-content{min-height:125px;overflow:auto;overscroll-behavior:contain;padding:22px 30px;display:grid;gap:16px}
.delivery-ticket{display:grid;grid-template-columns:minmax(0,1fr) auto;border:1px solid var(--dd-rule);border-radius:14px;background:#f9f1e7}
.delivery-ticket dl{display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:16px;margin:0;padding:14px 17px}
.delivery-ticket dl div{min-width:0}
.delivery-ticket dt,.delivery-amount span{color:var(--dd-muted);font-size:.72rem;font-weight:650}
.delivery-ticket dd{margin:3px 0 0;font-weight:730;overflow-wrap:anywhere}
.delivery-ticket dd.delivery-muted{font-size:.74rem;font-weight:500}
.delivery-amount{display:grid;align-content:center;gap:4px;padding:12px 16px;border-left:1px dashed #cdb79f;text-align:right}
.delivery-amount strong{font-size:1.15rem;font-variant-numeric:tabular-nums;white-space:nowrap}
.delivery-stage{display:grid;gap:12px;min-width:0}
.delivery-stage-head{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.delivery-stage h3,.delivery-receipt h3{margin:0;color:var(--dd-ink);font:normal 1.55rem/1.15 Georgia,serif}
.delivery-stage-head p,.delivery-receipt p{margin:5px 0 0;color:var(--dd-muted);font-size:.84rem}
.delivery-desk a{color:#70442b;font-weight:700;font-size:.78rem;text-underline-offset:3px}
.delivery-notice,.delivery-alert{margin:0;padding:11px 13px;border:1px solid #ebdac6;border-radius:9px;background:#f8f0e3;color:#634732;font-size:.83rem}
.delivery-alert{border-color:#ebc6b8;background:#fff1e9;color:#8b3924}
.delivery-alert p{margin:0 0 7px}
.delivery-alert button+button{margin-left:8px}
.delivery-muted{color:var(--dd-muted);margin:0;font-size:.78rem}
.delivery-requests{display:grid;gap:5px;margin:0;padding:0;list-style:none}
.delivery-requests li{display:flex;align-items:center;flex-wrap:wrap;gap:8px;padding:9px 11px;border:1px solid var(--dd-rule);border-radius:8px;background:#fffbf5}
.delivery-pill{padding:2px 7px;border-radius:20px;background:#eee1d0;color:#60422d;font-size:.72rem;font-weight:700}
.delivery-pill.warning{background:#f7dcd0;color:#813a27}
.delivery-entry-links{margin-left:auto}
.delivery-table-wrap{border:1px solid var(--dd-rule);border-radius:9px;overflow:auto}
.delivery-table{border-collapse:collapse;width:100%;text-align:left;font-size:.82rem}
.delivery-table th,.delivery-table td{padding:10px 12px;vertical-align:top}
.delivery-table th{background:#f5eadd;color:#644831;font-size:.74rem}
.delivery-table tr+tr{border-top:1px solid #eee3d8}
.delivery-table td small{display:block;color:var(--dd-muted);overflow-wrap:anywhere}
.delivery-table td:not(:first-child){font-variant-numeric:tabular-nums}
.delivery-stock-warning{color:#893b26;font-weight:760}
.delivery-consent{display:flex;gap:12px;align-items:flex-start;padding:16px;border:1px solid #dcc7b2;border-radius:12px;background:#faf0e3;font-weight:650;cursor:pointer}
.delivery-consent input{width:18px;height:18px;flex:none;accent-color:var(--dd-accent);margin:2px 0 0}
.delivery-receipt{display:grid;justify-items:center;text-align:center;gap:5px;padding:22px 14px;border:1px dashed #d2bba2;border-radius:13px;background:#fbf3e9}
.delivery-done-icon{display:grid;place-items:center;width:42px;height:42px;margin-bottom:5px;border-radius:50%;background:#ead8c4;color:#633d24;font-size:1.4rem}
.delivery-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;flex:none;padding:12px 30px;border-top:1px solid var(--dd-rule);background:#f9f1e7}
.delivery-button{min-height:36px;padding:7px 12px;border:1px solid #d6c1ab;border-radius:8px;background:#fffbf5;color:#5e412d;font:inherit;font-size:.8rem;font-weight:700;cursor:pointer}
.delivery-button.primary{background:#754b31;border-color:#754b31;color:#fff8ef}
.delivery-button.primary:not(:disabled):hover{background:#613c26}
.delivery-button:disabled,.delivery-close:disabled{opacity:.52;cursor:not-allowed}
@media(max-width:650px){
  .delivery-mask{padding:0}.delivery-desk{width:100%;height:100dvh;max-height:none;border:0;border-radius:0}
  .delivery-header,.delivery-content,.delivery-footer{padding-left:14px;padding-right:14px}
  .delivery-steps{padding:0 6px}.delivery-steps li{flex-direction:column;gap:4px;padding:7px 3px;text-align:center;font-size:.68rem}
  .delivery-ticket{grid-template-columns:1fr}.delivery-ticket dl{grid-template-columns:1fr 1fr;gap:8px;padding:10px 12px}
  .delivery-ticket dl div:last-child{grid-column:1/-1}
  .delivery-amount{display:flex;justify-content:space-between;align-items:center;border-left:0;border-top:1px dashed #cdb79f;padding:7px 12px}
  .delivery-table th,.delivery-table td{padding:7px 8px}
}
</style>
