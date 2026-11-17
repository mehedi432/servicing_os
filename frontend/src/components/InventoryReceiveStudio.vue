<script setup>
// SOS_INV_RECEIVE_V57 — dedicated receiving / requisition studio (ERPNext v15)
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({
  items: { type:Array, default:()=>[] },
  warehouses: { type:Array, default:()=>[] },
  currency: { type:String, default:'BDT' },
  company: { type:String, default:'' },
  initialSku: { type:String, default:'' },
  selectedWarehouse: { type:String, default:'' },
})
const emit = defineEmits(['close','received','requested'])
const bn = computed(()=>currentLanguage.value === 'bn')
const tr=(en,bd)=>bn.value?bd:en
const pane=ref('receive'), busy=ref(false), loading=ref(true), error=ref(''), info=ref(null)
const term=ref(''), itemCode=ref(''), itemDropdown=ref(false)
const warehouse=ref(props.selectedWarehouse || props.warehouses?.[0]?.name || '')
const qty=ref(1), buyingRate=ref(''), sellingRate=ref('')
const updatePrices=ref(false), supplierText=ref(''), supplier=ref('')
const supplierList=ref([]), supplierOpen=ref(false), supplierLoading=ref(false), sourceRef=ref(''), remarks=ref('')
const requiredBy=ref(''), reason=ref(''), finished=ref(null)
let supplierTimer=null, supplierRequest=0

function localDatePlus(days=0){const d=new Date();d.setDate(d.getDate()+days);const p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`}
requiredBy.value=localDatePlus(7)
const item=computed(()=>props.items.find(v=>v.item_code===itemCode.value)||null)
const matches=computed(()=>{const q=term.value.trim().toLocaleLowerCase(); if(!q)return props.items.slice(0,12);return props.items.filter(i=>[i.item_name,i.item_code,i.brand,i.item_group].some(s=>String(s||'').toLocaleLowerCase().includes(q))).slice(0,14)})
const available=computed(()=>{
  if(!item.value)return 0
  if(!warehouse.value)return Number(item.value.actual_qty||0)-Number(item.value.reserved_qty||0)
  const b=(item.value.by_warehouse||[]).find(b=>b.warehouse===warehouse.value)
  return Math.max(0,Number(b?.qty||0)-Number(b?.reserved||0))
})
const receiptTotal=computed(()=>positiveNumber(qty.value)*positiveNumber(buyingRate.value))
const expectedStock=computed(()=>available.value+positiveNumber(qty.value))
const margin=computed(()=>{const s=positiveNumber(sellingRate.value),b=positiveNumber(buyingRate.value);return s>0?((s-b)/s)*100:null})
const canReceive=computed(()=>!!info.value?.can_receive)
const canRequest=computed(()=>!!info.value?.can_request)
const showPriceToggle=computed(()=>!!info.value?.can_price_update && !!info.value?.buying_price_list && !!info.value?.selling_price_list)
const trackDisabled=computed(()=>!!item.value && (!!item.value.has_serial_no || !!item.value.has_batch_no))
function positiveNumber(n){const x=Number(n);return Number.isFinite(x)&&x>0?x:0}
function money(n){return new Intl.NumberFormat(bn.value?'bn-BD':'en-BD',{minimumFractionDigits:0,maximumFractionDigits:2}).format(Number(n||0))}
function num(n){return new Intl.NumberFormat(bn.value?'bn-BD':'en-BD',{maximumFractionDigits:3}).format(Number(n||0))}
function choose(i){itemCode.value=i.item_code;term.value=`${i.item_name} · ${i.item_code}`;itemDropdown.value=false;buyingRate.value=i.buying_price!=null?String(i.buying_price):'';sellingRate.value=i.selling_price!=null?String(i.selling_price):'';finished.value=null;error.value=''}
function onTermInput(){itemCode.value='';itemDropdown.value=true;finished.value=null}
function setPane(p){if(busy.value)return; pane.value=p;error.value='';finished.value=null}
function close(){if(!busy.value)emit('close')}
async function api(name,params={},post=false){
  const url=new URL('/api/method/servicing_os.api.inventory_receiving.'+name,window.location.origin)
  const opts={credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}}
  if(post){opts.method='POST';opts.headers['Content-Type']='application/json';const token=window.csrf_token||window.frappe?.csrf_token;if(token)opts.headers['X-Frappe-CSRF-Token']=token;opts.body=JSON.stringify(params)}
  else for(const [k,v] of Object.entries(params))url.searchParams.set(k,String(v??''))
  const res=await fetch(url,opts);let payload
  try{payload=await res.json()}catch{throw new Error('ERPNext returned an invalid response')}
  if(!res.ok||payload.exc||payload.exception){let msg='ERPNext request failed';try{const m=JSON.parse(payload._server_messages||'[]');if(m.length)msg=JSON.parse(m[0]).message||msg}catch{}throw new Error(String(msg).replace(/<[^>]+>/g,''))}
  return payload.message
}
async function loadAccess(){try{info.value=await api('get_receive_access')}catch(e){error.value=e?.message||String(e)}finally{loading.value=false}}
function supplierInput(){supplier.value='';supplierOpen.value=true;if(supplierTimer)clearTimeout(supplierTimer);supplierTimer=setTimeout(loadSupplierMatches,250)}
async function loadSupplierMatches(){const seq=++supplierRequest;supplierLoading.value=true;try{const rows=await api('search_suppliers',{q:supplierText.value});if(seq===supplierRequest){supplierList.value=rows||[];supplierOpen.value=true}}catch{if(seq===supplierRequest)supplierList.value=[]}finally{if(seq===supplierRequest)supplierLoading.value=false}}
function chooseSupplier(s){supplier.value=s.name;supplierText.value=`${s.label} · ${s.name}`;supplierOpen.value=false}
function validate(){
  if(!itemCode.value||!item.value){error.value=tr('Select an existing product from the suggestions.','তালিকা থেকে একটি পণ্য নির্বাচন করুন।');return false}
  if(trackDisabled.value && pane.value==='receive'){error.value=tr('This serial/batch-controlled item must use its dedicated ERPNext receiving flow.','সিরিয়াল/ব্যাচ আইটেমের জন্য আলাদা ERPNext পদ্ধতি ব্যবহার করুন।');return false}
  if(!warehouse.value||!props.warehouses.some(w=>w.name===warehouse.value)){error.value=tr('Choose a valid warehouse.','সঠিক গুদাম নির্বাচন করুন।');return false}
  if(!positiveNumber(qty.value)||Number(qty.value)>9999999){error.value=tr('Enter a valid positive quantity.','সঠিক ধনাত্মক পরিমাণ দিন।');return false}
  return true
}
async function submit(){if(busy.value)return;error.value='';finished.value=null;if(!validate())return
  if(pane.value==='receive'){
    if(!canReceive.value){error.value=tr('Stock Entry submit permission required.','স্টক এন্ট্রি সাবমিটের অনুমতি নেই।');return}
    if(!positiveNumber(buyingRate.value)){error.value=tr('Enter the actual unit purchase/valuation cost.','প্রকৃত একক ক্রয়/মূল্যায়ন হার দিন।');return}
    if(sellingRate.value!==''&&!positiveNumber(sellingRate.value)){error.value=tr('Selling price must be positive or blank.','বিক্রয়মূল্য ধনাত্মক হতে হবে অথবা খালি রাখুন।');return}
    if(supplierText.value&&!supplier.value){error.value=tr('Select the supplier from the suggestions, or clear the field.','তালিকা থেকে সরবরাহকারী নির্বাচন করুন অথবা খালি রাখুন।');return}
  }else{
    if(!canRequest.value){error.value=tr('Material Request create permission required.','মেটেরিয়াল রিকোয়েস্ট তৈরির অনুমতি নেই।');return}
    if(!/^\d{4}-\d{2}-\d{2}$/.test(requiredBy.value)){error.value=tr('Enter a valid required-by date.','প্রয়োজনের সঠিক তারিখ দিন।');return}
  }
  busy.value=true
  try{
    let result
    if(pane.value==='receive'){
      result=await api('receive_stock',{item_code:itemCode.value,warehouse:warehouse.value,qty:qty.value,buying_rate:buyingRate.value,selling_rate:sellingRate.value,supplier:supplier.value,supplier_reference:sourceRef.value,notes:remarks.value,update_catalog_prices:updatePrices.value?1:0},true)
      finished.value={type:'receipt',id:result.stock_entry};emit('received',result)
    }else{
      result=await api('create_purchase_request',{item_code:itemCode.value,warehouse:warehouse.value,qty:qty.value,required_by:requiredBy.value,reason:reason.value},true)
      finished.value={type:'request',id:result.material_request};emit('requested',result)
    }
  }catch(e){error.value=e?.message||String(e)}finally{busy.value=false}
}
onMounted(()=>{if(props.initialSku){const matched=props.items.find(i=>i.item_code===props.initialSku);if(matched)choose(matched)}loadAccess()})
onUnmounted(()=>{if(supplierTimer)clearTimeout(supplierTimer);supplierRequest++})
watch(()=>props.initialSku,sku=>{if(sku){const found=props.items.find(i=>i.item_code===sku);if(found)choose(found)}})
</script>

<template>
  <div class="sr57-backdrop" @click.self="close" @keydown.esc="close">
    <section class="sr57-dialog" role="dialog" aria-modal="true" :aria-label="tr('Stock receiving and purchase request','স্টক গ্রহণ ও মেটেরিয়াল রিকোয়েস্ট')">
      <header class="sr57-header">
        <div class="sr57-title-area">
          <span class="sr57-kicker">{{ tr('AL MODINA · INVENTORY OPERATIONS','আল মদিনা · ইনভেন্টরি কার্যক্রম') }}</span>
          <h2>{{ tr('Stock Receiving Studio','স্টক রিসিভিং স্টুডিও') }}</h2>
          <p>{{ tr('Item master · warehouse · actual cost · procurement request','পণ্য · গুদাম · প্রকৃত ক্রয়মূল্য · ক্রয় অনুরোধ') }}</p>
        </div>
        <button type="button" class="sr57-close" :disabled="busy" @click="close" :aria-label="tr('Close','বন্ধ')">×</button>
      </header>
      <nav class="sr57-tabs" role="tablist" :aria-label="tr('Receiving workflow','গ্রহণ কার্যক্রম')">
        <button type="button" class="sr57-tab" :class="{'is-active':pane==='receive'}" role="tab" :aria-selected="pane==='receive'" @click="setPane('receive')"><span class="sr57-tab-icon">↥</span><span><strong>{{ tr('Receive Stock','স্টক গ্রহণ') }}</strong><small>{{ tr('Post physical stock','প্রকৃত স্টক এন্ট্রি') }}</small></span></button>
        <button type="button" class="sr57-tab" :class="{'is-active':pane==='request'}" role="tab" :aria-selected="pane==='request'" @click="setPane('request')"><span class="sr57-tab-icon">▤</span><span><strong>{{ tr('Request Purchase','ক্রয়ের অনুরোধ') }}</strong><small>{{ tr('Auto-create Material Request','স্বয়ংক্রিয় ম্যাটেরিয়াল রিকোয়েস্ট') }}</small></span></button>
      </nav>
      <div class="sr57-body" role="tabpanel">
        <div v-if="loading" class="sr57-inline">{{tr('Checking ERPNext permissions…','ERPNext অনুমতি যাচাই চলছে…')}}</div>
        <div class="sr57-section-head"><span>01</span><div><strong>{{ tr('Select stock item','স্টক পণ্য নির্বাচন করুন') }}</strong><small>{{ tr('Search by name, SKU or brand','নাম, SKU বা ব্র্যান্ড দিয়ে খুঁজুন') }}</small></div></div>
        <div class="sr57-search-block"><label class="sr57-label" for="sr57-item">{{tr('Product name / SKU','পণ্যের নাম / SKU')}} *</label>
          <div class="sr57-lookup"><input id="sr57-item" v-model="term" type="search" autocomplete="off" :placeholder="tr('Click or type to find an existing item…','পণ্য নির্বাচন করতে লিখুন…')" @focus="itemDropdown=true" @input="onTermInput" @keydown.esc.stop="itemDropdown=false" />
            <span class="sr57-search-glyph" aria-hidden="true">⌕</span>
            <div v-if="itemDropdown" class="sr57-matches" role="listbox">
              <button v-for="i in matches" :key="i.item_code" type="button" role="option" :aria-selected="itemCode===i.item_code" @click="choose(i)"><span class="sr57-monosymbol">{{(i.item_name||'?').slice(0,1)}}</span><span><strong>{{i.item_name}}</strong><small>{{i.item_code}} · {{i.item_group}}</small></span><span class="sr57-match-end">{{num(i.actual_qty)}} {{i.stock_uom}}</span></button>
              <p v-if="!matches.length">{{tr('No matching products','কোনো পণ্য পাওয়া যায়নি')}}</p>
            </div>
          </div>
        </div>
        <div v-if="item" class="sr57-product-card"><div class="sr57-product-avatar"><img v-if="item.image" :src="item.image" :alt="item.item_name"/><span v-else>{{(item.item_name||'?').slice(0,1)}}</span></div><div class="sr57-product-main"><strong>{{item.item_name}}</strong><small>{{item.item_code}} · {{item.item_group}} <span v-if="item.brand">· {{item.brand}}</span></small></div><span class="sr57-stock-pill">{{tr('Stock','স্টক')}} {{num(available)}} {{item.stock_uom}}</span></div>
        <div v-if="item" class="sr57-catalog-snapshot" :aria-label="tr('Current product catalog details','পণ্যের বর্তমান তথ্য')">
          <div><small>{{tr('Saved buying price','সংরক্ষিত ক্রয়মূল্য')}}</small><strong>{{item.buying_price==null?'—':money(item.buying_price)+' '+currency}}</strong></div>
          <div><small>{{tr('Saved selling price','সংরক্ষিত বিক্রয়মূল্য')}}</small><strong>{{item.selling_price==null?'—':money(item.selling_price)+' '+currency}}</strong></div>
          <div><small>{{tr('Warranty','ওয়ারেন্টি')}}</small><strong>{{item.warranty_days?num(item.warranty_days)+' '+tr('days','দিন'):tr('Not set','সেট করা নেই')}}</strong></div>
        </div>
        <div v-if="trackDisabled && pane==='receive'" class="sr57-warning">{{tr('Serial/batch-controlled products require their dedicated ERPNext receipt workflow.','সিরিয়াল/ব্যাচ আইটেমের জন্য ERPNext-এর আলাদা রিসিভ প্রক্রিয়া ব্যবহার করুন।')}}</div>
        <div class="sr57-section-head sr57-gap"><span>02</span><div><strong>{{ pane==='receive'?tr('Receiving details','স্টক গ্রহণের বিবরণ'):tr('Purchase request details','ক্রয়ের অনুরোধের বিবরণ') }}</strong><small>{{tr('All quantities are in the selected product stock unit','সব পরিমাণ নির্বাচিত পণ্যের স্টক এককে')}}</small></div></div>
        <div class="sr57-fields">
          <label class="sr57-field"><span>{{tr('Receiving warehouse','প্রাপ্তির গুদাম')}} *</span><select v-model="warehouse" required><option value="">{{tr('Select a warehouse','গুদাম নির্বাচন করুন')}}</option><option v-for="w in warehouses" :key="w.name" :value="w.name">{{w.warehouse_name||w.name}}</option></select></label>
          <label class="sr57-field"><span>{{pane==='receive'?tr('Received quantity','প্রাপ্ত পরিমাণ'):tr('Required quantity','প্রয়োজনীয় পরিমাণ')}} *</span><div class="sr57-unit-input"><input v-model.number="qty" type="number" min="0.001" step="0.001" required /><em>{{item?.stock_uom||'UOM'}}</em></div></label>
        </div>
        <div v-if="pane==='receive'">
          <div class="sr57-section-head sr57-gap"><span>03</span><div><strong>{{tr('Purchase and selling prices','ক্রয় ও বিক্রয় মূল্য')}}</strong><small>{{tr('Actual receipt cost is the stock valuation basis','প্রকৃত ক্রয়মূল্য হবে স্টক মূল্যায়নের ভিত্তি')}}</small></div></div>
          <div class="sr57-fields">
            <label class="sr57-field"><span>{{tr('Actual buying price / unit','প্রকৃত ক্রয়মূল্য / একক')}} ({{currency}}) *</span><input v-model.number="buyingRate" type="number" min="0.01" step="0.01" required /></label>
            <label class="sr57-field"><span>{{tr('Selling price / unit','বিক্রয়মূল্য / একক')}} ({{currency}})</span><input v-model.number="sellingRate" type="number" min="0.01" step="0.01" /></label>
          </div>
          <div class="sr57-metrics"><div><small>{{tr('Total receipt value','মোট গ্রহণ মূল্য')}}</small><strong>{{money(receiptTotal)}} {{currency}}</strong></div><div><small>{{tr('Expected available','প্রত্যাশিত মজুত')}}</small><strong>{{num(expectedStock)}} {{item?.stock_uom||''}}</strong></div><div><small>{{tr('Indicative gross margin','আনুমানিক গ্রস মার্জিন')}}</small><strong>{{margin===null?'—':num(margin)+'%'}}</strong></div></div>
          <label v-if="showPriceToggle" class="sr57-check"><input v-model="updatePrices" type="checkbox" /><span><strong>{{tr('Update catalog buying and selling prices','ক্যাটালগের ক্রয় ও বিক্রয়মূল্য আপডেট করুন')}}</strong><small>{{tr('Optional: writes general ERPNext Item Price records. Unchecked keeps catalog prices unchanged.','ঐচ্ছিক: ERPNext Item Price পরিবর্তন করে; না দিলে আগের মূল্য থাকবে।')}}</small></span></label>
          <div class="sr57-section-head sr57-gap"><span>04</span><div><strong>{{tr('Supplier and reference','সরবরাহকারী ও রেফারেন্স')}}</strong><small>{{tr('References only — use Purchase Receipt for supplier accounting','শুধু রেফারেন্স — সরবরাহকারী হিসাবের জন্য Purchase Receipt ব্যবহার করুন')}}</small></div></div>
          <div class="sr57-fields"><div class="sr57-field"><label class="sr57-label" for="sr57-supplier">{{tr('Supplier (optional)','সরবরাহকারী (ঐচ্ছিক)')}}</label><div class="sr57-lookup"><input id="sr57-supplier" v-model="supplierText" type="search" autocomplete="off" :placeholder="tr('Search existing suppliers','বিদ্যমান সরবরাহকারী খুঁজুন')" @focus="supplierOpen=true;loadSupplierMatches()" @input="supplierInput" @keydown.esc.stop="supplierOpen=false"/><div v-if="supplierOpen" class="sr57-matches sr57-suppliers" role="listbox"><button v-for="s in supplierList" :key="s.name" type="button" @click="chooseSupplier(s)"><span class="sr57-monosymbol">S</span><span><strong>{{s.label}}</strong><small>{{s.name}}</small></span></button><p v-if="supplierLoading">{{tr('Searching…','খোঁজা হচ্ছে…')}}</p><p v-else-if="!supplierList.length">{{tr('No suppliers found. Leave blank if not applicable.','সরবরাহকারী পাওয়া যায়নি; প্রযোজ্য না হলে খালি রাখুন।')}}</p></div></div></div>
            <label class="sr57-field"><span>{{tr('Invoice / challan / reference no.','ইনভয়েস / চালান / রেফারেন্স নং')}}</span><input v-model="sourceRef" maxlength="140" :placeholder="tr('Optional supplier paperwork reference','ঐচ্ছিক সরবরাহকারীর কাগজপত্র নম্বর')"/></label></div>
          <label class="sr57-field sr57-wide"><span>{{tr('Receiving notes','প্রাপ্তির মন্তব্য')}}</span><textarea v-model="remarks" maxlength="500" rows="2" :placeholder="tr('Condition, inspection, purchase context…','অবস্থা, পরীক্ষা, ক্রয়-সংক্রান্ত তথ্য…')"></textarea></label>
          <div class="sr57-warning"><strong>{{tr('Important','গুরুত্বপূর্ণ')}}:</strong> {{tr('A Direct Material Receipt updates stock and valuation only. It does not create a Purchase Receipt, supplier payable, or Material Request. For procurement, use the Request Purchase tab before receiving.','ডাইরেক্ট ম্যাটেরিয়াল রিসিপ্ট শুধু স্টক ও মূল্যায়ন বদলায়; Purchase Receipt, দেনা বা Material Request তৈরি করে না। ক্রয়ের জন্য আগে Request Purchase ট্যাব ব্যবহার করুন।')}}</div>
        </div>
        <div v-else>
          <div class="sr57-section-head sr57-gap"><span>03</span><div><strong>{{tr('Automatic purchase requisition','স্বয়ংক্রিয় ক্রয় অনুরোধ')}}</strong><small>{{tr('Creates one ERPNext Material Request in Draft','একটি ERPNext Material Request খসড়া তৈরি করবে')}}</small></div></div>
          <div class="sr57-fields"><label class="sr57-field"><span>{{tr('Required by','প্রয়োজনের তারিখ')}} *</span><input v-model="requiredBy" type="date" :min="localDatePlus(0)" required /></label><label class="sr57-field"><span>{{tr('Estimated unit buying price','আনুমানিক ক্রয়মূল্য')}}</span><input :value="buyingRate || ''" type="text" readonly :placeholder="tr('From product catalog','পণ্যের তালিকা থেকে')" /></label></div>
          <label class="sr57-field sr57-wide"><span>{{tr('Reason / purchasing instruction','ক্রয়ের কারণ / নির্দেশনা')}}</span><textarea v-model="reason" rows="3" maxlength="500" :placeholder="tr('Urgent replacement, repair parts, minimum-stock planning…','জরুরি রিপ্লেসমেন্ট, মেরামতের পার্টস, ন্যূনতম মজুত…')"></textarea></label>
          <div class="sr57-request-note"><span>▤</span><div><strong>{{tr('Automatic Draft Material Request','স্বয়ংক্রিয় খসড়া ম্যাটেরিয়াল রিকোয়েস্ট')}}</strong><p>{{tr('One action creates a purchase requirement for the selected SKU and warehouse. It does not increase stock or create a Purchase Order.','এক ক্লিকে নির্বাচিত পণ্য ও গুদামের জন্য ক্রয় অনুরোধ তৈরি হবে। স্টক বা Purchase Order তৈরি হবে না।')}}</p></div></div>
        </div>
        <div v-if="error" class="sr57-error" role="alert">{{error}}</div>
        <div v-if="finished" class="sr57-success" role="status"><strong>{{finished.type==='receipt'?tr('Stock Entry submitted','স্টক এন্ট্রি সাবমিট হয়েছে'):tr('Draft Material Request created','খসড়া ম্যাটেরিয়াল রিকোয়েস্ট তৈরি হয়েছে')}}</strong><span>{{finished.id}}</span></div>
      </div>
      <footer class="sr57-footer"><div class="sr57-footnote"><span class="sr57-dot"></span><span>{{ company }} · {{ tr('ERPNext live records','ERPNext লাইভ রেকর্ড') }}</span></div><div class="sr57-footer-actions"><button type="button" class="sr57-secondary" :disabled="busy" @click="close">{{tr('Close','বন্ধ')}}</button><button type="button" class="sr57-primary" :disabled="busy || loading || (trackDisabled && pane==='receive') || (pane==='receive'&&!canReceive) || (pane==='request'&&!canRequest)" @click="submit"><span v-if="busy">{{tr('Saving…','সংরক্ষণ হচ্ছে…')}}</span><span v-else>{{pane==='receive'?tr('Confirm & Submit Receipt','নিশ্চিত করে স্টক গ্রহণ'):tr('Auto-create Material Request','স্বয়ংক্রিয় রিকোয়েস্ট তৈরি')}}</span><span aria-hidden="true">↗</span></button></div></footer>
    </section>
  </div>
</template>

<style scoped>
.sr57-backdrop,.sr57-backdrop *{box-sizing:border-box}
.sr57-backdrop{position:fixed;inset:0;z-index:10060;background:rgba(40,29,21,.58);backdrop-filter:blur(7px);display:grid;place-items:center;padding:16px}
.sr57-dialog{width:min(910px,100%);max-height:min(94dvh,940px);display:flex;flex-direction:column;overflow:hidden;border:1px solid #dfcdb4;border-radius:23px;color:#493729;background:#fffdfa;box-shadow:0 22px 70px rgba(26,17,9,.34);font-family:inherit}
.sr57-header{flex:0 0 auto;padding:23px 27px 18px;display:flex;justify-content:space-between;gap:16px;align-items:flex-start;background:linear-gradient(120deg,#fffdfa 4%,#f2e6d4 100%);border-bottom:1px solid #ecdfce}
.sr57-kicker{font-size:10px;letter-spacing:.13em;color:#a37a55;font-weight:800}
.sr57-header h2{margin:6px 0 5px;font-size:26px;font-weight:850;letter-spacing:-.04em;color:#3c2b20}
.sr57-header p{margin:0;font-size:12px;color:#927c69}
.sr57-close{appearance:none;flex:0 0 36px;width:36px;height:36px;border:1px solid #ddcfbd;border-radius:11px;background:#fffaf2;color:#664c35;font-size:25px;cursor:pointer;line-height:1}
.sr57-tabs{flex:0 0 auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:13px 25px;background:#f9f3ea;border-bottom:1px solid #e9dcca}
.sr57-tab{min-width:0;display:flex;text-align:left;gap:12px;align-items:center;border:1px solid transparent;border-radius:14px;padding:11px 14px;background:transparent;color:#907865;cursor:pointer}
.sr57-tab.is-active{background:#fffdfa;border-color:#e5ceb0;color:#563c2a;box-shadow:0 3px 0 #ddc7aa,0 7px 15px #ad896529}
.sr57-tab-icon{width:36px;height:36px;flex:0 0 36px;border-radius:11px;display:grid;place-items:center;font-weight:900;font-size:22px;background:#e9dece}
.sr57-tab.is-active .sr57-tab-icon{background:#705037;color:#fff9ef}
.sr57-tab strong{font-weight:800;font-size:13px;display:block;line-height:1.3}
.sr57-tab small{font-size:10px;color:#927c69;display:block;line-height:1.7}
.sr57-body{overflow-y:auto;padding:19px 25px 25px;flex:1 1 auto;min-height:0;overscroll-behavior:contain}
.sr57-section-head{display:flex;align-items:center;gap:11px;margin:0 0 11px}.sr57-section-head>span{display:grid;place-items:center;flex:0 0 29px;width:29px;height:29px;border-radius:9px;background:#ece0d0;color:#7c5c3d;font-weight:800;font-size:11px}.sr57-section-head strong{font-size:13px;font-weight:850}.sr57-section-head small{display:block;font-size:10px;color:#948476;margin-top:2px}.sr57-gap{margin-top:23px}
.sr57-label,.sr57-field>span{font-size:11px;color:#75614d;font-weight:750;line-height:1.5}
.sr57-search-block{margin-bottom:10px}.sr57-lookup{position:relative;min-width:0}.sr57-lookup>input{width:100%;height:44px;outline:none}
.sr57-lookup>input,.sr57-field input,.sr57-field select,.sr57-field textarea{appearance:none;border:1px solid #dfd3c5;background:#fffefd;color:#463729;border-radius:10px;padding:10px 12px;font:inherit;font-size:13px;min-width:0;box-shadow:inset 0 1px 2px #8464440b}
.sr57-lookup>input:focus,.sr57-field input:focus,.sr57-field select:focus,.sr57-field textarea:focus{outline:2px solid #bb9b74;outline-offset:1px;border-color:#a68b66}
.sr57-search-glyph{position:absolute;right:13px;top:11px;font-size:22px;color:#927a62;pointer-events:none}
.sr57-matches{position:absolute;top:calc(100% + 4px);left:0;right:0;max-height:250px;overflow-y:auto;background:#fffdfa;border:1px solid #e4d1ba;border-radius:12px;box-shadow:0 15px 32px #34271b35;z-index:24;padding:4px}
.sr57-matches button{width:100%;background:transparent;border:0;display:flex;gap:9px;align-items:center;text-align:left;padding:9px;border-radius:8px;cursor:pointer;color:#574335}
.sr57-matches button:hover,.sr57-matches button:focus{background:#f2e6d5;outline:none}
.sr57-monosymbol{display:grid;place-items:center;flex:0 0 30px;width:30px;height:30px;background:#efe2d2;border-radius:8px;font-weight:800;color:#745237}
.sr57-matches button>span:nth-child(2){min-width:0;flex:1 1 auto}.sr57-matches strong{display:block;font-size:11px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sr57-matches small{display:block;font-size:10px;color:#938270;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sr57-match-end{font-size:10px;color:#9b826a;white-space:nowrap}.sr57-matches p{font-size:12px;color:#9a8977;padding:10px;margin:0}
.sr57-product-card{display:flex;gap:12px;padding:12px 14px;background:#f6f0e8;border:1px solid #e6d9c9;border-radius:13px;align-items:center;min-width:0}
.sr57-product-avatar{height:44px;width:44px;flex:0 0 44px;border-radius:11px;background:#e9dcc8;color:#674c32;display:grid;place-items:center;font-size:22px;font-weight:900;overflow:hidden}
.sr57-product-avatar img{height:100%;width:100%;object-fit:contain}
.sr57-product-main{min-width:0;flex:1}.sr57-product-main strong{font-size:13px;display:block;line-height:1.5}.sr57-product-main small{font-size:10px;color:#897561;display:block;word-break:break-word}.sr57-stock-pill{font-size:10px;white-space:nowrap;font-weight:800;border:1px solid #dac7ad;border-radius:99px;padding:8px 9px;color:#765332;background:#fffdfa}
.sr57-catalog-snapshot{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin:8px 0 3px}.sr57-catalog-snapshot>div{padding:9px 12px;border-radius:9px;border:1px solid #ebe1d5;background:#fffaf3;min-width:0}.sr57-catalog-snapshot small{display:block;font-size:10px;color:#987c60}.sr57-catalog-snapshot strong{display:block;font-size:12px;color:#57402b;font-weight:800;margin-top:3px;word-break:break-word}
.sr57-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:11px 0}.sr57-field{display:flex;flex-direction:column;min-width:0;gap:6px}.sr57-field input,.sr57-field select{height:44px;width:100%}.sr57-field select{appearance:auto}.sr57-field textarea{resize:vertical;min-height:64px;width:100%}.sr57-unit-input{display:flex;align-items:center;position:relative}.sr57-unit-input input{padding-right:63px}.sr57-unit-input em{position:absolute;right:10px;top:11px;font-size:11px;color:#8d7760;font-style:normal;font-weight:750}
.sr57-wide{margin-top:10px}.sr57-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:14px 0}.sr57-metrics>div{padding:13px;border:1px solid #eadfcf;background:#f9f4ed;border-radius:12px;min-width:0}.sr57-metrics small{display:block;font-size:10px;color:#947c65;margin-bottom:6px}.sr57-metrics strong{font-size:15px;font-weight:850;line-height:1.4;word-break:break-word}
.sr57-check{display:flex;gap:10px;align-items:flex-start;border:1px solid #e8daca;background:#f6f0e8;border-radius:12px;padding:12px 13px;cursor:pointer}.sr57-check input{width:16px;height:16px;accent-color:#765236;flex:0 0 16px;margin-top:2px}.sr57-check strong{font-size:12px;display:block}.sr57-check small{display:block;font-size:10px;line-height:1.6;color:#8a7662;margin-top:3px}
.sr57-warning{font-size:11px;color:#7a6045;line-height:1.7;padding:11px 13px;border:1px solid #e7d7bf;background:#fff6e8;border-radius:11px;margin-top:15px}.sr57-request-note{display:flex;align-items:flex-start;gap:12px;border:1px solid #ddc8af;background:#f5eadb;border-radius:14px;padding:15px;margin-top:15px}.sr57-request-note>span{font-size:25px;color:#744b31}.sr57-request-note strong{display:block;font-size:13px}.sr57-request-note p{font-size:11px;margin:4px 0 0;line-height:1.65;color:#7e6652}
.sr57-error,.sr57-success{border-radius:11px;padding:10px 13px;font-size:12px;line-height:1.5;margin-top:13px}.sr57-error{background:#fff1f0;border:1px solid #dfa8a2;color:#934135}.sr57-success{background:#edf5ee;border:1px solid #c5dac6;color:#31583a;display:flex;gap:12px;flex-wrap:wrap}.sr57-success span{font-weight:900}.sr57-inline{font-size:12px;color:#887460;margin:4px 0 14px}
.sr57-footer{flex:0 0 auto;padding:14px 25px;border-top:1px solid #e6d9c9;background:#fffaf3;display:flex;justify-content:space-between;align-items:center;gap:13px}.sr57-footnote{display:flex;align-items:center;gap:7px;font-size:10px;color:#9d8b78}.sr57-dot{background:#a98e69;border-radius:99px;width:7px;height:7px;flex:0 0 7px}.sr57-footer-actions{display:flex;gap:8px;flex-wrap:wrap}.sr57-footer-actions button{font:inherit;font-size:12px;font-weight:800;border-radius:11px;min-height:43px;padding:9px 16px;cursor:pointer}.sr57-secondary{background:#fffefa;border:1px solid #d8c5ae;color:#70543d}.sr57-primary{background:#6b4b31;border:1px solid #6b4b31;color:#fffaf2;display:flex;align-items:center;gap:8px;justify-content:center}.sr57-primary:disabled{opacity:.55;cursor:not-allowed}.sr57-primary:not(:disabled):hover{background:#50351f}
@media(max-width:680px){.sr57-backdrop{padding:0;place-items:stretch}.sr57-dialog{border-radius:0;max-height:100dvh;height:100dvh;width:100%}.sr57-header{padding:18px 15px}.sr57-header h2{font-size:21px}.sr57-tabs{padding:10px;gap:6px}.sr57-tab{padding:8px;gap:8px}.sr57-tab-icon{width:31px;height:31px;flex-basis:31px}.sr57-tab small{font-size:9px}.sr57-body{padding:15px}.sr57-fields{grid-template-columns:1fr;gap:9px}.sr57-catalog-snapshot{grid-template-columns:1fr 1fr}.sr57-metrics{grid-template-columns:1fr 1fr}.sr57-footer{padding:12px;align-items:stretch;flex-direction:column}.sr57-footer-actions button{flex:1}.sr57-stock-pill{white-space:normal}.sr57-product-card{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){.sr57-dialog *{transition:none!important}}
</style>
