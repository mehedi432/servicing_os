<script setup>
// SOS_UNIFIED_INVOICE_PRINT_684: Sales Invoice -> one premium studio; POS -> legacy compatible renderer.
import CounterPremiumInvoice681 from './CounterPremiumInvoice681.vue'
import InvoicePrint657 from './InvoicePrint657.vue'
const props = defineProps({
  invoiceName: { type: String, required: true },
  doctype: { type: String, default: 'Sales Invoice' },
  duplicate: { type: Boolean, default: false },
  previewOnly: { type: Boolean, default: false },
  checkout: Boolean,
  startPayment: Boolean,
  submitDraft: { type: Boolean, default: false }
})
const emit = defineEmits(['close','submitted'])
</script>
<template>
  <CounterPremiumInvoice681
    v-if="checkout || doctype === 'Sales Invoice'"
    :invoice-name="invoiceName" :doctype="doctype" :checkout="checkout"
    :duplicate="duplicate" :preview-only="previewOnly" :submit-draft="submitDraft" :start-payment="startPayment"
    @close="emit('close')" @submitted="emit('submitted', $event)" />
  <InvoicePrint657
    v-else
    :invoice-name="invoiceName"
    :doctype="doctype"
    :duplicate="duplicate" :preview-only="previewOnly"
    @close="emit('close')" />
</template>
