<script setup>
// SERVICING_EXECUTIVE_ACTION_CENTER_619A
import ExecutiveActionCenter from "./ExecutiveActionCenter.vue"
const showExecutive = ref(false)
// SERVICING_FINANCIAL_REPORTS_618C
import FinancialReports from "./FinancialReports.vue"
const showFinancial = ref(false)
import OperationalReports from "./OperationalReports.vue"
const showOperational = ref(false)
const operationalRefreshKey = ref(0)

// SERVICING_OWNER_REPORTS_618A
import { ref, computed, onMounted } from 'vue'

const now = new Date()
const localDate = (d) => {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}-${String(d.getDate()).padStart(2, '0')}`
}
const from = ref(localDate(new Date(now.getFullYear(), now.getMonth(), 1)))
const to = ref(localDate(now))
const loading = ref(false)
const error = ref('')
const data = ref(null)
const fmt = (n) => Number(n || 0).toLocaleString('en-BD', {minimumFractionDigits: 2, maximumFractionDigits: 2})
const money = (n) => `৳${fmt(n)}`
const stages = ['Received', 'Diagnosing', 'Waiting for Parts', 'Repairing', 'Completed', 'Ready to Deliver', 'Delivered', 'Cancelled']
const counts = computed(() => data.value?.service_jobs?.current_stage_for_received_jobs || {})
const statusList = computed(() => stages.map(s => ({name: s, value: counts.value[s] || 0})))
const totalStages = computed(() => Math.max(1, data.value?.service_jobs?.received_in_period || 0))
const reportLinks = [
  {name: 'Accounts Receivable', route: 'Accounts Receivable', description: 'Customer outstanding and ageing'},
  {name: 'Sales Register', route: 'Sales Register', description: 'Submitted sales invoices'},
  {name: 'Stock Balance', route: 'Stock Balance', description: 'Warehouse quantity and value'},
  {name: 'General Ledger', route: 'General Ledger', description: 'Posted accounting movements'},
  {name: 'Profit and Loss Statement', route: 'Profit and Loss Statement', description: 'Company-level financial performance'}
]
function openReport(report) {
  window.open(`/app/query-report/${encodeURIComponent(report.route)}`, '_blank', 'noopener,noreferrer')
}
function openInvoice(invoice) {
  window.open(`/app/sales-invoice/${encodeURIComponent(invoice.name)}`, '_blank', 'noopener,noreferrer')
}
function readError(data) {
  if (data?._server_messages) {
    try {const rows = JSON.parse(data._server_messages); return JSON.parse(rows.at(-1)).message}
    catch (_) {}
  }
  return data?.exception || data?.message?.message || 'Unable to load reports.'
}
async function refresh() {
  error.value = ''
  if (!from.value || !to.value || from.value > to.value) {
    error.value = 'Select a valid From Date and To Date.'
    return
  }
  operationalRefreshKey.value += 1
  loading.value = true
  try {
    const path = '/api/method/servicing_os.api.owner_reports.get_owner_dashboard'
    const url = new URL(path, window.location.origin)
    url.searchParams.set('from_date', from.value)
    url.searchParams.set('to_date', to.value)
    const response = await fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}})
    const json = await response.json()
    if (!response.ok || json.exc || json.exc_type) throw new Error(readError(json))
    data.value = json.message || null
  } catch (e) {
    error.value = e.message || 'Reports unavailable.'
  } finally {
    loading.value = false
  }
}
onMounted(refresh)
</script>

<template>
  <section class="or-root">
    <header class="or-header">
      <div><p class="or-overline">SERVICING OS / OWNER INSIGHTS</p><h1>Reports & Overview</h1>
        <p>Real ERPNext transactions · AL MODINA COMPUTERS LIMITED · BDT</p></div>
      <form class="or-filters" @submit.prevent="refresh">
        <label class="or-filter-field" for="or-report-date-from">
          <span>From</span>
          <input id="or-report-date-from" type="date" v-model="from" />
        </label>
        <label class="or-filter-field" for="or-report-date-to">
          <span>To</span>
          <input id="or-report-date-to" type="date" v-model="to" />
        </label>
        <div class="or-filter-action">
          <button type="submit" :disabled="loading">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M20 11a8 8 0 0 0-14.4-4.8L3 9" />
              <path d="M3 4v5h5" />
              <path d="M4 13a8 8 0 0 0 14.4 4.8L21 15" />
              <path d="M21 20v-5h-5" />
            </svg>
            <span>{{ loading ? 'Refreshing…' : 'Refresh Reports' }}</span>
          </button>
        </div>
      </form>
    </header>
    <nav class="or-view-tabs" aria-label="Reports section">
      <button type="button" :class="{'or-view-active': !showOperational && !showFinancial && !showExecutive}" :aria-pressed="!showOperational && !showFinancial && !showExecutive" @click="showOperational=false; showFinancial=false; showExecutive=false">Overview</button>
      <button type="button" :class="{'or-view-active': showOperational}" :aria-pressed="showOperational" @click="showOperational=true; showFinancial=false; showExecutive=false">Detailed Operations</button>
    
      <button type="button" :class="{'or-view-active': showFinancial}" :aria-pressed="showFinancial" @click="showFinancial=true; showOperational=false; showExecutive=false">Financial & Profitability</button>
    
      <button type="button" :class="{'or-view-active': showExecutive}" :aria-pressed="showExecutive"
        @click="showExecutive=true; showOperational=false; showFinancial=false">Executive Desk</button>
    </nav>
    <ExecutiveActionCenter v-if="showExecutive" :from-date="from" :to-date="to" :refresh-key="operationalRefreshKey" />

    <FinancialReports v-if="showFinancial" :from-date="from" :to-date="to" :refresh-key="operationalRefreshKey" />
    <OperationalReports v-if="showOperational" :from-date="from" :to-date="to" :refresh-key="operationalRefreshKey" />

    <p v-if="error && !showOperational && !showFinancial && !showExecutive" class="or-error" role="alert">{{ error }}</p>
    <template v-if="data && !showOperational && !showFinancial && !showExecutive">
      <div class="or-grid or-kpis">
        <article><span>Jobs Received</span><strong>{{data.service_jobs.received_in_period}}</strong><small>Selected period</small></article>
        <article><span>Repair Revenue</span><strong>{{money(data.billing.revenue_ex_tax_bdt)}}</strong><small>Submitted invoices · before tax</small></article>
        <article><span>Cash Collected</span><strong>{{money(data.collections.cash_allocated_to_service_invoices_bdt)}}</strong><small>Submitted, allocated cash payments</small></article>
        <article><span>Customer Dues</span><strong>{{money(data.billing.current_outstanding_all_dates_bdt)}}</strong><small>Current outstanding · all dates</small></article>
      </div>
      <div class="or-grid or-panels">
        <article class="or-panel">
          <div class="or-panel-heading"><div><span>OPERATIONS</span><h2>Repair Status</h2></div><small>Jobs received in selected period</small></div>
          <div v-for="stage in statusList" :key="stage.name" class="or-stage">
            <div><span>{{stage.name}}</span><strong>{{stage.value}}</strong></div>
            <div class="or-track"><span :style="{width: Math.max(0, 100 * stage.value / totalStages) + '%'}"></span></div>
          </div>
        </article>
        <article class="or-panel">
          <div class="or-panel-heading"><div><span>TECHNICIANS</span><h2>Current Workload</h2></div><small>Open jobs · all dates</small></div>
          <div class="or-table-wrap"><table><thead><tr><th>Technician</th><th>Active</th><th>Completed*</th><th>Waiting Parts</th></tr></thead>
            <tbody><tr v-for="person in data.technicians" :key="person.user_id || 'unassigned'">
              <td>{{person.technician}}</td><td>{{person.active_jobs}}</td><td>{{person.completed_waiting}}</td><td>{{person.waiting_parts}}</td>
            </tr><tr v-if="!data.technicians.length"><td colspan="4">No open jobs.</td></tr></tbody>
          </table></div><p class="or-footnote">* Completed status still awaiting delivery. Not a period-completion measure.</p>
        </article>
      </div>
      <div class="or-grid or-panels">
        <article class="or-panel">
          <div class="or-panel-heading"><div><span>ACCOUNTS</span><h2>Invoices & Collections</h2></div></div>
          <div class="or-line"><span>Submitted repair invoices</span><strong>{{data.billing.submitted_invoices_in_period}}</strong></div>
          <div class="or-line"><span>Invoiced incl. taxes</span><strong>{{money(data.billing.invoiced_incl_tax_bdt)}}</strong></div>
          <div class="or-line"><span>All allocated receipts</span><strong>{{money(data.collections.allocated_to_service_invoices_bdt)}}</strong></div>
          <div class="or-line"><span>Current unpaid invoices</span><strong>{{data.billing.current_open_invoices_all_dates}}</strong></div>
          <p class="or-footnote">Invoice totals use invoice dates; receipt totals use payment dates. They need not equal each other.</p>
        </article>
        <article class="or-panel">
          <div class="or-panel-heading"><div><span>STOCK</span><h2>Parts & Requirements</h2></div></div>
          <div class="or-line"><span>Draft parts requests (period)</span><strong>{{data.parts_requests.drafts_in_period}}</strong></div>
          <div class="or-line"><span>Submitted pending requests (period)</span><strong>{{data.parts_requests.submitted_pending_in_period}}</strong></div>
          <div class="or-line"><span>Stock on hand · units</span><strong>{{data.stock_now.on_hand_units}}</strong></div>
          <div class="or-line"><span>Reserved quantity · units</span><strong>{{data.stock_now.reserved_units}}</strong></div>
          <p class="or-footnote">Current stock is from {{data.stock_now.warehouse}}. Unit totals combine SKUs, not monetary value.</p>
        </article>
      </div>
      <article class="or-panel or-invoices">
        <div class="or-panel-heading"><div><span>RECENT ACTIVITY</span><h2>Submitted Repair Invoices</h2></div><small>Most recent 30 in period</small></div>
        <div class="or-table-wrap"><table><thead><tr><th>Invoice</th><th>Posting Date</th><th>Service Job</th><th>Customer</th><th>Revenue ex tax</th><th>Outstanding now</th></tr></thead>
          <tbody><tr v-for="invoice in data.recent_submitted_invoices" :key="invoice.name">
            <td><button class="or-link" @click="openInvoice(invoice)">{{invoice.name}} ↗</button></td>
            <td>{{invoice.posting_date}}</td><td>{{invoice.service_job}}</td><td>{{invoice.customer}}</td>
            <td class="or-number">{{money(invoice.revenue_ex_tax)}}</td><td class="or-number">{{money(invoice.outstanding_amount)}}</td>
          </tr><tr v-if="!data.recent_submitted_invoices.length"><td colspan="6">No submitted repair invoices in this period. Draft invoices are excluded.</td></tr></tbody>
        </table></div>
      </article>
      <article class="or-panel">
        <div class="or-panel-heading"><div><span>ERPNext STANDARD REPORTS</span><h2>Open Detailed Reports</h2></div><small>Read-only links · permissions apply</small></div>
        <div class="or-shortcuts"><button v-for="report in reportLinks" :key="report.name" @click="openReport(report)">
          <strong>{{report.name}} ↗</strong><small>{{report.description}}</small>
        </button></div>
        <p class="or-footnote">Standard reports may include non-servicing business activity. Apply Company, Warehouse and date filters within ERPNext.</p>
      </article>
      <p class="or-disclaimer">Service statuses show current state for jobs received in the selected period. Revenue excludes unsubmitted invoices and tax. Cash reflects allocated submitted payments only. These totals are not a substitute for ERPNext Profit and Loss or General Ledger.</p>
    </template>
    <div v-else-if="loading && !showOperational && !showFinancial && !showExecutive" class="or-loading">Loading ERPNext reports…</div>
  </section>
</template>

<style scoped>
.or-root,.or-root *{box-sizing:border-box}.or-root{min-height:calc(100vh - 76px);padding:24px;background:#f8f6f1;color:#4b4135}.or-overline{font-size:10px;letter-spacing:1.4px;color:#a18051;font-weight:800}.or-header{display:flex;justify-content:space-between;gap:22px;flex-wrap:wrap;align-items:end;margin-bottom:22px}.or-header h1{font-size:29px;font-weight:800;letter-spacing:-.7px;margin:6px 0}.or-header p:not(.or-overline){font-size:12px;color:#827365}.or-filters{display:flex;align-items:end;flex-wrap:wrap;gap:9px}.or-filters label{display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:700;color:#756550}.or-filters input{background:#fffdf9;border:1px solid #dcd0bf;border-radius:10px;padding:10px;color:#4b4135;font-size:12px;min-height:41px}.or-filters button{background:#755a3e;border:1px solid #755a3e;border-radius:10px;padding:11px 16px;color:white;font-weight:750;font-size:12px;min-height:41px;cursor:pointer}.or-filters button:disabled{opacity:.55}.or-grid{display:grid;gap:14px}.or-kpis{grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:14px}.or-kpis article,.or-panel{border:1px solid #e5dccf;background:#fffefa;border-radius:15px;box-shadow:0 3px 9px #66543a08}.or-kpis article{padding:18px;display:flex;flex-direction:column;gap:8px}.or-kpis article>span{font-size:12px;color:#8b7964;font-weight:600}.or-kpis article>strong{font-size:clamp(19px,2vw,27px);line-height:1.2;letter-spacing:-.7px;overflow-wrap:anywhere}.or-kpis article>small{font-size:11px;color:#a08e77}.or-panels{grid-template-columns:repeat(2,minmax(0,1fr));margin-bottom:14px}.or-panel{padding:19px;min-width:0}.or-panel-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:16px}.or-panel-heading span{font-size:10px;font-weight:750;letter-spacing:1px;color:#ae8756}.or-panel-heading h2{font-size:17px;font-weight:800;margin-top:5px}.or-panel-heading small{font-size:11px;color:#9c8a74}.or-stage{margin-bottom:12px}.or-stage>div:first-child{display:flex;justify-content:space-between;gap:10px;font-size:12px;margin-bottom:6px}.or-stage strong{color:#5c4932}.or-track{height:8px;border-radius:15px;background:#f0e9de;overflow:hidden}.or-track span{display:block;height:100%;border-radius:15px;background:#b08b62}.or-table-wrap{width:100%;overflow-x:auto}.or-panel table{width:100%;border-collapse:collapse;font-size:12px;text-align:left}.or-panel th{font-size:10px;letter-spacing:.2px;color:#9a8a76;padding:10px 9px;border-bottom:1px solid #e9e0d3;white-space:nowrap}.or-panel td{padding:12px 9px;border-bottom:1px solid #f1e9dd;white-space:nowrap}.or-panel td:first-child{font-weight:650}.or-footnote{font-size:11px;color:#96846e;line-height:1.5;margin-top:14px}.or-line{display:flex;justify-content:space-between;gap:15px;padding:10px 0;border-bottom:1px solid #eee6da;font-size:12px}.or-line strong{white-space:nowrap}.or-invoices{margin-bottom:14px}.or-number{text-align:right}.or-link{border:none;background:none;color:#785a3c;text-decoration:underline;font-size:12px;cursor:pointer}.or-shortcuts{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:10px}.or-shortcuts button{background:#fbf7f0;border:1px solid #e5d8c7;border-radius:12px;padding:13px;text-align:left;cursor:pointer}.or-shortcuts button:hover{background:#f1e7d9}.or-shortcuts strong{display:block;font-size:13px;color:#5f4c36}.or-shortcuts small{display:block;font-size:11px;color:#978570;margin-top:5px}.or-disclaimer{font-size:11px;line-height:1.55;color:#96846e;padding:8px 3px 18px}.or-error{background:#ffece8;color:#9c382e;padding:12px 15px;border-radius:12px;margin-bottom:14px;font-size:13px}.or-loading{padding:45px;text-align:center;color:#8c7c66}
@media(max-width:1100px){.or-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:880px){.or-panels{grid-template-columns:1fr}.or-header{align-items:stretch}}@media(max-width:580px){.or-root{padding:13px}.or-panel{padding:13px}.or-kpis{gap:8px}.or-kpis article{padding:13px}.or-header h1{font-size:23px}.or-filters label{flex:1;min-width:125px}.or-filters button{width:100%}}


/* SERVICING_REPORT_FILTER_ALIGNMENT_618A1 -- aligned, responsive report filter toolbar */
.or-header {
  align-items: center;
  column-gap: 24px;
  row-gap: 16px;
}
.or-filters {
  display: grid;
  grid-template-columns: minmax(155px, 175px) minmax(155px, 175px) max-content;
  align-items: end;
  column-gap: 12px;
  row-gap: 10px;
  flex-wrap: nowrap;
  margin: 0;
  padding: 0;
  min-width: 0;
}
.or-filters .or-filter-field {
  display: grid;
  grid-template-rows: 17px 44px;
  row-gap: 7px;
  min-width: 0;
  margin: 0;
  padding: 0;
  font-size: 12px;
  line-height: 17px;
  font-weight: 700;
  color: #70604c;
}
.or-filters .or-filter-field > span {
  display: block;
  white-space: nowrap;
}
.or-filters .or-filter-field input {
  box-sizing: border-box;
  display: block;
  width: 100%;
  min-width: 0;
  height: 44px;
  min-height: 44px;
  margin: 0;
  padding: 0 11px;
  border: 1px solid #ded2c1;
  border-radius: 10px;
  background: #fffdfa;
  color: #42372b;
  font: inherit;
  font-size: 13px;
  line-height: normal;
}
.or-filters .or-filter-action {
  display: flex;
  align-items: end;
  min-width: 0;
  margin: 0;
  padding: 0;
}
.or-filters .or-filter-action button {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 44px;
  min-height: 44px;
  margin: 0;
  padding: 0 17px;
  white-space: nowrap;
  border: 1px solid #755a3e;
  border-radius: 10px;
  background: #755a3e;
  color: #fffefa;
  font-size: 12px;
  font-weight: 750;
  line-height: 1;
  cursor: pointer;
  transition: background .15s ease, box-shadow .15s ease;
}
.or-filters .or-filter-action button:hover:not(:disabled) {
  background: #62492f;
  box-shadow: 0 2px 8px rgba(85, 61, 36, .13);
}
.or-filters .or-filter-action button:disabled {
  opacity: .6;
  cursor: not-allowed;
}
.or-filters .or-filter-field input:focus-visible,
.or-filters .or-filter-action button:focus-visible {
  outline: 2px solid #ae8d60;
  outline-offset: 2px;
}
@media (max-width: 1100px) {
  .or-header { align-items: stretch; }
  .or-filters { width: 100%; grid-template-columns: minmax(0,1fr) minmax(0,1fr) max-content; }
}
@media (max-width: 580px) {
  .or-filters { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .or-filters .or-filter-action { grid-column: 1 / -1; }
  .or-filters .or-filter-action button { width: 100%; }
}
@media (max-width: 355px) {
  .or-filters { grid-template-columns: 1fr; }
  .or-filters .or-filter-action { grid-column: 1; }
}


/* SERVICING_OPERATIONAL_REPORTS_618B - compact Owner Reports view tabs */
.or-view-tabs{display:flex;gap:7px;margin:0 0 16px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #e3d7c7;padding-bottom:13px}
.or-view-tabs button{border:1px solid #dfd2bf;background:#fffdf8;border-radius:10px;padding:10px 15px;font-size:12px;font-weight:750;color:#806e57;cursor:pointer;min-height:41px}
.or-view-tabs button:hover{background:#f0e5d6}
.or-view-tabs button.or-view-active{background:#e9dcc9;border-color:#d5bfa4;color:#4f3d2a}

</style>
