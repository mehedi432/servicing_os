<script setup>
// SERVICING OS 6.52 — genuine draft ERPNext Sales Invoice from Counter.
import { computed, onMounted, ref, unref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({ initialJob: { type: String, default: '' } })
const bn = computed(() => String(unref(currentLanguage) || 'en').toLowerCase().startsWith('bn'))
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref(null)
const jobs = ref([])
const catalog = ref([])
const selectedJob = ref('')
const notes = ref('')
watch(() => props.initialJob, value => { if (value && !selectedJob.value) selectedJob.value = String(value) }, { immediate: true })
const rows = ref([{ item_code: '', qty: 1, rate: '' }])
const customerLabel = computed(() => {
  const job = jobs.value.find(j => j.name === selectedJob.value)
  return job ? (job.customer_name || job.customer || '') : ''
})
const estimated = computed(() => rows.value.reduce((sum,r) => sum + (Number(r.qty)||0)*(Number(r.rate)||0),0))

function parseError(result, fallback) {
  try {
    if (result?._server_messages) {
      const entries = JSON.parse(result._server_messages)
      if (entries?.length) {
        const message = JSON.parse(entries[0])?.message
        if (message) return message.replace(/<[^>]*>/g,'')
      }
    }
  } catch (_) {}
  return (typeof result?.message === 'string' ? result.message : '') || result?.exception || fallback
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/method/servicing_os.api.counter_invoice_652.get_counter_invoice_setup', {
      method: 'GET', headers: { Accept: 'application/json' }, credentials: 'same-origin', cache: 'no-store'
    })
    const data = await response.json()
    if (!response.ok || data.exc) throw new Error(parseError(data,'Unable to load billing configuration'))
    jobs.value = Array.isArray(data.message?.jobs) ? data.message.jobs : []
    catalog.value = Array.isArray(data.message?.items) ? data.message.items : []
  } catch(e) { error.value = e?.message || 'Unable to load invoice setup' }
  finally { loading.value = false }
}
onMounted(load)

function addLine(){ if(rows.value.length<20) rows.value.push({item_code:'',qty:1,rate:''}) }
function removeLine(index){ if(rows.value.length>1) rows.value.splice(index,1) }
async function createDraft(){
  if (saving.value || success.value) return
  error.value = ''
  if (!selectedJob.value) {error.value = bn.value?'একটি সেভ করা সার্ভিস জব নির্বাচন করুন':'Select a saved Service Job';return}
  if (rows.value.some(x => !x.item_code || !Number.isFinite(Number(x.qty)) || Number(x.qty)<=0 || !Number.isFinite(Number(x.rate)) || Number(x.rate)<0 || x.rate==='')) {
    error.value = bn.value ? 'প্রতি সারিতে পণ্য, পরিমাণ এবং রেট দিন' : 'Every row requires a service Item, positive quantity and valid rate'
    return
  }
  saving.value = true
  try {
    const token = window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
    const response = await fetch('/api/method/servicing_os.api.counter_invoice_652.create_counter_invoice_draft',{
      method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json', ...(token?{'X-Frappe-CSRF-Token':token}:{})},
      body:JSON.stringify({job_name:selectedJob.value,items:rows.value,remarks:notes.value})
    })
    const data = await response.json()
    if (!response.ok || data.exc || !data.message?.invoice) throw new Error(parseError(data,'Could not create invoice draft'))
    success.value = data.message
  } catch(e) { error.value = e?.message || 'Unable to save invoice' }
  finally {saving.value=false}
}
function newDraft(){success.value=null;selectedJob.value='';notes.value='';rows.value=[{item_code:'',qty:1,rate:''}];load()}
</script>

<template>
  <section class="sos652-invoiceform" aria-label="Draft service invoice">
    <div v-if="loading" class="sos652-invoice-note">{{ bn ? 'বিলিং তথ্য লোড হচ্ছে...' : 'Loading service jobs and billable items…' }}</div>
    <template v-else-if="success">
      <div class="sos652-invoice-success" role="status">
        <strong>{{ bn ? 'খসড়া ইনভয়েস তৈরি হয়েছে' : 'Draft invoice created' }}</strong>
        <div class="sos652-invoice-number">{{ success.invoice }}</div>
        <p>{{ success.company }} · {{ success.currency }} {{ Number(success.grand_total || 0).toFixed(2) }}</p>
        <p>{{ bn ? 'এটি এখনো সাবমিট করা হয়নি, পেমেন্টও পোস্ট হয়নি।' : 'This is a draft, not a submitted invoice. No payment or ledger entry has been posted.' }}</p>
        <button type="button" class="sos652-invoice-primary" @click="newDraft">{{ bn ? 'নতুন খসড়া' : 'Create another draft' }}</button>
      </div>
    </template>
    <template v-else>
      <div class="sos652-invoice-formgrid">
        <label class="sos652-invoice-job">
          <span>{{ bn ? 'সেভ করা সার্ভিস জব' : 'Saved Service Job' }} *</span>
          <input v-model.trim="selectedJob" list="sos652-billjobs" :placeholder="bn ? 'জব নম্বর লিখুন' : 'Search or enter Service Job number'" autocomplete="off" />
          <datalist id="sos652-billjobs"><option v-for="j in jobs" :key="j.name" :value="j.name">{{ j.customer_name || j.customer }} · {{ j.status }}</option></datalist>
          <small v-if="customerLabel">{{ customerLabel }}</small>
        </label>
        <label class="sos652-invoice-job">
          <span>{{ bn ? 'নোট / বিবরণ' : 'Invoice remarks' }}</span>
          <input v-model.trim="notes" maxlength="500" :placeholder="bn ? 'ঐচ্ছিক' : 'Optional internal reference'" />
        </label>
      </div>
      <div class="sos652-invoice-lines">
        <div class="sos652-invoice-linetitle"><strong>{{ bn ? 'সার্ভিস চার্জ' : 'Service line items' }}</strong><button type="button" @click="addLine" :disabled="rows.length>=20">+ {{ bn ? 'সারি যোগ' : 'Add line' }}</button></div>
        <datalist id="sos652-billitems"><option v-for="item in catalog" :key="item.name" :value="item.name">{{ item.item_name }}</option></datalist>
        <div v-for="(r,i) in rows" :key="i" class="sos652-invoice-line">
          <label><span>{{ bn ? 'পণ্য / সার্ভিস আইডি' : 'Service Item Code' }}</span><input v-model.trim="r.item_code" list="sos652-billitems" placeholder="Service Item" /></label>
          <label><span>{{ bn ? 'পরিমাণ' : 'Qty' }}</span><input v-model.number="r.qty" type="number" min="0.01" step="0.01" /></label>
          <label><span>{{ bn ? 'রেট (BDT)' : 'Rate (BDT)' }}</span><input v-model.number="r.rate" type="number" min="0" step="0.01" placeholder="0.00" /></label>
          <button type="button" class="sos652-invoice-remove" :disabled="rows.length===1" @click="removeLine(i)" :title="bn ? 'সারি মুছুন' : 'Remove row'">×</button>
        </div>
      </div>
      <div class="sos652-invoice-total"><span>{{ bn ? 'সম্ভাব্য মোট (কর ব্যতীত)' : 'Estimated subtotal, before tax' }}</span><strong>৳ {{ estimated.toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2}) }}</strong></div>
      <p class="sos652-invoice-note">{{ bn ? 'এখানে শুধু নন-স্টক সার্ভিস আইটেম দিয়ে ড্রাফট ইনভয়েস তৈরি হবে। ভ্যাট ও হিসাবের চূড়ান্ত হিসাব ERPNext করবে।' : 'Only existing non-stock service Items are supported here. ERPNext calculates final taxes and totals when the draft is saved; physical parts use your stock-aware billing flow.' }}</p>
      <p v-if="error" class="sos652-invoice-error" role="alert">{{ error }}</p>
      <div class="sos652-invoice-buttons"><button type="button" @click="load" :disabled="saving">{{ bn ? 'রিফ্রেশ' : 'Refresh' }}</button><button type="button" class="sos652-invoice-primary" :disabled="saving" @click="createDraft">{{ saving ? (bn ? 'সেভ হচ্ছে...' : 'Saving…') : (bn ? 'খসড়া ইনভয়েস সেভ' : 'Save Draft Invoice') }}</button></div>
    </template>
    <p v-if="error && loading" class="sos652-invoice-error" role="alert">{{ error }}</p>
    <div v-if="!loading && !success && error && !jobs.length" class="sos652-invoice-retry"><button type="button" @click="load">Retry loading</button></div>
  </section>
</template>

<style>
.sos652-invoiceform,.sos652-invoiceform *{box-sizing:border-box}
.sos652-invoiceform{padding:13px;border:1px solid #e7d6c5;border-radius:12px;background:#fffcf7;color:#3c2c25}
.sos652-invoice-formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:15px}
.sos652-invoiceform label{display:flex;flex-direction:column;gap:5px;min-width:0;font-size:11px;font-weight:650;color:#5e4535}
.sos652-invoiceform input{width:100%;min-height:40px;padding:9px 10px;border:1px solid #ddc7b4!important;border-radius:8px!important;background:#fffefa!important;color:#3c2c25!important;font-size:12px;font-family:inherit}
.sos652-invoiceform input:focus{outline:2px solid #c99e78;outline-offset:1px}
.sos652-invoiceform label small{font-size:10px;color:#8b725e}
.sos652-invoice-linetitle{display:flex;justify-content:space-between;align-items:center;margin:0 0 10px;gap:10px}
.sos652-invoice-linetitle strong{font-size:13px}
.sos652-invoice-linetitle button,.sos652-invoice-buttons button,.sos652-invoice-retry button{padding:9px 13px;border:1px solid #e7d6c5!important;background:#f4e3d3!important;border-radius:8px!important;color:#684933!important;font-size:12px;font-weight:700}
.sos652-invoice-line{display:grid;grid-template-columns:minmax(0,5fr) minmax(66px,1fr) minmax(105px,2fr) 32px;gap:9px;align-items:end;margin:0 0 10px}
.sos652-invoice-line .sos652-invoice-remove{height:38px;border:1px solid #e7d6c5;background:#fff4ee;border-radius:8px;color:#8a513b;font-size:20px}
.sos652-invoice-line button:disabled{opacity:.5;cursor:not-allowed}
.sos652-invoice-total{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;border-top:1px solid #e7d6c5;color:#80614b;font-size:12px}
.sos652-invoice-total strong{font-size:16px;color:#3c2c25}
.sos652-invoice-note{padding:10px 12px;background:#f9f1e8;border-radius:9px;color:#836c57;font-size:11px;line-height:1.55;margin:8px 0 14px}
.sos652-invoice-error{padding:10px 12px;background:#fff2ed;color:#9c4431;border:1px solid #e4c0b3;border-radius:9px;font-size:12px;overflow-wrap:anywhere}
.sos652-invoice-buttons{display:flex;justify-content:flex-end;gap:8px;margin-top:10px}
.sos652-invoice-buttons button.sos652-invoice-primary,.sos652-invoiceform button.sos652-invoice-primary{background:#81583f!important;border-color:#81583f!important;color:#fff!important}
.sos652-invoice-success{padding:20px;text-align:center;background:#f7e9db;border-radius:10px}
.sos652-invoice-success strong{display:block;font-size:16px}.sos652-invoice-number{font-size:19px;font-weight:800;margin-top:7px}.sos652-invoice-success p{font-size:12px;color:#775741}
@media(max-width:680px){.sos652-invoice-formgrid{grid-template-columns:1fr}.sos652-invoice-line{grid-template-columns:minmax(0,1fr) minmax(72px,.4fr);}.sos652-invoice-line label:first-child{grid-column:1/-1}.sos652-invoice-line .sos652-invoice-remove{grid-column:2;grid-row:2}}
</style>
