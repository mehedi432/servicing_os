<script setup>
import { ref, onMounted } from 'vue';
import { moduleApi } from './extensionApi.js';
const query = ref('');
const customers = ref([]);
const detail = ref(null);
const config = ref(null);
const busy = ref(false);
const error = ref('');
const success = ref('');
const showNew = ref(false);
const form = ref({ name:'', mobile:'', group:'', territory:'' });

async function searchCustomers() {
  error.value=''; busy.value=true;
  try {
    const result = await moduleApi('search_customer_cards',{search:query.value});
    customers.value=result.customers || [];
  } catch(e) { error.value=e.message; }
  finally { busy.value=false; }
}
async function openCustomer(id) {
  error.value=''; busy.value=true;
  try { detail.value=await moduleApi('get_customer_card',{customer:id}); }
  catch(e) { error.value=e.message; }
  finally { busy.value=false; }
}
async function openNew() {
  error.value=''; showNew.value=true;
  if (config.value) return;
  try {
    const url=new URL('/api/method/servicing_os.api.counter_customers.get_customer_config',window.location.origin);
    const response=await fetch(url,{credentials:'same-origin',headers:{Accept:'application/json'}});
    const data=await response.json();
    if (!response.ok || data.exc) throw new Error(data.exception||'Customer setup unavailable');
    config.value=data.message;
    form.value.group=config.value.default_group || '';
    form.value.territory=config.value.default_territory || '';
  } catch(e) { error.value=e.message; }
}
async function saveCustomer() {
  busy.value=true; error.value=''; success.value='';
  try {
    const url='/api/method/servicing_os.api.counter_customers.create_counter_customer';
    const cookie=(document.cookie.split('; ').find(v=>v.startsWith('csrf_token='))||'').split('=').slice(1).join('=');
    const csrf=window.frappe?.csrf_token||window.csrf_token||(cookie?decodeURIComponent(cookie):'');
    const response=await fetch(url,{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json',Accept:'application/json',...(csrf?{'X-Frappe-CSRF-Token':csrf}:{})},
      body:JSON.stringify({customer_name:form.value.name,mobile_no:form.value.mobile,
        customer_group:form.value.group,territory:form.value.territory})});
    const data=await response.json();
    if (!response.ok || data.exc) {
      let message=data.exception||'Unable to save Customer';
      try { const m=JSON.parse(data._server_messages||'[]'); if(m.length) message=JSON.parse(m[m.length-1]).message; } catch {}
      throw new Error(message);
    }
    const newCustomer=data.message.customer;
    showNew.value=false; query.value=newCustomer.customer_name;
    success.value=`Customer ${newCustomer.customer_name} saved.`;
    await searchCustomers(); await openCustomer(newCustomer.name);
  } catch(e) { error.value=e.message; }
  finally {busy.value=false;}
}
const money=(n)=>'৳'+Number(n||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2});


// SERVICING_SHOP_STOCK_SEARCH_624A — automatic customer search (debounced).
import {watch as sosWatch, onBeforeUnmount as sosOnBeforeUnmount} from 'vue';
let sosSearchDelay = null;
let sosSearchVersion = 0;
sosWatch(query, (value) => {
  clearTimeout(sosSearchDelay);
  const token = ++sosSearchVersion;
  const term = String(value || '').trim();
  if (term.length < 2) { customers.value = []; return; }
  sosSearchDelay = setTimeout(async () => {
    try {
      const result = await moduleApi('search_customer_cards',{search:term});
      if (token === sosSearchVersion) {customers.value = result.customers || []; error.value='';}
    } catch (e) {if (token === sosSearchVersion) error.value = e.message;}
  }, 260);
});
sosOnBeforeUnmount(() => {clearTimeout(sosSearchDelay);sosSearchVersion++;});

</script>
<template>
  <section class="sos-ext-root sos-customers">
    <header class="ex-heading"><div><div class="ex-kicker">CUSTOMER RELATIONSHIPS</div><h1>Customers</h1><p>One customer, with service history, purchases and dues.</p></div>
      <button class="ex-primary" type="button" @click="openNew">+ New Customer</button></header>
    <div v-if="error" class="ex-alert ex-error" role="alert">{{ error }}</div>
    <div v-if="success" class="ex-alert ex-success" role="status">{{ success }}</div>
    <div class="ex-columns">
      <aside class="ex-panel"><h2>Find Customer</h2><div class="ex-search">
        <input v-model="query" placeholder="Name or mobile number" aria-label="Find customer" />
        <span class="ex-auto-hint">Auto search</span></div>
        <p class="ex-muted">Start typing a name or mobile number. Matches appear automatically.</p>
        <div class="ex-results"><button v-for="c in customers" :key="c.name" type="button" class="ex-result"
          :class="{ selected:detail?.customer?.name===c.name }" @click="openCustomer(c.name)">
          <span class="ex-avatar">{{ (c.customer_name||'?').slice(0,1).toUpperCase() }}</span>
          <span class="ex-result-body"><strong>{{ c.customer_name }}</strong><small>{{ c.mobile||c.name }}</small></span><span class="ex-chevron">›</span>
        </button><div v-if="!customers.length" class="ex-empty">No matches displayed. Search above to begin.</div></div>
      </aside>
      <div class="ex-panel ex-profile" v-if="detail">
        <div class="ex-profile-head"><div><div class="ex-kicker">CUSTOMER PROFILE</div><h2>{{ detail.customer.customer_name }}</h2><p>{{ detail.customer.mobile||'No mobile saved' }}</p></div><span class="ex-tag">{{ detail.customer.name }}</span></div>
        <div class="ex-metrics"><article><strong>{{ detail.job_count }}</strong><span>Recent service jobs</span></article><article><strong>{{ detail.invoice_count }}</strong><span>Recent invoices</span></article><article><strong>{{ detail.outstanding_bdt===null?'Restricted':money(detail.outstanding_bdt) }}</strong><span>Outstanding (BDT)</span></article></div>
        <h3>Repair history</h3><div v-if="!detail.jobs.length" class="ex-empty-small">No visible Service Jobs for this customer.</div>
        <div v-for="job in detail.jobs" :key="job.name" class="ex-history"><div><strong>{{ job.name }}</strong><small>{{ job.brand }} {{ job.device_model||job.device_type }}</small></div><span class="ex-tag">{{ job.status }}</span></div>
        <h3>Sales and invoices</h3><div v-if="!detail.invoices.length" class="ex-empty-small">No visible invoices.</div>
        <div v-for="inv in detail.invoices" :key="inv.name" class="ex-history"><div><strong>{{ inv.name }}</strong><small>{{ inv.posting_date }} · {{ inv.status }}</small></div><div class="ex-amount"><strong>{{ money(inv.grand_total) }}</strong><small>Due {{ money(inv.outstanding_amount) }}</small></div></div>
      </div>
      <div class="ex-panel ex-empty-profile" v-else><div class="ex-largeicon">◎</div><h2>Customer 360°</h2><p>Select a customer on the left to see their repair and billing history.</p></div>
    </div>
    <div v-if="showNew" class="ex-modal-shade" @click.self="showNew=false"><form class="ex-modal" @submit.prevent="saveCustomer" aria-label="Create customer">
      <div class="ex-modal-header"><div><div class="ex-kicker">NEW CUSTOMER</div><h2>Add Customer</h2></div><button type="button" class="ex-close" @click="showNew=false">×</button></div>
      <div class="ex-form"><label>Customer name<input v-model="form.name" required maxlength="120" placeholder="Full name" /></label>
        <label>Mobile number<input v-model="form.mobile" required inputmode="tel" placeholder="01XXXXXXXXX" /></label>
        <label>Customer group<select v-model="form.group" required><option value="">Choose group</option><option v-for="g in config?.groups||[]" :key="g">{{ g }}</option></select></label>
        <label>Territory<select v-model="form.territory" required><option value="">Choose territory</option><option v-for="t in config?.territories||[]" :key="t">{{ t }}</option></select></label></div>
      <p class="ex-muted">Mobile numbers are checked against existing customers to reduce duplicates.</p>
      <div class="ex-modal-actions"><button type="button" class="ex-secondary" @click="showNew=false">Cancel</button><button class="ex-primary" :disabled="busy || !config">{{ busy?'Saving...':'Save Customer' }}</button></div>
    </form></div>
  </section>
</template>
<style scoped src="./extensionStyle.css"></style>

<style scoped>
.ex-auto-hint{display:inline-flex;align-items:center;color:#8a6e4f;background:#f4eadb;border-radius:10px;padding:10px;font-size:11px;font-weight:700;white-space:nowrap}
</style>
