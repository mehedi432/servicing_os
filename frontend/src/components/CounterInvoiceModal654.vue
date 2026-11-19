<script setup>
import CounterCheckout670 from './CounterCheckout670.vue'
import ProductSuggestionGrid from './ProductSuggestionGrid.vue'
const completed670 = ref(null)
// SOS_FINAL_INVOICE_709
const finalizing709 = ref(false)
const finalized709 = ref(null)
async function finalize709() {
  if (!saved.value?.invoice || kind.value !== 'service' || finalizing709.value || finalized709.value) return
  finalizing709.value=true; error.value=''
  try {
    const body={job_name:sos690LockedServiceJob.value || selectedJob.value,invoice_name:saved.value.invoice}
    if(props.deliveryMode)body.confirmation=body.job_name
    const response=await fetch(props.deliveryMode?'/api/method/servicing_os.api.checkout_712.finalize_and_deliver':'/api/method/servicing_os.api.invoice_final_709.finalize_service_invoice',{
      method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'')},
      body:JSON.stringify(body)
    })
    const data=await response.json()
    if (!response.ok || data.exc || data.exc_type || data.exception) {
      throw new Error(errorText(data, 'Cannot finalize invoice. Review the saved draft and retry.'))
    }
    if(data.message?.docstatus!==1) throw new Error('Invoice was not submitted')
    if (props.deliveryMode && data.message.status !== 'Delivered') {
      throw new Error('The invoice was submitted. Retry to confirm device handover.')
    }
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
const sos712ImportBusy=ref(false)
const sos712PartsNote=ref('')
const props = defineProps({ initialKind: {type:String, default:'retail'}, initialJob: {type:String, default:''}, deliveryMode: {type:Boolean, default:false}, guidedDraft: Boolean })
const emit = defineEmits(['saved', 'close'])
const bn = computed(()=>String(unref(currentLanguage)||'en').toLowerCase().startsWith('bn'))
// SOS_SERVICE_WORKFLOW_690: lock the floating action to the exact selected Service Job.
const sos690LockedServiceJob = computed(() => String(props.initialJob || '').trim())
const kind = ref(['retail','used','service'].includes(props.initialKind) ? props.initialKind:'retail')
const setup = ref(null), loading = ref(true), saving=ref(false), error=ref(''), saved=ref(null)
const customerText=ref(''), customerId=ref(''), customerSuggestions=ref([]), customerFocus=ref(false)
const selectedJob=ref(''), jobList=ref([]), remarks=ref(''), discountMode=ref('none'), discountValue=ref(0)
let nextLineId = 0
function blankLine() {
  return { id: ++nextLineId, item_code:'', qty:1, rate:'', discount_percentage:0, serial_no:'' }
}
const rows=ref([blankLine()])
const checkedJob = ref('')
const checkingJob = ref(false)
let jobLookup = 0

// SERVICING_OS_WARRANTY_672: fetch and require an explicit warranty for each line.
const sos672WarrantyCache = new Map()
async function sos672ResolveModalWarranty(row) {
  if (!row?.item_code) return
  const code=String(row.item_code).trim()
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
    if(r.item_code && !r.sos672WarrantySelected && !r.sos672WarrantyPending && r.sos672WarrantySource!=='item_master')sos672ResolveModalWarranty(r)
  }),420)
})

let customerTimer, customerSeq=0
const currentJob=computed(()=>jobList.value.find(j=>j.name===selectedJob.value))
const money=v=>Number(v||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const lineTotal=row=>Math.round(Math.max(0,Number(row.qty)||0)*Math.max(0,Number(row.rate)||0)*(1-Math.min(100,Math.max(0,Number(row.discount_percentage)||0))/100)*100)/100
const subtotal=computed(()=>rows.value.reduce((s,r)=>s+lineTotal(r),0))
const overall=computed(()=>discountMode.value==='percent'?subtotal.value*Math.max(0,Math.min(100,Number(discountValue.value)||0))/100:discountMode.value==='amount'?Math.min(subtotal.value,Math.max(0,Number(discountValue.value)||0)):0)
const estimate=computed(()=>Math.max(0,subtotal.value-overall.value))
const kindName={retail:'New Sale',used:'Used Laptop Sale',service:'Service Job'}
function resetOnKind(){
  jobLookup++; checkedJob.value=''; checkingJob.value=false
  customerSeq++; clearTimeout(customerTimer)
  saved.value=null; completed670.value=null; finalized709.value=null; sos657Preview.value=''
  error.value='';customerId.value='';customerText.value='';customerSuggestions.value=[];selectedJob.value='';rows.value=[blankLine()]
  remarks.value=''; sos712PartsNote.value=''; customerFocus.value=false
  discountMode.value='none';discountValue.value=0
}
function errorText(data, fallback) {
  try {
    const entries = JSON.parse(data?._server_messages || '[]')
    for (const entry of (Array.isArray(entries) ? entries : []).slice().reverse()) {
      let message = entry?.message
      if (typeof entry === 'string') {
        try { message = JSON.parse(entry)?.message } catch (_) { message = entry }
      }
      if (typeof message === 'string' && message.trim()) return message.replace(/<[^>]*>/g, '')
    }
  } catch (_) {}
  const message = data?.message?.message || data?.message
  return typeof message === 'string' && message.trim() ? message.replace(/<[^>]*>/g, '') : fallback
}
async function api(name,{method='GET',params={},body=null,signal}={}){
  const url=new URL('/api/method/servicing_os.api.counter_invoice_654.'+name,location.origin)
  for(const [key,val] of Object.entries(params)) url.searchParams.set(key,String(val))
  const token=window.frappe?.csrf_token||window.csrf_token||document.querySelector('meta[name="csrf-token"]')?.content||''
  const res=await fetch(url,{method,credentials:'same-origin',cache:'no-store',signal,headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(token?{'X-Frappe-CSRF-Token':token}:{})},...(body?{body:JSON.stringify(body)}:{})})
  let data;try{data=await res.json()}catch(_){throw new Error('Unexpected invoice API response: HTTP '+res.status)}
  if(!res.ok||data.exc||data.exception)throw new Error(errorText(data,'Invoice request failed'))
  return data.message||{}
}

async function selectJob() {
  const id = selectedJob.value
  const lookup = ++jobLookup
  checkedJob.value = ''
  customerId.value = ''
  customerText.value = ''
  error.value = ''
  checkingJob.value = !!id
  if (!id) return
  try {
    const url = new URL('/api/method/servicing_os.api.service_invoice_661.get_job_context', window.location.origin)
    url.searchParams.set('job_name', id)
    const response = await fetch(url, {method:'GET', credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'}})
    const payload = await response.json()
    if (lookup !== jobLookup || selectedJob.value !== id || kind.value !== 'service') return
    const job = payload.message
    if (!response.ok || payload.exc || payload.exception || job?.name !== id) {
      throw new Error(errorText(payload, 'Could not load selected Service Job.'))
    }
    const invoices = (job.invoices || []).filter(invoice =>
      invoice.doctype === 'Sales Invoice' && !invoice.is_return && invoice.docstatus !== 2)
    if (invoices.length > 1) throw new Error('Multiple active Sales Invoices are linked to this Service Job. Review them in ERPNext.')
    const existing = invoices[0]
    if (existing && existing.customer !== job.customer) {
      throw new Error('The existing Sales Invoice customer differs from the Service Job. Review it in ERPNext.')
    }
    if (!jobList.value.some(row => row.name === id)) jobList.value.unshift(job)
    customerId.value = job.customer
    customerText.value = job.customer_name || job.customer
    checkedJob.value = id
    if (existing) {
      saved.value = { ...existing, invoice: existing.name, invoice_kind: 'service' }
      if (existing.docstatus === 1) completed670.value = { invoice: existing.name }
      if (props.guidedDraft) emit('saved', saved.value)
    }
  } catch (failure) {
    if (lookup === jobLookup && selectedJob.value === id) error.value = failure.message || 'Could not load selected Service Job.'
  } finally {
    if (lookup === jobLookup) checkingJob.value = false
  }
}

async function load(){
  loading.value = true
  error.value = ''
  try {
    if (sos690LockedServiceJob.value) {
      selectedJob.value = sos690LockedServiceJob.value
      await selectJob()
      if (saved.value || !checkedJob.value) return
    }
    setup.value = await api('get_invoice_setup')
    const selected = currentJob.value
    jobList.value = setup.value.jobs || []
    if (selected && !currentJob.value) jobList.value.unshift(selected)
    if (selectedJob.value && kind.value === 'service' && !sos690LockedServiceJob.value) await selectJob()
  } catch (e) {
    error.value = e.message || 'Cannot load invoice configuration'
  } finally { loading.value = false }
}
onMounted(load)
function customerSearch(){clearTimeout(customerTimer);customerSuggestions.value=[];customerId.value='';if(!customerFocus.value||customerText.value.trim().length<1)return;const seq=++customerSeq;customerTimer=setTimeout(async()=>{try{const x=await api('search_invoice_customers',{params:{q:customerText.value}});if(seq===customerSeq)customerSuggestions.value=x.results||[]}catch(e){if(seq===customerSeq)error.value=e.message}},240)}
function chooseCustomer(c){customerId.value=c.name;customerText.value=c.customer_name||c.name;customerFocus.value=false;customerSuggestions.value=[]}
function onCustomerBlur(){setTimeout(()=>{customerFocus.value=false;customerSuggestions.value=[]},220)}
async function searchItems(q, signal) {
  const result = await api('search_invoice_items', {params:{q, invoice_kind:kind.value, page_size:8}, signal})
  return (result.results || []).map(item => ({
    code: item.name, name: item.item_name, hasSerial: Boolean(item.has_serial_no),
    detail: item.stock_qty == null ? 'Service / non-stock item' : `${item.stock_qty} ${item.stock_uom || ''} on hand`,
  }))
}
function editItemCode(row, code) {
  if (row.item_code === code) return
  Object.assign(row, {
    item_code:code, selectedProduct:false, has_serial_no:false, serial_no:'', rate:'',
    priceLoading:false, priceError:'', priceList:'', sos672WarrantyCode:'',
    sos672WarrantyPending:false, sos672WarrantySelected:false, sos672WarrantyDays:'',
    sos672WarrantySource:'', sos672WarrantyError:'',
  })
}

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

async function loadItemPrice(row, code) {
  const request = Symbol()
  row.priceRequest = request
  const current = () => rows.value.includes(row) && row.item_code === code && row.priceRequest === request
  row.priceLoading = true
  row.priceError = ''
  try {
    const value = await sos660ModalPrice(code)
    if (!current()) return
    row.rate = Number(value.rate)
    row.priceList = value.price_list
  } catch (error) {
    if (current()) row.priceError = error.message || 'Selling price unavailable'
  } finally {
    if (current()) row.priceLoading = false
  }
}
function chooseItem(row, product) {
  editItemCode(row, product.code)
  row.selectedProduct = true
  row.has_serial_no = product.hasSerial
  if (!row.sos672WarrantySelected && !row.sos672WarrantyPending) sos672ResolveModalWarranty(row)
  loadItemPrice(row, product.code)
}

// SOS_REPAIR_PARTS_BILLING_712 — copy approved repair materials into billing lines.
async function sos712ImportApprovedParts(){
  const job=sos690LockedServiceJob.value||selectedJob.value
  if(sos712ImportBusy.value||!job||kind.value!=='service')return
  sos712ImportBusy.value=true;sos712PartsNote.value='';error.value=''
  try{
    const url=new URL('/api/method/servicing_os.api.parts_workbench_708.overview',location.origin)
    url.searchParams.set('job_name',job)
    const response=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
    const body=await response.json()
    if(!response.ok||body.exc||body.exception)throw new Error(errorText(body,'Could not load repair parts'))
    const requests=body.message?.requests||[]
    if(requests.some(x=>x.docstatus===0))throw new Error('Approve all draft Material Requests before final billing.')
    const totals=new Map()
    for(const mr of requests.filter(x=>x.docstatus===1))for(const part of mr.items||[]){
      const quantity = Number(part.stock_qty ?? part.qty)
      if(!part.item_code||!(quantity>0))continue
      totals.set(part.item_code,(totals.get(part.item_code)||0)+quantity)
    }
    if(!totals.size){sos712PartsNote.value='No approved parts. Add only service/labour charges as needed.';return}
    const already=rows.value.filter(x=>x.item_code).map(x=>x.item_code)
    const additions=[...totals.entries()].filter(([code])=>!already.includes(code))
    if((rows.value.length===1&&!rows.value[0].item_code?0:rows.value.length)+additions.length>35)throw new Error('The invoice exceeds 35 line items.')
    if(rows.value.length===1&&!rows.value[0].item_code)rows.value=[]
    for(const [code,qty] of additions){
      rows.value.push({...blankLine(), item_code:code, qty})
      const row = rows.value[rows.value.length - 1]
      sos672ResolveModalWarranty(row)
      await loadItemPrice(row, code)
    }
    sos712PartsNote.value=additions.length+' approved part line(s) imported. Review selling rates, quantities and warranty.'
  }catch(e){error.value=e.message||'Approved parts could not be imported'}finally{sos712ImportBusy.value=false}
}

function addItem(){if(rows.value.length<35)rows.value.push(blankLine())}
function removeItem(i){if(rows.value.length>1)rows.value.splice(i,1)}
function nextInvoice() {
  if (saving.value || finalizing709.value) return
  if (sos690LockedServiceJob.value) emit('close')
  else resetOnKind()
}
watch(kind,resetOnKind)
onUnmounted(()=>{clearTimeout(customerTimer);clearTimeout(sos672ModalTimer);customerSeq++;jobLookup++})
async function save(){
  if(saving.value||saved.value)return
  error.value=''
  if(sos690LockedServiceJob.value && (kind.value!=='service'||selectedJob.value!==sos690LockedServiceJob.value)){error.value='This invoice must belong to '+sos690LockedServiceJob.value;return}
  if(kind.value==='service'&&(!selectedJob.value||checkedJob.value!==selectedJob.value||checkingJob.value)){error.value='Choose a saved Service Job and wait for the invoice check.';return}
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
    if(kind.value==='service' && !props.guidedDraft) await finalize709()
  }catch(e){
    const message = e.message || 'Unable to save invoice'
    if (kind.value === 'service' && message.includes('invoice already exists for this Service Job')) {
      await selectJob()
    }
    if (!saved.value) error.value = message
  }finally{saving.value=false}
}
// SOS_CHECKOUT_STOCK_COMPACT_712 — Service Job delivery uses one atomic backend transaction.
</script>
<template>
  <div class="sos654-invoice">
    <p v-if="loading" class="sos654-info">Loading shop, customers and invoice settings…</p>
    <p v-else-if="saved && guidedDraft" class="sos654-info" role="status">Loading the saved invoice…</p>
    <div v-else-if="saved" class="sos654-success" role="status">
      <p v-if="error" class="sos654-error" role="alert">{{error}}</p>
      <strong>{{ completed670?.invoice===saved?.invoice ? "Invoice Submitted" : "Draft Invoice Saved" }}</strong><h2>{{ saved.invoice }}</h2>
      <p>{{ kindName[saved.invoice_kind] }} · {{ saved.customer }} · {{ saved.currency }} {{ money(saved.grand_total) }}</p>
      <p v-if="completed670?.invoice===saved.invoice">ERPNext submitted the invoice. You can print it below.</p>
      <p v-else-if="kind==='service'">This draft is linked to {{ selectedJob }}. Review it in ERPNext or finalize it here.</p>
      <p v-else>Review the draft in checkout before submitting.</p>
      <div class="sos654-result-actions">
        <button v-if="kind!=='service' || completed670?.invoice===saved.invoice" type="button" @click="sos657Preview=saved.invoice">Print Final Invoice</button>
        <template v-if="kind==='service' && (completed670?.invoice!==saved.invoice || (deliveryMode && !finalized709))">
          <a v-if="completed670?.invoice!==saved.invoice" :href="`/app/sales-invoice/${encodeURIComponent(saved.invoice)}`" target="_blank" rel="noopener">Review draft in ERPNext ↗</a>
          <button type="button" :disabled="finalizing709 || saving" @click="finalize709">{{ finalizing709 ? 'Submitting…' : completed670?.invoice===saved.invoice ? 'Deliver Device & Print Invoice' : error ? 'Retry Finalization' : deliveryMode ? 'Finalize Existing Invoice & Deliver' : 'Finalize Existing Invoice' }}</button>
        </template>
        <button type="button" :disabled="saving || finalizing709" @click="nextInvoice">{{ sos690LockedServiceJob ? 'Back to Service Jobs' : kind==='service' ? 'Choose another Service Job' : 'Create another invoice' }}</button>
      </div>
    </div>
    <form v-else @submit.prevent="save">
      <div v-if="!guidedDraft" class="sos654-kind" role="group" aria-label="Invoice type">
        <button v-for="(name,key) in kindName" :key="key" type="button" :class="{'selected':kind===key}" @click="kind=key" :disabled="saving || (!!sos690LockedServiceJob && key!=='service')">{{ name }}</button>
      </div>
      <div v-if="!guidedDraft" class="sos654-fields">
        <label v-if="kind==='service'"><span>Service Job *</span>
          <input v-model.trim="selectedJob" list="sos654-jobs" autocomplete="off" placeholder="Select saved job" @change="selectJob" :readonly="!!sos690LockedServiceJob" :disabled="saving" />
          <datalist id="sos654-jobs"><option v-for="j in jobList" :key="j.name" :value="j.name">{{ j.customer_name }}</option></datalist>
          <small v-if="checkingJob">Checking for an existing invoice…</small>
          <small v-else-if="currentJob">{{ currentJob.customer_name }} · {{ currentJob.status }}</small>
        </label>
        <label v-else class="sos654-search-field"><span>Customer *</span>
          <input v-model="customerText" autocomplete="off" placeholder="Click to search existing customers" @focus="customerFocus=true;customerSearch()" @input="customerSearch" @blur="onCustomerBlur" />
          <div v-if="customerFocus&&customerSuggestions.length" class="sos654-suggest" role="listbox">
            <button v-for="c in customerSuggestions" :key="c.name" type="button" @mousedown.prevent="chooseCustomer(c)">{{ c.customer_name }} <small>{{ c.name }}</small></button>
          </div>
          <small v-if="customerId">Selected: {{ customerId }}</small>
        </label>
        <label><span>Company</span><input :value="setup?.company||''" readonly /></label>
        <label><span>Warehouse</span><input :value="kind==='service'?'Repair parts · separate Stock Entry':kind==='used'?setup?.used_laptop_warehouse:setup?.retail_warehouse" readonly /></label>
        <label><span>Remarks (optional)</span><input v-model="remarks" maxlength="360" placeholder="Customer reference / notes" /></label>
      </div>
      <div class="sos654-heading"><div><strong>Invoice Items</strong><small>Focus the product field to browse or type to search</small></div><div class="sos712-import-actions"><button v-if="kind==='service'" type="button" :disabled="sos712ImportBusy" @click="sos712ImportApprovedParts">{{sos712ImportBusy?'Importing…':'＋ Import Approved Parts'}}</button><button type="button" :disabled="rows.length>=35" @click="addItem">+ Add Item</button></div></div>
      <p v-if="sos712PartsNote" class="sos712-parts-hint">{{sos712PartsNote}}</p>
      <div class="sos654-lines">
        <div v-for="(row,i) in rows" :key="row.id" class="invoice-line-fields">
          <ProductSuggestionGrid class="invoice-product" label="Item Code *" :model-value="row.item_code" :selected="!!row.selectedProduct"
            :lookup="searchItems" @update:model-value="editItemCode(row, $event)" @select="chooseItem(row, $event)" />
          <label><span>Qty</span><input v-model.number="row.qty" type="number" min="0.01" step="0.01" /></label>
          <label><span>Unit selling price (BDT)</span><input v-model.number="row.rate" type="number" min="0" step="0.01" :readonly="kind !== 'service'" title="Edit the final selling rate for service items and approved spare parts" @input="row.priceError = ''" /></label>
          <label><span>Discount %</span><input v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.01" /></label>
          <label class="invoice-warranty"><span>Warranty days</span>
            <input v-model.number="row.sos672WarrantyDays" type="number" :min="row.sos672WarrantySource==='none'?0:1" max="36500" step="1"
              :readonly="row.sos672WarrantySource==='item_master'"
              :disabled="row.sos672WarrantyPending" placeholder="Days" @input="sos672WarrantyEdited(row)" />
          </label>
          <div class="invoice-line-amount"><span>Line total</span><strong>৳ {{ money(lineTotal(row)) }}</strong></div>
          <button class="invoice-remove" type="button" aria-label="Remove invoice item" :disabled="rows.length<2" @click="removeItem(i)">×</button>
          <div v-if="row.item_code" class="invoice-line-notes">
            <span aria-live="polite">
              <span v-if="row.priceLoading">Fetching selling price…</span>
              <span v-else-if="row.priceError" class="invoice-note-error">{{ row.priceError }}</span>
              <span v-else-if="row.priceList">{{ row.priceList }}</span>
            </span>
            <div class="invoice-warranty-note">
              <span v-if="row.sos672WarrantySource==='item_master'">Warranty from Item Master</span>
              <span v-else-if="row.sos672WarrantyPending" role="status">Checking warranty…</span>
              <template v-else>
                <span v-if="row.sos672WarrantyError" class="invoice-note-error">{{ row.sos672WarrantyError }}</span>
                <button type="button" :aria-pressed="row.sos672WarrantySource==='none'" @click="sos672NoWarranty(row)">No warranty</button>
              </template>
            </div>
          </div>
          <label v-if="kind==='used'||row.has_serial_no" class="invoice-line-serial"><span>Serial Number(s)</span><input v-model.trim="row.serial_no" placeholder="For serialized items, one per unit" /></label>
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
      <p v-if="!guidedDraft" class="sos654-info">{{kind==='service'?'Final Service Invoice: submits the Sales Invoice and any approved, unissued parts requests. Draft parts requests require approval. No duplicate stock issue or automatic payment.':'Creates a Draft Sales Invoice; checkout handles final submission.'}}</p>
      <p v-if="error" class="sos654-error" role="alert">{{ error }}</p>
      <div class="sos654-footer"><button v-if="!guidedDraft || !checkedJob" type="button" :disabled="saving || checkingJob" @click="load">Refresh</button><button type="submit" class="primary" :disabled="saving || loading || sos712ImportBusy || (kind==='service' && (checkingJob || !selectedJob || checkedJob!==selectedJob))">{{ saving?'Saving…':guidedDraft?'Save invoice draft':kind==='service'?(props.deliveryMode?'Finalize · Deliver & Print':'Save Final Invoice'):'Review & Continue to Checkout' }}</button></div>
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
.sos654-lines{container: invoice-lines / inline-size;display:grid;gap:9px}
.sos654-invoice .invoice-line-fields{display:grid;grid-template-columns:minmax(130px,2.4fr) minmax(56px,.65fr) minmax(96px,1.15fr) minmax(69px,.8fr) minmax(95px,1fr) minmax(90px,1fr) 38px;align-items:end;gap:8px;padding:11px;border:1px solid #e7d6c5;border-radius:11px;background:#fffdf9;min-width:0}
.sos654-invoice .invoice-line-fields label,.invoice-line-amount{display:grid;grid-template-rows:auto 40px;gap:5px;min-width:0}
.invoice-line-amount{color:#634633;font-size:11px;font-weight:700}
.invoice-line-amount strong,.sos654-invoice .invoice-remove{display:flex;align-items:center;justify-content:center;min-height:40px;border:1px solid #e5d1bf;border-radius:9px;background:#f9f0e6;color:#573c2a;padding:4px}
.invoice-line-amount strong{justify-content:flex-start;padding-inline:8px;overflow-wrap:anywhere}
.sos654-invoice .invoice-remove{font-size:20px;background:#fff0e8;color:#a05a40}
.invoice-remove:disabled{opacity:.45;cursor:not-allowed}
.invoice-line-fields .invoice-product{display:contents}
.invoice-line-fields .sos-product-panel{grid-column:1/-1;order:1}
.invoice-line-notes{grid-column:1/-1;order:2;display:flex;justify-content:space-between;align-items:center;gap:6px;color:#765b47;font-size:11px}
.invoice-warranty-note{display:flex;justify-content:flex-end;align-items:center;gap:6px;flex-wrap:wrap}
.invoice-warranty-note button{background:#f8ebde;border:1px solid #e3cab4;border-radius:7px;color:#725037;padding:4px 8px;font-weight:650}
.invoice-warranty-note button[aria-pressed="true"]{background:#805a3e;color:#fff9f2}
.invoice-note-error{color:#963a2c}
.invoice-line-serial{grid-column:1/-1;order:3}
.sos654-invoice .sos654-discount select{height:40px}
@container invoice-lines (max-width:680px){
  .sos654-invoice .invoice-line-fields{grid-template-columns:repeat(4,minmax(0,1fr))}
  .invoice-line-fields .sos-product-label{grid-column:1/-1}
  .invoice-line-amount{grid-column:1/4}
}
@container invoice-lines (max-width:400px){
  .sos654-invoice .invoice-line-fields{grid-template-columns:repeat(2,minmax(0,1fr))}
  .invoice-line-amount{grid-column:1}
  .sos654-invoice .invoice-remove{justify-self:end;width:40px}
}
.sos654-bottom{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,1fr);gap:15px;margin-top:16px;padding:16px;border:1px solid #e7d6c5;background:#fffaf5;border-radius:11px}.sos654-discount{display:grid;grid-template-columns:1fr 1fr;gap:9px;align-content:start}.sos654-totals{display:grid;gap:11px}.sos654-totals>div{display:flex;justify-content:space-between;gap:8px}.sos654-totals .total{border-top:1px solid #e7d6c5;padding-top:10px;font-weight:800}.sos654-totals .total strong{font-size:17px}
.sos654-info{background:#f1e5d9;border-radius:9px;padding:10px 12px;margin-top:13px;color:#715641;line-height:1.45}.sos654-error{background:#fff1ec;color:#8e3a2b;border:1px solid #ecc7bb;padding:10px;border-radius:8px;margin-top:12px}.sos654-footer{display:flex;gap:10px;justify-content:flex-end;margin-top:15px}.sos654-footer button.primary,.sos654-success button{background:#805a3e!important;color:#fff!important;border-color:#805a3e!important}.sos654-success{text-align:center;padding:28px;background:#fffaf4;border:1px solid #e7d6c5;border-radius:11px}.sos654-success h2{font-weight:800;font-size:22px;margin:10px}.sos654-success p{color:#896b55;margin:10px}
@media(max-width:850px){.sos654-bottom{grid-template-columns:1fr}}
@media(max-width:560px){.sos654-fields,.sos654-discount{grid-template-columns:1fr}.sos654-footer button{flex:1}}
</style>

<!-- SERVICING_OS_COUNTER_657 -->

<style>/* SOS_SERVICE_WORKFLOW_690 */
.sos654-kind button:disabled{opacity:.48!important;cursor:not-allowed!important}.sos654-invoice input[readonly]{color:#5a3e2c!important;background:#f4e9df!important;cursor:not-allowed}
</style>

<style>
/* SOS_REPAIR_PARTS_BILLING_712 */
.sos712-import-actions{display:flex;gap:6px;flex-wrap:wrap}.sos712-parts-hint{background:#f5ece3;border-radius:7px;padding:8px 12px;color:#7b563c;font-size:11px;margin:8px 0}
.sos654-result-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:center}
.sos654-result-actions a{color:#684832}
</style>
