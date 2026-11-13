<script setup>
import { computed, onMounted, ref } from 'vue'
const dateLocal = d => {const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), a=String(d.getDate()).padStart(2,'0');return `${y}-${m}-${a}`}
const today = new Date()
const fromDate=ref(dateLocal(new Date(today.getFullYear(),today.getMonth(),today.getDate()-6)))
const toDate=ref(dateLocal(today))
const cashier=ref('')
const warehouse=ref('')
const busy=ref(false), error=ref(''), data=ref(null), tab=ref('sales')
const tabs=[['sales','Sales Invoices'],['payments','Cash Receipts'],['jobs','Service Jobs'],['stock','Warehouse Stock']]
const money=v=>v==null?'Restricted':'৳ '+Number(v||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
function csvEscape(v){let s=String(v??'');return '"'+s.replaceAll('"','""')+'"'}
const reportRows=computed(()=>data.value?.[tab.value] || [])
const columns=computed(()=>({sales:[['posting_date','Date'],['name','Invoice'],['customer_name','Customer'],['owner','Cashier'],['net_amount','Net ৳'],['outstanding_amount','Due ৳'],['status','Status']],payments:[['posting_date','Date'],['name','Payment'],['party_name','Customer'],['owner','Entered by'],['received_amount','Cash ৳'],['mode_of_payment','Method']],jobs:[['creation','Received'],['name','Job No.'],['customer_name','Customer'],['brand','Brand'],['device_model','Model'],['status','Status'],['technician','Technician']],stock:[['item_code','Item Code'],['warehouse','Warehouse'],['actual_qty','On Hand'],['valuation_rate','Unit Value'],['stock_value','Stock Value']]}[tab.value]))
const cards=computed(()=>[
 ['Net Sales',data.value?.kpis.net_sales,'money'],
 ['Cash Collected',data.value?.kpis.cash_collected,'money'],
 ['Invoice Outstanding',data.value?.kpis.invoice_outstanding,'money'],
 ['Service Received',data.value?.kpis.service_received,'number'],
 ['Open Repair Queue',data.value?.kpis.open_service_jobs,'number'],
 ['Stock Lines',data.value?.kpis.stock_lines,'number']])
async function refresh(){busy.value=true;error.value='';try{
 const url=new URL('/api/method/servicing_os.api.live_reports.get_business_report',location.origin)
 Object.entries({from_date:fromDate.value,to_date:toDate.value,cashier:cashier.value,warehouse:warehouse.value}).forEach(([k,v])=>{if(v)url.searchParams.set(k,v)})
 const response=await fetch(url,{credentials:'same-origin',headers:{Accept:'application/json'}})
 const json=await response.json();if(!response.ok || json.exc || json.exc_type)throw Error(json.message?.message||json.exception||'Unable to load reports')
 data.value=json.message
 }catch(e){error.value=e.message||String(e)}finally{busy.value=false}}
function printReport(){window.print()}
function exportCsv(){if(!data.value)return
 const col=columns.value
 const lines=[col.map(x=>csvEscape(x[1])).join(','),...reportRows.value.map(r=>col.map(x=>csvEscape(r[x[0]])).join(','))]
 const blob=new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8;'})
 const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=`servicing-${tab.value}-${fromDate.value}-${toDate.value}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),2000)
}
onMounted(refresh)
</script>
<template>
<section class="sos-fin-reports">
  <header class="sos-fin-header"><div><div class="sos-fin-eyebrow">SERVICING OS · MANAGEMENT</div><h1>Business Reports</h1><p>Posted financial transactions and live shop operations. No sample totals.</p></div>
    <button type="button" class="sos-fin-btn primary" :disabled="busy" @click="refresh">{{busy?'Loading…':'↻ Refresh Reports'}}</button>
  </header>
  <form class="sos-fin-filters" @submit.prevent="refresh">
    <label>From date<input v-model="fromDate" type="date" required></label>
    <label>To date<input v-model="toDate" type="date" required></label>
    <label>Cashier / creator<input v-model.trim="cashier" placeholder="All staff (or user email)"></label>
    <label>Warehouse<select v-model="warehouse"><option value="">All shop locations</option><option>Stores - AMCL</option><option>Spare Parts - AMCL</option><option>Used Laptops - AMCL</option></select></label>
    <button class="sos-fin-btn primary" :disabled="busy" type="submit">Apply Filters</button>
  </form>
  <p v-if="error" class="sos-fin-error" role="alert">{{error}}</p>
  <template v-if="data">
    <div class="sos-fin-kpis"><article v-for="[label,val,kind] in cards" :key="label"><span>{{label}}</span><strong>{{val==null?'No access':kind==='money'?money(val):Number(val).toLocaleString('en-BD')}}</strong></article></div>
    <div v-if="data.warnings?.length" class="sos-fin-warnings"><p v-for="w in data.warnings" :key="w">⚠ {{w}}</p></div>
    <div class="sos-fin-section"><div class="sos-fin-sectionhead"><div><h2>Detailed Register</h2><p>{{fromDate}} — {{toDate}} · {{reportRows.length}} records shown</p></div>
      <div class="sos-fin-actions"><button type="button" class="sos-fin-btn" @click="exportCsv">↓ Export CSV</button><button type="button" class="sos-fin-btn" @click="printReport">Print</button></div>
    </div>
    <nav class="sos-fin-tabs" aria-label="Report register"><button v-for="[key,title] in tabs" :key="key" type="button" :class="{selected:tab===key}" @click="tab=key">{{title}}</button></nav>
    <div class="sos-fin-tablewrap"><table><thead><tr><th v-for="[field,title] in columns" :key="field">{{title}}</th></tr></thead>
      <tbody><tr v-for="(row,i) in reportRows" :key="row.name || row.item_code+'_'+row.warehouse+'_'+i"><td v-for="[field] in columns" :key="field">{{row[field]??'—'}}</td></tr>
      <tr v-if="!reportRows.length"><td :colspan="columns.length">No matching records, or access is restricted.</td></tr></tbody></table></div>
    </div>
    <details class="sos-fin-basis"><summary>Report basis & accounting definitions</summary><p v-for="line in data.notes" :key="line">• {{line}}</p></details>
  </template>
</section>
</template>
<style>
.sos-fin-reports{width:100%;min-width:0;box-sizing:border-box;background:#faf8f4;color:#554735;min-height:100vh;padding:24px;font-family:inherit}
.sos-fin-reports *{box-sizing:border-box}.sos-fin-header{display:flex;justify-content:space-between;align-items:start;gap:20px;margin-bottom:20px}
.sos-fin-eyebrow{font-size:10px;letter-spacing:2px;font-weight:800;color:#a48665}.sos-fin-header h1{font-size:30px;font-weight:800;letter-spacing:-1px;margin:7px 0}
.sos-fin-header p,.sos-fin-sectionhead p{font-size:12px;color:#9b896f}.sos-fin-btn{padding:11px 15px;border:1px solid #dbcbb4;border-radius:10px;background:white;color:#655036;cursor:pointer;font-weight:700;font-size:12px}
.sos-fin-btn.primary{background:#755a3d;color:white;border-color:#755a3d}.sos-fin-btn:disabled{opacity:.6;cursor:not-allowed}
.sos-fin-filters{display:flex;flex-wrap:wrap;gap:10px;align-items:end;margin-bottom:18px;background:#fffdf9;border:1px solid #e7dbc9;border-radius:15px;padding:14px}
.sos-fin-filters label{font-size:11px;font-weight:700;display:grid;gap:5px;color:#806a4d;flex:1;min-width:155px}.sos-fin-filters input,.sos-fin-filters select{padding:10px 11px;border:1px solid #decfb8;border-radius:9px;background:white;min-height:40px;font-size:12px}
.sos-fin-kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:17px}.sos-fin-kpis article{border:1px solid #e6daca;border-radius:14px;background:white;padding:17px;display:grid;gap:8px}.sos-fin-kpis span{font-size:11px;color:#87765d}.sos-fin-kpis strong{font-size:21px;overflow-wrap:anywhere}
.sos-fin-section{background:#fffdf9;border:1px solid #e7dac8;border-radius:15px;overflow:hidden}.sos-fin-sectionhead{padding:16px 18px;display:flex;gap:12px;justify-content:space-between;align-items:center}.sos-fin-sectionhead h2{margin:0;font-size:17px}.sos-fin-sectionhead p{margin:5px 0 0}.sos-fin-actions{display:flex;gap:7px}.sos-fin-tabs{display:flex;gap:7px;overflow:auto;padding:0 16px 13px}.sos-fin-tabs button{padding:9px 13px;white-space:nowrap;border:1px solid #e2d6c4;border-radius:9px;background:#f9f5ef;color:#715d43;cursor:pointer;font-weight:650;font-size:12px}.sos-fin-tabs button.selected{background:#755a3d;color:white;border-color:#755a3d}
.sos-fin-tablewrap{max-width:100%;overflow:auto}.sos-fin-tablewrap table{border-collapse:collapse;width:100%;min-width:650px;font-size:12px;text-align:left}.sos-fin-tablewrap th{padding:12px 14px;background:#f7f0e5;color:#7e694c;white-space:nowrap}.sos-fin-tablewrap td{border-top:1px solid #f0e7da;padding:11px 14px;white-space:nowrap}.sos-fin-tablewrap tr:hover td{background:#fbf6ef}
.sos-fin-warnings,.sos-fin-error{border:1px solid #ebd3a8;padding:12px 15px;border-radius:12px;background:#fff6e5;color:#8a652d;margin-bottom:15px;font-size:12px}.sos-fin-warnings p{margin:4px 0}.sos-fin-error{background:#fff0ec;color:#a14435;border-color:#e8bcad}
.sos-fin-basis{margin-top:16px;padding:14px;background:#fffaf4;border:1px solid #eee2d1;border-radius:13px;font-size:12px;color:#806a4e}.sos-fin-basis p{margin:7px 0}.sos-fin-basis summary{cursor:pointer;font-weight:750}
@media(max-width:1000px){.sos-fin-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.sos-fin-reports{padding:12px}.sos-fin-kpis{grid-template-columns:1fr 1fr}.sos-fin-kpis strong{font-size:16px}.sos-fin-sectionhead{align-items:flex-start;flex-direction:column}.sos-fin-filters label{min-width:100%}}
@media print{body *{visibility:hidden!important}.sos-fin-reports,.sos-fin-reports *{visibility:visible!important}.sos-fin-reports{position:absolute!important;top:0;left:0;padding:0}.sos-fin-btn,.sos-fin-filters,.sos-fin-tabs{display:none!important}}
</style>
