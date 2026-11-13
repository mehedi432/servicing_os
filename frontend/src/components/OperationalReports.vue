<script setup>
// SERVICING_OPERATIONAL_REPORTS_618B
import { ref, computed, onMounted, watch } from 'vue'

const props = defineProps({
  fromDate: {type: String, required: true},
  toDate: {type: String, required: true},
  refreshKey: {type: Number, default: 0}
})
const report = ref('register')
const reports = [
  {key: 'register', label: 'Daily Service Register'},
  {key: 'technicians', label: 'Technician Performance'},
  {key: 'aging', label: 'Repair Aging'}
]
const data = ref(null)
const loading = ref(false)
const error = ref('')
const status = ref('All')
const technician = ref('All')
const searchDraft = ref('')
const appliedSearch = ref('')
const statuses = ref([])
const technicians = ref([])
const rows = computed(() => data.value?.rows || [])
const currentTab = computed(() => reports.find(t => t.key === report.value))
const count = computed(() => data.value?.total ?? 0)
const statusLabel = s => s || 'Unknown'
const formatDate = s => s ? String(s).replace('T',' ').slice(0,16) : '—'
const fmt = x => Number(x ?? 0).toLocaleString('en-BD')
const statusClass = s => {
  if (s === 'Completed' || s === 'Delivered') return 'opr-stage-done'
  if (s === 'Cancelled') return 'opr-stage-cancel'
  if (s === 'Waiting for Parts') return 'opr-stage-wait'
  return 'opr-stage-default'
}
function apiError(obj) {
  if(obj?._server_messages) {
    try {const list=JSON.parse(obj._server_messages);const last=JSON.parse(list[list.length-1]);return last.message || 'Unable to load report'} catch (_) {}
  }
  return obj?.exception || obj?.message?.message || 'Unable to load report'
}
async function getData(method, args={}) {
  const url = new URL('/api/method/servicing_os.api.operational_reports.'+method, window.location.origin)
  Object.entries(args).forEach(([key,value]) => {
    if(value !== null && value !== undefined && value !== '') url.searchParams.set(key,String(value))
  })
  const resp = await fetch(url,{credentials:'same-origin',headers:{Accept:'application/json'}})
  const result = await resp.json()
  if(!resp.ok || result.exc || result.exc_type) throw new Error(apiError(result))
  return result.message
}
let sequence = 0
async function refresh() {
  const requestId = ++sequence
  if(!props.fromDate || !props.toDate || props.fromDate > props.toDate) {
    error.value = 'Choose a valid From and To date in the Reports toolbar.'
    data.value = null
    return
  }
  loading.value=true
  error.value=''
  try {
    const payload = await getData('get_operational_report',{
      report:report.value, from_date:props.fromDate,to_date:props.toDate,
      status:status.value, technician:technician.value,
      search:appliedSearch.value, limit:500
    })
    if(requestId===sequence) data.value=payload
  } catch(err) {
    if(requestId===sequence){error.value=err.message || 'Report unavailable';data.value=null}
  } finally {
    if(requestId===sequence)loading.value=false
  }
}
function applySearch(){appliedSearch.value=searchDraft.value.trim();refresh()}
function changeTab(tab){report.value=tab;refresh()}
function jobUrl(job){return '/app/service-job/'+encodeURIComponent(job)}
function exportCsv(){
  if(!data.value || !rows.value.length)return
  let columns=[]
  if(report.value==='register') columns=[
    ['name','Service Job'],['received_date','Received'],['customer_name','Customer'],
    ['mobile','Mobile'],['brand','Brand'],['device_model','Device'],
    ['technician','Technician'],['status','Current Status'],
    ['expected_delivery','Expected Delivery'],['completed_recorded_at','Recorded Completed'],
    ['delivered_recorded_at','Recorded Delivered']
  ]
  else if(report.value==='technicians')columns=[
    ['technician','Technician'],['total_jobs','Received Jobs'],['open_jobs','Open'],
    ['completed_now','Completed Now'],['ready_now','Ready Now'],['delivered_now','Delivered Now'],
    ['waiting_parts','Waiting Parts'],['authored_notes','Work Notes'],
    ['avg_open_age_days','Avg Open Age Days']
  ]
  else columns=[
    ['name','Service Job'],['customer_name','Customer'],['technician','Technician'],
    ['status','Current Status'],['received_date','Received'],['age_days','Age Days'],
    ['age_bucket','Age Bucket'],['expected_delivery','Expected Delivery'],
    ['overdue_expected','Past Expected Delivery']
  ]
  const escapeCell = v => {
    let x=String(v ?? '')
    if(/^[=+@\-\t\r]/.test(x)) x="'"+x
    return '"'+x.replace(/"/g,'""')+'"'
  }
  const content='\uFEFF'+[columns.map(x=>escapeCell(x[1])).join(','),...rows.value.map(row=>columns.map(c=>escapeCell(row[c[0]])).join(','))].join('\r\n')
  const blob=new Blob([content],{type:'text/csv;charset=utf-8;'})
  const url=URL.createObjectURL(blob)
  const a=document.createElement('a')
  a.href=url
  a.download='servicing-'+report.value+'-'+props.fromDate+'-to-'+props.toDate+'.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1500)
}
watch([()=>props.fromDate,()=>props.toDate,()=>props.refreshKey],refresh)
onMounted(async()=>{
  try {
    const options=await getData('get_report_options')
    statuses.value=options?.statuses || []
    technicians.value=options?.technicians || []
  } catch(err){ /* Main report reports authorization/errors separately. */ }
  refresh()
})
</script>

<template>
  <section class="opr-root">
    <header class="opr-heading">
      <div>
        <p class="opr-eyebrow">OPERATIONS / DETAILED REPORTS</p>
        <h2>Service Operations</h2>
        <p>Actual Service Job records · dates refer to when the device was received</p>
      </div>
      <div class="opr-heading-actions">
        <button type="button" class="opr-outline" @click="refresh" :disabled="loading">{{loading?'Loading…':'Refresh Table'}}</button>
        <button type="button" class="opr-outline" :disabled="!rows.length" @click="exportCsv">Export CSV</button>
      </div>
    </header>

    <nav class="opr-tabs" aria-label="Operational report type">
      <button v-for="tab in reports" :key="tab.key" type="button"
        :class="{'opr-active': report===tab.key}" :aria-pressed="report===tab.key"
        @click="changeTab(tab.key)">{{tab.label}}</button>
    </nav>

    <form class="opr-toolbar" @submit.prevent="applySearch">
      <label class="opr-field"><span>Search job or customer</span><input v-model="searchDraft" placeholder="Job, customer, mobile, device…" /></label>
      <label class="opr-field"><span>Technician</span>
        <select v-model="technician" @change="refresh">
          <option value="All">All technicians</option><option value="__unassigned__">Unassigned</option>
          <option v-for="t in technicians" :key="t.value" :value="t.value">{{t.label}}</option>
        </select>
      </label>
      <label class="opr-field"><span>Current Status</span>
        <select v-model="status" @change="refresh"><option value="All">All statuses</option><option v-for="s in statuses" :key="s" :value="s">{{s}}</option></select>
      </label>
      <button class="opr-search" type="submit">Search</button>
    </form>

    <p v-if="error" class="opr-error" role="alert">{{error}}</p>
    <div v-if="data" class="opr-content">
      <div v-if="report==='register'" class="opr-summary">
        <article><span>Jobs Received</span><strong>{{fmt(count)}}</strong></article>
        <article><span>Currently Completed</span><strong>{{fmt(data.summary.currently_completed)}}</strong></article>
        <article><span>Currently Delivered</span><strong>{{fmt(data.summary.currently_delivered)}}</strong></article>
        <article><span>Waiting for Parts</span><strong>{{fmt(data.summary.currently_waiting_parts)}}</strong></article>
      </div>
      <div v-else-if="report==='technicians'" class="opr-summary">
        <article><span>Received Jobs</span><strong>{{fmt(data.summary.jobs)}}</strong></article>
        <article><span>Technician Groups</span><strong>{{fmt(data.summary.technicians_shown)}}</strong></article>
        <article><span>Open Jobs (shown)</span><strong>{{fmt(data.summary.open_jobs)}}</strong></article>
      </div>
      <div v-else class="opr-summary">
        <article><span>Pending Now</span><strong>{{fmt(data.summary.open_jobs)}}</strong></article>
        <article><span>Today / 1–2 days</span><strong>{{fmt(data.summary.today+data.summary.days_1_2)}}</strong></article>
        <article><span>3–6 days</span><strong>{{fmt(data.summary.days_3_6)}}</strong></article>
        <article><span>7–14 / 15+ days</span><strong>{{fmt(data.summary.days_7_14+data.summary.days_15_plus)}}</strong></article>
      </div>
      <div class="opr-table-shell">
        <div class="opr-table-head"><div><h3>{{currentTab?.label}}</h3><p>{{data.from_date}} to {{data.to_date}}</p></div><span>{{rows.length}} of {{fmt(count)}} jobs{{report==='technicians'?' (grouped)':''}}</span></div>
        <div class="opr-scroll" v-if="report==='register'">
          <table><thead><tr><th>Service Job</th><th>Received</th><th>Customer</th><th>Device</th><th>Technician</th><th>Status</th><th>Completed at*</th><th>Delivered at*</th></tr></thead>
            <tbody><tr v-for="job in rows" :key="job.name">
              <td><a :href="jobUrl(job.name)" target="_blank" rel="noopener noreferrer">{{job.name}}</a></td>
              <td>{{formatDate(job.received_date)}}</td><td>{{job.customer_name || '—'}}</td>
              <td>{{[job.brand,job.device_model].filter(Boolean).join(' ') || job.device_type || '—'}}</td>
              <td>{{job.technician}}</td><td><span class="opr-status" :class="statusClass(job.status)">{{statusLabel(job.status)}}</span></td>
              <td>{{formatDate(job.completed_recorded_at)}}</td><td>{{formatDate(job.delivered_recorded_at)}}</td>
            </tr><tr v-if="!rows.length"><td colspan="8" class="opr-empty">No Service Jobs match the selected filters.</td></tr></tbody>
          </table>
        </div>
        <div class="opr-scroll" v-else-if="report==='technicians'">
          <table><thead><tr><th>Technician</th><th>Received Jobs</th><th>Open</th><th>Completed Now</th><th>Ready Now</th><th>Delivered Now</th><th>Waiting Parts</th><th>Authored Work Notes</th><th>Avg Open Age</th></tr></thead>
            <tbody><tr v-for="person in rows" :key="person.technician_id || 'unassigned'">
              <td><strong>{{person.technician}}</strong><small>{{person.technician_id || 'Unassigned'}}</small></td>
              <td>{{person.total_jobs}}</td><td>{{person.open_jobs}}</td><td>{{person.completed_now}}</td>
              <td>{{person.ready_now}}</td><td>{{person.delivered_now}}</td><td>{{person.waiting_parts}}</td>
              <td>{{person.authored_notes}}</td><td>{{person.avg_open_age_days === null ? '—' : person.avg_open_age_days + ' d'}}</td>
            </tr><tr v-if="!rows.length"><td colspan="9" class="opr-empty">No technician performance records match these filters.</td></tr></tbody>
          </table>
        </div>
        <div class="opr-scroll" v-else>
          <table><thead><tr><th>Service Job</th><th>Customer</th><th>Device</th><th>Technician</th><th>Status</th><th>Received</th><th>Age</th><th>Expected Delivery</th></tr></thead>
            <tbody><tr v-for="job in rows" :key="job.name">
              <td><a :href="jobUrl(job.name)" target="_blank" rel="noopener noreferrer">{{job.name}}</a></td>
              <td>{{job.customer_name || '—'}}</td><td>{{[job.brand,job.device_model].filter(Boolean).join(' ') || '—'}}</td>
              <td>{{job.technician}}</td><td><span class="opr-status" :class="statusClass(job.status)">{{job.status}}</span></td>
              <td>{{formatDate(job.received_date)}}</td>
              <td><strong>{{job.age_days}} d</strong><small>{{job.age_bucket}}</small></td>
              <td :class="{'opr-overdue':job.overdue_expected}">{{job.expected_delivery ? formatDate(job.expected_delivery) : '—'}}{{job.overdue_expected?' · Past due':''}}</td>
            </tr><tr v-if="!rows.length"><td colspan="8" class="opr-empty">No open repairs match these filters.</td></tr></tbody>
          </table>
        </div>
      </div>
      <p v-if="data.truncated" class="opr-warning">Showing at most {{data.limit}} rows. CSV exports displayed rows only; narrow the filters for a complete export.</p>
      <p class="opr-note">{{data.note}}</p>
      <p v-if="report==='register'" class="opr-note">* Completion and delivery timestamps appear only when recorded in repair-status comments or the stored delivery timestamp. A dash means no reliable recorded timestamp was found.</p>
    </div>
    <div v-else-if="loading" class="opr-placeholder">Loading report…</div>
  </section>
</template>

<style scoped>
.opr-root,.opr-root *{box-sizing:border-box}
.opr-root{color:#483d31;padding:3px 1px 18px;max-width:100%}
.opr-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:14px 0 17px}
.opr-eyebrow{font-size:10px;letter-spacing:1.2px;font-weight:800;color:#a58253}
.opr-heading h2{font-weight:800;font-size:23px;letter-spacing:-.5px;margin:5px 0}
.opr-heading p:not(.opr-eyebrow){color:#867660;font-size:12px}
.opr-heading-actions{display:flex;gap:8px;flex-wrap:wrap}
.opr-outline{height:40px;border:1px solid #d9cbb8;background:#fffdf9;border-radius:10px;padding:0 14px;color:#6a533b;font-size:12px;font-weight:700;cursor:pointer}
.opr-outline:hover{background:#f4ecdf}.opr-outline:disabled{opacity:.5;cursor:not-allowed}
.opr-tabs{display:flex;align-items:center;gap:5px;overflow-x:auto;border-bottom:1px solid #e4d8c8;padding:0 0 8px;margin:0 0 14px}
.opr-tabs button{font-size:12px;color:#82715b;background:transparent;white-space:nowrap;padding:11px 15px;border:1px solid transparent;border-radius:10px;cursor:pointer;font-weight:700}
.opr-tabs button:hover{background:#f2eadc}.opr-tabs button.opr-active{background:#eee1ce;border-color:#dcc9ae;color:#5b4027}
.opr-toolbar{display:grid;grid-template-columns:minmax(180px,1fr) minmax(150px,205px) minmax(145px,190px) 95px;gap:10px;align-items:end;margin-bottom:17px}
.opr-field{display:grid;grid-template-rows:17px 43px;gap:6px;min-width:0;font-size:11px;font-weight:700;color:#776550}
.opr-field span{line-height:17px}.opr-field input,.opr-field select{display:block;width:100%;height:43px;min-height:43px;min-width:0;border:1px solid #dbcebc;background:#fffefa;border-radius:10px;padding:0 11px;color:#4c3d2e;font-size:12px;font-weight:500}
.opr-search{height:43px;background:#72583b;border:1px solid #72583b;border-radius:10px;color:#fffefa;font-weight:800;font-size:12px;cursor:pointer}
.opr-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px}
.opr-summary article{border:1px solid #e5daca;border-radius:13px;background:#fffdf9;display:flex;flex-direction:column;gap:7px;padding:15px 16px;min-width:0}
.opr-summary article span{font-size:11px;color:#8b7963}.opr-summary article strong{font-size:clamp(20px,2vw,27px);font-weight:800;color:#463829;line-height:1.15}
.opr-table-shell{border:1px solid #e5daca;border-radius:15px;background:#fffefa;overflow:hidden}
.opr-table-head{padding:17px 18px;border-bottom:1px solid #eee5d9;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.opr-table-head h3{font-size:16px;font-weight:800}.opr-table-head p,.opr-table-head span{font-size:11px;color:#9a8870}
.opr-scroll{overflow:auto;max-height:620px}
.opr-scroll table{border-collapse:collapse;min-width:970px;width:100%;text-align:left;font-size:12px}
.opr-scroll th{position:sticky;top:0;z-index:1;background:#f6f0e7;color:#826e55;font-size:10px;letter-spacing:.2px;padding:12px;border-bottom:1px solid #e3d8ca;white-space:nowrap}
.opr-scroll td{padding:12px;border-bottom:1px solid #f0e8dc;white-space:nowrap;vertical-align:middle}
.opr-scroll tbody tr:hover{background:#fbf7f0}
.opr-scroll td a{color:#78583a;text-decoration:none;font-weight:750}.opr-scroll td a:hover{text-decoration:underline}
.opr-scroll td small{display:block;font-size:10px;color:#98866f;margin-top:3px}
.opr-status{display:inline-block;border-radius:8px;padding:5px 8px;font-size:10px;font-weight:750}
.opr-stage-default{background:#f0e9df;color:#68553f}.opr-stage-wait{background:#fff1d6;color:#926318}
.opr-stage-done{background:#e6f2e8;color:#29633e}.opr-stage-cancel{background:#f9e9e8;color:#9f4741}
.opr-overdue{color:#9f4732;font-weight:700}
.opr-placeholder,.opr-empty{text-align:center;color:#96846c;padding:30px!important}
.opr-warning{margin-top:12px;padding:11px 13px;border-radius:9px;background:#fff1d8;color:#835d22;font-size:12px}
.opr-note{font-size:11px;line-height:1.6;color:#92806a;margin-top:11px}
.opr-error{padding:12px;background:#ffe9e6;border-radius:9px;color:#99372e;font-size:12px;margin:12px 0}
@media(max-width:1000px){.opr-toolbar{grid-template-columns:repeat(2,minmax(0,1fr))}.opr-search{width:100%}}
@media(max-width:650px){.opr-heading{align-items:flex-start}.opr-heading-actions{width:100%}.opr-outline{flex:1}.opr-toolbar{grid-template-columns:1fr}.opr-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.opr-heading h2{font-size:21px}}
</style>
