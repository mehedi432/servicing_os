<script setup>
// SERVICING_OS_CASH_UI_617B
import CashCollectionPanel from "./CashCollectionPanel.vue";

// AMCL_REPAIR_COMPLETED_616C
import { ref as amclRef } from 'vue';
const repairWorkspaceTab = amclRef('jobs');
// AMCL_REPAIR_BILLING_UI_616B
import RepairBillingPanel from "./RepairBillingPanel.vue";
// AMCL_QUICK_ASSIGN_615E1
import QuickAssignStockHub from "./QuickAssignStockHub.vue";
// SERVICING_WORKSTATION_614D
import TechnicianWorkstation from "./TechnicianWorkstation.vue";
import { ref, computed, onMounted } from "vue";

const emit = defineEmits(["close"]);

const statuses = [
  "Received",
  "Diagnosing",
  "Waiting for Parts",
  "Repairing",
  "Completed", "Ready to Deliver",
  "Delivered",
  "Cancelled"
];

const jobs = ref([]);
const selected = ref(null);
const selectedStatus = ref("All");
const search = ref("");
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const allowedStatuses = ref([]);

const form = ref({
  technician: "",
  diagnosis: "",
  estimated_cost: "",
  final_repair_cost: "",
  expected_delivery: "",
  remarks: "",
  status: ""
});

const filteredJobs = computed(() => jobs.value);

function csrfToken() {
  return window.frappe?.csrf_token ||
    window.csrf_token ||
    decodeURIComponent(
      document.cookie.split("; ")
        .find(x => x.startsWith("csrf_token="))
        ?.split("=").slice(1).join("=") || ""
    );
}

async function request(method, args = {}, post = false) {
  const url = new URL(
    "/api/method/servicing_os.api.lifecycle." + method,
    window.location.origin
  );

  const options = {
    method: post ? "POST" : "GET",
    credentials: "same-origin",
    headers: { "Accept": "application/json" }
  };

  if (post) {
    options.headers["Content-Type"] = "application/json";
    options.headers["X-Frappe-CSRF-Token"] = csrfToken();
    options.body = JSON.stringify(args);
  } else {
    Object.entries(args).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  const response = await fetch(url, options);
  const data = await response.json();

  if (!response.ok || data.exc || data.exc_type) {
    const message = data._server_messages
      ? (() => {
          try {
            const messages = JSON.parse(data._server_messages);
            const last = JSON.parse(messages[messages.length - 1]);
            return last.message;
          } catch {
            return null;
          }
        })()
      : null;

    throw new Error(
      message || data.message?.message ||
      data.exception || "Request failed"
    );
  }

  return data.message;
}

async function loadJobs() {
  loading.value = true;
  error.value = "";

  try {
    const result = await request("list_repair_jobs", {
      status: selectedStatus.value,
      search: search.value.trim(),
      limit: 100
    });

    jobs.value = result.jobs || [];
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function openJob(name) {
  error.value = "";
  success.value = "";

  try {
    const result = await request("get_repair_job", {
      job_name: name
    });

    selected.value = result.job;
    allowedStatuses.value = result.allowed_next_statuses || [];

    const job = result.job;

    form.value = {
      technician: job.technician || "",
      diagnosis: job.diagnosis || "",
      estimated_cost: job.estimated_cost ?? "",
      final_repair_cost: job.final_repair_cost ?? "",
      expected_delivery: job.expected_delivery
        ? String(job.expected_delivery).slice(0, 10) : "",
      remarks: job.remarks || "",
      status: job.status
    };
  } catch (e) {
    error.value = e.message;
  }
}

async function saveJob() {
  if (!selected.value || saving.value) return;

  saving.value = true;
  error.value = "";
  success.value = "";

  try {
    const payload = {
      job_name: selected.value.name,
      expected_modified: selected.value.modified,
      technician: form.value.technician,
      diagnosis: form.value.diagnosis,
      estimated_cost: form.value.estimated_cost,
      final_repair_cost: form.value.final_repair_cost,
      expected_delivery: form.value.expected_delivery,
      remarks: form.value.remarks,
      status: form.value.status
    };

    await request("update_repair_job", payload, true);

    success.value = "Repair information saved successfully.";

    await loadJobs();
    await openJob(payload.job_name);

    success.value = "Repair information saved successfully.";
  } catch (e) {
    error.value = e.message;
  } finally {
    saving.value = false;
  }
}

function statusClass(status) {
  if (status === "Delivered") return "bg-green-100 text-green-800";
  if (status === "Cancelled") return "bg-red-100 text-red-800";
  if (status === "Ready to Deliver") return "bg-emerald-100 text-emerald-800";
  if (status === "Repairing") return "bg-amber-100 text-amber-800";
  return "bg-stone-100 text-stone-700";
}

// SERVICING_TECHNICIAN_ROLE_614C
const technicians = ref([]);
const technicianLoading = ref(false);

async function loadTechnicians() {
  technicianLoading.value = true;

  try {
    const url = new URL(
      "/api/method/servicing_os.api.technicians.list_technicians",
      window.location.origin
    );

    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "application/json" }
    });

    const data = await response.json();

    if (!response.ok || data.exc || data.exc_type) {
      throw new Error(
        data.exception || "Unable to load technicians"
      );
    }

    technicians.value = data.message?.technicians || [];
  } catch (e) {
    error.value = e.message;
  } finally {
    technicianLoading.value = false;
  }
}

onMounted(() => {
  loadJobs();
  loadTechnicians();
});;
</script>

<template>
  <div class="repair-screen">
    
    <header class="repair-header">
      <div>
        <div class="repair-eyebrow">SERVICING OS / OPERATIONS</div>
        <h1>Repair Management</h1>
        <p>Manage diagnosis, technicians, repair progress and delivery.</p>
      </div>

      
      
    <div class="repair-header-actions-v3">
  <RepairBillingPanel />
<CashCollectionPanel />
  <button class="repair-close" type="button" @click="emit('close')">
        ← Back to workspace
      </button>
</div>
</header>

    <div v-if="error" class="repair-alert repair-error">{{ error }}</div>
    <div v-if="success" class="repair-alert repair-success">{{ success }}</div>

    <div class="repair-workspace-tabs-616c" role="tablist" aria-label="Repair workspace">
      <button type="button" role="tab" :aria-selected="repairWorkspaceTab==='jobs'"
        :class="{'active':repairWorkspaceTab==='jobs'}" @click="repairWorkspaceTab='jobs'">
        Service Jobs & Assignment
      </button>
      <button type="button" role="tab" :aria-selected="repairWorkspaceTab==='technicians'"
        :class="{'active':repairWorkspaceTab==='technicians'}" @click="repairWorkspaceTab='technicians'">
        Technician Workstation & Parts
      </button>
    </div>
    <TechnicianWorkstation v-if="repairWorkspaceTab==='technicians'" />
    <QuickAssignStockHub v-if="repairWorkspaceTab==='jobs'" />
    <div class="repair-layout" v-show="repairWorkspaceTab==='jobs'">
      <section class="repair-panel">
        <div class="repair-panel-heading">
          <h2>Service Jobs</h2>
          <span>{{ jobs.length }} shown</span>
        </div>

        <form class="repair-filters" @submit.prevent="loadJobs">
          <input
            v-model="search"
            placeholder="Job number, customer, mobile, serial..."
            aria-label="Search service jobs"
          />

          <select v-model="selectedStatus" aria-label="Filter by status">
            <option value="All">All statuses</option>
            <option v-for="status in statuses" :key="status" :value="status">
              {{ status }}
            </option>
          </select>

          <button type="submit" :disabled="loading">
            {{ loading ? "Loading..." : "Search / Refresh" }}
          </button>
        </form>

        <div class="repair-job-list">
          <button
            v-for="job in filteredJobs"
            :key="job.name"
            type="button"
            class="repair-job-row"
            :class="{ 'repair-job-selected': selected?.name === job.name }"
            @click="openJob(job.name)"
          >
            <span class="repair-job-title">
              <strong>{{ job.name }}</strong>
              <span :class="['repair-status', statusClass(job.status)]">
                {{ job.status }}
              </span>
            </span>

            <span class="repair-customer">{{ job.customer_name || "Customer unavailable" }}</span>
            <span class="repair-device">
              {{ [job.brand, job.device_model].filter(Boolean).join(" ") || job.device_type }}
            </span>
            <span class="repair-meta">
              {{ job.mobile || "No mobile" }}
              <span>{{ job.technician || "Unassigned" }}</span>
            </span>
          </button>

          <p v-if="!loading && !jobs.length" class="repair-empty">
            No matching Service Jobs found.
          </p>
        </div>
      </section>

      <section class="repair-panel">
        <template v-if="selected">
          <div class="repair-panel-heading">
            <div>
              <h2>{{ selected.name }}</h2>
              <p>{{ selected.customer_name }} · {{ selected.mobile }}</p>
            </div>
            <span :class="['repair-status', statusClass(selected.status)]">
              {{ selected.status }}
            </span>
          </div>

          <div class="repair-device-summary">
            <strong>{{ selected.brand }} {{ selected.device_model }}</strong>
            <p>{{ selected.reported_problem || "No reported problem" }}</p>
          </div>

          <form class="repair-edit-form" @submit.prevent="saveJob">
            <label>
              <span>Assign Technician (Service Technician role)</span>
              <select
  v-model="form.technician"
  :disabled="technicianLoading"
>
  <option value="">Unassigned</option>

  <option
    v-if="form.technician &&
      !technicians.some(t => t.value === form.technician)"
    :value="form.technician"
    disabled
  >
    {{ form.technician }} (not eligible)
  </option>

  <option
    v-for="technician in technicians"
    :key="technician.value"
    :value="technician.value"
  >
    {{ technician.label }} — {{ technician.email }}
  </option>
</select>
            </label>

            <label>
              <span>Next Status</span>
              <select v-model="form.status" aria-label="Repair status">
                <option :value="selected.status">{{ selected.status }} (current)</option>
                <option
                  v-for="status in statuses.filter(s => s !== 'All' && s !== selected.status)"
                  :key="status" :value="status"
                  :disabled="!allowedStatuses.includes(status)"
                >
                  {{ status }}{{ allowedStatuses.includes(status) ? ' — available' : ' — later / restricted' }}
                </option>
              </select>
            </label>

            <label class="repair-wide">
              <span>Diagnosis</span>
              <textarea
                v-model="form.diagnosis"
                rows="4"
                placeholder="Technician inspection findings..."
              ></textarea>
            </label>

            <label>
              <span>Estimated Cost (BDT)</span>
              <input v-model="form.estimated_cost" type="number" min="0" step="0.01" />
            </label>

            <label>
              <span>Final Repair Cost (BDT)</span>
              <input v-model="form.final_repair_cost" type="number" min="0" step="0.01" />
            </label>

            <label>
              <span>Expected Delivery</span>
              <input v-model="form.expected_delivery" type="date" />
            </label>

            <label class="repair-wide">
              <span>Repair Notes</span>
              <textarea v-model="form.remarks" rows="3"></textarea>
            </label>

            <div class="repair-wide repair-actions">
              <button type="submit" :disabled="saving">
                {{ saving ? "Saving..." : "Save Repair Update" }}
              </button>
            </div>
          </form>
        </template>

        <div v-else class="repair-empty repair-select-prompt">
          Select a Service Job to view and update its repair information.
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.repair-screen {
  position: relative;
  
  
  overflow-y: auto;
  background: #f8f6f0;
  color: #514635;
  padding: 24px;
}
.repair-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  max-width: 1500px;
  margin: 0 auto 24px;
}
.repair-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.4px;
  color: #a28a67;
}
.repair-header h1 {
  font-size: 27px;
  font-weight: 750;
  margin: 5px 0;
}
.repair-header p, .repair-panel-heading p {
  font-size: 13px;
  color: #8b7e6c;
}
.repair-close {
  background: #fffdf8;
  border: 1px solid #e2d7c7;
  padding: 12px 17px;
  border-radius: 12px;
  font-weight: 600;
}
.repair-layout {
  display: grid;
  grid-template-columns: minmax(310px, 0.9fr) minmax(0, 1.4fr);
  gap: 18px;
  max-width: 1500px;
  margin: auto;
}
.repair-panel {
  background: #fffdf9;
  border: 1px solid #e8dfd1;
  border-radius: 17px;
  padding: 20px;
  min-width: 0;
  box-shadow: 0 5px 8px #51402b08, 0 8px 13px #51402b06;
}
.repair-panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.repair-panel-heading h2 {
  font-weight: 750;
  font-size: 17px;
}
.repair-panel-heading > span {
  font-size: 12px;
  color: #8b7e6c;
}
.repair-filters {
  display: grid;
  gap: 10px;
  margin-bottom: 15px;
}
.repair-filters input, .repair-filters select,
.repair-edit-form input, .repair-edit-form select,
.repair-edit-form textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid #e2d7c7;
  background: #fffefa;
  border-radius: 10px;
  padding: 11px 12px;
  font-size: 13px;
  color: #514635;
}
.repair-filters button, .repair-actions button {
  background: #756247;
  color: white;
  border-radius: 11px;
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 700;
}
.repair-filters button:disabled, .repair-actions button:disabled {
  opacity: .55;
}
.repair-job-list {
  max-height: 65vh;
  overflow-y: auto;
}
.repair-job-row {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid #ece4d8;
  background: #fffefa;
  border-radius: 12px;
  padding: 13px;
  margin-bottom: 9px;
}
.repair-job-row:hover, .repair-job-selected {
  background: #f3eadb;
  border-color: #d3bea1;
}
.repair-job-title, .repair-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.repair-job-title strong {
  font-size: 13px;
  overflow-wrap: anywhere;
}
.repair-status {
  display: inline-block;
  padding: 5px 8px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}
.repair-customer {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-top: 9px;
}
.repair-device, .repair-meta {
  display: block;
  font-size: 12px;
  color: #887b69;
  margin-top: 5px;
}
.repair-meta {
  display: flex;
}
.repair-device-summary {
  background: #f7f1e7;
  border: 1px solid #e7dac8;
  padding: 15px;
  border-radius: 12px;
  margin-bottom: 18px;
}
.repair-device-summary p {
  font-size: 13px;
  margin-top: 6px;
}
.repair-edit-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 15px;
}
.repair-edit-form label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 12px;
  font-weight: 650;
}
.repair-wide {
  grid-column: 1 / -1;
}
.repair-actions {
  display: flex;
  justify-content: flex-end;
}
.repair-alert {
  max-width: 1500px;
  margin: 0 auto 14px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 13px;
}
.repair-error { background: #fee8e6; color: #9c322d; }
.repair-success { background: #e5f3e7; color: #276e3a; }
.repair-empty {
  text-align: center;
  padding: 35px 15px;
  color: #918471;
  font-size: 13px;
}
.repair-select-prompt { padding: 85px 15px; }
@media (max-width: 900px) {
  .repair-layout { grid-template-columns: 1fr; }
  .repair-job-list { max-height: 320px; }
}
@media (max-width: 540px) {
  .repair-screen { padding: 12px; }
  .repair-header h1 { font-size: 22px; }
  .repair-panel { padding: 14px; }
  .repair-edit-form { grid-template-columns: 1fr; }
  .repair-wide { grid-column: auto; }
}
</style>

<style>
/* AMCL_BILLING_MODAL_V3_616B3: repair header alignment */
.repair-screen .repair-header {
  display: flex !important; align-items: center !important;
  justify-content: space-between !important; gap: 16px !important;
  padding-bottom: 18px !important; margin-bottom: 20px !important;
  border-bottom: 1px solid #e7ddcf !important;
}
.repair-screen .repair-header-actions-v3 {
  display: flex; align-items: center; justify-content: flex-end;
  flex-wrap: wrap; gap: 10px; margin-left: auto;
}
.repair-screen .repair-header-actions-v3 .repair-close {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 40px; margin: 0; padding: 10px 15px;
  border: 1px solid #ded6c9; border-radius: 11px;
  background: #fffdf9; color: #685a48; font-size: 12px; font-weight: 700;
  position: static !important; transform: none !important;
}
.repair-screen .repair-header-actions-v3 .repair-close:hover { background:#f2ede5; }
@media(max-width:620px) {
  .repair-screen .repair-header { align-items:flex-start !important; }
  .repair-screen .repair-header-actions-v3 { width:100%; justify-content:flex-start; margin-left:0; }
}
</style>

<style scoped>
/* AMCL_REPAIR_COMPLETED_616C: clean two-view repair workflow */
.repair-workspace-tabs-616c{display:flex;gap:6px;flex-wrap:wrap;background:#eee6da;border:1px solid #e7dccd;border-radius:14px;padding:5px;margin-bottom:18px}
.repair-workspace-tabs-616c button{flex:1 1 170px;padding:13px 15px;border:1px solid transparent;border-radius:10px;color:#79654b;font-size:13px;font-weight:750;text-align:center;cursor:pointer}
.repair-workspace-tabs-616c button.active{background:#fffdf9;border-color:#e0d4c2;color:#5f492e;box-shadow:0 2px 6px #54412c11}
.repair-workspace-tabs-616c button:focus-visible{outline:2px solid #ae8552;outline-offset:1px}
</style>
