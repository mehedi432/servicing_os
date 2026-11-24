<script setup>
import { nextTick, ref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import BillingDeliveryCommand700 from './BillingDeliveryCommand700.vue'
import InvoiceRegister from './InvoiceRegister.vue'

const emit = defineEmits(['back', 'create'])
const tabs = [
  { key: 'register', en: 'All invoices', bn: 'সব ইনভয়েস' },
  { key: 'overview', en: 'Invoice overview', bn: 'ইনভয়েস ওভারভিউ' },
  { key: 'dues', en: 'Payments & dues', bn: 'পেমেন্ট ও বকেয়া' },
  { key: 'reports', en: 'Financial reports', bn: 'আর্থিক রিপোর্ট' },
]
const selected = ref('register')
const rail = ref(null)

function moveTab(event, index) {
  let next
  switch (event.key) {
    case 'ArrowRight': next = (index + 1) % tabs.length; break
    case 'ArrowLeft': next = (index + tabs.length - 1) % tabs.length; break
    case 'Home': next = 0; break
    case 'End': next = tabs.length - 1; break
    default: return
  }
  event.preventDefault()
  selected.value = tabs[next].key
  nextTick(() => rail.value?.children[next]?.focus())
}
</script>

<template>
  <section class="counter-invoices" aria-labelledby="counter-invoices-title" data-servicing-control-layout="local">
    <header class="counter-invoices-header">
      <div>
        <button class="counter-invoices-back" type="button" @click="emit('back')">
          <span aria-hidden="true">‹</span> {{ currentLanguage === 'bn' ? 'কাউন্টারে ফিরুন' : 'Back to Counter' }}
        </button>
        <h1 id="counter-invoices-title">{{ currentLanguage === 'bn' ? 'ইনভয়েস' : 'Invoices' }}</h1>
      </div>
      <button class="counter-invoices-create" type="button" @click="emit('create')">
        {{ currentLanguage === 'bn' ? 'ইনভয়েস তৈরি করুন' : 'Create invoice' }}
      </button>
    </header>
    <div ref="rail" class="counter-invoices-tabs" role="tablist" aria-label="Invoice workspace">
      <button v-for="(tab, index) in tabs" :id="'counter-invoice-tab-' + tab.key" :key="tab.key" type="button"
        role="tab" :aria-controls="'counter-invoice-panel-' + tab.key" :aria-selected="selected === tab.key"
        :tabindex="selected === tab.key ? 0 : -1" @click="selected = tab.key" @keydown="moveTab($event, index)">
        {{ currentLanguage === 'bn' ? tab.bn : tab.en }}
      </button>
    </div>
    <div v-for="tab in tabs" v-show="selected === tab.key" :id="'counter-invoice-panel-' + tab.key" :key="tab.key"
      role="tabpanel" :aria-labelledby="'counter-invoice-tab-' + tab.key" tabindex="0">
      <InvoiceRegister v-if="tab.key === 'register'" />
      <BillingDeliveryCommand700 v-else-if="selected === tab.key" :invoice-view="tab.key" @invoice-navigate="selected = $event" />
    </div>
  </section>
</template>

<style scoped>
.counter-invoices{min-width:0;margin-top:18px;color:var(--os-ink,#3c2c25)}
.counter-invoices-header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:12px;margin-bottom:14px}
.counter-invoices-header h1{margin:5px 0 0;font:clamp(1.9rem,4vw,2.6rem)/1.12 Georgia,serif}
.counter-invoices-back{border:0;background:none;padding:5px 0;color:var(--os-strong,#735139);font-size:12px;font-weight:700}
.counter-invoices-back span{font-size:16px;margin-right:4px}
.counter-invoices-create{min-height:38px;border-radius:8px;background:var(--os-accent,#765239);border:1px solid var(--os-accent,#765239);color:#fffaf5;font-size:13px;font-weight:700;padding:8px 14px}
.counter-invoices-tabs{display:flex;gap:4px;overflow-x:auto;margin-bottom:12px;padding:4px;border:1px solid var(--os-border,#e6d7c8);border-radius:10px;background:var(--os-tint,#f5eee5)}
.counter-invoices-tabs button{flex:1 0 auto;min-height:36px;padding:6px 12px;border:1px solid transparent;border-radius:7px;background:none;color:var(--os-muted,#624937);white-space:nowrap;font-size:12px;font-weight:650}
.counter-invoices-tabs button[aria-selected=true]{border-color:var(--os-border,#decbb9);background:var(--os-surface,#fffdf8);color:var(--os-strong,#593922)}
.counter-invoices :is(button,[role=tabpanel]):focus-visible{outline:2px solid var(--os-accent,#9a6d4e);outline-offset:1px}
</style>
