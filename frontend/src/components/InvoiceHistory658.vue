<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import InvoicePrint657 from './InvoicePrint657.vue'

// SERVICING_OS_COUNTER_658: print existing invoices; never clone the accounting document.
const props = defineProps({ scope: {type:String,default:'all'} })
const records = ref([])
const loading = ref(false)
const error = ref('')
const query = ref('')
const preview = ref(null)
const expanded = ref(true)
const availableScope = computed(() => ['all','sale','repair','used'].includes(props.scope) ? props.scope : 'all')
const heading = computed(() => ({all:'Recent Invoices',sale:'Recent Sale Invoices',repair:'Service Invoice History',used:'Used Laptop Invoices'})[availableScope.value])
const message = computed(() => ({all:'Latest 20 customer invoices across the counter',sale:'Retail and used-laptop customer purchases',repair:'Latest billed repair and service jobs',used:'Used-laptop customer sales'})[availableScope.value])
const matches = computed(() => records.value.filter(x => {
  const needle=query.value.trim().toLowerCase()
  if(!needle) return true
  return [x.name,x.customer,x.service_job,x.invoice_kind,x.status,x.doctype].some(y=>String(y||'').toLowerCase().includes(needle))
}))
const amount = (value,currency) => `${currency||'BDT'} ${Number(value||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})}`
const labelKind = kind => ({repair:'Service',sale:'Retail',used:'Used laptop'})[kind]||'Sale'
let requestSeq = 0

async function refresh() {
  const seq=++requestSeq
  loading.value=true;error.value=''
  try {
    const url=new URL('/api/method/servicing_os.api.invoice_history_658.get_recent_invoices',window.location.origin)
    url.searchParams.set('scope',availableScope.value)
    url.searchParams.set('limit','20')
    const result=await fetch(url,{method:'GET',credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'})
    const data=await result.json()
    if(!result.ok||data.exc||data.exception) throw new Error(typeof data.message==='string'?data.message:'Could not load invoice history')
    if(seq===requestSeq) records.value=data.message?.invoices||[]
  } catch(e){if(seq===requestSeq)error.value=e?.message||'Invoice history could not be loaded'}
  finally{if(seq===requestSeq)loading.value=false}
}
function open(row,duplicate=false){preview.value={name:row.name,doctype:row.doctype,duplicate}}
const onSaved=()=>refresh()
onMounted(()=>{
  refresh()
  window.addEventListener('servicing-os-invoice-draft-created',onSaved)
  window.addEventListener('servicing-os-sale-completed',onSaved)
})
onUnmounted(()=>{
  requestSeq++
  window.removeEventListener('servicing-os-invoice-draft-created',onSaved)
  window.removeEventListener('servicing-os-sale-completed',onSaved)
})
watch(availableScope,refresh)
</script>

<template>
  <section class="sos658-history" aria-label="Recent invoice history">
    <header class="sos658-head">
      <div class="sos658-title"><span class="sos658-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 3h14v18l-3-2-4 2-4-2-3 2V3z"/><path d="M9 8h6M9 12h6M9 16h4"/></svg></span>
        <div><h2>{{ heading }}</h2><p>{{ message }} · Print or reprint without creating a new sale</p></div>
      </div>
      <div class="sos658-controls">
        <span class="sos658-count">{{ records.length }}/20 invoices</span>
        <button type="button" @click="refresh" :disabled="loading" aria-label="Refresh invoice history">{{ loading?'Loading…':'↻ Refresh' }}</button>
        <button type="button" @click="expanded=!expanded" :aria-expanded="expanded">{{ expanded?'Hide':'Show' }}</button>
      </div>
    </header>
    <div v-if="expanded" class="sos658-body">
      <div class="sos658-searchbar">
        <label><span>Find invoice or customer</span><input v-model="query" type="search" placeholder="Invoice no. / Customer / Service Job" autocomplete="off" /></label>
        <small>Latest records from ERPNext · no manual invoice duplication</small>
      </div>
      <p v-if="error" class="sos658-error" role="alert">{{ error }} <button type="button" @click="refresh">Retry</button></p>
      <p v-else-if="loading" class="sos658-empty">Loading the latest invoices…</p>
      <p v-else-if="!matches.length" class="sos658-empty">No matching invoices in the most recent 20 records.</p>
      <div v-else class="sos658-tablewrap">
        <table><thead><tr><th>Invoice / Date</th><th>Customer</th><th>Sale type</th><th>Status</th><th class="sos658-num">Total</th><th class="sos658-actions-head">Print options</th></tr></thead>
          <tbody><tr v-for="row in matches" :key="row.doctype+':'+row.name">
            <td><strong>{{ row.name }}</strong><small>{{ row.posting_date }} · {{ row.doctype==='POS Invoice'?'POS':'Invoice' }}</small></td>
            <td><span>{{ row.customer }}</span><small v-if="row.service_job">Job: {{ row.service_job }}</small></td>
            <td>{{ labelKind(row.invoice_kind) }}</td>
            <td><span class="sos658-status" :class="row.docstatus===1?'sos658-submitted':row.docstatus===2?'sos658-cancelled':''">{{ row.status }}</span><small v-if="row.delivery_status">{{ row.delivery_status }}</small></td>
            <td class="sos658-num"><strong>{{ amount(row.grand_total,row.currency) }}</strong></td>
            <td><div class="sos658-rowbuttons">
              <button type="button" @click="open(row,false)" :aria-label="'Preview and print invoice '+row.name">Print</button>
              <button type="button" class="sos658-duplicate" @click="open(row,true)" :aria-label="'Reprint duplicate copy of invoice '+row.name">Duplicate Copy</button>
            </div></td>
          </tr></tbody>
        </table>
      </div>
      <p class="sos658-footnote">Duplicate Copy prints the same existing invoice number with a clear copy label. No new invoice, stock movement or payment is created.</p>
    </div>
    <InvoicePrint657 v-if="preview" :key="preview.doctype+preview.name+String(preview.duplicate)" :invoice-name="preview.name" :doctype="preview.doctype" :duplicate="preview.duplicate" @close="preview=null" />
  </section>
</template>

<style>
.sos658-history,.sos658-history *{box-sizing:border-box}
.sos658-history{margin:16px 0 0;width:100%;min-width:0;border:1px solid #e7d6c5;border-radius:14px;background:#fffcf7;color:#3c2c25;font:inherit;box-shadow:0 2px 7px #76513708}
.sos658-head{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px 15px;border-bottom:1px solid #eadbcf;flex-wrap:wrap}
.sos658-title{display:flex;align-items:center;gap:11px;min-width:0}.sos658-icon{display:grid;place-items:center;flex:0 0 36px;width:36px;height:36px;border-radius:10px;background:#f4e3d3;color:#805a3e}
.sos658-title h2{font-size:15px;line-height:1.2;font-weight:800;margin:0;color:#3c2c25}.sos658-title p{font-size:11px;line-height:1.5;color:#8b725e;margin:4px 0 0}
.sos658-controls{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.sos658-controls button,.sos658-error button{border:1px solid #dfc4ac!important;background:#fff9f2!important;color:#775039!important;border-radius:8px!important;padding:9px 11px!important;min-height:36px;font-size:11px!important;font-weight:700!important}.sos658-controls button:disabled{opacity:.6}
.sos658-count{font-size:10px;color:#8b725e;margin-right:4px}.sos658-body{padding:13px 15px 12px}
.sos658-searchbar{display:flex;gap:13px;align-items:end;justify-content:space-between;flex-wrap:wrap;margin-bottom:13px}.sos658-searchbar label{display:grid;gap:5px;flex:1 1 220px;font-size:11px;color:#72523d;font-weight:700;max-width:400px}
.sos658-searchbar input{background:#fff!important;color:#3c2c25!important;border:1px solid #dec6b4!important;border-radius:9px!important;width:100%;height:41px!important;min-height:41px!important;padding:9px 12px!important;font-size:12px!important}
.sos658-searchbar small{font-size:10px;color:#9a816c;max-width:270px}.sos658-tablewrap{max-width:100%;overflow:auto;border:1px solid #e9d9cb;border-radius:10px}
.sos658-history table{width:100%;min-width:810px;border-collapse:collapse;table-layout:auto}.sos658-history th{background:#f4e3d3;color:#6b4832;text-align:left;white-space:nowrap;padding:11px 10px;font-size:10px;font-weight:800}.sos658-history td{padding:11px 10px;vertical-align:middle;border-top:1px solid #efe4d8;font-size:11px;color:#3c2c25}
.sos658-history td strong{font-size:11px;font-weight:750}.sos658-history td small{display:block;margin-top:4px;color:#927964;font-size:10px}.sos658-history tr:hover td{background:#fff9f1}.sos658-num{text-align:right;white-space:nowrap}.sos658-status{display:inline-block;padding:4px 8px;border-radius:30px;background:#eee6df;color:#7b5b47;font-size:10px;font-weight:700}.sos658-submitted{background:#e9eee4;color:#3d6349}.sos658-cancelled{background:#f9e2dc;color:#953e2c}
.sos658-actions-head{width:190px}.sos658-rowbuttons{display:flex;gap:6px;align-items:center;white-space:nowrap}.sos658-rowbuttons button{min-height:33px!important;padding:7px 10px!important;border-radius:8px!important;border:1px solid #dcc3ad!important;background:#f7e9dc!important;color:#68452f!important;font-size:10px!important;font-weight:760!important}.sos658-rowbuttons .sos658-duplicate{background:#805a3e!important;border-color:#805a3e!important;color:white!important}
.sos658-footnote{margin:11px 2px 0;color:#927964;font-size:10px;line-height:1.5}.sos658-error,.sos658-empty{padding:18px;text-align:center;font-size:12px;color:#896951}.sos658-error{color:#a3402d;background:#fff1e8;border-radius:9px}
@media(max-width:650px){.sos658-head,.sos658-body{padding:11px}.sos658-title p{font-size:10px}.sos658-count{display:none}}
</style>
