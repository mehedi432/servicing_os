<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import { moduleApi } from './extensionApi.js'

const props = defineProps({ doctype: { type: String, required: true }, selected: String })
const emit = defineEmits(['create', 'open'])
const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const customer = computed(() => props.doctype === 'Customer')
const title = computed(() => customer.value ? tr('Customers', 'গ্রাহক') : tr('Suppliers', 'সরবরাহকারী'))
const createLabel = computed(() => customer.value ? tr('New Customer', 'নতুন গ্রাহক') : tr('New Supplier', 'নতুন সরবরাহকারী'))
const query = ref('')
const view = ref('grid')
const result = ref(null)
const loading = ref(true)
const error = ref('')
const page = computed(() => result.value?.page || 1)
const action = computed(() => customer.value ? tr('Customer 360', 'গ্রাহক ৩৬০') : tr('Supplier 360', 'সরবরাহকারী ৩৬০'))
let timer
let request = 0

async function load(nextPage = 1) {
  clearTimeout(timer)
  const version = ++request
  loading.value = true
  error.value = ''
  try {
    const data = await moduleApi('get_party_directory', {
      doctype: props.doctype, search: query.value.trim(), page: nextPage,
    })
    if (version === request) result.value = data
  } catch (err) {
    if (version === request) error.value = err.message
  } finally {
    if (version === request) loading.value = false
  }
}

watch(query, () => {
  request++
  clearTimeout(timer)
  error.value = ''
  loading.value = true
  timer = setTimeout(() => load(), 250)
})
onMounted(() => load())
onBeforeUnmount(() => {
  clearTimeout(timer)
  request++
})
defineExpose({ refresh: () => load(page.value) })

function initials(name) {
  return String(name).trim().split(/\s+/).slice(0, 2).map(word => Array.from(word)[0]).join('').toLocaleUpperCase() || '—'
}
</script>

<template>
  <section class="party-directory" :class="{ 'customer-directory': customer }" :aria-label="title">
    <header class="party-header">
      <div>
        <h1>{{ title }}</h1>
      </div>
      <button v-if="result?.can_create" type="button" class="party-button party-primary" @click="emit('create')">
        + {{ createLabel }}
      </button>
    </header>
    <div class="party-toolbar">
      <label class="party-search">
        {{ tr('Search', 'খুঁজুন') }}
        <input v-model="query" type="search" maxlength="100" :placeholder="tr('Name, group, phone, or email', 'নাম, গ্রুপ, ফোন বা ইমেইল')" />
      </label>
      <div class="party-modes" role="group" :aria-label="tr('Directory view', 'তালিকা দেখুন')">
        <button type="button" class="party-button" :aria-pressed="view === 'grid'" @click="view = 'grid'">{{ tr('Grid', 'গ্রিড') }}</button>
        <button type="button" class="party-button" :aria-pressed="view === 'list'" @click="view = 'list'">{{ tr('List', 'তালিকা') }}</button>
      </div>
      <button type="button" class="party-button" :disabled="loading" @click="load(page)">{{ tr('Refresh', 'রিফ্রেশ') }}</button>
    </div>
    <slot name="notices" />
    <div :aria-busy="loading">
      <p v-if="loading" class="party-state" role="status">{{ tr('Loading records…', 'রেকর্ড লোড হচ্ছে…') }}</p>
      <p v-else-if="error" class="party-state party-error" role="alert">{{ error }}</p>
      <p v-else-if="!result?.rows.length" class="party-state" role="status">
        {{ query ? tr('No records match your search.', 'কোনো মিল পাওয়া যায়নি।') : tr('No records to display yet.', 'এখনও কোনো রেকর্ড নেই।') }}
      </p>
      <ul v-else class="party-results" :class="'party-' + view" :aria-label="title" role="list">
        <li v-for="row in result.rows" :key="row.name">
          <button type="button" class="party-record" :aria-pressed="selected === row.name"
            :aria-label="action + ' ' + (row.display_name || row.name)" :title="row.display_name || row.name"
            @click="emit('open', row, result.can_edit)">
            <span class="party-avatar" aria-hidden="true">{{ initials(row.display_name || row.name) }}</span>
            <span class="party-record-text">
              <strong>{{ row.display_name || row.name }}</strong>
              <small v-if="row.mobile || row.email || row.group">{{ row.mobile || row.email || row.group }}</small>
              <small v-if="customer && row.group && (row.mobile || row.email)" class="customer-group">{{ row.group }}</small>
              <small v-else-if="view === 'list' && row.group && (row.mobile || row.email)">{{ row.group }}</small>
              <small v-if="row.open_purchase_orders != null" class="party-po-count">
                {{ row.open_purchase_orders }} {{ tr(row.open_purchase_orders === 1 ? 'open PO' : 'open POs', 'চলমান ক্রয়াদেশ') }}
              </small>
            </span>
            <span class="party-record-mark" aria-hidden="true">›</span>
          </button>
        </li>
      </ul>
      <footer v-if="result && !error && (result.page > 1 || result.has_next)" class="party-pager">
        <button type="button" class="party-button" :disabled="loading || page <= 1" @click="load(page - 1)">{{ tr('Previous', 'আগের') }}</button>
        <span>{{ tr('Page', 'পৃষ্ঠা') }} {{ page }}</span>
        <button type="button" class="party-button" :disabled="loading || !result.has_next" @click="load(page + 1)">{{ tr('Next', 'পরের') }}</button>
      </footer>
    </div>
  </section>
</template>

<style scoped>
.party-directory{--party-rule:var(--os-border,#e5d5c4);min-width:0;color:var(--os-ink,#39291f);background:var(--os-surface,#fffdf9);border:1px solid var(--party-rule);border-radius:14px;overflow:hidden}
.party-header{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:15px 13px;background:var(--os-tint,#f3ebe0);border-bottom:1px solid var(--party-rule)}
.party-header h1{margin:0;font:1.35rem/1.15 Georgia,serif}
.party-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:12px 13px;border-bottom:1px solid var(--party-rule)}
.party-search{flex:0 0 100%;display:grid;gap:4px;min-width:0;font-size:.75rem;font-weight:700}
.party-search input,.party-button{min-height:38px;color:inherit;background:var(--os-surface,#fffdf9);border:1px solid var(--party-rule);border-radius:7px;padding:6px 8px;font-size:.75rem}
.party-search input{box-sizing:border-box;min-width:0;width:100%}
.party-button{white-space:nowrap;font-weight:650}
.party-button:not(:disabled):hover{border-color:var(--os-accent,#855d43)}
.party-button.party-primary,.party-button[aria-pressed="true"]{background:var(--os-accent,#6b4935);color:var(--os-on-accent,#fffaf3);border-color:transparent}
.party-button:focus-visible,.party-search input:focus-visible,.party-record:focus-visible{outline:2px solid var(--os-accent,#855d43);outline-offset:1px}
.party-modes{display:flex;gap:3px;margin-inline-end:auto}
.party-state{margin:0;padding:16px 12px;font-size:.82rem}
.party-error{color:#98382e}
.party-results{display:grid;gap:8px;margin:0;padding:10px;list-style:none}
.party-grid{grid-template-columns:repeat(auto-fill,minmax(min(100%,120px),1fr));grid-auto-rows:1fr}
.party-list{grid-template-columns:minmax(0,1fr)}
.party-results li{min-width:0}
.party-record{display:flex;align-items:center;gap:8px;width:100%;height:100%;min-height:50px;min-width:0;padding:7px 8px;color:inherit;text-align:left;border:1px solid var(--party-rule);border-radius:9px;background:var(--os-surface,#fffefa);cursor:pointer;position:relative}
.party-record:hover,.party-record[aria-pressed="true"]{background:var(--os-selection,#f1e5d9);border-color:var(--os-accent,#855d43)}
.party-grid .party-record{flex-direction:column;align-items:start;min-height:77px}
.party-record-mark{margin-inline-start:auto;color:var(--os-muted,#6d5b4c);font-size:1.1rem;line-height:1}
.party-grid .party-record-mark{position:absolute;inset-block-start:9px;inset-inline-end:10px}
.party-avatar{display:grid;flex:none;place-items:center;width:30px;height:30px;border-radius:8px;background:var(--os-selection,#ecdccd);font-weight:750;font-size:.7rem}
.party-record-text{display:grid;gap:3px;min-width:0;width:100%;line-height:1.2}
.party-record-text strong,.party-record-text small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.party-record-text strong{font-size:.8rem;font-weight:750}
.party-record-text small{font-size:.7rem;color:var(--os-muted,#694f3b)}
.party-record-text .party-po-count{width:fit-content;max-width:100%;background:var(--os-tint,#f3ebe0);color:var(--os-strong,#644229);padding:2px 5px;border-radius:4px;font-weight:700}
.customer-directory .party-grid{grid-template-columns:repeat(auto-fill,minmax(min(100%,142px),1fr))}
.customer-directory .party-record{border-radius:11px;padding:10px 11px;gap:9px}
.customer-directory .party-grid .party-record{min-height:104px}
.customer-directory .party-avatar{width:35px;height:35px;border-radius:10px;color:var(--os-strong,#644229);font-size:.79rem}
.customer-directory .party-record[aria-pressed="true"] .party-avatar{color:#fff;background:var(--os-accent,#785238)}
.customer-directory .party-record-text strong{font-size:.88rem;line-height:1.35}
.customer-directory .party-grid .party-record-text strong{white-space:normal;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.customer-directory .party-record-text small{font-size:.74rem}
.customer-directory .customer-group{width:fit-content;max-width:100%;margin-top:2px;padding:2px 6px;border-radius:5px;background:var(--os-tint,#f3ebe0);color:var(--os-strong,#644229)}
.party-pager{display:flex;justify-content:space-between;align-items:center;gap:5px;padding:9px;border-top:1px solid var(--party-rule);font-size:.73rem}
</style>
