<script setup>
import { computed, onMounted, ref } from 'vue'
import { servicingApi } from './extensionApi.js'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({ order: { type: Object, required: true } })
const emit = defineEmits(['back', 'busy', 'saved', 'history'])
const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const context = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const warehouse = ref('')
const quantities = ref({})
const selected = computed(() => (context.value?.items || []).filter(line => Number(quantities.value[line.name]) > 0))
const needsDetails = computed(() => selected.value.some(line => line.requires_details))
const canSave = computed(() => !loading.value && !saving.value && warehouse.value && selected.value.length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await servicingApi('inventory_purchase_order', 'get_purchase_order_receiving', { name: props.order.name })
    const defaults = new Set(response.items.map(line => line.warehouse || props.order.warehouse))
    const preferred = defaults.size === 1 ? [...defaults][0] : ''
    warehouse.value = response.warehouses.some(row => row.name === preferred) ? preferred
      : (response.warehouses.length === 1 ? response.warehouses[0].name : '')
    quantities.value = Object.fromEntries(response.items.map(line => [line.name, line.remaining]))
    context.value = response
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save(action) {
  if (!canSave.value) return
  saving.value = true
  error.value = ''
  emit('busy', true)
  try {
    const data = {
      action,
      name: props.order.name,
      expected_modified: context.value.modified,
      warehouse: warehouse.value,
      items: selected.value.map(line => ({
        name: line.name, remaining: line.remaining, qty: Number(quantities.value[line.name]),
      })),
    }
    const receipt = await servicingApi('inventory_purchase_order', 'receive_purchase_order', { data }, true)
    emit('saved', receipt)
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
    emit('busy', false)
  }
}

function submitWhenValid(event, action) {
  event.preventDefault()
  if (event.currentTarget.form.reportValidity()) save(action)
}

onMounted(load)
</script>

<template>
  <section class="inv-desk po-receiving" :aria-label="tr('Receive items', 'পণ্য গ্রহণ')">
    <header class="desk-head">
      <div><h3>{{ tr('Receive items', 'পণ্য গ্রহণ') }}</h3><p>{{ order.name }} · {{ order.supplier_name || order.supplier }}</p></div>
      <button type="button" :disabled="saving" @click="emit('back')">{{ tr('Back to order', 'অর্ডারে ফিরুন') }}</button>
    </header>
    <p v-if="loading" role="status">{{ tr('Checking quantities and warehouses…', 'পরিমাণ ও গুদাম যাচাই হচ্ছে…') }}</p>
    <p v-if="error" class="desk-alert" role="alert">{{ error }}</p>
    <button v-if="error && !loading" type="button" :disabled="saving" @click="load">{{ tr('Refresh receiving details', 'গ্রহণের তথ্য রিফ্রেশ করুন') }}</button>
    <template v-if="context && !loading">
      <p v-if="context.needs_native">{{ tr('Open this order in ERPNext to receive subcontracted or unit-price items.', 'সাবকন্ট্রাক্ট বা ইউনিট-প্রাইস পণ্য গ্রহণের জন্য ইআরপিনেক্সটে অর্ডার খুলুন।') }}</p>
      <div v-else-if="context.has_draft" class="receipt-draft-warning">
        <p>{{ tr('A draft receipt already exists. Open Receipt history to review and complete it.', 'একটি খসড়া রসিদ আছে। রসিদের ইতিহাস থেকে যাচাই ও সম্পন্ন করুন।') }}</p>
        <button v-if="order.can_view_receipts" type="button" @click="emit('history')">{{ tr('View linked receipts', 'সংযুক্ত রসিদ দেখুন') }}</button>
      </div>
      <p v-else-if="!context.items.length">{{ tr('No items remain for receiving.', 'গ্রহণের জন্য কোনো পণ্য বাকি নেই।') }}</p>
      <p v-else-if="!context.warehouses.length">{{ tr('No active warehouse is accessible for this company.', 'এই কোম্পানির কোনো সক্রিয় গুদামে প্রবেশাধিকার নেই।') }}</p>
      <form v-else class="receipt-form" @submit.prevent>
        <label>{{ tr('Destination warehouse', 'গন্তব্য গুদাম') }}
          <select v-model="warehouse" required :disabled="saving">
            <option value="" disabled>{{ tr('Choose a warehouse', 'গুদাম নির্বাচন করুন') }}</option>
            <option v-for="row in context.warehouses" :key="row.name" :value="row.name">{{ row.name }}</option>
          </select>
        </label>
        <p>{{ tr('Enter the quantity delivered today. Use 0 for items you did not receive.', 'আজ গৃহীত পরিমাণ লিখুন। যে পণ্য পাননি সেখানে ০ দিন।') }}</p>
        <div class="desk-table-wrap">
          <table>
            <thead><tr><th>{{ tr('Item', 'পণ্য') }}</th><th>{{ tr('Remaining', 'বাকি') }}</th><th>{{ tr('Receive now', 'এখন গ্রহণ') }}</th></tr></thead>
            <tbody><tr v-for="line in context.items" :key="line.name">
              <td><b>{{ line.item_name || line.item_code }}</b><small>{{ line.item_code }}</small></td>
              <td>{{ line.remaining }} {{ line.uom }}</td>
              <td><input v-model.number="quantities[line.name]" class="receipt-qty" type="number" min="0" :max="line.remaining" step="any" :disabled="saving" :aria-label="tr('Receive now', 'এখন গ্রহণ') + ' · ' + line.item_code" /></td>
            </tr></tbody>
          </table>
        </div>
        <p v-if="needsDetails">{{ tr('Serial, batch, or inspection details are required. Save a draft and complete it in ERPNext.', 'সিরিয়াল, ব্যাচ বা পরিদর্শনের তথ্য প্রয়োজন। খসড়া সেভ করে ইআরপিনেক্সটে সম্পন্ন করুন।') }}</p>
        <p v-else-if="!context.can_submit">{{ tr('Save a draft for a user authorized to submit it in ERPNext.', 'ইআরপিনেক্সটে অনুমোদিত ব্যবহারকারীর সাবমিটের জন্য খসড়া সেভ করুন।') }}</p>
        <p v-else>{{ tr('Submitting the receipt adds the quantities entered to the selected warehouse.', 'রসিদ সাবমিট করলে লিখিত পরিমাণ নির্বাচিত গুদামে যোগ হবে।') }}</p>
        <div class="receipt-actions">
          <button v-if="context.can_submit && !needsDetails" type="submit" class="desk-primary" :disabled="!canSave" @click="submitWhenValid($event, 'receive')">{{ tr('Submit receipt & add stock', 'রসিদ সাবমিট করে স্টক যোগ করুন') }}</button>
          <button type="submit" :disabled="!canSave" @click="submitWhenValid($event, 'draft')">{{ tr('Save receipt draft', 'খসড়া রসিদ সেভ করুন') }}</button>
          <span v-if="saving" role="status">{{ tr('Saving…', 'সেভ হচ্ছে…') }}</span>
        </div>
      </form>
    </template>
  </section>
</template>

<style scoped src="./inventoryDesk.css"></style>
<style scoped>
.po-receiving{margin-top:12px}
.inv-desk .receipt-form{display:grid;align-items:stretch;gap:12px;margin-bottom:0}
.receipt-form .desk-table-wrap{margin:0}
.receipt-qty{width:110px}
.receipt-actions,.receipt-draft-warning{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
</style>
