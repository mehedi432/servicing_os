<script setup>
import { nextTick, ref } from 'vue'

defineProps({ heading: { type: String, required: true }, hint: { type: String, required: true }, selected: Boolean })

const split = ref(null)
const details = ref(null)

async function revealProfile() {
  await nextTick()
  if (split.value?.clientWidth && split.value.clientWidth < 800) {
    details.value?.scrollIntoView({ block: 'start' })
    details.value?.focus({ preventScroll: true })
  }
}
defineExpose({ revealProfile })
</script>

<template>
  <div class="party-layout">
    <div ref="split" class="party-split">
      <slot name="directory" />
      <div ref="details" class="party-details" role="region" :aria-label="heading" tabindex="-1">
        <slot v-if="selected" />
        <div v-else class="party-empty">
          <h2>{{ heading }}</h2>
          <p>{{ hint }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.party-layout{container-type:inline-size}
.party-split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,3fr);gap:clamp(12px,1.8vw,21px);align-items:start}
.party-details{min-width:0;scroll-margin-top:75px}
.party-details:focus-visible{outline:2px solid var(--os-accent,#855d43);outline-offset:2px;border-radius:14px}
.party-empty{padding:clamp(24px,6vw,66px) 20px;text-align:center;border:1px solid var(--os-border,#e5d5c4);border-radius:14px;background:var(--os-surface,#fffdf9);color:var(--os-ink,#39291f)}
.party-empty-icon{width:50px;height:50px;display:grid;place-items:center;margin:0 auto 13px;border:1px solid var(--os-border,#e5d5c4);border-radius:13px;background:var(--os-tint,#f3ebe0);color:var(--os-strong,#644229)}
.party-empty h2{margin:0 0 5px;font:1.35rem/1.15 Georgia,serif}
.party-empty p{margin:0;color:var(--os-muted,#674a36);font-size:.84rem}
@container (max-width:799px){.party-split{grid-template-columns:minmax(0,1fr)}}
</style>
