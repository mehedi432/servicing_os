<script setup>
import SalesInvoiceStudio from "./SalesInvoiceStudio.vue";

// SERVICING_RETAIL_HISTORY_620D
import { ref, onMounted } from 'vue'
const props = defineProps({ posProfile: { type: String, default: '' } })
const today = new Date()
function dateString(d) { return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-') }
const ago = new Date(today.getFullYear(), today.getMonth(), today.getDate()-30)
const from = ref(dateString(ago))
const to = ref(dateString(today))
const query = ref('')
const cashier = ref('')
const docType = ref('all')
const data = ref(null)
const busy = ref(false)
const error = ref('')
const selected = ref(null)
const printSelection = ref(null)
const printBusy = ref(false)
const detailsBusy = ref(false)
const detailsError = ref('')

async function api(method, params) {
  const url = new URL('/api/method/servicing_os.api.retail_history.' + method, window.location.origin)
  Object.entries(params).forEach(([k,v]) => { if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v)) })
  const r = await fetch(url, { method:'GET', credentials:'same-origin', headers:{Accept:'application/json'} })
  const x = await r.json()
  if (!r.ok || x.exc || x.exc_type) {
    let msg = x.exception || 'Unable to load sales history'
    if (x._server_messages) {
      try { const arr=JSON.parse(x._server_messages); msg=JSON.parse(arr[arr.length-1]).message || msg } catch (_) {}
    }
    throw new Error(msg)
  }
  return x.message
}
async function load() {
  busy.value = true
  error.value = ''
  selected.value = null
  try {
    data.value = await api('get_retail_history', {
      from_date: from.value, to_date: to.value, search: query.value.trim(),
      cashier: cashier.value.trim(), doc_type: docType.value, pos_profile: props.posProfile, limit: 200
    })
  } catch (e) { error.value = e.message || String(e) }
  finally { busy.value = false }
}
async function viewDetails(row) {
  if (selected.value?.name === row.name && selected.value?.doctype === row.doctype) {
    selected.value = null
    return
  }
  detailsError.value = ''
  detailsBusy.value = true
  try { selected.value = await api('get_retail_sale_detail', {doctype:row.doctype,name:row.name}) }
  catch (e) { selected.value=null; detailsError.value=e.message||String(e) }
  finally { detailsBusy.value=false }
}
function documentUrl(row) { return '/app/' + row.doctype.toLowerCase().replace(/\s+/g,'-') + '/' + encodeURIComponent(row.name) }
async function printPremium(row) {
 printBusy.value=true
 detailsError.value=''
 try {
  const d=await api('get_retail_sale_detail',{doctype:row.doctype,name:row.name})
  printSelection.value={...d, invoice:d.name||row.name, customer_name:d.customer_name||d.customer||row.customer_name||row.customer,
   items:(d.items||[]).map(i=>({...i,item_name:i.item_name||i.description||i.code,item_code:i.code||i.item_code})),
   total:d.grand_total,posting_date:d.posting_date||row.posting_date,currency:d.currency||row.currency}
 } catch(e){detailsError.value=e.message||String(e)}
 finally{printBusy.value=false}
}
function printUrl(row) { return '/printview?doctype=' + encodeURIComponent(row.doctype) + '&name=' + encodeURIComponent(row.name) }
function money(value, currency='BDT') {
  return (currency==='BDT'?'৳':currency+' ') + Number(value||0).toLocaleString('en-BD', {minimumFractionDigits:2,maximumFractionDigits:2})
}
function exportCSV() {
  if (!data.value?.rows?.length) return
  const header = ['Document Type','Document Number','Date','Customer','Created By','POS Profile','Total','Currency','Outstanding','Status']
  const lines = [header, ...data.value.rows.map(r => [
    r.doctype,r.name,r.posting_date,r.customer_name,r.cashier,r.pos_profile,r.grand_total,r.currency,
    r.outstanding_amount == null?'':r.outstanding_amount,r.status
  ])]
  const quote = (x) => {
    let s=String(x??'')
    if (/^[\s]*[=+@\t\r]/.test(s)) s="'"+s
    return '"'+s.replace(/"/g,'""')+'"'
  }
  const csv='\ufeff'+lines.map(line=>line.map(quote).join(',')).join('\r\n')
  const obj=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}))
  const a=document.createElement('a'); a.href=obj; a.download='amcl-retail-sales-'+from.value+'-to-'+to.value+'.csv';a.click()
  setTimeout(()=>URL.revokeObjectURL(obj),1000)
}
onMounted(load)
</script>

<template>
  <section class="rh-page">
    <div class="rh-title"><div><p class="rh-kicker">SERVICING OS / SELLING</p><h2>Retail Sales History</h2><p>Original POS documents, receipt reprints and searchable sales records.</p></div>
      <a class="rh-pos" href="/app/point-of-sale" target="_blank" rel="noopener noreferrer">Open ERPNext POS ↗</a></div>
    <form class="rh-filter" @submit.prevent="load">
      <label><span>From Date</span><input v-model="from" type="date" required /></label>
      <label><span>To Date</span><input v-model="to" type="date" required /></label>
      <label><span>Invoice / customer / POS profile</span><input v-model="query" type="search" placeholder="Search sale or customer" /></label>
      <label><span>Created by (User)</span><input v-model="cashier" placeholder="Optional User ID" /></label>
      <button class="rh-refresh" type="submit" :disabled="busy">{{ busy ? 'Loading…' : 'Refresh History' }}</button>
    </form>
    <div class="rh-pills" role="group" aria-label="Document type">
      <button v-for="t in [{id:'all',label:'All Retail'},{id:'POS Invoice',label:'POS Tickets'},{id:'Sales Invoice',label:'Sales Invoices'}]"
        :key="t.id" type="button" :class="{active:docType===t.id}" @click="docType=t.id;load()">{{t.label}}</button>
      <button class="rh-export" type="button" :disabled="!data?.rows?.length" @click="exportCSV">Export CSV</button>
    </div>
    <div v-if="error" class="rh-error" role="alert">{{error}}</div>
    <div v-for="w in data?.warnings||[]" :key="w" class="rh-warning">{{w}}</div>
    <div v-if="data" class="rh-cards">
      <article><span>POS tickets shown</span><strong>{{data.totals.pos_ticket_count}}</strong><small>Interim POS documents</small></article>
      <article><span>POS ticket amounts</span><strong>{{money(data.totals.pos_tickets_bdt)}}</strong><small>Not necessarily GL-posted</small></article>
      <article><span>Retail Sales Invoices</span><strong>{{data.totals.sales_invoice_count}}</strong><small>Submitted individual invoices</small></article>
      <article><span>Retail invoice amounts</span><strong>{{money(data.totals.posted_retail_invoices_bdt)}}</strong><small>Do not add to POS ticket totals</small></article>
    </div>
    <div class="rh-panel">
      <div class="rh-panel-head"><h3>Retail documents</h3><small>{{data?.shown||0}} shown</small></div>
      <p v-if="data?.has_more" class="rh-warning">There are more records than the current display limit. Narrow your date range or search.</p>
      <p v-if="data?.totals?.other_currency_rows_excluded" class="rh-warning">Non-BDT documents are shown, but excluded from BDT summary totals.</p>
      <p v-if="!busy && data && !data.rows.length" class="rh-empty">No matching retail sales found. If you have not completed a POS sale yet, this is expected. Configure the POS Profile and receive actual stock first.</p>
      <div v-else class="rh-table-wrap"><table><thead><tr><th>Sale</th><th>Customer</th><th>Date</th><th>Created by</th><th>Status</th><th class="rh-right">Total</th><th>Actions</th></tr></thead><tbody>
        <tr v-for="r in data?.rows||[]" :key="r.doctype+'-'+r.name">
          <td><strong>{{r.name}}</strong><small>{{r.doctype}}</small></td>
          <td>{{r.customer_name||r.customer}}</td><td>{{r.posting_date}}</td><td class="rh-muted">{{r.cashier}}</td>
          <td><span class="rh-status">{{r.status}}</span><small>{{r.posting_basis}}</small></td>
          <td class="rh-right rh-nowrap">{{money(r.grand_total,r.currency)}}</td>
          <td class="rh-actions"><button type="button" @click="viewDetails(r)">Details</button><a :href="documentUrl(r)" target="_blank" rel="noopener noreferrer">Open ↗</a><button type="button" :disabled="printBusy" @click="printPremium(r)">Premium Print ↗</button><a :href="printUrl(r)" target="_blank" rel="noopener noreferrer">ERPNext Print ↗</a></td>
        </tr>
      </tbody></table></div>
      <p class="rh-note">POS tickets may be consolidated into Sales Invoices during session closing. Totals above are separated, not combined revenue or collections. Print opens the original ERPNext document and requires permission.</p>
    </div>
    <div v-if="detailsBusy" class="rh-panel rh-details">Loading invoice items…</div>
    <div v-if="detailsError" class="rh-error">{{detailsError}}</div>
    <div v-if="selected" class="rh-panel rh-details">
      <div class="rh-panel-head"><div><h3>{{selected.doctype}} · {{selected.name}}</h3><small>{{selected.customer}} · {{selected.posting_date}}</small></div><button type="button" @click="selected=null">Close ✕</button></div>
      <div class="rh-table-wrap"><table><thead><tr><th>Item</th><th class="rh-right">Qty</th><th class="rh-right">Rate</th><th class="rh-right">Amount</th></tr></thead><tbody>
        <tr v-for="(i,index) in selected.items" :key="index"><td><strong>{{i.description||i.code}}</strong><small>{{i.code}}</small></td><td class="rh-right">{{i.qty}}</td><td class="rh-right">{{money(i.rate,selected.currency)}}</td><td class="rh-right">{{money(i.amount,selected.currency)}}</td></tr>
      </tbody></table></div>
      <div class="rh-detail-total"><strong>Document total</strong><strong>{{money(selected.grand_total,selected.currency)}}</strong></div>
    </div>
    <SalesInvoiceStudio v-if="printSelection" :receipt="printSelection" @close="printSelection=null" />
  </section>
</template>

<style scoped>
.rh-page,.rh-page *{box-sizing:border-box}.rh-page{color:#4b4034;max-width:1550px;margin:0 auto;padding:6px 0 20px}.rh-title{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:19px}.rh-kicker{font-size:10px;letter-spacing:1.3px;font-weight:800;color:#a1825a}.rh-title h2{font-size:22px;font-weight:800;letter-spacing:-.4px;margin:5px 0}.rh-title p:not(.rh-kicker){font-size:12px;color:#8b7f6c}.rh-pos,.rh-refresh{background:#735b40!important;color:white!important;border:1px solid #735b40!important;border-radius:10px;padding:11px 14px;font-weight:750;font-size:12px;text-decoration:none;display:inline-flex;justify-content:center;align-items:center;min-height:43px}.rh-filter{display:grid;grid-template-columns:repeat(2,minmax(145px,1fr)) minmax(220px,1.4fr) minmax(175px,1fr) auto;gap:11px;align-items:end;background:#fffefa;border:1px solid #e7dfd2;border-radius:15px;padding:15px;margin-bottom:12px}.rh-filter label{display:flex;flex-direction:column;gap:7px;min-width:0;font-size:11px;font-weight:750}.rh-filter input{width:100%;height:43px;border:1px solid #dfd4c5;border-radius:10px;background:#fff;color:#4c4134;padding:10px;font-size:12px}.rh-refresh:disabled{opacity:.6}.rh-pills{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:14px}.rh-pills button{padding:9px 13px;background:#fffefa;border:1px solid #e1d6c6;color:#745c40;border-radius:9px;font-size:12px;font-weight:750;min-height:38px}.rh-pills button.active{background:#ece0cd;border-color:#c6b28f;color:#513c23}.rh-pills .rh-export{margin-left:auto}.rh-pills .rh-export:disabled{opacity:.5}.rh-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:16px}.rh-cards article{background:#fffefa;border:1px solid #e6dcce;border-radius:13px;padding:15px;min-width:0}.rh-cards span,.rh-cards strong,.rh-cards small{display:block}.rh-cards span{font-size:11px;color:#8b7c66}.rh-cards strong{font-size:21px;margin:7px 0;font-weight:800;overflow-wrap:anywhere}.rh-cards small{font-size:10px;color:#938671}.rh-panel{background:#fffefa;border:1px solid #e7ddcf;border-radius:15px;padding:15px;margin-top:12px}.rh-panel-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:11px}.rh-panel-head h3{font-size:16px;font-weight:800}.rh-panel-head small{font-size:12px;color:#8e8070}.rh-table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:760px}th,td{padding:12px 10px;text-align:left;border-bottom:1px solid #eee7dd;font-size:12px;vertical-align:middle}th{font-size:10px;letter-spacing:.5px;text-transform:uppercase;color:#8a7b68;background:#f8f3ea}td strong,td small{display:block}td small{font-size:10px;color:#93836b;margin-top:4px}.rh-right{text-align:right}.rh-nowrap{white-space:nowrap}.rh-muted{color:#978571}.rh-status{display:inline-block;border-radius:8px;padding:5px 7px;background:#f2ecdf;color:#7b623f;font-size:11px;font-weight:750}.rh-actions{white-space:nowrap}.rh-actions button,.rh-actions a{display:inline-block;margin:2px 4px 2px 0;font-size:11px;font-weight:700;color:#785b36;text-decoration:none;border:0;background:transparent;cursor:pointer}.rh-actions button:hover,.rh-actions a:hover{text-decoration:underline}.rh-empty{padding:40px 12px;color:#8e8070;text-align:center;font-size:12px}.rh-note{font-size:11px;color:#9b8e7b;margin-top:13px}.rh-warning{background:#fff2d9;border-radius:9px;color:#86612b;padding:10px 12px;margin:8px 0;font-size:12px}.rh-error{background:#ffe8e5;border-radius:9px;color:#9b3129;padding:10px 12px;margin:9px 0;font-size:12px}.rh-details{margin-top:15px}.rh-panel-head button{font-size:12px;background:#eee4d5;padding:8px;border-radius:9px}.rh-detail-total{display:flex;justify-content:space-between;font-size:15px;padding:14px 6px;font-weight:800}@media(max-width:1200px){.rh-filter{grid-template-columns:repeat(2,minmax(0,1fr))}.rh-refresh{grid-column:1 / -1}}@media(max-width:650px){.rh-filter,.rh-cards{grid-template-columns:1fr}.rh-refresh{grid-column:auto}.rh-pills .rh-export{margin-left:0}}
</style>
