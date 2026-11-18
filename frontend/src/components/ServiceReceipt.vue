<script setup>
import { ref as sos683EarlyRef } from "vue"
const format = sos683EarlyRef("thermal")
// SOS_RECEIVE_PRINT_STUDIO_683: multiple print paper formats without changing receipt data.
const sos683RollLength = ref(220)
const sos683CustomWidth = ref(105)
const sos683CustomHeight = ref(148)
const sos683PrintFormats = [
  { key: 'a4', label: 'A4 · 210 × 297 mm', width: 210, height: 297, padding: 14 },
  { key: 'a5', label: 'A5 · 148 × 210 mm', width: 148, height: 210, padding: 10 },
  { key: 'letter', label: 'US Letter · 216 × 279 mm', width: 216, height: 279, padding: 14 },
  { key: 'b5', label: 'B5 · 176 × 250 mm', width: 176, height: 250, padding: 12 },
  { key: 'thermal58', label: 'POS Thermal · 58 mm', width: 58, height: 220, padding: 2.5 },
  { key: 'thermal76', label: 'POS Thermal · 76 mm', width: 76, height: 220, padding: 3 },
  { key: 'thermal', label: 'POS Thermal · 80 mm', width: 80, height: 220, padding: 3 },
  { key: 'thermal100', label: 'POS Roll · 100 mm', width: 100, height: 220, padding: 4 },
]
const sos683IsRoll = computed(() => ['thermal58','thermal76','thermal','thermal100'].includes(format.value))
function sos683Clamp(n, low, high, fallback) {
  const value = Number(n)
  return Number.isFinite(value) ? Math.max(low, Math.min(high, value)) : fallback
}
const sos683Paper = computed(() => {
  if (format.value === 'custom') return {
    width: sos683Clamp(sos683CustomWidth.value, 40, 216, 105),
    height: sos683Clamp(sos683CustomHeight.value, 60, 420, 148),
    padding: 5,
    isRoll: false,
  }
  const item = sos683PrintFormats.find(x => x.key === format.value) || sos683PrintFormats[6]
  return {
    width: item.width,
    height: sos683IsRoll.value ? sos683Clamp(sos683RollLength.value, 80, 420, 220) : item.height,
    padding: item.padding,
    isRoll: sos683IsRoll.value,
  }
})
const sos683PaperStyle = computed(() => ({
  '--sos683-width': `${sos683Paper.value.width}mm`,
  '--sos683-height': `${sos683Paper.value.height}mm`,
  '--sos683-pad': `${sos683Paper.value.padding}mm`,
  '--sos683-font': sos683Paper.value.width <= 58 ? '9px' : sos683Paper.value.width <= 100 ? '11px' : '12px',
  '--sos683-min-height': sos683Paper.value.isRoll ? '0mm' : `${sos683Paper.value.height}mm`,
}))
function sos683RemovePageRule() { document.getElementById('sos683-receipt-page')?.remove() }


// SOS_635_QR_INSIDE_RECEIPT_MODAL — QR and barcode sticker in existing receipt modal.
import { ref as sos35Ref, watch as sos35Watch, nextTick as sos35NextTick } from 'vue'
import SOS35QrCode from 'qrcode'
import SOS35JsBarcode from 'jsbarcode'
const sos35Sticker = sos35Ref(false)
const sos35QrImage = sos35Ref('')
const sos35BarcodeImage = sos35Ref('')
const sos35Error = sos35Ref('')
const sos35Host = sos35Ref(window.location.origin)
const sos35Job = () => String(props.data?.job?.name || '').trim()
const sos35Customer = () => String(props.data?.job?.customer_name || '').trim()
const sos35Phone = () => String(props.data?.job?.mobile || '').trim()
const sos35Problem = () => String(props.data?.job?.reported_problem || '').trim()
const sos35Device = () => [props.data?.job?.brand, props.data?.job?.device_model].filter(Boolean).join(' ').trim() || String(props.data?.job?.device_type || '').trim()
const sos35Serial = () => String(props.data?.job?.serial_number || '').trim()
function sos35BuildUrl() {
  const jobId = sos35Job()
  if (!jobId) throw Error('Service Job ID is missing.')
  const base = new URL(sos35Host.value.trim())
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || !base.hostname) {
    throw Error('Enter a valid shop URL reachable from the phone.')
  }
  if (['localhost', '127.0.0.1', '::1'].includes(base.hostname.toLowerCase())) {
    throw Error('For mobile scanning, replace localhost with your computer LAN address (for example http://192.168.0.100:8005).')
  }
  const url = new URL('/servicing-os', base.origin)
  url.searchParams.set('service_job', jobId)
  return url.href
}
async function sos35BuildImages() {
  sos35QrImage.value = ''
  sos35BarcodeImage.value = ''
  sos35Error.value = ''
  try {
    const jobId = sos35Job()
    const url = sos35BuildUrl()
    sos35QrImage.value = await SOS35QrCode.toDataURL(url, { width: 420, margin: 2, errorCorrectionLevel: 'M' })
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    SOS35JsBarcode(svg, jobId, { format: 'CODE128', width: 1.8, height: 34, margin: 3, displayValue: false })
    sos35BarcodeImage.value = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg.outerHTML)
  } catch (e) {
    sos35Error.value = e?.message || 'Could not generate the QR sticker.'
  }
}
// SOS_638_BN_QR_FULL_PROBLEM — stable button markers, independent of language.
function sos35ClickCapture(event) {
  const btn = event.target?.closest?.('button')
  if (!btn) return
  if (btn.dataset.sosStickerPrint === '1') {
    if (sos35Sticker.value) {
      event.preventDefault()
      event.stopPropagation()
      event.stopImmediatePropagation?.()
      sos35Print()
    }
    return
  }
  if (btn.dataset.sosStickerTab === '1') {
    sos35Sticker.value = true
    sos35BuildImages()
  }
}
// Watching the component's actual mode prevents Bangla DOM text replacements
// from hiding the sticker view or disabling its print control.
sos35Watch(() => format.value, (nextMode) => {
  const isSticker = /sticker|label/i.test(String(nextMode || ''))
  if (isSticker !== sos35Sticker.value) {
    sos35Sticker.value = isSticker
    if (isSticker) sos35BuildImages()
  }
}, { immediate: true })
sos35Watch(sos35Host, () => { if (sos35Sticker.value) sos35BuildImages() })
sos35Watch(() => props.data?.job?.name, () => { if (sos35Sticker.value) sos35BuildImages() })
function sos35Escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
}
// SOS_50X30_SYMMETRIC_STICKER_V7 — printed 50×30mm label only.
function sos35Html() {
  if (!sos35QrImage.value) throw Error(sos35Error.value || 'QR is not ready to print.')
  const name = sos35Escape(props.data?.shop?.name || 'AL MODINA COMPUTERS LIMITED')
  const job = sos35Escape(sos35Job())
  const device = sos35Escape(sos35Device().slice(0, 55))
  const serial = sos35Escape(sos35Serial().slice(0, 38))
  const customerText = sos35Customer().trim()
  const customer = sos35Escape(customerText || 'Customer not recorded')
  const phone = sos35Escape(sos35Phone().slice(0, 26))
  const problemText = sos35Problem().replace(/\s+/g, ' ').trim()
  const problem = sos35Escape(problemText || 'Not recorded')
  const compactName = customerText.length > 28 ? ' compact-name' : ''
  const compactFault = problemText.length > 75 ? ' compact-fault' : ''
  const serialLine = serial && !compactName ? `<div class="serial">S/N: ${serial}</div>` : ''
  const barcode = sos35BarcodeImage.value ? `<img class="code128" alt="Code 128 job barcode" src="${sos35BarcodeImage.value}">` : ''
  // QR links to the service job only; no personal information is encoded in it.
  return `<!doctype html><html><head><meta charset="utf-8"><title>Service Sticker ${job}</title><style>
    @page{size:50mm 30mm;margin:0}
    *{box-sizing:border-box}
    html,body{width:50mm;height:30mm;margin:0;padding:0;background:#fff;color:#17120e;font-family:Arial,"Noto Sans Bengali","Hind Siliguri",sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}
    .label{width:50mm;height:30mm;padding:.85mm 1mm .65mm;overflow:hidden;display:flex;flex-direction:column;gap:.22mm}
    .top{height:15.4mm;flex:0 0 15.4mm;display:flex;align-items:flex-start;gap:.9mm;overflow:hidden;min-width:0}
    .qr{width:13.5mm;height:13.5mm;flex:0 0 13.5mm;object-fit:contain;image-rendering:pixelated}
    .meta{min-width:0;flex:1;height:15.4mm;display:flex;flex-direction:column;gap:.14mm;overflow:hidden}
    .brand{font-size:5.2pt;font-weight:800;line-height:1.04;overflow:hidden;max-height:3.8mm;overflow-wrap:anywhere}
    .job{font-size:6.6pt;font-weight:900;line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .customer{font-size:9.2pt;font-weight:900;line-height:1.05;white-space:normal;overflow-wrap:anywhere;overflow:hidden;max-height:6.9mm}
    .mobile{font-size:7.7pt;font-weight:800;line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .device{font-size:5.8pt;font-weight:600;line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .serial{font-size:5pt;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .meta.compact-name .customer{font-size:7.8pt;max-height:6.1mm}
    .meta.compact-name .device,.meta.compact-name .serial{display:none}
    .fault{height:7mm;flex:0 0 7mm;margin:0;padding-top:.25mm;border-top:.15mm solid #2d251c;font-size:7.7pt;font-weight:800;line-height:1.06;overflow-wrap:anywhere;overflow:hidden;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2}
    .fault.compact-fault{font-size:6.7pt;line-height:1.06}
    .code128{width:100%;height:5.5mm;flex:0 0 5.5mm;object-fit:fill;display:block}
    @media screen{body{width:50mm;min-height:30mm}}
  </style></head><body><div class="label" data-sos-sticker-layout="SOS_STICKER_LAYOUT_V8_20261116">
    <div class="top"><img class="qr" alt="QR for ${job}" src="${sos35QrImage.value}">
      <div class="meta${compactName}"><div class="brand">${name}</div><div class="job">${job}</div>
        <div class="customer">${customer}</div><div class="mobile">Mobile: ${phone || '—'}</div>
        <div class="device">${device}</div>${serialLine}
      </div></div>
    <div class="fault${compactFault}">Problem: ${problem}</div>
    ${barcode}
  </div></body></html>`
}
async function sos35Print() {
  if (!sos35QrImage.value) { sos35Error.value = 'Generate the QR before printing.'; return }
  // Isolated print document, preventing A4/thermal CSS from affecting sticker dimensions.
  let iframe = null
  try {
    iframe = document.createElement('iframe')
    iframe.style.cssText = 'position:fixed;width:0;height:0;opacity:0;border:0;pointer-events:none;'
    iframe.setAttribute('aria-hidden', 'true')
    document.body.appendChild(iframe)
    const doc = iframe.contentDocument
    doc.open(); doc.write(sos35Html()); doc.close()
    await new Promise((resolve, reject) => {
      const imageNodes = [...doc.images]
      if (!imageNodes.length) return resolve()
      let remaining = imageNodes.length
      const finished = () => { if (--remaining === 0) resolve() }
      imageNodes.forEach(img => {
        if (img.complete && img.naturalWidth) return finished()
        img.addEventListener('load', finished, { once: true })
        img.addEventListener('error', () => reject(Error('Sticker image failed to load.')), { once: true })
      })
      setTimeout(() => reject(Error('Sticker image loading timed out.')), 7000)
    })
    await sos35NextTick()
    iframe.contentWindow?.focus()
    iframe.contentWindow?.print()
    setTimeout(() => iframe?.remove(), 45000)
  } catch (e) {
    iframe?.remove()
    sos35Error.value = e?.message || 'Sticker printing failed.'
  }
}

import JsBarcode from "jsbarcode";

import { ref, computed, watch, nextTick } from "vue";
import QRCode from "qrcode";

const props = defineProps({ data: { type: Object, required: true } });
const emit = defineEmits(["close"]);
// Print format initialized at the top of the script (6.83).
const qr = ref("");

const serviceBarcodeSrc = computed(() => {
  const value = String(job.value.name || "").trim();
  if (!value) return "";

  try {
    const svg = document.createElementNS(
      "http://www.w3.org/2000/svg", "svg"
    );

    // SOS_RECEIPT_READABILITY_V26 — print clean Code 128 bars; job ID is printed separately.
    JsBarcode(svg, value, {
      format: "CODE128",
      displayValue: false,
      width: 2.2,
      height: 62,
      margin: 10,
      background: "#ffffff",
      lineColor: "#000000"
    });

    return "data:image/svg+xml;charset=utf-8," +
      encodeURIComponent(
        new XMLSerializer().serializeToString(svg)
      );
  } catch (error) {
    console.error("Barcode generation:", error);
    return "";
  }
});

const job = computed(() => props.data.job || {});
// SOS_CUSTOMER_RECEIPT_COMPONENTS_V25: exact saved intake rows, never parts from shop stock.
const sos25Components = computed(() => {
  const rows = props.data?.job?.received_components;
  return Array.isArray(rows) ? rows : [];
});
const sos25Wide = computed(() => sos683Paper.value.width >= 175);
const sos25Text = (value) => String(value ?? '').trim() || '—';
const sos25Qty = (value) => {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? String(Number(n.toFixed(3))) : '—';
};

// SOS_RECEIVED_COMPONENTS_PRINT_V24: read-only customer property; no repair parts.
const sos24ReceivedComponents = computed(() => {
  const rows = props.data?.job?.received_components;
  return Array.isArray(rows) ? rows : [];
});
// A5/thermal remain legible as compact entries; wide pages use columns.
const sos24WideComponents = computed(() => sos683Paper.value.width >= 175);
function sos24Text(value) {
  const result = String(value ?? '').trim();
  return result || '—';
}
function sos24Quantity(value) {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? String(parseFloat(num.toFixed(3))) : '—';
}

const shop = computed(() => props.data.shop || {});
const amount = computed(() => new Intl.NumberFormat("en-BD", {
  minimumFractionDigits: 2, maximumFractionDigits: 2
}).format(Number(job.value.estimated_cost || 0)));
// SOS_RECEIPT_READABILITY_V26 — prioritize important customer details per physical paper width.
const sos26Has = (v) => String(v ?? '').trim().length > 0;
const sos26IsThermal = computed(() => sos683Paper.value.width <= 100);
function sos26ScaledFont(text, width, kind) {
  const chars = Array.from(String(text ?? '').trim()).length;
  const base = kind === 'name'
    ? (width <= 58 ? 13 : width <= 80 ? 16 : width <= 100 ? 18 : width <= 148 ? 21 : 24)
    : (width <= 58 ? 12.5 : width <= 80 ? 15 : width <= 100 ? 16 : width <= 148 ? 19 : 21);
  const factor = chars > 44 ? .70 : chars > 32 ? .80 : chars > 23 ? .90 : 1;
  return `${Math.max(width <= 58 ? 11 : 13, Math.round(base * factor))}px`;
}
const sos26NameStyle = computed(() => ({fontSize: sos26ScaledFont(job.value.customer_name, sos683Paper.value.width, 'name')}));
const sos26PhoneStyle = computed(() => ({fontSize: sos26ScaledFont(job.value.mobile, sos683Paper.value.width, 'phone')}));

const deviceName = computed(() => [
  job.value.device_type, job.value.brand, job.value.device_model
].filter(Boolean).join(" / "));

watch(() => job.value.name, async (name) => {
  qr.value = "";
  if (!name) return;
  try {
    // SOS_RECEIPT_LINK_QR_629: Deep link, never a customer name/mobile.
    const mobileLink = new URL('/servicing-os', window.location.origin);
    mobileLink.searchParams.set('service_job', name);
    qr.value = await QRCode.toDataURL(mobileLink.href, {
      width: 180, margin: 1, errorCorrectionLevel: "M"
    });
  } catch (e) { console.error("Receipt QR error:", e); }
}, { immediate: true });

// SOS_RECEIPT_ISOLATED_PRINT_V27 — print ONLY the visible receipt, never the full Vue application.
// Current-page @media print rules hide large sections of the application; they can
// produce empty paper in Safari. Freeze the actual preview's computed styles into
// an independent document so app-wide print styles cannot affect the customer receipt.
function sos27CopyRenderedStyles(source, target) {
  const pending = [[source, target]]
  while (pending.length) {
    const [from, to] = pending.pop()
    const computed = window.getComputedStyle(from)
    const declarations = []
    for (let i = 0; i < computed.length; i++) {
      const name = computed[i]
      const value = computed.getPropertyValue(name)
      if (value) declarations.push(`${name}:${value};`)
    }
    // Computed styles preserve V25/V26 receipt typography, labels, barcode
    // dimensions, received-component rows and printer-size-specific layout.
    to.setAttribute('style', declarations.join(''))
    for (let i = from.children.length - 1; i >= 0; i--) {
      pending.push([from.children[i], to.children[i]])
    }
  }
}

async function sos27PrintWindowReady(win) {
  const doc = win.document
  // Data-URL QR/barcode images should be ready before the print dialog opens.
  const images = Array.from(doc.querySelectorAll('#sos27-print-root img'))
  await Promise.all(images.map(img => {
    if (img.complete) return Promise.resolve()
    return new Promise(resolve => {
      const finish = () => resolve()
      img.addEventListener('load', finish, { once: true })
      img.addEventListener('error', finish, { once: true })
      win.setTimeout(finish, 3500)
    })
  }))
  try { if (doc.fonts?.ready) await doc.fonts.ready } catch (_) { /* font fallback available */ }
  await new Promise(resolve => win.setTimeout(resolve, 250))
}

async function printReceipt() {
  // The 50x30 sticker uses its own, already-working QR label print pipeline.
  if (format.value === 'sticker') { await sos35Print(); return }

  const original = document.getElementById('servicing-receipt-paper')
  if (!original || !original.textContent?.trim()) {
    window.alert('Receipt content is not ready. Open the receipt preview and try again.')
    return
  }

  const paper = sos683Paper.value
  const w = Number(paper.width)
  const h = Number(paper.height)
  if (!Number.isFinite(w) || !Number.isFinite(h) || w < 40 || w > 216 || h < 60 || h > 420) {
    window.alert('Invalid selected paper dimensions.')
    return
  }

  // Open during the ORIGINAL user click, before any await, for Safari pop-up rules.
  const win = window.open('', '_blank', 'width=900,height=780')
  if (!win) {
    window.alert('Safari blocked the receipt print window. Allow pop-ups for this SERVICING OS address and try again.')
    return
  }

  try {
    const copy = original.cloneNode(true)
    sos27CopyRenderedStyles(original, copy)
    copy.removeAttribute('id')
    copy.setAttribute('data-sos27-print', 'SOS_RECEIPT_ISOLATED_PRINT_V27')
    // Keep the actual paper dimensions but remove screen-only preview constraints.
    copy.style.setProperty('box-sizing', 'border-box', 'important')
    copy.style.setProperty('width', `${w}mm`, 'important')
    copy.style.setProperty('max-width', 'none', 'important')
    copy.style.setProperty('min-height', '0', 'important')
    copy.style.setProperty('height', 'auto', 'important')
    copy.style.setProperty('max-height', 'none', 'important')
    copy.style.setProperty('position', 'relative', 'important')
    copy.style.setProperty('top', 'auto', 'important')
    copy.style.setProperty('left', 'auto', 'important')
    copy.style.setProperty('overflow', 'visible', 'important')
    copy.style.setProperty('box-shadow', 'none', 'important')
    copy.style.setProperty('margin', '0', 'important')
    copy.style.setProperty('background', '#ffffff', 'important')
    copy.style.setProperty('color', '#111111', 'important')

    const content = copy.outerHTML
    const doc = win.document
    doc.open()
    doc.write(`<!doctype html><html><head><meta charset="utf-8"><title>Service Receipt</title>
      <style>
        @page { size: ${w}mm ${h}mm; margin: 0; }
        html, body { box-sizing: border-box; margin: 0; padding: 0; background: white; color: #111; }
        body { width: ${w}mm; }
        *, *::before, *::after { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        #sos27-print-root { margin: 0; padding: 0; width: ${w}mm; }
        #sos27-controls { display: none; }
        @media screen {
          html, body { width: auto; min-height: 100%; background: #eee8df; }
          #sos27-controls { display: flex; align-items: center; justify-content: space-between;
             gap: 12px; padding: 12px 16px; background: #fff8f0; border-bottom: 1px solid #dccab4;
             font: 13px Arial, sans-serif; color: #483322; position: sticky; top: 0; z-index: 5; }
          #sos27-print-now { background: #785337; color: #fff; border: 0; border-radius: 9px;
             padding: 11px 18px; font-weight: 800; cursor: pointer; }
          #sos27-print-root { margin: 16px auto 30px; background: #fff; box-shadow: 0 3px 18px #3332; }
        }
        @media print {
          #sos27-controls { display: none !important; }
          html, body, #sos27-print-root { margin: 0 !important; padding: 0 !important;
             box-shadow: none !important; background: white !important; }
          #sos27-print-root { width: ${w}mm !important; }
        }
      </style></head><body>
      <div id="sos27-controls"><span>Service Receipt · ${w} × ${h} mm</span>
      <button type="button" id="sos27-print-now">Print / Reprint Receipt</button></div>
      <main id="sos27-print-root">${content}</main>
      </body></html>`)
    doc.close()

    // Manual button remains available if Safari blocks automatic print()
    // after asynchronous font/image loading.
    doc.getElementById('sos27-print-now')?.addEventListener('click', () => {
      win.focus()
      win.print()
    })
    await sos27PrintWindowReady(win)
    if (!win.closed) {
      win.focus()
      win.print()
    }
  } catch (error) {
    console.error('SERVICING OS V27 receipt print:', error)
    if (!win.closed) {
      const panel = win.document.getElementById('sos27-controls')
      if (panel) panel.insertAdjacentText('beforeend', ' · Automatic printing failed; use Print button.')
    }
    window.alert('Could not start automatic printing. Use the Print button in the receipt window, or check the browser console.')
  }
}
</script>

<template>
  <div class="sr-overlay sos683-overlay" @click.capture="sos35ClickCapture" role="dialog" aria-modal="true" aria-label="Service receipt preview">
    <div class="sr-dialog sos683-dialog">
      <header class="sr-toolbar sos683-header">
        <div><strong>Service Receipt Preview</strong><div class="sr-muted">{{ job.name }}</div></div>
        <button type="button" @click="emit('close')">Close</button>
      </header>
      <!-- SOS_RECEIVE_PRINT_STUDIO_683: brand-matched print options -->
      <nav class="sr-toolbar sr-actions sos683-actions" aria-label="Receipt paper and print options">
        <!-- SOS_PRINT_PRESETS_V18_BEGIN: permanent quick formats; existing select remains below -->
        <div class="sos684-presets" data-sos-print-presets="SOS_PRINT_PRESETS_V18" role="group" aria-label="Common paper sizes">
          <div class="sos684-presets-intro">
            <strong>QUICK PAPER FORMATS</strong>
            <span>Choose a format, then select Print / Reprint Receipt</span>
          </div>
          <div class="sos684-presets-grid">
            <button type="button" class="sos684-preset" :class="{ 'sos684-preset--active': format === 'thermal' }" :aria-pressed="format === 'thermal'" @click="format = 'thermal'">
              <span class="sos684-preset-title">80 mm Thermal</span><small>POS receipt</small>
            </button>
            <button type="button" class="sos684-preset" :class="{ 'sos684-preset--active': format === 'sticker' }" :aria-pressed="format === 'sticker'" @click="format = 'sticker'">
              <span class="sos684-preset-title">50 × 30 mm</span><small>QR device sticker</small>
            </button>
            <button type="button" class="sos684-preset" :class="{ 'sos684-preset--active': format === 'a4' }" :aria-pressed="format === 'a4'" @click="format = 'a4'">
              <span class="sos684-preset-title">A4</span><small>210 × 297 mm</small>
            </button>
            <button type="button" class="sos684-preset" :class="{ 'sos684-preset--active': format === 'a5' }" :aria-pressed="format === 'a5'" @click="format = 'a5'">
              <span class="sos684-preset-title">A5</span><small>148 × 210 mm</small>
            </button>
            <button type="button" class="sos684-preset" :class="{ 'sos684-preset--active': format === 'letter' }" :aria-pressed="format === 'letter'" @click="format = 'letter'">
              <span class="sos684-preset-title">Letter</span><small>216 × 279 mm</small>
            </button>
          </div>
        </div>
        <!-- SOS_PRINT_PRESETS_V18_END -->
        <label class="sos683-paper-control" for="sos683-format-select">
          <span>PRINT LAYOUT / PAPER SIZE</span>
          <select id="sos683-format-select" v-model="format" aria-label="Print layout and paper size">
            <optgroup label="Full page / Standard">
              <option value="a4">A4 · 210 × 297 mm</option>
              <option value="a5">A5 · 148 × 210 mm</option>
              <option value="letter">US Letter · 216 × 279 mm</option>
              <option value="b5">B5 · 176 × 250 mm</option>
            </optgroup>
            <optgroup label="Thermal receipt / POS rolls">
              <option value="thermal58">58 mm thermal</option>
              <option value="thermal76">76 mm thermal</option>
              <option value="thermal">80 mm thermal</option>
              <option value="thermal100">100 mm POS roll</option>
            </optgroup>
            <optgroup label="Custom and label">
              <option value="custom">Custom paper size (mm)</option>
              <option value="sticker">QR Sticker · 50 × 30 mm</option>
            </optgroup>
          </select>
        </label>
        <label v-if="sos683IsRoll" class="sos683-number-control">
          <span>ROLL LENGTH (MM)</span>
          <input type="number" min="80" max="420" step="5" v-model.number="sos683RollLength" aria-label="Thermal roll length in millimetres" />
        </label>
        <template v-if="format === 'custom'">
          <label class="sos683-number-control"><span>WIDTH (MM)</span><input type="number" min="40" max="216" v-model.number="sos683CustomWidth" /></label>
          <label class="sos683-number-control"><span>HEIGHT (MM)</span><input type="number" min="60" max="420" v-model.number="sos683CustomHeight" /></label>
        </template>
        <div class="sos683-paper-note" v-if="format === 'sticker'">For other QR label sizes use the separate <strong>Print QR Sticker</strong> tool in Customer History.</div>
        <div class="sos683-paper-note" v-else>Choose the matching paper setting in your printer dialog. Preview uses exact millimetre dimensions.</div>
        <button type="button" class="sr-print sos683-print" @click="printReceipt" data-sos-sticker-print="1">
          {{ format === 'sticker' ? 'Print QR Sticker' : 'Print / Reprint Receipt' }}
        </button>
      </nav>
      <!-- SOS_632_RECEIPT_DETAILS_QR: Full customer name, mobile, fault, and QR on the paper receipt. -->
      
      <!-- SOS_635_QR_INSIDE_RECEIPT_MODAL: sticker preview replaces original sticker paper only for selected mode. -->
      <section v-if="sos35Sticker" class="sos35-preview-shell" aria-label="QR sticker preview inside service receipt modal">
        <div class="sos35-utilities">
          <label>QR link base (phone-reachable address)
            <input v-model.trim="sos35Host" type="url" placeholder="http://192.168.0.100:8005" autocomplete="url" />
          </label>
          <button type="button" class="sos35-print-button" :disabled="!sos35QrImage" @click="sos35Print">Print QR Sticker 50 × 30 mm</button>
        </div>
        <p v-if="sos35Error" class="sos35-error" role="alert">{{ sos35Error }}</p>
        <div class="sos35-sticker-stage">
          <div class="sos35-label" data-sos-sticker-layout="SOS_STICKER_LAYOUT_V8_20261116">
            <div class="sos35-top">
              <img v-if="sos35QrImage" :src="sos35QrImage" alt="Scannable QR code for this service job" />
              <span v-else class="sos35-qr-missing">QR pending</span>
              <div class="sos35-words" :class="{ 'sos35-compact-name': sos35Customer().length > 28 }">
                 <strong class="sos35-shop">{{ shop.name || 'AL MODINA COMPUTERS LIMITED' }}</strong>
                 <strong class="sos35-id">{{ job.name }}</strong>
                 <strong class="sos35-customer">{{ sos35Customer() || 'Customer not recorded' }}</strong>
                 <strong class="sos35-mobile">Mobile: {{ sos35Phone() || '—' }}</strong>
                 <small class="sos35-device">{{ sos35Device() }}</small>
                 <small v-if="sos35Serial() && sos35Customer().length <= 28" class="sos35-serial">S/N: {{ sos35Serial() }}</small>
               </div>
             </div>
             <div class="sos35-fault" :class="{ 'sos35-compact-fault': sos35Problem().length > 75 }">Problem: {{ sos35Problem() || 'Not recorded' }}</div>
             <img v-if="sos35BarcodeImage" class="sos35-barcode" :src="sos35BarcodeImage" alt="Service Job Code 128 barcode" />
            
          </div>
        </div>
        <section class="sos35-sticker-full-problem" aria-label="Full reported problems">
          <h4>Reported Problem / জানানো সব সমস্যা — সম্পূর্ণ বিবরণ</h4>
          <p>{{ sos35Problem() || 'Not recorded' }}</p>
        </section>
        <p class="sos35-hint"><strong>Sticker layout V8</strong> · Scan with a phone on your shop Wi-Fi. QR contains the job link only; staff must sign in to view customer information.</p>
      </section>

      <div class="sr-preview" v-show="!sos35Sticker">
        <article id="servicing-receipt-paper" :style="sos683PaperStyle"
                 :class="['sr-paper', 'sr-' + format, 'sos683-paper', { 'sos26-roll': sos683IsRoll, 'sos26-roll58': sos683Paper.width <= 58 }]">
          
          
<template v-if="format === 'sticker'">
  <div class="sr-barcode-sticker">
    <div class="sr-sticker-title">
      {{ shop.name }}
    </div>

    <img
      v-if="serviceBarcodeSrc"
      :src="serviceBarcodeSrc"
      class="sr-sticker-barcode"
      alt="Service Job Code 128 barcode"
    />

    <div class="sr-sticker-device-info">
      {{ deviceName }}
    </div>

    <div class="sr-sticker-contact">
      {{ job.customer_name }} · {{ job.mobile }}
    </div>
  </div>
</template>

          <template v-else>
<header class="sr-company">
            <h1>{{ shop.name }}</h1>
            <p>{{ shop.address || 'Mawna Chowrasta, Sreepur, Gazipur, Bangladesh' }}</p>
            <p v-if="shop.phone">Phone: {{ shop.phone }}</p>
          </header>
          <h2 class="sr-heading">SERVICE RECEIVE RECEIPT</h2>
          <div class="sr-line"><span>Job No.</span><strong>{{ job.name }}</strong></div>
          <div class="sr-line"><span>Received</span><span>{{ job.received_date }}</span></div>
          <div class="sr-line"><span>Status</span><span>{{ job.status }}</span></div>
          <div class="sr-line"><span>Priority</span><span>{{ job.priority }}</span></div>
          <h3>CUSTOMER DETAILS</h3>
          <!-- SOS_RECEIPT_READABILITY_V26: full-width priority contact on paper and screen. -->
          <div class="sr-customer26" data-sos-receipt-version="SOS_RECEIPT_READABILITY_V26" aria-label="Customer name and mobile number">
            <div class="sr-customer26-field sr-customer26-name">
              <span>Customer / গ্রাহক</span><strong :style="sos26NameStyle">{{ job.customer_name || '—' }}</strong>
            </div>
            <div class="sr-customer26-field sr-customer26-phone">
              <span>Mobile / মোবাইল</span><strong :style="sos26PhoneStyle">{{ job.mobile || '—' }}</strong>
            </div>
          </div>
          <h3>DEVICE DETAILS</h3>
          <div class="sr-line"><span>Device</span><span>{{ deviceName }}</span></div>
          <div v-if="job.serial_number" class="sr-device-serial26"><span>Device S/N</span><strong>{{ job.serial_number }}</strong></div>
          <section class="sr-description"><strong>Reported Problem</strong><p>{{ job.reported_problem || "Not recorded" }}</p></section>
          <section class="sr-description"><strong>Accessories Received</strong><p>{{ job.accessories_received || "None recorded" }}</p></section>
          <!-- SOS_CUSTOMER_RECEIPT_COMPONENTS_V25: part of actual customer receipt paper. -->
          <section class="sr-custody25" data-sos-customer-receipt="SOS_CUSTOMER_RECEIPT_COMPONENTS_V25"
            :class="sos25Wide ? 'is-wide' : sos683Paper.width <= 100 ? 'is-thermal' : 'is-small'"
            aria-label="Device intake customer property received components">
            <div class="sr-custody25-eyebrow">DEVICE INTAKE · CUSTOMER PROPERTY</div>
            <h3 class="sr-custody25-title">Components Received <small>· গ্রাহকের জমা দেওয়া যন্ত্রাংশ</small></h3>
            <p class="sr-custody25-note">Customer-owned items brought with this device · Not repair parts or shop inventory.</p>
            <p v-if="!sos25Components.length" class="sr-custody25-empty">No individual components recorded at device intake.</p>
            <template v-else>
              <table v-if="sos25Wide" class="sr-custody25-table">
                <thead><tr>
                  <th>Component</th><th>Type</th><th>Brand</th><th>Capacity / Specification</th>
                  <th>Quantity</th><th>Model</th><th>Serial Number</th><th>Condition at Receive</th><th>Remarks</th>
                </tr></thead>
                <tbody>
                  <tr v-for="(part, index) in sos25Components" :key="index">
                    <td>{{ index + 1 }}</td>
                    <td>{{ sos25Text(part.component_type) }}</td>
                    <td>{{ sos25Text(part.brand) }}</td>
                    <td>{{ sos25Text(part.capacity) }}</td>
                    <td>{{ sos25Qty(part.qty) }}</td>
                    <td>{{ sos25Text(part.model) }}</td>
                    <td>{{ sos25Text(part.serial_number) }}</td>
                    <td>{{ sos25Text(part.condition_received) }}</td>
                    <td>{{ sos25Text(part.remarks) }}</td>
                  </tr>
                </tbody>
              </table>
              <!-- SOS_RECEIPT_READABILITY_V26: compact, nonempty fields only on thermal rolls. -->
              <div v-else-if="sos26IsThermal" class="sr-custody26-list">
                <div v-for="(part, index) in sos25Components" :key="index" class="sr-custody26-row">
                  <div class="sr-custody26-head">
                    <strong>{{ index + 1 }}. {{ sos25Text(part.component_type) }}<template v-if="sos26Has(part.brand)"> · {{ part.brand }}</template></strong>
                    <b v-if="sos26Has(part.qty)" class="sr-custody26-qty">×{{ sos25Qty(part.qty) }}</b>
                  </div>
                  <div v-if="sos26Has(part.capacity) || sos26Has(part.model)" class="sr-custody26-sub">
                    <span v-if="sos26Has(part.capacity)"><b>SPEC</b> {{ part.capacity }}</span>
                    <span v-if="sos26Has(part.model)"><b>MODEL</b> {{ part.model }}</span>
                  </div>
                  <div v-if="sos26Has(part.serial_number)" class="sr-custody26-serial"><b>S/N</b> {{ part.serial_number }}</div>
                  <div v-if="sos26Has(part.condition_received) || sos26Has(part.remarks)" class="sr-custody26-sub">
                    <span v-if="sos26Has(part.condition_received)"><b>CONDITION</b> {{ part.condition_received }}</span>
                    <span v-if="sos26Has(part.remarks)"><b>NOTE</b> {{ part.remarks }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="sr-custody25-list">
                <div v-for="(part, index) in sos25Components" :key="index" class="sr-custody25-item">
                  <div class="sr-custody25-index">Component {{ index + 1 }}</div>
                  <div class="sr-custody25-fields">
                    <div><b>Type</b><span>{{ sos25Text(part.component_type) }}</span></div>
                    <div><b>Brand</b><span>{{ sos25Text(part.brand) }}</span></div>
                    <div><b>Capacity / Specification</b><span>{{ sos25Text(part.capacity) }}</span></div>
                    <div><b>Quantity</b><span>{{ sos25Qty(part.qty) }}</span></div>
                    <div><b>Model</b><span>{{ sos25Text(part.model) }}</span></div>
                    <div><b>Serial Number</b><span>{{ sos25Text(part.serial_number) }}</span></div>
                    <div><b>Condition at Receive</b><span>{{ sos25Text(part.condition_received) }}</span></div>
                    <div><b>Remarks</b><span>{{ sos25Text(part.remarks) }}</span></div>
                  </div>
                </div>
              </div>
            </template>
          </section>
          <div v-if="job.expected_delivery" class="sr-line"><span>Expected Delivery</span><span>{{ job.expected_delivery }}</span></div>
          <div class="sr-total"><span>Estimated Repair Cost</span><strong>{{ shop.currency }} {{ amount }}</strong></div>
          <div class="sr-qr"><img v-if="qr" :src="qr" alt="Service Job QR code"/><strong>{{ job.name }}</strong></div>
          <p class="sr-notice">This is a device receiving acknowledgment, not a payment receipt. Estimated repair charges may change after diagnosis and customer approval. Please retain this receipt when collecting your device.</p>
          
<div class="sr-receipt-barcode">
  <img
    v-if="serviceBarcodeSrc"
    :src="serviceBarcodeSrc"
    alt="Service Job Code 128 barcode"
  />
  <strong class="sr-barcode26-number">{{ job.name }}</strong>
  <div>Scan to find this Service Job</div>
</div>
<footer class="sr-signatures"><span>Received By</span><span>Customer Signature</span></footer>
                  </template>
        </article>
      </div>
    </div>
  </div>
</template>

<style>
.sr-overlay{position:fixed;inset:0;z-index:99999;display:flex;justify-content:center;align-items:center;padding:10px;background:rgba(15,23,42,.78)}
.sr-dialog{width:100%;max-width:850px;max-height:96dvh;display:flex;flex-direction:column;overflow:hidden;background:#f1f5f9;border-radius:14px}
.sr-toolbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:12px;background:#fff;color:#0f172a;border-bottom:1px solid #cbd5e1}
.sr-muted{font-size:12px;color:#64748b}
.sr-toolbar button{border:1px solid #cbd5e1;border-radius:8px;padding:9px 12px;background:#fff;color:#0f172a;font-size:13px;cursor:pointer}
.sr-toolbar button.selected{background:#2563eb;color:#fff;border-color:#2563eb}
.sr-toolbar button.sr-print{background:#059669;color:#fff;border-color:#059669;font-weight:bold}
.sr-preview{overflow:auto;padding:16px}
.sr-paper{box-sizing:border-box;background:#fff;color:#111;margin:0 auto;font-family:Arial,sans-serif;line-height:1.4;overflow-wrap:anywhere;box-shadow:0 3px 16px #0002}
.sr-thermal{width:80mm;max-width:100%;padding:4mm;font-size:10px}
.sr-a5{width:148mm;max-width:100%;min-height:210mm;padding:12mm;font-size:12px}
.sr-company{text-align:center;margin-bottom:12px}
.sr-company h1{font-size:1.35em;font-weight:800;margin:0;text-transform:uppercase}
.sr-company p{margin:3px 0}
.sr-heading{font-size:1.1em;font-weight:800;text-align:center;padding:8px 0;margin:12px 0;border-top:2px solid;border-bottom:2px solid}
.sr-line{display:flex;justify-content:space-between;gap:10px;padding:4px 0}
.sr-line>:first-child{flex:0 0 34%}
.sr-line>:last-child{text-align:right;min-width:0}
.sr-paper h3{font-size:1em;font-weight:800;margin:14px 0 6px;border-bottom:1px solid;padding-bottom:4px}
.sr-description{margin-top:12px}
.sr-description p{white-space:pre-wrap;margin:4px 0}
.sr-total{display:flex;justify-content:space-between;gap:10px;margin-top:16px;padding:10px 0;border-top:2px solid;border-bottom:2px solid;font-weight:bold}
.sr-qr{display:flex;align-items:center;flex-direction:column;gap:4px;margin:15px 0;font-size:10px}
.sr-qr img{width:92px;height:92px}
.sr-notice{font-size:.9em;text-align:center;border-top:1px dashed #777;padding-top:10px}
.sr-signatures{display:flex;justify-content:space-between;gap:20px;margin-top:38px;font-size:.9em}
.sr-signatures span{flex:1;border-top:1px solid #555;text-align:center;padding-top:5px}
@media print{
  @page{margin:0}
  body:has(.sr-overlay) *{visibility:hidden!important}
  body:has(.sr-overlay) .sr-paper,body:has(.sr-overlay) .sr-paper *{visibility:visible!important}
  body:has(.sr-overlay) .sr-overlay,body:has(.sr-overlay) .sr-dialog,body:has(.sr-overlay) .sr-preview{position:static!important;display:block!important;width:100%!important;max-width:none!important;max-height:none!important;overflow:visible!important;padding:0!important;margin:0!important;background:#fff!important;box-shadow:none!important}
  body:has(.sr-overlay) .sr-toolbar{display:none!important}
  body:has(.sr-overlay) .sr-paper{position:absolute!important;top:0!important;left:0!important;margin:0!important;box-shadow:none!important;max-width:none!important}
  body:has(.sr-overlay) .sr-thermal{width:80mm!important;min-height:0!important;padding:3mm 4mm!important}
  body:has(.sr-overlay) .sr-a5{width:148mm!important;min-height:210mm!important;padding:12mm!important}
}

/* A4 receipt */
.sr-a4 {
  width: 210mm;
  max-width: 100%;
  min-height: 297mm;
  padding: 16mm;
  font-size: 13px;
}

/* 50 x 30 mm device sticker */
.sr-sticker {
  width: 50mm;
  height: 30mm;
  max-width: none;
  min-height: 0;
  padding: 1.5mm 2mm;
  font-size: 7px;
  line-height: 1.15;
  overflow: hidden;
}

.sr-sticker-head {
  height: 5mm;
  line-height: 4mm;
  font-size: 8px;
  font-weight: 800;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-bottom: 1px solid #111;
}

.sr-sticker-body {
  height: 21mm;
  display: flex;
  align-items: center;
  gap: 1.5mm;
}

.sr-sticker-qr {
  width: 17mm;
  height: 17mm;
  flex-shrink: 0;
}

.sr-sticker-qr img {
  width: 17mm;
  height: 17mm;
  display: block;
}

.sr-sticker-details {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.sr-sticker-details > * {
  display: block;
  margin-bottom: 1mm;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sr-sticker-job {
  font-size: 8px;
  overflow-wrap: anywhere;
}

.sr-sticker-device,
.sr-sticker-customer {
  white-space: nowrap;
}

.sr-sticker-mobile {
  font-size: 8px;
}

@media print {
  body:has(.sr-overlay) .sr-a4 {
    width: 210mm !important;
    min-height: 297mm !important;
    padding: 16mm !important;
  }

  body:has(.sr-overlay) .sr-sticker {
    width: 50mm !important;
    height: 30mm !important;
    min-height: 0 !important;
    padding: 1.5mm 2mm !important;
    overflow: hidden !important;
  }

  body:has(.sr-overlay) .sr-sticker-qr img {
    width: 17mm !important;
    height: 17mm !important;
  }
}


/* Step 6.9: Code 128 printing */
.sr-receipt-barcode {
  text-align: center;
  margin: 14px auto;
  page-break-inside: avoid;
  break-inside: avoid;
}

.sr-receipt-barcode img {
  display: block;
  width: 100%;
  max-width: 78mm;
  height: auto;
  margin: 0 auto;
}

.sr-receipt-barcode > div {
  font-size: 9px;
  margin-top: 3px;
}

.sr-barcode-sticker {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #000;
  background: #fff;
  text-align: center;
}

.sr-sticker-title {
  font-size: 7px;
  line-height: 1.1;
  font-weight: 800;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
}

.sr-sticker-barcode {
  display: block;
  width: 100%;
  max-width: 45mm;
  height: 13mm;
  object-fit: fill;
  margin: 1mm auto;
}

.sr-sticker-device-info {
  width: 100%;
  font-size: 7px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sr-sticker-contact {
  width: 100%;
  font-size: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media print {
  .sr-receipt-barcode,
  .sr-barcode-sticker {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }

  .sr-sticker-barcode {
    width: 100% !important;
    height: 13mm !important;
  }
}


/* SOS_635_QR_INSIDE_RECEIPT_MODAL — ivory controls; 50x30mm label preview. */
.sos35-preview-shell{padding:16px 18px 20px;background:#faf5eb;color:#443426;display:grid;gap:12px;min-width:0;overflow:auto}
.sos35-utilities{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
.sos35-utilities label{flex:1 1 270px;display:grid;gap:5px;font-size:11px;font-weight:700;color:#66543f}
.sos35-utilities input{min-height:40px;padding:8px 11px;background:#fff;border:1px solid #d9c9b4;border-radius:9px;color:#352717;font:inherit}
.sos35-print-button{min-height:40px;padding:10px 16px;background:#705137;border:1px solid #705137;border-radius:9px;color:white;font-weight:800;cursor:pointer}
.sos35-print-button:disabled{opacity:.5;cursor:not-allowed}
.sos35-error{background:#fff1eb;border:1px solid #e5b19e;color:#9a3127;font-size:12px;padding:9px 12px;border-radius:9px}
.sos35-sticker-stage{padding:20px 12px;background:#f2e9dc;border:1px solid #e2d4c1;border-radius:12px;display:grid;place-items:center;overflow:auto}
.sos35-label{width:50mm;height:30mm;flex:0 0 auto;box-sizing:border-box;padding:1mm 1.4mm .5mm;background:#fff;color:#18130e;border:1px solid #ddd;display:flex;flex-direction:column;gap:.3mm;font-family:Arial,Helvetica,sans-serif;overflow:hidden;box-shadow:0 3px 12px #241a151c}
.sos35-top{display:flex;align-items:flex-start;gap:.8mm;height:23mm;overflow:hidden}
.sos35-top>img,.sos35-qr-missing{width:14.5mm;height:14.5mm;flex:0 0 14.5mm;object-fit:contain;image-rendering:pixelated}
.sos35-qr-missing{font-size:8px;display:grid;place-items:center;color:#998}
.sos35-words{flex:1;min-width:0;display:flex;flex-direction:column;gap:.3mm;overflow:hidden}
.sos35-words>*{line-height:1.08;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:5.8pt}
.sos35-words>.sos35-shop{font-size:5.8pt;white-space:normal;max-height:4mm}
.sos35-words>.sos35-id{font-size:7pt;white-space:normal;overflow-wrap:anywhere;line-height:1.05}
.sos35-barcode{display:block;width:100%;height:3.7mm;object-fit:fill}
.sos35-footer{text-align:center;line-height:1;font-size:5.2pt}
.sos35-hint{font-size:11px;color:#7c6854;margin:0;line-height:1.45}
.sos35-utilities button:focus-visible,.sos35-utilities input:focus-visible{outline:3px solid #cfab73;outline-offset:2px}
@media(max-width:440px){.sos35-preview-shell{padding:12px}.sos35-sticker-stage{padding:12px 6px}}
@media print{.sos35-preview-shell{display:none!important}}


/* SOS_638_BN_QR_FULL_PROBLEM — only receipt / QR-sticker presentation. */
.sos35-sticker-full-problem {
  padding: 11px 13px; border: 1px solid #dbcbb8; border-radius: 10px;
  background: #fffcf7; color: #493626; min-width: 0;
}
.sos35-sticker-full-problem h4 { margin: 0 0 5px; font-size: 12px; font-weight: 800; }
.sos35-sticker-full-problem p {
  margin: 0; font-size: 12px; line-height: 1.5;
  white-space: pre-wrap; overflow-wrap: anywhere; overflow: visible;
  max-height: none; text-overflow: clip;
}
.sos35-words .sos638-sticker-problem {
  font-size: 5.2pt; font-weight: 650; line-height: 1.12;
  white-space: normal; overflow-wrap: anywhere;
  display: -webkit-box; -webkit-box-orient: vertical;
  -webkit-line-clamp: 3; line-clamp: 3; max-height: 9mm;
}
/* Never truncate reported problems on the full A4/A5/80mm receipt. */
.sr-preview .sr-description, .sr-preview .sr-description p {
  max-height: none !important; overflow: visible !important;
  text-overflow: clip !important; -webkit-line-clamp: unset !important;
  line-clamp: unset !important; white-space: pre-wrap !important;
  overflow-wrap: anywhere !important;
}
@media print {
  .sr-paper .sr-description, .sr-paper .sr-description p {
    max-height: none !important; overflow: visible !important;
    text-overflow: clip !important; -webkit-line-clamp: unset !important;
    line-clamp: unset !important; white-space: pre-wrap !important;
    overflow-wrap: anywhere !important;
  }
  .sr-paper:not(.sos35-label) { height: auto !important; overflow: visible !important; }
  .sos35-sticker-full-problem { display: none !important; }
}


/* SERVICING_OS_STICKER_FONT_FIX_V1_BEGIN */
/* Scoped only to the Service Receive device QR sticker.
   Keep the existing sticker dimensions, colors, QR and field arrangement. */
.sr-sticker.sr-sticker {
  font-size: 11px !important;
  line-height: 1.22 !important;
}
.sr-sticker.sr-sticker :is(div, span, p, small, strong, b, label, time, dt, dd, td, th) {
  font-size: max(11px, 1em) !important;
  line-height: 1.20 !important;
  overflow-wrap: anywhere;
}
.sr-sticker.sr-sticker :is(h1, h2, h3, h4) {
  font-size: max(13px, 1em) !important;
  line-height: 1.16 !important;
}
/* QR/barcode graphics and the physical paper sizes are deliberately untouched. */
/* SERVICING_OS_STICKER_FONT_FIX_V1_END */

/* SOS_50X30_SYMMETRIC_STICKER_V7 — mirror the isolated 50×30mm print layout in the preview. */
.sos35-label {
  width:50mm;height:30mm;padding:.85mm 1mm .65mm;
  border:0;gap:.22mm;box-sizing:border-box;
}
.sos35-top {height:16.2mm;flex:0 0 16.2mm;align-items:flex-start;gap:.9mm;min-width:0;overflow:hidden}
.sos35-top>img,.sos35-qr-missing {width:13.5mm;height:13.5mm;flex:0 0 13.5mm}
.sos35-words {height:16.2mm;flex:1;min-width:0;gap:.14mm;overflow:hidden}
.sos35-words>* {text-overflow:ellipsis;overflow:hidden}
.sos35-words>.sos35-shop {font-size:5.2pt;font-weight:800;line-height:1.04;white-space:normal;max-height:3.8mm;overflow-wrap:anywhere}
.sos35-words>.sos35-id {font-size:6.6pt;font-weight:900;line-height:1.05;white-space:nowrap;max-height:none}
.sos35-words>.sos35-customer {font-size:9.2pt;font-weight:900;line-height:1.05;white-space:normal;overflow-wrap:anywhere;max-height:6.9mm;text-overflow:clip}
.sos35-words>.sos35-mobile {font-size:7.7pt;font-weight:800;line-height:1.05;white-space:nowrap}
.sos35-words>.sos35-device {font-size:5.8pt;font-weight:600;line-height:1.05;white-space:nowrap}
.sos35-words>.sos35-serial {font-size:5pt;line-height:1;white-space:nowrap}
.sos35-words.sos35-compact-name>.sos35-customer {font-size:7.8pt;max-height:6.1mm}
.sos35-words.sos35-compact-name>.sos35-device,.sos35-words.sos35-compact-name>.sos35-serial {display:none}
.sos35-fault {
  margin:0;height:8.1mm;flex:0 0 8.1mm;padding-top:.25mm;border-top:.15mm solid #2d251c;
  font-size:7.7pt;font-weight:800;line-height:1.06;overflow-wrap:anywhere;
  display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;line-clamp:3;
  overflow:hidden;color:#18130e;
}
.sos35-fault.sos35-compact-fault {font-size:6.7pt;line-height:1.06}
.sos35-barcode {height:3.1mm;flex:0 0 3.1mm;object-fit:fill}
@media print {.sos35-preview-shell {display:none!important}}

</style>

<style>

/* SOS_RECEIVE_PRINT_STUDIO_683 — premium ivory modal and physical paper controls. */
.sr-overlay.sos683-overlay{background:rgba(35,26,19,.64)!important;backdrop-filter:blur(5px);padding:18px;align-items:center}
.sr-dialog.sos683-dialog{background:#f9f5ef!important;border:1px solid #dbc9b4;border-radius:18px!important;max-width:1050px!important;max-height:min(92dvh,980px)!important;box-shadow:0 30px 90px rgba(26,18,13,.3);color:#382b23}
.sr-dialog.sos683-dialog .sr-toolbar{background:#fffcf7!important;color:#3b2d25!important;border-bottom:1px solid #e6d8c8;padding:14px 18px!important}
.sr-dialog.sos683-dialog .sr-toolbar strong{color:#35271f;font-size:16px;letter-spacing:-.015em}
.sr-dialog.sos683-dialog .sr-muted{color:#8b705a;font-size:11px;margin-top:4px}
.sr-dialog.sos683-dialog .sr-toolbar button{background:#f6ebe0;color:#70533e;border:1px solid #dfccb8;min-height:37px;border-radius:9px;font-size:12px;font-weight:750}
.sr-dialog.sos683-dialog .sr-toolbar button:hover{background:#edddcb}
.sr-dialog.sos683-dialog .sr-toolbar .sos683-print{background:#805a3e!important;color:#fffaf6!important;border-color:#805a3e!important;padding:10px 17px!important;white-space:nowrap}
.sr-dialog.sos683-dialog .sr-toolbar .sos683-print:hover{background:#65462f!important}
.sr-dialog.sos683-dialog .sr-toolbar.sos683-actions{display:flex;align-items:end;gap:11px;padding:12px 18px!important;flex-wrap:wrap}
.sos683-actions label{display:flex;flex-direction:column;gap:5px;margin:0;font-weight:700;font-size:11px;color:#705640}
.sos683-actions label>span{font-size:10px;font-weight:760;letter-spacing:.07em;color:#8b705a}
.sos683-paper-control{flex:1 1 260px;min-width:190px}
.sos683-number-control{flex:0 1 114px;min-width:100px}
.sos683-actions :is(select,input){width:100%;min-height:38px;box-sizing:border-box;border:1px solid #d8c1aa;background:#fffdfa;color:#3d3027;border-radius:9px;padding:8px 10px;font:inherit;font-size:12px;outline:none}
.sos683-actions :is(select,input):focus-visible{box-shadow:0 0 0 3px rgba(158,119,83,.18);border-color:#a98462}
.sos683-paper-note{font-size:10px;color:#957a63;flex:1 1 160px;line-height:1.35;align-self:center}
.sr-dialog.sos683-dialog .sr-preview{background:#efe6db!important;padding:18px;min-height:90px;overflow:auto;display:block}
.sr-dialog.sos683-dialog .sr-paper.sos683-paper{box-sizing:border-box;width:var(--sos683-width)!important;max-width:none!important;min-height:var(--sos683-min-height)!important;padding:var(--sos683-pad)!important;font-size:var(--sos683-font)!important;position:relative;overflow-wrap:anywhere;box-shadow:0 6px 24px rgba(45,33,23,.12)}
.sr-dialog.sos683-dialog .sr-paper .sr-description p{max-height:none!important;overflow:visible!important;white-space:pre-wrap!important}
.sr-dialog.sos683-dialog .sr-paper .sr-company{margin-bottom:8px}
.sr-dialog.sos683-dialog .sr-paper .sr-company h1{letter-spacing:.012em}
.sr-dialog.sos683-dialog .sr-paper :is(.sr-line,.sr-description){break-inside:avoid}
.sr-dialog.sos683-dialog .sr-paper .sr-qr img{max-width:26mm;max-height:26mm}
@media(max-width:720px){.sr-overlay.sos683-overlay{padding:7px}.sr-dialog.sos683-dialog{max-height:98dvh!important;border-radius:12px!important}.sr-dialog.sos683-dialog .sr-toolbar{padding:11px!important}.sos683-paper-control{flex-basis:100%}.sos683-paper-note{display:none}.sr-dialog.sos683-dialog .sr-preview{padding:10px}}
@media print{
  .sr-overlay.sos683-overlay,.sr-dialog.sos683-dialog,.sr-dialog.sos683-dialog .sr-preview{background:#fff!important;border:0!important;box-shadow:none!important;overflow:visible!important;padding:0!important;max-height:none!important}
  .sr-dialog.sos683-dialog .sr-toolbar,.sr-dialog.sos683-dialog .sos683-actions{display:none!important}
  body:has(.sr-overlay.sos683-overlay) .sr-dialog.sos683-dialog .sr-paper.sos683-paper{width:var(--sos683-width)!important;max-width:none!important;min-height:var(--sos683-min-height)!important;padding:var(--sos683-pad)!important;position:absolute!important;top:0!important;left:0!important;margin:0!important;box-shadow:none!important;background:#fff!important;color:#121212!important;overflow:visible!important}
}

</style>

<style>
/* SOS_PRINT_PRESETS_V18_CSS_BEGIN — screen-only modal controls, never print styling. */
@media screen {
  .sr-dialog.sos683-dialog .sos684-presets {
    width: 100%; flex: 0 0 100%; box-sizing: border-box;
    margin: 0 0 3px; padding: 0 0 13px;
    border-bottom: 1px solid #e7d9c9; color: #463428;
  }
  .sr-dialog.sos683-dialog .sos684-presets-intro {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 8px 14px; flex-wrap: wrap; margin-bottom: 9px;
  }
  .sr-dialog.sos683-dialog .sos684-presets-intro strong {
    font-size: 10px !important; color: #805d43 !important;
    font-weight: 800; letter-spacing: .095em;
  }
  .sr-dialog.sos683-dialog .sos684-presets-intro span {
    font-size: 10px; color: #9a806b;
  }
  .sr-dialog.sos683-dialog .sos684-presets-grid {
    display: grid; width: 100%; grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px; align-items: stretch;
  }
  .sr-dialog.sos683-dialog .sr-toolbar button.sos684-preset {
    display: flex !important; min-width: 0; min-height: 57px;
    padding: 9px 10px !important; flex-direction: column; align-items: flex-start;
    justify-content: center; gap: 3px; text-align: left;
    border: 1px solid #ddcab7 !important; border-radius: 11px !important;
    background: #fffaf3 !important; color: #4a3526 !important;
    box-shadow: inset 0 1px 0 #fff, 0 1px 2px rgba(63,39,23,.035);
    cursor: pointer; transition: border-color .12s, background .12s;
  }
  .sr-dialog.sos683-dialog .sr-toolbar button.sos684-preset:hover {
    background: #f5e8d9 !important; border-color: #b99573 !important;
  }
  .sr-dialog.sos683-dialog .sr-toolbar button.sos684-preset--active,
  .sr-dialog.sos683-dialog .sr-toolbar button.sos684-preset[aria-pressed="true"] {
    color: #fffaf3 !important; background: #805a3e !important;
    border-color: #805a3e !important;
    box-shadow: 0 0 0 2px rgba(128,90,62,.11);
  }
  .sr-dialog.sos683-dialog .sos684-preset-title {
    font-size: 12px !important; font-weight: 800; line-height: 1.15;
    letter-spacing: -.01em; white-space: normal;
  }
  .sr-dialog.sos683-dialog .sr-toolbar .sos684-preset small {
    font-size: 10px; opacity: .82; line-height: 1.15; white-space: normal;
  }
  .sr-dialog.sos683-dialog .sos684-preset:focus-visible {
    outline: 3px solid #cfaa80 !important; outline-offset: 2px;
  }
  .sr-dialog.sos683-dialog .sr-toolbar.sos683-actions {
    flex: 0 0 auto; overflow-y: auto;
    max-height: min(50dvh, 330px);
  }
  @media (max-width: 790px) {
    .sr-dialog.sos683-dialog .sos684-presets-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
  @media (max-width: 470px) {
    .sr-dialog.sos683-dialog .sos684-presets-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px;
    }
    .sr-dialog.sos683-dialog .sr-toolbar button.sos684-preset {
      min-height: 50px; padding: 7px 9px !important;
    }
    .sr-dialog.sos683-dialog .sos684-presets-intro span {display: none}
    .sr-dialog.sos683-dialog .sr-toolbar.sos683-actions {max-height: min(55dvh, 375px)}
  }
}
/* SOS_PRINT_PRESETS_V18_CSS_END */
</style>

<style>
/* SOS_PRINT_ALIGNMENT_V19_RECEIPT_BEGIN
   Controls only. Printed output and print handler remain unchanged. */
@media screen {
  .sr-dialog.sos683-dialog .sr-toolbar.sos683-actions {
    --sos-v19-receipt-h: 46px;
    display: grid !important;
    grid-template-columns: repeat(12, minmax(0, 1fr)) !important;
    align-items: end !important;
    justify-items: stretch !important;
    gap: 11px 12px !important;
    padding: 14px 18px !important;
    box-sizing: border-box !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos684-presets {
    grid-column: 1 / -1 !important;
    flex: initial !important;
    width: 100% !important;
    margin: 0 0 1px !important;
    min-width: 0;
  }
  .sr-dialog.sos683-dialog .sos684-presets-grid {
    display: grid !important;
    grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
    align-items: stretch !important;
    gap: 9px !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > label {
    margin: 0 !important;
    min-width: 0 !important;
    width: 100% !important;
    flex: none !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    align-self: stretch !important;
    justify-content: end !important;
    gap: 7px !important;
    box-sizing: border-box !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > label > span {
    display: block !important;
    min-height: 14px !important;
    line-height: 14px !important;
    margin: 0 !important;
    font-size: 10px !important;
    font-weight: 800 !important;
    letter-spacing: .055em !important;
    color: #80634d !important;
    white-space: normal;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-paper-control {
    grid-column: 1 / -1 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions:has(> .sos683-number-control) > .sos683-paper-control {
    grid-column: span 8 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-number-control {
    grid-column: span 4 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions:has(> .sos683-number-control + .sos683-number-control) > .sos683-paper-control {
    grid-column: span 6 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions:has(> .sos683-number-control + .sos683-number-control) > .sos683-number-control {
    grid-column: span 3 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions :is(select, input) {
    display: block !important;
    box-sizing: border-box !important;
    width: 100% !important;
    min-width: 0 !important;
    height: var(--sos-v19-receipt-h) !important;
    min-height: var(--sos-v19-receipt-h) !important;
    max-height: var(--sos-v19-receipt-h) !important;
    padding: 0 14px !important;
    margin: 0 !important;
    border: 1px solid #d7c4b0 !important;
    border-radius: 12px !important;
    background-color: #fffcf7 !important;
    color: #3c3026 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: normal !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions select {
    -webkit-appearance: none !important;
    appearance: none !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='m5.5 7.5 4.5 5 4.5-5' stroke='%23795842' stroke-width='1.9' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-position: right 13px center !important;
    background-size: 18px 18px !important;
    padding-right: 39px !important;
    cursor: pointer !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions :is(select, input):focus-visible {
    outline: none !important;
    border-color: #946a49 !important;
    box-shadow: 0 0 0 3px rgba(148,106,73,.16) !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-paper-note {
    grid-column: span 8 !important;
    display: block !important;
    min-width: 0 !important;
    width: 100% !important;
    margin: 0 !important;
    flex: none !important;
    align-self: center !important;
    font-size: 11px !important;
    line-height: 1.5 !important;
    color: #856d59 !important;
    overflow-wrap: anywhere;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-paper-note strong {
    font-size: inherit !important;
    font-weight: 800 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > button.sos683-print {
    grid-column: span 4 !important;
    justify-self: stretch !important;
    align-self: center !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    box-sizing: border-box !important;
    width: 100% !important;
    min-width: 0 !important;
    min-height: var(--sos-v19-receipt-h) !important;
    margin: 0 !important;
    padding: 10px 12px !important;
    border-radius: 12px !important;
    line-height: 1.3 !important;
    white-space: normal !important;
    text-align: center !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions .sos684-preset {
    box-sizing: border-box !important;
    width: 100% !important;
    height: 100%;
    min-width: 0 !important;
    border-radius: 12px !important;
  }
}
@media screen and (max-width: 800px) {
  .sr-dialog.sos683-dialog .sos684-presets-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  }
}
@media screen and (max-width: 680px) {
  .sr-dialog.sos683-dialog .sr-toolbar.sos683-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 10px !important;
    padding: 13px 12px !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos684-presets,
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-paper-control,
  .sr-dialog.sos683-dialog .sos683-actions:has(> .sos683-number-control) > .sos683-paper-control,
  .sr-dialog.sos683-dialog .sos683-actions:has(> .sos683-number-control + .sos683-number-control) > .sos683-paper-control,
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-paper-note,
  .sr-dialog.sos683-dialog .sos683-actions > button.sos683-print {
    grid-column: 1 / -1 !important;
  }
  .sr-dialog.sos683-dialog .sos683-actions > .sos683-number-control,
  .sr-dialog.sos683-dialog .sos683-actions:has(> .sos683-number-control + .sos683-number-control) > .sos683-number-control {
    grid-column: span 1 !important;
  }
  .sr-dialog.sos683-dialog .sos684-presets-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}
/* SOS_PRINT_ALIGNMENT_V19_RECEIPT_END */
</style>

<style>
/* SOS_RECEIVED_COMPONENTS_PRINT_V24: custody rows are part of the printable paper only. */
.sr-paper .sr-components-received{margin:10px 0 12px;color:#16110d;break-inside:auto;page-break-inside:auto}
.sr-paper .sr-components-received h3{margin:10px 0 3px;padding-bottom:4px;border-bottom:1px solid #564a42;font-size:1em;line-height:1.24;font-weight:800}
.sr-paper .sr-components-received h3 small{font-size:.78em;font-weight:500}
.sr-paper .sr-components-custody{margin:3px 0 7px;font-size:.78em;color:#5d5046;line-height:1.25}
.sr-paper .sr-components-empty{margin:4px 0 8px;font-size:.86em;color:#5d5046}
.sr-paper .sr-components-wide{max-width:100%;overflow-x:auto}
.sr-paper .sr-components-wide table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:.74em;line-height:1.3}
.sr-paper .sr-components-wide th,.sr-paper .sr-components-wide td{padding:4px 3px;text-align:left;vertical-align:top;border:1px solid #b9afa5;overflow-wrap:anywhere;word-break:break-word}
.sr-paper .sr-components-wide th{background:#efebe6;color:#251e18;font-weight:800}
.sr-paper .sr-components-wide th:first-child{width:5%}
.sr-paper .sr-components-wide th:nth-child(2){width:11%}
.sr-paper .sr-components-wide th:nth-child(3){width:10%}
.sr-paper .sr-components-wide th:nth-child(4){width:14%}
.sr-paper .sr-components-wide th:nth-child(5){width:6%}
.sr-paper .sr-components-wide th:nth-child(6){width:11%}
.sr-paper .sr-components-wide th:nth-child(7){width:15%}
.sr-paper .sr-components-wide th:nth-child(8){width:13%}
.sr-paper .sr-components-wide th:nth-child(9){width:15%}
.sr-paper .sr-components-wide tr{break-inside:avoid;page-break-inside:avoid}
.sr-paper .sr-components-compact{display:grid;gap:4px}
.sr-paper .sr-component-entry{padding:4px 0;border-bottom:1px dashed #b4a9a0;break-inside:avoid;page-break-inside:avoid;font-size:.9em;line-height:1.35;overflow-wrap:anywhere}
.sr-paper .sr-component-first{display:flex;align-items:baseline;justify-content:space-between;gap:5px}
.sr-paper .sr-component-first strong{font-size:1em;font-weight:800;min-width:0}
.sr-paper .sr-component-first>span{font-weight:800;white-space:nowrap}
.sr-paper .sr-component-detail{display:flex;flex-wrap:wrap;column-gap:8px;row-gap:1px;margin-top:2px;min-width:0}
.sr-paper .sr-component-detail b{font-weight:800}
@media print{
  .sr-paper .sr-components-received{color:#000!important}
  .sr-paper .sr-components-wide{overflow:visible!important}
  .sr-paper .sr-components-wide th{background:#eee!important;color:#000!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .sr-paper .sr-component-entry{break-inside:avoid!important;page-break-inside:avoid!important}
}
</style>

<style>
/* SOS_CUSTOMER_RECEIPT_COMPONENTS_V25 — scoped to receipt paper: same preview = same printed content. */
.sr-paper .sr-custody25{display:block;margin:11px 0 13px;color:#181310;break-inside:auto;page-break-inside:auto;line-height:1.3}
.sr-paper .sr-custody25-eyebrow{font-size:.83em;letter-spacing:.08em;font-weight:800;color:#44362b;margin-bottom:2px}
.sr-paper .sr-custody25 h3.sr-custody25-title{font-size:1.05em!important;font-weight:800!important;margin:3px 0 4px!important;padding:0 0 5px!important;border-bottom:1px solid #776c64!important;line-height:1.28!important}
.sr-paper .sr-custody25-title small{font-size:.82em;font-weight:600;letter-spacing:0}
.sr-paper .sr-custody25-note{margin:2px 0 8px!important;color:#544a40;font-size:.81em;line-height:1.4}
.sr-paper .sr-custody25-empty{font-size:.9em;margin:5px 0 10px!important}
.sr-paper .sr-custody25-table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:.72em;line-height:1.27}
.sr-paper .sr-custody25-table :is(td,th){border:1px solid #bab2aa;padding:4px 3px;vertical-align:top;text-align:left;overflow-wrap:anywhere;word-break:break-word;white-space:normal}
.sr-paper .sr-custody25-table th{background:#f0eee9;color:#201b17;font-weight:800}
.sr-paper .sr-custody25-table th:nth-child(1){width:7%}
.sr-paper .sr-custody25-table th:nth-child(2){width:9%}
.sr-paper .sr-custody25-table th:nth-child(3){width:10%}
.sr-paper .sr-custody25-table th:nth-child(4){width:16%}
.sr-paper .sr-custody25-table th:nth-child(5){width:8%}
.sr-paper .sr-custody25-table th:nth-child(6){width:10%}
.sr-paper .sr-custody25-table th:nth-child(7){width:14%}
.sr-paper .sr-custody25-table th:nth-child(8){width:14%}
.sr-paper .sr-custody25-table th:nth-child(9){width:12%}
.sr-paper .sr-custody25-table tr,.sr-paper .sr-custody25-item{break-inside:avoid!important;page-break-inside:avoid!important}
.sr-paper .sr-custody25-list{display:grid;gap:7px;min-width:0}
.sr-paper .sr-custody25-item{border:1px solid #d7d0c8;padding:6px 7px;min-width:0;overflow-wrap:anywhere}
.sr-paper .sr-custody25-index{font-weight:800;border-bottom:1px solid #d7d0c8;padding-bottom:3px;margin-bottom:4px;font-size:1em}
.sr-paper .sr-custody25-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:8px;row-gap:4px}
.sr-paper .sr-custody25-fields>div{min-width:0;display:flex;flex-direction:column;gap:1px}
.sr-paper .sr-custody25-fields b{font-size:.76em;font-weight:700;line-height:1.2;color:#50463e}
.sr-paper .sr-custody25-fields span{font-size:.93em;font-weight:600;overflow-wrap:anywhere;word-break:break-word}
.sr-paper .sr-custody25.is-thermal .sr-custody25-fields{grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 6px}
.sr-paper .sr-custody25.is-thermal .sr-custody25-item{padding:5px}
.sr-paper .sr-custody25.is-thermal .sr-custody25-fields b{font-size:.8em}
.sr-paper .sr-custody25.is-thermal .sr-custody25-fields span{font-size:1em}
@media print {
 .sr-paper .sr-custody25{color:#000!important;visibility:visible!important;overflow:visible!important}
 .sr-paper .sr-custody25 *{visibility:visible!important}
 .sr-paper .sr-custody25-table th{background:#eee!important;color:#000!important;print-color-adjust:exact;-webkit-print-color-adjust:exact}
 .sr-paper .sr-custody25-item{break-inside:avoid!important;page-break-inside:avoid!important}
}
</style>

<style>
/* SOS_RECEIPT_READABILITY_V26 — affects printed customer receipts and their exact on-screen previews. */
.sr-paper.sos683-paper .sr-customer26 {
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 14px;
  margin:4px 0 12px; padding:8px 0 10px; border-bottom:1.4px solid #161616;
  page-break-inside:avoid;break-inside:avoid;
}
.sr-paper.sos683-paper .sr-customer26-field {display:flex;flex-direction:column;min-width:0;gap:2px;}
.sr-paper.sos683-paper .sr-customer26-field>span {font-size:.86em;font-weight:700;line-height:1.1; color:#555;}
.sr-paper.sos683-paper .sr-customer26-field>strong {
  display:block;min-width:0;color:#000;line-height:1.14;font-weight:900;
  overflow-wrap:anywhere;word-break:normal;letter-spacing:-.018em;
}
.sr-paper.sos683-paper.sos26-roll .sr-customer26 {grid-template-columns:minmax(0,1fr);gap:5px;margin:3px 0 6px;padding:3px 0 6px;}
.sr-paper.sos683-paper.sos26-roll .sr-customer26-field {gap:1px;}
.sr-paper.sos683-paper.sos26-roll .sr-customer26-field>span {font-size:9px;line-height:1.15;}
.sr-paper.sos683-paper .sr-device-serial26{display:flex;justify-content:space-between;gap:8px;align-items:baseline;margin:3px 0;padding:3px 0;break-inside:avoid;}
.sr-paper.sos683-paper .sr-device-serial26>span{flex:0 0 34%;color:#444;}
.sr-paper.sos683-paper .sr-device-serial26>strong{min-width:0;flex:1;text-align:right;font-size:1.05em;font-weight:800;overflow-wrap:anywhere;color:#000;}
.sr-paper.sos683-paper.sos26-roll .sr-device-serial26{display:block;margin:2px 0;padding:2px 0;}
.sr-paper.sos683-paper.sos26-roll .sr-device-serial26>span{display:block;font-size:9px;font-weight:700;}
.sr-paper.sos683-paper.sos26-roll .sr-device-serial26>strong{display:block;text-align:left;font-size:1.1em;line-height:1.15;}
.sr-paper.sos683-paper.sos26-roll :is(.sr-company,.sr-heading){margin-top:4px;margin-bottom:5px;}
.sr-paper.sos683-paper.sos26-roll .sr-heading{padding:4px 0;}
.sr-paper.sos683-paper.sos26-roll h3{margin:8px 0 4px;padding-bottom:3px;}
.sr-paper.sos683-paper.sos26-roll .sr-line{padding:2px 0;gap:4px;line-height:1.3;}
.sr-paper.sos683-paper.sos26-roll .sr-description{margin-top:6px;}
.sr-paper.sos683-paper.sos26-roll .sr-description p{margin:2px 0;}
.sr-paper.sos683-paper.sos26-roll .sr-total{padding:5px 0;margin-top:9px;}
.sr-paper.sos683-paper.sos26-roll .sr-qr{margin:8px 0;}
.sr-paper.sos683-paper.sos26-roll .sr-qr img{width:22mm;height:22mm;}
.sr-paper.sos683-paper.sos26-roll .sr-notice{padding-top:6px;font-size:.83em;}
.sr-paper.sos683-paper.sos26-roll .sr-signatures{margin-top:20px;}

/* Every nonempty intake attribute remains readable, but is not a wasteful eight-box grid. */
.sr-paper .sr-custody25.is-thermal {margin:5px 0 7px;line-height:1.2;}
.sr-paper .sr-custody25.is-thermal .sr-custody25-eyebrow{font-size:9px;line-height:1.08;margin:0;}
.sr-paper .sr-custody25.is-thermal h3.sr-custody25-title{font-size:10px!important;line-height:1.16!important;margin:2px 0 4px!important;padding-bottom:3px!important;}
.sr-paper .sr-custody25.is-thermal .sr-custody25-title small{font-size:.82em;}
.sr-paper .sr-custody25.is-thermal .sr-custody25-note{display:none!important;}
.sr-paper .sr-custody26-list{display:block;width:100%;}
.sr-paper .sr-custody26-row{padding:4px 0;border-bottom:1px dashed #888;break-inside:avoid;page-break-inside:avoid;overflow-wrap:anywhere;}
.sr-paper .sr-custody26-row:last-child{border-bottom:0;}
.sr-paper .sr-custody26-head{display:flex;justify-content:space-between;align-items:start;gap:3px;line-height:1.17;}
.sr-paper .sr-custody26-head>strong{font-size:1.02em;font-weight:800;flex:1;min-width:0;overflow-wrap:anywhere;}
.sr-paper .sr-custody26-qty{font-size:1.02em;flex:0 0 auto;white-space:nowrap;}
.sr-paper .sr-custody26-sub{display:flex;flex-wrap:wrap;gap:1px 6px;line-height:1.18;margin-top:2px;font-size:.91em;}
.sr-paper .sr-custody26-sub>span{min-width:0;overflow-wrap:anywhere;}
.sr-paper .sr-custody26-sub b,.sr-paper .sr-custody26-serial b{font-size:.88em;font-weight:800;}
.sr-paper .sr-custody26-serial{margin-top:2px;font-size:.93em;line-height:1.18;overflow-wrap:anywhere;}

/* Code 128 service-job barcode: maximize width and retain more vertical bar height. */
.sr-paper.sos683-paper .sr-receipt-barcode {margin:9px auto 8px;padding:3mm 1mm 0;break-inside:avoid;page-break-inside:avoid;}
.sr-paper.sos683-paper .sr-receipt-barcode img {
  display:block;width:100%!important;max-width:110mm!important;
  height:16mm!important;object-fit:fill;margin:0 auto;
  image-rendering:auto;
}
.sr-paper.sos683-paper .sr-receipt-barcode .sr-barcode26-number {
  display:block;font-family:Arial,monospace;font-size:14px;font-weight:900;line-height:1.2;
  color:#000;letter-spacing:.035em;margin-top:2mm;white-space:nowrap;
}
.sr-paper.sos683-paper.sos26-roll .sr-receipt-barcode {margin:5px auto;padding:2mm 0 0;}
.sr-paper.sos683-paper.sos26-roll .sr-receipt-barcode img {max-width:100%!important;height:13.5mm!important;}
.sr-paper.sos683-paper.sos26-roll .sr-receipt-barcode .sr-barcode26-number {font-size:12px;margin-top:1mm;}
.sr-paper.sos683-paper.sos26-roll.sos26-roll58 .sr-receipt-barcode img{height:12mm!important;}
.sr-paper.sos683-paper.sos26-roll.sos26-roll58 .sr-receipt-barcode .sr-barcode26-number{font-size:11px;}

/* Sticker preview mirrors the 50×30 mm isolated print document without changing paper size. */
.sos35-label[data-sos-sticker-layout] .sos35-top{height:15.4mm;flex:0 0 15.4mm;}
.sos35-label[data-sos-sticker-layout] .sos35-words{height:15.4mm;}
.sos35-label[data-sos-sticker-layout] .sos35-fault{height:7mm;flex:0 0 7mm;font-size:7.4pt;-webkit-line-clamp:2;line-clamp:2;}
.sos35-label[data-sos-sticker-layout] .sos35-fault.sos35-compact-fault{font-size:6.7pt;}
.sos35-label[data-sos-sticker-layout] img.sos35-barcode{height:5.5mm;flex:0 0 5.5mm;object-fit:fill;}

@media print {
  .sr-paper.sos683-paper .sr-customer26-field>strong{color:#000!important;}
  .sr-paper .sr-custody26-row{break-inside:avoid!important;page-break-inside:avoid!important;}
  .sr-paper.sos683-paper .sr-receipt-barcode{break-inside:avoid!important;page-break-inside:avoid!important;}
}
</style>
