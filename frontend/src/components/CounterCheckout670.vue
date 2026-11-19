<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import CounterPremiumInvoice681 from './CounterPremiumInvoice681.vue'

const props = defineProps({ invoiceName: {type:String,default:''}, draftOnly: Boolean })
const emit = defineEmits(['completed','updated','close'])
const invoiceInput = ref(props.invoiceName || '')
const details = ref(null)
const loading = ref(false)
const working = ref(false)
const error = ref('')
const success = ref('')
const editMode = ref(false)
const draftLines = ref([])
const discountMode = ref('none')
const discountValue = ref(0)
const paymentMode = ref('cash')
const cashReceived = ref('')
const previewName = ref('')
let requestSeq = 0
const money = n => Number(n||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const change = computed(()=>Math.max(0,Number(cashReceived.value||0)-Number(details.value?.grand_total||0)))
const isSubmitted = computed(()=>Number(details.value?.docstatus)===1)
const canComplete = computed(()=>details.value?.docstatus===0 &&
 (paymentMode.value==='credit'||(Number(cashReceived.value)>=Number(details.value?.grand_total||0)&&Number(details.value?.grand_total||0)>0)))
function errText(data, fallback) {
  try { const msgs=JSON.parse(data?._server_messages||'[]');if(msgs.length){const v=JSON.parse(msgs[0]);return String(v.message||fallback).replace(/<[^>]+>/g,'')} } catch(_) {}
  return String(data?.message || fallback).replace(/<[^>]+>/g,'')
}
async function api(name, body=null, params={}) {
  const url=new URL('/api/method/servicing_os.api.counter_checkout_670.'+name,window.location.origin)
  for(const [k,v] of Object.entries(params))url.searchParams.set(k,String(v))
  const token=window.frappe?.csrf_token||window.csrf_token||document.querySelector('meta[name="csrf-token"]')?.content||''
  const response=await fetch(url,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{'Accept':'application/json',...(body?{'Content-Type':'application/json','X-Frappe-CSRF-Token':token}:{})},...(body?{body:JSON.stringify(body)}:{})})
  let data;try{data=await response.json()}catch(_){throw new Error('Server returned HTTP '+response.status)}
  if(!response.ok||data.exc||data.exception)throw new Error(errText(data,'Invoice checkout failed'))
  return data.message||{}
}
function setDetails(data) {
  details.value=data
  draftLines.value=(data.items||[]).map(r=>({...r,rate:Number(r.price_list_rate||r.rate||0)}))
  discountMode.value=data.discount_mode||'none'
  discountValue.value=data.discount_value||0
  cashReceived.value=String(data.grand_total||0)
  editMode.value=false
}
async function load(name=invoiceInput.value) {
  const n=String(name||'').trim()
  if(!n)return
  const seq=++requestSeq
  loading.value=true;error.value='';success.value='';details.value=null;invoiceInput.value=n
  try{
    const data=await api('get_checkout',null,{invoice_name:n})
    if(seq===requestSeq){
      setDetails(data)
      if(props.draftOnly && !isSubmitted.value) beginEdit()
    }
  }
  catch(e){if(seq===requestSeq)error.value=e.message}
  finally{if(seq===requestSeq)loading.value=false}
}
watch(()=>props.invoiceName,(next)=>{if(next && (!details.value || next!==details.value.invoice))load(next)},{immediate:true})
function beginEdit(){if(!details.value||isSubmitted.value)return;editMode.value=true;error.value=''}
async function saveEdits(){
  if(!details.value||working.value)return
  working.value=true;error.value=''
  try{
    const data=await api('edit_draft',{invoice_name:details.value.invoice,items:draftLines.value.map(r=>({name:r.name,qty:r.qty,rate:r.rate,discount_percentage:r.discount_percentage})),discount_mode:discountMode.value,discount_value:discountMode.value==='none'?0:Number(discountValue.value)})
    setDetails(data);success.value='Draft updated. Review the total before completing the sale.';emit('updated',data)
  }catch(e){error.value=e.message}finally{working.value=false}
}
async function complete(){
  if(props.draftOnly||!details.value||working.value||!canComplete.value)return
  working.value=true;error.value='';success.value=''
  try{
    const result=await api('complete_sale',{invoice_name:details.value.invoice,payment_mode:paymentMode.value,cash_received:paymentMode.value==='cash'?Number(cashReceived.value):null})
    setDetails(result)
    success.value=result.already_completed?'This invoice was already submitted. No second sale was created.':'Sale completed successfully. You can print the invoice now.'
    emit('completed', result)
    window.dispatchEvent(new CustomEvent('servicing-os-invoice-completed',{detail:result}))
    window.dispatchEvent(new CustomEvent('servicing-os-checkout-completed',{detail:result}))
    // Read the authoritative status back without a full browser reload.
    // The returned submit result has already made the checkout immediately Submitted.
    try {
      const authoritative = await api('get_checkout', null, {invoice_name:result.invoice})
      if (Number(authoritative.docstatus)===1) setDetails(authoritative)
    } catch (_) { /* Submitted result remains visible if the follow-up GET fails. */ }
  }catch(e){error.value=e.message;success.value='The invoice remains a draft if ERPNext rejected submission.'}
  finally{working.value=false}
}
onUnmounted(()=>{requestSeq++})
</script>

<template>
<section class="sos670-checkout" aria-label="Invoice checkout and draft editor">
  <div v-if="!details && !draftOnly" class="sos670-resume">
    <strong>Finish a saved invoice</strong>
    <p>Open an existing draft to edit or complete it without leaving Counter.</p>
    <div class="sos670-resume-row">
      <input v-model.trim="invoiceInput" type="text" aria-label="Draft Sales Invoice number" placeholder="Invoice number (e.g. ACC-SINV-...)" @keyup.enter="load()" />
      <button type="button" :disabled="!invoiceInput||loading" @click="load()">{{ loading?'Loading…':'Open Draft' }}</button>
    </div>
  </div>
  <template v-else-if="details">
    <div v-if="!draftOnly" class="sos670-heading">
      <div><small>ERPNext · {{ details.invoice_kind==='service'?'Service Invoice':details.invoice_kind==='used'?'Used Laptop Sale':'Retail Sale' }}</small>
        <strong>{{ details.invoice }}</strong>
        <p>{{ details.customer }} · {{ details.currency }}</p></div>
      <span class="sos670-status" :class="{'complete':isSubmitted}">{{ isSubmitted?'Submitted':'Draft · Editable' }}</span>
    </div>
    <div v-if="editMode" class="sos670-editor">
      <p>Edit quantities, base unit prices and discounts before final submission. Item codes remain linked to the original draft.</p>
      <div v-for="line in draftLines" :key="line.name" class="sos670-editline">
        <strong>{{ line.item_name||line.item_code }} <small>{{ line.item_code }}</small></strong>
        <label>Qty<input v-model.number="line.qty" type="number" step="0.01" min="0.01" /></label>
        <label>Unit price<input v-model.number="line.rate" type="number" step="0.01" min="0" /></label>
        <label>Discount %<input v-model.number="line.discount_percentage" type="number" step="0.01" min="0" max="100" /></label>
      </div>
      <div class="sos670-discounts">
        <label>Invoice discount
          <select v-model="discountMode" @change="discountValue=0">
            <option value="none">None</option><option value="percent">Percentage (%)</option><option value="amount">Fixed amount (BDT)</option>
          </select>
        </label>
        <label v-if="discountMode!=='none'">Discount value<input v-model.number="discountValue" type="number" min="0" step="0.01" /></label>
      </div>
      <div class="sos670-actions"><button type="button" :disabled="working" @click="draftOnly ? emit('close') : editMode=false">Cancel editing</button><button type="button" class="sos670-primary" :disabled="working" @click="saveEdits">{{working?'Saving…':'Save Draft Changes'}}</button></div>
    </div>
    <template v-else-if="!draftOnly">
      <div class="sos670-summary"><div><span>Invoice total</span><strong>৳ {{ money(details.grand_total) }}</strong></div>
        <div><span>Invoice items</span><strong>{{ details.items?.length||0 }}</strong></div>
        <div v-if="isSubmitted"><span>Outstanding</span><strong>৳ {{ money(details.outstanding_amount) }}</strong></div>
      </div>
      <template v-if="!isSubmitted">
        <div class="sos670-payment">
          <label>Payment type
            <select v-model="paymentMode"><option value="cash">Cash received</option><option value="credit">Pay later (credit sale)</option></select>
          </label>
          <label v-if="paymentMode==='cash'">Cash received (BDT)
            <input v-model="cashReceived" type="number" min="0" step="0.01" />
          </label>
          <div v-if="paymentMode==='cash'" class="sos670-change">Change to return <strong>৳ {{ money(change) }}</strong></div>
          <p class="sos670-note">Confirming submits this Sales Invoice in ERPNext. Stock-tracked items leave the warehouse if native validation succeeds. Cash sales use the configured Cash payment account.</p>
        </div>
        <div class="sos670-actions"><button type="button" @click="beginEdit">Edit Draft</button>
          <button type="button" class="sos670-primary" :disabled="working||!canComplete" @click="complete">{{working?'Completing…':paymentMode==='cash'?'Confirm Cash & Deliver':'Submit & Deliver · Pay Later'}}</button></div>
      </template>
      <div v-else class="sos670-actions"><button type="button" class="sos670-primary" @click="previewName=details.invoice">Print Invoice / Receipt</button>
        <button type="button" @click="details=null;invoiceInput=''">Another invoice</button></div>
      <p v-if="isSubmitted" class="sos670-note">Submitted invoices cannot be edited directly. Correct them through authorized Cancel & Amend or Sales Return procedures.</p>
    </template>
  </template>
  <p v-if="draftOnly && loading" role="status">Loading invoice editor…</p>
  <button v-if="draftOnly && !loading && !editMode" type="button" @click="emit('close')">Close editor</button>
  <p v-if="error" class="sos670-error" role="alert">{{ error }}</p>
  <p v-if="success" class="sos670-success" role="status">{{success}}</p>
  <CounterPremiumInvoice681 v-if="previewName" :invoice-name="previewName" @close="previewName=''" />
</section>
</template>

<style>
.sos670-checkout,.sos670-checkout *{box-sizing:border-box}
.sos670-checkout{min-width:0;margin:12px 0;padding:15px;background:#fffcf7;border:1px solid #e7d6c5;border-radius:13px;color:#3c2c25;font:inherit;font-size:12px}
.sos670-checkout :is(input,select){min-width:0;width:100%;min-height:42px;padding:9px 10px;color:#3c2c25;background:#fffefa;border:1px solid #ddc8b5;border-radius:9px;font-size:12px}
.sos670-checkout label{display:grid;gap:5px;min-width:0;font-weight:650;color:#765944;font-size:11px}
.sos670-checkout button{cursor:pointer;padding:10px 12px;background:#f4e3d3;border:1px solid #e1c9b3;border-radius:9px;color:#634632;font-size:12px;font-weight:700}
.sos670-checkout button:disabled{opacity:.5;cursor:not-allowed}
.sos670-checkout .sos670-primary{color:#fffaf5;background:#805a3e;border-color:#805a3e}
.sos670-heading,.sos670-actions,.sos670-summary>div,.sos670-resume-row{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.sos670-heading{border-bottom:1px solid #e7d6c5;padding-bottom:12px}.sos670-heading>div{min-width:0;overflow-wrap:anywhere}
.sos670-heading strong{display:block;font-size:17px}.sos670-heading small{color:#8b725e;letter-spacing:.05em}.sos670-heading p,.sos670-resume p,.sos670-note,.sos670-editor>p{font-size:11px;color:#8b725e;line-height:1.5;margin:5px 0}
.sos670-status{background:#f7e9d5;color:#815f3a;border-radius:100px;padding:7px 9px;font-size:11px}.sos670-status.complete{background:#e5f3e7;color:#30704d}
.sos670-summary{display:grid;gap:9px;padding:14px 0}.sos670-summary>div{border-bottom:1px solid #efdfd0;padding-bottom:8px}.sos670-summary strong{font-size:14px}
.sos670-payment{background:#f9f2eb;border:1px solid #ead7c4;padding:12px;border-radius:11px;display:grid;gap:11px}.sos670-change{display:flex;justify-content:space-between;gap:10px}.sos670-change strong{font-size:15px;color:#5e442d}.sos670-actions{justify-content:flex-end;margin-top:15px}
.sos670-editline{display:grid;grid-template-columns:minmax(140px,2.2fr) minmax(65px,.75fr) minmax(90px,1fr) minmax(90px,1fr);gap:9px;padding:12px 0;border-bottom:1px solid #ebddce;align-items:end}.sos670-editline strong{overflow-wrap:anywhere;font-size:11px}.sos670-editline small{display:block;color:#8b725e;font-weight:400}
.sos670-discounts{margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:10px}.sos670-error,.sos670-success{padding:12px;margin:12px 0;border-radius:9px;font-size:11px;line-height:1.45}.sos670-error{background:#fff0e9;color:#a03928}.sos670-success{background:#f1e9dd;color:#725235}.sos670-resume strong{font-size:13px}.sos670-resume-row{margin-top:10px}.sos670-resume-row input{flex:1 1 180px}
@media(max-width:730px){.sos670-editline{grid-template-columns:repeat(2,minmax(0,1fr))}.sos670-editline>strong{grid-column:1/-1}.sos670-discounts{grid-template-columns:1fr}}
</style>

<!-- SERVICING_OS_671 -->
