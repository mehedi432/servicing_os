<script setup>
// AMCL_PARTS_ISSUE_615F
import {ref,onMounted} from 'vue';
const loading=ref(false),saving=ref(''),error=ref(''),notice=ref('');
const requests=ref([]),warehouse=ref('Spare Parts - AMCL'),canCreate=ref(false);
function csrf(){return window.frappe?.csrf_token||window.csrf_token||decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'')}
async function call(method,data={},post=false){
 const url=new URL('/api/method/servicing_os.api.parts_issue.'+method,window.location.origin);
 const opts={method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}};
 if(post){opts.headers['Content-Type']='application/json';opts.headers['X-Frappe-CSRF-Token']=csrf();opts.body=JSON.stringify(data)}
 const response=await fetch(url,opts);let body;try{body=await response.json()}catch{throw Error('Server returned an invalid response')}
 if(!response.ok||body.exc||body.exc_type){let msg=body.exception||'Request failed';try{const a=JSON.parse(body._server_messages);msg=JSON.parse(a[a.length-1]).message.replace(/<[^>]+>/g,'')}catch{}throw Error(msg)}
 return body.message;
}
async function refresh(){loading.value=true;error.value='';try{const r=await call('get_issue_candidates');requests.value=r.requests||[];warehouse.value=r.warehouse;canCreate.value=!!r.can_create}catch(e){error.value=e.message}finally{loading.value=false}}
async function draft(r){error.value='';notice.value='';if(!window.confirm(`Create a DRAFT Material Issue for ${r.service_job}? Review it in ERPNext before submitting. No stock is deducted yet.`))return;
 saving.value=r.name;try{const result=await call('create_draft_issue',{material_request:r.name},true);notice.value=`Draft ${result.stock_entry} created for ${r.service_job}. Review in ERPNext; only Submit deducts stock.`;await refresh();window.open('/app/stock-entry/'+encodeURIComponent(result.stock_entry),'_blank','noopener')}catch(e){error.value=e.message}finally{saving.value=''}}
onMounted(refresh);
</script>
<template>
<section class="pi-root">
 <div class="pi-head"><div><h2>Issue Parts to Service Job</h2><p>Approved Material Requests · {{warehouse}} · ERPNext Material Issue</p></div><button class="pi-secondary" :disabled="loading" @click="refresh">{{loading?'Loading…':'↻ Refresh'}}</button></div>
 <div v-if="error" class="pi-alert pi-error" role="alert">{{error}}</div><div v-if="notice" class="pi-alert pi-success" role="status">{{notice}}</div>
 <div class="pi-note">Creating a draft does not deduct stock. An authorized user must review and submit it in ERPNext. This view issues all remaining request quantities together.</div>
 <div v-if="!requests.length&&!loading" class="pi-empty">No approved requests with outstanding quantities. Approve a Material Request first; receive stock before creating an issue.</div>
 <article v-for="req in requests" :key="req.name" class="pi-card">
  <div class="pi-head"><div><strong>{{req.service_job}}</strong><p>{{req.name}} · {{req.status}}</p></div><div class="pi-actions"><a :href="'/app/material-request/'+encodeURIComponent(req.name)" target="_blank" rel="noopener">View Request ↗</a><button :disabled="!canCreate||saving!==''||req.drafts.length>0" @click="draft(req)">{{saving===req.name?'Saving…':req.drafts.length?'Draft already exists':'Create Draft Issue'}}</button></div></div>
  <div class="pi-tablewrap"><table><thead><tr><th>Part</th><th>Requested</th><th>Already Issued</th><th>Remaining</th><th>In Stock</th></tr></thead><tbody><tr v-for="line in req.lines" :key="line.row_name"><td><strong>{{line.item_name}}</strong><small>{{line.item_code}}</small></td><td>{{line.requested_qty}}</td><td>{{line.already_issued_qty}}</td><td>{{line.remaining_qty}}</td><td :class="{'pi-low':line.actual_qty<line.remaining_qty}">{{line.actual_qty}}</td></tr></tbody></table></div>
  <div v-if="req.drafts.length" class="pi-draft">Existing draft: <a :href="'/app/stock-entry/'+encodeURIComponent(req.drafts[0])" target="_blank" rel="noopener">{{req.drafts[0]}} ↗</a></div>
 </article>
</section>
</template>
<style scoped>
.pi-root{color:#534633;font-size:13px}.pi-head,.pi-actions{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.pi-head{margin-bottom:14px}.pi-head h2{font-size:19px;font-weight:750}.pi-head p{color:#8b7d69;margin-top:4px}.pi-secondary,.pi-actions button{border:1px solid #dfd2be;padding:10px 12px;border-radius:9px;background:#fffdfa;font-weight:700}.pi-actions button{background:#80694b;color:white;border-color:#80694b}.pi-actions button:disabled{opacity:.5}.pi-actions a,.pi-draft a{color:#81603d;text-decoration:underline}.pi-note{background:#f4eee4;padding:13px;border-radius:10px;border:1px solid #e7dac6;margin-bottom:16px}.pi-empty{border:1px dashed #ddceba;border-radius:12px;padding:34px;text-align:center;color:#927f67}.pi-card{border:1px solid #e9dfd1;border-radius:14px;padding:16px;background:#fffefb;margin-bottom:14px}.pi-card strong{font-weight:750}.pi-tablewrap{overflow-x:auto}.pi-card table{width:100%;border-collapse:collapse;min-width:550px}.pi-card td,.pi-card th{text-align:left;border-bottom:1px solid #eee5d9;padding:10px}.pi-card th{color:#927f67;font-size:11px}.pi-card td small{display:block;color:#96856d;margin-top:3px}.pi-low{color:#aa4d37;font-weight:750}.pi-draft{margin-top:12px}.pi-alert{padding:12px;border-radius:10px;margin:10px 0}.pi-error{background:#fae8e5;color:#8a3026}.pi-success{background:#e7f4e9;color:#276e3a}
</style>
