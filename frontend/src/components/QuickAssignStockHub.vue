<script setup>
// AMCL_QUICK_ASSIGN_615E1
import { ref, onMounted } from 'vue';
const ready = ref(false);
const jobs = ref([]);
const techs = ref([]);
const loading = ref(false);
const busy = ref('');
const notice = ref('');
const error = ref('');

function csrf() {
  return window.frappe?.csrf_token || window.csrf_token ||
    decodeURIComponent(document.cookie.split('; ').find(s => s.startsWith('csrf_token='))?.split('=').slice(1).join('=') || '');
}
async function invoke(method, data={}, post=false) {
  const url = new URL('/api/method/servicing_os.api.quick_assign.'+method, window.location.origin);
  const opt = {method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}};
  if(post){opt.headers['Content-Type']='application/json';opt.headers['X-Frappe-CSRF-Token']=csrf();opt.body=JSON.stringify(data);}
  const response = await fetch(url,opt);
  let body;
  try{body=await response.json();}catch{throw Error('Server returned an unexpected response.');}
  if(!response.ok || body.exc || body.exc_type){
    let msg = body.exception || 'Could not complete request';
    if(body._server_messages){try{const list=JSON.parse(body._server_messages);msg=JSON.parse(list[list.length-1]).message||msg;}catch{}}
    const err = Error(msg); err.status=response.status; throw err;
  }
  return body.message;
}
async function reload() {
  loading.value=true;error.value='';
  try {const x=await invoke('get_quick_assign_queue');jobs.value=x.jobs||[];techs.value=x.technicians||[];ready.value=true;}
  catch(e){if(e.status===403 || /permission|only a service manager|not permitted/i.test(e.message)){ready.value=false;}else{error.value=e.message;ready.value=true;}}
  finally{loading.value=false;}
}
async function assign(job, technician) {
  if(busy.value || job.technician===technician)return;
  busy.value=job.name;error.value='';notice.value='';
  try{
    const result=await invoke('assign_technician',{job_name:job.name,technician,expected_modified:job.modified},true);
    notice.value=result.changed ? `${job.name} assigned successfully.` : 'Already assigned.';
    await reload();
  }catch(e){error.value=e.message;}finally{busy.value='';}
}
function label(user){const t=techs.value.find(x=>x.name===user);return t?.full_name||user||'Unassigned';}
onMounted(reload);
</script>
<template>
  <section v-if="ready" class="qa-root">
    <div class="qa-top">
      <div>
        <p class="qa-kicker">FAST COUNTER OPERATIONS</p>
        <h2>Quick Technician Assignment</h2>
        <p>One click assigns a job. No need to open the complete repair form.</p>
      </div>
      <button type="button" class="qa-refresh" :disabled="loading" @click="reload">{{ loading?'Refreshing…':'Refresh jobs' }}</button>
    </div>
    <p v-if="notice" class="qa-ok" role="status">{{ notice }}</p>
    <p v-if="error" class="qa-error" role="alert">{{ error }}</p>
    <div class="qa-list">
      <article v-for="job in jobs" :key="job.name" class="qa-job">
        <div class="qa-description">
          <strong>{{ job.name }}</strong>
          <span>{{ [job.brand,job.device_model].filter(Boolean).join(' ') }} · {{ job.customer_name || 'Customer' }}</span>
          <small>{{ job.status }} · Assigned: {{label(job.technician)}}</small>
        </div>
        <div class="qa-actions">
          <button v-for="tech in techs" :key="tech.name" type="button"
            :disabled="!!busy || job.technician===tech.name"
            :class="['qa-choice',{'qa-current':job.technician===tech.name}]"
            :title="job.technician===tech.name?'Already assigned to '+tech.full_name:'Assign '+job.name+' to '+tech.full_name"
            @click="assign(job,tech.name)">
            <span v-if="job.technician===tech.name" aria-hidden="true">✓</span>
            {{tech.full_name || tech.name}}
          </button>
        </div>
      </article>
      <p v-if="!jobs.length && !loading" class="qa-empty">No open repair jobs found.</p>
      <p v-if="!techs.length" class="qa-empty">No enabled Service Technician users found.</p>
    </div>
    <div class="qa-stock">
      <div>
        <h3>Receive Spare Parts in ERPNext</h3>
        <p>Use Purchase Receipt for purchases from suppliers. For existing opening stock, use Stock Reconciliation with correct valuation. These links do not post stock themselves.</p>
      </div>
      <div class="qa-stock-links">
        <a href="/app/purchase-receipt" target="_blank" rel="noopener noreferrer">Purchase Receipts ↗</a>
        <a href="/app/stock-reconciliation" target="_blank" rel="noopener noreferrer">Opening Stock ↗</a>
        <a href="/app/stock-balance" target="_blank" rel="noopener noreferrer">Stock Balance ↗</a>
      </div>
    </div>
  </section>
</template>
<style scoped>
.qa-root{background:#fffdf9;border:1px solid #e7ded0;border-radius:17px;padding:20px;color:#453a2a;margin:0 0 20px;box-shadow:0 5px 18px #6a543309}
.qa-top{display:flex;gap:16px;align-items:center;justify-content:space-between;margin-bottom:15px;flex-wrap:wrap}
.qa-kicker{font-size:10px;font-weight:800;letter-spacing:.14em;color:#a1835c}.qa-top h2{font-size:19px;font-weight:750;margin:2px 0 4px}.qa-top p:not(.qa-kicker){font-size:12px;color:#917e64}
.qa-refresh,.qa-choice,.qa-stock-links a{border:1px solid #d9ccb9;border-radius:10px;padding:10px 13px;background:#faf5ec;color:#685235;font-size:12px;font-weight:700;cursor:pointer}
.qa-refresh:hover,.qa-choice:hover:not(:disabled){background:#ecdec8}.qa-refresh:disabled,.qa-choice:disabled{cursor:default;opacity:.66}
.qa-list{display:grid;gap:9px}.qa-job{display:flex;justify-content:space-between;align-items:center;gap:15px;background:#fff;border:1px solid #eee4d7;border-radius:12px;padding:12px}
.qa-description{display:flex;flex-direction:column;gap:3px;min-width:0}.qa-description strong{font-size:13px}.qa-description span{font-size:12px;color:#72634f;overflow-wrap:anywhere}.qa-description small{font-size:11px;color:#977f5e}
.qa-actions{display:flex;flex-wrap:wrap;align-items:center;gap:7px}.qa-choice{white-space:nowrap}.qa-current{background:#e4f3e6!important;color:#336541!important;border-color:#b6d6bd!important}
.qa-empty{text-align:center;padding:15px;color:#988773;font-size:12px}.qa-ok,.qa-error{font-size:12px;padding:10px 12px;border-radius:9px;margin-bottom:10px}.qa-ok{background:#e8f4e8;color:#38643d}.qa-error{background:#fbe9e4;color:#923e30}
.qa-stock{margin-top:19px;padding:15px;border-radius:12px;background:#f8f1e5;border:1px solid #e9dbc7;display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}
.qa-stock h3{font-size:14px;font-weight:750}.qa-stock p{max-width:620px;font-size:12px;color:#837158;margin-top:3px}.qa-stock-links{display:flex;flex-wrap:wrap;gap:8px}.qa-stock-links a{text-decoration:none}
@media(max-width:800px){.qa-root{padding:12px}.qa-job{flex-direction:column;align-items:stretch}.qa-actions{justify-content:flex-start}.qa-stock{align-items:stretch}}
</style>
