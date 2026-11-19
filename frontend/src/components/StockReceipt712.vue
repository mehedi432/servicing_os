<script setup>
// SOS_STOCK_RECEIPT_712 — authorized stock receipt, not a supplier purchase invoice.
import { ref, computed, onMounted } from 'vue'
const props = defineProps({jobName:{type:String,required:true}})
const emit = defineEmits(['close','received'])
const ctx = ref(null), busy=ref(false), error=ref(''), itemText=ref(''), found=ref([]), item=ref(null)
const qty=ref(1), buying=ref(''), selling=ref(''), buyList=ref(''), sellList=ref('')
const reason=ref(''), confirmText=ref(''), success=ref(null)
const requestKey=ref((typeof crypto!=='undefined' && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now())+'-'+Math.random().toString(36).slice(2,13))
const listsBuy=computed(()=>ctx.value?.price_lists?.filter(p=>p.buying && (!p.currency || p.currency===ctx.value.currency))||[])
const listsSell=computed(()=>ctx.value?.price_lists?.filter(p=>p.selling && (!p.currency || p.currency===ctx.value.currency))||[])
const valid=computed(()=>item.value && Number(qty.value)>0 && Number(buying.value)>0 && selling.value!=='' && Number(selling.value)>0 && buyList.value && sellList.value && reason.value.trim().length>=12 && confirmText.value.trim()==='RECEIVE '+item.value.item_code)
function csrf(){return window.frappe?.csrf_token||window.csrf_token||decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')||'')}
function problem(body, status){
  try {const v=JSON.parse(body?._server_messages||'[]');if(v.length){const x=JSON.parse(v.at(-1));const div=document.createElement('div');div.innerHTML=x.message;return div.textContent||'Validation failed'}}catch(_){}
  return body?.message?.message||body?.exception||`Stock API unavailable (HTTP ${status})`
}
async function api(method, args={},post=false){
  const url=new URL('/api/method/servicing_os.api.stock_receipt_712.'+method,location.origin)
  if(!post)Object.entries(args).forEach(([k,v])=>url.searchParams.set(k,v))
  const response=await fetch(url,{method:post?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json',...(post?{'Content-Type':'application/json','X-Frappe-CSRF-Token':csrf()}:{})},...(post?{body:JSON.stringify(args)}:{})})
  const body=await response.json().catch(()=>({}))
  if(!response.ok||body.exc||body.exception||body.exc_type)throw new Error(problem(body,response.status))
  return body.message
}
async function load(){busy.value=true;error.value='';try{ctx.value=await api('receipt_context',{job_name:props.jobName});buyList.value=listsBuy.value.find(p=>p.name==='Standard Buying')?.name||listsBuy.value[0]?.name||'';sellList.value=listsSell.value.find(p=>p.name==='Standard Selling')?.name||listsSell.value[0]?.name||''}catch(e){error.value=e.message}finally{busy.value=false}}
async function search(){error.value='';found.value=[];if(itemText.value.trim().length<2)return;try{const url=new URL('/api/method/servicing_os.api.parts_workbench_708.search_items',location.origin);url.searchParams.set('job_name',props.jobName);url.searchParams.set('search',itemText.value.trim());const r=await fetch(url,{credentials:'same-origin',cache:'no-store'});const b=await r.json();if(!r.ok||b.exc)throw new Error(problem(b,r.status));found.value=b.message?.items||[]}catch(e){error.value=e.message}}
async function choose(part){busy.value=true;error.value='';try{ctx.value=await api('receipt_context',{job_name:props.jobName,item_code:part.item_code});item.value=ctx.value.item;itemText.value=part.item_name+' · '+part.item_code;found.value=[];confirmText.value=''}catch(e){error.value=e.message}finally{busy.value=false}}
async function receive(){if(!valid.value||busy.value)return;busy.value=true;error.value='';try{const result=await api('receive_part',{job_name:props.jobName,item_code:item.value.item_code,qty:Number(qty.value),buying_rate:Number(buying.value),selling_rate:Number(selling.value),buying_price_list:buyList.value,selling_price_list:sellList.value,reason:reason.value.trim(),confirmation:confirmText.value.trim(),request_key:requestKey.value},true);success.value=result;emit('received',result)}catch(e){error.value=e.message}finally{busy.value=false}}
onMounted(load)
</script>
<template>
<Teleport to="body">
  <div class="sos712-receipt-mask" @click.self="!busy&&emit('close')">
    <section class="sos712-receipt" role="dialog" aria-modal="true" aria-label="Receive missing spare parts">
      <header><div><small>INVENTORY CONTROL · {{jobName}}</small><h2>Receive Spare Part</h2><p>Material Receipt · Warehouse valuation · Buying &amp; selling prices</p></div><button type="button" class="close" :disabled="busy" @click="emit('close')">×</button></header>
      <div class="body">
        <div v-if="ctx" class="context"><span><b>Company</b>{{ctx.company}}</span><span><b>Receiving warehouse</b>{{ctx.warehouse}}</span><span><b>Currency</b>{{ctx.currency}}</span></div>
        <div v-if="success" class="notice success" role="status"><strong>Stock receipt submitted</strong><p>{{success.stock_entry}} · {{success.already_recorded?'Previously recorded':'Stock ledger updated'}}.</p><a :href="`/app/stock-entry/${encodeURIComponent(success.stock_entry)}`" target="_blank" rel="noopener">Open Stock Entry ↗</a></div>
        <template v-else>
          <label>Find stock item<input v-model="itemText" type="search" placeholder="Search Item Code or item name" @input="search" autocomplete="off" /></label>
          <div v-if="found.length" class="results"><button v-for="p in found" :key="p.item_code" type="button" @click="choose(p)"><b>{{p.item_name}}</b><small>{{p.item_code}} · {{p.available_qty}} {{p.uom}} available</small></button></div>
          <p v-if="item" class="chosen"><b>{{item.item_name}}</b> · {{item.item_code}} <span>{{item.available}} {{item.uom}} available</span></p>
          <div class="grid">
            <label>Quantity to receive<input v-model.number="qty" type="number" min="0.001" step="0.001" /></label>
            <label>Buying / valuation rate ({{ctx?.currency||'BDT'}})<input v-model.number="buying" type="number" min="0.01" step="0.01" /></label>
            <label>Unit selling price ({{ctx?.currency||'BDT'}})<input v-model.number="selling" type="number" min="0.01" step="0.01" /></label>
            <label>Estimated stock value <strong class="estimate">{{ctx?.currency||'BDT'}} {{(Number(qty||0)*Number(buying||0)).toLocaleString('en-BD',{maximumFractionDigits:2})}}</strong></label>
            <label>Buying Price List<select v-model="buyList"><option v-for="p in listsBuy" :key="p.name" :value="p.name">{{p.name}}</option></select></label>
            <label>Selling Price List<select v-model="sellList"><option v-for="p in listsSell" :key="p.name" :value="p.name">{{p.name}}</option></select></label>
          </div>
          <label>Receipt reason / source reference<textarea v-model="reason" rows="2" maxlength="250" placeholder="Stock correction reference / actual goods received / authorized reason (minimum 12 characters)" /></label>
          <div class="warning"><strong>Accounting control</strong><p>Use this Material Receipt only for legitimately received stock or an authorized adjustment. Supplier purchases require an ERPNext Purchase Receipt. This action updates inventory valuation and Item Price; it is not a Purchase Invoice and does not issue stock to the repair.</p></div>
          <label v-if="item" class="confirm">To receive stock, type <strong>RECEIVE {{item.item_code}}</strong><input v-model="confirmText" autocomplete="off" placeholder="Type exact confirmation" /></label>
        </template>
        <p v-if="error" class="error" role="alert">{{error}}</p>
      </div>
      <footer><button type="button" @click="emit('close')">Close</button><button v-if="!success" type="button" class="primary" :disabled="!valid||busy" @click="receive">{{busy?'Submitting…':'Submit Material Receipt'}}</button></footer>
    </section>
  </div>
</Teleport>
</template>
<style>
.sos712-receipt-mask{position:fixed;inset:0;z-index:200500;background:#28190fbd;display:grid;place-items:center;padding:16px;backdrop-filter:blur(5px)}
.sos712-receipt{width:min(850px,100%);max-height:92vh;display:flex;flex-direction:column;overflow:hidden;background:#fffbf6;color:#443124;border:1px solid #decab4;border-radius:22px;box-shadow:0 30px 100px #25150c66;font:13px/1.45 Inter,system-ui,sans-serif}
.sos712-receipt header{padding:20px 24px;border-bottom:1px solid #eaddcf;display:flex;justify-content:space-between;gap:20px;align-items:flex-start;background:#f8f0e8}.sos712-receipt header small{letter-spacing:1.2px;color:#96795f;font-size:9px;font-weight:850}.sos712-receipt h2{font:700 25px Georgia,serif;margin:4px 0}.sos712-receipt header p{color:#8c715e;font-size:11px;margin:2px 0}.sos712-receipt .close{border:0;border-radius:50%;width:34px;height:34px;background:#eee0d0;font-size:24px;color:#604632;cursor:pointer}
.sos712-receipt .body{padding:20px 24px;overflow:auto;display:grid;gap:14px}.sos712-receipt .context{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.sos712-receipt .context span{display:grid;gap:4px;padding:10px;background:#f3e9df;border-radius:10px;font-size:11px;overflow-wrap:anywhere}.sos712-receipt .context b{font-size:9px;text-transform:uppercase;letter-spacing:1px;color:#896b54}.sos712-receipt .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.sos712-receipt label{display:grid;gap:5px;color:#6c523f;font-size:11px;font-weight:750}.sos712-receipt input,.sos712-receipt textarea,.sos712-receipt select{width:100%;min-width:0;border:1px solid #ddc8b6;border-radius:9px;padding:10px;background:white;color:#34251d;font:12px Inter,system-ui,sans-serif}.sos712-receipt .estimate{border:1px solid #e3d0bf;border-radius:9px;background:#f8f1e9;padding:10px;font-size:14px}.sos712-receipt .results{max-height:150px;overflow:auto;border:1px solid #e0ccba;border-radius:9px}.sos712-receipt .results button{display:grid;gap:3px;width:100%;text-align:left;border:0;background:#fffefa;padding:10px;border-bottom:1px solid #f0e4d8;cursor:pointer}.sos712-receipt .results small{color:#90755b}.sos712-receipt .chosen{background:#f4e5d4;border-radius:9px;padding:10px;margin:0}.sos712-receipt .chosen span{float:right}.sos712-receipt .warning{background:#f8efe6;border-left:3px solid #a37b5b;padding:12px}.sos712-receipt .warning p{font-size:11px;margin:4px 0 0;color:#795f4b}.sos712-receipt .confirm{padding-top:8px;border-top:1px solid #e8d9c8}.sos712-receipt .error{padding:12px;background:#fff0ed;color:#9b4338;border-radius:9px}.sos712-receipt .success{background:#ebf4e9;padding:16px;border-radius:10px}.sos712-receipt .success a{color:#725032;text-decoration:underline}.sos712-receipt footer{display:flex;gap:10px;justify-content:flex-end;border-top:1px solid #eaddcf;padding:15px 24px}.sos712-receipt footer button{padding:10px 17px;border:1px solid #d7bda5;border-radius:11px;color:#634935;background:#fff;font-weight:750}.sos712-receipt footer .primary{background:#765139;border-color:#765139;color:white}.sos712-receipt button:disabled{opacity:.5;cursor:not-allowed}
@media(max-width:640px){.sos712-receipt-mask{padding:5px}.sos712-receipt{max-height:98vh}.sos712-receipt header,.sos712-receipt .body,.sos712-receipt footer{padding:13px}.sos712-receipt .context,.sos712-receipt .grid{grid-template-columns:1fr}}
</style>
