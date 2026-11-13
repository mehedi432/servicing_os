<script setup>
import {ref,onMounted} from 'vue'
import {shopApi} from './shopQuickApi.js'
const emit=defineEmits(['navigate'])
const data=ref(null),loading=ref(false),error=ref('')
async function load(){loading.value=true;error.value='';try{data.value=await shopApi('get_shop_home')}catch(e){error.value=e.message}finally{loading.value=false}}
const go=(name)=>emit('navigate',name)
onMounted(load)
</script>
<template>
  <section class="sos-ext-root sh-root" aria-label="Service Shop">
    <header class="sh-head">
      <div><div class="sh-kicker">SERVICING OS / YOUR BUSINESS</div><h1>Service Shop</h1><p>Everything happening in your computer shop, in one place.</p></div>
      <button class="sh-outline" @click="load" :disabled="loading">{{loading?'Loading…':'↻ Refresh'}}</button>
    </header>
    <div v-if="error" class="sh-alert" role="alert">{{error}} <button type="button" @click="load">Retry</button></div>
    <div class="sh-banner">
      <div class="sh-emblem">⌘</div><div><span class="sh-kicker">CURRENT SHOP</span><h2>{{data?.shops?.[0]?.shop_name || 'AL MODINA COMPUTERS LIMITED'}}</h2>
        <p>{{data?.shops?.length?'Shop configuration found':'Showing available shop information. The shop record is not accessible under this login.'}}</p>
      </div><span class="sh-status">{{data?.shops?.[0]?.is_active?'Active':(data?.shops?.length?'Inactive':'Check setup')}}</span>
    </div>
    <div class="sh-metrics">
      <article><span>Service Jobs</span><strong>{{data?.job_total ?? '—'}}</strong><small>Actual visible records</small></article>
      <article><span>Jobs In Progress</span><strong>{{data?.pending_jobs ?? '—'}}</strong><small>Not delivered or cancelled</small></article>
      <article><span>Customers</span><strong>{{data?.customer_count ?? '—'}}</strong><small>Visible customer records</small></article>
      <article><span>Stock Products</span><strong>{{data?.item_count ?? '—'}}</strong><small>Enabled stock-managed Items</small></article>
    </div>
    <div class="sh-grid">
      <div class="sh-card">
        <h3>What do you need to do?</h3><p class="sh-caption">Big buttons for everyday counter work. No other system or tabs.</p>
        <div class="sh-actions">
          <button type="button" @click="go('Counter')"><span class="sh-icon">▣</span><span><strong>Receive a Computer</strong><small>Start a service job</small></span><b>›</b></button>
          <button type="button" @click="go('New Sales')"><span class="sh-icon">◈</span><span><strong>New Sale & Checkout</strong><small>Products, customers and cash</small></span><b>›</b></button>
          <button type="button" @click="go('Service Jobs')"><span class="sh-icon">⚒</span><span><strong>Manage Repairs</strong><small>Technician and delivery status</small></span><b>›</b></button>
          <button type="button" @click="go('Inventory')"><span class="sh-icon">▤</span><span><strong>Add Products / Receive Stock</strong><small>One easy stock modal</small></span><b>›</b></button>
          <button type="button" @click="go('Used Laptops')"><span class="sh-icon">▣</span><span><strong>Used Laptop Buy / Sell</strong><small>Serial-tracked devices</small></span><b>›</b></button>
          <button type="button" @click="go('Customers')"><span class="sh-icon">♙</span><span><strong>Find a Customer</strong><small>Automatic name/mobile search</small></span><b>›</b></button>
        </div>
      </div>
      <div class="sh-card">
        <h3>Recent Service Jobs</h3><p class="sh-caption">Live records; nothing is invented.</p>
        <div v-if="data?.recent_jobs?.length" class="sh-jobs"><div v-for="j in data.recent_jobs" :key="j.name"><div><strong>{{j.name}}</strong><small>{{j.customer||'Customer not set'}}</small></div><span>{{j.status}}</span></div></div>
        <div v-else class="sh-empty">{{loading?'Loading recent jobs…':'No accessible service jobs yet.'}}</div>
        <h3 class="sh-ware-title">Stock Locations</h3>
        <div v-for="w in data?.warehouses||[]" :key="w.name" class="sh-warehouse"><span>{{w.name}}</span><small>{{w.enabled?'Available':'Disabled'}}</small></div>
        <div v-if="!data?.warehouses?.length" class="sh-empty">No warehouses available to this login.</div>
      </div>
    </div>
    <p v-for="warn in data?.warnings||[]" :key="warn" class="sh-warning">{{warn}} Open Settings to check permissions and shop configuration.</p>
  </section>
</template>
<style scoped>
.sh-root{background:#faf8f4;color:#483a2a;padding:26px clamp(18px,3vw,40px) 60px;min-height:100vh;box-sizing:border-box}
.sh-root *{box-sizing:border-box}.sh-head{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}.sh-head h1{font-size:30px;line-height:1.1;margin:5px 0 8px;font-weight:780;letter-spacing:-.03em}.sh-head p,.sh-caption{font-size:13px;color:#8b7b67;margin:0}.sh-kicker{font-size:10px;font-weight:850;letter-spacing:.15em;color:#a38867}.sh-outline{border:1px solid #e5d8c8;background:white;color:#644f34;border-radius:11px;padding:10px 14px;font-size:12px;font-weight:750;cursor:pointer}.sh-banner{border:1px solid #e9ddcc;background:linear-gradient(115deg,#fffcf6,#f0e5d3);border-radius:20px;padding:25px;display:flex;align-items:center;gap:18px}.sh-banner h2{font-size:20px;margin:5px 0}.sh-banner p{font-size:12px;color:#887661;margin:0}.sh-emblem{width:56px;height:56px;border-radius:16px;background:#6b543b;color:white;display:grid;place-items:center;font-size:30px}.sh-status{margin-left:auto;font-size:11px;border-radius:20px;background:#fff;padding:8px 12px;color:#806b4e;font-weight:700}.sh-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.sh-metrics article,.sh-card{background:#fff;border:1px solid #eae2d6;border-radius:16px;padding:20px}.sh-metrics span,.sh-metrics small{display:block;font-size:12px;color:#948673}.sh-metrics strong{display:block;font-size:30px;margin:9px 0;font-weight:800}.sh-metrics small{font-size:11px}.sh-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:16px}.sh-card h3{font-size:17px;font-weight:800;margin:0 0 7px}.sh-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:20px}.sh-actions button{display:flex;align-items:center;gap:10px;background:#fbf8f3;border:1px solid #e8ddce;border-radius:12px;text-align:left;padding:13px;cursor:pointer;color:inherit}.sh-actions button:hover{border-color:#bfa582;background:#f4eadc}.sh-actions button>span:nth-child(2){display:grid;gap:3px;flex:1}.sh-actions strong{font-size:12px}.sh-actions small{font-size:10px;color:#96836c}.sh-actions b{font-size:22px;color:#937759}.sh-icon{width:34px;height:34px;background:#ede0ce;border-radius:9px;display:grid;place-items:center;color:#71573b;font-size:20px}.sh-jobs{margin-top:14px}.sh-jobs>div{border-bottom:1px solid #eee8de;display:flex;justify-content:space-between;gap:12px;padding:11px 0;font-size:12px}.sh-jobs strong,.sh-jobs small{display:block}.sh-jobs small{color:#978672;margin-top:3px}.sh-jobs span{font-size:10px;color:#896943;font-weight:700}.sh-ware-title{margin-top:26px!important}.sh-warehouse{display:flex;justify-content:space-between;font-size:12px;padding:9px 0;border-bottom:1px solid #f2ece2}.sh-warehouse small{color:#8c7760}.sh-empty{background:#f9f6f0;border-radius:12px;padding:20px;font-size:12px;color:#9b8568;margin-top:15px}.sh-warning,.sh-alert{margin-top:14px;background:#fff0df;padding:12px;border-radius:10px;color:#81512b;font-size:12px}.sh-alert button{margin-left:12px;text-decoration:underline}@media(max-width:920px){.sh-grid{grid-template-columns:1fr}.sh-metrics{grid-template-columns:repeat(2,1fr)}}@media(max-width:570px){.sh-actions{grid-template-columns:1fr}.sh-head{align-items:flex-start}.sh-banner{padding:16px}.sh-status{display:none}}
</style>
