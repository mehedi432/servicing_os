<script setup>
// S44_SERVICE_JOBS_INVOICE: only wire existing actions; no sidebar or layout replacement.
import { ref as s44Ref, computed as s44Computed } from 'vue';
import ServiceJobQuickInvoice644 from './ServiceJobQuickInvoice644.vue';
import StockReceipt712 from './StockReceipt712.vue';
const s44InvoiceOpen = s44Ref(false);
const s44InitialJob = s44Computed(() => selected.value?.name || '');
const s44ReceiptJob = s44Ref('');
function s44OpenCounterReceive() {
  window.dispatchEvent(new CustomEvent('servicing-os:open-counter-service-receive'));
}
function s44InvoiceCreated(invoice) {
  window.dispatchEvent(new CustomEvent('servicing-os:service-invoice-created', { detail: invoice }));
}

// SERVICING_SERVICE_JOBS_624B
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import ServiceJobSticker629 from './ServiceJobSticker629.vue'
import ServiceJobRecordActions699 from './ServiceJobRecordActions699.vue'; // SOS_REPAIR_RECORD_ACTIONS_699
const sos629StickerJob = ref(''); // SOS_QR_STICKER_UI_629
const emit = defineEmits(['receive', 'manage', 'handover']);
const jobsView=ref('list'); // SOS_JOBS_GRID_625A
const jobs=ref([]), filter=ref('All'), term=ref(''), options=ref(['All']);
const loading=ref(false), detailLoading=ref(false), saving=ref(false);
const error=ref(''), actionError=ref(''), notice=ref('');
const selected=ref(null), detail=ref(null), progress=ref(null);
const nextStatus=ref(''), stage=ref('Inspection'), note=ref(''), worklog=ref([]);
const techs=ref([]), tech=ref('');

// SOS_COUNTER_REPAIR_TABS_698: optional Counter-only scope. Standalone jobs stay unchanged.
const props = defineProps({
  counterScope: { type: String, default: 'all' },
  refreshToken: { type: Number, default: 0 },
  guidedHandover: Boolean
});
const visibleJobs = computed(() => {
  const scope = props.counterScope;
  const rows = jobs.value;
  if (scope === 'active') return rows.filter(j => !['Completed', 'Ready to Deliver', 'Delivered', 'Cancelled'].includes(j.status));
  if (scope === 'unassigned') return rows.filter(j => !j.technician);
  if (scope === 'waiting') return rows.filter(j => j.status === 'Waiting for Parts');
  if (scope === 'ready') return rows.filter(j => ['Completed', 'Ready to Deliver'].includes(j.status));
  if (scope === 'delivered') return rows.filter(j => j.status === 'Delivered');
  return rows;
});

const stats=computed(()=>({total:jobs.value.length, active:jobs.value.filter(j=>!['Delivered','Cancelled'].includes(j.status)).length, completed:jobs.value.filter(j=>['Completed','Ready to Deliver'].includes(j.status)).length, unassigned:jobs.value.filter(j=>!j.technician).length}));
let searchDelay=null, requestVersion=0;
function token(){return window.frappe?.csrf_token||window.csrf_token||decodeURIComponent(document.cookie.split('; ').find(s=>s.startsWith('csrf_token='))?.split('=')?.slice(1).join('=')||'');}
async function api(path,params={},post=false){
  const url=new URL('/api/method/'+path,window.location.origin);
  if(!post)Object.entries(params).forEach(([k,v])=>{if(v!==undefined && v!==null)url.searchParams.set(k,String(v));});
  const opts={method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}};
  if(post){opts.headers['Content-Type']='application/json';opts.headers['X-Frappe-CSRF-Token']=token();opts.body=JSON.stringify(params);}
  const res=await fetch(url,opts);let data={};try{data=await res.json();}catch{throw Error('Server did not return a valid response.');}
  if(!res.ok||data.exc||data.exc_type){let message=data.exception||data.message||`Request failed (${res.status})`;if(data._server_messages){try{const arr=JSON.parse(data._server_messages);message=JSON.parse(arr[arr.length-1]).message||message;}catch{}}throw Error(typeof message==='string'?message:'Request failed.');}
  return data.message||{};
}
const hub='servicing_os.api.service_jobs_hub.';
async function load(){const version=++requestVersion;loading.value=true;error.value='';try{const data=await api(hub+'get_service_jobs',{search:term.value,status:filter.value});if(version!==requestVersion)return;jobs.value=data.jobs||[];options.value=data.status_options||['All'];if(selected.value){const updated=jobs.value.find(x=>x.name===selected.value.name);if(updated)selected.value=updated;}}
catch(e){if(version===requestVersion)error.value=e.message;}finally{if(version===requestVersion)loading.value=false;}}
watch(term,()=>{clearTimeout(searchDelay);searchDelay=setTimeout(load,250);});
watch(filter,()=>{clearTimeout(searchDelay);load();});
onBeforeUnmount(()=>{requestVersion++;clearTimeout(searchDelay);});

// SOS_COUNTER_REPAIR_TABS_698: reuse the existing authorised search / job actions.
// Exact statuses are queried server-side when configured; composite groups are
// filtered inside the latest 200 accessible jobs returned by the existing API.
watch(() => props.counterScope, scope => {
  const exact = scope === 'waiting' ? 'Waiting for Parts' : scope === 'delivered' ? 'Delivered' : 'All';
  const wanted = options.value.includes(exact) ? exact : 'All';
  if (filter.value !== wanted) filter.value = wanted;
  else load();
});
watch(() => props.refreshToken, () => load());

function fmt(v){return v?String(v).slice(0,16).replace('T',' '):'—';}
async function choose(job){selected.value=job;detail.value=null;progress.value=null;worklog.value=[];nextStatus.value='';actionError.value='';notice.value='';detailLoading.value=true;
  try{
    const out=await api(hub+'get_service_job_detail',{job_name:job.name});
    if(selected.value?.name!==job.name)return;
    detail.value=out.job;
    try{const p=await api('servicing_os.api.repair_progress.get_progress',{job_name:job.name});if(selected.value?.name===job.name){progress.value=p;nextStatus.value=(p.allowed_next_statuses||[])[0]||'';}}catch{/* Status controls are optional for read-only users. */}
    try{const w=await api('servicing_os.api.workstation.get_job_worklog',{job_name:job.name});if(selected.value?.name===job.name)worklog.value=w.logs||[];}catch{/* Work-log permission can be narrower than job read permission. */}
    try{const q=await api('servicing_os.api.quick_assign.get_quick_assign_queue');techs.value=q.technicians||[];tech.value=job.technician||'';}catch{techs.value=[];}
  }catch(e){actionError.value=e.message;}finally{detailLoading.value=false;}
}
async function advance(){if(!selected.value||!nextStatus.value||saving.value)return;
 if(!window.confirm(`Move ${selected.value.name} to ${nextStatus.value}?`))return;
 saving.value=true;actionError.value='';notice.value='';try{await api('servicing_os.api.repair_progress.advance_repair',{job_name:selected.value.name,next_status:nextStatus.value,expected_modified:progress.value?.modified||null},true);notice.value='Job status updated.';await load();await choose(selected.value);}catch(e){actionError.value=e.message;}finally{saving.value=false;}}
async function log(){if(!selected.value||note.value.trim().length<3||saving.value)return;saving.value=true;actionError.value='';notice.value='';try{await api('servicing_os.api.workstation.add_work_note',{job_name:selected.value.name,stage:stage.value,note:note.value.trim()},true);note.value='';notice.value='Repair note saved.';await choose(selected.value);}catch(e){actionError.value=e.message;}finally{saving.value=false;}}
async function assign(){if(!selected.value||!tech.value||saving.value)return;saving.value=true;actionError.value='';notice.value='';try{await api('servicing_os.api.quick_assign.assign_technician',{job_name:selected.value.name,technician:tech.value,expected_modified:selected.value.modified},true);notice.value='Technician assigned.';await load();await choose(selected.value);}catch(e){actionError.value=e.message;}finally{saving.value=false;}}
// Mobile sticker links open exactly this job. Permission checks happen server-side.
async function sos629Start(){
  const id = new URLSearchParams(window.location.search).get('service_job');
  if (!id) { await load(); return; }
  if (id.length > 140 || !/^[A-Za-z0-9._-]+$/.test(id)) {
    error.value = 'The scanned Service Job number is invalid.'; await load(); return;
  }
  term.value = id;
  await load();
  await choose(jobs.value.find(j => j.name === id) || {name:id});
}
onMounted(sos629Start);
function onHandover(event) {
  if (event.detail?.service_job === selected.value?.name) {
    selected.value = null;
    detail.value = null;
  }
  load();
}
onMounted(() => {
  if (props.guidedHandover) window.addEventListener('servicing-os-job-delivered', onHandover);
});
onBeforeUnmount(() => window.removeEventListener('servicing-os-job-delivered', onHandover));
// SOS_REPAIR_RECORD_ACTIONS_699 — keep native job register and invoice workflows.
async function sos699Saved() {
  await load();
  const latest = jobs.value.find(j => j.name === selected.value?.name);
  if (latest) await choose(latest);
  window.dispatchEvent(new CustomEvent('servicing-os:service-job-updated'));
}
async function sos699Deleted() {
  selected.value = null;
  detail.value = null;
  progress.value = null;
  worklog.value = [];
  actionError.value = '';
  notice.value = 'Service Job permanently deleted.';
  await load();
  window.dispatchEvent(new CustomEvent('servicing-os:service-job-updated'));
}
</script>
<template>
<!-- S44_SERVICE_JOBS_INVOICE: same Service Jobs screen, one invoice dialog -->
<ServiceJobQuickInvoice644 :open="s44InvoiceOpen" :initial-job="s44InitialJob" @close="s44InvoiceOpen = false" @created="s44InvoiceCreated" />

  <div class="sj-app sos629-jobs">
    <header class="sj-header">
      <div><small>SERVICING OS / DAILY OPERATIONS</small><h1>Service Jobs</h1><p>Search, inspect, assign and advance real repair jobs. No other screen required for everyday work.</p></div>
      <div class="sj-actions"><button type="button" class="sj-outline" @click="emit('manage')">Repair Management</button><button type="button" class="sj-primary" @click.stop="s44OpenCounterReceive">＋ Receive Computer</button><button type="button" class="sj-outline" @click.stop="s44InvoiceOpen = true">Create Invoice</button></div>
    </header>
    <div class="sj-kpis">
      <div><span>Showing</span><strong>{{stats.total}}</strong><small>Recent or filtered jobs</small></div>
      <div><span>Undelivered</span><strong>{{stats.active}}</strong><small>Not delivered / cancelled</small></div>
      <div><span>Ready / Completed</span><strong>{{stats.completed}}</strong><small>Awaiting delivery process</small></div>
      <div><span>Unassigned</span><strong>{{stats.unassigned}}</strong><small>Needs technician</small></div>
    </div>
    <div class="sj-main" :class="{'sj-grid-mode':jobsView==='grid'}">
      <section class="sj-list">
        <div class="sj-list-top"><strong>Job Register</strong><div class="sj-view-switch" role="group" aria-label="Job display view">
            <button type="button" title="List view" aria-label="List view" :aria-pressed="jobsView==='list'" :class="{active:jobsView==='list'}" @click="jobsView='list'">List</button>
            <button type="button" title="Grid view" aria-label="Grid view" :aria-pressed="jobsView==='grid'" :class="{active:jobsView==='grid'}" @click="jobsView='grid'">Grid</button>
          </div></div>
        <div class="sj-filter"><label>Find a job, customer or device<input v-model="term" placeholder="Type name, job ID, model or serial…" autocomplete="off" /></label>
        <label v-if="props.counterScope === 'all'">Status<select v-model="filter"><option v-for="s in options" :key="s">{{s}}</option></select></label></div>
        <div v-if="error" class="sj-error">{{error}}</div>
        <div v-if="loading" class="sj-muted">Loading Service Jobs…</div>
        <div v-else-if="!visibleJobs.length" class="sj-empty"><strong>No matching Service Jobs</strong><span>Try another search or receive a new device using the button above.</span></div>
        <div class="sj-items" :class="{'sj-grid-items':jobsView==='grid'}">
          <button v-for="job in visibleJobs" :key="job.name" type="button" class="sj-item" :class="{chosen:selected?.name===job.name}" @click="choose(job)">
            <div class="sj-item-top"><strong>{{job.name}}</strong><span class="sj-status">{{job.status||'Unknown'}}</span></div>
            <b>{{job.customer_name||job.customer||'Customer'}}</b>
            <span>{{[job.brand,job.device_model].filter(Boolean).join(' · ')||job.device_type||'Device'}} · {{job.technician||'Unassigned'}}</span>
            <small>{{fmt(job.received_date||job.modified)}}</small>
          </button>
        </div>
        <p class="sj-foot">Showing up to 200 accessible jobs. Results update automatically while typing.</p>
      </section>
      <section class="sj-detail">
        <div v-if="!selected || (props.counterScope !== 'all' && !visibleJobs.some(j => j.name === selected.name))" class="sj-empty sj-big"><strong>Select a Service Job</strong><span>Click any job on the left to see its details and available actions.</span></div>
        <template v-else>
          <div class="sj-detail-head"><div><small>JOB DETAILS</small><h2>{{selected.name}}</h2><span class="sj-status">{{detail?.status||selected.status}}</span></div><button type="button" class="sj-outline" @click="choose(selected)">Refresh</button></div>
          <div v-if="detailLoading" class="sj-muted">Loading job details…</div>
          <div v-if="actionError" class="sj-error" role="alert">{{actionError}}</div>
          <div v-if="notice" class="sj-success" role="status">{{notice}}</div>
          <template v-if="detail">
            <button v-if="guidedHandover && ['Ready to Deliver', 'Delivered'].includes(detail.status)" type="button" class="sj-primary sj-handover" @click="emit('handover', selected.name)">
              {{ detail.status === 'Delivered' ? 'Open delivery documents' : 'Open Delivery Desk' }}
            </button>
            <div class="sj-row">
              <button type="button" class="sj-outline" @click="s44InvoiceOpen = true">Review or create invoice</button>
              <button v-if="!['Delivered','Cancelled','Canceled'].includes(detail.status)" type="button"
                class="sj-outline" @click="s44ReceiptJob = selected.name">Receive Spare Part</button>
            </div>
            <ServiceJobRecordActions699 :job-name="selected.name" @saved="sos699Saved" @deleted="sos699Deleted" />
            <div class="sj-print-sticker"><button type="button" @click="sos629StickerJob = selected.name">Print QR Device Sticker</button></div>
            <div class="sj-info">
              <div><small>Customer</small><strong>{{detail.customer_name||detail.customer||'—'}}</strong></div>
              <div><small>Device</small><strong>{{[detail.brand,detail.device_model].filter(Boolean).join(' ')||detail.device_type||'—'}}</strong></div>
              <div><small>Serial No.</small><strong>{{detail.serial_number||'—'}}</strong></div>
              <div><small>Technician</small><strong>{{detail.technician||'Not assigned'}}</strong></div>
              <div class="sj-wide"><small>Customer's Problem</small><p>{{detail.reported_problem||'Not recorded'}}</p></div>
            </div>
            <div v-if="techs.length && !['Delivered','Cancelled'].includes(detail.status)" class="sj-panel"><strong>Assign Technician</strong><div class="sj-row"><select v-model="tech"><option value="">Select technician</option><option v-for="t in techs" :key="t.name" :value="t.name">{{t.full_name||t.name}}</option></select><button type="button" :disabled="saving||!tech||tech===detail.technician" @click="assign">Save Assignment</button></div></div>
            <div v-if="progress?.allowed_next_statuses?.length" class="sj-panel"><strong>Update Repair Status</strong><p>Only permitted next steps are listed.</p><div class="sj-row"><select v-model="nextStatus"><option v-for="s in progress.allowed_next_statuses" :key="s">{{s}}</option></select><button type="button" :disabled="saving||!nextStatus" @click="advance">Move Status</button></div></div>
            <div v-if="progress || worklog.length" class="sj-panel"><strong>Technician Work Notes</strong><div class="sj-row"><select v-model="stage"><option v-for="s in ['Inspection','Diagnosis','Repair','Testing','Parts Required','Customer Update']" :key="s">{{s}}</option></select></div><textarea v-model="note" placeholder="What was checked, repaired, or tested?" rows="3"></textarea><button type="button" :disabled="saving||note.trim().length<3" @click="log">Save Work Note</button><div v-for="w in worklog.slice(0,10)" :key="w.name" class="sj-log"><b>{{w.stage||'Work'}}</b><span>{{w.note}}</span><small>{{fmt(w.at)}}</small></div></div>
          </template>
        </template>
      </section>
    </div>
  </div>
  <StockReceipt712 v-if="s44ReceiptJob" :job-name="s44ReceiptJob" @close="s44ReceiptJob = ''" />
  <ServiceJobSticker629 v-if="sos629StickerJob" :job-name="sos629StickerJob" @close="sos629StickerJob = ''" />
</template>
<style scoped>
.sj-handover{margin-bottom:12px}
.sj-list-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 12px;font-size:14px;color:#634e35}
.sj-view-switch{display:flex;gap:3px;padding:3px;border:1px solid #e7daca;border-radius:10px;background:#f7f0e7}
.sj-view-switch button{border:0;border-radius:7px;background:transparent;color:#715a40;font-size:17px;font-weight:800;cursor:pointer;width:35px;height:33px}
.sj-view-switch button.active{background:white;box-shadow:0 2px 8px #66524020}
.sj-main.sj-grid-mode{grid-template-columns:1fr}.sj-grid-items{grid-template-columns:repeat(auto-fill,minmax(255px,1fr));max-height:none;overflow:visible}
.sj-grid-items .sj-item{min-height:140px;align-content:start}
.sj-app{background:#f9f7f3;color:#3c3328;font-family:inherit;min-height:100vh;padding:25px 26px 45px;width:100%;box-sizing:border-box}.sj-app *{box-sizing:border-box}.sj-header{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap}.sj-header small,.sj-detail-head small{font-size:10px;letter-spacing:.13em;color:#a28b6f;font-weight:900}.sj-header h1{font-size:29px;margin:6px 0 4px;font-weight:850;line-height:1.2}.sj-header p{margin:0;color:#8a7a66;font-size:12px}.sj-actions{display:flex;gap:9px;flex-wrap:wrap}.sj-primary,.sj-outline{border-radius:12px;padding:13px 17px;border:1px solid #d8c8b5;font-size:12px;font-weight:800;cursor:pointer}.sj-primary{background:#76583a;border-color:#76583a;color:white}.sj-outline{background:white;color:#6f543b}.sj-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:22px 0}.sj-kpis>div{background:white;border:1px solid #e7dccf;border-radius:15px;padding:15px;display:grid;gap:5px}.sj-kpis span{font-size:12px;color:#9a856d}.sj-kpis strong{font-size:25px}.sj-kpis small{font-size:10px;color:#a59480}.sj-main{display:grid;grid-template-columns:minmax(275px,.95fr) minmax(330px,1.25fr);gap:16px;align-items:start}.sj-list,.sj-detail{min-width:0;background:#fff;border:1px solid #e6dccc;border-radius:17px;padding:16px;min-height:390px}.sj-filter{display:grid;grid-template-columns:1fr minmax(120px,.5fr);gap:9px;margin-bottom:14px}.sj-filter label{font-size:11px;font-weight:800;color:#85725a;display:grid;gap:7px}.sj-filter input,.sj-filter select,.sj-panel select,.sj-panel textarea{width:100%;padding:12px;border:1px solid #e1d5c5;border-radius:10px;background:#fff;color:#453726;font:inherit;font-size:12px;outline:0}.sj-filter input:focus,.sj-panel textarea:focus{border-color:#96785a}.sj-items{display:grid;gap:8px;max-height:68vh;overflow:auto}.sj-item{display:grid;gap:5px;text-align:left;border:1px solid #ebe2d5;border-radius:12px;background:#fffdf9;padding:14px;cursor:pointer;min-width:0;color:#42362a}.sj-item:hover,.sj-item.chosen{border-color:#a98a65;background:#fbf5ec}.sj-item-top{display:flex;gap:10px;justify-content:space-between;align-items:center;min-width:0}.sj-item-top strong{font-size:12px;overflow-wrap:anywhere}.sj-item b{font-size:13px}.sj-item span,.sj-item small{font-size:11px;color:#937d64}.sj-status{padding:5px 8px;background:#f0e6d8;border-radius:999px;white-space:nowrap;font-size:10px!important;font-weight:800;color:#765537!important}.sj-detail-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;margin-bottom:18px}.sj-detail-head h2{font-size:20px;margin:4px 0 8px;overflow-wrap:anywhere}.sj-info{display:grid;grid-template-columns:1fr 1fr;gap:10px}.sj-info>div{background:#faf7f2;border-radius:11px;padding:12px}.sj-info small{font-size:10px;font-weight:800;color:#99826a;display:block;margin-bottom:6px}.sj-info strong{font-size:13px}.sj-info .sj-wide{grid-column:1 / -1}.sj-info p{font-size:12px;margin:0;white-space:pre-wrap}.sj-panel{padding:15px;border:1px solid #e9dfd3;border-radius:13px;margin-top:14px;display:grid;gap:9px}.sj-panel>strong{font-size:13px}.sj-panel>p{margin:0;color:#94826e;font-size:11px}.sj-row{display:flex;gap:9px}.sj-row select{flex:1}.sj-row button,.sj-panel>button{border:0;background:#745538;color:white;border-radius:9px;padding:12px 15px;cursor:pointer;font-size:12px;font-weight:800}.sj-row button:disabled,.sj-panel>button:disabled{opacity:.45;cursor:not-allowed}.sj-panel textarea{resize:vertical}.sj-log{background:#f7f3ed;padding:10px;border-radius:9px;display:grid;gap:5px}.sj-log b{font-size:11px}.sj-log span,.sj-log small{font-size:11px;color:#796b5a}.sj-error{background:#fff0e9;color:#a23e25;padding:12px;border-radius:9px;font-size:12px;margin:9px 0}.sj-success{background:#edf6eb;color:#336b45;padding:12px;border-radius:9px;font-size:12px;margin:9px 0}.sj-muted,.sj-empty{font-size:12px;color:#94806b;padding:30px 12px;text-align:center}.sj-empty{display:grid;gap:9px}.sj-empty strong{font-size:14px;color:#67513b}.sj-big{padding:75px 12px}.sj-foot{font-size:10px;color:#a18c72;margin:12px 0 0}@media(max-width:1050px){.sj-main{grid-template-columns:1fr}.sj-items{max-height:340px}}@media(max-width:780px){.sj-app{padding:15px}.sj-kpis{grid-template-columns:repeat(2,1fr)}.sj-filter{grid-template-columns:1fr}.sj-actions{width:100%}.sj-actions button{flex:1}}
</style>

<style>
/* SOS_JOBS_PREMIUM_629 — polish existing list/grid without rewriting job actions. */
.sj-app.sos629-jobs{background:#f6f8f7;color:#253740;padding:25px 28px 45px}
.sos629-jobs .sj-header{background:#fff;border:1px solid #e1e7e5;border-radius:19px;padding:22px 25px;box-shadow:0 7px 25px #24434b08}
.sos629-jobs .sj-header h1{color:#243840;letter-spacing:-.045em;font-size:32px}
.sos629-jobs .sj-header p{color:#667980;font-size:13px;line-height:1.5}
.sos629-jobs .sj-header small,.sos629-jobs .sj-detail-head small{color:#9d7e57;font-size:10px;letter-spacing:.13em}
.sos629-jobs .sj-primary{background:#203944;color:#fff;border-color:#203944;border-radius:11px;min-height:43px}
.sos629-jobs .sj-outline{background:#fff;color:#324c57;border-color:#cedbd9;border-radius:11px;min-height:43px}
.sos629-jobs .sj-primary:hover,.sos629-jobs .sj-row button:hover,.sos629-jobs .sj-panel>button:hover{background:#315462}
.sos629-jobs .sj-outline:hover{background:#f2f7f6}
.sos629-jobs button:focus-visible,.sos629-jobs input:focus-visible,.sos629-jobs select:focus-visible{outline:3px solid #d0aa77;outline-offset:2px}
.sos629-jobs .sj-kpis{gap:13px;margin:15px 0 17px}
.sos629-jobs .sj-kpis>div{background:linear-gradient(150deg,#fff,#fbfcfb);border-color:#dfe7e3;border-radius:15px;padding:17px 18px;box-shadow:0 5px 18px #2c454906}
.sos629-jobs .sj-kpis span{font-size:12px;color:#63777f;font-weight:700}
.sos629-jobs .sj-kpis strong{font-size:29px;color:#253b45;letter-spacing:-.045em}
.sos629-jobs .sj-kpis small{color:#899ba0;font-size:11px}
.sos629-jobs .sj-main{gap:17px;grid-template-columns:minmax(330px,1.03fr) minmax(370px,1.22fr)}
.sos629-jobs .sj-list,.sos629-jobs .sj-detail{border:1px solid #dfe7e4;border-radius:17px;padding:18px;background:#fff;box-shadow:0 9px 28px #263e4407}
.sos629-jobs .sj-list-top{margin-bottom:14px;display:flex;justify-content:space-between;align-items:center}
.sos629-jobs .sj-list-top strong{font-size:16px;color:#223740;letter-spacing:-.02em}
.sos629-jobs .sj-view-switch{background:#edf3f1;border-color:#dce5e2}
.sos629-jobs .sj-view-switch button{min-width:52px;width:auto;font-size:11px;font-weight:800;color:#546970;padding:5px 9px}
.sos629-jobs .sj-view-switch button.active{background:#213b47;color:#fff}
.sos629-jobs .sj-filter{gap:12px}
.sos629-jobs .sj-filter label{color:#6a7d83;font-size:11px}
.sos629-jobs .sj-filter input,.sos629-jobs .sj-filter select{padding:13px 12px;border-color:#d9e2df;color:#273c46;font-size:13px;min-height:46px}
.sos629-jobs .sj-items{gap:8px;max-height:70vh;scrollbar-width:thin}
.sos629-jobs .sj-item{background:#fff;border:1px solid #e1e8e4;border-radius:12px;border-left:4px solid #b9a07d;padding:13px 15px;gap:8px;box-shadow:0 3px 10px #193e4305;transition:border-color .14s,transform .14s,background .14s}
.sos629-jobs .sj-item:hover{background:#f8faf9;border-color:#b0bfb9;transform:translateY(-1px)}
.sos629-jobs .sj-item.chosen{border-color:#315965;border-left-color:#315965;background:#f1f7f6;box-shadow:inset 0 0 0 1px #c1d8d1}
.sos629-jobs .sj-item-top strong{color:#213947;font-size:13px;letter-spacing:-.02em}
.sos629-jobs .sj-item>b{font-size:14px;color:#2b3e44;font-weight:760}
.sos629-jobs .sj-item>span,.sos629-jobs .sj-item>small{color:#70858c;font-size:11px;line-height:1.45}
.sos629-jobs .sj-item .sj-status,.sos629-jobs .sj-detail-head .sj-status{background:#eff3f1;border:1px solid #d7e3de;color:#33605d!important;font-size:10px!important;padding:6px 9px;font-weight:850}
.sos629-jobs .sj-item-top{gap:6px}
.sos629-jobs .sj-grid-items{grid-template-columns:repeat(auto-fill,minmax(225px,1fr));max-height:none;overflow:visible}
.sos629-jobs .sj-grid-items .sj-item{min-height:158px;padding:17px;align-content:start}
.sos629-jobs .sj-detail-head h2{color:#263c45;letter-spacing:-.03em}
.sos629-jobs .sj-info>div{background:#f5f8f7;border:1px solid #e6edeb;border-radius:12px}
.sos629-jobs .sj-info small{color:#768a90}
.sos629-jobs .sj-panel{border-color:#e2eae7;border-radius:13px}
.sos629-jobs .sj-panel>strong{font-size:14px;color:#263c45}
.sos629-jobs .sj-row button,.sos629-jobs .sj-panel>button{background:#284653;border-radius:9px;min-height:43px}
.sos629-jobs .sj-print-sticker{margin:0 0 16px;display:flex;justify-content:flex-start}
.sos629-jobs .sj-print-sticker button{border:1px solid #b9cfc9;background:#ebf5f2;color:#234e52;cursor:pointer;border-radius:10px;padding:11px 16px;font-size:12px;font-weight:850;min-height:43px}
.sos629-jobs .sj-print-sticker button:hover{background:#dcece7}
.sos629-jobs .sj-empty{background:#f8faf9;border-radius:13px;margin:7px 0}
@media(max-width:1100px){.sos629-jobs .sj-main{grid-template-columns:1fr}.sos629-jobs .sj-items{max-height:360px}}
@media(max-width:780px){.sj-app.sos629-jobs{padding:12px}.sos629-jobs .sj-header{padding:17px}.sos629-jobs .sj-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.sos629-jobs .sj-list,.sos629-jobs .sj-detail{padding:13px}.sos629-jobs .sj-header h1{font-size:26px}}
</style>


<style>
/* SOS_SJ_SINGLE_PALETTE_631 — final unified theme, scoped to Service Jobs only.
   Intentionally appended last to override the original ivory and 6.29 teal mix.
   No receiving form, sidebar, Counter, or document styles are touched. */
.sj-app.sos629-jobs {
  --sj631-ink:#20343b;
  --sj631-muted:#627780;
  --sj631-brand:#294852;
  --sj631-brand-hover:#365e69;
  --sj631-border:#dfe7e5;
  --sj631-cream:#f7f8f6;
  --sj631-paper:#ffffff;
  background:var(--sj631-cream);
  color:var(--sj631-ink);
  font-family:inherit;
  padding:22px;
  min-width:0;
}
.sj-app.sos629-jobs .sj-header,
.sj-app.sos629-jobs .sj-kpis > div,
.sj-app.sos629-jobs .sj-list,
.sj-app.sos629-jobs .sj-detail {
  background:var(--sj631-paper);
  border:1px solid var(--sj631-border);
  border-radius:16px;
  box-shadow:0 5px 20px rgba(25,51,56,.045);
}
.sj-app.sos629-jobs .sj-header { padding:20px 22px; align-items:center; }
.sj-app.sos629-jobs .sj-header h1,
.sj-app.sos629-jobs .sj-detail-head h2 { color:var(--sj631-ink); letter-spacing:-.035em; }
.sj-app.sos629-jobs .sj-header p,
.sj-app.sos629-jobs .sj-foot,
.sj-app.sos629-jobs .sj-item > small,
.sj-app.sos629-jobs .sj-item > span,
.sj-app.sos629-jobs .sj-filter label,
.sj-app.sos629-jobs .sj-panel > p,
.sj-app.sos629-jobs .sj-info small { color:var(--sj631-muted); }
.sj-app.sos629-jobs .sj-actions { display:flex;align-items:center;gap:10px;flex-wrap:wrap; }
/* One geometry and brand colour for ALL real actions, including QR printing. */
.sj-app.sos629-jobs .sj-primary,
.sj-app.sos629-jobs .sj-row button,
.sj-app.sos629-jobs .sj-panel > button,
.sj-app.sos629-jobs .sj-print-sticker button {
  min-height:44px;
  padding:10px 16px;
  font:inherit;
  font-size:12px;
  font-weight:750;
  line-height:1.25;
  border:1px solid var(--sj631-brand);
  border-radius:10px;
  color:#fff;
  background:var(--sj631-brand);
  box-shadow:none;
  cursor:pointer;
  transition:background .16s ease,border-color .16s ease,transform .16s ease;
}
.sj-app.sos629-jobs .sj-primary:not(:disabled):hover,
.sj-app.sos629-jobs .sj-row button:not(:disabled):hover,
.sj-app.sos629-jobs .sj-panel > button:not(:disabled):hover,
.sj-app.sos629-jobs .sj-print-sticker button:not(:disabled):hover {
  background:var(--sj631-brand-hover); border-color:var(--sj631-brand-hover);
}
.sj-app.sos629-jobs .sj-outline {
  min-height:44px; padding:10px 16px; font:inherit; font-size:12px;
  font-weight:750; line-height:1.25; border-radius:10px;
  background:#fff; color:var(--sj631-brand); border:1px solid #cad9d7;
  box-shadow:none; cursor:pointer;
}
.sj-app.sos629-jobs .sj-outline:not(:disabled):hover {background:#edf4f2;color:var(--sj631-brand);border-color:#a6c1ba;}
.sj-app.sos629-jobs button:disabled {opacity:.48;cursor:not-allowed;transform:none;}
.sj-app.sos629-jobs button:focus-visible,
.sj-app.sos629-jobs input:focus-visible,
.sj-app.sos629-jobs select:focus-visible,
.sj-app.sos629-jobs textarea:focus-visible {outline:3px solid #b2c9c0;outline-offset:2px;}
.sj-app.sos629-jobs .sj-kpis {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:16px 0 18px;}
.sj-app.sos629-jobs .sj-kpis > div {padding:17px;min-width:0;min-height:102px;}
.sj-app.sos629-jobs .sj-kpis strong {color:var(--sj631-ink);font-size:28px;}
.sj-app.sos629-jobs .sj-main {display:grid;grid-template-columns:minmax(315px,1fr) minmax(390px,1.18fr);gap:16px;align-items:start;}
.sj-app.sos629-jobs .sj-list,
.sj-app.sos629-jobs .sj-detail {padding:18px;min-width:0;}
.sj-app.sos629-jobs .sj-items {gap:9px;}
.sj-app.sos629-jobs .sj-item {border:1px solid var(--sj631-border);border-left:3px solid #a9c2b9;border-radius:12px;background:#fff;color:var(--sj631-ink);padding:13px;box-shadow:none;}
.sj-app.sos629-jobs .sj-item:hover {background:#f5faf8;border-color:#b5cac4;transform:none;}
.sj-app.sos629-jobs .sj-item.chosen {background:#f0f7f4;border-color:#6f9c90;border-left-color:var(--sj631-brand);box-shadow:inset 0 0 0 1px #dce9e4;}
.sj-app.sos629-jobs .sj-status {background:#edf4f1!important;border:1px solid #cde0d7!important;color:#365e59!important;border-radius:8px;}
.sj-app.sos629-jobs .sj-info > div {background:#f6f9f7;border:1px solid #e1eae6;border-radius:11px;}
.sj-app.sos629-jobs .sj-panel {border:1px solid var(--sj631-border);background:#fff;border-radius:12px;}
.sj-app.sos629-jobs .sj-panel textarea,
.sj-app.sos629-jobs .sj-panel select,
.sj-app.sos629-jobs .sj-filter input,
.sj-app.sos629-jobs .sj-filter select {
  color:var(--sj631-ink);background:#fff;border:1px solid #d3e0dc;border-radius:10px;
  min-height:43px;font:inherit;font-size:12px;
}
.sj-app.sos629-jobs .sj-view-switch {display:inline-flex;align-items:center;padding:4px;border:1px solid var(--sj631-border);border-radius:10px;background:#f2f6f4;}
.sj-app.sos629-jobs .sj-view-switch button {min-height:33px;min-width:48px;padding:6px 10px;background:transparent;border:0;border-radius:7px;color:#526971;font-size:12px;font-weight:750;cursor:pointer;}
.sj-app.sos629-jobs .sj-view-switch button.active,
.sj-app.sos629-jobs .sj-view-switch button[aria-pressed="true"] {background:var(--sj631-brand);color:#fff;}
@media(max-width:1150px){.sj-app.sos629-jobs .sj-main{grid-template-columns:1fr;}.sj-app.sos629-jobs .sj-items{max-height:400px;}}
@media(max-width:730px){.sj-app.sos629-jobs{padding:12px;}.sj-app.sos629-jobs .sj-header{padding:16px;}.sj-app.sos629-jobs .sj-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}.sj-app.sos629-jobs .sj-list,.sj-app.sos629-jobs .sj-detail{padding:13px;}.sj-app.sos629-jobs .sj-actions button{flex:1;}}
</style>

<style>
/* SOS_IVORY_STOCK_633 — unified ivory/coffee Service Jobs theme. */
.sj-app.sos629-jobs {
  --sos633-bg:#F8F5EE; --sos633-paper:#FFFCF7;
  --sos633-ink:#35291F; --sos633-muted:#796A59;
  --sos633-border:#E5D9C8; --sos633-accent:#755536;
  background:var(--sos633-bg)!important;
  color:var(--sos633-ink)!important;
  padding:23px!important;
}
.sj-app.sos629-jobs .sj-header,
.sj-app.sos629-jobs .sj-list,
.sj-app.sos629-jobs .sj-detail,
.sj-app.sos629-jobs .sj-kpis > div {
  background:var(--sos633-paper)!important;
  border:1px solid var(--sos633-border)!important;
  box-shadow:0 6px 24px rgba(89,64,38,.045)!important;
  border-radius:16px!important;
}
.sj-app.sos629-jobs .sj-header{padding:20px 23px!important;}
.sj-app.sos629-jobs .sj-list,
.sj-app.sos629-jobs .sj-detail{padding:21px!important;}
.sj-app.sos629-jobs .sj-header h1,
.sj-app.sos629-jobs .sj-detail-head h2,
.sj-app.sos629-jobs .sj-list-top strong,
.sj-app.sos629-jobs .sj-kpis strong,
.sj-app.sos629-jobs .sj-panel > strong,
.sj-app.sos629-jobs .sj-item-top strong,
.sj-app.sos629-jobs .sj-item > b {color:var(--sos633-ink)!important;}
.sj-app.sos629-jobs .sj-header p,
.sj-app.sos629-jobs .sj-kpis span,
.sj-app.sos629-jobs .sj-kpis small,
.sj-app.sos629-jobs .sj-item > span,
.sj-app.sos629-jobs .sj-item > small,
.sj-app.sos629-jobs .sj-info small,
.sj-app.sos629-jobs .sj-filter label,
.sj-app.sos629-jobs .sj-panel > p {color:var(--sos633-muted)!important;}
.sj-app.sos629-jobs .sj-item {
  background:#FFFDFA!important;color:var(--sos633-ink)!important;
  border:1px solid #E9DCCB!important;border-left:3px solid #C7A984!important;
  border-radius:12px!important;padding:14px 15px!important;box-shadow:none!important;
}
.sj-app.sos629-jobs .sj-item:hover{background:#F9F0E4!important;border-color:#C9AC89!important;transform:none!important;}
.sj-app.sos629-jobs .sj-item.chosen{
  background:#F2E5D2!important;border-color:#B8966F!important;
  border-left-color:var(--sos633-accent)!important;box-shadow:inset 0 0 0 1px #DCC8AA!important;
}
.sj-app.sos629-jobs .sj-status{
  color:#78522D!important;background:#F1E5D4!important;
  border:1px solid #E1CDB1!important;border-radius:8px!important;
}
.sj-app.sos629-jobs .sj-info > div,
.sj-app.sos629-jobs .sj-panel,
.sj-app.sos629-jobs .sj-log,
.sj-app.sos629-jobs .sj-empty {
  color:var(--sos633-ink)!important;background:#FAF4EA!important;
  border:1px solid #EDE1D0!important;border-radius:11px!important;
}
.sj-app.sos629-jobs .sj-panel {padding:17px!important;}
.sj-app.sos629-jobs .sj-primary,
.sj-app.sos629-jobs .sj-row button,
.sj-app.sos629-jobs .sj-panel > button,
.sj-app.sos629-jobs .sj-print-sticker button {
  color:#FFF!important;background:var(--sos633-accent)!important;
  border:1px solid var(--sos633-accent)!important;border-radius:10px!important;
  min-height:44px!important;box-shadow:none!important;
}
.sj-app.sos629-jobs .sj-outline{
  color:var(--sos633-accent)!important;background:#FFFCF7!important;
  border:1px solid #D8C4AA!important;border-radius:10px!important;min-height:44px!important;
}
.sj-app.sos629-jobs .sj-primary:not(:disabled):hover,
.sj-app.sos629-jobs .sj-row button:not(:disabled):hover,
.sj-app.sos629-jobs .sj-panel > button:not(:disabled):hover,
.sj-app.sos629-jobs .sj-print-sticker button:not(:disabled):hover{background:#5E4128!important;border-color:#5E4128!important;}
.sj-app.sos629-jobs .sj-outline:not(:disabled):hover{background:#F5EADA!important;}
.sj-app.sos629-jobs .sj-view-switch{background:#F1E9DE!important;border-color:#DED0BC!important;}
.sj-app.sos629-jobs .sj-view-switch button{background:transparent!important;color:#725D45!important;}
.sj-app.sos629-jobs .sj-view-switch button.active,
.sj-app.sos629-jobs .sj-view-switch button[aria-pressed="true"]{background:var(--sos633-accent)!important;color:#FFF!important;}
.sj-app.sos629-jobs .sj-filter input,
.sj-app.sos629-jobs .sj-filter select,
.sj-app.sos629-jobs .sj-panel select,
.sj-app.sos629-jobs .sj-panel textarea{background:#FFFEFC!important;color:var(--sos633-ink)!important;border:1px solid #DACBB8!important;}
.sj-app.sos629-jobs button:focus-visible,
.sj-app.sos629-jobs input:focus-visible,
.sj-app.sos629-jobs select:focus-visible{outline:3px solid #C7A77F!important;outline-offset:2px;}
@media(max-width:780px){.sj-app.sos629-jobs{padding:12px!important}.sj-app.sos629-jobs .sj-list,.sj-app.sos629-jobs .sj-detail{padding:15px!important}.sj-app.sos629-jobs .sj-header{padding:17px!important}}
</style>
