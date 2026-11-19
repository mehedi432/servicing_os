<script setup>
// SOS_UNIFIED_INVOICE_PRINT_684: Sales Invoice -> one premium studio; POS -> legacy compatible renderer.
import CounterPremiumInvoice681 from './CounterPremiumInvoice681.vue'
import InvoicePrint657 from './InvoicePrint657.vue'
const props = defineProps({
  invoiceName: { type: String, required: true },
  doctype: { type: String, default: 'Sales Invoice' },
  duplicate: { type: Boolean, default: false }
})
const emit = defineEmits(['close'])
</script>
<template>
  <CounterPremiumInvoice681
    v-if="doctype === 'Sales Invoice'"
    :invoice-name="invoiceName"
    :duplicate="duplicate"
    @close="emit('close')" />
  <InvoicePrint657
    v-else
    :invoice-name="invoiceName"
    :doctype="doctype"
    :duplicate="duplicate"
    @close="emit('close')" />
</template>
