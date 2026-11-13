<script setup>
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
	activeNav.value = item;
	message.value = "";
}


function resetServiceForm() {
  resetCustomerSearch();
  deviceType.value = "Laptop";
  brand.value = "";
  model.value = "";
  serialNumber.value = "";
  problem.value = "";
  accessories.value = "";
  priority.value = "Normal";
  estimatedCost.value = "";
  message.value = "";
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

    selectedCustomerId.value = "";
    customer.value = job.customer_name || "";
    mobile.value = job.mobile || "";

    deviceType.value = job.device_type || "Laptop";
    brand.value = job.brand || "";
    model.value = job.device_model || "";
    serialNumber.value = job.serial_number || "";
    problem.value = job.reported_problem || "";
    accessories.value = job.accessories_received || "";
    priority.value = job.priority || "Normal";
    estimatedCost.value = String(job.estimated_cost ?? "");

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
    message.value =
      "This is an existing Service Job. Select New Service Receive to create another job.";
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
      priority: priority.value,
      estimated_cost: Number(estimatedCost.value || 0)
    });

    message.value = "Service Job " + result.service_job + " saved successfully!";
    receiptJobNumber.value = result.service_job;
    await openServiceReceipt(result.service_job);
    if (receiptError.value) message.value += " Receipt: " + receiptError.value;

    await refreshDashboard();

    resetCustomerSearch();

    deviceType.value = "Laptop";
    brand.value = "";
    model.value = "";
    serialNumber.value = "";
    problem.value = "";
    accessories.value = "";
    priority.value = "Normal";
    estimatedCost.value = "";

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
</script>

<template>
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
<div v-if="activeNav === 'Inventory' && (typeof repairManagementOpen === 'undefined' || !repairManagementOpen)" class="sos-item-quick-624B">
  <StockQuickAdd @changed="sosStockChanged624B" />
</div>

<!-- SERVICING_NAV_WORKSPACES_621_623: standalone workspace screens -->
<CustomerWorkspace v-if="activeNav === 'Customers'" />
<UsedLaptopWorkspace v-if="activeNav === 'Used Laptops'" />
<SettingsWorkspace v-if="activeNav === 'Settings'" />
<ServiceShopWorkspace v-if="activeNav === 'Service Shop' || activeNav === 'Servicing Shop'" @navigate="sosNavigateFromShop" />


<RetailSales v-if="activeNav === 'New Sales' && !repairManagementOpen" />

<OwnerReports v-if="activeNav === 'Reports' && !repairManagementOpen" />

<StockManagement v-if="activeNav === 'Inventory' && !repairManagementOpen" />

<RepairManagement v-if="repairManagementOpen" @close="repairManagementOpen = false" />
<div v-show="(!repairManagementOpen && activeNav !== 'Inventory' && activeNav !== 'Reports') && activeNav !== 'New Sales'">

			<header
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

			</header>

			<div class="p-3 sm:p-5 lg:p-7 space-y-4 sm:space-y-6 min-w-0">
				<div
					class="flex flex-wrap items-center gap-3 rounded-xl border bg-white px-4 py-3 text-sm"
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

				<section class="flex flex-wrap justify-between gap-4 items-start">
					<div>
						<h1 class="text-2xl font-bold text-slate-900">
							{{ title }}
						</h1>
						<p class="text-sm text-slate-500 mt-1">
							Sales · Service Receive · Delivery · Billing
						</p>
					</div>
				</section>

				<div class="grid grid-cols-2 xl:grid-cols-4 gap-2 sm:gap-4 sos636c-obsolete-preview">
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

				<section v-if="activeNav === 'Counter'" class="sos627-counter-root">
<CounterWorkspace627 :tab="sos627Tab" @select="sos627Choose" />

					<div class="flex flex-wrap gap-2 mb-5 sos627-old-operations">
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

							<form :class="{ 'existing-job-view': viewingServiceJob }"
								v-if="activeOperation === 'Service Receive'"
								@submit.prevent="submitDemo"
								class="space-y-4"
							>

<div
  v-if="viewingServiceJob && viewedServiceJob"
  class="rounded-xl border border-blue-200
         bg-blue-50 p-4 sm:p-5 space-y-4"
>
  <div class="flex flex-col sm:flex-row
              sm:items-center sm:justify-between gap-3">
    <div>
      <p class="text-xs font-bold uppercase text-blue-700">
        Existing Service Job — View Only
      </p>

      <h3 class="mt-1 break-all text-xl font-bold text-slate-900">
        {{ viewedServiceJob.name }}
      </h3>

      <p class="mt-1 text-sm text-slate-600">
        Status: {{ viewedServiceJob.status || "Unknown" }}
        · Priority: {{ viewedServiceJob.priority || "Normal" }}
      </p>
    </div>

    <div class="flex flex-wrap gap-2">
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


<div class="rounded-xl border border-blue-200 bg-blue-50 p-3 sm:p-4 space-y-2">
  <p class="text-sm font-semibold text-blue-900">Service Receipt Printing</p>
  <div class="flex flex-col sm:flex-row gap-2">
    <input v-model="receiptJobNumber" type="text" placeholder="Enter Service Job number"
      aria-label="Service Job number" class="w-full min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-3 text-sm text-slate-900" />
    <button type="button" :disabled="receiptLoading"
      class="rounded-lg bg-blue-700 px-4 py-3 font-semibold text-white disabled:opacity-50"
      @click="openServiceReceipt(receiptJobNumber)">
      {{ receiptLoading ? "Loading..." : "Print / Reprint Receipt" }}
    </button>
    <!-- SOS_632_RECEIPT_PRINT_CENTER: sticker action in the existing print section. -->
    <button type="button" class="sos632-sticker-action" @click="sos632PrintQrSticker">Print QR Sticker</button>

  </div>
  <p v-if="receiptError" class="text-sm text-red-700">{{ receiptError }}</p>
</div>

								<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
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
    v-if="selectedCustomerId"
    class="rounded-lg border border-green-200 bg-green-50 px-3 py-3 text-sm text-green-800"
  >
    Existing Customer selected:
    <strong>{{ customer }}</strong>
  </div>

  <div
    v-else-if="customerSearchOpen && customerSearchTerm.length >= 2"
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

								<div class="flex flex-wrap justify-end gap-3 pt-3">
									<button
										type="button" @click="resetServiceForm"
										class="px-5 py-3 rounded-lg border text-slate-600"
									>
										Reset
									</button>
									<button
										type="submit"
										class="px-5 py-3 rounded-lg bg-blue-600 text-white font-medium"
									>
										Receive Job
									</button>
								</div>

								<p
									v-if="message"
									class="text-sm text-amber-700 bg-amber-50 p-3 rounded-lg"
								>
									{{ message }}
								</p>
							</form>

							<div v-else class="py-20 text-center text-slate-500">
								{{ activeOperation }} will be implemented in its own milestone.
							</div>
						</section>

						<section class="xl:col-span-3 space-y-5">
							<div class="bg-white border rounded-xl p-5">
								<h2 class="font-bold text-slate-900">Customer Service History</h2>
								<p class="text-sm text-slate-500 mt-5">
									Select a customer to view previous repairs.
								</p>
							</div>

							<div class="bg-white border rounded-xl p-5">
  <div class="flex items-center justify-between gap-3">
    <h2 class="font-bold text-slate-900">
      Recent Service Jobs
    </h2>

    <button
      type="button"
      @click="refreshDashboard"
      :disabled="dashboardLoading"
      class="text-xs px-3 py-2 rounded-lg border hover:bg-slate-50 disabled:opacity-50"
    >
      {{ dashboardLoading ? "Loading..." : "Refresh" }}
    </button>
  </div>

  <p
    v-if="dashboardError"
    class="text-xs text-red-700 bg-red-50 p-3 rounded-lg mt-3"
  >
    {{ dashboardError }}
  </p>

  <div v-if="recentServiceJobs.length" class="mt-4 space-y-3">
    <div
       role="button"
       tabindex="0"
       aria-label="Open Service Job"
       @click="openExistingJobInForm(job.name)"
       @keydown.enter.prevent="openExistingJobInForm(job.name)"
       @keydown.space.prevent="openExistingJobInForm(job.name)"
      v-for="job in recentServiceJobs"
      :key="job.name"
      class="cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 border rounded-lg p-3 hover:bg-slate-50"
    >
      <div class="flex justify-between items-start gap-3">
        <div class="min-w-0">
          <div class="text-sm font-bold text-blue-700">
            {{ job.name }}
          </div>

          <div class="text-sm font-medium text-slate-800 mt-1">
            {{ job.customer_name }}
          </div>

          <div class="text-xs text-slate-500">
            {{ job.mobile }}
          </div>

          <div class="text-xs text-slate-600 mt-2">
            {{ [job.brand, job.device_model].filter(Boolean).join(" ") || job.device_type }}
          </div>
        </div>

        <div class="text-right shrink-0">
          <span
            class="inline-block text-xs px-2 py-1 rounded-full font-medium"
            :class="serviceJobStatusClass(job.status)"
          >
            {{ job.status }}
          </span>

          <div class="text-xs text-slate-500 mt-2">
            {{ job.priority }}
          </div>
        </div>
      </div>
    </div>
  </div>

  <p
    v-else
    class="text-sm text-slate-500 mt-5"
  >
    {{
      dashboardLoading
        ? "Loading service jobs..."
        : "No service jobs found."
    }}
  </p>
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
				</section>

				<section v-else class="bg-white border rounded-xl p-10 text-center">
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
