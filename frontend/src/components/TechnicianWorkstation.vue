<script setup>
// SERVICING_PARTS_615C2
import ServicePartsRequests from "./ServicePartsRequests.vue";
import { ref, computed, onMounted } from 'vue';
const jobs = ref([]);
const technicians = ref([]);
const manager = ref(false);
const user = ref('');
const filterTechnician = ref('All');
const filterStatus = ref('All');
const search = ref('');
const selected = ref(null);
const logs = ref([]);
const stage = ref('Diagnosis');
const note = ref('');
const error = ref('');
const success = ref('');
const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
// AMCL_REPAIR_COMPLETED_616C: work activity and repair status are separate.
const progress = ref(null);
const progressStatus = ref('');
// AMCL_VISIBLE_WORKFLOW_616C2
const repairStages = ['Received', 'Diagnosing', 'Waiting for Parts', 'Repairing', 'Completed', 'Ready to Deliver', 'Delivered'];
const repairStatusOptions = [...repairStages, 'Cancelled'];
const nextActionLabel = (status) => ({
  'Diagnosing': 'Start Diagnosis',
  'Waiting for Parts': 'Wait for Parts',
  'Repairing': 'Resume / Start Repair',
  'Completed': 'Mark Completed',
  'Ready to Deliver': 'Mark Ready to Deliver',
  'Delivered': 'Mark Delivered',
  'Cancelled': 'Cancel Repair',
})[status] || 'Update Status';
const mayMoveTo = (status) => !!progress.value?.allowed_next_statuses?.includes(status);

const changingStatus = ref(false);
const progressError = ref('');

const statuses = ['All','Received','Diagnosing','Waiting for Parts','Repairing','Completed','Ready to Deliver','Delivered','Cancelled'];
const stages = ['Inspection','Diagnosis','Repair','Testing','Parts Required','Customer Update'];
const results = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return jobs.value;
  return jobs.value.filter(j => [j.name,j.customer_name,j.brand,j.device_model,j.technician,j.status]
    .some(x => String(x || '').toLowerCase().includes(q)));
});
function csrf() {
  return window.frappe?.csrf_token || window.csrf_token ||
    decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('csrf_token='))?.split('=').slice(1).join('=') || '');
}
async function api(method, data={}, post=false) {
  const url = new URL('/api/method/servicing_os.api.workstation.' + method, window.location.origin);
  const options = {method: post ? 'POST' : 'GET', credentials:'same-origin', headers:{'Accept':'application/json'}};
  if (post) {
    options.headers['Content-Type']='application/json';
    options.headers['X-Frappe-CSRF-Token']=csrf();
    options.body=JSON.stringify(data);
  } else Object.entries(data).forEach(([k,v]) => {if(v !== '' && v !== null)url.searchParams.set(k,v)});
  const res=await fetch(url,options);
  const payload=await res.json();
  if(!res.ok || payload.exc || payload.exc_type) {
    let message=payload.exception || 'Request failed';
    if(payload._server_messages) {
      try {const a=JSON.parse(payload._server_messages);const last=JSON.parse(a[a.length-1]);message=last.message||message;} catch(e){}
    }
    throw Error(message);
  }
  return payload.message;
}
async function refresh() {
  loading.value=true;error.value='';
  try {
    const data=await api('get_workstation',{technician:filterTechnician.value,status:filterStatus.value});
    jobs.value=data.jobs||[];technicians.value=data.technicians||[];
    manager.value=!!data.manager;user.value=data.current_user||'';
  } catch(e){error.value=e.message;}finally{loading.value=false;}
}
async function openJob(job) {
  error.value='';success.value='';
  try {const data=await api('get_job_worklog',{job_name:job.name});selected.value=data.job;logs.value=data.logs||[];visible.value=true;await loadProgress(job.name);}
  catch(e){error.value=e.message;}
}
async function saveNote() {
  if(!selected.value || saving.value)return;
  saving.value=true;error.value='';success.value='';
  try {const result=await api('add_work_note',{job_name:selected.value.name,stage:stage.value,note:note.value},true);
    logs.value=result.logs||[];note.value='';success.value='Work activity saved.';}
  catch(e){error.value=e.message;}finally{saving.value=false;}
}
async function progressCall(method, args={}, post=false) {
  const url = new URL('/api/method/servicing_os.api.repair_progress.'+method, window.location.origin);
  const opts={method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}};
  if(post){opts.headers['Content-Type']='application/json';opts.headers['X-Frappe-CSRF-Token']=csrf();opts.body=JSON.stringify(args);}
  else Object.entries(args).forEach(([key,val])=>{if(val!==null&&val!==undefined&&val!=='')url.searchParams.set(key,String(val))});
  const response=await fetch(url,opts);
  let body;
  try{body=await response.json()}catch{throw Error('Unexpected response from repair workflow API')}
  if(!response.ok||body.exc||body.exc_type){
    let message=body.exception||body.exc_type||'Could not update repair status';
    if(body._server_messages){try{const a=JSON.parse(body._server_messages);message=JSON.parse(a[a.length-1]).message||message}catch{}}
    throw Error(message);
  }
  return body.message;
}
async function loadProgress(name) {
  progress.value=null;progressStatus.value='';progressError.value='';
  try {progress.value=await progressCall('get_progress',{job_name:name});}
  catch(e){progressError.value=e.message;}
}
async function changeRepairStatus() {
  if(!selected.value||!progressStatus.value||changingStatus.value)return;
  changingStatus.value=true;progressError.value='';success.value='';
  try {
    const result=await progressCall('advance_repair',{
      job_name:selected.value.name,next_status:progressStatus.value,
      expected_modified:progress.value?.modified
    },true);
    const name=selected.value.name;
    await refresh();
    await openJob({name});
    success.value='Repair moved to '+result.status+'.';
  }catch(e){progressError.value=e.message;}
  finally{changingStatus.value=false;}
}
onMounted(refresh);
</script>
<template>
  <section class="tw-root">
    <ServicePartsRequests />
    <div class="tw-heading">
      <div><p class="tw-eyebrow">OPERATIONS / TECHNICIANS</p><h2>Technician Workstation</h2>
        <p>Assigned repairs and time-stamped repair activity. No financial posting.</p></div>
      <button type="button" class="tw-secondary" :disabled="loading" @click="refresh">{{loading?'Loading...':'Refresh'}}</button>
    </div>
    <p v-if="error" class="tw-error" role="alert">{{error}}</p>
    <p v-if="success" class="tw-success" role="status">{{success}}</p>
    <div class="tw-filters">
      <input v-model="search" aria-label="Search technician jobs" placeholder="Search job, customer or device" />
      <select v-if="manager" v-model="filterTechnician" @change="refresh" aria-label="Technician filter">
        <option value="All">All technicians</option><option v-for="t in technicians" :key="t.name" :value="t.name">{{t.full_name || t.name}}</option>
      </select>
      <select v-model="filterStatus" @change="refresh" aria-label="Job status filter"><option v-for="s in statuses" :key="s">{{s}}</option></select>
    </div>
    <div class="tw-body">
      <div class="tw-jobs">
        <div class="tw-subheading">{{manager?'Repair queue':'My assigned jobs'}} <span>{{results.length}}</span></div>
        <button v-for="j in results" :key="j.name" type="button" class="tw-job" :class="{'tw-selected':selected?.name===j.name}" @click="openJob(j)">
          <span class="tw-job-line"><strong>{{j.name}}</strong><small>{{j.status}}</small></span>
          <span class="tw-muted">{{j.customer_name || 'Customer'}} · {{[j.brand,j.device_model].filter(Boolean).join(' ')}}</span>
          <span class="tw-muted">{{j.technician || 'Unassigned'}}</span>
        </button>
        <p v-if="!results.length" class="tw-empty">No matching jobs.</p>
      </div>
      <div class="tw-detail">
        <div v-if="selected && visible">
          <div class="tw-subheading">{{selected.name}} <span>{{selected.status}}</span></div>
          <p class="tw-muted tw-problem">{{selected.reported_problem || 'No reported problem provided.'}}</p>
          <div class="amcl-flow-card">
            <div class="amcl-flow-header">
              <div>
                <div class="amcl-flow-eyebrow">REPAIR WORKFLOW</div>
                <h3>Repair progress</h3>
                <p>All stages are shown. Only valid next steps can be selected.</p>
              </div>
              <strong class="amcl-flow-current">{{ progress?.status || selected.status }}</strong>
            </div>

            <div class="amcl-flow-steps" aria-label="All repair stages">
              <button
                v-for="s in repairStages" :key="s" type="button"
                class="amcl-flow-stage"
                :class="{
                  'amcl-flow-active': (progress?.status || selected.status) === s,
                  'amcl-flow-allowed': mayMoveTo(s),
                  'amcl-flow-picked': progressStatus === s,
                  'amcl-flow-locked': !mayMoveTo(s) && (progress?.status || selected.status) !== s
                }"
                :disabled="!mayMoveTo(s) || changingStatus"
                :aria-pressed="progressStatus === s"
                :title="mayMoveTo(s) ? 'Choose ' + s : ((progress?.status || selected.status) === s ? 'Current status' : 'Not available yet')"
                @click="progressStatus=s"
              >
                <span class="amcl-flow-stage-name">{{ s }}</span>
                <span class="amcl-flow-stage-note">
                  {{ (progress?.status || selected.status) === s ? 'Current' : (mayMoveTo(s) ? 'Select' : 'Later') }}
                </span>
              </button>
            </div>

            <p v-if="(progress?.status || selected.status) === 'Waiting for Parts'" class="amcl-flow-help">
              Parts pending. Select <b>Repairing</b> when work resumes; after saving, you can select <b>Completed</b>.
            </p>
            <p v-else-if="(progress?.status || selected.status) === 'Repairing'" class="amcl-flow-help">
              Repair work finished? Choose <b>Completed</b>, then save. This unlocks Draft Invoice preparation.
            </p>
            <p v-else-if="(progress?.status || selected.status) === 'Completed'" class="amcl-flow-help">
              Repair completed. Draft invoice preparation is available. A manager can mark it Ready to Deliver.
            </p>
            <p v-else-if="(progress?.status || selected.status) === 'Ready to Deliver'" class="amcl-flow-help">
              Ready for collection. A manager can mark the repair Delivered after physical handover.
            </p>
            <p v-else class="amcl-flow-help">
              Activity notes do not change the repair status. Choose an available next step below.
            </p>

            <div v-if="progress" class="amcl-flow-action">
              <label class="amcl-flow-select-label">
                <span>Change repair status</span>
                <select v-model="progressStatus" :disabled="changingStatus" aria-label="Change repair status">
                  <option value="">Choose next stage...</option>
                  <option v-for="s in repairStatusOptions" :key="s" :value="s" :disabled="!mayMoveTo(s)">
                    {{ s }}{{ mayMoveTo(s) ? ' — available' : (s === progress.status ? ' — current' : ' — not yet available') }}
                  </option>
                </select>
              </label>
              <button
                type="button" class="amcl-flow-save"
                :disabled="changingStatus || !progressStatus || !mayMoveTo(progressStatus)"
                @click="changeRepairStatus"
              >
                {{ changingStatus ? 'Saving...' : nextActionLabel(progressStatus || '') }}
              </button>
            </div>
            <p v-else class="amcl-flow-help">Loading permitted transitions...</p>
            <p v-if="progressError" class="tw-error" role="alert">{{progressError}}</p>
            <p class="amcl-flow-footnote">Cancellation is available only when permitted. Ready to Deliver and Delivered are manager-controlled.</p>
          </div>
          <form v-if="!['Delivered','Cancelled'].includes(selected.status)" class="tw-note" @submit.prevent="saveNote">
            <div class="tw-activity-type">
              <div class="tw-status-head"><span>ACTIVITY TYPE</span><strong>{{stage}}</strong></div>
              <p>Choose the kind of work note. This does not change the repair status.</p>
              <div class="tw-activity-chips" role="group" aria-label="Activity type">
                <button v-for="s in stages" :key="s" type="button"
                  :aria-pressed="stage===s" :class="{'tw-stage-active':stage===s}"
                  @click="stage=s">{{s}}</button>
              </div>
            </div>
            <label>Repair work performed<textarea v-model="note" rows="3" maxlength="3000" minlength="3" required placeholder="Record findings, repairs, tests or parts needed..."></textarea></label>
            <button :disabled="saving || note.trim().length<3" type="submit">{{saving?'Saving...':'Add Work Note'}}</button>
          </form>
          <div class="tw-subheading">Activity timeline <span>{{logs.length}}</span></div>
          <div v-for="entry in logs" :key="entry.name" class="tw-entry"><strong>{{entry.stage}}</strong><p>{{entry.note}}</p><small>{{entry.by}} · {{entry.at}}</small></div>
          <p v-if="!logs.length" class="tw-empty">No recorded work activity yet.</p>
        </div>
        <p v-else class="tw-empty">Select a job to inspect its repair activity.</p>
      </div>
    </div>
  </section>
</template>
<style scoped>
.tw-root{margin:0 0 22px;padding:20px;border:1px solid #e8ddce;border-radius:18px;background:#fffdf9;color:#493e30;box-shadow:0 5px 22px #59452709}
.tw-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.tw-heading h2{font-size:20px;font-weight:750}.tw-heading p{font-size:12px;color:#87775f}.tw-eyebrow{letter-spacing:.12em;font-weight:700;margin-bottom:3px}
.tw-secondary,.tw-note button{border:1px solid #bfa887;background:#746148;color:white;border-radius:11px;padding:10px 15px;font-size:13px;font-weight:650}.tw-secondary{background:#f5eee3;color:#5f4f3a;border-color:#e1d3be}
.tw-filters{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:16px}.tw-filters input{flex:1 1 240px}.tw-filters select{flex:1 1 130px}
.tw-filters input,.tw-filters select,.tw-note input,.tw-note select,.tw-note textarea{padding:10px 12px;border:1px solid #e0d4c2;border-radius:10px;background:#fff;color:#443c30;min-width:0;font-size:13px}
.tw-body{display:grid;grid-template-columns:minmax(220px,1fr) minmax(260px,1.25fr);gap:12px}.tw-jobs,.tw-detail{padding:14px;border:1px solid #ece3d7;border-radius:12px;min-width:0}
.tw-subheading{display:flex;justify-content:space-between;align-items:center;gap:10px;font-weight:700;font-size:14px;margin-bottom:12px}.tw-subheading span{font-size:11px;color:#82715b}
.tw-job{width:100%;display:flex;flex-direction:column;text-align:left;gap:6px;background:#fff;border:1px solid #e9dfd0;border-radius:10px;padding:11px;margin-bottom:8px}.tw-job:hover,.tw-selected{border-color:#bda47d;background:#faf4e8}
.tw-job-line{display:flex;justify-content:space-between;gap:8px;font-size:12px}.tw-job-line small{font-size:11px;color:#967246}.tw-muted{font-size:12px;color:#8b7b67}.tw-problem{margin-bottom:15px}
.tw-note{display:grid;gap:11px;margin-bottom:24px}.tw-note label{font-size:12px;font-weight:650;display:grid;gap:5px}.tw-note textarea{resize:vertical}.tw-note button{justify-self:start}.tw-note button:disabled{opacity:.5}
.tw-entry{padding:11px 0;border-top:1px solid #eee5d8}.tw-entry strong{font-size:12px;color:#8e6d43}.tw-entry p{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere;margin:5px 0}.tw-entry small{font-size:11px;color:#958570}
.tw-empty{font-size:13px;text-align:center;color:#9b8b76;padding:30px 10px}.tw-error,.tw-success{padding:10px 12px;border-radius:9px;margin-bottom:11px;font-size:13px}.tw-error{background:#feeae6;color:#913c2c}.tw-success{background:#e8f5e9;color:#376743}
@media(max-width:850px){.tw-body{grid-template-columns:1fr}.tw-root{padding:13px}}
</style>

<style scoped>
/* AMCL_REPAIR_COMPLETED_616C: reliable activity selection and status UI */
.tw-status-panel,.tw-activity-type{background:#f8f4ec;border:1px solid #e9ddcb;border-radius:13px;padding:14px;margin:12px 0 18px}
.tw-status-head{display:flex;align-items:center;justify-content:space-between;gap:12px;color:#75664f;font-size:10px;letter-spacing:.07em;font-weight:800}
.tw-status-head strong{font-size:13px;color:#58452c;letter-spacing:0}
.tw-status-panel p,.tw-activity-type p{font-size:12px;color:#87735b;margin:8px 0}
.tw-status-controls{display:flex;flex-wrap:wrap;gap:9px;margin-top:13px}
.tw-status-controls select{flex:1 1 200px;background:white;border:1px solid #d9cbb5;border-radius:10px;padding:11px;min-width:0;font-size:13px}
.tw-status-controls button{min-height:42px;border:0;border-radius:10px;background:#766148;color:white;padding:10px 16px;font-size:12px;font-weight:750}
.tw-status-controls button:disabled{opacity:.45;cursor:not-allowed}
.tw-status-controls .tw-mark-complete{background:#456e55;color:white}
.tw-status-hint{font-size:11px!important;line-height:1.5}
.tw-activity-chips{display:flex;gap:7px;flex-wrap:wrap;margin:11px 0 2px}
.tw-activity-chips button{display:inline-flex;align-items:center;min-height:36px;padding:8px 11px;border:1px solid #ddcfba;border-radius:11px;background:#fffdf8;color:#725a3f;font-size:12px;font-weight:650;cursor:pointer;transition:background .16s,border-color .16s}
.tw-activity-chips button:hover{background:#f1e5d3}
.tw-activity-chips button.tw-stage-active{background:#745d42;border-color:#745d42;color:white;box-shadow:0 3px 9px #59412422}
@media(max-width:580px){.tw-status-controls{flex-direction:column}.tw-status-controls select,.tw-status-controls button{width:100%}}
</style>

<style scoped>
/* AMCL_VISIBLE_WORKFLOW_616C2 — visually clear and safe, frontend only */
.amcl-flow-card{background:#fffdf9;border:1px solid #e0d2bf;border-radius:16px;padding:18px;margin:14px 0 22px;box-shadow:0 5px 18px rgba(79,60,38,.055)}
.amcl-flow-header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-bottom:14px;border-bottom:1px solid #ece3d7}
.amcl-flow-eyebrow{font-size:10px;font-weight:800;letter-spacing:.13em;color:#a08560}
.amcl-flow-header h3{font-weight:800;font-size:17px;line-height:1.35;color:#43382a;margin:4px 0}
.amcl-flow-header p{font-size:12px;line-height:1.5;color:#857561}
.amcl-flow-current{background:#f1e7d8;color:#634b30;font-size:12px;padding:8px 12px;border-radius:999px;white-space:nowrap}
.amcl-flow-steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:8px;padding:16px 0}
.amcl-flow-stage{display:flex;flex-direction:column;justify-content:center;gap:5px;text-align:left;padding:10px;border:1px solid #e1d7c9;background:#fffdfa;color:#5f513f;border-radius:11px;min-height:66px;font-size:12px}
.amcl-flow-stage-name{font-weight:750;line-height:1.25;overflow-wrap:anywhere}
.amcl-flow-stage-note{font-size:10px;color:#9d8a72}
.amcl-flow-stage.amcl-flow-locked{opacity:.64;cursor:not-allowed}
.amcl-flow-stage.amcl-flow-active{background:#ede0ce;border-color:#cbb08b;opacity:1}
.amcl-flow-stage.amcl-flow-allowed{background:#f0f7f0;border-color:#b6ceb7;cursor:pointer;opacity:1}
.amcl-flow-stage.amcl-flow-picked{outline:2px solid #6a886c;outline-offset:1px}
.amcl-flow-help{font-size:12px;line-height:1.65;background:#f9f4ea;border:1px solid #eee2cc;border-radius:10px;color:#726049;padding:12px;margin:4px 0 13px}
.amcl-flow-action{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap}
.amcl-flow-select-label{flex:1 1 200px;min-width:0;display:grid;gap:7px;font-size:12px;font-weight:700;color:#5c4a36}
.amcl-flow-select-label select{width:100%;background:#fff;border:1px solid #d8c9b4;border-radius:11px;padding:11px 12px;color:#43392c;font-size:13px;min-height:45px}
.amcl-flow-save{flex:0 1 auto;min-height:45px;background:#6d5840;color:white;border:1px solid #6d5840;border-radius:11px;padding:11px 18px;font-size:13px;font-weight:750;cursor:pointer}
.amcl-flow-save:disabled{opacity:.48;cursor:not-allowed}
.amcl-flow-footnote{font-size:11px;color:#9a896f;margin-top:11px;line-height:1.45}
@media(max-width:600px){.amcl-flow-card{padding:12px}.amcl-flow-steps{grid-template-columns:repeat(2,minmax(0,1fr))}.amcl-flow-save{width:100%}}
</style>
