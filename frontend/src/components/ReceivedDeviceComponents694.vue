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
  <section class="sos694-panel" aria-label="Components received with device">
    <header class="sos694-head">
      <div>
        <div class="sos694-eyebrow">DEVICE INTAKE · CUSTOMER PROPERTY</div>
        <h3>Components Received <span>· গ্রাহকের জমা দেওয়া যন্ত্রাংশ</span></h3>
        <p>Record RAM, SSD, HDD, charger, PSU and other items brought with this device. Not repair parts or shop inventory.</p>
      </div>
      <button type="button" class="sos694-add" :disabled="disabled || count >= 60" @click="add">+ Add Component</button>
    </header>
    <div v-if="!count" class="sos694-empty">No individual components recorded. Use <b>+ Add Component</b> for each customer-owned part.</div>
    <div v-else class="sos694-list">
      <article v-for="(part,i) in modelValue" :key="i" class="sos694-entry">
        <div class="sos694-rowtop"><strong>Component {{ i+1 }}</strong><button type="button" class="sos694-remove" :disabled="disabled" @click="remove(i)" :aria-label="'Remove component '+(i+1)">Remove ×</button></div>
        <div class="sos694-fields">
          <label>Type
            <select :value="part.component_type" :disabled="disabled" @change="change(i, 'component_type', $event.target.value)"><option v-for="t in types" :key="t" :value="t">{{ t }}</option></select>
          </label>
          <label>Brand
            <input :value="part.brand" :disabled="disabled" placeholder="e.g. Kingston" maxlength="140" @input="change(i, 'brand', $event.target.value)" />
          </label>
          <label>Capacity / Specification
            <input :value="part.capacity" :disabled="disabled" placeholder="e.g. 16 GB / 512 GB / 650 W" maxlength="140" @input="change(i, 'capacity', $event.target.value)" />
          </label>
          <label>Quantity
            <input type="number" min="0.01" max="1000" step="0.01" :value="part.qty" :disabled="disabled" @input="change(i, 'qty', $event.target.value)" />
          </label>
          <label>Model
            <input :value="part.model" :disabled="disabled" placeholder="Part model" maxlength="140" @input="change(i, 'model', $event.target.value)" />
          </label>
          <label>Serial Number
            <input :value="part.serial_number" :disabled="disabled" placeholder="Optional serial" maxlength="140" @input="change(i, 'serial_number', $event.target.value)" />
          </label>
          <label>Condition at Receive
            <select :value="part.condition_received" :disabled="disabled" @change="change(i, 'condition_received', $event.target.value)"><option v-for="c in conditions" :key="c" :value="c">{{ c }}</option></select>
          </label>
          <label>Remarks
            <input :value="part.remarks" :disabled="disabled" maxlength="500" placeholder="Notes / damage / accessories" @input="change(i, 'remarks', $event.target.value)" />
          </label>
        </div>
      </article>
    </div>
    <footer class="sos694-foot"><span>{{ count }} component{{ count === 1 ? '' : 's' }} recorded</span><span>Saved together with this Service Job</span></footer>
  </section>
</template>

<style scoped>
.sos694-panel,.sos694-panel *{box-sizing:border-box}
.sos694-panel{container-type:inline-size;width:100%;min-width:0;padding:15px;border-radius:13px;border:1px solid #e3d0bf;background:#fffaf5;color:#4c382b;display:flex;flex-direction:column;gap:12px}
.sos694-head{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
.sos694-head h3{font-size:15px;font-weight:750;margin:3px 0 2px;color:#38281f}
.sos694-head h3 span{font-size:11px;font-weight:500;color:#977962}
.sos694-head p{font-size:11px;color:#8a715d;line-height:1.5;margin:4px 0 0}
.sos694-eyebrow{font-size:9px;letter-spacing:.1em;color:#aa8263;font-weight:750}
.sos694-add{background:#78533b;border:1px solid #78533b;color:#fffaf4;border-radius:9px;padding:9px 14px;font-size:12px;font-weight:700;white-space:nowrap;min-height:36px}
.sos694-add:disabled,.sos694-remove:disabled{opacity:.5;cursor:not-allowed}
.sos694-empty{background:#f6ede3;border:1px dashed #dac3b0;border-radius:10px;padding:18px;font-size:12px;color:#866a53}
/* SOS_RECEIVED_COMPONENTS_PRINT_V24: ONE ROW per customer-owned component; scroll on narrow screens. */
.sos694-list{display:flex;flex-direction:column;gap:9px;min-width:0;overflow-x:auto;overflow-y:hidden;padding:1px 0 9px;scrollbar-color:#c6a98e #f8eee4;scrollbar-width:thin}
.sos694-entry{border:1px solid #eadccd;border-radius:11px;background:#fffdf9;padding:10px;min-width:1200px;width:max(100%,1200px);display:grid;grid-template-columns:70px minmax(0,1fr);gap:9px;align-items:end}
.sos694-rowtop{display:flex;align-items:flex-start;justify-content:flex-end;flex-direction:column;gap:6px;min-width:0;margin:0;font-size:11px;min-height:62px}
.sos694-rowtop strong{color:#62452e;white-space:nowrap}
.sos694-remove{color:#a43c32;background:#fff5f1;border:1px solid #e4c9be;border-radius:7px;padding:5px 7px;font-size:10px;white-space:nowrap}
.sos694-fields{display:grid;grid-template-columns:128px 115px 190px 72px 120px 142px 145px minmax(155px,1fr);gap:7px;align-items:end;min-width:0}
.sos694-fields label{display:flex;flex-direction:column;gap:5px;font-size:10px;font-weight:700;color:#745c49;min-width:0;white-space:nowrap}
.sos694-fields input,.sos694-fields select{width:100%;max-width:100%;min-width:0;height:36px;padding:6px 8px;background:#fff;border:1px solid #d9c7b5;border-radius:8px;color:#3c3027;font-size:11px}
.sos694-fields :is(input,select):focus{outline:2px solid #ccb19b;outline-offset:0;border-color:#aa8b72}
.sos694-foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:10px;color:#9b816c}
/* Always keep the eight fields in one horizontal row. Never collapse into two/four rows. */
</style>
