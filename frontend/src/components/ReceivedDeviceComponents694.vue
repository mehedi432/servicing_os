<script setup>
import { computed } from 'vue'
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
const types = ['RAM','SSD','HDD','Power Supply','Charger','Adapter','Battery','GPU','CPU','Motherboard','Monitor','Keyboard','Mouse','Cable','Bag','Accessory','Other']
const conditions = ['Not Tested','Working','Faulty','Damaged','Missing Parts','Other']
const count = computed(() => props.modelValue.length)
function add() {
  if (props.disabled || props.modelValue.length >= 60) return
  emit('update:modelValue', [...props.modelValue, { component_type:'RAM', brand:'', model:'', capacity:'', serial_number:'', qty:1, condition_received:'Not Tested', remarks:'' }])
}
function change(i, key, value) {
  if (props.disabled) return
  const next = props.modelValue.map((part, j) => j === i ? { ...part, [key]: value } : part)
  emit('update:modelValue', next)
}
function remove(i) {
  if (!props.disabled) emit('update:modelValue', props.modelValue.filter((_, j) => i !== j))
}
</script>

<template>
  <!-- SOS_DEVICE_COMPONENTS_694: customer-owned items, never shop stock -->
  <section class="intake-custody-panel" data-servicing-component-layout="vue" data-servicing-control-layout="local" aria-label="Components received with device">
    <header class="intake-custody-header">
      <div>
        <div class="intake-custody-eyebrow">DEVICE INTAKE · CUSTOMER PROPERTY</div>
        <h3>Components Received <span>· গ্রাহকের জমা দেওয়া যন্ত্রাংশ</span></h3>
        <p>Record RAM, SSD, HDD, charger, PSU and other items brought with this device. Not repair parts or shop inventory.</p>
      </div>
      <button type="button" class="intake-custody-add" :disabled="disabled || count >= 60" @click="add">+ Add Component</button>
    </header>
    <div v-if="!count" class="intake-custody-empty">No individual components recorded. Use <b>+ Add Component</b> for each customer-owned part.</div>
    <div v-else class="intake-custody-list" tabindex="0" role="region" aria-label="Received component rows">
      <table class="intake-custody-table">
        <colgroup>
          <col class="intake-custody-index-col"><col class="intake-custody-type-col"><col class="intake-custody-brand-col">
          <col class="intake-custody-capacity-col"><col class="intake-custody-quantity-col"><col class="intake-custody-model-col">
          <col class="intake-custody-serial-col"><col class="intake-custody-condition-col"><col class="intake-custody-remarks-col">
          <col class="intake-custody-action-col">
        </colgroup>
        <thead>
          <tr>
            <th scope="col" aria-label="Component number"></th>
            <th scope="col">Type</th><th scope="col">Brand</th><th scope="col">Capacity / Specification</th>
            <th scope="col">Quantity</th><th scope="col">Model</th><th scope="col">Serial Number</th>
            <th scope="col">Condition on receipt</th><th scope="col">Remarks</th><th scope="col" aria-label="Remove"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(part, i) in modelValue" :key="i" class="intake-custody-row">
            <th scope="row" class="intake-custody-index">{{ String(i + 1).padStart(2, '0') }}</th>
            <td>
              <select aria-label="Type" :value="part.component_type" :disabled="disabled" @change="change(i, 'component_type', $event.target.value)">
                <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
              </select>
            </td>
            <td><input aria-label="Brand" :value="part.brand" :disabled="disabled" placeholder="e.g. Kingston" maxlength="140" @input="change(i, 'brand', $event.target.value)" /></td>
            <td><input aria-label="Capacity / Specification" :value="part.capacity" :disabled="disabled" placeholder="e.g. 16 GB / 512 GB" maxlength="140" @input="change(i, 'capacity', $event.target.value)" /></td>
            <td><input aria-label="Quantity" type="number" min="0.01" max="1000" step="0.01" :value="part.qty" :disabled="disabled" @input="change(i, 'qty', $event.target.value)" /></td>
            <td><input aria-label="Model" :value="part.model" :disabled="disabled" placeholder="Part model" maxlength="140" @input="change(i, 'model', $event.target.value)" /></td>
            <td><input aria-label="Serial Number" :value="part.serial_number" :disabled="disabled" placeholder="Optional serial" maxlength="140" @input="change(i, 'serial_number', $event.target.value)" /></td>
            <td>
              <select aria-label="Condition on receipt" :value="part.condition_received" :disabled="disabled" @change="change(i, 'condition_received', $event.target.value)">
                <option v-for="c in conditions" :key="c" :value="c">{{ c }}</option>
              </select>
            </td>
            <td><input aria-label="Remarks" :value="part.remarks" :disabled="disabled" maxlength="500" placeholder="Notes / damage / accessories" @input="change(i, 'remarks', $event.target.value)" /></td>
            <td>
              <button type="button" class="intake-custody-remove" :disabled="disabled" @click="remove(i)" :aria-label="'Remove component ' + (i + 1)" title="Remove component">
                <span aria-hidden="true">×</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="intake-custody-summary"><span>{{ count }} component{{ count === 1 ? '' : 's' }} recorded</span><span>Saved together with this Service Job</span></footer>
  </section>
</template>

<style scoped>
.intake-custody-panel,.intake-custody-panel *{box-sizing:border-box}
.intake-custody-panel{width:100%;min-width:0;padding:15px;border-radius:13px;border:1px solid #e3d0bf;background:#fffaf5;color:#4c382b;display:flex;flex-direction:column;gap:12px}
.intake-custody-header{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
.intake-custody-header h3{font-size:15px;font-weight:750;margin:3px 0 2px;color:#38281f}
.intake-custody-header h3 span{font-size:11px;font-weight:500;color:#977962}
.intake-custody-header p{font-size:11px;color:#8a715d;line-height:1.5;margin:4px 0 0}
.intake-custody-eyebrow{font-size:9px;letter-spacing:.1em;color:#aa8263;font-weight:750}
.intake-custody-add{background:#78533b;border:1px solid #78533b;color:#fffaf4;border-radius:9px;padding:9px 14px;font-size:12px;font-weight:700;white-space:nowrap;min-height:36px}
.intake-custody-add:disabled,.intake-custody-remove:disabled{opacity:.5;cursor:not-allowed}
.intake-custody-empty{background:#f6ede3;border:1px dashed #dac3b0;border-radius:10px;padding:18px;font-size:12px;color:#866a53}
.intake-custody-list{min-width:0;max-width:100%;overflow-x:auto;border:1px solid #e9d9c9;border-radius:9px;background:#fffdf9;scrollbar-color:#bfa288 #f8f0e6}
.intake-custody-table{width:100%;min-width:918px;table-layout:fixed;border-collapse:collapse}
.intake-custody-index-col{width:36px}
.intake-custody-type-col{width:96px}
.intake-custody-brand-col{width:95px}
.intake-custody-capacity-col{width:139px}
.intake-custody-quantity-col{width:64px}
.intake-custody-model-col{width:97px}
.intake-custody-serial-col{width:108px}
.intake-custody-condition-col{width:117px}
.intake-custody-remarks-col{width:125px}
.intake-custody-action-col{width:41px}
.intake-custody-table :is(th,td){padding:6px 4px;vertical-align:middle}
.intake-custody-table thead th{background:#f6ede3;color:#755944;border-bottom:1px solid #e9d9c9;text-align:left;font-size:10px;font-weight:750;line-height:1.25;white-space:nowrap}
.intake-custody-table tbody tr + tr{border-top:1px solid #eee0d2}
.intake-custody-index{background:#fbf3ea;color:#795c46;text-align:center;font-size:11px;font-weight:750;font-variant-numeric:tabular-nums}
.intake-custody-table :is(input,select),.intake-custody-remove{display:block;width:100%;min-width:0;height:34px;min-height:34px;margin:0;border:1px solid #d9c7b5;border-radius:7px;background:#fffdfa;color:#3c3027;font-family:inherit;font-size:11px;line-height:1.25}
.intake-custody-table :is(input,select){padding:0 7px}
.intake-custody-table select{appearance:none;padding-inline-end:18px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='9' height='6' viewBox='0 0 9 6'%3E%3Cpath d='m1 1 3.5 3.5L8 1' fill='none' stroke='%23765741' stroke-width='1.3'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 6px center;text-overflow:ellipsis}
.intake-custody-remove{border-color:#e4c9be;background:#fff5f1;color:#943d34;font-size:16px;font-weight:650;cursor:pointer}
.intake-custody-list:focus-visible,.intake-custody-row :is(input,select,button):focus-visible{outline:2px solid #9f7757;outline-offset:-2px}
.intake-custody-summary{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:10px;color:#9b816c}
</style>
