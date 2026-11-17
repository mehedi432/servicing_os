<script setup>
import { ref, computed } from 'vue'
import QRCode from './invoice_qr_682/index.js'
import QRErrorCorrectLevel from './invoice_qr_682/QRErrorCorrectLevel.js'
const props=defineProps({receipt:{type:Object,required:true}})
const emit=defineEmits(['close'])
const format=ref('a4')
const paper=ref(null)
const formats=[{id:'a4',label:'A4 · Signature'},{id:'a5',label:'A5 · Compact'},{id:'thermal',label:'80mm · Receipt'},{id:'delivery',label:'Delivery Note'}]
const r=computed(()=>props.receipt||{})
const items=computed(()=>Array.isArray(r.value.items)?r.value.items:[])
const val=(...keys)=>{for(const k of keys){const v=r.value[k];if(v!==undefined&&v!==null&&v!=='')return v}return null}
const num=v=>v===null||v===undefined||v===''?null:Number(v)
const money=v=>'৳'+Number(v||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
const amount=i=>num(i.amount)??((num(i.qty)||0)*(num(i.rate)||0))
const unit=i=>num(i.rate)??(Number(i.qty)?amount(i)/Number(i.qty):null)
const subtotal=computed(()=>num(val('net_total','subtotal'))??items.value.reduce((s,i)=>s+amount(i),0))
const total=computed(()=>num(val('grand_total','total'))??subtotal.value)
const discount=computed(()=>num(val('discount_amount','discount')))
const tax=computed(()=>num(val('total_taxes_and_charges','tax_amount','tax')))
const paid=computed(()=>num(val('paid_amount','paid')))
const outstanding=computed(()=>num(val('outstanding_amount','outstanding')))
const invoice=computed(()=>val('invoice','name')||'—')
const customer=computed(()=>val('customer_name','customer')||'Customer')
const date=computed(()=>val('posting_date','invoice_date','date'))
const financial=computed(()=>format.value!=='delivery')
const itemSerial=i=>[i.serial_no,i.serial_number,i.serial_code,i.serial_numbers,i.serial].filter(v=>v!==undefined&&v!==null&&String(v).trim()).map(String).join(', ')
const itemWarranty=i=>i.warranty_days??i.manual_warranty_days??i.warranty_period_days??null

// SOS_INVOICE_LUXE_682 — real, offline-generated QR and Code39 barcode.
// QR contains invoice ID (not an unverified public verification claim).
const qrText=computed(()=>String(val('verification_url')||invoice.value||'').trim())
const qrMatrix=computed(()=>{
 if(!qrText.value||qrText.value==='—')return []
 try{const qr=new QRCode(-1,QRErrorCorrectLevel.M);qr.addData(qrText.value);qr.make();return qr.modules.map(row=>row.map(Boolean))}
 catch(e){console.warn('Invoice QR unavailable',e);return []}
})
const qrRects=computed(()=>{
 const a=[];const m=qrMatrix.value
 for(let y=0;y<m.length;y++)for(let x=0;x<m[y].length;x++)if(m[y][x])a.push({x:x+4,y:y+4})
 return a
})
const qrSize=computed(()=>qrMatrix.value.length+8)
// SOS_MINIMAL_PREMIUM_685 — Code 128 Set B with checksum
const code128Patterns = {"0":"BaBbBb","1":"BbBaBb","2":"BbBbBa","3":"AbAbBc","4":"AbAcBb","5":"AcAbBb","6":"AbBbAc","7":"AbBcAb","8":"AcBbAb","9":"BbAbAc","10":"BbAcAb","11":"BcAbAb","12":"AaBbCb","13":"AbBaCb","14":"AbBbCa","15":"AaCbBb","16":"AbCaBb","17":"AbCbBa","18":"BbCbAa","19":"BbAaCb","20":"BbAbCa","21":"BaCbAb","22":"BbCaAb","23":"CaBaCa","24":"CaAbBb","25":"CbAaBb","26":"CbAbBa","27":"CaBbAb","28":"CbBaAb","29":"CbBbAa","30":"BaBaBc","31":"BaBcBa","32":"BcBaBa","33":"AaAcBc","34":"AcAaBc","35":"AcAcBa","36":"AaBcAc","37":"AcBaAc","38":"AcBcAa","39":"BaAcAc","40":"BcAaAc","41":"BcAcAa","42":"AaBaCc","43":"AaBcCa","44":"AcBaCa","45":"AaCaBc","46":"AaCcBa","47":"AcCaBa","48":"CaCaBa","49":"BaAcCa","50":"BcAaCa","51":"BaCaAc","52":"BaCcAa","53":"BaCaCa","54":"CaAaBc","55":"CaAcBa","56":"CcAaBa","57":"CaBaAc","58":"CaBcAa","59":"CcBaAa","60":"CaDaAa","61":"BbAdAa","62":"DcAaAa","63":"AaAbBd","64":"AaAdBb","65":"AbAaBd","66":"AbAdBa","67":"AdAaBb","68":"AdAbBa","69":"AaBbAd","70":"AaBdAb","71":"AbBaAd","72":"AbBdAa","73":"AdBaAb","74":"AdBbAa","75":"BdAbAa","76":"BbAaAd","77":"DaCaAa","78":"BdAaAb","79":"AcDaAa","80":"AaAbDb","81":"AbAaDb","82":"AbAbDa","83":"AaDbAb","84":"AbDaAb","85":"AbDbAa","86":"DaAbAb","87":"DbAaAb","88":"DbAbAa","89":"BaBaDa","90":"BaDaBa","91":"DaBaBa","92":"AaAaDc","93":"AaAcDa","94":"AcAaDa","95":"AaDaAc","96":"AaDcAa","97":"DaAaAc","98":"DaAcAa","99":"AaCaDa","100":"AaDaCa","101":"CaAaDa","102":"DaAaCa","103":"BaAdAb","104":"BaAbAd","105":"BaAbCb","106":"BcCaAaB"}
const barcodeValue=computed(()=>String(invoice.value||'').trim())
const barcodeValid=computed(()=>barcodeValue.value.length>0&&barcodeValue.value.length<=60&&[...barcodeValue.value].every(c=>c.charCodeAt(0)>=32&&c.charCodeAt(0)<=126))
const barcodeBars=computed(()=>{
 if(!barcodeValid.value)return []
 const codes=[104];let checksum=104
 for(let i=0;i<barcodeValue.value.length;i++){const c=barcodeValue.value.charCodeAt(i)-32;codes.push(c);checksum+=c*(i+1)}
 codes.push(checksum%103,106)
 const bars=[];let x=10
 for(const code of codes){for(const char of code128Patterns[String(code)]){const w='ABCD'.indexOf(char.toUpperCase())+1;if(char===char.toUpperCase())bars.push({x,w});x+=w}}
 return bars
})
const barcodeWidth=computed(()=>barcodeBars.value.length?Math.max(...barcodeBars.value.map(b=>b.x+b.w))+10:0)
const printableCss="\n.shell{max-width:1200px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:22px}.eyebrow{font-size:11px;font-weight:800;letter-spacing:2px;color:#947454}.top h1{margin:5px 0;font-size:28px}.muted{color:#917e69;font-size:13px}.toolbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;background:#fffaf3;border:1px solid #e5d7c5;border-radius:16px;padding:12px;margin-bottom:20px}.toolbar button{border:1px solid #dacbb9;background:white;border-radius:10px;padding:10px 14px;color:#614c37;font-weight:700;cursor:pointer}.toolbar button.active{background:#5c4432;color:white;border-color:#5c4432}.toolbar .print{background:#5c4432;color:white;margin-left:auto}.layout{display:grid;grid-template-columns:1fr 260px;gap:20px;align-items:start}.sheet{background:#fff;box-shadow:0 12px 45px #48321b1b;margin:auto;padding:35px 39px;width:100%;min-height:700px}.brand{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;border-bottom:2px solid #5c4432;padding-bottom:20px}.brand h2{margin:5px 0 7px;font-size:25px;letter-spacing:-.7px}.brand address{font-style:normal;font-size:11px;line-height:1.7;color:#756454}.seal{font-size:10px;font-weight:800;letter-spacing:2px;color:#9e7c55}.invoice-title{text-align:right}.invoice-title h3{font-size:24px;letter-spacing:2px;margin:0 0 9px}.invoice-title small{font-size:11px;color:#82715e}.details{display:grid;grid-template-columns:1fr 1fr;gap:25px;padding:24px 0}.label{font-size:10px;font-weight:800;letter-spacing:1.5px;color:#92765a;margin-bottom:9px}.details strong{font-size:13px}.details p{font-size:12px;color:#756454;line-height:1.7;margin:4px 0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:7px;font-size:12px}.meta span{color:#85715d}.meta b{text-align:right}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;background:#f4eee5;color:#6d533b;text-transform:uppercase;letter-spacing:.7px;font-size:10px;padding:12px 9px}td{padding:14px 9px;border-bottom:1px solid #eee7dd;vertical-align:top}td small{display:block;color:#94816e;margin-top:5px}.right{text-align:right}.totals{margin:23px 0 0 auto;width:min(300px,100%)}.totals div{display:flex;justify-content:space-between;padding:9px 0;font-size:12px}.totals .grand{border-top:2px solid #5c4432;font-size:18px;font-weight:800;padding-top:15px}.bottom{display:flex;justify-content:space-between;gap:20px;margin-top:55px;border-top:1px solid #e9dfd2;padding-top:20px}.bottom p{font-size:11px;color:#82715f;max-width:380px;line-height:1.6}.qr{width:75px;height:75px;border:5px solid #fff;outline:1px solid #ded3c4;background:repeating-linear-gradient(90deg,#483727 0 4px,#fff 4px 7px,#483727 7px 9px,#fff 9px 13px);display:grid;place-items:center}.qr span{background:white;padding:3px;font-size:8px;color:#4e3826;font-weight:800}.aside{background:#fffaf3;border:1px solid #e6d9c9;border-radius:16px;padding:20px}.aside h3{margin:0 0 10px;font-size:15px}.aside p,.aside li{font-size:12px;color:#7e6a54;line-height:1.6}.aside ul{padding-left:18px}.paper-thermal .sheet{width:340px;padding:20px 14px;min-height:0}.paper-thermal .brand{display:block;text-align:center}.paper-thermal .brand h2{font-size:17px}.paper-thermal .invoice-title{text-align:center;margin-top:17px}.paper-thermal .invoice-title h3{font-size:17px}.paper-thermal .details{display:block;padding:16px 0}.paper-thermal .details>div{margin-bottom:12px}.paper-thermal th,.paper-thermal td{padding:8px 3px;font-size:10px}.paper-thermal .totals{width:100%}.paper-thermal .bottom{margin-top:22px}.paper-thermal .qr{width:55px;height:55px}.paper-a5 .sheet{max-width:610px;min-height:770px;padding:27px}.paper-a5 .brand h2{font-size:20px}.paper-a5 .invoice-title h3{font-size:19px}.paper-delivery .invoice-title h3:after{content:' \u00b7 DELIVERY';font-size:12px;letter-spacing:1px}.paper-delivery .totals{display:none}.paper-delivery .deliverynote{display:block!important}.deliverynote{display:none;margin-top:25px;background:#f8f2e9;padding:15px;font-size:12px}.disclaimer{font-size:10px;color:#9a8976;margin-top:10px}@media(max-width:850px){.layout{grid-template-columns:1fr}.aside{order:-1}.shell{padding:12px}.sheet{padding:22px}.top{align-items:flex-start}.top h1{font-size:23px}}@media(max-width:540px){.brand{display:block}.invoice-title{text-align:left;margin-top:17px}.details{grid-template-columns:1fr}.toolbar .print{margin-left:0}.sheet{padding:16px}.brand h2{font-size:20px}.invoice-title h3{font-size:20px}}"
const executivePrintCss=`.amci683-document{font-family:Inter,Arial,sans-serif!important;color:#25211e}.amci683-topline{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid #d8c8b5;padding-bottom:10px;margin-bottom:19px;font-size:9px;font-weight:800;letter-spacing:1.3px;color:#79604b}.amci683-reference{display:flex;justify-content:space-between;gap:18px;background:#f3eee7;border:1px solid #dfd0be;padding:17px 19px;margin:20px 0 0;break-inside:avoid}.amci683-reference>div:first-child{min-width:0}.amci683-reference strong{display:block;font-size:22px;letter-spacing:-.6px;overflow-wrap:anywhere;color:#30251d;margin:5px 0}.amci683-kicker{font-size:9px;font-weight:850;letter-spacing:1.4px;color:#8c6a4e}.amci683-reference small{display:block;font-size:9px;color:#786553}.amci683-refside{text-align:right;min-width:110px}.amci683-refside span{display:block;font-size:10px;letter-spacing:1px;font-weight:850}.amci683-refside b{display:block;margin:7px 0;font-size:12px}.amci683-sl{width:36px!important;text-align:center!important;white-space:nowrap!important;font-weight:800!important}.amci683-document .brand{border-bottom:3px solid #3f3024!important;padding-bottom:21px}.amci683-document .brand h2{font-size:25px!important;letter-spacing:-.8px!important;font-weight:900!important}.amci683-document .seal{letter-spacing:2.5px!important}.amci683-document .invoice-title h3{font-size:19px!important;letter-spacing:2.2px!important}.amci683-document .details{padding:25px 0 23px!important}.amci683-document .label{font-size:9px!important;letter-spacing:1.8px!important}.amci683-document table{border-top:2px solid #45372c!important}.amci683-document th{background:#ece3d7!important;color:#423226!important;font-size:9px!important;padding:12px 9px!important}.amci683-document td{padding:13px 9px!important}.amci683-document tbody tr:nth-child(even){background:#fbf8f3}.amci683-document .totals .grand{background:#eee5da!important;padding:14px 12px!important;margin-top:7px!important;border-top:2px solid #45372c!important}.amci683-document .amci682-footer{margin-top:34px!important}.paper-thermal .amci683-topline{font-size:7px;letter-spacing:0}.paper-thermal .amci683-reference{display:block;text-align:center;padding:9px 4px;margin:12px 0}.paper-thermal .amci683-reference strong{font-size:15px}.paper-thermal .amci683-refside{display:none}.paper-thermal .amci683-document th{padding:5px 2px!important}.paper-thermal .amci683-document td{padding:6px 2px!important}.paper-thermal .amci683-sl{width:23px!important;font-size:9px!important}.paper-thermal .amci683-document .brand h2{font-size:15px!important}@media print{.amci683-reference,.amci683-topline{break-inside:avoid}}`
const luxePrintCss=`.amci682-footer{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin-top:30px;border-top:1px solid #ded3c4;padding-top:14px}.amci682-thanks{flex:1}.amci682-thanks>b{font-size:11px}.amci682-thanks p{font-size:10px}.amci682-codes{display:flex;gap:12px;align-items:flex-end;justify-content:flex-end;flex-wrap:wrap}.amci682-qrblock,.amci682-barblock{display:flex;flex-direction:column;align-items:center;gap:4px}.amci682-qr{width:88px;height:88px;background:#fff}.amci682-barcode{width:155px;height:46px;background:#fff}.amci682-codes small{font-size:8px;text-align:center;overflow-wrap:anywhere}.paper-thermal .amci682-footer{display:flex;flex-direction:column;align-items:center;gap:12px}.paper-thermal .amci682-codes{justify-content:center;max-width:100%}.paper-thermal .amci682-thanks{text-align:center}.paper-thermal .amci682-qr{width:90px;height:90px}.paper-thermal .amci682-barcode{width:185px;height:46px}@media print{.amci682-footer,.amci682-codes,.amci682-qrblock,.amci682-barblock{break-inside:avoid}}`
const minimalPrintCss="\n.amci683-document{font-family:Inter,Arial,sans-serif!important;color:#25221f!important}\n.amci683-document .brand{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:20px!important;border-bottom:1.5px solid #3f332b!important;padding-bottom:20px!important}\n.amci683-document .seal{display:none!important}\n.amci683-document .brand h2{font-size:22px!important;font-weight:850!important;letter-spacing:-.5px!important;margin:0 0 6px!important}\n.amci683-document .brand address{font-size:10px!important;line-height:1.6!important;color:#665b50!important}\n.amci683-document .invoice-title{min-width:175px!important;text-align:right!important}\n.amci683-document .invoice-title h3{font-size:17px!important;font-weight:800!important;letter-spacing:.6px!important;margin:8px 0 5px!important;white-space:nowrap!important}\n.amci685-invoice-ref{display:block!important;font-size:10px!important;color:#4c3c30!important;overflow-wrap:anywhere!important}\n.amci685-topbarcode{width:190px;max-width:100%;margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;gap:2px}\n.amci685-topbarcode svg{display:block;width:100%;height:42px;background:#fff}\n.amci685-topbarcode small{font:600 9px/1.2 monospace!important;letter-spacing:.25px!important;color:#111!important}\n.amci683-document .details{padding:22px 0!important;border-bottom:0!important}\n.amci683-document .label{font-size:9px!important;letter-spacing:1px!important;color:#786958!important}\n.amci683-document table{margin-top:4px!important}\n.amci683-document th{background:#f5f1eb!important;color:#3b332d!important;font-size:10px!important;font-weight:750!important;padding:11px 9px!important}\n.amci683-document td{font-size:11px!important;padding:11px 9px!important;border-bottom:1px solid #e9e4dd!important}\n.amci683-document .totals .grand{background:#f5f1eb!important;border:0!important;padding:13px!important}\n.amci683-document .bottom{border-top:1px solid #ddd5ca!important;margin-top:26px!important;padding-top:13px!important}\n.amci683-document .amci682-thanks>b{font-size:10px!important;letter-spacing:0!important}\n.amci683-document .amci682-thanks p{font-size:9px!important}\n.amci683-document .amci682-qr{width:65px!important;height:65px!important;border:0!important}\n.amci683-document .amci682-codes{max-width:90px!important}\n.paper-thermal .amci683-document .brand{display:block!important;text-align:center!important}\n.paper-thermal .amci683-document .invoice-title{text-align:center!important;margin:12px auto 0!important;min-width:0!important}\n.paper-thermal .amci685-topbarcode{width:195px!important;margin:0 auto!important;align-items:center!important}\n.paper-thermal .amci683-document .invoice-title h3{font-size:14px!important}\n.paper-thermal .amci683-document .brand h2{font-size:14px!important}\n.paper-thermal .amci683-document .amci682-qr{width:60px!important;height:60px!important}\n"
const fitPrintCss = "\n/* SOS_INVOICE_FIT_686_SAFE */\n\n/* Keep the entire invoice inside its paper container. */\n.amci-paper-wrap,\n.print-root,\n.amci-paper-wrap .sheet,\n.print-root .sheet {\n    box-sizing: border-box !important;\n    min-width: 0 !important;\n}\n\n.amci-paper-wrap .sheet,\n.print-root .sheet {\n    width: 100% !important;\n    max-width: 100% !important;\n    overflow: hidden !important;\n}\n\n.amci-paper-wrap .sheet table,\n.print-root .sheet table {\n    width: 100% !important;\n    max-width: 100% !important;\n    min-width: 0 !important;\n    table-layout: fixed !important;\n    border-collapse: collapse !important;\n}\n\n/* Five-column sales invoice. */\n.amci-paper-wrap .sheet th,\n.amci-paper-wrap .sheet td,\n.print-root .sheet th,\n.print-root .sheet td {\n    box-sizing: border-box !important;\n    min-width: 0 !important;\n    padding: 8px 4px !important;\n    font-size: 10px !important;\n    letter-spacing: 0 !important;\n    overflow-wrap: anywhere !important;\n    white-space: normal !important;\n    vertical-align: top !important;\n}\n\n.amci-paper-wrap .sheet th:first-child,\n.amci-paper-wrap .sheet td:first-child,\n.print-root .sheet th:first-child,\n.print-root .sheet td:first-child {\n    width: 7% !important;\n}\n\n.amci-paper-wrap .sheet th:nth-child(2),\n.amci-paper-wrap .sheet td:nth-child(2),\n.print-root .sheet th:nth-child(2),\n.print-root .sheet td:nth-child(2) {\n    width: 43% !important;\n}\n\n.amci-paper-wrap .sheet th:nth-child(3),\n.amci-paper-wrap .sheet td:nth-child(3),\n.print-root .sheet th:nth-child(3),\n.print-root .sheet td:nth-child(3) {\n    width: 9% !important;\n}\n\n.amci-paper-wrap .sheet th:nth-child(4),\n.amci-paper-wrap .sheet td:nth-child(4),\n.print-root .sheet th:nth-child(4),\n.print-root .sheet td:nth-child(4) {\n    width: 20% !important;\n}\n\n.amci-paper-wrap .sheet th:nth-child(5),\n.amci-paper-wrap .sheet td:nth-child(5),\n.print-root .sheet th:nth-child(5),\n.print-root .sheet td:nth-child(5) {\n    width: 21% !important;\n}\n\n/* Delivery note has only three columns. */\n.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) th:nth-child(2),\n.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) td:nth-child(2),\n.print-root .sheet table:not(:has(th:nth-child(4))) th:nth-child(2),\n.print-root .sheet table:not(:has(th:nth-child(4))) td:nth-child(2) {\n    width: 78% !important;\n}\n\n.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) th:nth-child(3),\n.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) td:nth-child(3),\n.print-root .sheet table:not(:has(th:nth-child(4))) th:nth-child(3),\n.print-root .sheet table:not(:has(th:nth-child(4))) td:nth-child(3) {\n    width: 15% !important;\n}\n\n/* Prevent long item names and warranty details from expanding columns. */\n.amci-paper-wrap .sheet td *,\n.print-root .sheet td * {\n    max-width: 100% !important;\n    overflow-wrap: anywhere !important;\n}\n\n/* 80mm thermal-specific typography and spacing. */\n.amci-paper-wrap.paper-thermal .sheet,\n.print-root.paper-thermal .sheet {\n    width: 80mm !important;\n    max-width: 80mm !important;\n    min-width: 0 !important;\n    padding: 8px 5px !important;\n}\n\n.amci-paper-wrap.paper-thermal .sheet th,\n.amci-paper-wrap.paper-thermal .sheet td,\n.print-root.paper-thermal .sheet th,\n.print-root.paper-thermal .sheet td {\n    padding: 5px 2px !important;\n    font-size: 8px !important;\n}\n\n.amci-paper-wrap.paper-thermal .sheet th,\n.print-root.paper-thermal .sheet th {\n    font-size: 7px !important;\n}\n\n/* Compact modal interface \u2014 does not shrink the printed document. */\n.amci-modal {\n    font-size: 12px !important;\n}\n\n.amci-header {\n    padding: 10px 15px !important;\n}\n\n.amci-header h2 {\n    font-size: 16px !important;\n    line-height: 1.3 !important;\n}\n\n.amci-header small {\n    font-size: 10px !important;\n}\n\n.amci-eyebrow {\n    font-size: 9px !important;\n}\n\n.amci-toolbar {\n    padding: 9px 13px !important;\n    gap: 6px !important;\n}\n\n.amci-toolbar button,\n.amci-header button {\n    font-size: 11px !important;\n    min-height: 32px !important;\n    padding: 6px 9px !important;\n}\n"
const thermalMonoCss=`.paper-thermal .sheet{color:#111!important;background:#fff!important;max-width:80mm!important;min-height:0!important}.paper-thermal .brand{border-bottom:2px solid #111!important}.paper-thermal .brand h2{font-size:15px!important;letter-spacing:0!important}.paper-thermal .seal,.paper-thermal .label,.paper-thermal th,.paper-thermal td small{color:#111!important}.paper-thermal .label{border-bottom:1px solid #111!important;padding-bottom:5px!important}.paper-thermal th{background:white!important;border-top:1px solid #111!important;border-bottom:1px solid #111!important;padding:6px 3px!important;font-size:9px!important}.paper-thermal td{padding:7px 3px!important;font-size:10px!important;border-bottom:1px dashed #aaa!important;overflow-wrap:anywhere}.paper-thermal td small{overflow-wrap:anywhere}.paper-thermal .totals .grand{border-color:#111!important}.paper-thermal .bottom{border-top:1px dashed #111!important}`
function printInvoice(){
 if(!paper.value)return
 const w=window.open('','_blank','width=980,height=880')
 if(!w){window.alert('Please allow pop-ups to print.');return}
 const size=format.value==='thermal'?'80mm auto':format.value==='a5'?'A5':'A4'
 const margin=format.value==='thermal'?'2mm':'10mm'
 const printCss=`@page{size:${size};margin:${margin}}html,body{margin:0;background:white!important} .sheet{box-shadow:none!important;min-height:0!important;width:100%!important;max-width:none!important;padding:0!important} .print-root{display:block!important;width:100%!important;max-width:none!important} .brand,.bottom,tr{break-inside:avoid} .paper-thermal .sheet{width:100%!important} .paper-thermal .details{display:block} .paper-thermal .brand{display:block;text-align:center} .paper-thermal .invoice-title{text-align:center;margin-top:12px} .paper-thermal .bottom{margin-top:18px} .paper-delivery .totals{display:none!important} @media print{*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}`
 w.document.open()
 w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Invoice '+String(invoice.value).replace(/[<>&"']/g,'')+'</title><style>'+printableCss+'\n'+printCss+'\n'+thermalMonoCss+'\n'+luxePrintCss+'\n'+executivePrintCss+'\n'+minimalPrintCss+'\n'+fitPrintCss+'</style></head><body><div class="print-root paper-'+format.value+'">'+paper.value.outerHTML+'</div></body></html>')
 w.document.close()
 w.focus()
 w.setTimeout(()=>w.print(),450)
}
</script>
<template>
<div class="amci-overlay" role="dialog" aria-modal="true" aria-label="Invoice Studio">
 <div class="amci-modal">
  <header class="amci-header"><div><span class="amci-eyebrow">AL MODINA · PRINT STUDIO</span><h2>Premium Invoice Formats</h2><small>{{invoice}} · {{customer}}</small></div><button type="button" @click="emit('close')">✕ Close</button></header>
  <div class="amci-toolbar"><button v-for="f in formats" :key="f.id" type="button" :class="{active:format===f.id}" @click="format=f.id">{{f.label}}</button><button class="amci-print" type="button" @click="printInvoice">Print selected format ↗</button></div>
  <div class="amci-content"><div class="amci-paper-wrap" :class="'paper-'+format">
   <article ref="paper" class="sheet amci683-document">
    <div class="brand"><div><div class="seal">AL MODINA · COMPUTERS</div><h2>AL MODINA COMPUTERS LIMITED</h2><address>Mawna Chowrasta, Sreepur Upazila<br>Gazipur 1740, Bangladesh</address></div><div class="invoice-title amci685-invoice-title"><div v-if="barcodeValid" class="amci685-topbarcode"><svg xmlns="http://www.w3.org/2000/svg" :viewBox="`0 0 ${barcodeWidth} 52`" preserveAspectRatio="none" shape-rendering="crispEdges" role="img" :aria-label="`Code 128 barcode for invoice ${barcodeValue}`"><rect :width="barcodeWidth" height="52" fill="#fff"/><rect v-for="(bar,n) in barcodeBars" :key="n" :x="bar.x" y="2" :width="bar.w" height="48" fill="#111"/></svg><small>{{barcodeValue}}</small></div><h3>{{format==='delivery'?'DELIVERY NOTE':'SALES INVOICE'}}</h3><small class="amci685-invoice-ref">Invoice No. <b>{{invoice}}</b></small><small v-if="date">{{date}}</small></div></div>
    <div class="details"><div><div class="label">BILL TO</div><strong>{{customer}}</strong><p v-if="val('customer_mobile','mobile_no','contact_mobile')">Mobile: {{val('customer_mobile','mobile_no','contact_mobile')}}</p></div><div><div class="label">INVOICE DETAILS</div><div class="meta"><template v-if="val('mode_of_payment','payment_method')"><span>Payment</span><b>{{val('mode_of_payment','payment_method')}}</b></template><span>Currency</span><b>{{val('currency')||'BDT'}}</b></div></div></div>
    <table><thead><tr><th class="amci683-sl">S/L</th><th>Item / Description</th><th class="right">Qty</th><th v-if="financial" class="right">Unit Price</th><th v-if="financial" class="right">Amount</th></tr></thead><tbody><tr v-for="(i,idx) in items" :key="idx"><td class="amci683-sl">{{String(idx+1).padStart(2,'0')}}</td><td><b>{{i.item_name||i.description||i.item_code||i.code||'Item'}}</b><small v-if="itemSerial(i)"><b>Serial / SN:</b> {{itemSerial(i)}}</small><small v-if="itemWarranty(i)!=null">Warranty: {{itemWarranty(i)}} days</small></td><td class="right">{{i.qty}}</td><td v-if="financial" class="right">{{unit(i)==null?'—':money(unit(i))}}</td><td v-if="financial" class="right">{{money(amount(i))}}</td></tr></tbody></table>
    <div v-if="financial" class="totals"><div><span>Subtotal</span><b>{{money(subtotal)}}</b></div><div v-if="discount!=null"><span>Discount</span><b>−{{money(discount)}}</b></div><div v-if="tax!=null"><span>Tax</span><b>{{money(tax)}}</b></div><div class="grand"><span>Grand Total</span><span>{{money(total)}}</span></div><div v-if="paid!=null"><span>Paid</span><b>{{money(paid)}}</b></div><div v-if="outstanding!=null"><span>Outstanding</span><b>{{money(outstanding)}}</b></div></div>
    <div v-if="format==='delivery'" class="deliverynote" style="display:block"><b>DELIVERY ACKNOWLEDGEMENT</b><p>Received the items listed above in satisfactory visible condition.</p><p>Received by: __________________ &nbsp; Date: ________________</p></div>
    <div class="bottom amci682-footer">
      <div class="amci682-thanks"><b>THANK YOU FOR CHOOSING AL MODINA</b><p>Retain this invoice for warranty and service.</p></div>
      <div class="amci682-codes">
        <div v-if="qrRects.length" class="amci682-qrblock"><svg xmlns="http://www.w3.org/2000/svg" class="amci682-qr" :viewBox="`0 0 ${qrSize} ${qrSize}`" shape-rendering="crispEdges" role="img" :aria-label="`QR for invoice ${invoice}`"><rect :width="qrSize" :height="qrSize" fill="#fff"/><rect v-for="(cell,n) in qrRects" :key="n" :x="cell.x" :y="cell.y" width="1" height="1" fill="#111"/></svg><small>{{val('verification_url')?'Scan invoice link':'Scan invoice number'}}</small></div>
        
      </div>
    </div>
   </article>
  </div></div>
 </div>
</div>
</template>
<style scoped>

.shell{max-width:1200px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:22px}.eyebrow{font-size:11px;font-weight:800;letter-spacing:2px;color:#947454}.top h1{margin:5px 0;font-size:28px}.muted{color:#917e69;font-size:13px}.toolbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;background:#fffaf3;border:1px solid #e5d7c5;border-radius:16px;padding:12px;margin-bottom:20px}.toolbar button{border:1px solid #dacbb9;background:white;border-radius:10px;padding:10px 14px;color:#614c37;font-weight:700;cursor:pointer}.toolbar button.active{background:#5c4432;color:white;border-color:#5c4432}.toolbar .print{background:#5c4432;color:white;margin-left:auto}.layout{display:grid;grid-template-columns:1fr 260px;gap:20px;align-items:start}.sheet{background:#fff;box-shadow:0 12px 45px #48321b1b;margin:auto;padding:35px 39px;width:100%;min-height:700px}.brand{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;border-bottom:2px solid #5c4432;padding-bottom:20px}.brand h2{margin:5px 0 7px;font-size:25px;letter-spacing:-.7px}.brand address{font-style:normal;font-size:11px;line-height:1.7;color:#756454}.seal{font-size:10px;font-weight:800;letter-spacing:2px;color:#9e7c55}.invoice-title{text-align:right}.invoice-title h3{font-size:24px;letter-spacing:2px;margin:0 0 9px}.invoice-title small{font-size:11px;color:#82715e}.details{display:grid;grid-template-columns:1fr 1fr;gap:25px;padding:24px 0}.label{font-size:10px;font-weight:800;letter-spacing:1.5px;color:#92765a;margin-bottom:9px}.details strong{font-size:13px}.details p{font-size:12px;color:#756454;line-height:1.7;margin:4px 0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:7px;font-size:12px}.meta span{color:#85715d}.meta b{text-align:right}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;background:#f4eee5;color:#6d533b;text-transform:uppercase;letter-spacing:.7px;font-size:10px;padding:12px 9px}td{padding:14px 9px;border-bottom:1px solid #eee7dd;vertical-align:top}td small{display:block;color:#94816e;margin-top:5px}.right{text-align:right}.totals{margin:23px 0 0 auto;width:min(300px,100%)}.totals div{display:flex;justify-content:space-between;padding:9px 0;font-size:12px}.totals .grand{border-top:2px solid #5c4432;font-size:18px;font-weight:800;padding-top:15px}.bottom{display:flex;justify-content:space-between;gap:20px;margin-top:55px;border-top:1px solid #e9dfd2;padding-top:20px}.bottom p{font-size:11px;color:#82715f;max-width:380px;line-height:1.6}.qr{width:75px;height:75px;border:5px solid #fff;outline:1px solid #ded3c4;background:repeating-linear-gradient(90deg,#483727 0 4px,#fff 4px 7px,#483727 7px 9px,#fff 9px 13px);display:grid;place-items:center}.qr span{background:white;padding:3px;font-size:8px;color:#4e3826;font-weight:800}.aside{background:#fffaf3;border:1px solid #e6d9c9;border-radius:16px;padding:20px}.aside h3{margin:0 0 10px;font-size:15px}.aside p,.aside li{font-size:12px;color:#7e6a54;line-height:1.6}.aside ul{padding-left:18px}.paper-thermal .sheet{width:340px;padding:20px 14px;min-height:0}.paper-thermal .brand{display:block;text-align:center}.paper-thermal .brand h2{font-size:17px}.paper-thermal .invoice-title{text-align:center;margin-top:17px}.paper-thermal .invoice-title h3{font-size:17px}.paper-thermal .details{display:block;padding:16px 0}.paper-thermal .details>div{margin-bottom:12px}.paper-thermal th,.paper-thermal td{padding:8px 3px;font-size:10px}.paper-thermal .totals{width:100%}.paper-thermal .bottom{margin-top:22px}.paper-thermal .qr{width:55px;height:55px}.paper-a5 .sheet{max-width:610px;min-height:770px;padding:27px}.paper-a5 .brand h2{font-size:20px}.paper-a5 .invoice-title h3{font-size:19px}.paper-delivery .totals{display:none}.paper-delivery .deliverynote{display:block!important}.deliverynote{display:none;margin-top:25px;background:#f8f2e9;padding:15px;font-size:12px}.disclaimer{font-size:10px;color:#9a8976;margin-top:10px}@media(max-width:850px){.layout{grid-template-columns:1fr}.aside{order:-1}.shell{padding:12px}.sheet{padding:22px}.top{align-items:flex-start}.top h1{font-size:23px}}@media(max-width:540px){.brand{display:block}.invoice-title{text-align:left;margin-top:17px}.details{grid-template-columns:1fr}.toolbar .print{margin-left:0}.sheet{padding:16px}.brand h2{font-size:20px}.invoice-title h3{font-size:20px}}
.amci-overlay{position:fixed;inset:0;z-index:11000;background:#291c12aa;display:grid;place-items:center;padding:14px;color:#3e3025;font-family:Inter,ui-sans-serif,system-ui,Arial}.amci-modal{width:min(1220px,100%);max-height:96vh;background:#f5f0e8;border-radius:18px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 80px #24170c66}.amci-header{display:flex;align-items:center;justify-content:space-between;padding:15px 24px;background:#fffaf3;border-bottom:1px solid #e5d7c5}.amci-header h2{font-size:22px;margin:4px 0}.amci-header small{font-size:11px;color:#917e69}.amci-eyebrow{font-size:10px;letter-spacing:1.6px;font-weight:800;color:#947454}.amci-header button{border:1px solid #dacbb9;border-radius:9px;padding:9px 13px;background:#fff;color:#614c37;cursor:pointer}.amci-toolbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:12px 24px;background:#fffaf3;border-bottom:1px solid #e5d7c5}.amci-toolbar button{border:1px solid #dacbb9;background:white;border-radius:10px;padding:10px 14px;color:#614c37;font-weight:700;cursor:pointer}.amci-toolbar button.active,.amci-toolbar .amci-print{background:#5c4432;color:white;border-color:#5c4432}.amci-toolbar .amci-print{margin-left:auto}.amci-content{display:grid;grid-template-columns:minmax(0,1fr) 235px;gap:18px;overflow:auto;padding:20px 24px;align-items:start}.amci-paper-wrap{min-width:0}.amci-paper-wrap .sheet{max-width:795px}.amci-paper-wrap.paper-a5 .sheet{max-width:550px}.amci-paper-wrap.paper-thermal .sheet{max-width:340px}.amci-aside{background:#fffaf3;border:1px solid #e6d9c9;border-radius:14px;padding:18px}.amci-aside h3{margin:0 0 10px;font-size:14px}.amci-aside p,.amci-aside li{font-size:11px;color:#7e6a54;line-height:1.65}.amci-aside ul{padding-left:18px}.amci-paper-wrap.paper-delivery .totals{display:none}@media(max-width:820px){.amci-content{grid-template-columns:1fr}.amci-aside{display:none}}@media(max-width:540px){.amci-overlay{padding:0}.amci-modal{max-height:100vh;border-radius:0}.amci-header,.amci-toolbar{padding:10px}.amci-toolbar .amci-print{margin-left:0}.amci-content{padding:10px}.amci-paper-wrap .sheet{min-height:0;padding:15px}}
</style>

<style>
/* v6.75: monochrome 80mm receipt styling based on supplied thermal sample */
.amci-paper-wrap.paper-thermal .sheet{color:#111!important;background:#fff!important;border:0!important;box-shadow:none!important;max-width:80mm!important;min-height:0!important;padding:12px 9px!important}
.amci-paper-wrap.paper-thermal .brand{border-bottom:2px solid #111!important;padding-bottom:12px!important}
.amci-paper-wrap.paper-thermal .seal{color:#111!important}
.amci-paper-wrap.paper-thermal .brand h2{color:#111!important;font-size:15px!important;letter-spacing:0!important}
.amci-paper-wrap.paper-thermal .brand address,.amci-paper-wrap.paper-thermal .details p,.amci-paper-wrap.paper-thermal .meta span,.amci-paper-wrap.paper-thermal .bottom p{color:#222!important}
.amci-paper-wrap.paper-thermal .invoice-title h3{font-size:14px!important;letter-spacing:1px!important}
.amci-paper-wrap.paper-thermal .label{color:#111!important;border-bottom:1px solid #111!important;padding-bottom:5px!important}
.amci-paper-wrap.paper-thermal th{background:#fff!important;color:#111!important;border-top:1px solid #111!important;border-bottom:1px solid #111!important;padding:6px 3px!important;font-size:9px!important}
.amci-paper-wrap.paper-thermal td{border-bottom:1px dashed #aaa!important;padding:7px 3px!important;font-size:10px!important;overflow-wrap:anywhere}
.amci-paper-wrap.paper-thermal td small{color:#111!important;line-height:1.4!important;overflow-wrap:anywhere}
.amci-paper-wrap.paper-thermal .totals .grand{border-color:#111!important}
.amci-paper-wrap.paper-thermal .bottom{border-top:1px dashed #111!important}
</style>

<style>
/* SOS_INVOICE_LUXE_682 — premium print typography and true machine-readable codes */
.amci-paper-wrap .sheet{border:1px solid #e9ddce!important}
.amci-paper-wrap .brand{padding-bottom:24px}
.amci-paper-wrap .brand h2{font-weight:850;letter-spacing:-.8px;line-height:1.12}
.amci-paper-wrap .invoice-title h3{font-weight:900;letter-spacing:1.5px}
.amci-paper-wrap .totals .grand{font-size:19px}
.amci682-footer{align-items:flex-end;gap:24px}
.amci682-thanks{flex:1;min-width:0}
.amci682-thanks>b{font-size:11px;letter-spacing:.5px;color:#503928}
.amci682-footnote{font-size:10px!important}
.amci682-codes{display:flex;gap:14px;align-items:flex-end;justify-content:flex-end;flex-wrap:wrap;max-width:270px}
.amci682-qrblock,.amci682-barblock{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}
.amci682-qr{display:block;width:90px;height:90px;background:white;padding:3px;border:1px solid #e6dbcd}
.amci682-barcode{display:block;width:150px;height:44px;max-width:100%;background:white}
.amci682-codes small{font-size:8px!important;line-height:1.25!important;color:#554437!important;text-align:center;overflow-wrap:anywhere}
.amci-paper-wrap.paper-thermal .amci682-footer{display:flex!important;flex-direction:column!important;align-items:center!important;gap:12px!important}
.amci-paper-wrap.paper-thermal .amci682-codes{justify-content:center!important;width:100%!important;max-width:none!important;gap:10px!important}
.amci-paper-wrap.paper-thermal .amci682-thanks{text-align:center!important}
.amci-paper-wrap.paper-thermal .amci682-qr{width:92px!important;height:92px!important;border:0!important}
.amci-paper-wrap.paper-thermal .amci682-barcode{width:190px!important;height:46px!important}
.amci-paper-wrap.paper-thermal .amci682-codes small{color:#111!important}
@media(max-width:540px){.amci682-footer{flex-direction:column;align-items:center}.amci682-codes{justify-content:center}}
</style>

<style>
/* SOS_INVOICE_EXECUTIVE_683 — same hierarchy in preview and print */
.amci683-document{font-family:Inter,Arial,sans-serif!important;color:#25211e}
.amci683-topline{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid #d8c8b5;padding-bottom:10px;margin-bottom:19px;font-size:9px;font-weight:800;letter-spacing:1.3px;color:#79604b}
.amci683-reference{display:flex;justify-content:space-between;gap:18px;background:#f3eee7;border:1px solid #dfd0be;padding:17px 19px;margin:20px 0 0}
.amci683-reference>div:first-child{min-width:0}.amci683-reference strong{display:block;font-size:22px;letter-spacing:-.6px;overflow-wrap:anywhere;color:#30251d;margin:5px 0}
.amci683-kicker{font-size:9px;font-weight:850;letter-spacing:1.4px;color:#8c6a4e}.amci683-reference small{display:block;font-size:9px;color:#786553}
.amci683-refside{text-align:right;min-width:110px}.amci683-refside span{display:block;font-size:10px;letter-spacing:1px;font-weight:850}.amci683-refside b{display:block;margin:7px 0;font-size:12px}
.amci683-sl{width:36px!important;text-align:center!important;white-space:nowrap!important;font-weight:800!important}
.amci683-document .brand{border-bottom:3px solid #3f3024!important;padding-bottom:21px}.amci683-document .brand h2{font-size:25px!important;letter-spacing:-.8px!important;font-weight:900!important}
.amci683-document .seal{letter-spacing:2.5px!important}.amci683-document .invoice-title h3{font-size:19px!important;letter-spacing:2.2px!important}
.amci683-document .details{padding:25px 0 23px!important}.amci683-document .label{font-size:9px!important;letter-spacing:1.8px!important}
.amci683-document table{border-top:2px solid #45372c!important}.amci683-document th{background:#ece3d7!important;color:#423226!important;font-size:9px!important;padding:12px 9px!important}.amci683-document td{padding:13px 9px!important}.amci683-document tbody tr:nth-child(even){background:#fbf8f3}
.amci683-document .totals .grand{background:#eee5da!important;padding:14px 12px!important;margin-top:7px!important;border-top:2px solid #45372c!important}.amci683-document .amci682-footer{margin-top:34px!important}
.amci-paper-wrap.paper-thermal .amci683-topline{font-size:7px;letter-spacing:0}.amci-paper-wrap.paper-thermal .amci683-reference{display:block;text-align:center;padding:9px 4px;margin:12px 0}.amci-paper-wrap.paper-thermal .amci683-reference strong{font-size:15px}.amci-paper-wrap.paper-thermal .amci683-refside{display:none}.amci-paper-wrap.paper-thermal .amci683-document th{padding:5px 2px!important}.amci-paper-wrap.paper-thermal .amci683-document td{padding:6px 2px!important}.amci-paper-wrap.paper-thermal .amci683-sl{width:23px!important;font-size:9px!important}.amci-paper-wrap.paper-thermal .amci683-document .brand h2{font-size:15px!important}
@media(max-width:540px){.amci683-reference{display:block}.amci683-refside{text-align:left;margin-top:9px}}
</style>

<style>
/* SOS_MINIMAL_PREMIUM_685 */

.amci683-document{font-family:Inter,Arial,sans-serif!important;color:#25221f!important}
.amci683-document .brand{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:20px!important;border-bottom:1.5px solid #3f332b!important;padding-bottom:20px!important}
.amci683-document .seal{display:none!important}
.amci683-document .brand h2{font-size:22px!important;font-weight:850!important;letter-spacing:-.5px!important;margin:0 0 6px!important}
.amci683-document .brand address{font-size:10px!important;line-height:1.6!important;color:#665b50!important}
.amci683-document .invoice-title{min-width:175px!important;text-align:right!important}
.amci683-document .invoice-title h3{font-size:17px!important;font-weight:800!important;letter-spacing:.6px!important;margin:8px 0 5px!important;white-space:nowrap!important}
.amci685-invoice-ref{display:block!important;font-size:10px!important;color:#4c3c30!important;overflow-wrap:anywhere!important}
.amci685-topbarcode{width:190px;max-width:100%;margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;gap:2px}
.amci685-topbarcode svg{display:block;width:100%;height:42px;background:#fff}
.amci685-topbarcode small{font:600 9px/1.2 monospace!important;letter-spacing:.25px!important;color:#111!important}
.amci683-document .details{padding:22px 0!important;border-bottom:0!important}
.amci683-document .label{font-size:9px!important;letter-spacing:1px!important;color:#786958!important}
.amci683-document table{margin-top:4px!important}
.amci683-document th{background:#f5f1eb!important;color:#3b332d!important;font-size:10px!important;font-weight:750!important;padding:11px 9px!important}
.amci683-document td{font-size:11px!important;padding:11px 9px!important;border-bottom:1px solid #e9e4dd!important}
.amci683-document .totals .grand{background:#f5f1eb!important;border:0!important;padding:13px!important}
.amci683-document .bottom{border-top:1px solid #ddd5ca!important;margin-top:26px!important;padding-top:13px!important}
.amci683-document .amci682-thanks>b{font-size:10px!important;letter-spacing:0!important}
.amci683-document .amci682-thanks p{font-size:9px!important}
.amci683-document .amci682-qr{width:65px!important;height:65px!important;border:0!important}
.amci683-document .amci682-codes{max-width:90px!important}
.paper-thermal .amci683-document .brand{display:block!important;text-align:center!important}
.paper-thermal .amci683-document .invoice-title{text-align:center!important;margin:12px auto 0!important;min-width:0!important}
.paper-thermal .amci685-topbarcode{width:195px!important;margin:0 auto!important;align-items:center!important}
.paper-thermal .amci683-document .invoice-title h3{font-size:14px!important}
.paper-thermal .amci683-document .brand h2{font-size:14px!important}
.paper-thermal .amci683-document .amci682-qr{width:60px!important;height:60px!important}

</style>

<style>

/* SOS_INVOICE_FIT_686_SAFE */

/* Keep the entire invoice inside its paper container. */
.amci-paper-wrap,
.print-root,
.amci-paper-wrap .sheet,
.print-root .sheet {
    box-sizing: border-box !important;
    min-width: 0 !important;
}

.amci-paper-wrap .sheet,
.print-root .sheet {
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden !important;
}

.amci-paper-wrap .sheet table,
.print-root .sheet table {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    table-layout: fixed !important;
    border-collapse: collapse !important;
}

/* Five-column sales invoice. */
.amci-paper-wrap .sheet th,
.amci-paper-wrap .sheet td,
.print-root .sheet th,
.print-root .sheet td {
    box-sizing: border-box !important;
    min-width: 0 !important;
    padding: 8px 4px !important;
    font-size: 10px !important;
    letter-spacing: 0 !important;
    overflow-wrap: anywhere !important;
    white-space: normal !important;
    vertical-align: top !important;
}

.amci-paper-wrap .sheet th:first-child,
.amci-paper-wrap .sheet td:first-child,
.print-root .sheet th:first-child,
.print-root .sheet td:first-child {
    width: 7% !important;
}

.amci-paper-wrap .sheet th:nth-child(2),
.amci-paper-wrap .sheet td:nth-child(2),
.print-root .sheet th:nth-child(2),
.print-root .sheet td:nth-child(2) {
    width: 43% !important;
}

.amci-paper-wrap .sheet th:nth-child(3),
.amci-paper-wrap .sheet td:nth-child(3),
.print-root .sheet th:nth-child(3),
.print-root .sheet td:nth-child(3) {
    width: 9% !important;
}

.amci-paper-wrap .sheet th:nth-child(4),
.amci-paper-wrap .sheet td:nth-child(4),
.print-root .sheet th:nth-child(4),
.print-root .sheet td:nth-child(4) {
    width: 20% !important;
}

.amci-paper-wrap .sheet th:nth-child(5),
.amci-paper-wrap .sheet td:nth-child(5),
.print-root .sheet th:nth-child(5),
.print-root .sheet td:nth-child(5) {
    width: 21% !important;
}

/* Delivery note has only three columns. */
.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) th:nth-child(2),
.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) td:nth-child(2),
.print-root .sheet table:not(:has(th:nth-child(4))) th:nth-child(2),
.print-root .sheet table:not(:has(th:nth-child(4))) td:nth-child(2) {
    width: 78% !important;
}

.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) th:nth-child(3),
.amci-paper-wrap .sheet table:not(:has(th:nth-child(4))) td:nth-child(3),
.print-root .sheet table:not(:has(th:nth-child(4))) th:nth-child(3),
.print-root .sheet table:not(:has(th:nth-child(4))) td:nth-child(3) {
    width: 15% !important;
}

/* Prevent long item names and warranty details from expanding columns. */
.amci-paper-wrap .sheet td *,
.print-root .sheet td * {
    max-width: 100% !important;
    overflow-wrap: anywhere !important;
}

/* 80mm thermal-specific typography and spacing. */
.amci-paper-wrap.paper-thermal .sheet,
.print-root.paper-thermal .sheet {
    width: 80mm !important;
    max-width: 80mm !important;
    min-width: 0 !important;
    padding: 8px 5px !important;
}

.amci-paper-wrap.paper-thermal .sheet th,
.amci-paper-wrap.paper-thermal .sheet td,
.print-root.paper-thermal .sheet th,
.print-root.paper-thermal .sheet td {
    padding: 5px 2px !important;
    font-size: 8px !important;
}

.amci-paper-wrap.paper-thermal .sheet th,
.print-root.paper-thermal .sheet th {
    font-size: 7px !important;
}

/* Compact modal interface — does not shrink the printed document. */
.amci-modal {
    font-size: 12px !important;
}

.amci-header {
    padding: 10px 15px !important;
}

.amci-header h2 {
    font-size: 16px !important;
    line-height: 1.3 !important;
}

.amci-header small {
    font-size: 10px !important;
}

.amci-eyebrow {
    font-size: 9px !important;
}

.amci-toolbar {
    padding: 9px 13px !important;
    gap: 6px !important;
}

.amci-toolbar button,
.amci-header button {
    font-size: 11px !important;
    min-height: 32px !important;
    padding: 6px 9px !important;
}

</style>
