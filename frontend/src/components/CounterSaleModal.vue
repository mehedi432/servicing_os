<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import RetailSales from './RetailSales.vue'
const props = defineProps({open: {type:Boolean,default:false}})
const emit = defineEmits(['close'])
function keydown(e) { if (props.open && e.key === 'Escape') emit('close') }
onMounted(()=>window.addEventListener('keydown',keydown))
onBeforeUnmount(()=>window.removeEventListener('keydown',keydown))
</script>
<template>
  <Teleport to="body">
    <div v-if="open" class="sos-modal-backdrop" role="presentation" @click.self="$emit('close')">
      <section role="dialog" aria-modal="true" aria-label="Counter sale and payment" class="sos-modal-window">
        <div class="sos-modal-bar"><div><b>Counter · New Sale</b><span>Scan, select customer, take payment and print — stay at Counter</span></div>
          <button type="button" class="sos-modal-close" @click="$emit('close')" aria-label="Close checkout">✕ Close</button>
        </div>
        <div class="sos-modal-sales"><RetailSales /></div>
      </section>
    </div>
  </Teleport>
</template>
<style>
.sos-modal-backdrop{position:fixed;inset:0;z-index:19000;background:#231c13b0;display:flex;align-items:center;justify-content:center;padding:12px}
.sos-modal-window{width:min(1510px,100%);height:min(94vh,1050px);background:#f9f6f0;border-radius:18px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 20px 80px #1f170e70}
.sos-modal-bar{padding:14px 20px;background:#fffdf8;border-bottom:1px solid #e5dac7;display:flex;gap:20px;align-items:center;justify-content:space-between;color:#614d34;flex-shrink:0}
.sos-modal-bar div{display:grid;gap:4px}.sos-modal-bar b{font-size:16px}.sos-modal-bar span{font-size:12px;color:#8d785e}
.sos-modal-close{border:1px solid #dfcfb5;border-radius:10px;background:#fff;padding:10px 13px;color:#694f2f;font-weight:700;cursor:pointer}
.sos-modal-sales{flex:1;min-height:0;overflow:auto}.sos-modal-sales .cc-root{min-height:100%;padding:15px}
@media(max-width:700px){.sos-modal-backdrop{padding:0}.sos-modal-window{width:100%;height:100dvh;border-radius:0}.sos-modal-bar{padding:9px 12px}.sos-modal-bar span{display:none}}
@media print{.sos-modal-backdrop,.sos-modal-window,.sos-modal-sales{position:static!important;overflow:visible!important;height:auto!important;max-height:none!important;background:white!important;box-shadow:none!important}.sos-modal-bar{display:none!important}}
</style>
