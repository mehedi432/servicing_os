<script setup>
import InvoiceHistory658 from './InvoiceHistory658.vue'
// SERVICING_COUNTER_EXACT_654: screenshot-accurate, with real parent actions.
import { computed, nextTick, onMounted, onUnmounted, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({
  active: { type: String, default: '' },
  company: { type: String, default: 'AL MODINA COMPUTERS LIMITED' },
  user: { type: String, default: 'Administrator' },
  currency: { type: String, default: 'BDT' },
  connected: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  searchValue: { type: String, default: '' },
  billingMode: { type: String, default: 'Service Delivery' },
})
const emit = defineEmits(['select', 'settings', 'open-menu', 'navigate', 'update:searchValue', 'billing-mode'])
const brandLetters = computed(() => {
  const parts = String(props.company || 'AL MODINA').trim().split(/\s+/)
  return ((parts[0] || 'A')[0] + (parts[1] || 'M')[0]).toUpperCase()
})
const bn = computed(() => String(unref(currentLanguage) || 'en').toLowerCase().startsWith('bn'))
const invoiceMode = ref(false)
// SERVICING_OS_SERVICE_INVOICE_662: selected job shared with existing invoice modal.
const sos661Job = ref('')
const sos661Kind = ref('')
function sos661StartInvoice(jobName) {
  sos661Job.value = String(jobName || '').trim()
  sos661Kind.value = sos661Job.value ? 'service' : ''
  invoiceMode.value = true
}
function sos661ReceiveInvoiceRequest(event) {
  const job = String(event?.detail?.service_job || '').trim()
  if (!job) return
  sos661StartInvoice(job)
}
onMounted(() => window.addEventListener('servicing-os-create-service-invoice', sos661ReceiveInvoiceRequest))
onUnmounted(() => window.removeEventListener('servicing-os-create-service-invoice', sos661ReceiveInvoiceRequest))
const billingTab = ref('invoices')
function openInvoice() { sos661StartInvoice('') }
const profileOpen = ref(false)
const searching = ref(false)
const logoutBusy = ref(false)
const logoutError = ref('')
const profileWrap = ref(null)
const searchInput = ref(null)
const actions = [
  {key:'receive',en:'Service Receive',bn:'ডিভাইস গ্রহণ',help:'New service intake',helpBn:'নতুন সার্ভিস গ্রহণ',paths:['M4 4h11a2 2 0 0 1 2 2v6','M6 17H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2','M10 19H8','M14 15h7v7h-7z','M17 19h1']},
  {key:'sale',en:'New Sale',bn:'নতুন বিক্রয়',help:'Retail counter',helpBn:'খুচরা বিক্রয়',paths:['M2 3h2l2.2 10.6a2 2 0 0 0 2 1.6H19a2 2 0 0 0 1.96-1.6L22 7H5','M9 21h.01','M19 21h.01']},
  {key:'repair',en:'Repair Jobs',bn:'মেরামতের কাজ',help:'Track and process',helpBn:'কাজের অগ্রগতি',paths:['M14.7 6.3a5 5 0 0 0-6.4 6.4L3 18l3 3 5.3-5.3a5 5 0 0 0 6.4-6.4l-3.3 2-3-3z']},
  {key:'billing',en:'Billing & Delivery',bn:'বিল ও ডেলিভারি',help:'Invoice and handover',helpBn:'বিল ও পণ্য হস্তান্তর',paths:['M6 3h12a2 2 0 0 1 2 2v16l-3-2-3 2-3-2-3 2-3-2V5a2 2 0 0 1 2-2z','M9 8h6','M9 12h6','M9 16h3']},
  {key:'used',en:'Used Laptops',bn:'পুরোনো ল্যাপটপ',help:'Trade and resale',helpBn:'ক্রয় ও পুনর্বিক্রয়',paths:['M4 5h16v12H4z','M2 21h20','M8 17l-1 4','M16 17l1 4']},
  {key:'stock',en:'Stock & Items',bn:'স্টক ও পণ্য',help:'Inventory lookup',helpBn:'ইনভেন্টরি অনুসন্ধান',paths:['M12 2 3 7l9 5 9-5-9-5z','M3 7v10l9 5 9-5V7','M12 12v10']}
]
// SOS_COUNTER_HERO_676 — read-only, permission-aware operational snapshot.
const hero = ref(null)
const heroBusy = ref(false)
const heroError = ref('')
const heroUpdated = ref('')
let heroTimer = null
const heroCards = computed(() => [
  { key:'sales_total', en:'Today’s Sales', bn:'আজকের বিক্রয়', money:true, note:'Submitted invoices today', noteBn:'আজকের জমা ইনভয়েস' },
  { key:'received_today', en:'Service Received', bn:'আজ সার্ভিস গ্রহণ', note:'Devices received today', noteBn:'আজ গৃহীত ডিভাইস' },
  { key:'open_repairs', en:'Active Service Jobs', bn:'চলমান সার্ভিস কাজ', note:'Not delivered or cancelled', noteBn:'ডেলিভারি বাকি' },
  { key:'ready_delivery', en:'Ready for Delivery', bn:'ডেলিভারির জন্য প্রস্তুত', note:'Ready for collection', noteBn:'হস্তান্তরের অপেক্ষায়' }
])
function heroDisplay(card) {
  const v = hero.value?.metrics?.[card.key]
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return card.money ? '৳ ' + n.toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2}) : n.toLocaleString('en-BD')
}
async function refreshHero() {
  if (heroBusy.value || !props.connected) return
  heroBusy.value = true; heroError.value = ''
  try {
    const r = await fetch('/api/method/servicing_os.api.counter_snapshot.get_counter_snapshot', {credentials:'same-origin',cache:'no-store'})
    if (!r.ok) throw new Error('HTTP '+r.status)
    const data = await r.json()
    if (data.exc || !data.message?.metrics) throw new Error('Dashboard data unavailable')
    hero.value = data.message
    heroUpdated.value = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
  } catch (e) { heroError.value = e?.message || 'Unable to load metrics' }
  finally { heroBusy.value = false }
}
onMounted(() => { refreshHero(); heroTimer = window.setInterval(refreshHero, 120000) })
onUnmounted(() => { if (heroTimer) window.clearInterval(heroTimer) })
// Reload when connectivity is restored without modifying any transaction.
import { watch } from 'vue'
watch(() => props.connected, v => { if (v) refreshHero() })
const isEmpty = computed(() => !props.active)
const statusLabel = computed(() => props.loading ? (bn.value ? 'সংযোগ হচ্ছে' : 'Connecting') : props.error ? (bn.value ? 'সংযোগ নেই' : 'Offline') : props.connected ? (bn.value ? 'সংযুক্ত' : 'Connected') : (bn.value ? 'সংযোগ নেই' : 'Offline'))
async function openSearch() {
  searching.value = !searching.value
  if (searching.value) { await nextTick(); searchInput.value?.focus() }
}
function doSelect(id) { invoiceMode.value = false; profileOpen.value = false; searching.value = false; emit('select', id) }
function closeProfileOnOutside(event) {
  if (profileOpen.value && profileWrap.value && !profileWrap.value.contains(event.target)) profileOpen.value = false
}
function closeOnEscape(event) {
  if (event.key === 'Escape') { profileOpen.value = false; searching.value = false; invoiceMode.value = false }
}
onMounted(() => { document.addEventListener('pointerdown', closeProfileOnOutside); document.addEventListener('keydown', closeOnEscape) })
onUnmounted(() => { document.removeEventListener('pointerdown', closeProfileOnOutside); document.removeEventListener('keydown', closeOnEscape) })

async function logout() {
  if (logoutBusy.value) return
  logoutBusy.value = true
  logoutError.value = ''
  try {
    const token = window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
    const headers = token ? {'X-Frappe-CSRF-Token': token} : {}
    let response = await fetch('/api/method/logout', {method:'POST', credentials:'same-origin', headers, cache:'no-store'})
    // Existing Frappe installs may expose the logout endpoint as GET only.
    // Fetch it in-place; never navigate the browser to the JSON/API response.
    if (!response.ok && (response.status === 403 || response.status === 405)) {
      response = await fetch('/api/method/logout', {method:'GET', credentials:'same-origin', cache:'no-store'})
    }
    if (!response.ok) throw new Error('Logout failed (HTTP '+response.status+')')
    // Never navigate to the raw /api/method/logout endpoint.
    // The site's customized /login page retains the original SERVICING OS branding.
    window.location.replace('/login?redirect-to=%2Fservicing-os')
  } catch (error) {
    logoutError.value = error?.message || 'Unable to log out'
    logoutBusy.value = false
  }
}

</script>

<template>
  <div class="sos652-shell" aria-label="Computer shop counter">
    <header class="sos652-bar">
      <div class="sos652-brandgroup">
        <button class="sos652-mobile" type="button" @click="emit('open-menu')" aria-label="Open navigation">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
        </button>
        <span class="sos652-logo" aria-hidden="true"><span>{{ brandLetters }}</span></span>
        <div class="sos652-brandcopy"><strong :title="company">{{ company || 'AL MODINA COMPUTERS LIMITED' }}</strong><small>{{ bn ? 'কম্পিউটার বিক্রয় ও সার্ভিস সেন্টার' : 'Computer sales · Service center' }}</small></div>
      </div>
      <div class="sos652-topactions">
        <span class="sos652-connect" :class="{offline:!connected||!!error, pending:loading}" role="status" :title="error || statusLabel">
          <svg v-if="!error && connected && !loading" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>
          <span v-else class="sos652-status-dot"></span>{{ statusLabel }}
        </span>
        <span class="sos652-currency">{{ currency || 'BDT' }}</span>
        <div ref="profileWrap" class="sos652-profilewrap">
          <button type="button" class="sos652-avatar" :aria-expanded="profileOpen" aria-label="User profile" @click="profileOpen=!profileOpen">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="3.3"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>
          </button>
          <div v-if="profileOpen" class="sos652-profilepop">
            <strong>{{ user || 'Administrator' }}</strong>
            <small>{{ currency || 'BDT' }} · {{ bn ? 'স্টাফ কনসোল' : 'Staff console' }}</small>
            <button type="button" @click="profileOpen=false;emit('settings')">{{ bn ? 'সেটিংস' : 'Settings' }}</button>
            <button type="button" class="sos652-logout" :disabled="logoutBusy" @click="logout">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4M16 17l5-5-5-5M21 12H9"/></svg>
              {{ logoutBusy ? (bn ? 'লগ আউট হচ্ছে...' : 'Logging out...') : (bn ? 'লগ আউট' : 'Log out') }}
            </button>
            <span v-if="logoutError" class="sos652-logout-error" role="alert">{{ logoutError }}</span>
          </div>
        </div>
      </div>
    </header>

    <div class="sos652-section-title">
      <div><h1>{{ bn ? 'কাউন্টার' : 'Counter' }}</h1><p>{{ bn ? 'বিক্রয় · সার্ভিস · ডেলিভারি · বিলিং' : 'Sales · Service · Delivery · Billing' }}</p></div>
      <span class="sos652-ops">{{ bn ? 'অপারেশন' : 'Operations' }}</span>
    </div>

    <!-- SOS_COUNTER_HERO_676: read-only snapshot; no hard-coded business figures -->
    <section class="sos676-hero" aria-label="Counter performance overview">
      <div class="sos676-hero-head">
        <div class="sos676-hero-title"><span class="sos676-eyebrow">{{ bn ? 'আজকের অপারেশন' : 'TODAY AT A GLANCE' }}</span><h2>{{ bn ? 'কাউন্টার পারফরম্যান্স' : 'Your counter, at a glance' }}</h2><p>{{ bn ? 'বিক্রয়, সার্ভিস ও ডেলিভারি — লাইভ তথ্য' : 'Sales, repairs and handovers · live operational figures' }}</p></div>
        <button type="button" class="sos676-refresh" :disabled="heroBusy || !connected" @click="refreshHero" :title="bn ? 'হালনাগাদ' : 'Refresh figures'">↻ <span>{{ heroBusy ? (bn ? 'লোড হচ্ছে' : 'Loading') : (bn ? 'রিফ্রেশ' : 'Refresh') }}</span></button>
      </div>
      <div class="sos676-metrics">
        <div v-for="(c,i) in heroCards" :key="c.key" class="sos676-metric">
          <span class="sos676-metric-top"><span class="sos676-metric-label">{{ bn ? c.bn : c.en }}</span><span class="sos676-index">0{{ i+1 }}</span></span>
          <strong class="sos676-value">{{ heroBusy && !hero ? '···' : heroDisplay(c) }}</strong>
          <small>{{ bn ? c.noteBn : c.note }}</small>
        </div>
      </div>
      <div class="sos676-foot"><span>{{ heroError ? (bn ? 'তথ্য লোড করা যায়নি' : 'Metrics unavailable: '+heroError) : heroUpdated ? (bn ? 'সর্বশেষ আপডেট ' : 'Updated ') + heroUpdated : (bn ? 'তথ্য লোড হচ্ছে' : 'Waiting for live data') }}</span><span v-if="hero?.warnings?.length" :title="hero.warnings.join(' • ')">{{ bn ? 'কিছু তথ্য সীমিত' : 'Some figures restricted' }} · {{ hero.warnings.length }}</span><span v-else>{{ bn ? 'লাইভ ইআরপি তথ্য' : 'ERPNext · live data' }}</span></div>
    </section>

    <nav class="sos652-grid" :aria-label="bn ? 'কাউন্টার কাজ' : 'Counter operations'">
      <button v-for="a in actions" :key="a.key" type="button" class="sos652-tile" :class="{'sos652-selected':active===a.key}" :aria-pressed="active===a.key" @click="doSelect(a.key)">
        <span class="sos652-cardtop"><span class="sos652-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-for="(path,i) in a.paths" :key="i" :d="path"/></svg></span><svg class="sos652-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M8 16 16 8M9 8h7v7"/></svg></span>
        <span class="sos652-label">{{ bn ? a.bn : a.en }}</span>
        <span class="sos652-sub">{{ bn ? a.helpBn : a.help }}</span>
      </button>
    </nav>

    <section class="sos652-workspace" aria-label="Active workspace">
      <div class="sos652-workbar">
        <strong>{{ bn ? 'সক্রিয় ওয়ার্কস্পেস' : 'Active workspace' }}</strong>
        <div class="sos652-searchwrap">
          <input v-if="searching" ref="searchInput" :value="searchValue" type="search" :placeholder="bn ? 'রেকর্ড খুঁজুন' : 'Search records'" @input="emit('update:searchValue',$event.target.value)" @keydown.esc="searching=false" />
          <button v-else type="button" class="sos652-searchbtn" @click="openSearch"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m16.2 16.2 4 4"/></svg>{{ bn ? 'রেকর্ড খুঁজুন' : 'Search records' }}</button>
          <button v-if="searching" type="button" aria-label="Close search" class="sos652-searchclose" @click="searching=false">×</button>
        </div>
      </div>
      <div v-if="isEmpty" class="sos652-empty">
        <svg viewBox="0 0 24 24" fill="currentColor" width="23" height="23" aria-hidden="true"><path d="M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2H3V6Zm0 4h18v8a2 2 0 0 1-2 2h-6v-6h-2v6H5a2 2 0 0 1-2-2v-8Z"/></svg>
        <span>{{ bn ? 'কাজ শুরু করতে উপরের যেকোনো অপশন বেছে নিন' : 'Choose an operation to start working' }}</span>
      </div>
      <div v-else class="sos652-workbody sos653-real-workspace">
        <div class="sos652-workcontext">
          <span>{{ bn ? 'নির্বাচিত কাজ' : 'Selected task' }}: <strong>{{ bn ? actions.find(a=>a.key===active)?.bn : actions.find(a=>a.key===active)?.en }}</strong></span>
          <button v-if="active==='repair' || active==='billing'" type="button" class="sos652-new-job" @click="doSelect('receive')">+ {{ bn ? 'নতুন সার্ভিস জব' : 'New Service Job' }}</button>
        </div>
        <template v-if="active === 'receive'"><slot name="workspace" /></template>
        <template v-else-if="active === 'sale'"><slot name="sale" /></template>
        <template v-else-if="active === 'repair'"><slot name="repair" /></template>
        <template v-else-if="active === 'used'"><slot name="used" /></template>
        <template v-else-if="active === 'stock'"><slot name="stock" /></template>
        <template v-else-if="active === 'billing'">
          <div class="sos653-billing-tabs" role="tablist" aria-label="Billing and delivery">
            <button type="button" role="tab" :aria-selected="billingTab === 'invoices'" :class="{'active':billingTab === 'invoices'}" @click="billingTab='invoices'">{{ bn ? 'ইনভয়েস' : 'Invoices' }}</button>
            <button type="button" role="tab" :aria-selected="billingTab === 'handover'" :class="{'active':billingTab === 'handover'}" @click="billingTab='handover'">{{ bn ? 'ডেলিভারি / হস্তান্তর' : 'Delivery & Handover' }}</button>
          </div>
          <slot v-if="billingTab === 'invoices'" name="billing" :open-invoice="openInvoice" />
          <slot v-else name="delivery" />
        </template>
        <!-- SERVICING_OS_COUNTER_658: real invoice history beneath live workspaces -->
        <InvoiceHistory658 v-if="active === 'sale' || active === 'used'" :scope="active" />
      </div>
      <div class="sos653-invoice-action">
        <button type="button" class="sos653-floating-invoice" @click="sos661StartInvoice('')" :title="bn ? 'নতুন বিক্রয় বা সার্ভিস ইনভয়েস তৈরি' : 'Create Retail, Used Laptop or Service Invoice'">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M5 3h14v18l-3-2-4 2-4-2-3 2V3Z"/><path d="M9 9h6M9 13h6"/></svg>
          {{ bn ? 'ইনভয়েস তৈরি করুন' : 'Create Invoice' }}
        </button>
      </div>
    </section>
    <Teleport to="body">
      <div v-if="invoiceMode" class="sos653-modal-backdrop" role="presentation" @click.self="invoiceMode=false">
        <section class="sos653-modal" role="dialog" aria-modal="true" aria-label="Create invoice">
          <div class="sos653-modal-titlebar">
            <div><strong>{{ bn ? 'নতুন ইনভয়েস' : 'Create Invoice' }}</strong><p>{{ bn ? 'সার্ভিস জবের জন্য খসড়া ইনভয়েস' : 'Retail · Used Laptop · Service · Discounts' }}</p></div>
            <button type="button" aria-label="Close invoice modal" @click="invoiceMode=false">×</button>
          </div>
          <div class="sos653-modal-content"><slot name="invoice" :initial-kind="sos661Kind || (active==='used'?'used':active==='sale'?'retail':'service')" :initial-job="sos661Job" /></div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style>
/* SERVICING_COUNTER_652: warm ivory / tan / walnut palette sampled from supplied screenshot.
   No forest green: #F9F6F2 backdrop, #FFFCF7 cards, #F4E3D3 tile,
   #E7D6C5 borders, #3C2C25 ink, #8B725E secondary typography. */
.sos652-shell,.sos652-shell *{box-sizing:border-box}
.sos652-shell{--sos652-page:#f9f6f2;--sos652-paper:#fffcf7;--sos652-tile:#f4e3d3;--sos652-ink:#3c2c25;--sos652-walnut:#775741;--sos652-muted:#8b725e;--sos652-line:#e7d6c5;--sos652-hover:#f7ece1;
  width:100%;min-width:0;padding:14px;border-radius:18px;background:var(--sos652-page)!important;color:var(--sos652-ink)!important;font-family:inherit;line-height:1.35;isolation:isolate}
.sos652-shell button{font-family:inherit;cursor:pointer}
.sos652-bar{display:flex;align-items:center;justify-content:space-between;gap:13px;min-height:57px;padding:0 0 15px;border-bottom:1px solid var(--sos652-line);background:transparent!important}
.sos652-brandgroup{display:flex;align-items:center;gap:10px;min-width:0;flex:1}
.sos652-logo{height:37px;width:37px;flex:0 0 37px;display:grid;place-items:center;background:#8d6245!important;color:#fffaf4!important;border-radius:11px;box-shadow:inset 0 1px 0 #ffffff38}
.sos652-logo span{font-size:14px;line-height:1;letter-spacing:-.05em;font-weight:800}
.sos652-brandcopy{display:flex;flex-direction:column;gap:3px;min-width:0;max-width:100%}
.sos652-brandcopy strong{font-size:14px;line-height:1.22;font-weight:800;letter-spacing:.015em;color:var(--sos652-ink)!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.sos652-brandcopy small{font-size:10px;line-height:1.18;color:var(--sos652-muted)!important;white-space:nowrap}
.sos652-topactions{display:flex;align-items:center;gap:10px;flex:0 0 auto}
.sos652-connect{display:flex;align-items:center;gap:5px;min-height:32px;padding:0 10px;border-radius:50px;background:#eee2d6!important;color:#765441!important;white-space:nowrap;font-size:10px;font-weight:600}
.sos652-connect.offline{background:#f6e5dd!important;color:#9f4d39!important}.sos652-connect.pending{background:#f2ead9!important;color:#806332!important}
.sos652-status-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:currentColor}
.sos652-currency{color:var(--sos652-walnut)!important;font-size:11px;white-space:nowrap;font-weight:650}
.sos652-profilewrap{position:relative}.sos652-avatar{display:grid!important;place-items:center!important;height:34px;width:34px;border:0!important;border-radius:50%!important;background:#f1e7db!important;color:#71523f!important;padding:0!important;box-shadow:none!important}
.sos652-avatar:hover{background:#ead8c7!important}.sos652-profilepop{position:absolute;right:0;top:42px;z-index:2000;display:grid;gap:7px;width:214px;padding:13px;background:var(--sos652-paper)!important;border:1px solid var(--sos652-line)!important;border-radius:12px!important;box-shadow:0 16px 36px #5a3c2b28!important}
.sos652-profilepop strong{font-size:12px;color:var(--sos652-ink)!important;overflow-wrap:anywhere}.sos652-profilepop small{color:var(--sos652-muted)!important;font-size:10px}
.sos652-profilepop button{display:flex!important;align-items:center!important;gap:7px!important;text-align:left!important;font-size:11px!important;padding:9px 10px!important;border-radius:8px!important;border:1px solid var(--sos652-line)!important;background:#f8f0e7!important;color:var(--sos652-ink)!important}
.sos652-profilepop button:hover{background:#f3e2d1!important}.sos652-profilepop button.sos652-logout{background:#fff4ed!important;color:#86402c!important;border-color:#ead1c5!important}.sos652-profilepop button:disabled{opacity:.6;cursor:wait}.sos652-logout-error{font-size:10px;color:#a34130;overflow-wrap:anywhere}
.sos652-section-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:21px 0 10px}
.sos652-section-title h1{font-size:16px;line-height:1.25;font-weight:750;letter-spacing:-.01em;color:var(--sos652-ink)!important;margin:0 0 5px}
.sos652-section-title p{font-size:10px;color:var(--sos652-muted)!important;margin:0;line-height:1.3}
.sos652-ops{background:#f0e7dc!important;color:#8b725e!important;border:0!important;border-radius:7px;padding:4px 9px;font-size:10px;line-height:1.2;white-space:nowrap}
.sos652-grid{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:9px!important;margin:0 0 12px!important}
.sos652-shell .sos652-grid>.sos652-tile{display:flex!important;flex-direction:column!important;align-items:flex-start!important;justify-content:flex-start!important;text-align:left!important;min-width:0;min-height:103px;height:auto!important;padding:12px 13px!important;border:1px solid var(--sos652-line)!important;border-radius:12px!important;background:var(--sos652-paper)!important;color:var(--sos652-ink)!important;box-shadow:0 1px 1px #49312306!important;appearance:none!important;-webkit-appearance:none!important;transition:background .15s,border-color .15s,box-shadow .15s}
.sos652-shell .sos652-grid>.sos652-tile:hover{background:#fffaf2!important;border-color:#d6b99e!important;box-shadow:0 3px 12px #49312310!important}
.sos652-shell .sos652-grid>.sos652-tile.sos652-selected{background:#fff8ef!important;border-color:#cda884!important;box-shadow:inset 0 0 0 1px #dec3a9!important}
.sos652-cardtop{display:flex;justify-content:space-between;align-items:flex-start;width:100%;margin-bottom:10px}
.sos652-icon{display:grid!important;place-items:center!important;width:35px!important;height:35px!important;border-radius:10px!important;background:var(--sos652-tile)!important;color:#866045!important}
.sos652-icon svg{width:19px;height:19px;stroke:#866045!important}.sos652-arrow{height:12px;width:12px;margin:8px 2px 0 0;stroke:#aa9480!important;color:#aa9480!important}
.sos652-label{color:var(--sos652-ink)!important;font-size:14px!important;line-height:1.13!important;font-weight:760!important;margin:0 0 4px;overflow-wrap:anywhere}
.sos652-sub{color:var(--sos652-muted)!important;font-size:10px!important;line-height:1.18!important;font-weight:400!important;overflow-wrap:anywhere}
.sos652-workspace{min-height:168px;min-width:0;margin:0;padding:12px;border:1px solid var(--sos652-line)!important;border-radius:12px!important;background:var(--sos652-paper)!important;box-shadow:none!important}
.sos652-workbar{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:42px;padding:0 0 19px;border-bottom:1px solid #ebddd0}
.sos652-workbar strong{font-size:14px;line-height:1.2;font-weight:720;color:var(--sos652-ink)!important}
.sos652-searchwrap{display:flex;align-items:center;gap:4px;min-width:0}.sos652-searchbtn{display:flex!important;align-items:center!important;gap:5px!important;border:0!important;background:transparent!important;color:#8f7a69!important;padding:4px 3px;font-size:10px;white-space:nowrap}
.sos652-searchbtn svg{height:13px;width:13px}.sos652-searchwrap input{min-width:0;width:190px;max-width:190px;border:1px solid var(--sos652-line)!important;border-radius:8px!important;padding:6px 9px!important;font-size:11px;color:var(--sos652-ink);background:#fff}
.sos652-searchclose{border:0;background:transparent;color:var(--sos652-muted);font-size:18px}.sos652-empty{min-height:99px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:10px;color:#a39182;text-align:center;font-size:12px}.sos652-empty svg{color:#b6a18e}
.sos652-workbody{padding-top:12px;min-width:0;max-width:100%;background:var(--sos652-paper)!important}.sos652-workbody :is(input,textarea,select){max-width:100%}.sos652-workbody .sos627-old-operations,.sos652-workbody .counter-647-actions{display:none!important}
.sos652-workcontext{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:0 1px 11px;font-size:11px;color:var(--sos652-muted)}.sos652-workcontext strong{color:var(--sos652-ink)!important}
.sos652-new-job{border:1px solid #dbbfa7!important;background:#f8eadd!important;color:#6c4935!important;border-radius:8px!important;padding:8px 11px!important;font-size:11px!important;font-weight:700!important}
.sos652-billing-tabs{display:flex;gap:6px;margin:0 0 12px;flex-wrap:wrap}.sos652-billing-tabs button{padding:8px 12px;font-size:11px;border-radius:8px;border:1px solid var(--sos652-line)!important;background:#fff;color:var(--sos652-ink)!important}.sos652-billing-tabs button.on{border-color:#cba786!important;background:#f7e9db!important;color:#67462d!important;font-weight:700!important}
.sos652-mobile{display:none;width:31px;height:33px;flex-shrink:0;background:#f1e4d6;color:#78583f;border:0;border-radius:8px;padding:7px}.sos652-mobile svg{width:18px;height:18px}
.sos652-shell :is(.sos652-avatar,.sos652-searchbtn,.sos652-tile,.sos652-new-job):focus-visible{outline:2px solid #a7794d!important;outline-offset:2px}
@media(max-width:860px){.sos652-shell{padding:12px}.sos652-grid{gap:8px!important}.sos652-brandcopy strong{font-size:12.5px}}
@media(max-width:680px){.sos652-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.sos652-mobile{display:grid;place-items:center}.sos652-section-title{margin-top:15px}}
@media(max-width:470px){.sos652-shell{padding:10px}.sos652-topactions{gap:6px}.sos652-connect{font-size:0;padding:0 9px}.sos652-connect svg,.sos652-status-dot{width:11px;height:11px}.sos652-brandcopy strong{font-size:11px;max-width:170px}.sos652-brandcopy small{font-size:9px}.sos652-tile{padding:10px!important}.sos652-label{font-size:12px!important}.sos652-sub{font-size:9px!important}.sos652-workbar strong{font-size:12px}.sos652-searchwrap input{width:128px}}

/* STEP 6.52: layout is full width, no unused 12-column space. */
.sos652-shell{width:100%!important;max-width:none!important;overflow:visible!important}
.sos652-workspace{position:relative;min-width:0;padding:14px!important}
.sos652-workbody{min-width:0;width:100%;padding-bottom:6px}
.sos652-workbody .sos649-original-workspace{width:100%;min-width:0;max-width:none!important}
.sos652-workbody .sos649-original-workspace > .grid,
.sos652-workbody .sos649-original-workspace > div.grid{
  display:grid!important;grid-template-columns:minmax(0,3fr) minmax(245px,1fr)!important;
  gap:14px!important;align-items:start;width:100%!important;max-width:none!important;min-width:0
}
.sos652-workbody .sos649-original-workspace > .grid > section,
.sos652-workbody .sos649-original-workspace > div.grid > section{
  min-width:0!important;width:100%!important;max-width:none!important;
  border:1px solid #e7d6c5!important;border-radius:12px!important;
  background:#fffcf7!important;color:#3c2c25!important;padding:15px!important;
  box-shadow:none!important
}
.sos652-workbody .sos649-original-workspace > .grid > section:nth-of-type(1),
.sos652-workbody .sos649-original-workspace > div.grid > section:nth-of-type(1){grid-column:1!important;grid-row:1!important}
.sos652-workbody .sos649-original-workspace > .grid > section:nth-of-type(2),
.sos652-workbody .sos649-original-workspace > div.grid > section:nth-of-type(2){grid-column:2!important;grid-row:1!important}
.sos652-workbody .sos649-original-workspace > .grid > section:nth-of-type(3),
.sos652-workbody .sos649-original-workspace > div.grid > section:nth-of-type(3){grid-column:1/-1!important;grid-row:2!important}
.sos652-workbody .sos649-original-workspace > .grid > section:nth-of-type(n+4),
.sos652-workbody .sos649-original-workspace > div.grid > section:nth-of-type(n+4){grid-column:1/-1!important}
/* Intake form and embedded operational cards: warm ivory / walnut, without recoloring alerts. */
.sos652-workbody .sos649-original-workspace :is(h1,h2,h3,.text-slate-900,.text-slate-800){color:#3c2c25!important}
.sos652-workbody .sos649-original-workspace :is(.text-blue-700,.text-blue-600){color:#835a3f!important}
.sos652-workbody .sos649-original-workspace :is(.bg-blue-50,.bg-slate-50){background:#f9f1e8!important}
.sos652-workbody .sos649-original-workspace .border-blue-200{border-color:#e7d6c5!important}
.sos652-workbody .sos649-original-workspace :is(input,select,textarea){background:#fffdfa!important;border-color:#ddc7b4!important;border-radius:8px!important;color:#3c2c25!important;min-width:0}
.sos652-workbody .sos649-original-workspace :is(input,select,textarea):focus{outline:2px solid #c99e78!important;outline-offset:1px}
.sos652-workbody .sos649-original-workspace :is(button.bg-blue-600,button.bg-blue-700,button.bg-slate-900){background:#856044!important;border-color:#856044!important;color:#fffaf2!important}
.sos652-workbody .sos649-original-workspace :is(.border-slate-200,.border-slate-300){border-color:#e7d6c5!important}
.sos652-workbody .sos649-original-workspace .text-slate-500{color:#8b725e!important}
.sos652-invoicebar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0 0 14px;padding:6px 0 12px;border-bottom:1px solid #e7d6c5}
.sos652-invoicebar strong{font-size:14px!important;color:#3c2c25!important}
.sos652-invoicebar p{font-size:11px;color:#8b725e;margin:3px 0 0}
.sos652-invoicebar button{background:#f4e3d3!important;border:1px solid #e7d6c5!important;border-radius:8px!important;color:#6b4a35!important;padding:8px 10px!important;font-size:11px}
.sos652-invoice-action{display:flex;justify-content:flex-end;min-height:58px;align-items:flex-end;pointer-events:none}
.sos652-shell .sos652-floating-invoice{pointer-events:auto!important;position:fixed;right:24px;bottom:20px;z-index:100;display:inline-flex!important;gap:8px!important;align-items:center!important;justify-content:center!important;min-height:44px;padding:10px 16px!important;border:1px solid #714c33!important;border-radius:100px!important;background:#81583f!important;color:#fffaf4!important;font-size:13px!important;font-weight:750!important;box-shadow:0 7px 21px #52351d26!important}
.sos652-shell .sos652-floating-invoice:hover{background:#6a4934!important}
.sos652-shell .sos652-floating-invoice:focus-visible{outline:2px solid #ae8057!important;outline-offset:3px}
.sos652-full-counter{padding:0!important;margin:0!important;max-width:none!important;width:100%!important}
.sos652-full-counter > section.sos649-counter-root{width:100%!important;max-width:none!important;margin:0!important}
@media(max-width:1100px){
.sos652-workbody .sos649-original-workspace > .grid,
.sos652-workbody .sos649-original-workspace > div.grid{grid-template-columns:minmax(0,2fr) minmax(235px,1fr)!important}
}
@media(max-width:900px){
.sos652-workbody .sos649-original-workspace > .grid,
.sos652-workbody .sos649-original-workspace > div.grid{grid-template-columns:minmax(0,1fr)!important}
.sos652-workbody .sos649-original-workspace > .grid > section,
.sos652-workbody .sos649-original-workspace > div.grid > section{grid-column:1/-1!important;grid-row:auto!important}
}
@media(max-width:600px){.sos652-workspace{padding:10px!important}.sos652-shell .sos652-floating-invoice{right:12px;bottom:12px;width:auto;min-width:170px}}


/* 6.53 actual modules, full-width and no placeholder blocks */
.sos653-real-workspace {width:100%!important;min-width:0!important;max-width:none!important}
.sos653-embedded-module,.sos653-embedded-module > * {min-width:0;max-width:none;width:100%}
.sos653-embedded-module {padding:1px 0 4px;color:#3c2c25}
.sos653-embedded-module :is(input,select,textarea) {max-width:100%;min-width:0;border-color:#decab8;background:#fffcf8;color:#3c2c25}
.sos653-embedded-module :is(.bg-white,.bg-slate-50){background:#fffcf7!important}
.sos653-embedded-module :is(.text-blue-700,.text-blue-600){color:#825b41!important}
.sos653-embedded-module :is(button.bg-blue-600,button.bg-blue-700,button.bg-slate-900) {background:#805a3e!important;border-color:#805a3e!important;color:#fffaf4!important}
.sos653-billing-tabs{display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #e7d6c5;margin:0 0 16px;padding:0 0 12px}
.sos653-billing-tabs button{background:#fffaf3!important;border:1px solid #e7d6c5!important;padding:9px 13px!important;color:#765942!important;border-radius:9px!important;font-size:12px!important;font-weight:650!important}
.sos653-billing-tabs button.active{background:#805a3e!important;border-color:#805a3e!important;color:#fff!important}
.sos653-invoice-action{height:1px;overflow:visible}
.sos653-floating-invoice{position:fixed!important;right:25px;bottom:22px;z-index:200;display:inline-flex!important;align-items:center!important;gap:9px!important;background:#805a3e!important;color:#fff!important;border:1px solid #684329!important;border-radius:100px!important;box-shadow:0 12px 30px #5d392c35!important;min-height:47px!important;padding:11px 18px!important;font-size:13px!important;font-weight:750!important}
.sos653-floating-invoice:hover{background:#69482e!important}
.sos653-modal-backdrop{position:fixed;inset:0;z-index:11000;display:grid;place-items:center;background:rgba(31,22,17,.54);padding:18px;overflow-y:auto}
.sos653-modal{width:min(960px,100%);max-height:min(92vh,900px);display:flex;flex-direction:column;background:#f9f6f2;border:1px solid #e7d6c5;border-radius:17px;box-shadow:0 30px 75px #140d0b55;overflow:hidden;color:#3c2c25}
.sos653-modal-titlebar{padding:17px 21px;border-bottom:1px solid #e7d6c5;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-shrink:0}
.sos653-modal-titlebar strong{font-size:17px;color:#3c2c25;font-weight:800}
.sos653-modal-titlebar p{font-size:11px;color:#8b725e;margin-top:4px}
.sos653-modal-titlebar button{border:1px solid #e7d6c5!important;border-radius:10px;background:#f4e3d3!important;color:#684832!important;width:36px;height:36px;font-size:25px;display:grid;place-items:center}
.sos653-modal-content{padding:17px;overflow-y:auto;min-height:0;flex:1}
.sos653-modal-content .sos653-invoice{border:0;border-radius:0;padding:0;background:transparent}
@media(max-width:650px){.sos653-modal-backdrop{padding:7px;align-items:end}.sos653-modal{max-height:97vh;border-radius:15px 15px 0 0}.sos653-modal-content{padding:11px}.sos653-floating-invoice{right:12px;bottom:12px}}


/* SOS_COUNTER_HERO_676 */
.sos676-hero{background:linear-gradient(125deg,#efe0d0 0%,#f8f0e7 55%,#fffaf4 100%)!important;border:1px solid #e2cdb9!important;border-radius:18px!important;padding:19px!important;margin:0 0 16px!important;box-shadow:0 7px 24px #5e3f2810!important;color:#3c2c25!important}
.sos676-hero-head{display:flex;justify-content:space-between;align-items:flex-start;gap:15px;margin-bottom:17px}
.sos676-eyebrow{font-size:10px;letter-spacing:1.6px;color:#8d6648;font-weight:800}
.sos676-hero-title h2{font-size:23px;line-height:1.16;letter-spacing:-.035em;font-weight:800;color:#3c2c25;margin:6px 0 5px}
.sos676-hero-title p{font-size:11px;color:#8b725e;margin:0}
.sos652-shell .sos676-refresh{display:inline-flex!important;align-items:center!important;gap:7px!important;border:1px solid #dac4af!important;background:#fffaf5!important;color:#6d4c37!important;border-radius:10px!important;padding:8px 11px!important;font-size:11px!important;font-weight:700!important;white-space:nowrap!important}
.sos676-refresh:disabled{opacity:.55;cursor:wait!important}
.sos676-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.sos676-metric{min-width:0;display:flex;flex-direction:column;gap:9px;background:#fffcf8;border:1px solid #e8d9c9;border-radius:13px;padding:15px 14px;box-shadow:0 2px 5px #4a2b1708}
.sos676-metric-top{display:flex;align-items:flex-start;justify-content:space-between;gap:5px}
.sos676-metric-label{font-size:11px;font-weight:700;color:#705440}
.sos676-index{font-size:10px;font-weight:800;color:#b9a18d}
.sos676-value{font-size:clamp(19px,2vw,28px);font-variant-numeric:tabular-nums;line-height:1.1;letter-spacing:-.04em;color:#39271d;overflow-wrap:anywhere}
.sos676-metric small{font-size:10px;color:#9c8570;line-height:1.3}
.sos676-foot{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:10px;color:#8e7159;margin-top:12px}
@media(max-width:900px){.sos676-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:470px){.sos676-hero{padding:13px!important}.sos676-hero-title h2{font-size:19px}.sos676-metric{padding:12px 10px}.sos676-value{font-size:20px}.sos676-hero-head{gap:7px}}
</style>

<!-- SERVICING_OS_COUNTER_658 -->
