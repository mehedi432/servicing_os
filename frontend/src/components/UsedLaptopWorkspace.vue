<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { moduleApi } from './extensionApi.js';

const API_ROOT = '/api/method/servicing_os.api.';
async function call(namespace, method, data={}, post=false) {
  const url = new URL(API_ROOT + namespace + '.' + method, window.location.origin);
  const cfg = { method: post ? 'POST' : 'GET', credentials:'same-origin', headers:{'Accept':'application/json'} };
  if(post){
    cfg.headers['Content-Type']='application/json';
    const token=window.frappe?.csrf_token || window.csrf_token || decodeURIComponent((document.cookie.split('; ').find(v=>v.startsWith('csrf_token='))||'').split('=').slice(1).join('=')||'');
    if(token) cfg.headers['X-Frappe-CSRF-Token']=token;
    cfg.body=JSON.stringify(data);
  }else Object.entries(data).forEach(([k,v])=>{if(v!==null&&v!==undefined&&v!=='')url.searchParams.set(k,String(v));});
  let r, j;
  try{r=await fetch(url.toString(),cfg);j=await r.json();}catch{throw new Error('Unable to connect. Check your connection and try again.');}
  if(!r.ok||j.exc||j.exc_type){
    let msg='The request could not be completed.';
    try{const arr=JSON.parse(j._server_messages||'[]');if(arr.length)msg=JSON.parse(arr[arr.length-1]).message||msg;}catch{}
    throw new Error(msg==='The request could not be completed.'?(j.message?.message||j.exception||msg):msg);
  }
  return j.message;
}
const ul=(method, data={},post=false)=>call('used_laptop_counter',method,data,post);
const customerApi=(method,data={},post=false)=>call('counter_customers',method,data,post);
const hub=ref({items:[],receipts:[],suppliers:[],supplier_groups:[]});
const query=ref('');const busy=ref(false);const notice=ref('');const error=ref('');
const laptopView=ref('list'); // SOS_LAPTOP_GRID_FLOW_625A
const selected=ref('');const tab=ref('overview');const showBuy=ref(false);const showSupplier=ref(false);const receiveId=ref('');
const buy=ref({supplier:'',brand:'',model:'',serial:'',purchase_cost:''});
const sup=ref({name:'',group:''});
const svc=ref({status:'Inspection Pending',condition:'B',diagnosis:'',work_done:'',technician:'',repair_spend:'',asking_price:'',warranty_days:0});
const serviceHistory=ref([]);
const customerQuery=ref('');const customerResults=ref([]);const customer=ref(null);const showCustomer=ref(false);
const customerCfg=ref({groups:[],territories:[],default_group:'',default_territory:''});
const newCustomer=ref({customer_name:'',mobile_no:'',customer_group:'',territory:''});
const sale=ref({price:'',quote:null,key:'',confirm:false});
const receipt=ref(null);
let searchTimer=null;let laptopSearchTimer=null;
const devices=computed(()=>hub.value.items||[]);
const picked=computed(()=>devices.value.find(x=>x.name===selected.value)||null);
const receipts=computed(()=>hub.value.receipts||[]);
// SOS_UL_INSPECTION_LABELS_631: presentation only; never overwrite a stored laptop status.
// A purchase does not imply a repair. A real repair must be explicitly recorded.
const stageOptionLabel=s=>({
  'Inspection Pending':'Awaiting Inspection',
  'Diagnosing':'Inspection / Diagnosis',
  'Repairing':'Repair in Progress',
  'Hold':'On Hold',
  'Ready for Sale':'Ready for Sale'
})[s]||s;
const statusText=x=>{
  if(!x) return 'Not Selected';
  if(x.status==='Sold') return 'Sold';
  if(Number(x.intake?.docstatus)===0) return 'Purchase Draft · Stock Not Received';
  if(Number(x.actual_qty)<1) return 'Awaiting Stock Receipt / Stock Check';
  const current=x.status||'Inspection Pending';
  if(current==='Inspection Pending') return 'In Stock · Awaiting Inspection';
  if(current==='Diagnosing') return 'Inspection in Progress';
  if(current==='Repairing') return 'Repair in Progress';
  if(current==='Hold') return 'On Hold';
  return current;
};
const money=n=>'৳'+Number(n||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2});
const canReceive=x=>Number(x?.intake?.docstatus)===0&&hub.value.can_submit;
const resetMessages=()=>{error.value='';notice.value='';};
const showError=e=>{error.value=e?.message||String(e);};
const key=()=>('UL'+Date.now().toString(36)+Math.random().toString(36).slice(2).padEnd(20,'0')).slice(0,40);
async function refresh(keep=true){
  busy.value=true;error.value='';
  try{
    const result=await ul('get_workspace',{search:query.value});hub.value=result;
    if(!keep||!devices.value.some(x=>x.name===selected.value))selected.value=devices.value[0]?.name||'';
    if(picked.value)copyService();
  }catch(e){showError(e);}finally{busy.value=false;}
}
function copyService(){
  const x=picked.value;if(!x)return;
  svc.value={status:x.status==='Awaiting Stock Receipt'?'Inspection Pending':x.status,
    condition:x.custom_sos_ul_condition||'B',
    diagnosis:x.custom_sos_ul_diagnosis||'',work_done:x.custom_sos_ul_work_done||'',
    technician:x.custom_sos_ul_technician||'',
    repair_spend:x.custom_sos_ul_service_cost??0,asking_price:x.custom_sos_ul_asking_price??'',
    warranty_days:x.custom_sos_ul_warranty_days||0};
  sale.value={price:x.custom_sos_ul_asking_price||'',quote:null,key:'',confirm:false};
  serviceHistory.value=[];
}
function selectDevice(x){selected.value=x.name;tab.value='overview';receipt.value=null;resetMessages();copyService();}
function nextLabel(x){
  if(x.status==='Sold')return 'View sale status';
  if(Number(x.intake?.docstatus)===0)return 'Receive Into Stock';
  if(Number(x.actual_qty)<1)return 'Check stock receipt';
  return x.can_sell?'Sell This Laptop':'Inspect / Service';
}
function nextStep(x){
  if(!x)return;
  selectDevice(x);
  if(x.status==='Sold'){tab.value='overview';notice.value='This laptop is already sold. Use its invoice reference for a duplicate receipt.';return;}
  if(Number(x.intake?.docstatus)===0 && x.intake?.receipt){receiveId.value=x.intake.receipt;return;}
  if(Number(x.actual_qty)<1){error.value='No submitted stock is available for this device. Check its physical receipt and exact serial before attempting a sale.';return;}
  if(x.can_sell){openSell();return;}
  openService();
}
function openQuick(action){
  resetMessages();
  if(devices.value.length===0){
    showBuy.value=true;
    notice.value='Start by registering an actual laptop. Then receive it into stock, inspect it and sell it. No demo devices are created.';
    return;
  }
  if(!picked.value){
    if(devices.value.length===1){selectDevice(devices.value[0]);}
    else{notice.value='Select the exact laptop from the list or grid first, so another device is not serviced or sold by mistake.';return;}
  }
  if(action==='sell')openSell();else openService();
}
watch(query,()=>{clearTimeout(laptopSearchTimer);laptopSearchTimer=setTimeout(()=>refresh(false),350);});
function openService(){if(!picked.value)return;tab.value='service';resetMessages();loadHistory();}
async function loadHistory(){if(!picked.value)return;try{serviceHistory.value=(await ul('get_service_history',{item_code:picked.value.name})).events||[];}catch{serviceHistory.value=[];}}
async function register(){resetMessages();busy.value=true;try{
  const r=await moduleApi('create_used_laptop_draft',buy.value,true);
  showBuy.value=false;query.value='';await refresh(false);selected.value=r.item_code;copyService();
  notice.value=`${r.item_code} registered. Now click Receive Into Stock to confirm the physical laptop.`;
  buy.value={supplier:'',brand:'',model:'',serial:'',purchase_cost:''};
}catch(e){showError(e);}finally{busy.value=false;}}
async function createSupplier(){resetMessages();busy.value=true;try{
  const r=await moduleApi('create_supplier_from_counter',{name:sup.value.name,supplier_group:sup.value.group},true);
  showSupplier.value=false;await refresh();buy.value.supplier=r.supplier;notice.value='Supplier saved and selected.';
  sup.value={name:'',group:''};
}catch(e){showError(e);}finally{busy.value=false;}}
async function submitReceipt(){if(!receiveId.value)return;resetMessages();busy.value=true;const id=receiveId.value;
  try{await moduleApi('submit_used_laptop_receipt',{receipt_name:id},true);receiveId.value='';await refresh();notice.value=`${id} received into Used Laptops stock. Next: Inspect / Service.`;}
  catch(e){showError(e);receiveId.value='';}finally{busy.value=false;}
}
async function saveService(){if(!picked.value)return;resetMessages();busy.value=true;try{
  const args={...svc.value,item_code:picked.value.name};await ul('save_service',args,true);
  await refresh();tab.value='service';await loadHistory();notice.value='Inspection / repair record saved. No inventory or accounting posting.';
}catch(e){showError(e);}finally{busy.value=false;}}
async function openSell(){if(!picked.value)return;resetMessages();tab.value='sell';sale.value.quote=null;sale.value.confirm=false;
  if(!customerCfg.value.groups.length){try{customerCfg.value=await customerApi('get_customer_config');
    newCustomer.value.customer_group=customerCfg.value.default_group;
    newCustomer.value.territory=customerCfg.value.default_territory;}catch(e){showError(e);}}
}
async function findCustomer(){const s=customerQuery.value.trim();if(s.length<2){customerResults.value=[];return;}
  try{customerResults.value=(await customerApi('search_customers',{search:s})).customers||[];}catch(e){showError(e);}}
watch(customerQuery,()=>{clearTimeout(searchTimer);searchTimer=setTimeout(findCustomer,280);});
function pickCustomer(x){customer.value=x;customerQuery.value=x.customer_name;customerResults.value=[];sale.value.quote=null;}
async function createCustomer(){resetMessages();busy.value=true;try{
  const r=await customerApi('create_counter_customer',newCustomer.value,true);
  showCustomer.value=false;pickCustomer(r.customer);notice.value='New customer created and selected.';
}catch(e){showError(e);}finally{busy.value=false;}}
async function quote(){if(!picked.value||!customer.value)return;resetMessages();busy.value=true;try{
  const r=await ul('quote_cash_sale',{item_code:picked.value.name,customer:customer.value.name,selling_price:sale.value.price},true);
  sale.value.quote=r;sale.value.key=key();
}catch(e){showError(e);}finally{busy.value=false;}}
async function complete(){if(!sale.value.quote||!picked.value||!customer.value)return;resetMessages();busy.value=true;try{
  const r=await ul('complete_cash_sale',{item_code:picked.value.name,customer:customer.value.name,
    selling_price:sale.value.price,expected_total:sale.value.quote.grand_total,checkout_key:sale.value.key},true);
  sale.value.confirm=false;receipt.value=await ul('get_sale_receipt',{invoice_name:r.invoice});
  await refresh();tab.value='sell';notice.value=`Sale completed: ${r.invoice}. Inventory and cash collection posted.`;
}catch(e){showError(e);}finally{busy.value=false;}}
async function printReceipt(){if(!receipt.value)return;await nextTick();document.body.classList.add('sos-ul-print-mode');window.print();}
function afterPrint(){document.body.classList.remove('sos-ul-print-mode');}
onMounted(()=>{window.addEventListener('afterprint',afterPrint);refresh(false);});
onBeforeUnmount(()=>{clearTimeout(searchTimer);clearTimeout(laptopSearchTimer);window.removeEventListener('afterprint',afterPrint);afterPrint();});
</script>

<template>
<section class="sos-ext-root sos-used sos-ul-workspace">
  <header class="ex-heading ul-header">
    <div><div class="ex-kicker">SERVICING OS · OWNED DEVICE OPERATIONS</div><h1>Used Laptops</h1><p>Buy it. Inspect it. Refurbish it. Sell it. One workspace.</p></div>
    <button class="ex-secondary" type="button" :disabled="busy" @click="refresh()">↻ Refresh</button>
  </header>
  <div v-if="error" class="ex-alert ex-error ul-alert" role="alert">{{error}}</div>
  <div v-if="notice" class="ex-alert ex-success ul-alert" role="status">{{notice}}</div>
  <div class="ul-quick">
    <button class="ul-action" type="button" @click="showBuy=true"><span class="ul-action-icon">＋</span><strong>1. Buy / Add Laptop</strong><small>Supplier, serial, actual cost & receive</small></button>
    <button class="ul-action" type="button" @click="openQuick('service')"><span class="ul-action-icon">⚒</span><strong>2. Service / Refurbish</strong><small>Condition, testing, technician & repairs</small></button>
    <button class="ul-action" type="button" @click="openQuick('sell')"><span class="ul-action-icon">৳</span><strong>3. Sell Laptop</strong><small>Customer, cash checkout & receipt</small></button>
  </div>
  <div class="ul-stats"><span><strong>{{devices.length}}</strong> Registered</span><span><strong>{{devices.filter(x=>Number(x.actual_qty)>0).length}}</strong> In stock</span><span><strong>{{devices.filter(x=>x.can_sell).length}}</strong> Ready for sale</span><span><strong>{{receipts.filter(x=>x.docstatus===0).length}}</strong> Draft receipts</span></div>
  <div class="ul-guide"><strong>Simple flow:</strong><span>① Buy / Add</span><span>② Receive</span><span>③ Inspect &amp; Price</span><span>④ Sell &amp; Print</span></div>
  <div class="ul-workgrid" :class="{'ul-grid-mode':laptopView==='grid'}">
    <aside class="ul-panel ul-list-panel">
      <div class="ul-panel-head ul-register-head"><div><h2>Laptops</h2><span>{{devices.length}} shown</span></div>
        <div class="ul-view-switch" role="group" aria-label="Laptop display view">
          <button type="button" title="List view" aria-label="List view" :aria-pressed="laptopView==='list'" :class="{active:laptopView==='list'}" @click="laptopView='list'">☰</button>
          <button type="button" title="Grid view" aria-label="Grid view" :aria-pressed="laptopView==='grid'" :class="{active:laptopView==='grid'}" @click="laptopView='grid'">▦</button>
        </div></div>
      <div class="ul-search"><input v-model="query" placeholder="Search laptop, model or serial — results update automatically" aria-label="Find used laptop" /></div>
      <div v-if="!devices.length" class="ul-empty ul-guided-empty">
          <strong>{{query.trim()?'No matching laptops':'No laptops registered yet'}}</strong>
          <p>{{query.trim()?'Clear your search to see all registered devices.':'To enable Service and Sell, register the first physical laptop with its unique serial and actual purchase cost.'}}</p>
          <button v-if="!query.trim()" class="ex-primary" type="button" @click="showBuy=true">＋ Buy / Add First Laptop</button>
          <button v-else class="ex-secondary" type="button" @click="query=''">Clear Search</button>
          <p v-if="!hub.can_register">Your login lacks Item/Purchase Receipt creation access. Ask your manager to enable the required permission.</p>
        </div>
      <div class="ul-devices">
        <button v-for="x in devices" :key="x.name" class="ul-device" type="button" :class="{active:selected===x.name}" @click="selectDevice(x)">
          <span class="ul-device-symbol">▣</span><span class="ul-device-main"><strong>{{x.item_name}}</strong><small>{{x.intake?.serial||x.name}}</small><em :class="{'is-ready':x.can_sell}">{{statusText(x)}}</em><span class="ul-next-inline">{{nextLabel(x)}} →</span></span><span class="ul-right-arrow">›</span>
        </button>
      </div>
      <button class="ul-add-bottom" type="button" @click="showBuy=true">+ Add another used laptop</button>
    </aside>
    <main class="ul-panel ul-detail-panel">
      <template v-if="picked">
        <div class="ul-detail-title"><div><div class="ex-kicker">DEVICE FILE</div><h2>{{picked.item_name}}</h2><p>Serial: <b>{{picked.intake?.serial||'Awaiting receipt'}}</b> · {{picked.name}}</p></div><span class="ul-pill" :class="{'green':picked.can_sell}">{{statusText(picked)}}</span></div>
        <div class="ul-next-area"><span>Recommended next step</span><button type="button" class="ex-primary" :disabled="busy" @click="nextStep(picked)">{{nextLabel(picked)}} →</button></div>
        <div class="sos633-stock-truth" role="status">
          <div><span>Inventory type</span><strong :class="{'sos633-bad':Number(picked.is_stock_item)!==1}">{{Number(picked.is_stock_item)===1?'Stock Item':'Not a Stock Item — needs review'}}</strong></div>
          <div><span>Serial tracking</span><strong :class="{'sos633-bad':Number(picked.has_serial_no)!==1}">{{Number(picked.has_serial_no)===1?'Enabled':'Disabled — needs review'}}</strong></div>
          <div><span>Warehouse on-hand</span><strong>{{Number(picked.actual_qty||0)}} {{picked.stock_uom||'Nos'}}</strong></div>
          <p v-if="Number(picked.actual_qty||0)<1" class="sos633-stock-message">A registered laptop is not automatically available for sale. Confirm its actual Purchase Receipt into {{hub.warehouse}} first.</p>
          <p v-else class="sos633-stock-message">Warehouse: {{hub.warehouse}}. Sale additionally requires a verified serial and Ready for Sale status.</p>
        </div>
        <div class="ul-facts"><div><small>Owned stock</small><strong>{{Number(picked.actual_qty)>0?'1 device':'Not received / Sold'}}</strong></div><div><small>Supplier</small><strong>{{picked.intake?.supplier||'—'}}</strong></div><div><small>Purchase receipt</small><strong>{{picked.intake?.receipt||'Not recorded'}}</strong></div><div><small>Condition</small><strong>{{picked.custom_sos_ul_condition||'Not inspected'}}</strong></div></div>
        <div v-if="Number(picked.intake?.docstatus)===0" class="ul-callout"><div><strong>Physical receiving required</strong><p>This laptop is only a draft purchase. Verify its serial and supplier before stock is posted.</p></div><button class="ex-primary" type="button" :disabled="!hub.can_submit||busy" @click="receiveId=picked.intake.receipt">Receive Into Stock</button><small v-if="!hub.can_submit">A user with Purchase Receipt submit access must confirm.</small></div>
        <div class="ul-detail-tabs"><button type="button" :class="{active:tab==='overview'}" @click="tab='overview'">Overview</button><button type="button" :class="{active:tab==='service'}" @click="openService">Inspect & Service</button><button type="button" :class="{active:tab==='sell'}" @click="openSell">Sell & Receive Cash</button></div>
        <div v-if="tab==='overview'" class="ul-panel-content">
          <div v-if="picked.status==='Inspection Pending' && Number(picked.actual_qty)>0" class="ul-631-inspection-note" role="status">
            <strong>Purchased and received — awaiting inspection</strong>
            <span>No repair is required by default. Inspect the device first. If it passes, enter the findings and selling price, then choose Ready for Sale. Select Repair in Progress only when a real fault needs fixing.</span>
          </div>
          <h3>What should happen next?</h3>
          <div class="ul-step"><span>1</span><div><strong>Receive the purchased laptop</strong><p>Confirm that the device and serial match the supplier receipt.</p></div><b>{{Number(picked.actual_qty)>0?'✓ Done':'Pending'}}</b></div>
          <div class="ul-step"><span>2</span><div><strong>Inspect / repair</strong><p>Record condition, diagnosis, technician, tests and asking price.</p></div><button class="ex-secondary" @click="openService">Open</button></div>
          <div class="ul-step"><span>3</span><div><strong>Sell to customer</strong><p>Ready devices can be sold by serial with cash settlement and receipt.</p></div><button class="ex-primary" @click="openSell">Open</button></div>
          <p class="ul-explain">Sale is blocked until this exact serial is in stock and the device is marked <b>Ready for Sale</b>.</p>
        </div>
        <div v-if="tab==='service'" class="ul-panel-content">
          <div class="ul-section-head"><h3>Inspection & Refurbishment</h3><span>Recorded against this device</span></div>
          <div v-if="!hub.can_service" class="ul-callout">Your account needs the Service Technician or System Manager role to save a repair record.</div>
          <form class="ul-form" @submit.prevent="saveService">
            <label>Inspection / preparation status<select v-model="svc.status" required><option v-for="s in hub.service_statuses||[]" :key="s" :value="s">{{stageOptionLabel(s)}}</option></select></label>
            <label>Condition grade<select v-model="svc.condition" required><option v-for="g in hub.condition_grades||[]" :key="g">{{g}}</option></select></label>
            <label>Assigned technician (user ID)<input v-model.trim="svc.technician" placeholder="Optional, e.g. rasel@amcl.com" /></label>
            <label>Warranty to offer (days)<input v-model.number="svc.warranty_days" type="number" min="0" max="1095" /></label>
            <label class="ul-wide">Inspection / diagnosis<textarea v-model="svc.diagnosis" rows="3" maxlength="1800" placeholder="Display, keyboard, ports, battery, storage, processor..." /></label>
            <label class="ul-wide">Repair and testing work<textarea v-model="svc.work_done" rows="3" maxlength="1800" placeholder="Cleaning, SSD replacement, battery test, Windows setup, stress test..." /></label>
            <label>Tracked repair spend (BDT)<input v-model="svc.repair_spend" type="number" min="0" step="0.01" :disabled="!hub.can_price" placeholder="0.00" /></label>
            <label>Asking price (BDT)<input v-model="svc.asking_price" type="number" min="0" step="0.01" :disabled="!hub.can_price" placeholder="0.00" /></label>
            <p class="ul-wide ul-631-explain">A purchased laptop is not automatically a repair job. Inspect it first. Choose <b>Ready for Sale</b> after a passing inspection and record the test findings. Choose <b>Repair in Progress</b> only if a fault has been confirmed.</p>
            <p class="ul-wide ul-explain">Repair spend here is a tracking note, <b>not</b> a posted accounting expense. Managers control pricing. Set Ready for Sale only after inspection is complete.</p>
            <div class="ul-wide ul-form-actions"><button class="ex-primary" type="submit" :disabled="busy||!hub.can_service||Number(picked.actual_qty)<1">{{busy?'Saving...':'Save Inspection / Repair'}}</button></div>
          </form>
          <h4 class="ul-history-heading">Service history</h4>
          <div v-if="!serviceHistory.length" class="ul-explain">No service updates recorded yet.</div>
          <div v-for="(h,i) in serviceHistory" :key="i" class="ul-history"><small>{{h.creation}} · {{h.comment_by}}</small><p>{{h.content}}</p></div>
        </div>
        <div v-if="tab==='sell'" class="ul-panel-content">
          <div v-if="!picked.can_sell" class="ul-callout"><div><strong>Sale not available yet</strong>
              <p v-if="Number(picked.intake?.docstatus)===0">First receive this laptop into stock. The purchase receipt is still a draft.</p>
              <p v-else-if="Number(picked.actual_qty)<1">The selected serial is not available in the Used Laptops warehouse.</p>
              <p v-else>Complete inspection, enter a selling price and choose Ready for Sale.</p>
            </div><button class="ex-secondary" type="button" @click="nextStep(picked)">{{nextLabel(picked)}}</button></div>
          <div v-if="!hub.can_cash_sale" class="ul-callout">Your cashier account needs create and submit access for Sales Invoice and Payment Entry. Ask the manager.</div>
          <div v-if="receipt" class="ul-sale-complete"><strong>✓ Sale completed</strong><p>{{receipt.invoice}} · {{receipt.item_name}} · {{money(receipt.grand_total)}}</p><button class="ex-primary" @click="printReceipt">Print Receipt</button></div>
          <div class="ul-form">
            <div class="ul-wide"><label>Customer — search name or mobile</label><div class="ul-customer-bar"><input v-model="customerQuery" placeholder="Customer name or 01XXXXXXXXX" @input="customer=null;sale.quote=null" /><button class="ex-secondary" @click="showCustomer=true">+ New Customer</button></div>
              <div v-if="customerResults.length" class="ul-customer-results"><button v-for="c in customerResults" :key="c.name" @click="pickCustomer(c)"><b>{{c.customer_name}}</b><small>{{c.mobile||c.name}}</small></button></div>
              <p v-if="customer" class="ul-selected">✓ Selected: <strong>{{customer.customer_name}}</strong> · {{customer.mobile||customer.name}}</p>
            </div>
            <label>Final selling price (BDT)<input v-model="sale.price" type="number" min="0.01" step="0.01" placeholder="Enter agreed price" @input="sale.quote=null" /></label>
            <div class="ul-price-info"><small>Exact OEM serial</small><strong>{{picked.intake?.serial||'—'}}</strong><small>Warehouse</small><strong>{{hub.warehouse}}</strong></div>
            <div class="ul-wide ul-form-actions"><button class="ex-secondary" :disabled="busy||!picked.can_sell||!hub.can_cash_sale||!customer||!Number(sale.price)" @click="quote">1. Review Final Total</button></div>
          </div>
          <div v-if="sale.quote" class="ul-quote"><div><span>Net</span><strong>{{money(sale.quote.net_total)}}</strong></div><div><span>Taxes / charges</span><strong>{{money(sale.quote.tax_total)}}</strong></div><div class="ul-quote-total"><span>Cash to collect</span><strong>{{money(sale.quote.grand_total)}}</strong></div><button class="ex-primary" :disabled="busy" @click="sale.confirm=true">2. Confirm Cash Sale</button></div>
          <p class="ul-explain">Confirm posts a real invoice, removes the exact serial from inventory and records a fully allocated Cash payment. No external checkout screen.</p>
        </div>
      </template>
      <div v-else class="ul-empty ul-big-empty"><strong>{{devices.length?'Choose a laptop to continue':'Start with the first purchase'}}</strong>
        <p>{{devices.length?'Select the exact serial above to inspect or sell it.':'A sale cannot be made until the laptop is registered, physically received and inspected.'}}</p>
        <button v-if="!devices.length" type="button" class="ex-primary" @click="showBuy=true">＋ Buy / Add Laptop</button>
      </div>
    </main>
  </div>
  <div v-if="showBuy" class="ex-modal-shade" @click.self="showBuy=false"><form class="ex-modal ul-modal" @submit.prevent="register">
    <div class="ex-modal-header"><div><div class="ex-kicker">STEP 1 · BUY / REGISTER</div><h2>Add Used Laptop</h2></div><button type="button" class="ex-close" @click="showBuy=false">×</button></div>
    <div v-if="!hub.can_register" class="ul-callout">Your account needs Item create and Purchase Receipt create permissions. Ask the manager to give this access.</div>
    <div class="ex-form"><label>Supplier<select v-model="buy.supplier" required><option value="">Choose supplier</option><option v-for="s in hub.suppliers||[]" :key="s.name" :value="s.name">{{s.supplier_name}}</option></select></label><button class="ex-inline-link" type="button" @click="showSupplier=true">+ Add supplier without leaving this screen</button><label>Brand<input v-model.trim="buy.brand" required maxlength="45" placeholder="Dell / HP / Lenovo" /></label><label>Model<input v-model.trim="buy.model" required maxlength="90" placeholder="ThinkPad T480 / Latitude 5420" /></label><label>Original device serial<input v-model.trim="buy.serial" required maxlength="90" placeholder="Read from actual laptop" /></label><label>Actual purchase cost · BDT<input v-model="buy.purchase_cost" required type="number" min="0.01" step="0.01" /></label></div>
    <p class="ul-explain">Save creates a laptop record and <b>draft</b> purchase receipt. Stock and accounting are updated only after you explicitly receive the laptop.</p>
    <div class="ex-modal-actions"><button type="button" class="ex-secondary" @click="showBuy=false">Cancel</button><button class="ex-primary" :disabled="busy||!hub.can_register" type="submit">{{busy?'Saving...':'Save Laptop Intake'}}</button></div>
  </form></div>
  <div v-if="showSupplier" class="ex-modal-shade ul-top-modal" @click.self="showSupplier=false"><form class="ex-modal" @submit.prevent="createSupplier"><div class="ex-modal-header"><h2>New Supplier</h2><button class="ex-close" type="button" @click="showSupplier=false">×</button></div><div class="ex-form"><label>Supplier name<input v-model.trim="sup.name" required maxlength="120" /></label><label>Supplier group<select v-model="sup.group" required><option value="">Choose group</option><option v-for="g in hub.supplier_groups||[]" :key="g">{{g}}</option></select></label></div><div class="ex-modal-actions"><button type="button" class="ex-secondary" @click="showSupplier=false">Cancel</button><button class="ex-primary" :disabled="busy||!hub.can_add_supplier">Create & Select Supplier</button></div></form></div>
  <div v-if="receiveId" class="ex-modal-shade" @click.self="receiveId=''" ><div class="ex-modal"><div class="ex-modal-header"><h2>Receive Physical Laptop?</h2><button class="ex-close" @click="receiveId=''">×</button></div><p><b>{{receiveId}}</b> will be submitted to the shop inventory. Confirm the serial, actual cost, supplier, and physical condition first.</p><div class="ex-modal-actions"><button class="ex-secondary" @click="receiveId=''">Cancel</button><button class="ex-primary" :disabled="busy" @click="submitReceipt">Confirm Stock Receipt</button></div></div></div>
  <div v-if="showCustomer" class="ex-modal-shade" @click.self="showCustomer=false"><form class="ex-modal" @submit.prevent="createCustomer"><div class="ex-modal-header"><h2>Add New Customer</h2><button type="button" class="ex-close" @click="showCustomer=false">×</button></div><div class="ex-form"><label>Customer name<input required v-model.trim="newCustomer.customer_name" /></label><label>Mobile number (required)<input required v-model.trim="newCustomer.mobile_no" placeholder="01XXXXXXXXX" inputmode="tel" /></label><label>Customer group<select v-model="newCustomer.customer_group" required><option value="">Choose group</option><option v-for="g in customerCfg.groups" :key="g">{{g}}</option></select></label><label>Territory<select v-model="newCustomer.territory" required><option value="">Choose territory</option><option v-for="t in customerCfg.territories" :key="t">{{t}}</option></select></label></div><p class="ul-explain">Duplicate mobile numbers are checked before saving.</p><div class="ex-modal-actions"><button class="ex-secondary" @click="showCustomer=false" type="button">Cancel</button><button class="ex-primary" :disabled="busy||!hub.can_create_customer">Save & Select Customer</button></div></form></div>
  <div v-if="sale.confirm" class="ex-modal-shade" @click.self="sale.confirm=false"><div class="ex-modal"><div class="ex-modal-header"><h2>Confirm Real Cash Sale</h2><button class="ex-close" @click="sale.confirm=false">×</button></div><p><b>{{picked?.item_name}}</b><br/>Serial: {{picked?.intake?.serial}}<br/>Customer: {{customer?.customer_name}}</p><p class="ul-confirm-total">Cash received: {{money(sale.quote?.grand_total)}}</p><p class="ul-explain">This posts an invoice, deducts the exact serialized laptop from stock, and records the cash collection. This is not a demo.</p><div class="ex-modal-actions"><button class="ex-secondary" @click="sale.confirm=false">Cancel</button><button class="ex-primary" :disabled="busy" @click="complete">{{busy?'Posting...':'Confirm & Complete Sale'}}</button></div></div></div>
  <div v-if="receipt" id="ul-print-receipt" class="ul-print-paper"><h2>AL MODINA COMPUTERS LIMITED</h2><p>USED LAPTOP SALE RECEIPT</p><hr/><p>Invoice: {{receipt.invoice}}<br/>Date: {{receipt.posting_date}}<br/>Customer: {{receipt.customer}}</p><hr/><p>{{receipt.item_name}}<br/>Serial: {{receipt.serial}}</p><div class="ul-print-total"><span>Total paid</span><b>{{money(receipt.grand_total)}}</b></div><p>Thank you for shopping with us.</p></div>
</section>
</template>
<style scoped src="./extensionStyle.css"></style>
<style scoped>
.sos-ul-workspace{--ink:#463a2b;--muted:#887765}
.ul-guide{display:flex;gap:8px;flex-wrap:wrap;align-items:center;background:#fff9ef;border:1px solid #e9dcc9;border-radius:12px;padding:10px 13px;margin-bottom:14px;font-size:11px;color:#786142}
.ul-guide strong{margin-right:4px;color:#47372a}.ul-guide span{padding:4px 8px;background:#f5eddf;border-radius:7px}
.ul-view-switch{display:flex;gap:3px;border:1px solid #e6d9c9;background:#f7f2e8;border-radius:10px;padding:3px}
.ul-view-switch button{font-size:17px;font-weight:800;display:grid;place-items:center;border:0;border-radius:7px;width:34px;height:32px;color:#7b6851;background:transparent;cursor:pointer}
.ul-view-switch button.active{background:white;color:#674b2f;box-shadow:0 2px 7px #62503f24}
.ul-register-head{align-items:center}.ul-register-head>div:first-child{display:grid;gap:3px}
.ul-grid-mode{grid-template-columns:minmax(0,1fr)!important}
.ul-grid-mode .ul-list-panel{position:static}.ul-grid-mode .ul-devices{grid-template-columns:repeat(auto-fill,minmax(230px,1fr));max-height:none;overflow:visible}
.ul-grid-mode .ul-device{min-height:160px;align-items:flex-start;flex-direction:column;gap:13px}.ul-grid-mode .ul-device-main{width:100%}.ul-grid-mode .ul-right-arrow{display:none}
.ul-grid-mode .ul-list-panel{min-width:0}.ul-grid-mode .ul-detail-panel{min-height:200px}
.ul-next-inline{font-size:10px!important;color:#81603b!important;font-weight:800}
.ul-next-area{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin:15px 0;padding:11px 13px;border-radius:11px;background:#f7f1e8;font-size:11px;font-weight:800;color:#84694b}
.ul-guided-empty button,.ul-big-empty button{margin-top:12px}
.ul-header{margin-bottom:14px}.ul-alert{margin:12px 0}
.ul-quick{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 15px}
.ul-action{padding:17px;display:flex;align-items:flex-start;flex-direction:column;gap:8px;text-align:left;border:1px solid #e8dccb;border-radius:16px;background:#fffefb;min-height:132px;color:#473a2a;box-shadow:0 5px 18px #88735b0d}
.ul-action:hover{background:#f4ecdf;border-color:#bc9d78;transform:translateY(-2px)}.ul-action-icon{display:grid;place-items:center;width:36px;height:36px;border-radius:11px;background:#f2e7d7;font-size:24px;font-weight:600;color:#79603d}
.ul-action strong{font-size:14px}.ul-action small{font-size:11px;color:var(--muted)}
.ul-stats{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 16px}.ul-stats span{font-size:11px;border:1px solid #ebdfd0;background:#fbf8f3;border-radius:9px;padding:8px 12px;color:#8a7967}.ul-stats strong{font-size:14px;color:#56442f;margin-right:3px}
.ul-workgrid{display:grid;grid-template-columns:minmax(270px,36%) minmax(0,1fr);gap:15px;align-items:start}
.ul-panel{min-width:0;border:1px solid #e8ddcf;background:#fffefa;border-radius:17px;padding:17px;box-shadow:0 8px 23px #65553d0a}
.ul-list-panel{position:sticky;top:10px}.ul-panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px}.ul-panel h2{font-size:18px;margin:0;font-weight:800}.ul-panel-head span{font-size:11px;color:var(--muted)}
.ul-search{display:flex;gap:7px;margin-bottom:12px}.ul-search input{flex:1;width:0;min-width:0;border:1px solid #ded2c3;border-radius:10px;padding:10px 11px;background:white;font-size:12px}.ul-search button{min-height:40px}
.ul-devices{max-height:66vh;overflow-y:auto;display:grid;gap:7px}.ul-device{display:flex;align-items:center;gap:10px;width:100%;min-height:78px;text-align:left;border:1px solid #efe4d8;background:#fff;padding:11px;border-radius:11px;color:var(--ink)}
.ul-device:hover,.ul-device.active{border-color:#c9ad84;background:#f8f2e8}.ul-device-symbol{flex:none;background:#efe7dc;border-radius:9px;width:35px;height:35px;display:grid;place-items:center;color:#8a6a41;font-size:17px}
.ul-device-main{display:grid;gap:4px;min-width:0;flex:1}.ul-device-main strong{font-size:11px;line-height:1.35}.ul-device-main small{color:#928675;font-family:monospace;font-size:10px;overflow-wrap:anywhere}.ul-device-main em{font-size:10px;font-style:normal;color:#aa7a3e;font-weight:750}.ul-device-main em.is-ready{color:#257347}.ul-right-arrow{color:#ac9882;font-size:20px}
.ul-add-bottom{margin-top:14px;width:100%;padding:12px;border:1px dashed #b6a07f;border-radius:11px;color:#725535;background:#fcf9f4;font-size:12px;font-weight:750}
.ul-detail-panel{min-height:520px}.ul-detail-title{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.ul-detail-title h2{font-size:19px;margin:0 0 6px}.ul-detail-title p{font-size:11px;color:var(--muted);margin:0;overflow-wrap:anywhere}
.ul-pill{flex:none;border-radius:8px;padding:7px 9px;background:#f6e9d8;color:#a06d30;font-size:10px;font-weight:750}.ul-pill.green{background:#e2f2e6;color:#297449}
.ul-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:18px 0}.ul-facts>div{background:#f9f6f0;border:1px solid #efe5d9;border-radius:10px;padding:11px;min-width:0}.ul-facts small{display:block;color:#9a8871;font-size:10px;margin-bottom:5px}.ul-facts strong{font-size:11px;overflow-wrap:anywhere}
.ul-detail-tabs{display:flex;gap:4px;overflow:auto;border-bottom:1px solid #e9dfd1;margin:8px 0 16px}.ul-detail-tabs button{flex:none;border:0;border-bottom:2px solid transparent;background:none;padding:12px 13px;font-size:12px;font-weight:760;color:#8d7962}.ul-detail-tabs button.active{color:#674a2e;border-color:#a17b51}
.ul-panel-content{min-height:170px}.ul-panel-content h3{font-size:15px;margin:4px 0 15px}.ul-step{display:flex;align-items:center;gap:12px;border-bottom:1px solid #f1e9e0;padding:15px 0}.ul-step>span{width:28px;height:28px;border-radius:50%;background:#f2e8d8;display:grid;place-items:center;color:#866941;font-weight:750;font-size:13px;flex:none}.ul-step div{flex:1}.ul-step strong{font-size:12px}.ul-step p{font-size:11px;color:var(--muted);margin:5px 0 0}.ul-step>b{font-size:11px;color:#63836a}
.ul-callout{background:#fff4df;border:1px solid #e7d6b8;border-radius:12px;padding:13px;margin:14px 0;display:flex;align-items:center;justify-content:space-between;gap:11px;flex-wrap:wrap;font-size:12px;color:#7a5a2c}.ul-callout p{font-size:11px;margin:5px 0}.ul-explain{color:#998873;font-size:11px;line-height:1.6;margin:12px 0}.ul-section-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px}.ul-section-head span{font-size:10px;color:var(--muted)}
.ul-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.ul-form label{display:flex;flex-direction:column;gap:6px;font-size:11px;color:#6f5b40;font-weight:700}.ul-form input,.ul-form select,.ul-form textarea,.ul-customer-bar input{background:white;border:1px solid #ded1c1;border-radius:10px;padding:10px 12px;min-height:41px;width:100%;min-width:0;color:#463c31;font-size:12px;font-family:inherit}.ul-form textarea{resize:vertical}.ul-wide{grid-column:1/-1}.ul-form-actions{display:flex;justify-content:flex-end;gap:9px}.ul-form-actions button{min-height:41px}.ul-history-heading{margin:23px 0 8px;font-size:13px}.ul-history{padding:12px;background:#f9f5ef;border-radius:10px;margin:8px 0;font-size:11px;overflow-wrap:anywhere}.ul-history small{color:#907f6c}.ul-history p{line-height:1.5;color:#5a4a36}
.ul-customer-bar{display:flex;gap:8px}.ul-customer-bar button{white-space:nowrap}.ul-customer-results{background:#fff;border:1px solid #e8d8c4;border-radius:10px;margin-top:6px;max-height:180px;overflow:auto}.ul-customer-results button{display:flex;align-items:center;justify-content:space-between;text-align:left;gap:10px;width:100%;padding:11px;border-bottom:1px solid #f2ece4;color:#57452f}.ul-customer-results button:hover{background:#f7efe4}.ul-customer-results small{color:#9a8a77}.ul-selected{color:#267443;font-size:11px;margin:8px 0}.ul-price-info{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:4px 9px;padding:8px;font-size:11px}.ul-price-info small{color:#96826c}.ul-price-info strong{overflow-wrap:anywhere}
.ul-quote{border:1px solid #e3cdaa;background:#fbf4e7;border-radius:13px;padding:18px;margin:20px 0}.ul-quote>div{display:flex;justify-content:space-between;padding:5px 0;font-size:12px}.ul-quote-total{margin-top:10px;padding-top:12px!important;border-top:1px solid #e1d0b6;font-size:17px!important;font-weight:800}.ul-quote button{width:100%;margin-top:16px}.ul-sale-complete{background:#e5f5e9;color:#2e784c;border-radius:12px;padding:15px;margin:10px 0}.ul-sale-complete p{font-size:12px}.ul-confirm-total{font-size:20px!important;font-weight:800}.ul-empty{text-align:center;padding:30px 15px;color:#7d6c57}.ul-empty strong{font-size:15px}.ul-empty p{font-size:11px;line-height:1.6}.ul-big-empty{padding:85px 20px}.ul-modal{max-width:540px}.ul-top-modal{z-index:270}
.ul-print-paper{display:none}
@media(max-width:920px){.ul-workgrid{grid-template-columns:1fr}.ul-list-panel{position:static}.ul-devices{max-height:340px}.ul-quick{gap:8px}}
@media(max-width:600px){.ul-quick{grid-template-columns:1fr}.ul-action{min-height:75px;display:grid;grid-template-columns:36px 1fr;column-gap:9px;padding:12px}.ul-action small{grid-column:2}.ul-stats{gap:6px}.ul-stats span{padding:7px}.ul-facts{gap:6px}.ul-form{grid-template-columns:1fr}.ul-customer-bar{flex-wrap:wrap}.ul-customer-bar button{width:100%}}
</style>
<style>
@media print {
  body.sos-ul-print-mode * { visibility: hidden !important; }
  body.sos-ul-print-mode #ul-print-receipt,
  body.sos-ul-print-mode #ul-print-receipt * { visibility: visible !important; }
  body.sos-ul-print-mode #ul-print-receipt { display:block!important;position:fixed;top:0;left:0;width:80mm;max-width:80mm;padding:6mm;background:#fff;color:#000;font-family:Arial,sans-serif;font-size:11px;line-height:1.6;z-index:9999; }
  body.sos-ul-print-mode #ul-print-receipt h2 {font-size:14px;text-align:center;margin:0 0 6px;}
  body.sos-ul-print-mode #ul-print-receipt>p:first-of-type{text-align:center;letter-spacing:1px;font-size:10px}
  body.sos-ul-print-mode #ul-print-receipt .ul-print-total{display:flex;justify-content:space-between;margin:16px 0;font-size:16px;font-weight:bold}
  @page {margin:0;size:80mm auto;}
}
</style>


<style scoped>
/* SOS_UL_INSPECTION_LABELS_631: inspection is not automatically a repair. */
.sos-ul-workspace .ul-631-inspection-note {
  border:1px solid #cddfd7; background:#f2faf6; color:#254d40;
  border-radius:12px; padding:13px 15px; margin:12px 0;
  display:grid; gap:6px; font-size:12px; line-height:1.55;
}
.sos-ul-workspace .ul-631-inspection-note strong {font-weight:800;font-size:13px;}
.sos-ul-workspace .ul-631-explain {border-left:3px solid #86a99c;padding:9px 12px;background:#f4faf7;color:#37594f;border-radius:5px;font-size:12px;line-height:1.55;}
.sos-ul-workspace .ul-device-main em {line-height:1.3;white-space:normal;}
.sos-ul-workspace .ul-pill {white-space:normal;text-align:center;max-width:170px;line-height:1.4;}
</style>

<style>
/* SOS_IVORY_STOCK_633 — right detail card padding + real inventory facts. */
.sos-ul-workspace {--sos633-bg:#F8F5EE;--sos633-paper:#FFFCF7;--sos633-ink:#35291F;--sos633-border:#E5D9C8;--sos633-accent:#755536;}
.sos-ul-workspace .ul-workgrid {gap:18px!important;align-items:start!important;}
.sos-ul-workspace .ul-panel {background:var(--sos633-paper)!important;border:1px solid var(--sos633-border)!important;box-shadow:0 7px 24px #5940260a!important;box-sizing:border-box!important;}
.sos-ul-workspace .ul-detail-panel {padding:25px 27px 29px!important;min-width:0!important;}
.sos-ul-workspace .ul-detail-panel > .ul-empty {padding:70px 22px!important;}
.sos-ul-workspace .ul-detail-title {padding:3px 2px 17px!important;margin:0 0 7px!important;border-bottom:1px solid #E9DDCA!important;gap:15px!important;}
.sos-ul-workspace .ul-detail-title > div {min-width:0!important;}
.sos-ul-workspace .ul-detail-title h2 {color:var(--sos633-ink)!important;line-height:1.32!important;overflow-wrap:anywhere!important;}
.sos-ul-workspace .ul-detail-tabs {margin:18px 0 13px!important;padding:0 0 2px!important;}
.sos-ul-workspace .ul-detail-tabs button {min-height:45px!important;padding:11px 14px!important;color:#7A654E!important;}
.sos-ul-workspace .ul-detail-tabs button.active {color:var(--sos633-accent)!important;border-color:var(--sos633-accent)!important;}
.sos-ul-workspace .ul-panel-content {box-sizing:border-box!important;min-width:0!important;padding:14px 5px 17px!important;}
.sos-ul-workspace .ul-panel-content .ul-form {min-width:0!important;gap:14px!important;}
.sos-ul-workspace .ul-facts {margin:17px 0!important;gap:11px!important;}
.sos-ul-workspace .ul-facts > div {background:#F9F1E7!important;border:1px solid #EADDCB!important;padding:14px!important;min-width:0!important;}
.sos-ul-workspace .ul-step {padding:17px 3px!important;}
.sos-ul-workspace .ul-callout {padding:16px!important;}
.sos-ul-workspace .ul-next-area {margin:15px 0!important;padding:14px 16px!important;border:1px solid #E5D4BE!important;background:#F6ECDD!important;}
.sos-ul-workspace .ul-pill {background:#F1E2CE!important;color:#77512E!important;max-width:min(190px,45%)!important;}
.sos-ul-workspace .ul-pill.green {background:#E8F1E6!important;color:#446447!important;}
.sos-ul-workspace .ul-action {background:#FFFCF7!important;color:var(--sos633-ink)!important;border-color:#E4D7C4!important;}
.sos-ul-workspace .ul-action:hover {background:#F7EDE0!important;border-color:#C9AD89!important;}
.sos-ul-workspace .ul-action-icon {background:#F1E4D1!important;color:var(--sos633-accent)!important;}
.sos-ul-workspace .ul-device.active {background:#F6EADD!important;border-color:#BD9C70!important;}
.sos-ul-workspace .ul-631-inspection-note {background:#F9F0E2!important;color:#624B32!important;border-color:#E6D5BC!important;}
.sos-ul-workspace .ul-631-explain {background:#F7EEE1!important;color:#624B32!important;border-left-color:#B4936D!important;}
.sos-ul-workspace .sos633-stock-truth {
  display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;
  margin:17px 0 4px;padding:14px;background:#F7EFE3;
  border:1px solid #E7D9C5;border-radius:13px;
}
.sos-ul-workspace .sos633-stock-truth > div {display:grid;gap:6px;min-width:0;padding:3px 5px;}
.sos-ul-workspace .sos633-stock-truth span {color:#82715D;font-size:11px;font-weight:700;}
.sos-ul-workspace .sos633-stock-truth strong {color:#433326;font-size:13px;overflow-wrap:anywhere;}
.sos-ul-workspace .sos633-stock-truth strong.sos633-bad {color:#A63C26;}
.sos-ul-workspace .sos633-stock-message {grid-column:1/-1;border-top:1px solid #E4D5C0;margin:0;padding:11px 5px 0;color:#735A3C;font-size:11px;line-height:1.55;}
@media(max-width:800px){
  .sos-ul-workspace .ul-detail-panel{padding:18px 16px 22px!important;}
  .sos-ul-workspace .sos633-stock-truth{grid-template-columns:1fr 1fr;}
}
@media(max-width:500px){
  .sos-ul-workspace .ul-detail-panel{padding:15px 12px 19px!important;}
  .sos-ul-workspace .sos633-stock-truth{grid-template-columns:1fr;}
  .sos-ul-workspace .ul-panel-content{padding:13px 2px!important;}
}
</style>
