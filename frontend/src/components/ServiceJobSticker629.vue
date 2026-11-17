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
/* SOS_QR_RECENT_V16_START */
const sos16RecentJobs = ref([])
const sos16Open = ref(false)
const sos16Busy = ref(false)
const sos16Error = ref('')
const sos16Active = ref(-1)
const sos16Filtering = ref(false)
const sos16Options = computed(() => {
  const term = sos16Filtering.value ? search.value.trim().toLowerCase() : ''
  if (!term) return sos16RecentJobs.value
  return sos16RecentJobs.value.filter(job =>
    [job.name, job.customer_name, job.mobile, job.device_type, job.brand, job.device_model]
      .some(value => String(value || '').toLowerCase().includes(term)))
})
async function sos16OnFocus() {
  sos16Open.value = true
  sos16Filtering.value = false
  sos16Active.value = -1
  sos16Busy.value = true
  sos16Error.value = ''
  try {
    const url = new URL('/api/method/servicing_os.api.service.get_recent_service_jobs', window.location.origin)
    url.searchParams.set('limit', '20')
    const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    if (!response.ok) throw new Error(response.status === 403 ? 'এই অ্যাকাউন্টে সাম্প্রতিক জব দেখার অনুমতি নেই।' : `Recent jobs unavailable (${response.status}).`)
    const json = await response.json()
    if (!Array.isArray(json.message)) throw new Error('Recent service jobs could not be loaded.')
    sos16RecentJobs.value = json.message.filter(x => x?.name).slice(0, 20)
  } catch (e) {
    sos16RecentJobs.value = []
    sos16Error.value = e.message || 'সাম্প্রতিক জব লোড করা যায়নি।'
  } finally {
    sos16Busy.value = false
  }
}
function sos16OnInput() {
  sos16Open.value = true
  sos16Filtering.value = true
  sos16Active.value = -1
}
function sos16Choose(job) {
  if (!job?.name) return
  search.value = job.name
  sos16Open.value = false
  sos16Filtering.value = false
  sos16Active.value = -1
  fetchJob()
}
function sos16OnKeydown(event) {
  const key = event.key
  if (key === 'Escape' && sos16Open.value) {
    event.preventDefault()
    sos16Open.value = false
    return
  }
  if (key === 'ArrowDown' || key === 'ArrowUp') {
    event.preventDefault()
    sos16Open.value = true
    const n = sos16Options.value.length
    if (n) sos16Active.value = key === 'ArrowDown'
      ? (sos16Active.value + 1) % n
      : (sos16Active.value <= 0 ? n - 1 : sos16Active.value - 1)
    return
  }
  if (key === 'Enter' && sos16Open.value && sos16Active.value >= 0) {
    const selected = sos16Options.value[sos16Active.value]
    if (selected) { event.preventDefault(); sos16Choose(selected) }
  }
}
/* SOS_QR_RECENT_V16_END */

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
            <div class="sos16-search-field" data-sos-recent-version="SOS_QR_RECENT_V16">
              <label for="sos16-job-input">Service Job Number <span class="sos16-bn">/ সার্ভিস জব</span></label>
              <div class="sos16-combo">
                <input id="sos16-job-input" v-model="search" autocomplete="off" spellcheck="false"
                  placeholder="SRV-2026-00001" role="combobox" aria-autocomplete="list"
                  aria-haspopup="listbox" aria-controls="sos16-recent-list"
                  :aria-expanded="sos16Open ? 'true' : 'false'"
                  :aria-activedescendant="sos16Active >= 0 && sos16Options[sos16Active] ? 'sos16-option-' + sos16Active : undefined"
                  @focus="sos16OnFocus" @click="sos16Open = true" @input="sos16OnInput"
                  @keydown="sos16OnKeydown" @blur="sos16Open = false" />
                <span class="sos16-search-icon" aria-hidden="true">⌕</span>
                <div v-if="sos16Open" id="sos16-recent-list" class="sos16-recent-list" role="listbox" aria-label="Recent service received jobs">
                  <div class="sos16-list-header">
                    <span>সাম্প্রতিক সার্ভিস রিসিভ <small>RECENT JOBS</small></span>
                    <span class="sos16-count">{{ sos16Options.length }}</span>
                  </div>
                  <div v-if="sos16Busy" class="sos16-list-message" role="status">সাম্প্রতিক জব লোড হচ্ছে…</div>
                  <div v-else-if="sos16Error" class="sos16-list-message sos16-list-error" role="status">{{ sos16Error }}</div>
                  <template v-else-if="sos16Options.length">
                    <button v-for="(job, index) in sos16Options" :id="'sos16-option-' + index"
                      :key="job.name" class="sos16-recent-option" type="button" role="option"
                      :aria-selected="sos16Active === index" :class="{ 'sos16-is-active': sos16Active === index }"
                      @pointerdown.prevent="sos16Choose(job)" @mouseenter="sos16Active = index">
                      <span class="sos16-result-main">
                        <strong>{{ job.name }}</strong>
                        <small>{{ job.customer_name || 'Customer not recorded' }} <span v-if="job.mobile">· {{ job.mobile }}</span></small>
                      </span>
                      <span class="sos16-result-aside">
                        <span>{{ job.status || 'Received' }}</span>
                        <small>{{ [job.brand, job.device_model].filter(Boolean).join(' ') || job.device_type || 'Device' }}</small>
                      </span>
                    </button>
                  </template>
                  <div v-else class="sos16-list-message">{{ sos16Filtering ? 'এ নামে সাম্প্রতিক জব নেই। নম্বর লিখে Find Service Job চাপুন।' : 'সাম্প্রতিক সার্ভিস জব পাওয়া যায়নি।' }}</div>
                  <div class="sos16-list-tip">↑ ↓ বেছে নিন · Enter খুলুন · Esc বন্ধ করুন</div>
                </div>
              </div>
            </div>
            <button type="submit" :disabled="loading">{{ loading ? 'Searching…' : 'Find Service Job' }}</button>
          </form>
          <div v-if="data" class="sos629-options">
            <label class="sos16-size-field">Sticker size / স্টিকারের মাপ
              <select v-model="printSize" aria-label="Label size">
                <option v-for="size in stickerPresets" :key="size" :value="size">{{ size.replace('x', ' × ') }} mm</option>
                <option value="custom">Custom / নিজের মাপ</option>
              </select>
            </label>
            <div v-if="printSize === 'custom'" class="sos13-custom-sizes">
              <label>Width / প্রস্থ (mm)<input v-model.number="customWidth" type="number" min="20" max="150" step="1" /></label>
              <label>Height / উচ্চতা (mm)<input v-model.number="customHeight" type="number" min="15" max="200" step="1" /></label>
            </div>
            <label class="sos16-copies-field">Copies / কপি
              <input v-model.number="printCopies" type="number" min="1" max="20" step="1" />
            </label>
            <label class="sos16-url-field">Mobile access address / মোবাইলে খোলার ঠিকানা
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

<style>
/* SOS_QR_THEME_POLISH_V15_START
   SCREEN-ONLY appearance for the QR device sticker dialog.
   Intentionally does not style .sos629-paper or the print popup. */
@media screen {
  .sos629-sticker-overlay {
    --sos-qr-v15-token: 1;
    --sos-v15-ivory: #fffaf2;
    --sos-v15-cream: #f7f0e5;
    --sos-v15-taupe: #efe4d5;
    --sos-v15-border: #e5d7c7;
    --sos-v15-espresso: #3e2f22;
    --sos-v15-muted: #796656;
    --sos-v15-brown: #785338;
    background: rgba(39, 30, 23, .64) !important;
    backdrop-filter: blur(7px) saturate(.8);
    -webkit-backdrop-filter: blur(7px) saturate(.8);
    color: var(--sos-v15-espresso) !important;
    font-family: 'Hind Siliguri', 'Noto Sans Bengali', 'Anek Bangla', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  .sos629-sticker-overlay .sos629-sticker-dialog {
    width: min(810px, 100%) !important;
    max-height: min(94dvh, 920px) !important;
    border: 1px solid #eadfce !important;
    border-radius: 22px !important;
    background: var(--sos-v15-ivory) !important;
    box-shadow: 0 34px 100px rgba(31, 21, 14, .33), 0 5px 15px rgba(59, 42, 27, .13) !important;
    isolation: isolate;
  }
  .sos629-sticker-overlay .sos629-dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 18px;
    padding: 23px 28px 20px !important;
    border-bottom: 1px solid var(--sos-v15-border) !important;
    background: linear-gradient(145deg, #fffdf9 0%, #f7ecdd 100%) !important;
  }
  .sos629-sticker-overlay .sos629-dialog-header small {
    display: block;
    font-size: 10px !important;
    font-weight: 850 !important;
    letter-spacing: .14em !important;
    color: #95755d !important;
  }
  .sos629-sticker-overlay .sos629-dialog-header h2 {
    margin: 7px 0 4px !important;
    color: var(--sos-v15-espresso) !important;
    font-size: clamp(23px, 3vw, 27px) !important;
    line-height: 1.3 !important;
    font-weight: 800 !important;
    letter-spacing: -.025em !important;
  }
  .sos629-sticker-overlay .sos629-dialog-header p {
    margin: 0 !important;
    color: var(--sos-v15-muted) !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
  }
  .sos629-sticker-overlay button.sos629-close {
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    border-radius: 12px !important;
    background: #fffaf2 !important;
    color: var(--sos-v15-espresso) !important;
    border: 1px solid #ded0bf !important;
    font-size: 23px !important;
    box-shadow: 0 2px 8px #61492d0b;
    transition: background .18s ease, border-color .18s ease;
  }
  .sos629-sticker-overlay button.sos629-close:hover {
    background: #eee0cd !important;
    border-color: #b99d80 !important;
  }
  .sos629-sticker-overlay .sos629-dialog-body {
    padding: 23px 27px 21px !important;
    gap: 16px !important;
    background: var(--sos-v15-ivory) !important;
    scrollbar-color: #d8c5af transparent;
  }
  .sos629-sticker-overlay .sos629-lookup {
    display: flex;
    align-items: end;
    gap: 11px !important;
    padding: 0 0 17px;
    border-bottom: 1px solid #eee2d3;
  }
  .sos629-sticker-overlay .sos629-lookup label,
  .sos629-sticker-overlay .sos629-options label {
    display: grid;
    align-content: start;
    gap: 7px !important;
    min-width: 0;
    color: #69513f !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    line-height: 1.4 !important;
  }
  .sos629-sticker-overlay .sos629-options {
    align-items: start !important;
    gap: 13px 16px !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
  .sos629-sticker-overlay input,
  .sos629-sticker-overlay select {
    width: 100% !important;
    min-height: 44px !important;
    padding: 10px 13px !important;
    border: 1px solid #dcccb8 !important;
    border-radius: 12px !important;
    background: #fffefb !important;
    color: #3f3024 !important;
    font-size: 13px !important;
    font-weight: 650 !important;
    line-height: 1.4 !important;
    box-shadow: 0 1px 2px #50341c08;
    outline: none;
    transition: border-color .16s ease, box-shadow .16s ease;
  }
  .sos629-sticker-overlay input:focus,
  .sos629-sticker-overlay select:focus {
    border-color: #a67f60 !important;
    box-shadow: 0 0 0 3px rgba(166, 127, 96, .14) !important;
    outline: none !important;
  }
  .sos629-sticker-overlay .sos629-lookup > button,
  .sos629-sticker-overlay .sos629-dialog-footer button.sos629-print {
    min-height: 44px !important;
    padding: 10px 19px !important;
    border: 1px solid #785338 !important;
    border-radius: 12px !important;
    background: #785338 !important;
    color: #fffaf4 !important;
    font-size: 12.5px !important;
    font-weight: 800 !important;
    letter-spacing: 0 !important;
    box-shadow: 0 4px 10px rgba(80, 47, 26, .15) !important;
    transition: background .16s ease, transform .16s ease, box-shadow .16s ease;
  }
  .sos629-sticker-overlay .sos629-lookup > button:hover:not(:disabled),
  .sos629-sticker-overlay .sos629-dialog-footer button.sos629-print:hover:not(:disabled) {
    background: #61422d !important;
    border-color: #61422d !important;
    box-shadow: 0 5px 13px rgba(80, 47, 26, .21) !important;
  }
  .sos629-sticker-overlay .sos629-lookup > button:disabled,
  .sos629-sticker-overlay .sos629-dialog-footer button.sos629-print:disabled {
    opacity: .5 !important;
    cursor: not-allowed !important;
  }
  .sos629-sticker-overlay .sos629-advice {
    grid-column: 1 / -1;
    margin: 0 !important;
    padding: 9px 12px;
    border-left: 3px solid #c2a082;
    border-radius: 0 8px 8px 0;
    background: #f8f0e5;
    color: #806b56 !important;
    font-size: 11px !important;
    line-height: 1.65 !important;
  }
  .sos629-sticker-overlay .sos629-error {
    border-radius: 11px !important;
    padding: 12px 13px !important;
  }
  .sos629-sticker-overlay .sos629-paper-wrap {
    min-height: 204px !important;
    padding: 23px !important;
    border: 1px solid #e4d6c5 !important;
    border-radius: 16px !important;
    background: radial-gradient(ellipse at 42% 20%, #f9f2e9 0%, #efe4d6 100%) !important;
    box-shadow: inset 0 2px 9px #6c51300c;
  }
  .sos629-sticker-overlay .sos629-link-wrap {
    display: grid;
    gap: 6px !important;
    font-size: 11px !important;
    color: #816a56 !important;
  }
  .sos629-sticker-overlay .sos629-link-wrap code {
    padding: 10px 13px !important;
    border: 1px solid #eadccc;
    border-radius: 11px !important;
    color: #5f4936 !important;
    background: #f3eadf !important;
    font-size: 10px !important;
    line-height: 1.6 !important;
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .sos629-sticker-overlay footer.sos629-dialog-footer {
    display: flex !important;
    visibility: visible !important;
    align-items: center;
    gap: 10px !important;
    flex-wrap: wrap;
    min-height: 72px;
    padding: 13px 27px !important;
    border-top: 1px solid #e6d5c1 !important;
    border-radius: 0 0 21px 21px;
    background: #f7eee3 !important;
    box-shadow: 0 -4px 15px rgba(79, 52, 26, .06) !important;
  }
  .sos629-sticker-overlay .sos629-dialog-footer .sos13-version {
    color: #846a54 !important;
    font-size: 10px !important;
    font-weight: 750 !important;
    line-height: 1.4 !important;
    white-space: normal !important;
    margin-right: auto !important;
  }
  .sos629-sticker-overlay .sos629-dialog-footer button.sos629-outline {
    min-height: 44px !important;
    padding: 10px 18px !important;
    border: 1px solid #dac7b3 !important;
    border-radius: 12px !important;
    background: #fffaf3 !important;
    color: #614d3d !important;
    font-size: 12.5px !important;
    font-weight: 800 !important;
    box-shadow: none !important;
  }
  .sos629-sticker-overlay .sos629-dialog-footer button.sos629-outline:hover {
    background: #efe1d1 !important;
  }
  .sos629-sticker-overlay button:focus-visible {
    outline: 3px solid rgba(161, 121, 82, .35) !important;
    outline-offset: 2px !important;
  }
  .sos629-sticker-overlay .sos13-custom-sizes {
    gap: 12px !important;
    grid-template-columns: repeat(2, minmax(0,1fr)) !important;
  }
}
@media screen and (max-width: 650px) {
  .sos629-sticker-overlay { padding: 8px !important; }
  .sos629-sticker-overlay .sos629-sticker-dialog {
    border-radius: 17px !important;
    max-height: calc(100dvh - 16px) !important;
  }
  .sos629-sticker-overlay .sos629-dialog-header { padding: 18px !important; }
  .sos629-sticker-overlay .sos629-dialog-header h2 { font-size: 22px !important; }
  .sos629-sticker-overlay .sos629-dialog-body { padding: 18px !important; gap: 13px !important; }
  .sos629-sticker-overlay .sos629-lookup { flex-direction: column !important; align-items: stretch !important; }
  .sos629-sticker-overlay .sos629-options { grid-template-columns: 1fr !important; }
  .sos629-sticker-overlay .sos13-custom-sizes { grid-template-columns: repeat(2, minmax(0,1fr)) !important; }
  .sos629-sticker-overlay .sos629-paper-wrap { padding: 16px !important; min-height: 180px !important; }
  .sos629-sticker-overlay footer.sos629-dialog-footer { padding: 12px 18px !important; border-radius: 0 0 16px 16px; }
  .sos629-sticker-overlay .sos629-dialog-footer .sos13-version { width: 100%; margin: 0 !important; }
  .sos629-sticker-overlay .sos629-dialog-footer button { flex: 1; }
}
/* SOS_QR_THEME_POLISH_V15_END */
</style>

<style>
/* SOS_QR_RECENT_V16_STYLE_START */
/* Screen only. No sticker-paper / print rules, so V14 print remains unchanged. */
@media screen {
  .sos629-sticker-overlay { --sos-qr-v16-token: 1; }
  .sos629-sticker-overlay .sos629-lookup {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) 168px !important;
    align-items: end !important;
    gap: 12px !important;
    position: relative !important;
    z-index: 12 !important;
  }
  .sos629-sticker-overlay .sos16-search-field {
    position: relative; display: grid; grid-template-rows: auto auto;
    gap: 7px; min-width: 0;
  }
  .sos629-sticker-overlay .sos16-search-field > label {
    margin: 0; color: #614b3b !important; font-weight: 800 !important;
    font-size: 12px !important; line-height: 1.35;
  }
  .sos629-sticker-overlay .sos16-bn { color:#90745b; font-size: 11px; font-weight: 700; }
  .sos629-sticker-overlay .sos16-combo { position: relative; min-width: 0; }
  .sos629-sticker-overlay #sos16-job-input {
    padding-left: 39px !important; padding-right: 13px !important;
    letter-spacing: .018em; font-size: 14px !important; font-weight: 750 !important;
    background-color: #fffdf9 !important; border-color: #d8c4ac !important;
  }
  .sos629-sticker-overlay .sos16-search-icon {
    position:absolute; top:50%; left:13px; transform:translateY(-50%);
    pointer-events:none; font-size:23px; color:#94775c; font-family:Arial,sans-serif;
  }
  .sos629-sticker-overlay .sos629-lookup > button {
    width:100%; min-height:44px !important; white-space:normal;
    padding-inline: 10px !important; line-height:1.3;
  }
  .sos629-sticker-overlay .sos16-recent-list {
    display:block !important; position:absolute !important;
    top:calc(100% + 7px); left:0; right:0; z-index:100 !important;
    border-radius:14px; overflow-y:auto; max-height:282px;
    border:1px solid #d9c5ac !important; background:#fffdf9 !important;
    box-shadow:0 16px 44px rgba(57,37,18,.23),0 2px 5px rgba(57,37,18,.07);
    color:#3e2f22; overscroll-behavior:contain;
  }
  .sos629-sticker-overlay .sos16-list-header {
    display:flex; align-items:center; justify-content:space-between; gap:9px;
    padding:10px 13px 8px; background:#f7eee3; border-bottom:1px solid #e6d8c6;
    font-size:12px; font-weight:800; color:#604731;
  }
  .sos629-sticker-overlay .sos16-list-header small {
    color:#92755e; font-size:9px; letter-spacing:.09em; margin-left:5px;
  }
  .sos629-sticker-overlay .sos16-count {
    display:inline-flex; align-items:center; justify-content:center;
    min-width:23px; height:23px; border-radius:8px;
    color:#745037; background:#ecddca; font-size:11px;
  }
  .sos629-sticker-overlay .sos16-recent-option {
    display:flex !important; align-items:center; justify-content:space-between; gap:12px;
    width:100%; margin:0 !important; padding:11px 13px !important;
    border:0 !important; border-bottom:1px solid #efe5d8 !important;
    border-radius:0 !important; background:#fffdf9 !important;
    color:#3f3025 !important; text-align:left; cursor:pointer;
    box-shadow:none !important; font-size:12px;
  }
  .sos629-sticker-overlay .sos16-recent-option:last-of-type { border-bottom:0 !important; }
  .sos629-sticker-overlay .sos16-recent-option:hover,
  .sos629-sticker-overlay .sos16-recent-option.sos16-is-active { background:#f2e5d5 !important; }
  .sos629-sticker-overlay .sos16-result-main,
  .sos629-sticker-overlay .sos16-result-aside {
    display:grid; gap:5px; min-width:0;
  }
  .sos629-sticker-overlay .sos16-result-main { flex:1 1 auto; }
  .sos629-sticker-overlay .sos16-result-main strong {
    font-size:12.5px; color:#463021; letter-spacing:.015em; overflow-wrap:anywhere;
  }
  .sos629-sticker-overlay .sos16-result-main small,
  .sos629-sticker-overlay .sos16-result-aside small {
    color:#856f5d; font-size:10.5px; line-height:1.35; overflow-wrap:anywhere;
  }
  .sos629-sticker-overlay .sos16-result-aside {
    flex:0 1 34%; text-align:right; justify-items:end;
  }
  .sos629-sticker-overlay .sos16-result-aside > span {
    font-size:10px; font-weight:750; border-radius:7px;
    background:#eee1d2; color:#6f4b35; padding:3px 7px; max-width:100%;
  }
  .sos629-sticker-overlay .sos16-list-message { padding:17px 13px; color:#796452; font-size:11px; line-height:1.55; }
  .sos629-sticker-overlay .sos16-list-error { color:#9b493d; }
  .sos629-sticker-overlay .sos16-list-tip {
    padding:8px 12px; background:#f9f3eb; color:#977d67;
    border-top:1px solid #ebdfd0; font-size:9.5px; line-height:1.3;
  }
  .sos629-sticker-overlay .sos629-options {
    display:grid !important; grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    align-items:start !important; gap:14px 16px !important;
  }
  .sos629-sticker-overlay .sos629-options > label.sos16-url-field,
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes {
    grid-column:1 / -1 !important;
  }
  .sos629-sticker-overlay .sos629-options > label {
    display:grid; grid-template-rows:auto auto; gap:7px !important;
    align-content:start; min-width:0;
  }
  .sos629-sticker-overlay .sos629-options select {
    -webkit-appearance:none !important; appearance:none !important;
    background-color:#fffdf9 !important;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='m5 7.5 5 5 5-5' stroke='%23785338' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    background-position:right 13px center !important;
    background-repeat:no-repeat !important; background-size:17px 17px !important;
    padding:10px 41px 10px 14px !important;
    min-height:46px !important; cursor:pointer; font-weight:700 !important;
  }
  .sos629-sticker-overlay .sos629-options input { min-height:46px !important; }
  .sos629-sticker-overlay .sos629-options select:focus,
  .sos629-sticker-overlay .sos629-options input:focus {
    border-color:#997250 !important; box-shadow:0 0 0 3px rgba(153,114,80,.15) !important;
  }
  .sos629-sticker-overlay .sos13-custom-sizes { gap:12px !important; }
}
@media screen and (max-width:650px) {
  .sos629-sticker-overlay .sos629-lookup { grid-template-columns:1fr !important; gap:10px !important; }
  .sos629-sticker-overlay .sos629-lookup > button { width:100%; }
  .sos629-sticker-overlay .sos629-options { grid-template-columns:1fr !important; }
  .sos629-sticker-overlay .sos629-options > label.sos16-url-field,
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes { grid-column:1 !important; }
  .sos629-sticker-overlay .sos16-recent-list { max-height:230px; }
  .sos629-sticker-overlay .sos16-result-aside { flex-basis:39%; }
}
/* SOS_QR_RECENT_V16_STYLE_END */
</style>

<style>
/* SOS_PRINT_ALIGNMENT_V19_QR_BEGIN
   Screen control alignment only: does not affect QR image, sticker or print popup. */
@media screen {
  .sos629-sticker-overlay .sos629-lookup {
    --sos-v19-qr-h: 46px;
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) minmax(130px, 168px) !important;
    align-items: end !important;
    gap: 12px !important;
  }
  .sos629-sticker-overlay .sos629-lookup > .sos16-search-field {
    min-width: 0 !important;
    width: 100% !important;
  }
  .sos629-sticker-overlay .sos629-lookup > button {
    box-sizing: border-box !important;
    width: 100% !important;
    min-width: 0 !important;
    min-height: var(--sos-v19-qr-h) !important;
    height: var(--sos-v19-qr-h) !important;
    border-radius: 12px !important;
    line-height: 1.3 !important;
    white-space: normal !important;
  }
  .sos629-sticker-overlay .sos629-options {
    --sos-v19-qr-h: 46px;
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 13px 16px !important;
    align-items: start !important;
  }
  .sos629-sticker-overlay .sos629-options > label {
    min-width: 0 !important;
    width: 100% !important;
    margin: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 7px !important;
    justify-content: flex-end !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    line-height: 1.45 !important;
    color: #765940 !important;
  }
  .sos629-sticker-overlay .sos629-options > label.sos16-url-field,
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes {
    grid-column: 1 / -1 !important;
  }
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes {
    width: 100% !important;
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 13px 16px !important;
  }
  .sos629-sticker-overlay .sos13-custom-sizes > label {
    display: flex !important;
    flex-direction: column !important;
    min-width: 0 !important;
    gap: 7px !important;
    margin: 0 !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    line-height: 1.45 !important;
    color: #765940 !important;
  }
  .sos629-sticker-overlay .sos629-options :is(select,input),
  .sos629-sticker-overlay .sos629-lookup input {
    box-sizing: border-box !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    height: var(--sos-v19-qr-h, 46px) !important;
    min-height: var(--sos-v19-qr-h, 46px) !important;
    max-height: var(--sos-v19-qr-h, 46px) !important;
    padding: 0 14px !important;
    margin: 0 !important;
    background-color: #fffdf9 !important;
    border: 1px solid #d7c4b0 !important;
    border-radius: 12px !important;
    color: #3c3026 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: normal !important;
  }
  .sos629-sticker-overlay .sos629-options select {
    -webkit-appearance: none !important;
    appearance: none !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='m5.5 7.5 4.5 5 4.5-5' stroke='%23795842' stroke-width='1.9' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-position: right 13px center !important;
    background-size: 18px 18px !important;
    padding-right: 39px !important;
    cursor: pointer !important;
  }
  .sos629-sticker-overlay .sos629-options :is(select,input):focus-visible,
  .sos629-sticker-overlay .sos629-lookup input:focus-visible {
    outline: none !important;
    border-color: #946a49 !important;
    box-shadow: 0 0 0 3px rgba(148,106,73,.16) !important;
  }
  .sos629-sticker-overlay .sos629-options > .sos629-advice {
    grid-column: 1 / -1 !important;
  }
}
@media screen and (max-width: 680px) {
  .sos629-sticker-overlay .sos629-lookup {
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 10px !important;
  }
  .sos629-sticker-overlay .sos629-lookup > button { width: 100% !important; }
  .sos629-sticker-overlay .sos629-options { grid-template-columns: minmax(0, 1fr) !important; }
  .sos629-sticker-overlay .sos629-options > label.sos16-url-field,
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes { grid-column: 1 !important; }
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
}
@media screen and (max-width: 390px) {
  .sos629-sticker-overlay .sos629-options > .sos13-custom-sizes { grid-template-columns: minmax(0, 1fr) !important; }
}
/* SOS_PRINT_ALIGNMENT_V19_QR_END */
</style>
