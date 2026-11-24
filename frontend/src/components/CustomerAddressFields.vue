<script setup>
import { currentLanguage } from '../i18n/servicingLanguage.js'

defineProps({ supplier: Boolean, readonly: Boolean })
const tr = (en, bn) => currentLanguage.value === 'bn' ? bn : en
const address = defineModel({ type: Object, required: true })
</script>

<template>
  <div class="customer-address-fields">
    <label class="customer-address-line">
      {{ supplier ? tr('Supplier address', 'সরবরাহকারীর ঠিকানা') : tr('Customer address', 'গ্রাহকের ঠিকানা') }}
      <input v-model.trim="address.address_line1" autocomplete="address-line1" maxlength="140"
         :readonly="readonly" :required="!readonly" :placeholder="tr('House, road or village', 'বাড়ি, রাস্তা বা গ্রাম')" />
    </label>
    <label v-if="supplier" class="customer-address-line">
      {{ tr('Address line 2 (optional)', 'ঠিকানার দ্বিতীয় লাইন (ঐচ্ছিক)') }}
      <input v-model.trim="address.address_line2" autocomplete="address-line2" maxlength="140" :readonly="readonly" />
    </label>
    <label>
      {{ tr('City / Upazila', 'শহর / উপজেলা') }}
      <input v-model.trim="address.city" autocomplete="address-level2" maxlength="140" :readonly="readonly" :required="!readonly" />
    </label>
    <label v-if="supplier">
      {{ tr('District (optional)', 'জেলা (ঐচ্ছিক)') }}
      <input v-model.trim="address.state" autocomplete="address-level1" maxlength="140" :readonly="readonly" />
    </label>
    <label>
      {{ tr('Postal code (optional)', 'পোস্ট কোড (ঐচ্ছিক)') }}
      <input v-model.trim="address.pincode" autocomplete="postal-code" maxlength="20" :readonly="readonly" />
    </label>
  </div>
</template>

<style scoped>
.customer-address-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;grid-column:1/-1}
.customer-address-line{grid-column:1/-1}
.customer-address-fields label{display:grid;gap:4px;min-width:0;font-size:.78rem;font-weight:650}
.customer-address-fields input{box-sizing:border-box;min-width:0;width:100%;min-height:40px;padding:8px 10px;border:1px solid var(--os-border,#e5d6c4);border-radius:7px;background:var(--os-surface,#fffdf9);color:var(--os-ink,#39291f)}
.customer-address-fields input:focus-visible{outline:2px solid var(--os-accent,#855d43);outline-offset:1px}
</style>
