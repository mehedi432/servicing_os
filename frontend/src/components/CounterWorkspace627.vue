<script setup>
// SOS_634_COUNTER_LIVE_KPIS: actual KPIs embedded in Counter tabs.
import CounterLiveCards634 from './CounterLiveCards634.vue'
// SERVICING_COUNTER_TABS_627B: text tabs only; original Receive Device lives in App.vue.
import { computed, ref } from 'vue'
import ServiceJobSticker629 from './ServiceJobSticker629.vue'
import RetailSales from './RetailSales.vue'
import ServiceJobsWorkspace from './ServiceJobsWorkspace.vue'
import RepairManagement from './RepairManagement.vue'
import UsedLaptopWorkspace from './UsedLaptopWorkspace.vue'
import StockManagement from './StockManagement.vue'
import StockQuickAdd from './StockQuickAdd.vue'

const sos629ShowSticker = ref(false)
const props = defineProps({ tab: { type: String, default: 'receive' } })
const emit = defineEmits(['select'])
const tabs = [
  { id: 'receive', label: 'Receive Device', hint: 'Original intake form and receipt printing' },
  { id: 'sale', label: 'New Sale', hint: 'Products, customer, cash payment and receipt' },
  { id: 'repairs', label: 'Repair Jobs', hint: 'Job status, technician and work progress' },
  { id: 'delivery', label: 'Billing & Delivery', hint: 'Repair bills, collections and delivery' },
  { id: 'used', label: 'Used Laptops', hint: 'Buy, inspect, refurbish and sell' },
  { id: 'stock', label: 'Stock & Items', hint: 'Items, quantities and stock receiving' },
]
const selected = computed(() => tabs.find(t => t.id === props.tab) || tabs[0])
function choose(id) {
  if (tabs.some(t => t.id === id)) emit('select', id)
}
function keyTabs(e, index) {
  if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) return
  e.preventDefault()
  let next = index
  if (e.key === 'ArrowRight') next = (index + 1) % tabs.length
  if (e.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length
  if (e.key === 'Home') next = 0
  if (e.key === 'End') next = tabs.length - 1
  choose(tabs[next].id)
  const nav = e.currentTarget?.closest('[role="tablist"]')
  nav?.querySelectorAll('[role="tab"]')?.[next]?.focus()
}
</script>

<template>
  <div class="sos627-workspace sos629-counter" :class="{ 'is-other': tab !== 'receive' }">
    <div class="sos627-toolbar">
      <div class="sos627-kicker">
        <strong>Counter</strong>
        <span>Choose a task</span>
      </div>
      <nav class="sos627-tabs" role="tablist" aria-label="Counter tasks">
        <button
          v-for="(item, index) in tabs"
          :key="item.id"
          class="sos627-tab"
          :class="{ active: tab === item.id }"
          role="tab"
          type="button"
          :aria-selected="tab === item.id"
          :aria-label="item.label"
          :tabindex="tab === item.id ? 0 : -1"
          @click="choose(item.id)"
          @keydown="keyTabs($event, index)"
        >{{ item.label }}</button>
      </nav>
    </div>
    <!-- SOS_QR_STICKER_UI_629: Non-invasive sticker launcher, intake remains in App.vue. -->
    <div v-if="tab === 'receive'" class="sos629-receive-tools">
      <button type="button" class="sos629-sticker-button" @click="sos629ShowSticker = true">Print QR Device Sticker</button>
    </div>
    <!-- SOS_634_COUNTER_LIVE_KPIS: Read-only real-time counters. -->
    <CounterLiveCards634 />
    <!-- Keep the original Service Receive DOM completely untouched in App.vue. -->
    <div v-if="tab === 'receive'" class="sos627-receive-target" role="status">
      <span class="sos627-visually-hidden">The original Receive Device form follows below.</span>
    </div>
    <div v-else class="sos627-content">
      <div class="sos627-context">
        <strong>{{ selected.label }}</strong>
        <span>{{ selected.hint }}</span>
      </div>
      <section v-if="tab === 'sale'" class="sos627-panel" aria-label="Counter new sale">
        <RetailSales />
      </section>
      <section v-else-if="tab === 'repairs'" class="sos627-panel" aria-label="Counter repair jobs">
        <ServiceJobsWorkspace @receive="choose('receive')" @manage="choose('delivery')" />
      </section>
      <section v-else-if="tab === 'delivery'" class="sos627-panel" aria-label="Counter billing and delivery">
        <RepairManagement />
      </section>
      <section v-else-if="tab === 'used'" class="sos627-panel" aria-label="Counter used laptops">
        <UsedLaptopWorkspace />
      </section>
      <section v-else-if="tab === 'stock'" class="sos627-panel" aria-label="Counter inventory and items">
        <div class="sos627-stockhead">
          <div><strong>Stock & Items</strong><span>Find products or receive new stock</span></div>
          <StockQuickAdd />
        </div>
        <StockManagement />
      </section>
    </div>
  </div>
  <ServiceJobSticker629 v-if="sos629ShowSticker" @close="sos629ShowSticker = false" />
</template>

<style>
/* Minimal, text-only Counter tabs.  Scoped via unique prefixes. */
.sos627-workspace{--sos627-accent:#6e4f33;--sos627-ink:#312b25;--sos627-muted:#847563;--sos627-edge:#e6dcd0;width:100%;min-width:0;margin:5px 0 17px;font-family:inherit;color:var(--sos627-ink)}
.sos627-workspace *{box-sizing:border-box}
.sos627-toolbar{display:flex;align-items:center;gap:18px;justify-content:space-between;padding:11px 13px;background:#fffefa;border:1px solid var(--sos627-edge);border-radius:15px;box-shadow:0 2px 12px rgba(68,48,25,.035);min-width:0}
.sos627-kicker{min-width:91px;display:flex;flex-direction:column;gap:2px;padding:2px 4px;white-space:nowrap}
.sos627-kicker strong{font-size:13px;letter-spacing:-.01em;font-weight:800}
.sos627-kicker span{font-size:10px;color:var(--sos627-muted)}
.sos627-tabs{display:flex;gap:5px;align-items:center;max-width:100%;min-width:0;overflow-x:auto;padding:3px;scrollbar-width:thin;scroll-behavior:smooth}
.sos627-tab{appearance:none;min-height:47px;flex-shrink:0;padding:11px 15px;border:1px solid transparent;border-radius:10px;background:transparent;color:#655b50;font-size:13px;font-weight:750;line-height:1.25;white-space:nowrap;cursor:pointer;transition:background .15s,border-color .15s,color .15s,box-shadow .15s;font-family:inherit}
.sos627-tab:hover{border-color:#e1d3c1;background:#f5f0e8;color:#513a25}
.sos627-tab.active{border-color:var(--sos627-accent);background:var(--sos627-accent);color:#fff;box-shadow:0 3px 9px rgba(86,57,29,.12)}
.sos627-tab:focus-visible{outline:3px solid #b38a57;outline-offset:2px}
.sos627-content{min-width:0;padding:18px 0 0}
.sos627-context{display:flex;align-items:baseline;gap:15px;flex-wrap:wrap;margin:0 0 13px;padding:0 3px}
.sos627-context strong{font-size:18px;font-weight:800}
.sos627-context span{font-size:12px;color:var(--sos627-muted)}
.sos627-panel{min-height:290px;min-width:0;width:100%}
.sos627-panel > *{max-width:100%}
.sos627-stockhead{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;border:1px solid var(--sos627-edge);background:#fffefa;border-radius:13px;padding:12px 15px;margin-bottom:13px}
.sos627-stockhead>div:first-child{display:flex;flex-direction:column;gap:3px}.sos627-stockhead strong{font-size:14px}.sos627-stockhead span{font-size:11px;color:var(--sos627-muted)}
.sos627-receive-target{height:0;overflow:hidden}
.sos627-visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
/* All original Counter children (including its form) remain untouched on Receive Device. */
.sos627-counter-root:has(> .sos627-workspace.is-other)>:not(.sos627-workspace){display:none!important}
/* Remove only the redundant old operation-choice strip, not the intake form. */
.sos627-counter-root .sos627-old-operations{display:none!important}
/* Preserve 6.27 behavior for the known obsolete disabled checkout preview. */
.sos627-counter-root .sos627-old-checkout-preview{display:none!important}
.sos627-counter-root:not(:has(> .sos627-workspace.is-other))>.grid:has(> .sos627-old-checkout-preview)>section:first-child{grid-column:1/-1!important}
@media(max-width:1160px){.sos627-toolbar{align-items:stretch;flex-direction:column;gap:8px}.sos627-kicker{flex-direction:row;gap:9px;align-items:baseline}.sos627-tabs{width:100%}}
@media(max-width:680px){.sos627-workspace{margin:0 0 12px}.sos627-toolbar{padding:10px 9px;border-radius:11px}.sos627-tab{min-height:46px;padding:10px 13px;font-size:12px}.sos627-content{padding-top:13px}.sos627-context strong{font-size:16px}.sos627-context span{font-size:11px}}
@media print{.sos627-toolbar,.sos627-context{display:none!important}.sos627-workspace{margin:0}.sos627-content{padding:0}}
</style>

<style>
/* SOS_COUNTER_REFINEMENT_629 — text-only, accessible, and form-safe. */
.sos627-workspace.sos629-counter{--sos629-ink:#1f3038;--sos629-line:#dce3e2;--sos629-gold:#b99563;--sos629-navy:#203743;color:var(--sos629-ink)}
.sos629-counter .sos627-toolbar{background:linear-gradient(118deg,#fff 0%,#f6f9f8 100%);border:1px solid #e0e7e5;border-radius:18px;box-shadow:0 8px 28px #1c394008;padding:15px 16px;gap:22px;position:relative}
.sos629-counter .sos627-toolbar:before{content:"";position:absolute;left:15px;top:16px;bottom:16px;width:3px;border-radius:4px;background:var(--sos629-gold)}
.sos629-counter .sos627-kicker{padding-left:13px;min-width:117px}
.sos629-counter .sos627-kicker strong{color:var(--sos629-ink);font-size:15px;letter-spacing:-.025em}
.sos629-counter .sos627-kicker span{color:#718087;font-size:11px}
.sos629-counter .sos627-tabs{border:1px solid #e4ebe9;border-radius:13px;background:#edf2f1;padding:4px;gap:3px}
.sos629-counter .sos627-tab{height:48px;min-height:48px;border-radius:10px;padding:12px 16px;color:#475b65;font-size:13px;letter-spacing:-.015em;font-weight:760;border:1px solid transparent;position:relative}
.sos629-counter .sos627-tab:hover{background:#fff9f1;border-color:#e0d3c0;color:#263d48}
.sos629-counter .sos627-tab.active{background:#203844;color:#fff;border-color:#203844;box-shadow:0 3px 12px #20384422}
.sos629-counter .sos627-tab.active:after{content:"";position:absolute;bottom:7px;left:25%;right:25%;height:2px;border-radius:1px;background:#d8b17b}
.sos629-counter .sos627-tab:focus-visible{outline:3px solid #c0a074;outline-offset:2px}
.sos629-counter .sos627-context{padding:3px 8px 9px;border-bottom:1px solid #e6ebe9}
.sos629-counter .sos627-context strong{color:#253a44;font-size:21px;letter-spacing:-.03em}
.sos629-counter .sos627-context span{font-size:12px;color:#77858c}
.sos629-counter .sos629-receive-tools{display:flex;justify-content:flex-end;padding:10px 2px 3px}
.sos629-counter .sos629-sticker-button{background:#fff;color:#203844;border:1px solid #bccbc8;padding:12px 19px;border-radius:11px;min-height:45px;font-size:13px;font-weight:800;cursor:pointer;box-shadow:0 3px 11px #1c39400a}
.sos629-counter .sos629-sticker-button:hover{background:#f2f7f6;border-color:#b99563}
.sos629-counter .sos629-sticker-button:focus-visible{outline:3px solid #b99563;outline-offset:2px}
@media(max-width:760px){.sos629-counter .sos627-toolbar{padding:12px;border-radius:14px;gap:12px}.sos629-counter .sos627-kicker{flex-direction:row;gap:8px}.sos629-counter .sos627-tabs{scroll-snap-type:x mandatory}.sos629-counter .sos627-tab{scroll-snap-align:start;min-height:48px;padding:11px 14px}}
</style>

<style>
/* SOS_IVORY_STOCK_633 — ivory identity, tabs only. Does not restyle Receive Device form. */
.sos627-workspace.sos629-counter,
.sos627-workspace {
  --sos633-bg:#F8F5EE; --sos633-paper:#FFFCF7;
  --sos633-ink:#35291F; --sos633-muted:#796A59;
  --sos633-border:#E5D9C8; --sos633-accent:#755536;
  --sos627-accent:var(--sos633-accent);
  color:var(--sos633-ink);
}
.sos627-workspace.sos629-counter .sos627-toolbar,
.sos627-workspace .sos627-toolbar {
  background:var(--sos633-paper)!important;
  border:1px solid var(--sos633-border)!important;
  border-radius:17px!important;
  padding:14px 18px!important;
  box-shadow:0 8px 27px rgba(75,54,29,.055)!important;
  gap:17px!important;
}
.sos627-workspace.sos629-counter .sos627-toolbar::before {background:#B99467!important;}
.sos627-workspace.sos629-counter .sos627-kicker strong,
.sos627-workspace .sos627-kicker strong {color:var(--sos633-ink)!important;}
.sos627-workspace.sos629-counter .sos627-kicker span,
.sos627-workspace .sos627-kicker span {color:var(--sos633-muted)!important;}
.sos627-workspace.sos629-counter .sos627-tabs,
.sos627-workspace .sos627-tabs {
  background:#F2EBE0!important;border:1px solid var(--sos633-border)!important;
  border-radius:12px!important;padding:5px!important;gap:3px!important;
}
.sos627-workspace.sos629-counter .sos627-tab,
.sos627-workspace .sos627-tab {
  background:transparent!important;color:#64503C!important;
  border:1px solid transparent!important;border-radius:9px!important;
  min-height:46px!important;font-weight:760!important;
  box-shadow:none!important;
}
.sos627-workspace.sos629-counter .sos627-tab:hover,
.sos627-workspace .sos627-tab:hover {background:#FFFBF5!important;border-color:#DCCBB5!important;color:#3D2C20!important;}
.sos627-workspace.sos629-counter .sos627-tab.active,
.sos627-workspace .sos627-tab.active {
  background:var(--sos633-accent)!important;
  border-color:var(--sos633-accent)!important;
  color:#FFF!important;box-shadow:0 4px 11px rgba(94,63,35,.16)!important;
}
.sos627-workspace.sos629-counter .sos627-tab.active::after{background:#E7CA9F!important;}
.sos627-workspace.sos629-counter .sos627-context,
.sos627-workspace .sos627-context {border-bottom:1px solid var(--sos633-border)!important;}
.sos627-workspace.sos629-counter .sos627-context strong,
.sos627-workspace .sos627-context strong{color:var(--sos633-ink)!important;}
.sos627-workspace.sos629-counter .sos627-context span,
.sos627-workspace .sos627-context span {color:var(--sos633-muted)!important;}
.sos627-workspace.sos629-counter .sos629-sticker-button {
  border-color:#D5C3AA!important;background:#FFFCF7!important;color:#674A30!important;
}
.sos627-workspace.sos629-counter .sos629-sticker-button:hover{background:#F3EADB!important;}
.sos627-workspace .sos627-tab:focus-visible{outline:3px solid #C4A37B!important;outline-offset:2px;}
@media(max-width:760px){
  .sos627-workspace.sos629-counter .sos627-toolbar,
  .sos627-workspace .sos627-toolbar{padding:11px!important;}
}
</style>
