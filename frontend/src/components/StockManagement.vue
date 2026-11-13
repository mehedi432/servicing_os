<script setup>
// SERVICING_SHOP_STOCK_SEARCH_624A
import StockQuickAdd from "./StockQuickAdd.vue";

// AMCL_PARTS_ISSUE_615F
import PartsIssuePanel from "./PartsIssuePanel.vue";
// AMCL_STOCK_MANAGEMENT_615E3
import { ref, computed, onMounted } from 'vue';
const busy = ref(false);
const saving = ref(false);
const error = ref('');
const notice = ref('');
const tab = ref('balance');
const search = ref('');
const stock = ref([]);
const suppliers = ref([]);
const receipts = ref([]);
const requests = ref([]);
const supplier = ref('');
const canCreate = ref(false);
const warehouse = ref('Spare Parts - AMCL');
const lines = ref([{id:1,item_code:'',qty:1,rate:''}]);
let nextId = 2;
const items = computed(() => stock.value.filter(i =>
  `${i.item_code} ${i.item_name}`.toLowerCase().includes(search.value.toLowerCase())));
const availableItems = computed(() => stock.value);
const total = computed(() => lines.value.reduce((sum,r) =>
  sum + (Number(r.qty) > 0 && Number(r.rate) >= 0 ? Number(r.qty)*Number(r.rate) : 0), 0));
const hasLines = computed(() => lines.value.some(r => r.item_code));
function csrf() {return window.frappe?.csrf_token || window.csrf_token ||
  decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'');}
function failure(payload, fallback) {
  if (payload._server_messages) {
    try {const arr=JSON.parse(payload._server_messages);const m=JSON.parse(arr[arr.length-1]);return String(m.message||fallback).replace(/<[^>]*>/g,'');}catch{}
  }
  return payload.exception || fallback;
}
async function call(api, method, data={}, post=false) {
  const url=new URL(`/api/method/servicing_os.api.${api}.${method}`,window.location.origin);
  const options={method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}};
  if(post){options.headers['Content-Type']='application/json';options.headers['X-Frappe-CSRF-Token']=csrf();options.body=JSON.stringify(data);}
  else Object.entries(data).forEach(([k,v])=>{if(v!==''&&v!=null)url.searchParams.set(k,v)});
  const res=await fetch(url,options);
  let body;try{body=await res.json()}catch{throw Error('Unexpected server response')}
  if(!res.ok||body.exc||body.exc_type)throw Error(failure(body,'Request failed'));
  return body.message;
}
async function refresh(){busy.value=true;error.value='';try{
  const result=await call('stock_hub','get_stock_hub');
  stock.value=result.stock?.items||[];warehouse.value=result.stock?.warehouse||warehouse.value;
  suppliers.value=result.suppliers||[];receipts.value=result.receipts||[];
  requests.value=result.pending_requests||[];canCreate.value=!!result.can_create_receipt;
  if(!suppliers.value.some(s=>s.name===supplier.value))supplier.value='';
}catch(e){error.value=e.message}finally{busy.value=false}}
function add(){if(lines.value.length>=100)return;lines.value.push({id:nextId++,item_code:'',qty:1,rate:''})}
function remove(id){if(lines.value.length===1){lines.value=[{id:nextId++,item_code:'',qty:1,rate:''}]}else lines.value=lines.value.filter(l=>l.id!==id)}
function money(x){return new Intl.NumberFormat('en-BD',{style:'currency',currency:'BDT',maximumFractionDigits:2}).format(Number(x)||0)}
function openDoc(doctype,name){const slug=doctype.toLowerCase().replaceAll(' ','-');window.open('/app/'+slug+(name?'/'+encodeURIComponent(name):''),'_blank','noopener')}
async function createDraft(){
  error.value='';notice.value='';
  if(!canCreate.value){error.value='Your account cannot create Purchase Receipts.';return}
  if(!supplier.value){error.value='Select a Supplier. Create one in ERPNext if needed.';return}
  const filled=lines.value.filter(l=>l.item_code);
  if(!filled.length||filled.some(l=>!(Number(l.qty)>0)||l.rate===''||!Number.isFinite(Number(l.rate))||Number(l.rate)<0)){
    error.value='Select Items and enter valid quantities and actual purchase rates for every row.';return;
  }
  if(filled.length!==lines.value.length){error.value='Remove blank Item rows before saving.';return}
  if(!window.confirm(`Create a DRAFT Purchase Receipt for ${supplier.value}, ${filled.length} line(s), ${money(total.value)}? No stock will be posted.`))return;
  saving.value=true;
  try{
    const r=await call('stock_receiving','create_draft_purchase_receipt',{
      supplier:supplier.value,items:filled.map(l=>({item_code:l.item_code,qty:Number(l.qty),rate:Number(l.rate)}))
    },true);
    notice.value=`Draft ${r.purchase_receipt} created. Review and submit in ERPNext to receive stock.`;
    lines.value=[{id:nextId++,item_code:'',qty:1,rate:''}];
    await refresh();
    if(window.confirm(`Open ${r.purchase_receipt} in ERPNext for review?`))openDoc('Purchase Receipt',r.purchase_receipt);
  }catch(e){error.value=e.message}finally{saving.value=false}
}
onMounted(refresh);
</script>
<template>
  <section class="sm-root" aria-label="Stock Management">
<!-- StockQuickAdd is mounted globally in Inventory by 6.24B -->

    <div class="sm-top"><div><div class="sm-kicker">AL MODINA COMPUTERS LIMITED / INVENTORY</div>
      <h1>Spare Parts & Receiving</h1><p>ERPNext stock, supplier receipts and material requests · {{ warehouse }}</p></div>
      <button class="sm-secondary" :disabled="busy" @click="refresh">{{ busy?'Loading…':'↻ Refresh' }}</button>
    </div>
    <p v-if="error" class="sm-alert sm-error" role="alert">{{error}}</p>
    <p v-if="notice" class="sm-alert sm-success" role="status">{{notice}}</p>
    <div class="sm-stats"><div><strong>{{stock.length}}</strong><span>Stock Items</span></div>
      <div><strong>{{stock.filter(x=>Number(x.available_qty)>0).length}}</strong><span>In Stock</span></div>
      <div><strong>{{stock.filter(x=>Number(x.available_qty)<=0).length}}</strong><span>Out of Stock</span></div>
      <div><strong>{{requests.length}}</strong><span>Pending Issue Requests (up to 30)</span></div></div>
    <nav class="sm-tabs" aria-label="Inventory sections">
      <button v-for="x in [{key:'balance',label:'Stock Balance'},{key:'receive',label:'Receive Parts'},{key:'receipts',label:'Purchase Receipts'},{key:'requests',label:'Parts Requests'},{key:'issue',label:'Issue to Repair'}]" :key="x.key" type="button" :class="{'sm-active':tab===x.key}" @click="tab=x.key">{{x.label}}</button>
    </nav>
    <div v-if="tab==='balance'" class="sm-panel">
      <div class="sm-sectionhead"><h2>Warehouse Stock</h2><input v-model="search" aria-label="Search stock" placeholder="Search Items…" /></div>
      <div class="sm-table-wrap"><table><thead><tr><th>Item</th><th>Group</th><th class="sm-num">Actual</th><th class="sm-num">Reserved</th><th class="sm-num">Available</th></tr></thead>
        <tbody><tr v-for="r in items" :key="r.item_code"><td><strong>{{r.item_name}}</strong><small>{{r.item_code}}</small></td><td>{{r.item_group}}</td><td class="sm-num">{{r.actual_qty}}</td><td class="sm-num">{{r.reserved_qty}}</td><td class="sm-num"><span :class="Number(r.available_qty)>0?'sm-good':'sm-zero'">{{r.available_qty}}</span></td></tr>
          <tr v-if="!items.length"><td colspan="5">No matching Items found.</td></tr></tbody></table></div>
    </div>
    <div v-if="tab==='receive'" class="sm-panel">
      <div class="sm-sectionhead"><div><h2>Draft Purchase Receipt</h2><p>Supplier, Items and actual buying rates. Save as Draft; an authorized reviewer submits it in ERPNext.</p></div>
        <button type="button" class="sm-secondary" @click="openDoc('Supplier')">Manage Suppliers ↗</button></div>
      <div v-if="!canCreate" class="sm-alert sm-error">Your account cannot create Purchase Receipts. Ask a Stock Manager for permission.</div>
      <form @submit.prevent="createDraft">
        <label class="sm-label">Supplier<select v-model="supplier" required :disabled="!canCreate"><option value="">Select Supplier</option><option v-for="s in suppliers" :value="s.name" :key="s.name">{{s.supplier_name||s.name}}</option></select></label>
        <p v-if="!suppliers.length" class="sm-tip">No accessible Suppliers found. Create a real Supplier in ERPNext first, then Refresh.</p>
        <div class="sm-table-wrap"><table><thead><tr><th>Stock Item</th><th>Qty</th><th>Actual buying rate (BDT)</th><th></th></tr></thead>
          <tbody><tr v-for="(line,index) in lines" :key="line.id"><td><select v-model="line.item_code" :aria-label="'Item row '+(index+1)" :disabled="!canCreate" required><option value="">Select Item</option><option v-for="i in availableItems" :key="i.item_code" :value="i.item_code">{{i.item_name}}</option></select></td>
            <td><input v-model.number="line.qty" type="number" min="0.001" step="any" required :disabled="!canCreate" /></td>
            <td><input v-model="line.rate" type="number" min="0" step="0.01" required placeholder="Actual cost" :disabled="!canCreate" /></td>
            <td><button type="button" class="sm-remove" :disabled="!canCreate" @click="remove(line.id)" aria-label="Remove item">×</button></td></tr></tbody></table></div>
        <div class="sm-bottom"><button type="button" class="sm-secondary" :disabled="lines.length>=100||!canCreate" @click="add">+ Add Part</button><span class="sm-total">Estimated subtotal: {{money(total)}}</span></div>
        <div class="sm-actions"><span>Draft only · No stock or ledger posting</span><button type="submit" class="sm-primary" :disabled="saving||!canCreate||!stock.length">{{saving?'Saving…':'Create Draft Receipt'}}</button></div>
      </form>
    </div>
    <div v-if="tab==='receipts'" class="sm-panel"><div class="sm-sectionhead"><h2>Recent Purchase Receipts</h2><button class="sm-secondary" @click="openDoc('Purchase Receipt')">Open ERPNext ↗</button></div>
      <div class="sm-table-wrap"><table><thead><tr><th>Receipt</th><th>Supplier</th><th>Date</th><th>Status</th><th class="sm-num">Total</th></tr></thead>
        <tbody><tr v-for="r in receipts" :key="r.name"><td><button class="sm-link" @click="openDoc('Purchase Receipt',r.name)">{{r.name}} ↗</button></td><td>{{r.supplier}}</td><td>{{r.posting_date}}</td><td>{{r.docstatus===0?'Draft':r.docstatus===1?'Submitted':'Cancelled'}}</td><td class="sm-num">{{money(r.grand_total)}}</td></tr>
          <tr v-if="!receipts.length"><td colspan="5">No accessible Purchase Receipts yet.</td></tr></tbody></table></div></div>
    <div v-if="tab==='requests'" class="sm-panel"><div class="sm-sectionhead"><h2>Approved Parts Requests</h2><button class="sm-secondary" @click="openDoc('Material Request')">Open ERPNext ↗</button></div>
      <div class="sm-table-wrap"><table><thead><tr><th>Request</th><th>Service Job</th><th>Date</th><th>Status</th></tr></thead>
        <tbody><tr v-for="r in requests" :key="r.name"><td><button class="sm-link" @click="openDoc('Material Request',r.name)">{{r.name}} ↗</button></td><td>{{r.custom_service_job||'—'}}</td><td>{{r.transaction_date}}</td><td>{{r.status}}</td></tr>
        <tr v-if="!requests.length"><td colspan="4">No accessible approved requests.</td></tr></tbody></table></div></div>
    <div v-if="tab==='issue'" class="sm-panel"><PartsIssuePanel /></div>
    <div class="sm-foot">Stock figures come from ERPNext Bin. Purchase Receipts change stock only when submitted. Supplier invoices and payments are separate accounting documents.</div>
  </section>
</template>
<style scoped>
.sm-root{background:#f8f6f1;color:#504434;min-height:calc(100vh - 76px);padding:24px;box-sizing:border-box}
.sm-root *{box-sizing:border-box}.sm-top,.sm-sectionhead,.sm-bottom,.sm-actions{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.sm-top{margin-bottom:18px}.sm-top h1{font-size:26px;font-weight:750;letter-spacing:-.6px;margin:4px 0}.sm-top p,.sm-sectionhead p{font-size:13px;color:#8b7b67}.sm-kicker{font-size:11px;font-weight:700;letter-spacing:1.1px;color:#ac885a}
.sm-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:16px 0}.sm-stats>div{background:#fffdf9;padding:16px;border:1px solid #e7ddce;border-radius:12px;display:flex;flex-direction:column;gap:5px}.sm-stats strong{font-size:23px}.sm-stats span{font-size:12px;color:#877763}
.sm-tabs{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:16px}.sm-tabs button{border:1px solid #e4d8c8;padding:10px 14px;border-radius:10px;background:#fffdfa;font-weight:650;font-size:13px}.sm-tabs .sm-active{background:#80694b;color:white;border-color:#80694b}
.sm-panel{background:#fffdf9;border:1px solid #e5dace;border-radius:16px;padding:18px;min-width:0}.sm-sectionhead{margin-bottom:16px}.sm-sectionhead h2{font-size:17px;font-weight:750}.sm-sectionhead input{max-width:280px}.sm-root input,.sm-root select{min-width:0;width:100%;border:1px solid #ded3c3;border-radius:9px;background:#fff;color:#504434;padding:10px 12px;font-size:13px}.sm-label{display:flex;flex-direction:column;gap:8px;font-size:13px;font-weight:700;margin:0 0 16px;max-width:440px}
.sm-table-wrap{overflow:auto}.sm-root table{width:100%;border-collapse:collapse;font-size:13px}.sm-root th{color:#82715c;text-align:left;font-size:11px;font-weight:700;border-bottom:1px solid #e5dace;padding:12px}.sm-root td{border-bottom:1px solid #f0e9dd;padding:12px;vertical-align:middle}.sm-root td small{display:block;color:#9d8d79;margin-top:4px;overflow-wrap:anywhere}.sm-num{text-align:right!important;white-space:nowrap}.sm-good{color:#37764c;font-weight:750}.sm-zero{color:#a45b49;font-weight:750}
.sm-root .sm-secondary,.sm-root .sm-primary{border:1px solid #dacdb9;border-radius:9px;padding:10px 14px;font-weight:700;font-size:13px;cursor:pointer}.sm-root .sm-secondary{background:#fffdf8;color:#6b563b}.sm-root .sm-primary{background:#786044;color:#fff;border-color:#786044}.sm-root button:disabled{opacity:.55;cursor:not-allowed}.sm-remove{font-size:21px;padding:4px 10px;color:#a05243}.sm-bottom,.sm-actions{padding-top:16px}.sm-actions{border-top:1px solid #eee5d8;margin-top:16px}.sm-actions span,.sm-tip,.sm-foot{font-size:12px;color:#90816d}.sm-total{font-weight:700}.sm-link{color:#765b38;text-decoration:underline;cursor:pointer}.sm-alert{padding:12px 14px;border-radius:9px;margin:10px 0;font-size:13px}.sm-error{background:#fbe7e4;color:#8b2e24}.sm-success{background:#e8f3e8;color:#2b693d}.sm-foot{padding:18px 4px}
@media(max-width:900px){.sm-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.sm-root{padding:14px}.sm-panel{padding:12px}}
@media(max-width:560px){.sm-root td,.sm-root th{padding:9px}.sm-stats{gap:8px}}
</style>
