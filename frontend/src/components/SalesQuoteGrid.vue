<script setup>
import {ref, computed, onMounted, unref} from 'vue'
import {currentLanguage} from '../i18n/servicingLanguage.js'
const bn = computed(()=>unref(currentLanguage) === 'bn')
const form = ref({name:'',customer:'',customer_name:'',valid_till:'',notes:'',items:[]})
const customerSearch=ref(''),itemSearch=ref(''),registerSearch=ref('')
const customers=ref([]),catalog=ref([]),register=ref([])
const loading=ref(false),error=ref(''),success=ref('')
const quoteInfo=ref(null)
const money=v=>'৳ '+(Number(v)||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const subtotal=computed(()=>form.value.items.reduce((sum,it)=>sum+Math.max(0,Number(it.qty)||0)*Math.max(0,Number(it.rate)||0),0))
const discountTotal=computed(()=>form.value.items.reduce((sum,it)=>sum+(Math.max(0,Number(it.qty)||0)*Math.max(0,Number(it.rate)||0)*(Math.max(0,Math.min(100,Number(it.discount_percentage)||0))/100)),0))
const estimate=computed(()=>subtotal.value-discountTotal.value)
let counter=0
function newQuote(){
 form.value={name:'',customer:'',customer_name:'',valid_till:'',notes:'',items:[]};quoteInfo.value=null
 customerSearch.value='';itemSearch.value='';customers.value=[];catalog.value=[];success.value='';error.value=''
}
async function api(method,args={},write=false){
 const url='/api/method/servicing_os.api.' + method
 const csrf=window.csrf_token || window.frappe?.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
 const headers=write?{'Content-Type':'application/json','X-Frappe-CSRF-Token':csrf}:{}
 const qs=new URLSearchParams()
 if(!write)for(const [k,v] of Object.entries(args))qs.set(k,v??'')
 const response=await fetch(url+(write?'':'?'+qs),{method:write?'POST':'GET',credentials:'same-origin',headers,body:write?JSON.stringify(args):undefined})
 const data=await response.json()
 if(!response.ok||data.exc||data.exception){
   let msg=typeof data.message==='string'?data.message:''
   if(data._server_messages){try{const parsed=JSON.parse(data._server_messages);msg=JSON.parse(parsed[0]).message||msg}catch{}}
   throw new Error(msg||data.exception||`Request failed (${response.status})`)
 }
 return data.message
}
async function task(fn){if(loading.value)return;loading.value=true;error.value='';try{await fn()}catch(e){error.value=e.message||String(e)}finally{loading.value=false}}
function addProduct(p){
 form.value.items.push({key:++counter,item_code:p.item_code,item_name:p.item_name,uom:p.uom,stock_qty:p.stock_qty,rate:Number(p.rate)||0,qty:1,discount_percentage:0})
 itemSearch.value='';catalog.value=[]
}
async function findCustomers(){if(customerSearch.value.trim().length<2)return;await task(async()=>{customers.value=await api('sales_center.customers',{q:customerSearch.value})})}
async function findItems(){if(itemSearch.value.trim().length<2)return;await task(async()=>{catalog.value=await api('sales_center.catalog',{q:itemSearch.value})})}
async function list(){await task(async()=>{register.value=await api('sales_center.records',{kind:'quotation',query:registerSearch.value,limit:100})})}
async function edit(name){await task(async()=>{
 const d=await api('quotation_grid.detail',{name})
 if(d.docstatus!==0){throw new Error('Submitted quotation is read-only. Open its print view instead.')}
 form.value={name:d.name,customer:d.customer,customer_name:d.customer_name,valid_till:d.valid_till,notes:'',items:d.items.map(it=>({...it,key:++counter}))}
 customerSearch.value=d.customer_name;quoteInfo.value=d
 success.value=`Editing draft ${d.name}`
})}
function valid(){
 if(!form.value.customer)throw new Error('Choose an existing Customer from the search results.')
 if(!form.value.items.length)throw new Error('Add at least one item to the quotation grid.')
 for(const [i,it] of form.value.items.entries()){
  if(!(Number(it.qty)>0) || Number(it.rate)<0 || Number(it.discount_percentage)<0 || Number(it.discount_percentage)>100 || !Number.isFinite(Number(it.rate)))throw new Error(`Invalid Qty / Rate / Discount in item row ${i+1}`)
 }
}
async function save(){await task(async()=>{
 valid()
 const d=await api('quotation_grid.save',{name:form.value.name||undefined,customer:form.value.customer,valid_till:form.value.valid_till||undefined,notes:form.value.notes,
   items:form.value.items.map(it=>({item_code:it.item_code,uom:it.uom,qty:Number(it.qty),rate:Number(it.rate),discount_percentage:Number(it.discount_percentage)||0}))},true)
 form.value.name=d.name;quoteInfo.value=d
 success.value=`Draft ${d.name} saved in ERPNext · total ${money(d.grand_total)}. Review taxes and terms before submitting.`
 register.value=await api('sales_center.records',{kind:'quotation',limit:100})
})}
async function submit(name){
 if(!window.confirm(`Submit quotation ${name}? Submitted quotations are formal offers and cannot be edited as drafts.`))return
 await task(async()=>{const d=await api('sales_center.submit_quotation',{name},true);register.value=await api('sales_center.records',{kind:'quotation',limit:100});if(form.value.name===name)newQuote();success.value=`Quotation ${d.name} submitted.`})
}
function print(name){window.open('/printview?doctype=Quotation&name='+encodeURIComponent(name)+'&trigger_print=1','_blank','noopener,noreferrer')}
onMounted(list)
</script>
<template>
<div class="sqg">
 <header class="sqg-head"><div><div class="sqg-kicker">SALES · BUSINESS PROPOSALS</div><h2>{{bn?'কোটেশন ও মূল্য প্রস্তাব':'Quotation Workspace'}}</h2><p>Live customer and product search · editable item grid · saved ERPNext quotations</p></div><button class="sqg-btn" @click="newQuote">+ New quotation</button></header>
 <p v-if="error" class="sqg-alert error" role="alert">{{error}}</p><p v-if="success" class="sqg-alert" role="status">{{success}}</p>
 <section class="sqg-panel">
 <div class="sqg-title"><h3>{{form.name?'Edit quotation · '+form.name:'Create quotation'}}</h3><small>Draft · {{form.items.length}} line items</small></div>
 <div class="sqg-topgrid">
  <div class="sqg-field"><label>Customer <span>*</span></label><div class="sqg-search"><input v-model="customerSearch" placeholder="Search customer name or ID" @input="form.customer='';form.customer_name='';customers=[]" @keyup.enter="findCustomers"/><button :disabled="loading" @click="findCustomers">Find</button></div>
   <div v-if="customers.length" class="sqg-options"><button v-for="c in customers" :key="c.name" @click="form.customer=c.name;form.customer_name=c.customer_name;customerSearch=c.customer_name;customers=[]">{{c.customer_name}}<small>{{c.name}}</small></button></div>
   <div class="sqg-picked" v-if="form.customer">✓ {{form.customer_name||form.customer}} <small>({{form.customer}})</small></div>
  </div>
  <div class="sqg-field"><label>Valid until</label><input v-model="form.valid_till" type="date"/></div>
  <div class="sqg-field"><label>Quotation reference</label><div class="sqg-ref">{{form.name||'Generated when saved'}}</div></div>
 </div>
 <div class="sqg-add"><div><h4>Items & pricing</h4><small>Search catalog by item code or product name. Edit quantity, unit rate and discount for each row.</small></div><div class="sqg-search"><input v-model="itemSearch" placeholder="Search item / scan item code" @keyup.enter="findItems"/><button :disabled="loading" @click="findItems">Add item</button></div></div>
 <div class="sqg-options sqg-products" v-if="catalog.length"><button v-for="p in catalog" :key="p.item_code" @click="addProduct(p)"><b>{{p.item_name}}</b><small>{{p.item_code}} · {{money(p.rate)}} · Stock: {{p.stock_qty}} {{p.uom}}</small></button></div>
 <div class="sqg-table-scroll"><table><thead><tr><th>#</th><th>Product / Item code</th><th>Stock</th><th>UOM</th><th>Qty</th><th>Unit rate</th><th>Discount %</th><th>Line total</th><th></th></tr></thead><tbody>
  <tr v-for="(it,index) in form.items" :key="it.key"><td>{{index+1}}</td><td class="sqg-itemname">{{it.item_name}}<small>{{it.item_code}}</small></td><td>{{it.stock_qty ?? '—'}}</td><td>{{it.uom}}</td><td><input v-model.number="it.qty" type="number" min="0.0001" step="0.01" aria-label="Item quantity"/></td><td><input v-model.number="it.rate" type="number" min="0" step="0.01" aria-label="Unit rate"/></td><td><input v-model.number="it.discount_percentage" type="number" min="0" max="100" step="0.5" aria-label="Discount percent"/></td><td class="sqg-total">{{money(Math.max(0,it.qty||0)*Math.max(0,it.rate||0)*(1-(Number(it.discount_percentage)||0)/100))}}</td><td><button class="sqg-remove" title="Remove row" @click="form.items.splice(index,1)">×</button></td></tr>
  <tr v-if="!form.items.length"><td colspan="9" class="sqg-empty">No items yet. Search the catalog to add your first product.</td></tr>
 </tbody></table></div>
 <div class="sqg-footer"><div class="sqg-field sqg-notes"><label>Commercial notes (optional)</label><textarea v-model="form.notes" rows="3" maxlength="3000" placeholder="Delivery, payment, or warranty terms for the buyer"></textarea></div><div class="sqg-totals"><div><span>Subtotal</span><b>{{money(subtotal)}}</b></div><div><span>Discount</span><b>− {{money(discountTotal)}}</b></div><div class="sqg-grand"><span>Estimated net total</span><b>{{money(estimate)}}</b></div><p>ERPNext calculates the authoritative tax, discount and grand total when saved.</p><div class="sqg-actions"><button class="sqg-btn primary" :disabled="loading||!form.customer||!form.items.length" @click="save">{{loading?'Saving…':form.name?'Save changes':'Save draft in ERPNext'}}</button><button v-if="form.name" class="sqg-btn" @click="print(form.name)">Print</button></div></div></div>
 </section>
 <section class="sqg-panel"><div class="sqg-title"><h3>Quotation register</h3><span>Drafts and submitted proposals</span></div><div class="sqg-search sqg-register-search"><input v-model="registerSearch" placeholder="Search quotation number" @keyup.enter="list"/><button :disabled="loading" @click="list">Search / Refresh</button></div>
  <div class="sqg-table-scroll"><table><thead><tr><th>Quotation</th><th>Date</th><th>Customer</th><th>Status</th><th>Grand total</th><th>Actions</th></tr></thead><tbody><tr v-for="q in register" :key="q.name"><td class="sqg-itemname">{{q.name}}</td><td>{{q.transaction_date}}</td><td>{{q.party_name}}</td><td>{{q.status}}</td><td>{{money(q.grand_total)}}</td><td><div class="sqg-row-actions"><button v-if="q.docstatus===0" @click="edit(q.name)">Edit</button><button @click="print(q.name)">Print</button><button v-if="q.docstatus===0" :disabled="loading" @click="submit(q.name)">Submit</button></div></td></tr><tr v-if="!register.length"><td colspan="6" class="sqg-empty">No quotations found with the current filter.</td></tr></tbody></table></div>
 </section>
</div>
</template>
<style scoped>
.sqg{color:#4b3b2c}.sqg-head{display:flex;align-items:start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:18px}.sqg-kicker{font-size:10px;letter-spacing:.12em;font-weight:800;color:#9c7f5d}.sqg-head h2{font-size:24px;font-weight:850;margin:7px 0}.sqg-head p{font-size:12px;color:#967f66;margin:0}.sqg-panel{padding:18px 20px;border-radius:16px;background:#fffdfa;border:1px solid #e8ddcd;margin:15px 0;box-shadow:0 6px 20px #5b452510}.sqg-title{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px}.sqg-title h3{font-size:16px;font-weight:850;margin:0}.sqg-title small,.sqg-title span{color:#98836e;font-size:11px}.sqg-topgrid{display:grid;grid-template-columns:minmax(230px,1.4fr) minmax(135px,.65fr) minmax(165px,.8fr);gap:14px}.sqg-field{display:flex;flex-direction:column;gap:7px;min-width:0;position:relative}.sqg-field label{font-size:12px;font-weight:750;color:#79614b}.sqg-field label span{color:#a34d3e}.sqg-field input,.sqg-field textarea,.sqg-search input{width:100%;min-width:0;border:1px solid #dfd2bf;border-radius:9px;background:#fff;color:#4b3929;font-size:12px;padding:9px 11px;min-height:40px}.sqg-field textarea{resize:vertical}.sqg-ref{background:#faf5ec;border:1px solid #eee0cf;border-radius:9px;padding:11px;font-size:12px;min-height:40px;color:#866d53}.sqg-search{display:flex;min-width:0;gap:7px}.sqg-search input{flex:1;min-width:0}.sqg-search button,.sqg-btn{border:1px solid #dfcfba;border-radius:9px;min-height:40px;padding:8px 13px;white-space:nowrap;cursor:pointer;background:#f5eee5;color:#795738;font-size:12px;font-weight:780}.sqg-btn.primary{background:#73533a;border-color:#73533a;color:#fff}.sqg-btn:disabled,.sqg-search button:disabled{opacity:.45;cursor:not-allowed}.sqg-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:7px;max-height:210px;overflow:auto;margin:8px 0}.sqg-options button{cursor:pointer;text-align:left;padding:10px;border:1px solid #e7d7c2;border-radius:10px;background:#fbf5ec;color:#604936;font-size:12px}.sqg-options button:hover{background:#f0e3d1}.sqg-options small{display:block;font-size:10px;color:#8e765d;margin-top:4px}.sqg-picked{font-size:11px;color:#896a49;font-weight:800}.sqg-add{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;padding-top:17px;margin-top:15px;border-top:1px solid #eee4d8}.sqg-add h4{font-size:14px;font-weight:850;margin:0 0 5px}.sqg-add small{font-size:11px;color:#967e65}.sqg-add .sqg-search{min-width:min(100%,330px)}.sqg-table-scroll{width:100%;overflow:auto;margin-top:12px}.sqg-table-scroll table{border-collapse:collapse;width:100%;min-width:900px;font-size:12px}.sqg-table-scroll th,.sqg-table-scroll td{padding:10px;text-align:left;border-bottom:1px solid #efe6d9;vertical-align:middle}.sqg-table-scroll thead th{background:#f5eee5;font-size:11px;color:#7d674c;font-weight:850}.sqg-table-scroll input{border:1px solid #dfd4c5;border-radius:7px;padding:7px;width:78px;color:#3d3229;background:white;font-size:12px}.sqg-itemname{font-weight:750;min-width:150px}.sqg-itemname small{display:block;font-size:10px;font-weight:500;color:#98836e;margin-top:4px}.sqg-total{font-weight:850;white-space:nowrap}.sqg-remove{cursor:pointer;border:0;background:#f5e9e0;color:#9c5635;font-size:22px;border-radius:7px;padding:0;width:30px;height:30px}.sqg-empty{color:#988573;text-align:center!important;padding:24px!important}.sqg-footer{display:grid;grid-template-columns:1.2fr minmax(270px,.8fr);gap:18px;margin-top:17px}.sqg-totals{padding:13px;background:#f9f2e8;border:1px solid #e9dbc9;border-radius:12px}.sqg-totals>div:not(.sqg-actions){display:flex;align-items:center;justify-content:space-between;padding:6px 0;font-size:12px}.sqg-grand{border-top:1px solid #e5d2b9;margin-top:6px;padding-top:14px!important;font-weight:850;font-size:15px!important}.sqg-totals p{font-size:10px;color:#98816b;line-height:1.6}.sqg-actions,.sqg-row-actions{display:flex;gap:6px;flex-wrap:wrap}.sqg-row-actions button{background:transparent;border:0;color:#805b3b;text-decoration:underline;text-underline-offset:3px;cursor:pointer;font-size:11px;font-weight:800;padding:5px}.sqg-register-search{max-width:460px}.sqg-alert{border-radius:10px;padding:10px 14px;background:#f7eedd;color:#745b3c;font-size:12px}.sqg-alert.error{background:#fae8e2;color:#993f32}@media(max-width:800px){.sqg-topgrid{grid-template-columns:1fr}.sqg-footer{grid-template-columns:1fr}.sqg-panel{padding:14px}.sqg-add .sqg-search{width:100%}}
</style>
