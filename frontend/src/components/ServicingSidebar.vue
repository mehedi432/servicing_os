<script setup>
import { currentLanguage, setLanguage } from '../i18n/servicingLanguage.js'
import { computed, onMounted, ref, watch } from 'vue';

// SERVICING_STABLE_SIDEBAR_V4_20261110
const props = defineProps({
  items: { type: Array, default: () => [] },
  active: { type: String, default: 'Counter' },
  repairOpen: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
  salesSection: { type: String, default: 'New Sale' },
  counterInvoices: { type: Boolean, default: false }
});
const emit = defineEmits(['navigate', 'repair', 'close-mobile']);
const compact = ref(false);
const STORAGE_KEY = 'servicing-os-sidebar-compact-v4';

onMounted(() => {
  try { compact.value = localStorage.getItem(STORAGE_KEY) === '1'; }
  catch (_) { /* Storage disabled: sidebar still works. */ }
});

function toggle() {
  compact.value = !compact.value;
  try { localStorage.setItem(STORAGE_KEY, compact.value ? '1' : '0'); }
  catch (_) { /* Storage disabled: no impact on toggling. */ }
}

// SERVICING_NAVBAR_6452: preserve parent-provided items and existing navigation events.
const menuItems = computed(() => {
  const entries = [...(props.items || [])].filter(x => x && x !== 'Repair Management');
  const index = entries.indexOf('Service Jobs');
  if (index >= 0) entries.splice(index + 1, 0, 'Repair Management');
  else entries.push('Repair Management');
  if (!entries.includes('Suppliers')) {
    const position = entries.indexOf('Customers');
    if (position >= 0) entries.splice(position + 1, 0, 'Suppliers');
    else entries.push('Suppliers');
  }
  return entries;
});
function choose(item) {
  if (item === 'Repair Management') emit('repair');
  else emit('navigate', item);
  emit('close-mobile');
}

const ICON = {
  'Suppliers': ['M1 5h13v12H1z','M14 9h4l4 4v4h-8z','M8 19a2 2 0 1 1-4 0 2 2 0 0 1 4 0','M21 19a2 2 0 1 1-4 0 2 2 0 0 1 4 0'],

  'Counter': ['M3 3h8v8H3z','M13 3h8v5h-8z','M13 10h8v11h-8z','M3 13h8v8H3z'],
  'New Sales': ['M3 4h2l2.4 11h11.5l2-8H6','M9 20h.01','M18 20h.01'],
  'Invoices': ['M6 3h12v18l-3-2-3 2-3-2-3 2z','M9 8h6','M9 12h6','M9 16h4'],
  'Used Laptops': ['M4 5h16v12H4z','M2 21h20','M8 17l-1 4','M16 17l1 4'],
  'Service Jobs': ['M8 4H6a2 2 0 0 0-2 2v14h16V6a2 2 0 0 0-2-2h-2','M9 4a3 3 0 0 1 6 0v2H9z','M8 13h8','M8 17h5'],
  'Repair Management': ['M14 7l3 3','M5 19l7-7','M14.4 3.7a5 5 0 0 0-6.7 6.7L3 15l6 6 4.7-4.7a5 5 0 0 0 6.7-6.7l-3.4 2-4-4z'],
  'Customers': ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2','M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8','M22 21v-2a4 4 0 0 0-3-3.87','M16 3.13a4 4 0 0 1 0 7.75'],
  'Inventory': ['M3 7l9-4 9 4-9 4z','M3 7v10l9 4 9-4V7','M12 11v10'],
  'Reports': ['M4 20V10','M10 20V4','M16 20v-7','M22 20H2'],
  'Settings': ['M4 7h16','M4 17h16','M9 4v6','M15 14v6'],
};
function iconPaths(item) { return ICON[item] || ['M4 4h16v16H4z']; }
function isActive(item) {
  return item === 'Repair Management' ? props.repairOpen :
    (!props.repairOpen && props.active === item);
}

// SERVICING_NAVBAR_646: only expose entries already provided by the parent.
const menuSearch = ref('');
const menuGroups = [
  { id: 'workspace', label: 'WORKSPACE', entries: ['Overview','Counter','New Sales','Service Jobs','Repair Management'] },
  { id: 'inventory', label: 'INVENTORY & CUSTOMERS', entries: ['Used Laptops','Inventory','Customers','Suppliers'] },
  { id: 'management', label: 'MANAGEMENT', entries: ['Reports','Settings'] }
];
const filteredGroups = computed(() => {
  const available = menuItems.value;
  const q = menuSearch.value.trim().toLocaleLowerCase();
  const seen = new Set();
  const groups = menuGroups.map(group => {
    const entries = group.entries.filter(item => available.includes(item));
    entries.forEach(item => seen.add(item));
    return { ...group, entries: entries.filter(item => item.toLocaleLowerCase().includes(q) ||
      (item === 'Counter' && 'invoices'.includes(q))) };
  });
  const other = available.filter(item => !seen.has(item) && item.toLocaleLowerCase().includes(q));
  if (other.length) groups.push({ id:'other', label:'OTHER', entries:other });
  return groups.filter(group => group.entries.length);
});



// SOS_SALES_V3_PRESERVE_POS: additive submenu, never changes original choose(item)
const dropdownOpen = ref({ Counter: false, 'New Sales': false })
watch(() => props.counterInvoices, open => {
  if (open) dropdownOpen.value.Counter = true
}, { immediate: true })
const sosSalesChildren = [
  { en: "New Sale", bn: "নতুন বিক্রয়" },
  { en: "Sales History", bn: "বিক্রয় ইতিহাস" },
  { en: "Quotations", bn: "মূল্য প্রস্তাব" },
  { en: "Returns & Exchanges", bn: "ফেরত ও পরিবর্তন" },
  { en: "Payments & Dues", bn: "পেমেন্ট ও বকেয়া" },
  { en: "Sales Warranty", bn: "বিক্রয় ওয়ারেন্টি" },
  { en: "Sales Reports", bn: "বিক্রয় প্রতিবেদন" },
]
function toggleDropdown(item) {
  if (compact.value) toggle()
  const open = isDropdownOpen(item)
  if (item === 'Counter' && menuSearch.value.trim() && !'counter'.includes(menuSearch.value.trim().toLowerCase())) {
    menuSearch.value = ''
  }
  dropdownOpen.value[item] = !open
}
function isDropdownOpen(item) {
  return dropdownOpen.value[item] || (item === 'Counter' && !!menuSearch.value.trim() && 'invoices'.includes(menuSearch.value.trim().toLowerCase()))
}
function chooseChild(item, key) {
  choose((item === 'Counter' ? 'Counter: ' : 'Sales: ') + key)
}
function isCurrentChild(item, key) {
  return isActive(item) && (item === 'Counter' ? props.counterInvoices : props.salesSection === key)
}
function panelId(item) {
  return item === 'Counter' ? 'sos-counter-nav-panel' : 'sos-sales-nav-panel'
}

// SOS_SALES_UI_V3_2_DESCRIPTIONS — Navigation presentation only, no transaction code.
const sosSalesNavDetails = {
  'New Sale': { en: 'POS & checkout', bn: 'পস ও চেকআউট', paths: ['M3 4h2l2.2 10h11.8l2-7H6', 'M9 20h.01', 'M18 20h.01'] },
  'Sales History': { en: 'Invoices & receipts', bn: 'ইনভয়েস ও রসিদ', paths: ['M4 5h16v15l-4-2-4 2-4-2-4 2z','M8 9h8','M8 13h8'] },
  'Quotations': { en: 'Customer proposals', bn: 'ক্রেতার মূল্য প্রস্তাব', paths: ['M7 3h8l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z','M15 3v5h5','M9 13h6','M9 17h6'] },
  'Returns & Exchanges': { en: 'After-sales adjustments', bn: 'ফেরত ও পরিবর্তন', paths: ['M3 10h11a4 4 0 0 1 0 8h-2','m7 6-4 4 4 4','M21 14H10a4 4 0 0 1 0-8h2','m17 10 4 4-4 4'] },
  'Payments & Dues': { en: 'Collections & balances', bn: 'আদায় ও বকেয়া', paths: ['M3 6h18v12H3z','M3 10h18','M7 15h4'] },
  'Sales Warranty': { en: 'Coverage & expiry', bn: 'ওয়ারেন্টি ও মেয়াদ', paths: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z','m9 12 2 2 4-4'] },
  'Sales Reports': { en: 'Performance & insights', bn: 'বিক্রয় বিশ্লেষণ', paths: ['M4 20V11h4v9','M10 20V5h4v15','M16 20v-7h4v7','M3 20h18'] }
}

const dropdowns = {
  'New Sales': sosSalesChildren.map(child => ({ ...child, key: child.en, description: sosSalesNavDetails[child.en] })),
  Counter: [{
    key: 'Invoices',
    en: 'Invoices',
    bn: 'ইনভয়েস',
    description: { en: 'Register & reports', bn: 'রেজিস্টার ও রিপোর্ট', paths: ICON.Invoices }
  }]
}

</script>

<template>
  <aside class="sos4-sidebar"
         :class="{ 'sos4-compact': compact, 'sos4-mobile-open': mobileOpen }"
         aria-label="SERVICING OS navigation">
    <div class="sos4-brandbar">
      <div class="sos4-brand">
        <span class="sos4-logo" aria-hidden="true">S</span>
        <span class="sos4-brandwords">
          <strong>SERVICING <b>OS</b></strong>
          <small>Computer Shop ERP</small>
        </span>
      </div>
      <button type="button" class="sos4-toggle"
              :title="compact ? 'Expand sidebar' : 'Collapse sidebar'"
              :aria-label="compact ? 'Expand sidebar' : 'Collapse sidebar'"
              :aria-expanded="!compact"
              @click.stop="toggle">
        <svg viewBox="0 0 24 24" width="19" height="19" fill="none"
             stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M9 4v16"/>
          <path v-if="compact" d="m13 9 3 3-3 3"/>
          <path v-else d="m17 9-3 3 3 3"/>
        </svg>
      </button>
      <button class="sos4-close" type="button" @click.stop="emit('close-mobile')"
              aria-label="Close navigation">×</button>
    </div>
        <div class="sos4-scroll">
      <div class="sos646-search" v-show="!compact">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 4 4"/></svg>
        <input v-model="menuSearch" type="search" placeholder="Search menu..." aria-label="Search menu" autocomplete="off" />
      </div>
      <template v-for="group in filteredGroups" :key="group.id">
        <div class="sos4-group-label">{{ group.label }}</div>
        <nav class="sos4-nav" :aria-label="group.label">
          
<!-- SOS_SALES_V3_3_NATIVE_ROW -->
<template v-for="item in group.entries" :key="item">
  <div class="sosSalesWrap" :class="{'sosSalesOther':!dropdowns[item]}">
    <div class="sosSalesNavRow" :class="{'sosSalesNavParent':dropdowns[item]}">
<button   type="button" class="sos4-item"
                  :class="{ 'sos4-active': isActive(item) }"
                  :title="compact ? item : undefined" :aria-label="item"
                  :aria-current="isActive(item) && !(item === 'Counter' && counterInvoices) ? 'page' : undefined"
                  @click.stop="choose(item)">
            <svg class="sos4-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="(path,index) in iconPaths(item)" :key="index" :d="path" />
            </svg>
            <span class="sos4-label">{{ currentLanguage === 'bn' && item === 'Inventory' ? 'ইনভেন্টরি' : item }}</span>
          </button>
      <button v-if="dropdowns[item]" type="button" class="sosSalesExpand"
              :aria-label="(isDropdownOpen(item) ? 'Collapse ' : 'Expand ') + item"
              :title="(isDropdownOpen(item) ? 'Collapse ' : 'Expand ') + item"
              :aria-controls="panelId(item)" :aria-expanded="isDropdownOpen(item)"
              @click.stop="toggleDropdown(item)">
        <svg class="sosSalesChevron" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"
             fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
    </div>
    <Transition name="sosSalesSlide">
      <div v-if="dropdowns[item] && isDropdownOpen(item)" :id="panelId(item)"
           class="sosSalesNavPanel" role="group" :aria-label="item">
        <button v-for="child in dropdowns[item]" :key="child.key" type="button"
                class="sos4-item sosSalesChild"
                :class="{'sos4-active sosSalesChildCurrent':isCurrentChild(item, child.key)}"
                :aria-current="isCurrentChild(item, child.key) ? 'page' : undefined"
                @click.stop="chooseChild(item, child.key)">
          <svg class="sosSalesChildIcon" viewBox="0 0 24 24" width="19" height="19"
               fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="(path,index) in child.description.paths" :key="index" :d="path" />
          </svg>
          <span class="sosSalesChildText">
            <span class="sosSalesChildName">{{currentLanguage==='bn'?child.bn:child.en}}</span>
            <span class="sosSalesChildHelp">{{currentLanguage==='bn'?child.description.bn:child.description.en}}</span>
          </span>
        </button>
      </div>
    </Transition>
  </div>
</template>


        </nav>
      </template>
      <p v-if="!filteredGroups.length && !compact" class="sos646-empty">No matching sections</p>
    </div>
<!-- SERVICING_OS_LANGUAGE_637 : persistent sidebar language switch -->
    <div class="sos37-language" data-sos-language-control role="group" aria-label="Language / ভাষা">
      <div class="sos37-caption"><svg class="sos648-language-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 8 6 6"/><path d="m4 14 6-6 2-3H2"/><path d="M2 5h12"/><path d="M7 2v3"/><path d="m13 21 5-11 5 11"/><path d="M15 17h6"/></svg><span class="sos648-language-label">{{ currentLanguage === 'bn' ? 'ভাষা' : 'Language' }}</span></div>
      <div class="sos37-choices">
        <button type="button" class="sos37-choice"
                :class="{ 'sos37-selected': currentLanguage === 'en' }"
                :aria-pressed="currentLanguage === 'en'" title="English"
                @click.stop="setLanguage('en')">
          <span class="sos37-choice-full">EN</span><span class="sos37-choice-short">EN</span>
        </button>
        <button type="button" class="sos37-choice" lang="bn"
                :class="{ 'sos37-selected': currentLanguage === 'bn' }"
                :aria-pressed="currentLanguage === 'bn'" title="বাংলা"
                @click.stop="setLanguage('bn')">
          <span class="sos37-choice-full">বাংলা</span><span class="sos37-choice-short">বাং</span>
        </button>
      </div>
    </div>
    <div class="sos4-foot">
      <span class="sos4-foot-dot" aria-hidden="true"></span>
      <span class="sos4-foot-text">SERVICING OS · Workspace</span>
    </div>
  </aside>
</template>

<style scoped>
.sos4-sidebar, .sos4-sidebar * { box-sizing: border-box; }
.sos4-sidebar {
  --sos4-border: #e5dfd4;
  position: fixed;
  z-index: 75;
  inset: 0 auto 0 0;
  width: min(280px, 86vw);
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  color: #554b40;
  background: #fbfaf7;
  border-right: 1px solid var(--sos4-border);
  box-shadow: 5px 0 20px rgba(45,36,25,.06);
  transform: translateX(-103%);
  transition: transform .2s ease, width .2s ease, flex-basis .2s ease;
}
.sos4-sidebar.sos4-mobile-open { transform: translateX(0); }
.sos4-brandbar {
  flex: 0 0 76px;
  height: 76px;
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
  padding: 0 12px;
  background: #fffdfa;
  border-bottom: 1px solid var(--sos4-border);
}
.sos4-brand { display:flex;align-items:center;gap:9px;min-width:0;flex:1 1 auto;overflow:hidden; }
.sos4-logo { display:grid;place-items:center;flex:0 0 35px;width:35px;height:35px;border-radius:11px;
  background: #eadcc7;color:#7b5d3b;font-size:20px;font-weight:800;
  box-shadow:inset 0 0 0 1px #dac9af; }
.sos4-brandwords { display:flex;flex-direction:column;gap:2px;min-width:0;white-space:nowrap; }
.sos4-brandwords strong {font-size:13px;letter-spacing:-.35px;color:#44392e;line-height:18px;font-weight:800;}
.sos4-brandwords b {color:#a27b48;}
.sos4-brandwords small {font-size:10px;color:#90816d;line-height:14px;}
.sos4-toggle, .sos4-close {
  border:1px solid #e3d6c4;background:#f8f2e9;color:#745b3e;
  border-radius:10px;width:35px;height:35px;flex:0 0 35px;
  display:grid;place-items:center;cursor:pointer;user-select:none;
}
.sos4-toggle {display:none;}
.sos4-toggle:hover,.sos4-close:hover {background:#ede2d0;color:#513d28;}
.sos4-toggle:focus-visible,.sos4-close:focus-visible,.sos4-item:focus-visible {
  outline:3px solid #bba078;outline-offset:2px;
}
.sos4-close {font-size:23px;line-height:1;}
.sos4-scroll {flex:1 1 auto;overflow-y:auto;overflow-x:hidden;padding:20px 11px 10px;}
.sos4-group-label {padding:0 12px 10px;font-size:10px;font-weight:800;letter-spacing:1.2px;color:#aaa092;}
.sos4-nav {display:flex;flex-direction:column;gap:4px;}
.sos4-item {
  width:100%;min-height:45px;padding:10px 11px;display:flex;align-items:center;gap:13px;
  appearance:none;border:0;background:transparent;border-radius:10px;
  cursor:pointer;text-align:left;color:#756b5e;
  font-size:13px;font-weight:600;line-height:21px;white-space:nowrap;
  transition:background-color .14s ease,color .14s ease;
}
.sos4-item:hover {background:#f0ebe3;color:#40352b;}
.sos4-item.sos4-active {background:#eee4d4;color:#664c2b;font-weight:750;}
.sos4-icon {flex:0 0 21px;width:21px;height:21px;}
.sos4-label {white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sos4-foot {height:53px;min-height:53px;display:flex;align-items:center;gap:9px;
  border-top:1px solid var(--sos4-border);padding:0 21px;color:#a69a8a;font-size:10px;white-space:nowrap;}
.sos4-foot-dot {width:7px;height:7px;border-radius:50%;background:#a8977b;flex:0 0 7px;}
@media (min-width:1024px) {
  .sos4-sidebar {
    position:sticky;z-index:20;inset:auto;top:0;align-self:flex-start;
    transform:none !important;flex:0 0 252px;width:252px;min-width:252px;max-width:252px;
    box-shadow:none;
  }
  .sos4-toggle {display:grid;}
  .sos4-close {display:none;}
  .sos4-sidebar.sos4-compact {flex-basis:76px;width:76px;min-width:76px;max-width:76px;}
  .sos4-compact .sos4-brandbar {justify-content:center;padding:0 8px;}
  .sos4-compact .sos4-brand {display:none;}
  .sos4-compact .sos4-toggle {flex:0 0 42px;width:42px;height:42px;}
  .sos4-compact .sos4-scroll {padding:20px 8px 10px;}
  .sos4-compact .sos4-group-label {visibility:hidden;height:0;padding:0;}
  .sos4-compact .sos4-item {justify-content:center;gap:0;padding:10px 0;height:48px;}
  .sos4-compact .sos4-label {display:none;}
  .sos4-compact .sos4-icon {width:22px;height:22px;flex-basis:22px;}
  .sos4-compact .sos4-foot {justify-content:center;padding:0;}
  .sos4-compact .sos4-foot-text {display:none;}
}
@media (prefers-reduced-motion:reduce) {
  .sos4-sidebar,.sos4-item {transition:none;}
}
</style>

<!-- SERVICING_OS_LANGUAGE_637 styles, ivory/espresso only -->
<style scoped>
.sos37-language {
  margin-top:auto; flex:0 0 auto; padding:12px 12px 13px;
  border-top:1px solid #e7dbcb; background:#fffaf3;
  color:#695440;
}
.sos37-caption {font-size:10px;letter-spacing:.07em;font-weight:800;color:#9b8060;margin:0 0 7px 3px;}
.sos37-choices {display:flex;gap:5px;padding:4px;border-radius:12px;background:#f1e8d9;border:1px solid #e6d6c0;}
.sos37-choice {flex:1;min-width:0;min-height:38px;border:1px solid transparent;border-radius:9px;
  padding:7px 5px;cursor:pointer;font-weight:750;font-size:12px;line-height:1.4;
  text-align:center;color:#705d48;background:transparent;white-space:nowrap;
  transition:background .16s ease,color .16s ease,box-shadow .16s ease;}
.sos37-choice:hover {background:#fffaf4;color:#4e3924;}
.sos37-choice.sos37-selected {background:#745032;color:#fffdf8;box-shadow:0 2px 5px #46312124;}
.sos37-choice:focus-visible {outline:3px solid #bb9354;outline-offset:2px;}
.sos37-choice-short {display:none;}
@media(min-width:1024px) {
.sos4-sidebar.sos4-compact .sos37-language {padding:9px 6px;}
.sos4-sidebar.sos4-compact .sos37-caption {display:none;}
.sos4-sidebar.sos4-compact .sos37-choices {display:flex;flex-direction:column;gap:4px;padding:3px;}
.sos4-sidebar.sos4-compact .sos37-choice {font-size:10px;min-height:33px;padding:6px 1px;}
.sos4-sidebar.sos4-compact .sos37-choice-full {display:none;}
.sos4-sidebar.sos4-compact .sos37-choice-short {display:inline;}
}
@media(prefers-reduced-motion:reduce){.sos37-choice{transition:none;}}
</style>




<!-- SERVICING_NAVBAR_646 : approved ivory navigation visual -->
<style scoped>
.sos4-sidebar{background:#faf8f3;border-right-color:#e8ded0;color:#66584a}
.sos4-brandbar{height:86px;min-height:86px;flex-basis:86px;background:#faf8f3;border-bottom-color:#e8ded0;padding:0 15px}
.sos4-logo{background:#765338;color:#fff;border:0;box-shadow:0 3px 9px #76533820;border-radius:13px;width:44px;height:44px;flex-basis:44px;font-size:24px}
.sos4-brandwords strong{font-size:14px;color:#463628;letter-spacing:-.35px}
.sos4-brandwords b{color:#a98253}
.sos4-brandwords small{font-size:10px;letter-spacing:1px;font-weight:700;color:#998a77}
.sos4-scroll{padding:18px 12px 12px}
.sos646-search{display:flex;align-items:center;gap:10px;height:44px;padding:0 12px;margin:0 1px 21px;background:#fff;border:1px solid #e6ded3;border-radius:11px;color:#a79a88}
.sos646-search:focus-within{border-color:#a98253;box-shadow:0 0 0 3px #a982531b}
.sos646-search input{border:0;outline:0;background:transparent;min-width:0;width:100%;font:500 12px inherit;color:#463628;font-size:12px}
.sos646-search input::placeholder{color:#a79a88}
.sos4-group-label{padding:0 12px 10px;color:#a89a86;font-size:10px;font-weight:800;letter-spacing:1.3px}
.sos4-nav{gap:4px;margin-bottom:15px}
.sos4-nav+.sos4-group-label{border-top:1px solid #e8ded0;padding-top:18px}
.sos4-item{min-height:43px;padding:10px 12px;gap:12px;color:#66584a;border-radius:10px;font-size:13px;font-weight:600}
.sos4-icon{color:#817464}
.sos4-item:hover{background:#f1ece4;color:#463628}
.sos4-item.sos4-active{background:#ede2d2;color:#765338;font-weight:750;box-shadow:none}
.sos4-item.sos4-active .sos4-icon{color:#765338}
.sos37-language{background:#faf8f3;border-top-color:#e8ded0}
.sos4-foot{border-top-color:#e8ded0}
.sos646-empty{font-size:12px;color:#998a77;padding:0 12px}
@media(min-width:1024px){
 .sos4-sidebar.sos4-compact .sos646-search{display:none}
 .sos4-sidebar.sos4-compact .sos4-nav{margin-bottom:9px}
 .sos4-sidebar.sos4-compact .sos4-group-label{height:0;padding:0;visibility:hidden}
 .sos4-sidebar.sos4-compact .sos4-brandbar{padding:0 8px}
}
</style>

<!-- SERVICING_STEP_647 language control, aligned to approved ivory preview -->
<style scoped>
.sos37-language{display:flex;align-items:center;justify-content:space-between;gap:9px;padding:12px 13px 13px;background:#faf8f3;border-top:1px solid #e8ded0;min-height:69px}
.sos37-caption{display:flex;align-items:center;gap:7px;white-space:nowrap;font-size:11px;letter-spacing:0;text-transform:none;margin:0;font-weight:750;color:#66584a}
.sos37-caption::before{content:'🌐';font-size:16px;line-height:1}
.sos37-choices{display:flex;gap:2px;padding:3px;border-radius:10px;background:#eee6da;border:0;min-width:123px;flex:0 0 auto}
.sos37-choice{min-height:30px;padding:5px 7px;font-size:11px;border-radius:8px;font-weight:800;color:#765338;line-height:19px}
.sos37-choice.sos37-selected{background:#765338;color:#fff;box-shadow:none}
.sos37-choice-full{display:inline}
@media(min-width:1024px){
.sos4-sidebar.sos4-compact .sos37-language{display:block;padding:8px 6px;min-height:0}
.sos4-sidebar.sos4-compact .sos37-choices{min-width:0;flex-direction:column;gap:4px}
.sos4-sidebar.sos4-compact .sos37-choice-full{display:none}
.sos4-sidebar.sos4-compact .sos37-choice-short{display:inline}
}
@media(max-width:340px){.sos37-choices{min-width:105px}.sos37-choice{padding:4px}}
</style>

<!-- SERVICING_STEP_648: approved compact ivory language control -->
<style scoped>
.sos37-language {display:flex!important;align-items:center!important;justify-content:space-between!important;gap:6px!important;width:100%;min-width:0!important;min-height:61px!important;padding:10px!important;overflow:hidden;background:#faf8f3!important;border-top:1px solid #e8ded0!important;}
.sos37-caption{display:flex!important;align-items:center!important;gap:5px!important;flex:0 1 auto;min-width:0;white-space:nowrap;padding:0!important;margin:0!important;font-size:11px!important;letter-spacing:0!important;color:#66584a!important;}
.sos37-caption::before{content:none!important;display:none!important;}
.sos648-language-icon{display:block;flex:none;color:#765338;}
.sos648-language-label{min-width:0;overflow:hidden;text-overflow:ellipsis;}
.sos37-choices{display:flex!important;flex:0 0 111px!important;width:111px!important;min-width:0!important;gap:2px!important;padding:3px!important;background:#eee6da!important;border:0!important;border-radius:10px!important;}
.sos37-choice{display:flex;justify-content:center;align-items:center;flex:1 1 0!important;min-width:0!important;min-height:31px!important;padding:5px 3px!important;border-radius:8px!important;font-size:11px!important;}
.sos37-choice.sos37-selected{background:#765338!important;color:#fffdf8!important;}
.sos37-choice-full{display:inline!important;}.sos37-choice-short{display:none!important;}
@media(min-width:1024px){.sos4-sidebar.sos4-compact .sos37-language{display:block!important;padding:9px 6px!important;min-height:0!important;}.sos4-sidebar.sos4-compact .sos37-caption{display:none!important;}.sos4-sidebar.sos4-compact .sos37-choices{display:flex!important;flex-direction:column!important;width:100%!important;min-width:0!important;}.sos4-sidebar.sos4-compact .sos37-choice-full{display:none!important;}.sos4-sidebar.sos4-compact .sos37-choice-short{display:inline!important;}}
</style>


<!-- SOS_SALES_V3_3_NATIVE_ROW -->
<style scoped>
/* The Sales item uses EXACTLY the existing .sos4-item surface, dimensions, colors,
   typography, hover and active state as every other top-level navigation row. */
.sosSalesWrap {width:100%;min-width:0}
.sosSalesWrap.sosSalesOther {display:contents}
.sosSalesNavRow {position:relative;width:100%;min-width:0}
.sosSalesNavRow > .sos4-item {width:100%}
.sosSalesNavParent > .sos4-item {padding-right:45px}
.sosSalesExpand {position:absolute;right:8px;top:50%;transform:translateY(-50%);
  width:29px;height:32px;display:grid;place-items:center;padding:0;border:0;
  background:transparent;color:inherit;border-radius:7px;cursor:pointer;
  color:#806a54}
.sosSalesExpand:hover {background:#e7dccb;color:#533d2a}
.sosSalesExpand:focus-visible,.sosSalesChild:focus-visible{outline:2px solid #b08b5e;outline-offset:1px}
.sosSalesChevron{transition:transform .18s ease}
.sosSalesWrap:has(.sosSalesNavPanel) .sosSalesChevron{transform:rotate(180deg)}
/* Keep child rows consistent with main menu, only a modest visual indent. */
.sosSalesNavPanel{margin:3px 0 8px 15px;padding-left:9px;border-left:1px solid #e3d7c6;
 display:flex;flex-direction:column;gap:3px}
.sos4-item.sosSalesChild{width:100%;min-height:45px;display:flex;align-items:center;
 gap:11px;padding:7px 9px;border-radius:10px;font-size:12px;line-height:1.2;
 white-space:normal;text-align:left}
.sosSalesChildIcon{flex:0 0 19px;width:19px;height:19px;color:inherit}
.sosSalesChildText{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1;overflow:hidden}
.sosSalesChildName{font-size:12px;font-weight:700;line-height:1.15;white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis}
.sosSalesChildHelp{font-size:10px;font-weight:450;line-height:1.1;color:#9e8d79;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sos4-item.sosSalesChildCurrent .sosSalesChildHelp{color:#8a7359}
.sosSalesSlide-enter-active,.sosSalesSlide-leave-active{transition:opacity .17s ease,transform .17s ease}
.sosSalesSlide-enter-from,.sosSalesSlide-leave-to{opacity:0;transform:translateY(-4px)}
@media(min-width:1024px){.sos4-compact .sosSalesNavParent>.sos4-item{padding-right:0}
  .sos4-compact .sosSalesExpand,.sos4-compact .sosSalesNavPanel{display:none}}
@media(prefers-reduced-motion:reduce){.sosSalesChevron,.sosSalesSlide-enter-active,.sosSalesSlide-leave-active{transition:none}}
</style>

