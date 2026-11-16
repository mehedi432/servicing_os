<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
const granularity = ref('daily')
const fromDate = ref(''), toDate = ref('')
const report = ref(null), loading = ref(false), error = ref('')
const bn = computed(() => currentLanguage.value === 'bn')
const freq = [
  { value:'daily', en:'Daily', bn:'দৈনিক' },
  { value:'weekly', en:'Weekly', bn:'সাপ্তাহিক' },
  { value:'monthly', en:'Monthly', bn:'মাসিক' },
  { value:'yearly', en:'Yearly', bn:'বার্ষিক' }
]
const money = v => v === null || v === undefined ? '—' : '৳ ' + Number(v).toLocaleString('en-BD',{ minimumFractionDigits:2, maximumFractionDigits:2 })
const pct = v => v === null || v === undefined ? '—' : Number(v).toFixed(2) + '%'
const rows = computed(() => report.value?.rows || [])
const maxSales = computed(() => Math.max(1, ...rows.value.map(x => Math.abs(x.net_sales || 0))))
const total = computed(() => report.value?.totals || {})
const bestPeriod = computed(() => rows.value.reduce((best, row) => !best || Number(row.net_sales)>Number(best.net_sales) ? row : best, null))
const lastPeriod = computed(() => rows.value[0] || null)
const prevPeriod = computed(() => rows.value[1] || null)
const changePct = computed(() => { const before=Number(prevPeriod.value?.net_sales||0); if(before<=0 || !lastPeriod.value) return null; return (Number(lastPeriod.value.net_sales)-before)*100/before })
const restrictedMoney = v => report.value?.pnl_visible ? money(v) : 'Restricted'
const restrictedPct = v => report.value?.pnl_visible ? pct(v) : 'Restricted'
const rangeError = computed(() => {
 if(Boolean(fromDate.value) !== Boolean(toDate.value)) return 'Choose both start and end dates.'
 if(fromDate.value && toDate.value && fromDate.value > toDate.value) return 'Start date must not be after end date.'
 return ''
})
function localDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function setShortcut(which){
 const today=new Date()
 granularity.value=which==='today'?'daily':'monthly'
 fromDate.value=which==='today'?localDate(today):localDate(new Date(today.getFullYear(),today.getMonth(),1))
 toDate.value=localDate(today)
 reload()
}
function resetRange(){fromDate.value='';toDate.value='';reload()}
let latestRequest=0
let controller=null
onBeforeUnmount(()=>{latestRequest++;controller?.abort()})
async function reload(){
 if(rangeError.value){latestRequest++;controller?.abort();loading.value=false;report.value=null;error.value=rangeError.value;return}
 const request=++latestRequest
 controller?.abort()
 controller=new AbortController()
 loading.value=true;error.value=''
 try {
  const params=new URLSearchParams({granularity:granularity.value})
  if(fromDate.value)params.set('from_date',fromDate.value)
  if(toDate.value)params.set('to_date',toDate.value)
  const response=await fetch('/api/method/servicing_os.api.sales_analytics.period_report?'+params,
    {credentials:'same-origin',signal:controller.signal})
  const payload=await response.json()
  if(!response.ok || payload.exc || payload.exception)throw new Error(typeof payload.message==='string'?payload.message:payload.exception||'Unable to load report')
  if(request===latestRequest)report.value=payload.message
 } catch(e) {
  if(request===latestRequest && e.name!=='AbortError'){report.value=null;error.value=e.message||String(e)}
 } finally {if(request===latestRequest)loading.value=false}
}
function setPeriod(value){granularity.value=value;fromDate.value='';toDate.value='';reload()}
const csvValue = x => '"' + String(x ?? '').replace(/"/g,'""') + '"'
function exportCSV(){
  if(!report.value) return
  const names=['Period','Sales before returns','Returns','Net sales','COGS','Gross profit','P&L income','Total expenses','Net profit','Net profit %']
  const keys=['label','sales','returns','net_sales','cogs','gross_profit','pnl_income','expenses','net_profit','margin_pct']
  const data=[names.map(csvValue).join(','),...rows.value.map(r=>keys.map(k=>csvValue(report.value.pnl_visible || !['cogs','gross_profit','pnl_income','expenses','net_profit','margin_pct'].includes(k)?r[k]:'' )).join(','))].join('\r\n')
  const url=URL.createObjectURL(new Blob(['\ufeff'+data],{type:'text/csv;charset=utf-8'}))
  const link=document.createElement('a');link.href=url;link.download='amcl-sales-pnl-'+granularity.value+'.csv';link.click();URL.revokeObjectURL(url)
}
onMounted(reload)
</script>
<template>
  <div class="srp">
    <header class="srp-header">
      <div><div class="srp-kicker">AL MODINA COMPUTERS LIMITED · FINANCIAL PERFORMANCE</div><h2>{{bn?'বিক্রয় ও লাভ-ক্ষতির প্রতিবেদন':'Sales & Profit / Loss'}}</h2><p>{{bn?'বাস্তব ইনভয়েস ও জেনারেল লেজারের তথ্য':'Real submitted invoices and posted general-ledger transactions'}}</p></div>
      <button class="srp-button" :disabled="!report || loading" @click="exportCSV">{{bn?'CSV ডাউনলোড':'Export CSV'}}</button>
    </header>
    <div class="srp-panel srp-controls">
      <div class="srp-tabs" role="group" aria-label="Reporting period">
        <button v-for="f in freq" :key="f.value" type="button" :class="{selected:granularity===f.value}" :aria-pressed="granularity===f.value" @click="setPeriod(f.value)">{{bn?f.bn:f.en}}</button>
      </div>
      <label>From<input v-model="fromDate" type="date" /></label><label>To<input v-model="toDate" type="date" /></label>
      <button class="srp-button srp-dark" :disabled="!!rangeError" @click="reload">{{loading?'Loading…':'Apply dates'}}</button>
      <button class="srp-button" @click="resetRange">Default range</button>
      <div class="srp-quick" role="group" aria-label="Quick date ranges"><button class="srp-button" @click="setShortcut('today')">{{bn?'আজ':'Today'}}</button><button class="srp-button" @click="setShortcut('month')">{{bn?'এই মাস':'This month'}}</button></div>
    </div>
    <p v-if="rangeError" role="alert" class="srp-error">{{rangeError}}</p>
    <div v-if="error && error!==rangeError" role="alert" class="srp-error">{{error}} <button class="srp-button" @click="reload">Retry</button></div>
    <div v-if="loading" class="srp-loading" role="status" aria-live="polite"><span class="srp-spinner" aria-hidden="true"></span>{{bn?'হিসাব লোড হচ্ছে…':'Loading submitted invoices and ledger data…'}}</div>
    <div v-if="report && !loading">
      <div class="srp-context">{{report.from_date}} — {{report.to_date}} <span>· {{report.currency}} · {{report.invoice_rows}} invoice/credit note rows</span></div>
      <div v-if="!Number(report.invoice_rows)" class="srp-empty">{{bn?'এই সময়ে কোনো জমা দেওয়া বিক্রয় ইনভয়েস নেই।':'No submitted sales invoices in this range. Try another period or date filter.'}}</div>
      <div class="srp-highlights" v-if="rows.length">
        <div><small>{{bn?'সর্বশেষ সময়':'Latest period'}}</small><strong>{{lastPeriod?.label||'—'}}</strong><span>{{money(lastPeriod?.net_sales)}} net sales</span></div>
        <div><small>{{bn?'সেরা সময়':'Best sales period'}}</small><strong>{{bestPeriod?.label||'—'}}</strong><span>{{money(bestPeriod?.net_sales)}} net sales</span></div>
        <div><small>{{bn?'পরিবর্তন':'Vs previous period'}}</small><strong :class="{'negative':changePct<0}">{{changePct===null?'—':(changePct>=0?'+':'')+pct(changePct)}}</strong><span>{{changePct===null?'Not comparable when prior sales are zero':'Net sales change'}}</span></div>
      </div>
      <div class="srp-cards">
        <div><small>Gross sales</small><strong>{{money(total.sales)}}</strong><span>Submitted invoice net amounts before returns</span></div>
        <div><small>Returns</small><strong>{{money(total.returns)}}</strong><span>Submitted credit notes</span></div>
        <div class="featured"><small>Net sales</small><strong>{{money(total.net_sales)}}</strong><span>Excludes sales tax</span></div>
        <div><small>Cost of goods sold</small><strong>{{report.pnl_visible?money(total.cogs):'Restricted'}}</strong><span>Posted COGS ledger accounts</span></div>
        <div><small>Gross profit</small><strong>{{restrictedMoney(total.gross_profit)}}</strong><span>Net sales less posted COGS</span></div>
        <div><small>Net P&L</small><strong :class="{'negative':report.pnl_visible && total.net_profit<0}">{{restrictedMoney(total.net_profit)}}</strong><span>All P&L income minus all expenses</span></div>
        <div><small>Net profit %</small><strong :class="{'negative':report.pnl_visible && total.margin_pct<0}">{{restrictedPct(total.margin_pct)}}</strong><span>Net P&L / net sales × 100</span></div>
      </div>
      <div v-if="!report.pnl_visible" class="srp-warning">P&L unavailable: {{report.pnl_note}}. Sales remain visible; profit is never presented as zero when data is missing.</div>
      <div class="srp-panel">
        <div class="srp-section-head"><h3>{{bn?'পিরিয়ড অনুসারে বিক্রয় ও লাভ':'Period-by-period performance'}}</h3><span>{{rows.length}} periods</span></div>
        <div class="srp-scroll-hint">{{bn?'সমস্ত কলাম দেখতে পাশে স্ক্রল করুন':'Scroll horizontally for the full breakdown'}} ↔</div><div class="srp-table-scroll" role="region" aria-label="Sales and profit by period" tabindex="0"><table><thead><tr><th>Period</th><th>Sales</th><th>Returns</th><th>Net sales</th><th>COGS</th><th>Gross profit</th><th>P&L income</th><th>Expenses</th><th>Net P&L</th><th>Profit %</th></tr></thead>
          <tbody><tr v-for="r in rows" :key="r.period_key">
            <td class="srp-period">{{r.label}}<div class="srp-track"><div :style="{width:(Math.abs(r.net_sales||0)/maxSales*100)+'%'}"></div></div></td>
            <td>{{money(r.sales)}}</td><td>{{money(r.returns)}}</td><td class="srp-em">{{money(r.net_sales)}}</td>
            <td>{{restrictedMoney(r.cogs)}}</td><td>{{restrictedMoney(r.gross_profit)}}</td><td>{{restrictedMoney(r.pnl_income)}}</td><td>{{restrictedMoney(r.expenses)}}</td><td :class="{'negative':report.pnl_visible && r.net_profit<0}">{{restrictedMoney(r.net_profit)}}</td><td :class="{'negative':report.pnl_visible && r.margin_pct<0}">{{restrictedPct(r.margin_pct)}}</td>
          </tr></tbody>
          <tfoot><tr><th>TOTAL</th><th>{{money(total.sales)}}</th><th>{{money(total.returns)}}</th><th>{{money(total.net_sales)}}</th><th>{{restrictedMoney(total.cogs)}}</th><th>{{restrictedMoney(total.gross_profit)}}</th><th>{{restrictedMoney(total.pnl_income)}}</th><th>{{restrictedMoney(total.expenses)}}</th><th>{{restrictedMoney(total.net_profit)}}</th><th>{{restrictedPct(total.margin_pct)}}</th></tr></tfoot>
        </table></div>
      </div>
      <p class="srp-note">{{report.basis}} Accounting accuracy depends on complete stock valuation, expense, opening and closing postings. For statutory or audited financial statements use the native ERPNext Profit and Loss report.</p>
    </div>
  </div>
</template>
<style scoped>
.srp{color:#49392b}.srp-header{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:8px 0 15px}.srp-kicker{letter-spacing:.13em;color:#98785a;font-weight:850;font-size:10px}.srp-header h2{font-size:24px;font-weight:850;margin:6px 0 4px}.srp-header p{font-size:12px;color:#897a6a;margin:0}.srp-panel{background:#fffdfa;border:1px solid #e5d9ca;border-radius:15px;padding:16px;margin:15px 0;box-shadow:0 4px 18px #5940210b}.srp-controls{display:flex;flex-wrap:wrap;align-items:end;gap:10px}.srp-controls label{display:flex;flex-direction:column;font-size:11px;gap:5px;font-weight:750;color:#806d58}.srp-controls input{height:38px;border:1px solid #dfd2bf;border-radius:9px;background:white;color:#49392b;padding:0 10px;font-size:12px}.srp-tabs{display:flex;border:1px solid #e1d5c6;background:#f5efe6;border-radius:10px;padding:4px;gap:3px;flex-wrap:wrap}.srp-tabs button{font-size:12px;cursor:pointer;padding:8px 11px;border:0;border-radius:7px;background:transparent;color:#796551;font-weight:750}.srp-tabs .selected{color:#fffdfa;background:#795b41;box-shadow:0 1px 5px #4f352326}.srp-button{border:1px solid #dfd1be;border-radius:9px;min-height:38px;cursor:pointer;background:#f6eee3;color:#624a33;font-size:12px;padding:7px 12px;font-weight:750}.srp-dark{background:#795b41;border-color:#795b41;color:#fff}.srp-button:disabled{opacity:.5;cursor:not-allowed}.srp-context{color:#93816c;font-size:12px;margin:15px 0 6px}.srp-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:10px}.srp-cards>div{background:#fffdfa;border:1px solid #e9dccc;border-radius:13px;display:flex;flex-direction:column;gap:7px;padding:15px;min-width:0}.srp-cards small{font-size:11px;color:#8d765e;font-weight:750}.srp-cards strong{font-size:clamp(16px,1.7vw,23px);overflow-wrap:anywhere}.srp-cards span{font-size:10px;line-height:1.5;color:#9c8976}.srp-cards .featured{background:#efe5d6;border-color:#d9c0a4}.srp-error,.srp-warning{padding:12px;border-radius:10px;margin:12px 0;border:1px solid #d3bca1;background:#fff1df;color:#795135;font-size:12px}.srp-section-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.srp-section-head h3{font-size:15px;font-weight:800;margin:0}.srp-section-head span{color:#96816d;font-size:11px}.srp-table-scroll{overflow-x:auto;margin-top:14px}.srp table{border-collapse:collapse;min-width:1220px;width:100%;font-size:11px}.srp th,.srp td{padding:11px 9px;text-align:right;border-bottom:1px solid #ede4d8;white-space:nowrap;font-variant-numeric:tabular-nums}.srp th:first-child,.srp td:first-child{text-align:left}.srp thead th{color:#846b50;background:#f8f1e8;font-weight:850}.srp tfoot th{background:#e9dbc8;font-weight:850}.srp-period{font-weight:750}.srp-track{background:#f2ece4;width:105px;border-radius:8px;height:3px;margin-top:8px;overflow:hidden}.srp-track>div{background:#a47b50;height:100%;border-radius:8px}.srp-em{font-weight:850}.negative{color:#ac4939!important}.srp-note{font-size:11px;color:#8e7c69;line-height:1.7;padding:5px 2px}@media(max-width:600px){.srp-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.srp-panel{padding:12px}}

/* v3.4 enhanced filters and readability; no financial computation changes */
.srp-empty{border:1px dashed #d9c6ad;background:#fffaf3;border-radius:11px;color:#866b4f;font-size:12px;padding:13px 15px;margin:10px 0}
.srp-quick{display:flex;gap:6px;flex-wrap:wrap;border-left:1px solid #e6d9c9;padding-left:11px}
.srp-highlights{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}
.srp-highlights>div{background:#fffdfa;border:1px solid #e5d9c9;border-radius:12px;padding:13px;display:flex;flex-direction:column;gap:6px;min-width:0}
.srp-highlights small{font-size:10px;font-weight:800;color:#987f65;letter-spacing:.04em}
.srp-highlights strong{color:#59412f;font-size:16px;overflow-wrap:anywhere}
.srp-highlights span{font-size:11px;color:#96816d}
.srp-scroll-hint{color:#8b7965;font-size:11px;margin-top:11px}
.srp-loading{display:flex;align-items:center;gap:12px;background:#fbf3e9;border:1px solid #e4d3be;padding:24px;border-radius:12px;color:#76583b;font-size:13px;font-weight:750;min-height:90px}
.srp-spinner{height:22px;width:22px;border:3px solid #e7d7c6;border-top-color:#78573b;border-radius:50%;animation:srpSpin 850ms linear infinite}
@keyframes srpSpin{to{transform:rotate(360deg)}}
.srp input:focus-visible,.srp button:focus-visible,.srp-table-scroll:focus-visible{outline:2px solid #a78056;outline-offset:2px}
.srp-table-scroll thead th{position:sticky;top:0;z-index:2}
.srp-table-scroll th:first-child,.srp-table-scroll td:first-child{position:sticky;left:0;background:#fffdfa;z-index:1;box-shadow:3px 0 5px #56402112}
.srp-table-scroll thead th:first-child{background:#f8f1e8;z-index:3}
.srp-table-scroll tfoot th:first-child{background:#e9dbc8;z-index:2}
.srp tbody tr:hover{background:#fff7ee}
@media(max-width:690px){.srp-highlights{grid-template-columns:1fr 1fr}.srp-highlights>div:last-child{grid-column:1 / -1}.srp-quick{padding-left:0;border:0}.srp-controls{align-items:stretch}.srp-controls label{flex:1;min-width:130px}}
@media(prefers-reduced-motion:reduce){.srp-spinner{animation:none}}
</style>
