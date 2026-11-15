<script setup>
import {ref as sos657Ref, nextTick as sos657NextTick} from 'vue'

// SERVICING_OS_COUNTER_657: Print the ACTUAL rendered sticker inside the modal.
const sos657StickerPaper = sos657Ref('60x40')
const sos657StickerError = sos657Ref('')
function sos657BackToTabs(){
  if(typeof sos655ReturnToCounterTabs==='function'){sos655ReturnToCounterTabs();return}
  if(typeof emit==='function'){emit('close');return}
  const tabs=[...document.querySelectorAll('[role=tab], [role=tablist] button')]
  const go=tabs.find(btn=>/Receive|Details|Jobs|Overview|Back|বিস্তারিত/i.test(btn.textContent||'') && !/QR|Sticker/i.test(btn.textContent||''))
  if(go)go.click()
}
let sos657StickerFrame = null
async function sos657PrintSticker() {
  sos657StickerError.value=''
  const modal = document.querySelector('.sos657-sticker-controls')?.closest('[role="dialog"]') ||
                document.querySelector('.sos657-sticker-controls')?.parentElement
  if(!modal){sos657StickerError.value='Open a saved service-job QR sticker.';return}
  const selectors = ['.sos629-sticker-paper','.sos629-sticker','.sticker-paper','.sticker-preview',
                     '.qr-sticker','.qr-sticker-card','.sos655-sticker-card',
                     '[data-sos655-sticker-print]']
  let target
  for(const selector of selectors) {
    const el=modal.querySelector(selector) || document.querySelector(selector)
    if(el && el.getClientRects().length && !el.classList.contains('sos655-sticker-toolbar')){target=el;break}
  }
  if(!target){
    const candidates=[...modal.querySelectorAll('article,figure,section,div')].filter(el=>{
      if(!el.getClientRects().length || el.closest('.sos657-sticker-controls,.sos655-sticker-toolbar'))return false
      const rect=el.getBoundingClientRect()
      const words=(el.innerText||'').toUpperCase()
      return rect.width>=130 && rect.height>=70 && el.querySelector('img,svg,canvas') &&
        /SERVICE JOB|SCAN JOB|SRV-/.test(words) && words.length<1000
    })
    candidates.sort((a,b)=>a.getBoundingClientRect().width*a.getBoundingClientRect().height-
                           b.getBoundingClientRect().width*b.getBoundingClientRect().height)
    target=candidates[0]
  }
  if(!target){sos657StickerError.value='QR sticker preview not found. Select a saved job and generate the sticker first.';return}
  await sos657NextTick()
  const sticker=target.cloneNode(true)
  sticker.querySelectorAll('button,nav,.sos657-sticker-controls,.sos655-sticker-toolbar').forEach(e=>e.remove())
  // Preserve rendered canvas QR images when a component uses canvas rather than IMG or SVG.
  const originalCanvas=[...target.querySelectorAll('canvas')]
  const clonedCanvas=[...sticker.querySelectorAll('canvas')]
  clonedCanvas.forEach((canvas,i)=>{try{const img=document.createElement('img');img.src=originalCanvas[i].toDataURL('image/png');canvas.replaceWith(img)}catch(_){}})
  if(!sticker.querySelector('img,svg,canvas')) {sos657StickerError.value='QR image has not finished generating.';return}
  const page = { '60x40':['60mm','40mm'],'50x30':['50mm','30mm'], '70x40':['70mm','40mm'], 'A4':['210mm','297mm']}[sos657StickerPaper.value]||['50mm','30mm']
  try {
    if(sos657StickerFrame?.parentNode)sos657StickerFrame.remove()
    const frame=document.createElement('iframe');sos657StickerFrame=frame
    Object.assign(frame.style,{position:'fixed',left:'-9999px',top:'-9999px',width:'0',height:'0',border:'0'})
    document.body.appendChild(frame)
    const d=frame.contentDocument
    // Copy same-origin CSS so the preview keeps its layout on the actual sticker paper.
    const css=[...document.styleSheets].map(sheet=>{try{return [...sheet.cssRules].map(rule=>rule.cssText).join('\n')}catch(_){return ''}}).join('\n')
    d.open();d.write('<!doctype html><html><head><meta charset="utf-8"><style>'+css+
       '@page{size:'+page.join(' ')+';margin:0}html,body{margin:0!important;padding:0!important;background:white!important}'+
       'body>*{position:static!important;transform:none!important;box-shadow:none!important;max-width:100%!important;max-height:100%!important;margin:0!important;overflow:hidden!important}'+
       '.sos657-printed-sticker{width:'+page[0]+';height:'+page[1]+';display:flex;justify-content:center;align-items:center;padding:1mm!important;background:white!important;overflow:hidden!important}'+
       '.sos657-printed-sticker>*,.sos657-printed-sticker img,.sos657-printed-sticker svg{max-width:100%!important;max-height:100%!important;box-sizing:border-box!important}'+
       '</style></head><body><div class="sos657-printed-sticker">'+sticker.outerHTML+'</div></body></html>');d.close()
    await Promise.all([...d.images].map(im=>im.complete?Promise.resolve():new Promise(resolve=>{im.onload=resolve;im.onerror=resolve})))
    frame.contentWindow.focus();frame.contentWindow.print()
    const cleanup=()=>{if(frame.parentNode)frame.remove();if(sos657StickerFrame===frame)sos657StickerFrame=null}
    frame.contentWindow.addEventListener('afterprint',cleanup,{once:true})
    setTimeout(cleanup,90000)
  } catch(error){sos657StickerError.value=error?.message||'Printer could not be opened.'}
}


// SERVICING_OS_COUNTER_655 — explicit print and return navigation.
async function sos655PrintQrSticker() {
 const target = document.querySelector('[data-sos655-sticker-print]')
 if (!target || !target.getClientRects().length) {
   window.alert('Open a QR sticker preview for a saved service job before printing.')
   return
 }
 // Wait for QR images and current font assets before invoking the printer.
 await Promise.all([...target.querySelectorAll('img')].map(img => img.decode?.().catch(() => {}) || Promise.resolve()))
 if (document.fonts?.ready) await document.fonts.ready
 const html = document.documentElement
 html.setAttribute('data-sos655-print-sticker','1')
 window.addEventListener('afterprint', () => html.removeAttribute('data-sos655-print-sticker'), {once:true})
 try { window.print() } finally {
   // afterprint normally clears the flag. Fallback covers browsers that omit it.
   setTimeout(() => html.removeAttribute('data-sos655-print-sticker'), 1500)
 }
}
function sos655ReturnToCounterTabs() {
 // Clicking a real Vue tab preserves its existing navigation handler.
 const candidates = [...document.querySelectorAll('[role="tablist"] button, [role="tab"], [class*="tabs"] button')]
 const backTab = candidates.find(el => el.getClientRects().length &&
   !el.closest('.sos655-sticker-toolbar') &&
   /Receive|Details|Overview|All Jobs|Job List|Service Jobs|Summary|ডিভাইস|সার্ভিস|বিস্তারিত/i.test(el.textContent||'') &&
   !/QR|Sticker|স্টিকার/i.test(el.textContent||''))
 if (backTab) { backTab.click(); return }
 const fallback = document.querySelector('.sos652-grid button.sos652-tile')
 if (fallback) fallback.click()
 else window.dispatchEvent(new CustomEvent('sos655-sticker-back'))
}

// SOS_629B_VISIBLE_QR_PRINT: Job QR access, no writes to repair records.
import { ref, watch, onBeforeUnmount } from 'vue'
import ServiceJobSticker629 from './ServiceJobSticker629.vue'

const pickerOpen = ref(false)
const stickerJob = ref('')
const query = ref('')
const loading = ref(false)
const problem = ref('')
const jobs = ref([])
let searchTimer = null
let requestId = 0

function describeFailure(payload, status) {
  if (payload?._server_messages) {
    try {
      const messages = JSON.parse(payload._server_messages)
      if (messages.length) return JSON.parse(messages[messages.length - 1]).message || 'Unable to load jobs.'
    } catch {}
  }
  return (typeof payload?.message === 'string' ? payload.message : '') || `Job lookup failed (${status})`
}
async function findJobs() {
  const thisRequest = ++requestId
  loading.value = true
  problem.value = ''
  try {
    const url = new URL('/api/method/servicing_os.api.service_jobs_hub.get_service_jobs', window.location.origin)
    url.searchParams.set('search', query.value.trim())
    url.searchParams.set('status', 'All')
    const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    const payload = await response.json()
    if (!response.ok || payload.exc || payload.exc_type || !payload.message || !Array.isArray(payload.message.jobs)) {
      throw new Error(describeFailure(payload, response.status))
    }
    if (thisRequest !== requestId || !pickerOpen.value) return
    jobs.value = payload.message.jobs.slice(0, 60)
  } catch (err) {
    if (thisRequest === requestId && pickerOpen.value) {
      problem.value = err?.message || 'Unable to load Service Jobs.'
      jobs.value = []
    }
  } finally {
    if (thisRequest === requestId) loading.value = false
  }
}
function showPicker() {
  stickerJob.value = ''
  pickerOpen.value = true
  query.value = ''
  jobs.value = []
  problem.value = ''
  findJobs()
}
function closePicker() {
  requestId += 1
  clearTimeout(searchTimer)
  pickerOpen.value = false
}
function useJob(name) {
  const id = String(name || '').trim()
  if (!id || id.length > 140) {
    problem.value = 'Enter a valid Service Job number.'
    return
  }
  closePicker()
  stickerJob.value = id
}
function useManual() { useJob(query.value) }
function closeSticker() { stickerJob.value = '' }
watch(query, () => {
  if (!pickerOpen.value) return
  clearTimeout(searchTimer)
  searchTimer = setTimeout(findJobs, 240)
})
onBeforeUnmount(() => { requestId += 1; clearTimeout(searchTimer) })
</script>

<template>
  <!-- SERVICING_OS_COUNTER_655: always-visible controls while sticker view is mounted -->
  <div class="sos655-sticker-toolbar" role="toolbar" aria-label="QR sticker controls">
    <button type="button" class="sos655-print-button" @click="sos655PrintQrSticker">▣ Print QR Sticker</button>
    <button type="button" class="sos655-back-button" @click="sos655ReturnToCounterTabs">← Back to Tabs</button>
  </div>

  <Teleport to="body">
    <div v-if="!pickerOpen && !stickerJob" class="sos629b-launcher" data-sos655-sticker-print="true">
<!-- SERVICING_OS_COUNTER_657: in-modal controls, not a floating placeholder -->
<div class="sos657-sticker-controls sos658-sticker-tools" role="toolbar" aria-label="Sticker paper and print">
  <label>Sticker Paper
    <select v-model="sos657StickerPaper" aria-label="Sticker paper size">
      <option value="60x40">60 × 40 mm</option><option value="50x30">50 × 30 mm</option><option value="70x40">70 × 40 mm</option><option value="A4">A4 label sheet</option>
    </select>
  </label>
  <button type="button" class="sos657-sticker-print" @click.stop="sos657PrintSticker">Print QR Sticker · Selected Size</button>
  <button type="button" class="sos657-sticker-back" @click.stop="sos657BackToTabs">← Back to Tabs</button>
  <span v-if="sos657StickerError" role="alert">{{ sos657StickerError }}</span>
</div>

      <button type="button" class="sos629b-launch-button" @click="showPicker">
        <span class="sos629b-bullet" aria-hidden="true"></span>
        Print Service QR Sticker
      </button>
    </div>
    <div v-if="pickerOpen" class="sos629b-overlay" @click.self="closePicker">
      <section class="sos629b-dialog" role="dialog" aria-modal="true" aria-label="Choose a job to print its QR sticker">
        <header class="sos629b-header">
          <div><small>SERVICING OS / PRINT CENTER</small><h2>Print Service QR Sticker</h2><p>Find an existing repair job and print its QR device label.</p></div>
          <button type="button" class="sos629b-close" aria-label="Close" @click="closePicker">×</button>
        </header>
        <div class="sos629b-body">
          <label for="sos629b-job-search">Find a Service Job</label>
          <div class="sos629b-search">
            <input id="sos629b-job-search" v-model.trim="query" type="search" autocomplete="off" placeholder="Job ID, customer, device or serial" @keydown.enter.prevent="useManual" />
            <button type="button" @click="useManual" :disabled="!query.trim()">Use Job ID</button>
          </div>
          <p class="sos629b-hint">Results update automatically. Select a job below, or enter its exact Job ID.</p>
          <p v-if="problem" class="sos629b-error" role="alert">{{ problem }}</p>
          <p v-if="loading" class="sos629b-loading">Finding Service Jobs…</p>
          <div v-else-if="jobs.length" class="sos629b-results">
            <button v-for="job in jobs" :key="job.name" type="button" class="sos629b-job" @click="useJob(job.name)">
              <span><strong>{{ job.name }}</strong><small>{{ [job.customer_name || job.customer, job.brand, job.device_model].filter(Boolean).join(' · ') || 'Repair record' }}</small></span>
              <em>Choose</em>
            </button>
          </div>
          <div v-else-if="!problem" class="sos629b-empty">No matching jobs. Receive a device first, or enter an existing Service Job ID.</div>
        </div>
        <footer class="sos629b-footer"><button type="button" @click="closePicker">Close</button></footer>
      </section>
    </div>
  </Teleport>
  <ServiceJobSticker629 v-if="stickerJob" :job-name="stickerJob" @close="closeSticker" />
</template>

<style>
.sos629b-launcher{position:fixed;z-index:2000000;right:24px;bottom:23px;pointer-events:none;font-family:inherit}
.sos629b-launch-button{pointer-events:auto;display:flex;align-items:center;gap:11px;border:1px solid #9b7d5c;background:#233a45;color:#fff;border-radius:12px;box-shadow:0 8px 22px #15242c42;padding:15px 18px;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit;min-height:51px}
.sos629b-launch-button:hover{background:#344f5d;box-shadow:0 10px 28px #15242c55}
.sos629b-launch-button:focus-visible,.sos629b-overlay button:focus-visible,.sos629b-overlay input:focus-visible{outline:3px solid #c79860;outline-offset:2px}
.sos629b-bullet{width:9px;height:9px;border:2px solid #e1bf8c;border-radius:2px;display:inline-block;transform:rotate(45deg);flex-shrink:0}
.sos629b-overlay{position:fixed;inset:0;z-index:2100000000;background:#131f2bb3;display:flex;align-items:center;justify-content:center;padding:14px;backdrop-filter:blur(4px);font-family:inherit}
.sos629b-dialog{width:min(630px,100%);max-height:92dvh;overflow:auto;border:1px solid #e7ddd0;background:#fffcf8;color:#283844;border-radius:19px;box-shadow:0 25px 90px #101d295e}
.sos629b-header{display:flex;justify-content:space-between;gap:14px;background:#fff;padding:22px;border-bottom:1px solid #e9e0d5}
.sos629b-header small{font-size:10px;color:#8b6d49;letter-spacing:.13em;font-weight:800}
.sos629b-header h2{font-size:22px;line-height:1.2;letter-spacing:-.02em;margin:7px 0 4px;font-weight:850}
.sos629b-header p{font-size:12px;color:#71808a;margin:0}
.sos629b-close{border:1px solid #dfd7cd;border-radius:10px;background:#fff;color:#283844;font-size:22px;min-width:37px;height:37px;cursor:pointer}
.sos629b-body{display:grid;gap:10px;padding:19px 23px}
.sos629b-body>label{font-size:12px;font-weight:800}
.sos629b-search{display:flex;gap:9px}
.sos629b-search input{flex:1;min-width:0;border:1px solid #d6cdc2;background:#fff;color:#283844;padding:12px;border-radius:10px;font-size:13px}
.sos629b-search>button{background:#304957;color:#fff;border:0;border-radius:10px;padding:10px 14px;font-size:12px;font-weight:800;cursor:pointer}
.sos629b-search>button:disabled{opacity:.45;cursor:not-allowed}
.sos629b-hint{font-size:11px;color:#79848b;margin:0}
.sos629b-error{background:#fff0e9;color:#9c4530;border:1px solid #edc8b9;border-radius:9px;padding:11px;font-size:12px;margin:0}
.sos629b-loading,.sos629b-empty{font-size:12px;color:#75818a;padding:22px 12px;text-align:center}
.sos629b-results{display:grid;gap:6px;max-height:42vh;overflow:auto}
.sos629b-job{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;border:1px solid #e4d9ca;background:#fff;border-radius:11px;padding:13px;text-align:left;cursor:pointer;color:#263b47}
.sos629b-job:hover{background:#f7f1e9;border-color:#c5a783}
.sos629b-job span{display:grid;gap:4px;min-width:0}.sos629b-job strong{font-size:12px;overflow-wrap:anywhere}.sos629b-job small{font-size:11px;color:#80909b;overflow-wrap:anywhere}.sos629b-job em{font-size:11px;font-style:normal;color:#7a5834;font-weight:800}
.sos629b-footer{display:flex;justify-content:end;padding:12px 22px 18px}.sos629b-footer button{border:1px solid #dcd1c6;background:white;border-radius:9px;color:#364650;padding:10px 16px;cursor:pointer}
@media(max-width:600px){.sos629b-launcher{right:12px;bottom:12px}.sos629b-launch-button{font-size:12px;padding:13px}.sos629b-header{padding:16px}.sos629b-body{padding:14px}.sos629b-search{flex-direction:column}.sos629b-search>button{min-height:40px}}
@media print{.sos629b-launcher,.sos629b-overlay{display:none!important}}
</style>


<style>
.sos655-sticker-toolbar{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:2147483640;
 display:flex;align-items:center;justify-content:center;gap:9px;max-width:calc(100vw - 24px);
 padding:10px;background:#f9f6f2!important;border:1px solid #e7d6c5!important;border-radius:14px;
 box-shadow:0 14px 35px #402b2238;pointer-events:auto}
.sos655-sticker-toolbar button{cursor:pointer;min-height:42px;white-space:nowrap;
 border-radius:9px!important;padding:10px 14px!important;font-size:12px!important;font-weight:750!important}
.sos655-print-button{background:#805a3e!important;color:#fffdf7!important;border:1px solid #805a3e!important}
.sos655-back-button{background:#fffcf7!important;color:#6f4d36!important;border:1px solid #e7d6c5!important}
@media(max-width:500px){.sos655-sticker-toolbar{bottom:7px;padding:7px;gap:5px}.sos655-sticker-toolbar button{padding:10px!important;font-size:11px!important}}
@media print {
 html[data-sos655-print-sticker="1"] body * {visibility:hidden!important}
 html[data-sos655-print-sticker="1"] [data-sos655-sticker-print],
 html[data-sos655-print-sticker="1"] [data-sos655-sticker-print] * {visibility:visible!important}
 html[data-sos655-print-sticker="1"] [data-sos655-sticker-print] {
   position:fixed!important;top:0!important;left:0!important;max-width:100%!important;
   background:white!important;margin:0!important;padding:0!important;
   box-shadow:none!important;border-color:transparent!important
 }
 html[data-sos655-print-sticker="1"] .sos655-sticker-toolbar{display:none!important}
}
</style>


<style>
/* SERVICING_OS_COUNTER_657: visible IN the sticker modal. */
.sos657-sticker-controls{position:sticky;top:0;z-index:999;display:flex!important;align-items:center;justify-content:center;flex-wrap:wrap;gap:9px;padding:10px!important;background:#f9f6f2!important;border:1px solid #e7d6c5!important;border-radius:10px;margin:7px 0 12px;color:#3c2c25!important}
.sos657-sticker-controls label{display:flex;align-items:center;gap:7px;font-size:12px!important;font-weight:700!important;color:#72523d!important}
.sos657-sticker-controls select{min-height:41px!important;padding:8px!important;border-radius:8px!important;background:#fffcf7!important;border:1px solid #dcc4ad!important;color:#3c2c25!important}
.sos657-sticker-controls .sos657-sticker-print{min-height:42px!important;border-radius:9px!important;padding:10px 15px!important;border:1px solid #805a3e!important;background:#805a3e!important;color:white!important;font-weight:800!important;font-size:12px!important;cursor:pointer}
.sos657-sticker-controls .sos657-sticker-back{min-height:42px!important;border-radius:9px!important;padding:10px 15px!important;border:1px solid #e7d6c5!important;background:#fffcf7!important;color:#654733!important;font-size:12px!important;cursor:pointer}.sos657-sticker-controls [role=alert]{font-size:11px;color:#a33d2c}.sos655-sticker-toolbar{display:none!important}
@media print{.sos657-sticker-controls{display:none!important}}
</style>

<!-- SERVICING_OS_COUNTER_657 -->

<style>
/* SERVICING_OS_COUNTER_658: symmetric input heights and highly visible print inside QR dialog */
.sos658-sticker-tools{display:grid!important;grid-template-columns:minmax(190px,1fr) auto auto!important;align-items:end!important;gap:9px!important;width:100%!important;max-width:100%!important;margin:10px 0 14px!important;position:sticky!important;top:0;z-index:1005!important;padding:13px!important;background:#fffaf3!important;border:1px solid #dbc4ac!important;border-radius:12px!important;box-shadow:0 3px 10px #5c3f2912!important}
.sos658-sticker-tools label{display:grid!important;gap:5px!important;min-width:0;font-size:11px!important;font-weight:750!important;color:#654631!important}
.sos658-sticker-tools select{min-height:44px!important;height:44px!important;width:100%!important;max-width:none!important;font-size:13px!important;padding:9px 33px 9px 12px!important;background:#fffdf9!important;border:1px solid #d8bfa9!important;border-radius:9px!important;color:#3c2c25!important}
.sos658-sticker-tools button{min-height:44px!important;height:44px!important;white-space:nowrap!important;font-size:12px!important;border-radius:9px!important;padding:11px 14px!important;cursor:pointer!important;visibility:visible!important;opacity:1!important}
.sos658-sticker-tools button.sos657-sticker-print{background:#805a3e!important;color:#fff!important;border:1px solid #805a3e!important;font-weight:800!important}
.sos658-sticker-tools button.sos657-sticker-back{background:#fffcf7!important;color:#65432f!important;border:1px solid #d8bfa9!important}
:where([role="dialog"]:has(> .sos658-sticker-tools),[role="dialog"]:has(.sos658-sticker-tools)) :is(input:not([type="checkbox"]), select){height:44px!important;min-height:44px!important;border-radius:9px!important;border:1px solid #d8bfa9!important;padding:9px 12px!important;background:#fffcf7!important;color:#3c2c25!important;min-width:0!important;box-sizing:border-box!important}
@media(max-width:720px){.sos658-sticker-tools{grid-template-columns:1fr 1fr!important}.sos658-sticker-tools label{grid-column:1/-1}.sos658-sticker-tools button{white-space:normal!important;height:auto!important;min-height:44px!important;padding:8px!important}}
@media print{.sos658-sticker-tools{display:none!important}}
</style>

<!-- SERVICING_OS_COUNTER_658 -->
