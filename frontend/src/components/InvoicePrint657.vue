<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'
import JsBarcode from 'jsbarcode'

const props = defineProps({ invoiceName: { type:String, required:true }, doctype: {type:String,default:'Sales Invoice'}, duplicate: {type:Boolean,default:false} })
const emit = defineEmits(['close'])
const invoice = ref(null)
const busy = ref(false)
const error = ref('')
const qr = ref('')
const barcode = ref(null)
const paper = ref(null)
const paperSize = ref('A4')
const printing = ref(false)
const cash = computed(()=>invoice.value?.currency||'BDT')
const money = n => Number(n||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const isDraft = computed(()=>invoice.value?.docstatus !== 1)
const barcodeString = computed(()=>String(invoice.value?.name||''))
let loadNumber = 0

async function load() {
  const seq = ++loadNumber
  busy.value = true; error.value=''; invoice.value=null; qr.value=''
  try {
    const url = new URL('/api/method/servicing_os.api.invoice_delivery_657.get_branded_invoice',location.origin)
    url.searchParams.set('invoice_name',props.invoiceName)
    url.searchParams.set('doctype',props.doctype)
    const response = await fetch(url,{credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'})
    const result = await response.json()
    if (!response.ok || result.exc || result.exception) throw new Error(typeof result.message==='string'?result.message:'Could not load invoice details.')
    if(seq!==loadNumber)return
    invoice.value=result.message
    qr.value=await QRCode.toDataURL(invoice.value.qr_reference||invoice.value.name,{width:190,margin:1,errorCorrectionLevel:'M'})
    await nextTick()
    if (barcode.value) JsBarcode(barcode.value, barcodeString.value,{format:'CODE128',lineColor:'#3c2c25',width:1.4,height:35,margin:2,displayValue:false})
  } catch(e) { if(seq===loadNumber)error.value=e?.message||'Unable to prepare invoice.' }
  finally { if(seq===loadNumber)busy.value=false }
}
watch(()=>[props.invoiceName,props.doctype],load,{immediate:true})

const sheetCSS = `
.sos658-duplicate-ribbon{font-family:Arial,Helvetica,sans-serif;text-align:center;font-weight:800;font-size:11px;letter-spacing:1.3px;color:#70462e;background:#f4e3d3;border:1px solid #dcc4aa;border-radius:6px;padding:8px 10px;margin:0 0 13px;page-break-inside:avoid}
.sos657-receipt .sos658-duplicate-ribbon{font-size:8px;letter-spacing:.4px;padding:5px;margin-bottom:8px}
* { box-sizing:border-box } html,body {padding:0;margin:0;color:#3b2a22;background:#fff;font-family:Arial,Helvetica,sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.sos657-sheet{width:100%;margin:0 auto;background:#fff;color:#3c2c25;padding:23mm 18mm 16mm;font-size:11px;line-height:1.44;position:relative;min-height:260mm}
.sos657-sheet-top{height:7px;background:linear-gradient(90deg,#6a4834,#bd9274 70%,#f4e3d3);margin:-23mm -18mm 20mm}
.sos657-print-brand{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;border-bottom:1px solid #e8dace;padding-bottom:18px}
.sos657-monogram{flex:0 0 auto;width:47px;height:47px;border-radius:12px;background:#805a3e;color:#fff;font-size:17px;font-weight:800;letter-spacing:-1px;display:grid;place-items:center}
.sos657-brand-title{display:flex;align-items:center;gap:12px;min-width:0}.sos657-brand-title strong{display:block;font-size:18px;line-height:1.22;letter-spacing:.2px}.sos657-brand-title small{display:block;font-size:10px;color:#806a59;margin-top:5px}
.sos657-invoice-caption{text-align:right;flex:0 0 auto}.sos657-invoice-caption h1{font-size:21px;letter-spacing:1.9px;margin:0 0 4px;color:#5f3f2d}.sos657-invoice-caption small{font-size:10px;color:#806a59}
.sos657-status{display:inline-block;padding:5px 11px;background:#eee3d7;border:1px solid #dec6b3;color:#704f37;border-radius:20px;font-weight:750;font-size:9px;letter-spacing:.5px;margin:10px 0}
.sos657-meta{display:grid;grid-template-columns:1.1fr .9fr;gap:22px;padding:23px 0 24px}.sos657-meta h2{margin:0 0 7px;color:#96755e;text-transform:uppercase;font-weight:800;letter-spacing:1.5px;font-size:9px}.sos657-meta strong{display:block;font-size:14px;margin-bottom:5px;overflow-wrap:anywhere}.sos657-meta p{margin:0;color:#6d5749;font-size:10px;overflow-wrap:anywhere}
.sos657-fieldgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 13px;margin-top:8px}.sos657-fieldgrid div{display:flex;justify-content:space-between;gap:7px;font-size:10px;padding:4px 0;border-bottom:1px solid #f0e7df}.sos657-fieldgrid b{overflow-wrap:anywhere;text-align:right;font-size:10px}
.sos657-lines{width:100%;border-collapse:collapse;table-layout:fixed}.sos657-lines thead{background:#71503c;color:white}.sos657-lines th{font-size:9px;letter-spacing:.4px;text-transform:uppercase;padding:10px 8px;text-align:left}.sos657-lines td{padding:11px 8px;border-bottom:1px solid #ebdfd3;vertical-align:top;font-size:10px}.sos657-lines tr:nth-child(even){background:#fffaf5}.sos657-lines .number{text-align:right}.sos657-lines .description{color:#856b57;font-size:9px;white-space:normal;word-wrap:break-word}.sos657-lines .item-name{font-weight:780}.sos657-lines .serial{font-size:9px;color:#694b37;font-weight:700;margin-top:5px;overflow-wrap:anywhere}
.sos657-total-grid{display:grid;grid-template-columns:1fr minmax(230px,38%);gap:22px;margin-top:19px;align-items:start}.sos657-total-note{padding:15px;background:#f8f1e9;border-radius:10px;font-size:10px;color:#806a59}.sos657-total-note strong{display:block;margin-bottom:6px;color:#5a3d2b}.sos657-amount-box{padding:14px 18px;border:1px solid #e6d3bf;border-radius:10px;background:#fffefa}.sos657-amount-box div{display:flex;justify-content:space-between;gap:9px;padding:5px 0}.sos657-amount-box .grand{font-size:17px;font-weight:850;border-top:1px solid #dbbfa8;margin-top:8px;padding-top:12px;color:#5c3b29}.sos657-amount-box span{color:#756050}.sos657-amount-box .grand span{color:inherit}
.sos657-bottom{display:grid;grid-template-columns:1fr 160px;gap:25px;margin-top:30px;padding-top:16px;border-top:1px solid #e8dace;align-items:end}.sos657-bottom strong{display:block;font-size:11px}.sos657-bottom p{margin:4px 0;font-size:9px;color:#8d7968}.sos657-verify{display:flex;gap:8px;align-items:center;justify-content:flex-end}.sos657-verify img{width:75px;height:75px;object-fit:contain}.sos657-code{display:flex;flex-direction:column;align-items:flex-end;gap:4px}.sos657-code svg{width:154px;height:43px}.sos657-code small{font-size:9px;letter-spacing:.2px}.sos657-draftmark{position:absolute;top:48%;left:19%;font-size:100px;font-weight:900;color:rgba(110,71,49,.08);letter-spacing:10px;transform:rotate(-22deg);pointer-events:none}
.sos657-receipt .sos657-sheet{width:80mm!important;padding:5mm 4mm!important;min-height:auto}.sos657-receipt .sos657-sheet-top{margin:-5mm -4mm 5mm;height:4px}.sos657-receipt .sos657-print-brand{display:block;text-align:center;padding-bottom:10px}.sos657-receipt .sos657-brand-title{display:flex;justify-content:center}.sos657-receipt .sos657-monogram{width:28px;height:28px;font-size:11px}.sos657-receipt .sos657-brand-title strong{font-size:12px}.sos657-receipt .sos657-invoice-caption{text-align:center;margin-top:7px}.sos657-receipt .sos657-invoice-caption h1{font-size:14px}.sos657-receipt .sos657-meta{grid-template-columns:1fr;gap:10px;padding:12px 0}.sos657-receipt .sos657-fieldgrid{gap:0}.sos657-receipt .sos657-lines th,.sos657-receipt .sos657-lines td{padding:6px 3px;font-size:8px}.sos657-receipt .sos657-total-grid{grid-template-columns:1fr;gap:10px}.sos657-receipt .sos657-amount-box{padding:9px}.sos657-receipt .sos657-bottom{grid-template-columns:1fr;gap:10px}.sos657-receipt .sos657-verify{justify-content:center}.sos657-receipt .sos657-draftmark{font-size:45px;left:10%}
@media print{.sos657-lines tr{break-inside:avoid}.sos657-lines thead{display:table-header-group}}
`

async function printInvoice() {
  if(!paper.value || !invoice.value || printing.value)return
  printing.value=true;error.value=''
  let frame
  try {
    await nextTick()
    if(document.fonts?.ready)await document.fonts.ready
    frame=document.createElement('iframe')
    frame.setAttribute('aria-hidden','true')
    Object.assign(frame.style,{position:'fixed',left:'-10000px',top:'-10000px',width:'0',height:'0',border:'none'})
    document.body.appendChild(frame)
    const w=frame.contentWindow
    const html=frame.contentDocument
    const media=paperSize.value==='A4'?'A4':'80mm 250mm'
    const margin=paperSize.value==='A4'?'0':'0'
    const className=paperSize.value==='80mm'?'sos657-receipt':''
    html.open()
    html.write('<!doctype html><html><head><meta charset="utf-8"><title>Invoice '+String(invoice.value.name).replace(/[&<>"']/g,'')+'</title><style>@page{size:'+media+';margin:'+margin+'}'+sheetCSS+'</style></head><body class="'+className+'">'+paper.value.outerHTML+'</body></html>')
    html.close()
    await Promise.all([...html.images].map(img=>img.complete?Promise.resolve():new Promise(resolve=>{img.onload=resolve;img.onerror=resolve})))
    w.focus();w.print()
    const cleanup=()=>{if(frame?.parentNode)frame.remove()}
    w.addEventListener('afterprint',cleanup,{once:true})
    setTimeout(cleanup,90000)
  }catch(e){error.value=e?.message||'Unable to open print dialog'; if(frame?.parentNode)frame.remove()}
  finally{printing.value=false}
}
</script>

<template>
  <Teleport to="body">
    <div class="sos657-backdrop" @click.self="emit('close')">
      <section class="sos657-dialog" role="dialog" aria-modal="true" :aria-label="'Invoice '+invoiceName">
        <div class="sos657-tools">
          <div class="sos657-dialoghead"><strong>{{ duplicate ? 'Duplicate invoice copy' : 'Invoice preview' }}</strong><small>{{ invoiceName }} · AL MODINA COMPUTERS LIMITED</small></div>
          <label>Paper <select v-model="paperSize"><option value="A4">A4 Invoice</option><option value="80mm">80mm Receipt</option></select></label>
          <button type="button" class="sos657-print" :disabled="!invoice || printing" @click="printInvoice">{{ printing?'Preparing…':duplicate?'Print Duplicate Copy':'Print Invoice' }}</button>
          <button type="button" @click="emit('close')">Close ×</button>
        </div>
        <p v-if="busy" class="sos657-message">Preparing invoice with barcode and QR code…</p>
        <p v-else-if="error" role="alert" class="sos657-error">{{ error }}</p>
        <div v-if="invoice" class="sos657-scroll" :class="{'sos657-receipt':paperSize==='80mm'}">
          <article ref="paper" class="sos657-sheet">
            <div class="sos657-sheet-top"></div>
            <div v-if="duplicate" class="sos658-duplicate-ribbon" aria-label="Duplicate invoice copy">DUPLICATE COPY · REPRINT OF {{ invoice.name }}</div>
            <div class="sos657-print-brand">
              <div class="sos657-brand-title"><div class="sos657-monogram">AM</div><div><strong>{{ invoice.company }}</strong><small>Computer sales · Parts · Repairs · Service</small></div></div>
              <div class="sos657-invoice-caption"><h1>SALES INVOICE</h1><small>{{ duplicate ? 'DUPLICATE COPY · Reprint' : 'Original customer copy' }}</small><div class="sos657-status">{{ invoice.status }} · {{ invoice.delivery_status }}</div></div>
            </div>
            <div class="sos657-meta">
              <div><h2>Bill to</h2><strong>{{ invoice.customer_name }}</strong><p>{{ invoice.customer_phone }}</p><h2 style="margin-top:18px">From</h2><p>{{ invoice.company_address }}</p><p>{{ invoice.company_phone }}</p><p>{{ invoice.company_email }}</p></div>
              <div><h2>Invoice details</h2><strong>{{ invoice.name }}</strong><div class="sos657-fieldgrid"><div><span>Date</span><b>{{ invoice.posting_date }}</b></div><div><span>Currency</span><b>{{ cash }}</b></div><div v-if="invoice.service_job"><span>Service Job</span><b>{{ invoice.service_job }}</b></div><div><span>Payment status</span><b>{{ invoice.status }}</b></div><div><span>Delivered</span><b>{{ invoice.delivery_status }}</b></div><div v-if="invoice.due_date"><span>Due date</span><b>{{ invoice.due_date }}</b></div></div></div>
            </div>
            <table class="sos657-lines"><thead><tr><th style="width:7%">#</th><th style="width:46%">Product / Service</th><th style="width:10%">Qty</th><th style="width:17%" class="number">Rate</th><th style="width:20%" class="number">Amount</th></tr></thead><tbody>
              <tr v-for="(item,i) in invoice.items" :key="i"><td>{{ i+1 }}</td><td><span class="item-name">{{ item.item_name }}</span><div class="description">{{ item.item_code }} · {{ item.uom }}<template v-if="item.discount_percentage"> · {{ item.discount_percentage }}% off</template></div><div v-if="item.serial_no" class="serial">Serial: {{ item.serial_no }}</div></td><td>{{ item.qty }}</td><td class="number">{{ money(item.rate) }}</td><td class="number">{{ money(item.amount) }}</td></tr>
            </tbody></table>
            <div class="sos657-total-grid">
              <div class="sos657-total-note"><strong>Thank you for choosing {{ invoice.company }}.</strong><span>Keep this invoice for warranty and return support. Serial numbers on this invoice identify the supplied devices where recorded.</span><p v-if="invoice.remarks">{{ invoice.remarks }}</p></div>
              <div class="sos657-amount-box"><div><span>Net amount</span><b>{{ money(invoice.net_total) }}</b></div><div v-if="invoice.discount_amount"><span>Additional discount</span><b>− {{ money(invoice.discount_amount) }}</b></div><div v-for="(tax,i) in invoice.taxes" :key="i"><span>{{ tax.description }}</span><b>{{ money(tax.amount) }}</b></div><div class="grand"><span>Grand total</span><b>{{ cash }} {{ money(invoice.grand_total) }}</b></div><div><span>Paid</span><b>{{ money(invoice.paid_amount) }}</b></div><div><span>Outstanding</span><b>{{ money(invoice.outstanding_amount) }}</b></div></div>
            </div>
            <div class="sos657-bottom"><div><strong>Authorized signature / received by customer</strong><p>____________________________________________</p><p>Invoice generated by SERVICING OS · {{ invoice.company }}</p><p>QR is an invoice reference, not a public authenticity verification.</p></div><div class="sos657-verify"><div class="sos657-code"><svg ref="barcode"></svg><small>{{ invoice.name }}</small><small>Invoice serial / Code 128</small></div><img v-if="qr" :src="qr" alt="Invoice reference QR code" /></div></div>
            <div v-if="isDraft" class="sos657-draftmark">{{ invoice.status }}</div>
          </article>
        </div>
      </section>
    </div>
  </Teleport>
</template>
<style>
.sos657-backdrop,.sos657-backdrop *{box-sizing:border-box}
.sos657-backdrop{position:fixed;inset:0;z-index:2147483000;background:#291b15ba;display:flex;align-items:center;justify-content:center;padding:15px}
.sos657-dialog{width:min(1120px,100%);max-height:96vh;background:#f9f6f2;border-radius:17px;overflow:hidden;display:flex;flex-direction:column;border:1px solid #e8d4c3;box-shadow:0 18px 65px #1b100c69}
.sos657-tools{display:flex;align-items:center;flex-wrap:wrap;gap:10px;padding:13px 17px;background:#fffaf5;border-bottom:1px solid #e6d5c3;position:relative;z-index:1}
.sos657-dialoghead{display:flex;flex-direction:column;min-width:170px;flex:1;color:#3c2c25}.sos657-dialoghead strong{font-size:14px}.sos657-dialoghead small{font-size:10px;color:#876f5d}
.sos657-tools label{display:flex;align-items:center;gap:6px;color:#856a57;font-size:11px}.sos657-tools select{border:1px solid #dbc4b0;border-radius:8px;min-height:39px;background:#fffcf7;padding:7px}
.sos657-tools button{border:1px solid #d8c0aa;background:#f5e8dc;border-radius:9px;color:#5f4231;min-height:39px;padding:8px 14px;font-weight:700;font-size:11px}
.sos657-tools button.sos657-print{background:#805a3e;color:#fff;border-color:#805a3e}.sos657-tools button:disabled{opacity:.55}
.sos657-scroll{overflow-y:auto;padding:24px;background:#ede5db}.sos657-scroll .sos657-sheet{max-width:210mm;box-shadow:0 8px 30px #503e2927}
.sos657-scroll.sos657-receipt .sos657-sheet{max-width:80mm;min-height:0}
.sos657-scroll .sos657-sheet{font-family:Arial,Helvetica,sans-serif}.sos657-scroll .sos657-sheet{color:#3c2c25;background:#fff;font-size:11px;line-height:1.44;padding:23mm 18mm 16mm;position:relative;min-height:260mm}
.sos657-scroll .sos657-sheet-top{height:7px;background:linear-gradient(90deg,#6a4834,#bd9274 70%,#f4e3d3);margin:-23mm -18mm 20mm}
.sos657-scroll .sos657-print-brand{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;border-bottom:1px solid #e8dace;padding-bottom:18px}
.sos657-scroll .sos657-brand-title{display:flex;align-items:center;gap:12px}.sos657-scroll .sos657-monogram{flex:0 0 auto;width:47px;height:47px;border-radius:12px;background:#805a3e;color:#fff;font-size:17px;font-weight:800;letter-spacing:-1px;display:grid;place-items:center}
.sos657-scroll .sos657-brand-title strong{display:block;font-size:18px;line-height:1.22}.sos657-scroll .sos657-brand-title small{display:block;font-size:10px;color:#806a59;margin-top:5px}
.sos657-scroll .sos657-invoice-caption{text-align:right}.sos657-scroll .sos657-invoice-caption h1{font-size:21px;letter-spacing:1.9px;margin:0 0 4px;color:#5f3f2d}.sos657-scroll .sos657-invoice-caption small{font-size:10px;color:#806a59}
.sos657-scroll .sos657-status{display:inline-block;padding:5px 11px;background:#eee3d7;border:1px solid #dec6b3;color:#704f37;border-radius:20px;font-weight:750;font-size:9px;letter-spacing:.5px;margin:10px 0}
.sos657-scroll .sos657-meta{display:grid;grid-template-columns:1.1fr .9fr;gap:22px;padding:23px 0 24px}.sos657-scroll .sos657-meta h2{margin:0 0 7px;color:#96755e;text-transform:uppercase;font-weight:800;letter-spacing:1.5px;font-size:9px}.sos657-scroll .sos657-meta strong{display:block;font-size:14px;margin-bottom:5px}.sos657-scroll .sos657-meta p{margin:0;color:#6d5749;font-size:10px}.sos657-scroll .sos657-fieldgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 13px;margin-top:8px}.sos657-scroll .sos657-fieldgrid div{display:flex;justify-content:space-between;gap:7px;font-size:10px;padding:4px 0;border-bottom:1px solid #f0e7df}
.sos657-scroll .sos657-lines{width:100%;border-collapse:collapse;table-layout:fixed}.sos657-scroll .sos657-lines thead{background:#71503c;color:white}.sos657-scroll .sos657-lines th{font-size:9px;letter-spacing:.4px;text-transform:uppercase;padding:10px 8px;text-align:left}.sos657-scroll .sos657-lines td{padding:11px 8px;border-bottom:1px solid #ebdfd3;vertical-align:top;font-size:10px}.sos657-scroll .sos657-lines tr:nth-child(even){background:#fffaf5}.sos657-scroll .sos657-lines .number{text-align:right}.sos657-scroll .sos657-lines .description{color:#856b57;font-size:9px}.sos657-scroll .sos657-lines .item-name{font-weight:780}.sos657-scroll .sos657-lines .serial{font-size:9px;color:#694b37;font-weight:700;margin-top:5px;overflow-wrap:anywhere}
.sos657-scroll .sos657-total-grid{display:grid;grid-template-columns:1fr minmax(230px,38%);gap:22px;margin-top:19px;align-items:start}.sos657-scroll .sos657-total-note{padding:15px;background:#f8f1e9;border-radius:10px;font-size:10px;color:#806a59}.sos657-scroll .sos657-total-note strong{display:block;margin-bottom:6px;color:#5a3d2b}.sos657-scroll .sos657-amount-box{padding:14px 18px;border:1px solid #e6d3bf;border-radius:10px;background:#fffefa}.sos657-scroll .sos657-amount-box div{display:flex;justify-content:space-between;gap:9px;padding:5px 0}.sos657-scroll .sos657-amount-box .grand{font-size:17px;font-weight:850;border-top:1px solid #dbbfa8;margin-top:8px;padding-top:12px;color:#5c3b29}
.sos657-scroll .sos657-bottom{display:grid;grid-template-columns:1fr 160px;gap:25px;margin-top:30px;padding-top:16px;border-top:1px solid #e8dace;align-items:end}.sos657-scroll .sos657-bottom strong{display:block;font-size:11px}.sos657-scroll .sos657-bottom p{margin:4px 0;font-size:9px;color:#8d7968}.sos657-scroll .sos657-verify{display:flex;gap:8px;align-items:center;justify-content:flex-end}.sos657-scroll .sos657-verify img{width:75px;height:75px;object-fit:contain}.sos657-scroll .sos657-code{display:flex;flex-direction:column;align-items:flex-end;gap:4px}.sos657-scroll .sos657-code svg{width:154px;height:43px}.sos657-scroll .sos657-code small{font-size:9px}.sos657-scroll .sos657-draftmark{position:absolute;top:48%;left:19%;font-size:100px;font-weight:900;color:#6e473112;letter-spacing:10px;transform:rotate(-22deg);pointer-events:none}
.sos657-scroll.sos657-receipt .sos657-sheet{width:80mm!important;padding:5mm 4mm!important;min-height:auto}.sos657-scroll.sos657-receipt .sos657-sheet-top{margin:-5mm -4mm 5mm;height:4px}.sos657-scroll.sos657-receipt .sos657-print-brand{display:block;text-align:center;padding-bottom:10px}.sos657-scroll.sos657-receipt .sos657-brand-title{justify-content:center}.sos657-scroll.sos657-receipt .sos657-monogram{width:28px;height:28px;font-size:11px}.sos657-scroll.sos657-receipt .sos657-brand-title strong{font-size:12px}.sos657-scroll.sos657-receipt .sos657-invoice-caption{text-align:center;margin-top:7px}.sos657-scroll.sos657-receipt .sos657-invoice-caption h1{font-size:14px}.sos657-scroll.sos657-receipt .sos657-meta{grid-template-columns:1fr;gap:10px;padding:12px 0}.sos657-scroll.sos657-receipt .sos657-total-grid{grid-template-columns:1fr;gap:10px}.sos657-scroll.sos657-receipt .sos657-bottom{grid-template-columns:1fr;gap:10px}.sos657-scroll.sos657-receipt .sos657-verify{justify-content:center}.sos657-scroll.sos657-receipt .sos657-draftmark{font-size:45px;left:10%}
.sos657-message,.sos657-error{padding:25px;text-align:center;color:#795940;font-size:13px}.sos657-error{color:#a04129}
.sos657-scroll .sos658-duplicate-ribbon{text-align:center;font-size:11px;font-weight:800;letter-spacing:1px;color:#70462e;background:#f4e3d3;border:1px solid #dcc4aa;border-radius:6px;padding:9px;margin:0 0 13px}
.sos657-scroll.sos657-receipt .sos658-duplicate-ribbon{font-size:8px;letter-spacing:0;padding:5px}
</style>

<!-- SERVICING_OS_COUNTER_658 -->
