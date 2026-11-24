<script setup>
import { onMounted, ref, watch } from 'vue'
import PartyDialog from './PartyDialog.vue'
import { servicingApi } from './extensionApi.js'
import { currentLanguage } from '../i18n/servicingLanguage.js'

const props = defineProps({ receipt: { type: String, default: '' } })
const emit = defineEmits(['serial'])
const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const api = (method, args, post = false) => servicingApi('supplier_warranty', method, args, post)
const filters = [
  ['all', 'All receipts', 'সব রসিদ'], ['expiring', 'Due in 30 days', '৩০ দিনের মধ্যে শেষ'],
  ['expired', 'Expired', 'মেয়াদ শেষ'], ['missing', 'Expiry missing', 'মেয়াদ নেই'],
  ['active', 'Current or upcoming', 'বর্তমান বা আসন্ন'], ['none', 'No warranty', 'ওয়ারেন্টি নেই'],
]
const labels = {
  missing: ['Expiry missing', 'মেয়াদ নেই'], expiring: ['Expiring', 'মেয়াদ শেষ হচ্ছে'],
  active: ['Active', 'সক্রিয়'], upcoming: ['Starts later', 'পরে শুরু'],
  expired: ['Expired', 'মেয়াদ শেষ'], none: ['No warranty', 'ওয়ারেন্টি নেই'],
}
const query = ref('')
const state = ref('all')
const applied = ref({ search: '', state: 'all' })
const register = ref(null)
const page = ref(1)
const selected = ref('')
const record = ref(null)
const loading = ref(false)
const loadingDetail = ref(false)
const listError = ref('')
const detailError = ref('')
const edit = ref(null)
const saving = ref(false)
const editError = ref('')
const notice = ref('')
let listVersion = 0
let detailVersion = 0

async function openReceipt(receipt) {
  const version = ++detailVersion
  selected.value = receipt
  record.value = null
  detailError.value = ''
  loadingDetail.value = true
  try {
    const data = await api('get_receipt', { receipt, ...applied.value })
    if (version === detailVersion) record.value = data
  } catch (error) {
    if (version === detailVersion) detailError.value = error.message
  } finally {
    if (version === detailVersion) loadingDetail.value = false
  }
}

async function load(nextPage = 1, pinnedReceipt = '') {
  const version = ++listVersion
  loading.value = true
  listError.value = ''
  try {
    const data = await api('list_receipts', { ...applied.value, page: nextPage })
    if (version !== listVersion) return
    register.value = data
    page.value = nextPage
    const next = pinnedReceipt || data.receipts.find(row => row.name === selected.value)?.name || data.receipts[0]?.name
    if (next) void openReceipt(next)
    else {
      detailVersion++
      loadingDetail.value = false
      selected.value = ''
      record.value = null
    }
  } catch (error) {
    if (version === listVersion) listError.value = error.message
  } finally {
    if (version === listVersion) loading.value = false
  }
}

function applyFilters() {
  notice.value = ''
  applied.value = { search: query.value.trim(), state: state.value }
  load()
}
function clearFilters() {
  query.value = ''
  state.value = 'all'
  applyFilters()
}
function pin(receipt) {
  query.value = receipt
  state.value = 'all'
  applied.value = { search: receipt, state: 'all' }
  load(1, receipt)
}
function editLine(line) {
  notice.value = ''
  editError.value = ''
  edit.value = {
    receipt: record.value.name, modified: record.value.modified, line: line.name, item: line.item_name || line.item_code,
    kind: line.kind, starts: line.starts, expires: line.expires, terms: line.terms, reference: line.reference,
  }
}
async function save() {
  if (saving.value) return
  saving.value = true
  editError.value = ''
  const { item, ...data } = edit.value
  if (!data.kind || data.kind === 'No Warranty') {
    data.starts = ''
    data.expires = ''
  }
  try {
    await api('save_coverage', data, true)
    edit.value = null
    notice.value = tr('Supplier coverage saved.', 'সরবরাহকারীর ওয়ারেন্টি সংরক্ষিত।')
    await load(page.value, data.receipt)
  } catch (error) {
    editError.value = error.message
  } finally {
    saving.value = false
  }
}
onMounted(() => props.receipt ? pin(props.receipt) : load())
watch(() => props.receipt, value => {
  if (value) pin(value)
  else {
    query.value = ''
    state.value = 'all'
    applyFilters()
  }
})
</script>

<template>
  <section class="inv-desk stock-warranty" :aria-label="tr('Stock and supplier warranty', 'স্টক ও সরবরাহকারীর ওয়ারেন্টি')">
    <header class="desk-head">
      <div>
        <h3>{{ tr('Stock & supplier coverage', 'স্টক ও সরবরাহকারীর ওয়ারেন্টি') }}</h3>
        <p>{{ tr('Record the supplier’s terms on each purchase receipt line. Quantities shown are units received.', 'ক্রয় রসিদের প্রতিটি পণ্যে সরবরাহকারীর শর্ত রাখুন। এখানে প্রাপ্ত পরিমাণ দেখানো হচ্ছে।') }}</p>
      </div>
    </header>
    <form class="workspace-filters" @submit.prevent="applyFilters">
      <label class="desk-search">{{ tr('Receipt, supplier, product or reference', 'রসিদ, সরবরাহকারী, পণ্য বা রেফারেন্স') }}<input v-model="query" type="search" maxlength="140" /></label>
      <label>{{ tr('Coverage', 'ওয়ারেন্টি') }}
        <select v-model="state">
          <option v-for="[value, en, bn] in filters" :key="value" :value="value">{{ tr(en, bn) }}</option>
        </select>
      </label>
      <div class="filter-actions">
        <button type="submit" class="desk-primary" :disabled="loading">{{ tr('Apply', 'প্রয়োগ') }}</button>
        <button type="button" @click="clearFilters">{{ tr('Clear', 'মুছুন') }}</button>
      </div>
    </form>
    <p v-if="notice" class="desk-success" role="status">{{ notice }}</p>
    <p v-if="listError" class="desk-alert" role="alert">{{ listError }}</p>
    <div v-else class="stock-warranty-layout">
      <aside class="warranty-panel">
        <h4>{{ tr('Purchase receipts', 'ক্রয় রসিদ') }}</h4>
        <p v-if="loading" role="status">{{ tr('Loading receipts…', 'রসিদ লোড হচ্ছে…') }}</p>
        <p v-else-if="!register?.receipts.length">{{ tr('No matching purchase receipts.', 'কোনো ক্রয় রসিদ পাওয়া যায়নি।') }}</p>
        <button v-for="row in register?.receipts || []" :key="row.name" type="button" class="warranty-receipt-button"
          :aria-pressed="selected === row.name" :disabled="loading" @click="openReceipt(row.name)">
          <strong>{{ row.supplier_name || row.supplier }}</strong>
          <small>{{ row.name }} · {{ row.posting_date }}</small>
        </button>
        <footer v-if="page > 1 || register?.has_next" class="desk-pager">
          <button type="button" :disabled="loading || page === 1" @click="load(page - 1)">{{ tr('Previous', 'আগের') }}</button>
          <span>{{ page }}</span>
          <button type="button" :disabled="loading || !register?.has_next" @click="load(page + 1)">{{ tr('Next', 'পরের') }}</button>
        </footer>
      </aside>
      <div class="warranty-panel" :aria-busy="loadingDetail">
        <p v-if="detailError" class="desk-alert" role="alert">{{ detailError }}</p>
        <p v-else-if="loadingDetail" role="status">{{ tr('Loading warranty records…', 'ওয়ারেন্টির তথ্য লোড হচ্ছে…') }}</p>
        <template v-else-if="record">
          <header class="stock-receipt-head">
            <div>
              <h3>{{ record.supplier_name || record.supplier }}</h3>
              <p>{{ record.name }} · {{ record.posting_date }}</p>
            </div>
            <a :href="'/app/purchase-receipt/' + encodeURIComponent(record.name)" target="_blank" rel="noopener">{{ tr('Open purchase receipt', 'ক্রয় রসিদ খুলুন') }} ↗</a>
          </header>
          <p v-if="!record.lines.length">{{ tr('No item lines match this filter.', 'এই ফিল্টারে কোনো পণ্য নেই।') }}</p>
          <article v-for="line in record.lines" :key="line.name" class="stock-warranty-card">
            <div class="stock-receipt-head">
              <div><h3>{{ line.item_name || line.item_code }}</h3><p>{{ line.item_code }} · {{ line.quantity }} {{ line.uom }} · {{ line.warehouse || '—' }}</p></div>
              <span class="warranty-tag" :data-state="line.status">{{ tr(...labels[line.status]) }}</span>
            </div>
            <dl class="warranty-facts">
              <div><dt>{{ tr('Provider', 'প্রদানকারী') }}</dt><dd>{{ line.kind || '—' }}</dd></div>
              <div><dt>{{ tr('Starts', 'শুরু') }}</dt><dd>{{ line.starts || '—' }}</dd></div>
              <div><dt>{{ tr('Expires', 'শেষ') }}</dt><dd>{{ line.expires || '—' }}</dd></div>
              <div v-if="line.sku_on_hand != null">
                <dt>{{ tr('SKU on hand in warehouse', 'গুদামে পণ্যের বর্তমান মজুত') }}</dt><dd>{{ line.sku_on_hand }}</dd>
              </div>
              <div v-if="line.days_remaining !== null"><dt>{{ tr('Time remaining', 'বাকি সময়') }}</dt>
                <dd>{{ line.days_remaining === 0 ? tr('Ends today', 'আজ শেষ') : (line.days_remaining > 0 ? line.days_remaining + tr(' days left', ' দিন বাকি') : -line.days_remaining + tr(' days past expiry', ' দিন আগে শেষ')) }}</dd>
              </div>
              <div v-if="line.reference"><dt>{{ tr('Supplier reference', 'সরবরাহকারী রেফারেন্স') }}</dt><dd>{{ line.reference }}</dd></div>
              <div v-if="line.batch_no"><dt>{{ tr('Batch', 'ব্যাচ') }}</dt><dd>{{ line.batch_no }}</dd></div>
            </dl>
            <p v-if="line.terms" class="warranty-text">{{ line.terms }}</p>
            <details v-if="line.serials.length" class="warranty-serials">
              <summary>{{ line.serials.length }} {{ tr('serial numbers', 'সিরিয়াল নম্বর') }}</summary>
              <div><button v-for="serial in line.serials" :key="serial" type="button" @click="emit('serial', serial)">{{ serial }}</button></div>
            </details>
            <button v-if="record.can_edit" type="button" @click="editLine(line)">
              {{ line.kind ? tr('Edit coverage', 'ওয়ারেন্টি সম্পাদনা') : tr('Record coverage', 'ওয়ারেন্টি লিখুন') }}
            </button>
          </article>
        </template>
      </div>
    </div>

    <PartyDialog v-if="edit" :title="tr('Supplier warranty', 'সরবরাহকারীর ওয়ারেন্টি')" :busy="saving" @close="edit = null">
      <div class="inv-desk warranty-editor">
        <p>{{ edit.item }} · {{ edit.receipt }}</p>
        <p v-if="editError" class="desk-alert" role="alert">{{ editError }}</p>
        <form @submit.prevent="save">
          <label>{{ tr('Coverage type', 'ওয়ারেন্টির ধরন') }}
            <select v-model="edit.kind">
              <option value="">{{ tr('Unrecorded', 'রেকর্ড নেই') }}</option>
              <option value="Supplier Warranty">{{ tr('Supplier warranty', 'সরবরাহকারীর ওয়ারেন্টি') }}</option>
              <option value="Manufacturer Warranty">{{ tr('Manufacturer warranty', 'প্রস্তুতকারকের ওয়ারেন্টি') }}</option>
              <option value="No Warranty">{{ tr('No warranty', 'ওয়ারেন্টি নেই') }}</option>
            </select>
          </label>
          <div v-if="edit.kind && edit.kind !== 'No Warranty'" class="warranty-date-fields">
            <label>{{ tr('Start date', 'শুরুর তারিখ') }}<input v-model="edit.starts" type="date" /></label>
            <label>{{ tr('Expiry date', 'শেষ তারিখ') }}<input v-model="edit.expires" type="date" :min="edit.starts" required /></label>
          </div>
          <label>{{ tr('Warranty card or supplier reference', 'ওয়ারেন্টি কার্ড বা সরবরাহকারীর রেফারেন্স') }}<input v-model.trim="edit.reference" maxlength="140" /></label>
          <label>{{ tr('Terms and exclusions', 'শর্তাবলি') }}<textarea v-model.trim="edit.terms" rows="3" maxlength="2000"></textarea></label>
          <button class="desk-primary" type="submit" :disabled="saving">{{ saving ? tr('Saving…', 'সংরক্ষণ হচ্ছে…') : tr('Save coverage', 'ওয়ারেন্টি সংরক্ষণ') }}</button>
        </form>
      </div>
    </PartyDialog>
  </section>
</template>

<style scoped src="./inventoryDesk.css"></style>
<style scoped src="./warrantyDesk.css"></style>
<style scoped src="./workspaceFilters.css"></style>
<style scoped>
.stock-warranty{border:0;padding:0;background:none}
.stock-warranty-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:12px}
.warranty-panel{background:var(--os-surface,#fffefa);color:var(--os-ink,#38291f);border:1px solid var(--os-border,#e5d5c4);border-radius:12px;padding:12px;min-width:0}
.warranty-panel h4{margin:0 0 7px;font-size:.83rem;font-weight:750}
.warranty-receipt-button{width:100%;text-align:left;margin-top:5px;white-space:normal!important;overflow-wrap:anywhere}
.warranty-receipt-button small{display:block;margin-top:2px}
.warranty-receipt-button[aria-pressed=true]{background:var(--os-selection,#f3e6d8);border-color:var(--os-accent,#976d4b)}
.stock-receipt-head{display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px}
.stock-receipt-head a{font-size:.8rem}
.stock-warranty-card{border-top:1px solid var(--os-border,#e5d5c4);padding:12px 0;margin-top:10px}
.stock-warranty-card:last-child{padding-bottom:0}
.stock-warranty-card>button,.stock-warranty-card>details{margin-top:8px}
.warranty-serials summary{cursor:pointer;font-size:.82rem;font-weight:700}
.warranty-serials div{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}
.warranty-date-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
@media(max-width:850px){.stock-warranty-layout{grid-template-columns:minmax(0,1fr)}}
</style>
