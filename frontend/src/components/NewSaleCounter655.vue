<script setup>
// SERVICING_OS_655 — mult-item draft billing with native POS preserved in a separate tab.
import { computed, onUnmounted, ref } from 'vue'
const emit = defineEmits(['saved'])
const mode = ref('cart')
const query = ref('')
const itemFocused = ref(false)
const itemBusy = ref(false)
const itemHits = ref([])
const customerQuery = ref('')
const customerFocused = ref(false)
const customerBusy = ref(false)
const customerHits = ref([])
const selectedCustomer = ref(null)
const cart = ref([])
const discountMode = ref('none')
const discountValue = ref(0)
const error = ref('')
const info = ref('')
const saving = ref(false)
const saved = ref(null)
let itemTimer, customerTimer, itemSequence = 0, customerSequence = 0
const money = value => Number(value || 0).toLocaleString('en-BD',{minimumFractionDigits:2, maximumFractionDigits:2})
const lineTotal = row => Math.round((Number(row.qty)||0)*(Number(row.rate)||0)*(1-(Number(row.discount_percentage)||0)/100)*100)/100
const subtotal = computed(() => cart.value.reduce((sum,row)=>sum+lineTotal(row),0))
const overall = computed(() => discountMode.value === 'percent' ? subtotal.value*Number(discountValue.value||0)/100 : discountMode.value === 'amount' ? Number(discountValue.value||0) : 0)
const total = computed(() => Math.max(0,Math.round((subtotal.value-overall.value)*100)/100))
const itemCount = computed(() => cart.value.reduce((total,row)=>total+Number(row.qty||0),0))
function errMessage(data,fallback){
 try{const a=JSON.parse(data?._server_messages||'[]'); if(a.length){const msg=JSON.parse(a[0]);return String(msg.message||fallback).replace(/<[^>]*>/g,'')}}catch(_){ }
 return data?.message||fallback
}
async function request(method, params={}, body=null){
 const url=new URL('/api/method/servicing_os.api.counter_invoice_654.'+method, location.origin)
 Object.entries(params).forEach(([k,v])=>url.searchParams.set(k,String(v)))
 const token=window.frappe?.csrf_token||window.csrf_token||document.querySelector('meta[name="csrf-token"]')?.content||''
 const res=await fetch(url,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(token?{'X-Frappe-CSRF-Token':token}:{})},...(body?{body:JSON.stringify(body)}:{})})
 const data=await res.json()
 if(!res.ok||data.exc||data.exception)throw new Error(errMessage(data,'Invoice API request failed'))
 return data.message||{}
}
function closeItems(){setTimeout(()=>{itemFocused.value=false;itemHits.value=[]},190)}
function closeCustomers(){setTimeout(()=>{customerFocused.value=false;customerHits.value=[]},190)}
function lookupItems(){
 clearTimeout(itemTimer); const q=query.value.trim(); const seq=++itemSequence; itemHits.value=[]
 if(!itemFocused.value||q.length<1)return
 itemTimer=setTimeout(async()=>{itemBusy.value=true;try{const data=await request('search_invoice_items',{q,invoice_kind:'retail'});if(seq===itemSequence)itemHits.value=(data.results||[]).slice(0,12)}catch(e){if(seq===itemSequence)error.value=e.message}finally{if(seq===itemSequence)itemBusy.value=false}},220)
}
function lookupCustomers(){
 clearTimeout(customerTimer); const q=customerQuery.value.trim(); const seq=++customerSequence; customerHits.value=[];selectedCustomer.value=null
 if(!customerFocused.value||q.length<1)return
 customerTimer=setTimeout(async()=>{customerBusy.value=true;try{const data=await request('search_invoice_customers',{q});if(seq===customerSequence)customerHits.value=(data.results||[]).slice(0,12)}catch(e){if(seq===customerSequence)error.value=e.message}finally{if(seq===customerSequence)customerBusy.value=false}},220)
}
function selectCustomer(c){selectedCustomer.value=c;customerQuery.value=c.customer_name||c.name;customerFocused.value=false;customerHits.value=[]}
function addItem(product){
 const code=product.name||product.item_code
 let existing=cart.value.find(x=>x.item_code===code&&!x.has_serial_no)
 if(existing)existing.qty+=1
 else cart.value.push({item_code:code,item_name:product.item_name||code,qty:1,rate:0,discount_percentage:0,serial_no:'',has_serial_no:!!product.has_serial_no,stock_qty:product.stock_qty})
 query.value='';itemHits.value=[]; itemFocused.value=false; info.value='Added '+code+' to cart';saved.value=null
}
function removeItem(i){cart.value.splice(i,1); saved.value=null}
function newSale(){cart.value=[];selectedCustomer.value=null;customerQuery.value='';discountMode.value='none';discountValue.value=0;saved.value=null;error.value='';info.value='';query.value=''}
async function createDraft(){
 error.value='';info.value=''
 if(!selectedCustomer.value?.name){error.value='Select an existing Customer from suggestions.';return}
 if(!cart.value.length){error.value='Add one or more items to cart.';return}
 if(cart.value.some(x=>!x.item_code||!(Number(x.qty)>0)||!Number.isFinite(Number(x.rate))||Number(x.rate)<0||Number(x.discount_percentage)<0||Number(x.discount_percentage)>100)){
  error.value='Review all item quantities, rates, and line discounts.';return
 }
 if(!Number.isFinite(Number(discountValue.value))||Number(discountValue.value)<0||(discountMode.value==='percent'&&Number(discountValue.value)>=100)||(discountMode.value==='amount'&&Number(discountValue.value)>=subtotal.value)||total.value<=0){error.value='Review the overall discount and invoice total.';return}
 saving.value=true
 try{
 const data=await request('create_unified_invoice_draft',{}, {invoice_kind:'retail',customer:selectedCustomer.value.name,items:cart.value.map(x=>({item_code:x.item_code,qty:Number(x.qty),rate:Number(x.rate),discount_percentage:Number(x.discount_percentage||0),serial_no:x.serial_no||''})),discount_mode:discountMode.value,discount_value:discountMode.value==='none'?0:Number(discountValue.value),remarks:'Created from SERVICING OS New Sale counter'})
 if(!data.invoice)throw new Error('No Sales Invoice number returned')
 saved.value=data; info.value='Draft invoice '+data.invoice+' saved in ERPNext';emit('saved',data);window.dispatchEvent(new CustomEvent('servicing-os-invoice-draft-created',{detail:data}))
 }catch(e){error.value=e?.message||'Unable to save draft invoice'}finally{saving.value=false}
}
onUnmounted(()=>{clearTimeout(itemTimer);clearTimeout(customerTimer);++itemSequence;++customerSequence})
</script>

<template>
 <div class="sos655-new-sale">
   <div class="sos655-sales-tabs" role="tablist" aria-label="Sale mode">
     <button type="button" role="tab" :aria-selected="mode==='cart'" :class="{current:mode==='cart'}" @click="mode='cart'">Multi-item New Sale</button>
     <button type="button" role="tab" :aria-selected="mode==='native'" :class="{current:mode==='native'}" @click="mode='native'">Existing POS Checkout</button>
   </div>
   <div v-if="mode==='native'" class="sos655-native-pos"><slot name="legacy" /></div>
   <div v-else class="sos655-sales-layout">
     <section class="sos655-sales-main">
       <div class="sos655-sales-title"><div><h2>New Sale</h2><p>Search and add multiple inventory items.</p></div><span>{{ cart.length }} item types</span></div>
       <div class="sos655-search-box">
         <label for="sos655-itemsearch">Find product / item code</label>
         <div class="sos655-search-line"><input id="sos655-itemsearch" v-model="query" type="search" autocomplete="off" placeholder="Select this field, then search items…" @focus="itemFocused=true;lookupItems()" @input="lookupItems" @blur="closeItems" @keydown.esc="itemFocused=false" /><span v-if="itemBusy">Searching…</span></div>
         <div v-if="itemFocused&&query.trim().length>0" class="sos655-product-results">
            <p v-if="!itemBusy&&!itemHits.length">No matching sellable items.</p>
            <button v-for="item in itemHits" :key="item.name" type="button" @mousedown.prevent="addItem(item)">
             <span class="sos655-item-icon" aria-hidden="true">▦</span><strong>{{ item.item_name||item.name }}</strong><small>{{ item.name }}</small><small v-if="item.stock_qty!==null&&item.stock_qty!==undefined">Stock: {{ item.stock_qty }}</small><b>Add +</b>
            </button>
         </div>
       </div>
       <div class="sos655-cart-header"><h3>Sale Items</h3><span>{{ itemCount }} unit(s)</span></div>
       <div v-if="!cart.length" class="sos655-cart-empty">Select a product above to start this sale. Add as many different items as needed.</div>
       <div v-for="(row,i) in cart" :key="row.item_code+'-'+i" class="sos655-cart-line">
         <div class="sos655-product-name"><strong>{{ row.item_name }}</strong><small>{{ row.item_code }}</small></div>
         <label>Qty<input v-model.number="row.qty" type="number" min="0.01" step="0.01" :max="row.stock_qty===null?undefined:row.stock_qty" /></label>
         <label>Unit Price ৳<input v-model.number="row.rate" type="number" min="0" step="0.01" /></label>
         <label>Disc. %<input v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.01" /></label>
         <strong class="sos655-row-total">৳ {{ money(lineTotal(row)) }}</strong>
         <button class="sos655-remove" type="button" aria-label="Remove item" @click="removeItem(i)">×</button>
         <label v-if="row.has_serial_no" class="sos655-serial">Serial number(s)<textarea v-model="row.serial_no" rows="2" placeholder="One serial number per unit" /></label>
       </div>
       <div class="sos655-sales-footer"><button type="button" @click="newSale">Clear sale</button><p>Stock is validated on invoice creation. Final stock/payment posting occurs when the invoice is submitted through ERPNext.</p></div>
     </section>
     <aside class="sos655-checkout">
       <h2>Checkout & Billing</h2>
       <p class="sos655-muted">Invoice for multiple products</p>
       <div class="sos655-customer-field">
         <label for="sos655-customer">Customer *</label>
         <input id="sos655-customer" v-model="customerQuery" type="search" autocomplete="off" placeholder="Select and search customer" @focus="customerFocused=true" @input="lookupCustomers" @blur="closeCustomers" />
         <div v-if="customerFocused&&customerQuery.trim()" class="sos655-customer-results"><p v-if="customerBusy">Searching…</p><button v-for="c in customerHits" :key="c.name" type="button" @mousedown.prevent="selectCustomer(c)">{{ c.customer_name||c.name }} <small>{{ c.name }}</small></button></div>
         <small v-if="selectedCustomer">Selected: {{ selectedCustomer.name }}</small>
       </div>
       <div class="sos655-summary-row"><span>Subtotal</span><strong>৳ {{ money(subtotal) }}</strong></div>
       <div class="sos655-discount-fields"><label>Overall discount<select v-model="discountMode" @change="discountValue=0"><option value="none">No discount</option><option value="percent">Percentage (%)</option><option value="amount">Fixed amount (BDT)</option></select></label><label v-if="discountMode!=='none'">Discount {{ discountMode==='percent'?'%':'BDT' }}<input v-model.number="discountValue" type="number" min="0" step="0.01" :max="discountMode==='percent'?99.99:undefined" /></label></div>
       <div class="sos655-summary-row"><span>Additional discount</span><strong>− ৳ {{ money(overall) }}</strong></div>
       <div class="sos655-summary-row grand"><span>Before tax</span><strong>৳ {{ money(total) }}</strong></div>
       <p class="sos655-notice">Saves an ERPNext <b>draft</b> Sales Invoice; no stock deduction or payment posting yet. Use Existing POS Checkout for your current direct checkout workflow.</p>
       <button type="button" class="sos655-save" :disabled="saving||!cart.length||!!saved" @click="createDraft">{{ saving?'Saving…':'Save Draft Invoice' }}</button>
       <div v-if="saved" class="sos655-success" role="status">Saved: <strong>{{ saved.invoice }}</strong> · {{ saved.currency }} {{ money(saved.grand_total) }}</div>
       <p v-if="error" role="alert" class="sos655-error">{{ error }}</p><p v-else-if="info" class="sos655-info">{{ info }}</p>
     </aside>
   </div>
 </div>
</template>

<style>
.sos655-new-sale,.sos655-new-sale *{box-sizing:border-box}.sos655-new-sale{color:#3c2c25;width:100%;min-width:0;font-size:12px}
.sos655-sales-tabs{display:flex;gap:8px;padding:0 0 13px;margin-bottom:15px;border-bottom:1px solid #e7d6c5;flex-wrap:wrap}
.sos655-sales-tabs button{border:1px solid #e2ccb6!important;background:#fffbf6!important;color:#73533f!important;border-radius:9px!important;padding:9px 13px!important;font-weight:680!important;font-size:12px!important}
.sos655-sales-tabs button.current{background:#805a3e!important;color:white!important;border-color:#805a3e!important}
.sos655-sales-layout{display:grid;grid-template-columns:minmax(0,3fr) minmax(275px,1fr);align-items:start;gap:13px;width:100%}
.sos655-sales-main,.sos655-checkout{background:#fffcf7;border:1px solid #e7d6c5;border-radius:13px;padding:16px;min-width:0;box-shadow:0 1px 2px #6b4a3409}
.sos655-sales-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px}
.sos655-sales-title h2,.sos655-checkout h2{font-size:16px;font-weight:780;color:#3c2c25;margin:0 0 4px}.sos655-sales-title p,.sos655-muted{margin:0;font-size:11px;color:#8b725e}
.sos655-sales-title>span{font-size:11px;color:#8b725e;background:#f4e3d3;border-radius:7px;padding:6px 8px;white-space:nowrap}
.sos655-new-sale :is(input,select,textarea){width:100%;min-width:0;min-height:42px;border:1px solid #ddc8b5!important;border-radius:9px!important;background:#fffdfa!important;color:#3c2c25!important;padding:8px 10px!important;font:inherit!important;font-size:12px!important;line-height:1.4!important}
.sos655-new-sale :is(input,select,textarea):focus{outline:2px solid #bd9274;outline-offset:1px}
.sos655-new-sale label{display:flex;flex-direction:column;gap:5px;color:#72543f;font-size:11px;font-weight:650;min-width:0}
.sos655-search-box{position:relative;background:#f8efe7;border:1px solid #ecd9c8;border-radius:11px;padding:12px;margin-bottom:18px}
.sos655-search-line{position:relative}.sos655-search-line>span{position:absolute;right:12px;top:11px;color:#8b725e;font-size:11px}
.sos655-product-results{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:9px;max-height:280px;overflow:auto;margin-top:11px;padding:4px}
.sos655-product-results p{grid-column:1/-1;color:#8b725e;margin:6px}
.sos655-product-results button{display:flex!important;flex-direction:column;gap:3px;text-align:left!important;min-height:105px;padding:11px!important;background:#fffcf7!important;border:1px solid #e7d6c5!important;border-radius:11px!important;color:#3c2c25!important}
.sos655-product-results button:hover{border-color:#ba9876!important;background:#fff7ee!important}.sos655-product-results button .sos655-item-icon{display:grid;place-items:center;width:27px;height:27px;background:#f4e3d3;border-radius:7px;color:#8e6140;font-size:17px}
.sos655-product-results button strong{font-size:11.5px;line-height:1.3;overflow-wrap:anywhere}.sos655-product-results button small{font-size:10px;color:#8b725e;overflow-wrap:anywhere}.sos655-product-results button b{font-size:10px;color:#805a3e;margin-top:auto}
.sos655-cart-header{display:flex;justify-content:space-between;gap:10px;align-items:center;border-bottom:1px solid #e7d6c5;padding-bottom:10px}.sos655-cart-header h3{font-size:14px;font-weight:760}.sos655-cart-header span{font-size:11px;color:#8b725e}
.sos655-cart-empty{padding:27px 12px;text-align:center;color:#9b826e;font-size:12px}
.sos655-cart-line{display:grid;grid-template-columns:minmax(155px,2.3fr) minmax(63px,.65fr) minmax(83px,1fr) minmax(73px,.85fr) minmax(96px,1fr) 30px;align-items:end;gap:8px;padding:12px 3px;border-bottom:1px solid #eddfd2}
.sos655-cart-line .sos655-product-name{display:flex;flex-direction:column;gap:5px;min-width:0;overflow-wrap:anywhere}.sos655-product-name strong{font-size:12px}.sos655-product-name small{font-size:10px;color:#8b725e}
.sos655-row-total{font-size:12px;white-space:nowrap;align-self:center}.sos655-remove{background:#f8e6dd!important;color:#8e442f!important;border:1px solid #eed0c2!important;border-radius:8px!important;height:41px;font-size:20px!important}
.sos655-cart-line .sos655-serial{grid-column:1/-1}.sos655-sales-footer{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-top:18px}.sos655-sales-footer button{background:#f4e3d3!important;color:#79583e!important;border:1px solid #e2ccb6!important;border-radius:8px;padding:8px 12px!important}.sos655-sales-footer p{max-width:65%;font-size:10px;color:#8b725e}
.sos655-checkout{position:sticky;top:12px}.sos655-customer-field{position:relative;margin:18px 0}.sos655-customer-field>small{display:block;color:#8b725e;margin-top:5px}
.sos655-customer-results{position:absolute;z-index:30;top:67px;left:0;right:0;max-height:210px;overflow:auto;border:1px solid #e2c8b1;background:#fffcf7;box-shadow:0 8px 18px #3c2c2525;border-radius:9px}
.sos655-customer-results p{padding:9px;color:#8b725e}.sos655-customer-results button{display:block;text-align:left!important;width:100%;padding:10px!important;border:0!important;border-bottom:1px solid #eddfd2!important;background:#fffcf7!important;color:#3c2c25!important}
.sos655-customer-results small{display:block;color:#8b725e;margin-top:3px}.sos655-summary-row{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 0;border-bottom:1px solid #eddfd2}.sos655-summary-row>span{color:#7f6553}.sos655-summary-row.grand{font-size:14px;font-weight:750}.sos655-discount-fields{margin:15px 0;display:grid;gap:10px}.sos655-discount-fields select{min-height:42px!important}
.sos655-notice{background:#f4e9df;border:1px solid #ead8c8;border-radius:9px;color:#785c46;font-size:10.5px;line-height:1.5;margin:14px 0;padding:10px}
.sos655-save{width:100%;padding:12px!important;background:#805a3e!important;border:1px solid #805a3e!important;border-radius:10px!important;color:#fffaf2!important;font-weight:760!important;min-height:44px!important}.sos655-save:disabled{opacity:.55;cursor:not-allowed}
.sos655-error,.sos655-info,.sos655-success{margin-top:13px;padding:11px;border-radius:9px;font-size:11px;overflow-wrap:anywhere}.sos655-error{color:#873f2d;background:#fff0e9}.sos655-info,.sos655-success{color:#5d4832;background:#f0e9dc}.sos655-native-pos{min-width:0}
@media(max-width:1160px){.sos655-sales-layout{grid-template-columns:minmax(0,2fr) minmax(260px,1fr)}.sos655-product-results{grid-template-columns:repeat(2,minmax(0,1fr))!important}.sos655-cart-line{grid-template-columns:minmax(120px,2fr) 58px 80px 74px;}.sos655-row-total{grid-column:2/4}.sos655-remove{grid-column:4}}
@media(max-width:850px){.sos655-sales-layout{grid-template-columns:1fr}.sos655-checkout{position:static}.sos655-sales-footer{flex-direction:column;align-items:start}.sos655-sales-footer p{max-width:100%}}
@media(max-width:540px){.sos655-product-results{grid-template-columns:repeat(2,minmax(0,1fr))!important}.sos655-cart-line{grid-template-columns:repeat(3,minmax(0,1fr))}.sos655-product-name{grid-column:1/-1}.sos655-row-total{grid-column:1/3}.sos655-remove{grid-column:3}.sos655-sales-main,.sos655-checkout{padding:11px}}
</style>
