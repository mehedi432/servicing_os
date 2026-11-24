<script setup>
import { ref } from 'vue'
import PartyDirectory from './PartyDirectory.vue'
import CustomerAddressFields from './CustomerAddressFields.vue'
import PartyDialog from './PartyDialog.vue'
import PartyProfile from './PartyProfile.vue'
import PartySplit from './PartySplit.vue'

const directory = ref(null)
const selected = ref(null)
const split = ref(null)
const config = ref(null)
const saving = ref(false)
const error = ref('')
const success = ref('')
const showNew = ref(false)
const form = ref({ name: '', mobile: '', group: '', address: {} })

function selectCustomer(row) {
  selected.value = row
  split.value?.revealProfile()
}

async function openNew() {
  error.value = ''
  success.value = ''
  showNew.value = true
  try {
    if (!config.value) {
      const response = await fetch('/api/method/servicing_os.api.counter_customers.get_customer_config', {
        credentials: 'same-origin', headers: { Accept: 'application/json' },
      })
      const data = await response.json()
      if (!response.ok || !data.message) throw new Error(data.exception || 'Customer setup unavailable.')
      config.value = data.message
    }
    form.value = {
      name: '', mobile: '', group: config.value.default_group || '',
      address: {},
    }
  } catch (err) {
    error.value = err.message
  }
}

async function saveCustomer() {
  saving.value = true
  error.value = ''
  try {
    const cookie = document.cookie.split('; ').find(value => value.startsWith('csrf_token='))?.slice(11)
    const csrf = window.frappe?.csrf_token || window.csrf_token || (cookie ? decodeURIComponent(cookie) : '')
    const response = await fetch('/api/method/servicing_os.api.counter_customers.create_counter_customer', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Frappe-CSRF-Token': csrf },
      body: JSON.stringify({
        customer_name: form.value.name, mobile_no: form.value.mobile,
        customer_group: form.value.group, ...form.value.address,
      }),
    })
    const data = await response.json()
    if (!response.ok || !data.message?.customer) {
      let message = data.exception || 'Unable to save Customer.'
      try {
        const messages = JSON.parse(data._server_messages || '[]')
        if (messages.length) message = JSON.parse(messages[messages.length - 1]).message || message
      } catch {}
      throw new Error(message)
    }
    const customer = data.message.customer
    showNew.value = false
    success.value = `Customer ${customer.customer_name} saved.`
    directory.value?.refresh()
    selectCustomer({ name: customer.name, display_name: customer.customer_name, mobile: form.value.mobile, group: form.value.group })
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

</script>

<template>
  <section class="sos-ext-root customer-workspace">
    <PartySplit ref="split" heading="Customer 360" hint="Select a customer to see balances, ledger entries and activity." :selected="!!selected">
      <template #directory>
        <PartyDirectory ref="directory" doctype="Customer" :selected="selected?.name" @create="openNew" @open="selectCustomer">
          <template #notices><p v-if="success" class="ex-alert ex-success directory-notice" role="status">{{ success }}</p></template>
        </PartyDirectory>
      </template>
      <PartyProfile v-if="selected" :key="selected.name" type="Customer" :record="selected" />
    </PartySplit>
    <PartyDialog v-if="showNew" title="New Customer" wide :busy="saving" @close="showNew = false">
      <p v-if="error" class="ex-alert ex-error" role="alert">{{ error }}</p>
      <p v-else-if="!config" role="status">Loading customer setup…</p>
      <form v-if="config" class="party-entry" @submit.prevent="saveCustomer">
        <fieldset class="party-entry-group party-entry-fields" :disabled="saving">
          <legend>Customer details</legend>
          <label>Customer name<input v-model="form.name" required maxlength="120" placeholder="Full name" /></label>
          <label>Mobile number<input v-model="form.mobile" required type="tel" placeholder="01XXXXXXXXX" /></label>
          <label>Customer group<select v-model="form.group" required><option value="">Choose group</option><option v-for="group in config.groups" :key="group">{{ group }}</option></select></label>
        </fieldset>
        <fieldset class="party-entry-group" :disabled="saving">
          <legend>Billing address</legend>
          <CustomerAddressFields v-model="form.address" />
        </fieldset>
        <div class="party-entry-actions">
          <button type="button" class="ex-secondary" :disabled="saving" @click="showNew = false">Cancel</button>
          <button type="submit" class="ex-primary" :disabled="saving || !config.can_create">{{ saving ? 'Saving…' : 'Save Customer' }}</button>
        </div>
      </form>
    </PartyDialog>
  </section>
</template>

<style scoped src="./extensionStyle.css"></style>
<style scoped src="./partyEntry.css"></style>
<style scoped>
.directory-notice{margin:12px}
</style>
