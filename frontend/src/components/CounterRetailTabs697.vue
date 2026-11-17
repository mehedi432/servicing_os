<script setup>
// SOS_COUNTER_RETAIL_TABS_697
// Presentation and navigation only. All invoices, stock and payments remain
// owned by the existing NewSaleCounter655 / SalesCenter ERPNext flows.
import { computed, nextTick, onMounted, onUnmounted, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import NewSaleCounter655 from './NewSaleCounter655.vue'
import SalesCenter from './SalesCenter.vue'

const selected = ref('New Sale')
const tabRail = ref(null)
const bn = computed(() => String(unref(currentLanguage) || 'en').startsWith('bn'))
const tabs = [
  {key:'New Sale', en:'New Sale', bn:'নতুন বিক্রয়',
    sub:['Product selection, cart, customer and checkout','পণ্য, কার্ট, ক্রেতা ও চেকআউট'],
    paths:['M3 4h2l2 11h12l2-8H6','M9 20h.01','M18 20h.01']},
  {key:'Sales History', en:'Sales History', bn:'বিক্রয়ের ইতিহাস',
    sub:['Submitted invoices, earlier sales and reprints','আগের বিক্রয়, ইনভয়েস ও পুনর্মুদ্রণ'],
    paths:['M4 5h16v16H4z','M8 3v4','M16 3v4','M4 10h16','M8 14h8','M8 17h5']},
  {key:'Quotations', en:'Quotations', bn:'মূল্য প্রস্তাব',
    sub:['Create and manage customer quotations','ক্রেতার মূল্য প্রস্তাব তৈরি ও পরিচালনা'],
    paths:['M7 3h10l4 4v14H3V3z','M17 3v5h5','M7 13h10','M7 17h8']},
  {key:'Returns & Exchanges', en:'Returns', bn:'ফেরত / পরিবর্তন',
    sub:['Return against the original invoice','মূল ইনভয়েসের বিপরীতে পণ্য ফেরত'],
    paths:['M4 7h12a5 5 0 0 1 0 10H8','M8 13l-4 4 4 4','M20 17H8']},
  {key:'Payments & Dues', en:'Payments & Dues', bn:'পেমেন্ট / বকেয়া',
    sub:['Outstanding invoices and customer payments','বকেয়া ইনভয়েস ও ক্রেতার পেমেন্ট'],
    paths:['M3 6h18v13H3z','M3 10h18','M7 15h5']},
  {key:'Sales Warranty', en:'Warranty', bn:'ওয়ারেন্টি',
    sub:['Invoice item warranty and serial records','ইনভয়েসের ওয়ারেন্টি ও সিরিয়াল তথ্য'],
    paths:['M12 2l8 4v6c0 5-3 8-8 10-5-2-8-5-8-10V6z','M9 12l2 2 4-4']},
  {key:'Sales Reports', en:'Reports', bn:'প্রতিবেদন',
    sub:['Sales performance, trends and profit reporting','বিক্রয়, প্রবণতা ও লাভ-ক্ষতির প্রতিবেদন'],
    paths:['M4 20V10','M10 20V4','M16 20v-8','M22 20H2']},
]
const activeTab = computed(() => tabs.find(t => t.key === selected.value) || tabs[0])
function choose(key) {
  if (!tabs.some(t => t.key === key)) return
  selected.value = key
}
function keyboard(event, index) {
  const key = event.key
  if (!['ArrowLeft','ArrowRight','Home','End'].includes(key)) return
  event.preventDefault()
  const last = tabs.length - 1
  const next = key === 'Home' ? 0 : key === 'End' ? last :
    key === 'ArrowRight' ? (index + 1) % tabs.length : (index - 1 + tabs.length) % tabs.length
  choose(tabs[next].key)
  nextTick(() => tabRail.value?.querySelectorAll('[role="tab"]')[next]?.focus())
}
const loading = ref(false)
const stats = ref(null)
const statsError = ref('')
const money = n => Number(n || 0).toLocaleString('en-BD', {minimumFractionDigits:2,maximumFractionDigits:2})
const getMoney = n => (stats.value ? '৳ ' + money(n) : '—')
const metrics = computed(() => [
  {name:bn.value?'বিক্রয় ইনভয়েস':'Sales invoices', value:stats.value ? String(stats.value.invoice_count ?? 0) : '—'},
  {name:bn.value?'নিট বিক্রয়':'Net sales', value:getMoney(stats.value?.net_sales)},
  {name:bn.value?'বকেয়া':'Outstanding', value:getMoney(stats.value?.outstanding)},
  {name:bn.value?'আদায়':'Collections', value:stats.value?.collections_visible ? getMoney(stats.value?.collections) : '—'},
])
let requestSequence = 0
let controller = null
async function refreshMetrics() {
  const seq = ++requestSequence
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  statsError.value = ''
  try {
    const response = await fetch('/api/method/servicing_os.api.sales_center.statistics', {
      credentials:'same-origin',cache:'no-store',signal:controller.signal,
      headers:{Accept:'application/json'}
    })
    const data = await response.json()
    if (!response.ok || data.exc || data.exception || !data.message || typeof data.message !== 'object')
      throw new Error(typeof data.message === 'string' ? data.message : data.exception || 'Sales metrics unavailable')
    if (seq === requestSequence) stats.value = data.message
  } catch (error) {
    if (seq !== requestSequence || error?.name === 'AbortError') return
    stats.value = null
    statsError.value = responseMessage(error)
  } finally {
    if (seq === requestSequence) loading.value = false
  }
}
function responseMessage(error) {
  const message = String(error?.message || 'Unable to load sales summary')
  return message.slice(0, 200)
}
function checkoutCompleted() { refreshMetrics() }
onMounted(() => {
  refreshMetrics()
  window.addEventListener('servicing-os-checkout-completed', checkoutCompleted)
})
onUnmounted(() => {
  requestSequence++
  controller?.abort()
  window.removeEventListener('servicing-os-checkout-completed', checkoutCompleted)
})
</script>

<template>
  <section class="sos697-retail" aria-label="Retail sales command center">
    <header class="sos697-heading">
      <div class="sos697-heading-copy">
        <p class="sos697-kicker">{{ bn ? 'সার্ভিসিং ওএস · রিটেইল কাউন্টার' : 'SERVICING OS · RETAIL COUNTER' }}
          <span class="sos697-status"><span class="sos697-dot"></span>ERPNext</span>
        </p>
        <h2>{{ bn ? 'বিক্রয় কেন্দ্র' : 'Retail sales center' }}</h2>
        <p class="sos697-intro">{{ bn ? 'পণ্য, বিক্রয়, গ্রাহক, পেমেন্ট ও প্রতিবেদন একই জায়গায়।' : 'Products, checkout, invoices and sales operations in one connected workspace.' }}</p>
      </div>
      <div class="sos697-topactions">
        <button type="button" class="sos697-refresh" :disabled="loading" @click="refreshMetrics" :aria-label="bn ? 'তথ্য রিফ্রেশ' : 'Refresh sales summary'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M6.2 9a7 7 0 0 1 12.2-2L20 12M4 12l1.6 5a7 7 0 0 0 12.2-2"/></svg>
          {{ loading ? (bn ? 'লোড হচ্ছে' : 'Updating') : (bn ? 'রিফ্রেশ' : 'Refresh') }}
        </button>
      </div>
    </header>

    <section class="sos697-metrics" :aria-label="bn?'বিগত ৩০ দিনের সারসংক্ষেপ':'Last 30 days sales summary'">
      <div v-for="metric in metrics" :key="metric.name" class="sos697-metric">
        <span>{{metric.name}}</span><strong>{{metric.value}}</strong>
      </div>
    </section>
    <p class="sos697-metrics-caption">
      {{ bn ? 'বিগত ৩০ দিনের সাবমিটকৃত ইনভয়েস · তথ্য অ্যাক্সেস ও ERPNext অনুমতির উপর নির্ভরশীল' : 'Last 30 days · submitted invoices · ERPNext permissions apply' }}
      <span v-if="stats?.limited">{{ bn ? ' · আংশিক তথ্য (রেকর্ড সীমা)' : ' · Partial data (record limit)' }}</span>
      <span v-if="statsError" role="status" :title="statsError"> · {{bn ? 'সারাংশ পাওয়া যায়নি; বিক্রয় ফর্ম ব্যবহার করা যাবে' : 'Summary unavailable; sales functions remain available'}}</span>
    </p>

    <div ref="tabRail" class="sos697-tabs" role="tablist" :aria-label="bn?'রিটেইল বিক্রয় ট্যাব':'Retail sales tabs'">
      <button v-for="(tab, index) in tabs" :id="'sos697-tab-'+index" :key="tab.key"
        type="button" role="tab" class="sos697-tab"
        :class="{'sos697-active':selected===tab.key}"
        :aria-selected="selected===tab.key"
        aria-controls="sos697-panel"
        :tabindex="selected===tab.key ? 0 : -1"
        @click="choose(tab.key)" @keydown="keyboard($event,index)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-for="(d,i) in tab.paths" :key="i" :d="d"/></svg>
        <span>{{bn ? tab.bn : tab.en}}</span>
      </button>
    </div>

    <div class="sos697-context">
      <div><span class="sos697-context-label">{{ bn ? 'সক্রিয় বিভাগ' : 'ACTIVE SECTION' }}</span>
        <h3>{{bn ? activeTab.bn : activeTab.en}}</h3>
        <p>{{activeTab.sub[bn?1:0]}}</p>
      </div>
      <span class="sos697-context-tag">{{bn?'ERPNext-এর সাথে সংযুক্ত':'ERPNext connected'}}</span>
    </div>

    <div class="sos697-panel" role="tabpanel" id="sos697-panel"
      :aria-labelledby="'sos697-tab-'+tabs.findIndex(t=>t.key===selected)" tabindex="0">
      <!-- KEEP mounted while browsing other tabs: prevents a partially entered cart being lost. -->
      <div v-show="selected==='New Sale'" class="sos697-new-sale">
        <NewSaleCounter655>
          <template #legacy><slot name="legacy" /></template>
        </NewSaleCounter655>
      </div>
      <!-- REAL existing components and routes, not placeholders or demo records. -->
      <SalesCenter v-if="selected!=='New Sale'" :key="selected" :section="selected" />
    </div>
  </section>
</template>

<style scoped>
.sos697-retail,.sos697-retail *{box-sizing:border-box}
.sos697-retail{--sos697-paper:#fffcf7;--sos697-ink:#3c2c25;--sos697-line:#e7d6c5;--sos697-muted:#8b725e;--sos697-accent:#805a3e;color:var(--sos697-ink);width:100%;min-width:0;font-family:inherit}
.sos697-heading{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;padding:12px 4px 15px}
.sos697-kicker{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin:0 0 7px;font-size:10px;letter-spacing:.11em;font-weight:800;color:#9b795c}
.sos697-status{display:inline-flex;align-items:center;gap:5px;border:1px solid #e8d8c6;border-radius:99px;padding:3px 9px;font-size:9px;letter-spacing:0;font-weight:750;color:#755843;background:#fffaf3}
.sos697-dot{width:6px;height:6px;border-radius:50%;background:#b88a5c}
.sos697-heading h2{margin:0;font-size:clamp(22px,2.7vw,30px);line-height:1.14;font-weight:800;letter-spacing:-.045em;color:#3c2c25}
.sos697-intro{margin:7px 0 0;color:var(--sos697-muted);font-size:12px;line-height:1.5}
.sos697-refresh{display:inline-flex;align-items:center;gap:7px;border:1px solid #dcc8b4!important;border-radius:9px;background:#fffaf3!important;color:#73553c!important;padding:9px 13px!important;font:inherit;font-size:11px!important;font-weight:750!important;cursor:pointer;white-space:nowrap}
.sos697-refresh svg{width:15px;height:15px}.sos697-refresh:disabled{opacity:.5;cursor:wait}
.sos697-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:4px 0 0}
.sos697-metric{padding:15px 14px 14px;background:linear-gradient(145deg,#fffdf9,#f7eee5);border:1px solid #e9dbcb;border-radius:12px;min-width:0}
.sos697-metric span{display:block;font-size:10px;font-weight:650;color:#917760;margin-bottom:9px;line-height:1.4}
.sos697-metric strong{display:block;font-size:clamp(15px,1.65vw,22px);font-weight:820;letter-spacing:-.04em;color:#493528;overflow-wrap:anywhere;line-height:1.3;font-variant-numeric:tabular-nums}
.sos697-metrics-caption{margin:7px 3px 16px;font-size:10px;line-height:1.4;color:#a18b78}
.sos697-tabs{display:flex;align-items:stretch;gap:6px;padding:7px 7px 0;background:#f5eee6;border:1px solid #e7d6c5;border-radius:12px 12px 0 0;overflow-x:auto;scrollbar-width:thin;max-width:100%}
.sos697-tab{flex:1 0 auto;display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid transparent!important;border-bottom:0!important;border-radius:8px 8px 0 0;background:transparent!important;color:#846b55!important;font:inherit;font-size:11px!important;font-weight:740!important;min-height:45px;padding:10px 11px!important;cursor:pointer;white-space:nowrap;transition:background .12s ease,color .12s ease}
.sos697-tab svg{height:15px;width:15px;flex:none}
.sos697-tab:hover{background:#fff8f0!important;color:#62452f!important}
.sos697-tab.sos697-active{background:#fffdf9!important;color:#67462f!important;border-color:#e4d3c2!important;box-shadow:0 -2px 4px #3a24100a}
.sos697-tab:focus-visible{outline:2px solid #ba926c;outline-offset:-2px}
.sos697-context{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;padding:13px 16px;margin:0 0 11px;border:1px solid #e7d6c5;border-top:0;border-radius:0 0 12px 12px;background:#fffdf9}
.sos697-context-label{display:block;font-size:9px;letter-spacing:.1em;font-weight:850;color:#aa8b6d;margin-bottom:4px}
.sos697-context h3{margin:0;font-size:14px;font-weight:780;letter-spacing:-.02em;color:#513b2a}
.sos697-context p{margin:3px 0 0;color:#8b725e;font-size:11px;line-height:1.45}
.sos697-context-tag{background:#f4e8d9;color:#735238;border:1px solid #ead5bd;border-radius:99px;padding:6px 10px;font-size:10px;font-weight:750;white-space:nowrap}
.sos697-panel{width:100%;max-width:100%;min-width:0;outline:none}
.sos697-new-sale{min-width:0;max-width:100%}
.sos697-panel :deep(.sosc-sales){min-height:0;background:transparent;padding:4px 0 20px}
.sos697-panel :deep(.sosc-heading){margin-top:2px}
.sos697-panel :deep(.sosc-eyebrow){display:none}
.sos697-panel :deep(.sosc-heading h1){font-size:20px}
.sos697-panel :deep(.sosc-panel){background:#fffcf7}
@media(max-width:1080px){.sos697-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.sos697-tabs{justify-content:flex-start}.sos697-tab{flex:0 0 auto}}
@media(max-width:580px){.sos697-heading{padding-top:5px}.sos697-metrics{gap:7px}.sos697-metric{padding:10px}.sos697-metric strong{font-size:16px}.sos697-context{padding:11px}.sos697-context-tag{display:none}.sos697-tab{min-height:41px;padding:8px 10px!important;font-size:11px!important}.sos697-panel :deep(.sosc-sales){padding:3px 0 16px}}
</style>
