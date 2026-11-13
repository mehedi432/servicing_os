<script setup>
// SERVICING_EXECUTIVE_ACTION_CENTER_619A
import { ref, computed, onMounted, watch } from 'vue'
const props = defineProps({
  fromDate: { type: String, required: true },
  toDate: { type: String, required: true },
  refreshKey: { type: Number, default: 0 }
})
const loading = ref(false)
const error = ref('')
const report = ref(null)
const active = ref('unassigned')
const queueDefinitions = [
  { key: 'unassigned', name: 'Assign technicians', caption: 'Open repairs without a technician', icon: '↗' },
  { key: 'aging_7_days', name: 'Overdue attention', caption: 'Open at least 7 calendar days', icon: '◷' },
  { key: 'ready_unbilled', name: 'Prepare invoices', caption: 'Completed/ready/delivered jobs without invoice', icon: '▤' },
  { key: 'draft_invoices', name: 'Draft invoice review', caption: 'Drafts awaiting accounting review', icon: '▣' },
  { key: 'customer_dues', name: 'Collect customer dues', caption: 'Submitted unpaid repair invoices', icon: '৳' },
  { key: 'parts_requests_review', name: 'Review parts requests', caption: 'Submitted requests requiring stock review', icon: '□' },
  { key: 'out_of_stock_catalog', name: 'Check zero-stock items', caption: 'Sales stock catalog with no available on-hand units', icon: '▧' }
]
const selected = computed(() => report.value?.queues?.[active.value] || {count:0,rows:[]})
const selectedDefinition = computed(() => queueDefinitions.find(x => x.key === active.value))
const money = x => '৳' + Number(x || 0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const label = x => x === null || x === undefined || x === '' ? '—' : String(x)
function apiError(x) {
  try {
    if (x?._server_messages) {
      const arr = JSON.parse(x._server_messages)
      return JSON.parse(arr[arr.length - 1]).message || 'Unable to load the Executive Desk'
    }
  } catch (_) {}
  return x?.exception || x?.message?.message || 'Unable to load Executive Desk'
}
let seq = 0
async function refresh() {
  const requestId = ++seq
  error.value = ''
  if (!props.fromDate || !props.toDate || props.fromDate > props.toDate) {
    report.value = null
    error.value = 'Select a valid From and To date in the main Reports toolbar.'
    return
  }
  loading.value = true
  try {
    const url = new URL('/api/method/servicing_os.api.executive_center.get_executive_center', window.location.origin)
    url.searchParams.set('from_date', props.fromDate)
    url.searchParams.set('to_date', props.toDate)
    const response = await fetch(url, {credentials:'same-origin',headers:{Accept:'application/json'}})
    const json = await response.json()
    if (!response.ok || json.exc || json.exc_type) throw new Error(apiError(json))
    if (requestId === seq) report.value = json.message
  } catch (e) {
    if (requestId === seq) { report.value = null; error.value = e?.message || 'Unable to load' }
  } finally { if (requestId === seq) loading.value = false }
}
function detailLink(row) {
  const pairs = [
    ['invoice','sales-invoice'], ['material_request','material-request'],
    ['service_job','service-job'], ['item_code','item']
  ]
  for (const [field,route] of pairs) {
    if (row[field]) return '/app/' + route + '/' + encodeURIComponent(row[field])
  }
  return ''
}
function rowTitle(row) {
  return row.service_job || row.invoice || row.material_request || row.item_code || 'Record'
}
function rowSubtitle(row) {
  return [row.customer_name || row.item_name, row.status, row.technician].filter(Boolean).join(' · ') || 'Open in ERPNext for details'
}
function rowAside(row) {
  if (row.amount !== undefined && row.amount !== null) return money(row.amount)
  if (row.age_days !== undefined && row.age_days !== null) return row.age_days + ' days'
  if (row.actual_qty !== undefined && row.actual_qty !== null) return row.actual_qty + ' units'
  return ''
}
const menuLinks = [
  {title:'Service Jobs', desc:'Assign and update repairs', route:'/app/service-job'},
  {title:'Purchase Receipts', desc:'Review received stock', route:'/app/purchase-receipt'},
  {title:'Sales Invoices', desc:'Review billable repairs', route:'/app/sales-invoice'},
  {title:'Payment Entries', desc:'Record verified collections', route:'/app/payment-entry'},
  {title:'Accounts Receivable', desc:'Official customer dues', route:'/app/query-report/Accounts%20Receivable'},
  {title:'Profit and Loss', desc:'Official financial statement', route:'/app/query-report/Profit%20and%20Loss%20Statement'}
]
watch([()=>props.fromDate,()=>props.toDate,()=>props.refreshKey], refresh)
onMounted(refresh)
</script>

<template>
  <section class="exc-root">
    <header class="exc-header">
      <div>
        <p class="exc-eyebrow">SERVICING OS / OWNER'S DESK</p>
        <h2>Today's Priorities</h2>
        <p>Operational exceptions and actual accounting signals, together in one place.</p>
      </div>
      <button type="button" class="exc-refresh" :disabled="loading" @click="refresh">{{loading?'Refreshing…':'Refresh Priorities'}}</button>
    </header>

    <p v-if="error" role="alert" class="exc-error">{{error}}</p>
    <p v-if="loading && !report" class="exc-empty">Loading current business priorities…</p>
    <template v-if="report">
      <div class="exc-kpis">
        <article><span>Jobs received in period</span><strong>{{report.overview.received_in_period}}</strong><small>By received date</small></article>
        <article><span>Posted repair sales</span><strong>{{money(report.overview.revenue_ex_tax_bdt)}}</strong><small>Excluding tax, invoice date</small></article>
        <article><span>Allocated collections</span><strong>{{money(report.overview.allocated_collections_bdt)}}</strong><small>By payment date</small></article>
        <article><span>Outstanding now</span><strong>{{money(report.overview.outstanding_now_all_dates_bdt)}}</strong><small>Across all invoice dates</small></article>
      </div>

      <div class="exc-layout">
        <section class="exc-card exc-queue-list" aria-label="Priority categories">
          <div class="exc-section-head"><h3>Action queue</h3><span>Current, all dates</span></div>
          <button v-for="q in queueDefinitions" :key="q.key" type="button"
            class="exc-queue-button" :class="{'exc-active':active===q.key}"
            :aria-pressed="active===q.key" @click="active=q.key">
            <span class="exc-icon" aria-hidden="true">{{q.icon}}</span>
            <span class="exc-queue-name"><b>{{q.name}}</b><small>{{q.caption}}</small></span>
            <span class="exc-count">{{report.queues[q.key]?.count ?? 0}}</span>
          </button>
        </section>

        <section class="exc-card exc-records" aria-label="Selected priority records">
          <div class="exc-section-head">
            <div><h3>{{selectedDefinition?.name}}</h3><p>{{selectedDefinition?.caption}}</p></div>
            <span>{{selected.count}} total</span>
          </div>
          <div v-if="!selected.rows?.length" class="exc-empty">Nothing requires attention in this category.</div>
          <div v-else class="exc-rows">
            <a v-for="(row,i) in selected.rows" :key="rowTitle(row)+'-'+i"
              class="exc-record" :href="detailLink(row)" target="_blank" rel="noopener noreferrer">
              <div class="exc-record-content"><strong>{{rowTitle(row)}}</strong><span>{{rowSubtitle(row)}}</span></div>
              <span class="exc-record-right">{{rowAside(row)}} <span aria-hidden="true">↗</span></span>
            </a>
          </div>
          <p v-if="selected.truncated" class="exc-hint">Showing the first {{selected.rows?.length || 0}} records. Use ERPNext lists for the full queue.</p>
        </section>
      </div>

      <section class="exc-card exc-shortcuts">
        <div class="exc-section-head"><h3>Open ERPNext</h3><span>Standard business documents &amp; reports</span></div>
        <div class="exc-shortcut-grid">
          <a v-for="link in menuLinks" :key="link.title" :href="link.route" target="_blank" rel="noopener noreferrer">
            <b>{{link.title}}</b><span>{{link.desc}}</span><span class="exc-arrow" aria-hidden="true">↗</span>
          </a>
        </div>
      </section>
      <p class="exc-hint">Period controls above filter the four KPI cards. Action queues and outstanding balances show the current situation across all dates. No postings or records are changed here.</p>
      <p class="exc-hint">{{report.basis.accounting}} {{report.basis.profit}}</p>
    </template>
  </section>
</template>

<style scoped>
.exc-root,.exc-root *{box-sizing:border-box}
.exc-root{padding:5px 0 20px;color:#4c3b2c}
.exc-header{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:6px 0 18px}
.exc-eyebrow{font-size:10px;color:#ac8859;letter-spacing:1.2px;font-weight:800}
.exc-header h2{margin:5px 0;font-size:clamp(22px,2vw,27px);font-weight:800;letter-spacing:-.5px}
.exc-header p:not(.exc-eyebrow){font-size:12px;color:#91806d}
.exc-refresh{height:42px;padding:0 16px;border:1px solid #d9cbb8;border-radius:11px;background:#fffdf9;color:#6a5036;font-size:12px;font-weight:700;cursor:pointer}
.exc-refresh:hover{background:#f2e8da}.exc-refresh:disabled{opacity:.6;cursor:default}
.exc-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px}
.exc-kpis article{padding:16px;border:1px solid #e3d7c6;background:#fffdfa;border-radius:14px;display:flex;flex-direction:column;gap:8px;min-width:0}
.exc-kpis article span{font-size:11px;color:#95816a}.exc-kpis article strong{font-size:clamp(18px,2vw,25px);font-weight:800;letter-spacing:-.5px;overflow-wrap:anywhere}
.exc-kpis article small{font-size:10px;color:#a69279}
.exc-layout{display:grid;grid-template-columns:minmax(270px,0.88fr) minmax(0,1.5fr);gap:14px;margin-bottom:16px}
.exc-card{background:#fffdf9;border:1px solid #e5d8c7;border-radius:15px;padding:17px;min-width:0}
.exc-section-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;border-bottom:1px solid #eee5d9;padding:0 0 13px;margin-bottom:12px}
.exc-section-head h3{font-size:15px;font-weight:800;margin:0}.exc-section-head p,.exc-section-head>span{font-size:11px;color:#9e8a71;margin:3px 0 0}
.exc-queue-button{display:flex;align-items:center;width:100%;padding:12px 10px;border-radius:12px;border:1px solid transparent;gap:10px;background:transparent;text-align:left;cursor:pointer;color:#51402f}
.exc-queue-button:hover{background:#f8f2e8}.exc-queue-button.exc-active{background:#efe2d0;border-color:#dfcdb4}
.exc-icon{width:32px;height:32px;flex:0 0 32px;display:grid;place-items:center;border-radius:10px;background:#f3ecdf;color:#795b39;font-size:18px}
.exc-queue-name{display:flex;flex:1;min-width:0;flex-direction:column;gap:3px}.exc-queue-name b{font-weight:750;font-size:12px}.exc-queue-name small{font-size:10px;color:#978671;line-height:1.35}
.exc-count{min-width:26px;padding:5px 7px;text-align:center;border-radius:9px;background:#fffaf1;border:1px solid #e4d6c5;font-size:12px;font-weight:800}
.exc-rows{max-height:570px;overflow:auto}.exc-record{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 6px;border-bottom:1px solid #eee5db;text-decoration:none;color:inherit;cursor:pointer}
.exc-record:hover{background:#f9f3e9}.exc-record-content{display:flex;flex-direction:column;gap:4px;min-width:0}
.exc-record-content strong{font-size:12px;overflow-wrap:anywhere}.exc-record-content span{font-size:11px;color:#8d7c67;overflow-wrap:anywhere}
.exc-record-right{display:flex;align-items:center;gap:7px;font-size:12px;color:#8b6945;white-space:nowrap}
.exc-empty{text-align:center;padding:45px 15px;color:#9d896d;font-size:12px}
.exc-hint{font-size:11px;color:#97846d;line-height:1.6;margin:10px 0 0}
.exc-shortcut-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}
.exc-shortcut-grid a{position:relative;display:flex;flex-direction:column;gap:5px;padding:14px 28px 14px 13px;border:1px solid #e7daca;border-radius:11px;background:#fbf7f0;text-decoration:none;color:#4f402f}
.exc-shortcut-grid a:hover{background:#f0e5d6}.exc-shortcut-grid a b{font-size:12px}.exc-shortcut-grid a span:not(.exc-arrow){font-size:10px;color:#927f69}
.exc-arrow{position:absolute;right:11px;top:12px;color:#987a56}
.exc-error{margin:13px 0;padding:12px;background:#ffebe8;color:#983c32;border-radius:10px;font-size:12px}
@media(max-width:1080px){.exc-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.exc-shortcut-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:820px){.exc-layout{grid-template-columns:1fr}.exc-shortcut-grid{grid-template-columns:1fr 1fr}}
@media(max-width:540px){.exc-card{padding:12px}.exc-shortcut-grid{grid-template-columns:1fr}.exc-header{align-items:stretch}.exc-refresh{width:100%}}
</style>
