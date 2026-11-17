<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import InventoryPurchaseOrderStudio from './InventoryPurchaseOrderStudio.vue'

// SOS_INV_PO_V54: standalone top-tab purchasing desk. Draft-only mutations.
const props = defineProps({
  catalog:{type:Array,default:()=>[]},
  currentWarehouse:{type:String,default:''},
  company:{type:String,default:''},
  currency:{type:String,default:'BDT'},
  topSellers:{type:Array,default:()=>[]},
  initialTab:{type:String,default:'draft'},
})
const emit=defineEmits(['created','updated','mode-change'])
const bn=computed(()=>currentLanguage.value==='bn')
const words={
  heading:['Purchase Order Center','ক্রয়াদেশ কেন্দ্র'],
  subtitle:['Manage supplier orders, buying rates and stock priorities','সরবরাহকারী অর্ডার, ক্রয়মূল্য ও স্টক অগ্রাধিকার'],
  draft:['Draft orders','খসড়া অর্ডার'], submitted:['Submitted','সাবমিটকৃত'], form:['Order form','অর্ডার ফর্ম'], reorder:['Reorder planner','পুনঃক্রয় পরিকল্পনা'],
  new:['New Purchase Order','নতুন ক্রয়াদেশ'], search:['Search order number or supplier…','অর্ডার নম্বর বা সরবরাহকারী খুঁজুন…'],
  loading:['Loading purchase orders…','ক্রয়াদেশ লোড হচ্ছে…'], empty:['No matching Purchase Orders','কোনো ক্রয়াদেশ পাওয়া যায়নি'],
  number:['PO number','অর্ডার নম্বর'], supplier:['Supplier','সরবরাহকারী'], date:['Order date','অর্ডার তারিখ'],
  delivery:['Required by','প্রয়োজনের তারিখ'], total:['Amount','মোট'], actions:['Actions','কর্ম'],
  edit:['Edit draft','খসড়া সম্পাদনা'], view:['Details','বিস্তারিত'], remove:['Delete','মুছুন'],
  items:['Order items','অর্ডারের পণ্য'], quantity:['Quantity','পরিমাণ'], rate:['Buying rate','ক্রয়মূল্য'],
  cancel:['Back to orders','অর্ডারে ফিরে যান'], refresh:['Refresh','রিফ্রেশ'], more:['Load more','আরও দেখুন'],
  deleted:['Draft Purchase Order deleted','খসড়া ক্রয়াদেশ মুছে ফেলা হয়েছে'],
  noEdits:['Submitted orders are read-only here. Use ERPNext’s controlled purchasing workflow for amendments.','সাবমিটকৃত অর্ডার এখানে শুধু দেখা যাবে। পরিবর্তনের জন্য ইআরপিনেক্সটের অনুমোদিত পদ্ধতি ব্যবহার করুন।'],
  noPermission:['Read permission for Purchase Order is required.','ক্রয়াদেশ পড়ার অনুমতি প্রয়োজন।'],
  confirmDelete:['Permanently delete this draft Purchase Order? This cannot be undone.','খসড়া ক্রয়াদেশ স্থায়ীভাবে মুছে ফেলবেন? এটি ফেরত আনা যাবে না।'],
  note:['Only draft orders can be edited or deleted; these actions do not change stock.','শুধু খসড়া অর্ডার সম্পাদনা বা মুছে ফেলা যায়; এতে স্টক পরিবর্তন হয় না।'],
  created:['Draft saved successfully','খসড়া সংরক্ষিত হয়েছে'], updated:['Draft updated successfully','খসড়া হালনাগাদ হয়েছে'],
  open:['Open in ERPNext','ইআরপিনেক্সটে খুলুন'],
}
const t=k=>words[k]?.[bn.value?1:0]||k
const mode=ref(['draft','submitted','form','reorder'].includes(props.initialTab)?props.initialTab:'draft')
const status=ref('draft'), search=ref(''), rows=ref([]), page=ref(0), hasMore=ref(false)
const loading=ref(false), working=ref(false), error=ref(''), notice=ref('')
const selected=ref(null), editName=ref(''), formKey=ref(0), selectedLoading=ref(false)
const canEdit=ref(false),canDelete=ref(false),canCreate=ref(false)
const displayed=computed(()=>rows.value)
const tabs=[
  {id:'draft',paths:['M4 4h16v16H4z','M8 9h8','M8 13h8','M8 17h5']},
  {id:'submitted',paths:['M4 12l5 5L20 6','M12 2a10 10 0 1 1-6.8 17.3']},
  {id:'form',paths:['M12 20h9','M16 4l4 4-11 11-5 1 1-5z']},
  {id:'reorder',paths:['M4 17l6-6 4 3 6-7','M15 7h5v5']},
]
watch(mode,(value)=>emit('mode-change',value),{immediate:true})

async function api(method,query={},post=false){
  const url=new URL('/api/method/servicing_os.api.inventory_purchase_order.'+method,window.location.origin)
  const headers={Accept:'application/json'}
  const opts={credentials:'same-origin',cache:'no-store',headers}
  if(post){opts.method='POST';headers['Content-Type']='application/json';const csrf=window.csrf_token||window.frappe?.csrf_token;if(csrf)headers['X-Frappe-CSRF-Token']=csrf;opts.body=JSON.stringify({data:query})}
  else Object.entries(query).forEach(([k,v])=>url.searchParams.set(k,String(v??'')))
  const response=await fetch(url,opts)
  const payload=await response.json()
  if(!response.ok||payload.exc||payload.exception){
    let msg=typeof payload.message==='string'?payload.message:'Purchase Order request failed ('+response.status+')'
    try{const messages=JSON.parse(payload._server_messages||'[]');if(messages.length)msg=JSON.parse(messages[0]).message||msg}catch{}
    throw new Error(msg.replace(/<[^>]*>/g,''))
  }
  return payload.message
}
async function load(reset=true){
  if(loading.value)return
  loading.value=true;error.value=''
  try{
    const next=reset?0:page.value+1
    const r=await api('list_purchase_orders',{status:status.value,page:next,search:search.value})
    rows.value=reset?r.orders:[...rows.value,...r.orders]
    page.value=next
    hasMore.value=!!r.has_more
    canEdit.value=!!r.can_edit;canDelete.value=!!r.can_delete;canCreate.value=!!r.can_create
  }catch(e){error.value=e.message||String(e)}finally{loading.value=false}
}
function chooseTab(id){
  error.value='';notice.value='';selected.value=null
  if(id==='form') {openCreate(1);return}
  if(id==='reorder'){openCreate(0,'reorder');return}
  mode.value=id
  status.value=id
  search.value=''
  load()
}
function openCreate(tab=1, origin='form'){
  editName.value='';formKey.value+=1;mode.value=origin==='reorder'?'reorder':'form';
  formStart.value=tab;selected.value=null;error.value=''
}
const formStart=ref(1)
async function openDetail(name){
  selectedLoading.value=true;error.value=''
  try{selected.value=await api('get_purchase_order_record',{name})}
  catch(e){error.value=e.message||String(e)}finally{selectedLoading.value=false}
}
async function openEdit(name){
  selected.value=null;editName.value=name;formStart.value=1;formKey.value+=1;mode.value='form';error.value=''
}
async function deleteDraft(name){
  const row=rows.value.find(r=>r.name===name)
  if(!row||Number(row.docstatus)!==0||!canDelete.value)return
  if(!window.confirm(t('confirmDelete')+'\n'+name))return
  working.value=true;error.value='';notice.value=''
  try{
    await api('delete_purchase_order_draft',{name},true)
    notice.value=t('deleted')+' · '+name
    selected.value=null
    await load()
  }catch(e){error.value=e.message||String(e)}finally{working.value=false}
}
function backToOrders(){mode.value='draft';status.value='draft';editName.value='';selected.value=null;load()}
async function onSaved(doc,isUpdate){
  notice.value=(isUpdate?t('updated'):t('created'))+' · '+doc.name
  emit(isUpdate?'updated':'created',doc)
  await backToOrders()
}
watch(search,()=>{ /* manual Refresh avoids one request per keystroke */ })
onMounted(()=>{ if(mode.value==='draft'||mode.value==='submitted'){status.value=mode.value;load()} else openCreate(mode.value==='reorder'?0:1,mode.value) })
function amount(n){return Number(n||0).toLocaleString(bn.value?'bn-BD':'en-BD',{minimumFractionDigits:0,maximumFractionDigits:2})}
</script>

<template>
  <div class="po54-desk" :lang="bn?'bn':'en'">
    <div class="po54-heading">
      <div><span class="po54-eyebrow">AL MODINA · BUYING WORKSPACE</span><h2>{{ t('heading') }}</h2><p>{{ t('subtitle') }}</p></div>
      <button type="button" class="po54-new" @click="openCreate(1)"><span aria-hidden="true">＋</span>{{ t('new') }}</button>
    </div>
    <!-- SOS_INV_PO_V55_NAV — quiet subnavigation; primary rail owns the emphasis. -->
    <nav class="po55-workflow-tabs" role="tablist" :aria-label="bn?'ক্রয়াদেশ ওয়ার্কস্পেস':'Purchase order workspace'">
      <button v-for="tab in tabs" :key="tab.id" type="button" role="tab" :aria-selected="mode===tab.id" :class="{'is-active':mode===tab.id}" @click="chooseTab(tab.id)">
        <span class="po55-workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path v-for="(p,n) in tab.paths" :key="n" :d="p" /></svg></span>
        <span>{{ t(tab.id) }}</span><span v-if="mode===tab.id" class="po55-workflow-mark" aria-hidden="true"></span>
      </button>
    </nav>
    <p v-if="error" class="po54-alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="po54-notice" role="status">{{ notice }}</p>
    <div v-if="mode==='draft'||mode==='submitted'" class="po54-panel" role="tabpanel">
      <div class="po54-toolbar">
        <div><strong>{{ t(mode) }}</strong><small>{{ t('note') }}</small></div>
        <form class="po54-search" @submit.prevent="load()">
          <input v-model="search" :placeholder="t('search')" :aria-label="t('search')" maxlength="120"/>
          <button type="submit" :disabled="loading">⌕</button>
          <button type="button" :disabled="loading" @click="load()">{{ t('refresh') }}</button>
        </form>
      </div>
      <p v-if="loading&&!rows.length" class="po54-empty">{{ t('loading') }}</p>
      <p v-else-if="!displayed.length" class="po54-empty">{{ t('empty') }}</p>
      <div v-else class="po54-table-wrap"><table class="po54-table">
        <thead><tr><th>{{ t('number') }}</th><th>{{ t('supplier') }}</th><th>{{ t('date') }}</th><th>{{ t('delivery') }}</th><th>{{ t('total') }}</th><th>{{ t('actions') }}</th></tr></thead>
        <tbody><tr v-for="r in displayed" :key="r.name">
          <td><button class="po54-link" type="button" @click="openDetail(r.name)">{{ r.name }}</button><small>{{ r.status }}</small></td>
          <td>{{ r.supplier }}</td><td>{{ r.transaction_date }}</td><td>{{ r.schedule_date }}</td>
          <td><b>{{ r.currency }} {{ amount(r.grand_total) }}</b></td>
          <td><div class="po54-row-actions"><button type="button" @click="openDetail(r.name)">{{ t('view') }}</button><button v-if="r.docstatus===0&&canEdit" type="button" @click="openEdit(r.name)">{{ t('edit') }}</button><button v-if="r.docstatus===0&&canDelete" class="po54-danger" type="button" :disabled="working" @click="deleteDraft(r.name)">{{ t('remove') }}</button></div></td>
        </tr></tbody>
      </table></div>
      <div v-if="hasMore" class="po54-more"><button type="button" :disabled="loading" @click="load(false)">{{ t('more') }}</button></div>
      <section v-if="selected" class="po54-detail" aria-label="Purchase Order details">
        <div class="po54-detail-header"><div><small>{{ selected.status }}</small><h3>{{ selected.name }}</h3><p>{{ selected.supplier }} · {{ selected.company }}</p></div><button type="button" @click="selected=null" aria-label="Close details">×</button></div>
        <div class="po54-facts"><div><small>{{ t('delivery') }}</small><b>{{ selected.schedule_date }}</b></div><div><small>{{ t('total') }}</small><b>{{ selected.currency }} {{ amount(selected.grand_total) }}</b></div><div><small>{{ t('items') }}</small><b>{{ selected.items?.length||0 }}</b></div></div>
        <div v-for="line in selected.items" :key="line.item_code" class="po54-detail-line"><span><b>{{ line.item_name }}</b><small>{{ line.item_code }}</small></span><span>{{ amount(line.qty) }} {{ line.uom }} × {{ amount(line.rate) }}</span></div>
        <p v-if="selected.docstatus!==0" class="po54-readonly">{{ t('noEdits') }}</p>
        <div class="po54-detail-actions"><button v-if="selected.can_edit" type="button" @click="openEdit(selected.name)">{{ t('edit') }}</button><button v-if="selected.can_delete" type="button" class="po54-danger" @click="deleteDraft(selected.name)">{{ t('remove') }}</button><a :href="'/app/purchase-order/'+encodeURIComponent(selected.name)" target="_blank" rel="noopener">{{ t('open') }}</a></div>
      </section>
      <p v-if="selectedLoading" class="po54-empty">{{ t('loading') }}</p>
    </div>
    <div v-else role="tabpanel" class="po54-form-panel">
      <InventoryPurchaseOrderStudio :key="formKey" embedded :catalog="catalog" :current-warehouse="currentWarehouse" :company="company" :currency="currency" :top-sellers="topSellers" :editing-name="editName" :initial-tab="formStart" @close="backToOrders" @created="d=>onSaved(d,false)" @updated="d=>onSaved(d,true)"/>
    </div>
  </div>
</template>

<style scoped>
.po54-desk,.po54-desk *{box-sizing:border-box}
.po54-desk{--ink:#513d2a;--tan:#dfc09a;color:var(--ink);font-family:inherit;min-width:0}
.po54-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}
.po54-eyebrow{font-size:10px;letter-spacing:.12em;font-weight:850;color:#a28a6e}
.po54-heading h2{font-size:clamp(23px,2.3vw,31px);line-height:1.2;font-weight:850;margin:7px 0;color:#503824}
.po54-heading p{font-size:12px;color:#967d65;margin:0}
.po54-new{min-height:42px;border:1px solid #cba57a;border-radius:13px;padding:9px 14px;white-space:nowrap;background:#735237;color:#fff9ef;font-weight:800;font-size:12px;cursor:pointer}
.po54-new span{font-size:17px;margin-right:5px}
.po54-clay-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:12px;margin:0 0 18px;border:1px solid #ead7bd;border-radius:19px;background:linear-gradient(140deg,#f4e4cc,#fffcf5);box-shadow:inset 5px 5px 11px #d4b99c99,inset -5px -5px 11px #ffffff,0 6px 15px #4d2f1310}
.po54-clay-tabs button{display:flex;align-items:center;justify-content:center;gap:9px;min-height:53px;border:1px solid #dfc6a5;border-radius:13px;background:linear-gradient(145deg,#fffaf0,#edd8b9);color:#785b3e;font-weight:800;font-size:12px;cursor:pointer;box-shadow:4px 4px 9px #c8ab87a1,-3px -3px 8px #ffffff}
.po54-clay-tabs button.active{background:linear-gradient(140deg,#f3ddbc,#e6c89f);color:#4e321e;border-color:#c7a075;box-shadow:inset 4px 4px 8px #ad8c6477,inset -4px -4px 9px #fff9eb}
.po54-tab-icon{font-size:18px}
.po54-clay-tabs button:focus-visible,.po54-new:focus-visible{outline:3px solid #bb9365;outline-offset:2px}
.po54-panel{border-radius:17px;border:1px solid #eadac5;background:#fffdfa;box-shadow:0 8px 20px #5c3e1a0e;overflow:hidden}
.po54-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:17px;border-bottom:1px solid #eee0cf}
.po54-toolbar>div{display:flex;flex-direction:column;gap:4px}.po54-toolbar strong{font-size:14px}.po54-toolbar small{font-size:11px;color:#96816e}
.po54-search{display:flex;gap:7px;align-items:center}.po54-search input{border:1px solid #e0cbb2;border-radius:10px;background:#fffdfa;min-width:190px;max-width:330px;width:24vw;min-height:42px;padding:8px 11px;color:#59422c}.po54-search button,.po54-row-actions button,.po54-detail-actions button,.po54-detail-actions a,.po54-more button{min-height:36px;padding:7px 10px;border:1px solid #d6bea1;border-radius:9px;color:#68503b;background:#f6eadd;font-size:11px;font-weight:800;cursor:pointer;text-decoration:none}
.po54-empty{padding:28px;color:#a1876b;text-align:center;font-size:12px}
.po54-alert,.po54-notice{border:1px solid #dcb8a8;background:#ffefe6;color:#874d3c;border-radius:12px;padding:11px 14px;margin-bottom:12px;font-size:12px}.po54-notice{border-color:#dfcaaa;background:#faf0dc;color:#775335}
.po54-table-wrap{overflow:auto}.po54-table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}.po54-table th{background:#f8eee1;text-align:left;padding:12px 13px;color:#89684b;font-size:10px;letter-spacing:.05em}.po54-table td{border-top:1px solid #efe4d6;padding:10px 13px;color:#67503c}.po54-table small{display:block;margin-top:5px;color:#a28c77;font-size:10px}
.po54-link{border:0;background:none;padding:0;color:#60432d;font-weight:850;cursor:pointer;text-decoration:underline}.po54-row-actions,.po54-detail-actions{display:flex;gap:5px;align-items:center;white-space:nowrap}
.po54-row-actions .po54-danger,.po54-detail-actions .po54-danger{background:#ffede7;color:#9b493b;border-color:#efd2c7}
.po54-more{text-align:center;padding:15px;border-top:1px solid #eee0cf}
.po54-detail{border-top:2px solid #e8d7be;padding:17px;background:#fdf6ed}.po54-detail-header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.po54-detail-header h3{font-size:18px;margin:6px 0}.po54-detail-header small{font-size:10px;color:#9a7b5a}.po54-detail-header p{font-size:12px;color:#997e68}.po54-detail-header>button{border:0;background:none;font-size:22px;cursor:pointer}
.po54-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:12px 0}.po54-facts>div{border:1px solid #e5d1b8;border-radius:10px;background:#fffdfa;padding:11px}.po54-facts small{display:block;font-size:10px;color:#997d64;margin-bottom:6px}.po54-facts b{font-size:12px}.po54-detail-line{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 3px;border-bottom:1px solid #e9d9c6;font-size:11px}.po54-detail-line small{display:block;color:#9e866e;margin-top:3px}.po54-readonly{font-size:11px;color:#9a6d41}.po54-detail-actions{margin-top:14px}
@media(max-width:800px){.po54-clay-tabs{gap:6px;padding:8px}.po54-clay-tabs button{min-height:50px;font-size:10px;flex-direction:column;gap:2px}.po54-tab-icon{font-size:14px}.po54-toolbar{align-items:stretch;flex-direction:column}.po54-search input{width:100%;max-width:none;min-width:0;flex:1}}
@media(max-width:550px){.po54-heading{align-items:flex-start}.po54-new{font-size:10px;padding:8px}.po54-clay-tabs{gap:4px;padding:5px;border-radius:12px}.po54-clay-tabs button{font-size:9px;padding:7px 2px;border-radius:9px;min-height:54px}.po54-facts{grid-template-columns:1fr 1fr}.po54-search{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){.po54-clay-tabs button{transition:none}}

/* SOS_INV_PO_V55_NAV — restrained secondary tabs; no duplicate clay tile stacks. */
.po55-workflow-tabs{display:flex;align-items:center;gap:4px;overflow-x:auto;scrollbar-width:thin;padding:5px;margin:0 0 17px;
 border:1px solid #eae0d4;border-radius:13px;background:#f7f1e8;box-shadow:inset 0 1px 2px #5b3b1910}
.po55-workflow-tabs button{position:relative;appearance:none;flex:1 0 0;display:flex;align-items:center;justify-content:center;gap:9px;
 min-width:124px;min-height:46px;padding:8px 12px;border:1px solid transparent;border-radius:10px;background:transparent;
 font-size:12px;font-weight:750;color:#917a62;white-space:nowrap;cursor:pointer;transition:background .15s,border-color .15s,box-shadow .15s}
.po55-workflow-tabs button:hover{color:#664a31;background:#fffaf2}
.po55-workflow-tabs button.is-active{color:#513822;background:#fffdfa;border-color:#e4d5c1;box-shadow:0 2px 7px #46322012}
.po55-workflow-icon{display:grid;place-items:center;flex:0 0 20px;width:20px;height:20px;color:inherit}
.po55-workflow-icon svg{width:18px;height:18px;display:block}
.po55-workflow-mark{position:absolute;bottom:3px;left:36%;right:36%;height:2px;border-radius:3px;background:#9a7047}
.po55-workflow-tabs button:focus-visible{outline:3px solid #b89265;outline-offset:2px}
@media(max-width:740px){.po55-workflow-tabs button{min-width:132px;flex:0 0 auto;font-size:11px;min-height:43px;padding:7px 9px}.po55-workflow-tabs{gap:2px}}
@media(prefers-reduced-motion:reduce){.po55-workflow-tabs button{transition:none}}
</style>
