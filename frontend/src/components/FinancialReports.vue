<script setup>
// SERVICING_FINANCIAL_REPORTS_618C
import {ref, computed, watch, onMounted} from 'vue'
const props = defineProps({
  fromDate: {type:String, required:true},
  toDate: {type:String, required:true},
  refreshKey: {type:Number, default:0}
})
const tabs = [
  {key:'sales', title:'Repair Sales'},
  {key:'collections', title:'Allocated Collections'},
  {key:'dues', title:'Customer Dues'},
  {key:'contribution', title:'Job Contribution'}
]
const columns = {
  sales: [
    ['invoice','Invoice'],['posting_date','Date'],['service_job','Service Job'],
    ['customer_name','Customer'],['net_sales','Net Sales (BDT)','money'],
    ['grand_total','Gross (BDT)','money'],['outstanding_now','Outstanding Now','money'],['status','Status']
  ],
  collections: [
    ['payment_entry','Payment Entry'],['posting_date','Payment Date'],
    ['invoice','Invoice'],['service_job','Service Job'],['customer','Customer'],
    ['mode_of_payment','Method'],['paid_to','Received In'],
    ['allocated_amount','Allocated (BDT)','money']
  ],
  dues: [
    ['invoice','Invoice'],['posting_date','Invoice Date'],['due_date','Due Date'],
    ['service_job','Service Job'],['customer_name','Customer'],
    ['grand_total','Invoice Total','money'],['outstanding_amount','Due Now','money'],['status','Status']
  ],
  contribution: [
    ['service_job','Service Job'],['customer','Customer'],['invoices','Invoices'],
    ['parts_revenue','Parts Revenue','money'],['labor_revenue','Labor Revenue','money'],
    ['net_revenue','Net Revenue','money'],['issued_parts_cost','Issued Parts Cost','money'],
    ['contribution','Contribution*','money']
  ]
}
const active = ref('sales')
const loading = ref(false)
const error = ref('')
const data = ref(null)
const rows = computed(()=>data.value?.rows || [])
const activeColumns = computed(()=>columns[active.value] || [])
const currency = v => v === null || v === undefined ? '—' :
  Number(v).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const display = (value, kind) => value === null || value === undefined || value === '' ? '—' :
  kind === 'money' ? '৳' + currency(value) : String(value).slice(0,140)
function message(obj){
  if(obj?._server_messages){
    try{const a=JSON.parse(obj._server_messages); const item=JSON.parse(a[a.length-1]);return item.message || 'Report unavailable'}catch(_){ }
  }
  return obj?.exception || obj?.message?.message || 'Report unavailable'
}
let requestNumber=0
async function refresh(){
  const requestId=++requestNumber
  if(!props.fromDate || !props.toDate || props.fromDate > props.toDate){
    error.value='Select a valid From and To date in the toolbar above.'
    data.value=null
    return
  }
  loading.value=true;error.value=''
  const u=new URL('/api/method/servicing_os.api.financial_reports.get_financial_report',window.location.origin)
  Object.entries({report:active.value,from_date:props.fromDate,to_date:props.toDate,limit:200}).forEach(([k,v])=>u.searchParams.set(k,String(v)))
  try{
    const response=await fetch(u,{credentials:'same-origin',headers:{Accept:'application/json'}})
    const json=await response.json()
    if(!response.ok || json.exc || json.exc_type) throw new Error(message(json))
    if(requestId===requestNumber) data.value=json.message
  }catch(e){
    if(requestId===requestNumber){data.value=null;error.value=e.message || 'Report unavailable'}
  }finally{if(requestId===requestNumber)loading.value=false}
}
function changeTab(tab){active.value=tab; refresh()}
function csvExport(){
  if(!rows.value.length)return
  const escapeCell=value=>{
    let str=String(value ?? '')
    if(/^[=+@\-\t\r]/.test(str))str="'"+str
    return '"'+str.replace(/"/g,'""')+'"'
  }
  const head=activeColumns.value.map(c=>escapeCell(c[1])).join(',')
  const lines=rows.value.map(row=>activeColumns.value.map(c=>escapeCell(row[c[0]])).join(','))
  const file=new Blob(['\uFEFF'+[head,...lines].join('\r\n')],{type:'text/csv;charset=utf-8'})
  const url=URL.createObjectURL(file)
  const link=document.createElement('a')
  link.href=url;link.download='amcl-'+active.value+'-'+props.fromDate+'-'+props.toDate+'.csv'
  document.body.appendChild(link);link.click();link.remove()
  window.setTimeout(()=>URL.revokeObjectURL(url),1500)
}
const linkFor=(key,value)=>{
  if(!value)return ''
  const path={invoice:'sales-invoice',payment_entry:'payment-entry',service_job:'service-job'}[key]
  return path?'/app/'+path+'/'+encodeURIComponent(value):''
}
watch([()=>props.fromDate,()=>props.toDate,()=>props.refreshKey], refresh)
onMounted(refresh)
</script>

<template>
  <section class="fin-root">
    <header class="fin-head">
      <div><p class="fin-eyebrow">ACCOUNTING / FINANCIAL REPORTS</p>
        <h2>Repair Finance</h2>
        <p>Posted ERPNext transactions · company currency BDT</p>
      </div>
      <div class="fin-actions">
        <button class="fin-secondary" type="button" :disabled="loading" @click="refresh">{{loading?'Loading…':'Refresh Table'}}</button>
        <button class="fin-secondary" type="button" :disabled="!rows.length" @click="csvExport">Export CSV</button>
      </div>
    </header>
    <nav class="fin-tabs" aria-label="Finance report type">
      <button v-for="t in tabs" :key="t.key" type="button" @click="changeTab(t.key)"
        :class="{'fin-current':active===t.key}" :aria-pressed="active===t.key">{{t.title}}</button>
    </nav>
    <p v-if="error" class="fin-error" role="alert">{{error}}</p>
    <template v-if="data">
      <div class="fin-cards" v-if="active==='sales'">
        <article><span>Net Repair Sales (ex tax)</span><strong>৳{{currency(data.summary.net_sales_ex_tax)}}</strong></article>
        <article><span>Gross Repair Sales</span><strong>৳{{currency(data.summary.gross_including_tax)}}</strong></article>
        <article><span>Outstanding Now (these invoices)</span><strong>৳{{currency(data.summary.outstanding_now)}}</strong></article>
      </div>
      <div class="fin-cards" v-else-if="active==='collections'">
        <article><span>Allocated Repair Collections</span><strong>৳{{currency(data.summary.allocated_to_repairs)}}</strong></article>
        <article><span>Allocated into Cash - AMCL</span><strong>৳{{currency(data.summary.allocated_to_cash_account)}}</strong></article>
      </div>
      <div class="fin-cards" v-else-if="active==='dues'">
        <article><span>Outstanding on Selected Invoices</span><strong>৳{{currency(data.summary.current_outstanding)}}</strong></article>
      </div>
      <div class="fin-cards" v-else>
        <article><span>Repair Jobs in Table</span><strong>{{data.summary.jobs_shown}}</strong></article>
        <article><span>Known-Valuation Jobs in Table</span><strong>{{data.summary.valuation_complete_shown}}</strong></article>
        <article><span>Contribution (Known Cost Only)</span><strong>৳{{currency(data.summary.contribution_known_shown)}}</strong></article>
      </div>
      <div class="fin-table-shell">
        <div class="fin-table-title"><div><h3>{{tabs.find(t=>t.key===active)?.title}}</h3>
          <p>{{data.from_date}} to {{data.to_date}}</p></div>
          <span>Showing {{rows.length}} / {{data.total}}</span>
        </div>
        <div class="fin-scroll">
          <table><thead><tr><th v-for="col in activeColumns" :key="col[0]">{{col[1]}}</th></tr></thead>
            <tbody>
              <tr v-for="(row,i) in rows" :key="(row.invoice||row.payment_entry||row.service_job||'r')+'-'+i">
                <td v-for="col in activeColumns" :key="col[0]">
                  <a v-if="linkFor(col[0],row[col[0]])" :href="linkFor(col[0],row[col[0]])" target="_blank" rel="noopener noreferrer">{{display(row[col[0]],col[2])}}</a>
                  <span v-else>{{display(row[col[0]],col[2])}}</span>
                </td>
              </tr>
              <tr v-if="!rows.length"><td :colspan="activeColumns.length" class="fin-empty">No posted transactions match the selected dates.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <p v-if="data.truncated" class="fin-warning">Only {{data.limit}} rows are shown; totals are based on the full selection where stated. Narrow the dates for complete CSV exports.</p>
      <p class="fin-note">{{data.note}}</p>
      <p v-if="active==='contribution'" class="fin-note">* Contribution is NOT net profit. It excludes technician wages, overhead and other costs.</p>
    </template>
    <p v-else-if="loading" class="fin-empty">Loading finance report…</p>
  </section>
</template>

<style scoped>
.fin-root,.fin-root *{box-sizing:border-box}
.fin-root{color:#483b2d;max-width:100%;padding:4px 0 14px}
.fin-head{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:14px 0 18px}
.fin-eyebrow{font-size:10px;font-weight:800;letter-spacing:1.25px;color:#a78555}
.fin-head h2{font-weight:800;font-size:23px;letter-spacing:-.4px;margin:5px 0}
.fin-head p:not(.fin-eyebrow){font-size:12px;color:#8a7b69}
.fin-actions{display:flex;gap:8px;flex-wrap:wrap}
.fin-secondary{height:42px;padding:0 14px;border:1px solid #ddd0bc;border-radius:10px;background:#fffdfa;color:#6b573f;cursor:pointer;font-size:12px;font-weight:750}
.fin-secondary:hover{background:#f4ebdf}.fin-secondary:disabled{opacity:.5;cursor:default}
.fin-tabs{display:flex;gap:5px;overflow:auto;padding:0 0 9px;margin:0 0 14px;border-bottom:1px solid #e5d9c9}
.fin-tabs button{border:1px solid transparent;background:transparent;color:#786854;white-space:nowrap;font-size:12px;font-weight:750;padding:11px 15px;border-radius:10px;cursor:pointer}
.fin-tabs button.fin-current{background:#eee1ce;border-color:#dec9ac;color:#503d2a}
.fin-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin:0 0 15px}
.fin-cards article{border:1px solid #e5d9c9;border-radius:13px;background:#fffdf9;padding:15px;display:flex;flex-direction:column;gap:8px;min-width:0}
.fin-cards article span{font-size:11px;color:#8d7c68}.fin-cards article strong{font-size:clamp(17px,2vw,24px);font-weight:800;overflow-wrap:anywhere}
.fin-table-shell{background:#fffefa;border:1px solid #e6daca;border-radius:14px;overflow:hidden}
.fin-table-title{padding:15px 18px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;border-bottom:1px solid #eee6db}
.fin-table-title h3{font-size:15px;font-weight:800}.fin-table-title p,.fin-table-title span{font-size:11px;color:#998874}
.fin-scroll{overflow:auto;max-height:620px}
.fin-scroll table{width:100%;min-width:920px;border-collapse:collapse;text-align:left;font-size:12px}
.fin-scroll th{position:sticky;top:0;z-index:1;background:#f7f0e6;color:#7f6a53;font-size:10px;padding:12px;white-space:nowrap;border-bottom:1px solid #e8dbcc}
.fin-scroll td{padding:12px;border-bottom:1px solid #f0e7dc;white-space:nowrap;vertical-align:top}
.fin-scroll tbody tr:hover{background:#fbf6ee}
.fin-scroll a{color:#74583a;font-weight:750;text-decoration:none}.fin-scroll a:hover{text-decoration:underline}
.fin-empty{text-align:center;padding:28px!important;font-size:12px;color:#92816a}
.fin-note{font-size:11px;line-height:1.65;color:#8d7d6a;margin-top:11px}
.fin-warning{margin-top:13px;background:#fff0d3;border-radius:9px;padding:11px 13px;color:#8f631c;font-size:12px}
.fin-error{background:#ffe7e3;color:#963e34;padding:12px 14px;border-radius:10px;font-size:12px;margin:12px 0}
@media(max-width:700px){.fin-head{align-items:flex-start}.fin-actions{width:100%}.fin-secondary{flex:1}.fin-cards{grid-template-columns:1fr}.fin-head h2{font-size:21px}}
</style>
