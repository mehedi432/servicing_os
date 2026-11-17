<script setup>
// SOS_REPAIR_RECORD_ACTIONS_699
// Embedded edit + guarded irreversible deletion for Counter and standalone Service Jobs.
import { computed, ref, watch, onUnmounted, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({ jobName: { type: String, default: '' } })
const emit = defineEmits(['saved', 'deleted'])
const bn = computed(() => String(unref(currentLanguage) || 'en').toLowerCase().startsWith('bn'))
const busy = ref(false)
const loading = ref(false)
const error = ref('')
const context = ref(null)
const mode = ref('')
const values = ref({})
const confirmName = ref('')
const acknowledge = ref(false)
let requestId = 0

function csrf() {
  return window.frappe?.csrf_token || window.csrf_token || decodeURIComponent(
    document.cookie.split('; ').find(x => x.startsWith('csrf_token='))?.split('=')?.slice(1).join('=') || '')
}
async function request(method, params = {}, post = false) {
  const url = new URL(`/api/method/servicing_os.api.job_record_actions_699.${method}`, location.origin)
  if (!post) Object.entries(params).forEach(([k,v]) => url.searchParams.set(k, String(v)))
  const init = { method: post ? 'POST' : 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (post) {
    init.headers['Content-Type'] = 'application/json'
    init.headers['X-Frappe-CSRF-Token'] = csrf()
    init.body = JSON.stringify(params)
  }
  const r = await fetch(url, init)
  let data
  try { data = await r.json() } catch { throw new Error('Server response is not JSON.') }
  if (!r.ok || data.exc || data.exc_type || data.exception) {
    let msg = data.exception || data.message || `Request failed (${r.status})`
    if (data._server_messages) {
      try { const a = JSON.parse(data._server_messages); msg = JSON.parse(a[a.length-1]).message || msg } catch { /* fall back */ }
    }
    throw new Error(typeof msg === 'string' ? msg : 'Request failed.')
  }
  return data.message || {}
}
function close() {
  if (busy.value) return
  mode.value = ''
  error.value = ''
  confirmName.value = ''
  acknowledge.value = false
}
async function refresh() {
  const id = ++requestId
  context.value = null
  loading.value = Boolean(props.jobName)
  error.value = ''
  if (!props.jobName) { loading.value = false; return }
  try {
    const data = await request('get_record_context', { job_name: props.jobName })
    if (id === requestId) context.value = data
  } catch (e) { if (id === requestId) error.value = e.message }
  finally { if (id === requestId) loading.value = false }
}
watch(() => props.jobName, () => { close(); refresh() }, { immediate: true })
onUnmounted(() => { requestId++ })
function edit() {
  if (!context.value?.can_edit) return
  values.value = Object.fromEntries(context.value.fields.map(f => [f.name, f.value ?? '']))
  error.value = ''
  mode.value = 'edit'
}
function askDelete() {
  if (!context.value?.can_delete) return
  error.value = ''
  confirmName.value = ''
  acknowledge.value = false
  mode.value = 'delete'
}
async function save() {
  if (busy.value || !context.value?.can_edit) return
  busy.value = true; error.value = ''
  try {
    const data = await request('save_job_changes', {
      job_name: props.jobName, expected_modified: context.value.modified, values: values.value
    }, true)
    mode.value = ''
    await refresh()
    emit('saved', data)
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
async function destroy() {
  if (busy.value || !acknowledge.value || confirmName.value !== props.jobName) return
  busy.value = true; error.value = ''
  try {
    const data = await request('permanently_delete_job', {
      job_name: props.jobName,
      expected_modified: context.value.modified,
      confirmation: confirmName.value
    }, true)
    mode.value = ''
    emit('deleted', data)
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <div class="sos699-actions" aria-label="Service Job record actions">
    <div class="sos699-title"><span>{{bn?'রেকর্ড নিয়ন্ত্রণ':'Record controls'}}</span><small>{{bn?'পরিবর্তন ও স্থায়ী অপসারণ':'Edit & permanent removal'}}</small></div>
    <div v-if="loading" class="sos699-hint">{{bn?'অনুমতি যাচাই হচ্ছে…':'Checking permissions…'}}</div>
    <div v-else class="sos699-controls">
      <button class="sos699-edit" type="button" :disabled="!context?.can_edit || busy" @click="edit">✎ {{bn?'জব সম্পাদনা':'Edit Job'}}</button>
      <button class="sos699-delete" type="button" :disabled="!context?.can_delete || busy" @click="askDelete">{{bn?'স্থায়ীভাবে মুছুন':'Permanently Delete'}}</button>
    </div>
    <p v-if="!loading && context && !context.can_delete" class="sos699-hint">{{context.delete_reason}}</p>
    <p v-if="!loading && context && !context.can_edit" class="sos699-hint">{{bn?'আপনার এই জব সম্পাদনার অনুমতি নেই।':'You do not have permission to edit this job.'}}</p>
    <p v-if="error && !mode" class="sos699-error" role="alert">{{error}}</p>

    <div v-if="mode" class="sos699-backdrop" role="presentation">
      <section class="sos699-dialog" role="dialog" aria-modal="true" :aria-label="mode==='edit'?'Edit Service Job':'Delete Service Job'">
        <header class="sos699-dialog-head">
          <div><small>SERVICING OS / SERVICE JOB</small><h2>{{mode==='edit'?(bn?'জব সম্পাদনা':'Edit Service Job'):(bn?'স্থায়ীভাবে মুছে ফেলুন':'Permanently Delete Job')}}</h2><p>{{jobName}}</p></div>
          <button type="button" class="sos699-x" :disabled="busy" @click="close" aria-label="Close dialog">×</button>
        </header>
        <form v-if="mode==='edit'" @submit.prevent="save">
          <p class="sos699-sub">{{bn?'সংশোধনগুলো মূল ERPNext Service Job রেকর্ডে সংরক্ষিত হবে।':'Changes are saved to the original ERPNext Service Job. Repair status and invoices are managed separately.'}}</p>
          <div class="sos699-grid">
            <label v-for="f in context.fields" :key="f.name" :class="{'sos699-wide': ['Small Text','Text','Long Text'].includes(f.fieldtype)}">
              <span>{{f.label}}<b v-if="f.reqd"> *</b></span>
              <select v-if="f.fieldtype==='Select'" v-model="values[f.name]" :required="f.reqd" :disabled="busy">
                <option v-if="!f.reqd" value="">—</option>
                <option v-for="option in f.options" :key="option" :value="option">{{option}}</option>
              </select>
              <textarea v-else-if="['Small Text','Text','Long Text'].includes(f.fieldtype)" v-model="values[f.name]" rows="2" :required="f.reqd" :disabled="busy" maxlength="3000" />
              <input v-else v-model="values[f.name]" :type="['Currency','Float','Int'].includes(f.fieldtype)?'number':'text'" :step="['Currency','Float'].includes(f.fieldtype)?'0.01':undefined" :min="['Currency','Float','Int'].includes(f.fieldtype)?0:undefined" :required="f.reqd" :disabled="busy" :maxlength="f.fieldtype==='Data'?140:undefined" />
            </label>
          </div>
          <div v-if="error" class="sos699-error" role="alert">{{error}}</div>
          <footer class="sos699-footer"><button type="button" class="sos699-cancel" :disabled="busy" @click="close">{{bn?'বাতিল':'Cancel'}}</button><button class="sos699-submit" type="submit" :disabled="busy">{{busy?(bn?'সংরক্ষণ…':'Saving…'):(bn?'পরিবর্তন সংরক্ষণ':'Save Changes')}}</button></footer>
        </form>
        <div v-else>
          <div class="sos699-warning"><strong>{{bn?'এই কাজটি ফেরানো যাবে না।':'This action cannot be undone.'}}</strong><p>{{bn?'জবের তথ্য, সংযুক্ত উপাদান ও সংশ্লিষ্ট কার্যক্রমের ইতিহাস মুছে যেতে পারে। অর্থনৈতিক সংযোগ থাকলে সিস্টেম অপসারণ আটকে দেবে।':'The Service Job, its received-components data and related activity history may be permanently removed. Financially linked or delivered records cannot be deleted.'}}</p></div>
          <label class="sos699-confirm-label"><span>{{bn?'নিশ্চিত করতে হুবহু জব নম্বর লিখুন':'Type the exact Job ID to confirm'}}: <strong>{{jobName}}</strong></span><input v-model="confirmName" :disabled="busy" autocomplete="off" spellcheck="false" /></label>
          <label class="sos699-check"><input type="checkbox" v-model="acknowledge" :disabled="busy" /><span>{{bn?'আমি বুঝেছি এটি স্থায়ীভাবে মুছে যাবে।':'I understand this is permanent and cannot be undone.'}}</span></label>
          <div v-if="error" class="sos699-error" role="alert">{{error}}</div>
          <footer class="sos699-footer"><button type="button" class="sos699-cancel" :disabled="busy" @click="close">{{bn?'ফিরে যান':'Keep Job'}}</button><button type="button" class="sos699-danger" :disabled="busy || !acknowledge || confirmName !== jobName" @click="destroy">{{busy?(bn?'মুছছে…':'Deleting…'):(bn?'স্থায়ীভাবে মুছুন':'Delete Permanently')}}</button></footer>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.sos699-actions{background:#fffaf3;border:1px solid #e8d9c8;border-radius:11px;padding:12px 13px;margin:12px 0;display:grid;gap:8px;font-family:inherit;color:#3e2d20}
.sos699-title{display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:8px;font-size:12px;font-weight:800}
.sos699-title small{font-size:10px;font-weight:600;color:#9a8068}
.sos699-controls{display:flex;gap:8px;flex-wrap:wrap}.sos699-controls button{border-radius:8px;padding:10px 12px;min-height:36px;font-size:11px;font-weight:750;cursor:pointer}
.sos699-edit{border:1px solid #cfb799;background:#6e5038;color:white}.sos699-delete{border:1px solid #dbb3a6;background:#fff7f4;color:#a04630}
.sos699-controls button:disabled{opacity:.48;cursor:not-allowed}.sos699-hint{font-size:10px;color:#9a7866;line-height:1.5;margin:0}
.sos699-backdrop{position:fixed;inset:0;z-index:50000;background:rgba(35,22,14,.56);display:flex;align-items:center;justify-content:center;padding:18px}
.sos699-dialog{width:min(780px,100%);max-height:min(90vh,950px);overflow:auto;background:#fffdf9;border:1px solid #d8c3ac;border-radius:18px;box-shadow:0 25px 90px #21130655;padding:22px;color:#3c2d22}
.sos699-dialog-head{display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid #ecddcc;padding-bottom:15px;margin-bottom:15px;gap:15px}.sos699-dialog-head small{font-size:10px;letter-spacing:.12em;font-weight:800;color:#a58564}
.sos699-dialog-head h2{font-size:23px;margin:4px 0;letter-spacing:-.04em}.sos699-dialog-head p{font-size:12px;color:#866b53;margin:0}
.sos699-x{border:1px solid #e2d3c1;background:#faf0e5;border-radius:9px;min-width:37px;min-height:37px;color:#6d4d36;font-size:23px;cursor:pointer}
.sos699-sub{font-size:12px;color:#866c54;margin:0 0 15px;line-height:1.5}
.sos699-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px 12px}
.sos699-grid label,.sos699-confirm-label{min-width:0;display:grid;gap:5px;font-size:11px;font-weight:750;color:#795d46}
.sos699-grid label span b{color:#a43f2f}.sos699-grid label.sos699-wide{grid-column:span 3}
.sos699-grid input,.sos699-grid select,.sos699-grid textarea,.sos699-confirm-label input{width:100%;background:#fff;border:1px solid #dccab7;border-radius:9px;min-height:36px;padding:8px 10px;color:#3d2a1e;font:inherit;font-size:12px;box-sizing:border-box}
.sos699-grid textarea{resize:vertical;min-height:58px}.sos699-grid input:focus,.sos699-grid select:focus,.sos699-grid textarea:focus,.sos699-confirm-label input:focus{outline:2px solid #b99571;outline-offset:1px}
.sos699-footer{display:flex;justify-content:flex-end;gap:8px;margin-top:17px;flex-wrap:wrap}
.sos699-footer button{font:inherit;font-weight:800;font-size:12px;border-radius:9px;padding:10px 16px;min-height:39px;cursor:pointer}
.sos699-footer button:disabled{cursor:not-allowed;opacity:.48}.sos699-cancel{border:1px solid #d9c7b3;background:#fffaf2;color:#72563c}
.sos699-submit{border:1px solid #6e5038;background:#6e5038;color:white}.sos699-danger{border:1px solid #ad4434;background:#a43d2d;color:white}
.sos699-error{border-radius:8px;background:#ffede7;color:#a23b2c;padding:10px;font-size:11px;line-height:1.4;overflow-wrap:anywhere}
.sos699-warning{border:1px solid #e6b4a5;background:#fff0ea;border-radius:12px;padding:14px;margin:0 0 15px}.sos699-warning strong{font-size:13px;color:#923c2c}.sos699-warning p{font-size:12px;line-height:1.5;color:#955d4c;margin:7px 0 0}
.sos699-confirm-label{margin:10px 0}.sos699-confirm-label strong{overflow-wrap:anywhere;color:#513829}
.sos699-check{display:flex;align-items:flex-start;gap:8px;margin-top:13px;font-size:11px;color:#785e48;cursor:pointer}.sos699-check input{accent-color:#994632;margin-top:2px}
@media(max-width:720px){.sos699-dialog{padding:15px}.sos699-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sos699-grid label.sos699-wide{grid-column:span 2}}
@media(max-width:450px){.sos699-grid{grid-template-columns:1fr}.sos699-grid label.sos699-wide{grid-column:span 1}.sos699-controls button{flex:1}}
</style>
