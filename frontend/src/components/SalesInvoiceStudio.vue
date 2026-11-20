<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import JsBarcode from 'jsbarcode'
import QRCode from 'qrcode'
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
const formats = [
  { id: 'a4', label: 'A4', size: '210 × 297 mm', barcodeLimit: 330 },
  { id: 'a5', label: 'A5', size: '148 × 210 mm', barcodeLimit: 285 },
  { id: 'thermal', label: '80 mm Thermal', size: 'Receipt roll', barcodeLimit: 265 },
  { id: 'delivery', label: 'Delivery Note', size: 'A4 · No prices', barcodeLimit: 330 },
]
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => dialog.value?.close())

const r = computed(() => props.receipt || {})
const draft = computed(() => String(r.value.docstatus) === '0')
const cancelled = computed(() => String(r.value.docstatus) === '2')
const canPrint = computed(() => Boolean(props.receipt) && !props.actionHeading && !props.previewOnly && !draft.value && !cancelled.value)
const heading = computed(() => props.actionHeading || (canPrint.value ? 'Print / Reprint Invoice' : 'Invoice Preview'))
const stamp = computed(() => draft.value ? 'Draft' : cancelled.value ? 'Cancelled' : copy.value === 'duplicate' ? 'Duplicate / Reprint' : 'Customer copy')
const financial = computed(() => format.value !== 'delivery')
const title = computed(() => !financial.value ? 'Delivery Note' : r.value.doctype === 'POS Invoice' ? 'POS Invoice' : 'Sales Invoice')
const items = computed(() => Array.isArray(r.value.items) ? r.value.items : [])
const value = (...keys) => keys.map(key => r.value[key]).find(val => val != null && val !== '')
const number = val => val == null || val === '' ? null : Number(val)
const invoice = computed(() => value('invoice', 'name') || props.invoiceName)
const customer = computed(() => value('customer_name', 'customer') || 'Customer')
const company = computed(() => value('company') || 'AL MODINA COMPUTERS LTD')
const isAlModina = computed(() => /^AL MODINA COMPUTERS (?:LTD|LIMITED)$/i.test(company.value))
const companyAddress = computed(() => value('company_address') || (isAlModina.value ? 'Mawna Chowrasta, Sreepur, Gazipur, Bangladesh' : ''))
const companyPhone = computed(() => value('company_phone') || (isAlModina.value ? '+8801911179837' : ''))
const currency = computed(() => value('currency') || 'BDT')
const money = val => (currency.value === 'BDT' ? '৳' : currency.value + ' ') + Number(val || 0).toLocaleString('en-BD', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
})
const amount = item => number(item.amount) ?? ((number(item.qty) || 0) * (number(item.rate) || 0))
const unit = item => number(item.rate) ?? (Number(item.qty) ? amount(item) / Number(item.qty) : null)
const subtotal = computed(() => number(value('net_total', 'subtotal')) ?? items.value.reduce((sum, item) => sum + amount(item), 0))
const total = computed(() => number(value('grand_total', 'total')) ?? subtotal.value)
const discount = computed(() => number(value('discount_amount', 'discount')))
const tax = computed(() => number(value('total_taxes_and_charges', 'tax_amount', 'tax')))
const paid = computed(() => number(value('paid_amount', 'paid')))
const outstanding = computed(() => number(value('outstanding_amount', 'outstanding')))
const serials = item => [...new Set([item.serial_no, item.serial_number, item.serial_code, item.serial_numbers, item.serial]
  .flat().filter(Boolean).flatMap(serial => String(serial).split(/[\r\n,]+/)).map(serial => serial.trim()).filter(Boolean))]
const warranty = item => {
  const days = item.warranty_days ?? item.manual_warranty_days ?? item.warranty_period_days
  return item.warranty_type !== 'No Warranty' && Number(days) > 0 ? days : null
}

const qrText = computed(() => String(value('verification_url') || invoice.value || '').trim())
const qr = computed(() => {
  if (!qrText.value || qrText.value === '—') return null
  try {
    const { modules } = QRCode.create(qrText.value, { errorCorrectionLevel: 'M' })
    // Four modules of white space are included on every side within the SVG.
    const path = []
    for (let row = 0; row < modules.size; row += 1) {
      for (let col = 0; col < modules.size; col += 1) {
        if (modules.get(row, col)) path.push(`M${col + 4} ${row + 4}h1v1h-1z`)
      }
    }
    return { path: path.join(''), size: modules.size + 8 }
  } catch {
    return null
  }
})

const barcode = computed(() => {
  if (!invoice.value || !/^[ -~]{1,70}$/.test(invoice.value)) return null
  try {
    const encoded = {}
    JsBarcode(encoded, invoice.value, { format: 'CODE128', displayValue: false })
    const modules = encoded.encodings.map(part => part.data).join('')
    const path = []
    for (const match of modules.matchAll(/1+/g)) {
      const width = match[0].length
      path.push(`M${match.index + 12} 0h${width}v48h-${width}z`)
    }
    return { path: path.join(''), size: modules.length + 24 }
  } catch {
    return null
  }
})
const showBarcode = computed(() => barcode.value && barcode.value.size <= formats.find(option => option.id === format.value).barcodeLimit)

function printInvoice() {
  if (!paper.value || !canPrint.value) return
  printError.value = ''
  const popup = window.open('', '_blank', 'width=980,height=880')
  if (!popup) {
    printError.value = 'Allow pop-ups for this site, then select Print / Reprint again.'
    return
  }
  const size = format.value === 'thermal' ? 'auto' : format.value === 'a5' ? 'A5' : 'A4'
  const margin = format.value === 'thermal' ? '0' : '10mm'
  // The same sheet markup and CSS are used in preview and in the print window.
  popup.document.open()
  popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Invoice</title><style>${invoicePaperCss}
@page{size:${size};margin:${margin}} html,body{margin:0;background:white}
body .invoice-paper{margin:0;min-height:0;box-shadow:none;width:100%;max-width:none;padding:0}
body .invoice-paper.ip-thermal{width:76mm;padding:2mm}
@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head><body>${paper.value.outerHTML}</body></html>`)
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
            <article ref="paper" class="invoice-paper" :class="'ip-' + format">
              <header class="ip-masthead">
                <div class="ip-brand">
                  <h2>{{ company }}</h2>
                  <address v-if="companyAddress || companyPhone || value('company_email')">
                    <span v-if="companyAddress">{{ companyAddress }}</span>
                    <span v-if="companyPhone">{{ companyPhone }}</span>
                    <span v-if="value('company_email')">{{ value('company_email') }}</span>
                  </address>
                </div>
                <div class="ip-heading"><span class="ip-copy">{{ stamp }}</span><h3>{{ title }}</h3></div>
              </header>

              <div class="ip-reference">
                <div class="ip-id">
                  <span class="ip-label">Invoice number</span><strong>{{ invoice || '—' }}</strong>
                  <svg v-if="showBarcode" class="ip-barcode" xmlns="http://www.w3.org/2000/svg"
                    :viewBox="`0 0 ${barcode.size} 48`" preserveAspectRatio="none" shape-rendering="crispEdges"
                    role="img" :aria-label="`Code 128 barcode for invoice ${invoice}`">
                    <rect :width="barcode.size" height="48" fill="white" /><path :d="barcode.path" fill="#000" />
                  </svg>
                  <div v-if="value('posting_date', 'invoice_date', 'date')" class="ip-date">{{ value('posting_date', 'invoice_date', 'date') }}</div>
                </div>
                <figure v-if="qr" class="ip-qr">
                  <svg xmlns="http://www.w3.org/2000/svg" :viewBox="`0 0 ${qr.size} ${qr.size}`" shape-rendering="crispEdges"
                    role="img" :aria-label="`QR code for invoice ${invoice}`">
                    <rect :width="qr.size" :height="qr.size" fill="white" /><path :d="qr.path" fill="#000" />
                  </svg>
                  <figcaption>{{ value('verification_url') ? 'Scan invoice link' : 'Scan invoice number' }}</figcaption>
                </figure>
              </div>

              <div class="ip-parties">
                <section><span class="ip-label">Bill to</span><strong>{{ customer }}</strong>
                  <span v-if="value('customer_mobile', 'customer_phone', 'mobile_no', 'contact_mobile')">{{ value('customer_mobile', 'customer_phone', 'mobile_no', 'contact_mobile') }}</span>
                </section>
                <section v-if="value('service_job')">
                  <span class="ip-label">Service Job</span><strong>{{ value('service_job') }}</strong>
                  <span v-if="value('service_device')">{{ value('service_device') }}</span>
                  <div v-if="value('service_device_serial')" class="ip-serial"><span>Device serial</span><strong>{{ value('service_device_serial') }}</strong></div>
                </section>
                <section v-if="financial">
                  <span class="ip-label">Currency</span><strong>{{ currency }}</strong>
                  <span v-if="!draft && !cancelled && outstanding > 0 && value('due_date')">Due {{ value('due_date') }}</span>
                </section>
              </div>

              <table class="ip-items" :class="{ 'ip-items-charges': financial }">
                <thead><tr><th scope="col">No.</th><th scope="col">Item / Description</th><th scope="col">Qty</th><th v-if="financial" scope="col">Unit price</th><th v-if="financial" scope="col">Amount</th></tr></thead>
                <tbody>
                  <tr v-for="(item, index) in items" :key="index">
                    <td>{{ index + 1 }}</td>
                    <td>
                      <strong>{{ item.item_name || item.description || item.item_code || item.code || 'Item' }}</strong>
                      <div v-if="serials(item).length" class="ip-serial"><span>Serial</span><strong v-for="serial in serials(item)" :key="serial">{{ serial }}</strong></div>
                      <small v-if="warranty(item) != null">Warranty {{ warranty(item) }} days</small>
                    </td>
                    <td>{{ item.qty }}</td><td v-if="financial">{{ unit(item) == null ? '—' : money(unit(item)) }}</td><td v-if="financial">{{ money(amount(item)) }}</td>
                  </tr>
                </tbody>
              </table>

              <dl v-if="financial" class="ip-totals">
                <div><dt>Subtotal</dt><dd>{{ money(subtotal) }}</dd></div>
                <div v-if="discount"><dt>Discount</dt><dd>{{ money(discount) }}</dd></div>
                <div v-if="tax"><dt>Tax</dt><dd>{{ money(tax) }}</dd></div>
                <div class="ip-grand"><dt>Grand total</dt><dd>{{ money(total) }}</dd></div>
                <template v-if="!draft && !cancelled">
                  <div v-if="paid != null"><dt>Paid</dt><dd>{{ money(paid) }}</dd></div>
                  <div v-if="outstanding != null" class="ip-due"><dt>Outstanding</dt><dd>{{ money(outstanding) }}</dd></div>
                </template>
              </dl>
              <div v-else class="ip-acknowledgement">
                <strong>Delivery acknowledgement</strong><p>Received the items listed above in satisfactory visible condition.</p>
                <p>Received by ____________________ &nbsp; Date ____________________</p>
              </div>
              <footer class="ip-footer">Retain this document for warranty and service.</footer>
            </article>
          </slot>
        </section>
      </div>
    </dialog>
  </Teleport>
</template>

<style src="./invoice-paper.css"></style>
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
