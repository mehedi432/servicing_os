<script setup>
import {ref,onMounted,computed} from 'vue';
import {moduleApi} from './extensionApi.js';
const data=ref({shops:[],users:[],role:'Service Technician'});
const busy=ref(false);const error=ref('');const success=ref('');const filter=ref('');
const pending=ref(null);
const staff=computed(()=>data.value.users.filter(u=>(u.full_name+' '+u.name).toLowerCase().includes(filter.value.toLowerCase())));
async function refresh(){busy.value=true;error.value='';try{data.value=await moduleApi('get_shop_access_settings');}catch(e){error.value=e.message;}finally{busy.value=false;}}
async function change(){if(!pending.value)return;busy.value=true;error.value='';success.value='';try{const r=await moduleApi('set_service_technician_role',{user_id:pending.value.name,enabled:!pending.value.technician},true);pending.value=null;await refresh();success.value=`Access updated for ${r.user}.`;}catch(e){error.value=e.message;pending.value=null;}finally{busy.value=false;}}
onMounted(refresh);
</script>
<template>
  <section class="sos-ext-root sos-settings">
    <header class="ex-heading"><div><div class="ex-kicker">OWNER / ADMINISTRATION</div><h1>Settings</h1><p>Shop configuration and staff access—no need to leave SERVICING OS.</p></div><button class="ex-secondary" @click="refresh" :disabled="busy">Refresh</button></header>
    <div v-if="error" class="ex-alert ex-error" role="alert">{{error}}</div><div v-if="success" class="ex-alert ex-success" role="status">{{success}}</div>
    <div class="ex-panel"><div class="ex-panel-top"><div><h2>Shop & Warehouse Configuration</h2><p class="ex-muted">The live configuration, displayed safely without changing accounting defaults.</p></div><span class="ex-tag">BDT</span></div>
      <div v-if="data.shops?.length" class="ex-config-grid"><article v-for="shop in data.shops" :key="shop.name"><h3>{{shop.shop_name||shop.name}}</h3><div><span>Company</span><strong>{{shop.company}}</strong></div><div><span>Retail stock</span><strong>{{shop.retail_warehouse}}</strong></div><div><span>Used laptops</span><strong>{{shop.used_laptop_warehouse}}</strong></div><div><span>Spare parts</span><strong>{{shop.spare_parts_warehouse}}</strong></div><div><span>Status</span><strong>{{shop.is_active?'Active':'Inactive'}}</strong></div></article></div><p v-else class="ex-empty-small">No accessible Servicing Shop records.</p>
      <p class="ex-muted">Warehouse/account defaults are shown read-only because changing them without updating checkout and stock rules could mispost transactions.</p>
    </div>
    <div class="ex-panel ex-settings-roles"><div class="ex-panel-top"><div><h2>Service Technician Access</h2><p class="ex-muted">Assign or remove the technician role while preserving every other user role.</p></div><input class="ex-filter" v-model="filter" placeholder="Find staff by name or email" aria-label="Find staff"></div>
      <div v-if="!data.can_manage_roles" class="ex-alert ex-error">Your account cannot edit user roles.</div>
      <div class="ex-scroll"><table class="ex-table"><thead><tr><th>User</th><th>Account ID</th><th>Service Technician</th><th>Action</th></tr></thead><tbody><tr v-for="u in staff" :key="u.name"><td><strong>{{u.full_name||u.name}}</strong></td><td class="ex-monospace">{{u.name}}</td><td><span class="ex-tag" :class="{'ex-tag-good':u.technician}">{{u.technician?'Assigned':'Not assigned'}}</span></td><td><button v-if="u.name!=='Administrator'" type="button" class="ex-small-primary" :disabled="!data.can_manage_roles || busy" @click="pending=u">{{u.technician?'Remove Technician Role':'Assign Technician Role'}}</button><span v-else class="ex-muted">Protected</span></td></tr><tr v-if="!staff.length"><td colspan="4" class="ex-empty">No matching staff.</td></tr></tbody></table></div>
      <p class="ex-muted ex-under">Changing a role changes real access immediately. It does not create, enable or disable accounts.</p>
    </div>
    <div class="ex-modal-shade" v-if="pending" @click.self="pending=null"><div class="ex-modal"><div class="ex-modal-header"><h2>Confirm Technician Access</h2><button class="ex-close" @click="pending=null">×</button></div>
      <p>{{pending.technician?'Remove':'Assign'}} <strong>Service Technician</strong> role {{pending.technician?'from':'to'}} <strong>{{pending.full_name||pending.name}}</strong>?</p><p class="ex-muted">All of this user's other roles and permissions will be preserved.</p><div class="ex-modal-actions"><button class="ex-secondary" @click="pending=null">Cancel</button><button class="ex-primary" :disabled="busy" @click="change">{{busy?'Saving...':'Confirm Change'}}</button></div></div></div>
  </section>
</template>
<style scoped src="./extensionStyle.css"></style>
