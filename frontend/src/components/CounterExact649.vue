<script setup>
// SERVICING_COUNTER_EXACT_649: screenshot-accurate, with real parent actions.
import { computed, nextTick, ref, unref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({
  active: { type: String, default: '' },
  user: { type: String, default: 'Administrator' },
  currency: { type: String, default: 'BDT' },
  connected: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  searchValue: { type: String, default: '' },
  billingMode: { type: String, default: 'Service Delivery' },
})
const emit = defineEmits(['select', 'settings', 'open-menu', 'update:searchValue', 'billing-mode'])
const bn = computed(() => String(unref(currentLanguage) || 'en').toLowerCase().startsWith('bn'))
const profileOpen = ref(false)
const searching = ref(false)
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
function doSelect(id) { profileOpen.value = false; searching.value = false; emit('select', id) }
</script>

<template>
  <div class="sos649-shell" aria-label="SERVICING OS counter">
    <header class="sos649-bar">
      <div class="sos649-brandgroup">
        <button class="sos649-mobile" type="button" @click="emit('open-menu')" aria-label="Open navigation">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
        </button>
        <span class="sos649-logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="15" height="12" rx="2"/><path d="M8 20h8M12 16v4"/><path d="m15 9 2-2 2 2"/></svg>
        </span>
        <div class="sos649-brandcopy"><strong>SERVICING OS</strong><small>{{ bn ? 'কাউন্টার ওয়ার্কস্পেস' : 'Counter workspace' }}</small></div>
      </div>
      <div class="sos649-topactions">
        <span class="sos649-connect" :class="{offline:!connected||!!error, pending:loading}" role="status" :title="error || statusLabel">
          <svg v-if="!error && connected && !loading" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>
          <span v-else class="sos649-status-dot"></span>{{ statusLabel }}
        </span>
        <span class="sos649-currency">{{ currency || 'BDT' }}</span>
        <div class="sos649-profilewrap">
          <button type="button" class="sos649-avatar" :aria-expanded="profileOpen" aria-label="User profile" @click="profileOpen=!profileOpen">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="3.3"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>
          </button>
          <div v-if="profileOpen" class="sos649-profilepop">
            <strong>{{ user || 'Administrator' }}</strong>
            <small>{{ currency || 'BDT' }} · SERVICING OS</small>
            <button type="button" @click="profileOpen=false;emit('settings')">{{ bn ? 'সেটিংস' : 'Settings' }}</button>
          </div>
        </div>
      </div>
    </header>

    <div class="sos649-section-title">
      <div><h1>{{ bn ? 'কাউন্টার' : 'Counter' }}</h1><p>{{ bn ? 'বিক্রয় · সার্ভিস · ডেলিভারি · বিলিং' : 'Sales · Service · Delivery · Billing' }}</p></div>
      <span class="sos649-ops">{{ bn ? 'অপারেশন' : 'Operations' }}</span>
    </div>

    <nav class="sos649-grid" :aria-label="bn ? 'কাউন্টার কাজ' : 'Counter operations'">
      <button v-for="a in actions" :key="a.key" type="button" class="sos649-tile" :class="{'sos649-selected':active===a.key}" :aria-pressed="active===a.key" @click="doSelect(a.key)">
        <span class="sos649-cardtop"><span class="sos649-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-for="(path,i) in a.paths" :key="i" :d="path"/></svg></span><svg class="sos649-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M8 16 16 8M9 8h7v7"/></svg></span>
        <span class="sos649-label">{{ bn ? a.bn : a.en }}</span>
        <span class="sos649-sub">{{ bn ? a.helpBn : a.help }}</span>
      </button>
    </nav>

    <section class="sos649-workspace" aria-label="Active workspace">
      <div class="sos649-workbar">
        <strong>{{ bn ? 'সক্রিয় ওয়ার্কস্পেস' : 'Active workspace' }}</strong>
        <div class="sos649-searchwrap">
          <input v-if="searching" ref="searchInput" :value="searchValue" type="search" :placeholder="bn ? 'রেকর্ড খুঁজুন' : 'Search records'" @input="emit('update:searchValue',$event.target.value)" @keydown.esc="searching=false" />
          <button v-else type="button" class="sos649-searchbtn" @click="openSearch"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m16.2 16.2 4 4"/></svg>{{ bn ? 'রেকর্ড খুঁজুন' : 'Search records' }}</button>
          <button v-if="searching" type="button" aria-label="Close search" class="sos649-searchclose" @click="searching=false">×</button>
        </div>
      </div>
      <div v-if="isEmpty" class="sos649-empty"><svg viewBox="0 0 24 24" fill="currentColor" width="23" height="23" aria-hidden="true"><path d="M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2H3V6Zm0 4h18v8a2 2 0 0 1-2 2h-6v-6h-2v6H5a2 2 0 0 1-2-2v-8Z"/></svg><span>{{ bn ? 'এখানে বিক্রয়, সার্ভিস, কাজ ও বিলিং খুলবে' : 'Sales, device intake, jobs and billing open here' }}</span></div>
      <div v-else class="sos649-workbody">
        <div v-if="active === 'billing'" class="sos649-billing-tabs" aria-label="Billing and delivery options">
          <button type="button" :class="{'on':billingMode==='Service Delivery'}" @click="emit('billing-mode','Service Delivery')">{{ bn ? 'ডেলিভারি' : 'Delivery' }}</button>
          <button type="button" :class="{'on':billingMode==='Repair Billing'}" @click="emit('billing-mode','Repair Billing')">{{ bn ? 'মেরামতের বিল' : 'Repair Billing' }}</button>
        </div>
        <slot name="workspace" />
      </div>
    </section>
  </div>
</template>

<style>
/* SERVICING_COUNTER_EXACT_649: screenshot matched 782px reference. */
.sos649-shell,.sos649-shell *{box-sizing:border-box}
.sos649-shell{width:100%;min-width:0;background:#f7f5f1;border-radius:18px;padding:13px 13px 13px;color:#2d4339;font-family:inherit;line-height:1.35}
.sos649-bar{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;height:56px;padding:1px 0 17px;border-bottom:1px solid #dfdad0}
.sos649-brandgroup{display:flex;align-items:center;gap:9px;min-width:0}
.sos649-logo{height:34px;width:34px;flex:0 0 34px;border-radius:10px;background:#283f35;color:#fff;display:grid;place-items:center}
.sos649-brandcopy{display:flex;flex-direction:column;gap:2px;min-width:0}.sos649-brandcopy strong{font-size:15px;line-height:1.15;font-weight:700;letter-spacing:.005em;white-space:nowrap}.sos649-brandcopy small{font-size:9px;color:#8b958e;line-height:1.3;white-space:nowrap}
.sos649-topactions{display:flex;align-items:center;gap:10px;flex:0 0 auto}.sos649-connect{display:flex;align-items:center;gap:5px;min-height:32px;border-radius:50px;background:#e4ece6;color:#286649;font-size:10px;padding:0 9px;white-space:nowrap}.sos649-connect.offline{color:#9b543c;background:#f5e5df}.sos649-connect.pending{color:#856e2f;background:#f1eddc}.sos649-status-dot{width:7px;height:7px;background:currentColor;border-radius:50%;display:inline-block}
.sos649-currency{font-size:11px;color:#536057;font-weight:450;white-space:nowrap}.sos649-profilewrap{position:relative}.sos649-avatar{display:grid;place-items:center;height:32px;width:32px;flex:none;background:#eae6df;border:0;border-radius:50%;color:#3b4f43;cursor:pointer}.sos649-avatar:hover{background:#e0e9df}.sos649-profilepop{z-index:60;position:absolute;top:40px;right:0;width:198px;background:#fff;border:1px solid #e0dacf;border-radius:12px;padding:12px;box-shadow:0 10px 32px #25362a20;display:grid;gap:6px}.sos649-profilepop strong{font-size:12px;overflow-wrap:anywhere}.sos649-profilepop small{font-size:10px;color:#879187}.sos649-profilepop button{background:#f2f5ef;border:1px solid #dfe6dd;color:#2c503d;padding:7px;border-radius:7px;text-align:left;font-size:11px;cursor:pointer}
.sos649-section-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:22px 0 10px}.sos649-section-title h1{font-size:16px;font-weight:700;line-height:1.25;margin:0 0 5px;letter-spacing:-.01em}.sos649-section-title p{font-size:10px;line-height:1.3;margin:0;color:#8b918a}.sos649-ops{background:#eeeae4;color:#687369;border-radius:7px;padding:4px 9px;font-size:10px;line-height:1.2;white-space:nowrap}
.sos649-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 12px}.sos649-tile{display:flex;flex-direction:column;align-items:flex-start;appearance:none;-webkit-appearance:none;text-align:left;min-width:0;height:102px;border:1px solid #e3ded6;border-radius:12px;padding:12px;background:#fffefd;color:#2a4337;cursor:pointer;box-shadow:0 1px 1px #272e2604;transition:border-color .14s ease,background .14s ease,box-shadow .14s ease}.sos649-tile:hover{border-color:#a5baaa;background:#fff;box-shadow:0 2px 9px #2945320c}.sos649-tile:focus-visible,.sos649-searchbtn:focus-visible,.sos649-avatar:focus-visible{outline:2px solid #406c55;outline-offset:2px}.sos649-tile.sos649-selected{border-color:#9fb8a6;background:#f9fcf8}.sos649-cardtop{display:flex;justify-content:space-between;align-items:flex-start;width:100%;margin-bottom:10px}.sos649-icon{width:33px;height:33px;border-radius:9px;background:#e9f0eb;color:#355e49;display:grid;place-items:center}.sos649-icon svg{width:18px;height:18px}.sos649-arrow{height:12px;width:12px;margin:8px 2px 0 0;color:#a7afa7}.sos649-label{font-size:14px;line-height:1.1;font-weight:700;color:#2d4339;margin:1px 0 4px;overflow-wrap:anywhere}.sos649-sub{font-size:10px;line-height:1.15;color:#929890;margin:0;overflow-wrap:anywhere}
.sos649-workspace{background:#fffefd;border:1px solid #e4ded4;border-radius:12px;min-height:168px;padding:12px;margin:0;min-width:0}.sos649-workbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 0 19px;border-bottom:1px solid #e9e4dc;min-height:42px}.sos649-workbar strong{font-size:14px;font-weight:700;line-height:1.2}.sos649-searchwrap{display:flex;gap:4px;align-items:center;min-width:0}.sos649-searchbtn{display:flex;align-items:center;gap:5px;background:transparent;border:0;cursor:pointer;font-size:10px;color:#718075;padding:4px 3px;white-space:nowrap}.sos649-searchbtn svg{height:13px;width:13px}.sos649-searchwrap input{min-width:0;max-width:190px;width:190px;border:1px solid #d8e0d8;border-radius:8px;padding:6px 9px;font-size:11px;background:#fff;color:#273f33}.sos649-searchclose{border:0;background:transparent;color:#6b7e70;font-size:18px;cursor:pointer}
.sos649-empty{min-height:99px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:#85948b;text-align:center;font-size:12px}.sos649-empty svg{color:#a1b0a5;opacity:.95}.sos649-workbody{padding-top:12px;min-width:0}.sos649-workbody .sos627-old-operations,.sos649-workbody .counter-647-actions{display:none!important}.sos649-workbody :is(input,textarea,select){max-width:100%}
.sos649-billing-tabs{display:flex;gap:6px;margin:0 0 12px;flex-wrap:wrap}.sos649-billing-tabs button{padding:7px 12px;font-size:11px;border-radius:8px;border:1px solid #dddcd4;background:#fff;color:#4c6154;cursor:pointer}.sos649-billing-tabs button.on{border-color:#89aa92;background:#eaf1e9;color:#275b3f;font-weight:700}
.sos649-mobile{display:none;width:30px;height:32px;flex-shrink:0;background:#edece7;color:#365746;border:0;border-radius:8px;padding:7px;cursor:pointer}.sos649-mobile svg{height:18px;width:18px}
@media(max-width:800px){.sos649-shell{padding:11px}.sos649-grid{gap:7px}}
@media(max-width:680px){.sos649-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sos649-tile{height:100px}.sos649-mobile{display:grid;place-items:center}.sos649-section-title{margin-top:16px}}
@media(max-width:420px){.sos649-connect{font-size:0;padding:0 10px}.sos649-connect svg,.sos649-status-dot{width:11px;height:11px}.sos649-brandcopy strong{font-size:12px}.sos649-cardtop{margin-bottom:7px}.sos649-tile{height:97px;padding:10px}.sos649-label{font-size:12px}.sos649-sub{font-size:9px}.sos649-workbar strong{font-size:12px}.sos649-searchwrap input{width:125px}}
</style>
