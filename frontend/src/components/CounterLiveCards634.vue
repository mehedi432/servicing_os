<script setup>
// SOS_634_COUNTER_LIVE_KPIS — visual-only dashboard; no data mutations.
import {ref, computed, onMounted, onBeforeUnmount} from 'vue'
const data = ref(null)
const error = ref('')
const loading = ref(false)
let refreshTimer = null
let requestNo = 0
const formatCurrency = x => x == null ? 'Restricted' : '৳' + Number(x).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const formatNumber = x => x == null ? 'Restricted' : Number(x).toLocaleString('en-BD')
const cards = computed(() => {
  const m = data.value?.metrics || {}
  return [
    {id:'sales',label:'Today\'s Sales',value:formatCurrency(m.sales_total),detail:'Posted invoices · net of returns',money:true},
    {id:'invoices',label:'Sales Invoices',value:formatNumber(m.sales_count),detail:'Submitted today'},
    {id:'cash',label:'Cash Receipts',value:formatCurrency(m.cash_receipts),detail:'Payment Entries to Cash - AMCL',money:true},
    {id:'received',label:'Devices Received',value:formatNumber(m.received_today),detail:'Service Jobs created today'},
    {id:'ready',label:'Ready to Deliver',value:formatNumber(m.ready_delivery),detail:'Current ready-for-delivery queue'},
    {id:'open',label:'Open Repairs',value:formatNumber(m.open_repairs),detail:'All undelivered, active jobs'}
  ]
})
async function refresh(){
  const run = ++requestNo
  loading.value=true;error.value=''
  try {
    const response=await fetch('/api/method/servicing_os.api.counter_snapshot.get_counter_snapshot',
      {credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'})
    const payload=await response.json()
    if(!response.ok || payload.exc || payload.exc_type || !payload.message || !payload.message.metrics) {
      throw new Error(payload.exception || (typeof payload.message === 'string' ? payload.message : '') || `Counter data unavailable (${response.status})`)
    }
    if(run===requestNo)data.value=payload.message
  } catch(e){ if(run===requestNo)error.value=e?.message || 'Unable to load Counter figures.' }
  finally {if(run===requestNo)loading.value=false}
}
function onVisible(){if(document.visibilityState==='visible')refresh()}
onMounted(()=>{refresh();refreshTimer=setInterval(()=>{if(document.visibilityState==='visible')refresh()},60000);document.addEventListener('visibilitychange',onVisible)})
onBeforeUnmount(()=>{requestNo++;if(refreshTimer)clearInterval(refreshTimer);document.removeEventListener('visibilitychange',onVisible)})
</script>
<template>
<section class="sos634-live" aria-label="Live counter performance">
 <header class="sos634-header">
  <div><span class="sos634-kicker">SERVICING OS · LIVE COUNTER</span><h2>Today's Overview</h2><p>Verified shop activity and inventory, not preview numbers</p></div>
  <button type="button" class="sos634-refresh" :disabled="loading" @click="refresh">{{loading ? 'Updating…' : 'Refresh figures'}}</button>
 </header>
 <p v-if="error" class="sos634-error" role="alert">{{error}} <button type="button" @click="refresh">Retry</button></p>
 <div v-if="data" class="sos634-grid">
  <article v-for="card in cards" :key="card.id" class="sos634-card" :class="'sos634-'+card.id">
    <div class="sos634-cardlabel">{{card.label}}</div>
    <div class="sos634-cardvalue" :class="{restricted:card.value==='Restricted'}">{{card.value}}</div>
    <div class="sos634-cardfoot">{{card.detail}}</div>
  </article>
 </div>
 <div v-else-if="loading" class="sos634-loading" role="status">Loading actual sales and service activity…</div>
 <div class="sos634-foot" v-if="data">
  <div><strong>Retail stock</strong><span>{{formatNumber(data.metrics.retail_stock_units)}} units in Stores - AMCL</span></div>
  <div><strong>Used laptops</strong><span>{{formatNumber(data.metrics.used_laptop_stock_units)}} units on hand</span></div>
  <time>{{data.date}} · updated {{data.as_of?.slice(11,16)}}</time>
 </div>
 <details v-if="data?.warnings?.length" class="sos634-warnings"><summary>Data access / reporting notes ({{data.warnings.length}})</summary><p v-for="w in data.warnings" :key="w">{{w}}</p></details>
</section>
</template>
<style>
/* SOS_634_COUNTER_LIVE_KPIS — ivory only, no effect on Receive Device fields. */
.sos634-live{font-family:inherit;background:#f8f4ec;border:1px solid #e9dccb;border-radius:17px;padding:16px 18px 18px;margin:0 0 14px;color:#37291e;min-width:0}
.sos634-live *{box-sizing:border-box}
.sos634-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px}
.sos634-kicker{font-size:10px;letter-spacing:.13em;font-weight:850;color:#916f4b}
.sos634-header h2{font-size:21px;letter-spacing:-.02em;font-weight:850;color:#382a21;margin:3px 0}
.sos634-header p{color:#867360;font-size:12px;margin:0}
.sos634-refresh{background:#fffdf8;border:1px solid #d4bea3;color:#705034;border-radius:10px;min-height:42px;padding:10px 16px;font-size:12px;font-weight:800;cursor:pointer}
.sos634-refresh:hover{background:#f0e6d8}.sos634-refresh:disabled{opacity:.6;cursor:wait}
.sos634-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.sos634-card{border:1px solid #e9dccb;background:#fffcf7;border-radius:13px;min-height:110px;padding:15px 16px;display:flex;flex-direction:column;gap:7px;box-shadow:0 3px 10px rgba(90,62,37,.035);overflow:hidden}
.sos634-cardlabel{font-size:12px;font-weight:750;color:#77644f}.sos634-cardvalue{font-size:24px;font-weight:900;letter-spacing:-.025em;color:#382a21;overflow-wrap:anywhere;line-height:1.2}
.sos634-cardvalue.restricted{font-size:16px;color:#a45a3c}.sos634-cardfoot{font-size:11px;color:#8c7963;line-height:1.4;margin-top:auto}
.sos634-foot{margin-top:11px;border-top:1px solid #e6d6c2;padding:12px 3px 0;display:flex;flex-wrap:wrap;gap:10px 22px;color:#715f4b;font-size:11px}
.sos634-foot>div{display:flex;gap:6px;align-items:baseline}.sos634-foot strong{color:#4a3625}.sos634-foot time{margin-left:auto;color:#8b7968}
.sos634-error{background:#fff2e8;border:1px solid #e7bfab;padding:12px;border-radius:11px;color:#934226;font-size:12px}.sos634-error button{font-weight:750;text-decoration:underline}
.sos634-loading{padding:24px;text-align:center;color:#846c53;font-size:13px}
.sos634-warnings{margin-top:10px;font-size:11px;color:#8b5a39}.sos634-warnings summary{cursor:pointer;font-weight:750}.sos634-warnings p{margin:7px 0}
@media(max-width:1000px){.sos634-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.sos634-live{padding:12px}.sos634-grid{gap:8px}.sos634-card{padding:12px;min-height:102px}.sos634-cardvalue{font-size:19px}.sos634-header h2{font-size:19px}.sos634-foot time{margin-left:0}}
@media print{.sos634-refresh,.sos634-warnings{display:none!important}}
</style>
