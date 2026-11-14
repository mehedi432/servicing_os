<script setup>
import { computed, onMounted, ref } from 'vue';
import { getShopConfig, receiveServiceJob } from '../api/frappe.js';

const emit = defineEmits(['close', 'created']);
const shop = ref(null);
const loadingShop = ref(true);
const saving = ref(false);
const error = ref('');
const createdJob = ref('');
const form = ref({
  customer_name: '', mobile: '', device_type: 'Laptop', brand: '',
  device_model: '', serial_number: '', reported_problem: '',
  accessories_received: '', priority: 'Normal', estimated_cost: '',
});
const canSave = computed(() => !loadingShop.value && !!shop.value?.name && !saving.value);

onMounted(async () => {
  try {
    shop.value = await getShopConfig();
    if (!shop.value?.name) throw new Error('সক্রিয় শপ সেটআপ পাওয়া যায়নি।');
  } catch (e) {
    error.value = e?.message || 'শপ সেটআপ লোড করা যায়নি।';
  } finally {
    loadingShop.value = false;
  }
});

async function save() {
  if (!canSave.value || createdJob.value) return;
  error.value = '';
  saving.value = true;
  try {
    const result = await receiveServiceJob({
      ...form.value,
      shop: shop.value.name,
      customer_name: form.value.customer_name.trim(),
      mobile: form.value.mobile.trim(),
      reported_problem: form.value.reported_problem.trim(),
      estimated_cost: Number(form.value.estimated_cost || 0),
    });
    const id = result?.service_job;
    if (!id) throw new Error('জব নম্বর সার্ভার থেকে আসেনি।');
    createdJob.value = id;
    emit('created', id);
  } catch (e) {
    error.value = e?.message || 'সার্ভিস জব তৈরি করা যায়নি।';
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="s41-shade" role="presentation" @click.self="emit('close')">
    <section class="s41-dialog" role="dialog" aria-modal="true" aria-labelledby="s41-title">
      <header class="s41-head">
        <div>
          <p class="s41-eyebrow">SERVICING OS · DAILY OPERATIONS</p>
          <h2 id="s41-title">নতুন সার্ভিস জব</h2>
          <p class="s41-sub">Receive Computer · একই স্ক্রিনে সার্ভিস রেজিস্ট্রেশন</p>
        </div>
        <button type="button" class="s41-close" aria-label="Close" @click="emit('close')">×</button>
      </header>

      <div v-if="createdJob" class="s41-success" role="status">
        <strong>সার্ভিস জব সফলভাবে তৈরি হয়েছে।</strong>
        <div class="s41-job-number">{{ createdJob }}</div>
        <p>এই জবটি Service Jobs তালিকায় থাকবে। তালিকা নতুন করে লোড করতে প্রয়োজনে Refresh চাপুন।</p>
        <button type="button" class="s41-primary" @click="emit('close')">বন্ধ করুন</button>
      </div>
      <form v-else class="s41-form" @submit.prevent="save">
        <p v-if="error" class="s41-error" role="alert">{{ error }}</p>
        <p v-if="loadingShop" class="s41-help">শপ সেটআপ লোড হচ্ছে…</p>
        <div class="s41-grid">
          <label>কাস্টমারের নাম <b>*</b><input v-model="form.customer_name" required maxlength="140" autocomplete="name" placeholder="Customer name" /></label>
          <label>মোবাইল নম্বর <b>*</b><input v-model="form.mobile" required maxlength="30" type="tel" autocomplete="tel" placeholder="01XXXXXXXXX" /></label>
          <label>ডিভাইসের ধরন <b>*</b>
            <select v-model="form.device_type" required>
              <option value="Laptop">Laptop</option><option value="Desktop">Desktop</option>
              <option value="Monitor">Monitor</option><option value="Printer">Printer</option>
              <option value="Other">Other</option>
            </select>
          </label>
          <label>ব্র্যান্ড<input v-model="form.brand" maxlength="100" placeholder="Dell, HP, Apple…" /></label>
          <label>মডেল<input v-model="form.device_model" maxlength="120" placeholder="Model" /></label>
          <label>সিরিয়াল নম্বর<input v-model="form.serial_number" maxlength="140" placeholder="Serial / IMEI" /></label>
          <label class="s41-wide">সমস্যার বিস্তারিত <b>*</b><textarea v-model="form.reported_problem" required rows="3" placeholder="সমস্যাটি সম্পূর্ণ লিখুন"></textarea></label>
          <label class="s41-wide">সাথে পাওয়া জিনিসপত্র<textarea v-model="form.accessories_received" rows="2" placeholder="চার্জার, ব্যাগ, কেবল…"></textarea></label>
          <label>অগ্রাধিকার<select v-model="form.priority"><option value="Normal">Normal</option><option value="High">High</option><option value="Urgent">Urgent</option></select></label>
          <label>সম্ভাব্য খরচ (৳)<input v-model="form.estimated_cost" min="0" step="0.01" type="number" placeholder="0.00" /></label>
        </div>
        <footer class="s41-actions">
          <button type="button" class="s41-secondary" @click="emit('close')">বাতিল</button>
          <button type="submit" class="s41-primary" :disabled="!canSave">{{ saving ? 'সেভ হচ্ছে…' : 'সার্ভিস জব তৈরি করুন' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
.s41-shade{position:fixed;inset:0;z-index:9999;display:flex;justify-content:center;align-items:center;padding:20px;background:rgba(36,31,24,.5);backdrop-filter:blur(3px)}
.s41-dialog{width:min(760px,100%);max-height:94vh;overflow:auto;background:#fcfaf6;color:#302c27;border:1px solid #e9e2d7;border-radius:18px;box-shadow:0 24px 80px rgba(28,24,19,.2);font:inherit}
.s41-head{display:flex;justify-content:space-between;gap:15px;align-items:start;padding:24px 27px 18px;border-bottom:1px solid #e9e2d7}
.s41-eyebrow{margin:0 0 7px;color:#937b59;font-size:10px;letter-spacing:.12em;font-weight:800}
.s41-head h2{margin:0;font-size:23px;font-weight:750}.s41-sub{margin:5px 0 0;color:#8c8378;font-size:12px}
.s41-close{border:1px solid #e5ddd2;border-radius:10px;background:#fffdf9;color:#665a4c;font-size:24px;cursor:pointer;width:37px;height:37px;line-height:1}
.s41-form{padding:21px 27px 26px}.s41-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.s41-grid label{display:block;color:#584e42;font-size:12px;font-weight:700}.s41-grid b{color:#a14c38}
.s41-grid input,.s41-grid select,.s41-grid textarea{display:block;width:100%;box-sizing:border-box;background:#fffefb;color:#332f29;border:1px solid #e1d8ca;border-radius:9px;padding:11px 12px;margin-top:7px;font:inherit;font-size:13px;outline:0;resize:vertical}
.s41-grid input:focus,.s41-grid select:focus,.s41-grid textarea:focus{border-color:#ad956f;box-shadow:0 0 0 3px #ad956f1e}
.s41-wide{grid-column:1/-1}.s41-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:22px}
.s41-actions button,.s41-success button{border-radius:9px;border:1px solid #d7ccbc;padding:11px 18px;font:inherit;font-size:13px;font-weight:700;cursor:pointer}
.s41-primary{background:#42382d;color:#fff;border-color:#42382d!important}.s41-primary:disabled{opacity:.55;cursor:not-allowed}.s41-secondary{background:#fffdf9;color:#4e453a}
.s41-error{padding:12px;margin:0 0 16px;border-radius:8px;background:#fff0ed;color:#9c4234;font-size:13px}.s41-help{font-size:12px;color:#806d55}
.s41-success{padding:28px;display:flex;flex-direction:column;align-items:start;gap:15px}.s41-success strong{font-size:19px}.s41-success p{font-size:13px;color:#756a5b}.s41-job-number{padding:11px 15px;border:1px solid #d6c6ad;border-radius:9px;font-size:16px;font-weight:800;background:#f7f1e8}
@media(max-width:600px){.s41-shade{padding:7px}.s41-dialog{max-height:96vh}.s41-head{padding:18px}.s41-form{padding:18px}.s41-grid{grid-template-columns:1fr}.s41-wide{grid-column:auto}}
</style>
