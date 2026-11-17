<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

// SOS_INV_PO_V54 — inline clay tabs, draft create/edit. No stock mutations.
const props = defineProps({
  catalog: {type:Array,default:()=>[]},
  currentWarehouse: {type:String,default:''},
  company: {type:String,default:''},
  currency: {type:String,default:'BDT'},
  topSellers: {type:Array,default:()=>[]},
  embedded: {type:Boolean,default:false},
  editingName: {type:String,default:''},
  initialTab: {type:Number,default:0},
})
const emit = defineEmits(['close','created','updated'])
const bn = computed(() => currentLanguage.value === 'bn')
const words = {
  heading:['Purchase order studio','ক্রয়াদেশ তৈরি'], subtitle:['Draft a supplier order from stock priorities and your catalog','স্টক ও পণ্যের তালিকা থেকে সরবরাহকারীর ক্রয়াদেশ তৈরি করুন'],
  suggestions:['Reorder suggestions','পুনঃক্রয়ের পরামর্শ'], lines:['Order items','অর্ডারের পণ্য'], supplier:['Supplier & delivery','সরবরাহকারী ও ডেলিভারি'], review:['Review & create','পর্যালোচনা ও তৈরি'],
  close:['Close','বন্ধ'], back:['Back','পেছনে'], next:['Continue','এগিয়ে যান'], create:['Create draft Purchase Order','খসড়া ক্রয়াদেশ তৈরি করুন'], saving:['Saving draft…','খসড়া সংরক্ষণ হচ্ছে…'],
  warehouse:['Receiving warehouse','গ্রহণের গুদাম'], loading:['Loading buying details…','ক্রয়ের তথ্য লোড হচ্ছে…'], retry:['Retry','আবার চেষ্টা'],
  sales:['Top seller · 90 days','সর্বাধিক বিক্রি · ৯০ দিন'], actual:['Available','উপলব্ধ'], onorder:['On order','অর্ডার করা'], reorder:['Reorder at','পুনঃক্রয়ের সীমা'],
  qty:['Order qty','অর্ডারের পরিমাণ'], rate:['Buying rate','ক্রয়মূল্য'], value:['Est. line value','আনুমানিক মূল্য'], add:['Add to order','অর্ডারে যোগ করুন'], added:['Added','যোগ করা হয়েছে'], remove:['Remove','বাদ দিন'],
  supplierName:['Supplier','সরবরাহকারী'], supplierPlaceholder:['Search suppliers by name…','নাম দিয়ে সরবরাহকারী খুঁজুন…'], supplierChoose:['Choose an existing supplier','বিদ্যমান সরবরাহকারী নির্বাচন করুন'],
  requiredBy:['Required by','প্রয়োজনীয় তারিখ'], remarks:['Internal remarks','অভ্যন্তরীণ মন্তব্য'], buyingList:['Buying price list','ক্রয়মূল্যের তালিকা'], company:['Company','কোম্পানি'],
  items:['Items','পণ্য'], total:['Estimated subtotal','আনুমানিক উপমোট'], totalNote:['Taxes, discounts and ERPNext pricing rules may change the final amount.','কর, ছাড় ও মূল্যনীতির কারণে চূড়ান্ত পরিমাণ বদলাতে পারে।'],
  recommended:['Based on reorder rules','পুনঃক্রয়ের নিয়ম অনুযায়ী'], reviewStockout:['Stockouts to review','শেষ হওয়া স্টক পর্যালোচনা'], unknown:['Open-order quantities are not visible. Please check existing Purchase Orders before ordering.','আগের ক্রয়াদেশের পরিমাণ দেখা যাচ্ছে না। নতুন অর্ডারের আগে পরীক্ষা করুন।'],
  noRule:['No reorder rule','পুনঃক্রয়ের নিয়ম নেই'], noSuggestions:['No items require replenishment under configured reorder rules.','বর্তমান পুনঃক্রয়ের নিয়মে অর্ডারের প্রয়োজন নেই।'],
  noItems:['No order lines yet. Add products from suggestions or catalog search.','এখনও কোনো পণ্য যোগ করা হয়নি। পরামর্শ বা তালিকা থেকে যোগ করুন।'],
  find:['Search products, SKU or group…','পণ্যের নাম, কোড বা গ্রুপ খুঁজুন…'], noMatch:['No matching products','কোনো পণ্য পাওয়া যায়নি'],
  limited:['Only the loaded catalog is searchable. Use the full catalog for additional items.','লোড হওয়া পণ্য থেকেই নির্বাচন করা যাবে।'],
  supplierHelp:['The supplier, warehouse and delivery date are required.','সরবরাহকারী, গুদাম ও ডেলিভারির তারিখ আবশ্যক।'],
  draft:['Draft only · not submitted','শুধু খসড়া · সাবমিট হয়নি'], status:['Draft saved','খসড়া সংরক্ষিত'],
  open:['Open in ERPNext','ইআরপিনেক্সটে খুলুন'], finish:['Return to Inventory','ইনভেন্টরিতে ফিরুন'],
  noSupplier:['No suppliers found. Create a Supplier in ERPNext first.','কোনো সরবরাহকারী পাওয়া যায়নি। আগে ইআরপিনেক্সটে তৈরি করুন।'],
  blocked:['You do not have permission to create Purchase Orders.','আপনার ক্রয়াদেশ তৈরির অনুমতি নেই।'],
  configure:['Configure a reorder level and reorder quantity per item/warehouse to get evidence-based recommendations.','তথ্যভিত্তিক পরামর্শের জন্য প্রতিটি পণ্য/গুদামে পুনঃক্রয়ের সীমা ও পরিমাণ সেট করুন।'],
  missingRate:['Enter a buying rate before saving.','সংরক্ষণের আগে ক্রয়মূল্য লিখুন।'],
  manual:['Manual review · quantity not inferred','ম্যানুয়ালি যাচাই করুন · পরিমাণ অনুমান করা হয়নি'],
  selected:['Selected supplier','নির্বাচিত সরবরাহকারী'],
  updating:['Save changes to draft','খসড়ার পরিবর্তন সংরক্ষণ'],
  editHeading:['Edit draft Purchase Order','খসড়া ক্রয়াদেশ সম্পাদনা'],
  editSaved:['Draft changes saved','খসড়া পরিবর্তন সংরক্ষিত'],
  successClose:['Back to Purchase Orders','ক্রয়াদেশে ফিরে যান'],
}
const t = k => words[k]?.[bn.value?1:0] || k
const index = ref(props.initialTab || 0)
const loadedOrder = ref('')
const tabs = [{id:'suggestions',icon:'◫'},{id:'lines',icon:'▤'},{id:'supplier',icon:'♙'},{id:'review',icon:'✓'}]
const ctx = ref({suppliers:[],warehouses:[],pending_visible:false,reorder_rules:{},pending_orders:{},can_create:false})
const busy = ref(false), loading = ref(true), error = ref(''), created = ref(null)
const warehouse = ref(props.currentWarehouse || '')
const supplier = ref(''), supplierSearch = ref(''), supplierMenu = ref(false)
const delivery = ref(''), remarks = ref(''), search = ref('')
const orderLines = ref([]), quickSearch = ref('')
const supplierInput = ref(null)

function isoAfter(days){const d=new Date();d.setDate(d.getDate()+days);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function amount(v){return Number(v||0).toLocaleString(bn.value?'bn-BD':'en-BD',{maximumFractionDigits:2})}
function money(v){return `${ctx.value.currency||props.currency} ${amount(v)}`}
async function api(method, data, post=false){
  const url = new URL('/api/method/servicing_os.api.inventory_purchase_order.'+method,window.location.origin)
  const headers = {Accept:'application/json'}
  const opts = {credentials:'same-origin',headers,cache:'no-store'}
  if(post){opts.method='POST';headers['Content-Type']='application/json';const token=window.csrf_token||window.frappe?.csrf_token;if(token)headers['X-Frappe-CSRF-Token']=token;opts.body=JSON.stringify({data})}
  else for (const [k,v] of Object.entries(data||{})) url.searchParams.set(k,String(v||''))
  const res=await fetch(url,opts)
  const payload=await res.json()
  if(!res.ok||payload.exc||payload.exception){let msg=payload.message||`Purchase Order API error (${res.status})`;try{const list=JSON.parse(payload._server_messages||'[]');if(list.length)msg=JSON.parse(list[0]).message||msg}catch{}throw new Error(String(msg).replace(/<[^>]+>/g,''))}
  return payload.message
}
async function load(){
  loading.value=true;error.value=''
  try{
    const data=await api('get_purchase_order_context',{warehouse:props.currentWarehouse})
    ctx.value=data
    if (!warehouse.value || !data.warehouses.some(w=>w.name===warehouse.value)) warehouse.value=data.warehouses[0]?.name||''
    if (!data.can_create && !props.editingName) error.value=t('blocked')
    if (props.editingName) {
      const doc = await api('get_purchase_order_record',{name:props.editingName})
      if (Number(doc.docstatus) !== 0 || !doc.can_edit) throw new Error('Only an authorized draft can be edited')
      loadedOrder.value = doc.name
      supplier.value = doc.supplier
      const ss = data.suppliers.find(s=>s.name===doc.supplier)
      supplierSearch.value = ss?.supplier_name||doc.supplier
      warehouse.value = doc.warehouse || data.warehouses[0]?.name || ''
      delivery.value = doc.schedule_date || isoAfter(7)
      remarks.value = doc.remarks || ''
      orderLines.value = doc.items.map(i=>{
        const product = props.catalog.find(p=>p.item_code===i.item_code)
        return {item_code:i.item_code,item_name:i.item_name||product?.item_name||i.item_code,
          item_group:product?.item_group||'',uom:i.uom,qty:i.qty,rate:i.rate,
          stock:product?available(product):0,on_order:product?pending(product):null}
      })
      index.value=1
    }
  }catch(e){error.value=e?.message||String(e)}finally{loading.value=false}
}
onMounted(()=>{delivery.value=isoAfter(7);load()})
function close(){if(!busy.value)emit('close')}
function key(item){return `${item.item_code}::${warehouse.value}`}
function available(item){
  if(!warehouse.value)return 0
  // The context endpoint loads real Bin balances per warehouse. Inventory's
  // filtered catalog must not be reused as another warehouse's stock figure.
  return Number(ctx.value.stock_by_warehouse?.[key(item)] || 0)
}
function pending(item){return ctx.value.pending_visible?Number(ctx.value.pending_orders?.[key(item)]||0):null}
function rule(item){return ctx.value.reorder_rules?.[key(item)]||null}
function calculated(item){
  const r=rule(item), p=pending(item)
  if(!r||p===null||Number(r.level)<=0)return 0
  const free=available(item)+p
  return free>Number(r.level)?0:Math.max(1,Math.ceil(Number(r.reorder_qty||0)||Math.max(1,Number(r.level)-free)))
}
const suggestionItems = computed(()=>props.catalog.filter(i=>calculated(i)>0).sort((a,b)=>calculated(b)-calculated(a)).slice(0,200))
const stockouts = computed(()=>props.catalog.filter(i=>available(i)<=0&&!rule(i)).sort((a,b)=>(salesByCode.value.get(b.item_code)||0)-(salesByCode.value.get(a.item_code)||0)).slice(0,40))
const suggestionFiltered = computed(()=>{
  const q=search.value.trim().toLowerCase()
  return suggestionItems.value.filter(i=>!q||[i.item_name,i.item_code,i.item_group].some(x=>String(x||'').toLowerCase().includes(q))).slice(0,30)
})
const reviewFiltered = computed(()=>{
  const q=search.value.trim().toLowerCase()
  return stockouts.value.filter(i=>!q||[i.item_name,i.item_code,i.item_group].some(x=>String(x||'').toLowerCase().includes(q))).slice(0,12)
})
const selectedCodes = computed(()=>new Set(orderLines.value.map(i=>i.item_code)))
const salesByCode = computed(()=>new Map(props.topSellers.map(s=>[s.item_code, Number(s.sold_units||0)])))
const productMatches = computed(()=>{
  const q=quickSearch.value.trim().toLowerCase()
  if(!q) return []
  return props.catalog.filter(i=>[i.item_code,i.item_name,i.item_group,i.brand].some(x=>String(x||'').toLowerCase().includes(q))&&!selectedCodes.value.has(i.item_code)).slice(0,12)
})
const supplierMatches = computed(()=>{
  const q=supplierSearch.value.trim().toLowerCase()
  return (ctx.value.suppliers||[]).filter(s=>!q||[s.name,s.supplier_name,s.supplier_group].some(v=>String(v||'').toLowerCase().includes(q))).slice(0,15)
})
const total = computed(()=>orderLines.value.reduce((n,l)=>n+Number(l.qty||0)*Number(l.rate||0),0))
const invalidLines = computed(()=>orderLines.value.some(l=>!(Number(l.qty)>0)||!(Number(l.rate)>0)))
const valid = computed(()=>(loadedOrder.value?ctx.value.can_edit:ctx.value.can_create) && !!supplier.value && !!warehouse.value && !!delivery.value && orderLines.value.length>0 && !invalidLines.value)
function addLine(item, suggested=0){
  if(selectedCodes.value.has(item.item_code)){index.value=1;return}
  if(orderLines.value.length>=60){error.value='Maximum 60 lines per Purchase Order';return}
  orderLines.value.push({item_code:item.item_code,item_name:item.item_name,item_group:item.item_group,uom:item.stock_uom,qty:suggested||1,rate:Number(item.buying_price)||0,stock:available(item),on_order:pending(item),original_warehouse:warehouse.value})
  quickSearch.value=''
}
function gotoTab(i){if(!loading.value&&i>=0&&i<4) {index.value=i;error.value=''}}
function setSupplier(x){supplier.value=x.name;supplierSearch.value=x.supplier_name||x.name;supplierMenu.value=false}
function onSupplierBlur(){setTimeout(()=>{supplierMenu.value=false},160)}
watch(warehouse,()=>{
  // Warehouse change does not discard chosen products, but updates the stock references.
  for(const l of orderLines.value){const i=props.catalog.find(p=>p.item_code===l.item_code);if(i){l.stock=available(i);l.on_order=pending(i)}}
})
async function save(){
  error.value='';if(!valid.value){error.value=bn.value?'সরবরাহকারী, গুদাম, তারিখ, পণ্য ও ধনাত্মক ক্রয়মূল্য নিশ্চিত করুন।':'Choose supplier, warehouse and date; add products with positive quantity and buying rate.';return}
  busy.value=true
  try{
    const r=await api(loadedOrder.value?'update_purchase_order_draft':'create_purchase_order_draft',{name:loadedOrder.value||undefined,supplier:supplier.value,warehouse:warehouse.value,schedule_date:delivery.value,remarks:remarks.value,items:orderLines.value.map(l=>({item_code:l.item_code,qty:Number(l.qty),rate:Number(l.rate)}))},true)
    created.value=r
    emit(loadedOrder.value?'updated':'created',r)
    index.value=3
  }catch(e){error.value=e?.message||String(e)}finally{busy.value=false}
}
function openOrder(){if(created.value?.name)window.location.assign('/app/purchase-order/'+encodeURIComponent(created.value.name))}
</script>

<template>
  <div class="po53-overlay" :class="{'po54-embedded':embedded}" @click.self="embedded?null:close()" @keydown.esc.stop="embedded?null:close()">
    <section class="po53-modal" :role="embedded?'region':'dialog'" :aria-modal="embedded?undefined:true" :aria-label="editingName?t('editHeading'):t('heading')">
      <header class="po53-header">
        <div><span class="po53-eyebrow">AL MODINA · INVENTORY / BUYING</span><h2>{{ editingName?t('editHeading'):t('heading') }}</h2><p>{{ t('subtitle') }}</p></div>
        <button type="button" class="po53-close" :disabled="busy" :aria-label="t('close')" @click="close">×</button>
      </header>
      <!-- SOS_INV_PO_V55_NAV — refined progress stepper; business form untouched. -->
      <nav class="po55-form-steps" role="tablist" :aria-label="bn?'ক্রয়াদেশ ফর্মের ধাপ':'Purchase order form steps'">
        <button v-for="(tab,n) in tabs" :key="tab.id" type="button" :class="{'is-active':index===n,'is-complete':index>n}" :aria-selected="index===n" role="tab" :aria-controls="'po54-content-'+n" :disabled="loading||!!created" @click="gotoTab(n)">
          <span class="po55-step-number" aria-hidden="true">{{ String(n+1).padStart(2,'0') }}</span>
          <span class="po55-step-name">{{ t(tab.id) }}</span><small v-if="n===1 && orderLines.length">{{ orderLines.length }}</small>
        </button>
      </nav>
      <div v-if="loading" class="po53-centre">{{ t('loading') }}</div>
      <div v-else class="po53-body" role="tabpanel" :id="'po54-content-'+index">
        <div v-if="error" class="po53-error" role="alert">{{ error }} <button v-if="!ctx.company" type="button" @click="load">{{ t('retry') }}</button></div>
        <template v-if="!created">
          <div v-if="index===0" class="po53-stack">
            <div class="po53-banner"><div><strong>{{ t('recommended') }}</strong><small>{{ t('configure') }}</small></div><label>{{ t('warehouse') }}<select v-model="warehouse"><option v-for="w in ctx.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name||w.name }}</option></select></label></div>
            <p v-if="!ctx.pending_visible" class="po53-warning">{{ t('unknown') }}</p>
            <div class="po53-listhead"><strong>{{ t('suggestions') }} · {{ suggestionItems.length }}</strong><input v-model="search" :placeholder="t('find')" autocomplete="off" /></div>
            <div v-if="!suggestionFiltered.length" class="po53-empty">{{ t('noSuggestions') }}</div>
            <div class="po53-suggestions">
              <article v-for="i in suggestionFiltered" :key="i.item_code" class="po53-suggest">
                <div class="po53-name"><strong>{{ i.item_name }}</strong><small>{{ i.item_code }} · {{ i.item_group }}</small><small v-if="salesByCode.get(i.item_code)" class="po53-signal">↗ {{ t('sales') }} · {{ amount(salesByCode.get(i.item_code)) }}</small></div>
                <div class="po53-facts"><span>{{ t('actual') }} <b>{{ amount(available(i)) }}</b></span><span>{{ t('onorder') }} <b>{{ amount(pending(i)) }}</b></span><span>{{ t('reorder') }} <b>{{ amount(rule(i)?.level) }}</b></span></div>
                <button type="button" class="po53-add" :disabled="selectedCodes.has(i.item_code)" @click="addLine(i,calculated(i))">{{ selectedCodes.has(i.item_code)?t('added'):`+ ${t('add')} · ${amount(calculated(i))}` }}</button>
              </article>
            </div>
            <details class="po53-disclosure"><summary>{{ t('reviewStockout') }} · {{ stockouts.length }}</summary><p class="po53-help">{{ t('manual') }}</p>
              <div v-for="i in reviewFiltered" :key="i.item_code" class="po53-compact"><span><b>{{ i.item_name }}</b><small>{{ i.item_code }} · {{ i.item_group }}</small></span><button type="button" class="po53-textbutton" :disabled="selectedCodes.has(i.item_code)" @click="addLine(i)">+ {{ t('add') }}</button></div>
            </details>
          </div>
          <div v-else-if="index===1" class="po53-stack">
            <div class="po53-listhead"><strong>{{ t('lines') }} · {{ orderLines.length }}</strong><input v-model="quickSearch" :placeholder="t('find')" autocomplete="off" /></div>
            <div v-if="productMatches.length" class="po53-matches"><button v-for="i in productMatches" :key="i.item_code" type="button" @click="addLine(i)"><span>{{ i.item_name }}<small>{{ i.item_code }} · {{ i.item_group }}</small></span><b>+</b></button></div>
            <p v-if="!orderLines.length" class="po53-empty">{{ t('noItems') }}</p>
            <div v-for="(line,n) in orderLines" :key="line.item_code" class="po53-line">
              <div class="po53-line-name"><b>{{ line.item_name }}</b><small>{{ line.item_code }} · {{ line.uom }} · {{ t('actual') }} {{ amount(line.stock) }}</small></div>
              <label>{{ t('qty') }}<input v-model.number="line.qty" type="number" min="0.001" max="100000000" step="any" /></label>
              <label>{{ t('rate') }}<input v-model.number="line.rate" type="number" min="0.01" step="any" /></label>
              <strong class="po53-amount">{{ money(Number(line.qty||0)*Number(line.rate||0)) }}</strong>
              <button type="button" class="po53-delete" :aria-label="t('remove')" @click="orderLines.splice(n,1)">×</button>
            </div>
            <p class="po53-help">{{ t('limited') }} {{ t('missingRate') }}</p>
          </div>
          <div v-else-if="index===2" class="po53-stack">
            <div class="po53-fields">
              <div class="po53-field po53-supplier-field"><label for="po53-supplier">{{ t('supplierName') }} *</label><input id="po53-supplier" ref="supplierInput" v-model="supplierSearch" autocomplete="off" :placeholder="t('supplierPlaceholder')" @focus="supplierMenu=true" @input="supplier='';supplierMenu=true" @blur="onSupplierBlur" />
                <div v-if="supplierMenu" class="po53-suppliers" role="listbox"><button v-for="s in supplierMatches" :key="s.name" type="button" role="option" :aria-selected="s.name===supplier" @mousedown.prevent @click="setSupplier(s)"><b>{{ s.supplier_name }}</b><small>{{ s.name }} · {{ s.supplier_group }}</small></button><p v-if="!supplierMatches.length">{{ t('noSupplier') }}</p></div>
                <small v-if="supplier">{{ t('selected') }}: {{ supplier }}</small><small v-else>{{ t('supplierChoose') }}</small>
              </div>
              <div class="po53-field"><label>{{ t('warehouse') }} *</label><select v-model="warehouse"><option v-for="w in ctx.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name||w.name }}</option></select></div>
              <div class="po53-field"><label>{{ t('requiredBy') }} *</label><input v-model="delivery" type="date" :min="isoAfter(0)" :max="isoAfter(730)" /></div>
              <div class="po53-field"><label>{{ t('company') }}</label><input :value="ctx.company" readonly /></div>
              <div class="po53-field"><label>{{ t('buyingList') }}</label><input :value="ctx.buying_price_list||t('missingRate')" readonly /></div>
              <div class="po53-field"><label>{{ t('total') }}</label><input :value="money(total)" readonly /></div>
              <div class="po53-field po53-full"><label>{{ t('remarks') }}</label><textarea v-model="remarks" rows="3" maxlength="2000"></textarea></div>
            </div>
            <p class="po53-help">{{ t('supplierHelp') }}</p>
          </div>
          <div v-else class="po53-stack">
            <div class="po53-review"><div><small>{{ t('company') }}</small><b>{{ ctx.company }}</b></div><div><small>{{ t('supplierName') }}</small><b>{{ supplier||'—' }}</b></div><div><small>{{ t('warehouse') }}</small><b>{{ warehouse||'—' }}</b></div><div><small>{{ t('requiredBy') }}</small><b>{{ delivery }}</b></div><div><small>{{ t('items') }}</small><b>{{ orderLines.length }}</b></div><div><small>{{ t('total') }}</small><b>{{ money(total) }}</b></div></div>
            <div class="po53-review-lines"><div v-for="l in orderLines" :key="l.item_code" class="po53-review-row"><span>{{ l.item_name }} <small>{{ l.item_code }}</small></span><b>{{ amount(l.qty) }} × {{ money(l.rate) }}</b><strong>{{ money(Number(l.qty)*Number(l.rate)) }}</strong></div></div>
            <p class="po53-warning">{{ t('draft') }}. {{ t('totalNote') }}</p>
          </div>
        </template>
        <div v-else class="po53-success"><div class="po53-success-icon">✓</div><h3>{{ loadedOrder?t('editSaved'):t('status') }} · {{ created.name }}</h3><p>{{ created.supplier }} · {{ created.company }}</p><p>{{ created.items_count }} {{ t('items') }} · {{ money(created.grand_total) }}</p><p class="po53-help">{{ t('draft') }}</p><div class="po53-success-actions"><button class="po53-primary" @click="openOrder">{{ t('open') }}</button><button class="po53-secondary" @click="close">{{ embedded?t('successClose'):t('finish') }}</button></div></div>
      </div>
      <footer v-if="!loading&&!created" class="po53-footer"><div><b>{{ orderLines.length }} {{ t('items') }}</b><span>{{ t('total') }}: {{ money(total) }}</span></div><div class="po53-foot-actions"><button type="button" class="po53-secondary" @click="index?gotoTab(index-1):close()">{{ index?t('back'):t('close') }}</button><button v-if="index<3" type="button" class="po53-primary" @click="gotoTab(index+1)">{{ t('next') }} →</button><button v-else type="button" class="po53-primary" :disabled="!valid||busy" @click="save">{{ busy?t('saving'):(loadedOrder?t('updating'):t('create')) }}</button></div></footer>
    </section>
  </div>
</template>

<style scoped>
.po53-overlay,.po53-overlay *{box-sizing:border-box}
.po53-overlay{position:fixed;inset:0;z-index:11010;background:#26170cb3;display:flex;align-items:center;justify-content:center;padding:14px;font-family:inherit;color:#533d2d}
.po53-modal{width:min(1100px,100%);max-height:calc(100dvh - 28px);background:#fffcf7;border:1px solid #deceb9;border-radius:21px;box-shadow:0 30px 90px #21130965;display:flex;flex-direction:column;overflow:hidden;min-height:400px}
.po53-header{padding:19px 24px 15px;display:flex;align-items:flex-start;justify-content:space-between;gap:14px;border-bottom:1px solid #e9dece;background:linear-gradient(115deg,#fffaf1,#f6eddf)}
.po53-eyebrow{color:#a28a6b;font-size:10px;font-weight:800;letter-spacing:1.1px}.po53-header h2{font-size:23px;line-height:1.2;letter-spacing:-.45px;color:#4b3322;font-weight:850;margin:7px 0 5px}.po53-header p{font-size:12px;color:#9a816b;margin:0}
.po53-close{flex:0 0 36px;width:36px;height:36px;border:1px solid #d9c8b1;background:#fffaf4;color:#644b36;border-radius:10px;font-size:24px;line-height:1;cursor:pointer}
.po53-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;background:#f5ebdc;padding:8px 14px;border-bottom:1px solid #e7d9c6}
.po53-tabs button{display:flex;gap:8px;align-items:center;justify-content:center;border:1px solid transparent;background:transparent;border-radius:10px;padding:11px 7px;font-size:12px;font-weight:750;color:#94795f;cursor:pointer;min-width:0}
.po53-tabs button.active{background:#fffdf9;border-color:#e1cbb1;color:#62462e;box-shadow:0 2px 8px #5f452216}.po53-tabs button span{font-size:16px}.po53-tabs button small{background:#e9d9c2;border-radius:50%;width:21px;height:21px;display:grid;place-items:center;color:#705036}
.po53-body{padding:18px 22px;overflow:auto;flex:1;min-height:0}.po53-centre,.po53-empty{padding:32px 18px;text-align:center;color:#997e66;font-size:12px}
.po53-error,.po53-warning{padding:11px 13px;border:1px solid #e2c5b4;border-radius:11px;background:#fff2e8;color:#915343;font-size:12px;margin-bottom:12px}.po53-error button{margin-left:10px;border:none;background:transparent;text-decoration:underline;color:inherit;cursor:pointer}
.po53-warning{background:#fff7e9;border-color:#e5d6be;color:#8c6d45}.po53-stack{display:flex;flex-direction:column;gap:12px}.po53-banner{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px 15px;border-radius:13px;background:#f6ecdf;border:1px solid #e4d4bd}.po53-banner>div{display:flex;flex-direction:column;gap:3px}.po53-banner strong{font-size:13px;color:#65462c}.po53-banner small{font-size:10px;color:#987f65;line-height:1.4;max-width:480px}.po53-banner label{font-size:10px;display:flex;flex-direction:column;gap:5px;font-weight:750;color:#7b5e44;min-width:215px}
.po53-overlay input,.po53-overlay select,.po53-overlay textarea{height:41px;border:1px solid #dfcdb5;background:#fffefa;border-radius:9px;color:#4c3828;padding:9px 11px;font-family:inherit;font-size:12px;width:100%;min-width:0;outline-color:#bc986c}.po53-overlay textarea{height:auto;min-height:80px;resize:vertical}.po53-overlay input[readonly]{background:#f5efe8;color:#8e7a66}
.po53-listhead{display:flex;align-items:center;justify-content:space-between;gap:12px}.po53-listhead strong{font-size:13px}.po53-listhead input{width:min(350px,100%)}
.po53-suggestions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.po53-suggest{display:flex;align-items:center;gap:10px;padding:11px;border:1px solid #e8dac8;border-radius:12px;background:#fffefa;min-width:0;flex-wrap:wrap}.po53-name{flex:1 1 210px;min-width:0}.po53-name strong{font-size:12px;display:block;color:#4b3625;line-height:1.3}.po53-signal{color:#785334!important;font-weight:800}.po53-name small,.po53-compact small,.po53-line-name small{display:block;font-size:10px;margin-top:4px;color:#a08972;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.po53-facts{display:flex;gap:9px;flex:1 1 230px;flex-wrap:wrap;font-size:10px;color:#97806a}.po53-facts b{color:#553e2d}.po53-add,.po53-textbutton{background:#f0e1cd;color:#65492f;border:1px solid #d9bc95;border-radius:9px;cursor:pointer;padding:8px 11px;font-weight:750;font-size:11px;white-space:nowrap}.po53-add:hover,.po53-textbutton:hover{background:#e9d5ba}.po53-add:disabled,.po53-textbutton:disabled{opacity:.5;cursor:default}
.po53-disclosure{border:1px solid #e9ddce;background:#fffefa;border-radius:12px;padding:10px 13px}.po53-disclosure summary{font-size:12px;font-weight:800;color:#76583b;cursor:pointer}.po53-help{font-size:11px;color:#98826d;line-height:1.5;margin:0}.po53-compact{border-top:1px solid #f0e7dd;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 3px}.po53-compact b{font-size:11px}.po53-compact span{min-width:0}
.po53-matches{border:1px solid #e2d4c0;border-radius:11px;max-height:230px;overflow:auto;background:#fff}.po53-matches button{display:flex;justify-content:space-between;gap:12px;width:100%;border:0;border-bottom:1px solid #f1e8dd;background:#fff;text-align:left;padding:11px;color:#66503d;cursor:pointer;font-size:12px}.po53-matches button:hover{background:#fbf3e7}.po53-matches small{display:block;font-size:10px;margin-top:3px;color:#97816c}
.po53-line{display:grid;grid-template-columns:minmax(0,2.4fr) minmax(85px,.65fr) minmax(105px,.85fr) minmax(115px,1fr) 30px;align-items:end;gap:10px;padding:12px;border:1px solid #e7d8c5;border-radius:12px;background:#fffefa}.po53-line-name{min-width:0;align-self:center}.po53-line-name b{font-size:12px}.po53-line label{display:flex;flex-direction:column;gap:5px;font-size:10px;font-weight:750;color:#8d7359}.po53-amount{font-size:12px;color:#62452f;align-self:center;text-align:right;overflow-wrap:anywhere}.po53-delete{border:1px solid #e6d0be;background:#fcf0e7;color:#9b553d;height:34px;border-radius:9px;cursor:pointer;font-size:22px}
.po53-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.po53-field{min-width:0;display:flex;flex-direction:column;gap:6px}.po53-field>label{font-size:11px;font-weight:750;color:#765a40}.po53-field>small{font-size:10px;color:#a28c78}.po53-full{grid-column:1/-1}.po53-supplier-field{position:relative;z-index:3}.po53-suppliers{position:absolute;top:66px;left:0;right:0;z-index:30;background:#fff;border:1px solid #dbc6ad;border-radius:10px;box-shadow:0 8px 20px #4e331e26;max-height:250px;overflow:auto}.po53-suppliers button{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #eee3d5;background:#fff;padding:10px;font-size:12px;color:#5e4430;cursor:pointer}.po53-suppliers button:hover{background:#f9f0e5}.po53-suppliers small{display:block;color:#9b806a;margin-top:4px}.po53-suppliers p{padding:12px;color:#9b806a;font-size:11px}
.po53-review{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.po53-review>div{border:1px solid #e5d7c6;background:#f9f1e7;padding:12px;border-radius:11px;min-width:0}.po53-review small{display:block;font-size:10px;color:#9b816a;margin-bottom:5px}.po53-review b{font-size:12px;display:block;overflow-wrap:anywhere;color:#58402e}.po53-review-lines{border:1px solid #ebddcc;border-radius:11px;overflow:hidden}.po53-review-row{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;padding:10px 12px;border-bottom:1px solid #eee3d6;font-size:11px;align-items:center}.po53-review-row small{display:block;color:#a3907f;margin-top:3px}.po53-review-row b,.po53-review-row strong{text-align:right}
.po53-footer{border-top:1px solid #e4d6c4;display:flex;align-items:center;justify-content:space-between;gap:13px;padding:12px 21px;background:#fff8ed}.po53-footer>div:first-child{display:flex;flex-direction:column;gap:3px;font-size:12px}.po53-footer>div:first-child span{font-size:11px;color:#8f745e}.po53-foot-actions,.po53-success-actions{display:flex;gap:9px;align-items:center}.po53-primary,.po53-secondary{min-height:41px;border:1px solid #78543a;border-radius:10px;padding:9px 17px;font-size:12px;font-weight:800;cursor:pointer}.po53-primary{background:#6b4b31;color:#fffaf4}.po53-primary:hover{background:#513821}.po53-primary:disabled{opacity:.4;cursor:not-allowed}.po53-secondary{color:#684d35;background:#fffdf8;border-color:#dfcbb2}
.po53-success{padding:35px 12px;text-align:center}.po53-success-icon{display:grid;place-items:center;width:54px;height:54px;border-radius:17px;background:#e7d9c5;color:#755032;font-size:28px;margin:0 auto 12px}.po53-success h3{font-size:20px;color:#503925}.po53-success p{font-size:12px;color:#947b64;margin:8px}.po53-success-actions{justify-content:center;margin-top:18px}
.po53-close:focus-visible,.po53-tabs button:focus-visible,.po53-primary:focus-visible,.po53-secondary:focus-visible,.po53-add:focus-visible{outline:3px solid #b58d5e;outline-offset:2px}
@media(max-width:780px){.po53-suggestions{grid-template-columns:1fr}.po53-review{grid-template-columns:repeat(2,minmax(0,1fr))}.po53-line{grid-template-columns:minmax(0,1.6fr) minmax(66px,.65fr) minmax(82px,.8fr) 28px}.po53-amount{grid-column:2/4;text-align:right}.po53-delete{grid-column:4;grid-row:1}}
@media(max-width:530px){.po53-overlay{padding:5px}.po53-modal{max-height:calc(100dvh - 10px);border-radius:13px}.po53-header{padding:13px}.po53-header h2{font-size:19px}.po53-tabs{padding:5px;gap:1px}.po53-tabs button{flex-direction:column;gap:3px;font-size:9px;padding:8px 3px}.po53-tabs button span{font-size:14px}.po53-body{padding:12px}.po53-banner,.po53-listhead{flex-direction:column;align-items:stretch}.po53-banner label{min-width:0}.po53-fields{grid-template-columns:1fr}.po53-full{grid-column:auto}.po53-review{grid-template-columns:1fr 1fr}.po53-footer{padding:10px}.po53-line{grid-template-columns:minmax(0,1fr) 80px 90px 26px}.po53-line-name{grid-column:1/-1}.po53-footer .po53-foot-actions{gap:5px}.po53-primary,.po53-secondary{padding:9px;font-size:11px}}
@media(prefers-reduced-motion:reduce){.po53-overlay *{scroll-behavior:auto}}
/* SOS_INV_PO_V54 — Claymorphism tab bar + full-width form mode. */
.po54-embedded{position:relative;inset:auto;z-index:auto;padding:0;background:transparent;display:block;min-height:0}
.po54-embedded .po53-modal{width:100%;max-height:none;min-height:530px;box-shadow:0 12px 28px #6a49221c,0 2px 8px #bd997043;border:1px solid #e6d4b9}
.po54-embedded .po53-body{flex:initial;overflow:visible;min-height:390px}
.po54-embedded .po53-close{display:none}
.po53-tabs{position:sticky;top:0;z-index:4;gap:12px;background:linear-gradient(135deg,#f7ead6,#f3e2c8);padding:13px 17px;box-shadow:inset 4px 4px 8px #ccb08b80,inset -4px -4px 10px #fffcf9,0 3px 14px #7b5a3024;border-bottom:1px solid #dec7a5}
.po53-tabs button{background:linear-gradient(145deg,#fffaf0,#ecd9bd);border:1px solid #dfc5a1;border-radius:14px;min-height:50px;color:#725238;box-shadow:4px 4px 9px #c6ad8c80,-3px -3px 7px #fffaf4;font-weight:850;transition:transform .14s,box-shadow .14s}
.po53-tabs button:hover:not(:disabled){transform:translateY(-1px)}
.po53-tabs button.active{background:linear-gradient(140deg,#f8e4c6,#e5c8a2);border:1px solid #bd9460;color:#503622;box-shadow:inset 3px 3px 7px #b99b7677,inset -3px -3px 7px #fff7e8,0 2px 4px #76512a18}
@media(max-width:630px){.po53-tabs{gap:5px;padding:8px}.po53-tabs button{min-height:57px;padding:7px 3px;font-size:9px;gap:3px;border-radius:10px}}

/* SOS_INV_PO_V55_NAV — four elegant workflow steps, subordinate to Inventory tabs. */
.po55-form-steps{position:sticky;top:0;z-index:4;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
 gap:0;padding:8px 13px;border-bottom:1px solid #e8dccb;background:#f9f3ea}
.po55-form-steps button{appearance:none;display:flex;align-items:center;justify-content:center;gap:9px;position:relative;
 min-width:0;min-height:45px;padding:6px 8px;border:0;border-radius:9px;background:transparent;color:#978069;
 font-size:11px;font-weight:750;cursor:pointer;transition:color .14s,background .14s}
.po55-form-steps button:not(:last-child):after{content:'';position:absolute;right:-1px;top:16px;bottom:16px;width:1px;background:#e7d9c7}
.po55-form-steps button.is-active{background:#fffdfa;color:#553923;box-shadow:inset 0 0 0 1px #e3cbb0,0 2px 6px #69411f13}
.po55-step-number{display:grid;place-items:center;flex:0 0 27px;width:27px;height:27px;border:1px solid #e4d6c5;border-radius:9px;background:#fffaf3;color:#98795a;font-size:10px;font-weight:850}
.po55-form-steps button.is-active .po55-step-number{background:#715036;color:#fffaf4;border-color:#715036;box-shadow:0 2px 5px #6d442329}
.po55-form-steps button.is-complete .po55-step-number{background:#ebdecf;color:#674a31;border-color:#dac3a7}
.po55-step-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.po55-form-steps button small{display:grid;place-items:center;border-radius:8px;background:#ece1d2;color:#74543a;font-size:9px;min-width:18px;height:18px}
.po55-form-steps button:focus-visible{outline:3px solid #b28c5e;outline-offset:1px}
.po55-form-steps button:disabled{cursor:default;opacity:.7}
@media(max-width:730px){.po55-form-steps{display:flex;gap:2px;overflow-x:auto;padding:6px 8px}.po55-form-steps button{flex:0 0 auto;min-width:118px;min-height:43px;padding:5px 7px;gap:6px}.po55-step-number{width:24px;height:24px;flex-basis:24px}.po55-step-name{font-size:10px}}
@media(prefers-reduced-motion:reduce){.po55-form-steps button{transition:none}}
</style>
