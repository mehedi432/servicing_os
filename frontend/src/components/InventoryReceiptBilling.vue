<script setup>
import { onMounted, ref } from 'vue'
import PartyDialog from './PartyDialog.vue'
import InvoiceTransactionPanel from './InvoiceTransactionPanel.vue'
import { servicingApi } from './extensionApi.js'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({ receiptName: { type: String, required: true } })
const emit = defineEmits(['close'])
const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const receipt = ref(null)
const invoice = ref(null)
const view = ref('receipt')
const loading = ref(false)
const working = ref(false)
const error = ref('')
const notice = ref('')
const paymentLink = ref('')
const billNo = ref('')
const billDate = ref('')
const label = ref('')

const money = (amount, currency) => new Intl.NumberFormat(currentLanguage.value === 'bn' ? 'bn-BD' : 'en-BD', {
  style: 'currency', currency: currency || 'BDT',
}).format(Number(amount || 0))
const link = (doctype, name) => '/app/' + doctype + '/' + encodeURIComponent(name)
const api = (method, fields, post = false) => servicingApi(
  'inventory_receipt_billing', method, { receipt_name: props.receiptName, ...fields }, post)

async function load() {
  loading.value = true
  error.value = ''
  try {
    receipt.value = await api('get_receipt_billing')
    return true
  } catch (err) {
    error.value = err.message
    return false
  } finally {
    loading.value = false
  }
}

async function openInvoice(name) {
  loading.value = true
  error.value = ''
  try {
    invoice.value = await api('get_linked_invoice', { invoice_name: name })
    view.value = 'invoice'
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function createInvoice() {
  if (working.value) return
  working.value = true
  error.value = ''
  try {
    const result = await api('create_receipt_invoice', { bill_no: billNo.value, bill_date: billDate.value }, true)
    notice.value = result.already_exists ? tr('Opened the existing draft', 'বিদ্যমান খসড়া খোলা হয়েছে')
      : tr('Purchase Invoice draft saved', 'ক্রয় চালানের খসড়া সেভ হয়েছে')
    view.value = 'receipt'
    await load()
    await openInvoice(result.name)
  } catch (err) {
    error.value = err.message
  } finally {
    working.value = false
  }
}

async function submitInvoice() {
  if (working.value || !invoice.value?.can_submit) return
  if (!window.confirm(tr('Submit this Purchase Invoice and record the supplier payable?', 'ক্রয় চালান সাবমিট করে সরবরাহকারীর পাওনা রেকর্ড করবেন?'))) return
  working.value = true
  error.value = ''
  const name = invoice.value.name
  try {
    await api('submit_receipt_invoice', { invoice_name: name, expected_modified: invoice.value.modified }, true)
    notice.value = tr('Purchase Invoice submitted', 'ক্রয় চালান সাবমিট হয়েছে')
    view.value = 'receipt'
    invoice.value = null
    await load()
    await openInvoice(name)
  } catch (err) {
    error.value = err.message
  } finally {
    working.value = false
  }
}

function choosePayment(row) {
  label.value = row.name
  error.value = ''
  view.value = 'payment'
}

async function paymentRecorded(result) {
  const name = label.value
  notice.value = tr('Supplier payment recorded', 'সরবরাহকারীর পেমেন্ট রেকর্ড হয়েছে')
  paymentLink.value = result.payment_entry
  invoice.value = null
  view.value = 'receipt'
  await load()
  await openInvoice(name)
}

function backToReceipt() {
  view.value = 'receipt'
  error.value = ''
}

onMounted(load)
</script>

<template>
  <PartyDialog :title="tr('Invoice & payment', 'চালান ও পেমেন্ট') + ' · ' + receiptName" wide :busy="working"
    :close-label="tr('Close', 'বন্ধ করুন')" @close="emit('close')">
    <section class="inv-desk receipt-billing">
      <header class="desk-head">
        <div>
          <h3>{{ receipt?.supplier || receiptName }}</h3>
          <p v-if="receipt">{{ [receipt.status, receipt.posting_date].filter(Boolean).join(' · ') }}</p>
        </div>
        <a class="desk-btn" :href="link('purchase-receipt',receiptName)" target="_blank" rel="noopener">{{ tr('Open receipt in ERPNext', 'ইআরপিনেক্সটে রসিদ খুলুন') }}</a>
      </header>
      <p v-if="notice" class="desk-success" role="status">{{ notice }}<template v-if="paymentLink"> · <a :href="link('payment-entry',paymentLink)" target="_blank" rel="noopener">{{ paymentLink }}</a></template></p>
      <p v-if="error" class="desk-alert" role="alert">{{ error }}</p>
      <button v-if="!receipt && error" type="button" @click="load">{{ tr('Retry', 'আবার চেষ্টা করুন') }}</button>
      <p v-if="loading" role="status">{{ tr('Loading…', 'লোড হচ্ছে…') }}</p>

      <template v-else-if="receipt && view === 'receipt'">
        <div class="billing-heading">
          <div><h3>{{ tr('Linked Purchase Invoices', 'সংযুক্ত ক্রয় চালান') }}</h3><p>{{ tr('Review supplier bills and outstanding amounts for this receipt.', 'এই রসিদের সরবরাহকারীর বিল ও বকেয়া দেখুন।') }}</p></div>
          <button v-if="receipt.can_bill && !receipt.invoices.some(row => row.docstatus === 0)" type="button" class="desk-primary" @click="view = 'create'; error = ''">{{ tr('Create Purchase Invoice', 'ক্রয় চালান তৈরি করুন') }}</button>
        </div>
        <p v-if="!receipt.can_read_invoices">{{ tr('Purchase Invoice read permission is required.', 'ক্রয় চালান দেখার অনুমতি প্রয়োজন।') }}</p>
        <p v-else-if="!receipt.invoices.length">{{ tr('No Purchase Invoices are linked to this receipt.', 'এই রসিদের সঙ্গে কোনো ক্রয় চালান সংযুক্ত নেই।') }}</p>
        <div v-else class="desk-table-wrap">
          <table>
            <thead><tr><th>{{ tr('Invoice', 'চালান') }}</th><th>{{ tr('Status', 'অবস্থা') }}</th><th>{{ tr('Total', 'মোট') }}</th><th>{{ tr('Outstanding', 'বকেয়া') }}</th><th>{{ tr('Action', 'করণীয়') }}</th></tr></thead>
            <tbody><tr v-for="row in receipt.invoices" :key="row.name">
              <td><button type="button" class="billing-link" @click="openInvoice(row.name)">{{ row.name }}</button><small v-if="row.bill_no">{{ row.bill_no }}</small></td>
              <td>{{ row.status }}</td><td>{{ money(row.rounded_total || row.grand_total, row.currency) }}</td>
              <td>{{ row.docstatus === 1 ? money(row.outstanding_amount, row.party_account_currency || row.currency) : '—' }}</td>
              <td><button v-if="row.can_pay" type="button" class="desk-primary" @click="choosePayment(row)">{{ tr('Pay Supplier', 'সরবরাহকারীকে পেমেন্ট') }}</button>
                <button v-else type="button" @click="openInvoice(row.name)">{{ row.docstatus === 0 ? tr('Review draft', 'খসড়া দেখুন') : tr('View invoice', 'চালান দেখুন') }}</button></td>
            </tr></tbody>
          </table>
        </div>
        <p v-if="receipt.docstatus === 0">{{ tr('Submit the receipt before creating its Purchase Invoice.', 'ক্রয় চালান তৈরির আগে রসিদ সাবমিট করুন।') }}</p>
        <p v-else-if="receipt.is_return">{{ tr('Open the return receipt in ERPNext to review any supplier credit note.', 'সরবরাহকারীর ক্রেডিট নোটের জন্য ইআরপিনেক্সটে রিটার্ন রসিদ খুলুন।') }}</p>
      </template>

      <template v-else-if="receipt && view === 'create'">
        <p>{{ tr('ERPNext carries the unbilled items and rates into the draft. Review it before submitting.', 'ইআরপিনেক্সট বিল না হওয়া পণ্য ও মূল্য খসড়ায় নিয়ে আসবে। সাবমিটের আগে যাচাই করুন।') }}</p>
        <form class="billing-fields" @submit.prevent="createInvoice">
          <label>{{ tr('Supplier invoice number', 'সরবরাহকারীর চালান নম্বর') }}<input v-model.trim="billNo" maxlength="140" :disabled="working" /></label>
          <label>{{ tr('Supplier invoice date', 'সরবরাহকারীর চালানের তারিখ') }}<input v-model="billDate" type="date" :max="receipt.today" :disabled="working" /></label>
          <div class="billing-actions">
            <button type="button" :disabled="working" @click="backToReceipt">{{ tr('Back to receipt', 'রসিদে ফিরুন') }}</button>
            <button type="submit" class="desk-primary" :disabled="working">{{ tr('Save invoice draft', 'চালানের খসড়া সেভ করুন') }}</button>
          </div>
        </form>
      </template>

      <template v-else-if="receipt && invoice && view === 'invoice'">
        <div class="billing-heading">
          <div>
            <h3>{{ invoice.name }} · {{ invoice.status }}</h3>
            <p>{{ [invoice.bill_no, invoice.bill_date].filter(Boolean).join(' · ') }}</p>
            <p v-if="invoice.due_date">{{ tr('Due', 'পরিশোধের তারিখ') }} {{ invoice.due_date }}</p>
          </div>
          <a class="desk-btn" :href="link('purchase-invoice',invoice.name)" target="_blank" rel="noopener">{{ tr('Open invoice in ERPNext', 'ইআরপিনেক্সটে চালান খুলুন') }}</a>
        </div>
        <div class="desk-table-wrap">
          <table>
            <thead><tr><th>{{ tr('Item', 'পণ্য') }}</th><th>{{ tr('Quantity', 'পরিমাণ') }}</th><th>{{ tr('Rate', 'মূল্য') }}</th><th>{{ tr('Amount', 'টাকা') }}</th></tr></thead>
            <tbody><tr v-for="row in invoice.items" :key="row.name"><td>{{ row.item }}</td><td>{{ row.qty }} {{ row.uom }}</td>
              <td>{{ money(row.rate, invoice.currency) }}</td><td>{{ money(row.amount, invoice.currency) }}</td></tr></tbody>
          </table>
        </div>
        <div class="billing-totals">
          <strong>{{ tr('Invoice total', 'চালানের মোট') }} {{ money(invoice.total, invoice.currency) }}</strong>
          <strong v-if="invoice.docstatus === 1">{{ tr('Outstanding', 'বকেয়া') }} {{ money(invoice.outstanding, invoice.outstanding_currency || invoice.currency) }}</strong>
        </div>
        <p v-if="invoice.docstatus === 0 && !invoice.can_submit">{{ tr('Open this draft in ERPNext for approval or editing.', 'অনুমোদন বা সম্পাদনার জন্য ইআরপিনেক্সটে খসড়াটি খুলুন।') }}</p>
        <div class="billing-actions">
          <button type="button" :disabled="working" @click="backToReceipt">{{ tr('Back to receipt', 'রসিদে ফিরুন') }}</button>
          <button v-if="invoice.can_submit" type="button" class="desk-primary" :disabled="working" @click="submitInvoice">{{ tr('Submit Purchase Invoice', 'ক্রয় চালান সাবমিট করুন') }}</button>
          <button v-if="receipt.invoices.some(row => row.name === invoice.name && row.can_pay)" type="button" class="desk-primary" @click="choosePayment(invoice)">{{ tr('Pay Supplier', 'সরবরাহকারীকে পেমেন্ট') }}</button>
        </div>
      </template>

      <template v-else-if="view === 'payment'">
        <p>{{ tr('Record a payment you have already made to the supplier.', 'সরবরাহকারীকে ইতিমধ্যে করা পেমেন্ট রেকর্ড করুন।') }}</p>
        <InvoiceTransactionPanel :key="label" mode="payment" :invoice-name="label" :purchase-receipt="receiptName"
          :back-label="tr('Back to receipt', 'রসিদে ফিরুন')" @back="backToReceipt" @busy="working = $event" @changed="paymentRecorded" />
        <p class="billing-native"><a :href="link('purchase-invoice',label)" target="_blank" rel="noopener">{{ tr('Open invoice in ERPNext for other payment options', 'অন্যান্য পেমেন্ট পদ্ধতির জন্য ইআরপিনেক্সটে চালান খুলুন') }}</a></p>
      </template>
    </section>
  </PartyDialog>
</template>

<style scoped src="./inventoryDesk.css"></style>
<style scoped>
.receipt-billing { display:grid;gap:12px }
.receipt-billing .desk-head { margin-bottom:0 }
.receipt-billing :is(.billing-heading,.billing-totals,.billing-actions) { display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap }
.receipt-billing .billing-fields { display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr));align-items:stretch;margin:0 }
.billing-fields .billing-actions { grid-column:1/-1 }
.receipt-billing .billing-totals { padding:10px 12px;background:var(--os-tint,#f5ebe0);border-radius:8px }
.inv-desk td .billing-link { border:0;padding:0;min-height:26px;text-align:left;text-decoration:underline;white-space:normal }
.receipt-billing :is(p,td) { overflow-wrap:anywhere }
</style>
