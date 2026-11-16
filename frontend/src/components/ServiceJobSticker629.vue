<script setup>
// SOS_STICKER_QR_629 — Sticker identifies a Service Job; hardware serial is secondary.
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import QRCode from 'qrcode'

const props = defineProps({ jobName: { type: String, default: '' } })
const emit = defineEmits(['close'])
const search = ref(props.jobName || '')
const loading = ref(false)
const error = ref('')
const data = ref(null)
const qrData = ref('')
const printSize = ref('60x40')

// SOS_QR_PRINT_V13 — custom label dimensions and page-aware printing.
const stickerPresets = [
  '30x20', '38x25', '40x25', '40x30', '50x25', '50x30',
  '50x40', '54x25', '58x40', '60x30', '60x40', '70x40',
  '75x50', '80x50', '89x36', '100x50', '100x75', '100x100', '100x150'
]
const customWidth = ref(60)
const customHeight = ref(40)
const printCopies = ref(1)
const safeCopies = computed(() => Math.max(1, Math.min(20, Math.trunc(Number(printCopies.value) || 1))))
const stickerWidth = computed(() => {
  const number = printSize.value === 'custom' ? Number(customWidth.value) : Number(printSize.value.split('x')[0])
  return Math.max(20, Math.min(150, Number.isFinite(number) ? number : 60))
})
const stickerHeight = computed(() => {
  const number = printSize.value === 'custom' ? Number(customHeight.value) : Number(printSize.value.split('x')[1])
  return Math.max(15, Math.min(200, Number.isFinite(number) ? number : 40))
})
const stickerClass = computed(() => {
  if (stickerWidth.value < 43 || stickerHeight.value < 28) return 'sos13-mini'
  if (stickerWidth.value <= 55 || stickerHeight.value <= 35) return 'sos13-small'
  if (stickerWidth.value <= 75 || stickerHeight.value <= 48) return 'sos13-medium'
  return 'sos13-large'
})
const stickerStyle = computed(() => ({
  width: `${stickerWidth.value}mm`,
  height: `${stickerHeight.value}mm`,
  '--sos13-qr': `${Math.max(10, Math.min(30, stickerHeight.value - 7, stickerWidth.value * 0.38))}mm`
}))
function removeStickerPageRule() {
  document.getElementById('sos13-print-page')?.remove()
}
onUnmounted(removeStickerPageRule)

const mobileBase = ref(window.location.origin)
const lookupJob = computed(() => data.value?.job || {})
const store = computed(() => data.value?.shop || {})
const deepLink = ref('')
const hasLocalhost = computed(() => /(^|\/\/)(localhost|127\.0\.0\.1)(:|\/|$)/i.test(mobileBase.value.trim()))

function errorText(result, status) {
  if (result?._server_messages) {
    try {
      const messages = JSON.parse(result._server_messages)
      if (messages.length) return JSON.parse(messages[messages.length - 1]).message || 'Unable to retrieve job.'
    } catch {}
  }
  return typeof result?.message === 'string' ? result.message : `Service Job lookup failed (${status}).`
}
function mobileJobUrl(job) {
  const raw = mobileBase.value.trim()
  const base = new URL(raw)
  if (!['http:', 'https:'].includes(base.protocol) || !base.hostname || base.username || base.password) {
    throw new Error('Enter an HTTP(S) address that your phone can reach.')
  }
  // Do not expose mobile numbers, customer names, or diagnostic notes in the QR.
  const url = new URL('/servicing-os', base.origin)
  url.searchParams.set('service_job', job)
  return url.toString()
}
async function generateQr() {
  qrData.value = ''
  deepLink.value = ''
  if (!lookupJob.value.name) return
  try {
    const target = mobileJobUrl(lookupJob.value.name)
    deepLink.value = target
    qrData.value = await QRCode.toDataURL(target, { width: 360, margin: 1, errorCorrectionLevel: 'M' })
    error.value = ''
  } catch (e) { error.value = e.message || 'Could not build mobile QR code.' }
}
async function fetchJob() {
  const job = search.value.trim()
  if (!job) { error.value = 'Enter the Service Job number shown on the receipt.'; return }
  if (job.length > 140) { error.value = 'Service Job number is too long.'; return }
  loading.value = true
  error.value = ''
  data.value = null
  qrData.value = ''
  try {
    const url = new URL('/api/method/servicing_os.api.receipt.get_service_receipt', window.location.origin)
    url.searchParams.set('job_name', job)
    const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    const result = await response.json()
    if (!response.ok || result.exc || result.exc_type || !result.message?.job?.name) {
      throw new Error(errorText(result, response.status))
    }
    data.value = result.message
    await generateQr()
  } catch (e) { error.value = e.message || 'Unable to look up this Service Job.' }
  finally { loading.value = false }
}
watch(mobileBase, () => { if (data.value) generateQr() })
watch(() => props.jobName, name => { if (name) { search.value = name; fetchJob() } }, { immediate: true })
async function printSticker() {
  if (!data.value?.job?.name || !qrData.value || loading.value) return
  // Only numeric millimetres reach the @page rule.
  removeStickerPageRule()
  const rule = document.createElement('style')
  rule.id = 'sos13-print-page'
  rule.textContent = `@media print { @page { size: ${stickerWidth.value}mm ${stickerHeight.value}mm; margin: 0; } }`
  document.head.appendChild(rule)
  await nextTick()
  if (document.fonts?.ready) await document.fonts.ready
  // Wait for the QR image to finish decoding, if supported.
  const qrImage = document.querySelector('.sos629-paper .sos629-qr-zone img')
  if (qrImage?.decode) { try { await qrImage.decode() } catch {} }
  window.addEventListener('afterprint', removeStickerPageRule, { once: true })
  window.print()
}
// SOS_QR_EXACT_PRINT_V14 — print the already-rendered label at its actual dimensions.
// This deliberately does not call window.print() on the main Frappe application.
async function sos14PrintExact() {
  if (!data.value?.job?.name || !qrData.value || loading.value) return
  const source = document.querySelector('.sos629-sticker-overlay .sos629-paper:not(.sos13-extra-copy)')
    || document.querySelector('.sos629-sticker-overlay .sos629-paper')
  if (!source) { error.value = 'Sticker preview unavailable. Find the service job first.'; return }

  const sizeText = String(printSize.value || '60x40')
  const preset = sizeText.match(/^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$/)
  const userW = sizeText === 'custom' && typeof customWidth !== 'undefined'
    ? Number(customWidth.value) : Number(preset?.[1] || 60)
  const userH = sizeText === 'custom' && typeof customHeight !== 'undefined'
    ? Number(customHeight.value) : Number(preset?.[2] || 40)
  const width = Math.min(150, Math.max(20, Number.isFinite(userW) ? userW : 60))
  const height = Math.min(200, Math.max(15, Number.isFinite(userH) ? userH : 40))
  const userCopies = typeof safeCopies !== 'undefined' ? Number(safeCopies.value)
    : (typeof printCopies !== 'undefined' ? Number(printCopies.value) : 1)
  const copies = Math.min(20, Math.max(1, Math.trunc(userCopies) || 1))

  // Open immediately during the actual button click, so Safari does not block it
  // as a delayed, automatic popup.
  const popup = window.open('', '_blank', 'width=580,height=500')
  if (!popup) {
    error.value = 'Safari blocked the print window. Allow pop-ups for this site and retry.'
    return
  }
  popup.document.open()
  popup.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Device sticker</title></head><body></body></html>')
  popup.document.close()
  popup.document.title = `Device sticker — ${data.value.job.name}`

  const css = popup.document.createElement('style')
  // A separate print document prevents receipt controls, headers, and app-wide
  // print CSS from leaking onto the label. CSS mm units map 1:1 to the label.
  css.textContent = `
    @page { size: ${width}mm ${height}mm; margin: 0; }
    html, body { margin:0!important; padding:0!important; width:${width}mm; background:#fff!important; }
    body { font-family:Arial, sans-serif; }
    .sos14-sheet { width:${width}mm!important; height:${height}mm!important;
      display:block!important; position:relative; margin:0!important; padding:0!important;
      overflow:hidden!important; break-after:page; page-break-after:always; }
    .sos14-sheet:last-child { break-after:auto; page-break-after:auto; }
    .sos14-sheet > .sos629-paper { width:${width}mm!important; height:${height}mm!important;
      box-sizing:border-box!important; box-shadow:none!important; border:0!important;
      margin:0!important; max-width:none!important; transform:none!important; }
    @media screen {
      html, body { width:auto!important; background:#e8e8e8!important; }
      .sos14-sheet { margin:12px auto!important; box-shadow:0 1px 12px #0002; background:#fff!important; }
    }
    @media print {
      html,body { width:${width}mm!important; background:#fff!important; }
      .sos14-sheet { margin:0!important; box-shadow:none!important; }
    }
  `
  popup.document.head.appendChild(css)

  // Preserve the exact rendered QR/image/text arrangement and all computed
  // typography from the current sticker PREVIEW, including V13 custom sizes.
  const cloneWithStyles = (node) => {
    if (node.nodeType !== 1) return node.cloneNode(true)
    const cloned = node.cloneNode(false)
    const computed = window.getComputedStyle(node)
    for (let i = 0; i < computed.length; i++) {
      const name = computed[i]
      cloned.style.setProperty(name, computed.getPropertyValue(name), computed.getPropertyPriority(name))
    }
    for (const child of node.childNodes) cloned.appendChild(cloneWithStyles(child))
    return cloned
  }

  for (let i = 0; i < copies; i++) {
    const sheet = popup.document.createElement('div')
    sheet.className = 'sos14-sheet'
    sheet.appendChild(cloneWithStyles(source))
    popup.document.body.appendChild(sheet)
  }
  // Keep print area the EXACT physical size, not the padded preview container.
  const images = [...popup.document.images]
  await Promise.all(images.map(async (img) => {
    try { if (img.decode) await img.decode() } catch (_) {}
  }))
  try { await popup.document.fonts?.ready } catch (_) {}
  popup.addEventListener('afterprint', () => { try { popup.close() } catch (_) {} }, { once: true })
  popup.focus()
  // The small delay lets Safari render data-URI QR images before print opens.
  popup.setTimeout(() => { try { popup.print() } catch (_) { popup.focus() } }, 120)
}

function closeOnOverlay(e) { if (e.target === e.currentTarget) emit('close') }
</script>

<template>
  <Teleport to="body">
    <div class="sos629-sticker-overlay" role="presentation" @click="closeOnOverlay">
      <section class="sos629-sticker-dialog" role="dialog" aria-modal="true" aria-labelledby="sos629-sticker-title">
        <header class="sos629-dialog-header">
          <div><small>SERVICING OS / DEVICE IDENTIFICATION</small><h2 id="sos629-sticker-title">Print QR Sticker</h2><p>Scan on a mobile device to open the matching service record.</p></div>
          <button type="button" class="sos629-close" aria-label="Close sticker window" @click="emit('close')">×</button>
        </header>
        <div class="sos629-dialog-body">
          <form class="sos629-lookup" @submit.prevent="fetchJob">
            <label>Service Job Number<input v-model="search" autocomplete="off" placeholder="SRV-2026-00001" /></label>
            <button type="submit" :disabled="loading">{{ loading ? 'Searching…' : 'Find Service Job' }}</button>
          </form>
          <div v-if="data" class="sos629-options">
            <label>Sticker size
              <select v-model="printSize" aria-label="Label size">
                <option v-for="size in stickerPresets" :key="size" :value="size">{{ size.replace('x', ' × ') }} mm</option>
                <option value="custom">Custom / নিজের মাপ</option>
              </select>
            </label>
            <div v-if="printSize === 'custom'" class="sos13-custom-sizes">
              <label>Width / প্রস্থ (mm)<input v-model.number="customWidth" type="number" min="20" max="150" step="1" /></label>
              <label>Height / উচ্চতা (mm)<input v-model.number="customHeight" type="number" min="15" max="200" step="1" /></label>
            </div>
            <label>Copies / কপি
              <input v-model.number="printCopies" type="number" min="1" max="20" step="1" />
            </label>
            <label>Mobile access address
              <input v-model.trim="mobileBase" type="url" placeholder="http://192.168.0.100:8005" />
            </label>
            <p v-if="hasLocalhost" class="sos629-advice">A localhost QR link cannot open on another phone. Enter the computer's LAN IP or an accessible HTTPS domain.</p>
            <p class="sos629-advice">The QR contains the Service Job ID only. Mobile users must be connected to the shop network or your secure public domain and have access to the job.</p>
          </div>
          <p v-if="error" class="sos629-error" role="alert">{{ error }}</p>
          <div v-if="data" class="sos629-paper-wrap">
            <div v-for="copyNo in safeCopies" :key="copyNo" class="sos629-paper" :class="[stickerClass, { 'sos13-extra-copy': copyNo > 1 }]" :style="stickerStyle" aria-label="Printable service device sticker">
              <div class="sos629-qr-zone"><img v-if="qrData" :src="qrData" alt="QR code that opens the Service Job" /><div v-else class="sos629-qr-pending">QR pending</div><small>SCAN JOB</small></div>
              <div class="sos629-label-zone">
                <strong class="sos629-brand">{{ (store.name || 'SERVICING OS').slice(0, 36) }}</strong>
                <span class="sos629-job-caption">SERVICE JOB</span>
                <b class="sos629-job-id">{{ lookupJob.name }}</b>
                <span class="sos629-model">{{ [lookupJob.brand, lookupJob.device_model].filter(Boolean).join(' · ') || lookupJob.device_type || 'Device received' }}</span>
                <span class="sos629-serial">S/N: {{ lookupJob.serial_number || '—' }}</span>
                <span class="sos632-customer">{{ lookupJob.customer_name || 'Customer not recorded' }}</span>
                <span class="sos632-mobile">{{ lookupJob.mobile || 'Mobile not recorded' }}</span>
                <span class="sos632-fault">{{ lookupJob.reported_problem || 'Problem not recorded' }}</span>
                <span class="sos629-received">Received: {{ String(lookupJob.received_date || '').slice(0, 10) || '—' }}</span>
              </div>
            </div>
          </div>
          <div v-if="deepLink" class="sos629-link-wrap"><span>QR link</span><code>{{ deepLink }}</code></div>
        </div>
        <footer class="sos629-dialog-footer">
          <small class="sos13-version">QR PRINT V13 · {{ stickerWidth }} × {{ stickerHeight }} mm · {{ safeCopies }} {{ safeCopies === 1 ? 'copy' : 'copies' }}</small>
          <button type="button" class="sos629-outline" @click="emit('close')">Close</button>
          <button type="button" class="sos629-print" :disabled="!qrData || loading" @click="sos14PrintExact" data-sos-print-version="SOS_QR_EXACT_PRINT_V14">🖨 Print Sticker / স্টিকার প্রিন্ট</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style>
.sos629-sticker-overlay{position:fixed;inset:0;z-index:2147482000;background:rgba(26,31,38,.70);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;padding:18px;font-family:inherit;color:#233042}
.sos629-sticker-overlay *{box-sizing:border-box}
.sos629-sticker-dialog{width:min(760px,100%);max-height:96dvh;overflow:auto;background:#fbfaf8;border-radius:20px;box-shadow:0 30px 96px #0d101c70}
.sos629-dialog-header{padding:23px 27px 18px;border-bottom:1px solid #e6e2dc;display:flex;justify-content:space-between;gap:15px;align-items:flex-start;background:#fff}
.sos629-dialog-header small{font-size:10px;color:#89745e;letter-spacing:.14em;font-weight:800}
.sos629-dialog-header h2{font-size:23px;letter-spacing:-.04em;margin:5px 0 2px;font-weight:800;color:#252b31}
.sos629-dialog-header p{font-size:12px;color:#7f858b;margin:0}
.sos629-close{border:1px solid #dedad4;background:#fff;color:#40474d;border-radius:11px;font-size:23px;line-height:1;width:35px;height:35px;cursor:pointer}
.sos629-dialog-body{padding:22px 26px;display:grid;gap:14px}
.sos629-lookup{display:flex;align-items:end;gap:9px}
.sos629-lookup label,.sos629-options label{display:grid;gap:6px;color:#555e67;font-size:11px;font-weight:750;min-width:0;flex:1}
.sos629-sticker-overlay input,.sos629-sticker-overlay select{border:1px solid #d6d8da;background:#fff;color:#242c33;border-radius:10px;padding:11px 12px;min-height:43px;width:100%;font:inherit;font-size:13px}
.sos629-sticker-overlay input:focus-visible,.sos629-sticker-overlay select:focus-visible,.sos629-sticker-overlay button:focus-visible{outline:3px solid #d6a65e;outline-offset:2px}
.sos629-lookup button,.sos629-print{background:#253a46;border:1px solid #253a46;color:white;border-radius:10px;padding:12px 18px;min-height:43px;font-weight:800;font-size:12px;cursor:pointer}
.sos629-lookup button:disabled,.sos629-print:disabled{opacity:.46;cursor:not-allowed}
.sos629-options{display:grid;grid-template-columns:160px minmax(0,1fr);gap:12px;align-items:end}
.sos629-advice{grid-column:1/-1;margin:0;font-size:11px;color:#69747e;line-height:1.5}
.sos629-error{background:#fff1ef;color:#a33b31;border:1px solid #e8c9c5;padding:10px 12px;border-radius:9px;font-size:12px;margin:0}
.sos629-paper-wrap{background:linear-gradient(145deg,#eff0ee,#e7e7e4);min-height:182px;border:1px solid #e1e1dd;border-radius:14px;display:flex;justify-content:center;align-items:center;padding:24px;overflow:auto}
.sos629-paper{display:flex;align-items:center;gap:2mm;background:#fff;border:1px solid #bbc2c6;color:#000;padding:2mm;font-family:Arial,Helvetica,sans-serif;overflow:hidden;box-shadow:0 3px 15px #0002;flex-shrink:0}
.sos629-size-60x40{width:60mm;height:40mm}
.sos629-size-50x30{width:50mm;height:30mm}
.sos629-qr-zone{width:23mm;flex:0 0 23mm;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0}
.sos629-qr-zone img{width:23mm;height:23mm;object-fit:contain;image-rendering:pixelated}
.sos629-qr-zone small{font-size:6pt;font-weight:900;letter-spacing:.06em}
.sos629-label-zone{min-width:0;flex:1;display:flex;flex-direction:column;align-items:start;justify-content:center;gap:1.6mm;overflow:hidden;line-height:1.1}
.sos629-brand{font-size:6.4pt;letter-spacing:-.02em;line-height:1.1;word-break:break-word;max-height:7mm;overflow:hidden}
.sos629-job-caption{font-size:6pt;letter-spacing:.07em;font-weight:700}
.sos629-job-id{font-size:8pt;word-break:break-all;line-height:1.15}
.sos629-model,.sos629-serial,.sos629-received{font-size:6.2pt;word-break:break-word;line-height:1.12}
.sos629-size-50x30{gap:1mm;padding:1.2mm}.sos629-size-50x30 .sos629-qr-zone{width:19mm;flex-basis:19mm}.sos629-size-50x30 .sos629-qr-zone img{width:19mm;height:19mm}.sos629-size-50x30 .sos629-label-zone{gap:.65mm}.sos629-size-50x30 .sos629-brand{font-size:5.6pt}.sos629-size-50x30 .sos629-job-id{font-size:7.3pt}.sos629-size-50x30 .sos629-model,.sos629-size-50x30 .sos629-serial,.sos629-size-50x30 .sos629-received{font-size:5.4pt}
.sos629-link-wrap{display:grid;gap:5px;color:#66717a;font-size:11px}.sos629-link-wrap code{display:block;padding:9px 11px;overflow-wrap:anywhere;background:#f0f1ef;border-radius:8px;color:#34434c;font-size:10px}
.sos629-dialog-footer{padding:15px 26px;display:flex;justify-content:flex-end;gap:10px;background:white;border-top:1px solid #e6e2dc}
.sos629-outline{background:white;border:1px solid #d6d8da;color:#33414a;border-radius:10px;padding:11px 16px;cursor:pointer;font-weight:750;font-size:12px}
@media(max-width:650px){.sos629-sticker-overlay{padding:8px}.sos629-dialog-header{padding:17px}.sos629-dialog-body{padding:15px}.sos629-dialog-footer{padding:14px}.sos629-lookup{align-items:stretch;flex-direction:column}.sos629-options{grid-template-columns:1fr}.sos629-paper-wrap{padding:15px}}
@media print{
  @page{margin:0;size:auto}
  body:has(> .sos629-sticker-overlay)>*:not(.sos629-sticker-overlay){display:none!important}
  body:has(> .sos629-sticker-overlay){margin:0!important;padding:0!important;background:#fff!important}
  .sos629-sticker-overlay{position:static!important;display:block!important;inset:auto!important;padding:0!important;background:#fff!important;backdrop-filter:none!important;overflow:visible!important}
  .sos629-sticker-dialog{width:auto!important;max-height:none!important;overflow:visible!important;border-radius:0!important;box-shadow:none!important;background:#fff!important}
  .sos629-dialog-header,.sos629-lookup,.sos629-options,.sos629-advice,.sos629-error,.sos629-link-wrap,.sos629-dialog-footer{display:none!important}
  .sos629-dialog-body{display:block!important;padding:0!important;margin:0!important}
  .sos629-paper-wrap{background:#fff!important;min-height:0!important;padding:0!important;border:0!important;margin:0!important;display:block!important;overflow:visible!important}
  .sos629-paper{box-shadow:none!important;border:0!important;margin:0!important;break-inside:avoid!important}
}
</style>

<style>
/* SOS_632_PRINT_CENTER_STICKER — readable identifiers within a fixed thermal label. */
.sos629-label-zone .sos632-customer,.sos629-label-zone .sos632-mobile,.sos629-label-zone .sos632-fault{font-size:5.7pt;line-height:1.1;overflow-wrap:anywhere;max-width:100%}
.sos629-label-zone .sos632-customer,.sos629-label-zone .sos632-mobile{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sos629-label-zone .sos632-fault{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden}
.sos629-size-50x30 .sos629-brand,.sos629-size-50x30 .sos629-job-caption,.sos629-size-50x30 .sos629-model,.sos629-size-50x30 .sos629-received{display:none}
.sos629-size-50x30 .sos629-label-zone{gap:.6mm}
.sos629-size-50x30 .sos632-customer,.sos629-size-50x30 .sos632-mobile,.sos629-size-50x30 .sos632-fault{font-size:5.1pt}
.sos629-size-50x30 .sos632-fault{-webkit-line-clamp:1;line-clamp:1}
.sos629-size-60x40 .sos629-received{display:none}
.sos629-size-60x40 .sos629-label-zone{gap:.85mm}
</style>

<style>
/* SOS_QR_PRINT_V13: live sticker preview + fixed print sheet, not the receipt modal. */
.sos629-sticker-dialog{display:flex!important;flex-direction:column!important;overflow:hidden!important;max-height:96dvh!important}
.sos629-dialog-header{flex:0 0 auto}
.sos629-dialog-body{flex:1 1 auto;overflow:auto!important;min-height:0}
.sos629-dialog-footer{position:relative;z-index:3;flex:0 0 auto;display:flex;align-items:center;gap:10px;background:#fffaf4;border-top:1px solid #e7d9c7;box-shadow:0 -5px 18px #40251412}
.sos13-version{margin-right:auto;color:#765c48;font-size:10px;font-weight:800;white-space:nowrap}
.sos629-print{background:#634734!important;border-color:#634734!important;color:#fff!important;white-space:nowrap}
.sos629-options{grid-template-columns:minmax(165px,1fr) minmax(160px,1fr)!important}
.sos13-custom-sizes{grid-column:1/-1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.sos629-paper.sos13-extra-copy{display:none}
.sos629-paper{gap:1mm!important;padding:1.2mm!important;align-items:center!important}
.sos629-paper .sos629-qr-zone{width:var(--sos13-qr)!important;flex:0 0 var(--sos13-qr)!important}
.sos629-paper .sos629-qr-zone img{width:var(--sos13-qr)!important;height:var(--sos13-qr)!important;image-rendering:pixelated}
.sos629-paper .sos629-qr-zone small{font-size:5pt!important}
.sos629-paper .sos629-label-zone{gap:.55mm!important;line-height:1.12!important;justify-content:center}
.sos629-paper .sos632-customer{font-size:9pt!important;font-weight:900!important;line-height:1.1!important;color:#000;white-space:normal!important;text-overflow:clip!important;overflow:hidden!important;max-height:7mm}
.sos629-paper .sos632-mobile{font-size:7.3pt!important;font-weight:800!important;line-height:1.1!important;white-space:normal!important;text-overflow:clip!important;overflow-wrap:anywhere}
.sos629-paper .sos632-fault{display:-webkit-box!important;-webkit-box-orient:vertical;-webkit-line-clamp:2!important;line-clamp:2!important;font-size:8.1pt!important;line-height:1.12!important;font-weight:900!important;overflow:hidden!important;overflow-wrap:anywhere;max-height:8mm}
.sos629-paper.sos13-small .sos629-brand,.sos629-paper.sos13-small .sos629-job-caption,.sos629-paper.sos13-small .sos629-model,.sos629-paper.sos13-small .sos629-serial,.sos629-paper.sos13-small .sos629-received{display:none!important}
.sos629-paper.sos13-small .sos629-job-id{font-size:7.4pt!important;line-height:1.12!important;overflow-wrap:anywhere}
.sos629-paper.sos13-medium .sos629-job-caption,.sos629-paper.sos13-medium .sos629-received{display:none!important}
.sos629-paper.sos13-medium .sos629-brand{font-size:5.7pt!important;max-height:5mm!important}
.sos629-paper.sos13-medium .sos629-serial{display:none!important}
.sos629-paper.sos13-medium .sos629-model{font-size:6pt!important;line-height:1.1!important}
.sos629-paper.sos13-mini .sos629-brand,.sos629-paper.sos13-mini .sos629-job-caption,.sos629-paper.sos13-mini .sos629-model,.sos629-paper.sos13-mini .sos629-serial,.sos629-paper.sos13-mini .sos629-received,.sos629-paper.sos13-mini .sos632-fault{display:none!important}
.sos629-paper.sos13-mini .sos629-label-zone{gap:.35mm!important}
.sos629-paper.sos13-mini .sos629-job-id{font-size:6pt!important;overflow-wrap:anywhere}
.sos629-paper.sos13-mini .sos632-customer{font-size:6pt!important;max-height:5mm!important}
.sos629-paper.sos13-mini .sos632-mobile{font-size:5.6pt!important}
.sos629-paper.sos13-large .sos629-label-zone{gap:1.1mm!important}
.sos629-paper.sos13-large .sos632-customer{font-size:11pt!important;max-height:12mm!important}
.sos629-paper.sos13-large .sos632-mobile{font-size:9pt!important}
.sos629-paper.sos13-large .sos632-fault{font-size:10pt!important;max-height:14mm}
@media(max-width:650px){.sos629-sticker-dialog{max-height:98dvh!important}.sos629-dialog-footer{flex-wrap:wrap;padding:10px!important}.sos13-version{width:100%}.sos629-options{grid-template-columns:1fr!important}}
@media print{
  .sos629-sticker-dialog{max-height:none!important;overflow:visible!important;display:block!important}
  .sos629-dialog-body{overflow:visible!important;padding:0!important}
  .sos629-paper-wrap{overflow:visible!important;padding:0!important;margin:0!important}
  .sos629-paper.sos13-extra-copy{display:flex!important}
  .sos629-paper{break-inside:avoid!important;page-break-inside:avoid!important}
  .sos629-paper:not(:last-child){break-after:page!important;page-break-after:always!important}
  .sos629-paper:last-child{break-after:auto!important;page-break-after:auto!important}
}
</style>

<style>
/* SOS_QR_EXACT_PRINT_V14 — keep action bar visible, even with legacy Frappe footer rules. */
.sos629-sticker-overlay footer.sos629-dialog-footer {
  display:flex!important; visibility:visible!important;
  position:sticky!important; bottom:0!important;
  z-index:20!important; background:#fffaf5!important;
  border-top:1px solid #e6d5c1!important;
  flex-shrink:0!important;
}
.sos629-sticker-overlay .sos629-print {
  display:inline-flex!important; align-items:center!important; justify-content:center!important;
  min-height:43px!important; background:#644a36!important; color:white!important;
  font-weight:800!important; border-radius:10px!important; cursor:pointer!important;
}
</style>
