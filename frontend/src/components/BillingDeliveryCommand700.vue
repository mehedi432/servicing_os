<script setup>
// SOS_BILLING_DELIVERY_700 — non-destructive Counter billing & delivery.
// Existing CounterBilling654, ServiceInvoiceHub661 and ServiceJobsWorkspace own all
// POST/accounting/delivery workflows. Custom dashboard endpoints are read-only.
import { computed, nextTick, onMounted, onBeforeUnmount, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import InvoiceFinancialTotals from './InvoiceFinancialTotals.vue'
import ThreeLedger700 from './ThreeLedger700.vue'
import ServiceJobsWorkspace from './ServiceJobsWorkspace.vue'
import ServiceInvoiceHub661 from './ServiceInvoiceHub661.vue'
import UnifiedInvoicePrint684 from './UnifiedInvoicePrint684.vue'

const props = defineProps({ invoiceView: { type: String, default: '' } })
const emit = defineEmits(['handover', 'invoice-navigate'])
const bn = computed(() => String(unref(currentLanguage)||'en').toLowerCase().startsWith('bn'))
const tab = ref(props.invoiceView || 'overview')
const invoicePreview = ref('')
const tabs = [
  {key:'overview', en:'Overview',bn:'ওভারভিউ',icon:'◈'},
  {key:'checkout', en:'Billing Desk',bn:'বিলিং ডেস্ক',icon:'▣'},
  {key:'delivery', en:'Delivery Queue',bn:'ডেলিভারি তালিকা',icon:'▤'},
  {key:'service', en:'Service Invoices',bn:'সার্ভিস ইনভয়েস',icon:'▧'},
  {key:'register', en:'Invoice Register',bn:'ইনভয়েস রেজিস্টার',icon:'☷'},
  {key:'dues', en:'Payments & Dues',bn:'পেমেন্ট ও বকেয়া',icon:'৳'},
  {key:'reports', en:'Financial Reports',bn:'আর্থিক রিপোর্ট',icon:'▥'}
]
const rail = ref(null)
const startDate = ref(''), endDate = ref('')
const summary = ref(null), summaryError = ref(''), busy = ref(false), refreshed = ref('')
const registers = ref({invoices:{rows:[],total:0,page:1,has_next:false},payments:{rows:[],total:0,page:1,has_next:false}})
const regLoading=ref(false),regError=ref(''), query=ref(''), regPage=ref(1)
const dueMode=ref('due')
const catalog = ref([]), catalogError = ref(''), catalogLoading=ref(false)
const caption = computed(() => summary.value?.company || register.value.company ||
  (props.invoiceView ? '' : 'AL MODINA COMPUTERS'))
const currency = computed(() => summary.value?.currency || register.value.currency || 'BDT')
let requestVersion=0, controller=null, registerVersion=0, regController=null, catalogController=null
let debounce=null
const isoLocal=(d)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
function initDates(){const e=new Date();const s=new Date(e);s.setDate(e.getDate()-29);startDate.value=isoLocal(s);endDate.value=isoLocal(e)}
initDates()
const num=(v)=>Number(v||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const money=(v)=>v===null || v===undefined?'—':`${currency.value} ${num(v)}`
const dateFmt=(v)=>String(v||'—')
function parseError(data,status){
  try { const messages=JSON.parse(data?._server_messages||'[]');if(messages.length){const item=JSON.parse(messages[messages.length-1]);if(item?.message)return String(item.message).replace(/<[^>]*>/g,'').slice(0,240)} } catch {}
  return typeof data?.message==='string'?data.message.slice(0,240):data?.exception?String(data.exception).slice(0,200):`Request failed (HTTP ${status})`
}
async function get(method,params={},signal){
  const url=new URL('/api/method/servicing_os.api.billing_command_700.'+method,window.location.origin)
  Object.entries(params).forEach(([k,v])=>{if(v!==null&&v!==undefined&&v!=='')url.searchParams.set(k,String(v))})
  const response=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'},signal})
  const data=await response.json().catch(()=>({}))
  if(!response.ok||data.exc||data.exception||data.exc_type||!data.message||typeof data.message!=='object') throw Error(parseError(data,response.status))
  return data.message
}
const params=()=>({start_date:startDate.value,end_date:endDate.value})
async function refresh(){
  const seq=++requestVersion
  controller?.abort();controller=new AbortController();busy.value=true;summaryError.value=''
  try{
    const d=await get('get_overview',{...params(), include_delivery: props.invoiceView ? 0 : 1},controller.signal)
    if(seq!==requestVersion)return
    summary.value=d
    refreshed.value=new Date().toLocaleTimeString('en-BD',{hour:'numeric',minute:'2-digit'})
  }catch(e){if(e.name==='AbortError'||seq!==requestVersion)return;summary.value=null;summaryError.value=e.message||'Overview unavailable'}
  finally{if(seq===requestVersion)busy.value=false}
}
async function fetchRegister(kind,page=1){
  const seq=++registerVersion
  regController?.abort();regController=new AbortController();regLoading.value=true;regError.value=''
  try {
    const d=await get('get_register',{...params(),kind,page,q:query.value.trim()},regController.signal)
    if(seq!==registerVersion)return
    registers.value={...registers.value,[kind]:d};regPage.value=page
  }catch(e){if(e.name==='AbortError'||seq!==registerVersion)return;regError.value=e.message||'Register unavailable'}
  finally{if(seq===registerVersion)regLoading.value=false}
}
async function fetchCatalog(){
  if(catalog.value.length||catalogLoading.value)return
  catalogController?.abort();catalogController=new AbortController();catalogLoading.value=true;catalogError.value=''
  try{const d=await get('get_report_catalog',{},catalogController.signal);catalog.value=d.groups||[]}
  catch(e){if(e.name!=='AbortError')catalogError.value=e.message||'Report catalogue unavailable'}
  finally{catalogLoading.value=false}
}
function choose(key){
  if(!tabs.some(x=>x.key===key))return
  if (props.invoiceView && key !== props.invoiceView) {
    emit('invoice-navigate', key)
    return
  }
  tab.value=key;query.value='';regPage.value=1
  if(key==='register')fetchRegister('invoices',1)
  if(key==='dues'){dueMode.value='due';fetchRegister('dues',1)}
  if(key==='reports')fetchCatalog()
}
function onKeyboard(e,i){if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return
  e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?tabs.length-1:e.key==='ArrowRight'?(i+1)%tabs.length:(i-1+tabs.length)%tabs.length
  choose(tabs[n].key);nextTick(()=>rail.value?.querySelectorAll('[role="tab"]')?.[n]?.focus())
}
function applyDates(){if(!startDate.value||!endDate.value||startDate.value>endDate.value){summaryError.value='Select a valid date range.';return}
  summaryError.value = ''
  if (!props.invoiceView || tab.value === 'overview') refresh()
  if(tab.value==='register')fetchRegister('invoices',1)
  if(tab.value==='dues')fetchRegister(dueMode.value==='payments'?'payments':'dues',1)
}
function clearDates() {
  initDates()
  applyDates()
}
function dueChange(mode){dueMode.value=mode;regPage.value=1;query.value='';fetchRegister(mode==='payments'?'payments':'dues',1)}
const registerKind=computed(()=>tab.value==='dues'?(dueMode.value==='payments'?'payments':'dues'):'invoices')
const register=computed(()=>registers.value[registerKind.value]||{rows:[],total:0,page:1,has_next:false})
const visibleRows=computed(()=>register.value.rows)
const cards=computed(()=>{
  const s=summary.value
  return [
    {name:bn.value?'নিট বিক্রয়':'Net invoiced revenue',value:s?money(s.net_revenue):'—',hint:bn.value?'রিটার্নসহ, কর বাদে':'After returns · excluding taxes'},
    {name:bn.value?'ইনভয়েস মোট':'Gross invoiced',value:s?money(s.gross_invoiced):'—',hint:bn.value?'রিটার্নসহ, করসহ':'Including returns and taxes'},
    {name:bn.value?'বকেয়া':'Current outstanding',value:s?money(s.invoice_outstanding_current):'—',hint:bn.value?'নির্বাচিত ইনভয়েসের':'Selected invoices · current balance'},
    {name:bn.value?'আদায়':'Payment receipts',value:s?money(s.received_payments):'—',hint:bn.value?'পেমেন্ট এন্ট্রি; অগ্রিম অন্তর্ভুক্ত হতে পারে':'Submitted receipts · may include advances'},
    {name:bn.value?'রিটার্ন':'Returns',value:s?money(s.returns_gross):'—',hint:bn.value?'গ্রস রিটার্নের পরিমাণ':'Gross value of return invoices'},
    {name:bn.value?'ভ্যাট/কর':'Taxes on invoices',value:s?money(s.taxes):'—',hint:bn.value?'রিটার্নসহ নিট কর':'Net tax after return adjustments'},
  ]
})
function reportHref(name){return '/app/query-report/'+encodeURIComponent(name)}
function paymentHref(name){return '/app/payment-entry/'+encodeURIComponent(name)}
function exportCsv(){
  // Exports the visible 50-row server-verified page, not a misleading complete ledger.
  const rows=visibleRows.value
  if(!rows.length)return
  const keys=registerKind.value==='payments'?['name','date','party','type','mode','received','paid']:['name','date','party','type','status','net','gross','outstanding','due_date','service_job']
  const esc=v=>'"'+String(v??'').replace(/"/g,'""')+'"'
  const csv=[keys.join(','),...rows.map(row=>keys.map(k=>esc(row[k])).join(','))].join('\r\n')
  const url=URL.createObjectURL(new Blob(['\uFEFF',csv],{type:'text/csv;charset=utf-8'}))
  const a=document.createElement('a');a.href=url;a.download=`servicing-${registerKind.value}-${startDate.value}-${endDate.value}-page${regPage.value}.csv`;a.click()
  setTimeout(()=>URL.revokeObjectURL(url),1500)
}
function eventRefresh() {
  if (!props.invoiceView || tab.value === 'overview') refresh()
  if (tab.value === 'register' || tab.value === 'dues') fetchRegister(registerKind.value, 1)
}
const events=['servicing-os-reporting-stream-updated','servicing-os-invoice-payment-recorded','servicing-os-invoice-completed','servicing-os-invoice-draft-created','servicing-os-sale-completed','servicing-os-checkout-completed','servicing-os:service-invoice-created','servicing-os:service-job-updated']
onMounted(() => {
  if (props.invoiceView && tab.value !== 'overview') choose(tab.value)
  else refresh()
  events.forEach(name => window.addEventListener(name, eventRefresh))
})
onBeforeUnmount(()=>{++requestVersion;++registerVersion;controller?.abort();regController?.abort();catalogController?.abort();clearTimeout(debounce);events.forEach(name=>window.removeEventListener(name,eventRefresh))})
</script>

<template>
<section class="sos700-shell" :aria-label="invoiceView ? 'Invoices' : 'SERVICING OS Billing and Delivery Command Center'">
  <header class="sos700-top">
    <div v-if="invoiceView">
      <h2 v-if="tab === 'overview'">{{bn ? 'ইনভয়েস ওভারভিউ' : 'Invoice overview'}}</h2>
      <h2 v-else-if="tab === 'dues'">{{bn ? 'পেমেন্ট ও বকেয়া' : 'Payments & dues'}}</h2>
      <h2 v-else>{{bn ? 'আর্থিক রিপোর্ট' : 'Financial reports'}}</h2>
    </div>
    <div v-else><div class="sos700-eyebrow"><span class="sos700-dot"></span>SERVICING OS · {{bn?'বিলিং ও ডেলিভারি':'BILLING & DELIVERY'}} <span class="sos700-live">ERPNext connected</span></div>
      <h2>{{bn?'বিলিং ও ডেলিভারি কমান্ড সেন্টার':'Billing & delivery command center'}}</h2>
      <p>{{bn?'ইনভয়েস, গ্রাহক বকেয়া, পেমেন্ট, ডেলিভারি ও হিসাব রিপোর্ট — একটি কর্মক্ষেত্রে।':'One beautiful workspace for invoices, collections, customer balances, delivery and full accounting reports.'}}</p>
    </div>
    <div class="sos700-header-actions">
      <div v-if="caption" class="sos700-company" :title="caption">{{caption}}</div>
      <button v-if="tab !== 'reports' || !invoiceView" type="button" class="sos700-button" :disabled="busy || regLoading" @click="applyDates">{{busy?'Refreshing…':(bn?'↻ রিফ্রেশ':'↻ Refresh')}}</button>
      <button v-if="!invoiceView" type="button" class="sos700-button sos700-dark" @click="choose('checkout')">{{bn?'বিল তৈরি করুন':'＋ Billing desk'}}</button>
    </div>
  </header>

  <div v-if="tab !== 'reports' || !invoiceView" class="sos700-filters workspace-filters" aria-label="Financial date range">
    <label>{{bn?'শুরুর তারিখ':'From date'}}<input v-model="startDate" type="date" :max="endDate" /></label>
    <label>{{bn?'শেষ তারিখ':'To date'}}<input v-model="endDate" type="date" :min="startDate" /></label>
    <div class="filter-actions">
      <button type="button" @click="applyDates" :disabled="busy">{{bn?'প্রয়োগ':'Apply period'}}</button>
      <button type="button" class="sos700-clear" @click="clearDates" :disabled="busy">{{bn?'মুছুন':'Clear'}}</button>
    </div>
    <span class="sos700-timestamp">{{refreshed ? 'Refreshed '+refreshed : 'Reporting: submitted ERPNext documents'}} · {{currency}}</span>
  </div>
  <p v-if="summaryError" class="sos700-error" role="alert">{{summaryError}}</p>

  <div v-if="!invoiceView || tab === 'overview'" class="sos700-metrics" aria-label="Financial KPIs">
    <article v-for="(item,i) in cards" :key="i" class="sos700-metric">
      <span>{{item.name}}</span><strong>{{item.value}}</strong><small>{{item.hint}}</small>
    </article>
  </div>
  <div v-if="!invoiceView" ref="rail" class="sos700-tabs" role="tablist" aria-label="Billing and delivery sections">
    <button v-for="(item,i) in tabs" :key="item.key" type="button" role="tab" :aria-selected="tab===item.key"
      :tabindex="tab===item.key?0:-1" :class="{'sos700-active':tab===item.key}"
      @click="choose(item.key)" @keydown="onKeyboard($event,i)"><span aria-hidden="true">{{item.icon}}</span>{{bn?item.bn:item.en}}</button>
  </div>

  <div v-if="tab==='overview'" class="sos700-content" role="tabpanel">
    <section v-if="summary?.revenue_by_stream?.length" class="sos700-panel sos700-revenue" aria-label="Revenue by stream">
      <div class="sos700-panel-head">
        <div><h3>Revenue by stream</h3><p>Submitted Sales Invoices in the selected period. Net of returns, before tax.</p></div>
      </div>
      <dl class="sos700-revenue-grid">
        <div v-for="row in summary.revenue_by_stream" :key="row.stream">
          <dt>{{row.stream}}</dt><dd>{{money(row.net_revenue)}}</dd>
        </div>
      </dl>
      <p>Includes streams identified from historical invoices and reporting labels. Use General Ledger for posted income-account balances.</p>
    </section>
    <div :class="invoiceView ? 'sos700-invoice-overview' : 'sos700-overview-grid'">
      <article class="sos700-panel sos700-hero-chart">
        <div class="sos700-panel-head"><div><span class="sos700-kicker">REVENUE INTELLIGENCE</span><h3>{{bn ? 'আয়ের 3D বিশ্লেষণ' : invoiceView ? 'Daily invoice revenue' : 'Billing & delivery · Visual studio'}}</h3><p>Last 14 days of the selected date range · submitted invoices only</p></div><span class="sos700-chip">3D / 2D fallback</span></div>
        <ThreeLedger700 :series="summary?.daily || []" :currency="currency" :delivery="summary?.delivery || null" />
      </article>
      <article v-if="!invoiceView" class="sos700-panel sos700-operations">
        <div class="sos700-panel-head"><div><span class="sos700-kicker">WORKFLOW HEALTH</span><h3>{{bn?'ডেলিভারি নজরদারি':'Delivery pulse'}}</h3><p>Most recently modified accessible service jobs</p></div></div>
        <div class="sos700-flow"><div><span>Ready for handover</span><strong>{{summary?.delivery?.ready ?? '—'}}</strong></div><div><span>Delivered recently</span><strong>{{summary?.delivery?.delivered ?? '—'}}</strong></div><div><span>Jobs inspected</span><strong>{{summary?.delivery?.scanned ?? '—'}}</strong></div></div>
        <p class="sos700-micro">Sample of up to 200 jobs; not a complete historical delivery total.</p>
        <button class="sos700-button sos700-dark" type="button" @click="choose('delivery')">Open delivery queue →</button>
      </article>
    </div>
    <div class="sos700-lower-grid">
      <article class="sos700-panel"><div class="sos700-panel-head"><div><span class="sos700-kicker">AR WATCH</span><h3>Overdue on selected invoices</h3><p>Current unpaid amount past the due date</p></div></div><strong class="sos700-big">{{summary?money(summary.invoice_overdue_current):'—'}}</strong><button class="sos700-inline" type="button" @click="choose('dues')">Inspect invoices & payments →</button></article>
      <article class="sos700-panel"><div class="sos700-panel-head"><div><span class="sos700-kicker">BOOKS OF ACCOUNT</span><h3>Financial statements</h3><p>Official ERPNext reports, not estimated figures</p></div></div><p class="sos700-report-summary">P&L · Balance Sheet · Cash Flow · General Ledger · Trial Balance · VAT · AR/AP · Margin</p><button class="sos700-inline" type="button" @click="choose('reports')">Explore all financial reports →</button></article>
    </div>
    <div class="sos700-note"><strong>Accounting basis</strong><p v-for="(line,i) in summary?.notes || []" :key="i">{{line}}</p><p v-if="!summary">KPIs are unavailable until ERPNext returns authorized report data. No placeholder financial amounts are shown.</p></div>
    <InvoiceFinancialTotals v-if="summary?.financial_totals && !busy && !summaryError" class="sos700-financials" :totals="summary.financial_totals" />
  </div>

  <div v-else-if="tab==='checkout'" class="sos700-content" role="tabpanel">
    <div class="sos700-workhead"><div><span class="sos700-kicker">COUNTER INVOICING</span><h3>Invoice creation & checkout</h3><p>Original billing desk retained — drafts, complete invoice, discounts, print and reprint.</p></div></div>
    <div class="sos700-existing"><slot name="legacy"><div class="sos700-error">The existing Counter billing component was not mounted. Re-run installer verification.</div></slot></div>
  </div>

  <div v-else-if="tab==='delivery'" class="sos700-content" role="tabpanel">
    <div class="sos700-workhead"><div><h3>Delivery operations</h3><p>Select a job that is ready to deliver and open its Delivery Desk.</p></div><button type="button" class="sos700-button" @click="choose('service')">View linked invoices</button></div>
    <div class="sos700-existing"><ServiceJobsWorkspace counter-scope="ready" guided-handover @handover="emit('handover', $event)" /></div>
  </div>

  <div v-else-if="tab==='service'" class="sos700-content" role="tabpanel">
    <div class="sos700-workhead"><div><span class="sos700-kicker">SERVICE INVOICES</span><h3>Job-linked billing & receipts</h3><p>Find an actual job, create an eligible invoice, print or reprint.</p></div></div>
    <div class="sos700-existing"><ServiceInvoiceHub661 /></div>
  </div>

  <div v-else-if="tab==='register'||tab==='dues'" class="sos700-content" role="tabpanel">
    <div class="sos700-workhead"><div><span class="sos700-kicker">{{tab==='register'?'FINANCIAL REGISTER':'COLLECTIONS & CREDIT CONTROL'}}</span><h3>{{tab==='register'?'Invoice register':'Payments & customer dues'}}</h3><p>{{tab==='register'?'Authorized submitted invoices, returns, taxes-excluded net values and current dues.':'Balance investigation and payment entries; advance receipts are not treated as invoice revenue.'}}</p></div></div>
    <div v-if="tab==='dues'" class="sos700-subtabs"><button type="button" :class="{current:dueMode==='due'}" @click="dueChange('due')">Unpaid invoices</button><button type="button" :class="{current:dueMode==='payments'}" @click="dueChange('payments')">Payment entries</button></div>
    <div class="sos700-toolbar"><form @submit.prevent="fetchRegister(registerKind,1)"><input v-model="query" type="search" placeholder="Search invoice, customer, payment or job…" aria-label="Search finance register"/><button type="submit" :disabled="regLoading">Search</button></form><span>{{register.total}} matching records · showing page {{register.page}}</span><button type="button" @click="exportCsv" :disabled="!visibleRows.length">Export visible page CSV ↓</button></div>
    <p v-if="regError" class="sos700-error" role="alert">{{regError}}</p>
    <div v-if="regLoading" class="sos700-loading">Loading authorized transactions from ERPNext…</div>
    <div v-else-if="!visibleRows.length" class="sos700-loading">No matching records on this page. Check date range or use search.</div>
    <div v-else class="sos700-scroll"><table><thead><tr v-if="registerKind!=='payments'"><th>Invoice</th><th>Date / due</th><th>Customer</th><th>Type</th><th>Status</th><th>Net</th><th>Gross</th><th>Outstanding now</th></tr><tr v-else><th>Payment</th><th>Date</th><th>Party</th><th>Type</th><th>Method</th><th>Received</th><th>Paid</th></tr></thead>
      <tbody><tr v-for="record in visibleRows" :key="record.name"><template v-if="registerKind!=='payments'"><td><button type="button" class="sos700-invoice-link" @click="invoicePreview = record.name">{{record.name}}</button><small v-if="record.service_job">Job {{record.service_job}}</small></td><td>{{record.date}}<small>Due {{record.due_date||'—'}}</small></td><td>{{record.party}}</td><td>{{record.type}}</td><td>{{record.status}}</td><td class="sos700-number">{{money(record.net)}}</td><td class="sos700-number">{{money(record.gross)}}</td><td class="sos700-number">{{money(record.outstanding)}}</td></template>
        <template v-else><td><a :href="paymentHref(record.name)" target="_blank" rel="noopener noreferrer">{{record.name}}</a></td><td>{{record.date}}</td><td>{{record.party||'—'}}</td><td>{{record.type}}</td><td>{{record.mode||'—'}}</td><td class="sos700-number">{{money(record.received)}}</td><td class="sos700-number">{{money(record.paid)}}</td></template>
      </tr></tbody></table></div>
    <div class="sos700-pager"><button type="button" :disabled="regLoading||regPage<=1" @click="fetchRegister(registerKind,regPage-1)">← Previous</button><span>Page {{regPage}} · 50 records per page</span><button type="button" :disabled="regLoading||!register.has_next" @click="fetchRegister(registerKind,regPage+1)">Next →</button></div>
    <p class="sos700-micro">Invoice register includes submitted transactions within the selected posting dates. Outstanding amounts are current balances, not historical balances at the reporting date. Customer aging and bank reconciliation belong in official financial reports.</p>
  </div>

  <div v-else-if="tab==='reports'" class="sos700-content" role="tabpanel">
    <div class="sos700-workhead"><div><span class="sos700-kicker">AUTHORITATIVE ERPNext REPORTING</span><h3 v-if="!invoiceView">Financial reports library</h3><p>Accounting, taxation, inventory valuation, customer dues and management reports. Availability depends on your installed ERPNext reports and permissions.</p></div><button class="sos700-button" type="button" @click="catalog=[];fetchCatalog()">↻ Refresh catalogue</button></div>
    <div v-if="!invoiceView" class="sos700-note"><strong>Why official reports?</strong><p>Balance Sheet, cash flow, profit and loss, trial balance, bank reconciliation, AR/AP aging and tax must use the ERPNext accounting ledger. The links below open real installed reports with normal ERPNext permission checks and financial filters.</p></div>
    <div v-if="catalogLoading" class="sos700-loading">Checking installed ERPNext reports…</div>
    <p v-if="catalogError" class="sos700-error" role="alert">{{catalogError}}</p>
    <div class="sos700-report-grid"><article v-for="group in catalog" :key="group.category" class="sos700-panel"><h4>{{group.category}}</h4><div class="sos700-report-links"><div v-for="report in group.reports" :key="report.name" class="sos700-report-link"><span>{{report.name}}</span><a v-if="report.available" :href="reportHref(report.name)" target="_blank" rel="noopener noreferrer" :aria-label="'Open '+report.name">Open ↗</a><span v-else class="sos700-unavailable">Not installed</span></div></div></article></div>
    <p v-if="!invoiceView" class="sos700-micro">The report library lists common financial reports; missing reports are explicitly identified instead of shown as working. You can also access additional installed reports from your existing ERPNext Reports workspace.</p>
  </div>
  <UnifiedInvoicePrint684 v-if="invoicePreview" :key="invoicePreview" :invoice-name="invoicePreview" submit-draft
    @close="invoicePreview = ''" />
</section>
</template>

<style scoped src="./workspaceFilters.css"></style>
<style scoped>
.sos700-invoice-link{padding:0;border:0;background:none;color:var(--os-accent,#825b3e);text-decoration:underline;cursor:pointer;font:inherit;font-weight:740}
.sos700-revenue{margin-bottom:12px}
.sos700-revenue-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(132px,100%),1fr));gap:8px;margin:0 0 12px}
.sos700-revenue-grid div{padding:9px 11px;border:1px solid var(--edge);border-radius:9px;background:var(--os-surface,#fffdfa);min-width:0}
.sos700-revenue-grid dt{font-size:11px;color:var(--os-strong,#755844);font-weight:680}
.sos700-revenue-grid dd{margin:4px 0 0;font-weight:750;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}

.sos700-invoice-overview{min-width:0;margin-bottom:16px}
.sos700-shell{--ink:var(--os-ink,#332920);--muted:var(--os-muted,#7b6a5c);--edge:var(--os-border,#e8ded4);--accent:#896549;--surface:var(--os-surface,#fffdf9);--bg:var(--os-canvas,#faf6f1);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;line-height:1.45;padding:22px 22px 32px;background:var(--bg);min-width:0}
.sos700-top{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px;margin-bottom:16px}.sos700-top h2{font-size:clamp(23px,2.6vw,31px);letter-spacing:-.04em;font-weight:760;line-height:1.2;margin:7px 0 9px}.sos700-top p{font-size:12px;color:var(--muted);margin:0;max-width:730px}.sos700-eyebrow{display:flex;align-items:center;gap:8px;font-size:10px;font-weight:800;letter-spacing:.15em;color:var(--os-muted,#9b795c)}.sos700-dot{background:var(--os-muted,#ae8966);border-radius:50%;width:7px;height:7px}.sos700-live{background:var(--os-border,#e9e0d5);border-radius:50px;padding:3px 7px;letter-spacing:0;font-size:10px;color:var(--os-muted,#715842)}.sos700-header-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.sos700-company{font-size:10px;font-weight:740;max-width:175px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sos700-button,.sos700-filters button,.sos700-toolbar button,.sos700-pager button{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--os-border,#d5c4b4);border-radius:9px;background:var(--os-surface,#fffefa);color:var(--os-muted,#5c4839);min-height:34px;font-size:11px;font-weight:700;padding:7px 12px;cursor:pointer}.sos700-button:hover,.sos700-filters button:hover,.sos700-toolbar button:hover,.sos700-pager button:hover{border-color:var(--os-accent,#9b7556);background:var(--os-tint,#fbf5ef)}.sos700-button:disabled,.sos700-toolbar button:disabled,.sos700-pager button:disabled{opacity:.5;cursor:default}.sos700-dark{background:var(--os-ink,#4b372b);color:white;border-color:var(--os-ink,#4b372b)}.sos700-dark:hover{background:var(--os-strong,#694b39);color:white}.sos700-filters{display:flex;align-items:end;gap:9px;flex-wrap:wrap;margin-bottom:14px}.sos700-filters label{font-size:10px;display:grid;gap:4px;font-weight:700;color:var(--os-muted,#746253)}.sos700-filters input{height:34px;border:1px solid var(--os-border,#ddcfc2);border-radius:8px;background:var(--os-surface,#fffefa);color:var(--os-ink,#49382c);padding:0 10px;font:inherit}.sos700-timestamp{font-size:10px;color:var(--os-muted,#978575);margin-left:auto}.sos700-error{border:1px solid #e9c6be;background:#fff5f2;color:#ab4b3d;border-radius:10px;padding:10px;margin:0 0 12px}.sos700-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-bottom:18px}.sos700-metric{background:var(--os-surface,#fffdfa);border:1px solid var(--edge);border-radius:13px;padding:13px 15px;min-width:0;box-shadow:0 6px 15px #48352608}.sos700-metric span,.sos700-metric small{display:block;color:var(--os-muted,#827162)}.sos700-metric span{font-size:11px;font-weight:680}.sos700-metric strong{display:block;font-size:clamp(17px,1.6vw,23px);font-weight:760;letter-spacing:-.04em;margin:5px 0;overflow-wrap:anywhere}.sos700-metric small{font-size:10px;line-height:1.3}.sos700-tabs{display:flex;align-items:center;gap:4px;overflow-x:auto;scrollbar-width:thin;border-bottom:1px solid var(--edge);margin-bottom:18px;padding:3px 0}.sos700-tabs button{flex-shrink:0;display:inline-flex;align-items:center;gap:7px;padding:10px 12px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--os-muted,#807163);font-size:11px;cursor:pointer;font-weight:680;white-space:nowrap}.sos700-tabs button span{font-size:15px}.sos700-tabs button:hover{color:var(--os-strong,#5f4230);background:var(--os-tint,#f0e8df)}.sos700-tabs button.sos700-active{color:var(--os-strong,#5a3d2b);border-bottom-color:var(--os-strong,#79583d);background:var(--os-tint,#f1e6d9)}.sos700-tabs button:focus-visible,.sos700-shell a:focus-visible,.sos700-shell button:focus-visible{outline:2px solid var(--os-muted,#aa7e58);outline-offset:2px}.sos700-content{min-width:0}.sos700-overview-grid{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(260px,.9fr);gap:12px;margin-bottom:12px}.sos700-lower-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:12px}.sos700-panel{background:var(--surface);border:1px solid var(--edge);border-radius:15px;padding:17px;box-shadow:0 4px 16px #4b372808;min-width:0}.sos700-panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:14px}.sos700-panel h3,.sos700-workhead h3{margin:5px 0 3px;font-size:17px;letter-spacing:-.02em;font-weight:740}.sos700-panel h4{font-size:13px;margin:0 0 14px}.sos700-panel p,.sos700-workhead p{font-size:11px;color:var(--os-muted,#8e7b6c);margin:0}.sos700-kicker{font-size:9px;letter-spacing:.13em;color:var(--os-muted,#ac8664);font-weight:820}.sos700-chip{color:var(--os-muted,#715741);background:var(--os-tint,#f0e5d9);border-radius:99px;padding:5px 9px;white-space:nowrap;font-size:9px}.sos700-flow{display:grid;gap:9px;margin-bottom:16px}.sos700-flow>div{border:1px solid var(--os-border,#ece1d6);border-radius:10px;padding:11px;display:flex;justify-content:space-between;gap:8px}.sos700-flow span{color:var(--os-muted,#857160)}.sos700-flow strong{font-size:17px}.sos700-operations .sos700-button{margin-top:12px;width:100%}.sos700-micro{color:var(--os-muted,#938477);font-size:10px;line-height:1.55}.sos700-big{display:block;font-size:30px;letter-spacing:-.04em;margin:14px 0}.sos700-inline{border:0;background:none;padding:0;color:var(--os-accent,#805d44);font-size:11px;font-weight:700;cursor:pointer}.sos700-report-summary{padding:12px 0;line-height:1.9}.sos700-note{background:var(--os-tint,#f1e9e0);border:1px solid var(--os-border,#e4d7ca);border-radius:12px;padding:13px 16px;color:var(--os-muted,#705c4c);margin-top:13px}.sos700-note strong{font-size:11px}.sos700-note p{font-size:10px;line-height:1.65;margin:4px 0}.sos700-workhead{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:14px}.sos700-existing{min-width:0;background:var(--os-surface,#fffefa);border:1px solid var(--edge);border-radius:14px;padding:8px}.sos700-toolbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin:13px 0}.sos700-toolbar form{display:flex;gap:6px;flex:1;min-width:250px}.sos700-toolbar input{border:1px solid var(--os-border,#dfd2c5);border-radius:9px;padding:8px 10px;min-width:100px;flex:1;background:var(--os-surface,#fffefa);font-size:11px}.sos700-toolbar span{font-size:10px;color:var(--os-muted,#897666)}.sos700-scroll{border:1px solid var(--edge);border-radius:12px;overflow-x:auto;background:var(--os-surface,#fffefa)}.sos700-scroll table{width:100%;min-width:760px;border-collapse:collapse;text-align:left;font-size:11px}.sos700-scroll th{background:var(--os-tint,#f4ece3);color:var(--os-muted,#6e5847);letter-spacing:.025em;font-size:10px;text-transform:none;font-weight:760}.sos700-scroll th,.sos700-scroll td{padding:10px 11px;border-bottom:1px solid var(--os-border,#eee4db);vertical-align:top}.sos700-scroll tr:hover td{background:var(--os-surface,#fdfaf6)}.sos700-scroll a{color:var(--os-accent,#825b3e);text-decoration:none;font-weight:740}.sos700-scroll small{display:block;color:var(--os-muted,#988675);font-size:10px;margin-top:3px}.sos700-number{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.sos700-loading{padding:32px 12px;text-align:center;color:var(--os-muted,#907969);border:1px dashed var(--os-border,#d9c8b9);border-radius:12px}.sos700-pager{display:flex;justify-content:flex-end;align-items:center;gap:10px;margin:10px 0}.sos700-pager span{font-size:10px;color:var(--os-muted,#8e7c6f)}.sos700-subtabs{display:flex;gap:6px;margin:12px 0}.sos700-subtabs button{border:1px solid var(--os-border,#dacbbc);background:var(--os-surface,#fffefa);border-radius:8px;padding:8px 12px;font-size:11px;color:var(--os-muted,#6f5a48);cursor:pointer}.sos700-subtabs button.current{background:var(--os-strong,#5f4534);border-color:var(--os-strong,#5f4534);color:white}.sos700-report-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}.sos700-report-links{display:grid;gap:0}.sos700-report-link{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--os-border,#eee5dc);font-size:11px}.sos700-report-link:last-child{border-bottom:0}.sos700-report-link a{flex-shrink:0;border-radius:7px;background:var(--os-tint,#f0e6db);color:var(--os-strong,#70503b);text-decoration:none;padding:6px 9px;font-weight:700}.sos700-unavailable{font-size:10px;color:var(--os-muted,#a29284);white-space:nowrap}
@media(max-width:1000px){.sos700-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.sos700-overview-grid{grid-template-columns:1fr}}
@media(max-width:680px){.sos700-shell{padding:12px}.sos700-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.sos700-metric{padding:11px}.sos700-metric strong{font-size:16px}.sos700-lower-grid,.sos700-report-grid{grid-template-columns:1fr}.sos700-timestamp{margin:0}.sos700-header-actions{width:100%}.sos700-panel{padding:12px}}
.sos700-financials{margin-top:12px;background:var(--os-surface,#fffdf9)}
.sos700-filters.workspace-filters input{height:var(--filter-height)}
.sos700-filters.workspace-filters .filter-actions button{background:var(--os-accent,#785238);color:#fff;border:1px solid var(--os-accent,#785238)}
.sos700-filters.workspace-filters .filter-actions .sos700-clear{background:var(--os-surface,#fffdf9);color:var(--os-ink,#38291f);border-color:var(--os-border,#e5d6c4)}
@media print{.sos700-header-actions,.sos700-tabs,.sos700-filters,.sos700-button,.sos700-pager,.sos700-toolbar button{display:none!important}.sos700-shell{background:white}.sos700-panel,.sos700-metric{box-shadow:none;break-inside:avoid}}
</style>
