<script setup>
import { computed, ref } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import CustomerAddressFields from './CustomerAddressFields.vue'
import { servicingApi } from './extensionApi.js'
import PartyDirectory from './PartyDirectory.vue'
import PartyDialog from './PartyDialog.vue'
import PartyProfile from './PartyProfile.vue'
import PartySplit from './PartySplit.vue'

const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const directory = ref(null)
const groups = ref(null)
const form = ref(null)
const profile = ref(null)
const split = ref(null)
const loadingGroups = ref(false)
const loadingAddress = ref(false)
const addressLoaded = ref(false)
const canEditAddress = ref(false)
const profileVersion = ref(0)
const api = (method, args, write = false) => servicingApi('supplier_directory', method, args, write)
let formVersion = 0
const saving = ref(false)
const error = ref('')
const notice = ref('')
const title = computed(() => !form.value?.name ? tr('New Supplier', 'নতুন সরবরাহকারী') :
  tr('Edit Supplier', 'সরবরাহকারী পরিবর্তন'))

function errorText(data, fallback) {
  try {
    const entries = JSON.parse(data._server_messages || '[]')
    if (entries.length) return JSON.parse(entries[0]).message || fallback
  } catch {}
  return data.exception || fallback
}

async function loadGroups() {
  if (groups.value || loadingGroups.value) return
  loadingGroups.value = true
  try {
    const params = new URLSearchParams({
      fields: JSON.stringify(['name']), filters: JSON.stringify({ is_group: 0 }),
      limit_page_length: '200', order_by: 'name asc',
    })
    const response = await fetch('/api/resource/Supplier Group?' + params, {credentials:'same-origin', headers:{Accept:'application/json'}})
    const body = await response.json()
    if (!response.ok) throw new Error(errorText(body, 'Supplier groups are unavailable.'))
    groups.value = body.data.map(group => group.name)
    if (groups.value.length === 1 && form.value && !form.value.supplier_group) {
      form.value.supplier_group = groups.value[0]
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loadingGroups.value = false
  }
}

function selectSupplier(row, canEdit) {
  profile.value = { row, canEdit }
  split.value?.revealProfile()
}

function closeForm() {
  formVersion++
  form.value = null
}
async function open(row = null) {
  const version = ++formVersion
  form.value = {
    name: row?.name || '',
    supplier_name: row?.display_name || row?.name || '',
    supplier_group: row?.group || (groups.value?.length === 1 ? groups.value[0] : ''),
    supplier_type: row?.type || 'Company',
    mobile_no: row?.mobile || '',
    email_id: row?.email || '',
    address: {},
  }
  error.value = ''
  notice.value = ''
  loadingAddress.value = true
  addressLoaded.value = false
  canEditAddress.value = false
  loadGroups()
  try {
    const data = await api('get_supplier_form', { name: form.value.name })
    if (version !== formVersion) return
    form.value.address = data.address
    canEditAddress.value = data.can_edit_address
    addressLoaded.value = true
  } catch (err) {
    if (version === formVersion) error.value = err.message
  } finally {
    if (version === formVersion) loadingAddress.value = false
  }
}

const groupOptions = computed(() => {
  const options = groups.value || []
  const selected = form.value?.supplier_group
  return selected && !options.includes(selected) ? [selected, ...options] : options
})

async function save() {
  const { name, ...payload } = form.value
  payload.supplier_name = payload.supplier_name.trim()
  if (!payload.supplier_name || !payload.supplier_group) {
    error.value = tr('Supplier name and group are required.', 'সরবরাহকারীর নাম ও গ্রুপ আবশ্যক।')
    return
  }
  if (saving.value || !addressLoaded.value || (!name && !canEditAddress.value)) return
  saving.value = true
  error.value = ''
  try {
    if (!canEditAddress.value) delete payload.address
    const saved = await api('save_supplier', {data: { name, ...payload }}, true)
    profileVersion.value++
    selectSupplier({ name: saved.name, display_name: saved.supplier_name, group: saved.supplier_group,
      type: saved.supplier_type, mobile: saved.mobile_no, email: saved.email_id }, saved.can_edit)
    closeForm()
    notice.value = tr('Supplier saved.', 'সরবরাহকারী সংরক্ষিত হয়েছে।')
    directory.value?.refresh()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="sos-ext-root">
    <PartySplit ref="split" heading="Supplier 360" hint="Select a supplier to see balances, purchases and payments." :selected="!!profile">
      <template #directory>
        <PartyDirectory ref="directory" doctype="Supplier" :selected="profile?.row.name" @create="open()" @open="selectSupplier">
          <template #notices><p v-if="notice" class="ex-alert ex-success directory-notice" role="status">{{ notice }}</p></template>
        </PartyDirectory>
      </template>
      <PartyProfile v-if="profile" :key="profile.row.name + profileVersion" type="Supplier" :record="profile.row" :can-edit="profile.canEdit"
        @edit="open(profile.row)" />
    </PartySplit>
    <PartyDialog v-if="form" :title="title" wide :busy="saving" :close-label="tr('Close', 'বন্ধ করুন')" @close="closeForm">
      <p v-if="error" class="ex-alert ex-error" role="alert">{{ error }}</p>
      <p v-if="loadingGroups" role="status">{{ tr('Loading supplier groups…', 'সরবরাহকারী গ্রুপ লোড হচ্ছে…') }}</p>
      <form class="party-entry" @submit.prevent="save">
        <fieldset class="party-entry-group party-entry-fields" :disabled="saving">
          <legend>{{ tr('Supplier details', 'সরবরাহকারীর তথ্য') }}</legend>
          <label>{{ tr('Supplier name', 'সরবরাহকারীর নাম') }}<input v-model="form.supplier_name" required maxlength="140" /></label>
          <label>{{ tr('Supplier group', 'সরবরাহকারী গ্রুপ') }}
            <select v-model="form.supplier_group" required>
              <option value="">{{ tr('Select group', 'গ্রুপ নির্বাচন করুন') }}</option>
              <option v-for="group in groupOptions" :key="group">{{ group }}</option>
            </select>
          </label>
          <label>{{ tr('Supplier type', 'সরবরাহকারীর ধরন') }}
            <select v-model="form.supplier_type">
              <option value="Company">{{ tr('Company', 'প্রতিষ্ঠান') }}</option>
              <option value="Individual">{{ tr('Individual', 'ব্যক্তি') }}</option>
              <option v-if="!['Company', 'Individual'].includes(form.supplier_type)">{{ form.supplier_type }}</option>
            </select>
          </label>
          <label>{{ tr('Mobile number', 'মোবাইল নম্বর') }}<input v-model="form.mobile_no" type="tel" /></label>
          <label class="supplier-email">{{ tr('Email address', 'ইমেইল ঠিকানা') }}<input v-model="form.email_id" type="email" /></label>
        </fieldset>
        <fieldset class="party-entry-group" :disabled="saving || loadingAddress">
          <legend>{{ tr('Billing address', 'বিলিং ঠিকানা') }}</legend>
          <p v-if="loadingAddress" class="party-entry-note" role="status">{{ tr('Loading address…', 'ঠিকানা লোড হচ্ছে…') }}</p>
          <CustomerAddressFields v-else-if="addressLoaded && (canEditAddress || form.address.address_line1)"
            v-model="form.address" supplier :readonly="!canEditAddress" />
          <p v-if="addressLoaded && !canEditAddress" class="party-entry-note">{{ tr('Address permission is required to enter or change this address.', 'ঠিকানা লিখতে বা বদলাতে অনুমতি প্রয়োজন।') }}</p>
        </fieldset>
        <div class="party-entry-actions">
          <button type="button" class="ex-secondary" :disabled="saving" @click="closeForm">{{ tr('Cancel', 'বাতিল') }}</button>
          <button type="submit" class="ex-primary" :disabled="saving || loadingGroups || !addressLoaded || (!form.name && !canEditAddress)">{{ saving ? tr('Saving…', 'সংরক্ষণ হচ্ছে…') : tr('Save Supplier', 'সংরক্ষণ করুন') }}</button>
        </div>
      </form>
    </PartyDialog>
  </section>
</template>

<style scoped src="./extensionStyle.css"></style>
<style scoped src="./partyEntry.css"></style>
<style scoped>
.directory-notice{margin:12px}
.supplier-email{grid-column:1/-1}
</style>
