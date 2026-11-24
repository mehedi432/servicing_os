<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import InvoiceDocument from './InvoiceDocument.vue'
import { INVOICE_PRINT_FORMATS, invoicePrintHtml } from './invoice-print.mjs'
import invoicePaperCss from './invoice-paper.css?raw'

const props = defineProps({
  receipt: Object,
  invoiceName: { type: String, default: '' },
  error: String,
  duplicate: Boolean,
  previewOnly: Boolean,
  draftAction: Boolean,
  actionHeading: String,
  canSubmit: Boolean,
  submitting: Boolean,
  submitError: String,
  submitMessage: String,
})
const emit = defineEmits(['close', 'retry', 'submit'])
const format = ref('a4')
const copy = ref(props.duplicate ? 'duplicate' : 'customer')
const dialog = ref(null)
const paper = ref(null)
const printError = ref('')
const formats = INVOICE_PRINT_FORMATS
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => dialog.value?.close())

const invoice = computed(() => props.receipt?.invoice || props.receipt?.name || props.invoiceName)
const customer = computed(() => props.receipt?.customer_name || props.receipt?.customer || 'Customer')
const draft = computed(() => String(props.receipt?.docstatus) === '0')
const cancelled = computed(() => String(props.receipt?.docstatus) === '2')
const canPrint = computed(() => Boolean(props.receipt) && !props.actionHeading && !props.previewOnly && !draft.value && !cancelled.value)
const heading = computed(() => props.actionHeading || (canPrint.value ? 'Print / Reprint Invoice' : 'Invoice Preview'))

function printInvoice() {
  if (!paper.value || !canPrint.value) return
  printError.value = ''
  const popup = window.open('', '_blank', 'width=980,height=880')
  if (!popup) {
    printError.value = 'Allow pop-ups for this site, then select Print / Reprint again.'
    return
  }
  popup.document.open()
  popup.document.write(invoicePrintHtml(paper.value.$el.outerHTML, invoicePaperCss, format.value))
  popup.document.close()
  popup.focus()
  popup.setTimeout(() => popup.print(), 450)
}
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="invoice-studio" :aria-label="heading" @cancel.prevent="!submitting && emit('close')">
      <header class="invoice-studio-head">
        <div><h2>{{ heading }}</h2><p>{{ invoice }}<template v-if="receipt"> · {{ customer }}</template></p></div>
        <button type="button" autofocus :disabled="submitting" @click="emit('close')">Close</button>
      </header>
      <div v-if="!receipt" class="invoice-studio-load">
        <template v-if="error"><p role="alert">{{ error }}</p><button type="button" @click="emit('retry')">Retry</button></template>
        <p v-else role="status">Loading invoice…</p>
      </div>
      <div v-else class="invoice-studio-content" :class="{ 'invoice-studio-transaction': actionHeading }">
        <aside v-if="!actionHeading" class="invoice-studio-controls" aria-label="Invoice actions">
          <p v-if="submitMessage" role="status">{{ submitMessage }}</p>
          <template v-if="draftAction && draft">
            <button v-if="canSubmit" type="button" class="studio-primary" :disabled="submitting" @click="emit('submit')">
              {{ submitting ? 'Submitting…' : 'Submit Draft Invoice' }}
            </button>
            <p v-else>Sales Invoice submit permission is required.</p>
          </template>
          <p v-if="submitError" role="alert">{{ submitError }}</p>
          <slot name="actions" />
          <div class="invoice-studio-formats" role="group" aria-label="Paper format">
            <button v-for="option in formats" :key="option.id" type="button"
              :aria-pressed="format === option.id" @click="format = option.id">
              <strong>{{ option.label }}</strong><small>{{ option.size }}</small>
            </button>
          </div>
          <label v-if="canPrint">Copy
            <select v-model="copy"><option value="customer">Customer copy</option><option value="duplicate">Duplicate / Reprint</option></select>
          </label>
          <button v-if="canPrint" class="studio-primary" type="button" @click="printInvoice">Print / Reprint</button>
          <p v-if="printError" role="alert">{{ printError }}</p>
        </aside>
        <section class="invoice-studio-preview" :aria-label="actionHeading || 'Invoice preview'" tabindex="0">
          <slot name="workspace">
            <InvoiceDocument ref="paper" :receipt="receipt" :invoice-name="invoiceName" :format="format" :copy="copy" />
          </slot>
        </section>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.invoice-studio{color:#33261e;background:#fffcf6;border:1px solid #e0cbb7;border-radius:17px;padding:0;width:min(1170px,calc(100vw - 24px));max-height:calc(100dvh - 24px);box-shadow:0 22px 94px #2b201660;font:14px/1.4 system-ui,sans-serif}
.invoice-studio::backdrop{background:#30251fb2}
.invoice-studio-head{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 18px;background:#f8efe4;border-bottom:1px solid #e2cfbc}
.invoice-studio-head h2{margin:0;font:1.4rem/1.2 Georgia,serif}.invoice-studio-head p{margin:3px 0 0;color:#6d5140;font-size:12px}
.invoice-studio-content{display:grid;grid-template-columns:190px minmax(0,1fr);max-height:calc(100dvh - 108px)}
.invoice-studio-controls{min-width:0;padding:14px;overflow:auto;border-right:1px solid #e2cfbc;display:grid;align-content:start;gap:11px}
.invoice-studio button,.invoice-studio select{color:#513822;border:1px solid #d6bba0;border-radius:7px;background:#fffaf3;padding:7px 9px;min-height:36px;font:inherit;font-weight:650}
.invoice-studio button{cursor:pointer}.invoice-studio button:disabled{opacity:.55;cursor:default}
.invoice-studio-controls label{display:grid;gap:4px;font-weight:650}
.invoice-studio-controls p{margin:0;font-size:12px}
.invoice-studio-formats{display:grid;gap:6px}.invoice-studio-formats button{text-align:left}
.invoice-studio-formats small{display:block;font-size:11px;font-weight:500}
.invoice-studio-formats button[aria-pressed=true]{background:#efe0ce;border-color:#aa7753}
.invoice-studio .studio-primary{background:#735038;border-color:#735038;color:white}
.invoice-studio-load{padding:16px}
.invoice-studio-preview{container:invoice-preview / inline-size;overflow:auto;padding:18px;background:#f0e7db;min-width:0}
.invoice-studio-transaction{grid-template-columns:minmax(0,1fr)}
@media(max-width:680px){
  .invoice-studio-content{grid-template-columns:minmax(0,1fr);grid-template-rows:auto minmax(0,1fr)}
  .invoice-studio-transaction{grid-template-rows:minmax(0,1fr)}
  .invoice-studio-controls{border-right:0;border-bottom:1px solid #e2cfbc;padding:8px;gap:6px;grid-template-columns:minmax(0,1fr) auto}
  .invoice-studio-formats{grid-column:1/-1;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px}
  .invoice-studio-formats button{font-size:11px;padding:5px}
  .invoice-studio-formats small{display:none}
  .invoice-studio-preview{padding:9px}
}
</style>
