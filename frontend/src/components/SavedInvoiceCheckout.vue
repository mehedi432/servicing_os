<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  invoiceName: { type: String, required: true },
  invoice: Object,
  error: String,
  actionError: String,
  message: String,
  busy: Boolean,
  mode: String,
})
const emit = defineEmits(['close', 'retry', 'edit', 'pay', 'submit'])
const dialog = ref(null)
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => dialog.value?.close())
const draft = computed(() => Number(props.invoice?.docstatus) === 0)
const cancelled = computed(() => Number(props.invoice?.docstatus) === 2)
const due = computed(() => Number(props.invoice?.outstanding_amount || 0))
const amount = value => new Intl.NumberFormat('en-BD', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
}).format(Number(value || 0))
const money = value => (props.invoice?.currency || 'BDT') + ' ' + amount(value)
const documentStatus = computed(() => {
  if (draft.value) return 'Draft'
  if (cancelled.value) return 'Cancelled'
  return due.value > 0 ? 'Balance due' : 'Submitted'
})
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="saved-checkout" aria-labelledby="saved-checkout-title"
      @cancel.prevent="!busy && emit('close')">
      <header class="saved-checkout-head">
        <div>
          <p>{{ invoice?.doctype || 'Sales Invoice' }}</p>
          <h2 id="saved-checkout-title">{{ invoiceName }}</h2>
        </div>
        <button class="saved-action" type="button" autofocus :disabled="busy" @click="emit('close')">Close</button>
      </header>
      <div class="saved-checkout-body">
        <p v-if="!invoice && !error" class="saved-notice" role="status">Loading saved invoice…</p>
        <div v-if="error" class="saved-alert" role="alert">
          <p>{{ error }}</p><button type="button" class="saved-action" @click="emit('retry')">Reload invoice</button>
        </div>
        <p v-if="message" class="saved-notice" role="status">{{ message }}</p>
        <p v-if="actionError" class="saved-alert" role="alert">{{ actionError }}</p>
        <slot v-if="mode && invoice" name="transaction" />
        <div v-else-if="invoice" class="saved-checkout-grid">
          <section class="saved-lines" aria-label="Customer and items">
            <div class="saved-customer">
              <div><span>Customer</span><strong>{{ invoice.customer_name || invoice.customer }}</strong><small v-if="invoice.customer_mobile">{{ invoice.customer_mobile }}</small></div>
              <div v-if="invoice.service_job"><span>Service Job</span><strong>{{ invoice.service_job }}</strong><small v-if="invoice.service_device_serial">Device serial {{ invoice.service_device_serial }}</small></div>
            </div>
            <h3>Invoice items</h3>
            <div class="saved-table-scroll" role="region" aria-label="Invoice items table" tabindex="0">
              <table>
                <thead><tr><th scope="col">Item</th><th scope="col">Qty</th><th scope="col">Rate</th><th scope="col">Amount</th></tr></thead>
                <tbody>
                  <tr v-for="(item, index) in invoice.items" :key="index">
                    <th scope="row">{{ item.item_name || item.item_code }}
                      <small v-if="item.item_code && item.item_code !== item.item_name">{{ item.item_code }}</small>
                      <small v-if="item.serial_no" class="saved-serial">{{ item.serial_no }}</small>
                    </th>
                    <td>{{ item.qty }}</td><td>{{ amount(item.rate) }}</td><td>{{ amount(item.amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
          <aside class="saved-summary" aria-label="Order summary">
            <div class="saved-summary-title"><h3>Order summary</h3><span class="saved-status" :class="{ 'saved-due': due > 0 && !draft }">{{ documentStatus }}</span></div>
            <dl>
              <div v-if="invoice.posting_date"><dt>Invoice date</dt><dd>{{ invoice.posting_date }}</dd></div>
              <div><dt>Subtotal</dt><dd>{{ money(invoice.net_total) }}</dd></div>
              <div v-if="invoice.discount_amount"><dt>Discount</dt><dd>{{ money(invoice.discount_amount) }}</dd></div>
              <div v-if="invoice.total_taxes_and_charges"><dt>Tax</dt><dd>{{ money(invoice.total_taxes_and_charges) }}</dd></div>
              <div class="saved-total"><dt>Grand total</dt><dd>{{ money(invoice.grand_total) }}</dd></div>
              <template v-if="!draft && !cancelled">
                <div v-if="invoice.paid_amount != null"><dt>Paid</dt><dd>{{ money(invoice.paid_amount) }}</dd></div>
                <div v-if="invoice.outstanding_amount != null" class="saved-balance"><dt>Outstanding</dt><dd>{{ money(due) }}</dd></div>
              </template>
            </dl>
            <div class="saved-actions">
              <button v-if="invoice.can_edit" class="saved-action" type="button" :disabled="busy" @click="emit('edit')">Edit Draft</button>
              <button v-if="invoice.can_submit" class="saved-action saved-primary" type="button" :disabled="busy" @click="emit('submit')">{{ busy ? 'Submitting…' : 'Submit Draft Invoice' }}</button>
              <button v-if="invoice.can_pay" class="saved-action saved-primary" type="button" :disabled="busy" @click="emit('pay')">Receive payment</button>
            </div>
          </aside>
        </div>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.saved-checkout{color:#30251e;background:#fffdf8;border:1px solid #dfcfbe;border-radius:18px;padding:0;width:min(1050px,calc(100vw - 28px));max-height:calc(100dvh - 28px);box-shadow:0 24px 100px #2b201640;font:14px/1.45 system-ui,sans-serif}
.saved-checkout::backdrop{background:#30251fb2}
.saved-checkout-head{position:sticky;top:0;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:19px 24px;border-bottom:1px solid #e9d9c8;background:#f4ece1}
.saved-checkout-head p{margin:0 0 4px;color:#6e4d35;font-size:12px;font-weight:650}
.saved-checkout-head h2{margin:0;font:1.65rem/1.15 Georgia,serif;overflow-wrap:anywhere}
.saved-checkout-body{padding:20px 24px}
.saved-checkout-grid{display:grid;align-items:start;grid-template-columns:minmax(0,1.8fr) minmax(0,1fr);gap:20px}
.saved-customer{display:flex;flex-wrap:wrap;gap:16px 32px;padding:15px 17px;background:#f7efe5;border:1px solid #e9d9c8;border-radius:10px;overflow-wrap:anywhere}
.saved-customer span,.saved-customer small,.saved-lines th small{display:block;color:#694e3d}
.saved-customer span{font-size:12px}.saved-customer strong{display:block;margin:2px 0 1px;font-size:15px}
.saved-lines h3,.saved-summary h3{margin:0;font-size:16px}.saved-lines h3{margin:19px 0 9px}
.saved-table-scroll{overflow:auto;border:1px solid #e9d9c8;border-radius:9px}
.saved-lines table{width:100%;border-collapse:collapse;font-size:13px}
.saved-lines th,.saved-lines td{text-align:right;padding:9px 11px;font-variant-numeric:tabular-nums}
.saved-lines th:first-child{text-align:left;width:53%;overflow-wrap:anywhere}
.saved-lines td{white-space:nowrap}
.saved-lines thead{background:#f3e8dc;color:#553923}
.saved-lines tbody tr+tr{border-top:1px solid #ede1d6}
.saved-lines th small{margin-top:3px;font-weight:500}
.saved-lines .saved-serial{white-space:pre-line;font-family:monospace;color:#422e21}
.saved-summary{padding:16px;background:#f8f1e8;border:1px solid #e9d9c8;border-radius:12px}
.saved-summary-title{display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap}
.saved-status{background:#e9dfd3;color:#513c2d;padding:4px 7px;border-radius:5px;font-size:11px;font-weight:750}
.saved-status.saved-due{background:#f6e2d1;color:#693a20}
.saved-summary dl{margin:11px 0 0}
.saved-summary dl>div{display:flex;align-items:baseline;justify-content:space-between;gap:7px;padding:6px 0}
.saved-summary dt{color:#634b3b}.saved-summary dd{margin:0;text-align:right;font-weight:650;font-variant-numeric:tabular-nums}
.saved-summary .saved-total{border-top:1px solid #dac7b3;margin-top:6px;padding-top:10px;font-size:15px}
.saved-summary .saved-balance{font-weight:750}.saved-actions{display:grid;gap:8px;margin-top:13px}.saved-actions:empty{display:none}
.saved-action{padding:8px 12px;min-height:36px;border:1px solid #cfb59c;border-radius:8px;background:#fffdf8;color:#513923;font:inherit;font-weight:700;cursor:pointer}
.saved-action.saved-primary{color:#fff;background:#765236;border-color:#765236}.saved-action:disabled{opacity:.55;cursor:default}
.saved-notice,.saved-alert{margin:0 0 12px;padding:11px;background:#f5ecdf;border-radius:8px}.saved-alert{color:#8c3221;background:#fff0e9}.saved-alert p{margin:0 0 6px}
@media(max-width:720px){.saved-checkout-grid{grid-template-columns:1fr;gap:14px}.saved-checkout-head,.saved-checkout-body{padding:13px}.saved-lines th,.saved-lines td{padding:8px 6px}}
</style>
