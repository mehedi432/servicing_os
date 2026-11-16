<script setup>
// SERVICING_OS_CUSTOMER_LOOKUP_666: hand off to existing native POS customer select.
import CustomerQuickSearch666 from './CustomerQuickSearch666.vue'
import { ref as sos666Ref } from 'vue'
const sos666RetailSelected = sos666Ref(null)
function sos666RetailChoose(c) {
  if (!c || !c.name) return
  chooseCustomer(c)
  sos666RetailSelected.value = c
}
function sos666RetailClear() { sos666RetailSelected.value = null }



// SERVICING_OS_FEATURED_665 — in-stock catalog before item search is selected.
import { ref as sos665Ref, onMounted as sos665Mounted } from 'vue'
const sos665Stock = sos665Ref([])
const sos665Warehouse = sos665Ref('Retail warehouse')
const sos665Loading = sos665Ref(false)
const sos665Error = sos665Ref('')
const sos665Cursors = sos665Ref([0])
const sos665CursorIndex = sos665Ref(0)
const sos665NextCursor = sos665Ref(null)
let sos665Seq = 0
async function sos665LoadStock(cursor=0) {
 const seq=++sos665Seq
 sos665Loading.value=true; sos665Error.value=''
 try {
   const url=new URL('/api/method/servicing_os.api.counter_fast_667.get_stock_products',window.location.origin)
   url.searchParams.set('cursor',String(cursor))
   const res=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
   const data=await res.json()
   if (!res.ok || data.exc || data.exception) throw new Error('Unable to load stock items from ERPNext')
   if(seq!==sos665Seq)return
   sos665Warehouse.value=data.message?.warehouse || 'Retail warehouse'
   sos665Stock.value=(data.message?.items||[]).slice(0,20).map(x=>({
     ...x, ledger_qty:x.stock_qty, list_price:x.list_price ?? null,
     item_code:x.item_code || x.name
   }))
   sos665NextCursor.value=data.message?.has_next ? data.message.next_cursor : null
 }catch(e){if(seq===sos665Seq)sos665Error.value=e?.message || 'Available stock could not be loaded.'}
 finally{if(seq===sos665Seq)sos665Loading.value=false}
}
function sos665Next(){if(sos665Loading.value||sos665NextCursor.value==null)return;
 sos665Cursors.value=sos665Cursors.value.slice(0,sos665CursorIndex.value+1);
 sos665Cursors.value.push(sos665NextCursor.value);sos665CursorIndex.value++;
 sos665LoadStock(sos665Cursors.value[sos665CursorIndex.value])}
function sos665Previous(){if(sos665Loading.value||sos665CursorIndex.value<=0)return;
 sos665CursorIndex.value--;sos665LoadStock(sos665Cursors.value[sos665CursorIndex.value])}
sos665Mounted(()=>sos665LoadStock(0))

// SERVICING_OS_CATALOG_664: show a maximum of 20 products at once in either layout.
import { ref as sos664Ref, watch as sos664Watch, unref as sos664Unref } from 'vue'
const sos664RetailPage = sos664Ref(1)
function sos664RetailLength(items) { return Array.isArray(items) ? items.length : 0 }
function sos664RetailPageOf(items) {
  return Array.isArray(items) ? items.slice((sos664RetailPage.value-1)*20,sos664RetailPage.value*20) : []
}
sos664Watch(() => sos664Unref(search), () => { sos664RetailPage.value = 1 })

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

// SERVICING_COUNTER_PATCH_654: show product suggestions only while item search is selected.
import { ref as sos654Ref } from 'vue'
const sos654RetailFocused = sos654Ref(false)
let sos654RetailBlurTimer = null
function sos654RetailClose() {
  if (sos654RetailBlurTimer) clearTimeout(sos654RetailBlurTimer)
  sos654RetailBlurTimer = setTimeout(() => { sos654RetailFocused.value = false }, 230)
}

// SERVICING_COUNTER_620E
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const products = ref([])
const customers = ref([])
const cart = ref([])
const search = ref('')
const customerSearch = ref('')
const customer = ref('')

// SERVICING_COUNTER_CUSTOMERS_620F — single Customer picker
const matchedCustomers = ref([])
const selectedCustomer = ref(null)
const customerPickerOpen = ref(false)
const customerLoading = ref(false)
const savingCustomer = ref(false)
const newCustomerOpen = ref(false)
const newCustomerName = ref('')
const newCustomerMobile = ref('')
const newCustomerGroup = ref('')
const newCustomerTerritory = ref('')
const classificationOpen = ref(false)
const customerConfig = ref({groups:[],territories:[],default_group:'',default_territory:'',can_create:false})
const customerHint = ref('')
let customerRequestSerial = 0

const checking = ref(false)
const loading = ref(false)
const error = ref('')
const notices = ref([])
const quote = ref(null)
const receipt = ref(null)
const tendered = ref('')
const recent = ref([])
const showRecent = ref(false)
const key = ref(newKey())
let searchTimer = null
let customerTimer = null

function newKey() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID()
  return 'sos_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2)
}
function money(value) {return '৳' + Number(value || 0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})}
function csrf() { return window.frappe?.csrf_token || window.csrf_token ||
  decodeURIComponent(document.cookie.split('; ').find(c=>c.startsWith('csrf_token='))?.split('=').slice(1).join('=') || '') }
async function call(name,args={},post=false) {
  const namespace = ['search_customers','get_customer_config','create_counter_customer'].includes(name) ? 'counter_customers' : 'counter_checkout'
  const url = new URL('/api/method/servicing_os.api.'+namespace+'.'+name,window.location.origin)
  if (!post) Object.entries(args).forEach(([k,v])=>url.searchParams.set(k,String(v??'')))
  const options = {method:post?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json'}}
  if (post) {options.headers['Content-Type']='application/json';options.headers['X-Frappe-CSRF-Token']=csrf();options.body=JSON.stringify(args)}
  const response = await fetch(url, options)
  let data
  try {data=await response.json()} catch {throw Error('Server returned an unreadable response')}
  if (!response.ok || data.exc || data.exc_type) {
    let message=data.message?.message || data.exception || 'Request failed'
    if (data._server_messages) {try {const parsed=JSON.parse(data._server_messages);message=JSON.parse(parsed.at(-1)).message||message}catch{}}
    throw Error(message)
  }
  return data.message
}
function clearQuote() {quote.value=null;receipt.value=null;tendered.value=''}
function add(p) {
  if (p.rate==null || Number(p.stock_qty)<=0) return
  const row=cart.value.find(x=>x.item_code===p.item_code)
  if (row) {if(row.qty>=p.stock_qty) return;row.qty+=1}
  else cart.value.push({item_code:p.item_code,item_name:p.item_name,rate:p.rate,qty:1,stock_qty:p.stock_qty})
  clearQuote()
}
function changeQty(row,delta) {
  row.qty=Math.min(row.stock_qty,Math.max(0,Number(row.qty)+delta))
  if (!row.qty) cart.value=cart.value.filter(x=>x!==row)
  clearQuote()
}
function remove(row) {cart.value=cart.value.filter(x=>x!==row);clearQuote()}
// SERVICING_COUNTER_GUIDANCE_620G — explain when checkout is disabled.
const checkoutHelp620G = computed(() => {
  if (checking.value) return 'Processing your request…'
  if (quote.value) return 'Check the final total, enter cash received, then confirm payment.'
  if (!cart.value.length) {
    if (products.value.length && !products.value.some(p => Number(p.stock_qty) > 0 && p.rate != null)) {
      return 'No saleable stock in Stores - AMCL. Go to Inventory to receive or transfer genuine stock before checkout.'
    }
    return 'Step 1: Click an in-stock product on the left to add it to the cart.'
  }
  if (!customer.value) return 'Step 2: Search for a customer, or add a new customer using their mobile number.'
  return 'Step 3: Click Review & Take Cash to confirm the final amount.'
})
const subtotal=computed(()=>cart.value.reduce((acc,x)=>acc+(x.rate*x.qty),0))
const count=computed(()=>cart.value.reduce((acc,x)=>acc+x.qty,0))
const change=computed(()=>Math.max(0,Number(tendered.value||0)-Number(quote.value?.grand_total||0)))
async function loadProducts(){
  loading.value=true;error.value=''
  try {const r=await call('get_register',{search:search.value,customer_search:customerSearch.value});products.value=r.items||[];customers.value=r.customers||[];notices.value=r.checks||[]}
  catch(e){error.value=e.message}finally{loading.value=false}
}
async function loadCustomerConfig() {
  try {
    const cfg = await call('get_customer_config')
    customerConfig.value = cfg
    newCustomerGroup.value = cfg.default_group || ''
    newCustomerTerritory.value = cfg.default_territory || ''
  } catch(e) {customerHint.value = e.message}
}
async function loadCustomers() {
  const serial = ++customerRequestSerial
  const query = customerSearch.value.trim()
  if (!query) {matchedCustomers.value=[];customerLoading.value=false;return}
  customerLoading.value=true
  try {
    const result=await call('search_customers',{search:query})
    if (serial === customerRequestSerial) matchedCustomers.value = result.customers || []
  } catch(e) {
    if (serial === customerRequestSerial) {customerHint.value=e.message;matchedCustomers.value=[]}
  } finally {if(serial === customerRequestSerial) customerLoading.value=false}
}
function chooseCustomer(c) {
  customer.value=c.name
  selectedCustomer.value=c
  customerSearch.value=''
  customerPickerOpen.value=false
  newCustomerOpen.value=false
  customerHint.value=''
  clearQuote()
}
function changeCustomer() {
  customer.value=''
  selectedCustomer.value=null
  customerSearch.value=''
  matchedCustomers.value=[]
  customerPickerOpen.value=true
  customerHint.value=''
  clearQuote()
}
function onCustomerSearch() {
  customerPickerOpen.value=true
  customerHint.value=''
  clearTimeout(customerTimer)
  customerTimer=setTimeout(loadCustomers,230)
}
function startNewCustomer() {
  if (!customerConfig.value.can_create) {customerHint.value='Your account needs permission to create customers.';return}
  newCustomerOpen.value=true
  customerPickerOpen.value=false
  const typed=customerSearch.value.trim()
  if (/^[+\d\s-]+$/.test(typed) && /\d/.test(typed)) newCustomerMobile.value=typed
  else if(typed) newCustomerName.value=typed
}
async function saveNewCustomer() {
  customerHint.value=''
  error.value=''
  if(newCustomerName.value.trim().length < 2) {customerHint.value='Enter the customer name.';return}
  const digits=newCustomerMobile.value.replace(/\D/g,'')
  if(!( /^01[3-9]\d{8}$/.test(digits) || /^8801[3-9]\d{8}$/.test(digits) )) {
    customerHint.value='Mobile number must be 11 digits starting 01 (or +8801...).';return
  }
  if(!newCustomerGroup.value || !newCustomerTerritory.value) {
    customerHint.value='Select Customer Group and Territory.';classificationOpen.value=true;return
  }
  savingCustomer.value=true
  try {
    const result=await call('create_counter_customer',{
      customer_name:newCustomerName.value.trim(),mobile_no:newCustomerMobile.value.trim(),
      customer_group:newCustomerGroup.value,territory:newCustomerTerritory.value
    },true)
    chooseCustomer(result.customer)
    newCustomerName.value=''
    newCustomerMobile.value=''
    customerHint.value='New customer saved and selected.'
  } catch(e) {customerHint.value=e.message}
  finally {savingCustomer.value=false}
}
function onProducts(){clearTimeout(searchTimer);searchTimer=setTimeout(loadProducts,220)}
async function loadRecent(){try {const r=await call('recent_sales');recent.value=r.sales||[]}catch(e){error.value=e.message}}
async function review(){
  error.value=''
  if(!customer.value){error.value='Choose a customer';return}
  if(!cart.value.length){error.value='Add at least one product';return}
  checking.value=true
  try {quote.value=await call('quote_sale',{customer:customer.value,items:cart.value.map(x=>({item_code:x.item_code,qty:x.qty}))},true);tendered.value=String(quote.value.grand_total)}
  catch(e){error.value=e.message}finally{checking.value=false}
}
async function complete(){
  if(checking.value || !quote.value) return
  if(Number(tendered.value)<Number(quote.value.grand_total)){error.value='Cash received is less than amount due';return}
  error.value='';checking.value=true
  try {
    const result=await call('complete_cash_sale',{
      customer:customer.value,items:cart.value.map(x=>({item_code:x.item_code,qty:x.qty})),
      checkout_key:key.value,expected_total:quote.value.grand_total},true)
    receipt.value=result;quote.value=null;cart.value=[];key.value=newKey();search.value='';customer.value='';selectedCustomer.value=null;customerSearch.value='';matchedCustomers.value=[]
    await loadProducts();await loadRecent()
  }catch(e){error.value=e.message}finally{checking.value=false}
}
function reset(){cart.value=[];clearQuote();error.value='';key.value=newKey()}
function printReceipt(){window.print()}
onMounted(()=>{loadProducts();loadRecent();loadCustomerConfig()})
onBeforeUnmount(()=>{clearTimeout(searchTimer);clearTimeout(customerTimer)})
</script>

<template>
 <section class="cc-root">
  <div class="cc-header"><div><div class="cc-eyebrow">SERVICING OS · COUNTER</div><h1>New Sale</h1><p>Find a product, take payment and print a receipt. All in one place.</p></div>
    <div class="cc-header-actions"><button type="button" class="cc-outline" @click="showRecent=!showRecent">{{showRecent?'Hide':'View'}} recent sales</button><span class="cc-online">● LIVE COUNTER</span></div>
  </div>
  <div v-if="error" class="cc-error" role="alert">{{error}} <button type="button" @click="error=''">Dismiss</button></div>
  <div v-if="notices.length" class="cc-notice"><strong>Counter setup</strong><span v-for="msg in notices" :key="msg">{{msg}}.</span></div>
  <section v-if="showRecent" class="cc-recent"><div class="cc-recent-head"><strong>Recent completed sales</strong><button type="button" @click="loadRecent">Refresh</button></div>
    <div v-if="!recent.length" class="cc-muted">No counter sales recorded yet.</div>
    <div v-for="sale in recent" :key="sale.name" class="cc-recent-row"><strong>{{sale.name}}</strong><span>{{sale.customer_name||sale.customer}}</span><span>{{money(sale.grand_total)}}</span></div>
  </section>
  <div class="cc-layout">
    <section class="cc-products">
      <label class="cc-label" for="cc-product-search">Search product or scan barcode</label>
      <div class="cc-searchbox"><span aria-hidden="true">⌕</span><input id="cc-product-search" v-model="search" @input="onProducts" @keydown.enter.prevent="loadProducts" autocomplete="off" placeholder="SSD, RAM, barcode or Item Code" @focusin="sos654RetailFocused = true" @focusout="sos654RetailClose" @keydown.esc="sos654RetailFocused = false" /><button type="button" @click="loadProducts">Search</button></div>
      <p v-if="!loading && products.length && !products.some(p => Number(p.stock_qty) > 0 && p.rate != null)" class="cc-stock-help" role="status">
        All listed products currently have 0 saleable stock in <strong>Stores - AMCL</strong>. You can browse prices, but you cannot add them to the cart until stock is received.
      </p>
      <div class="cc-product-header"><b>Products</b><small>{{products.length}} results · Stores - AMCL</small></div>
      <div class="sos663-retail-viewbar">
  <div class="sos663-viewbar" role="group" aria-label="Product view">
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
</div>
</div>

<div v-if="!sos654RetailFocused" class="sos665-retail-defaultbar">
  <div><strong>In Stock · Ready to Sell</strong><small>Browse up to 20 available products, or search the full catalog above</small></div>
  <button type="button" @click="sos665LoadStock(sos665Cursors[sos665CursorIndex])" :disabled="sos665Loading">Refresh Stock</button>
</div>
<div class="cc-product-list sos663-retail-results" :data-sos663-view="sos663View">
        <button v-for="p in (sos654RetailFocused ? sos664RetailPageOf((products)) : sos665Stock)" :key="p.item_code" type="button" class="cc-product" :disabled="p.rate==null || Number(p.stock_qty)<=0 || checking" @click="add(p)"><span v-if="(p.ledger_qty ?? p.stock_qty) !== null && (p.ledger_qty ?? p.stock_qty) !== undefined"
                class="sos664-retail-stock" :class="{'sos664-out':Number(p.ledger_qty ?? p.stock_qty)<=0}">
        {{ Number(p.ledger_qty ?? p.stock_qty)>0 ? 'In stock: '+(p.ledger_qty ?? p.stock_qty) : 'Out of stock · 0' }}
      </span>
          <span class="cc-product-icon">▣</span><span class="cc-product-info"><b>{{p.item_name}}</b><small>{{p.item_code}}</small></span>
          <span class="cc-product-price"><b>{{p.rate==null?'No price':money(p.rate)}}</b><small :class="Number(p.stock_qty)>0?'cc-available':'cc-out'">{{Number(p.stock_qty)>0?p.stock_qty+' in stock':'Out of stock'}}</small></span><span class="cc-add">+</span>
        </button>
        <div v-if="!products.length" class="cc-empty">No matching stock products. Try another search.</div>
      </div>

<div v-if="!sos654RetailFocused" class="sos665-retail-footer">
 <span v-if="sos665Loading">Loading in-stock items…</span>
 <span v-else-if="sos665Error" role="alert">{{ sos665Error }}</span>
 <span v-else-if="!sos665Stock.length">No stocked products found in the retail warehouse.</span>
 <span v-else>Page {{ sos665CursorIndex+1 }} · {{ sos665Stock.length }} available products</span>
 <div><button type="button" @click="sos665Previous" :disabled="sos665Loading||sos665CursorIndex===0">Previous</button>
 <button type="button" @click="sos665Next" :disabled="sos665Loading||sos665NextCursor==null">Next 20</button></div>
</div>

<div class="sos664-retail-pager" v-if="sos654RetailFocused && sos664RetailLength((products))">
  <span>Showing {{ Math.min(sos664RetailPage * 20, sos664RetailLength((products))) }} of {{ sos664RetailLength((products)) }} loaded products · 20 per page</span>
  <div class="sos664-actions">
    <button type="button" :disabled="sos664RetailPage<=1" @mousedown.prevent @click="sos664RetailPage--">Previous</button>
    <button type="button" :disabled="sos664RetailPage*20>=sos664RetailLength((products))" @mousedown.prevent @click="sos664RetailPage++">Next 20</button>
  </div>
</div>
    </section>
    <section class="cc-checkout">
      <div class="cc-checkout-title"><div><div class="cc-eyebrow">CURRENT ORDER</div><h2>Shopping Cart <span>{{count}} items</span></h2></div><button type="button" class="cc-small" @click="reset" :disabled="checking">Clear</button></div>
      <section class="cc-customer-card" aria-label="Customer selection">
        <div class="cc-customer-title"><div><strong>Customer</strong><small>Search once, or add a new customer here</small></div>
          <button type="button" class="cc-new-customer" v-if="customerConfig.can_create" @click="startNewCustomer">＋ New Customer</button>
        </div>
        <div v-if="selectedCustomer" class="cc-selected-person">
          <span class="cc-person-avatar" aria-hidden="true">✓</span>
          <span class="cc-person-details"><strong>{{selectedCustomer.customer_name || selectedCustomer.name}}</strong><small>{{selectedCustomer.mobile || 'Mobile not recorded'}}</small></span>
          <button type="button" class="cc-customer-change" @click="changeCustomer">Change</button>
        </div>
        <div v-else class="cc-customer-search-area">
          <div class="cc-customer-query"><span aria-hidden="true">⌕</span>
            <div class="sos666-retail-picker"><CustomerQuickSearch666 :selected="sos666RetailSelected"
  label="Customer · Search by name or mobile" @selected="sos666RetailChoose" @clear="sos666RetailClear" /></div>
<input id="cc-customer-search" v-model="customerSearch" @focus="customerPickerOpen=true" @input="onCustomerSearch" @keydown.esc="customerPickerOpen=false" @keydown.enter.prevent="matchedCustomers.length===1 ? chooseCustomer(matchedCustomers[0]) : (customerPickerOpen=true)" placeholder="Customer name or mobile number" autocomplete="off" aria-label="Find customer by name or phone" class="sos666-native-old-search" />
            <span v-if="customerLoading" class="cc-customer-loader" aria-label="Searching">…</span>
          </div>
          <div v-if="customerPickerOpen && customerSearch.trim()" class="cc-customer-options" role="listbox" aria-label="Customer matches">
            <button v-for="c in matchedCustomers" :key="c.name" type="button" class="cc-customer-option" role="option" @click="chooseCustomer(c)">
              <span class="cc-person-avatar" aria-hidden="true">{{(c.customer_name || c.name).slice(0,1).toUpperCase()}}</span>
              <span class="cc-person-details"><strong>{{c.customer_name || c.name}}</strong><small>{{c.mobile || 'No mobile saved'}} · {{c.name}}</small></span><span aria-hidden="true">↗</span>
            </button>
            <div v-if="!matchedCustomers.length && !customerLoading" class="cc-customer-empty">No matching customer. Use <b>＋ New Customer</b> below.</div>
          </div>
          <p v-if="!customerSearch.trim()" class="cc-customer-tip">Start typing a name or mobile number to find an existing customer.</p>
        </div>
        <form v-if="newCustomerOpen" class="cc-new-customer-form" @submit.prevent="saveNewCustomer">
          <div class="cc-new-form-heading"><strong>Create Customer</strong><button type="button" @click="newCustomerOpen=false">✕</button></div>
          <div class="cc-new-form-fields">
            <label>Customer Name <span>*</span><input v-model="newCustomerName" type="text" maxlength="120" required autocomplete="name" placeholder="Full customer name"/></label>
            <label>Mobile Number <span>*</span><input v-model="newCustomerMobile" type="tel" maxlength="18" required autocomplete="tel-national" inputmode="tel" placeholder="01XXXXXXXXX"/></label>
          </div>
          <button v-if="newCustomerGroup && newCustomerTerritory && !classificationOpen" class="cc-classification-toggle" type="button" @click="classificationOpen=true">Customer classification · Change</button>
          <div v-if="classificationOpen || !newCustomerGroup || !newCustomerTerritory" class="cc-new-form-fields">
            <label>Customer Group <span>*</span><select v-model="newCustomerGroup" required><option disabled value="">Select group</option><option v-for="g in customerConfig.groups" :key="g" :value="g">{{g}}</option></select></label>
            <label>Territory <span>*</span><select v-model="newCustomerTerritory" required><option disabled value="">Select territory</option><option v-for="t in customerConfig.territories" :key="t" :value="t">{{t}}</option></select></label>
          </div>
          <div class="cc-new-form-actions"><button class="cc-outline" type="button" @click="newCustomerOpen=false">Cancel</button><button class="cc-new-save" type="submit" :disabled="savingCustomer">{{savingCustomer?'Saving…':'Save & Select Customer'}}</button></div>
        </form>
        <p v-if="customerHint" class="cc-customer-hint" role="status">{{customerHint}}</p>
      </section>
      <div class="cc-cart-items"><div v-if="!cart.length" class="cc-cart-empty">Cart is empty. Select a product on the left.</div>
        <div v-for="row in cart" :key="row.item_code" class="cc-cart-row"><div><b>{{row.item_name}}</b><small>{{money(row.rate)}} each</small></div>
          <div class="cc-cart-qty"><button type="button" @click="changeQty(row,-1)">−</button><span>{{row.qty}}</span><button type="button" @click="changeQty(row,1)">+</button></div><b>{{money(row.rate*row.qty)}}</b><button type="button" class="cc-remove" aria-label="Remove" @click="remove(row)">×</button>
        </div>
      </div>
      <div class="cc-summary"><div><span>Product subtotal</span><b>{{money(subtotal)}}</b></div><div v-if="quote"><span>Taxes and charges</span><b>{{money(quote.tax_total)}}</b></div><div class="cc-grand"><span>{{quote?'Total due':'Estimated subtotal'}}</span><strong>{{money(quote?quote.grand_total:subtotal)}}</strong></div></div>
      <div v-if="quote" class="cc-paybox"><label class="cc-label" for="cc-cash">Cash received (BDT)</label><input id="cc-cash" v-model="tendered" class="cc-input" type="number" min="0" step="0.01" /><div class="cc-change"><span>Change to return</span><b>{{money(change)}}</b></div><p>Completing the sale posts the invoice, reduces stock and records payment.</p></div>
      <button v-if="!quote" type="button" class="cc-primary" :disabled="checking || !cart.length || !customer" @click="review">{{checking?'Checking...':'Review & Take Cash'}}</button>
      <div v-if="!quote" class="cc-action-help" role="status">{{ checkoutHelp620G }}</div>
      <div v-else class="cc-pay-actions"><button type="button" class="cc-outline" @click="clearQuote" :disabled="checking">Back</button><button type="button" class="cc-primary" :disabled="checking || Number(tendered)<Number(quote.grand_total)" @click="complete">{{checking?'Processing...':'Confirm Sale & Payment'}}</button></div>
    </section>
  </div>
  <div v-if="receipt" class="cc-receipt-layer"><div class="cc-receipt">
    <header><div class="cc-receipt-brand">SERVICING OS</div><small>AL MODINA COMPUTERS LIMITED</small><h2>Payment Received</h2></header>
    <div class="cc-receipt-meta"><span>Invoice</span><b>{{receipt.invoice}}</b></div><div class="cc-receipt-meta"><span>Customer</span><b>{{receipt.customer}}</b></div>
    <div v-for="r in receipt.items||[]" :key="r.item_code" class="cc-receipt-row"><span>{{r.item_name}} × {{r.qty}}</span><b>{{money(r.amount)}}</b></div>
    <div class="cc-receipt-total"><span>Paid</span><b>{{money(receipt.total)}}</b></div><small>Thank you for shopping with us.</small>
    <div class="cc-receipt-actions"><button type="button" class="cc-outline" @click="receipt=null">New Sale</button><button type="button" class="cc-primary" @click="printReceipt">Print Receipt</button></div>
  </div></div>
 </section>
</template>

<style scoped>
.cc-root,.cc-root *{box-sizing:border-box}.cc-root{min-height:calc(100vh - 74px);background:#faf8f4;color:#514635;padding:22px;font-family:inherit}.cc-header{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:20px}.cc-header h1{font-size:28px;font-weight:750;letter-spacing:-.8px;margin:5px 0}.cc-header p{font-size:13px;color:#92816b}.cc-eyebrow{font-size:10px;font-weight:800;letter-spacing:1.6px;color:#a48661}.cc-header-actions{display:flex;gap:12px;align-items:center}.cc-online{font-size:10px;font-weight:800;color:#668368;letter-spacing:1px}.cc-outline{padding:10px 14px;border:1px solid #e1d3be;background:#fffdf9;color:#6d5538;border-radius:10px;font-weight:650;cursor:pointer}.cc-layout{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(350px,.85fr);gap:18px;align-items:start;max-width:1550px;margin:auto}.cc-products,.cc-checkout,.cc-recent{border:1px solid #e6dccc;border-radius:17px;background:#fffefa;box-shadow:0 3px 15px #5a412609;padding:20px;min-width:0}.cc-searchbox{border:1px solid #ddcfbb;border-radius:12px;display:flex;align-items:center;gap:10px;padding:4px 5px 4px 13px;background:#fff}.cc-searchbox input{flex:1;min-width:0;border:0;outline:none;padding:10px 0;font-size:14px}.cc-searchbox button{padding:10px 14px;background:#f0e7d9;color:#725941;border-radius:9px;font-size:12px;font-weight:700}.cc-label{display:block;font-size:11px;font-weight:700;margin:8px 0;color:#846d50}.cc-product-header{display:flex;justify-content:space-between;align-items:center;margin:20px 0 10px;font-size:13px}.cc-product-header small{color:#978873}.cc-product-list{max-height:60vh;overflow-y:auto}.cc-product{display:flex;width:100%;text-align:left;align-items:center;gap:12px;border:1px solid #eee6da;background:#fffefa;border-radius:12px;margin:0 0 8px;padding:12px;color:inherit;cursor:pointer;transition:background .12s}.cc-product:hover:not(:disabled){background:#f4eee4}.cc-product:disabled{opacity:.48;cursor:not-allowed}.cc-product-icon{display:grid;place-items:center;height:40px;width:40px;flex:none;background:#f2eadd;border-radius:10px;color:#8c6b43;font-size:23px}.cc-product-info{flex:1;min-width:0}.cc-product-info b{font-size:12px;display:block;line-height:1.4}.cc-product-info small{color:#988670;display:block;font-size:10px;overflow-wrap:anywhere}.cc-product-price{text-align:right;display:grid;gap:2px}.cc-product-price b{font-size:13px;white-space:nowrap}.cc-product-price small{font-size:10px;white-space:nowrap}.cc-available{color:#507a53}.cc-out{color:#a35246}.cc-add{font-size:21px;color:#947455}.cc-checkout{position:sticky;top:12px}.cc-checkout-title{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.cc-checkout-title h2{font-size:18px;font-weight:750;margin-top:3px}.cc-checkout-title h2 span{font-size:12px;color:#a08c70;font-weight:500}.cc-small{font-size:12px;color:#866b4a;text-decoration:underline}.cc-input{border:1px solid #ddcfbc;background:#fff;width:100%;padding:11px 12px;border-radius:10px;margin:0 0 10px;font-size:13px;outline-color:#b99b77}.cc-select{appearance:auto}.cc-cart-items{min-height:115px;max-height:30vh;overflow-y:auto}.cc-cart-empty,.cc-empty{padding:30px;text-align:center;font-size:13px;color:#ab9b83}.cc-cart-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:9px;align-items:center;padding:10px 0;border-bottom:1px solid #eee5d7}.cc-cart-row b{font-size:12px}.cc-cart-row small{display:block;color:#95816b;font-size:11px;margin-top:4px}.cc-cart-qty{display:flex;align-items:center;gap:5px;border:1px solid #e5d8c7;border-radius:9px}.cc-cart-qty button{width:26px;height:29px;font-size:17px}.cc-cart-qty span{font-size:12px;min-width:14px;text-align:center}.cc-remove{color:#a45e50;font-size:21px}.cc-summary{padding:15px 0}.cc-summary>div{display:flex;justify-content:space-between;align-items:center;margin:8px 0;color:#8d7b64;font-size:12px}.cc-summary .cc-grand{border-top:1px solid #e5d9c6;padding-top:13px;color:#54412c;font-weight:700}.cc-grand strong{font-size:23px;letter-spacing:-.5px}.cc-primary{width:100%;border:0;border-radius:12px;background:#746044;color:white;padding:13px 17px;font-weight:750;cursor:pointer;font-size:13px}.cc-primary:disabled{opacity:.5;cursor:not-allowed}.cc-pay-actions{display:grid;grid-template-columns:110px 1fr;gap:10px}.cc-paybox{border:1px solid #d9cfbd;padding:13px;border-radius:12px;background:#faf4e9;margin-bottom:12px}.cc-paybox p{font-size:11px;color:#8f806c}.cc-change{display:flex;justify-content:space-between;font-size:12px;margin:8px 0}.cc-error,.cc-notice{padding:12px 16px;border-radius:10px;background:#fff0eb;color:#913c2d;margin-bottom:13px;font-size:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.cc-notice{background:#f8edda;color:#82613e}.cc-notice strong{margin-right:6px}.cc-error button{text-decoration:underline}.cc-recent{margin-bottom:14px}.cc-recent-head{display:flex;justify-content:space-between;margin-bottom:8px}.cc-recent-row{padding:9px 0;border-top:1px solid #eee5d8;display:flex;gap:20px;justify-content:space-between;font-size:12px}.cc-recent-row span{color:#887868}.cc-receipt-layer{position:fixed;inset:0;background:#231b13a8;z-index:9999;display:grid;place-items:center;padding:18px}.cc-receipt{background:#fffdfa;border-radius:14px;padding:24px;width:min(420px,100%);max-height:90vh;overflow:auto;text-align:center}.cc-receipt header{padding-bottom:14px;border-bottom:1px dashed #ddd}.cc-receipt-brand{font-weight:850;letter-spacing:2px;font-size:18px}.cc-receipt h2{font-size:19px;font-weight:800;margin-top:12px}.cc-receipt small{font-size:11px;color:#857461}.cc-receipt-meta,.cc-receipt-row,.cc-receipt-total{display:flex;justify-content:space-between;gap:8px;text-align:left;font-size:12px;padding:9px 0;border-bottom:1px dashed #eee}.cc-receipt-total{font-size:16px;border-top:2px solid #66523c;margin-top:10px}.cc-receipt-actions{display:flex;gap:10px;margin-top:18px}.cc-receipt-actions>*{flex:1}.cc-muted{color:#9b8c77;font-size:12px}.cc-recent-row strong{overflow-wrap:anywhere}
@media(max-width:1050px){.cc-layout{grid-template-columns:1fr}.cc-checkout{position:static}.cc-product-list{max-height:380px}.cc-header{align-items:flex-start}}
@media(max-width:560px){.cc-root{padding:11px}.cc-header h1{font-size:23px}.cc-header{gap:10px}.cc-header-actions{gap:4px}.cc-products,.cc-checkout{padding:13px}.cc-cart-row{grid-template-columns:minmax(0,1fr) auto auto auto;gap:4px}.cc-recent-row{display:grid;gap:3px}}

/* SERVICING_COUNTER_CUSTOMERS_620F */
.cc-customer-card{border:1px solid #e9dfce;background:linear-gradient(145deg,#fffefa,#faf6ee);border-radius:15px;padding:14px;margin-bottom:14px}
.cc-customer-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}
.cc-customer-title strong{font-size:14px;color:#4d3d29}
.cc-customer-title small{display:block;font-size:11px;color:#9a8971;margin-top:3px}
.cc-new-customer{font-size:12px;font-weight:750;color:#765839;padding:9px 12px;background:#f3e7d4;border:1px solid #e6d1b4;border-radius:10px;white-space:nowrap;cursor:pointer}
.cc-new-customer:hover{background:#ead8c0}
.cc-customer-search-area{position:relative}
.cc-customer-query{display:flex;align-items:center;gap:10px;border:1px solid #d8c7af;background:#fff;border-radius:11px;padding:0 13px;min-height:46px;box-shadow:0 1px 3px #6d54320b}
.cc-customer-query:focus-within{border-color:#ad885b;box-shadow:0 0 0 3px #ad885b22}
.cc-customer-query>span:first-child{font-size:23px;color:#a18a6b}
.cc-customer-query input{border:none;outline:none;min-width:0;flex:1;background:transparent;padding:12px 0;font-size:13px;color:#4f3d2c}
.cc-customer-query input::placeholder{color:#a79781}
.cc-customer-loader{font-size:19px;color:#987d5c}
.cc-customer-options{position:absolute;top:calc(100% + 5px);left:0;right:0;background:#fffefa;border:1px solid #e0d0bb;border-radius:12px;box-shadow:0 14px 34px #46321b25;max-height:240px;overflow-y:auto;z-index:90;padding:5px}
.cc-customer-option{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border-radius:9px;padding:10px;background:transparent;cursor:pointer;color:#4e3d2a}
.cc-customer-option:hover,.cc-customer-option:focus-visible{background:#f4ecdf;outline:none}
.cc-person-avatar{display:grid;place-items:center;flex:0 0 34px;width:34px;height:34px;border-radius:10px;background:#eee1cb;color:#7b5f3d;font-size:14px;font-weight:800}
.cc-person-details{display:grid;gap:3px;min-width:0;flex:1}
.cc-person-details strong{font-size:12px;line-height:1.35;overflow-wrap:anywhere}
.cc-person-details small{font-size:10px;color:#98856a;overflow-wrap:anywhere}
.cc-selected-person{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #cddfc9;background:#f6faf4;border-radius:12px}
.cc-selected-person .cc-person-avatar{background:#deefdc;color:#4e7a48}
.cc-customer-change{font-size:12px;font-weight:700;color:#725636;background:#fff;border:1px solid #e4d8c8;border-radius:9px;padding:8px 11px;cursor:pointer}
.cc-customer-tip,.cc-customer-empty{font-size:11px;color:#98856a;margin-top:9px;line-height:1.5}
.cc-customer-empty{padding:13px}
.cc-new-customer-form{margin-top:13px;padding:14px;background:#fffdf9;border:1px solid #e3d5bf;border-radius:12px}
.cc-new-form-heading{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px;font-size:13px}
.cc-new-form-heading button{font-size:16px;color:#997d5b}
.cc-new-form-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:10px 0}
.cc-new-form-fields label{display:grid;gap:6px;font-size:11px;font-weight:700;color:#776248}
.cc-new-form-fields label span{color:#a34e3d}
.cc-new-form-fields input,.cc-new-form-fields select{min-width:0;width:100%;height:43px;padding:0 10px;border:1px solid #ddcfbc;background:#fff;border-radius:9px;font-size:12px;color:#4f4030;outline-color:#ad885b}
.cc-classification-toggle{font-size:10px;color:#91755a;text-decoration:underline;cursor:pointer}
.cc-new-form-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:14px}
.cc-new-save{padding:11px 14px;border:0;border-radius:10px;background:#755c3f;color:white;font-size:12px;font-weight:750;cursor:pointer}
.cc-new-save:disabled{opacity:.55;cursor:not-allowed}
.cc-customer-hint{font-size:11px;color:#8c5833;background:#fcf0de;border-radius:9px;padding:9px 11px;margin-top:10px;line-height:1.5}
@media(max-width:560px){.cc-new-form-fields{grid-template-columns:1fr}.cc-customer-title{align-items:flex-start}.cc-new-customer{padding:8px}.cc-customer-card{padding:11px}}


/* SERVICING_COUNTER_GUIDANCE_620G */
.cc-stock-help,.cc-action-help{margin:12px 0;padding:12px 14px;border:1px solid #ead8bd;border-radius:11px;background:#fcf5e8;color:#765b3c;font-size:12px;line-height:1.55}
.cc-action-help{margin-top:11px;background:#f8f4eb;border-color:#e7dfd3}

</style>
<style>
@media print{body *{visibility:hidden!important}.cc-receipt-layer,.cc-receipt-layer *{visibility:visible!important}.cc-receipt-layer{position:absolute!important;inset:0!important;background:#fff!important;display:block!important;padding:0!important}.cc-receipt{box-shadow:none!important;border:0!important;max-height:none!important;margin:0 auto!important}.cc-receipt-actions{display:none!important}}
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

/* Only the existing product-results container is switched; cart/order handlers stay intact. */
.sos663-retail-results[data-sos663-view="grid"]{display:grid!important;
 grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:10px!important;
 align-content:start!important;align-items:stretch!important;min-width:0}
.sos663-retail-results[data-sos663-view="list"]{display:flex!important;
 flex-direction:column!important;grid-template-columns:none!important;gap:7px!important;
 align-items:stretch!important;min-width:0}
.sos663-retail-results[data-sos663-view="grid"] > *{min-width:0;width:100%!important}
.sos663-retail-results[data-sos663-view="list"] > *{min-width:0;width:100%!important;
 min-height:56px!important;max-width:100%!important;margin:0!important}
.sos663-retail-viewbar{display:flex;justify-content:flex-end;align-items:center;
 flex-wrap:wrap;gap:8px;margin:8px 0 10px;min-width:0}
@media(max-width:1100px){.sos663-retail-results[data-sos663-view="grid"]{
 grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@media(max-width:600px){.sos663-retail-results[data-sos663-view="grid"]{
 grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .sos663-viewbar-label{display:none}}

</style>

<style>
/* SERVICING_OS_CATALOG_664 — product paging; do not alter the POS cart or payment form. */
.sos664-retail-pager{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
 padding:9px 4px;margin:8px 0 12px;border-top:1px solid #e7d6c5;color:#866a52;font-size:11px}
.sos664-retail-pager .sos664-actions{display:flex;gap:6px}
.sos664-retail-pager button{min-height:32px!important;padding:6px 10px!important;border-radius:8px!important;
 border:1px solid #ddc8b5!important;background:#fffcf7!important;color:#77543d!important;font-weight:650!important}
.sos664-retail-pager button:disabled{opacity:.43;cursor:not-allowed}
.sos664-retail-stock{font-size:10px;color:#805a3e;padding:2px 6px;border-radius:6px;background:#f4e3d3}
.sos664-retail-stock.sos664-out{color:#9d4838;background:#f9e5dd}
</style>

<style>
/* SERVICING_OS_FEATURED_665: stock catalog is visible without search focus */
.sos665-retail-defaultbar,.sos665-retail-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;color:#7a5c47;margin:10px 0;padding:8px 4px;font-size:11px}
.sos665-retail-defaultbar strong{font-size:13px;color:#3c2c25;display:block}
.sos665-retail-defaultbar small{display:block;color:#8b725e;margin-top:4px}
.sos665-retail-defaultbar>button,.sos665-retail-footer button{border:1px solid #e2cdbb!important;border-radius:8px!important;min-height:33px!important;background:#f4e9dd!important;color:#79583f!important;padding:7px 11px!important;font-size:11px!important;font-weight:700!important}
.sos665-retail-footer{border-top:1px solid #e8d8ca;margin-top:10px}
.sos665-retail-footer>div{display:flex;gap:8px}
.sos665-retail-defaultbar>button:disabled,.sos665-retail-footer button:disabled{opacity:.43;cursor:not-allowed}
.sos663-retail-results[data-sos663-view="grid"]{align-content:start!important;grid-template-columns:repeat(4,minmax(0,1fr))!important}
.sos663-retail-results{min-height:420px;max-height:590px;overflow-y:auto}
@media(max-width:1250px){.sos663-retail-results[data-sos663-view="grid"]{grid-template-columns:repeat(3,minmax(0,1fr))!important}}
@media(max-width:850px){.sos663-retail-results[data-sos663-view="grid"]{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
</style>

<style>
/* SERVICING_OS_CUSTOMER_LOOKUP_666: one reliable picker, original native handler retained. */
.sos666-retail-picker{width:100%;min-width:0;margin:8px 0 11px;position:relative;z-index:20}
.sos666-native-old-search{display:none!important}
</style>


<style>
/* 6.67: restore the real native retail product grid without changing Add to Cart. */
.sos663-retail-results{box-sizing:border-box;min-height:0!important;max-height:none!important;overflow:visible!important;min-width:0!important;width:100%!important}
.sos663-retail-results[data-sos663-view="grid"]{display:grid!important;grid-template-columns:repeat(auto-fill,minmax(min(100%,175px),1fr))!important;gap:10px!important;align-items:stretch!important;align-content:start!important}
.sos663-retail-results[data-sos663-view="list"]{display:flex!important;flex-direction:column!important;gap:8px!important;align-items:stretch!important}
.sos663-retail-results[data-sos663-view="grid"]>*{min-width:0!important;max-width:100%!important;width:100%!important;min-height:90px;border-radius:11px!important;overflow-wrap:anywhere}
.sos663-retail-results[data-sos663-view="list"]>*{min-width:0!important;width:100%!important}
.sos665-retail-defaultbar{align-items:center!important;margin-bottom:10px!important}
.sos665-retail-defaultbar,.sos665-retail-footer{max-width:100%!important;box-sizing:border-box}
.sos666-retail-picker{margin:10px 0!important;position:relative!important;z-index:60!important}
</style>

<!-- SERVICING_SALES_VISUAL_669: shared visual rules only; existing product and cart events preserved. -->
<style src="./SalesProductVisual669.css"></style>
