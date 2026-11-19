<script setup>
// SOS_COUNTER_TECHNICIAN_681: compact Counter assignment; saved Service Jobs only.
import { computed, onMounted, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
const bn = computed(() => String(unref(currentLanguage) || 'en').toLowerCase().startsWith('bn'))
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const jobs = ref([])
const technicians = ref([])
const job = ref('')
const employee = ref('')
const needsSetup = ref(false)
const currentJob = computed(() => jobs.value.find(x => x.name === job.value))
async function request(method, args = {}, write = false) {
  const url = '/api/method/servicing_os.api.counter_technician_681.' + method
  const token = window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
  const params = write ? undefined : '?' + new URLSearchParams(args).toString()
  const response = await fetch(url + (params || ''), {
    method: write ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
    headers: write ? {'Content-Type': 'application/json', ...(token ? {'X-Frappe-CSRF-Token': token} : {})} : {},
    body: write ? JSON.stringify(args) : undefined,
  })
  let body = {}
  try { body = await response.json() } catch {}
  if (!response.ok || body.exc_type || body.exception) {
    const raw = body._server_messages || body.message || body.exception || `HTTP ${response.status}`
    let message = typeof raw === 'string' ? raw : JSON.stringify(raw)
    if (body._server_messages) {
      try { const v = JSON.parse(body._server_messages); message = v.map(x => JSON.parse(x).message || x).join('; ') } catch {}
    }
    throw new Error(message)
  }
  return body.message || {}
}
async function refresh() {
  if (loading.value) return
  loading.value = true; error.value = ''; success.value = ''
  try {
    const data = await request('get_counter_technicians')
    jobs.value = data.jobs || []
    technicians.value = data.technicians || []
    needsSetup.value = !!data.setup_needed
    if (job.value && !jobs.value.some(x => x.name === job.value)) job.value = ''
    if (job.value) employee.value = jobs.value.find(x => x.name === job.value)?.assigned_employee || ''
  } catch (e) { error.value = e.message || String(e) }
  finally { loading.value = false }
}
function jobChanged() {
  success.value = ''; error.value = ''
  employee.value = currentJob.value?.assigned_employee || ''
}
async function assign() {
  if (!job.value || !employee.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    const result = await request('assign_counter_technician', {job_name: job.value, employee: employee.value}, true)
    const found = jobs.value.find(x => x.name === result.job)
    if (found) found.assigned_employee = result.employee
    success.value = bn.value ? 'টেকনিশিয়ান বরাদ্দ সংরক্ষিত হয়েছে' : `Assigned ${result.employee_name} to ${result.job}`
    window.dispatchEvent(new CustomEvent('servicing-os:technician-assigned', {detail: result}))
  } catch (e) { error.value = e.message || String(e) }
  finally { saving.value = false }
}
onMounted(refresh)
</script>

<template>
  <section class="sos681-techbar" aria-label="Assign service technician">
    <div class="sos681-heading">
      <span class="sos681-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="7" r="3"/><path d="M5 21v-3a7 7 0 0 1 14 0v3M16 10l2 2 4-4"/></svg></span>
      <div class="sos681-heading-text"><strong>{{ bn ? 'টেকনিশিয়ান বরাদ্দ' : 'Assign Technician' }}</strong><small>{{ bn ? 'সার্ভিস জব সেভ করার পরে টেকনিশিয়ান নির্বাচন করুন' : 'Save the service intake, then select its job and technician' }}</small></div>
    </div>
    <form class="sos681-controls" @submit.prevent="assign">
      <label class="sos681-field"><span>{{ bn ? 'সার্ভিস জব' : 'Recent Service Job' }}</span>
        <select v-model="job" :disabled="loading || saving || needsSetup" @change="jobChanged">
          <option value="">{{ bn ? 'সার্ভিস জব নির্বাচন করুন' : 'Select saved job' }}</option>
          <option v-for="j in jobs" :key="j.name" :value="j.name">{{ j.name }}{{ j.customer_name ? ' · ' + j.customer_name : '' }}</option>
        </select>
      </label>
      <label class="sos681-field"><span>{{ bn ? 'টেকনিশিয়ান' : 'Technician' }}</span>
        <select v-model="employee" :disabled="loading || saving || needsSetup">
          <option value="">{{ bn ? 'টেকনিশিয়ান নির্বাচন করুন' : 'Select technician' }}</option>
          <option v-for="t in technicians" :key="t.value" :value="t.value">{{ t.label }} ({{ t.value }})</option>
        </select>
      </label>
      <button class="sos681-assign" :disabled="!job || !employee || saving || loading || needsSetup" type="submit">{{ saving ? (bn ? 'সংরক্ষণ হচ্ছে…' : 'Saving…') : (bn ? 'বরাদ্দ করুন' : 'Assign') }}</button>
      <button class="sos681-refresh" :disabled="loading || saving" type="button" @click="refresh" :title="bn ? 'সাম্প্রতিক সার্ভিস জব রিফ্রেশ করুন' : 'Refresh recently saved jobs'" :aria-label="bn ? 'রিফ্রেশ' : 'Refresh jobs'">↻</button>
    </form>
    <p v-if="needsSetup" class="sos681-message sos681-error" role="alert">{{ bn ? 'Service Job টেকনিশিয়ান ফিল্ড সেটআপ প্রয়োজন।' : 'Service Job technician field requires setup by System Manager.' }}</p>
    <p v-if="error" class="sos681-message sos681-error" role="alert">{{ error }}</p>
    <p v-if="success" class="sos681-message sos681-success" role="status">{{ success }}</p>
  </section>
</template>

<style>
.sos681-techbar,.sos681-techbar *{box-sizing:border-box}
.sos681-techbar{display:flex;flex-wrap:wrap;align-items:flex-end;gap:9px 14px;padding:10px 12px;margin:0 0 12px;border:1px solid #e3cfbd;border-radius:12px;background:#f8efe5;color:#3c2c25}
.sos681-heading{display:flex;align-items:center;gap:9px;flex:0 1 225px;min-width:190px}
.sos681-icon{display:grid;place-items:center;background:#ecdbcb;color:#78563e;width:34px;height:34px;border-radius:10px;flex:0 0 34px}
.sos681-icon svg{width:19px;height:19px}
.sos681-heading-text{display:flex;flex-direction:column;gap:3px;min-width:0}
.sos681-heading-text strong{font-size:12px;line-height:1.2;font-weight:750;color:#3c2c25}
.sos681-heading-text small{font-size:10px;line-height:1.25;color:#8d735e}
.sos681-controls{display:flex;gap:8px;align-items:flex-end;flex:1 1 480px;min-width:0}
.sos681-field{display:flex;flex-direction:column;gap:4px;flex:1 1 150px;min-width:0}
.sos681-field span{font-size:10px;font-weight:700;color:#78604c}
.sos681-techbar .sos681-field select{height:35px!important;width:100%;max-width:100%;font-size:11px!important;padding:0 9px!important;border:1px solid #d8bdab!important;border-radius:8px!important;background:#fffcf7!important;color:#3c2c25!important;min-width:0}
.sos681-assign{height:35px;min-width:80px;border:0;border-radius:8px;background:#7b593e;color:#fffaf3;font-size:11px;font-weight:750;padding:0 13px;white-space:nowrap}
.sos681-assign:disabled{opacity:.48;cursor:not-allowed}
.sos681-refresh{height:35px;width:35px;flex:0 0 35px;border:1px solid #dec5b0;border-radius:8px;background:#fff9f1;color:#79543b;font-size:20px;line-height:1}
.sos681-techbar :is(button,select):focus-visible{outline:2px solid #a67e5b!important;outline-offset:2px}
.sos681-message{flex-basis:100%;margin:0;font-size:11px;line-height:1.4}
.sos681-error{color:#9b422e}.sos681-success{color:#496e48}
/* Compact only the existing Receive Device form, never other Counter modules. */
.sos681-receive-content .sos649-original-workspace > .grid,.sos681-receive-content .sos649-original-workspace > div.grid{gap:10px!important}
.sos681-receive-content .sos649-original-workspace > .grid > section,.sos681-receive-content .sos649-original-workspace > div.grid > section{padding:12px!important}
.sos681-receive-content .sos649-original-workspace :is(.gap-4,.gap-5,.gap-6,.space-y-4,.space-y-5,.space-y-6){gap:9px!important}
.sos681-receive-content .sos649-original-workspace :is(input:not([type="checkbox"]):not([type="radio"]),select):not(:where([data-servicing-control-layout="local"] *)){min-height:34px!important;padding:6px 9px!important;font-size:12px!important}
.sos681-receive-content .sos649-original-workspace textarea{padding:8px 9px!important;font-size:12px!important;min-height:56px!important;resize:vertical}
.sos681-receive-content .sos649-original-workspace label{font-size:11px!important;line-height:1.25!important}
.sos681-receive-content .sos649-original-workspace :is(.space-y-4,.space-y-5,.space-y-6)>:not([hidden])~:not([hidden]){margin-top:9px!important}
.sos681-receive-content .sos649-original-workspace :is(h2,h3){margin-bottom:7px!important}
@media(max-width:1050px){.sos681-heading{flex-basis:100%}}
@media(max-width:620px){.sos681-techbar{padding:10px}.sos681-controls{flex-wrap:wrap}.sos681-field{flex-basis:calc(50% - 8px);min-width:140px}.sos681-assign{flex:1 1 auto}}
</style>
