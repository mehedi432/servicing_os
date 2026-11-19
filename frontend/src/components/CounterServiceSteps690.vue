<script setup>
import {computed, ref, watch, onBeforeUnmount} from 'vue'
// SOS_SERVICE_WORKFLOW_690 — use existing ERPNext permissions and repair_progress API.
const props = defineProps({jobName:{type:String,required:true}})
const emit = defineEmits(['updated'])
const stages = ['Received','Diagnosing','Waiting for Parts','Repairing','Completed','Ready to Deliver','Delivered']
const actions = {
  Diagnosing: 'Start diagnosis', 'Waiting for Parts': 'Wait for parts', Repairing: 'Start repair',
  Completed: 'Mark repair complete', 'Ready to Deliver': 'Mark ready for pickup',
}
const preferred = {Received:'Diagnosing', Diagnosing:'Repairing', 'Waiting for Parts':'Repairing', Repairing:'Completed', Completed:'Ready to Deliver'}
const progress=ref(null)
const nextSteps = computed(() => {
  const options = stages.filter(stage => actions[stage] && stage !== progress.value?.status && progress.value?.allowed_next_statuses?.includes(stage))
  const primary = preferred[progress.value?.status]
  return options.includes(primary) ? [primary, ...options.filter(stage => stage !== primary)] : options
})
const loading=ref(false)
const savingStep=ref('')
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
  progress.value=null;done.value='';error.value=''
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
function actionLabel(stage) {
  if (stage === 'Repairing' && ['Waiting for Parts', 'Completed'].includes(progress.value?.status)) return 'Resume repair'
  if (stage === 'Diagnosing' && progress.value?.status === 'Waiting for Parts') return 'Return to diagnosis'
  return actions[stage]
}
function goToParts() {
  const parts = document.getElementById(`repair-parts-${props.jobName}`)
  if (!parts) return
  parts.focus({ preventScroll: true })
  parts.scrollIntoView({ block: 'start' })
}
async function advance(destination){
  const name=String(props.jobName||'').trim()
  if(!progress.value||savingStep.value)return
  if(progress.value.job!==name){error.value='Selected Service Job changed. Reload before updating.';return}
  if(!nextSteps.value.includes(destination)){
    error.value='The selected transition is not allowed. Reload the current status.';return
  }
  savingStep.value=destination;error.value='';done.value=''
  try {
    const out=await call('advance_repair',{job_name:name,next_status:destination,expected_modified:progress.value.modified},true)
    if(name!==props.jobName)throw Error('Service selection changed; reload the record.')
    if(out.job!==name||out.status!==destination)throw Error('The server did not confirm the requested step.')
    progress.value = { ...progress.value, ...out }
    done.value = `Updated to ${out.status}`
    emit('updated',{name,status:out.status})
  }catch(e){error.value=e.message||'Unable to save repair step';await load().catch(()=>{});if(!error.value)error.value=e.message||'Repair step not saved'}
  finally{savingStep.value=''}
}
watch(()=>props.jobName,load,{immediate:true})
onBeforeUnmount(()=>{seq++})
</script>
<template>
<section class="sos690-steps" aria-label="Service Job repair steps">
  <header class="sos690-header">
    <div class="sos690-heading"><h3>Service Steps</h3><span class="sos690-job">{{ jobName }}</span></div>
    <span v-if="progress" class="sos690-current">{{ progress.status }}</span>
    <button type="button" class="sos690-outline" :disabled="loading||!!savingStep" @click="load" aria-label="Refresh repair status">Refresh</button>
  </header>
  <p v-if="error" role="alert" class="sos690-alert">{{ error }}</p>
  <p v-if="loading" role="status" class="sos690-help">Loading repair status…</p>
  <template v-else-if="progress">
    <ol class="sos690-rail" aria-label="Repair stages">
      <li v-for="stage in stages" :key="stage" :aria-current="progress.status === stage ? 'step' : undefined">
        <span class="sos690-dot" aria-hidden="true"></span>{{ stage }}
      </li>
    </ol>
    <div v-if="nextSteps.length || progress.status === 'Waiting for Parts'" class="sos690-action" aria-label="Available actions">
      <button v-for="(stage, index) in nextSteps" :key="stage" type="button"
        :class="index === 0 ? 'sos690-primary' : 'sos690-outline'" :disabled="!!savingStep" @click="advance(stage)">
        {{ savingStep === stage ? 'Saving…' : actionLabel(stage) }}
      </button>
      <button v-if="progress.status === 'Waiting for Parts'" type="button" class="sos690-outline" @click="goToParts">View spare parts</button>
    </div>
    <p v-else-if="progress.status === 'Ready to Deliver'" class="sos690-help">Use Deliver Device when the customer collects it.</p>
    <p v-else-if="!['Delivered', 'Cancelled'].includes(progress.status)" class="sos690-help">No next step available for your account.</p>
  </template>
  <p v-if="done" role="status" class="sos690-good">{{ done }}</p>
</section>
</template>
<style scoped>
.sos690-steps{border:1px solid #e1cfbf;background:#fffcf8;border-radius:12px;padding:11px 14px;color:#423024;font-size:13px;container-type:inline-size}
.sos690-header,.sos690-heading,.sos690-action{display:flex;align-items:center;gap:8px;min-width:0}
.sos690-header{flex-wrap:wrap}
.sos690-heading{margin-right:auto;flex-wrap:wrap}
.sos690-heading h3{font-size:15px;font-weight:750;line-height:1.3;margin:0}
.sos690-job{font-size:11px;color:#806650;overflow-wrap:anywhere}
.sos690-current{padding:4px 9px;border-radius:6px;background:#f3e7d8;color:#63432d;font-size:12px;font-weight:750}
.sos690-rail{display:flex;flex-wrap:wrap;gap:4px 9px;list-style:none;padding:8px 0;margin:5px 0 0;border-bottom:1px solid #ebddce}
.sos690-rail li{display:flex;align-items:center;gap:5px;border-radius:6px;padding:4px 6px;color:#715c49;font-size:11px}
.sos690-dot{width:7px;height:7px;border-radius:50%;border:1px solid #b7a08c;flex:none}
.sos690-rail [aria-current=step]{background:#efe0d0;color:#4e3422;font-weight:750}
.sos690-rail [aria-current=step] .sos690-dot{background:#84583b;border-color:#84583b}
.sos690-action{margin-top:9px;flex-wrap:wrap}
.sos690-outline,.sos690-primary{min-height:34px;padding:5px 10px;border:1px solid #d9c3af;border-radius:7px;background:#fffaf4;color:#63432d;font:inherit}
.sos690-outline,.sos690-primary{font-size:12px;font-weight:750;cursor:pointer}
.sos690-primary{background:#735038;color:white;border-color:#735038}
.sos690-primary:disabled,.sos690-outline:disabled{opacity:.55;cursor:not-allowed}
.sos690-help,.sos690-alert{margin:7px 0 0;font-size:12px}
.sos690-help{color:#806650}
.sos690-alert{padding:6px 8px;border:1px solid #e9c4b8;border-radius:7px;background:#fff2ec;color:#963b2d}
.sos690-good{font-size:12px;color:#376146;margin:6px 0 0}
</style>
