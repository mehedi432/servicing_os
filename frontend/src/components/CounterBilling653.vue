<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
const emit=defineEmits(['create'])
const busy=ref(false), error=ref(''), invoices=ref([]), search=ref(''), details=ref(null), detailBusy=ref(false)
const money=(n,c='BDT')=>`${c} ${Number(n||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})}`
const filtered=computed(()=>invoices.value.filter(v=>[v.name,v.customer,v.custom_service_job,v.status].some(s=>String(s||'').toLowerCase().includes(search.value.toLowerCase()))))
async function api(endpoint,params={}){
  const url=new URL('/api/method/servicing_os.api.counter_invoice_653.'+endpoint,window.location.origin)
  for(const [k,v] of Object.entries(params)) url.searchParams.set(k,String(v))
  const res=await fetch(url,{credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'})
  const json=await res.json()
  if(!res.ok||json.exc||json.exception)throw new Error(json.message||'Unable to load invoices')
  return json.message||{}
}
async function refresh(){busy.value=true;error.value='';try{const data=await api('get_counter_billing_overview');invoices.value=data.invoices||[]}catch(e){error.value=e.message||'Could not load billing history'}finally{busy.value=false}}
async function view(name){detailBusy.value=true;error.value='';try{details.value=await api('get_counter_invoice_detail',{invoice_name:name})}catch(e){error.value=e.message||'Cannot read invoice'}finally{detailBusy.value=false}}
onMounted(()=>{refresh();window.addEventListener('servicing-os-invoice-draft-created',refresh)})
onUnmounted(()=>window.removeEventListener('servicing-os-invoice-draft-created',refresh))
</script>
<template>
  <div class="sos653-billing" aria-label="Live service invoice register">
    <div class="sos653-billing-header">
      <div><strong>Service invoices</strong><p>Saved ERPNext invoices linked to service jobs</p></div>
      <div class="sos653-billing-actions"><button type="button" @click="refresh" :disabled="busy">{{ busy?'Refreshing…':'Refresh' }}</button><button type="button" class="main" @click="emit('create')">+ Create Invoice</button></div>
    </div>
    <div class="sos653-billing-search"><input v-model="search" type="search" placeholder="Search invoice, customer, job or status" aria-label="Search invoices" /><span>{{ filtered.length }} record(s)</span></div>
    <p v-if="error" class="sos653-billing-error" role="alert">{{ error }}</p>
    <div v-if="busy" class="sos653-billing-empty">Loading invoices from ERPNext…</div>
    <div v-else-if="!filtered.length" class="sos653-billing-empty">No matching service invoices. Create a draft to begin.</div>
    <div v-else class="sos653-billing-scroll">
      <table><thead><tr><th>Invoice</th><th>Service Job</th><th>Customer</th><th>Status</th><th>Total</th><th>Due</th><th></th></tr></thead>
      <tbody><tr v-for="i in filtered" :key="i.name"><td><strong>{{ i.name }}</strong><small>{{ i.posting_date }}</small></td><td>{{ i.custom_service_job }}</td><td>{{ i.customer }}</td><td><span class="sos653-billing-tag">{{ i.docstatus===0?'Draft':i.status||'Submitted' }}</span></td><td>{{ money(i.grand_total,i.currency) }}</td><td>{{ money(i.outstanding_amount,i.currency) }}</td><td><button type="button" @click="view(i.name)">Details</button></td></tr></tbody></table>
    </div>
    <div v-if="detailBusy" class="sos653-billing-empty">Loading invoice details…</div>
    <section v-else-if="details" class="sos653-billing-detail" aria-label="Invoice details">
      <div class="sos653-billing-header"><div><strong>{{ details.name }}</strong><p>{{ details.customer }} · {{ details.service_job }} · {{ details.status }}</p></div><button type="button" @click="details=null">Close ×</button></div>
      <div v-for="it in details.items" :key="it.item_code" class="sos653-billing-row"><span>{{ it.item_name||it.item_code }} <small>({{ it.qty }} × {{ money(it.rate,details.currency) }}, {{ it.discount_percentage||0 }}% line discount)</small></span><strong>{{ money(it.amount,details.currency) }}</strong></div>
      <div class="sos653-billing-row final"><span>Net total</span><strong>{{ money(details.net_total,details.currency) }}</strong></div>
      <div class="sos653-billing-row"><span>Invoice discount</span><strong>{{ money(details.discount_amount,details.currency) }}</strong></div>
      <div class="sos653-billing-row final"><span>Grand total (ERPNext)</span><strong>{{ money(details.grand_total,details.currency) }}</strong></div>
      <p>Invoice details are read-only. A draft is not a submitted invoice.</p>
    </section>
  </div>
</template>
<style>
.sos653-billing,.sos653-billing *{box-sizing:border-box}.sos653-billing{width:100%;max-width:none;color:#3c2c25;font-size:12px}
.sos653-billing-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:11px;padding:5px 0 14px}
.sos653-billing-header strong{font-size:15px}.sos653-billing-header p{font-size:11px;color:#8b725e;margin-top:3px}
.sos653-billing-actions{display:flex;gap:9px}.sos653-billing button{border:1px solid #e0c7b0!important;background:#f4e3d3!important;padding:9px 12px!important;border-radius:9px!important;font-size:11px!important;font-weight:700!important;color:#775038!important}
.sos653-billing button.main{background:#805a3e!important;border-color:#805a3e!important;color:#fff!important}
.sos653-billing-search{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:1px 0 12px}.sos653-billing-search input{max-width:410px;width:100%;padding:10px;border:1px solid #e7d6c5;border-radius:9px;background:#fffcf7;color:#3c2c25}.sos653-billing-search span{white-space:nowrap;color:#8b725e}
.sos653-billing-scroll{width:100%;overflow:auto;border:1px solid #e7d6c5;border-radius:12px}.sos653-billing table{min-width:700px;width:100%;border-collapse:collapse}.sos653-billing th{text-align:left;padding:12px;background:#f4e3d3;color:#5b3b27;font-size:11px}.sos653-billing td{padding:12px;border-bottom:1px solid #eee1d4}.sos653-billing td strong{display:block}.sos653-billing td small{display:block;color:#927966;margin-top:3px}
.sos653-billing tr:last-child td{border-bottom:none}.sos653-billing-tag{display:inline-block;padding:5px 9px;background:#f4e3d3;border-radius:100px;font-size:10px;white-space:nowrap}
.sos653-billing-detail{margin-top:15px;padding:16px;border:1px solid #e7d6c5;background:#fffaf4;border-radius:12px}.sos653-billing-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #e9dacc}.sos653-billing-row span small{display:block;font-size:10px;color:#8b725e;margin-top:3px}.sos653-billing-row.final{font-weight:800}.sos653-billing-detail p{color:#8b725e;font-size:11px;margin-top:12px}
.sos653-billing-error{border:1px solid #e6c7bd;background:#fff1ec;color:#993c31;padding:10px;border-radius:9px}.sos653-billing-empty{padding:26px;text-align:center;color:#8b725e}
</style>
