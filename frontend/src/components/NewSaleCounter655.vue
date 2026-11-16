<script setup>
import { watch as sos671Watch } from 'vue'
import CounterCheckout670 from './CounterCheckout670.vue'
function on670Complete(result) {
  if (typeof saved !== 'undefined' && saved?.value) saved.value = {...saved.value, ...result}
  if (typeof info !== 'undefined' && info?.value !== undefined) info.value = 'Sale submitted successfully. Stock and payment are now processed by ERPNext.'
  window.dispatchEvent(new CustomEvent('servicing-os-checkout-completed',{detail:result}))
}


// SERVICING_OS_SHIP_667 — one query returns stock + current Item Price.
async function sos667SearchProducts(q,page=1) {
  const url=new URL('/api/method/servicing_os.api.counter_fast_667.search_sale_products',window.location.origin)
  url.searchParams.set('q',String(q||''));url.searchParams.set('page',String(page||1))
  const response=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
  const data=await response.json()
  if(!response.ok||data.exc||data.exception)throw new Error(errMessage(data,'Unable to search products'))
  return data.message||{}
}


// SERVICING_OS_CUSTOMER_LOOKUP_666 — preserve checkout's existing Customer state.
import CustomerQuickSearch666 from './CustomerQuickSearch666.vue'
function sos666ChooseCounterCustomer(c) {
  clearTimeout(customerTimer)
  customerSequence++
  selectedCustomer.value = c
  customerQuery.value = c.customer_name || c.name
  customerHits.value = []
  customerBusy.value = false
  customerFocused.value = false
}
function sos666ClearCounterCustomer() {
  clearTimeout(customerTimer)
  customerSequence++
  selectedCustomer.value = null
  customerQuery.value = ''
  customerHits.value = []
  customerBusy.value = false
  customerFocused.value = false
}



// SERVICING_OS_FEATURED_665 — browse available stock before searching.
import { ref as sos665Ref, onMounted as sos665Mounted } from 'vue'
const sos665Stock = sos665Ref([])
const sos665Warehouse = sos665Ref('Retail warehouse')
const sos665Loading = sos665Ref(false)
const sos665Error = sos665Ref('')
const sos665Cursors = sos665Ref([0])
const sos665CursorIndex = sos665Ref(0)
const sos665NextCursor = sos665Ref(null)
let sos665RequestSeq = 0
async function sos665LoadStock(cursor=0) {
  const seq = ++sos665RequestSeq
  sos665Loading.value = true
  sos665Error.value = ''
  try {
    const url = new URL('/api/method/servicing_os.api.counter_fast_667.get_stock_products', window.location.origin)
    url.searchParams.set('cursor', String(cursor))
    const response = await fetch(url, { credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'} })
    const data = await response.json()
    if (!response.ok || data.exc || data.exception) throw new Error(errMessage(data,'Unable to load stock items'))
    if (seq !== sos665RequestSeq) return
    sos665Stock.value = (data.message?.items || []).slice(0,20)
    sos665Warehouse.value = data.message?.warehouse || 'Retail warehouse'
    sos665NextCursor.value = data.message?.has_next ? data.message.next_cursor : null
  } catch(e) {
    if (seq === sos665RequestSeq) sos665Error.value = e?.message || 'Unable to load stock.'
  } finally {
    if (seq === sos665RequestSeq) sos665Loading.value = false
  }
}
function sos665Next() {
  if (sos665Loading.value || sos665NextCursor.value == null) return
  sos665Cursors.value = sos665Cursors.value.slice(0,sos665CursorIndex.value+1)
  sos665Cursors.value.push(sos665NextCursor.value)
  sos665CursorIndex.value++
  sos665LoadStock(sos665Cursors.value[sos665CursorIndex.value])
}
function sos665Previous() {
  if (sos665Loading.value || sos665CursorIndex.value<=0) return
  sos665CursorIndex.value--
  sos665LoadStock(sos665Cursors.value[sos665CursorIndex.value])
}
sos665Mounted(() => sos665LoadStock(0))

// SERVICING_OS_CATALOG_664: item search shows 20 sellable catalog entries, including zero-stock.
const sos664ItemPage = ref(1)
const sos664ItemNext = ref(false)

// SERVICING_OS_ITEM_VIEW_663: one saved layout preference across both selling screens.
import { ref as sos663Ref, onMounted as sos663Mounted, onUnmounted as sos663Unmounted } from 'vue'
const sos663View = sos663Ref('grid')
const sos663StorageKey = 'servicing-os-product-view-v1'
function sos663SetView(layout) {
  if (layout !== 'grid' && layout !== 'list') return
  sos663View.value = layout
  try { window.localStorage.setItem(sos663StorageKey, layout) } catch (_) { /* private browsing */ }
  window.dispatchEvent(new CustomEvent('servicing-os-product-view', { detail: layout }))
}
function sos663SyncView(event) {
  const next = event?.detail
  if (next === 'grid' || next === 'list') sos663View.value = next
}
function sos663StorageChange(event) {
  if (event?.key === sos663StorageKey && ['grid','list'].includes(event.newValue)) {
    sos663View.value = event.newValue
  }
}
sos663Mounted(() => {
  try {
    const value = window.localStorage.getItem(sos663StorageKey)
    if (value === 'grid' || value === 'list') sos663View.value = value
  } catch (_) { /* storage unavailable */ }
  window.addEventListener('servicing-os-product-view', sos663SyncView)
  window.addEventListener('storage', sos663StorageChange)
})
sos663Unmounted(() => {
  window.removeEventListener('servicing-os-product-view', sos663SyncView)
  window.removeEventListener('storage', sos663StorageChange)
})

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

// SERVICING_OS_WARRANTY_672: warranty is a value per sale line, not global state.
function sos672ManualWarranty(row) {
  if (row.sos672WarrantySource === 'item_master') return
  row.sos672WarrantySource = 'manual'
  row.sos672WarrantySelected = true
  row.sos672WarrantyError = ''
  saved.value = null
}
function sos672SetNoWarranty(row) {
  if (row.sos672WarrantySource === 'item_master') return
  row.sos672WarrantyDays = 0
  row.sos672WarrantySource = 'none'
  row.sos672WarrantySelected = true
  row.sos672WarrantyError = ''
  saved.value = null
}
function sos672WarrantyValid(row) {
  if (row.sos672WarrantyError || row.sos672WarrantyPending) return false
  const days = Number(row.sos672WarrantyDays)
  return row.sos672WarrantySource === 'none' ||
    ((row.sos672WarrantySource === 'manual' || row.sos672WarrantySource === 'item_master') &&
     Number.isInteger(days) && days >= 1 && days <= 36500)
}

// SERVICING_OS_671: read-only per-item warranty from ERPNext Item.warranty_period.
const sos671Warranty = ref({})
let sos671WarrantySequence = 0
sos671Watch(() => cart.value.map(r => r.item_code).join('|'), async (key) => {
  const seq = ++sos671WarrantySequence
  const codes = [...new Set(cart.value.map(r => r.item_code).filter(Boolean))].slice(0,25)
  if (!codes.length) { sos671Warranty.value = {}; return }
  for (const row of cart.value) if (codes.includes(row.item_code)) {row.sos672WarrantyPending=true;row.sos672WarrantyError=''}
  try {
    const url = new URL('/api/method/servicing_os.api.item_warranty_671.get_item_warranties', window.location.origin)
    url.searchParams.set('items', JSON.stringify(codes))
    const response = await fetch(url, {credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'}})
    const data = await response.json()
    if (!response.ok || data.exc || data.exception) throw new Error('Item warranty lookup failed')
    if (seq === sos671WarrantySequence) {
      sos671Warranty.value = Object.fromEntries((data.message?.items || []).map(v => [v.item_code, Number(v.warranty_period_days || 0)]))
      // Keep manual values intact if the user already chose a warranty.
      for (const row of cart.value) {
        if (!codes.includes(row.item_code)) continue
        const master = Number(sos671Warranty.value[row.item_code] || 0)
        if (master > 0) {
          row.sos672WarrantyDays = master
          row.sos672WarrantySource = 'item_master'
          row.sos672WarrantySelected = true
        } else if (!row.sos672WarrantySelected) {
          row.sos672WarrantyDays = ''
          row.sos672WarrantySource = 'manual'
        }
        row.sos672WarrantyPending = false
        row.sos672WarrantyError = ''
      }
    }
  } catch (_) {
    if (seq === sos671WarrantySequence) for (const row of cart.value) if (codes.includes(row.item_code)) {row.sos672WarrantyPending=false;row.sos672WarrantyError='Warranty lookup failed. Retry the product.'}
  }
}, {immediate:true})

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

// SERVICING_OS_AUTO_SELLING_PRICE_660 — read from ERPNext selling Item Price.
async function sos660FetchPrice(itemCode) {
  const url = new URL('/api/method/servicing_os.api.counter_selling_price_660.get_selling_price', window.location.origin)
  url.searchParams.set('item_code', String(itemCode))
  const response = await fetch(url, {
    method: 'GET', credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json' }
  })
  const data = await response.json()
  if (!response.ok || data.exc || data.exception) {
    throw new Error(errMessage(data, 'Unable to fetch ERPNext selling price'))
  }
  if (!data.message?.found || data.message.rate === null || data.message.rate === undefined) {
    throw new Error(data.message?.message || 'No valid selling price is configured for this item.')
  }
  return data.message
}
async function sos660LoadPrice(row) {
  if (row.priceLoading) return
  row.priceLoading = true
  row.priceError = ''
  row.rate = null
  try {
    const result = await sos660FetchPrice(row.item_code)
    if (!cart.value.includes(row)) return
    row.rate = Number(result.rate)
    row.priceList = result.price_list
    row.priceSource = result.item_price
  } catch (e) {
    if (cart.value.includes(row)) {
      row.priceError = e?.message || 'Selling price unavailable'
      error.value = row.priceError
    }
  } finally {
    row.priceLoading = false
  }
}

function closeItems(){setTimeout(()=>{itemFocused.value=false;itemHits.value=[]},190)}
function closeCustomers(){setTimeout(()=>{customerFocused.value=false;customerHits.value=[]},190)}
function lookupItems(page=1){
 clearTimeout(itemTimer)
 const q=query.value.trim()
 const seq=++itemSequence
 const requested=Math.max(1,Number(page)||1)
 sos664ItemPage.value=requested
 itemHits.value=[]
 sos664ItemNext.value=false
 if(!itemFocused.value)return
 itemTimer=setTimeout(async()=>{
   itemBusy.value=true
   try{
     const data=await sos667SearchProducts(q,requested)
     if(seq===itemSequence && itemFocused.value){
       itemHits.value=(data.results||[]).slice(0,20)
       sos664ItemNext.value=!!data.has_next
     }
   }catch(e){if(seq===itemSequence)error.value=e.message}
   finally{if(seq===itemSequence)itemBusy.value=false}
 },180)
}
function lookupCustomers(){
 clearTimeout(customerTimer); const q=customerQuery.value.trim(); const seq=++customerSequence; customerHits.value=[];selectedCustomer.value=null
 if(!customerFocused.value||q.length<1)return
 customerTimer=setTimeout(async()=>{customerBusy.value=true;try{const data=await request('search_invoice_customers',{q});if(seq===customerSequence)customerHits.value=(data.results||[]).slice(0,12)}catch(e){if(seq===customerSequence)error.value=e.message}finally{if(seq===customerSequence)customerBusy.value=false}},220)
}
function selectCustomer(c){selectedCustomer.value=c;customerQuery.value=c.customer_name||c.name;customerFocused.value=false;customerHits.value=[]}
function addItem(product){
 const code = product.name || product.item_code
 let row = cart.value.find(x => x.item_code === code && !x.has_serial_no)
 if (row) row.qty += 1
 else {
   row = {item_code:code,item_name:product.item_name||code,qty:1,
     rate:null,discount_percentage:0,serial_no:'',has_serial_no:!!product.has_serial_no,
     stock_qty:product.stock_qty,priceLoading:false,priceError:'',priceList:'',priceSource:''}
   cart.value.push(row)
 }
 // SERVICING_OS_SHIP_667: list_price is from the active ERPNext selling Price List.
 // Set it immediately, rather than making the cashier wait for another request.
 if ((row.rate === null || row.rate === undefined || row.priceError) &&
     product.list_price !== null && product.list_price !== undefined &&
     Number.isFinite(Number(product.list_price)) && Number(product.list_price)>=0) {
   row.rate = Number(product.list_price)
   row.priceList = product.price_list || 'Selling Price List'
   row.priceSource = product.item_price || ''
   row.priceError = ''
 }
 // Missing Item Price is a blocker; never substitute a purchase/valuation rate.
 if (row.rate === null || row.rate === undefined || row.priceError) sos660LoadPrice(row)
 query.value='';itemHits.value=[];itemFocused.value=false;
 info.value='Added '+code+' to cart';saved.value=null
}
function removeItem(i){cart.value.splice(i,1); saved.value=null}
function newSale(){cart.value=[];selectedCustomer.value=null;customerQuery.value='';discountMode.value='none';discountValue.value=0;saved.value=null;error.value='';info.value='';query.value=''}
async function createDraft(){
 error.value='';info.value=''
 if(!selectedCustomer.value?.name){error.value='Select an existing Customer from suggestions.';return}
 if(!cart.value.length){error.value='Add one or more items to cart.';return}
 if(cart.value.some(x=>x.priceLoading || x.priceError || x.rate === null || x.rate === undefined || x.rate === '')){error.value='Wait for the selling price or update the missing Item Price in ERPNext.';return}
 if(cart.value.some(x=>!x.item_code||!(Number(x.qty)>0)||!Number.isFinite(Number(x.rate))||Number(x.rate)<0||Number(x.discount_percentage)<0||Number(x.discount_percentage)>100)){
  error.value='Review all item quantities, rates, and line discounts.';return
 }
 if(!Number.isFinite(Number(discountValue.value))||Number(discountValue.value)<0||(discountMode.value==='percent'&&Number(discountValue.value)>=100)||(discountMode.value==='amount'&&Number(discountValue.value)>=subtotal.value)||total.value<=0){error.value='Review the overall discount and invoice total.';return}
 if(cart.value.some(row=>!sos672WarrantyValid(row))){error.value='Each item needs ERPNext warranty days, manually entered days, or an explicit No warranty choice.';return}
 saving.value=true
 try{
 const data=await request('create_unified_invoice_draft',{}, {invoice_kind:'retail',customer:selectedCustomer.value.name,items:cart.value.map(x=>({item_code:x.item_code,qty:Number(x.qty),rate:Number(x.rate),discount_percentage:Number(x.discount_percentage||0),serial_no:x.serial_no||'',warranty_choice:x.sos672WarrantySource||'',warranty_period_days:x.sos672WarrantySource==='none'?0:Number(x.sos672WarrantyDays||0)})),discount_mode:discountMode.value,discount_value:discountMode.value==='none'?0:Number(discountValue.value),remarks:'Created from SERVICING OS New Sale counter'})
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
       <div class="sos655-sales-title"><div><h2>New Sale</h2><p>Search and add multiple inventory items.</p></div><div class="sos663-counter-actions"><span class="sos663-counter-count">{{ cart.length }} item types</span><div class="sos663-viewbar" role="group" aria-label="Product view">
  <span class="sos663-viewbar-label">View</span>
  <button type="button" :class="{ 'sos663-selected': sos663View === 'grid' }"
    :aria-pressed="sos663View === 'grid'" title="Grid view" @mousedown.prevent
    @click="sos663SetView('grid')">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
    Grid
  </button>
  <button type="button" :class="{ 'sos663-selected': sos663View === 'list' }"
    :aria-pressed="sos663View === 'list'" title="List view" @mousedown.prevent
    @click="sos663SetView('list')">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01"/></svg>
    List
  </button>
</div></div></div>
       <div class="sos655-search-box">
         <label for="sos655-itemsearch">Find product / item code</label>
         <div class="sos655-search-line"><input id="sos655-itemsearch" v-model="query" type="search" autocomplete="off" placeholder="Select this field, then search items…" @focus="itemFocused=true;lookupItems()" @input="lookupItems" @blur="closeItems" @keydown.esc="itemFocused=false" /><span v-if="itemBusy">Searching…</span></div>
         <div v-if="itemFocused" class="sos655-product-results" :data-sos663-view="sos663View">
            <p v-if="!itemBusy&&!itemHits.length">No matching products.</p>
            <button v-for="item in itemHits" :key="item.name" type="button" @mousedown.prevent="addItem(item)" :disabled="!!item.is_stock_item && Number(item.stock_qty)<=0">
             <span class="sos655-item-icon" aria-hidden="true">▦</span><strong>{{ item.item_name||item.name }}</strong><small>{{ item.name }}</small><small v-if="item.stock_qty!==null&&item.stock_qty!==undefined"
               class="sos664-stock-tag" :class="{out:Number(item.stock_qty)<=0}">
               {{ Number(item.stock_qty)>0 ? 'In stock: '+item.stock_qty : 'Out of stock · 0' }}
             </small><b>Add +</b>
            </button>
         
         <!-- SERVICING_OS_CATALOG_664: keep pagination inside the focused product picker. -->
         <div v-if="itemHits.length || sos664ItemNext || sos664ItemPage>1" class="sos664-item-pager">
           <span>Showing {{ itemHits.length }} products · Page {{ sos664ItemPage }} · Stock and out-of-stock</span>
           <div class="sos664-pages">
             <button type="button" @mousedown.prevent @click="lookupItems(sos664ItemPage-1)" :disabled="itemBusy || sos664ItemPage<=1">Previous</button>
             <button type="button" @mousedown.prevent @click="lookupItems(sos664ItemPage+1)" :disabled="itemBusy || !sos664ItemNext">Next 20</button>
           </div>
         </div>
         </div>
       </div>
       
       <!-- SERVICING_OS_FEATURED_665: visible without selecting search or any cart item. -->
       

       <div class="sos655-cart-header"><h3>Sale Items</h3><span>{{ itemCount }} unit(s)</span></div>
              <div v-if="cart.length" class="sos665-cart-column-head" aria-hidden="true"><span>PRODUCT / ITEM CODE</span><span>QTY</span><span>UNIT PRICE</span><span>DISCOUNT %</span><span>WARRANTY (DAYS)</span><span>LINE TOTAL</span><span></span></div>
       <div v-if="!cart.length" class="sos655-cart-empty">Select a product above to start this sale. Add as many different items as needed.</div>
       <div v-for="(row,i) in cart" :key="row.item_code+'-'+i" class="sos655-cart-line">
         <div class="sos655-product-name"><strong>{{ row.item_name }}</strong><small>{{ row.item_code }}</small><small v-if="sos671Warranty[row.item_code] > 0" class="sos671-warranty">ERPNext warranty · {{ sos671Warranty[row.item_code] }} days</small></div>
         <label>Qty<input v-model.number="row.qty" type="number" min="0.01" step="0.01" :max="row.stock_qty===null?undefined:row.stock_qty" /></label>
         <label>Unit Price ৳
           <input :value="row.rate===null?'':row.rate" type="number" min="0" step="0.01" readonly :aria-busy="row.priceLoading" title="Fetched from ERPNext Selling Price List; use Discount for reductions" />
           <small v-if="row.priceLoading" class="sos660-price-note">Fetching selling price…</small>
           <small v-else-if="row.priceError" class="sos660-price-error">{{ row.priceError }} <button type="button" @click="sos660LoadPrice(row)">Retry</button></small>
           <small v-else-if="row.priceList" class="sos660-price-note">{{ row.priceList }}</small>
         </label>
         <label>Disc. %<input v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.01" /></label>
         <label class="sos672-warranty-label">Warranty (Days)
           <input v-model.number="row.sos672WarrantyDays" type="number" min="1" max="36500" step="1"
             :readonly="row.sos672WarrantySource === 'item_master'"
             :disabled="row.sos672WarrantyPending" :placeholder="row.sos672WarrantyPending?'Loading…':'Enter days'"
             @input="sos672ManualWarranty(row)" aria-label="Warranty days for this item" />
           <small v-if="row.sos672WarrantySource==='item_master'">From Item Master</small>
           <small v-else-if="row.sos672WarrantyPending">Checking Item Master…</small>
           <small v-else-if="row.sos672WarrantyError" class="sos660-price-error">{{ row.sos672WarrantyError }}</small>
           <small v-else-if="row.sos672WarrantySource==='none'">No warranty selected</small>
           <small v-else>Manual warranty days</small>
           <button v-if="row.sos672WarrantySource!=='item_master' && !row.sos672WarrantyPending"
             class="sos672-no-warranty" type="button" @click="sos672SetNoWarranty(row)">No warranty</button>
         </label>
         <strong class="sos655-row-total">৳ {{ money(lineTotal(row)) }}</strong>
         <button class="sos655-remove" type="button" aria-label="Remove item" @click="removeItem(i)">×</button>
         <label v-if="row.has_serial_no" class="sos655-serial">Serial number(s)<textarea v-model="row.serial_no" rows="2" placeholder="One serial number per unit" /></label>
       </div>
       <div class="sos655-sales-footer"><button type="button" @click="newSale">Clear sale</button><p>Stock is validated on invoice creation. Final stock/payment posting occurs when the invoice is submitted through ERPNext.</p></div>
<!-- SOS666_CART_BEFORE_STOCK -->
<section v-if="!itemFocused && !query.trim()" class="sos665-featured-section" aria-label="In stock products">
         <div class="sos665-featured-heading">
           <div><h3>In Stock · Ready to Sell</h3><p>Up to 20 available products · {{ sos665Warehouse }}</p></div>
           <button type="button" class="sos665-reload" @click="sos665LoadStock(sos665Cursors[sos665CursorIndex])" :disabled="sos665Loading">Refresh</button>
         </div>
         <p v-if="sos665Error" role="alert" class="sos665-featured-error">{{ sos665Error }}</p>
         <p v-else-if="sos665Loading && !sos665Stock.length" class="sos665-featured-muted">Loading available products…</p>
         <p v-else-if="!sos665Stock.length" class="sos665-featured-muted">No stocked items found in the selected retail warehouse.</p>
         <div class="sos665-stock-grid" :data-sos663-view="sos663View">
           <button v-for="item in sos665Stock" :key="item.item_code" type="button" :disabled="Number(item.stock_qty)<=0"
             @click="addItem(item)" :title="item.item_name+' — '+item.item_code">
             <span class="sos665-product-mark" aria-hidden="true">▣</span>
             <strong>{{ item.item_name }}</strong>
             <small>{{ item.item_code }}</small>
             <small class="sos665-price">{{ item.list_price !== null && item.list_price !== undefined ? "৳ " + money(item.list_price) : "Price on selection" }}</small>
             <span class="sos665-product-bottom"><small class="sos665-qty">{{ item.stock_qty }} in stock</small><b>Add +</b></span>
           </button>
         </div>
         <div v-if="sos665Stock.length" class="sos665-pagination">
           <span>Page {{ sos665CursorIndex+1 }} · {{ sos665Stock.length }} available products</span>
           <div>
             <button type="button" @click="sos665Previous" :disabled="sos665Loading||sos665CursorIndex===0">Previous</button>
             <button type="button" @click="sos665Next" :disabled="sos665Loading||sos665NextCursor==null">Next 20</button>
           </div>
         </div>
       </section>

     </section>
     <aside class="sos655-checkout">
       <h2>Checkout & Billing</h2>
       <p class="sos655-muted">Invoice for multiple products</p>
       <div class="sos655-customer-field">
         <CustomerQuickSearch666 :selected="selectedCustomer" label="Customer · Search name or mobile number"
           @selected="sos666ChooseCounterCustomer" @clear="sos666ClearCounterCustomer" />
</div>
       <div class="sos655-summary-row"><span>Subtotal</span><strong>৳ {{ money(subtotal) }}</strong></div>
       <div class="sos655-discount-fields"><label>Overall discount<select v-model="discountMode" @change="discountValue=0"><option value="none">No discount</option><option value="percent">Percentage (%)</option><option value="amount">Fixed amount (BDT)</option></select></label><label v-if="discountMode!=='none'">Discount {{ discountMode==='percent'?'%':'BDT' }}<input v-model.number="discountValue" type="number" min="0" step="0.01" :max="discountMode==='percent'?99.99:undefined" /></label></div>
       <div class="sos655-summary-row"><span>Additional discount</span><strong>− ৳ {{ money(overall) }}</strong></div>
       <div class="sos655-summary-row grand"><span>Before tax</span><strong>৳ {{ money(total) }}</strong></div>
       <p class="sos655-notice">Saves an ERPNext <b>draft</b> Sales Invoice; no stock deduction or payment posting yet. Use Existing POS Checkout for your current direct checkout workflow.</p>
       <button type="button" class="sos655-save" :disabled="saving||!cart.length||!!saved||cart.some(row=>row.priceLoading||row.priceError||row.rate===null||row.rate===undefined)" @click="createDraft">{{ saving?'Saving…':'Review & Continue to Checkout' }}</button>
       <div v-if="saved" class="sos655-success" role="status">{{ Number(saved.docstatus)===1 ? (saved.update_stock ? 'Submitted · Stock posted' : 'Submitted') : 'Draft saved' }}: <strong>{{ saved.invoice }}</strong> · {{ saved.currency }} {{ money(saved.grand_total) }}</div>
       <p v-if="error" role="alert" class="sos655-error">{{ error }}</p><p v-else-if="info" class="sos655-info">{{ info }}</p>
     
       <!-- SERVICING_OS_670: same-screen draft edit and final checkout -->
       <CounterCheckout670 :invoice-name="saved?.invoice || ''" @completed="on670Complete" />
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

<style>
/* SERVICING_OS_AUTO_SELLING_PRICE_660 */
.sos655-new-sale .sos660-price-note{color:#866a52;font-size:10px;font-weight:500;line-height:1.2}
.sos655-new-sale .sos660-price-error{color:#9d412c;font-size:10px;font-weight:600;overflow-wrap:anywhere}
.sos655-new-sale .sos660-price-error button{font-size:10px;color:#805a3e;text-decoration:underline;background:transparent!important;border:0!important;padding:1px!important}
.sos655-new-sale input[readonly]{background:#f5ebe2!important;color:#634633!important;cursor:default}
</style>

<style>

/* SERVICING_OS_ITEM_VIEW_663 — warm ivory product display switch. */
.sos663-viewbar,.sos663-viewbar *{box-sizing:border-box}
.sos663-viewbar{display:inline-flex;align-items:center;gap:4px;padding:4px;
 background:#f6ede4!important;border:1px solid #e4cdb9!important;border-radius:11px;
 flex-shrink:0;max-width:100%}
.sos663-viewbar-label{font-size:11px;color:#8a6d57;font-weight:650;padding:0 7px}
.sos663-viewbar button{display:inline-flex!important;align-items:center!important;justify-content:center!important;
 gap:5px!important;white-space:nowrap;min-height:33px!important;padding:6px 11px!important;
 border:1px solid transparent!important;border-radius:8px!important;background:transparent!important;
 color:#78563f!important;font-size:12px!important;line-height:1.2!important;font-weight:700!important;
 box-shadow:none!important;cursor:pointer}
.sos663-viewbar button.sos663-selected{background:#fffcf7!important;border-color:#e4cdb9!important;
 color:#4a3021!important;box-shadow:0 2px 5px #5a423017!important}
.sos663-viewbar button:hover:not(.sos663-selected){background:#efe2d6!important}
.sos663-viewbar button:focus-visible{outline:2px solid #996d4d!important;outline-offset:2px!important}
.sos663-viewbar svg{display:block;flex-shrink:0}

.sos655-new-sale .sos663-counter-actions{display:flex;gap:9px;align-items:center;justify-content:flex-end;flex-wrap:wrap;min-width:0}
.sos655-new-sale .sos663-counter-count{font-size:11px;color:#8b725e;background:#f4e3d3;border-radius:7px;padding:6px 8px;white-space:nowrap}
.sos655-new-sale .sos655-product-results[data-sos663-view="list"]{
 display:flex!important;flex-direction:column!important;grid-template-columns:none!important;gap:7px!important;
 max-height:380px!important;align-items:stretch!important}
.sos655-new-sale .sos655-product-results[data-sos663-view="list"] > button{
 display:flex!important;flex-direction:row!important;flex-wrap:wrap!important;align-items:center!important;
 min-height:62px!important;width:100%!important;text-align:left!important;padding:10px 12px!important;gap:9px!important}
.sos655-new-sale .sos655-product-results[data-sos663-view="list"] > button strong{
 flex:1 1 180px;min-width:100px;font-size:12px!important}
.sos655-new-sale .sos655-product-results[data-sos663-view="list"] > button small{
 flex:0 1 auto;max-width:170px;margin:0;color:#876c59}
.sos655-new-sale .sos655-product-results[data-sos663-view="list"] > button b{
 margin-left:auto!important;margin-top:0!important;white-space:nowrap;color:#805a3e}
@media(max-width:740px){.sos655-new-sale .sos655-sales-title{flex-wrap:wrap}
 .sos655-new-sale .sos663-counter-actions{justify-content:space-between;width:100%}}

</style>

<style>
/* SERVICING_OS_CATALOG_664 — ivory item list with stock labels and paging */
.sos655-new-sale .sos655-product-results{max-height:420px!important;overflow-y:auto!important;align-content:start!important}
.sos655-new-sale .sos655-product-results > button[disabled]{opacity:.67!important;cursor:not-allowed!important;background:#f8f1ea!important}
.sos655-new-sale .sos664-stock-tag{color:#805a3e!important;font-size:10px!important;font-weight:650}
.sos655-new-sale .sos664-stock-tag.out{color:#a34c39!important}
.sos655-new-sale .sos664-item-pager{grid-column:1/-1!important;display:flex!important;align-items:center!important;justify-content:space-between!important;gap:8px!important;flex-wrap:wrap!important;padding:10px 3px!important;border-top:1px solid #e7d6c5!important;color:#7b5e4c;font-size:11px}
.sos655-new-sale .sos664-pages{display:flex!important;gap:6px!important}
.sos655-new-sale .sos664-pages>button{min-height:32px!important;border:1px solid #ddc8b5!important;border-radius:8px!important;background:#fffcf7!important;color:#77543d!important;padding:6px 11px!important;font-weight:650!important}
.sos655-new-sale .sos664-pages>button:disabled{opacity:.40!important;cursor:not-allowed!important}
</style>

<style>
/* SERVICING_OS_FEATURED_665 — ivory stock browser / consistent six-column sale rows. */
.sos655-sales-main { container-type:inline-size; }
.sos665-featured-section{margin:0 0 20px;padding:15px;background:#fffdfa;border:1px solid #ead9c9;border-radius:13px;min-width:0}
.sos665-featured-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}
.sos665-featured-heading h3{margin:0 0 3px;color:#3c2c25;font-size:14px;font-weight:760}
.sos665-featured-heading p{margin:0;color:#8b725e;font-size:11px;line-height:1.4}
.sos665-reload,.sos665-pagination button{border:1px solid #e2cdbb!important;border-radius:8px!important;background:#f4e9dd!important;color:#79583f!important;min-height:33px!important;padding:7px 12px!important;font-size:11px!important;font-weight:680!important;white-space:nowrap}
.sos665-reload:disabled,.sos665-pagination button:disabled{opacity:.45;cursor:not-allowed}
.sos665-featured-muted,.sos665-featured-error{padding:14px 0;color:#876b55;font-size:12px}.sos665-featured-error{color:#983f34}
.sos665-stock-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;min-width:0}
.sos665-stock-grid[data-sos663-view="list"]{display:flex;flex-direction:column}
.sos665-stock-grid>button{display:flex;flex-direction:column;gap:5px;align-items:flex-start;min-width:0;min-height:121px;background:#fffcf7!important;border:1px solid #ead9c8!important;border-radius:11px!important;text-align:left!important;padding:11px!important;color:#3c2c25!important;box-shadow:0 1px 3px #4a382009!important}
.sos665-stock-grid>button:hover{border-color:#c79f7f!important;background:#fff7ef!important;box-shadow:0 4px 12px #805a3e12!important}
.sos665-stock-grid>button:focus-visible{outline:2px solid #a77b59;outline-offset:2px}
.sos665-product-mark{display:grid;place-items:center;width:29px;height:29px;background:#f4e3d3;border-radius:8px;color:#876044;font-size:16px}
.sos665-stock-grid strong{font-size:11.5px;line-height:1.4;font-weight:750;overflow-wrap:anywhere}
.sos665-stock-grid small{font-size:10px;color:#89705d;overflow-wrap:anywhere}
.sos665-stock-grid .sos665-price{font-size:12px;color:#75523e;font-weight:750}
.sos665-product-bottom{display:flex;align-items:center;justify-content:space-between;width:100%;gap:6px;margin-top:auto;padding-top:6px}
.sos665-product-bottom .sos665-qty{color:#587d52!important;font-weight:680!important}
.sos665-product-bottom b{color:#805a3e;font-size:10px;white-space:nowrap}
.sos665-stock-grid[data-sos663-view="list"]>button{min-height:64px;display:grid;grid-template-columns:30px minmax(0,1fr) 150px;column-gap:10px;align-items:center}
.sos665-stock-grid[data-sos663-view="list"]>button>strong{grid-column:2;grid-row:1}
.sos665-stock-grid[data-sos663-view="list"]>button>small{grid-column:2;grid-row:2}
.sos665-stock-grid[data-sos663-view="list"]>button>.sos665-price{grid-column:2;grid-row:3}
.sos665-stock-grid[data-sos663-view="list"] .sos665-product-mark{grid-column:1;grid-row:1/3}
.sos665-stock-grid[data-sos663-view="list"] .sos665-product-bottom{grid-column:3;grid-row:1/3;justify-content:flex-end;gap:12px}
.sos665-pagination{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;border-top:1px solid #ede0d6;margin-top:12px;padding-top:10px;color:#8b725e;font-size:11px}
.sos665-pagination>div{display:flex;gap:6px}
/* Product, Qty, Unit Price, Discount, Line Amount, remove — exact same columns for header and each row. */
.sos665-cart-column-head,.sos655-new-sale .sos655-cart-line{
 grid-template-columns:minmax(160px,2.65fr) minmax(68px,.7fr) minmax(108px,1.08fr) minmax(84px,.8fr) minmax(110px,1.02fr) 40px!important;
 gap:10px!important;min-width:0!important}
.sos665-cart-column-head{display:grid;align-items:end;margin-top:12px;padding:8px 4px;background:#f7eee5;border-radius:8px;color:#8b6d58;font-size:10px;font-weight:750}
.sos665-cart-column-head span:nth-child(5){text-align:right}
.sos655-new-sale .sos655-cart-line{display:grid!important;align-items:center!important;padding:12px 4px!important}
.sos655-new-sale .sos655-cart-line>.sos655-product-name{min-width:0!important;grid-column:1!important}
.sos655-new-sale .sos655-cart-line>label{min-width:0!important;align-self:center!important;overflow-wrap:anywhere}
.sos655-new-sale .sos655-cart-line>label input{width:100%!important;min-height:41px!important}
.sos655-new-sale .sos655-cart-line>.sos655-row-total{grid-column:5!important;text-align:right!important;white-space:nowrap!important;font-size:12px!important;font-weight:780!important;align-self:center!important}
.sos655-new-sale .sos655-cart-line>.sos655-remove{grid-column:6!important;align-self:center!important;width:40px!important;min-height:40px!important;line-height:1!important}
.sos655-new-sale .sos655-cart-line>.sos655-serial{grid-column:1/-1!important}
@container (max-width:760px){
 .sos665-cart-column-head{display:none}
 .sos655-new-sale .sos655-cart-line{grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:9px!important}
 .sos655-new-sale .sos655-cart-line>.sos655-product-name{grid-column:1/-1!important}
 .sos655-new-sale .sos655-cart-line>label:nth-of-type(1){grid-column:1/3!important}
 .sos655-new-sale .sos655-cart-line>label:nth-of-type(2){grid-column:3/5!important}
 .sos655-new-sale .sos655-cart-line>label:nth-of-type(3){grid-column:5/7!important}
 .sos655-new-sale .sos655-cart-line>.sos655-row-total{grid-column:1/6!important;text-align:left!important}
 .sos655-new-sale .sos655-cart-line>.sos655-remove{grid-column:6!important}
 .sos655-new-sale .sos655-cart-line>.sos655-serial{grid-column:1/-1!important}
 .sos665-stock-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@container (max-width:480px){
 .sos665-stock-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .sos665-featured-heading{flex-wrap:wrap}
 .sos665-stock-grid[data-sos663-view="list"]>button{grid-template-columns:26px minmax(0,1fr)}
 .sos665-stock-grid[data-sos663-view="list"] .sos665-product-bottom{grid-column:2;grid-row:3}
}
</style>

<style>
/* 6.67: same reliable ivory product view, using container rather than viewport width. */
.sos655-new-sale,.sos655-sales-layout,.sos655-sales-main,.sos655-checkout{min-width:0!important;max-width:100%}
.sos655-new-sale .sos655-sales-main{container-type:inline-size}
.sos655-new-sale .sos665-stock-grid[data-sos663-view="grid"]{display:grid!important;grid-template-columns:repeat(auto-fill,minmax(min(100%,170px),1fr))!important;gap:10px!important;align-items:stretch!important;max-height:none!important;overflow:visible!important}
.sos655-new-sale .sos665-stock-grid[data-sos663-view="list"]{display:flex!important;flex-direction:column!important;gap:8px!important}
.sos655-new-sale .sos665-stock-grid>button{width:100%!important;min-width:0!important;max-width:100%!important;opacity:1}
.sos655-new-sale .sos655-product-results[data-sos663-view="grid"]{display:grid!important;grid-template-columns:repeat(auto-fill,minmax(min(100%,170px),1fr))!important;align-items:stretch!important}
.sos655-new-sale .sos655-cart-header{margin-top:10px!important}
.sos655-new-sale .sos665-featured-section{margin-top:15px!important}
.sos655-new-sale .sos655-checkout{align-self:start}
@media(max-width:980px){.sos655-new-sale .sos655-sales-layout{grid-template-columns:1fr!important}.sos655-new-sale .sos655-checkout{position:static!important}}
</style>

<!-- SERVICING_SALES_VISUAL_669: shared visual rules only; existing product and cart events preserved. -->
<style src="./SalesProductVisual669.css"></style>

<style>
/* SERVICING_OS_671 — one grid geometry for header + sale rows. */
.sos655-new-sale .sos655-sales-main {container-type:inline-size;min-width:0}
.sos655-new-sale .sos665-cart-column-head,
.sos655-new-sale .sos655-cart-line {
  box-sizing:border-box!important;
  grid-template-columns:minmax(190px,2.55fr) minmax(88px,.72fr) minmax(142px,1.12fr) minmax(102px,.80fr) minmax(122px,.98fr) 42px!important;
  column-gap:12px!important;
  padding-left:10px!important;
  padding-right:10px!important;
  width:100%!important;
}
.sos655-new-sale .sos665-cart-column-head{
  display:grid!important; align-items:center!important; min-height:38px;
  padding-top:9px!important;padding-bottom:9px!important;
  border-radius:9px!important;background:#f6eee6!important;
  font-weight:750!important;line-height:1.25!important;
}
.sos655-new-sale .sos665-cart-column-head span:nth-child(2),
.sos655-new-sale .sos665-cart-column-head span:nth-child(3),
.sos655-new-sale .sos665-cart-column-head span:nth-child(4) {text-align:left!important}
.sos655-new-sale .sos665-cart-column-head span:nth-child(5){text-align:right!important}
.sos655-new-sale .sos655-cart-line{
  display:grid!important;align-items:start!important;gap:12px!important;
  padding-top:14px!important;padding-bottom:13px!important;
  border-bottom:1px solid #eadacc!important;
}
.sos655-new-sale .sos655-cart-line>.sos655-product-name{grid-column:1!important;min-width:0!important;padding-top:7px!important;line-height:1.4!important}
.sos655-new-sale .sos655-cart-line>.sos655-product-name strong{font-size:12px!important;font-weight:720!important;line-height:1.4!important;overflow-wrap:break-word!important}
.sos655-new-sale .sos655-cart-line>.sos655-product-name small{line-height:1.35!important}
.sos655-new-sale .sos655-cart-line>label:not(.sos655-serial){min-width:0!important;width:100%!important;margin:0!important;align-self:start!important;display:block!important;line-height:0!important;font-size:0!important;color:transparent!important}
.sos655-new-sale .sos655-cart-line>label:not(.sos655-serial) input{box-sizing:border-box!important;width:100%!important;min-width:0!important;height:43px!important;min-height:43px!important;line-height:normal!important;padding:9px 10px!important;font-size:13px!important;text-align:left!important;margin:0!important;color:#3c2c25!important}
.sos655-new-sale .sos655-cart-line>label:not(.sos655-serial)>small{display:block!important;font-size:10px!important;line-height:1.3!important;color:#8b725e!important;margin-top:5px!important;min-height:12px}
.sos655-new-sale .sos655-cart-line>.sos655-row-total{grid-column:5!important;min-height:43px!important;display:flex!important;align-items:center!important;justify-content:flex-end!important;white-space:nowrap!important;text-align:right!important;font-size:13px!important;margin:0!important;padding:0!important;align-self:start!important}
.sos655-new-sale .sos655-cart-line>.sos655-remove{grid-column:6!important;align-self:start!important;justify-self:end!important;width:42px!important;min-width:42px!important;min-height:43px!important;height:43px!important;margin:0!important}
.sos655-new-sale .sos655-cart-line>.sos655-serial{grid-column:1/-1!important;font-size:12px!important;color:#785843!important}
.sos671-warranty{font-size:10px!important;color:#72533d!important;background:#f7eee4!important;border-radius:5px;padding:4px 6px;display:inline-block!important;margin-top:3px}
@container (max-width:890px){
  .sos655-new-sale .sos665-cart-column-head{display:none!important}
  .sos655-new-sale .sos655-cart-line{grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:10px!important;padding:12px 6px!important}
  .sos655-new-sale .sos655-cart-line>.sos655-product-name{grid-column:1/-1!important;padding-top:0!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(1){grid-column:1/3!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(2){grid-column:3/5!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(3){grid-column:5/7!important}
  .sos655-new-sale .sos655-cart-line>label:not(.sos655-serial){font-size:11px!important;line-height:1.5!important;color:#79583f!important;font-weight:650!important}
  .sos655-new-sale .sos655-cart-line>.sos655-row-total{grid-column:1/6!important;justify-content:flex-start!important;min-height:32px!important}
  .sos655-new-sale .sos655-cart-line>.sos655-remove{grid-column:6!important}
}
@container (max-width:450px){
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(1){grid-column:1/3!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(2){grid-column:3/7!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(3){grid-column:1/4!important}
  .sos655-new-sale .sos655-cart-line>.sos655-row-total{grid-column:4/7!important;justify-content:flex-end!important}
}
</style>

<style>
/* SERVICING_OS_WARRANTY_672: equal header/row columns, with visible Warranty Days. */
.sos655-new-sale .sos665-cart-column-head,
.sos655-new-sale .sos655-cart-line {
  grid-template-columns: minmax(174px,2.4fr) minmax(74px,.65fr) minmax(108px,.9fr) minmax(80px,.75fr) minmax(122px,1fr) minmax(102px,.95fr) 42px!important;
  gap:10px!important;
}
.sos655-new-sale .sos665-cart-column-head{display:grid!important;align-items:center!important}
.sos655-new-sale .sos665-cart-column-head span{line-height:1.3;font-size:10px;white-space:normal;text-align:left}
.sos655-new-sale .sos665-cart-column-head span:nth-child(6){text-align:right!important}
.sos655-new-sale .sos655-cart-line > .sos672-warranty-label{grid-column:5!important}
.sos655-new-sale .sos655-cart-line > .sos655-row-total{grid-column:6!important}
.sos655-new-sale .sos655-cart-line > .sos655-remove{grid-column:7!important}
.sos655-new-sale .sos672-warranty-label input{min-height:43px!important;line-height:normal!important;font-size:13px!important}
.sos655-new-sale .sos672-warranty-label input[readonly]{background:#f3e8dd!important;color:#664632!important}
.sos655-new-sale .sos672-warranty-label small{display:block!important;color:#866850!important;line-height:1.35!important;font-size:10px!important;min-height:unset!important;margin-top:4px}
.sos655-new-sale .sos672-no-warranty{font-size:10px!important;font-weight:600!important;line-height:1.25!important;display:inline-block;background:transparent!important;color:#815a3f!important;padding:2px 0!important;border:0!important;text-decoration:underline!important;cursor:pointer}
@container (max-width:970px){
  .sos655-new-sale .sos665-cart-column-head{display:none!important}
  .sos655-new-sale .sos655-cart-line{grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:9px!important}
  .sos655-new-sale .sos655-cart-line>.sos655-product-name{grid-column:1/-1!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(1){grid-column:1/3!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(2){grid-column:3/5!important}
  .sos655-new-sale .sos655-cart-line>label:nth-of-type(3){grid-column:5/7!important}
  .sos655-new-sale .sos655-cart-line>.sos672-warranty-label{grid-column:1/4!important}
  .sos655-new-sale .sos655-cart-line>.sos655-row-total{grid-column:4/6!important;justify-content:flex-end!important}
  .sos655-new-sale .sos655-cart-line>.sos655-remove{grid-column:6!important}
  .sos655-new-sale .sos655-cart-line>label:not(.sos655-serial){font-size:11px!important;line-height:1.45!important;color:#785843!important}
}
</style>
