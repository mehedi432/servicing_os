<script setup>
import { computed, ref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import PartyDialog from './PartyDialog.vue'
import SupplierWarrantyRegister from './SupplierWarrantyRegister.vue'
import { servicingApi } from './extensionApi.js'

const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const statuses = ['Open', 'Work In Progress', 'Closed', 'Cancelled']
const textStatus = value => ({
  Open: tr('Open', 'খোলা'),
  'Work In Progress': tr('Work In Progress', 'কাজ চলছে'),
  Closed: tr('Closed', 'বন্ধ'),
  Cancelled: tr('Cancelled', 'বাতিল'),
  Active: tr('Active', 'সক্রিয়'),
  Expired: tr('Expired', 'মেয়াদ শেষ'),
  'No warranty': tr('No warranty', 'ওয়ারেন্টি নেই'),
  'Starts later': tr('Starts later', 'পরে শুরু হবে'),
  'Expiry not recorded': tr('Expiry not recorded', 'মেয়াদের তারিখ রেকর্ড করা হয়নি'),
})[value] || value
const tab = ref('stock')
const stockReceipt = ref('')
const salesSearch = ref('')
const salesType = ref('Sales Invoice')
const salesPage = ref(1)
const sales = ref(null)
const salesError = ref('')
const salesLoading = ref(false)
const showSales = ref(false)
const kind = ref('invoice')
const reference = ref('')
const coverage = ref(null)
const coverageError = ref('')
const checking = ref(false)
const claims = ref(null)
const claimPage = ref(1)
const status = ref('')
const claimSearch = ref('')
const claimFilters = ref({ search: '', status: '' })
const claimError = ref('')
const loadingClaims = ref(false)
const form = ref(null)
const formError = ref('')
const saving = ref(false)
const notice = ref('')
const detailError = ref('')
const claimDetail = ref(null)
const claimDraft = ref(null)
const summary = computed(() => {
  const lines = coverage.value?.invoices.flatMap(invoice => invoice.items) || []
  return {
    total: lines.length, active: lines.filter(line => line.status === 'Active').length,
    expired: lines.filter(line => line.status === 'Expired').length,
    missing: lines.filter(line => line.status === 'Expiry not recorded').length,
  }
})
const api = (name, args, post) => servicingApi('inventory_warranty', name, args, post)
const recordUrl = (route, name) => '/app/' + route + '/' + encodeURIComponent(name)
let lookupVersion = 0
let claimVersion = 0
let salesVersion = 0
let detailVersion = 0

function showStock(receipt = '') {
  stockReceipt.value = receipt
  tab.value = 'stock'
}

async function browseSales(page = 1) {
  const version = ++salesVersion
  showSales.value = true
  salesError.value = ''
  salesLoading.value = true
  try {
    const result = await api('find_customer_sales', {
      invoice_type: salesType.value, search: salesSearch.value.trim(), page,
    })
    if (version !== salesVersion) return
    sales.value = result
    salesType.value = result.invoice_type
    salesPage.value = page
  } catch (error) {
    if (version === salesVersion) salesError.value = error.message
  } finally {
    if (version === salesVersion) salesLoading.value = false
  }
}

function findSale(value, mode) {
  tab.value = 'coverage'
  reference.value = value
  kind.value = mode
  showSales.value = false
  lookup()
}

function timeRemaining(days) {
  if (days === 0) return tr('Ends today', 'আজ শেষ')
  if (days > 0) return days + tr(' days left', ' দিন বাকি')
  return -days + tr(' days past expiry', ' দিন আগে শেষ')
}

async function openDetails(name) {
  const version = ++detailVersion
  detailError.value = ''
  try {
    const result = await api('get_claim', { name })
    if (version !== detailVersion) return
    claimDetail.value = result
    claimDraft.value = {
      name: result.name, modified: result.modified, status: result.status,
      resolution: result.resolution || '', supplier_rma: result.supplier_rma || '',
    }
  } catch (error) {
    if (version === detailVersion) claimError.value = error.message
  }
}
async function saveDetails() {
  if (saving.value) return
  saving.value = true
  detailError.value = ''
  try {
    const result = await api('save_claim', claimDraft.value, true)
    claimDetail.value = null
    claimDraft.value = null
    notice.value = tr('Claim updated', 'দাবি হালনাগাদ হয়েছে') + ' · ' + result.name
    loadClaims(claimPage.value)
  } catch (error) {
    detailError.value = error.message
  } finally {
    saving.value = false
  }
}

function clearCoverage() {
  lookupVersion++
  coverage.value = null
  coverageError.value = ''
  checking.value = false
}
async function lookup() {
  clearCoverage()
  const version = lookupVersion
  checking.value = true
  try {
    const result = await api('get_coverage', { reference: reference.value.trim(), kind: kind.value })
    if (version === lookupVersion) coverage.value = result
  } catch (error) {
    if (version === lookupVersion) coverageError.value = error.message
  } finally {
    if (version === lookupVersion) checking.value = false
  }
}
async function loadClaims(page = 1) {
  const version = ++claimVersion
  claimError.value = ''
  loadingClaims.value = true
  try {
    const result = await api('list_claims', { ...claimFilters.value, page })
    if (version !== claimVersion) return
    claims.value = result
    claimPage.value = page
  } catch (error) {
    if (version === claimVersion) claimError.value = error.message
  } finally {
    if (version === claimVersion) loadingClaims.value = false
  }
}
function searchClaims() {
  claimFilters.value = { search: claimSearch.value.trim(), status: status.value }
  loadClaims()
}
function clearClaimFilters() {
  claimSearch.value = ''
  status.value = ''
  searchClaims()
}
function clearSalesFilters() {
  salesSearch.value = ''
  salesType.value = sales.value?.available[0] || 'Sales Invoice'
  browseSales()
}
function clearLookup() {
  reference.value = ''
  clearCoverage()
}
function showClaims() {
  tab.value = 'claims'
  loadClaims(claimPage.value)
}
function openClaim(invoice, line) {
  formError.value = ''
  form.value = {
    invoice: invoice.name, doctype: invoice.doctype, item_row: line.row, item: line.item_name,
    serials: line.serials, serial_no: line.serials.length === 1 ? line.serials[0] : '',
    complaint: '', issue_details: '',
  }
}
async function saveClaim() {
  if (saving.value) return
  saving.value = true
  formError.value = ''
  const { item, serials, ...data } = form.value
  try {
    const claim = await api('create_claim', data, true)
    form.value = null
    notice.value = tr('Claim opened', 'ওয়ারেন্টি দাবি খোলা হয়েছে') + ' · ' + claim.name
    status.value = ''
    claimSearch.value = claim.name
    tab.value = 'claims'
    searchClaims()
  } catch (error) {
    formError.value = error.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="inv-desk warranty-desk" :aria-label="tr('Warranties', 'ওয়ারেন্টি')">
    <header class="warranty-heading">
      <div><h2>{{ tr('Warranties', 'ওয়ারেন্টি') }}</h2><p>{{ tr('Supplier coverage, customer sale coverage and claims in one place.', 'সরবরাহকারী ও গ্রাহকের ওয়ারেন্টি এবং দাবি এক জায়গায়।') }}</p></div>
    </header>
    <nav class="warranty-navigation" :aria-label="tr('Warranty workspace', 'ওয়ারেন্টি ওয়ার্কস্পেস')">
      <button type="button" :aria-current="tab === 'stock' ? 'page' : undefined" @click="showStock()">{{ tr('Stock & suppliers', 'স্টক ও সরবরাহকারী') }}</button>
      <button type="button" :aria-current="tab === 'coverage' ? 'page' : undefined" @click="tab = 'coverage'">{{ tr('Customer coverage', 'গ্রাহকের ওয়ারেন্টি') }}</button>
      <button type="button" :aria-current="tab === 'claims' ? 'page' : undefined" @click="showClaims">{{ tr('Claims', 'দাবি') }}</button>
    </nav>
    <SupplierWarrantyRegister v-if="tab === 'stock'" :receipt="stockReceipt" @serial="serial => findSale(serial, 'serial')" />
    <div v-else-if="tab === 'coverage'">
      <header class="desk-head">
        <div><h3>{{ tr('Customer coverage', 'গ্রাহকের ওয়ারেন্টি') }}</h3><p>{{ tr('Find the coverage recorded on a submitted Sales or POS Invoice.', 'সাবমিট করা বিক্রয় বা পিওএস চালানের ওয়ারেন্টি দেখুন।') }}</p></div>
        <button type="button" :aria-expanded="showSales" @click="showSales ? showSales = false : browseSales()">{{ tr('Find invoice by customer', 'গ্রাহক দিয়ে চালান খুঁজুন') }}</button>
      </header>
      <section v-if="showSales" class="warranty-box">
        <form class="workspace-filters" @submit.prevent="browseSales()">
          <label class="desk-search">{{ tr('Customer or invoice number', 'গ্রাহক বা চালান নম্বর') }}<input v-model="salesSearch" type="search" maxlength="140" /></label>
          <label>{{ tr('Invoice type', 'চালানের ধরন') }}
            <select v-model="salesType">
              <option v-for="type in sales?.available || ['Sales Invoice', 'POS Invoice']" :key="type">{{ type }}</option>
            </select>
          </label>
          <div class="filter-actions"><button type="submit" :disabled="salesLoading">{{ tr('Find invoices', 'চালান খুঁজুন') }}</button><button type="button" @click="clearSalesFilters">{{ tr('Clear', 'মুছুন') }}</button></div>
        </form>
        <p v-if="salesError" class="desk-alert" role="alert">{{ salesError }}</p>
        <p v-else-if="salesLoading" role="status">{{ tr('Loading invoices…', 'চালান লোড হচ্ছে…') }}</p>
        <p v-else-if="!sales?.rows.length">{{ tr('No matching invoices.', 'কোনো চালান পাওয়া যায়নি।') }}</p>
        <ul v-else class="warranty-sales" role="list">
          <li v-for="invoice in sales.rows" :key="invoice.name">
            <button type="button" @click="findSale(invoice.name, 'invoice')">
              <strong>{{ invoice.customer_name || invoice.customer }}</strong>
              <small>{{ invoice.name }} · {{ invoice.posting_date }}</small>
            </button>
          </li>
        </ul>
        <footer v-if="salesPage > 1 || sales?.has_next" class="desk-pager">
          <button type="button" :disabled="salesLoading || salesPage === 1" @click="browseSales(salesPage - 1)">{{ tr('Previous', 'আগের') }}</button>
          <span>{{ salesPage }}</span>
          <button type="button" :disabled="salesLoading || !sales?.has_next" @click="browseSales(salesPage + 1)">{{ tr('Next', 'পরের') }}</button>
        </footer>
      </section>
      <form class="workspace-filters" @submit.prevent="lookup">
        <label>{{ tr('Look up by', 'যা দিয়ে খুঁজবেন') }}
          <select v-model="kind" @change="clearCoverage">
            <option value="invoice">{{ tr('Invoice number', 'চালান নম্বর') }}</option>
            <option value="serial">{{ tr('Serial number', 'সিরিয়াল নম্বর') }}</option>
          </select>
        </label>
        <label class="desk-search">{{ kind === 'serial' ? tr('Exact serial number', 'সঠিক সিরিয়াল নম্বর') : tr('Exact Sales or POS Invoice number', 'সঠিক বিক্রয় বা পিওএস চালান নম্বর') }}
          <input v-model.trim="reference" type="search" maxlength="140" required @input="clearCoverage" />
        </label>
        <div class="filter-actions"><button class="desk-primary" type="submit" :disabled="checking || !reference">{{ tr('Check warranty', 'ওয়ারেন্টি যাচাই') }}</button><button type="button" @click="clearLookup">{{ tr('Clear', 'মুছুন') }}</button></div>
      </form>
      <p v-if="coverageError" class="desk-alert" role="alert">{{ coverageError }}</p>
      <p v-else-if="checking" role="status">{{ tr('Checking warranty…', 'ওয়ারেন্টি যাচাই হচ্ছে…') }}</p>
      <div v-else-if="coverage" class="warranty-results">
        <dl v-if="summary.total" class="warranty-facts warranty-summary">
          <div><dt>{{ tr('Invoice lines', 'চালানের পণ্য') }}</dt><dd>{{ summary.total }}</dd></div>
          <div><dt>{{ tr('Active', 'সক্রিয়') }}</dt><dd>{{ summary.active }}</dd></div>
          <div><dt>{{ tr('Expired', 'মেয়াদ শেষ') }}</dt><dd>{{ summary.expired }}</dd></div>
          <div><dt>{{ tr('Expiry missing', 'মেয়াদ নেই') }}</dt><dd>{{ summary.missing }}</dd></div>
        </dl>
        <article v-if="coverage.serial" class="warranty-box">
          <h3>{{ coverage.serial.item_name || coverage.serial.item_code }} · {{ coverage.serial.name }}</h3>
          <dl class="warranty-facts">
            <div><dt>{{ tr('Serial status', 'সিরিয়ালের অবস্থা') }}</dt><dd>{{ coverage.serial.status || '—' }}</dd></div>
            <div><dt>{{ tr('Current warehouse', 'বর্তমান গুদাম') }}</dt><dd>{{ coverage.serial.warehouse || '—' }}</dd></div>
          </dl>
          <p v-if="coverage.serial.warranty_expiry_date">{{ tr('ERPNext serial warranty expiry', 'ইআরপিনেক্সটে সিরিয়ালের ওয়ারেন্টির মেয়াদ') }} · {{ coverage.serial.warranty_expiry_date }}</p>
          <template v-if="coverage.receipts.length">
            <h4>{{ tr('Supplier receipts', 'সরবরাহকারীর রসিদ') }}</h4>
            <ul class="warranty-receipts" role="list">
              <li v-for="receipt in coverage.receipts" :key="receipt.name">
                <a :href="recordUrl('purchase-receipt', receipt.name)" target="_blank" rel="noopener">{{ receipt.name }}</a>
                <small>{{ receipt.supplier_name || receipt.supplier }} · {{ receipt.posting_date }}</small>
                <button type="button" @click="showStock(receipt.name)">{{ tr('View supplier coverage', 'সরবরাহকারীর ওয়ারেন্টি দেখুন') }}</button>
              </li>
            </ul>
          </template>
          <p v-else>{{ tr('No matching supplier receipt is visible for this serial.', 'এই সিরিয়ালের কোনো সরবরাহকারী রসিদ দেখা যাচ্ছে না।') }}</p>
        </article>
        <article v-for="invoice in coverage.invoices" :key="invoice.doctype + ':' + invoice.name" class="warranty-box">
          <h3><a :href="recordUrl(invoice.doctype === 'POS Invoice' ? 'pos-invoice' : 'sales-invoice', invoice.name)" target="_blank" rel="noopener">{{ invoice.name }}</a></h3>
          <p>{{ invoice.customer }} · {{ invoice.posting_date }}</p>
          <ul class="warranty-lines" role="list">
            <li v-for="line in invoice.items" :key="line.row" class="warranty-line">
              <header class="warranty-line-head">
                <div><h4>{{ line.item_name }}</h4><p>{{ line.item_code }} · {{ line.quantity }} {{ tr('units invoiced', 'চালানের পরিমাণ') }}</p></div>
                <span class="warranty-tag" :data-state="line.status === 'Active' && line.days_remaining <= 30 ? 'expiring' : line.status.toLowerCase()">{{ textStatus(line.status) }}</span>
              </header>
              <dl class="warranty-facts">
                <div><dt>{{ tr('Coverage type', 'ওয়ারেন্টির ধরন') }}</dt><dd>{{ line.type || '—' }}</dd></div>
                <div><dt>{{ tr('Starts', 'শুরু') }}</dt><dd>{{ line.start || '—' }}</dd></div>
                <div><dt>{{ tr('Expires', 'শেষ') }}</dt><dd>{{ line.expires || '—' }}</dd></div>
                <div v-if="line.days_remaining != null"><dt>{{ tr('Time remaining', 'বাকি সময়') }}</dt><dd>{{ timeRemaining(line.days_remaining) }}</dd></div>
              </dl>
              <p v-if="line.terms" class="warranty-text">{{ line.terms }}</p>
              <details v-if="line.serials.length">
                <summary>{{ line.serials.length }} {{ tr('serial numbers', 'সিরিয়াল নম্বর') }}</summary>
                <div class="warranty-action-line"><button v-for="serial in line.serials" :key="serial" type="button" @click="findSale(serial, 'serial')">{{ serial }}</button></div>
              </details>
              <div class="warranty-action-line">
                <button v-if="coverage.can_claim && line.serials.length" type="button" @click="openClaim(invoice, line)">{{ tr('Open claim', 'দাবি খুলুন') }}</button>
                <small v-else-if="coverage.can_claim">{{ tr('A serial number is required to open an ERPNext claim here.', 'ইআরপিনেক্সটে দাবি খুলতে সিরিয়াল প্রয়োজন।') }}</small>
              </div>
            </li>
          </ul>
        </article>
        <p v-if="!coverage.invoices.length">{{ tr('No matching submitted sale is visible for this serial.', 'এই সিরিয়ালের কোনো সাবমিট করা বিক্রয় দেখা যাচ্ছে না।') }}</p>
      </div>
    </div>
    <div v-else>
      <header class="desk-head">
        <div><h3>{{ tr('Claims register', 'দাবির তালিকা') }}</h3><p>{{ tr('Review issues, log supplier RMA references, and close resolved claims.', 'সমস্যা, সরবরাহকারীর আরএমএ এবং সমাধান দেখুন।') }}</p></div>
      </header>
      <p v-if="notice" class="desk-success" role="status">{{ notice }}</p>
      <form class="workspace-filters" @submit.prevent="searchClaims">
        <label class="desk-search">{{ tr('Claim, customer, invoice, serial or RMA', 'দাবি, গ্রাহক, চালান, সিরিয়াল বা আরএমএ') }}<input v-model="claimSearch" type="search" maxlength="140" /></label>
        <label>{{ tr('Status', 'অবস্থা') }}
          <select v-model="status">
            <option value="">{{ tr('All statuses', 'সব অবস্থা') }}</option>
            <option v-for="state in statuses" :key="state" :value="state">{{ textStatus(state) }}</option>
          </select>
        </label>
        <div class="filter-actions"><button type="submit" :disabled="loadingClaims">{{ tr('Search', 'খুঁজুন') }}</button><button type="button" @click="clearClaimFilters">{{ tr('Clear', 'মুছুন') }}</button></div>
      </form>
      <p v-if="claimError" class="desk-alert" role="alert">{{ claimError }}</p>
      <p v-else-if="loadingClaims" role="status">{{ tr('Loading claims…', 'দাবি লোড হচ্ছে…') }}</p>
      <p v-else-if="claims && !claims.rows.length">{{ tr('No matching claims.', 'কোনো দাবি পাওয়া যায়নি।') }}</p>
      <div v-else-if="claims" class="desk-table-wrap">
        <table>
          <thead><tr><th>{{ tr('Claim', 'দাবি') }}</th><th>{{ tr('Customer', 'গ্রাহক') }}</th><th>{{ tr('Serial / item', 'সিরিয়াল / পণ্য') }}</th><th>{{ tr('Status', 'অবস্থা') }}</th></tr></thead>
          <tbody><tr v-for="claim in claims.rows" :key="claim.name">
            <td><button type="button" class="warranty-record-link" @click="openDetails(claim.name)">{{ claim.name }}</button><small>{{ claim.complaint }}</small></td>
            <td>{{ claim.customer_name || claim.customer }}<small v-if="claim.custom_sos_warranty_sale">{{ claim.custom_sos_warranty_sale }}</small><small v-if="claim.custom_sos_supplier_rma">RMA · {{ claim.custom_sos_supplier_rma }}</small></td><td>{{ claim.serial_no || '—' }}<small>{{ claim.item_code }}</small></td>
            <td>{{ textStatus(claim.status) }}<small>{{ claim.complaint_date }}</small></td>
          </tr></tbody>
        </table>
        <footer v-if="claimPage > 1 || claims.has_next" class="desk-pager">
          <button type="button" :disabled="claimPage <= 1" @click="loadClaims(claimPage - 1)">{{ tr('Previous', 'আগের') }}</button>
          <span>{{ claimPage }}</span>
          <button type="button" :disabled="!claims.has_next" @click="loadClaims(claimPage + 1)">{{ tr('Next', 'পরের') }}</button>
        </footer>
      </div>
    </div>
    <PartyDialog v-if="claimDetail" :title="claimDetail.name" :busy="saving" @close="claimDetail = null">
      <div class="inv-desk warranty-editor">
        <h3>{{ claimDetail.complaint }}</h3>
        <p>{{ claimDetail.customer }} · {{ claimDetail.item }}<template v-if="claimDetail.serial_no"> · {{ claimDetail.serial_no }}</template></p>
        <dl class="warranty-facts">
          <div><dt>{{ tr('Opened', 'খোলা হয়েছে') }}</dt><dd>{{ claimDetail.opened || '—' }}</dd></div>
          <div><dt>{{ tr('Coverage at claim', 'দাবির সময় ওয়ারেন্টি') }}</dt><dd>{{ claimDetail.warranty_status || '—' }} {{ claimDetail.warranty_expiry }}</dd></div>
          <div v-if="claimDetail.invoice"><dt>{{ tr('Invoice', 'চালান') }}</dt><dd>{{ claimDetail.invoice }}</dd></div>
          <div v-if="claimDetail.resolved"><dt>{{ tr('Resolved', 'সমাধান হয়েছে') }}</dt><dd>{{ claimDetail.resolved }} · {{ claimDetail.resolved_by }}</dd></div>
        </dl>
        <p v-if="claimDetail.issue_details" class="warranty-text">{{ claimDetail.issue_details }}</p>
        <p v-if="detailError" class="desk-alert" role="alert">{{ detailError }}</p>
        <form v-if="claimDetail.can_edit" @submit.prevent="saveDetails">
          <label>{{ tr('Status', 'অবস্থা') }}
            <select v-model="claimDraft.status">
              <option v-for="value in statuses" :key="value" :value="value"
                :disabled="['Closed', 'Cancelled'].includes(claimDetail.status) && value !== claimDetail.status">{{ textStatus(value) }}</option>
            </select>
          </label>
          <label>{{ tr('Supplier RMA reference', 'সরবরাহকারী আরএমএ রেফারেন্স') }}<input v-model.trim="claimDraft.supplier_rma" maxlength="140" /></label>
          <label>{{ tr('Resolution / outcome', 'সমাধান') }}<textarea v-model.trim="claimDraft.resolution" rows="3" maxlength="2000" :required="['Closed', 'Cancelled'].includes(claimDraft.status)"></textarea></label>
          <button type="submit" class="desk-primary" :disabled="saving">{{ tr('Save claim update', 'দাবি হালনাগাদ করুন') }}</button>
        </form>
        <p v-else>{{ textStatus(claimDetail.status) }} · {{ claimDetail.resolution || '—' }}</p>
        <a :href="recordUrl('warranty-claim', claimDetail.name)" target="_blank" rel="noopener">{{ tr('Open in ERPNext', 'ইআরপিনেক্সটে খুলুন') }} ↗</a>
      </div>
    </PartyDialog>
    <PartyDialog v-if="form" :title="tr('Open warranty claim', 'ওয়ারেন্টি দাবি খুলুন')" :busy="saving" @close="form = null">
      <div class="inv-desk claim-editor">
        <p>{{ form.invoice }} · {{ form.item }}</p>
        <p v-if="formError" class="desk-alert" role="alert">{{ formError }}</p>
        <form @submit.prevent="saveClaim">
          <label>{{ tr('Serial number', 'সিরিয়াল নম্বর') }}
            <select v-model="form.serial_no" required>
              <option value="" disabled>{{ tr('Choose serial', 'সিরিয়াল নির্বাচন করুন') }}</option>
              <option v-for="serial in form.serials" :key="serial">{{ serial }}</option>
            </select>
          </label>
          <label>{{ tr('Issue summary', 'সমস্যার সারাংশ') }}<input v-model.trim="form.complaint" required maxlength="140" /></label>
          <label>{{ tr('Issue details', 'সমস্যার বিবরণ') }}<textarea v-model.trim="form.issue_details" rows="3" maxlength="2000"></textarea></label>
          <button type="submit" class="desk-primary" :disabled="saving">{{ saving ? tr('Saving…', 'সংরক্ষণ হচ্ছে…') : tr('Save claim', 'দাবি সংরক্ষণ করুন') }}</button>
        </form>
      </div>
    </PartyDialog>
  </section>
</template>

<style scoped src="./inventoryDesk.css"></style>
<style scoped src="./warrantyDesk.css"></style>
<style scoped src="./workspaceFilters.css"></style>
<style scoped>
.warranty-heading{display:flex;justify-content:space-between;padding:clamp(14px,3vw,27px);border-radius:11px;background:var(--os-tint,#f3ebe0);color:var(--os-ink,#38291f);border:1px solid var(--os-border,#e5d6c4)}
.warranty-heading p{margin-top:5px;color:var(--os-muted,#6d5b4c)}
.warranty-navigation{padding-bottom:12px;border-bottom:1px solid var(--os-border,#e5d5c4)}
.warranty-navigation button{flex:1 1 140px;white-space:normal}
.warranty-results{display:grid;gap:9px}
.warranty-box{border:1px solid var(--os-border,#e5d5c4);border-radius:9px;padding:11px;min-width:0}
.warranty-box h4{overflow-wrap:anywhere;font-size:.92rem;margin:3px 0;font-weight:750}
.warranty-lines,.warranty-receipts,.warranty-sales{list-style:none;padding:0;margin:8px 0 0}
.warranty-line{padding:10px 0;border-top:1px solid var(--os-border,#e5d5c4)}
.warranty-line-head,.warranty-action-line,.warranty-receipts li{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 12px}
.warranty-action-line{justify-content:flex-start;margin-top:7px}
.warranty-receipts li{padding:5px 0;font-size:.85rem}
.warranty-summary dd{font-size:1.15rem}
.warranty-sales{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(200px,100%),1fr));gap:6px}
.warranty-sales button{width:100%;white-space:normal;text-align:left;overflow-wrap:anywhere}
.warranty-sales small{display:block}
.warranty-line summary{font-size:.8rem;font-weight:650;cursor:pointer;margin-top:7px}
.warranty-record-link{min-height:0!important;padding:2px 5px!important}
.claim-editor{border:0;padding:0}
.claim-editor form{display:grid;align-items:stretch}
.claim-editor button{justify-self:start}
</style>
