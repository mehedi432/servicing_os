<script setup>
// SOS_DEVICE_COMPONENTS_694 — Frappe child table, customer-owned device contents.
import ReceivedDeviceComponents694 from './components/ReceivedDeviceComponents694.vue'
const sos694Received = ref([])

import CounterServiceSteps690 from "./components/CounterServiceSteps690.vue"
import CounterPartsInline689 from "./components/CounterPartsInline689.vue"
import SalesCenter from './components/SalesCenter.vue'
import InventoryWorkspace from './components/InventoryWorkspace.vue' // SOS_INVENTORY_V1

import ServiceInvoiceHub661 from './components/ServiceInvoiceHub661.vue'
import NewSaleCounter655 from './components/NewSaleCounter655.vue'

import CounterRetailTabs697 from './components/CounterRetailTabs697.vue' // SOS_COUNTER_RETAIL_TABS_697
// SERVICING_COUNTER_EXACT_649 — route screenshot tiles into existing workspaces.
import CounterIvory654 from './components/CounterIvory654.vue'
import CounterInvoiceModal654 from './components/CounterInvoiceModal654.vue'
import CounterBilling654 from './components/CounterBilling654.vue';
import BillingDeliveryCommand700 from './components/BillingDeliveryCommand700.vue' // SOS_BILLING_DELIVERY_700
const counter649Selection = ref('receive');
// SERVICING_COUNTER_PATCH_651: select operations inside the Counter workspace.
function counter649Select(action) {
  if (!['receive', 'sale', 'repair', 'billing', 'used', 'stock'].includes(action)) return;
  counter649Selection.value = action;
  activeNav.value = 'Counter';
  if (action === 'receive') activeOperation.value = 'Service Receive';
  if (action === 'billing') activeOperation.value = 'Service Delivery';
}

// SERVICING_COUNTER_648: enhance existing native Counter cards, retain click handlers.
import { installCounter648 } from "./counterLayout648.js";
import "./counterLayout648.css";
onMounted(() => installCounter648());

// SERVICING_STEP_647: independent ERPNext Supplier workspace
import SupplierWorkspace from "./components/SupplierWorkspace.vue";
// S44_NATIVE_COUNTER_RECEIVE: share the ACTUAL Counter form via Vue Teleport.
import { ref as s44Ref, watch as s44Watch, onMounted as s44OnMounted, onUnmounted as s44OnUnmounted } from 'vue';
const s44ReceiveModalOpen = s44Ref(false);
const s44ReceiptPending = s44Ref(false);
let s44ReturnNav = 'Service Jobs';
let s44ReturnOperation = 'Service Receive';
let s44LastCreatedJob = '';
function s44OpenNativeReceive() {
  if (s44ReceiveModalOpen.value || s44ReceiptPending.value) return;
  s44ReturnNav = activeNav.value || 'Service Jobs';
  s44ReturnOperation = activeOperation.value || 'Service Receive';
  activeNav.value = 'Counter';
  activeOperation.value = 'Service Receive';
  s44ReceiveModalOpen.value = true;
}
function s44ReturnToJobs() {
  s44ReceiptPending.value = false;
  activeOperation.value = s44ReturnOperation;
  activeNav.value = s44ReturnNav;
  if (s44LastCreatedJob) {
    window.dispatchEvent(new CustomEvent('servicing-os:service-job-created', { detail: { name: s44LastCreatedJob } }));
    s44LastCreatedJob = '';
  }
}
function s44CloseNativeReceive() {
  if (savingJob.value || !s44ReceiveModalOpen.value) return;
  s44ReceiveModalOpen.value = false;
  s44ReturnToJobs();
}
function s44AfterCounterSaved(jobName) {
  if (!s44ReceiveModalOpen.value) return;
  s44LastCreatedJob = String(jobName || '');
  s44ReceiveModalOpen.value = false;
  // Keep Counter mounted while the existing QR/receipt dialog is open.
  if (receiptOpen.value) s44ReceiptPending.value = true;
  else s44ReturnToJobs();
}
function s44Keydown(event) {
  if (event.key === 'Escape' && s44ReceiveModalOpen.value) s44CloseNativeReceive();
}
let s44StopReceiptWatcher = null;
s44OnMounted(() => {
  // Defer receiptOpen access until after the entire Vue setup has initialized.
  s44StopReceiptWatcher = s44Watch(receiptOpen, (open) => {
    if (!open && s44ReceiptPending.value) s44ReturnToJobs();
  });
  window.addEventListener('servicing-os:open-counter-service-receive', s44OpenNativeReceive);
  window.addEventListener('keydown', s44Keydown);
});
s44OnUnmounted(() => {
  if (s44StopReceiptWatcher) s44StopReceiptWatcher();
  window.removeEventListener('servicing-os:open-counter-service-receive', s44OpenNativeReceive);
  window.removeEventListener('keydown', s44Keydown);
});

// SOS_632_RECEIPT_PRINT_CENTER: Unified print controls beside Print / Reprint Receipt.
import ServiceJobSticker629 from './components/ServiceJobSticker629.vue'
// SOS_629B_VISIBLE_QR_PRINT
// SOS_QR_DEEPLINK_629: only navigate after the existing authenticated UI mounts.
import { onMounted as sos629OnMounted } from 'vue'
sos629OnMounted(() => {
  const job = new URLSearchParams(window.location.search).get('service_job')
  if (!job || job.length > 140 || !/^[A-Za-z0-9._-]+$/.test(job)) return
  activeNav.value = 'Service Jobs'
  if (typeof repairManagementOpen !== 'undefined') repairManagementOpen.value = false
})

// SERVICING_COUNTER_TABS_627
import { ref as sos627Ref } from 'vue'
import CounterWorkspace627 from './components/CounterWorkspace627.vue'
const sos627Tab = sos627Ref('receive')
function sos627Choose(next) {
  if (!['sale', 'receive', 'repairs', 'delivery', 'used', 'stock'].includes(next)) return
  sos627Tab.value = next
  // Keep the original service intake form visible and intact in its own tab.
  if (next === 'receive' && typeof activeOperation !== 'undefined') {
    activeOperation.value = 'Service Receive'
  }
  if (typeof repairManagementOpen !== 'undefined') repairManagementOpen.value = false
}

// SERVICING_COUNTER_REPORTS_LOGIN_626
import {ref as sos626Ref, onMounted as sos626Mounted} from 'vue';
import CounterSaleModal from './components/CounterSaleModal.vue';
import BusinessReports626 from './components/BusinessReports626.vue';
const sos626SaleOpen = sos626Ref(false);
function sos626OpenSale() {sos626SaleOpen.value=true;}
function sos626Operation(op) {
  if (['New Product Sale','New Sale','New Sales'].includes(op)) {sos626OpenSale();return;}
  if (typeof counterChooseOperation620G === 'function') {counterChooseOperation620G(op);return;}
  if (typeof handleCounterOperation === 'function') {handleCounterOperation(op);return;}
  if (typeof activeOperation !== 'undefined') activeOperation.value=op;
}
// Existing backend permissions remain the security boundary. Guest users enter via branded login.
sos626Mounted(async () => {
  try {
    const response=await fetch('/api/method/frappe.auth.get_logged_user',{credentials:'same-origin'});
    const data=await response.json();
    if (response.ok && data.message==='Guest') window.location.replace('/servicing-login');
  } catch (_) { /* Existing backend status UI will show connectivity errors. */ }
});


// SERVICING_SERVICE_JOBS_ITEM_FIX_624B — active workspace mounts, not old previews.
import ServiceJobsWorkspace from './components/ServiceJobsWorkspace.vue';
import CounterRepairTabs698 from './components/CounterRepairTabs698.vue' // SOS_COUNTER_REPAIR_TABS_698
import StockQuickAdd from './components/StockQuickAdd.vue';
function sosReceiveFromJobs624B() {
  if (typeof repairManagementOpen !== 'undefined') repairManagementOpen.value = false;
  if (typeof activeOperation !== 'undefined') activeOperation.value = 'Service Receive';
  if (typeof selectNavigation === 'function') selectNavigation('Counter');
  else activeNav.value = 'Counter';
}
function sosManageFromJobs624B() {
  if (typeof repairManagementOpen !== 'undefined') repairManagementOpen.value = true;
}
function sosStockChanged624B() {
  // Keep stock creation and submission isolated to the existing stock API.
  // Reloading the Inventory tab causes the original stock widgets to requery.
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('sos-stock-changed'));
}

// SERVICING_SHOP_STOCK_SEARCH_624A
import ServiceShopWorkspace from "./components/ServiceShopWorkspace.vue";
function sosNavigateFromShop(menu) {
  if (typeof selectNavigation === "function") selectNavigation(menu);
  else activeNav.value = menu;
}

// SERVICING_NAV_WORKSPACES_621_623
import { computed as sosMenuComputed, unref as sosMenuUnref } from "vue";
import CustomerWorkspace from "./components/CustomerWorkspace.vue";
import UsedLaptopWorkspace from "./components/UsedLaptopWorkspace.vue";
import SettingsWorkspace from "./components/SettingsWorkspace.vue";
const servicingExtendedMenu = sosMenuComputed(() => {
  const existing = sosMenuUnref(navigation);
  const base = Array.isArray(existing) ? existing : [];
  const additional = ["Customers", "Used Laptops", "Settings"];
  return [...base, ...additional.filter(label => !base.includes(label))];
});

// SERVICING_RETAIL_SALES_620B_20261112
import RetailSales from "./components/RetailSales.vue";

// SERVICING_OWNER_REPORTS_618A_ADAPTIVE
import OwnerReports from "./components/OwnerReports.vue";

// AMCL_STOCK_MANAGEMENT_615E3
import StockManagement from "./components/StockManagement.vue";
import ServicingSidebar from "./components/ServicingSidebar.vue";
// REPAIR MANAGEMENT 6.14B
import RepairManagement from "./components/RepairManagement.vue";
import { ref as repairRef } from "vue";
const repairManagementOpen = repairRef(false);

import ServiceReceipt from "./components/ServiceReceipt.vue";
import { getServiceReceipt } from "./api/frappe.js";
const mobileMenuOpen = ref(false);
import { computed, ref, onMounted, watch, onUnmounted, nextTick } from "vue";
import { getAppInfo, receiveServiceJob, searchCustomers } from "./api/frappe.js";

const appInfo = ref(null);
const backendLoading = ref(true);
const backendError = ref("");

async function loadBackend() {
	backendLoading.value = true;
	backendError.value = "";
	try {
		appInfo.value = await getAppInfo();
	} catch (error) {
		backendError.value = error?.message || "Unable to connect to Frappe";
	} finally {
		backendLoading.value = false;
	}
}

onMounted(loadBackend);

const navigation = [
	"Counter",
	"New Sales",
	"Used Laptops",
	"Service Jobs",
	"Customers",
	"Inventory",
	"Reports",
	"Settings",
];

const operations = [
	"New Product Sale",
	"Used Laptop Sale",
	"Service Receive",
	"Service Delivery",
	"Repair Billing",
];


// Step 6.11 — Ivory navigation

// SERVICING PROFILE AND SIDEBAR FIX 6.13
const administratorMenuOpen = ref(false);

const administratorInitials = computed(() => {
  const name = String(
    appInfo.value?.full_name || "User"
  ).trim();

  return name.split(/\s+/)
    .slice(0, 2)
    .map(part => part.charAt(0).toUpperCase())
    .join("") || "U";
});

function closeAdministratorMenu() {
  administratorMenuOpen.value = false;
}

function openFrappeDesk() {
  window.location.assign("/app");
}

function openUserSettings() {
  window.location.assign("/app/user-profile");
}

function signOutOfServicing() {
  window.location.assign("/api/method/logout");
}

const ivorySidebarCollapsed = ref(false);

function toggleIvorySidebar() {
  ivorySidebarCollapsed.value = !ivorySidebarCollapsed.value;
}

const ivoryNavigationIcons = {
  "Counter": "◈",
  "New Sales": "▣",
  "Used Laptops": "▤",
  "Service Jobs": "⚒",
  "Customers": "♙",
  "Inventory": "▦",
  "Reports": "▥",
  "Settings": "⚙"
};

const activeNav = ref("Counter");
const activeOperation = ref("Service Receive");
const search = ref("");

// Step 6.9: Internal barcode lookup
const scanOpen = ref(false);
const scanLoading = ref(false);
const scanError = ref("");
const scanJob = ref(null);
const scanShop = ref(null);

async function scanServiceJob(value) {
  const number = String(value || "").trim().toUpperCase();

  if (!number) {
    scanError.value = "Scan or enter a Service Job number.";
    scanOpen.value = true;
    return;
  }

  if (!/^SRV-[A-Z0-9-]+$/.test(number)) {
    scanError.value = "Invalid Service Job number.";
    scanOpen.value = true;
    return;
  }

  scanOpen.value = true;
  scanLoading.value = true;
  scanError.value = "";
  scanJob.value = null;
  scanShop.value = null;

  try {
    const data = await getServiceReceipt(number);
    scanJob.value = data.job || null;
    await openExistingJobInForm(number, data);
    if (viewingServiceJob.value &&
        viewedServiceJob.value?.name === number) {
      scanOpen.value = false;
    }
    scanShop.value = data.shop || null;

    if (!scanJob.value) {
      throw new Error("Service Job details unavailable.");
    }

    search.value = number;
  } catch (error) {
    scanError.value =
      error.message || "Service Job not found or access denied.";
  } finally {
    scanLoading.value = false;
  }
}

function closeServiceScan() {
  scanOpen.value = false;
}

async function printScannedJob() {
  if (!scanJob.value?.name) return;
  scanOpen.value = false;
  await openServiceReceipt(scanJob.value.name);
}

const customer = ref("");
const mobile = ref("");

const activeCustomerSearchField = ref("name");
const selectedCustomerId = ref("");
const customerSuggestions = ref([]);
const customerSearchLoading = ref(false);
const customerSearchError = ref("");
const customerSearchOpen = ref(false);
const customerSearchTerm = ref("");

let customerSearchTimer = null;
let customerSearchController = null;
let customerSearchSequence = 0;
let selectingCustomer = false;

function cancelCustomerSearch() {
  if (customerSearchTimer) clearTimeout(customerSearchTimer);
  customerSearchTimer = null;

  if (customerSearchController) customerSearchController.abort();
  customerSearchController = null;
  customerSearchSequence++;
}

async function selectCustomerSuggestion(item) {
  cancelCustomerSearch();
  selectingCustomer = true;
  selectedCustomerId.value = item.name;
  customer.value = item.customer_name || item.name;
  mobile.value = item.mobile_no || "";
  customerSuggestions.value = [];
  customerSearchOpen.value = false;
  customerSearchError.value = "";
  await nextTick();
  selectingCustomer = false;
}

function resetCustomerSearch() {
  cancelCustomerSearch();
  selectingCustomer = true;
  selectedCustomerId.value = "";
  customerSuggestions.value = [];
  customerSearchOpen.value = false;
  customerSearchLoading.value = false;
  customerSearchError.value = "";
  customer.value = "";
  mobile.value = "";
  selectingCustomer = false;
}

watch([customer, mobile], () => {
  if (selectingCustomer) return;

  selectedCustomerId.value = "";
  cancelCustomerSearch();

  customerSuggestions.value = [];
  customerSearchError.value = "";

  const term = activeCustomerSearchField.value === "mobile"
    ? mobile.value.trim()
    : customer.value.trim();

  customerSearchTerm.value = term;

  if (term.length < 2) {
    customerSearchLoading.value = false;
    customerSearchOpen.value = false;
    return;
  }

  customerSearchOpen.value = true;
  customerSearchLoading.value = true;
  const sequence = customerSearchSequence;

  customerSearchTimer = setTimeout(async () => {
    const controller = new AbortController();
    customerSearchController = controller;

    try {
      const results = await searchCustomers(
        term,
        controller.signal
      );

      if (sequence !== customerSearchSequence) return;

      customerSuggestions.value = results;
    } catch (error) {
      if (error.name === "AbortError") return;
      if (sequence !== customerSearchSequence) return;
      customerSearchError.value = error.message;
    } finally {
      if (sequence === customerSearchSequence) {
        customerSearchLoading.value = false;
      }
    }
  }, 250);
});

onUnmounted(cancelCustomerSearch);

const deviceType = ref("Laptop");
const brand = ref("");
const model = ref("");
const serialNumber = ref("");
const problem = ref("");
const accessories = ref("");
const priority = ref("Normal");
const estimatedCost = ref("");
const message = ref("");

const title = computed(() =>
	activeNav.value === "Counter" ? "Counter Operations" : activeNav.value,
);


function selectNavigation(item) {
  if (item === 'New Sales') {
    sosSalesSection.value = 'New Sale'
    activeNav.value = 'New Sales'
  } else if (typeof item === 'string' && item.startsWith('Sales: ')) {
    const next = item.slice(7)
    if (!sosSalesAllowed.includes(next)) return
    sosSalesSection.value = next
    activeNav.value = 'New Sales'
  } else {
    sosSalesSection.value = 'New Sale'
    activeNav.value = item
  }
  message.value = ''
}



function resetServiceForm() {
  resetCustomerSearch();
  deviceType.value = "Laptop";
  brand.value = "";
  model.value = "";
  serialNumber.value = "";
  problem.value = "";
  accessories.value = "";
    sos694Received.value = [];
  priority.value = "Normal";
  estimatedCost.value = "";
  message.value = "";
  sos682Technician.value = "";
}


const sos632StickerOpen = ref(false);
function sos632PrintQrSticker() { sos632StickerOpen.value = true; }
const receiptOpen = ref(false);
const receiptData = ref(null);
const receiptJobNumber = ref("");
const receiptLoading = ref(false);
const receiptError = ref("");

async function openServiceReceipt(number) {
  const name = String(number || "").trim();
  if (!name) { receiptError.value = "Enter a Service Job number."; return; }
  receiptLoading.value = true;
  receiptError.value = "";
  try {
    receiptData.value = await getServiceReceipt(name);
    receiptJobNumber.value = name;
    receiptOpen.value = true;
  } catch (error) {
    receiptError.value = error.message || "Unable to load receipt";
  } finally {
    receiptLoading.value = false;
  }
}


// Existing Service Job view — Step 6.10
const viewingServiceJob = ref(false);
const viewedServiceJob = ref(null);
const existingJobLoading = ref(false);
const existingJobError = ref("");

async function openExistingJobInForm(jobNumber, existingData = null) {
  const number = String(jobNumber || "").trim();

  if (!number) {
    existingJobError.value = "Service Job number is required.";
    return;
  }

  existingJobLoading.value = true;
  existingJobError.value = "";

  try {
    const data = existingData || await getServiceReceipt(number);
    const job = data?.job;

    if (!job?.name) {
      throw new Error("Service Job not found.");
    }

    // Prevent customer autocomplete from treating
    // loaded data as a new customer search.
    cancelCustomerSearch();
    selectingCustomer = true;

    selectedCustomerId.value = job.customer || "";
    customer.value = job.customer_name || "";
    mobile.value = job.mobile || "";

    deviceType.value = job.device_type || "Laptop";
    brand.value = job.brand || "";
    model.value = job.device_model || "";
    serialNumber.value = job.serial_number || "";
    problem.value = job.reported_problem || "";
    accessories.value = job.accessories_received || "";
    sos694Received.value = Array.isArray(job.custom_received_components) ? job.custom_received_components.map(part => ({ ...part })) : [];
    priority.value = job.priority || "Normal";
    estimatedCost.value = String(job.estimated_cost ?? "");
    sos682Technician.value = job.technician || "";

    viewedServiceJob.value = job;
    viewingServiceJob.value = true;

    receiptJobNumber.value = job.name;

    activeNav.value = "Counter";
    activeOperation.value = "Service Receive";
    mobileMenuOpen.value = false;

    message.value = "";

    await nextTick();
    selectingCustomer = false;

    // Move to the Service Receive section.
    const form = document.querySelector(
      'form[v-if], form'
    );

    if (form) {
      form.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    }

  } catch (error) {
    selectingCustomer = false;
    existingJobError.value =
      error?.message || "Unable to load Service Job.";
  } finally {
    existingJobLoading.value = false;
  }
}

function startNewServiceReceive() {
  sos690RecentlyCreatedJob.value = ''
  sos690RecentStatus.value = 'Received'
  sos686Editing.value = false;
  sos686CanDelete.value = false;
  sos686DeleteReason.value = '';
  sos686SelectedModified.value = '';
  sos686DeleteOpen.value = false;
  viewingServiceJob.value = false;
  viewedServiceJob.value = null;
  existingJobError.value = "";

  resetServiceForm();
  receiptJobNumber.value = "";

  activeNav.value = "Counter";
  activeOperation.value = "Service Receive";
}

async function printViewedServiceJob() {
  if (!viewedServiceJob.value?.name) return;
  await openServiceReceipt(viewedServiceJob.value.name);
}

const savingJob = ref(false);

async function submitDemo() {
  if (viewingServiceJob.value) {
    if (sos686Editing.value) await sos686SaveExisting();
    else message.value = 'This Service Job is view-only. Select New Service Receive to make another job.';
    return;
  }

  if (savingJob.value) return;

  if (!servicingShop.value?.name) {
    message.value = "Shop configuration not loaded.";
    return;
  }

  if (!customer.value.trim()) {
    message.value = "Please enter or select a Customer Name.";
    return;
  }

  if (!mobile.value.trim()) {
    message.value = "Please enter the Customer Mobile Number.";
    return;
  }

  if (!problem.value.trim()) {
    message.value = "Please describe the device problem.";
    return;
  }

  savingJob.value = true;
  message.value = "Saving service job...";

  try {
    const result = await receiveServiceJob({
      shop: servicingShop.value.name,
      customer_name: customer.value.trim(),
      customer: selectedCustomerId.value || null,
      mobile: mobile.value.trim(),
      device_type: deviceType.value,
      brand: brand.value.trim(),
      device_model: model.value.trim(),
      serial_number: serialNumber.value.trim(),
      reported_problem: problem.value.trim(),
      accessories_received: accessories.value.trim(),
      received_components: sos694Received.value.map(part => ({ ...part })),
      priority: priority.value,
      assigned_technician: sos682Technician.value || null,
      estimated_cost: Number(estimatedCost.value || 0)
    });

    message.value = "Service Job " + result.service_job + " saved successfully!";
    receiptJobNumber.value = result.service_job;
    sos690RecentlyCreatedJob.value = String(result.service_job || '')
    await openServiceReceipt(result.service_job);
    s44AfterCounterSaved(result.service_job); // S44_NATIVE_COUNTER_RECEIVE
    if (receiptError.value) message.value += " Receipt: " + receiptError.value;

    await refreshDashboard();
    sos682SelectedJob.value = result.service_job;
    sos682LoadHistory();

    resetCustomerSearch();

    deviceType.value = "Laptop";
    brand.value = "";
    model.value = "";
    serialNumber.value = "";
    problem.value = "";
    accessories.value = "";
    sos694Received.value = [];
    priority.value = "Normal";
    estimatedCost.value = "";
    sos682Technician.value = "";

  } catch (error) {
    message.value = error.message || "Failed to save service job.";
    console.error("Service Receive:", error);
  } finally {
    savingJob.value = false;
  }
}

import { onMounted as onShopMounted } from 'vue'
import { getShopConfig } from './api/frappe.js'
import { getDashboard } from './api/frappe.js'

const servicingShop = ref(null)
const servicingShopLoading = ref(true)
const servicingShopError = ref('')

async function loadServicingShop() {
  servicingShopLoading.value = true
  servicingShopError.value = ''

  try {
    servicingShop.value = await getShopConfig()
  } catch (error) {
    servicingShopError.value =
      error.message || 'Unable to load shop'
    console.error('Shop configuration:', error)
  } finally {
    servicingShopLoading.value = false
  }
}

onShopMounted(loadServicingShop)


const dashboardData = ref(null);
const dashboardLoading = ref(false);
const dashboardError = ref("");

async function refreshDashboard() {
  dashboardLoading.value = true;
  dashboardError.value = "";

  try {
    dashboardData.value = await getDashboard();
  } catch (error) {
    dashboardError.value =
      error?.message || "Unable to load dashboard";
    console.error("Dashboard:", error);
  } finally {
    dashboardLoading.value = false;
  }
}

onMounted(refreshDashboard);

const dashboardCards = computed(() => [
  ["Today Sales", "৳ 0"],
  ["Service Received", String(dashboardData.value?.received_today ?? 0)],
  ["Ready to Deliver", String(dashboardData.value?.ready_to_deliver ?? 0)],
  ["Pending Jobs", String(dashboardData.value?.pending_jobs ?? 0)]
]);


// SOS_RECEIVE_INLINE_TECH_HISTORY_682: receive-time technician & printable paginated history.
const sos683TechnicianSearch = ref('')
const sos683TechnicianOptions = computed(() => {
  const query = sos683TechnicianSearch.value.trim().toLowerCase()
  const items = sos682Technicians.value || []
  return query ? items.filter(x => String(x.label || x.value || '').toLowerCase().includes(query) || x.value === sos682Technician.value) : items
})
const sos682Technician = ref('')
const sos682Technicians = ref([])
const sos682TechnicianError = ref('')
const sos682TechnicianLoading = ref(false)
const sos682History = ref([])
const sos682HistoryPage = ref(1)
const sos682HistoryNext = ref(false)
const sos682HistoryLoading = ref(false)
const sos682HistoryError = ref('')
const sos682Search = ref('')
const sos682SelectedJob = ref('')
const sos682HistoryScope = computed(() => selectedCustomerId.value || '')
let sos682Timer = null
let sos682Seq = 0
async function sos682Api(method, params = {}) {
  const url = new URL('/api/method/servicing_os.api.counter_receive_682.' + method, window.location.origin)
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } })
  const data = await response.json().catch(() => ({}))
  if (!response.ok || data.exc_type || data.exception || data.exc) {
    let message = `Unable to load data (HTTP ${response.status})`
    try { const messages = JSON.parse(data._server_messages || '[]'); if (messages.length) message = JSON.parse(messages[messages.length - 1]).message || message } catch {}
    throw new Error(message)
  }
  return data.message || {}
}
async function sos682LoadTechnicians() {
  sos682TechnicianLoading.value = true; sos682TechnicianError.value = ''
  try {
    const data = await sos682Api('get_receive_technicians')
    sos682Technicians.value = data.technicians || []
    if (data.setup_needed) sos682TechnicianError.value = 'Technician field setup required. Contact System Manager.'
  } catch (error) { sos682TechnicianError.value = error.message || 'Unable to load technicians.' }
  finally { sos682TechnicianLoading.value = false }
}
async function sos682LoadHistory() {
  const seq = ++sos682Seq
  sos682HistoryLoading.value = true; sos682HistoryError.value = ''
  try {
    const data = await sos682Api('get_receive_history', {
      q: sos682Search.value.trim(),
      customer: sos682Search.value.trim() ? '' : sos682HistoryScope.value,
      page: sos682HistoryPage.value,
    })
    if (seq !== sos682Seq) return
    sos682History.value = data.jobs || []
    sos682HistoryNext.value = !!data.has_next
  } catch (error) {
    if (seq !== sos682Seq) return
    sos682History.value = []
    sos682HistoryNext.value = false
    sos682HistoryError.value = error.message || 'Unable to load service jobs.'
  } finally { if (seq === sos682Seq) sos682HistoryLoading.value = false }
}
function sos682QueueHistory() {
  if (sos682Timer) clearTimeout(sos682Timer)
  sos682Timer = setTimeout(sos682LoadHistory, 250)
}
watch(sos682Search, () => { sos682SelectedJob.value = ''; sos682HistoryPage.value = 1; sos682QueueHistory() })
watch(sos682HistoryScope, () => { if (!sos682Search.value.trim()) { sos682HistoryPage.value = 1; sos682QueueHistory() } })
function sos682GoPage(next) {
  const page = sos682HistoryPage.value + next
  if (page < 1 || (next > 0 && !sos682HistoryNext.value)) return
  sos682HistoryPage.value = page
  sos682LoadHistory()
}
function sos682ChooseJob(job) {
  if (job?.name) sos686LoadExisting(job.name)
}
function sos682PrintId() {
  const input = sos682Search.value.trim()
  if (sos682SelectedJob.value) return sos682SelectedJob.value
  if (/^SRV-[A-Z0-9._-]+$/i.test(input) && input.length <= 140) return input
  return ''
}
async function sos682PrintReceipt(jobName = '') {
  const id = jobName || sos682PrintId()
  if (!id) { sos682HistoryError.value = 'Select a Service Job or enter its exact SRV number.'; return }
  receiptJobNumber.value = id
  await openServiceReceipt(id)
  if (receiptError.value) sos682HistoryError.value = receiptError.value
}
function sos682PrintSticker(jobName = '') {
  const id = jobName || sos682PrintId()
  if (!id) { sos682HistoryError.value = 'Select a Service Job or enter its exact SRV number.'; return }
  receiptJobNumber.value = id
  sos632PrintQrSticker()
}
onMounted(() => { sos682LoadTechnicians(); sos682LoadHistory() })
onUnmounted(() => { if (sos682Timer) clearTimeout(sos682Timer); ++sos682Seq })

// SOS_COUNTER_RECEIVE_EDITOR_686 — same-form edit/delete with optimistic locking.
const sos686Editing = ref(false)
const sos686CanDelete = ref(false)
const sos686DeleteReason = ref('')
const sos686SelectedModified = ref('')
const sos686Busy = ref(false)
const sos686DeleteOpen = ref(false)
const sos686DeleteConfirm = ref('')
const sos686Message = ref('')
async function sos686Request(method, payload = null) {
  const base = '/api/method/servicing_os.api.counter_editor_686.' + method
  const url = payload === null ? base : base
  const options = { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } }
  if (payload === null) { options.method = 'GET' }
  else {
    options.method = 'POST'
    options.headers['Content-Type'] = 'application/json'
    options.headers['X-Frappe-CSRF-Token'] = window.csrf_token || window.frappe?.csrf_token || ''
    options.body = JSON.stringify(payload)
  }
  const response = await fetch(url, options)
  const result = await response.json().catch(() => ({}))
  if (!response.ok || result.exc || result.exception || result.exc_type) {
    let detail = result.message && typeof result.message === 'string' ? result.message : `Service Job API error (HTTP ${response.status})`
    try {
      const messages = JSON.parse(result._server_messages || '[]')
      if (messages.length) detail = JSON.parse(messages[messages.length - 1]).message || detail
    } catch {}
    throw new Error(detail)
  }
  return result.message || {}
}
async function sos686LoadExisting(name) {
  if (!name || sos686Busy.value) return
  sos686Busy.value = true
  sos686Message.value = ''
  sos682HistoryError.value = ''
  try {
    const url = new URL('/api/method/servicing_os.api.counter_editor_686.get_job', window.location.origin)
    url.searchParams.set('name', name)
    const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || payload.exc || payload.exception || !payload.message?.job) {
      let detail = `Cannot open job (HTTP ${response.status})`
      try { const msgs = JSON.parse(payload._server_messages || '[]'); if (msgs.length) detail = JSON.parse(msgs[msgs.length - 1]).message || detail } catch {}
      throw new Error(detail)
    }
    const result = payload.message
    await openExistingJobInForm(name, result)
    if (!viewingServiceJob.value || viewedServiceJob.value?.name !== name) {
      throw new Error(existingJobError.value || 'Could not populate Service Receive form')
    }
    sos686Editing.value = !!result.can_edit
    sos686CanDelete.value = !!result.can_delete
    sos686DeleteReason.value = result.delete_reason || ''
    sos686SelectedModified.value = String(result.job.modified || '')
    sos682SelectedJob.value = name
    sos683TechnicianSearch.value = ''
    sos686Message.value = result.can_edit ? 'Editing existing Service Job. Save Changes to update it.' : 'This job is view-only.'
  } catch (error) { sos682HistoryError.value = error.message || 'Unable to open job.' }
  finally { sos686Busy.value = false }
}
async function sos686SaveExisting() {
  if (!viewedServiceJob.value?.name || sos686Busy.value) return
  if (!sos686Editing.value) { message.value = 'This Service Job is read-only.'; return }
  sos686Busy.value = true
  savingJob.value = true
  message.value = 'Saving changes…'
  try {
    const payload = {
      customer: selectedCustomerId.value || '',
      customer_name: customer.value.trim(),
      mobile: mobile.value.trim(),
      device_type: deviceType.value,
      brand: brand.value.trim(),
      device_model: model.value.trim(),
      serial_number: serialNumber.value.trim(),
      reported_problem: problem.value.trim(),
      accessories_received: accessories.value.trim(),
      received_components: sos694Received.value.map(part => ({ ...part })),
      priority: priority.value,
      estimated_cost: Number(estimatedCost.value || 0),
      technician: sos682Technician.value || ''
    }
    const result = await sos686Request('save_job', {
      name: viewedServiceJob.value.name,
      data: payload,
      expected_modified: sos686SelectedModified.value,
    })
    sos686SelectedModified.value = String(result.job?.modified || '')
    viewedServiceJob.value = { ...viewedServiceJob.value, ...(result.job || {}) }
    sos686CanDelete.value = !!result.can_delete
    message.value = 'Service Job ' + viewedServiceJob.value.name + ' updated successfully.'
    sos686Message.value = message.value
    await sos682LoadHistory()
    await refreshDashboard()
  } catch (error) { message.value = error.message || 'Unable to update Service Job.' }
  finally { sos686Busy.value = false; savingJob.value = false }
}
async function sos686ReloadSelected() {
  if (viewedServiceJob.value?.name) await sos686LoadExisting(viewedServiceJob.value.name)
}
function sos686AskDelete() {
  if (!sos686CanDelete.value || !viewedServiceJob.value?.name) return
  sos686DeleteConfirm.value = ''
  sos686Message.value = ''
  sos686DeleteOpen.value = true
}
async function sos686DeleteSelected() {
  const name = viewedServiceJob.value?.name || ''
  if (!name || !sos686CanDelete.value || sos686DeleteConfirm.value !== name || sos686Busy.value) return
  sos686Busy.value = true
  try {
    const result = await sos686Request('delete_job', { name, confirm: name, expected_modified: sos686SelectedModified.value })
    if (!result.deleted) throw new Error('Deletion was not confirmed by server')
    sos686DeleteOpen.value = false
    startNewServiceReceive()
    sos682SelectedJob.value = ''
    sos686Message.value = 'Deleted Service Job ' + name
    await sos682LoadHistory()
    await refreshDashboard()
  } catch (error) { sos686Message.value = error.message || 'Cannot delete Service Job.' }
  finally { sos686Busy.value = false }
}

// SOS_COUNTER_RECEIVE_UX_687: history-card actions, permission-aware deletion.
async function sos687EditHistoryJob(job) {
  if (!job?.name || sos686Busy.value) return
  await sos686LoadExisting(job.name)
  if (viewedServiceJob.value?.name === job.name && sos682SelectedJob.value === job.name) {
    await nextTick()
    document.querySelector('.sos682-receive-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}
async function sos687DeleteHistoryJob(job) {
  if (!job?.name || sos686Busy.value) return
  sos682HistoryError.value = ''
  // A completed/processed job is retained for its repair/payment audit trail.
  if (job.status && job.status !== 'Received') {
    sos682HistoryError.value = `${job.name} is ${job.status}. Permanent deletion is allowed only for unprocessed Received jobs; this record is protected.`
    return
  }
  // Recheck permissions, invoice links and modified timestamp on the server.
  sos686CanDelete.value = false
  await sos686LoadExisting(job.name)
  if (sos682SelectedJob.value !== job.name || viewedServiceJob.value?.name !== job.name) return
  if (!sos686CanDelete.value) {
    sos682HistoryError.value = sos686DeleteReason.value || 'Delete denied. Check Service Job Delete permission, linked invoices, and repair activity.'
    return
  }
  sos686Message.value = ''
  sos686AskDelete()
}

// SOS_COUNTER_RECEIVE_REPAIR_689 — visible results for existing Edit/Delete buttons.
// SOS_SERVICE_WORKFLOW_690: one selected job drives repair steps, parts and invoice.
const sos690RecentlyCreatedJob = ref('')
const sos690RecentStatus = ref('Received')
const sos690CurrentJob = computed(() => (
  viewingServiceJob.value && viewedServiceJob.value?.name
    ? (sos682SelectedJob.value === viewedServiceJob.value.name ? String(viewedServiceJob.value.name) : '')
    : String(sos690RecentlyCreatedJob.value || '')
))
const sos690InvoiceJob = computed(() => (
  sos686Busy.value || savingJob.value ? '' : sos690CurrentJob.value
))
async function sos690RepairStepUpdated(detail) {
  if (!detail?.name || detail.name !== sos690CurrentJob.value) return
  if (!viewingServiceJob.value && sos690RecentlyCreatedJob.value === detail.name) sos690RecentStatus.value = detail.status || sos690RecentStatus.value
  await sos682LoadHistory()
  await refreshDashboard()
  if (viewingServiceJob.value && viewedServiceJob.value?.name === detail.name) {
    await sos686LoadExisting(detail.name)
  }
}

const sos689ActionFeedback = ref('')
async function sos689EditHistory(job) {
  sos689ActionFeedback.value = ''
  await sos687EditHistoryJob(job)
  if (sos682HistoryError.value) sos689ActionFeedback.value = sos682HistoryError.value
  else if (viewedServiceJob.value?.name === job.name && !sos686Editing.value)
    sos689ActionFeedback.value = `Service Job ${job.name} cannot be edited in its current state or with your permissions.`
}
async function sos689DeleteHistory(job) {
  sos689ActionFeedback.value = ''
  await sos687DeleteHistoryJob(job)
  if (sos682HistoryError.value) sos689ActionFeedback.value = sos682HistoryError.value
}

const recentServiceJobs = computed(
  () => dashboardData.value?.recent_jobs || []
);

function serviceJobStatusClass(status) {
  const styles = {
    Received: "bg-blue-100 text-blue-700",
    Diagnosing: "bg-purple-100 text-purple-700",
    "Waiting for Parts": "bg-amber-100 text-amber-700",
    Repairing: "bg-orange-100 text-orange-700",
    "Ready to Deliver": "bg-green-100 text-green-700",
    Delivered: "bg-slate-100 text-slate-600",
    Cancelled: "bg-red-100 text-red-700"
  };

  return styles[status] || "bg-slate-100 text-slate-600";
}


// SERVICING_COUNTER_NEW_SALE_ROUTING_620C1
// The Counter sale button is a shortcut to the SAME New Sales workspace.
// Never create a parallel checkout or stock/accounting workflow.
function handleCounterOperation(operation) {
  if (['New Product Sale', 'New Sale', 'New Sales'].includes(operation)) {
    // Counter may be entered after the repair overlay was previously open.
    if (typeof repairManagementOpen !== 'undefined') {
      repairManagementOpen.value = false
    }
    selectNavigation('New Sales')
    return
  }
  activeOperation.value = operation
}


// SERVICING OS Counter operation routing: known working modules only.
function counterChooseOperation620G(operation) {
  if (operation === 'New Product Sale' || operation === 'New Sale' || operation === 'New Sales') {
    sos626OpenSale()
    return
  }
  if (operation === 'Service Receive') {
    activeOperation.value = 'Service Receive'
    return
  }
  if ((operation === 'Repair Billing' || operation === 'Service Delivery') &&
      typeof repairManagementOpen !== 'undefined') {
    repairManagementOpen.value = true
    return
  }
  // Unfinished modules are not presented as a working checkout.
  activeOperation.value = operation
}


// SOS_SALES_V3_PRESERVE_POS: existing New Sales remains the only retail POS route
const sosSalesSection = ref('New Sale')
const sosSalesAllowed = [
  'New Sale', 'Sales History', 'Quotations', 'Returns & Exchanges',
  'Payments & Dues', 'Sales Warranty', 'Sales Reports'
]

</script>

<template>
  <SupplierWorkspace v-if="activeNav === 'Suppliers'" />
	<div
  class="ivory-app min-h-screen lg:flex"
  :class="{ 'ivory-is-collapsed': ivorySidebarCollapsed }"
>
		<div
      v-if="mobileMenuOpen"
      class="fixed inset-0 z-40 bg-slate-950/60 lg:hidden"
      @click="mobileMenuOpen = false"
    ></div>

    <!-- SERVICING_STABLE_SIDEBAR_V4_20261110 -->
    <ServicingSidebar
      :items="servicingExtendedMenu"
      :active="activeNav"
       :sales-section="sosSalesSection"
      :repair-open="repairManagementOpen"
      :mobile-open="mobileMenuOpen"
      @navigate="(item) => { repairManagementOpen = false; selectNavigation(item); mobileMenuOpen = false }"
      @repair="() => { repairManagementOpen = true; mobileMenuOpen = false }"
      @close-mobile="mobileMenuOpen = false"
    />

		<main class="flex-1 min-w-0">
<!-- SERVICING_COUNTER_REPORTS_LOGIN_626: native Counter in-place checkout and reports -->
<CounterSaleModal :open="sos626SaleOpen" @close="sos626SaleOpen=false" />
<div v-if="false" class="sos626-counter-entry">
  <button type="button" class="sos626-sale-button" @click="sos626OpenSale">🛒 Take Sale Here · Open Checkout</button>
  <span>Customer → products → payment → receipt, without leaving Counter</span>
</div>
<BusinessReports626 v-if="activeNav === 'Reports'" />

<!-- SERVICING_SERVICE_JOBS_ITEM_FIX_624B -->
<section v-if="activeNav === 'Service Jobs' && (typeof repairManagementOpen === 'undefined' || !repairManagementOpen)" class="sos-servicejobs-root">
  <ServiceJobsWorkspace @receive="sosReceiveFromJobs624B" @manage="sosManageFromJobs624B" />
</section>
<template v-if="activeNav === 'Inventory' && (typeof repairManagementOpen === 'undefined' || !repairManagementOpen)">
        <InventoryWorkspace />
      </template>

<!-- SERVICING_NAV_WORKSPACES_621_623: standalone workspace screens -->
<CustomerWorkspace v-if="activeNav === 'Customers'" />
<UsedLaptopWorkspace v-if="activeNav === 'Used Laptops'" />
<SettingsWorkspace v-if="activeNav === 'Settings'" />
<ServiceShopWorkspace v-if="activeNav === 'Service Shop' || activeNav === 'Servicing Shop'" @navigate="sosNavigateFromShop" />


<!-- SOS_SALES_V3_PRESERVE_POS: original POS component remains unchanged -->
<RetailSales v-if="activeNav === 'New Sales' && !repairManagementOpen && sosSalesSection === 'New Sale'" />
<SalesCenter v-else-if="activeNav === 'New Sales' && !repairManagementOpen && sosSalesSection !== 'New Sale'"
             :section="sosSalesSection" />

<OwnerReports v-if="activeNav === 'Reports' && !repairManagementOpen" />

<!-- SOS_INVENTORY_V41: old Inventory stock table hidden; Counter stock panel remains intact -->

<RepairManagement v-if="repairManagementOpen" @close="repairManagementOpen = false" />
<div v-show="(!repairManagementOpen && activeNav !== 'Inventory' && activeNav !== 'Reports') && activeNav !== 'New Sales'">

			<header v-if="activeNav !== 'Counter'"
				class="bg-white border-b px-4 sm:px-6 py-3 sm:py-4 flex flex-wrap gap-3 sm:gap-4 justify-between items-center"
			>
				<div>
					<div class="flex items-center gap-3 min-w-0">
          <button
            type="button"
            @click="mobileMenuOpen = true"
            class="lg:hidden shrink-0 rounded-lg border px-3 py-2 text-lg"
            aria-label="Open menu"
          >
            ☰
          </button>
          <div class="min-w-0">
          <div class="font-semibold text-slate-800 break-words">{{ servicingShop?.shop_name || (servicingShopLoading ? 'Loading shop...' : 'Shop unavailable') }}</div>
					<div class="text-xs text-slate-400">SERVICING OS</div>
          </div>
        </div>
				</div>

				<input
					v-model="search"
                    @keyup.enter="scanServiceJob(search)"
					placeholder="Search customer, job or product..."
					class="border rounded-lg px-4 py-3 w-full sm:w-72 lg:w-80 text-sm min-w-0"
				/>



				
<div class="servicing-profile relative">
  <button
    type="button"
    class="servicing-profile-trigger"
    :aria-expanded="administratorMenuOpen"
    aria-haspopup="menu"
    @click="administratorMenuOpen = !administratorMenuOpen"
  >
    <span class="servicing-avatar">
      {{ administratorInitials }}
    </span>

    <span class="servicing-profile-identity">
      <strong>
        {{ appInfo?.full_name || "User" }}
      </strong>
      <small>My account</small>
    </span>

    <svg
      width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor"
      stroke-width="2" aria-hidden="true"
    >
      <path d="m6 9 6 6 6-6"/>
    </svg>
  </button>

  <div
    v-if="administratorMenuOpen"
    class="servicing-profile-menu"
    role="menu"
  >
    <div class="servicing-profile-menu-header">
      <strong>{{ appInfo?.full_name || "User" }}</strong>
      <span>SERVICING OS account</span>
    </div>

    <button
      type="button"
      role="menuitem"
      @click="closeAdministratorMenu(); openUserSettings()"
    >
      My Profile
    </button>

    <button
      type="button"
      role="menuitem"
      @click="closeAdministratorMenu(); openFrappeDesk()"
    >
      ERPNext Desk
    </button>

    <div class="servicing-profile-separator"></div>

    <button
      type="button"
      role="menuitem"
      class="servicing-logout"
      @click="signOutOfServicing"
    >
      Sign Out
    </button>
  </div>
</div>

			
<!-- SERVICING_COUNTER_647: existing live status moved into top bar -->
<div
					class="flex flex-wrap items-center gap-3 rounded-xl border bg-white px-4 py-3 text-sm counter-647-status"
				>
					<span
						class="h-2.5 w-2.5 rounded-full"
						:class="
							backendLoading
								? 'bg-amber-400'
								: backendError
									? 'bg-red-500'
									: 'bg-emerald-500'
						"
					></span>
					<span v-if="backendLoading" class="text-slate-500"
						>Connecting to Frappe...</span
					>
					<template v-else-if="backendError">
						<span class="text-red-600">Backend unavailable: {{ backendError }}</span>
						<button
							type="button"
							class="rounded border px-3 py-1"
							@click="loadBackend"
						>
							Retry
						</button>
					
</template>
					<template v-else>
						<span class="font-semibold text-slate-800">{{
							appInfo?.app_title || "SERVICING OS"
						}}</span>
						<span class="text-slate-500">{{ appInfo?.full_name }}</span>
						<span class="text-slate-500">Currency: {{ appInfo?.currency }}</span>
						<span class="font-medium text-emerald-700">Backend Connected</span>
					</template>
				</div>
</header>

			<div class="p-3 sm:p-5 lg:p-7 space-y-4 sm:space-y-6 min-w-0" :class="{'sos652-full-counter': activeNav === 'Counter'}">
				

				<section v-if="activeNav !== 'Counter'" class="flex flex-wrap justify-between gap-4 items-start counter-647-heading">
					<div>
						<h1 class="text-2xl font-bold text-slate-900">
							{{ title }}
						</h1>
						<p class="text-sm text-slate-500 mt-1">
							Sales · Service Receive · Delivery · Billing
						</p>
					</div>
				</section>

				<div v-if="activeNav !== 'Counter'" class="grid grid-cols-2 xl:grid-cols-4 gap-2 sm:gap-4 sos636c-obsolete-preview">
					<div
						v-for="card in dashboardCards"
						:key="card[0]"
						class="bg-white rounded-xl border p-5"
					>
						<div class="text-xs text-slate-500">
							{{ card[0] }}
						</div>
						<div class="text-2xl font-bold text-slate-900 mt-2">
							{{ card[1] }}
						</div>
						<div class="text-xs text-slate-400 mt-2">Preview data</div>
					</div>
				</div>

				<section v-if="activeNav === 'Counter'" class="sos627-counter-root sos649-counter-root">
<!-- SERVICING_COUNTER_EXACT_649: the ONE visible action grid; original working content is slotted below -->
<CounterIvory654
  :company="servicingShop?.company || 'AL MODINA COMPUTERS LIMITED'"
  :active="counter649Selection"
  :user="appInfo?.full_name || appInfo?.user || 'Administrator'"
  :currency="appInfo?.currency || 'BDT'"
  :connected="!backendLoading && !backendError"
  :loading="backendLoading"
  :error="backendError"
  v-model:search-value="search"
  :billing-mode="activeOperation"
  @billing-mode="activeOperation = $event"
  @select="counter649Select"
  @settings="selectNavigation('Settings')"
  @open-menu="mobileMenuOpen = true" :selected-service-job="sos690InvoiceJob">
  <template #workspace>
    <div v-if="counter649Selection === 'receive' || counter649Selection === 'billing'" class="sos649-original-workspace">


					<div class="flex flex-wrap gap-2 mb-5 sos627-old-operations counter-647-actions">
						<button
							v-for="operation in operations"
							:key="operation"
							@click="counterChooseOperation620G(operation)"
							class="px-4 py-3 rounded-lg text-sm font-medium border transition"
							:class="
								activeOperation === operation
									? 'bg-blue-600 text-white border-blue-600'
									: 'bg-white text-slate-600 hover:bg-slate-50'
							"
						>
							{{ operation }}
						</button>
					</div>

					<div class="grid grid-cols-1 xl:grid-cols-12 gap-3 sm:gap-5 min-w-0">
						<section class="xl:col-span-6 bg-white border rounded-xl p-5">
							<div class="flex justify-between items-center mb-5">
								<div>
									<h2 class="font-bold text-lg text-slate-900">
										{{ activeOperation }}
									</h2>
									<p class="text-xs text-slate-500 mt-1">
										{{
											activeOperation === "Service Receive"
												? "New repair intake"
												: "Module interface coming next"
										}}
									</p>
								</div>
								<span
									class="text-xs bg-blue-50 text-blue-700 px-3 py-1 rounded-full"
								>
									Preview
								</span>
							</div>

							<!-- S44_NATIVE_COUNTER_RECEIVE: the original Counter form is teleported, never copied -->
<Teleport v-if="activeOperation === 'Service Receive'" to="body" :disabled="!s44ReceiveModalOpen">
  <div class="s44-receive-layer" :class="{ 's44-receive-open': s44ReceiveModalOpen }" @click.self="s44CloseNativeReceive">
    <div class="s44-receive-shell">
      <header v-if="s44ReceiveModalOpen" class="s44-receive-header">
        <div>
          <span class="s44-receive-eyebrow">SERVICING OS · SERVICE JOBS</span>
          <h2>Receive Computer <small>· কম্পিউটার গ্রহণ</small></h2>
          <p>কাউন্টার পেজের একই ফর্ম · কাস্টমার খোঁজা · রসিদ প্রিন্ট</p>
        </div>
        <button type="button" class="s44-receive-close" aria-label="Close" :disabled="savingJob" @click="s44CloseNativeReceive">×</button>
      </header>
      <form :class="{ 'existing-job-view': viewingServiceJob && !sos686Editing }"
								@submit.prevent="submitDemo"
								class="space-y-4 sos682-receive-form"
							>

<div
  v-if="viewingServiceJob && viewedServiceJob"
  class="sos686-existing-head space-y-3"
>
  <div class="flex flex-col sm:flex-row
              sm:items-center sm:justify-between gap-3">
    <div>
      <p class="text-xs font-bold uppercase text-blue-700">
        {{ sos686Editing ? 'Editing Service Job' : 'Existing Service Job — View Only' }}
      </p>

      <h3 class="mt-1 break-all text-xl font-bold text-slate-900">
        {{ viewedServiceJob.name }}
      </h3>

      <p class="mt-1 text-sm text-slate-600">
        Status: {{ viewedServiceJob.status || "Unknown" }}
        · Priority: {{ viewedServiceJob.priority || "Normal" }}
      </p>
    </div>

    <div class="sos686-action-row">
      
      <button
        type="button"
        @click="printViewedServiceJob"
        class="rounded-lg bg-blue-700 px-4 py-3
               text-sm font-semibold text-white"
      >
        Print / Reprint
      </button>

      <button
        type="button"
        @click="startNewServiceReceive"
        class="rounded-lg bg-emerald-700 px-4 py-3
               text-sm font-semibold text-white"
      >
        + New Service Receive
      </button>
    </div>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
    <div>
      <span class="text-slate-500">Received:</span>
      <strong class="ml-1 text-slate-800">
        {{ viewedServiceJob.received_date || "—" }}
      </strong>
    </div>

    <div>
      <span class="text-slate-500">Expected Delivery:</span>
      <strong class="ml-1 text-slate-800">
        {{ viewedServiceJob.expected_delivery || "—" }}
      </strong>
    </div>
  </div>

  <div v-if="viewedServiceJob.diagnosis"
       class="rounded-lg bg-white p-3 text-sm">
    <strong>Diagnosis</strong>
    <p class="mt-1 whitespace-pre-wrap">
      {{ viewedServiceJob.diagnosis }}
    </p>
  </div>
</div>

<div
  v-if="existingJobError"
  class="rounded-lg bg-red-50 p-3 text-sm text-red-700"
>
  {{ existingJobError }}
</div>

<div
  v-if="existingJobLoading"
  class="rounded-lg bg-blue-50 p-3 text-sm text-blue-700"
>
  Loading Service Job...
</div>


<!-- 6.82 receipt controls moved to right-hand history -->

								<div class="sos694-four grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
									<label class="text-sm">
										Customer Name
										<input
											v-model="customer"
                  @input="activeCustomerSearchField = 'name'"
                  autocomplete="off" @focus="customerSearchOpen = true"
											class="field"
											placeholder="Customer name"
										/>
									</label>
									<label class="text-sm">
										Mobile Number
										<input
											v-model="mobile"
                  @input="activeCustomerSearchField = 'mobile'"
                  type="tel" inputmode="tel" autocomplete="off" @focus="customerSearchOpen = true"
											class="field"
											placeholder="01XXXXXXXXX"
										/>
									</label>

<div class="sm:col-span-2 min-w-0">
  <div
    v-if="!selectedCustomerId && customerSearchOpen && customerSearchTerm.length >= 2"
    class="rounded-xl border bg-white shadow-sm overflow-hidden"
  >
    <div class="flex items-center justify-between gap-3 bg-slate-50 px-3 py-2">
      <span class="text-xs font-semibold text-slate-600">
        Customer Suggestions
      </span>
      <button
        type="button"
        class="text-xs text-blue-600"
        @click="customerSearchOpen = false"
      >
        Close
      </button>
    </div>

    <div
      v-if="customerSearchLoading"
      class="px-3 py-4 text-sm text-slate-500"
    >
      Searching Customers...
    </div>

    <div
      v-else-if="customerSearchError"
      class="px-3 py-4 text-sm text-red-600"
    >
      {{ customerSearchError }}
    </div>

    <template v-else-if="customerSuggestions.length">
      <button
        v-for="item in customerSuggestions"
        :key="item.name"
        type="button"
        class="block w-full border-t px-3 py-3 text-left hover:bg-blue-50 active:bg-blue-100"
        @click="selectCustomerSuggestion(item)"
      >
        <span class="block text-sm font-semibold text-slate-900 break-words">
          {{ item.customer_name }}
        </span>
        <span class="block text-xs text-slate-500 mt-1">
          {{ item.mobile_no || "No mobile" }}
        </span>
      </button>
    </template>

    <div v-else class="px-3 py-4 text-sm text-slate-500">
      No matching Customer found.
      A new Customer will be created when you save.
    </div>
  </div>
</div>

									<label class="text-sm">
										Device Type
										<select v-model="deviceType" class="field">
											<option>Laptop</option>
											<option>Desktop</option>
											<option>Monitor</option>
											<option>Printer</option>
											<option>Other</option>
										</select>
									</label>
									<label class="text-sm">
										Brand
										<input
											v-model="brand"
											class="field"
											placeholder="Dell, HP, Lenovo..."
										/>
									</label>
									<label class="text-sm">
										Model
										<input
											v-model="model"
											class="field"
											placeholder="Device model"
										/>
									</label>
									<label class="text-sm">
										Serial Number
										<input
											v-model="serialNumber"
											class="field"
											placeholder="Serial / Service Tag"
										/>
									</label>
									<label class="text-sm">
										Priority
										<select v-model="priority" class="field">
											<option>Normal</option>
											<option>Urgent</option>
											<option>High</option>
										</select>
									</label>
									<!-- SOS_RECEIVE_INLINE_TECH_HISTORY_682: choose before saving Service Job -->
<!-- SOS_COUNTER_RECEIVE_EDITOR_686: exactly ONE bilingual technician field -->
<label class="text-sm sos682-tech-field">
  <span class="sos682-tech-label">Assigned Technician · টেকনিশিয়ান</span>
  <select v-model="sos682Technician" class="field sos686-technician-select" :disabled="savingJob || sos682TechnicianLoading || (viewingServiceJob && !sos686Editing)" @focus="!sos682Technicians.length && sos682LoadTechnicians()">
    <option value="">{{ sos682TechnicianLoading ? 'Loading technicians…' : 'Unassigned / Select technician' }}</option>
    <option v-for="person in sos682Technicians" :key="person.value" :value="person.value">{{ person.label }}</option>
  </select>
  <small v-if="sos682TechnicianError" class="sos682-warning" role="alert">{{ sos682TechnicianError }}</small>
</label>
<label class="text-sm">
										Estimated Cost (BDT)
										<input
											v-model="estimatedCost"
											type="number"
											min="0"
											class="field"
											placeholder="0.00"
										/>
									</label>
								</div>

								<label class="block text-sm">
									Reported Problem
									<textarea
										v-model="problem"
										class="field"
										rows="3"
										placeholder="Describe the device problem..."
									></textarea>
								</label>

								<label class="block text-sm">
									Accessories Received
									<textarea
										v-model="accessories"
										class="field"
										rows="2"
										placeholder="Charger, bag, cable..."
									></textarea>
								</label>
<!-- SOS_DEVICE_COMPONENTS_694 — components at intake, full-width below Accessories Received -->
<ReceivedDeviceComponents694 v-model="sos694Received" :disabled="savingJob || (viewingServiceJob && !sos686Editing)" />

								<div class="flex flex-wrap justify-end gap-3 pt-3">
									<button
										type="button" @click="viewingServiceJob ? sos686ReloadSelected() : resetServiceForm()"
										class="sos687-secondary"
									>
										{{ viewingServiceJob ? 'Discard Changes' : 'Reset' }}
									</button>
									<button
										type="submit"
										class="sos687-primary-save"
									 :disabled="savingJob || sos686Busy || (viewingServiceJob && !sos686Editing)"
              >
										{{ savingJob || sos686Busy ? 'Saving…' : (viewingServiceJob ? 'Update Service Job' : 'Receive Device') }}
									</button>
								</div>

								<p
									v-if="message"
									class="text-sm text-amber-700 bg-amber-50 p-3 rounded-lg"
								>
									{{ message }}
								</p>
							</form>
<!-- SOS_COUNTER_RECEIVE_REPAIR_689: parts management for currently selected job -->
<!-- SOS_SERVICE_WORKFLOW_690: Counter supports parts immediately after intake and during editing. -->
<div v-if="sos690CurrentJob" class="sos689-parts-wrap sos690-jobs">
  <CounterServiceSteps690 :key="sos690CurrentJob" :job-name="sos690CurrentJob" @updated="sos690RepairStepUpdated" />
  <CounterPartsInline689 :key="sos690CurrentJob" :job-name="sos690CurrentJob" :job-status="viewingServiceJob && viewedServiceJob?.name === sos690CurrentJob ? (viewedServiceJob.status || '') : sos690RecentStatus" />
</div>
<p v-else class="sos690-parts-prompt">Save the Service Receive first. Then use Service Steps and Add Required Parts below without leaving Counter.</p>

    </div>
  </div>
</Teleport>

							<div v-else class="py-20 text-center text-slate-500">
								{{ activeOperation }} will be implemented in its own milestone.
							</div>
						</section>

						<section class="xl:col-span-3 space-y-5">
							<!-- SOS_RECEIVE_INLINE_TECH_HISTORY_682: searchable customer history + receipt/QR -->
<div class="sos682-aside">
  <div class="sos682-aside-header">
    <div><span class="sos682-eyebrow">SERVICE RECEIVE</span><h2>Customer History</h2><p>{{ sos682HistoryScope && !sos682Search ? 'Jobs for selected customer' : 'Recent five service jobs · Search all records' }}</p></div>
    <button type="button" class="sos682-refresh" :disabled="sos682HistoryLoading" @click="sos682LoadHistory" aria-label="Refresh jobs">↻</button>
  </div>
  <label class="sos682-search-label" for="sos682-receipt-search">Find a saved service job</label>
  <input id="sos682-receipt-search" v-model="sos682Search" type="search" autocomplete="off"
    placeholder="Job No. / customer / mobile / serial" class="sos682-lookup"
    @keydown.enter.prevent="sos682History.length === 1 ? sos682ChooseJob(sos682History[0]) : null" />
  <div v-if="sos682HistoryError" role="alert" class="sos682-error">{{ sos682HistoryError }}</div>
  <p v-if="sos689ActionFeedback" class="sos689-history-alert" role="alert">{{ sos689ActionFeedback }}</p>
  <p class="sos687-history-note">Use the pencil to edit or the bin to request deletion. Processed or invoiced jobs cannot be permanently deleted.</p>
  <div class="sos682-list-head"><strong>{{ sos682Search ? 'Search results' : 'Recent service jobs' }}</strong><span>5 per page</span></div>
  <div v-if="sos682HistoryLoading && !sos682History.length" class="sos682-empty">Loading records…</div>
  <div v-else-if="!sos682History.length" class="sos682-empty">No service jobs found.</div>
  <div v-else class="sos682-job-list">
<!-- SOS_HISTORY_CARDS_688: compact cards designed for the narrow history sidebar -->
    <article v-for="job in sos682History" :key="job.name" class="sos688-job-card"
      :class="{ 'is-selected': sos682SelectedJob === job.name }">
      <button type="button" class="sos688-card-details" :disabled="sos686Busy"
        :title="job.name" :aria-label="`Edit service job ${job.name}`"
        @click="sos689EditHistory(job)">
        <strong class="sos688-job-number">{{ job.name }}</strong>
        <span class="sos688-customer" :title="[job.customer_name || 'Customer', job.mobile || ''].filter(Boolean).join(' · ')">
          {{ job.customer_name || 'Customer' }}<template v-if="job.mobile"> · {{ job.mobile }}</template>
        </span>
        <span class="sos688-device" :title="[job.brand, job.device_model].filter(Boolean).join(' ') || job.device_type || 'Device'">
          {{ [job.brand, job.device_model].filter(Boolean).join(' ') || job.device_type || 'Device' }}
        </span>
      </button>
      <div class="sos688-card-bottom">
        <span class="sos688-status" :title="job.status || 'Received'">{{ job.status || 'Received' }}</span>
        <div class="sos688-actions" aria-label="Service Job actions">
          <button type="button" class="sos688-action sos688-edit" title="Edit Service Job"
            :aria-label="`Edit ${job.name}`" :disabled="sos686Busy" @click.stop="sos689EditHistory(job)">
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9"/><path d="M16 4a2.1 2.1 0 0 1 3 3L9.2 16.8 5 18l1.2-4.2L16 4Z"/>
            </svg>
          </button>
          <!-- SOS_RECEIVED_COMPONENTS_PRINT_V24: same receipt popup, standard-sized action icon. -->
          <button type="button" class="sos688-action sos23-recent-print" title="Print / Reprint Receipt"
            :disabled="receiptLoading" :aria-label="`Print receipt for ${job.name}`"
            @click.stop="sos682PrintReceipt(job.name)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
              stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
              <path d="M6 14h12v7H6z"/><path d="M18 12h.01"/>
            </svg>
          </button>
          <button type="button" class="sos688-action sos688-delete" title="Delete Service Job (if eligible)"
            :aria-label="`Delete ${job.name}`" :disabled="sos686Busy" @click.stop="sos689DeleteHistory(job)">
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18M8 6V4h8v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/>
            </svg>
          </button>
        </div>
      </div>
    
    </article>
  </div>
  <div class="sos682-pagination">
    <button type="button" :disabled="sos682HistoryPage <= 1 || sos682HistoryLoading" @click="sos682GoPage(-1)">← Previous</button>
    <span>Page {{ sos682HistoryPage }}</span>
    <button type="button" :disabled="!sos682HistoryNext || sos682HistoryLoading" @click="sos682GoPage(1)">Next →</button>
  </div>
  <p class="sos686-history-hint">Select any job to load and edit its original Service Receive form. Delete is available only for eligible jobs.</p>
  <div class="sos682-printbox">
    <div class="sos682-print-title"><strong>Service Receipt Printing</strong><small>Choose a saved job above to reprint</small></div>
    <p class="sos682-current">{{ sos682PrintId() || 'No Service Job selected' }}</p>
    <div class="sos682-print-actions">
      <button type="button" :disabled="receiptLoading || !sos682PrintId()" @click="sos682PrintReceipt()">{{ receiptLoading ? 'Loading…' : 'Print / Reprint Receipt' }}</button>
      <button type="button" :disabled="!sos682PrintId()" @click="sos682PrintSticker()">Print QR Sticker</button>
    </div>
    <small v-if="receiptError" class="sos682-warning">{{ receiptError }}</small>
  </div>
</div>

						</section>

						<!-- SERVICING_COUNTER_GUIDANCE_620G -->
            <section class="xl:col-span-3 rounded-2xl border border-amber-100 bg-[#fffdf9] p-5 shadow-sm sos627-old-checkout-preview">
              <div class="border-b border-amber-100 pb-4">
                <div class="text-[10px] font-bold uppercase tracking-widest text-amber-700">Counter shortcuts</div>
                <h2 class="mt-2 text-lg font-bold text-stone-800">Checkout & Quick Actions</h2>
                <p class="mt-2 text-xs leading-relaxed text-stone-500">The live shopping cart and payment controls are in New Sales.</p>
              </div>
              <button type="button" @click="sos626OpenSale"
                class="mt-4 flex w-full items-center justify-between gap-2 rounded-xl bg-[#6e5537] px-4 py-4 text-left text-sm font-bold text-white shadow-sm transition hover:bg-[#543e25] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700">
                <span>🛒 Open New Sale & Checkout</span><span aria-hidden="true">→</span>
              </button>
              <p class="mt-2 text-xs leading-relaxed text-stone-500">Select a stocked product and a customer, then review the total and take payment.</p>
              <div class="mt-5 grid grid-cols-2 gap-2">
                <button type="button" @click="activeOperation = 'Service Receive'" class="rounded-xl border border-stone-200 bg-white px-3 py-3 text-left text-xs font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-700">🖥 Receive Device</button>
                <button type="button" @click="repairManagementOpen = true" class="rounded-xl border border-stone-200 bg-white px-3 py-3 text-left text-xs font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-700">🔧 Manage Repairs</button>
                <button type="button" @click="selectNavigation('Inventory')" class="rounded-xl border border-stone-200 bg-white px-3 py-3 text-left text-xs font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-700">📦 Inventory</button>
                <button type="button" @click="selectNavigation('Reports')" class="rounded-xl border border-stone-200 bg-white px-3 py-3 text-left text-xs font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-700">📊 Reports</button>
              </div>
              <div class="mt-5 rounded-xl border border-amber-100 bg-amber-50/70 p-3 text-xs leading-relaxed text-stone-600">
                <strong>Why checkout may be unavailable:</strong> No item in cart, no customer selected, or zero stock in the retail warehouse. The sales page explains the next step.
              </div>
            </section>
					</div>
				
    </div>
  </template>

  <!-- SERVICING_COUNTER_PATCH_651: actual ServiceJobsWorkspace, not navigation -->
  <template #repair>
    <!-- SERVICING_OS_SERVICE_INVOICE_662: live linked Service Job invoices -->
    <!-- SOS_COUNTER_REPAIR_TABS_698: reuse existing job and invoice flows -->
    <CounterRepairTabs698 @receive="sosReceiveFromJobs624B" @manage="sosManageFromJobs624B" />
  </template>
  <!-- SERVICING_COUNTER_PATCH_652: real ERPNext draft invoice workflow -->
  <template #invoice="{ initialKind, initialJob }"><CounterInvoiceModal654 :initial-job="initialJob"  :initial-kind="initialKind" /></template>

  <!-- SERVICING_COUNTER_PATCH_653: actual source feature components, never placeholders -->
  <template #sale>
  <CounterRetailTabs697>
    <template #legacy>
    <div class="sos653-embedded-module">
      <RetailSales v-if="counter649Selection === 'sale' && !repairManagementOpen" />
    </div>
  
    </template>
  </CounterRetailTabs697>
</template>
  <template #used>
    <div class="sos653-embedded-module">
      <UsedLaptopWorkspace v-if="counter649Selection === 'used'" />
    </div>
  </template>
  <template #stock>
    <div class="sos653-embedded-module">
      <!-- SOS_COUNTER_INVENTORY_696: share the full live Inventory Command Center -->
       <InventoryWorkspace v-if="counter649Selection === 'stock' && !repairManagementOpen" />
    </div>
  </template>
  <template #delivery>
    <div class="sos653-embedded-module">
      <ServiceJobsWorkspace @receive="sosReceiveFromJobs624B" @manage="sosManageFromJobs624B" />
    </div>
  </template>
  <template #billing="{ openInvoice }">
    <!-- SOS_BILLING_DELIVERY_700: original Counter billing is preserved in legacy slot -->
    <BillingDeliveryCommand700>
      <template #legacy>
    <CounterBilling654 @create="openInvoice" />
  
      </template>
    </BillingDeliveryCommand700>
    </template>
<!-- SERVICING_COUNTER_PATCH_654 -->
</CounterIvory654>
</section>

				<section v-else-if="activeNav !== 'Service Jobs'" class="bg-white border rounded-xl p-10 text-center">
					<h2 class="text-lg font-semibold">
						{{ activeNav }}
					</h2>
					<p class="text-slate-500 text-sm mt-2">
						This workspace will be connected in the next milestones.
					</p>
				</section>
			</div>
		</div>
</main>
	</div>

<!-- SOS_COUNTER_RECEIVE_EDITOR_686: confirmation, no silent deletion -->
<Teleport to="body">
  <div v-if="sos686DeleteOpen" class="sos686-overlay" @click.self="!sos686Busy && (sos686DeleteOpen = false)">
    <section class="sos686-modal" role="dialog" aria-modal="true" aria-label="Delete Service Job">
      <h2>Delete Service Job</h2>
      <p>You are about to permanently delete <strong>{{ viewedServiceJob?.name }}</strong>. This action cannot be undone.</p>
      <p>Only newly received, unprocessed and uninvoiced jobs may be deleted.</p>
      <label>Type the exact Service Job number to confirm
        <input v-model.trim="sos686DeleteConfirm" class="sos686-confirm-field" autocomplete="off" :placeholder="viewedServiceJob?.name || ''" />
      </label>
      <div v-if="sos686Message" role="alert" class="sos686-error">{{ sos686Message }}</div>
      <div class="sos686-modal-actions">
        <button type="button" @click="sos686DeleteOpen = false" :disabled="sos686Busy">Cancel</button>
        <button type="button" class="danger" :disabled="sos686Busy || sos686DeleteConfirm !== viewedServiceJob?.name" @click="sos686DeleteSelected">{{ sos686Busy ? 'Deleting…' : 'Delete Permanently' }}</button>
      </div>
    </section>
  </div>
</Teleport>

<ServiceReceipt v-if="receiptOpen && receiptData" :data="receiptData" @close="receiptOpen = false" />

<!-- Step 6.9: Internal Service Job lookup -->
<div
  v-if="scanOpen"
  class="fixed inset-0 z-[99998] flex items-center
         justify-center bg-slate-950/75 p-3 sm:p-6"
  @click.self="closeServiceScan"
>
  <section
    role="dialog"
    aria-modal="true"
    aria-label="Service Job Details"
    class="w-full max-w-2xl max-h-[92dvh] overflow-y-auto
           rounded-2xl bg-white shadow-2xl"
  >
    <header
      class="sticky top-0 flex items-center justify-between
             gap-3 border-b bg-white p-4 sm:p-5"
    >
      <div>
        <h2 class="text-lg font-bold text-slate-900">
          Service Job Lookup
        </h2>
        <p class="text-xs text-slate-500">
          SERVICING OS · Barcode Search
        </p>
      </div>
      <button
        type="button"
        @click="closeServiceScan"
        class="rounded-lg border px-3 py-2 text-slate-700"
      >
        Close
      </button>
    </header>

    <div class="p-4 sm:p-6">
      <p v-if="scanLoading" class="text-blue-700">
        Loading Service Job...
      </p>

      <p
        v-else-if="scanError"
        class="rounded-lg bg-red-50 p-4 text-red-700"
      >
        {{ scanError }}
      </p>

      <div v-else-if="scanJob" class="space-y-5">
        <div class="rounded-xl bg-slate-900 p-4 text-white">
          <p class="text-xs text-slate-300">
            SERVICE JOB
          </p>
          <h3 class="mt-1 break-all text-xl font-bold">
            {{ scanJob.name }}
          </h3>
          <div class="mt-3 flex flex-wrap gap-2">
            <span class="rounded bg-blue-700 px-3 py-1 text-sm">
              {{ scanJob.status || "Unknown" }}
            </span>
            <span class="rounded bg-slate-700 px-3 py-1 text-sm">
              {{ scanJob.priority || "Normal" }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p class="text-xs text-slate-500">Customer</p>
            <p class="font-semibold text-slate-900">
              {{ scanJob.customer_name || "—" }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">Mobile</p>
            <p class="font-semibold text-slate-900">
              {{ scanJob.mobile || "—" }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">Device</p>
            <p class="font-semibold text-slate-900">
              {{ [scanJob.device_type, scanJob.brand,
                  scanJob.device_model].filter(Boolean).join(" / ") }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">Serial Number</p>
            <p class="font-semibold text-slate-900">
              {{ scanJob.serial_number || "—" }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">Technician</p>
            <p class="font-semibold text-slate-900">
              {{ scanJob.technician || "Not assigned" }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">Estimated Cost</p>
            <p class="font-semibold text-slate-900">
              ৳ {{ Number(scanJob.estimated_cost || 0).toFixed(2) }}
            </p>
          </div>
        </div>

        <div>
          <p class="text-xs text-slate-500">Reported Problem</p>
          <p class="whitespace-pre-wrap text-slate-900">
            {{ scanJob.reported_problem || "—" }}
          </p>
        </div>

        <div>
          <p class="text-xs text-slate-500">Diagnosis</p>
          <p class="whitespace-pre-wrap text-slate-900">
            {{ scanJob.diagnosis || "Not recorded" }}
          </p>
        </div>

        <div>
          <p class="text-xs text-slate-500">Accessories Received</p>
          <p class="whitespace-pre-wrap text-slate-900">
            {{ scanJob.accessories_received || "None recorded" }}
          </p>
        </div>

        <div class="flex flex-wrap gap-2 border-t pt-4">
          <button
            type="button"
            @click="printScannedJob"
            class="rounded-lg bg-blue-700 px-5 py-3
                   font-semibold text-white"
          >
            Print / Reprint Receipt
          </button>
    <!-- SOS_632_RECEIPT_PRINT_CENTER: sticker action in the existing print section. -->
    <button type="button" class="sos632-sticker-action" @click="sos632PrintQrSticker">Print QR Sticker</button>

          <button
            type="button"
            @click="closeServiceScan"
            class="rounded-lg border px-5 py-3 text-slate-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </section>
</div>




  <ServiceJobSticker629 v-if="sos632StickerOpen" :job-name="receiptJobNumber || ''" @close="sos632StickerOpen = false" />
</template>

<style scoped>
.field {
    width: 100%;
    min-width: 0;
    max-width: 100%;
    font-size: 16px;
	display: block;
	width: 100%;
	margin-top: 7px;
	padding: 11px 12px;
	border: 1px solid #dbe2ea;
	border-radius: 8px;
	background: white;
	outline: none;
}

.field:focus {
	border-color: #2563eb;
	box-shadow: 0 0 0 2px #dbeafe;
}

@media (max-width: 639px) {
  main {
    width: 100%;
    min-width: 0;
  }

  input, select, textarea {
    max-width: 100%;
    font-size: 16px;
  }

  button {
    touch-action: manipulation;
  }
}
</style>


<style>
/* Existing Service Job view-only mode */
.existing-job-view input:not([type="button"]):not([type="submit"]),
.existing-job-view textarea,
.existing-job-view select {
  pointer-events: none;
  background-color: #f1f5f9 !important;
  color: #334155 !important;
}

.existing-job-view button[type="submit"] {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>


<style>
/* SERVICING OS — Ivory Navigation 6.11 */

.ivory-app {
  background: #f8f6f0;
  color: #433c30;
}

.ivory-sidebar {
  background: linear-gradient(
    160deg,
    #fbf9f3 0%,
    #f3efe5 60%,
    #ebe4d6 100%
  ) !important;

  color: #4d4436 !important;
  border-right: 1px solid #e4dac9;
  box-shadow:
    1px 0 5px rgba(90,72,43,.025),
    3px 0 8px rgba(90,72,43,.025),
    5px 0 13px rgba(90,72,43,.025),
    8px 0 21px rgba(90,72,43,.02);

  transition:
    width .28s cubic-bezier(.2,.8,.2,1),
    transform .25s ease,
    box-shadow .25s ease !important;
}

.ivory-sidebar .text-white {
  color: #4d4436 !important;
}

.ivory-sidebar .text-slate-400,
.ivory-sidebar .text-slate-300 {
  color: #8d7e67 !important;
}

.ivory-sidebar .text-blue-400 {
  color: #a18152 !important;
}

.ivory-sidebar .border-slate-700,
.ivory-sidebar .border-slate-800 {
  border-color: #e3dacb !important;
}

.ivory-sidebar .bg-slate-800,
.ivory-sidebar .bg-slate-700 {
  background: rgba(255,255,255,.65) !important;
  color: #564936 !important;
}

.ivory-sidebar .bg-blue-600,
.ivory-sidebar .bg-blue-700 {
  background: #e5d9c3 !important;
  color: #57432b !important;
}

.ivory-sidebar button {
  transition:
    background .2s ease,
    color .2s ease,
    transform .2s ease,
    box-shadow .2s ease;
}

.ivory-sidebar button:hover {
  background: rgba(255,255,255,.8);
  color: #6d5434;
}

.ivory-nav-button {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 12px;
  min-height: 43px;
}

.ivory-nav-icon {
  display: inline-flex;
  flex: 0 0 24px;
  justify-content: center;
  align-items: center;
  font-size: 19px;
  font-weight: 600;
  color: #92764f;
}

.ivory-collapse-control {
  justify-content: flex-end;
  padding: 12px 13px 0;
}

.ivory-collapse-button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid #e4dac8;
  border-radius: 11px;
  background: rgba(255,255,255,.85);
  color: #846c49;
  box-shadow:
    0 2px 5px rgba(79,61,36,.04),
    0 5px 13px rgba(79,61,36,.04);
  font-size: 22px;
}

.ivory-collapse-button:hover {
  background: #fff;
  transform: translateY(-1px);
}

@media (min-width: 1024px) {
  .ivory-sidebar {
    width: 240px !important;
    min-width: 240px !important;
    max-width: 240px !important;
  }

  .ivory-is-collapsed .ivory-sidebar {
    width: 76px !important;
    min-width: 76px !important;
    max-width: 76px !important;
    overflow-x: hidden;
  }

  .ivory-is-collapsed .ivory-nav-button {
    justify-content: center;
    font-size: 0 !important;
    gap: 0;
    padding-left: 8px !important;
    padding-right: 8px !important;
  }

  .ivory-is-collapsed .ivory-nav-icon {
    font-size: 20px !important;
  }

  .ivory-is-collapsed .ivory-sidebar
  > div:not(.ivory-collapse-control) {
    min-width: 0;
  }

  .ivory-is-collapsed .ivory-sidebar
  .text-xl {
    font-size: 0 !important;
  }

  .ivory-is-collapsed .ivory-sidebar
  .text-xl::before {
    content: "S";
    display: block;
    font-size: 24px;
    font-weight: 800;
    text-align: center;
    color: #8e724b;
  }

  .ivory-is-collapsed .ivory-sidebar
  .text-xs {
    font-size: 0 !important;
  }

  .ivory-is-collapsed .ivory-collapse-control {
    justify-content: center;
    padding-left: 0;
    padding-right: 0;
  }
}

/* Warm header and refined surfaces */
.ivory-app header {
  border-color: #eae2d5;
}

.ivory-app main {
  min-width: 0;
}

.ivory-app input:focus,
.ivory-app select:focus,
.ivory-app textarea:focus {
  outline-color: #b59b72;
}

/* Administrator visual treatment */
.ivory-app header button,
.ivory-app header [role="button"] {
  border-radius: 13px;
  transition:
    background .2s ease,
    box-shadow .2s ease;
}

.ivory-app header button:hover {
  box-shadow:
    0 3px 5px rgba(93,73,45,.04),
    0 5px 8px rgba(93,73,45,.04),
    0 8px 13px rgba(93,73,45,.03);
}

@media (max-width: 1023px) {
  .ivory-sidebar {
    width: 288px !important;
    max-width: 85vw !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ivory-sidebar,
  .ivory-sidebar button {
    transition: none !important;
  }
}
</style>


<style>
/* SERVICING OS IVORY BUTTON SYSTEM V6.12 */

.ivory-app {
  --ivory-body: #f8f6f0;
  --ivory-surface: #fffefa;
  --ivory-hover: #f3eddf;
  --ivory-active: #e8dcc6;
  --ivory-border: #e5dcce;
  --ivory-text: #554a3b;
  --ivory-muted: #81735e;
  --ivory-primary: #756247;
  --ivory-primary-hover: #645139;
  --ivory-radius: 12px;
}

/* Consistent body and panel surfaces */
.ivory-app main {
  background: var(--ivory-body);
}

.ivory-app main section {
  border-color: var(--ivory-border);
}

.ivory-app main .bg-white {
  background-color: var(--ivory-surface);
}

/* Unified button dimensions and shape */
.ivory-app main button:not(.sr-toolbar button),
.ivory-app aside button {
  border-radius: var(--ivory-radius);
  font-family: inherit;
  font-weight: 600;
  letter-spacing: 0.005em;
  transition:
    background-color 180ms ease,
    color 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

/* Neutral buttons */
.ivory-app main button[class*="bg-white"],
.ivory-app main button[class*="bg-slate-"],
.ivory-app main button[class*="border"]:not([class*="bg-blue-"]):not([class*="bg-green-"]):not([class*="bg-emerald-"]) {
  background: var(--ivory-surface) !important;
  color: var(--ivory-text) !important;
  border: 1px solid var(--ivory-border) !important;
  box-shadow:
    0 2px 5px rgba(84,67,42,.025),
    0 5px 8px rgba(84,67,42,.02) !important;
}

/* Active operation tabs and secondary actions */
.ivory-app main button[class*="bg-blue-600"],
.ivory-app main button[class*="bg-blue-100"],
.ivory-app main button[class*="bg-indigo-"] {
  background: var(--ivory-active) !important;
  color: #59452d !important;
  border: 1px solid #d8c7aa !important;
  box-shadow:
    0 2px 5px rgba(93,73,42,.035),
    0 5px 8px rgba(93,73,42,.025),
    0 8px 13px rgba(93,73,42,.02) !important;
}

/* Main save, print, and confirmation actions */
.ivory-app main button[class*="bg-blue-700"],
.ivory-app main button[class*="bg-green-"],
.ivory-app main button[class*="bg-emerald-"] {
  background: var(--ivory-primary) !important;
  color: #ffffff !important;
  border: 1px solid var(--ivory-primary) !important;
  box-shadow:
    0 2px 5px rgba(79,60,37,.06),
    0 5px 8px rgba(79,60,37,.045),
    0 8px 13px rgba(79,60,37,.025) !important;
}

/* Hover interactions */
@media (hover: hover) {
  .ivory-app main button[class*="bg-blue-700"]:hover,
  .ivory-app main button[class*="bg-green-"]:hover,
  .ivory-app main button[class*="bg-emerald-"]:hover {
    background: var(--ivory-primary-hover) !important;
    border-color: var(--ivory-primary-hover) !important;
    transform: translateY(-1px);
  }

  .ivory-app main button[class*="bg-white"]:hover,
  .ivory-app main button[class*="bg-slate-"]:hover,
  .ivory-app main button[class*="bg-blue-600"]:hover {
    background: var(--ivory-hover) !important;
    transform: translateY(-1px);
  }
}

/* Consistent operation navigation buttons */
.ivory-app main button[class*="px-4"][class*="py-3"] {
  min-height: 44px;
  padding: 11px 16px;
  line-height: 1.35;
  text-align: center;
}

/* Inputs aligned with the same visual language */
.ivory-app main input,
.ivory-app main select,
.ivory-app main textarea {
  border-radius: 11px;
  border-color: var(--ivory-border);
}

.ivory-app main input:focus,
.ivory-app main select:focus,
.ivory-app main textarea:focus {
  border-color: #b9a17b;
  outline-color: #b9a17b;
}

/* Refined panels */
.ivory-app main .rounded-xl,
.ivory-app main .rounded-2xl {
  border-color: var(--ivory-border);
}

/* Disabled actions */
.ivory-app main button:disabled {
  opacity: .48;
  cursor: not-allowed;
  transform: none !important;
}

/* Keyboard accessibility */
.ivory-app button:focus-visible {
  outline: 2px solid #a78b60;
  outline-offset: 3px;
}

/* Preserve mobile usability */
@media (max-width: 640px) {
  .ivory-app main button {
    min-height: 42px;
  }
}

/* Printing must remain unaffected */
@media print {
  .ivory-app main button {
    box-shadow: none !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ivory-app button {
    transition: none !important;
    transform: none !important;
  }
}
</style>


<style>
/* SERVICING PROFILE AND SIDEBAR FIX 6.13 */

.ivory-sidebar {
  display: flex !important;
  flex-direction: column !important;
  overflow-x: hidden;
}

.ivory-sidebar nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.ivory-nav-button {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  white-space: nowrap;
  overflow: hidden;
}

.ivory-nav-icon {
  flex: 0 0 24px !important;
  width: 24px !important;
  font-size: 19px !important;
  line-height: 1 !important;
}

.ivory-nav-label {
  display: inline-block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (min-width: 1024px) {
  .ivory-sidebar {
    width: 240px !important;
    min-width: 240px !important;
    max-width: 240px !important;
  }

  .ivory-is-collapsed .ivory-sidebar {
    width: 76px !important;
    min-width: 76px !important;
    max-width: 76px !important;
  }

  .ivory-is-collapsed .ivory-nav-button {
    justify-content: center !important;
    padding: 12px 8px !important;
    gap: 0 !important;
  }

  .ivory-is-collapsed .ivory-nav-label {
    display: none !important;
  }

  .ivory-is-collapsed .ivory-nav-icon {
    display: inline-flex !important;
    font-size: 20px !important;
  }

  .ivory-is-collapsed .ivory-sidebar nav {
    padding-left: 10px;
    padding-right: 10px;
  }

  .ivory-is-collapsed .ivory-sidebar
  .text-xl::before {
    content: "S";
  }
}

/* Administrator profile */
.servicing-profile {
  position: relative;
  z-index: 30;
}

.servicing-profile-trigger {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 7px 11px;
  border: 1px solid #e6ddce;
  border-radius: 15px;
  background: #fffdf8;
  color: #564632;
  min-height: 54px;
  box-shadow:
    0 2px 5px rgba(78,62,39,.035),
    0 5px 8px rgba(78,62,39,.025),
    0 8px 13px rgba(78,62,39,.02);
  transition: background .2s, box-shadow .2s;
}

.servicing-profile-trigger:hover {
  background: #f5efe4;
}

.servicing-avatar {
  width: 37px;
  height: 37px;
  flex: 0 0 37px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #e8dac1;
  color: #725635;
  font-size: 13px;
  font-weight: 800;
}

.servicing-profile-identity {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
  line-height: 1.35;
}

.servicing-profile-identity strong {
  font-size: 13px;
  font-weight: 700;
  max-width: 150px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.servicing-profile-identity small {
  font-size: 11px;
  color: #95856d;
}

.servicing-profile-menu {
  position: absolute;
  top: calc(100% + 9px);
  right: 0;
  width: 230px;
  padding: 7px;
  background: #fffdf8;
  border: 1px solid #e6ddce;
  border-radius: 16px;
  box-shadow:
    0 5px 8px rgba(75,57,34,.04),
    0 8px 13px rgba(75,57,34,.05),
    0 13px 21px rgba(75,57,34,.05);
}

.servicing-profile-menu-header {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px;
  color: #564632;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.servicing-profile-menu-header span {
  color: #95856d;
  font-size: 11px;
}

.servicing-profile-menu button {
  width: 100%;
  display: block;
  text-align: left;
  padding: 11px 12px;
  border-radius: 10px;
  font-size: 13px;
  color: #564632;
}

.servicing-profile-menu button:hover {
  background: #f1e8d9;
}

.servicing-profile-separator {
  height: 1px;
  background: #eae1d3;
  margin: 6px 3px;
}

.servicing-profile-menu .servicing-logout {
  color: #9c453c;
}

@media (max-width: 640px) {
  .servicing-profile-identity {
    display: none;
  }

  .servicing-profile-trigger {
    padding: 6px 8px;
  }

  .servicing-profile-menu {
    right: 0;
  }
}
</style>



<style>
/* SERVICING_STABLE_SIDEBAR_V4_20261110 : desktop header alignment */
@media (min-width: 1024px) {
  .ivory-app main > header,
  .ivory-app main > div > header {
    height: 76px;
    min-height: 76px;
    max-height: 76px;
    box-sizing: border-box;
    display: flex;
    flex-wrap: nowrap;
    gap: 12px;
    border-bottom: 1px solid #e5dfd4 !important;
  }
  .ivory-app main > header > input,
  .ivory-app main > div > header > input {
    flex: 1 1 150px;
    min-width: 100px;
    width: auto;
    max-width: 340px;
  }
}
</style>

<style>
/* SERVICING_NAV_WORKSPACES_621_623 — only hide the older workspace when a new one is selected */
main:has(> .sos-ext-root) > :not(.sos-ext-root) { display: none !important; }
main > .sos-ext-root { display: block; width: 100%; min-width: 0; }
</style>

<style>
/* SERVICING_SERVICE_JOBS_ITEM_FIX_624B */
main:has(> .sos-servicejobs-root) > :not(.sos-servicejobs-root) {display:none!important}
main > .sos-servicejobs-root {display:block!important;min-width:0;width:100%}
main > .sos-item-quick-624B {display:contents!important}
.sos-item-quick-624B .si-wrap {position:fixed;right:25px;bottom:25px;z-index:9000;display:flex;flex-direction:column;align-items:flex-end;gap:8px;width:auto;max-width:calc(100vw - 40px)}
.sos-item-quick-624B .si-launch {box-shadow:0 10px 28px rgba(60,42,21,.17);min-height:47px;font-size:13px}
.sos-item-quick-624B .si-backdrop {position:fixed;inset:0;z-index:100000}
@media(max-width:550px){.sos-item-quick-624B .si-wrap{right:12px;bottom:12px}.sos-item-quick-624B .si-launch{font-size:11px;padding:10px 11px}}
</style>

<style>
/* SERVICING_COUNTER_REPORTS_LOGIN_626 */
.sos626-counter-entry{background:#fffdf8;padding:12px 17px;border-bottom:1px solid #e7d9c6;display:flex;align-items:center;flex-wrap:wrap;gap:15px;color:#806b50;font-size:12px}
.sos626-sale-button{background:#73593b;color:#fff;padding:13px 18px;border:0;border-radius:11px;cursor:pointer;font-size:14px;font-weight:800;box-shadow:0 4px 14px #4c361c24}
.sos626-sale-button:hover{background:#60472d}
main:has(> .sos-fin-reports)>:not(.sos-fin-reports){display:none!important}
main>.sos-fin-reports{display:block!important;width:100%;min-width:0}
@media print{.sos626-counter-entry{display:none!important}}
</style>

<style>
/* SOS_632_RECEIPT_PRINT_CENTER — styles only the new print action. */
.sos632-sticker-action{appearance:none;background:#705137!important;color:#fff!important;border:1px solid #705137!important;border-radius:10px!important;padding:11px 16px!important;min-height:44px!important;font-weight:750!important;font-size:13px!important;cursor:pointer!important;transition:background .15s ease,box-shadow .15s ease}
.sos632-sticker-action:hover{background:#5b422c!important;box-shadow:0 3px 12px #5b422c20}
.sos632-sticker-action:focus-visible{outline:3px solid #c8a477;outline-offset:3px}
@media print{.sos632-sticker-action{display:none!important}}
</style>

<style>
/* SOS_636C_HIDE_LEGACY_PREVIEW: legacy hard-coded Counter preview, not the live KPI cards */
.sos636c-obsolete-preview{display:none!important}
</style>


<!-- S44_NATIVE_COUNTER_RECEIVE: modal presentation only; the existing Counter form remains untouched -->
<style>
.s44-receive-layer:not(.s44-receive-open),
.s44-receive-layer:not(.s44-receive-open) > .s44-receive-shell { display: contents; }
.s44-receive-layer.s44-receive-open {
  position: fixed; inset: 0; z-index: 9900; overflow-y: auto; display: flex;
  align-items: flex-start; justify-content: center; padding: clamp(10px, 3vw, 32px);
  background: rgba(36, 32, 27, .52); backdrop-filter: blur(3px);
}
.s44-receive-open .s44-receive-shell {
  width: min(940px, 100%); margin: auto; max-height: calc(100vh - 24px); overflow-y: auto;
  background: var(--card, #fffcf6); color: var(--text, #352f28);
  border: 1px solid var(--border, #e3dacf); border-radius: 17px;
  box-shadow: 0 30px 90px rgba(32,26,19,.25);
}
.s44-receive-header { display: flex; justify-content: space-between; align-items: flex-start;
  gap: 14px; padding: 22px 26px 18px; border-bottom: 1px solid #e9e1d5; }
.s44-receive-eyebrow { font-size: 10px; letter-spacing: .12em; font-weight: 750; color: #8f795a; }
.s44-receive-header h2 { margin: 5px 0 0; font-size: 21px; font-weight: 750; }
.s44-receive-header h2 small { font-size: 14px; font-weight: 500; }
.s44-receive-header p { margin: 6px 0 0; font-size: 12px; color: #786e60; }
.s44-receive-close { cursor: pointer; border: 1px solid #ded5c8; border-radius: 9px;
  width: 36px; height: 36px; flex: none; font-size: 23px; line-height: 1;
  color: #54493d; background: #fffdf9; }
.s44-receive-close:disabled { cursor: not-allowed; opacity: .45; }
.s44-receive-open .s44-receive-shell > form { padding: 23px 26px 28px; }
@media (max-width: 620px) {
  .s44-receive-layer.s44-receive-open { padding: 6px; }
  .s44-receive-open .s44-receive-shell { max-height: calc(100dvh - 12px); }
  .s44-receive-header { padding: 16px; }
  .s44-receive-open .s44-receive-shell > form { padding: 16px; }
}
</style>

<style>

/* SERVICING_COUNTER_647: ivory compact operational workspace */
.servicing-counter-647 { min-width: 0; }
.servicing-counter-647 .counter-647-actions {
  display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px!important;
  margin-bottom:12px!important;align-items:stretch;
}
.servicing-counter-647 .counter-647-actions > button {
  min-width:0;min-height:66px;padding:10px 12px!important;border:1px solid #e5e0d7!important;
  border-radius:12px!important;background:#fffefa;color:#34473e;
  font-size:13px;line-height:1.35;text-align:left;font-weight:650;
  box-shadow:0 1px 2px rgba(42,54,45,.035);transition:background .15s,border-color .15s;
}
.servicing-counter-647 .counter-647-actions > button:hover {background:#edf3ed;border-color:#99b5a5!important;}
.servicing-counter-647 .counter-647-actions > button:focus-visible {outline:2px solid #315e49;outline-offset:2px;}
.servicing-counter-647 .counter-647-actions > button[class*="bg-blue"],
.servicing-counter-647 .counter-647-actions > button[class*="bg-slate-900"] {
  background:#294c3d!important;color:#fff!important;border-color:#294c3d!important;
}
.servicing-counter-647 .counter-647-actions > button[class*="bg-blue"]:hover {background:#1f3c30!important;}
.servicing-counter-647 .counter-647-actions > button {white-space:normal!important;}
.servicing-counter-647 .counter-647-actions + * {min-width:0;}
.servicing-counter-647 .counter-647-heading {margin-bottom:10px!important;}
.servicing-counter-647 .counter-647-heading h1 {font-size:18px!important;line-height:1.3!important;}
.servicing-counter-647 .counter-647-heading p {font-size:11px!important;margin-top:2px!important;}
.counter-647-status {
  display:flex!important;align-items:center!important;justify-content:flex-end;flex-wrap:wrap;
  gap:7px!important;padding:0!important;margin:0!important;background:transparent!important;
  border:0!important;box-shadow:none!important;font-size:11px!important;min-width:0;
}
.counter-647-status .font-semibold {font-size:11px!important;}
.counter-647-status .text-slate-500 {font-size:11px!important;}
.counter-647-status .rounded-full {flex-shrink:0;}
@media(max-width:920px){.servicing-counter-647 .counter-647-actions{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:560px){.counter-647-status{justify-content:flex-start;}.servicing-counter-647 .counter-647-actions > button{min-height:58px;padding:8px!important;}}

</style>

<!-- SERVICING_OS_COUNTER_655 -->

<style>
/* SERVICING_OS_COUNTER_655 — equal-height selects and warm-ivory form controls. */
.sos652-shell .sos652-workbody :is(select,input,textarea),
.sos653-embedded-module :is(select,input,textarea),
.sos649-original-workspace :is(select,input,textarea) {
 box-sizing:border-box!important; min-width:0; max-width:100%;
 border:1px solid #ddc8b5!important; background:#fffdfa!important;
 border-radius:9px!important; color:#3c2c25!important;
}
.sos652-shell .sos652-workbody select,
.sos653-embedded-module select,
.sos649-original-workspace select {
 width:100%!important; height:43px!important; min-height:43px!important;
 padding:9px 32px 9px 11px!important; line-height:22px!important;
 font-size:13px!important; appearance:auto!important;
}
.sos652-shell .sos652-workbody :is(input:not([type=checkbox]):not([type=radio]),textarea),
.sos649-original-workspace input:not([type=checkbox]):not([type=radio]) {min-height:43px;padding:9px 11px}
.sos652-shell .sos652-workbody label,.sos649-original-workspace label{min-width:0}
.sos652-shell .sos652-workbody :is(select,input,textarea):focus-visible {outline:2px solid #bd9274;outline-offset:1px}
/* Embedded native POS remains unmodified. New counter uses a focused product grid. */
</style>


<style>
/* SOS_RECEIVE_INLINE_TECH_HISTORY_682 — compact ivory form + right history. */
.sos682-aside,.sos682-aside *{box-sizing:border-box}
.sos682-aside{background:#fffcf7;border:1px solid #e6d7c8;border-radius:13px;padding:14px;color:#3c2c25;display:flex;flex-direction:column;gap:10px;min-width:0}
.sos682-aside-header{display:flex;align-items:start;justify-content:space-between;gap:8px}
.sos682-aside-header h2{font-weight:780;font-size:14px;margin:1px 0;color:#3c2c25}
.sos682-aside-header p{color:#8d735e;font-size:10px;line-height:1.4;margin:2px 0}
.sos682-eyebrow{font-size:9px;letter-spacing:.12em;font-weight:800;color:#987356}
.sos682-refresh{flex:0 0 30px;height:30px;border:1px solid #d9c1ab;border-radius:8px;background:#f6eadc;color:#754c36;font-size:18px}
.sos682-search-label{font-size:10px;font-weight:760;color:#7c604b}
.sos682-lookup{width:100%;max-width:none;min-width:0;height:37px;border:1px solid #d9c4b1;border-radius:9px;background:#fffdfa;padding:7px 10px;font-size:12px;color:#3c2c25}
.sos682-lookup:focus-visible{outline:2px solid #ac825d;outline-offset:1px}
.sos682-list-head{display:flex;justify-content:space-between;align-items:center;gap:8px;border-top:1px solid #ebdfd2;padding-top:9px;font-size:10px;color:#765b46}
.sos682-list-head span{font-weight:600;color:#998371}
.sos682-job-list{display:flex;flex-direction:column;gap:5px;min-width:0}
.sos682-job{display:flex;align-items:start;justify-content:space-between;gap:6px;padding:9px 8px;text-align:left;width:100%;border:1px solid #ece0d4;border-radius:9px;background:#fffaf4;color:#3c2c25;min-width:0}
.sos682-job:hover,.sos682-job.chosen{background:#f3e5d6;border-color:#b99474}
.sos682-job-main{min-width:0;display:flex;flex-direction:column;gap:2px}
.sos682-job-main strong{font-size:11px;white-space:normal;overflow-wrap:anywhere}
.sos682-job-main small{font-size:10px;color:#8d735e;overflow-wrap:anywhere;line-height:1.35}
.sos682-status{font-size:9px;font-weight:700;color:#70513d;background:#f1e4d7;padding:4px 5px;border-radius:6px;max-width:93px;flex:0 0 auto;line-height:1.2;text-align:center}
.sos682-pagination{display:flex;align-items:center;justify-content:space-between;gap:5px}
.sos682-pagination button{padding:6px 8px;border:1px solid #dfcbb9;border-radius:7px;background:#fffbf6;font-size:10px;color:#755239}
.sos682-pagination button:disabled{opacity:.42;cursor:not-allowed}
.sos682-pagination span{font-size:10px;color:#8d735e}
.sos682-printbox{margin-top:4px;background:#f7ede2;border:1px solid #e5d3c0;border-radius:11px;padding:11px;display:flex;flex-direction:column;gap:8px}
.sos682-print-title{display:flex;flex-direction:column;gap:3px}
.sos682-print-title strong{font-size:12px;color:#3d3027}
.sos682-print-title small{color:#8d735e;font-size:10px}
.sos682-current{font-size:11px;font-weight:750;color:#7a563e;overflow-wrap:anywhere;margin:0}
.sos682-print-actions{display:grid;grid-template-columns:minmax(0,1fr);gap:6px}
.sos682-print-actions button{min-height:35px;padding:8px 10px!important;border:1px solid #78543a;border-radius:8px;background:#805a3e!important;color:#fffaf5!important;font-size:11px;font-weight:750;line-height:1.2}
.sos682-print-actions button:nth-child(2){background:#fffaf3!important;color:#72513b!important;border-color:#d8bda8}
.sos682-print-actions button:disabled{opacity:.5;cursor:not-allowed}
.sos682-warning,.sos682-error{font-size:10px;color:#a44234;line-height:1.35}
.sos682-empty{color:#87715f;text-align:center;padding:12px 3px;font-size:11px}
.sos682-tech-field{display:flex!important;flex-direction:column;gap:2px;min-width:0}
.sos682-tech-label{font-size:11px;font-weight:650;color:#614b3b}
.sos682-tech-label small{font-size:10px;font-weight:400;color:#977e6c}
.sos649-original-workspace .sos682-receive-form{gap:9px!important}
.sos649-original-workspace .sos682-receive-form .grid{gap:9px!important}
.sos649-original-workspace .sos682-receive-form .field{margin-top:4px!important;min-height:35px!important;padding:7px 10px!important;font-size:12px!important;line-height:1.25!important;border-radius:8px!important}
.sos649-original-workspace .sos682-receive-form textarea.field{min-height:52px!important;resize:vertical}
.sos649-original-workspace .sos682-receive-form label{font-size:11px!important}
.sos649-original-workspace .sos682-receive-form :is(button[type=submit],button[type=button]){min-height:35px!important;padding:7px 12px!important;font-size:11px!important;border-radius:8px!important}
@media(max-width:800px){.sos682-aside{padding:11px}}
</style>

<style>/* SOS_RECEIVE_PRINT_STUDIO_683: compact technician refresh line. */
.sos683-technician-feedback{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:space-between;color:#927862;font-size:10px;margin-top:3px}
.sos683-technician-feedback .sos683-tech-retry{background:#f4e8dc!important;border:1px solid #dfc9b3!important;color:#6f4e35!important;border-radius:7px!important;padding:4px 9px!important;min-height:24px!important;font-size:10px!important}
.sos683-technician-feedback .sos683-tech-retry:disabled{opacity:.5}
</style>


<style>
/* SOS_COUNTER_RECEIVE_EDITOR_686 — scoped to Counter Service Receive UI */
.sos686-existing-head{border:1px solid #e3d2c1!important;background:#fbf6ee!important;border-radius:12px!important;padding:12px!important}
.sos686-existing-head .sos686-action-row{display:flex;flex-wrap:wrap;gap:7px;align-items:center}
.sos686-action-row button,.sos686-existing-head button{min-height:34px;padding:7px 12px!important;border-radius:9px!important;font-size:12px!important;font-weight:650!important}
.sos686-edit-action{color:#fffaf5!important;background:#805a3e!important;border:1px solid #805a3e!important}
.sos686-delete-action{color:#a0362a!important;background:#fff7f2!important;border:1px solid #e7b9a9!important}
.sos686-delete-action:disabled{opacity:.45;cursor:not-allowed}
.sos686-technician-select{width:100%!important;min-height:36px!important;background:#fffdf9!important;color:#3f3026!important}
.sos686-history-hint{font-size:11px!important;color:#84654e!important;line-height:1.5}
.sos686-form-message{padding:8px 12px;border:1px solid #e4d2bf;border-radius:8px;background:#fff9f0;color:#634c3b;font-size:11px}
.sos686-overlay{position:fixed;inset:0;z-index:2147483000;background:rgba(32,22,17,.50);display:flex;align-items:center;justify-content:center;padding:14px;box-sizing:border-box}
.sos686-modal{background:#fffaf4;color:#3b2b23;border:1px solid #dcc7b4;border-radius:16px;padding:23px;width:100%;max-width:440px;box-shadow:0 22px 65px #25150947;display:flex;flex-direction:column;gap:12px;box-sizing:border-box}
.sos686-modal h2{font-size:18px;font-weight:800;margin:0}.sos686-modal p{font-size:12px;line-height:1.6;margin:0;color:#78604d}
.sos686-modal label{font-size:12px;font-weight:650;display:flex;flex-direction:column;gap:7px}
.sos686-confirm-field{background:#fff;border:1px solid #d8c2ae;border-radius:9px;padding:10px;font-size:12px;width:100%;box-sizing:border-box;color:#3b2b23}
.sos686-error{color:#a02e27;font-size:12px}.sos686-modal-actions{display:flex;gap:8px;justify-content:flex-end}
.sos686-modal-actions button{min-height:36px;border:1px solid #d5bba8;border-radius:9px;padding:8px 13px;font-size:12px;font-weight:700;background:#fffaf4;color:#77563d}
.sos686-modal-actions .danger{background:#a2392d;border-color:#a2392d;color:white}.sos686-modal-actions button:disabled{opacity:.45;cursor:not-allowed}
</style>


<style>
/* SOS_COUNTER_RECEIVE_UX_687 — list-card controls and ivory edit action */
.sos682-job-list .sos687-job-card{display:flex;align-items:stretch;min-width:0;gap:6px;margin:0 0 7px;padding:6px;border:1px solid #e6d7c9;background:#fffdf9;border-radius:12px;transition:border-color .15s,box-shadow .15s}
.sos682-job-list .sos687-job-card.is-selected{border-color:#b28b6a;box-shadow:0 0 0 2px #b28b6a21}
.sos687-job-main{min-width:0;flex:1;display:flex;align-items:center;gap:8px;padding:6px 7px;text-align:left;background:transparent;border:0;color:#3e2d22;cursor:pointer}
.sos687-job-content{display:flex;flex:1;flex-direction:column;gap:3px;min-width:0}
.sos687-job-content strong{font-size:12px;font-weight:800;overflow-wrap:anywhere;color:#493221}
.sos687-job-content small{font-size:10px;color:#917762;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sos687-job-main .sos682-status{flex-shrink:0;font-size:10px}
.sos687-job-actions{display:flex;flex-shrink:0;align-items:center;gap:5px;padding-left:6px;border-left:1px solid #e9dccf}
.sos687-icon-btn{width:34px;height:34px;display:grid;place-items:center;flex-shrink:0;border-radius:9px!important;padding:7px!important;border:1px solid #e4d3c2;background:#fbf1e7;color:#725034;cursor:pointer;transition:background .15s,border-color .15s,transform .15s}
.sos687-icon-btn svg{display:block;width:17px;height:17px}
.sos687-icon-btn:hover{background:#f1e0cd;border-color:#bf997a;transform:translateY(-1px)}
.sos687-icon-btn:focus-visible{outline:3px solid #aa805e;outline-offset:2px}
.sos687-icon-delete{background:#fff6f1;border-color:#efd6cc;color:#a34839}
.sos687-icon-delete:hover{background:#fae9e3;border-color:#d9a99e}
.sos687-icon-btn:disabled,.sos687-job-main:disabled{opacity:.55;cursor:wait}
.sos687-primary-save{display:inline-flex!important;align-items:center;justify-content:center;gap:9px;min-height:40px!important;min-width:164px;border-radius:10px!important;border:1px solid #74543b!important;background:#79583f!important;color:#fffaf6!important;font-size:13px!important;font-weight:750!important;padding:9px 18px!important;box-shadow:0 4px 12px #67422818;transition:background .15s,transform .15s}
.sos687-primary-save:not(:disabled):hover{background:#5d4030!important;transform:translateY(-1px)}
.sos687-primary-save:disabled{opacity:.55;cursor:not-allowed}
.sos687-secondary{min-height:40px!important;border:1px solid #dac8b7!important;background:#fffaf4!important;color:#725741!important;border-radius:10px!important;padding:9px 14px!important;font-size:12px!important;font-weight:650!important}
.sos687-secondary:hover{background:#f5e8dc!important}
.sos687-edit-note{font-size:11px;color:#70523d;background:#f8eee3;border:1px solid #e6d5c3;border-radius:9px;padding:9px 11px;line-height:1.5}
.sos687-history-note{font-size:10px;color:#917560;line-height:1.45;margin-top:5px}
@media(max-width:540px){.sos687-job-main .sos682-status{display:none}.sos687-job-actions{gap:3px}.sos687-icon-btn{width:32px;height:32px}}
</style>


<style>
/* SOS_HISTORY_CARDS_688: sidebar-first layout; no vertical text or tall cards. */
.sos682-job-list{min-width:0!important;width:100%!important;max-width:100%!important;box-sizing:border-box!important}
.sos682-job-list .sos688-job-card{display:block!important;position:relative;box-sizing:border-box!important;width:100%!important;min-width:0!important;max-width:100%!important;height:auto!important;min-height:0!important;margin:0 0 8px!important;padding:10px 11px!important;background:#fffdf9!important;border:1px solid #e6d7c9!important;border-radius:12px!important;overflow:hidden!important;box-shadow:none;transition:background .15s,border-color .15s,box-shadow .15s}
.sos682-job-list .sos688-job-card.is-selected{border-color:#b28b6a!important;box-shadow:0 0 0 2px #b28b6a22!important}
.sos688-card-details{display:flex!important;flex-direction:column!important;align-items:stretch!important;text-align:left!important;gap:4px!important;width:100%!important;min-width:0!important;max-width:100%!important;height:auto!important;border:0!important;background:none!important;padding:0!important;margin:0!important;cursor:pointer!important;box-shadow:none!important;color:#493221!important}
.sos688-job-number{display:block!important;width:100%!important;min-width:0!important;max-width:100%!important;font-size:12px!important;font-weight:800!important;line-height:1.35!important;letter-spacing:.01em!important;white-space:nowrap!important;word-break:normal!important;overflow-wrap:normal!important;overflow:hidden!important;text-overflow:ellipsis!important;color:#493221!important}
.sos688-customer,.sos688-device{display:block!important;max-width:100%!important;min-width:0!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;word-break:normal!important;overflow-wrap:normal!important;font-size:11px!important;line-height:1.35!important;color:#8c735d!important}
.sos688-card-bottom{display:flex!important;justify-content:space-between!important;align-items:center!important;flex-wrap:wrap!important;gap:7px!important;width:100%!important;min-width:0!important;margin-top:9px!important;padding-top:8px!important;border-top:1px solid #f0e5da!important;box-sizing:border-box!important}
.sos688-status{display:inline-block!important;min-width:0!important;max-width:100%!important;flex:0 1 auto!important;font-size:10px!important;line-height:1.3!important;font-weight:700!important;color:#79563c!important;background:#f5eadf!important;border-radius:6px!important;padding:4px 7px!important;text-align:left!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
.sos688-actions{display:flex!important;flex:0 0 auto!important;align-items:center!important;gap:6px!important;margin-left:auto!important;padding:0!important;border:0!important}
.sos688-action{display:grid!important;place-items:center!important;flex:0 0 30px!important;width:30px!important;height:30px!important;min-width:30px!important;min-height:30px!important;padding:5px!important;border:1px solid #e3cebb!important;border-radius:8px!important;background:#fbf0e6!important;color:#78553c!important;line-height:1!important;cursor:pointer!important;box-shadow:none!important;transition:background .15s,border-color .15s}
.sos688-action svg{display:block!important;width:16px!important;height:16px!important;max-width:16px!important;max-height:16px!important}
.sos688-action:hover{background:#f2e1d1!important;border-color:#c4a286!important}
.sos688-action:focus-visible,.sos688-card-details:focus-visible{outline:2px solid #a37c5d!important;outline-offset:2px!important}
.sos688-delete{background:#fff6f2!important;border-color:#edd3ca!important;color:#ab4b3b!important}
.sos688-delete:hover{background:#fceae3!important;border-color:#d9aaa0!important}
.sos688-action:disabled,.sos688-card-details:disabled{opacity:.5!important;cursor:wait!important}
@media (max-width:360px){.sos688-job-number{font-size:11px!important}.sos688-card-bottom{gap:5px!important}.sos688-status{font-size:9px!important}}
</style>

<style>/* SOS_COUNTER_RECEIVE_REPAIR_689 */
.sos689-history-alert{border:1px solid #edc8bf;background:#fff4f0;color:#9d372a;border-radius:9px;padding:9px;font-size:11px;line-height:1.5;margin:9px 0;overflow-wrap:anywhere}
.sos689-parts-wrap{width:100%;min-width:0;max-width:100%}
</style>

<style>/* SOS_SERVICE_WORKFLOW_690 */
.sos690-jobs{display:grid;gap:12px}.sos690-parts-prompt{background:#fff8ef;border:1px dashed #dfc6af;color:#806149;padding:10px 12px;border-radius:10px;font-size:11px;margin:11px 0}
</style>

<style>
/* SOS_COUNTER_SPACING_693 — visual spacing only; no event or data changes. */
.sos649-original-workspace .sos682-receive-form,
.sos682-receive-form {min-width:0;max-width:100%;box-sizing:border-box}

/* Keep Discard Changes + Update Service Job together with consistent separation
   from the last field (normally Accessories Received). */
.sos682-receive-form :is(div,footer):has(> .sos687-primary-save){
  display:flex!important;align-items:center!important;justify-content:flex-end!important;
  flex-wrap:wrap!important;column-gap:12px!important;row-gap:10px!important;
  width:100%;margin-block:18px 0!important;padding:16px 0 0!important;
  border-top:1px solid #e6d7c8;box-sizing:border-box;
}
.sos682-receive-form :is(div,footer):has(> .sos687-primary-save) > :is(button,.sos687-primary-save,.sos687-secondary){
  margin:0!important;min-height:40px!important;
}

/* Exactly one aligned edge for Repair Progress and Parts Required. */
.sos649-original-workspace .sos690-jobs,
.sos690-jobs{display:grid!important;grid-template-columns:minmax(0,1fr)!important;
  gap:16px!important;width:100%;min-width:0;max-width:100%;
  margin:18px 0 0!important;padding:18px 0 0!important;
  border-top:1px solid #e6d7c8;box-sizing:border-box;
}
.sos690-jobs > :is(.sos690-steps,.sos689-parts){
  width:100%!important;min-width:0;max-width:100%;margin:0!important;
  box-sizing:border-box;
}
.sos690-jobs > .sos690-steps{padding:clamp(14px,2vw,18px)!important;container-type:inline-size}
.sos690-jobs .sos690-header{display:flex;align-items:flex-start!important;
  justify-content:space-between;gap:14px!important;margin:0 0 14px!important}
.sos690-jobs .sos690-header > div{min-width:0;flex:1}
.sos690-jobs .sos690-header h3{margin:4px 0 5px!important;line-height:1.25}
.sos690-jobs .sos690-header p{margin:0!important;max-width:55ch}
.sos690-jobs .sos690-current{margin:0 0 14px!important;padding:12px 14px!important;
  display:flex;align-items:center;gap:12px}
.sos690-jobs .sos690-stage-grid{display:grid!important;
  grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:10px!important}
.sos690-jobs .sos690-stage{min-height:70px!important;min-width:0;
  padding:11px 12px!important;justify-content:space-between;align-content:space-between}
.sos690-jobs .sos690-stage strong{line-height:1.4;overflow-wrap:normal;word-break:normal}
.sos690-jobs .sos690-action{display:grid!important;
  grid-template-columns:minmax(0,1fr) auto!important;align-items:center!important;
  column-gap:14px!important;row-gap:10px!important;
  margin-top:16px!important;padding-top:16px!important}
.sos690-jobs .sos690-action > span{min-width:0;line-height:1.5}
.sos690-jobs .sos690-action > button{min-height:40px;white-space:nowrap;margin:0!important}
.sos690-jobs .sos690-help{margin:14px 0 0!important;line-height:1.6}

@container (max-width:560px){
  .sos690-jobs .sos690-stage-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@container (max-width:370px){
  .sos690-jobs .sos690-action{grid-template-columns:minmax(0,1fr)!important}
  .sos690-jobs .sos690-action > button{width:100%}
  .sos690-jobs .sos690-header{flex-wrap:wrap}
}
@media(max-width:540px){
  .sos682-receive-form :is(div,footer):has(> .sos687-primary-save) > button{
    flex:1 1 145px;min-width:0}
}
</style>

<style>
/* SOS_DEVICE_COMPONENTS_694 — make the actual receive grid four equal columns when its container has room. */
.sos682-receive-form{container-type:inline-size;container-name:sos694-form}
.sos682-receive-form .sos694-four{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:11px!important;align-items:start}
.sos682-receive-form .sos694-four > *{min-width:0}
.sos682-receive-form .sos694-four > .sm\:col-span-2{grid-column:1/-1!important}
@container sos694-form (min-width:530px){.sos682-receive-form .sos694-four{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@container sos694-form (min-width:770px){.sos682-receive-form .sos694-four{grid-template-columns:repeat(4,minmax(0,1fr))!important}}
.sos682-receive-form .sos694-four :is(label, input, select){max-width:100%;min-width:0}
</style>

<!-- SOS_RECENT_PRINT_V23: screen-only styling, never changes printed receipt -->
<style>
.sos688-job-card { position:relative; }
.sos688-job-card > .sos688-card-details {box-sizing:border-box;padding-right:0!important;}
/* SOS_RECEIVED_COMPONENTS_PRINT_V24: printer uses the same 30px action style as edit/delete. */
.sos688-actions > .sos23-recent-print{flex:0 0 30px!important;width:30px!important;height:30px!important;min-width:30px!important;min-height:30px!important;padding:5px!important;border-radius:8px!important}
.sos688-actions > .sos23-recent-print svg{width:16px!important;height:16px!important}
@media print {.sos688-actions > .sos23-recent-print{display:none!important}}
</style>
