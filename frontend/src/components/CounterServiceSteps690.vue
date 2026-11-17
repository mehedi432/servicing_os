<script setup>
import {ref, watch, onBeforeUnmount} from 'vue'
// SOS_SERVICE_WORKFLOW_690 — use existing ERPNext permissions and repair_progress API.
const props = defineProps({jobName:{type:String,required:true}})
const emit = defineEmits(['updated'])
const stages = ['Received','Diagnosing','Waiting for Parts','Repairing','Completed','Ready to Deliver','Delivered']
const details = {Received:'Intake saved',Diagnosing:'Diagnose the fault','Waiting for Parts':'Parts required',Repairing:'Repair underway',Completed:'Repair finished', 'Ready to Deliver':'Ready for pickup',Delivered:'Customer handover'}
const progress=ref(null)
const loading=ref(false)
const busy=ref(false)
const selectedStatus=ref('')
const error=ref('')
const done=ref('')
let seq=0
function csrf(){
  return window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content ||
    decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'')
}
function formatError(body,status){
  try {const rows=JSON.parse(body?._server_messages||'[]');if(rows.length)return String(JSON.parse(rows[rows.length-1]).message||'').replace(/<[^>]*>/g,'') }catch{}
  return typeof body?.message==='string'?body.message:(body?.exception||`HTTP ${status}: repair operation unsuccessful`)
}
async function call(method,args={},post=false){
  const url = new URL('/api/method/servicing_os.api.repair_progress.'+method,window.location.origin)
  if(!post) for(const [k,v] of Object.entries(args))url.searchParams.set(k,String(v))
  const resp=await fetch(url,{method:post?'POST':'GET',credentials:'same-origin',cache:'no-store',
    headers:{Accept:'application/json',...(post?{'Content-Type':'application/json','X-Frappe-CSRF-Token':csrf()}:{})},
    ...(post?{body:JSON.stringify(args)}:{})})
  const body=await resp.json().catch(()=>({}))
  if(!resp.ok||body.exc||body.exc_type||body.exception)throw new Error(formatError(body,resp.status))
  return body.message||{}
}
async function load(){
  const name=String(props.jobName||'').trim()
  const mySeq=++seq
  progress.value=null;selectedStatus.value='';done.value='';error.value=''
  if(!name)return
  loading.value=true
  try{
    const next=await call('get_progress',{job_name:name})
    if(mySeq!==seq)return
    if(next.job!==name)throw Error('Repair API returned a different job. Refresh the selected job.')
    progress.value=next
  }catch(e){if(mySeq===seq)error.value=e.message||'Cannot load repair progress'}
  finally{if(mySeq===seq)loading.value=false}
}
async function advance(){
  const name=String(props.jobName||'').trim()
  if(!progress.value||busy.value||!selectedStatus.value)return
  if(progress.value.job!==name){error.value='Selected Service Job changed. Reload before updating.';return}
  if(!(progress.value.allowed_next_statuses||[]).includes(selectedStatus.value)){
    error.value='The selected transition is not allowed. Reload the current status.';return
  }
  if(selectedStatus.value==='Delivered'){
    error.value='Confirm payment and handover under Billing & Delivery before marking Delivered.';return
  }
  const destination=selectedStatus.value
  busy.value=true;error.value='';done.value=''
  try {
    const out=await call('advance_repair',{job_name:name,next_status:destination,expected_modified:progress.value.modified},true)
    if(name!==props.jobName)throw Error('Service selection changed; reload the record.')
    if(out.job!==name||out.status!==destination)throw Error('The server did not confirm the requested step.')
    done.value=`${name} updated to ${out.status}`
    emit('updated',{name,status:out.status})
    await load()
    done.value=`${name} updated to ${out.status}`
  }catch(e){error.value=e.message||'Unable to save repair step';await load().catch(()=>{});if(!error.value)error.value=e.message||'Repair step not saved'}
  finally{busy.value=false}
}
watch(()=>props.jobName,load,{immediate:true})
onBeforeUnmount(()=>{seq++})
</script>
<template>
<section class="sos690-steps" aria-label="Service Job repair steps">
  <header class="sos690-header">
    <div><small>REPAIR PROGRESS · {{ jobName }}</small><h3>Service Steps</h3>
      <p>Choose a valid next step; it is saved directly to the Service Job.</p></div>
    <button type="button" class="sos690-outline" :disabled="loading||busy" @click="load">Refresh</button>
  </header>
  <p v-if="error" role="alert" class="sos690-alert">{{ error }}</p>
  <p v-if="done" role="status" class="sos690-good">{{ done }}</p>
  <p v-if="loading" class="sos690-help">Loading live ERPNext repair status…</p>
  <template v-else-if="progress">
    <div class="sos690-current"><span>Current status</span><strong>{{ progress.status }}</strong></div>
    <div class="sos690-stage-grid" role="group" aria-label="Repair stages">
      <button v-for="s in stages" :key="s" type="button" class="sos690-stage"
        :class="{'is-current':progress.status===s,'is-available':(progress.allowed_next_statuses||[]).includes(s),'is-selected':selectedStatus===s}"
        :disabled="busy||progress.status===s||!(progress.allowed_next_statuses||[]).includes(s)||s==='Delivered'"
        :aria-pressed="selectedStatus===s"
        @click="selectedStatus=s">
        <strong>{{ s }}</strong><small>{{ progress.status===s?'Current':s==='Delivered'?'Use Billing':(progress.allowed_next_statuses||[]).includes(s)?'Select':'Locked' }}</small>
      </button>
    </div>
    <div class="sos690-action">
      <span>{{ selectedStatus ? (details[selectedStatus]||selectedStatus) : 'Select an available next step above' }}</span>
      <button type="button" class="sos690-primary" :disabled="busy||!selectedStatus||!(progress.allowed_next_statuses||[]).includes(selectedStatus)" @click="advance">
        {{ busy?'Saving step…':'Save Repair Step' }}
      </button>
    </div>
  </template>
  <p class="sos690-help">For <b>Waiting for Parts</b>, use the Spare Parts Required panel directly below. Approval does not deduct stock; stock issue is a separate authorized action.</p>
</section>
</template>
<style scoped>
.sos690-steps,.sos690-steps *{box-sizing:border-box}
.sos690-steps{border:1px solid #e1cfbf;background:#fffcf8;border-radius:14px;padding:14px;color:#423024;font-size:12px;min-width:0}
.sos690-header{display:flex;justify-content:space-between;gap:12px;align-items:center}.sos690-header small{font-size:10px;color:#98745a;font-weight:800;letter-spacing:.045em}.sos690-header h3{font-size:16px;margin:4px 0}.sos690-header p,.sos690-help{color:#8b725e;font-size:11px;line-height:1.6;margin:0}.sos690-outline,.sos690-primary{border:1px solid #dcbfa8;background:#fff7ef;border-radius:8px;padding:9px 12px;color:#735038;cursor:pointer;font-weight:750}.sos690-primary{background:#78553a;color:white;border-color:#78553a}.sos690-primary:disabled,.sos690-outline:disabled{opacity:.5;cursor:not-allowed}
.sos690-current{display:flex;justify-content:space-between;gap:8px;background:#f5e9dd;border-radius:9px;margin:12px 0;padding:10px}.sos690-current span{color:#8b725e}.sos690-current strong{color:#563820}
.sos690-stage-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:7px}.sos690-stage{border:1px solid #e6d5c3;border-radius:9px;background:#f9f5ef;color:#756353;min-width:0;padding:10px;display:grid;gap:4px;text-align:left;cursor:pointer}.sos690-stage strong{font-size:11px;overflow-wrap:break-word}.sos690-stage small{font-size:10px}.sos690-stage.is-current{border-color:#9e7555;background:#f3e7d8;color:#583922}.sos690-stage.is-available{border-color:#cab19a;background:#fffdf9;color:#563b2b}.sos690-stage.is-selected{outline:2px solid #896345;outline-offset:1px}.sos690-stage:disabled{opacity:.75;cursor:not-allowed}.sos690-action{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-top:13px;padding-top:12px;border-top:1px solid #eadac9}.sos690-action span{color:#8b725e;font-size:11px}.sos690-help{margin-top:9px}.sos690-alert,.sos690-good{padding:9px;border-radius:8px;margin:10px 0;font-size:11px;line-height:1.5}.sos690-alert{border:1px solid #e9c4b8;background:#fff2ec;color:#9d3d2c}.sos690-good{border:1px solid #cbdece;background:#f2f7f0;color:#396347}
@media(max-width:520px){.sos690-stage-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sos690-header{align-items:flex-start}}
</style>
