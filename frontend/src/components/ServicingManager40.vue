<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { getOverview40, getBillPreview40, createBill40, registerJob40, findParts40 } from '../api/manager40.js';

const props = defineProps({ initialPage: { type: String, default: 'overview' } });
const emit = defineEmits(['close', 'receipt']);
const page = ref(props.initialPage === 'jobs' ? 'jobs' : 'overview');
watch(() => props.initialPage, value => { page.value = value === 'jobs' ? 'jobs' : 'overview'; });
const lang = ref(localStorage.getItem('servicing40_lang') === 'bn' ? 'bn' : 'en');
const isBn = computed(() => lang.value === 'bn');
function tr(en, bn) { return isBn.value ? bn : en; }
function toggleLanguage() { lang.value = isBn.value ? 'en' : 'bn'; localStorage.setItem('servicing40_lang', lang.value); }
const busy = ref(false), error = ref(''), data = ref({counts:{}, jobs:[], shop:'', company:''});
const search = ref('');
const jobs = computed(() => (data.value.jobs || []).filter(job => {
  const q = search.value.trim().toLowerCase();
  return !q || [job.name, job.customer_name, job.customer, job.brand, job.device_model,
                  job.serial_number, job.reported_problem, job.status].some(v => String(v || '').toLowerCase().includes(q));
}));
const recent = computed(() => jobs.value.slice(0, 8));
async function refresh() {
  busy.value = true; error.value = '';
  try { data.value = await getOverview40(); }
  catch (e) { error.value = e.message || 'Unable to load overview'; }
  finally { busy.value = false; }
}
onMounted(refresh);

const receiving = ref(false), saving = ref(false), registerError = ref('');
const initialForm = () => ({ customer_name:'', mobile:'', device_type:'Laptop', brand:'', device_model:'',
 serial_number:'', reported_problem:'', accessories_received:'', priority:'Normal', estimated_cost:0 });
const form = ref(initialForm());
async function register() {
  if (saving.value) return;
  registerError.value = '';
  if (!data.value.shop) { registerError.value = 'Shop configuration is not ready.'; return; }
  if (!form.value.customer_name.trim() || !form.value.mobile.trim() || !form.value.reported_problem.trim()) {
    registerError.value = tr('Customer, mobile and problem are required.', 'কাস্টমার, মোবাইল ও সমস্যার বিবরণ আবশ্যক।'); return;
  }
  saving.value = true;
  try {
    const result = await registerJob40({...form.value, shop:data.value.shop});
    form.value = initialForm(); receiving.value = false; page.value = 'jobs';
    await refresh();
    if (result?.service_job) emit('receipt', result.service_job);
  } catch (e) { registerError.value = e.message || 'Unable to create service job'; }
  finally { saving.value = false; }
}
const billOpen = ref(false), billBusy = ref(false), billError = ref(''), billResult = ref(null);
const billJob = ref(''), labour = ref(0), parts = ref([]), partQuery = ref(''), partMatches = ref([]);
async function openBill(job) {
  billOpen.value = true; billBusy.value = true; billError.value = ''; billResult.value = null;
  billJob.value = job.name || job; partQuery.value = ''; partMatches.value = [];
  try {
    const preview = await getBillPreview40(billJob.value);
    labour.value = Number(preview.labour_amount || 0);
    parts.value = (preview.parts || []).map(p => ({item_code:p.item_code, qty:Number(p.qty), rate:Number(p.rate || 0), source:p.source}));
    if (preview.existing_invoice) billResult.value = {invoice: preview.existing_invoice, already_exists:true};
  } catch (e) { billError.value = e.message || 'Billing preview unavailable'; }
  finally { billBusy.value = false; }
}
async function searchPart() {
  try { partMatches.value = await findParts40(partQuery.value); }
  catch (e) { billError.value = e.message; }
}
function addPart(item) {
  parts.value.push({item_code:item.name, qty:1, rate:Number(item.standard_rate || 0), source:'Manual'});
  partQuery.value = ''; partMatches.value = [];
}
const total = computed(() => Number(labour.value || 0) + parts.value.reduce((s,p) => s + Number(p.qty || 0) * Number(p.rate || 0), 0));
async function saveBill(submitInvoice = false) {
  if (billBusy.value || billResult.value) return;
  billError.value = '';
  if (!window.confirm(submitInvoice ? tr('Create and submit this invoice now? This will post accounting entries.', 'এখনই ইনভয়েস সাবমিট করবেন? এতে হিসাবরক্ষণে এন্ট্রি হবে।') : tr('Create a draft invoice for this service job?', 'এই সার্ভিস জবের ড্রাফট ইনভয়েস তৈরি করবেন?'))) return;
  billBusy.value = true;
  try {
    billResult.value = await createBill40(billJob.value, Number(labour.value || 0),
      parts.value.map(p => ({item_code:p.item_code, qty:Number(p.qty), rate:Number(p.rate)})), submitInvoice);
    await refresh();
  } catch (e) { billError.value = e.message || 'Invoice creation failed'; }
  finally { billBusy.value = false; }
}
async function submitDraft() {
  if (billBusy.value || !billResult.value?.invoice) return;
  if (!window.confirm(tr('Submit this invoice and post accounting entries?', 'এই ইনভয়েস সাবমিট করে হিসাবরক্ষণ এন্ট্রি করবেন?'))) return;
  billBusy.value = true;
  try {
    billResult.value = await createBill40(billJob.value, 0, [], true);
  } catch (e) { billError.value = e.message || 'Unable to submit invoice'; }
  finally { billBusy.value = false; }
}
function printInvoice() {
  if (!billResult.value?.invoice) return;
  const url = '/printview?doctype=Sales%20Invoice&name=' + encodeURIComponent(billResult.value.invoice);
  window.open(url, '_blank', 'noopener,noreferrer');
}
function amount(v) { return new Intl.NumberFormat(isBn.value ? 'bn-BD' : 'en-BD', { maximumFractionDigits: 2 }).format(Number(v || 0)); }
</script>

<template>
<div class="s40-root" role="dialog" aria-modal="true" aria-label="SERVICING OS operations">
  <aside class="s40-sidebar">
    <div class="s40-brand"><div class="s40-logo">S</div><div><strong>SERVICING OS</strong><span>{{ tr('Shop control center', 'দোকান পরিচালনা কেন্দ্র') }}</span></div></div>
    <div class="s40-caption">{{ tr('WORKSPACE', 'ওয়ার্কস্পেস') }}</div>
    <button type="button" class="s40-nav" :class="{selected:page==='overview'}" @click="page='overview'"><span>▦</span>{{ tr('Overview', 'ওভারভিউ') }}</button>
    <button type="button" class="s40-nav" :class="{selected:page==='jobs'}" @click="page='jobs'"><span>⌘</span>{{ tr('Service Jobs', 'সার্ভিস জব') }}<small>{{ data.counts?.total || 0 }}</small></button>
    <button type="button" class="s40-nav" @click="emit('close')"><span>▤</span>{{ tr('Counter Operations', 'কাউন্টার অপারেশন') }}</button>
    <div class="s40-grow"></div>
    <div class="s40-shop">{{ data.company || data.shop || 'SERVICING OS' }}<small>{{ tr('Powered by your private ERPNext backend', 'আপনার ERPNext ব্যাকএন্ডে সংযুক্ত') }}</small></div>
    <button type="button" class="s40-language" @click="toggleLanguage">🌐 {{ isBn ? 'English' : 'বাংলা ভাষা' }}</button>
  </aside>
  <main class="s40-main">
    <header class="s40-top"><div><div class="s40-overline">{{ tr('OPERATIONS', 'অপারেশন') }}</div>
      <h1>{{ page==='overview' ? tr('Business Overview', 'ব্যবসার ওভারভিউ') : tr('Service Jobs', 'সার্ভিস জবসমূহ') }}</h1>
      <p>{{ tr('Manage your repair counter without opening ERPNext Desk.', 'ERPNext ডেস্ক না খুলেই সার্ভিসিং ব্যবসা পরিচালনা করুন।') }}</p></div>
      <div class="s40-top-actions"><button type="button" class="s40-btn s40-light" @click="refresh">↻ {{ tr('Refresh', 'রিফ্রেশ') }}</button><button type="button" class="s40-btn s40-primary" @click="receiving=true">＋ {{ tr('Register Service Job', 'নতুন সার্ভিস জব') }}</button></div>
    </header>
    <div v-if="error" class="s40-error">{{ error }}</div>
    <div v-if="busy" class="s40-muted">{{ tr('Loading current data…', 'তথ্য লোড হচ্ছে…') }}</div>
    <template v-if="page==='overview'">
      <div class="s40-stats">
        <div class="s40-stat"><span>{{ tr('Total Jobs', 'মোট জব') }}</span><strong>{{ amount(data.counts?.total) }}</strong><small>{{ tr('All recorded jobs', 'মোট রেকর্ডকৃত জব') }}</small></div>
        <div class="s40-stat"><span>{{ tr('New / Received', 'নতুন / রিসিভ') }}</span><strong>{{ amount(data.counts?.new) }}</strong><small>{{ tr('Waiting for action', 'কাজের অপেক্ষায়') }}</small></div>
        <div class="s40-stat"><span>{{ tr('In Repair', 'মেরামত চলছে') }}</span><strong>{{ amount(data.counts?.repairing) }}</strong><small>{{ tr('Work in progress', 'কাজ চলমান') }}</small></div>
        <div class="s40-stat"><span>{{ tr('Ready', 'ডেলিভারির জন্য প্রস্তুত') }}</span><strong>{{ amount(data.counts?.ready) }}</strong><small>{{ tr('Awaiting collection', 'কাস্টমারের অপেক্ষায়') }}</small></div>
        <div class="s40-stat"><span>{{ tr('Delivered', 'ডেলিভারি হয়েছে') }}</span><strong>{{ amount(data.counts?.delivered) }}</strong><small>{{ tr('Completed handovers', 'সম্পন্ন ডেলিভারি') }}</small></div>
        <div class="s40-stat"><span>{{ tr('Received Today', 'আজকের রিসিভ') }}</span><strong>{{ amount(data.counts?.today) }}</strong><small>{{ tr('Today’s intake', 'আজকের জব গ্রহণ') }}</small></div>
      </div>
      <div class="s40-panel"><div class="s40-panel-head"><div><h2>{{ tr('Recent Service Jobs', 'সাম্প্রতিক সার্ভিস জব') }}</h2><p>{{ tr('Select a job to bill labour and used spare parts.', 'সার্ভিস চার্জ ও ব্যবহৃত যন্ত্রাংশের বিল তৈরি করুন।') }}</p></div><button class="s40-link" @click="page='jobs'">{{ tr('View all', 'সব দেখুন') }} →</button></div>
        <div class="s40-table-wrap"><table class="s40-table"><thead><tr><th>{{ tr('Job No.', 'জব নম্বর') }}</th><th>{{ tr('Customer / Device', 'কাস্টমার / ডিভাইস') }}</th><th>{{ tr('Status', 'অবস্থা') }}</th><th>{{ tr('Action', 'অ্যাকশন') }}</th></tr></thead><tbody><tr v-for="job in recent" :key="job.name"><td class="s40-code">{{ job.name }}</td><td><strong>{{ job.customer_name || job.customer || '—' }}</strong><small>{{ [job.brand, job.device_model, job.device_type].filter(Boolean).join(' · ') }}</small></td><td><span class="s40-pill">{{ job.status || '—' }}</span></td><td><button class="s40-link" @click="openBill(job)">{{ tr('Quick Invoice', 'দ্রুত ইনভয়েস') }}</button></td></tr><tr v-if="!recent.length"><td colspan="4" class="s40-empty">{{ tr('No service jobs yet. Use Register Service Job.', 'এখনো কোনো সার্ভিস জব নেই। নতুন সার্ভিস জব তৈরি করুন।') }}</td></tr></tbody></table></div>
      </div>
    </template>
    <template v-else>
      <div class="s40-panel"><div class="s40-panel-head"><div><h2>{{ tr('Repair Register', 'সার্ভিস রেজিস্টার') }}</h2><p>{{ tr('Search jobs and create invoices directly.', 'জব খুঁজুন এবং সরাসরি ইনভয়েস তৈরি করুন।') }}</p></div><input v-model="search" class="s40-input s40-search" :placeholder="tr('Search job, customer, serial, problem…', 'জব, কাস্টমার, সিরিয়াল খুঁজুন…')" /></div>
        <div class="s40-table-wrap"><table class="s40-table"><thead><tr><th>{{ tr('Service Job', 'সার্ভিস জব') }}</th><th>{{ tr('Customer', 'কাস্টমার') }}</th><th>{{ tr('Device / Problem', 'ডিভাইস / সমস্যা') }}</th><th>{{ tr('Status', 'অবস্থা') }}</th><th>{{ tr('Invoice', 'ইনভয়েস') }}</th></tr></thead><tbody><tr v-for="job in jobs" :key="job.name"><td class="s40-code">{{ job.name }}<small>{{ job.received_date }}</small></td><td>{{ job.customer_name || job.customer }}</td><td>{{ [job.brand, job.device_model].filter(Boolean).join(' ') }}<small>{{ job.reported_problem }}</small></td><td><span class="s40-pill">{{ job.status || '—' }}</span></td><td><button class="s40-btn s40-sm s40-primary" @click="openBill(job)">{{ tr('Create Invoice', 'ইনভয়েস তৈরি') }}</button><button class="s40-link s40-receipt" @click="emit('receipt',job.name)">{{ tr('Receipt', 'রিসিট') }}</button></td></tr><tr v-if="!jobs.length"><td colspan="5" class="s40-empty">{{ tr('No matching service jobs.', 'কোনো সার্ভিস জব পাওয়া যায়নি।') }}</td></tr></tbody></table></div>
      </div>
    </template>
    <p v-if="data.sample_limited" class="s40-note">{{ tr('Status breakdown shows the 300 most recently changed jobs; total jobs includes full history.', 'স্ট্যাটাস বিভাজনে সর্বশেষ ৩০০ জব দেখানো হয়েছে; মোট জবের সংখ্যা সম্পূর্ণ।') }}</p>
  </main>

  <div v-if="receiving" class="s40-scrim" @click.self="receiving=false"><form class="s40-modal" @submit.prevent="register"><div class="s40-modal-head"><div><h2>{{ tr('Register Service Job', 'নতুন সার্ভিস জব রেজিস্ট্রেশন') }}</h2><p>{{ tr('Receive a computer, laptop or accessory for repair.', 'মেরামতের জন্য ডিভাইস গ্রহণ করুন।') }}</p></div><button type="button" class="s40-x" @click="receiving=false">×</button></div>
    <div class="s40-form-grid"><label>{{ tr('Customer Name *', 'কাস্টমারের নাম *') }}<input v-model="form.customer_name" required class="s40-input" /></label><label>{{ tr('Mobile Number *', 'মোবাইল নম্বর *') }}<input v-model="form.mobile" required class="s40-input" /></label><label>{{ tr('Device Type', 'ডিভাইসের ধরন') }}<select v-model="form.device_type" class="s40-input"><option>Laptop</option><option>Desktop</option><option>Printer</option><option>Monitor</option><option>Mobile</option><option>Other</option></select></label><label>{{ tr('Brand', 'ব্র্যান্ড') }}<input v-model="form.brand" class="s40-input" /></label><label>{{ tr('Model', 'মডেল') }}<input v-model="form.device_model" class="s40-input" /></label><label>{{ tr('Serial Number', 'সিরিয়াল নম্বর') }}<input v-model="form.serial_number" class="s40-input" /></label><label class="s40-full">{{ tr('Customer Reported Problem *', 'কাস্টমারের সমস্যার বিবরণ *') }}<textarea v-model="form.reported_problem" required rows="3" class="s40-input"></textarea></label><label class="s40-full">{{ tr('Accessories Received', 'সাথে দেওয়া সামগ্রী') }}<input v-model="form.accessories_received" class="s40-input" /></label><label>{{ tr('Priority', 'অগ্রাধিকার') }}<select v-model="form.priority" class="s40-input"><option>Normal</option><option>High</option><option>Urgent</option></select></label><label>{{ tr('Estimated Cost (BDT)', 'সম্ভাব্য খরচ (টাকা)') }}<input v-model.number="form.estimated_cost" type="number" step="0.01" min="0" class="s40-input" /></label></div>
    <div v-if="registerError" class="s40-error">{{ registerError }}</div><div class="s40-foot"><button type="button" class="s40-btn s40-light" @click="receiving=false">{{ tr('Cancel', 'বাতিল') }}</button><button :disabled="saving" type="submit" class="s40-btn s40-primary">{{ saving ? tr('Saving…', 'সংরক্ষণ হচ্ছে…') : tr('Save & Print Receipt', 'সেভ ও রিসিট প্রিন্ট') }}</button></div>
  </form></div>

  <div v-if="billOpen" class="s40-scrim" @click.self="billOpen=false"><div class="s40-modal"><div class="s40-modal-head"><div><h2>{{ tr('Quick Service Invoice', 'দ্রুত সার্ভিস ইনভয়েস') }}</h2><p>{{ billJob }} · {{ tr('No repair-stage changes required', 'রিপেয়ার স্ট্যাটাস পরিবর্তন আবশ্যক নয়') }}</p></div><button class="s40-x" @click="billOpen=false">×</button></div>
    <div v-if="billBusy" class="s40-muted">{{ tr('Processing…', 'প্রসেসিং হচ্ছে…') }}</div><div v-if="billError" class="s40-error">{{ billError }}</div>
    <div v-if="billResult" class="s40-success"><strong>{{ tr('Invoice:', 'ইনভয়েস:') }} {{ billResult.invoice }}</strong><span>{{ billResult.status === 'Submitted' ? tr('Submitted successfully. Accounting entries are posted.', 'ইনভয়েস সাবমিট হয়েছে, হিসাবরক্ষণে এন্ট্রি হয়েছে।') : tr('Draft invoice ready. You can submit it here.', 'ড্রাফট ইনভয়েস প্রস্তুত। এখান থেকেই সাবমিট করতে পারবেন।') }}</span><div class="s40-foot"><button class="s40-btn s40-primary" @click="printInvoice">{{ tr('Print / Preview Invoice', 'ইনভয়েস প্রিন্ট / প্রিভিউ') }}</button><button v-if="billResult.status !== 'Submitted'" class="s40-btn s40-light" :disabled="billBusy" @click="submitDraft">{{ tr('Submit Invoice', 'ইনভয়েস সাবমিট') }}</button></div></div>
    <template v-else><label class="s40-full s40-labour">{{ tr('Repair / Service Labour (BDT)', 'সার্ভিস / মেরামত চার্জ (টাকা)') }}<input v-model.number="labour" class="s40-input" type="number" min="0" step="0.01" /></label>
      <div class="s40-panel-head s40-billing-title"><div><h3>{{ tr('Consumed Spare Parts', 'ব্যবহৃত যন্ত্রাংশ') }}</h3><p>{{ tr('Previously consumed parts are included automatically when linked to this job.', 'পূর্বে ব্যবহার করা যন্ত্রাংশ জবের সঙ্গে যুক্ত থাকলে স্বয়ংক্রিয়ভাবে যোগ হবে।') }}</p></div></div>
      <div class="s40-table-wrap"><table class="s40-table s40-bill-table"><thead><tr><th>{{ tr('Item Code', 'আইটেম কোড') }}</th><th>{{ tr('Quantity', 'পরিমাণ') }}</th><th>{{ tr('Selling Rate', 'বিক্রয় মূল্য') }}</th><th>{{ tr('Amount', 'মোট') }}</th><th></th></tr></thead><tbody><tr v-for="(p,i) in parts" :key="i"><td class="s40-code">{{ p.item_code }}<small>{{ p.source }}</small></td><td><input v-model.number="p.qty" class="s40-input" type="number" min="0.001" step="any" /></td><td><input v-model.number="p.rate" class="s40-input" type="number" min="0" step="0.01" /></td><td>{{ amount(Number(p.qty || 0) * Number(p.rate || 0)) }}</td><td><button class="s40-x" @click="parts.splice(i,1)">×</button></td></tr><tr v-if="!parts.length"><td colspan="5" class="s40-empty">{{ tr('No linked consumed parts. Search and add them below if applicable.', 'কোনো ব্যবহৃত যন্ত্রাংশ যুক্ত নেই। প্রয়োজনে নিচে খুঁজে যোগ করুন।') }}</td></tr></tbody></table></div>
      <div class="s40-part-search"><input v-model="partQuery" class="s40-input" :placeholder="tr('Search existing ERPNext item name or code', 'আইটেমের নাম বা কোড খুঁজুন')" @input="searchPart" /><div v-if="partMatches.length" class="s40-suggestions"><button v-for="p in partMatches" :key="p.name" @click="addPart(p)">{{ p.name }} — {{ p.item_name }} · {{ amount(p.standard_rate) }}</button></div></div>
      <div class="s40-warning">{{ tr('Stock is NOT deducted by this invoice. Issue any unposted parts through stock management first; already consumed parts must not be deducted twice.', 'এই ইনভয়েসে স্টক দ্বিতীয়বার কমবে না। যে যন্ত্রাংশ এখনো ইস্যু হয়নি, তা আগে স্টক থেকে ইস্যু করুন।') }}</div>
      <div class="s40-total"><span>{{ tr('Invoice Total', 'মোট বিল') }}</span><strong>৳ {{ amount(total) }}</strong></div>
      <div class="s40-foot"><button class="s40-btn s40-light" @click="billOpen=false">{{ tr('Cancel', 'বাতিল') }}</button><button class="s40-btn s40-light" :disabled="billBusy" @click="saveBill(false)">{{ tr('Save Draft', 'ড্রাফট সেভ') }}</button><button class="s40-btn s40-primary" :disabled="billBusy" @click="saveBill(true)">{{ tr('Create & Submit Invoice', 'ইনভয়েস তৈরি ও সাবমিট') }}</button></div>
    </template>
  </div></div>
</div>
</template>

<style scoped>
.s40-root{position:fixed;inset:0;z-index:1100;background:#f5f7fb;display:flex;font-family:Inter,system-ui,-apple-system,'Noto Sans Bengali',sans-serif;color:#152238;line-height:1.45}
.s40-sidebar{width:248px;flex:none;background:#fff;border-right:1px solid #e8edf5;padding:24px 14px;display:flex;flex-direction:column;gap:8px;box-shadow:2px 0 18px #14223b05}
.s40-brand{display:flex;align-items:center;gap:11px;padding:6px 7px 22px}.s40-brand strong{font-size:16px;letter-spacing:-.02em}.s40-brand span{font-size:11px;color:#8590a1;display:block;margin-top:2px}.s40-logo{width:40px;height:40px;border-radius:12px;background:#2468ef;color:white;display:grid;place-items:center;font-size:21px;font-weight:800}
.s40-caption{font-size:10px;font-weight:750;letter-spacing:.1em;color:#98a3b3;margin:10px 13px 12px}.s40-nav{border:none;background:transparent;color:#4e5e75;display:flex;align-items:center;text-align:left;gap:12px;width:100%;padding:13px 14px;border-radius:10px;font-size:13px;font-weight:650;cursor:pointer}.s40-nav:hover{background:#f2f6fc}.s40-nav.selected{background:#eaf1ff;color:#2564dc}.s40-nav span{font-size:20px}.s40-nav small{margin-left:auto;background:#e8edf5;padding:3px 8px;border-radius:12px}.s40-grow{flex:1}.s40-shop{font-size:11px;font-weight:750;color:#647186;border-top:1px solid #edf0f5;padding:16px 10px}.s40-shop small{display:block;font-size:10px;font-weight:400;color:#9aa6b7;margin-top:3px}.s40-language{background:#f4f6fa;border:1px solid #e8edf2;border-radius:11px;font-size:13px;font-weight:750;padding:13px;cursor:pointer}
.s40-main{flex:1;min-width:0;overflow:auto;padding:35px 40px 60px}.s40-top{display:flex;gap:15px;align-items:center;justify-content:space-between;margin-bottom:29px}.s40-overline{color:#2564dc;font-size:11px;font-weight:800;letter-spacing:.13em;margin-bottom:5px}.s40-top h1{font-size:27px;letter-spacing:-.04em;font-weight:780;margin:0}.s40-top p{font-size:13px;color:#8490a2;margin:5px 0 0}.s40-top-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.s40-btn{border:1px solid transparent;border-radius:9px;padding:10px 15px;font-size:12px;font-weight:750;cursor:pointer;white-space:nowrap}.s40-primary{background:#2467e8;color:white}.s40-primary:hover{background:#1d54bf}.s40-light{background:white;border-color:#dde4ee;color:#4b5b75}.s40-btn:disabled{opacity:.55;cursor:not-allowed}
.s40-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-bottom:25px}.s40-stat{padding:22px;background:#fff;border:1px solid #e8edf4;border-radius:15px;box-shadow:0 4px 12px #14223b04}.s40-stat span{display:block;color:#72829a;font-size:12px;font-weight:700}.s40-stat strong{display:block;font-size:30px;letter-spacing:-.035em;margin:11px 0 6px;font-weight:800;color:#1c2b43}.s40-stat small{color:#9eacbc;font-size:11px}
.s40-panel{background:white;border:1px solid #e7ecf3;border-radius:15px;overflow:hidden;box-shadow:0 4px 12px #14223b04}.s40-panel-head{padding:20px 22px;display:flex;gap:12px;align-items:center;justify-content:space-between}.s40-panel-head h2{margin:0;font-size:17px}.s40-panel-head h3{margin:0;font-size:14px}.s40-panel-head p{margin:3px 0 0;color:#8b9bad;font-size:11px}.s40-link{border:0;background:none;color:#2265da;cursor:pointer;font-size:12px;font-weight:750}.s40-table-wrap{overflow-x:auto}.s40-table{width:100%;border-collapse:collapse;text-align:left}.s40-table th{background:#f7f9fc;color:#8794a6;font-size:10px;text-transform:uppercase;letter-spacing:.065em;padding:12px 21px;white-space:nowrap}.s40-table td{padding:14px 21px;border-top:1px solid #f0f2f6;font-size:12px;vertical-align:middle}.s40-table td strong{display:block;font-weight:700}.s40-table td small{display:block;font-size:11px;color:#91a0b1;margin-top:3px;max-width:300px;white-space:normal}.s40-code{font-weight:750;word-break:break-word}.s40-pill{display:inline-block;padding:5px 10px;border-radius:20px;background:#ebf4ff;color:#2467b5;font-size:11px;font-weight:700}.s40-empty{text-align:center;color:#9a9fae;padding:38px!important}.s40-receipt{margin-left:10px}.s40-sm{padding:8px 10px}.s40-input{width:100%;min-width:0;background:white;border:1px solid #dfe5ed;border-radius:9px;padding:10px 11px;font-size:13px;color:#1c2a3e;box-sizing:border-box;outline:none}.s40-input:focus{border-color:#2468ef;box-shadow:0 0 0 2px #2468ef20}.s40-search{max-width:310px}.s40-muted{color:#8794a4;padding:14px 0}.s40-note{font-size:11px;color:#8091a6}.s40-error{border:1px solid #ffb6b7;border-radius:9px;background:#fff4f4;color:#bb3030;padding:12px;margin:13px 0;font-size:12px}
.s40-scrim{position:fixed;inset:0;z-index:1200;background:#101c3199;display:flex;align-items:center;justify-content:center;padding:20px}.s40-modal{width:min(760px,100%);max-height:94vh;overflow-y:auto;border-radius:18px;background:#fff;padding:25px;box-shadow:0 35px 90px #070e1b55}.s40-modal-head{display:flex;justify-content:space-between;gap:15px;align-items:start;border-bottom:1px solid #edf0f4;padding-bottom:16px;margin-bottom:19px}.s40-modal-head h2{font-size:20px;font-weight:800;letter-spacing:-.02em;margin:0}.s40-modal-head p{font-size:11px;color:#8793a6;margin:4px 0 0}.s40-x{font-size:24px;border:0;background:transparent;color:#7e8798;cursor:pointer}.s40-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.s40-form-grid label,.s40-labour{font-size:12px;font-weight:700;color:#526176;display:block}.s40-form-grid label .s40-input,.s40-labour .s40-input{margin-top:6px}.s40-full{grid-column:1/-1}.s40-foot{display:flex;gap:10px;justify-content:end;margin-top:22px}.s40-billing-title{padding:21px 0 8px}.s40-bill-table th,.s40-bill-table td{padding:11px}.s40-bill-table .s40-input{max-width:120px}.s40-part-search{margin-top:14px;position:relative}.s40-suggestions{position:absolute;top:calc(100% + 4px);left:0;right:0;background:white;border:1px solid #dde5ef;max-height:190px;overflow-y:auto;z-index:2;box-shadow:0 8px 22px #0002;border-radius:8px}.s40-suggestions button{display:block;width:100%;padding:10px 12px;text-align:left;border:none;background:white;font-size:12px;cursor:pointer}.s40-suggestions button:hover{background:#f2f6fb}.s40-warning{background:#fff8e7;border:1px solid #f7e5b8;border-radius:8px;padding:11px 13px;color:#997222;font-size:11px;margin-top:16px}.s40-total{display:flex;justify-content:space-between;gap:15px;border-top:1px solid #e9edf3;padding-top:16px;margin-top:16px}.s40-total strong{font-size:21px;color:#1858c4}.s40-success{display:flex;flex-direction:column;align-items:start;gap:12px;padding:20px;background:#effaf3;border:1px solid #c2ebd0;color:#236b41;border-radius:11px;font-size:13px}.s40-success strong{font-size:17px}
@media(max-width:1000px){.s40-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.s40-main{padding:26px}}
@media(max-width:700px){.s40-root{flex-direction:column}.s40-sidebar{width:auto;flex-direction:row;align-items:center;overflow-x:auto;padding:8px;gap:5px}.s40-brand{padding:0 8px 0 2px;min-width:145px}.s40-brand span,.s40-caption,.s40-grow,.s40-shop{display:none}.s40-nav{white-space:nowrap;width:auto;padding:9px 10px}.s40-language{white-space:nowrap;padding:9px}.s40-main{padding:20px 14px}.s40-top{flex-direction:column;align-items:stretch}.s40-stats{gap:9px}.s40-stat{padding:15px}.s40-stat strong{font-size:25px}.s40-modal{padding:17px}.s40-form-grid{grid-template-columns:1fr}.s40-panel-head{flex-direction:column;align-items:stretch}}
</style>
