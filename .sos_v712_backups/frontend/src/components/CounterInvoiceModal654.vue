<script setup>
import CounterCheckout670 from './CounterCheckout670.vue'
const completed670 = ref(null)
// SOS_FINAL_INVOICE_709
const finalizing709 = ref(false)
const finalized709 = ref(null)
async function finalize709() {
  if (!saved.value?.invoice || kind.value !== 'service' || finalizing709.value || finalized709.value) return
  finalizing709.value=true; error.value=''
  try {
    const body={job_name:sos690LockedServiceJob.value || selectedJob.value,invoice_name:saved.value.invoice}
    const response=await fetch('/api/method/servicing_os.api.invoice_final_709.finalize_service_invoice',{
      method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.frappe?.csrf_token || window.csrf_token || decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'')},
      body:JSON.stringify(body)
    })
    const data=await response.json()
    if(!response.ok || data.exc || data.exc_type) throw new Error(data.message?.message || data._server_messages || data.exception || 'Cannot finalize invoice')
    if(data.message?.docstatus!==1) throw new Error('Invoice was not submitted')
    finalized709.value=data.message
    completed670.value={invoice:saved.value.invoice}
    window.dispatchEvent(new CustomEvent('servicing-os-invoice-finalized',{detail:data.message}))
  } catch(e) {error.value=e?.message || 'Cannot finalize invoice. Draft remains available.'}
  finally {finalizing709.value=false}
}


import UnifiedInvoicePrint684 from './UnifiedInvoicePrint684.vue'
const sos657Preview = ref('')
import { computed, onMounted, ref, unref, watch, onUnmounted } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
const props = defineProps({ initialKind: {type:String, default:'retail'}, initialJob: {type:String, default:''} })
const emit = defineEmits(['saved'])
const bn = computed(()=>String(unref(currentLanguage)||'en').toLowerCase().startsWith('bn'))
// SOS_SERVICE_WORKFLOW_690: lock the floating action to the exact selected Service Job.
const sos690LockedServiceJob = computed(() => String(props.initialJob || '').trim())
const kind = ref(['retail','used','service'].includes(props.initialKind) ? props.initialKind:'retail')
const setup = ref(null), loading = ref(true), saving=ref(false), error=ref(''), saved=ref(null)
const customerText=ref(''), customerId=ref(''), customerSuggestions=ref([]), customerFocus=ref(false)
const selectedJob=ref(''), jobList=ref([]), remarks=ref(''), discountMode=ref('none'), discountValue=ref(0)
const rows=ref([{item_code:'',qty:1,rate:'',discount_percentage:0,serial_no:''}])

// SERVICING_OS_WARRANTY_672: fetch and require an explicit warranty for each line.
const sos672WarrantyCache = new Map()
let sos672WarrantyTicket = 0
async function sos672ResolveModalWarranty(row) {
  if (!row?.item_code) return
  const code=String(row.item_code).trim()
  const ticket=++sos672WarrantyTicket
  row.sos672WarrantyCode=code
  row.sos672WarrantyPending=true
  row.sos672WarrantyError=''
  try {
    let days = sos672WarrantyCache.get(code)
    if (days === undefined) {
      const url = new URL('/api/method/servicing_os.api.item_warranty_671.get_item_warranties', location.origin)
      url.searchParams.set('items',JSON.stringify([code]))
      const response=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
      const data=await response.json()
      if(!response.ok||data.exc||data.exception) throw new Error('Warranty lookup unavailable')
      days=Number(data.message?.items?.[0]?.warranty_period_days||0)
      sos672WarrantyCache.set(code,days)
    }
    if (!rows.value.includes(row)||row.item_code!==code) return
    if (days>0) {row.sos672WarrantyDays=days;row.sos672WarrantySource='item_master'}
    else if (!row.sos672WarrantySelected) {row.sos672WarrantyDays='';row.sos672WarrantySource='manual'}
  } catch(e) {
    if(rows.value.includes(row)&&row.item_code===code) row.sos672WarrantyError=e?.message||'Warranty lookup failed'
  } finally {
    if(rows.value.includes(row)&&row.item_code===code) row.sos672WarrantyPending=false
  }
}
function sos672WarrantyEdited(row) {
  if(row.sos672WarrantySource==='item_master')return
  row.sos672WarrantySource='manual';row.sos672WarrantySelected=true;row.sos672WarrantyError=''
}
function sos672NoWarranty(row) {
  if(row.sos672WarrantySource==='item_master')return
  row.sos672WarrantyDays=0;row.sos672WarrantySource='none';row.sos672WarrantySelected=true;row.sos672WarrantyError=''
}
function sos672ModalWarrantyValid(row) {
  if(row.sos672WarrantyPending||row.sos672WarrantyError)return false
  const n=Number(row.sos672WarrantyDays)
  return row.sos672WarrantySource==='none'||((row.sos672WarrantySource==='item_master'||row.sos672WarrantySource==='manual')&&Number.isInteger(n)&&n>0&&n<=36500)
}
// Also resolves manually entered Item Codes when staff do not pick a suggestion.
let sos672ModalTimer
watch(()=>rows.value.map(r=>r.item_code).join('|'),()=>{
  clearTimeout(sos672ModalTimer)
  sos672ModalTimer=setTimeout(()=>rows.value.forEach(r=>{
    if(r.item_code!==r.sos672WarrantyCode){r.sos672WarrantySelected=false;r.sos672WarrantyDays='';r.sos672WarrantySource='';r.sos672WarrantyCode=r.item_code}
    if(r.item_code && !r.sos672WarrantySelected)sos672ResolveModalWarranty(r)
  }),420)
})

const matches=ref([]), activeItem=ref(-1), itemBusy=ref(false), suggestFocused=ref(false)
let customerTimer, itemTimer, customerSeq=0, itemSeq=0
const currentJob=computed(()=>jobList.value.find(j=>j.name===selectedJob.value))
const money=v=>Number(v||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const lineTotal=row=>Math.round(Math.max(0,Number(row.qty)||0)*Math.max(0,Number(row.rate)||0)*(1-Math.min(100,Math.max(0,Number(row.discount_percentage)||0))/100)*100)/100
const subtotal=computed(()=>rows.value.reduce((s,r)=>s+lineTotal(r),0))
const overall=computed(()=>discountMode.value==='percent'?subtotal.value*Math.max(0,Math.min(100,Number(discountValue.value)||0))/100:discountMode.value==='amount'?Math.min(subtotal.value,Math.max(0,Number(discountValue.value)||0)):0)
const estimate=computed(()=>Math.max(0,subtotal.value-overall.value))
const kindName={retail:'New Sale',used:'Used Laptop Sale',service:'Service Job'}
function resetOnKind(){
  saved.value=null;error.value='';customerId.value='';customerText.value='';selectedJob.value='';rows.value=[{item_code:'',qty:1,rate:'',discount_percentage:0,serial_no:''}]
  matches.value=[];activeItem.value=-1;discountMode.value='none';discountValue.value=0
}
function errorText(data,fallback){try{let m=JSON.parse(data?._server_messages||'[]');if(m.length)return String(JSON.parse(m[0]).message||fallback).replace(/<[^>]+>/g,'')}catch(_){}return data?.message||fallback}
async function api(name,{method='GET',params={},body=null}={}){
  const url=new URL('/api/method/servicing_os.api.counter_invoice_654.'+name,location.origin)
  for(const [key,val] of Object.entries(params)) url.searchParams.set(key,String(val))
  const token=window.frappe?.csrf_token||window.csrf_token||document.querySelector('meta[name="csrf-token"]')?.content||''
  const res=await fetch(url,{method,credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(token?{'X-Frappe-CSRF-Token':token}:{})},...(body?{body:JSON.stringify(body)}:{})})
  let data;try{data=await res.json()}catch(_){throw new Error('Unexpected invoice API response: HTTP '+res.status)}
  if(!res.ok||data.exc||data.exception)throw new Error(errorText(data,'Invoice request failed'))
  return data.message||{}
}

// SERVICING_OS_SERVICE_INVOICE_662 — preselect exact Service Job and its linked Customer.
async function sos661SelectInitialJob() {
  const id = String(props.initialJob || '').trim()
  if (!id) return
  if (kind.value !== 'service') throw new Error('Requested job requires a Service Invoice.')
  if (!jobList.value.some(j => j.name === id)) {
    const url = new URL('/api/method/servicing_os.api.service_invoice_661.get_job_context', window.location.origin)
    url.searchParams.set('job_name', id)
    const response = await fetch(url, {method:'GET', credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'}})
    const payload = await response.json()
    if (!response.ok || payload.exc || payload.exception || !payload.message?.name) {
      throw new Error(typeof payload.message === 'string' ? payload.message : 'Could not load selected Service Job.')
    }
    jobList.value.unshift(payload.message)
  }
  selectedJob.value = id
  selectJob()
}

async function load(){loading.value=true;error.value='';try{setup.value=await api('get_invoice_setup');jobList.value=setup.value.jobs||[];await sos661SelectInitialJob()}catch(e){error.value=e.message||'Cannot load invoice configuration'}finally{loading.value=false}}
onMounted(load)
function selectJob(){let j=currentJob.value;if(j){customerId.value=j.customer;customerText.value=j.customer_name||j.customer}}
function customerSearch(){clearTimeout(customerTimer);customerSuggestions.value=[];customerId.value='';if(!customerFocus.value||customerText.value.trim().length<1)return;const seq=++customerSeq;customerTimer=setTimeout(async()=>{try{const x=await api('search_invoice_customers',{params:{q:customerText.value}});if(seq===customerSeq)customerSuggestions.value=x.results||[]}catch(e){if(seq===customerSeq)error.value=e.message}},240)}
function chooseCustomer(c){customerId.value=c.name;customerText.value=c.customer_name||c.name;customerFocus.value=false;customerSuggestions.value=[]}
function onCustomerBlur(){setTimeout(()=>{customerFocus.value=false;customerSuggestions.value=[]},220)}
function itemSearch(i){clearTimeout(itemTimer);activeItem.value=i;matches.value=[];if(!suggestFocused.value||!rows.value[i]||!rows.value[i].item_code.trim())return;const seq=++itemSeq;itemTimer=setTimeout(async()=>{itemBusy.value=true;try{const x=await api('search_invoice_items',{params:{q:rows.value[i].item_code,invoice_kind:kind.value}});if(seq===itemSeq)matches.value=x.results||[]}catch(e){if(seq===itemSeq)error.value=e.message}finally{if(seq===itemSeq)itemBusy.value=false}},230)}
function focusItem(i){suggestFocused.value=true;itemSearch(i)}
function onItemBlur(){setTimeout(()=>{suggestFocused.value=false;matches.value=[];activeItem.value=-1},250)}

// SERVICING_OS_AUTO_SELLING_PRICE_660: Invoice rate from Item Price.
async function sos660ModalPrice(code) {
  const url = new URL('/api/method/servicing_os.api.counter_selling_price_660.get_selling_price', window.location.origin)
  url.searchParams.set('item_code', String(code))
  const resp = await fetch(url,{method:'GET',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
  const data = await resp.json()
  if (!resp.ok || data.exc || data.exception) throw new Error(errorText(data,'Selling price lookup failed'))
  if (!data.message?.found || data.message.rate === null || data.message.rate === undefined) throw new Error(data.message?.message||'Selling price missing')
  return data.message
}

async function chooseItem(i,it){
  const row=rows.value[i]
  row.item_code=it.name;row.has_serial_no=!!it.has_serial_no;row.stock_qty=it.stock_qty;row.sos672WarrantySelected=false;row.sos672WarrantyDays='';row.sos672WarrantySource='';sos672ResolveModalWarranty(row)
  row.rate='';row.priceLoading=true;row.priceError='';row.priceList=''
  matches.value=[];activeItem.value=-1;suggestFocused.value=false
  try{
    const value=await sos660ModalPrice(it.name)
    if(rows.value[i]!==row||row.item_code!==it.name)return
    row.rate=Number(value.rate);row.priceList=value.price_list
  }catch(e){if(rows.value.includes(row)){
    row.priceError=e?.message||'Selling price unavailable';error.value=row.priceError
  }}finally{row.priceLoading=false}
}
function addItem(){if(rows.value.length<35)rows.value.push({item_code:'',qty:1,rate:'',discount_percentage:0,serial_no:''})}
function removeItem(i){if(rows.value.length>1)rows.value.splice(i,1)}
function reset(){saved.value=null;finalized709.value=null;resetOnKind();load()}
watch(kind,resetOnKind)
onUnmounted(()=>{clearTimeout(customerTimer);clearTimeout(itemTimer);customerSeq++;itemSeq++})
async function save(){
  if(saving.value||saved.value)return
  error.value=''
  if(sos690LockedServiceJob.value && (kind.value!=='service'||selectedJob.value!==sos690LockedServiceJob.value)){error.value='This invoice must belong to '+sos690LockedServiceJob.value;return}
  if(kind.value==='service'&&!selectedJob.value){error.value='Choose a saved Service Job.';return}
  if(kind.value!=='service'&&!customerId.value){error.value='Choose a Customer from the search suggestions.';return}
  if(rows.value.some(r=>!r.item_code||r.rate===''||r.priceLoading||r.priceError||!(Number(r.qty)>0)||Number(r.rate)<0||Number(r.discount_percentage)<0||Number(r.discount_percentage)>100)){
    error.value='Complete all item codes, quantities, rates and line discounts.';return
  }
  if(!Number.isFinite(Number(discountValue.value))||Number(discountValue.value)<0||(discountMode.value==='percent'&&Number(discountValue.value)>=100)||(discountMode.value==='amount'&&Number(discountValue.value)>=subtotal.value)){
    error.value='Invalid overall discount.';return
  }
  if(estimate.value<=0){error.value='Invoice must have a positive total.';return}
  if(rows.value.some(r=>r.item_code&&!sos672ModalWarrantyValid(r))){error.value='Enter warranty days for every item without an Item Master warranty, or select No warranty.';return}
  saving.value=true
  try{
    const d=await api('create_unified_invoice_draft',{method:'POST',body:{invoice_kind:kind.value,customer:customerId.value,job_name:sos690LockedServiceJob.value||selectedJob.value,items:rows.value.map(r=>({item_code:r.item_code,qty:r.qty,rate:r.rate,discount_percentage:r.discount_percentage,serial_no:r.serial_no,warranty_choice:r.sos672WarrantySource||'',warranty_period_days:r.sos672WarrantySource==='none'?0:Number(r.sos672WarrantyDays||0)})),discount_mode:discountMode.value,discount_value:discountMode.value==='none'?0:Number(discountValue.value),remarks:remarks.value}})
    if(!d.invoice)throw new Error('Invoice was not returned by backend')
    saved.value=d;emit('saved',d);window.dispatchEvent(new CustomEvent('servicing-os-invoice-draft-created',{detail:d}))
    if(kind.value==='service') await finalize709()
  }catch(e){error.value=e.message||'Unable to save invoice'}finally{saving.value=false}
}
</script>
<template>
  <div class="sos654-invoice">
    <p v-if="loading" class="sos654-info">Loading shop, customers and invoice settings…</p>
    <div v-else-if="saved" class="sos654-success" role="status">
      <p v-if="error" class="sos654-error" role="alert">{{error}}</p>
      <strong>{{ completed670?.invoice===saved?.invoice ? "Invoice Submitted" : "Draft Invoice Saved" }}</strong><h2>{{ saved.invoice }}</h2>
      <p>{{ kindName[saved.invoice_kind] }} · {{ saved.customer }} · {{ saved.currency }} {{ money(saved.grand_total) }}</p>
      <p v-if="completed670?.invoice!==saved?.invoice">Invoice saved as Draft. If finalization failed, resolve the error and retry below. Stock is not deducted by the invoice.</p><p v-else>ERPNext submitted the invoice. You can print it below.</p>
      <button v-if="kind!=='service' || finalized709" type="button" @click="sos657Preview=saved.invoice">Print Final Invoice</button><button v-if="kind==='service' && !finalized709" type="button" :disabled="finalizing709" @click="finalize709">{{finalizing709?'Submitting…':'Retry Save Final Invoice'}}</button><button type="button" @click="reset">Create another invoice</button>
    </div>
    <form v-else @submit.prevent="save">
      <div class="sos654-kind" role="group" aria-label="Invoice type">
        <button v-for="(name,key) in kindName" :key="key" type="button" :class="{'selected':kind===key}" @click="kind=key" :disabled="!!sos690LockedServiceJob && key!=='service'">{{ name }}</button>
      </div>
      <div class="sos654-fields">
        <label v-if="kind==='service'"><span>Service Job *</span>
          <input v-model.trim="selectedJob" list="sos654-jobs" autocomplete="off" placeholder="Select saved job" @change="selectJob" :readonly="!!sos690LockedServiceJob" />
          <datalist id="sos654-jobs"><option v-for="j in jobList" :key="j.name" :value="j.name">{{ j.customer_name }}</option></datalist>
          <small v-if="currentJob">{{ currentJob.customer_name }} · {{ currentJob.status }}</small>
        </label>
        <label v-else class="sos654-search-field"><span>Customer *</span>
          <input v-model="customerText" autocomplete="off" placeholder="Click to search existing customers" @focus="customerFocus=true;customerSearch()" @input="customerSearch" @blur="onCustomerBlur" />
          <div v-if="customerFocus&&customerSuggestions.length" class="sos654-suggest" role="listbox">
            <button v-for="c in customerSuggestions" :key="c.name" type="button" @mousedown.prevent="chooseCustomer(c)">{{ c.customer_name }} <small>{{ c.name }}</small></button>
          </div>
          <small v-if="customerId">Selected: {{ customerId }}</small>
        </label>
        <label><span>Company</span><input :value="setup?.company||''" readonly /></label>
        <label><span>Warehouse</span><input :value="kind==='service'?'Non-stock service':kind==='used'?setup?.used_laptop_warehouse:setup?.retail_warehouse" readonly /></label>
        <label><span>Remarks (optional)</span><input v-model="remarks" maxlength="360" placeholder="Customer reference / notes" /></label>
      </div>
      <div class="sos654-heading"><div><strong>Invoice Items</strong><small>Search existing items; select matching Item Code</small></div><button type="button" :disabled="rows.length>=35" @click="addItem">+ Add Item</button></div>
      <div class="sos654-lines">
        <div v-for="(row,i) in rows" :key="i" class="sos654-line">
          <label class="sos654-search-field"><span>Item Code *</span>
            <input v-model="row.item_code" autocomplete="off" placeholder="Click, then type Item Code" @focus="focusItem(i)" @input="itemSearch(i)" @blur="onItemBlur" />
            <div v-if="activeItem===i&&suggestFocused" class="sos654-suggest" role="listbox">
              <p v-if="itemBusy">Searching…</p>
              <button v-for="it in matches" :key="it.name" type="button" @mousedown.prevent="chooseItem(i,it)">{{ it.item_name }} <small>{{ it.name }} <template v-if="it.stock_qty!==null&&it.stock_qty!==undefined">· Stock: {{ it.stock_qty }}</template></small></button>
            </div>
          </label>
          <label><span>Qty</span><input v-model.number="row.qty" type="number" min="0.01" step="0.01" /></label>
          <label><span>Unit Selling Price (BDT)</span><input :value="row.rate" type="number" min="0" step="0.01" readonly title="Selling Price List rate, discount separately" />
           <small v-if="row.priceLoading">Fetching selling price…</small><small v-else-if="row.priceError" class="sos660-modal-error">{{ row.priceError }}</small><small v-else-if="row.priceList">{{ row.priceList }}</small>
         </label>
          <label><span>Disc. %</span><input v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.01" /></label>
          <label class="sos672-modal-warranty"><span>Warranty (Days)</span>
            <input v-model.number="row.sos672WarrantyDays" type="number" min="1" max="36500" step="1"
              :readonly="row.sos672WarrantySource==='item_master'"
              :disabled="row.sos672WarrantyPending" placeholder="Enter days" @input="sos672WarrantyEdited(row)" />
            <small v-if="row.sos672WarrantySource==='item_master'">ERPNext Item Master</small>
            <small v-else-if="row.sos672WarrantyPending">Checking warranty…</small>
            <small v-else-if="row.sos672WarrantyError">{{ row.sos672WarrantyError }}</small>
            <small v-else>Manual warranty days</small>
            <button v-if="row.sos672WarrantySource!=='item_master'&&!row.sos672WarrantyPending"
              type="button" class="sos672-none-button" @click="sos672NoWarranty(row)">No warranty</button>
          </label>
          <label v-if="kind==='used'||row.has_serial_no" class="sos654-serial"><span>Serial Number(s)</span><input v-model.trim="row.serial_no" placeholder="For serialized items, one per unit" /></label>
          <div class="sos654-lineamount"><small>Line</small><strong>৳ {{ money(lineTotal(row)) }}</strong></div>
          <button type="button" class="sos654-remove" aria-label="Remove invoice item" :disabled="rows.length<2" @click="removeItem(i)">×</button>
        </div>
      </div>
      <div class="sos654-bottom">
        <div class="sos654-discount">
          <label><span>Overall Discount</span><select v-model="discountMode" @change="discountValue=0"><option value="none">No additional discount</option><option value="percent">Percentage (%)</option><option value="amount">Fixed amount (BDT)</option></select></label>
          <label v-if="discountMode!=='none'"><span>{{ discountMode==='percent'?'Discount %':'Discount BDT' }}</span><input v-model.number="discountValue" type="number" min="0" :max="discountMode==='percent'?99.99:undefined" step="0.01" /></label>
        </div>
        <div class="sos654-totals">
          <div><span>Subtotal after line discount</span><strong>৳ {{ money(subtotal) }}</strong></div>
          <div><span>Additional discount</span><strong>− ৳ {{ money(overall) }}</strong></div>
          <div class="total"><span>Estimated before taxes</span><strong>৳ {{ money(estimate) }}</strong></div>
        </div>
      </div>
      <p class="sos654-info">{{kind==='service'?'Final Service Invoice: submits the Sales Invoice and any approved, unissued parts requests. Draft parts requests require approval. No duplicate stock issue or automatic payment.':'Creates a Draft Sales Invoice; checkout handles final submission.'}}</p>
      <p v-if="error" class="sos654-error" role="alert">{{ error }}</p>
      <div class="sos654-footer"><button type="button" @click="load">Refresh</button><button type="submit" class="primary" :disabled="saving||loading">{{ saving?'Saving…':kind==='service'?'Save Final Invoice':'Review & Continue to Checkout' }}</button></div>
    </form>
    <p v-if="error&&loading" class="sos654-error">{{ error }}</p>
    <UnifiedInvoicePrint684 v-if="sos657Preview" :invoice-name="sos657Preview" @close="sos657Preview=''" />

    <!-- SERVICING_OS_670: draft edit / payment / delivery / receipt -->
    <CounterCheckout670 v-if="saved?.invoice && kind!=='service'" :invoice-name="saved.invoice" @completed="completed670=$event" />
  </div>
</template>
<style>
.sos654-invoice,.sos654-invoice *{box-sizing:border-box}.sos654-invoice{font-size:12px;color:#3c2c25}
.sos654-kind{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:16px}
.sos654-invoice button{cursor:pointer}.sos654-kind button{border:1px solid #e3ceba!important;border-radius:11px;background:#fffcf7!important;padding:12px 9px!important;color:#805d45!important;font-weight:750!important;font-size:12px!important}
.sos654-kind button.selected{background:#805a3e!important;border-color:#805a3e!important;color:white!important}
.sos654-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:18px}
.sos654-invoice label{display:flex;flex-direction:column;gap:5px;min-width:0;color:#634633;font-size:11px;font-weight:700}
.sos654-invoice label>span{display:block}.sos654-invoice input,.sos654-invoice select{width:100%;min-height:40px;border:1px solid #ddc8b5!important;border-radius:9px!important;background:#fffcf7!important;padding:8px 10px!important;color:#3c2c25!important;font:inherit!important;font-size:12px!important}
.sos654-invoice input:focus{outline:2px solid #bd9274!important;outline-offset:1px}.sos654-invoice input[readonly]{background:#f3e8dd!important}
.sos654-invoice label small{font-size:10px;color:#987864}.sos654-search-field{position:relative}
.sos654-suggest{position:absolute;top:calc(100% - 2px);left:0;right:0;z-index:80;max-height:235px;overflow:auto;background:#fffefb;border:1px solid #d9bfa5;border-radius:9px;box-shadow:0 12px 25px #48332022}
.sos654-suggest button{display:block;width:100%;text-align:left;padding:10px!important;border:0!important;border-bottom:1px solid #efe3d8!important;color:#4a3729!important;background:#fffefa!important;font-size:12px!important}.sos654-suggest button:hover{background:#f4e3d3!important}.sos654-suggest small{display:block}.sos654-suggest p{margin:0;padding:12px;color:#8b725e}
.sos654-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px}.sos654-heading strong{font-size:15px}.sos654-heading small{display:block;color:#8b725e;margin-top:3px}
.sos654-heading button,.sos654-footer button,.sos654-success button{border:1px solid #e3ceba!important;background:#f4e3d3!important;color:#684832!important;padding:9px 12px!important;border-radius:9px!important;font-size:12px!important;font-weight:700!important}
.sos654-lines{display:grid;gap:9px}.sos654-line{display:grid;grid-template-columns:minmax(150px,3fr) minmax(60px,.7fr) minmax(90px,1fr) minmax(75px,.8fr) minmax(90px,1fr) 30px;gap:9px;padding:11px;border:1px solid #e7d6c5;border-radius:11px;background:#fffdf9;align-items:end}
.sos654-serial{grid-column:1/-1}.sos654-lineamount{display:grid;gap:4px;min-height:40px}.sos654-lineamount small{font-size:10px;color:#8b725e}.sos654-lineamount strong{white-space:nowrap}.sos654-remove{border:1px solid #eccfbe!important;border-radius:9px!important;background:#fff0e8!important;color:#a55e40!important;font-size:23px!important;min-height:40px!important}.sos654-remove:disabled{opacity:.4}
.sos654-bottom{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,1fr);gap:15px;margin-top:16px;padding:16px;border:1px solid #e7d6c5;background:#fffaf5;border-radius:11px}.sos654-discount{display:grid;grid-template-columns:1fr 1fr;gap:9px;align-content:start}.sos654-totals{display:grid;gap:11px}.sos654-totals>div{display:flex;justify-content:space-between;gap:8px}.sos654-totals .total{border-top:1px solid #e7d6c5;padding-top:10px;font-weight:800}.sos654-totals .total strong{font-size:17px}
.sos654-info{background:#f1e5d9;border-radius:9px;padding:10px 12px;margin-top:13px;color:#715641;line-height:1.45}.sos654-error{background:#fff1ec;color:#8e3a2b;border:1px solid #ecc7bb;padding:10px;border-radius:8px;margin-top:12px}.sos654-footer{display:flex;gap:10px;justify-content:flex-end;margin-top:15px}.sos654-footer button.primary,.sos654-success button{background:#805a3e!important;color:#fff!important;border-color:#805a3e!important}.sos654-success{text-align:center;padding:28px;background:#fffaf4;border:1px solid #e7d6c5;border-radius:11px}.sos654-success h2{font-weight:800;font-size:22px;margin:10px}.sos654-success p{color:#896b55;margin:10px}
@media(max-width:850px){.sos654-line{grid-template-columns:repeat(4,minmax(0,1fr))}.sos654-line .sos654-search-field{grid-column:1/-1}.sos654-lineamount{grid-column:1/3}.sos654-bottom{grid-template-columns:1fr}}
@media(max-width:560px){.sos654-fields,.sos654-discount{grid-template-columns:1fr}.sos654-line{grid-template-columns:1fr 1fr}.sos654-line .sos654-search-field{grid-column:1/-1}.sos654-lineamount{grid-column:1/-1}.sos654-footer button{flex:1}}
</style>

<!-- SERVICING_OS_COUNTER_657 -->

<style>
/* SERVICING_OS_AUTO_SELLING_PRICE_660 */
.sos654-invoice input[readonly]{background:#f5ebe2!important;color:#634633!important}
.sos654-invoice .sos660-modal-error{color:#9d412c!important;font-size:10px!important}
</style>

<style>
/* SERVICING_OS_WARRANTY_672 — explicit warranty controls on every modal row. */
.sos654-invoice .sos654-line{grid-template-columns:minmax(160px,2.6fr) minmax(65px,.7fr) minmax(92px,1fr) minmax(72px,.8fr) minmax(110px,1fr) minmax(90px,1fr) 34px!important;gap:8px!important}
.sos654-invoice .sos672-modal-warranty{min-width:0}
.sos654-invoice .sos672-modal-warranty input[readonly]{background:#f3e8dd!important}
.sos654-invoice .sos672-modal-warranty small{font-size:10px;line-height:1.3;color:#88674e}
.sos654-invoice .sos672-none-button{background:transparent!important;border:0!important;color:#805a3e!important;text-decoration:underline!important;font-size:10px!important;padding:2px!important;text-align:left}
@media(max-width:1200px){.sos654-invoice .sos654-line{grid-template-columns:repeat(4,minmax(0,1fr))!important}.sos654-invoice .sos654-line>.sos654-search-field{grid-column:1/-1}.sos654-invoice .sos654-line>.sos672-modal-warranty{grid-column:1/3}.sos654-invoice .sos654-line>.sos654-lineamount{grid-column:3/4}.sos654-invoice .sos654-line>.sos654-remove{grid-column:4}}
@media(max-width:550px){.sos654-invoice .sos654-line{grid-template-columns:repeat(2,minmax(0,1fr))!important}.sos654-invoice .sos654-line>.sos672-modal-warranty{grid-column:1/3}.sos654-invoice .sos654-line>.sos654-lineamount{grid-column:1}.sos654-invoice .sos654-line>.sos654-remove{grid-column:2}}
</style>

<style>/* SOS_SERVICE_WORKFLOW_690 */
.sos654-kind button:disabled{opacity:.48!important;cursor:not-allowed!important}.sos654-invoice input[readonly]{color:#5a3e2c!important;background:#f4e9df!important;cursor:not-allowed}
</style>
