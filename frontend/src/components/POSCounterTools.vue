<script setup>
// SERVICING_POS_COUNTER_TOOLS_620C
import { ref, watch, onMounted } from 'vue'

const props = defineProps({ posProfile: { type: String, default: '' } })
const setup = ref(null)
const loading = ref(false)
const error = ref('')
const scan = ref('')
const scanLoading = ref(false)
const scanError = ref('')
const scanResult = ref(null)

async function call(method, params = {}) {
  const url = new URL('/api/method/servicing_os.api.pos_counter_tools.' + method, window.location.origin)
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, String(v))
  }
  const response = await fetch(url, { method: 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } })
  const body = await response.json()
  if (!response.ok || body.exc || body.exc_type) {
    let message = body.exception || 'Unable to load POS information'
    if (body._server_messages) {
      try {
        const list = JSON.parse(body._server_messages)
        message = JSON.parse(list[list.length - 1]).message || message
      } catch (_) { /* keep fallback */ }
    }
    throw Error(message)
  }
  return body.message
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    setup.value = await call('get_pos_setup', { pos_profile: props.posProfile })
  } catch (e) {
    error.value = e.message || String(e)
  } finally { loading.value = false }
}

async function lookup() {
  const barcode = scan.value.trim()
  scanError.value = ''
  scanResult.value = null
  if (!barcode) { scanError.value = 'Scan a barcode or enter an Item Code.'; return }
  scanLoading.value = true
  try {
    const result = await call('lookup_pos_barcode', { barcode, pos_profile: props.posProfile })
    if (!result.found) scanError.value = result.reason || 'Product not found.'
    else scanResult.value = result
  } catch (e) {
    scanError.value = e.message || String(e)
  } finally { scanLoading.value = false }
}

function formatPrice(p) {
  if (!p || p.rate === null || p.rate === undefined) return 'No selling list price'
  return (p.currency === 'BDT' ? '৳' : `${p.currency || ''} `) + Number(p.rate).toLocaleString('en-BD', { maximumFractionDigits: 2 })
}

watch(() => props.posProfile, () => {
  scanResult.value = null
  scanError.value = ''
  refresh()
})
onMounted(refresh)
</script>

<template>
  <section class="pct-root" aria-label="Point of sale counter tools">
    <div class="pct-head">
      <div>
        <p class="pct-kicker">COUNTER TOOLS</p>
        <h2>Fast cashier preparation</h2>
        <p>Identify products, check the POS profile, and launch ERPNext checkout.</p>
      </div>
      <button class="pct-refresh" type="button" :disabled="loading" @click="refresh">{{ loading ? 'Checking…' : '↻ Check Setup' }}</button>
    </div>

    <p v-if="error" class="pct-alert" role="alert">{{ error }}</p>

    <div class="pct-grid">
      <div class="pct-card pct-scan">
        <div class="pct-card-header">
          <div><span class="pct-step">01 / BARCODE</span><h3>Find a product</h3></div>
          <span class="pct-chip">Read-only lookup</span>
        </div>
        <form class="pct-scan-row" @submit.prevent="lookup">
          <label class="pct-input-wrap">
            <span>Scan barcode or type Item Code</span>
            <input v-model="scan" type="search" autocomplete="off" placeholder="Try AMCL-LEXAR-NM620-512" aria-label="Barcode or Item Code" />
          </label>
          <button type="submit" :disabled="scanLoading">{{ scanLoading ? 'Searching…' : 'Find Item' }}</button>
        </form>
        <p class="pct-muted">Barcode scanners act like keyboards. Add real barcodes in the Item master; existing Item Codes also work here.</p>
        <p v-if="scanError" class="pct-error" role="status">{{ scanError }}</p>
        <div v-if="scanResult?.item" class="pct-result">
          <span class="pct-match">MATCHED {{ scanResult.matched_on === 'barcode' ? 'BARCODE' : 'ITEM CODE' }}</span>
          <strong>{{ scanResult.item.item_name }}</strong>
          <p class="pct-code">{{ scanResult.item.item_code }}</p>
          <div class="pct-result-stats">
            <div><span>List price</span><b>{{ formatPrice(scanResult.item.list_price) }}</b></div>
            <div><span>Warehouse ledger qty</span><b>{{ scanResult.item.is_stock_item ? (scanResult.item.ledger_qty ?? '—') : 'Non-stock' }}</b></div>
          </div>
          <div class="pct-links">
            <a :href="'/app/item/' + encodeURIComponent(scanResult.item.item_code)" target="_blank" rel="noopener noreferrer">View Item ↗</a>
            <a class="pct-button-link" href="/app/point-of-sale" target="_blank" rel="noopener noreferrer">Go to POS checkout ↗</a>
          </div>
        </div>
      </div>

      <div class="pct-card pct-checks">
        <div class="pct-card-header">
          <div><span class="pct-step">02 / READINESS</span><h3>Counter configuration</h3></div>
          <span v-if="setup" class="pct-chip" :class="setup.configuration_ready ? 'pct-good' : 'pct-warning'">{{ setup.configuration_ready ? 'Basic setup ready' : 'Setup required' }}</span>
        </div>
        <p v-if="loading && !setup" class="pct-muted">Checking ERPNext settings…</p>
        <template v-if="setup">
          <div class="pct-profile"><span>Selected profile</span><strong>{{ setup.profile || 'Not configured' }}</strong></div>
          <div class="pct-check" v-for="(check, i) in setup.checks" :key="i">
            <span class="pct-dot" :class="check.ok ? 'pct-dot-ok' : (check.required ? 'pct-dot-bad' : 'pct-dot-soft')">{{ check.ok ? '✓' : '!' }}</span>
            <div><strong>{{ check.label }}</strong><small>{{ check.detail }}</small></div>
          </div>
          <div class="pct-session"><span>Current cashier session</span><strong>{{ setup.session }}</strong></div>
        </template>
      </div>
    </div>

    <div class="pct-grid pct-bottom-grid">
      <div class="pct-card">
        <span class="pct-step">03 / RECEIPT</span>
        <h3>Receipt printing</h3>
        <p class="pct-muted">Receipts are printed by native ERPNext POS after a completed sale, using the selected POS Profile and print format.</p>
        <div class="pct-pair"><span>Auto print after order</span><b>{{ setup?.receipt?.auto_print ? 'Enabled' : 'Not enabled' }}</b></div>
        <div class="pct-pair"><span>Print format</span><b>{{ setup?.receipt?.print_format || 'POS default' }}</b></div>
        <a class="pct-text-link" href="/app/pos-profile" target="_blank" rel="noopener noreferrer">Configure POS receipts ↗</a>
      </div>
      <div class="pct-card">
        <span class="pct-step">04 / CASHIER</span>
        <h3>Open and close your shift</h3>
        <p class="pct-muted">Open a POS session, scan products in native POS, collect payment, print the receipt, then close the session.</p>
        <div class="pct-links pct-cashier-links">
          <a href="/app/pos-opening-entry" target="_blank" rel="noopener noreferrer">Opening Entries ↗</a>
          <a href="/app/pos-closing-entry" target="_blank" rel="noopener noreferrer">Closing Entries ↗</a>
          <a class="pct-button-link" href="/app/point-of-sale" target="_blank" rel="noopener noreferrer">Launch POS ↗</a>
        </div>
      </div>
    </div>
    <p class="pct-footnote">This screen does not add scanned Items to a cart or create invoices. Stock availability, taxes, discounts, payment and receipt printing are verified by ERPNext during checkout.</p>
  </section>
</template>

<style scoped>
.pct-root,.pct-root *{box-sizing:border-box}.pct-root{color:#514435;max-width:1500px;margin:0 auto}.pct-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 16px;flex-wrap:wrap}.pct-kicker,.pct-step{font-size:10px;font-weight:800;letter-spacing:1px;color:#9c7a50}.pct-head h2{font-size:20px;font-weight:800;margin:5px 0}.pct-head p:not(.pct-kicker){font-size:12px;color:#91836e}.pct-refresh{border:1px solid #dfd2be;background:#fffdf7;color:#655037;padding:10px 15px;border-radius:10px;font-weight:700;font-size:12px;min-height:40px}.pct-refresh:disabled{opacity:.6}.pct-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:14px}.pct-bottom-grid{margin-top:14px;grid-template-columns:repeat(2,minmax(0,1fr))}.pct-card{min-width:0;background:#fffefa;border:1px solid #e4d9ca;border-radius:15px;padding:20px;box-shadow:0 5px 15px #5b493308}.pct-card h3{font-size:17px;font-weight:800;margin:5px 0 14px}.pct-card-header{display:flex;align-items:start;justify-content:space-between;gap:10px;margin-bottom:12px}.pct-card-header h3{margin-bottom:0}.pct-chip{display:inline-flex;align-items:center;border:1px solid #e6dbce;padding:6px 9px;border-radius:20px;font-size:10px;font-weight:700;background:#f6f1e8;white-space:nowrap}.pct-good{color:#286a48;background:#e8f3ea;border-color:#d4e8d6}.pct-warning{color:#865f23;background:#fff2d8;border-color:#efdfb7}.pct-scan-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;align-items:end}.pct-input-wrap{display:flex;flex-direction:column;gap:7px;min-width:0}.pct-input-wrap span{font-size:11px;font-weight:700}.pct-input-wrap input{width:100%;padding:11px 12px;border:1px solid #d9cbb8;border-radius:10px;background:white;color:#43372a;font-size:13px;min-height:43px}.pct-input-wrap input:focus{outline:2px solid #d4b58b;outline-offset:1px}.pct-scan-row button,.pct-button-link{display:inline-flex;justify-content:center;align-items:center;text-decoration:none;background:#765e44;border:1px solid #765e44;color:#fff!important;padding:10px 14px;border-radius:10px;min-height:43px;font-size:12px;font-weight:750;white-space:nowrap}.pct-scan-row button:disabled{opacity:.6}.pct-muted{color:#8c7c69;font-size:12px;line-height:1.5;margin-top:10px}.pct-alert,.pct-error{background:#fff0ea;color:#9a372d;padding:11px 13px;border-radius:9px;font-size:12px;margin:10px 0}.pct-result{border:1px solid #dacbbb;background:#f8f3e9;border-radius:12px;padding:14px;margin-top:15px}.pct-result strong{display:block;font-size:15px;margin:6px 0 0}.pct-match{font-size:10px;font-weight:800;color:#897147;letter-spacing:.6px}.pct-code{font-size:12px;color:#897e70;margin:4px 0 12px;overflow-wrap:anywhere}.pct-result-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.pct-result-stats div{padding:9px;background:#fffdfa;border:1px solid #e5dacb;border-radius:9px}.pct-result-stats span,.pct-result-stats b{display:block;font-size:12px}.pct-result-stats span{font-size:10px;color:#91836f;margin-bottom:4px}.pct-links{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px}.pct-links a,.pct-text-link{font-size:12px;font-weight:750;color:#80613d;text-decoration:none}.pct-check{display:flex;gap:10px;align-items:start;padding:9px 0;border-bottom:1px solid #f0e9dd}.pct-dot{width:22px;height:22px;display:grid;place-items:center;border-radius:8px;font-weight:800;font-size:12px;flex:0 0 auto}.pct-dot-ok{background:#e6f1e9;color:#286a48}.pct-dot-bad{background:#fff0df;color:#93611d}.pct-dot-soft{background:#eee9e1;color:#827768}.pct-check strong,.pct-check small{display:block}.pct-check strong{font-size:12px}.pct-check small{font-size:11px;color:#998a76;margin-top:3px}.pct-profile,.pct-session,.pct-pair{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;padding:9px 0;border-bottom:1px solid #f0e8dd;font-size:12px}.pct-profile{background:#f7f1e6;padding:11px;border-radius:10px;margin-bottom:9px}.pct-pair span,.pct-profile span,.pct-session span{color:#8e806d}.pct-session{margin-top:8px}.pct-text-link{display:inline-block;margin-top:12px}.pct-cashier-links{gap:12px}.pct-footnote{font-size:11px;color:#9b8b77;margin:12px 0}.pct-root a:hover{text-decoration:underline}@media(max-width:850px){.pct-grid{grid-template-columns:1fr}}@media(max-width:560px){.pct-card{padding:14px}.pct-scan-row{grid-template-columns:1fr}.pct-result-stats{grid-template-columns:1fr}.pct-head h2{font-size:19px}}
</style>
