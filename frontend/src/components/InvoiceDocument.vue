<script setup>
import { computed } from 'vue'
import { encodeInvoiceBarcode, encodeInvoiceQr, invoicePrintBrand } from './invoice-print.mjs'

const props = defineProps({
  receipt: { type: Object, required: true },
  invoiceName: { type: String, default: '' },
  format: { type: String, default: 'a4' },
  copy: { type: String, default: 'customer' },
})

const r = computed(() => props.receipt || {})
const draft = computed(() => String(r.value.docstatus) === '0')
const cancelled = computed(() => String(r.value.docstatus) === '2')
const stamp = computed(() => draft.value ? 'Draft' : cancelled.value ? 'Cancelled' : props.copy === 'duplicate' ? 'Duplicate / Reprint' : 'Customer copy')
const financial = computed(() => props.format !== 'delivery')
const title = computed(() => !financial.value ? 'Delivery Note' : r.value.doctype === 'POS Invoice' ? 'POS Invoice' : 'Sales Invoice')
const items = computed(() => Array.isArray(r.value.items) ? r.value.items : [])
const value = (...keys) => keys.map(key => r.value[key]).find(val => val != null && val !== '')
const number = val => val == null || val === '' ? null : Number(val)
const invoice = computed(() => value('invoice', 'name') || props.invoiceName)
const customer = computed(() => value('customer_name', 'customer') || 'Customer')
const brand = computed(() => invoicePrintBrand(r.value))
const currency = computed(() => value('currency') || 'BDT')
const money = val => {
  const amount = Number(val || 0)
  const symbol = currency.value === 'BDT' ? '৳' : currency.value + ' '
  return (amount < 0 ? '−' : '') + symbol + Math.abs(amount).toLocaleString('en-BD', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })
}
const amount = item => number(item.amount) ?? ((number(item.qty) || 0) * (number(item.rate) || 0))
const unit = item => number(item.rate) ?? (Number(item.qty) ? amount(item) / Number(item.qty) : null)
const subtotal = computed(() => number(value('net_total', 'subtotal')) ?? items.value.reduce((sum, item) => sum + amount(item), 0))
const total = computed(() => number(value('print_total', 'grand_total', 'total')) ?? subtotal.value)
const words = computed(() => value('amount_in_words'))
const rounding = computed(() => number(value('print_rounding_adjustment')))
const discountRate = computed(() => number(value('additional_discount_percentage')))
const paymentSchedule = computed(() => {
  const rows = value('payment_schedule') || []
  return rows.length > 1 || rows.some(row => row.label) ? rows : []
})
const hasPaymentTerms = computed(() => !cancelled.value && (
  paymentSchedule.value.length || (draft.value || outstanding.value > 0) && value('due_date')
))
const monthDate = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',
})
const dateLabel = raw => {
  const date = new Date(raw)
  return Number.isNaN(date.valueOf()) ? raw : monthDate.format(date)
}
const discount = computed(() => number(value('discount_amount', 'discount')))
const tax = computed(() => number(value('total_taxes_and_charges', 'tax_amount', 'tax')))
const outstanding = computed(() => number(value('outstanding_amount', 'outstanding')))
const paid = computed(() => number(value('paid_amount', 'paid')) ?? (
  outstanding.value != null && total.value >= 0 ? Math.max(0, total.value - outstanding.value) : null
))
const serials = item => [...new Set([item.serial_no, item.serial_number, item.serial_code, item.serial_numbers, item.serial]
  .flat().filter(Boolean).flatMap(serial => String(serial).split(/[\r\n,]+/)).map(serial => serial.trim()).filter(Boolean))]
const itemName = item => item.item_name || item.description || item.item_code || item.code || 'Item'
const serialGroups = computed(() => items.value.map((item, index) => ({
  label: itemName(item), line: index + 1, values: serials(item),
})).filter(group => group.values.length))
const warranty = item => {
  const days = item.warranty_days ?? item.manual_warranty_days ?? item.warranty_period_days
  return item.warranty_type !== 'No Warranty' && Number(days) > 0 ? days : null
}

const qr = computed(() => encodeInvoiceQr(value('verification_url') || invoice.value))
const barcode = computed(() => encodeInvoiceBarcode(invoice.value, props.format))
</script>

<template>
<article class="invoice-paper" :class="'ip-' + format">
  <header class="ip-masthead">
    <div class="ip-brand">
      <h2>{{ brand.name }}</h2>
      <address v-if="brand.address">{{ brand.address }}</address>
    </div>
    <div class="ip-heading"><h3>{{ title }}</h3><span class="ip-copy">{{ stamp }}</span></div>
  </header>

  <div class="ip-parties">
    <section>
      <span class="ip-label">Bill to</span><strong>{{ customer }}</strong>
      <span v-if="value('customer_mobile', 'customer_phone', 'mobile_no', 'contact_mobile')">{{ value('customer_mobile', 'customer_phone', 'mobile_no', 'contact_mobile') }}</span>
      <template v-if="value('service_job')">
        <span class="ip-job">{{ value('service_job') }}<template v-if="value('service_device')"> · {{ value('service_device') }}</template></span>
      </template>
    </section>
    <dl class="ip-meta">
      <div><dt>Invoice no.</dt><dd class="ip-document-number">{{ invoice || '—' }}</dd></div>
      <div v-if="value('posting_date', 'invoice_date', 'date')"><dt>Issued</dt><dd>{{ dateLabel(value('posting_date', 'invoice_date', 'date')) }}</dd></div>
      <div v-if="financial"><dt>Currency</dt><dd>{{ currency }}</dd></div>
    </dl>
  </div>

  <table class="ip-items" :class="{ 'ip-items-charges': financial }">
    <thead><tr><th scope="col">No.</th><th scope="col">Item / Description</th><th scope="col">Qty</th><th v-if="financial" scope="col">Unit price</th><th v-if="financial" scope="col">Amount</th></tr></thead>
    <tbody>
      <tr v-for="(item, index) in items" :key="index">
        <td>{{ index + 1 }}</td>
        <td><strong>{{ itemName(item) }}</strong><small v-if="warranty(item) != null">Warranty {{ warranty(item) }} days</small></td>
        <td>{{ item.qty }}</td><td v-if="financial">{{ unit(item) == null ? '—' : money(unit(item)) }}</td><td v-if="financial">{{ money(amount(item)) }}</td>
      </tr>
    </tbody>
  </table>

  <div v-if="financial" class="ip-settlement">
    <div class="ip-payment">
      <div v-if="words" class="ip-amount-words">
        <h4>Amount in words</h4>
        <p>{{ words }}</p>
      </div>
      <div v-if="hasPaymentTerms" class="ip-terms">
        <h4>Payment terms</h4>
        <dl v-if="paymentSchedule.length" class="ip-due-schedule">
          <div v-for="(instalment, index) in paymentSchedule" :key="index">
            <dt><span v-if="instalment.label">{{ instalment.label }} · </span>{{ dateLabel(instalment.due_date) }}</dt>
            <dd>{{ money(instalment.amount) }}</dd>
          </div>
        </dl>
        <p v-else>Payment due {{ dateLabel(value('due_date')) }}.</p>
      </div>
    </div>
    <dl class="ip-totals">
      <div><dt>Net subtotal</dt><dd>{{ money(subtotal) }}</dd></div>
      <div v-if="tax"><dt>Tax</dt><dd>{{ money(tax) }}</dd></div>
      <div v-if="rounding"><dt>Rounding adjustment</dt><dd>{{ money(rounding) }}</dd></div>
      <div class="ip-grand"><dt>Grand total</dt><dd>{{ money(total) }}</dd></div>
      <div v-if="discount" class="ip-discount"><dt>Discount already applied<template v-if="discountRate"> ({{ discountRate }}%)</template></dt><dd>{{ money(discount) }}</dd></div>
      <template v-if="!draft && !cancelled">
        <div v-if="paid != null"><dt>Paid</dt><dd>{{ money(paid) }}</dd></div>
        <div v-if="outstanding != null" class="ip-balance"><dt>Outstanding</dt><dd>{{ money(outstanding) }}</dd></div>
      </template>
    </dl>
  </div>
  <div v-else class="ip-acknowledgement">
    <h4>Delivery acknowledgement</h4><p>Received the items listed above in satisfactory visible condition.</p>
    <p>Received by ____________________ &nbsp; Date ____________________</p>
  </div>

  <section v-if="value('service_device_serial') || serialGroups.length" class="ip-trace" aria-label="Serial numbers">
    <h4>Serial numbers</h4>
    <dl class="ip-serial-list">
      <div v-if="value('service_device_serial')">
        <dt>Service device</dt><dd>{{ value('service_device_serial') }}</dd>
      </div>
      <div v-for="group in serialGroups" :key="group.line">
        <dt>{{ group.label }} · Line {{ group.line }}</dt>
        <dd><span v-for="serial in group.values" :key="serial">{{ serial }}</span></dd>
      </div>
    </dl>
  </section>

  <footer class="ip-footer">
    <div class="ip-footer-details">
      <div class="ip-signature">Authorized signature</div>
      <address v-if="brand.contact.length" class="ip-contact">
        <span v-for="detail in brand.contact" :key="detail">{{ detail }}</span>
      </address>
    </div>
    <div class="ip-scan">
      <div class="ip-id">
        <svg v-if="barcode" class="ip-barcode" xmlns="http://www.w3.org/2000/svg"
          :viewBox="`0 0 ${barcode.size} 48`" preserveAspectRatio="none" shape-rendering="crispEdges"
          role="img" :aria-label="`Code 128 barcode for invoice ${invoice}`">
          <rect :width="barcode.size" height="48" fill="white" /><path :d="barcode.path" fill="#000" />
        </svg>
        <span class="ip-document-number">{{ invoice }}</span>
      </div>
      <figure v-if="qr" class="ip-qr">
        <svg xmlns="http://www.w3.org/2000/svg" :viewBox="`0 0 ${qr.size} ${qr.size}`" shape-rendering="crispEdges"
          role="img" :aria-label="`QR code for invoice ${invoice}`">
          <rect :width="qr.size" :height="qr.size" fill="white" /><path :d="qr.path" fill="#000" />
        </svg>
        <figcaption>{{ value('verification_url') ? 'Scan invoice link' : 'Scan invoice number' }}</figcaption>
      </figure>
    </div>
  </footer>
</article>
</template>

<style src="./invoice-paper.css"></style>
