<script setup>
// SERVICING_OS_CUSTOMER_LOOKUP_666 — one stable name/mobile lookup, usable by both sales views.
import { ref, watch, onUnmounted, nextTick } from 'vue'
import CustomerAddressFields from './CustomerAddressFields.vue'
const props = defineProps({ selected: { type: Object, default: null }, label: { type: String, default: 'Find customer by name or mobile' } })
const emit = defineEmits(['selected', 'clear'])
const query = ref('')
const open = ref(false)
const loading = ref(false)
const hits = ref([])
const error = ref('')
const box = ref(null)
// STEP 6.67: the same quick-create works in Counter and Navbar New Sales.
const adding = ref(false)
const newName = ref('')
const newMobile = ref('')
const newAddress = ref({})
const newBusy = ref(false)
const newMessage = ref('')
async function saveNewCustomer() {
  if (newBusy.value) return
  newBusy.value = true; error.value = ''; newMessage.value = ''
  try {
    const token = window.frappe?.csrf_token || window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || ''
    const response = await fetch('/api/method/servicing_os.api.counter_fast_667.create_customer', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...(token ? {'X-Frappe-CSRF-Token': token} : {}) },
      body: JSON.stringify({ customer_name: newName.value.trim(), mobile_no: newMobile.value.trim(), ...newAddress.value })
    })
    const payload = await response.json()
    if (!response.ok || payload.exc || payload.exception || !payload.message?.customer?.name) {
      let msg = payload.message?.message || 'Unable to create customer.'
      try { const list=JSON.parse(payload._server_messages || '[]');if(list.length)msg=JSON.parse(list[0]).message || msg }catch(_){}
      throw new Error(String(msg).replace(/<[^>]*>/g,''))
    }
    const customer = payload.message.customer
    newMessage.value = payload.message.message || 'Customer selected.'
    adding.value = false
    newName.value = ''; newMobile.value = ''; newAddress.value = {}
    choose(customer)
  } catch(e) { error.value = e?.message || 'Customer could not be created.' }
  finally { newBusy.value = false }
}

let timer = null
let closer = null
let controller = null
let sequence = 0
function cancel() { clearTimeout(timer); if (controller) controller.abort(); controller = null; sequence++ }
function sameSelected() { return !!props.selected?.name && query.value.trim() === (props.selected.customer_name || props.selected.name) }
watch(() => [props.selected?.name, props.selected?.customer_name], () => {
  if (props.selected?.name) { query.value = props.selected.customer_name || props.selected.name; hits.value = []; open.value = false }
  else if (!open.value) query.value = ''
}, { immediate: true })
function lookup() {
  cancel()
  error.value = ''
  const term = query.value.trim()
  if (props.selected?.name && !sameSelected()) emit('clear')
  hits.value = []
  if (!open.value || sameSelected()) { loading.value = false; return }
  const mine = sequence
  loading.value = true
  timer = setTimeout(async () => {
    controller = new AbortController()
    try {
      const u = new URL(term.length >= 2 ? '/api/method/servicing_os.api.counter_fast_667.find_customers' : '/api/method/servicing_os.api.customer_grid_673.recent_customers', window.location.origin)
      if (term.length >= 2) u.searchParams.set('q', term)
      const r = await fetch(u, { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }, signal: controller.signal })
      const d = await r.json()
      if (!r.ok || d.exc || d.exception) throw new Error('Customer search unavailable. Check access or server logs.')
      if (mine !== sequence || !open.value || query.value.trim() !== term) return
      hits.value = Array.isArray(d.message?.results) ? d.message.results.slice(0, 8) : []
    } catch (e) {
      if (e.name !== 'AbortError' && mine === sequence) error.value = e.message || 'Search failed'
    } finally { if (mine === sequence) loading.value = false }
  }, 240)
}
function focus() { clearTimeout(closer); open.value = true; if (!sameSelected()) lookup() }
function blur() { clearTimeout(closer); closer = setTimeout(() => { if (!adding.value) open.value = false }, 180) }
function choose(c) {
  cancel(); clearTimeout(closer)
  if (!c?.name) return
  query.value = c.customer_name || c.name
  hits.value = []; open.value = false; loading.value = false; error.value = ''
  emit('selected', c)
}
async function clearSelection() {
  cancel(); query.value = ''; hits.value = []; error.value = ''; open.value = true
  emit('clear'); await nextTick(); box.value?.focus()
}
onUnmounted(() => { cancel(); clearTimeout(closer) })
</script>
<template>
  <!-- SERVICING_SALES_VISUAL_669: shared visual customer picker, original events retained. -->
  <div class="sos669-customer" @keydown.esc="open=false">
    <div class="sos669-customer-top">
      <div class="sos669-customer-identity">
        <strong>Customer</strong>
      </div>
      <button type="button" class="sos669-new-customer" @click="adding=true;open=false;error='';newName=!props.selected?.name ? query.trim() : '';newAddress={};newMessage=''">
        <span aria-hidden="true">＋</span> New Customer
      </button>
    </div>

    <div v-if="props.selected?.name" class="sos669-selected-customer" role="status">
      <span class="sos669-avatar" aria-hidden="true">{{ (props.selected.customer_name || props.selected.name || 'C').slice(0, 1).toUpperCase() }}</span>
      <div class="sos669-selected-details">
        <span class="sos669-selected-indicator">✓ Selected for this sale</span>
        <strong>{{ props.selected.customer_name || props.selected.name }}</strong>
        <small>{{ props.selected.mobile_no || 'No mobile recorded' }}</small>
      </div>
      <button type="button" class="sos669-change" @click="clearSelection">Change</button>
    </div>
    <div v-else class="sos669-search-area">
      <label class="sos669-search-label" for="sos669-customer-search">Find customer</label>
      <div class="sos669-search-wrap">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="10.7" cy="10.7" r="6.7"/><path d="m16 16 5 5"/></svg>
        <input id="sos669-customer-search" ref="box" type="search" :value="query" autocomplete="off" inputmode="search"
          aria-label="Search existing customers by name or mobile number" placeholder="Name or mobile number"
          @focus="focus" @blur="blur" @input="query=$event.target.value;open=true;lookup()" />
      </div>
      
    </div>

    <p v-if="error && !adding" class="sos669-error" role="alert">{{ error }}</p>
    <p v-if="newMessage" class="sos669-confirmation" role="status">{{ newMessage }}</p>
    <div v-if="!props.selected?.name && open && !sameSelected()" class="sos669-results" role="listbox" aria-label="Matching customers">
      <div class="sos673-grid-head"><b>{{ query.trim().length >= 2 ? "Matching customers" : "Recent customers" }}</b><small>Up to 8 · Click to select</small></div>
      <p v-if="loading" class="sos669-placeholder">Loading customers…</p>
      <div class="sos673-customer-grid">
      <button v-for="c in hits" :key="c.name" type="button" role="option" aria-selected="false"
        @mousedown.prevent @click="choose(c)">
        <span class="sos669-result-avatar" aria-hidden="true">{{ (c.customer_name || c.name || 'C').slice(0,1).toUpperCase() }}</span>
        <span class="sos669-result-main"><strong>{{ c.customer_name || c.name }}</strong><small>{{ c.mobile_no || "No mobile recorded" }}</small></span>
        
      </button>
      </div>
      <p v-if="!loading && !hits.length && !error" class="sos669-placeholder">{{ query.trim().length >= 2 ? "No matching customers. Use New Customer to register." : "No recent customers. Start typing to search." }}</p>
    </div>

    <Teleport to="body">
      <div v-if="adding" class="sos669-modal-overlay" @click.self="adding=false" @keydown.esc.stop="adding=false">
        <div class="sos669-modal" role="dialog" aria-modal="true" aria-label="New Customer Registration">
          <header class="sos669-modal-header">
            <div class="sos669-modal-brand">＋</div>
            <div class="sos669-modal-title"><span class="sos669-eyebrow">COUNTER / CUSTOMERS</span><h2>New Customer</h2><p>Register once and select for this sale</p></div>
            <button type="button" class="sos669-close" aria-label="Close New Customer" @click="adding=false">×</button>
          </header>
          <form class="sos669-new-form" @submit.prevent="saveNewCustomer">
            <div class="sos669-form-grid">
              <label><span>Full customer name <b>*</b></span><input v-model.trim="newName" type="text" autocomplete="name" maxlength="140" required placeholder="e.g. Jewel Rana" /></label>
              <label><span>Mobile number <b>*</b></span><input v-model.trim="newMobile" type="tel" autocomplete="tel" inputmode="tel" maxlength="16" required placeholder="01XXXXXXXXX" /></label>
              <CustomerAddressFields v-model="newAddress" />
            </div>
            <p class="sos669-modal-note">Customer details will be saved in ERPNext and selected in your current shopping cart.</p>
            <p v-if="error" class="sos669-error" role="alert">{{ error }}</p>
            <footer class="sos669-modal-footer">
              <button type="button" class="sos669-cancel" @click="adding=false">Cancel</button>
              <button type="submit" class="sos669-save" :disabled="newBusy || newName.trim().length<2 || newMobile.trim().length<11">
                {{ newBusy ? 'Saving…' : 'Save & Select Customer' }}
              </button>
            </footer>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>
<style>
/* Customer Picker v6.78 */
.sos669-customer{padding:12px!important;border-radius:12px!important}
.sos669-customer-top{align-items:center!important;flex-wrap:nowrap!important;gap:8px!important;margin-bottom:10px!important}
.sos669-customer-identity strong{font-size:13px!important;line-height:1.3!important}
.sos669-new-customer{min-height:34px!important;padding:7px 10px!important;font-size:11px!important;flex-shrink:0!important}
.sos669-search-label{font-size:10px!important;margin-bottom:5px!important}
.sos669-search-wrap{min-height:42px!important}
.sos669-search-wrap input{min-height:40px!important;font-size:12px!important}
.sos669-selected-customer{padding:9px!important}
@media(max-width:620px){.sos669-customer-top{flex-wrap:wrap!important}.sos669-new-customer{width:auto!important}}

/* 6.73 — compact eight-customer picker */
.sos669-results{max-height:340px!important;overflow:auto!important;top:calc(100% - 5px)!important}
.sos673-grid-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px 10px}
.sos673-grid-head b{font-size:12px;color:#60452f}.sos673-grid-head small{font-size:10px;color:#a1876e}
.sos673-customer-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:2px 5px 7px}
.sos669-results .sos673-customer-grid button{display:flex!important;align-items:center!important;min-width:0!important;min-height:58px!important;border:1px solid #eadbcc!important;border-radius:10px!important;background:#fffaf5!important;padding:9px!important}
.sos669-results .sos673-customer-grid button:hover,.sos669-results .sos673-customer-grid button:focus-visible{background:#f1e4d6!important;border-color:#b38d6c!important;outline:2px solid #c7a48655!important}
.sos673-customer-grid .sos669-result-main strong{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sos673-customer-grid .sos669-result-main small{font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(max-width:460px){.sos673-customer-grid{grid-template-columns:1fr}}
/* 6.69 — customer selection is one coherent ivory card across both sale views. */
.sos669-customer,.sos669-customer *,.sos669-modal,.sos669-modal *{box-sizing:border-box}
.sos669-customer{position:relative;width:100%;min-width:0;max-width:100%;color:#3c2c25;font-family:inherit;border:1px solid #e7d6c5;border-radius:16px;background:#fffcf7;padding:15px;box-shadow:0 2px 6px #47331c0b;text-align:left;isolation:isolate}
.sos669-customer-top{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:13px}
.sos669-customer-identity{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}
.sos669-eyebrow{color:#a17b5d;font-size:9px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}
.sos669-customer-identity strong{color:#3c2c25;font-size:15px;font-weight:750;letter-spacing:-.015em}
.sos669-customer-identity small{color:#9a826d;font-size:11px;line-height:1.5}
.sos669-new-customer{display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:5px!important;border:1px solid #e4cdb8!important;border-radius:10px!important;white-space:nowrap!important;min-height:38px!important;padding:9px 12px!important;background:#f2e6da!important;color:#71513a!important;font-size:12px!important;font-weight:800!important;box-shadow:none!important}
.sos669-new-customer:hover{background:#e9d8c7!important}
.sos669-new-customer span{font-size:17px;line-height:1}
.sos669-search-area{width:100%;min-width:0}
.sos669-search-label{display:block!important;font-size:11px!important;color:#735740!important;font-weight:650!important;margin-bottom:6px!important}
.sos669-search-wrap{display:flex;align-items:center;gap:9px;min-height:46px;width:100%;border:1px solid #dfcbb9;background:#fffefd;border-radius:10px;padding:0 12px;color:#8d6c50}
.sos669-search-wrap:focus-within{border-color:#af8060;box-shadow:0 0 0 3px #bc926b22}
.sos669-search-wrap svg{flex-shrink:0}
.sos669-search-wrap input{display:block!important;flex:1!important;min-width:0!important;width:100%!important;border:0!important;box-shadow:none!important;outline:0!important;background:transparent!important;color:#3c2c25!important;padding:11px 0!important;min-height:44px!important;font-size:13px!important;line-height:1.3!important}
.sos669-search-wrap input:focus{outline:none!important;box-shadow:none!important}
.sos669-search-help{font-size:10px;color:#9f8770;margin:7px 0 0}
.sos669-selected-customer{display:flex;align-items:center;gap:11px;background:#f7eee5;border:1px solid #e6d3c0;padding:11px;border-radius:12px;min-width:0}
.sos669-avatar,.sos669-result-avatar{display:grid;place-items:center;flex:0 0 auto;width:38px;height:38px;border-radius:11px;background:#805a3e;color:#fffefa;font-size:15px;font-weight:850}
.sos669-selected-details{min-width:0;flex:1;display:flex;flex-direction:column;gap:3px}
.sos669-selected-details strong{font-size:13px;color:#3c2c25;overflow-wrap:anywhere;line-height:1.3}
.sos669-selected-details small{font-size:11px;color:#8a7058}
.sos669-selected-indicator{color:#7b835d;font-size:10px;font-weight:800}
.sos669-change{border:1px solid #dcc5ae!important;border-radius:9px!important;background:#fffcf7!important;color:#78543d!important;padding:8px 12px!important;font-size:11px!important;font-weight:780!important;flex-shrink:0}
.sos669-results{position:absolute;left:14px;right:14px;top:calc(100% - 8px);z-index:220;max-height:300px;overflow:auto;border:1px solid #e0c6ae;background:#fffcf7;border-radius:12px;padding:5px;box-shadow:0 14px 40px #39281833}
.sos669-results button{display:flex!important;align-items:center!important;gap:9px!important;min-height:62px!important;width:100%!important;border:0!important;border-bottom:1px solid #f0e6dc!important;background:transparent!important;color:#3c2c25!important;padding:9px!important;text-align:left!important}
.sos669-results button:last-of-type{border-bottom:0!important}
.sos669-results button:hover,.sos669-results button:focus-visible{background:#f7ece2!important;outline:0!important}
.sos669-result-avatar{width:32px;height:32px;border-radius:9px;background:#f3e2d1;color:#79573c;font-size:13px}
.sos669-result-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.sos669-result-main strong{font-size:12px;color:#3c2c25;overflow-wrap:anywhere}
.sos669-result-main small{font-size:10px;color:#9b836b}
.sos669-result-mobile{font-size:11px;color:#80624a;white-space:nowrap}
.sos669-placeholder,.sos669-error,.sos669-confirmation{padding:9px;margin:0;font-size:11px;color:#876951}
.sos669-error{color:#aa3b2c;background:#fff1ed;border-radius:8px;margin-top:9px}
.sos669-confirmation{color:#5f794f}
.sos669-modal-overlay{position:fixed;inset:0;z-index:2147480000;display:flex;align-items:center;justify-content:center;overflow:auto;padding:16px;background:#24191380;backdrop-filter:blur(3px)}
.sos669-modal{width:100%;max-width:530px;background:#fffcf7;color:#3c2c25;border:1px solid #e7d6c5;border-radius:20px;box-shadow:0 24px 70px #26180e55;max-height:calc(100vh - 32px);overflow:auto}
.sos669-modal-header{padding:21px 22px 16px;display:flex;align-items:center;gap:13px;border-bottom:1px solid #eee0d1}
.sos669-modal-brand{display:grid;place-items:center;width:44px;height:44px;background:#f4e3d3;color:#815e43;font-size:24px;font-weight:800;border-radius:12px;flex:0 0 auto}
.sos669-modal-title{flex:1;min-width:0}.sos669-modal-title h2{font-size:20px!important;color:#3c2c25!important;line-height:1.2!important;margin:3px 0!important;font-weight:800!important}.sos669-modal-title p{margin:0;color:#937c65;font-size:12px}
.sos669-close{flex-shrink:0;width:35px;height:35px;border:1px solid #e3d3c3!important;border-radius:9px!important;color:#72543f!important;background:#fbf6f0!important;font-size:23px!important;line-height:1!important}
.sos669-new-form{padding:20px 22px 22px}
.sos669-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.sos669-form-grid label{display:flex;flex-direction:column;min-width:0;gap:7px;color:#70543f;font-size:12px;font-weight:700}.sos669-form-grid label b{color:#ac6952}
.sos669-form-grid input{width:100%!important;min-width:0!important;min-height:44px!important;padding:11px 12px!important;border:1px solid #e1cab7!important;border-radius:10px!important;background:#fffefa!important;color:#39291e!important;font-size:13px!important;outline:none!important}
.sos669-form-grid input:focus{border-color:#af8262!important;box-shadow:0 0 0 3px #b5896429!important}
.sos669-modal-note{color:#987d66;font-size:11px;line-height:1.5;margin:15px 0 8px}
.sos669-modal-footer{display:flex;align-items:center;justify-content:flex-end;gap:10px;margin-top:15px}
.sos669-cancel,.sos669-save{min-height:42px!important;border-radius:10px!important;padding:11px 15px!important;font-size:12px!important;font-weight:800!important}
.sos669-cancel{background:#fffefa!important;border:1px solid #e1c9b7!important;color:#75543b!important}
.sos669-save{background:#805a3e!important;border:1px solid #805a3e!important;color:#fffefa!important}.sos669-save:hover{background:#69472f!important}.sos669-save:disabled{opacity:.5;cursor:not-allowed}
@media(max-width:620px){.sos669-form-grid{grid-template-columns:1fr}.sos669-customer{padding:12px}.sos669-customer-top{align-items:center}.sos669-new-customer{width:100%;justify-content:center!important}.sos669-modal-header,.sos669-new-form{padding-left:15px;padding-right:15px}}

/* SOS_CUSTOMER_SINGLE_BORDER_V679 */

/* One border around the complete search control */
.sos669-search-wrap {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    border: 1px solid #dfcbb9 !important;
    border-radius: 11px !important;
    background: #fffdfa !important;
    padding: 0 12px !important;
    min-height: 44px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}

/* Remove all input-level borders and inherited field styling */
.sos669-search-wrap input,
.sos669-search-wrap input[type="search"],
.sos669-search-wrap input:focus,
.sos669-search-wrap input:hover {
    appearance: none !important;
    -webkit-appearance: none !important;
    border: none !important;
    border-width: 0 !important;
    border-radius: 0 !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-image: none !important;
    padding: 0 !important;
    margin: 0 !important;
    min-height: 40px !important;
    height: 40px !important;
    flex: 1 !important;
    width: 100% !important;
    min-width: 0 !important;
    font-size: 13px !important;
    color: #3c2c25 !important;
}

.sos669-search-wrap:focus-within {
    border-color: #a77b59 !important;
    box-shadow: 0 0 0 3px rgba(167,123,89,.12) !important;
}

.sos669-search-wrap input::-webkit-search-decoration,
.sos669-search-wrap input::-webkit-search-cancel-button {
    -webkit-appearance: none !important;
}

</style>
