<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

// SERVICING_OS_INVENTORY_V4: actual ERPNext Items, Item Prices, Bins and Stock Entries.
const bn = computed(() => currentLanguage.value === 'bn')
const copy = {
  inventory:['Inventory','ইনভেন্টরি'], subtitle:['Manage products, prices, warranty and live stock in one place','পণ্য, মূল্য, ওয়ারেন্টি ও বর্তমান স্টক একই স্থানে'],
  live:['Connected to ERPNext','ইআরপিনেক্সটের সাথে সংযুক্ত'], add:['Add product','নতুন পণ্য'], edit:['Edit product','পণ্য সম্পাদনা'], save:['Save product','পণ্য সংরক্ষণ'],
  refresh:['Refresh','রিফ্রেশ'], export:['Export CSV','সিএসভি ডাউনলোড'], grid:['Grid','গ্রিড'], list:['List','লিস্ট'],
  receive:['Receive stock','স্টক গ্রহণ'], issue:['Issue stock','স্টক ইস্যু'], restock:['Restock','পুনঃমজুত'],
  existing:['Existing products','বিদ্যমান পণ্য'], chooseExisting:['Select an existing product to edit it','বিদ্যমান পণ্য সম্পাদনা করতে নির্বাচন করুন'],
  lookupHint:['Search by name or SKU; select a suggested product','নাম বা কোড লিখে পণ্য নির্বাচন করুন'], noMatch:['No matching existing products','মিলে যাওয়া কোনো পণ্য নেই'],
  looking:['Looking up products…','পণ্য খোঁজা হচ্ছে…'], clickToEdit:['Open for editing','সম্পাদনার জন্য খুলুন'], chosenProduct:['Selected product','নির্বাচিত পণ্য'],
  selectGroup:['Select category','ক্যাটাগরি নির্বাচন করুন'], selectUnit:['Select unit','একক নির্বাচন করুন'], selectBrand:['Select brand','ব্র্যান্ড নির্বাচন করুন'],
  products:['Active products','সক্রিয় পণ্য'], units:['Units in stock','মজুত পরিমাণ'], alerts:['Low-stock products','কম মজুত পণ্য'], value:['Inventory valuation','স্টক মূল্যায়ন'],
  catalog:['Product catalog','পণ্যের তালিকা'], countNote:['Item Master & warehouse balances','আইটেম মাস্টার ও গুদামভিত্তিক স্টক'],
  search:['Search product, SKU or brand…','পণ্যের নাম, কোড বা ব্র্যান্ড খুঁজুন…'], warehouses:['All warehouses','সব গুদাম'], groups:['All categories','সব ক্যাটাগরি'], all:['All stock','সব স্টক'],
  in:['In stock','স্টক আছে'], low:['Low stock','কম স্টক'], out:['Out of stock','স্টক শেষ'],
  item:['Product','পণ্য'], sku:['Item code / SKU','পণ্য কোড'], group:['Category','ক্যাটাগরি'], stock:['Available stock','মজুত'],
  buying:['Buying price','ক্রয়মূল্য'], selling:['Selling price','বিক্রয়মূল্য'], warranty:['Warranty','ওয়ারেন্টি'], amount:['Stock value','স্টক মূল্য'], status:['Status','অবস্থা'], actions:['Actions','কার্যক্রম'],
  days:['days','দিন'], none:['Not set','সেট করা নেই'],
  name:['Product name','পণ্যের নাম'], unit:['Stock unit','মজুত একক'], brand:['Brand','ব্র্যান্ড'], image:['Image URL','ছবির লিংক'], description:['Description','বিবরণ'],
  autoSku:['Optional — leave blank for auto-generated SKU','ঐচ্ছিক — ফাঁকা রাখলে স্বয়ংক্রিয় কোড হবে'],
  imageHelp:['Use a product image URL, or select an image to upload after saving','ছবির লিংক দিন, অথবা সংরক্ষণের পরে আপলোডের জন্য ছবি নির্বাচন করুন'],
  upload:['Product photo (optional)','পণ্যের ছবি (ঐচ্ছিক)'],
  priceHelp:['Separate ERPNext Item Price records. Existing prices remain unchanged if left blank.','ইআরপিনেক্সটের পৃথক আইটেম প্রাইস। ফাঁকা রাখলে আগের মূল্য অপরিবর্তিত থাকবে।'],
  priceList:['Price lists','মূল্য তালিকা'], notConfigured:['Not configured','কনফিগার করা নেই'], restricted:['Restricted','অনুমতি নেই'],
  warrantyHelp:['Enter days: 30, 90, 180, 365 or 730, for example','দিন লিখুন: যেমন ৩০, ৯০, ১৮০, ৩৬৫ বা ৭৩০'],
  skuNote:['SKU cannot be changed after creation','তৈরির পরে পণ্য কোড পরিবর্তন করা যাবে না'],
  cancel:['Cancel','বাতিল'], close:['Close','বন্ধ'], saving:['Saving…','সংরক্ষণ হচ্ছে…'], details:['Product details','পণ্যের তথ্য'],
  qty:['Quantity','পরিমাণ'], warehouse:['Warehouse','গুদাম'], valuation:['Receipt unit valuation','প্রাপ্তির একক মূল্যায়ন'],
  notes:['Remarks (optional)','মন্তব্য (ঐচ্ছিক)'], submit:['Submit stock entry','স্টক এন্ট্রি জমা দিন'], submitting:['Submitting…','জমা হচ্ছে…'],
  choose:['Choose a product','পণ্য নির্বাচন করুন'], chooseWarehouse:['Choose a warehouse','গুদাম নির্বাচন করুন'],
  empty:['No products match your filters.','এই ফিল্টারে কোনো পণ্য পাওয়া যায়নি।'], loading:['Loading inventory…','ইনভেন্টরি লোড হচ্ছে…'],
  more:['Show more products','আরও পণ্য দেখুন'], showing:['Showing','দেখাচ্ছে'], of:['of','মোট'], updated:['Updated','সর্বশেষ আপডেট'],
  threshold:['Low-stock alert at','কম স্টক সতর্কতা'], margin:['Gross margin','মোট মুনাফার হার'], noMargin:['—','—'],
  noPrices:['Company-currency buying and selling price lists must be configured in ERPNext before saving rates.','মূল্য সংরক্ষণের আগে ইআরপিনেক্সটে ক্রয় ও বিক্রয়ের মূল্য তালিকা সেট করুন।'],
  noPriceAccess:['Your role cannot view or edit Item Prices. Ask an administrator to grant Item Price permissions.','আপনার ভূমিকায় আইটেম মূল্য পড়া বা সম্পাদনার অনুমতি নেই।'],
  serial:['Serial/batch-controlled items must use their dedicated ERPNext tracking workflow.','সিরিয়াল বা ব্যাচ পণ্যের জন্য আলাদা ইআরপিনেক্সট প্রক্রিয়া ব্যবহার করুন।'],
  stockNote:['A stock receipt changes inventory valuation; it is not a supplier purchase invoice.','স্টক গ্রহণে মজুত বদলায়; এটি সরবরাহকারীর ক্রয় ইনভয়েস নয়।'],
  uploadFail:['Product saved, but photo upload failed:','পণ্য সংরক্ষিত, তবে ছবি আপলোড ব্যর্থ:'],
  truncated:['Only the first 2,500 accessible Items are displayed.','প্রথম ২,৫০০টি আইটেম দেখানো হচ্ছে।'],
  back:['Back to list','তালিকায় ফিরুন'],
}
const t = (k) => copy[k]?.[bn.value ? 1 : 0] || k
const inventory = ref({ company:'', currency:'BDT', items:[], warehouses:[], groups:[], uoms:[], brands:[], price_lists:{}, permissions:{} })
const loading = ref(false), error = ref(''), success = ref(''), newSku = ref('')
const warehouse = ref(''), group = ref(''), stockFilter = ref('all'), search = ref(''), threshold = ref(5)
const sort = ref('newest'), view = ref('grid'), pageSize = ref(48), lastRefreshed = ref(null)
const modal = ref(''), busy = ref(false), modalError = ref(''), chosenImage = ref(null)
const stockSearch = ref('')
const lookup = ref({open:false,kind:'product',options:[],loading:false,index:-1,query:''})
let lookupTimer = null, lookupSeq = 0, lookupBlurTimer = null
const product = ref(blankProduct())
const movement = ref('receive'), motion = ref(blankMotion())
let poller = null, requestSeq = 0
function blankProduct() { return { original_item_code:'',item_code:'',item_name:'',item_group:'',stock_uom:'Nos',brand:'',description:'',image:'',warranty_days:0,buying_price:'',selling_price:'' } }
function blankMotion() { return { item_code:'',warehouse:'',qty:1,basic_rate:'',remarks:'' } }
function apiError(raw, fallback) {
  try { const messages = JSON.parse(raw?._server_messages || '[]'); if (messages.length) { const v = JSON.parse(messages[0]); if (v.message) return String(v.message).replace(/<[^>]*>/g, '') } }
  catch (_) {}
  return typeof raw?.message === 'string' ? raw.message : fallback
}
async function api(method, params={}, post=false) {
  const url = new URL('/api/method/servicing_os.api.inventory_workspace.' + method, window.location.origin)
  const headers = { Accept:'application/json' }
  const opts = { credentials:'same-origin', cache:'no-store', headers }
  if (post) {
    opts.method = 'POST'; headers['Content-Type'] = 'application/json'
    const token = window.csrf_token || window.frappe?.csrf_token
    if (token) headers['X-Frappe-CSRF-Token'] = token
    opts.body = JSON.stringify(params)
  } else { for (const [key, value] of Object.entries(params)) { if (value !== null && value !== undefined) url.searchParams.set(key, String(value)) } }
  const res = await fetch(url, opts)
  let payload; try { payload = await res.json() } catch { throw new Error('ERPNext returned an invalid response') }
  if (!res.ok || payload.exc || payload.exception) throw new Error(apiError(payload, `ERPNext request failed (${res.status})`))
  return payload.message
}
async function reload() {
  const seq = ++requestSeq
  loading.value = true; error.value = ''
  try {
    const data = await api('get_inventory', { warehouse: warehouse.value })
    if (seq !== requestSeq) return
    inventory.value = {
      company:data.company || '', currency:data.currency || 'BDT', items:data.items || [],
      warehouses:data.warehouses || [], groups:data.groups || [], uoms:data.uoms || [],
      brands:data.brands || [], price_lists:data.price_lists || {}, permissions:data.permissions || {},
      truncated:!!data.truncated, warranty_supported:!!data.warranty_supported,
    }
    lastRefreshed.value = new Date()
  } catch (e) { if (seq === requestSeq) error.value = e?.message || String(e) }
  finally { if (seq === requestSeq) loading.value = false }
}
watch(warehouse, () => { pageSize.value=48; group.value=''; reload() })
watch([search,group,stockFilter,sort,view], () => { pageSize.value=48 })
function onFocus() { if (!modal.value && !document.hidden) reload() }
onMounted(() => { reload(); poller = window.setInterval(onFocus, 60000); window.addEventListener('focus',onFocus) })
onUnmounted(() => { window.clearInterval(poller); window.removeEventListener('focus',onFocus) })
const items = computed(() => inventory.value.items || [])
const groups = computed(() => [...new Set(items.value.map(i => i.item_group).filter(Boolean))].sort())
const permissions = computed(() => inventory.value.permissions || {})
function statusOf(i) { const q=Number(i.actual_qty||0); return q<=0?'out':q<=Number(threshold.value||5)?'low':'in' }
const filtered = computed(() => {
  const q=search.value.trim().toLocaleLowerCase()
  const arr=items.value.filter(i => {
    if (q && ![i.item_code,i.item_name,i.item_group,i.brand].some(v=>String(v||'').toLocaleLowerCase().includes(q))) return false
    if (group.value && i.item_group!==group.value) return false
    if (stockFilter.value!=='all' && statusOf(i)!==stockFilter.value) return false
    return true
  })
  if (sort.value==='name') arr.sort((a,b)=>String(a.item_name).localeCompare(String(b.item_name)))
  else if (sort.value==='stock') arr.sort((a,b)=>Number(b.actual_qty)-Number(a.actual_qty))
  else if (sort.value==='sell') arr.sort((a,b)=>Number(b.selling_price||0)-Number(a.selling_price||0))
  return arr
})
const visible = computed(() => filtered.value.slice(0,pageSize.value))
const totals = computed(() => ({
  products:items.value.length,
  units:items.value.reduce((s,i)=>s+Number(i.actual_qty||0),0),
  low:items.value.filter(i=>statusOf(i)==='low').length,
  value:items.value.reduce((s,i)=>s+Number(i.stock_value||0),0),
}))
function number(v) { return Number(v||0).toLocaleString(bn.value?'bn-BD':'en-BD',{maximumFractionDigits:2}) }
function money(v) { return v===null || v===undefined ? '—' : `${inventory.value.currency} ${number(v)}` }
function warrantyText(i) { return Number(i.warranty_days)>0?`${number(i.warranty_days)} ${t('days')}`:t('none') }
function margin(i) {
  const b=Number(i.buying_price),s=Number(i.selling_price)
  if (i.buying_price===null || i.selling_price===null || !s) return t('noMargin')
  return `${number(((s-b)/s)*100)}%`
}
function csvCell(v) { let s=String(v??''); if (/^\s*[=+@\-]/.test(s)) s="'"+s; return '"'+s.replace(/"/g,'""')+'"' }
function exportCsv() {
  const head=['SKU','Product','Category','Brand','Warehouse selection','Quantity','Reserved','UOM','Buying Price','Selling Price','Warranty Days','Stock Value']
  const rows=filtered.value.map(i=>[i.item_code,i.item_name,i.item_group,i.brand,warehouse.value||'All',i.actual_qty,i.reserved_qty,i.stock_uom,i.buying_price,i.selling_price,i.warranty_days,i.stock_value])
  const csv='\ufeff'+[head,...rows].map(row=>row.map(csvCell).join(',')).join('\r\n')
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}))
  const a=document.createElement('a'); a.href=url; a.download='servicing-os-inventory.csv'; a.click()
  window.setTimeout(()=>URL.revokeObjectURL(url),1000)
}

// Existing-item autocomplete uses permission-filtered ERPNext Item results.
// A short local shortlist appears immediately; the backend refreshes it without
// ever allowing an arbitrary typed product string to be posted as stock.
function localMatches(query) {
  const needle = String(query || '').trim().toLocaleLowerCase()
  const list = items.value.filter(i => !needle || [i.item_name, i.item_code, i.brand]
    .some(x => String(x || '').toLocaleLowerCase().includes(needle)))
  return list.slice(0, 12).map(i => ({item_code:i.item_code,item_name:i.item_name,item_group:i.item_group,brand:i.brand}))
}
function dismissLookup() {
  lookupSeq += 1
  if (lookupTimer) window.clearTimeout(lookupTimer)
  if (lookupBlurTimer) window.clearTimeout(lookupBlurTimer)
  lookup.value = {open:false,kind:'product',options:[],loading:false,index:-1,query:''}
}
function lookupBlur() {
  if (lookupBlurTimer) window.clearTimeout(lookupBlurTimer)
  lookupBlurTimer = window.setTimeout(() => {lookup.value.open=false}, 180)
}
function scheduleLookup(kind, immediate=false) {
  if (lookupTimer) window.clearTimeout(lookupTimer)
  if (lookupBlurTimer) window.clearTimeout(lookupBlurTimer)
  const query = kind === 'product' ? product.value.item_name : stockSearch.value
  const seq = ++lookupSeq
  lookup.value = {open:true,kind,options:localMatches(query),loading:true,index:-1,query}
  lookupTimer = window.setTimeout(async () => {
    try {
      const results = await api('search_inventory_items', {q:query, limit:12})
      if (seq !== lookupSeq || !lookup.value.open || lookup.value.kind !== kind) return
      lookup.value.options = Array.isArray(results) ? results : []
      lookup.value.index = -1
    } catch (e) {
      // Local matching remains useful if a permissions/network error occurs.
      if (seq === lookupSeq) lookup.value.options = localMatches(query)
    } finally {
      if (seq === lookupSeq) lookup.value.loading = false
    }
  }, immediate ? 0 : 200)
}
function lookupKeys(event, kind) {
  if (event.key === 'Escape') { dismissLookup();return }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!lookup.value.open) { scheduleLookup(kind,true);return }
    const n=lookup.value.options.length
    if (n) lookup.value.index = (lookup.value.index+(event.key==='ArrowDown'?1:n-1)+n)%n
  } else if (event.key === 'Enter' && lookup.value.open && lookup.value.index>=0) {
    const result=lookup.value.options[lookup.value.index]
    if (result) {event.preventDefault();selectLookup(result,kind)}
  }
}
async function selectLookup(item,kind) {
  dismissLookup()
  if (kind==='product') {
    modalError.value=''
    busy.value = true
    try {
      const result = await api('get_inventory_item', {item_code:item.item_code})
      if (!result?.item_code) throw new Error('Product record not found')
      openEdit(result)
    } catch (e) {modalError.value=e?.message||String(e)}
    finally {busy.value=false}
    return
  }
  motion.value.item_code = item.item_code
  stockSearch.value = `${item.item_name} · ${item.item_code}`
  if (movement.value==='receive') {
    const local=items.value.find(i=>i.item_code===item.item_code)
    if (local && local.buying_price !== null) motion.value.basic_rate=local.buying_price
    else {
      try {
        const remote=await api('get_inventory_item', {item_code:item.item_code})
        if (remote?.buying_price !== null && remote?.buying_price !== undefined) motion.value.basic_rate=remote.buying_price
      } catch (_) { /* User can set a manual valuation rate. */ }
    }
  }
}
function openAdd() {
  if (!permissions.value.create_item) return
  dismissLookup()
  product.value=blankProduct()
  product.value.item_group=inventory.value.groups?.[0] || ''
  product.value.stock_uom=inventory.value.uoms?.includes('Nos')?'Nos':(inventory.value.uoms?.[0]||'')
  modalError.value=''; chosenImage.value=null; modal.value='product'
}
function openEdit(i) {
  dismissLookup()
  product.value = {
    original_item_code:i.item_code,original_modified:i.modified,item_code:i.item_code,item_name:i.item_name,
    item_group:i.item_group,stock_uom:i.stock_uom,brand:i.brand||'',description:i.description||'',image:i.image||'',
    warranty_days:i.warranty_days||0,buying_price:i.buying_price ?? '',selling_price:i.selling_price ?? '',
  }
  modalError.value='';chosenImage.value=null;modal.value='product'
}
const editing = computed(() => !!product.value.original_item_code)
const productWritable = computed(() => editing.value ? !!permissions.value.edit_item : !!permissions.value.create_item)
const pricesWritable = computed(() => !!permissions.value.price_edit)
async function uploadImage(itemCode,file) {
  if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size>5*1024*1024) throw new Error('Choose a JPG, PNG or WebP image under 5 MB')
  const body=new FormData();body.append('file',file);body.append('is_private','0');body.append('doctype','Item');body.append('docname',itemCode);body.append('fieldname','image')
  const headers={ Accept:'application/json' }
  const csrf=window.csrf_token || window.frappe?.csrf_token
  if (csrf) headers['X-Frappe-CSRF-Token']=csrf
  const res=await fetch('/api/method/upload_file',{method:'POST',credentials:'same-origin',headers,body})
  const payload=await res.json()
  if (!res.ok || payload.exc || payload.exception || !payload.message?.file_url) throw new Error(apiError(payload,'File upload failed'))
  await api('set_product_image',{item_code:itemCode,file_url:payload.message.file_url},true)
}
async function saveProduct() {
  if (busy.value || !productWritable.value) return
  modalError.value=''
  if (!product.value.item_name.trim() || !product.value.item_group || !product.value.stock_uom) { modalError.value=bn.value?'পণ্যের নাম, ক্যাটাগরি ও একক দিন।':'Product name, category and unit are required.'; return }
  busy.value=true
  let code=''
  try {
    const payload={...product.value}
    if (!pricesWritable.value) { payload.buying_price=null; payload.selling_price=null }
    const saved=await api('save_product',{data:payload},true)
    code=saved.item_code
    product.value.original_modified=saved.modified
    if (chosenImage.value) await uploadImage(code,chosenImage.value)
    modal.value='';chosenImage.value=null;newSku.value=!editing.value?code:''
    success.value=(saved.created?(bn.value?'নতুন পণ্য তৈরি হয়েছে: ':'Product created: '):(bn.value?'পণ্য আপডেট হয়েছে: ':'Product updated: '))+code
    await reload()
  } catch (e) {
    const m=e?.message||String(e)
    modalError.value=code?`${t('uploadFail')} ${m}`:m
    if (code) { product.value.original_item_code=code;product.value.item_code=code;await reload() }
  } finally { busy.value=false }
}
function openMovement(type,item='') {
  if (!permissions.value.stock_post) return
  dismissLookup()
  movement.value=type
  motion.value={...blankMotion(),item_code:item,warehouse:warehouse.value||(inventory.value.warehouses?.[0]?.name||'')}
  const known = items.value.find(i=>i.item_code===item)
  stockSearch.value = known ? `${known.item_name} · ${known.item_code}` : ''
  if (type==='receive' && item) {
    const selected=items.value.find(i=>i.item_code===item)
    motion.value.basic_rate=selected?.buying_price ?? ''
  }
  modalError.value='';modal.value='movement'
}
const selectedItem = computed(() => items.value.find(i=>i.item_code===motion.value.item_code))
const availableHere = computed(() => {
  if (!selectedItem.value || !motion.value.warehouse) return null
  if (warehouse.value && warehouse.value!==motion.value.warehouse) return null
  return Number((selectedItem.value.by_warehouse||[]).find(w=>w.warehouse===motion.value.warehouse)?.qty||0)
})
async function saveMovement() {
  if (busy.value) return
  modalError.value=''
  if (!motion.value.item_code || !motion.value.warehouse || !(Number(motion.value.qty)>0)) { modalError.value=bn.value?'পণ্য, গুদাম ও সঠিক পরিমাণ দিন।':'Choose a product, warehouse and positive quantity.';return }
  if (selectedItem.value?.has_serial_no || selectedItem.value?.has_batch_no) {modalError.value=t('serial');return}
  if (movement.value==='receive' && !(Number(motion.value.basic_rate)>0)) {modalError.value=bn.value?'প্রাপ্তির মূল্যায়ন হার দিন।':'Enter a positive receipt valuation rate.';return}
  busy.value=true
  try {
    const data=await api('post_stock_movement',{...motion.value,movement:movement.value},true)
    modal.value='';success.value=`Stock Entry: ${data.stock_entry}`;newSku.value='';await reload()
  } catch(e) {modalError.value=e?.message||String(e)} finally {busy.value=false}
}
function close() {if (!busy.value) {dismissLookup(); modal.value=''}}
</script>

<template>
  <section class="inv-root sos-inventory-view-root" :lang="bn ? 'bn' : 'en'">
    <header class="inv-head">
      <div>
        <div class="inv-eyebrow"><span class="inv-live-dot"></span>{{ t('live') }}</div>
        <h1>{{ t('inventory') }}</h1>
        <p>{{ t('subtitle') }}</p>
      </div>
      <div class="inv-actions">
        <button type="button" class="inv-btn inv-outline" :disabled="loading" @click="reload">↻ {{ t('refresh') }}</button>
        <button type="button" class="inv-btn inv-outline" :disabled="!items.length" @click="exportCsv">⇩ {{ t('export') }}</button>
      </div>
    </header>

    <div v-if="error" class="inv-alert inv-error" role="alert">{{ error }} <button type="button" @click="reload">{{ t('refresh') }}</button></div>
    <div v-if="success" class="inv-alert inv-success" role="status">{{ success }} <button v-if="newSku && permissions.stock_post" type="button" @click="openMovement('receive',newSku)">{{ t('receive') }} ↗</button><button type="button" @click="success='';newSku=''">×</button></div>
    <div v-if="inventory.truncated" class="inv-alert">{{ t('truncated') }}</div>
    <div v-if="inventory.items.length && (!inventory.price_lists.buying || !inventory.price_lists.selling)" class="inv-alert">{{ t('noPrices') }}</div>
    <div v-if="!permissions.price_read && !loading && items.length" class="inv-alert">{{ t('noPriceAccess') }}</div>

    <div class="inv-metrics">
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">▦</span><span class="inv-stat-tag">PRODUCTS</span></div><div class="inv-stat-number">{{ number(totals.products) }}</div><span>{{ t('products') }}</span></div>
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">▤</span><span class="inv-stat-tag">QUANTITY</span></div><div class="inv-stat-number">{{ number(totals.units) }}</div><span>{{ t('units') }}</span></div>
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">!</span><span class="inv-stat-tag">ALERTS</span></div><div class="inv-stat-number">{{ number(totals.low) }}</div><span>{{ t('alerts') }}</span></div>
      <div class="inv-stat"><div class="inv-stat-top"><span class="inv-stat-symbol">৳</span><span class="inv-stat-tag">VALUATION</span></div><div class="inv-stat-number inv-amount">{{ money(totals.value) }}</div><span>{{ t('value') }}</span></div>
    </div>

    <div class="inv-panel">
      <div class="inv-panel-head">
        <div><h2>{{ t('catalog') }}</h2><p>{{ t('countNote') }}<span v-if="lastRefreshed"> · {{ t('updated') }} {{ lastRefreshed.toLocaleTimeString(bn?'bn-BD':'en-BD',{hour:'2-digit',minute:'2-digit'}) }}</span></p></div>
        <div class="inv-panel-actions">
          <button v-if="permissions.stock_post" type="button" class="inv-btn inv-small" :disabled="!items.length" @click="openMovement('issue')">− {{ t('issue') }}</button>
          <div class="inv-view-switch" role="group" :aria-label="'View mode'">
            <button type="button" :class="{chosen:view==='grid'}" :aria-pressed="view==='grid'" @click="view='grid'" :title="t('grid')">▦ <span>{{ t('grid') }}</span></button>
            <button type="button" :class="{chosen:view==='list'}" :aria-pressed="view==='list'" @click="view='list'" :title="t('list')">☷ <span>{{ t('list') }}</span></button>
          </div>
        </div>
      </div>
      <div class="inv-toolbar">
        <label class="inv-search"><span aria-hidden="true">⌕</span><input v-model="search" type="search" :placeholder="t('search')" :aria-label="t('search')" /></label>
        <select v-model="warehouse" :aria-label="t('warehouses')"><option value="">{{ t('warehouses') }}</option><option v-for="w in inventory.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name||w.name }}</option></select>
        <select v-model="group" :aria-label="t('groups')"><option value="">{{ t('groups') }}</option><option v-for="g in groups" :key="g" :value="g">{{ g }}</option></select>
        <select v-model="stockFilter" :aria-label="t('all')"><option value="all">{{ t('all') }}</option><option value="in">{{ t('in') }}</option><option value="low">{{ t('low') }}</option><option value="out">{{ t('out') }}</option></select>
      </div>
      <div class="inv-summary">
        <span>{{ t('showing') }} {{ number(visible.length) }} {{ t('of') }} {{ number(filtered.length) }} {{ t('products').toLowerCase() }}</span>
        <div class="inv-sorters">
          <label>{{ t('threshold') }} <input v-model.number="threshold" type="number" min="1" max="100000" step="1" /></label>
          <select v-model="sort" :aria-label="'Sort products'"><option value="newest">{{ bn?'সর্বশেষ পরিবর্তন':'Recently updated' }}</option><option value="name">{{ bn?'নাম অনুযায়ী':'Product name' }}</option><option value="stock">{{ bn?'মজুত অনুযায়ী':'Highest stock' }}</option><option value="sell">{{ bn?'বিক্রয়মূল্য অনুযায়ী':'Selling price' }}</option></select>
        </div>
      </div>
      <div v-if="loading && !items.length" class="inv-empty">{{ t('loading') }}</div>
      <div v-else-if="!filtered.length" class="inv-empty">{{ t('empty') }} <button v-if="permissions.create_item && !items.length" type="button" class="inv-btn inv-primary" @click="openAdd">＋ {{ t('add') }}</button></div>

      <!-- Real grid: responsive 4/3/2/1 product tiles with individual edit & stock actions. -->
      <div v-else-if="view==='grid'" class="inv-grid">
        <article v-for="i in visible" :key="i.item_code" class="inv-card">
          <div class="inv-card-image"><img v-if="i.image" :src="i.image" :alt="i.item_name" loading="lazy" /><span v-else class="inv-card-glyph">{{ (i.item_name||'?').slice(0,1).toUpperCase() }}</span><span class="inv-chip inv-image-chip" :class="'inv-'+statusOf(i)">{{ t(statusOf(i)) }}</span></div>
          <div class="inv-card-body">
            <div class="inv-card-category">{{ i.item_group||'—' }}<span v-if="i.brand"> · {{ i.brand }}</span></div>
            <h3 :title="i.item_name">{{ i.item_name }}</h3>
            <div class="inv-card-sku">{{ i.item_code }}</div>
            <div class="inv-price-duo"><div><small>{{ t('buying') }}</small><strong>{{ permissions.price_read ? money(i.buying_price) : t('restricted') }}</strong></div><div><small>{{ t('selling') }}</small><strong class="inv-sellprice">{{ permissions.price_read ? money(i.selling_price) : t('restricted') }}</strong></div></div>
            <div class="inv-card-meta"><span><b>{{ number(i.actual_qty) }}</b> {{ i.stock_uom }}</span><span>◷ {{ warrantyText(i) }}</span></div>
            <div class="inv-card-foot"><span>{{ t('amount') }}: {{ money(i.stock_value) }}</span><div>
              <button type="button" class="inv-square" :aria-label="t('details')+': '+i.item_name" :title="t('details')" @click="openEdit(i)">↗</button>
              <button v-if="permissions.stock_post" type="button" class="inv-square" :disabled="!!i.has_serial_no || !!i.has_batch_no" :aria-label="t('receive')+': '+i.item_name" :title="(i.has_serial_no || i.has_batch_no)?t('serial'):t('receive')" @click="openMovement('receive',i.item_code)">＋</button>
            </div></div>
          </div>
        </article>
      </div>
      <div v-else class="inv-table-wrap">
        <table class="inv-table"><thead><tr><th>{{ t('item') }}</th><th>{{ t('sku') }}</th><th>{{ t('group') }}</th><th class="inv-right">{{ t('stock') }}</th><th class="inv-right">{{ t('buying') }}</th><th class="inv-right">{{ t('selling') }}</th><th>{{ t('warranty') }}</th><th>{{ t('status') }}</th><th>{{ t('actions') }}</th></tr></thead><tbody>
          <tr v-for="i in visible" :key="i.item_code">
            <td><div class="inv-product"><div class="inv-thumb"><img v-if="i.image" :src="i.image" :alt="i.item_name" loading="lazy" /><span v-else>{{ (i.item_name||'?').slice(0,1).toUpperCase() }}</span></div><div class="inv-itemname"><strong>{{ i.item_name }}</strong><small>{{ i.brand||i.stock_uom }}</small></div></div></td>
            <td class="inv-code">{{ i.item_code }}</td><td class="inv-muted">{{ i.item_group }}</td>
            <td class="inv-right">{{ number(i.actual_qty) }} {{ i.stock_uom }}</td>
            <td class="inv-right inv-money">{{ permissions.price_read?money(i.buying_price):t('restricted') }}</td>
            <td class="inv-right inv-money">{{ permissions.price_read?money(i.selling_price):t('restricted') }}</td>
            <td>{{ warrantyText(i) }}</td><td><span class="inv-chip" :class="'inv-'+statusOf(i)">{{ t(statusOf(i)) }}</span></td>
            <td><button type="button" class="inv-rowaction" :title="t('details')" @click="openEdit(i)">✎</button><button v-if="permissions.stock_post" type="button" class="inv-rowaction" :disabled="!!i.has_serial_no || !!i.has_batch_no" :title="t('receive')" @click="openMovement('receive',i.item_code)">＋</button></td>
          </tr>
        </tbody></table>
      </div>
      <div v-if="pageSize<filtered.length" class="inv-more"><button type="button" class="inv-btn inv-outline" @click="pageSize+=48">{{ t('more') }} ({{ number(filtered.length-pageSize) }})</button></div>
    </div>

    <div v-if="!modal && (permissions.create_item || permissions.stock_post)" class="inv-floating-actions" role="group" :aria-label="bn?'পণ্য ও স্টক কার্যক্রম':'Product and stock quick actions'">
      <button v-if="permissions.stock_post" type="button" class="inv-fab inv-fab-restock" :disabled="!items.length" @click="openMovement('receive')" :title="t('restock')">
        <span class="inv-fab-icon" aria-hidden="true">↥</span><span>{{ t('restock') }}</span>
      </button>
      <button v-if="permissions.create_item" type="button" class="inv-fab inv-fab-add" @click="openAdd" :title="t('add')">
        <span class="inv-fab-icon" aria-hidden="true">＋</span><span>{{ t('add') }}</span>
      </button>
    </div>

    <div v-if="modal==='product'" class="inv-modal-backdrop" @click.self="close" @keydown.esc="close">
      <div class="inv-modal inv-product-modal" role="dialog" aria-modal="true" :aria-label="editing?t('edit'):t('add')">
        <div class="inv-modal-header"><div><div class="inv-eyebrow">{{ t('details') }}</div><h2>{{ editing?t('edit'):t('add') }}</h2><p class="inv-helper">{{ t('skuNote') }}</p></div><button type="button" class="inv-close" :disabled="busy" :aria-label="t('close')" @click="close">×</button></div>
        <form class="inv-modal-form" @submit.prevent="saveProduct">
          <div class="inv-form-grid">
            <div class="inv-lookup-field"><label for="inv-product-name">{{ t('name') }} *</label>
              <div class="inv-lookup-shell" @focusout="lookupBlur">
                <input id="inv-product-name" v-model="product.item_name" maxlength="140" autocomplete="off" required
                  role="combobox" aria-autocomplete="list" aria-controls="inv-product-matches"
                  :aria-expanded="lookup.open && lookup.kind==='product'" :disabled="!productWritable || busy"
                  @focus="!editing && scheduleLookup('product',true)"
                  @input="!editing && scheduleLookup('product')" @keydown="lookupKeys($event,'product')" />
                <span class="inv-lookup-mark" aria-hidden="true">⌕</span>
                <div v-if="!editing && lookup.open && lookup.kind==='product'" id="inv-product-matches" class="inv-lookup-options" role="listbox">
                  <div class="inv-lookup-heading">{{ t('existing') }} <small>{{ t('chooseExisting') }}</small></div>
                  <button v-for="(match,n) in lookup.options" :key="match.item_code" type="button"
                    role="option" :aria-selected="lookup.index===n" :class="{selected:lookup.index===n}"
                    @mousedown.prevent @click.stop="selectLookup(match,'product')">
                    <span class="inv-match-icon">▣</span>
                    <span class="inv-match-copy"><strong>{{ match.item_name }}</strong><small>{{ match.item_code }} · {{ match.item_group }}</small></span>
                    <span class="inv-match-action">{{ t('clickToEdit') }} ↗</span>
                  </button>
                  <p v-if="!lookup.options.length && !lookup.loading" class="inv-lookup-empty">{{ t('noMatch') }}</p>
                  <p v-if="lookup.loading" class="inv-lookup-loading">{{ t('looking') }}</p>
                </div>
              </div>
              <small v-if="!editing">{{ t('lookupHint') }}</small>
            </div>
            <label>{{ t('sku') }}<input v-model="product.item_code" maxlength="140" :readonly="editing" :disabled="!productWritable" :placeholder="t('autoSku')" /><small v-if="!editing">{{ t('autoSku') }}</small></label>
          </div>
          <div class="inv-form-grid"><label>{{ t('group') }} *<select v-model="product.item_group" required :disabled="!productWritable"><option value="">{{ t('selectGroup') }}</option><option v-for="g in inventory.groups" :key="g" :value="g">{{ g }}</option></select></label><label>{{ t('unit') }} *<select v-model="product.stock_uom" required :disabled="!productWritable"><option value="">{{ t('selectUnit') }}</option><option v-for="u in inventory.uoms" :key="u" :value="u">{{ u }}</option></select></label></div>
          <div class="inv-form-grid"><label>{{ t('brand') }}<select v-model="product.brand" :disabled="!productWritable"><option value="">{{ t('selectBrand') }}</option><option v-for="b in inventory.brands" :key="b" :value="b">{{ b }}</option></select></label><label>{{ t('warranty') }} ({{ t('days') }})<input v-model.number="product.warranty_days" type="number" min="0" max="36500" step="1" :disabled="!productWritable"/><small>{{ t('warrantyHelp') }}</small></label></div>
          <div class="inv-form-divider"><span>{{ t('priceList') }}: {{ inventory.price_lists.buying||t('notConfigured') }} / {{ inventory.price_lists.selling||t('notConfigured') }}</span></div>
          <div class="inv-form-grid"><label>{{ t('buying') }} ({{ inventory.currency }})<input v-model="product.buying_price" inputmode="decimal" type="number" step="0.01" min="0" :disabled="!productWritable || !pricesWritable" placeholder="0.00" /></label><label>{{ t('selling') }} ({{ inventory.currency }})<input v-model="product.selling_price" inputmode="decimal" type="number" step="0.01" min="0" :disabled="!productWritable || !pricesWritable" placeholder="0.00" /></label></div>
          <p class="inv-helper">{{ pricesWritable?t('priceHelp'):t('noPriceAccess') }}</p>
          <label>{{ t('description') }}<textarea v-model="product.description" rows="2" maxlength="10000" :disabled="!productWritable"></textarea></label>
          <label>{{ t('image') }}<input v-model="product.image" type="text" maxlength="500" placeholder="/files/product.jpg" :disabled="!productWritable" /></label>
          <label v-if="productWritable">{{ t('upload') }}<input type="file" accept="image/png,image/jpeg,image/webp" @change="chosenImage=$event.target.files?.[0] || null" /><small>{{ t('imageHelp') }}</small></label>
          <div v-if="editing" class="inv-helper">{{ t('stockNote') }}</div>
          <p v-if="modalError" class="inv-alert inv-error" role="alert">{{ modalError }}</p>
          <div class="inv-modal-foot"><button type="button" class="inv-btn inv-outline" :disabled="busy" @click="close">{{ t('cancel') }}</button><button v-if="productWritable" type="submit" class="inv-btn inv-primary" :disabled="busy">{{ busy?t('saving'):t('save') }}</button></div>
        </form>
      </div>
    </div>

    <div v-if="modal==='movement'" class="inv-modal-backdrop" @click.self="close" @keydown.esc="close">
      <div class="inv-modal" role="dialog" aria-modal="true" :aria-label="movement==='receive'?t('receive'):t('issue')">
        <div class="inv-modal-header"><div><div class="inv-eyebrow">{{ t('stock') }}</div><h2>{{ movement==='receive'?t('receive'):t('issue') }}</h2></div><button type="button" class="inv-close" :disabled="busy" :aria-label="t('close')" @click="close">×</button></div>
        <form class="inv-modal-form" @submit.prevent="saveMovement">
          <div class="inv-lookup-field"><label for="inv-restock-name">{{ t('choose') }} *</label>
            <div class="inv-lookup-shell" @focusout="lookupBlur">
              <input id="inv-restock-name" v-model="stockSearch" type="search" maxlength="160" autocomplete="off" required
                role="combobox" aria-autocomplete="list" aria-controls="inv-stock-matches"
                :aria-expanded="lookup.open && lookup.kind==='movement'" :placeholder="t('lookupHint')"
                @focus="scheduleLookup('movement',true)"
                @input="motion.item_code='';scheduleLookup('movement')"
                @keydown="lookupKeys($event,'movement')" />
              <span class="inv-lookup-mark" aria-hidden="true">⌕</span>
              <div v-if="lookup.open && lookup.kind==='movement'" id="inv-stock-matches" class="inv-lookup-options" role="listbox">
                <div class="inv-lookup-heading">{{ t('existing') }} <small>{{ t('lookupHint') }}</small></div>
                <button v-for="(match,n) in lookup.options" :key="match.item_code" type="button"
                  role="option" :aria-selected="lookup.index===n" :class="{selected:lookup.index===n}"
                  @mousedown.prevent @click.stop="selectLookup(match,'movement')">
                  <span class="inv-match-icon">▣</span>
                  <span class="inv-match-copy"><strong>{{ match.item_name }}</strong><small>{{ match.item_code }} · {{ match.item_group }}</small></span>
                </button>
                <p v-if="!lookup.options.length && !lookup.loading" class="inv-lookup-empty">{{ t('noMatch') }}</p>
                <p v-if="lookup.loading" class="inv-lookup-loading">{{ t('looking') }}</p>
              </div>
            </div>
            <small v-if="motion.item_code">{{ t('chosenProduct') }}: {{ motion.item_code }}</small>
          </div>
          <p v-if="selectedItem?.has_serial_no || selectedItem?.has_batch_no" class="inv-alert inv-error">{{ t('serial') }}</p>
          <label>{{ t('chooseWarehouse') }} *<select v-model="motion.warehouse" required><option value="">—</option><option v-for="w in inventory.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name||w.name }}</option></select></label>
          <div class="inv-modal-pair"><label>{{ t('qty') }} *<input v-model.number="motion.qty" type="number" min="0.001" step="0.001" required /></label><label v-if="movement==='receive'">{{ t('valuation') }} ({{ inventory.currency }}) *<input v-model.number="motion.basic_rate" type="number" min="0.01" step="0.01" required /></label></div>
          <p v-if="movement==='issue' && availableHere!==null" class="inv-helper">{{ t('stock') }}: {{ number(availableHere) }} {{ selectedItem?.stock_uom }}</p>
          <label>{{ t('notes') }}<textarea v-model="motion.remarks" rows="2" maxlength="1000"></textarea></label>
          <p class="inv-helper">{{ t('stockNote') }}</p>
          <p v-if="modalError" class="inv-alert inv-error" role="alert">{{ modalError }}</p>
          <div class="inv-modal-foot"><button type="button" class="inv-btn inv-outline" :disabled="busy" @click="close">{{ t('cancel') }}</button><button type="submit" class="inv-btn inv-primary" :disabled="busy || !!selectedItem?.has_serial_no || !!selectedItem?.has_batch_no">{{ busy?t('submitting'):t('submit') }}</button></div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.inv-root,.inv-root *{box-sizing:border-box}
.inv-root{--ink:#443429;--muted:#877869;--line:#e9ddcf;--cream:#fffdf9;--sand:#f5eee5;--espresso:#674a30;color:var(--ink);font-family:inherit;width:100%;min-width:0;padding:27px clamp(14px,2.3vw,34px) 44px;background:#faf7f2;min-height:calc(100vh - 70px)}
.inv-head{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:23px}.inv-eyebrow{font-size:10px;font-weight:800;letter-spacing:.12em;color:#977b59;text-transform:uppercase;display:flex;align-items:center;gap:8px}.inv-live-dot{width:8px;height:8px;border-radius:50%;background:#ba9568;display:inline-block}.inv-head h1{margin:7px 0 3px;font-size:clamp(24px,2.2vw,32px);font-weight:800;letter-spacing:-.035em;color:#392b21;line-height:1.25}.inv-head p{margin:0;color:var(--muted);font-size:13px}
.inv-actions,.inv-panel-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap}.inv-btn{appearance:none;border:1px solid #dbcbb7;background:#fffdf9;color:#705943;display:inline-flex;align-items:center;justify-content:center;gap:6px;border-radius:10px;padding:10px 14px;min-height:40px;white-space:nowrap;cursor:pointer;font-size:12px;font-weight:750}.inv-btn:hover:not(:disabled){background:#f4ebdf}.inv-btn:disabled,.inv-square:disabled,.inv-rowaction:disabled{opacity:.45;cursor:not-allowed}.inv-btn.inv-primary{background:#6e4e34;color:#fffaf2;border-color:#6e4e34}.inv-btn.inv-primary:hover:not(:disabled){background:#523824}.inv-btn.inv-small{padding:8px 11px;min-height:36px}.inv-btn:focus-visible,.inv-square:focus-visible,.inv-rowaction:focus-visible,.inv-view-switch button:focus-visible{outline:3px solid #c8a674;outline-offset:2px}
.inv-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:21px}.inv-stat{min-width:0;padding:17px 19px 18px;background:var(--cream);border:1px solid var(--line);border-radius:15px;box-shadow:0 4px 14px #6d513509}.inv-stat-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.inv-stat-symbol{height:38px;width:38px;display:grid;place-items:center;background:#f0e3d3;color:#77553b;font-weight:800;font-size:19px;border-radius:11px}.inv-stat-tag{font-size:9px;font-weight:800;color:#b5a594;letter-spacing:.09em}.inv-stat-number{font-weight:800;font-size:26px;line-height:1.2;color:#453226;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}.inv-stat-number.inv-amount{font-size:19px}.inv-stat>span{font-size:12px;color:#988676;display:block;margin-top:5px}
.inv-panel{background:#fffefb;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 5px 24px #8f75550b}.inv-panel-head{padding:19px 20px;display:flex;justify-content:space-between;gap:20px;align-items:center}.inv-panel-head h2,.inv-modal h2{font-size:17px;font-weight:800;color:#47362a;margin:0 0 5px;letter-spacing:-.025em}.inv-panel-head p{font-size:11px;color:#998c7d;margin:0}.inv-view-switch{display:flex;align-items:center;border:1px solid #e2d7c8;background:#f8f3ed;border-radius:9px;padding:3px}.inv-view-switch button{border:0;background:transparent;color:#836c57;padding:7px 10px;border-radius:7px;cursor:pointer;font-size:12px;font-weight:750}.inv-view-switch button.chosen{color:#fffaf4;background:#715138;box-shadow:0 2px 6px #52422a20}
.inv-toolbar{display:grid;grid-template-columns:minmax(185px,1.8fr) repeat(3,minmax(90px,1fr));gap:10px;padding:15px 20px;background:#fcf9f5;border-block:1px solid #eee5d9}.inv-toolbar select,.inv-search{height:41px;width:100%;border:1px solid #e5d9ca;border-radius:9px;background:white;color:#6b594a;padding:0 10px;min-width:0;font-size:12px;outline-color:#bfa17e}.inv-search{display:flex;align-items:center;gap:8px}.inv-search span{font-size:22px;color:#aa9075;line-height:1}.inv-search input{width:100%;min-width:0;border:0;outline:0;color:#48392f;background:transparent;font-size:12px}.inv-summary{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 20px;color:#9a8a7b;font-size:11px}.inv-sorters{display:flex;gap:13px;align-items:center}.inv-summary label{display:flex;align-items:center;gap:8px}.inv-summary input{width:57px;height:28px;border:1px solid #e5d8c8;border-radius:6px;padding:3px 5px;color:#65503d;background:#fff}.inv-sorters select{height:30px;border:1px solid #e5d8c8;border-radius:7px;padding:4px 8px;font-size:11px;background:#fff;color:#65503d}
.inv-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;padding:17px 19px 23px;background:#fffefa}.inv-card{min-width:0;border:1px solid #e8decf;border-radius:14px;background:#fffdf9;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 3px 15px #79613d0b;transition:transform .15s ease,box-shadow .15s ease}.inv-card:hover{transform:translateY(-2px);box-shadow:0 6px 19px #79613d1b}.inv-card-image{height:153px;background:linear-gradient(145deg,#f5eade,#ede0ce);position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.inv-card-image img{width:100%;height:100%;object-fit:contain;padding:12px}.inv-card-glyph{width:67px;height:67px;display:grid;place-items:center;background:#e2cfb8;border-radius:18px;color:#8b684b;font-weight:800;font-size:38px}.inv-image-chip{position:absolute;top:11px;right:11px;background:#fffdf9e9!important;backdrop-filter:blur(3px)}.inv-card-body{display:flex;flex-direction:column;flex:1;min-height:214px;padding:15px 15px 12px}.inv-card-category{font-size:10px;color:#a18d78;font-weight:650;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:5px}.inv-card h3{font-size:14px;line-height:1.35;color:#463225;min-height:38px;margin:0 0 3px;font-weight:800;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.inv-card-sku{font-size:10px;color:#aa9986;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:14px}.inv-price-duo{display:grid;grid-template-columns:1fr 1fr;gap:7px;background:#f8f1e8;padding:11px;border-radius:10px;margin-top:auto}.inv-price-duo>div{min-width:0}.inv-price-duo small{display:block;font-size:10px;color:#98816b;margin-bottom:4px}.inv-price-duo strong{display:block;font-size:12px;color:#654b34;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.inv-price-duo strong.inv-sellprice{color:#4c3522}.inv-card-meta{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:12px 0 10px;font-size:10px;color:#8f7967;white-space:nowrap}.inv-card-meta b{color:#5b4734;font-size:12px}.inv-card-foot{border-top:1px solid #eee4d9;padding-top:10px;display:flex;align-items:center;justify-content:space-between;gap:6px;color:#a08b79;font-size:10px}.inv-card-foot>span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.inv-card-foot>div{display:flex;gap:5px;flex-shrink:0}.inv-square{height:29px;width:29px;border-radius:8px;border:1px solid #e5d7c6;background:#fffaf4;color:#76553b;font-size:17px;font-weight:700;cursor:pointer}.inv-square:hover:not(:disabled){background:#eeddc5}
.inv-table-wrap{overflow-x:auto}.inv-table{width:100%;border-collapse:collapse;min-width:1080px;text-align:left}.inv-table thead{background:#f8f1e8}.inv-table th{padding:13px 11px;font-size:10px;text-transform:uppercase;letter-spacing:.03em;color:#8d7660;font-weight:800;white-space:nowrap}.inv-table td{padding:13px 11px;border-top:1px solid #f0e9df;vertical-align:middle;font-size:12px;color:#645347;max-width:245px}.inv-table tbody tr:hover{background:#fffcf8}.inv-product{display:flex;align-items:center;gap:9px;min-width:155px}.inv-thumb{height:39px;width:39px;border-radius:10px;display:grid;place-items:center;background:#f1e5d7;color:#936c47;font-size:17px;font-weight:800;flex:0 0 39px;overflow:hidden}.inv-thumb img{width:100%;height:100%;object-fit:contain}.inv-itemname{display:flex;flex-direction:column;gap:3px;min-width:0}.inv-itemname strong{font-size:12px;color:#443429;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:205px}.inv-itemname small{font-size:10px;color:#a3907d}.inv-right{text-align:right!important;font-variant-numeric:tabular-nums}.inv-code{font-size:11px!important;color:#846d59!important}.inv-muted{color:#938273!important}.inv-money{font-size:11px!important;white-space:nowrap}.inv-chip{display:inline-flex;align-items:center;border:1px solid #e5dbcc;border-radius:999px;background:#f6f0e8;color:#876c51;padding:5px 8px;font-size:10px;font-weight:750;white-space:nowrap}.inv-chip.inv-low{background:#fff2de;border-color:#f0dcba;color:#a16c2f}.inv-chip.inv-out{background:#f5e7e5;border-color:#ebd4cd;color:#9a584c}.inv-rowaction{height:29px;width:29px;margin-right:4px;border-radius:8px;border:1px solid #e4d9cb;background:#fffcf8;color:#815e41;font-size:15px;cursor:pointer}.inv-empty{text-align:center;padding:55px 20px;color:#a19283;font-size:13px}.inv-more{text-align:center;border-top:1px solid #eee6dc;padding:16px}.inv-alert{margin:0 0 14px;padding:12px 15px;border:1px solid #e6d8c3;background:#fff8ec;color:#7e6041;border-radius:10px;font-size:12px}.inv-error{background:#fff0ea;border-color:#edd3c7;color:#9c493d}.inv-success{background:#f2eee7;border-color:#ded0bc;color:#68523a}.inv-alert button{margin-left:10px;cursor:pointer;border:none;text-decoration:underline;color:inherit;background:none;font-weight:750}
.inv-modal-backdrop{position:fixed;inset:0;z-index:10000;background:#24190f91;display:flex;align-items:center;justify-content:center;padding:15px}.inv-modal{width:min(520px,100%);max-height:calc(100vh - 30px);max-height:calc(100dvh - 30px);overflow:auto;background:#fffdf9;border-radius:18px;border:1px solid #e4d5c1;box-shadow:0 18px 65px #1e130e43}.inv-modal.inv-product-modal{width:min(730px,100%)}.inv-modal-header{padding:21px 24px 16px;display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid #eee3d6}.inv-modal-header h2{font-size:21px;margin:7px 0}.inv-close{width:33px;height:33px;display:grid;place-items:center;border:1px solid #e8dac9;border-radius:9px;background:#fff8f1;font-size:22px;color:#886b52;cursor:pointer}.inv-modal-form{padding:19px 24px 24px;display:flex;flex-direction:column;gap:13px}.inv-modal-form label{display:flex;flex-direction:column;gap:6px;font-size:11px;color:#69513e;font-weight:750;min-width:0}.inv-modal-form input,.inv-modal-form select,.inv-modal-form textarea{font-family:inherit;width:100%;min-width:0;border:1px solid #e1d2bf;background:#fff;border-radius:9px;color:#4c382a;font-size:13px;padding:10px 11px;outline-color:#bb9b74}.inv-modal-form input:disabled,.inv-modal-form select:disabled,.inv-modal-form textarea:disabled{background:#f6f2ed;color:#a39487;cursor:not-allowed}.inv-modal-form input[type=file]{padding:9px 7px;background:#f9f3eb}.inv-modal-form label small{font-size:10px;color:#a3917e;line-height:1.5;font-weight:450}.inv-modal-pair,.inv-form-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}.inv-form-divider{margin:4px 0 0;border-top:1px dashed #e5d6c4;padding-top:13px;font-size:10px;font-weight:700;color:#92765b}.inv-helper{color:#927c69;font-size:11px;line-height:1.5;margin:0}.inv-modal-foot{display:flex;justify-content:flex-end;gap:9px;margin-top:5px}
@media(max-width:1460px){.inv-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:1120px){.inv-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.inv-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.inv-toolbar{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:680px){.inv-root{padding:16px 12px 35px}.inv-head{flex-direction:column;align-items:flex-start;gap:13px}.inv-actions{justify-content:flex-start}.inv-metrics{gap:9px}.inv-stat{padding:14px 13px}.inv-stat-number{font-size:22px}.inv-stat-number.inv-amount{font-size:16px}.inv-panel-head{padding:15px;align-items:flex-start;flex-direction:column}.inv-panel-actions{justify-content:flex-start;width:100%}.inv-toolbar{padding:12px;grid-template-columns:minmax(0,1fr)}.inv-summary{padding:10px 12px;flex-wrap:wrap}.inv-sorters{flex-wrap:wrap}.inv-grid{grid-template-columns:1fr;padding:12px;gap:12px}.inv-card-image{height:175px}.inv-modal-form{padding:17px}.inv-modal-header{padding:17px}.inv-modal-pair,.inv-form-grid{grid-template-columns:1fr}.inv-btn{padding:10px 11px}}
@media(prefers-reduced-motion:reduce){.inv-card{transition:none}}

/* V4 — balanced inputs and native selects, consistent at every breakpoint. */
.inv-root{--field-h:44px;padding-bottom:120px}
.inv-modal-form .inv-form-grid{align-items:start;column-gap:16px;row-gap:14px}
.inv-modal-form label{gap:7px;line-height:1.35;font-size:12px;font-weight:750}
.inv-modal-form label>input:not([type=file]),.inv-modal-form label>select,
.inv-modal-form .inv-lookup-shell>input,.inv-toolbar select,.inv-toolbar .inv-search{
  height:var(--field-h)!important;min-height:var(--field-h);width:100%;line-height:22px;
  font-size:13px;color:#483729;background-color:#fffdfa;border:1px solid #dccab5;
  border-radius:11px;padding:10px 13px;box-shadow:0 1px 2px #3c25170a;
}
.inv-modal-form input::placeholder,.inv-toolbar input::placeholder{color:#a89784;opacity:1}
.inv-modal-form label>select,.inv-toolbar select,.inv-sorters select{
  -webkit-appearance:none;appearance:none;padding-right:38px;cursor:pointer;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%238a6b4e' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center;background-size:17px 17px
}
.inv-modal-form label>input:focus-visible,.inv-modal-form label>select:focus-visible,
.inv-modal-form .inv-lookup-shell>input:focus-visible,.inv-toolbar select:focus-visible,
.inv-toolbar .inv-search:focus-within,.inv-sorters select:focus-visible{
  outline:none;border-color:#af8a5c;box-shadow:0 0 0 3px #b4936d32;
}
.inv-modal-form label>select:disabled{background-color:#f8f3ed;color:#a09386}
.inv-modal-form textarea{min-height:84px;resize:vertical}
.inv-modal-form .inv-lookup-field{min-width:0;display:flex;flex-direction:column;gap:7px}.inv-modal-form .inv-lookup-field>label{font-size:12px;min-height:17px}.inv-modal-form .inv-lookup-field>small{font-size:10px;color:#a3917e;line-height:1.5;font-weight:450}
.inv-lookup-shell{position:relative;display:block;min-width:0;width:100%}
.inv-lookup-shell>input{padding-right:38px!important}
.inv-lookup-mark{position:absolute;right:13px;top:50%;transform:translateY(-50%);font-size:22px;line-height:1;color:#a28b73;pointer-events:none}
.inv-lookup-options{position:absolute;top:calc(100% + 6px);left:0;right:0;max-height:295px;overflow-y:auto;
  z-index:120;background:#fffefa;border:1px solid #decbb6;border-radius:12px;box-shadow:0 14px 34px #3927162b;padding:5px;overscroll-behavior:contain}
.inv-lookup-heading{padding:10px 11px 8px;font-weight:800;color:#634a34;font-size:12px;display:flex;flex-direction:column;gap:2px}
.inv-lookup-heading small{font-size:10px;font-weight:500;color:#a08b76}
.inv-lookup-options button{width:100%;display:flex;align-items:center;gap:10px;padding:10px;text-align:left;cursor:pointer;
  border:0;background:transparent;color:#46362c;border-radius:9px;font-family:inherit}
.inv-lookup-options button:hover,.inv-lookup-options button.selected{background:#f4e8d7}
.inv-match-icon{display:grid;place-items:center;flex:0 0 35px;height:35px;border-radius:9px;background:#efe1ce;color:#886341;font-size:17px}
.inv-match-copy{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}
.inv-match-copy strong{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px;font-weight:750}
.inv-match-copy small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#97806b;font-size:10px;font-weight:450}
.inv-match-action{font-size:10px;color:#846244;white-space:nowrap}
.inv-lookup-empty,.inv-lookup-loading{margin:0;padding:13px;color:#9f8974;font-size:11px;font-weight:500}
/* High-contrast floating quick actions with safe-area spacing, never above a modal */
.inv-floating-actions{position:fixed;bottom:calc(22px + env(safe-area-inset-bottom,0px));right:24px;
  display:flex;flex-direction:column;align-items:stretch;gap:10px;z-index:45;max-width:calc(100vw - 28px)}
.inv-fab{min-width:156px;display:flex;align-items:center;gap:10px;min-height:50px;padding:8px 18px 8px 10px;
  border-radius:16px;cursor:pointer;box-shadow:0 7px 21px #4f392a34;font-weight:800;font-size:13px;
  border:1px solid #6e503a;white-space:nowrap;transition:transform .15s ease,box-shadow .15s ease}
.inv-fab:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 10px 26px #4f392a42}
.inv-fab:focus-visible{outline:3px solid #ba9359;outline-offset:3px}
.inv-fab:disabled{opacity:.45;cursor:not-allowed}
.inv-fab-icon{height:35px;width:35px;display:grid;place-items:center;font-size:23px;font-weight:750;border-radius:11px;flex:0 0 35px}
.inv-fab-add{background:#6b4b31;color:#fffaf4}.inv-fab-add .inv-fab-icon{background:#ffffff22}
.inv-fab-restock{background:#fffaf3;color:#6b4b31;border-color:#d9bf9f}.inv-fab-restock .inv-fab-icon{background:#eee0ce;color:#805f41}
@media(max-width:680px){.inv-floating-actions{right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px));gap:8px}
.inv-fab{min-width:138px;min-height:47px;padding:7px 12px 7px 8px;font-size:12px;border-radius:13px}
.inv-fab-icon{width:33px;height:33px;flex-basis:33px}.inv-lookup-options{max-height:210px}.inv-match-action{display:none}}
@media(prefers-reduced-motion:reduce){.inv-fab{transition:none}}
</style>
