<script setup>
// SOS_COUNTER_PARTS_INLINE_689 - uses the project's existing ERPNext Material Request APIs.
import { ref, watch, onBeforeUnmount, computed } from 'vue'
const props = defineProps({ jobName: { type: String, required: true }, jobStatus: { type: String, default: '' } })
const search = ref('')
const results = ref([])
const chosen = ref(null)
const qty = ref(1)
const items = ref([])
const notes = ref('')
const requests = ref([])
const permissions = ref({manager:false})
const issueState = ref({})
const error = ref('')
const message = ref('')
const loading = ref(false)
const searching = ref(false)
const busy = ref(false)
// SOS_SERVICE_WORKFLOW_690: show required parts as soon as a service is saved.
const expanded = ref(true)
let delay = null
let serial = 0
const closed = computed(() => ['Delivered','Cancelled','Canceled'].includes(props.jobStatus))
function csrf() {
  return window.frappe?.csrf_token || window.csrf_token || decodeURIComponent(
    document.cookie.split('; ').find(x => x.startsWith('csrf_token='))?.split('=').slice(1).join('=') || ''
  )
}
function err(body, fallback) {
  try { const msg = JSON.parse(body?._server_messages || '[]'); if(msg.length) return JSON.parse(msg[msg.length-1]).message.replace(/<[^>]*>/g, '') } catch {}
  return body?.message?.message || body?.exception || fallback
}
async function call(api, method, args={}, post=false) {
  const url = new URL(`/api/method/servicing_os.api.${api}.${method}`,window.location.origin)
  const opts={method:post?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}}
  if(post){opts.headers['Content-Type']='application/json'; opts.headers['X-Frappe-CSRF-Token']=csrf();opts.body=JSON.stringify(args)}
  else Object.entries(args).forEach(([key,value])=>{if(value!==null&&value!==undefined&&value!=='')url.searchParams.set(key,String(value))})
  const res=await fetch(url,opts)
  const body=await res.json().catch(()=>({}))
  if(!res.ok||body.exc||body.exc_type||body.exception)throw Error(err(body,`Parts API error HTTP ${res.status}`))
  return body.message || {}
}
async function load() {
  if(!props.jobName)return
  const name=props.jobName
  loading.value=true;error.value=''
  try {
    const [requestsData,permissionData]=await Promise.all([
      call('parts_request','list_parts_requests',{job_name:name}),
      call('parts_request_manage','manage_permissions')
    ])
    if(props.jobName===name){requests.value=(requestsData.requests||[]).filter(x=>x.custom_service_job===name);permissions.value=permissionData; await loadIssueStates(requests.value)}
  } catch(e){if(props.jobName===name) error.value=e.message || 'Cannot load parts requests.'}
  finally{if(props.jobName===name)loading.value=false}
}
async function findParts(q=''){
  const seq=++serial
  searching.value=true
  try{const data=await call('parts_request_manage','search_saleable_parts',{search:q});if(seq===serial)results.value=data.items || []}
  catch(e){if(seq===serial)error.value=e.message||'Parts search failed.'}
  finally{if(seq===serial)searching.value=false}
}
async function loadIssueStates(list) {
  const state={}
  for(const r of list.filter(x=>x.docstatus===1).slice(0,25)) {
    try {state[r.name] = await call('counter_parts_689','issue_state',{material_request:r.name})}
    catch(e) {state[r.name]={error:e.message||'Cannot check issue status'}}
  }
  issueState.value=state
}
async function issue(r) {
  if(busy.value || !issueState.value[r.name]?.can_issue)return
  if(!window.confirm(`ISSUE PARTS AND DEDUCT STOCK for ${r.name}? This creates and submits an ERPNext Stock Entry.`))return
  const confirm=window.prompt(`To confirm physical stock issue, enter Material Request ${r.name}`,'')
  if(confirm!==r.name)return
  busy.value=true;error.value='';message.value=''
  try {
    const out=await call('counter_parts_689','issue_parts',{material_request:r.name, confirm},true)
    if(!out.stock_deducted)throw Error('Stock Entry was not submitted; no confirmation of stock issue.')
    message.value=`Stock issued in ${out.stock_entry}. ERPNext Stock Ledger updated.`
    await load()
  } catch(e){error.value=e.message || 'Stock issue failed. No success confirmation.'}
  finally{busy.value=false}
}
function select(item){serial++;chosen.value=item;search.value=`${item.item_name} (${item.item_code})`;results.value=[]}
function add(){
  error.value=''
  const amount=Number(qty.value)
  if(!chosen.value){error.value='Select an Item from the search results.';return}
  if(!Number.isFinite(amount)||amount<=0){error.value='Enter a positive quantity.';return}
  const found=items.value.find(x=>x.item_code===chosen.value.item_code)
  if(found)found.qty+=amount
  else items.value.push({item_code:chosen.value.item_code,item_name:chosen.value.item_name,qty:amount,uom:chosen.value.uom})
  chosen.value=null;search.value='';qty.value=1
}
async function requestParts(){
  if(!props.jobName||!items.value.length||busy.value||closed.value)return
  if(!window.confirm(`Create a Draft Material Request for ${props.jobName}? This does NOT issue stock.`))return
  const current=props.jobName
  busy.value=true;error.value='';message.value=''
  try{
    const data=await call('parts_request','create_multi_parts_request',{
      job_name:current,items:items.value.map(x=>({item_code:x.item_code,qty:x.qty})),remarks:notes.value.trim()
    },true)
    if(current===props.jobName){items.value=[];notes.value='';message.value=`Draft ${data.material_request} created. Stock has NOT been issued.`;await load()}
  }catch(e){error.value=e.message || 'Could not request parts.'}
  finally{busy.value=false}
}
async function approve(r){
  if(busy.value||!permissions.value.manager||r.docstatus!==0)return
  if(!window.confirm(`Approve ${r.name}? Approval does not issue stock.`))return
  busy.value=true;error.value='';message.value=''
  try{await call('parts_request','approve_parts_request',{material_request:r.name},true);message.value=`Approved ${r.name}. A stock issue is still required.`;await load()}
  catch(e){error.value=e.message||'Approval failed.'}
  finally{busy.value=false}
}
watch(()=>props.jobName,()=>{items.value=[];chosen.value=null;search.value='';notes.value='';message.value='';error.value='';expanded.value=true;requests.value=[];issueState.value={};load()}, {immediate:true})
watch(search,(value)=>{if(delay)clearTimeout(delay); if(chosen.value && value.endsWith(`(${chosen.value.item_code})`))return; chosen.value=null; if(!value.trim()){serial++;results.value=[];return}delay=setTimeout(()=>findParts(value.trim()),240)})
onBeforeUnmount(()=>{if(delay)clearTimeout(delay)})
</script>

<template>
  <section v-if="jobName" class="sos689-parts" aria-label="Spare Parts for selected Service Job">
    <header class="sos689-heading">
      <div><small>EXISTING SERVICE JOB · {{ jobName }}</small><h3>Spare Parts Required</h3><p>Request parts here without leaving Service Receive.</p></div>
      <button type="button" class="sos689-quiet" @click="expanded=!expanded">{{ expanded?'Hide Parts':'Manage Parts' }}</button>
    </header>
    <template v-if="expanded">
      <p v-if="error" class="sos689-error" role="alert">{{ error }}</p>
      <p v-if="message" class="sos689-good" role="status">{{ message }}</p>
      <p v-if="closed" class="sos689-error">This job is {{ jobStatus }}; new parts cannot be requested.</p>
      <div v-if="!closed" class="sos689-editor">
        <label>Find stock item (Item Code or name)
          <input v-model="search" type="search" autocomplete="off" placeholder="SSD, RAM, charger, item code…" />
        </label>
        <div v-if="searching" class="sos689-muted">Searching items…</div>
        <div v-else-if="results.length" class="sos689-results">
          <button v-for="p in results" :key="p.item_code" type="button" @click="select(p)">
            <strong>{{ p.item_name }}</strong><small>{{ p.item_code }} · {{ p.available_qty }} {{ p.uom }} available</small>
          </button>
        </div>
        <div class="sos689-add">
          <label>Quantity<input v-model.number="qty" type="number" min="0.001" step="any" /></label>
          <button type="button" class="sos689-quiet" :disabled="!chosen" @click="add">+ Add Part</button>
        </div>
        <div v-if="items.length" class="sos689-lines">
          <div v-for="item in items" :key="item.item_code" class="sos689-line">
            <span><strong>{{ item.item_name }}</strong><small>{{ item.item_code }}</small></span>
            <input v-model.number="item.qty" type="number" min="0.001" step="any" :aria-label="`Quantity for ${item.item_code}`" />
            <button type="button" @click="items=items.filter(x=>x.item_code!==item.item_code)">Remove</button>
          </div>
        </div>
        <label>Parts requirement notes<textarea v-model="notes" rows="2" maxlength="500" placeholder="Why are these parts required?"></textarea></label>
        <button type="button" class="sos689-primary" :disabled="busy||!items.length||items.some(x=>!(Number(x.qty)>0))" @click="requestParts">
          {{ busy?'Saving…':`Create Draft Parts Request (${items.length})` }}
        </button>
      </div>
      <div class="sos689-requests">
        <div class="sos689-request-header"><strong>Existing requests</strong><button type="button" class="sos689-quiet" :disabled="loading" @click="load">Refresh</button></div>
        <p v-if="loading" class="sos689-muted">Loading existing requests…</p>
        <p v-else-if="!requests.length" class="sos689-muted">No parts requests for this job.</p>
        <div v-for="req in requests" :key="req.name" class="sos689-request">
          <span><strong>{{ req.name }}</strong><small>{{ req.docstatus===0?'Draft':req.docstatus===1?'Approved':'Cancelled' }} · {{ req.transaction_date }}</small></span>
          <div class="sos689-issue-actions">
            <button v-if="permissions.manager && req.docstatus===0" type="button" class="sos689-quiet" :disabled="busy" @click="approve(req)">Approve</button>
            <button v-if="issueState[req.name]?.can_issue" type="button" class="sos689-primary" :disabled="busy" @click="issue(req)">Issue Parts &amp; Deduct Stock</button>
            <small v-if="issueState[req.name]?.issued" class="sos689-issued">✓ Stock issued</small>
            <small v-else-if="issueState[req.name]?.has_draft" class="sos689-muted">Existing draft Stock Entry</small>
          </div>
        </div>
        <p class="sos689-muted">A draft or approved Material Request does not deduct stock. The manager-only Issue Parts action submits a native ERPNext Stock Entry; never also deduct the same parts through the invoice.</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.sos689-parts{min-width:0;border:1px solid #e5d2be;background:#f9f1e7;border-radius:14px;padding:13px;margin:11px 0 14px;color:#463021;font-size:12px;box-sizing:border-box}
.sos689-parts *{box-sizing:border-box}.sos689-heading{display:flex;justify-content:space-between;gap:10px;align-items:center}.sos689-heading h3{font-size:15px;font-weight:750;margin:2px 0}.sos689-heading small{font-size:10px;font-weight:750;color:#9b7656}.sos689-heading p,.sos689-muted{font-size:11px;color:#967b63}.sos689-quiet,.sos689-primary{border:1px solid #dec5ad;padding:8px 11px;background:#fffaf4;color:#705037;border-radius:9px;cursor:pointer;font-size:11px;font-weight:700;white-space:nowrap}.sos689-primary{background:#765239;border-color:#765239;color:white;white-space:normal}.sos689-quiet:disabled,.sos689-primary:disabled{opacity:.5;cursor:not-allowed}.sos689-editor{border-top:1px solid #e5d3c1;padding-top:11px;margin-top:11px;display:grid;gap:10px}.sos689-editor label{display:grid;gap:5px;min-width:0;font-size:11px;font-weight:700;color:#71543e}.sos689-editor input,.sos689-editor textarea{width:100%;min-width:0;border:1px solid #ddcbb7;background:white;border-radius:8px;padding:8px;color:#443124;font-size:12px}.sos689-results{display:grid;gap:4px;max-height:180px;overflow:auto;padding:4px;border:1px solid #e6d6c3;background:white;border-radius:9px}.sos689-results button{border:0;text-align:left;background:#fffdf9;border-radius:6px;display:grid;gap:2px;padding:8px;cursor:pointer}.sos689-results button:hover{background:#f5e8d9}.sos689-results small,.sos689-line small,.sos689-request small{display:block;font-size:10px;color:#97816c}.sos689-add{display:flex;align-items:end;gap:8px}.sos689-add label{width:110px}.sos689-lines{display:grid;gap:6px}.sos689-line{display:grid;grid-template-columns:minmax(0,1fr) 75px auto;gap:7px;align-items:center;background:#fff;border-radius:8px;border:1px solid #e5d7ca;padding:8px}.sos689-line span{min-width:0}.sos689-line strong{font-size:11px;overflow-wrap:anywhere}.sos689-line button{background:none;border:0;color:#a34e3d;font-size:11px;cursor:pointer}.sos689-requests{display:grid;gap:7px;margin-top:10px}.sos689-request-header{display:flex;justify-content:space-between;align-items:center;gap:8px}.sos689-request{background:#fffdf9;border:1px solid #e7daca;border-radius:9px;padding:8px;display:flex;justify-content:space-between;align-items:center;gap:7px;min-width:0}.sos689-request span{min-width:0;overflow-wrap:anywhere}.sos689-error,.sos689-good{border-radius:8px;padding:9px 10px;font-size:11px;line-height:1.5;margin-top:10px}.sos689-error{color:#922f25;background:#fff2ec;border:1px solid #f0d3c6}.sos689-good{color:#37634a;background:#eef5ed;border:1px solid #d5e5d2}@media(max-width:430px){.sos689-heading{align-items:flex-start;flex-wrap:wrap}.sos689-line{grid-template-columns:minmax(0,1fr) 55px auto}}
.sos689-issue-actions{display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap}.sos689-issued{color:#3b7152;font-size:10px;font-weight:700}
</style>
