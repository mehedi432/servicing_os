<script setup>
import { computed, ref, watch, onMounted, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import RetailSales from './RetailSales.vue'
import RetailSalesHistory from './RetailSalesHistory.vue'

const props = defineProps({ section: { type: String, default: 'New Sale' } })
const labels = {
  'New Sale': ['New Sale / POS', 'নতুন বিক্রয় / পিওএস'],
  'Sales History': ['Sales History', 'বিক্রয় ইতিহাস'],
  'Quotations': ['Quotations', 'মূল্য প্রস্তাব'],
  'Returns & Exchanges': ['Returns & Exchanges', 'ফেরত ও পরিবর্তন'],
  'Payments & Dues': ['Payments & Dues', 'পেমেন্ট ও বকেয়া'],
  'Sales Warranty': ['Sales Warranty', 'বিক্রয় ওয়ারেন্টি'],
  'Sales Reports': ['Sales Reports', 'বিক্রয় প্রতিবেদন']
}
const bdt = (number) => '৳ ' + (Number(number) || 0).toLocaleString('en-BD', {minimumFractionDigits: 2, maximumFractionDigits: 2})
const bn = computed(() => unref(currentLanguage) === 'bn')
const selectedTitle = computed(() => (labels[props.section] || labels['New Sale'])[bn.value ? 1 : 0])
const status = ref(''), error = ref(''), busy = ref(false), config = ref(null)
const search = ref(''), rows = ref([]), selected = ref(null), lines = ref([])
const customerQuery = ref(''), customerOptions = ref([]), customer = ref('')
const itemQuery = ref(''), productOptions = ref([]), quoteLines = ref([])
const expiry = ref(''), paymentAmount = ref(''), paymentMode = ref('Cash')
const paymentReference = ref(''), returnName = ref(''), warrantyDays = ref({}), returnQuantities = ref({})
const today = () => new Date().toLocaleDateString('en-CA')
const reportFrom = ref(''), reportTo = ref(''), stats = ref(null)
const kinds = {'Sales History':'invoice', 'Quotations':'quotation', 'Returns & Exchanges':'invoice', 'Payments & Dues':'invoice', 'Sales Warranty':'invoice'}

async function call(method, args = {}, write = false) {
  const url = '/api/method/servicing_os.api.sales_center.' + method
  const csrf = window.csrf_token || window.frappe?.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
  const query = new URLSearchParams()
  if (!write) for (const [k,v] of Object.entries(args)) query.set(k, v ?? '')
  const response = await fetch(url + (write ? '' : '?' + query.toString()), {
    method: write ? 'POST' : 'GET', credentials:'same-origin',
    headers: write ? {'Content-Type':'application/json', 'X-Frappe-CSRF-Token':csrf} : {},
    body: write ? JSON.stringify(args) : undefined
  })
  let body
  try { body = await response.json() } catch { throw new Error('Server returned an invalid response. Check login and server logs.') }
  if (!response.ok || body.exc || body.exception) {
    const messages = body._server_messages
    let message = body.message && typeof body.message === 'string' ? body.message : ''
    if (messages) { try { message = JSON.parse(JSON.parse(messages)[0]).message || message } catch {} }
    throw new Error(message || body.exception || `Request failed (${response.status})`)
  }
  return body.message
}
async function run(fn) {
  if (busy.value) return
  busy.value = true; status.value = ''; error.value = ''
  try { await fn() } catch(e) { error.value = e.message || String(e) } finally { busy.value = false }
}
async function init() {
  await run(async () => { config.value = await call('configuration') })
  await refresh()
}
function resetView() { rows.value=[]; selected.value=null; lines.value=[]; status.value=''; error.value=''; search.value='' }
watch(() => props.section, async () => { resetView(); await refresh() })
async function refresh() {
  if (props.section === 'New Sale' || props.section === 'Sales History') return
  if (props.section === 'Sales Reports') { await loadStats(); return }
  await run(async () => { rows.value = await call('records', {kind: kinds[props.section] || 'invoice',query:search.value,limit:80}) })
}
async function loadDetail(name) {
  await run(async () => {
    selected.value = await call('invoice_detail', {name})
    warrantyDays.value = Object.fromEntries(selected.value.items.map(item=>[item.name,item.warranty_days || 0]))
    returnQuantities.value = Object.fromEntries(selected.value.items.map(item=>[item.name,Math.abs(Number(item.qty || 0))]))
  })
}
async function lookupCustomer() {
  if (customerQuery.value.trim().length < 2) { customerOptions.value=[]; return }
  await run(async()=>{ customerOptions.value=await call('customers',{q:customerQuery.value}) })
}
async function lookupProduct() {
  if (itemQuery.value.trim().length < 2) { productOptions.value=[]; return }
  await run(async()=>{ productOptions.value=await call('catalog',{q:itemQuery.value}) })
}
function addProduct(item) {
  const existing = quoteLines.value.find(x=>x.item_code===item.item_code)
  if (existing) existing.qty++
  else quoteLines.value.push({item_code:item.item_code,item_name:item.item_name,rate:item.rate,qty:1, serialized:item.serialized})
  itemQuery.value=''; productOptions.value=[]
}
async function createQuote() {
  await run(async()=>{
    if (!customer.value || !quoteLines.value.length) throw new Error('Select a customer and add products.')
    const result = await call('create_quotation',{customer:customer.value,items:quoteLines.value.map(x=>({item_code:x.item_code,qty:Number(x.qty)})),valid_till:expiry.value||undefined},true)
    status.value=`Quotation ${result.name} saved as Draft.`; customer.value=''; customerQuery.value=''; quoteLines.value=[]
    rows.value=await call('records',{kind:'quotation'})
  })
}
async function submitQuote(name) {
  if (!window.confirm('Submit this quotation? Submitted quotations become formal offers.')) return
  await run(async()=>{const result=await call('submit_quotation',{name},true);status.value=`Quotation ${result.name} submitted.`;rows.value=await call('records',{kind:'quotation'})})
}
async function createReturn(invoice) {
  if (!window.confirm(`Create an ERPNext return draft for invoice ${invoice} with the selected quantities? Review serial numbers and payment implications before submission.`)) return
  await run(async()=>{
    const result=await call('create_return_draft',{invoice, quantities:returnQuantities.value},true)
    returnName.value=result.name
    status.value=`Created return draft ${result.name}. Review all returned items and payment rows before submission.`
    selected.value=await call('invoice_detail',{name:result.name})
    rows.value=await call('records',{kind:'invoice'})
  })
}
async function submitReturn() {
  if (!returnName.value) throw new Error('Enter a return draft name.')
  if (!window.confirm(`FINAL CONFIRMATION: Submit return ${returnName.value}? This affects stock and accounting and may book a POS payment refund. Verify returned goods, serial numbers, payment rows and the actual refund handling before continuing.`)) return
  await run(async()=>{const r=await call('submit_return',{name:returnName.value},true);status.value=`Credit note ${r.name} submitted. Verify payment/refund and reconciliation in ERPNext.`;returnName.value='';await refresh()})
}
async function receivePayment() {
  if (!selected.value) return
  if (!window.confirm(`Record ${bdt(paymentAmount.value)} received for ${selected.value.name} via ${paymentMode.value}?`)) return
  await run(async()=>{
    const result=await call('receive_payment',{invoice:selected.value.name,amount:Number(paymentAmount.value),mode_of_payment:paymentMode.value,reference_no:paymentReference.value},true)
    status.value=`Payment ${result.name} submitted.`;paymentAmount.value='';paymentReference.value=''
    const name=selected.value.name;selected.value=await call('invoice_detail',{name});await refresh()
  })
}
async function saveWarranty(row) {
  await run(async()=>{
    const result=await call('set_warranty',{invoice:selected.value.name,item_row:row.name,days:Number(warrantyDays.value[row.name])},true)
    status.value=`Warranty updated: ${result.days} days, expiry ${result.expiry || 'none'}.`
    selected.value=await call('invoice_detail',{name:selected.value.name})
  })
}
async function loadStats() {
  await run(async()=>{stats.value=await call('statistics',{from_date:reportFrom.value,to_date:reportTo.value})})
}
function printDoc(kind,name) {
  const doctype=kind==='quotation'?'Quotation':'Sales Invoice'
  const url='/printview?doctype='+encodeURIComponent(doctype)+'&name='+encodeURIComponent(name)+'&trigger_print=1'
  window.open(url,'_blank','noopener,noreferrer')
}
onMounted(()=>{init()})
</script>

<template>
  <section class="sosc-sales" :aria-label="selectedTitle">
    <div class="sosc-heading">
      <div><p class="sosc-eyebrow">AL MODINA COMPUTERS LIMITED · SALES</p><h1>{{selectedTitle}}</h1>
        <p class="sosc-sub">{{bn ? 'ERPNext-এর আসল হিসাব ও স্টক রেকর্ডের সাথে সংযুক্ত' : 'Connected to real ERPNext inventory and accounts'}}</p></div>
      <div class="sosc-head-actions"><button v-if="section!=='New Sale'&&section!=='Sales History'" class="sosc-button" type="button" :disabled="busy" @click="refresh">↻ {{bn?'রিফ্রেশ':'Refresh'}}</button></div>
    </div>
    <p v-if="error" class="sosc-alert error" role="alert">{{error}}</p>
    <p v-if="status" class="sosc-alert ok" role="status">{{status}}</p>
    <p v-if="busy" class="sosc-hint">{{bn?'লোড হচ্ছে...':'Loading live data…'}}</p>
    <div v-if="!config && section!=='New Sale'" class="sosc-panel">{{bn?'ব্যাকএন্ড সংযোগ পরীক্ষা করুন':'Check backend connection and required ERPNext permissions.'}}</div>

    <RetailSales v-if="section==='New Sale'" />
    <RetailSalesHistory v-else-if="section==='Sales History'" />

    <template v-else-if="section==='Quotations'">
      <div class="sosc-panel">
        <h2>{{bn?'নতুন কোটেশন':'Create quotation'}}</h2>
        <div class="sosc-formgrid"><label>{{bn?'ক্রেতা খুঁজুন':'Find customer'}}<input v-model="customerQuery" placeholder="Name / Customer ID" @input="customer=''" @keyup.enter="lookupCustomer"/></label>
        <div class="sosc-inline"><button class="sosc-button" :disabled="busy" @click="lookupCustomer">{{bn?'খুঁজুন':'Search'}}</button><span v-if="customer">✓ {{customer}}</span></div></div>
        <div class="sosc-options" v-if="customerOptions.length"><button v-for="c in customerOptions" :key="c.name" class="sosc-result" @click="customer=c.name;customerQuery=c.customer_name;customerOptions=[]">{{c.customer_name}} <small>{{c.name}}</small></button></div>
        <div class="sosc-formgrid"><label>{{bn?'পণ্য খুঁজুন':'Find product'}}<input v-model="itemQuery" placeholder="Item code / name" @keyup.enter="lookupProduct" /></label><div class="sosc-inline"><button class="sosc-button" :disabled="busy" @click="lookupProduct">{{bn?'খুঁজুন':'Search'}}</button></div></div>
        <div class="sosc-options" v-if="productOptions.length"><button v-for="p in productOptions" :key="p.item_code" class="sosc-result" @click="addProduct(p)">{{p.item_name}} <small>{{p.item_code}} · {{bdt(p.rate)}} · Stock {{p.stock_qty}}</small></button></div>
        <div class="sosc-table-scroll" v-if="quoteLines.length"><table><thead><tr><th>Product</th><th>Quantity</th><th>List price</th><th>Amount</th><th></th></tr></thead>
        <tbody><tr v-for="(p,i) in quoteLines" :key="p.item_code"><td>{{p.item_name}}<small>{{p.item_code}}</small></td><td><input type="number" min="1" step="1" v-model.number="p.qty"/></td><td>{{bdt(p.rate)}}</td><td>{{bdt(p.rate*p.qty)}}</td><td><button class="sosc-link" @click="quoteLines.splice(i,1)">Remove</button></td></tr></tbody></table></div>
        <div class="sosc-bottom"><label>Valid until<input type="date" v-model="expiry"/></label><strong>{{bdt(quoteLines.reduce((s,p)=>s+p.qty*p.rate,0))}}</strong><button class="sosc-primary" :disabled="busy||!customer||!quoteLines.length" @click="createQuote">{{bn?'ড্রাফট কোটেশন সংরক্ষণ':'Save quotation draft'}}</button></div>
      </div>
      <div class="sosc-panel"><h2>{{bn?'কোটেশন তালিকা':'Quotation register'}}</h2><div class="sosc-formgrid"><input v-model="search" placeholder="Search quotation number" @keyup.enter="refresh"/><button class="sosc-button" @click="refresh">Search</button></div>
        <div class="sosc-table-scroll"><table><thead><tr><th>Quotation</th><th>Date</th><th>Customer</th><th>Status</th><th>Total</th><th>Actions</th></tr></thead><tbody>
          <tr v-for="r in rows" :key="r.name"><td>{{r.name}}</td><td>{{r.transaction_date}}</td><td>{{r.party_name}}</td><td>{{r.status}}</td><td>{{bdt(r.grand_total)}}</td><td><button class="sosc-link" @click="printDoc('quotation',r.name)">Print</button> <button v-if="r.docstatus===0" class="sosc-link" @click="submitQuote(r.name)">Submit</button></td></tr>
        </tbody></table></div></div>
    </template>

    <template v-else-if="section==='Returns & Exchanges'">
      <div class="sosc-panel"><h2>{{bn?'মূল বিক্রয় খুঁজুন':'Return against original invoice'}}</h2><p class="sosc-hint">{{bn?'প্রথমে মূল ইনভয়েস নির্বাচন করুন। পূর্ণ রিটার্নের ড্রাফট তৈরি হবে।':'Choose a submitted sale. A full-return draft is prepared using ERPNext’s native return mapping. Nothing is refunded automatically.'}}</p>
        <div class="sosc-formgrid"><input v-model="search" placeholder="Invoice number" @keyup.enter="refresh"/><button class="sosc-button" @click="refresh">Search</button></div>
        <div class="sosc-table-scroll"><table><thead><tr><th>Invoice</th><th>Customer</th><th>Total</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="r in rows.filter(r=>!r.is_return)" :key="r.name"><td>{{r.name}}</td><td>{{r.customer_name}}</td><td>{{bdt(r.grand_total)}}</td><td>{{r.status}}</td><td><button class="sosc-link" :disabled="r.docstatus!==1||busy" @click="loadDetail(r.name)">Select items</button></td></tr></tbody></table></div>
      </div>
      <div class="sosc-panel" v-if="selected && !selected.is_return">
        <h2>{{selected.name}} · Select quantities to return</h2>
        <p class="sosc-hint">Only the original invoiced quantities can be credited. Serialized products must be returned in full in this quick workflow.</p>
        <div class="sosc-table-scroll"><table><thead><tr><th>Product</th><th>Original qty</th><th>Return qty</th><th>Serial number</th></tr></thead><tbody>
          <tr v-for="p in selected.items" :key="p.name"><td>{{p.item_name}}<small>{{p.item_code}}</small></td><td>{{p.qty}}</td><td><input type="number" min="0" :max="Math.abs(p.qty)" step="1" v-model.number="returnQuantities[p.name]" /></td><td>{{p.serial_no||'—'}}</td></tr>
        </tbody></table></div>
        <button class="sosc-primary" :disabled="busy" @click="createReturn(selected.name)">Create ERPNext return draft</button>
      </div>
      <div class="sosc-panel" v-if="selected && selected.is_return"><h2>Credit note draft · {{selected.name}}</h2>
        <p class="sosc-hint">Original: {{selected.return_against}} · Total credit: {{bdt(selected.grand_total)}} · Status {{selected.status}}</p>
        <div class="sosc-table-scroll"><table><thead><tr><th>Product</th><th>Quantity</th><th>Serial no.</th></tr></thead><tbody><tr v-for="p in selected.items" :key="p.name"><td>{{p.item_name}}</td><td>{{p.qty}}</td><td>{{p.serial_no||'—'}}</td></tr></tbody></table></div>
        <p class="sosc-hint" v-for="p in selected.payments" :key="p.mode">POS payment/refund row: {{p.mode}} · {{bdt(p.amount)}}</p>
      </div>
      <div class="sosc-panel"><h2>Submit inspected return</h2><p class="sosc-hint">Before submitting, confirm original invoice, all quantities, serial numbers and goods physically received. For partial serial-number returns, use a qualified serial-specific workflow.</p><div class="sosc-formgrid"><input v-model="returnName" placeholder="Return draft number"/><button class="sosc-primary" :disabled="!returnName||busy" @click="submitReturn">Submit full credit note</button></div><p class="sosc-hint">Exchange = credit note for returned goods + a separate new sale. Refunds must be reconciled separately.</p></div>
    </template>

    <template v-else-if="section==='Payments & Dues'||section==='Sales Warranty'">
      <div class="sosc-panel"><h2>{{section==='Sales Warranty'?'Find invoice to manage item warranty':'Find unpaid customer invoices'}}</h2>
      <div class="sosc-formgrid"><input v-model="search" placeholder="Search invoice number" @keyup.enter="refresh"/><button class="sosc-button" :disabled="busy" @click="refresh">Search</button></div>
      <div class="sosc-table-scroll"><table><thead><tr><th>Invoice</th><th>Customer</th><th>Invoice total</th><th>Outstanding</th><th></th></tr></thead><tbody><tr v-for="r in rows.filter(r=>r.docstatus===1&&!r.is_return&&(section==='Sales Warranty'||Number(r.outstanding_amount)>0))" :key="r.name"><td>{{r.name}}</td><td>{{r.customer_name}}</td><td>{{bdt(r.grand_total)}}</td><td>{{bdt(r.outstanding_amount)}}</td><td><button class="sosc-link" @click="loadDetail(r.name)">{{section==='Sales Warranty'?'Warranty':'Collect'}}</button></td></tr></tbody></table></div></div>
      <div class="sosc-panel" v-if="selected"><h2>{{selected.name}} · {{selected.customer_name}}</h2>
        <template v-if="section==='Payments & Dues'"><p class="sosc-hint">Outstanding: <b>{{bdt(selected.outstanding_amount)}}</b>. Payment is recorded through a submitted ERPNext Payment Entry.</p>
          <div class="sosc-formgrid"><label>Received amount (BDT)<input type="number" min="0.01" :max="selected.outstanding_amount" step="0.01" v-model="paymentAmount"/></label><label>Payment mode<select v-model="paymentMode"><option v-for="m in (config?.modes||[])" :key="m">{{m}}</option></select></label><label>Bank / mobile transaction reference<input v-model="paymentReference" placeholder="For non-cash modes"/></label><button class="sosc-primary" :disabled="busy||!paymentAmount||!paymentMode" @click="receivePayment">Confirm received payment</button></div>
        </template>
        <div v-else class="sosc-table-scroll"><table><thead><tr><th>Item</th><th>Serial no.</th><th>Warranty days</th><th>Expiry</th><th></th></tr></thead><tbody>
          <tr v-for="p in selected.items" :key="p.name"><td>{{p.item_name}}<small>{{p.item_code}}</small></td><td>{{p.serial_no||'—'}}</td><td><input type="number" min="0" max="3650" v-model.number="warrantyDays[p.name]"/></td><td>{{p.warranty_expiry||'—'}}</td><td><button class="sosc-link" :disabled="busy" @click="saveWarranty(p)">Save warranty</button></td></tr>
        </tbody></table><p class="sosc-hint">Enter 0 for no warranty. Manually entered days are added to the original invoice date. Warranty metadata does not modify accounting.</p></div>
      </div>
    </template>

    <template v-else-if="section==='Sales Reports'">
      <div class="sosc-panel"><h2>{{bn?'বিক্রয় পরিসংখ্যান':'Actual sales summary'}}</h2><div class="sosc-formgrid"><label>From<input type="date" v-model="reportFrom"/></label><label>To<input type="date" v-model="reportTo"/></label><button class="sosc-primary" :disabled="busy" @click="loadStats">Run report</button></div>
      <div class="sosc-metrics" v-if="stats"><div><span>Invoices</span><b>{{stats.invoice_count}}</b></div><div><span>Gross sales</span><b>{{bdt(stats.sales)}}</b></div><div><span>Returns</span><b>{{bdt(stats.returns)}}</b></div><div><span>Net sales</span><b>{{bdt(stats.net_sales)}}</b></div><div><span>Outstanding</span><b>{{bdt(stats.outstanding)}}</b></div><div v-if="stats.collections_visible"><span>Customer collections</span><b>{{bdt(stats.collections)}}</b></div></div>
      <p class="sosc-hint" v-if="stats">{{stats.from_date}} to {{stats.to_date}}. {{stats.limited?'WARNING: More than 5,000 invoices — this summary is incomplete. Narrow the date range.':'Based on submitted ERPNext Sales Invoices and Credit Notes.'}}</p></div>
    </template>
  </section>
</template>

<style scoped>
.sosc-sales{--bd:#e8dbca;--ink:#463829;--muted:#8f7a66;color:var(--ink);font-family:inherit;padding:22px clamp(12px,2.4vw,34px) 46px;min-width:0;background:#faf7f1;min-height:80vh}
.sosc-heading{display:flex;align-items:start;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:19px}
.sosc-eyebrow{font-weight:800;font-size:10px;letter-spacing:.13em;color:#9a7c59;margin:0 0 7px}
.sosc-heading h1{font-size:clamp(21px,2.3vw,29px);font-weight:800;margin:0;line-height:1.2;letter-spacing:-.025em}
.sosc-sub,.sosc-hint{font-size:12px;color:var(--muted);line-height:1.6}.sosc-sub{margin:8px 0 0}.sosc-hint{margin:9px 0 14px}
.sosc-head-actions,.sosc-inline,.sosc-formgrid,.sosc-bottom{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.sosc-formgrid{margin:13px 0}
.sosc-panel{background:#fffdfa;border:1px solid var(--bd);border-radius:16px;box-shadow:0 6px 25px #5c48320a;padding:18px 20px;margin:13px 0 17px}
.sosc-panel h2{font-weight:800;font-size:16px;margin:0 0 10px}
.sosc-panel input,.sosc-panel select{border:1px solid #ded1bf;background:white;border-radius:9px;min-height:41px;padding:9px 11px;font-size:13px;color:#4a3827;max-width:100%;min-width:0}
.sosc-formgrid>input,.sosc-formgrid>label{flex:1 1 230px}.sosc-panel label{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:700;color:#77614a}
.sosc-button,.sosc-primary,.sosc-link,.sosc-result{cursor:pointer;font-family:inherit}
.sosc-button,.sosc-primary{min-height:40px;padding:9px 15px;border-radius:9px;border:1px solid #dac8ae;font-size:12px;font-weight:800;white-space:nowrap;background:#f5ecdf;color:#72533a}
.sosc-primary{background:#715138;color:white;border-color:#715138}.sosc-button:hover{background:#eaddc9}.sosc-primary:hover{background:#573b27}
.sosc-button:disabled,.sosc-primary:disabled,.sosc-link:disabled{opacity:.45;cursor:not-allowed}
.sosc-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:7px;max-height:180px;overflow:auto;margin:6px 0 15px}
.sosc-result{background:#f8f1e8;border:1px solid #eddfcd;border-radius:9px;text-align:left;padding:10px;color:#54412f;font-size:13px}
.sosc-result:hover{background:#f0e0ca}.sosc-result small,.sosc-table-scroll small{display:block;color:#9c8a76;font-size:11px;margin-top:3px}
.sosc-table-scroll{width:100%;overflow:auto;margin-top:10px}.sosc-table-scroll table{width:100%;border-collapse:collapse;font-size:12px;text-align:left;min-width:510px}
.sosc-table-scroll th{background:#f7f0e7;color:#81674c;font-weight:800;border-bottom:1px solid var(--bd);padding:11px 10px}
.sosc-table-scroll td{padding:11px 10px;border-bottom:1px solid #f0e8dd;vertical-align:middle}
.sosc-table-scroll input{width:100px;min-height:35px}.sosc-link{border:none;background:transparent;color:#855e39;font-size:12px;font-weight:800;text-decoration:underline;text-underline-offset:3px;margin-right:8px}
.sosc-bottom{justify-content:flex-end;margin:14px 0 0}.sosc-bottom strong{margin:auto 12px auto 0;font-size:18px}
.sosc-alert{border-radius:10px;padding:12px 15px;font-size:13px;margin-bottom:10px}.sosc-alert.error{border:1px solid #e0b3a8;background:#fff0ec;color:#8f3527}.sosc-alert.ok{border:1px solid #d5c7a7;background:#fff8e6;color:#69552b}
.sosc-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:20px 0}
.sosc-metrics>div{padding:14px;border:1px solid #ebdbc7;border-radius:12px;background:#fcf7ef;display:flex;flex-direction:column;gap:6px}
.sosc-metrics span{font-size:11px;color:#91765c}.sosc-metrics b{font-size:20px;white-space:nowrap}
@media(max-width:700px){.sosc-panel{padding:13px}.sosc-sales{padding:15px 10px}.sosc-heading{margin-bottom:10px}}
</style>
