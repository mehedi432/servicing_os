<script setup>
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
  <Teleport to="body">
    <div v-if="!pickerOpen && !stickerJob" class="sos629b-launcher">
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
