<script setup>
// AMCL_BILLING_MODAL_V3_616B3
import { ref, computed, onUnmounted } from 'vue'
const open = ref(false)
const mode = ref('invoice')
const step = ref(1)
const jobs = ref([])
const jobName = ref('')
const preview = ref(null)
const repairDetails = ref(null)
const nextStatus = ref('')
const updatingStatus = ref(false)
const laborRate = ref('')
const rates = ref({})
const report = ref(null)
const busy = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const validStatuses = ['Completed','Ready to Deliver','Delivered']
const steps = ['Select repair','Parts & labor','Review charges','Create draft']
const parts = computed(() => preview.value?.parts || [])
const existing = computed(() => preview.value?.existing_invoices || [])
const isReady = computed(() => validStatuses.includes(preview.value?.status))
const subtotalParts = computed(() => parts.value.reduce((sum, p) => sum + Number(p.qty || 0) * (Number(rates.value[p.item_code]) || 0), 0))
const subtotal = computed(() => subtotalParts.value + (Number(laborRate.value) || 0))
const validRates = computed(() => parts.value.every(p => rates.value[p.item_code] !== '' && rates.value[p.item_code] != null && Number.isFinite(Number(rates.value[p.item_code])) && Number(rates.value[p.item_code]) >= 0))
const validLabor = computed(() => laborRate.value !== '' && Number.isFinite(Number(laborRate.value)) && Number(laborRate.value) >= 0)
const canPrepare = computed(() => preview.value && !busy.value && !saving.value && !updatingStatus.value && isReady.value && !existing.value.length && validRates.value && validLabor.value && (parts.value.length > 0 || Number(laborRate.value) > 0))
const allowedNext = computed(() => repairDetails.value?.allowed_next_statuses || [])
function money(value) { const n=Number(value); return Number.isFinite(n) ? '৳'+n.toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2}) : '—' }
function csrf() { return window.frappe?.csrf_token || window.csrf_token || decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'') }
function serverError(data) {
  if (data._server_messages) { try { const a=JSON.parse(data._server_messages); const v=JSON.parse(a[a.length-1]); return String(v.message || 'Validation failed').replace(/<[^>]*>/g,'') } catch {} }
  return data.message?.message || data.exception || data.exc_type || 'ERPNext request failed'
}
async function rpc(method,args={},post=false) {
  const url=new URL('/api/method/'+method,window.location.origin)
  const options={method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}}
  if(post) {options.headers['Content-Type']='application/json';options.headers['X-Frappe-CSRF-Token']=csrf();options.body=JSON.stringify(args)}
  else for(const [k,v] of Object.entries(args)) if(v!==''&&v!==null&&v!==undefined) url.searchParams.set(k,String(v))
  const resp=await fetch(url,options); let data
  try {data=await resp.json()} catch {throw new Error('Unexpected server response ('+resp.status+')')}
  if(!resp.ok || data.exc || data.exc_type) throw new Error(serverError(data))
  return data.message
}
async function loadJobs() {
  busy.value=true;error.value=''
  try {const data=await rpc('servicing_os.api.lifecycle.list_repair_jobs',{limit:200}); jobs.value=data?.jobs||[]}
  catch(e) {error.value=e.message} finally {busy.value=false}
}
async function loadRepairDetails() {
  repairDetails.value=null;nextStatus.value=''
  if(!jobName.value) return
  try {const detail=await rpc('servicing_os.api.lifecycle.get_repair_job',{job_name:jobName.value});repairDetails.value=detail;nextStatus.value=''}
  catch(e) {error.value=e.message}
}
async function showBill() {
  error.value='';notice.value='';preview.value=null;repairDetails.value=null;rates.value={};laborRate.value=''
  if(!jobName.value) return
  busy.value=true
  try {
    const result=await rpc('servicing_os.api.repair_billing.preview_repair_bill',{job_name:jobName.value})
    preview.value=result
    const r={};for(const p of result.parts||[])r[p.item_code]=p.selling_rate==null?'':String(p.selling_rate)
    rates.value=r
    try {const detail=await rpc('servicing_os.api.lifecycle.get_repair_job',{job_name:jobName.value});repairDetails.value=detail}
    catch(e) {error.value='Status editing unavailable: '+e.message}
  } catch(e) {error.value=e.message} finally {busy.value=false}
}
async function saveStatus() {
  if(!jobName.value || !nextStatus.value || updatingStatus.value || !repairDetails.value) return
  error.value='';notice.value='';updatingStatus.value=true
  try {
    await rpc('servicing_os.api.lifecycle.update_repair_job',{
      job_name:jobName.value,status:nextStatus.value,
      expected_modified:repairDetails.value.job?.modified
    },true)
    const previous=nextStatus.value
    await showBill();await loadJobs()
    notice.value='Repair moved to '+previous+'. You can review billing at any stage.'
  } catch(e) {error.value=e.message} finally {updatingStatus.value=false}
}
async function createDraft() {
  if(!canPrepare.value || !jobName.value) return
  if(!window.confirm('Create a DRAFT Sales Invoice for '+jobName.value+'? No stock will be deducted.')) return
  saving.value=true;error.value='';notice.value=''
  try {
    const part_rates=Object.fromEntries(parts.value.map(p=>[p.item_code,Number(rates.value[p.item_code])]))
    const result=await rpc('servicing_os.api.repair_billing.create_draft_repair_invoice',{
      job_name:jobName.value,labor_rate:Number(laborRate.value),part_rates
    },true)
    await showBill()
    notice.value='Draft '+result.sales_invoice+' created. Review and submit it in ERPNext.'
    step.value=4
  } catch(e) {error.value=e.message} finally {saving.value=false}
}
async function loadReport() {
  busy.value=true;error.value=''
  try {report.value=await rpc('servicing_os.api.repair_billing.repair_contribution_report',{limit:100})}
  catch(e) {error.value=e.message}finally {busy.value=false}
}
function openInvoice(name) {window.open('/app/sales-invoice/'+encodeURIComponent(name),'_blank','noopener,noreferrer')}
function close() {open.value=false;document.body.style.overflow=previousOverflow}
let previousOverflow=''
function toggle() {
  if(open.value){close();return}
  previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden'
  open.value=true;mode.value='invoice';step.value=1;error.value='';notice.value=''
  if(!jobs.value.length)loadJobs()
}
onUnmounted(()=>{if(open.value)document.body.style.overflow=previousOverflow})
</script>

<template>
  <button class="bill-launch-v3" type="button" @click="toggle" aria-haspopup="dialog">
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/></svg>
    Prepare Invoice
  </button>
  <Teleport to="body">
    <div v-if="open" class="bill-shade-v3" @click.self="close">
      <div class="bill-window-v3" role="dialog" aria-modal="true" aria-labelledby="bill-title-v3" @keydown.esc="close">
        <header class="bill-top-v3">
          <div class="bill-heading-v3"><span class="bill-kicker-v3">SERVICING OS / REPAIR ACCOUNTING</span><h2 id="bill-title-v3">Prepare repair invoice</h2><p>Four simple steps, from repair selection to draft invoice.</p></div>
          <button type="button" class="bill-close-v3" @click="close" aria-label="Close billing dialog">✕</button>
        </header>
        <div class="bill-tabs-v3"><button type="button" :class="{selected:mode==='invoice'}" @click="mode='invoice'">Invoice preparation</button><button type="button" :class="{selected:mode==='report'}" @click="mode='report';loadReport()">Contribution report</button></div>
        <div class="bill-scroll-v3">
          <div v-if="error" class="bill-message-v3 error" role="alert">{{ error }}</div>
          <div v-if="notice" class="bill-message-v3 success" role="status">{{ notice }}</div>
          <template v-if="mode==='invoice'">
            <nav class="bill-progress-v3" aria-label="Invoice steps">
              <button v-for="(label,i) in steps" :key="label" type="button" :class="{active:step===i+1,complete:step>i+1}" :disabled="i>0&&!preview" @click="step=i+1"><span>{{ String(i+1).padStart(2,'0') }}</span>{{ label }}</button>
            </nav>
            <section v-if="step===1" class="bill-content-v3">
              <div class="bill-section-caption-v3">01 / SELECT REPAIR</div><h3>Which device are we billing?</h3><p>Choose a repair. You can inspect the whole invoice even when it is still in progress.</p>
              <label class="bill-label-v3">Service Job
                <select v-model="jobName" @change="showBill"><option value="">Choose a Service Job...</option><option v-for="j in jobs" :key="j.name" :value="j.name">{{ j.name }} · {{ j.customer_name || 'Customer' }} · {{ j.status }}</option></select>
              </label>
              <button type="button" class="bill-textbutton-v3" :disabled="busy" @click="loadJobs">{{ busy?'Loading jobs…':'Refresh repair list' }}</button>
              <div v-if="preview" class="bill-job-v3"><div><strong>{{ preview.service_job }}</strong><span>{{ preview.customer }}</span></div><span class="bill-chip-v3">{{ preview.status }}</span></div>
              <div v-if="preview&&!isReady" class="bill-advice-v3"><strong>Billing can be reviewed now.</strong> A draft invoice can only be created at <b>Completed</b> or a later delivery stage. You can update the repair status below, following the normal workflow.</div>
              <div v-if="preview" class="bill-status-box-v3">
                <div class="bill-status-head-v3"><div><b>Repair progress</b><span>Current status: {{ preview.status }}</span></div><span class="bill-small-v3">Update without leaving billing</span></div>
                <div v-if="allowedNext.length" class="bill-status-actions-v3">
                  <select v-model="nextStatus" aria-label="Next repair status"><option value="">Select next step...</option><option v-for="s in allowedNext" :key="s" :value="s">{{ s }}</option></select>
                  <button type="button" class="bill-secondary-v3" :disabled="!nextStatus||updatingStatus" @click="saveStatus">{{ updatingStatus?'Updating…':'Update status' }}</button>
                </div>
                <p v-else class="bill-small-v3">No further transitions are available for this job or you do not have edit permission.</p>
                <p class="bill-small-v3">Normal progression: Received → Diagnosing → Repairing → Completed → Ready to Deliver → Delivered. Waiting for Parts is available when needed.</p>
              </div>
              <div v-if="existing.length" class="bill-advice-v3">Existing invoice found. A second invoice is blocked through this workflow.<div v-for="inv in existing" :key="inv.name" class="bill-existing-v3"><b>{{ inv.name }}</b><button type="button" @click="openInvoice(inv.name)">Open invoice ↗</button></div></div>
            </section>
            <section v-else-if="step===2" class="bill-content-v3">
              <div class="bill-section-caption-v3">02 / PARTS & LABOR</div><h3>What should the customer pay?</h3><p>Issued parts are loaded from submitted Material Issues. No stock is deducted during billing.</p>
              <div class="bill-tablewrap-v3"><table><thead><tr><th>Part</th><th>Quantity</th><th>Selling rate (BDT)</th><th>Line total</th></tr></thead><tbody><tr v-if="!parts.length"><td colspan="4" class="bill-empty-v3">No issued parts. You can still invoice repair labor.</td></tr><tr v-for="p in parts" :key="p.item_code"><td><strong>{{ p.item_code }}</strong></td><td>{{ p.qty }}</td><td><input v-model="rates[p.item_code]" type="number" min="0" step="0.01" :aria-label="'Selling rate for '+p.item_code"/></td><td>{{ money(Number(p.qty)*Number(rates[p.item_code]||0)) }}</td></tr></tbody></table></div>
              <label class="bill-label-v3 bill-labor-v3">Customer labor charge (BDT)<input v-model="laborRate" type="number" min="0" step="0.01" placeholder="Enter repair labor charge"/><span>AMCL-REPAIR-LABOR · Service - AMCL</span></label>
              <div class="bill-total-v3"><span>Estimated subtotal before taxes</span><strong>{{ money(subtotal) }}</strong></div>
            </section>
            <section v-else-if="step===3" class="bill-content-v3">
              <div class="bill-section-caption-v3">03 / REVIEW</div><h3>Confirm the invoice details</h3><p>Check the customer, repair, parts and labor before preparing a draft.</p>
              <div class="bill-review-v3"><div><span>Repair</span><b>{{ preview?.service_job }}</b></div><div><span>Customer</span><b>{{ preview?.customer }}</b></div><div><span>Parts subtotal</span><b>{{ money(subtotalParts) }}</b></div><div><span>Labor</span><b>{{ money(Number(laborRate)||0) }}</b></div><div class="total"><span>Pre-tax subtotal</span><b>{{ money(subtotal) }}</b></div></div>
              <div class="bill-advice-v3">Draft only: no automatic submission, stock movement, or GL posting. Accounting should review prices, taxes and accounts in ERPNext.</div>
            </section>
            <section v-else-if="step===4" class="bill-content-v3">
              <div class="bill-section-caption-v3">04 / PREPARE DRAFT</div><h3>Save the invoice for accounting review</h3><p>All invoice creation rules are checked by the server again when you click the final button.</p>
              <div class="bill-total-v3"><span>Estimated amount before tax</span><strong>{{ money(subtotal) }}</strong></div>
              <div v-if="!isReady" class="bill-advice-v3"><b>Repair is {{ preview?.status }}.</b> To enable invoice creation, use <b>Back</b> to return to Step 1 and advance the status to Completed. You do not need to mark the device Delivered before billing.</div>
              <div v-if="existing.length" class="bill-advice-v3">An invoice already exists. You cannot create a duplicate through this action.</div>
              <div v-if="!validRates||!validLabor" class="bill-advice-v3">Complete the selling prices and labor amount in Step 2 before creating an invoice.</div>
              <button type="button" class="bill-primary-v3 bill-create-v3" :disabled="!canPrepare" @click="createDraft">{{ saving?'Creating draft…':'Create Draft Sales Invoice' }}</button>
              <p class="bill-small-v3">No stock will be deducted again; Update Stock = No.</p>
            </section>
          </template>
          <section v-else class="bill-content-v3"><div class="bill-section-caption-v3">ACCOUNTING REPORT</div><h3>Repair contribution</h3><p>Submitted invoice revenue less issued-parts valuation. Internal technician labor and overhead are excluded.</p><button class="bill-textbutton-v3" type="button" :disabled="busy" @click="loadReport">Refresh report</button><div class="bill-tablewrap-v3"><table><thead><tr><th>Job</th><th>Technician</th><th>Revenue</th><th>Parts cost</th><th>Contribution</th></tr></thead><tbody><tr v-for="j in report?.jobs||[]" :key="j.service_job"><td>{{ j.service_job }}</td><td>{{ j.technician||'—' }}</td><td>{{ j.net_revenue_ex_tax==null?'Not invoiced':money(j.net_revenue_ex_tax) }}</td><td>{{ j.issued_parts_cost==null?'Unknown':money(j.issued_parts_cost) }}</td><td>{{ j.contribution_before_labor_and_overhead==null?'—':money(j.contribution_before_labor_and_overhead) }}</td></tr><tr v-if="!report?.jobs?.length"><td colspan="5" class="bill-empty-v3">No report records returned.</td></tr></tbody></table></div></section>
        </div>
        <footer class="bill-bottom-v3"><button type="button" class="bill-secondary-v3" @click="close">Close</button><div v-if="mode==='invoice'" class="bill-buttons-v3"><button v-if="step>1" type="button" class="bill-secondary-v3" @click="step--">← Back</button><button v-if="step<4" type="button" class="bill-primary-v3" :disabled="step===1&&!preview || busy" @click="step++">Continue →</button></div></footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.bill-launch-v3{display:inline-flex;align-items:center;justify-content:center;gap:9px;min-height:40px;background:#80613d;color:#fff;border:1px solid #80613d;border-radius:11px;padding:10px 15px;font-size:12px;font-weight:750;white-space:nowrap;cursor:pointer;box-shadow:0 2px 7px #55412818}.bill-launch-v3:hover{background:#6b4c30}
.bill-shade-v3{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(28,25,21,.58);backdrop-filter:blur(3px)}
.bill-window-v3{display:flex;flex-direction:column;width:min(880px,100%);max-height:min(92dvh,940px);overflow:hidden;border-radius:20px;background:#fffdf9;border:1px solid #e3d6c5;box-shadow:0 32px 100px #251d1460;color:#473d30;font-size:13px}
.bill-top-v3{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:22px 26px 18px;border-bottom:1px solid #e7dfd2;background:#fffdf9}.bill-kicker-v3{color:#a28a66;font-size:10px;letter-spacing:1.2px;font-weight:800}.bill-heading-v3 h2{font-size:24px;font-weight:750;margin:5px 0 3px}.bill-heading-v3 p{color:#8f806d;font-size:12px}.bill-close-v3{display:grid;place-items:center;width:38px;height:38px;flex-shrink:0;background:#f7f0e6;border:1px solid #e6d9c7;border-radius:11px;cursor:pointer}.bill-close-v3:hover{background:#eddfcb}
.bill-tabs-v3{display:flex;gap:5px;padding:10px 26px;border-bottom:1px solid #e8dfd2}.bill-tabs-v3 button{padding:9px 13px;font-size:12px;font-weight:700;color:#877660;border-radius:9px;cursor:pointer}.bill-tabs-v3 button.selected{background:#eee4d7;color:#6d5033}
.bill-scroll-v3{padding:22px 26px;min-height:0;overflow-y:auto;overscroll-behavior:contain;flex:1}.bill-progress-v3{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-bottom:20px}.bill-progress-v3 button{display:flex;align-items:center;gap:9px;border:1px solid #e7ddcf;border-radius:10px;background:#fbf8f3;color:#8c806f;padding:10px 9px;text-align:left;font-size:11px;font-weight:650}.bill-progress-v3 button span{font-size:10px;color:#9e8867;font-weight:800}.bill-progress-v3 button.active{background:#f0e4d3;border-color:#ceba9b;color:#624a30}.bill-progress-v3 button.complete{background:#eef2e8;color:#4b6545}.bill-progress-v3 button:disabled{opacity:.6;cursor:not-allowed}
.bill-content-v3{min-height:210px}.bill-section-caption-v3{font-size:10px;font-weight:800;letter-spacing:1.3px;color:#a28158}.bill-content-v3 h3{font-size:19px;font-weight:750;margin:7px 0}.bill-content-v3>p{font-size:12px;color:#887a6b;line-height:1.55;margin:0 0 17px}.bill-label-v3{display:flex;flex-direction:column;gap:9px;max-width:100%;margin:15px 0;font-weight:700;font-size:12px}.bill-label-v3 input,.bill-label-v3 select,.bill-status-actions-v3 select{width:100%;min-width:0;border:1px solid #d9cbb7;border-radius:10px;background:#fff;color:#40382d;padding:12px;font-size:13px}.bill-label-v3 span{font-size:11px;color:#8e806d;font-weight:450}.bill-textbutton-v3{padding:4px 0;color:#80603c;text-decoration:underline;font-size:12px;font-weight:750;cursor:pointer}.bill-job-v3{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:18px;background:#f6efe3;border:1px solid #e5d7c3;padding:15px;border-radius:13px}.bill-job-v3>div{display:flex;flex-direction:column;gap:3px}.bill-job-v3 strong{font-size:14px}.bill-job-v3 span{color:#74634f}.bill-chip-v3{background:#e9dbc5;padding:7px 10px;border-radius:99px;white-space:nowrap;font-size:11px;font-weight:750}
.bill-advice-v3{border:1px solid #edd8b6;background:#fff7e9;color:#795a2f;border-radius:12px;padding:13px 15px;font-size:12px;line-height:1.6;margin:15px 0}.bill-status-box-v3{border:1px solid #e8dfd0;background:#fcfaf6;border-radius:13px;padding:16px;margin:16px 0}.bill-status-head-v3{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:13px}.bill-status-head-v3>div{display:flex;flex-direction:column;gap:4px}.bill-status-head-v3 span,.bill-small-v3{color:#897b69;font-size:11px;line-height:1.6}.bill-status-actions-v3{display:flex;gap:10px;align-items:center}.bill-status-actions-v3 select{flex:1}.bill-secondary-v3{border:1px solid #dacdbb;background:#f9f5ee;color:#684f33;border-radius:10px;padding:11px 15px;font-size:12px;font-weight:750;cursor:pointer;white-space:nowrap}.bill-secondary-v3:hover{background:#eee3d4}.bill-secondary-v3:disabled{opacity:.5;cursor:not-allowed}.bill-primary-v3{border:1px solid #785a3b;background:#785a3b;color:white;border-radius:10px;padding:11px 16px;font-size:12px;font-weight:750;white-space:nowrap;cursor:pointer}.bill-primary-v3:hover:not(:disabled){background:#5c402c}.bill-primary-v3:disabled{opacity:.45;cursor:not-allowed}.bill-existing-v3{display:flex;align-items:center;gap:16px;justify-content:space-between;margin-top:10px}.bill-existing-v3 button{color:#785533;text-decoration:underline;cursor:pointer}
.bill-tablewrap-v3{border:1px solid #e8ddce;border-radius:12px;overflow-x:auto;margin:13px 0}.bill-tablewrap-v3 table{width:100%;border-collapse:collapse;text-align:left;min-width:520px;font-size:12px}.bill-tablewrap-v3 th{padding:12px;background:#f7f1e8;color:#816d54;white-space:nowrap;font-size:11px}.bill-tablewrap-v3 td{padding:12px;border-top:1px solid #ebe2d8}.bill-tablewrap-v3 input{max-width:130px;border:1px solid #d9cbb7;border-radius:9px;padding:9px;font-size:12px}.bill-empty-v3{text-align:center;color:#92836f;padding:25px!important}.bill-labor-v3{max-width:420px}.bill-total-v3{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#f3ebdf;border:1px solid #e2d1ba;border-radius:12px;padding:16px;margin-top:18px}.bill-total-v3 strong{font-size:22px}.bill-review-v3{margin-top:17px;border:1px solid #e5dacb;border-radius:12px;overflow:hidden}.bill-review-v3>div{display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid #e9e0d5;padding:13px 15px}.bill-review-v3>div:last-child{border:0}.bill-review-v3 span{color:#877763;font-size:12px}.bill-review-v3 .total{background:#f8f0e5;font-size:15px}
.bill-bottom-v3{border-top:1px solid #e9dfd2;display:flex;justify-content:space-between;align-items:center;padding:14px 26px;gap:12px;background:#fffdf9}.bill-buttons-v3{display:flex;gap:9px}.bill-message-v3{padding:12px 14px;border-radius:11px;margin-bottom:12px;font-size:12px;line-height:1.5}.bill-message-v3.error{color:#913b32;background:#fff0ed;border:1px solid #f0d3ce}.bill-message-v3.success{color:#32633a;background:#eff8ec;border:1px solid #d9eace}
@media(max-width:700px){.bill-shade-v3{padding:6px}.bill-window-v3{max-height:98dvh;border-radius:13px}.bill-top-v3{padding:15px 16px}.bill-heading-v3 h2{font-size:19px}.bill-scroll-v3{padding:16px}.bill-tabs-v3{padding:8px 16px}.bill-bottom-v3{padding:12px 16px}.bill-progress-v3{grid-template-columns:repeat(2,minmax(0,1fr))}.bill-status-actions-v3{flex-direction:column;align-items:stretch}.bill-total-v3 strong{font-size:17px}}
</style>
