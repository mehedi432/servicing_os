<script setup>
import { onMounted, ref, useId } from 'vue'
defineProps({ title: String, wide: Boolean, busy: Boolean, closeLabel: { type: String, default: 'Close' } })
defineEmits(['close'])
const dialog = ref(null)
const heading = useId()
onMounted(() => dialog.value.showModal())
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="party-dialog" :class="{ 'party-dialog-wide': wide }"
      :aria-labelledby="heading" @cancel.prevent="!busy && $emit('close')" @click.self="!busy && $emit('close')">
      <div class="party-dialog-content">
        <header>
          <h2 :id="heading">{{ title }}</h2>
          <button type="button" :aria-label="closeLabel" :disabled="busy" @click="$emit('close')">×</button>
        </header>
        <slot />
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.party-dialog{width:min(92vw,540px);max-height:88dvh;margin:auto;padding:0;border:1px solid #dfcdbb;border-radius:15px;background:#fffdf9;color:#39291f;box-shadow:0 20px 75px #2a1a1440}
.party-dialog-wide{width:min(92vw,810px)}
.party-dialog::backdrop{background:#2a1a147d}
.party-dialog-content{padding:clamp(14px,3vw,24px)}
.party-dialog header{display:flex;justify-content:space-between;align-items:start;gap:10px;border-bottom:1px solid #e8daca;padding-bottom:12px;margin-bottom:14px}
.party-dialog header h2{overflow-wrap:anywhere;margin:0;font:1.5rem/1.2 Georgia,serif}
.party-dialog header button{width:35px;height:35px;flex:none;border:1px solid #dcc6b1;border-radius:8px;background:#fbf1e7;color:#694832;font-size:1.25rem}
.party-dialog button:focus-visible{outline:2px solid #855d43;outline-offset:2px}
</style>
