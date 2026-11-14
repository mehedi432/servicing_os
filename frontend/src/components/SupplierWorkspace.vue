<script setup>
import { computed, onMounted, ref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
const bn = computed(() => currentLanguage.value === 'bn')
const tr = (en, bengali) => bn.value ? bengali : en
const rows = ref([])
const groups = ref([])
const query = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const editing = ref(false)
const formOpen = ref(false)
const form = ref(blank())
function blank() { return {name:'',supplier_name:'',supplier_group:'',supplier_type:'Company',mobile_no:'',email_id:''} }
function errorText(data, fallback) {
  if (data?._server_messages) {
    try { const x=JSON.parse(data._server_messages); if(x.length) return JSON.parse(x[0]).message || fallback } catch {}
  }
  return data?.message || data?.exception || fallback
}
async function request(path, options={}) {
  const headers = {'Accept':'application/json', ...(options.body ? {'Content-Type':'application/json'} : {})}
  // Frappe session cookies provide authentication; the existing CSRF token is used for writes.
  if (options.method && options.method !== 'GET') {
    const csrf = window.csrf_token || window.frappe?.csrf_token
    if (csrf) headers['X-Frappe-CSRF-Token'] = csrf
  }
  const response=await fetch(path,{credentials:'same-origin',...options,headers:{...headers,...(options.headers||{})}})
  const data=await response.json().catch(()=>({}))
  if(!response.ok || data.exc || data.exception) throw new Error(errorText(data,`${response.status}: Request failed`))
  return data.data ?? data.message ?? data
}
async function load() {
  loading.value=true; error.value=''
  try {
    const p = new URLSearchParams({fields:JSON.stringify(['name','supplier_name','supplier_group','supplier_type','mobile_no','email_id']),limit_page_length:'200',order_by:'modified desc'})
    rows.value=await request('/api/resource/Supplier?'+p)
  } catch(e) { error.value=e.message }
  finally {loading.value=false}
}
async function loadGroups() {
  try {
    const p=new URLSearchParams({fields:JSON.stringify(['name','is_group']),limit_page_length:'200',order_by:'name asc'})
    const all=await request('/api/resource/Supplier Group?'+p)
    groups.value=all.filter(g=>!Number(g.is_group)).map(g=>g.name)
  } catch(e) { error.value=e.message }
}
function add() {form.value=blank(); editing.value=false; formOpen.value=true; error.value=''; notice.value=''}
function edit(r) {form.value={...blank(),...r}; editing.value=true; formOpen.value=true; error.value='';notice.value=''}
const filtered = computed(()=>rows.value.filter(r=>[r.name,r.supplier_name,r.supplier_group,r.mobile_no,r.email_id].some(v=>String(v||'').toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase()))))
async function save() {
  error.value='';notice.value=''
  if(!form.value.supplier_name.trim() || !form.value.supplier_group) {error.value=tr('Supplier name and group are required','সরবরাহকারীর নাম ও গ্রুপ আবশ্যক');return}
  saving.value=true
  try {
    const payload={supplier_name:form.value.supplier_name.trim(),supplier_group:form.value.supplier_group,supplier_type:form.value.supplier_type,mobile_no:form.value.mobile_no,email_id:form.value.email_id}
    if(editing.value) await request('/api/resource/Supplier/'+encodeURIComponent(form.value.name),{method:'PUT',body:JSON.stringify(payload)})
    else await request('/api/resource/Supplier',{method:'POST',body:JSON.stringify(payload)})
    formOpen.value=false
    notice.value=tr('Supplier saved successfully','সরবরাহকারী সংরক্ষিত হয়েছে')
    await load()
  } catch(e) {error.value=e.message}
  finally {saving.value=false}
}
onMounted(async()=>{await Promise.all([load(),loadGroups()])})
</script>
<template>
  <section class="sos647-root" aria-label="Suppliers">
    <header class="sos647-top">
      <div><div class="sos647-eyebrow">SERVICING OS / {{ tr('PARTNERS','অংশীদার') }}</div><h1>{{tr('Suppliers','সরবরাহকারী')}}</h1><p>{{tr('Manage purchasing partners and contact information','ক্রয় সংক্রান্ত সরবরাহকারী ও যোগাযোগের তথ্য পরিচালনা করুন')}}</p></div>
      <button class="sos647-primary" @click="add">＋ {{tr('New Supplier','নতুন সরবরাহকারী')}}</button>
    </header>
    <div class="sos647-stats"><div><small>{{tr('Total suppliers','মোট সরবরাহকারী')}}</small><strong>{{rows.length}}</strong></div><div><small>{{tr('Matching results','মিলেছে')}}</small><strong>{{filtered.length}}</strong></div><div><small>{{tr('Supplier groups','সরবরাহকারী গ্রুপ')}}</small><strong>{{groups.length}}</strong></div></div>
    <main class="sos647-panel">
      <div class="sos647-toolbar"><div><h2>{{tr('Supplier Directory','সরবরাহকারী তালিকা')}}</h2><p>{{tr('Stored directly in ERPNext Supplier records','ERPNext Supplier রেকর্ডে সরাসরি সংরক্ষিত')}}</p></div><div class="sos647-actions"><input v-model="query" type="search" :placeholder="tr('Search suppliers...','সরবরাহকারী খুঁজুন...')" :aria-label="tr('Search suppliers','সরবরাহকারী খুঁজুন')"><button @click="load">↻ {{tr('Refresh','রিফ্রেশ')}}</button></div></div>
      <div v-if="error" class="sos647-error" role="alert">{{error}}</div>
      <div v-if="notice" class="sos647-ok" role="status">{{notice}}</div>
      <div class="sos647-tablewrap"><table><thead><tr><th>{{tr('Supplier','সরবরাহকারী')}}</th><th>{{tr('Group','গ্রুপ')}}</th><th>{{tr('Type','ধরন')}}</th><th>{{tr('Mobile','মোবাইল')}}</th><th>{{tr('Email','ইমেইল')}}</th><th>{{tr('Action','অ্যাকশন')}}</th></tr></thead><tbody><tr v-for="r in filtered" :key="r.name"><td><b>{{r.supplier_name}}</b><small>{{r.name}}</small></td><td>{{r.supplier_group||'—'}}</td><td>{{r.supplier_type||'—'}}</td><td>{{r.mobile_no||'—'}}</td><td>{{r.email_id||'—'}}</td><td><button class="sos647-edit" @click="edit(r)">{{tr('View / Edit','দেখুন / পরিবর্তন')}}</button></td></tr><tr v-if="!loading && !filtered.length"><td colspan="6" class="sos647-empty">{{tr('No suppliers found','কোনো সরবরাহকারী পাওয়া যায়নি')}}</td></tr></tbody></table></div><p v-if="loading" class="sos647-loading">{{tr('Loading suppliers...','সরবরাহকারী লোড হচ্ছে...')}}</p>
    </main>
    <div v-if="formOpen" class="sos647-backdrop" @click.self="formOpen=false"><form class="sos647-dialog" @submit.prevent="save"><div class="sos647-dialoghead"><div><small>SUPPLIER MASTER</small><h2>{{editing?tr('Edit Supplier','সরবরাহকারী পরিবর্তন'):tr('New Supplier','নতুন সরবরাহকারী')}}</h2></div><button type="button" @click="formOpen=false" aria-label="Close">✕</button></div><div class="sos647-fields"><label>{{tr('Supplier Name','সরবরাহকারীর নাম')}} *<input v-model="form.supplier_name" required maxlength="140" /></label><label>{{tr('Supplier Group','সরবরাহকারী গ্রুপ')}} *<select v-model="form.supplier_group" required><option value="">{{tr('Select group','গ্রুপ নির্বাচন করুন')}}</option><option v-for="g in groups" :key="g" :value="g">{{g}}</option></select></label><label>{{tr('Supplier Type','সরবরাহকারীর ধরন')}}<select v-model="form.supplier_type"><option value="Company">Company</option><option value="Individual">Individual</option></select></label><label>{{tr('Mobile Number','মোবাইল নম্বর')}}<input v-model="form.mobile_no" type="tel" /></label><label class="sos647-wide">{{tr('Email Address','ইমেইল ঠিকানা')}}<input v-model="form.email_id" type="email" /></label></div><div v-if="error" class="sos647-error" role="alert">{{error}}</div><div class="sos647-dialogfoot"><button type="button" @click="formOpen=false">{{tr('Cancel','বাতিল')}}</button><button class="sos647-primary" type="submit" :disabled="saving">{{saving?tr('Saving...','সংরক্ষণ হচ্ছে...'):tr('Save Supplier','সংরক্ষণ করুন')}}</button></div></form></div>
  </section>
</template>
<style scoped>
.sos647-root{--border:#e8ded0;position:fixed;inset:0 0 0 252px;z-index:19;overflow:auto;background:#faf8f3;padding:30px clamp(14px,3vw,44px);color:#493d32;font-family:inherit}
.sos647-root *{box-sizing:border-box}.sos647-top{display:flex;justify-content:space-between;align-items:center;gap:18px;margin:0 0 24px}.sos647-eyebrow{letter-spacing:1.6px;font-size:10px;color:#a18c70;font-weight:800}.sos647-top h1{font-size:30px;font-weight:800;margin:4px 0}.sos647-top p,.sos647-toolbar p{font-size:13px;color:#988a79;margin:4px 0}.sos647-primary{background:#765338!important;color:white!important;border:1px solid #765338!important;border-radius:11px;padding:12px 18px;white-space:nowrap;cursor:pointer;font-weight:700}.sos647-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:23px}.sos647-stats>div,.sos647-panel{background:#fff;border:1px solid var(--border);border-radius:16px;box-shadow:0 6px 22px #493d3207}.sos647-stats>div{padding:18px 20px}.sos647-stats small{display:block;color:#998978;font-weight:600}.sos647-stats strong{display:block;margin-top:9px;font-size:27px;color:#765338}.sos647-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:24px}.sos647-toolbar h2{font-size:17px;font-weight:800;margin:0}.sos647-actions{display:flex;gap:8px}.sos647-actions input,.sos647-fields input,.sos647-fields select{border:1px solid #e5dacb;background:#fffdfa;color:#4a3d30;border-radius:10px;padding:11px 12px;min-width:0}.sos647-actions button,.sos647-edit,.sos647-dialogfoot button:not(.sos647-primary){border:1px solid #e5dacb;background:#faf5ee;color:#765338;border-radius:10px;padding:10px 12px;cursor:pointer}.sos647-tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px}th{background:#f8f5ef;color:#998978;padding:13px 20px;font-size:10px;text-transform:uppercase;letter-spacing:.8px}td{padding:14px 20px;border-top:1px solid #f2eee7}td b{display:block;color:#4e3d2f;font-size:13px}td small{color:#a09586}.sos647-empty{text-align:center;padding:45px}.sos647-loading{padding:15px;color:#88745a}.sos647-error,.sos647-ok{margin:10px 20px;padding:12px;border-radius:9px;background:#fff1ed;color:#a53e30}.sos647-ok{background:#f1f8ef;color:#426e40}.sos647-backdrop{position:fixed;inset:0;z-index:99;background:#251d17a6;display:grid;place-items:center;padding:12px}.sos647-dialog{background:#fffdfa;border:1px solid var(--border);border-radius:18px;width:min(640px,100%);max-height:96vh;overflow:auto;box-shadow:0 25px 90px #20170b4d}.sos647-dialoghead,.sos647-dialogfoot{display:flex;justify-content:space-between;align-items:center;padding:22px 25px;border-bottom:1px solid var(--border)}.sos647-dialoghead small{font-size:10px;color:#9c896e;letter-spacing:1px}.sos647-dialoghead h2{font-size:21px;margin:3px 0}.sos647-dialoghead button{border:0;background:transparent;font-size:20px;cursor:pointer}.sos647-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:17px;padding:25px}.sos647-fields label{font-size:12px;color:#7a654d;font-weight:700;display:flex;flex-direction:column;gap:7px}.sos647-wide{grid-column:1/-1}.sos647-dialogfoot{border-top:1px solid var(--border);border-bottom:0;justify-content:flex-end;gap:10px}
@media(min-width:1024px){:global(body:has(.sos4-sidebar.sos4-compact)) .sos647-root{left:76px}}
@media(max-width:1023px){.sos647-root{left:0;padding:82px 15px 20px}.sos647-top{align-items:flex-start}.sos647-stats{gap:7px}.sos647-stats>div{padding:12px}.sos647-toolbar{flex-direction:column;align-items:stretch}.sos647-actions input{flex:1}.sos647-fields{grid-template-columns:1fr}.sos647-wide{grid-column:auto}}
</style>

<!-- SERVICING_STEP_648: keep main app header/profile visible above supplier workspace -->
<style scoped>
.sos647-root{inset:76px 0 0 252px!important;height:calc(100vh - 76px)!important;height:calc(100dvh - 76px)!important;z-index:19!important;overflow-y:auto!important;isolation:isolate;padding-top:23px!important;}
@media(min-width:1024px){:global(body:has(.sos4-sidebar.sos4-compact)) .sos647-root{left:76px!important;}}
@media(max-width:1023px){.sos647-root{inset:70px 0 0 0!important;height:calc(100vh - 70px)!important;height:calc(100dvh - 70px)!important;padding:18px 15px 25px!important;}}
</style>
