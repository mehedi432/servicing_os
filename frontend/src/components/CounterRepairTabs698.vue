<script setup>
// SOS_COUNTER_REPAIR_TABS_698 — Counter repair UX, real ERPNext operations only.
// Keep the existing ServiceJobsWorkspace mounted while switching operational tabs.
import { computed, nextTick, onMounted, onUnmounted, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import ServiceJobsWorkspace from './ServiceJobsWorkspace.vue'
import ServiceInvoiceHub661 from './ServiceInvoiceHub661.vue'

const emit = defineEmits(['receive', 'manage'])
const bn = computed(() => String(unref(currentLanguage) || 'en').toLowerCase().startsWith('bn'))
const active = ref('all')
const rail = ref(null)
const busy = ref(false)
const summary = ref(null)
const summaryError = ref('')
const updatedAt = ref('')
const refreshToken = ref(0)
let controller = null
let sequence = 0

const tabs = [
  {key:'all',en:'All Jobs',bn:'সব সার্ভিস',detailEn:'Search every recent job, view device details, assign technicians and advance repairs.',detailBn:'সার্ভিস খুঁজুন, বিস্তারিত দেখুন, টেকনিশিয়ান দিন এবং কাজের ধাপ পরিবর্তন করুন.',icon:'list'},
  {key:'active',en:'Active Repairs',bn:'চলমান রিপেয়ার',detailEn:'Received, diagnosing, repairing and other work not yet completed.',detailBn:'চলমান পরীক্ষা ও মেরামতের কাজগুলো এখানে দেখুন।',icon:'tool'},
  {key:'unassigned',en:'Unassigned',bn:'টেকনিশিয়ান বাকি',detailEn:'Jobs without a technician; assign directly from the job detail panel.',detailBn:'যেসব কাজে টেকনিশিয়ান দেওয়া হয়নি, সেখান থেকেই দায়িত্ব দিন।',icon:'user'},
  {key:'waiting',en:'Waiting Parts',bn:'পার্টসের অপেক্ষা',detailEn:'Devices waiting for replacement parts or materials.',detailBn:'যন্ত্রাংশের অপেক্ষায় থাকা ডিভাইসগুলো দেখুন।',icon:'box'},
  {key:'ready',en:'Ready to Deliver',bn:'ডেলিভারির জন্য প্রস্তুত',detailEn:'Completed repairs and devices marked ready for delivery.',detailBn:'সম্পন্ন কাজ ও ডেলিভারির জন্য প্রস্তুত ডিভাইস।',icon:'check'},
  {key:'delivered',en:'Delivered',bn:'ডেলিভারি হয়েছে',detailEn:'Find delivered jobs and review their service history.',detailBn:'ডেলিভারি করা সার্ভিস জবের ইতিহাস ও তথ্য দেখুন।',icon:'truck'},
  {key:'invoices',en:'Invoices & Billing',bn:'বিল ও ইনভয়েস',detailEn:'Linked service invoices, new invoice drafts, print and reprint.',detailBn:'সার্ভিস ইনভয়েস, নতুন বিল, প্রিন্ট ও পুনর্মুদ্রণ।',icon:'receipt'}
]
const selected = computed(() => tabs.find(x => x.key === active.value) || tabs[0])
const stats = computed(() => {
  const s = summary.value
  const rows = Array.isArray(s?.jobs) ? s.jobs : []
  const value = test => s ? String(rows.filter(test).length) : '—'
  return [
    {name:bn.value?'সাম্প্রতিক জব':'Recent jobs',value:s?String(rows.length):'—',hint:bn.value?'সর্বোচ্চ ২০০টি':'Up to 200'},
    {name:bn.value?'চলমান কাজ':'Active repairs',value:value(j=>!['Delivered','Cancelled','Completed','Ready to Deliver'].includes(j.status)),hint:bn.value?'নমুনা তালিকায়':'Within loaded jobs'},
    {name:bn.value?'প্রস্তুত':'Ready / completed',value:value(j=>['Completed','Ready to Deliver'].includes(j.status)),hint:bn.value?'নমুনা তালিকায়':'Within loaded jobs'},
    {name:bn.value?'দায়িত্ব বাকি':'Unassigned',value:value(j=>!j.technician),hint:bn.value?'নমুনা তালিকায়':'Within loaded jobs'}
  ]
})
function choose(key) {
  if (!tabs.some(tab => tab.key === key)) return
  active.value = key
}
function keyboard(event,index) {
  if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return
  event.preventDefault()
  const last=tabs.length-1
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? last :
    event.key === 'ArrowRight' ? (index+1)%tabs.length : (index-1+tabs.length)%tabs.length
  choose(tabs[next].key)
  nextTick(() => rail.value?.querySelectorAll('[role="tab"]')[next]?.focus())
}
function receive() {
  // Native intake/receipt modal already lives in App.vue; do not create another.
  window.dispatchEvent(new CustomEvent('servicing-os:open-counter-service-receive'))
}
function management() { emit('manage') }
async function refresh() {
  const current=++sequence
  controller?.abort()
  controller=new AbortController()
  busy.value=true
  summaryError.value=''
  refreshToken.value += 1
  try {
    const url='/api/method/servicing_os.api.service_jobs_hub.get_service_jobs?status=All'
    const response=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{Accept:'application/json'}})
    const json=await response.json()
    if(!response.ok || json.exc || json.exc_type || json.exception || !Array.isArray(json.message?.jobs)) {
      throw Error(typeof json.message === 'string' ? json.message : json.exception || 'Service Job summary is unavailable')
    }
    if (current!==sequence) return
    summary.value=json.message
    updatedAt.value=new Date().toLocaleTimeString(bn.value?'bn-BD':'en-BD',{hour:'numeric',minute:'2-digit'})
  } catch (error) {
    if (current!==sequence || error?.name==='AbortError') return
    summary.value=null
    summaryError.value=String(error?.message||'Unable to read Service Jobs').slice(0,180)
  } finally {
    if(current===sequence) busy.value=false
  }
}
function externalRefresh() { refresh() }
onMounted(() => {
  refresh()
  ;['servicing-os:service-job-created','servicing-os:service-invoice-created','servicing-os:service-job-updated'].forEach(evt=>window.addEventListener(evt,externalRefresh))
})
onUnmounted(() => {
  sequence++
  controller?.abort()
  ;['servicing-os:service-job-created','servicing-os:service-invoice-created','servicing-os:service-job-updated'].forEach(evt=>window.removeEventListener(evt,externalRefresh))
})
</script>

<template>
  <section class="sos698-repair" aria-label="Repair operations command center">
    <header class="sos698-head">
      <div class="sos698-heading">
        <div class="sos698-kicker"><span class="sos698-pulse" aria-hidden="true"></span>{{bn?'সার্ভিসিং ওএস · রিপেয়ার অপারেশনস':'SERVICING OS · REPAIR OPERATIONS'}}<span class="sos698-connected">ERPNext</span></div>
        <h2>{{bn?'রিপেয়ার কমান্ড সেন্টার':'Repair command center'}}</h2>
        <p>{{bn?'ডিভাইস রিসিভ, রিপেয়ার, টেকনিশিয়ান, ডেলিভারি ও বিল — একই কর্মক্ষেত্রে।':'A unified operational workspace for device intake, repairs, technicians, delivery and billing.'}}</p>
      </div>
      <div class="sos698-actions">
        <button type="button" class="sos698-outline" :disabled="busy" @click="refresh" :aria-label="bn?'তালিকা রিফ্রেশ':'Refresh job data'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20 6v6h-6M4 18v-6h6M6.5 9a7 7 0 0 1 12-2.4L20 12M4 12l1.6 5a7 7 0 0 0 12-2"/></svg>
          {{busy?(bn?'লোড হচ্ছে':'Refreshing'):(bn?'রিফ্রেশ':'Refresh')}}
        </button>
        <button type="button" class="sos698-outline" @click="management">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 3l2 2 3-.5.5 3 2 2-2 2 .5 3-3 .5-2 2-2-2-3 .5-.5-3-2-2 2-2-.5-3 3-.5z"/><circle cx="12" cy="10" r="2"/></svg>
          {{bn?'রিপেয়ার ম্যানেজমেন্ট':'Repair Management'}}
        </button>
        <button type="button" class="sos698-primary" @click="receive">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 4v16M4 12h16"/></svg>
          {{bn?'ডিভাইস রিসিভ':'Receive Device'}}
        </button>
      </div>
    </header>
    <div class="sos698-stats" :aria-label="bn?'সাম্প্রতিক সার্ভিস জবের সারাংশ':'Recent service job overview'">
      <article v-for="(item,i) in stats" :key="i" class="sos698-stat"><div class="sos698-stat-label">{{item.name}}</div><div class="sos698-stat-value">{{item.value}}</div><div class="sos698-stat-hint">{{item.hint}}</div></article>
    </div>
    <p class="sos698-caption" role="status">
      {{bn?'সাম্প্রতিক সর্বোচ্চ ২০০টি অনুমোদিত সার্ভিস জব থেকে সারাংশ; সব জবের মোট সংখ্যা নয়।':'Overview uses up to 200 most recently modified accessible jobs; figures are not all-time totals.'}}
      <span v-if="updatedAt"> · {{bn?'আপডেট':'Updated'}} {{updatedAt}}</span>
      <span v-if="summaryError" :title="summaryError"> · {{bn?'সারাংশ পাওয়া যায়নি; কাজের তালিকা ব্যবহার করা যাবে।':'Summary unavailable; the job workspace remains usable.'}}</span>
    </p>
    <div ref="rail" class="sos698-rail" role="tablist" :aria-label="bn?'রিপেয়ার ট্যাব':'Repair operations tabs'">
      <button v-for="(tab,index) in tabs" :key="tab.key" :id="'sos698-tab-'+tab.key" class="sos698-tab" type="button" role="tab"
        :class="{'sos698-selected':active===tab.key}" :aria-selected="active===tab.key" aria-controls="sos698-panel"
        :tabindex="active===tab.key?0:-1" @click="choose(tab.key)" @keydown="keyboard($event,index)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <template v-if="tab.icon==='list'"><path d="M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01"/></template>
          <template v-else-if="tab.icon==='tool'"><path d="M21 8a6 6 0 0 1-8 5.65L7.5 19.2a2.3 2.3 0 0 1-3.25-3.25L9.7 10.5A6 6 0 0 1 17 3l-4 4 4 4z"/></template>
          <template v-else-if="tab.icon==='user'"><circle cx="10" cy="8" r="4"/><path d="M3 21v-2a7 7 0 0 1 14 0v2M19 10v6M16 13h6"/></template>
          <template v-else-if="tab.icon==='box'"><path d="M3 7l9-4 9 4v10l-9 4-9-4zM3 7l9 5 9-5M12 12v9"/></template>
          <template v-else-if="tab.icon==='check'"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></template>
          <template v-else-if="tab.icon==='truck'"><path d="M3 6h12v12H3zM15 10h4l3 4v4h-7M7 18h.01M18 18h.01"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></template>
          <template v-else><path d="M7 3h10l3 3v15l-4-2-4 2-4-2-4 2V3zM8 9h8M8 13h8"/></template>
        </svg>
        <span>{{bn?tab.bn:tab.en}}</span>
      </button>
    </div>
    <div class="sos698-context">
      <div><div class="sos698-context-kicker">{{bn?'নির্বাচিত বিভাগ':'CURRENT WORKSPACE'}}</div><h3>{{bn?selected.bn:selected.en}}</h3><p>{{bn?selected.detailBn:selected.detailEn}}</p></div>
      <span class="sos698-tag">{{bn?'লাইভ সার্ভিস রেকর্ড':'Live service records'}}</span>
    </div>
    <div id="sos698-panel" class="sos698-panel" role="tabpanel" :aria-labelledby="'sos698-tab-'+active" tabindex="0">
      <!-- Keep ServiceJobsWorkspace mounted: preserves selection, work notes and native modal actions. -->
      <div v-show="active!=='invoices'" class="sos698-jobs">
        <ServiceJobsWorkspace :counter-scope="active" :refresh-token="refreshToken" @receive="emit('receive')" @manage="emit('manage')" />
      </div>
      <div v-if="active==='invoices'" class="sos698-invoices"><ServiceInvoiceHub661 /></div>
    </div>
  </section>
</template>

<style scoped>
.sos698-repair,.sos698-repair *{box-sizing:border-box}
.sos698-repair{--sos698-bg:#fffcf8;--sos698-ink:#3f2e23;--sos698-border:#e5d7c7;--sos698-soft:#f6ede2;--sos698-muted:#8c7561;--sos698-brand:#785436;color:var(--sos698-ink);width:100%;min-width:0;font-family:inherit}
.sos698-head{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;padding:8px 2px 15px}
.sos698-heading{min-width:0}.sos698-kicker{display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:#997756;font-size:10px;font-weight:830;letter-spacing:.115em;margin:0 0 9px}
.sos698-pulse{display:inline-block;width:7px;height:7px;border-radius:50%;background:#bc8f63;box-shadow:0 0 0 3px #e9d9c5}
.sos698-connected{padding:3px 8px;border-radius:20px;border:1px solid #e5d4bd;background:#fff8ed;letter-spacing:0;font-size:9px;color:#82644b}
.sos698-heading h2{font-size:clamp(22px,2.5vw,30px);line-height:1.17;font-weight:800;letter-spacing:-.045em;color:#38271c;margin:0}
.sos698-heading p{font-size:12px;color:var(--sos698-muted);margin:7px 0 0;line-height:1.5;max-width:690px}
.sos698-actions{display:flex;flex-wrap:wrap;align-items:center;gap:7px}
.sos698-actions button{min-height:38px!important;display:inline-flex;justify-content:center;align-items:center;gap:7px;font:inherit;font-size:11px!important;font-weight:770!important;border-radius:9px!important;cursor:pointer;padding:8px 11px!important;white-space:nowrap}
.sos698-actions button svg{width:15px;height:15px;flex:none}
.sos698-outline{border:1px solid #dfcbb5!important;background:#fffaf3!important;color:#79573a!important}
.sos698-outline:hover{background:#f7ebdd!important}
.sos698-primary{background:#795539!important;border:1px solid #795539!important;color:#fff!important}
.sos698-primary:hover{background:#614025!important}
.sos698-actions button:disabled{opacity:.6;cursor:wait}
.sos698-actions button:focus-visible,.sos698-tab:focus-visible{outline:2px solid #ad8153;outline-offset:2px}
.sos698-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:3px 0 0}
.sos698-stat{min-width:0;background:linear-gradient(150deg,#fffdf9,#f7eee3);border:1px solid #eadccb;border-radius:12px;padding:14px 15px;box-shadow:0 3px 12px #43301906}
.sos698-stat-label{color:#947b61;font-size:10px;font-weight:720;line-height:1.3}
.sos698-stat-value{font-size:clamp(21px,2.1vw,29px);font-variant-numeric:tabular-nums;line-height:1.25;font-weight:800;color:#423125;letter-spacing:-.04em;margin:7px 0}
.sos698-stat-hint{font-size:10px;color:#a28b75;line-height:1.3}
.sos698-caption{margin:7px 3px 15px;color:#9b8570;font-size:10px;line-height:1.5}
.sos698-rail{display:flex;gap:5px;max-width:100%;overflow-x:auto;scrollbar-width:thin;align-items:stretch;padding:7px 7px 0;border:1px solid #e6d6c4;border-radius:12px 12px 0 0;background:#f4ece2}
.sos698-tab{flex:1 0 auto;display:inline-flex;gap:7px;align-items:center;justify-content:center;min-height:44px;padding:9px 11px!important;background:transparent!important;color:#8a7058!important;border:1px solid transparent!important;border-bottom:0!important;border-radius:8px 8px 0 0!important;font:inherit;font-weight:760!important;font-size:11px!important;cursor:pointer;white-space:nowrap}
.sos698-tab svg{width:14px;height:14px;flex:none}
.sos698-tab:hover{background:#fff8ef!important;color:#73513a!important}
.sos698-tab.sos698-selected{background:#fffdf9!important;border-color:#e4d3c2!important;color:#64452e!important;box-shadow:0 -2px 4px #53301208}
.sos698-context{padding:13px 16px;background:#fffdf9;border:1px solid #e6d6c4;border-top:0;border-radius:0 0 12px 12px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.sos698-context-kicker{font-size:9px;font-weight:860;color:#ab8c6f;letter-spacing:.11em;margin-bottom:4px}
.sos698-context h3{margin:0;color:#4e3828;font-size:14px;font-weight:800;letter-spacing:-.02em}
.sos698-context p{margin:4px 0 0;color:#8c745e;font-size:11px;line-height:1.45}
.sos698-tag{flex:none;border-radius:99px;border:1px solid #ead6bc;background:#f5eada;color:#77553b;padding:6px 10px;font-size:10px;font-weight:750}
.sos698-panel,.sos698-jobs,.sos698-invoices{min-width:0;max-width:100%}
/* Scoped final theme override: earlier styles in ServiceJobsWorkspace contain !important rules. */
.sos698-jobs :deep(.sj-app.sos629-jobs){background:transparent!important;padding:0!important;color:#3f2e23!important}
.sos698-jobs :deep(.sj-header){display:none!important}
.sos698-jobs :deep(.sj-kpis){display:none!important}
.sos698-jobs :deep(.sj-list),.sos698-jobs :deep(.sj-detail){background:#fffcf8!important;border:1px solid #e5d7c7!important;border-radius:13px!important;box-shadow:0 4px 18px #39250f06!important;padding:15px!important}
.sos698-jobs :deep(.sj-main){grid-template-columns:minmax(290px,.95fr) minmax(345px,1.25fr)!important;gap:12px!important}
.sos698-jobs :deep(.sj-item){padding:10px 11px!important;gap:6px!important;background:#fffdf9!important}
.sos698-jobs :deep(.sj-item.chosen){background:#f2e5d2!important}
.sos698-jobs :deep(.sj-filter input),.sos698-jobs :deep(.sj-filter select){min-height:37px!important;padding:8px 10px!important;font-size:12px!important}
.sos698-jobs :deep(.sj-filter){gap:9px!important}
.sos698-jobs :deep(.sj-list-top){margin-bottom:9px!important}
.sos698-jobs :deep(.sj-item>b){font-size:12px!important}
.sos698-jobs :deep(.sj-detail-head h2){font-size:18px!important}
.sos698-jobs :deep(.sj-row button),.sos698-jobs :deep(.sj-panel>button){min-height:37px!important;font-size:11px!important;padding:8px 11px!important}
.sos698-jobs :deep(.sj-info>div){background:#faf3e9!important;border-color:#ecdcc7!important}
.sos698-invoices :deep(.sos661){background:transparent!important;padding:0!important}
@media(max-width:1130px){.sos698-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.sos698-rail{justify-content:flex-start}.sos698-tab{flex:0 0 auto}.sos698-jobs :deep(.sj-main){grid-template-columns:1fr!important}}
@media(max-width:650px){.sos698-head{align-items:flex-start}.sos698-actions{width:100%}.sos698-stats{gap:7px}.sos698-stat{padding:11px}.sos698-context{padding:11px}.sos698-tag{display:none}.sos698-tab{padding:8px 10px!important;font-size:10px!important}.sos698-jobs :deep(.sj-list),.sos698-jobs :deep(.sj-detail){padding:12px!important}}
</style>
