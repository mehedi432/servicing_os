<script setup>
// SERVICING_COUNTER_EXACT_652: screenshot-accurate, with real parent actions.
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
const profileOpen = ref(false)
const searching = ref(false)
const logoutBusy = ref(false)
const logoutError = ref('')
const profileWrap = ref(null)
const searchInput = ref(null)
const actions = [
  {key:'receive',en:'Receive Device',bn:'ডিভাইস গ্রহণ',help:'New service intake',helpBn:'নতুন সার্ভিস গ্রহণ',paths:['M4 4h11a2 2 0 0 1 2 2v6','M6 17H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2','M10 19H8','M14 15h7v7h-7z','M17 19h1']},
  {key:'sale',en:'New Sale',bn:'নতুন বিক্রয়',help:'Retail counter',helpBn:'খুচরা বিক্রয়',paths:['M2 3h2l2.2 10.6a2 2 0 0 0 2 1.6H19a2 2 0 0 0 1.96-1.6L22 7H5','M9 21h.01','M19 21h.01']},
  {key:'repair',en:'Repair Jobs',bn:'মেরামতের কাজ',help:'Track and process',helpBn:'কাজের অগ্রগতি',paths:['M14.7 6.3a5 5 0 0 0-6.4 6.4L3 18l3 3 5.3-5.3a5 5 0 0 0 6.4-6.4l-3.3 2-3-3z']},
  {key:'billing',en:'Billing & Delivery',bn:'বিল ও ডেলিভারি',help:'Invoice and handover',helpBn:'বিল ও পণ্য হস্তান্তর',paths:['M6 3h12a2 2 0 0 1 2 2v16l-3-2-3 2-3-2-3 2-3-2V5a2 2 0 0 1 2-2z','M9 8h6','M9 12h6','M9 16h3']},
  {key:'used',en:'Used Laptops',bn:'পুরোনো ল্যাপটপ',help:'Trade and resale',helpBn:'ক্রয় ও পুনর্বিক্রয়',paths:['M4 5h16v12H4z','M2 21h20','M8 17l-1 4','M16 17l1 4']},
  {key:'stock',en:'Stock & Items',bn:'স্টক ও পণ্য',help:'Inventory lookup',helpBn:'ইনভেন্টরি অনুসন্ধান',paths:['M12 2 3 7l9 5 9-5-9-5z','M3 7v10l9 5 9-5V7','M12 12v10']}
]
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
  if (event.key === 'Escape') { profileOpen.value = false; searching.value = false }
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
const moduleDestinations = {sale:'New Sales', repair:'Service Jobs', used:'Used Laptops', stock:'Inventory'}
function openOriginalModule() {
  const target = moduleDestinations[props.active]
  if (target) emit('navigate', target)
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
      <div v-if="isEmpty" class="sos652-empty"><svg viewBox="0 0 24 24" fill="currentColor" width="23" height="23" aria-hidden="true"><path d="M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2H3V6Zm0 4h18v8a2 2 0 0 1-2 2h-6v-6h-2v6H5a2 2 0 0 1-2-2v-8Z"/></svg><span>{{ bn ? 'এখানে বিক্রয়, সার্ভিস, কাজ ও বিলিং খুলবে' : 'Sales, device intake, jobs and billing open here' }}</span></div>
      <div v-else class="sos652-workbody">
        <div v-if="invoiceMode" class="sos652-invoice-area">
          <div class="sos652-invoicebar">
            <div><strong>{{ bn ? 'নতুন সার্ভিস ইনভয়েস' : 'Create Service Invoice' }}</strong><p>{{ bn ? 'সেভ করা সার্ভিস জব থেকে খসড়া চালান তৈরি' : 'Create an ERPNext invoice draft for a saved Service Job' }}</p></div>
            <button type="button" @click="invoiceMode=false">{{ bn ? 'কাজে ফিরে যান' : 'Back to workspace' }}</button>
          </div>
          <slot name="invoice"></slot>
        </div>
        <template v-else>
        <div class="sos652-workcontext">
          <span>{{ bn ? 'নির্বাচিত কাজ' : 'Selected task' }}: <strong>{{ bn ? actions.find(a=>a.key===active)?.bn : actions.find(a=>a.key===active)?.en }}</strong></span>
          <button v-if="active==='repair'" type="button" class="sos652-new-job" @click="doSelect('receive')">+ {{ bn ? 'নতুন সার্ভিস জব' : 'New Service Job' }}</button>
        </div>
        <div v-if="active === 'billing'" class="sos652-billing-tabs" aria-label="Billing and delivery options">
          <button type="button" :class="{'on':billingMode==='Service Delivery'}" @click="emit('billing-mode','Service Delivery')">{{ bn ? 'ডেলিভারি' : 'Delivery' }}</button>
          <button type="button" :class="{'on':billingMode==='Repair Billing'}" @click="emit('billing-mode','Repair Billing')">{{ bn ? 'মেরামতের বিল' : 'Repair Billing' }}</button>
        </div>
        <slot v-if="active === 'receive' || active === 'billing'" name="workspace" />
        <slot v-else-if="active === 'repair'" name="repair">
          <div class="sos652-fallback"><p>{{ bn ? 'সার্ভিস জব তালিকা খোলার জন্য বাটন চাপুন' : 'Open the existing Service Jobs workspace' }}</p><button type="button" @click="openOriginalModule">{{ bn ? 'সার্ভিস জব খুলুন' : 'Open Service Jobs' }}</button></div>
        </slot>
        <slot v-else-if="active === 'sale'" name="sale">
          <div class="sos652-fallback"><p>{{ bn ? 'বর্তমান বিক্রয় মডিউল খুলুন' : 'Open the existing retail sales module' }}</p><button type="button" @click="openOriginalModule">{{ bn ? 'বিক্রয় খুলুন' : 'Open Sales' }}</button></div>
        </slot>
        <slot v-else-if="active === 'used'" name="used">
          <div class="sos652-fallback"><p>{{ bn ? 'পুরোনো ল্যাপটপ মডিউল খুলুন' : 'Open the existing used laptop module' }}</p><button type="button" @click="openOriginalModule">{{ bn ? 'ল্যাপটপ খুলুন' : 'Open Used Laptops' }}</button></div>
        </slot>
        <slot v-else-if="active === 'stock'" name="stock">
          <div class="sos652-fallback"><p>{{ bn ? 'পণ্যের তালিকা ও মজুদ খুলুন' : 'Open the existing inventory tools' }}</p><button type="button" @click="openOriginalModule">{{ bn ? 'স্টক খুলুন' : 'Open Inventory' }}</button></div>
        </slot>
        </template>
      </div>
      <div v-if="!isEmpty" class="sos652-invoice-action">
        <button type="button" class="sos652-floating-invoice" @click="invoiceMode=!invoiceMode" :aria-pressed="invoiceMode" :title="bn ? 'ইনভয়েস তৈরি করুন' : 'Create a service invoice draft'">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 3h14v18l-3-2-4 2-4-2-3 2V3Z"/><path d="M9 9h6M9 13h6"/></svg>
          {{ invoiceMode ? (bn ? 'কাজে ফিরুন' : 'Back to task') : (bn ? 'ইনভয়েস তৈরি' : 'Create Invoice') }}
        </button>
      </div>
    </section>
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
.sos652-fallback{padding:28px 8px;text-align:center;color:var(--sos652-muted);font-size:12px}.sos652-fallback button{margin-top:9px;padding:9px 13px!important;border-radius:9px!important;border:1px solid #d8bba4!important;background:#f4e3d3!important;color:var(--sos652-ink)!important;font-size:12px;font-weight:700}
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

</style>
