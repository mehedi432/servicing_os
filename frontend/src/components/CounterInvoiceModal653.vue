<script setup>
import { computed, onMounted, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
const props = defineProps({ initialJob: { type: String, default: '' } })
const emit = defineEmits(['saved'])
const bn = computed(() => String(unref(currentLanguage)||'en').toLowerCase().startsWith('bn'))
const loading=ref(true), saving=ref(false), error=ref(''), saved=ref(null)
const jobs=ref([]), catalog=ref([]), selectedJob=ref(props.initialJob||'')
const remarks=ref(''), discountMode=ref('none'), discountValue=ref(0)
const rows=ref([{item_code:'',qty:1,rate:'',discount_percentage:0}])
const currentJob=computed(()=>jobs.value.find(j=>j.name===selectedJob.value))
const lineAmount=(row)=>{
  const q=Math.max(0,Number(row.qty)||0), r=Math.max(0,Number(row.rate)||0)
  const p=Math.max(0,Math.min(100,Number(row.discount_percentage)||0))
  return Math.round(q*r*(1-p/100)*100)/100
}
const lineSubtotal=computed(()=>rows.value.reduce((sum,r)=>sum+lineAmount(r),0))
const discountPreview=computed(()=>{
  const val=Math.max(0,Number(discountValue.value)||0)
  if(discountMode.value==='percent')return Math.round(lineSubtotal.value*Math.min(100,val)/100*100)/100
  if(discountMode.value==='amount')return Math.min(lineSubtotal.value,val)
  return 0
})
const previewTotal=computed(()=>Math.max(0,lineSubtotal.value-discountPreview.value))
const money=x=>Number(x||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
function serverError(data,fallback){
  try { const a=JSON.parse(data?._server_messages||'[]'); const first=a[0]&&JSON.parse(a[0]); if(first?.message)return String(first.message).replace(/<[^>]*>/g,'') }catch(_){}
  return (typeof data?.message==='string'&&data.message) || fallback
}
async function api(path,options={}){
  const token=window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
  const res=await fetch('/api/method/servicing_os.api.counter_invoice_653.'+path,{
    credentials:'same-origin',cache:'no-store',...options,headers:{Accept:'application/json',...(options.body?{'Content-Type':'application/json'}:{}),...(token?{'X-Frappe-CSRF-Token':token}:{}),...(options.headers||{})}
  })
  let data={}
  try{data=await res.json()}catch(_){throw new Error('Billing API returned an invalid response (HTTP '+res.status+')')}
  if(!res.ok||data.exc||data.exception)throw new Error(serverError(data,'Billing request failed (HTTP '+res.status+')'))
  return data.message
}
async function load(){
  loading.value=true;error.value=''
  try {const data=await api('get_counter_invoice_setup');jobs.value=data.jobs||[];catalog.value=data.items||[]}
  catch(e){error.value=e.message||'Unable to load invoice setup'}
  finally{loading.value=false}
}
onMounted(load)
function addLine(){if(rows.value.length<30)rows.value.push({item_code:'',qty:1,rate:'',discount_percentage:0})}
function removeLine(i){if(rows.value.length>1)rows.value.splice(i,1)}
function reset(){saved.value=null;selectedJob.value='';remarks.value='';discountMode.value='none';discountValue.value=0;rows.value=[{item_code:'',qty:1,rate:'',discount_percentage:0}];load()}
async function createDraft(){
  if(saving.value||saved.value)return
  error.value=''
  if(!selectedJob.value.trim()){error.value='Choose a saved Service Job';return}
  if(!rows.value.length||rows.value.some(r=>!r.item_code || r.rate==='' || !Number.isFinite(Number(r.rate)) || Number(r.rate)<0 || !Number.isFinite(Number(r.qty)) || Number(r.qty)<=0 || !Number.isFinite(Number(r.discount_percentage)) || Number(r.discount_percentage)<0 || Number(r.discount_percentage)>100)){
    error.value='Each line needs a valid service item, quantity, rate and discount (0–100%).';return
  }
  if(!Number.isFinite(Number(discountValue.value))||Number(discountValue.value)<0 || (discountMode.value==='percent'&&Number(discountValue.value)>100)|| (discountMode.value==='amount'&&Number(discountValue.value)>=lineSubtotal.value)){
    error.value='Overall discount is invalid or exceeds the subtotal.';return
  }
  if(previewTotal.value<=0){error.value='Invoice total must be greater than zero.';return}
  saving.value=true
  try{
    const result=await api('create_counter_invoice_draft',{method:'POST',body:JSON.stringify({
      job_name:selectedJob.value,items:rows.value,remarks:remarks.value,
      discount_mode:discountMode.value,discount_value:discountMode.value==='none'?0:Number(discountValue.value)
    })})
    if(!result?.invoice)throw new Error('The server did not return an invoice number')
    saved.value=result;emit('saved',result);window.dispatchEvent(new CustomEvent('servicing-os-invoice-draft-created',{detail:result}))
  }catch(e){error.value=e.message||'Unable to create invoice draft'}
  finally{saving.value=false}
}
</script>
<template>
  <div class="sos653-invoice" aria-label="Invoice creation form">
    <div v-if="loading" class="sos653-notice">{{ bn ? 'ইনভয়েস তথ্য লোড হচ্ছে...' : 'Loading saved jobs and service items…' }}</div>
    <div v-else-if="saved" class="sos653-invoice-success" role="status">
      <strong>{{ bn ? 'খসড়া ইনভয়েস তৈরি হয়েছে' : 'Draft invoice created successfully' }}</strong>
      <div class="sos653-invoice-number">{{ saved.invoice }}</div>
      <p>{{ saved.company }} · {{ saved.currency }} {{ money(saved.grand_total) }}</p>
      <p>Draft only. This invoice has not been submitted and no payment or stock movement was posted.</p>
      <button type="button" class="sos653-primary" @click="reset">{{ bn ? 'নতুন ইনভয়েস' : 'Create another draft' }}</button>
    </div>
    <form v-else @submit.prevent="createDraft">
      <div class="sos653-invoice-fields">
        <label><span>{{ bn ? 'সার্ভিস জব' : 'Saved Service Job' }} *</span>
          <input v-model.trim="selectedJob" list="sos653-jobcodes" autocomplete="off" placeholder="Search by Service Job number" />
          <datalist id="sos653-jobcodes"><option v-for="j in jobs" :key="j.name" :value="j.name">{{ j.customer_name||j.customer }} · {{ j.status }}</option></datalist>
          <small v-if="currentJob">{{ currentJob.customer_name || currentJob.customer }} · {{ currentJob.status }}</small>
        </label>
        <label><span>{{ bn ? 'বিবরণ' : 'Remarks / Reference' }}</span><input v-model="remarks" maxlength="500" placeholder="Optional billing notes" /></label>
      </div>
      <div class="sos653-line-header">
        <div><strong>{{ bn ? 'ইনভয়েস আইটেম' : 'Invoice line items' }}</strong><small>{{ bn ? 'প্রতি সারিতে ছাড় দেওয়া যাবে' : 'Discount is available on every line' }}</small></div>
        <button type="button" :disabled="rows.length>=30" @click="addLine">+ {{ bn ? 'আইটেম যোগ' : 'Add Item' }}</button>
      </div>
      <datalist id="sos653-serviceitems"><option v-for="item in catalog" :key="item.name" :value="item.name">{{ item.item_name }}</option></datalist>
      <div class="sos653-lines">
        <div v-for="(line,index) in rows" :key="index" class="sos653-line">
          <label><span>{{ bn ? 'সার্ভিস কোড' : 'Service Item' }}</span><input v-model.trim="line.item_code" list="sos653-serviceitems" placeholder="Select existing Item Code" /></label>
          <label><span>{{ bn ? 'পরিমাণ' : 'Qty' }}</span><input v-model.number="line.qty" type="number" min="0.01" step="0.01" /></label>
          <label><span>{{ bn ? 'দর' : 'Rate (BDT)' }}</span><input v-model="line.rate" type="number" min="0" step="0.01" placeholder="0.00" /></label>
          <label><span>{{ bn ? 'ছাড় %' : 'Discount %' }}</span><input v-model.number="line.discount_percentage" type="number" min="0" max="100" step="0.01" /></label>
          <div class="sos653-linetotal"><small>{{ bn ? 'লাইন মোট' : 'Line total' }}</small><strong>৳ {{ money(lineAmount(line)) }}</strong></div>
          <button type="button" class="sos653-delete" :disabled="rows.length<=1" aria-label="Remove line" @click="removeLine(index)">×</button>
        </div>
      </div>
      <div class="sos653-summary">
        <div class="sos653-discount-fields">
          <label><span>{{ bn ? 'মোট ছাড়ের ধরন' : 'Overall discount type' }}</span><select v-model="discountMode" @change="discountValue=0"><option value="none">No extra discount</option><option value="percent">Percentage (%)</option><option value="amount">Fixed amount (BDT)</option></select></label>
          <label v-if="discountMode!=='none'"><span>{{ discountMode==='percent'?'Discount %':'Discount amount (BDT)' }}</span><input v-model.number="discountValue" type="number" min="0" :max="discountMode==='percent'?100:undefined" step="0.01" /></label>
        </div>
        <div class="sos653-totals">
          <div><span>{{ bn ? 'সাবটোটাল' : 'Subtotal (after line discounts)' }}</span><strong>৳ {{ money(lineSubtotal) }}</strong></div>
          <div><span>{{ bn ? 'অতিরিক্ত ছাড়' : 'Overall discount' }}</span><strong>− ৳ {{ money(discountPreview) }}</strong></div>
          <div class="sos653-total-main"><span>{{ bn ? 'আনুমানিক মোট (কর ব্যতীত)' : 'Estimated total before taxes' }}</span><strong>৳ {{ money(previewTotal) }}</strong></div>
        </div>
      </div>
      <div class="sos653-notice">{{ bn ? 'এটি একটি ড্রাফট ইনভয়েস। ERPNext চূড়ান্ত কর ও মোট হিসাব করবে।' : 'Draft Sales Invoice only. ERPNext calculates actual taxes and totals. Retail stock checkout continues through New Sale; this form bills saved service jobs and non-stock service items.' }}</div>
      <p v-if="error" class="sos653-error" role="alert">{{ error }}</p>
      <div class="sos653-invoice-footer"><button type="button" @click="load" :disabled="saving">Refresh</button><button class="sos653-primary" type="submit" :disabled="saving||loading">{{ saving?(bn?'সেভ হচ্ছে...':'Saving…'):(bn?'ড্রাফট ইনভয়েস তৈরি':'Save Draft Invoice') }}</button></div>
    </form>
    <p v-if="error && loading" class="sos653-error">{{ error }}</p>
    <p v-if="!loading && error && !jobs.length" class="sos653-error">{{ error }} <button type="button" @click="load">Retry</button></p>
  </div>
</template>
<style>
.sos653-invoice,.sos653-invoice *{box-sizing:border-box}
.sos653-invoice{color:#3c2c25;font-size:12px;min-width:0}
.sos653-invoice-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:15px}
.sos653-invoice label{display:flex;flex-direction:column;gap:5px;min-width:0;color:#5c4030;font-weight:650;font-size:11px}
.sos653-invoice label span{display:block}
.sos653-invoice input,.sos653-invoice select{width:100%;min-height:40px;border:1px solid #decab8!important;border-radius:9px!important;background:#fffcf7!important;color:#3c2c25!important;padding:8px 10px;font:inherit;font-size:12px}
.sos653-invoice input:focus,.sos653-invoice select:focus{outline:2px solid #c69e7c;outline-offset:1px}
.sos653-invoice label small{font-size:10px;color:#8b725e}
.sos653-line-header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:5px 0 10px}.sos653-line-header strong{display:block;font-size:13px}.sos653-line-header small{display:block;color:#8b725e;margin-top:3px;font-size:10px}
.sos653-line-header button,.sos653-invoice-footer button,.sos653-invoice-success button,.sos653-invoice .sos653-error button{padding:10px 14px;background:#f4e3d3!important;border:1px solid #d9bda5!important;border-radius:9px!important;color:#664632!important;font-weight:700;font-size:12px}
.sos653-lines{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.sos653-line{display:grid;grid-template-columns:minmax(155px,3fr) minmax(58px,.8fr) minmax(85px,1.15fr) minmax(80px,1fr) minmax(94px,1.25fr) 31px;align-items:end;gap:8px;padding:11px;border:1px solid #ead8c8;background:#fffcf8;border-radius:10px}
.sos653-line .sos653-linetotal{display:flex;flex-direction:column;gap:5px;white-space:nowrap}.sos653-linetotal small{font-size:10px;color:#8b725e}.sos653-linetotal strong{line-height:40px;font-size:11px}
.sos653-delete{width:31px;height:40px;align-self:end;border:1px solid #edd5c9!important;background:#fff0e8!important;color:#985e43!important;border-radius:9px!important;font-size:22px}
.sos653-delete:disabled{opacity:.4}
.sos653-summary{display:grid;grid-template-columns:minmax(0,1fr) minmax(245px,1fr);gap:18px;padding:16px;border:1px solid #e7d6c5;border-radius:11px;background:#fffaf4}
.sos653-discount-fields{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-content:start}
.sos653-totals{display:grid;gap:10px}.sos653-totals>div{display:flex;justify-content:space-between;gap:10px;color:#80634e}.sos653-totals strong{white-space:nowrap;color:#3c2c25}.sos653-totals .sos653-total-main{border-top:1px solid #e7d6c5;padding-top:12px;color:#3c2c25;font-weight:700}.sos653-total-main strong{font-size:17px}
.sos653-notice{border-radius:10px;background:#f1e4d7;color:#795c46;padding:11px 13px;margin:12px 0;font-size:11px;line-height:1.5}
.sos653-error{border:1px solid #eccabe;background:#fff1eb;border-radius:9px;padding:10px;color:#8b3e2c;font-size:12px}
.sos653-invoice-footer{display:flex;justify-content:flex-end;gap:10px;margin-top:13px}.sos653-invoice-footer .sos653-primary,.sos653-invoice .sos653-primary{background:#805a3e!important;color:#fffaf4!important;border-color:#805a3e!important}
.sos653-invoice-success{text-align:center;padding:34px 15px;background:#fffaf4;border:1px solid #e7d6c5;border-radius:12px}.sos653-invoice-success strong{font-size:16px}.sos653-invoice-success p{margin:10px 0;color:#836c58}.sos653-invoice-number{font-size:24px;font-weight:800;margin:13px 0}
@media(max-width:850px){.sos653-line{grid-template-columns:repeat(4,minmax(0,1fr))}.sos653-line label:first-child{grid-column:1/-1}.sos653-linetotal{grid-column:1/3}.sos653-summary{grid-template-columns:1fr}}
@media(max-width:590px){.sos653-invoice-fields{grid-template-columns:1fr}.sos653-discount-fields{grid-template-columns:1fr}.sos653-line{grid-template-columns:1fr 1fr}.sos653-line label:first-child{grid-column:1/-1}.sos653-line .sos653-linetotal{grid-column:1/2}.sos653-invoice-footer{flex-wrap:wrap}.sos653-invoice-footer button{flex:1}}
</style>
