<script setup>
import { currentLanguage, setLanguage } from '../i18n/servicingLanguage.js'
import { computed, onMounted, ref } from 'vue';

// SERVICING_STABLE_SIDEBAR_V4_20261110
const props = defineProps({
  items: { type: Array, default: () => [] },
  active: { type: String, default: 'Counter' },
  repairOpen: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false }
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

const menuItems = computed(() => {
  const entries = [...(props.items || [])].filter(x => x && x !== 'Repair Management');
  const index = entries.indexOf('Service Jobs');
  if (index >= 0) entries.splice(index + 1, 0, 'Repair Management');
  else entries.push('Repair Management');
  return entries;
});

function choose(item) {
  if (item === 'Repair Management') emit('repair');
  else emit('navigate', item);
  emit('close-mobile');
}

const ICON = {
  'Counter': ['M3 3h8v8H3z','M13 3h8v5h-8z','M13 10h8v11h-8z','M3 13h8v8H3z'],
  'New Sales': ['M3 4h2l2.4 11h11.5l2-8H6','M9 20h.01','M18 20h.01'],
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
      <div class="sos4-group-label">WORKSPACE</div>
      <nav class="sos4-nav" aria-label="Main menu">
        <button v-for="item in menuItems" :key="item"
                type="button" class="sos4-item"
                :class="{ 'sos4-active': isActive(item) }"
                :title="compact ? item : undefined"
                :aria-label="item"
                :aria-current="isActive(item) ? 'page' : undefined"
                @click.stop="choose(item)">
          <svg class="sos4-icon" viewBox="0 0 24 24" width="20" height="20"
               fill="none" stroke="currentColor" stroke-width="1.75"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="(path,index) in iconPaths(item)" :key="index" :d="path" />
          </svg>
          <span class="sos4-label">{{ item }}</span>
        </button>
      </nav>
    </div>
    <!-- SERVICING_OS_LANGUAGE_637 : persistent sidebar language switch -->
    <div class="sos37-language" data-sos-language-control role="group" aria-label="Language / ভাষা">
      <div class="sos37-caption">ভাষা / LANGUAGE</div>
      <div class="sos37-choices">
        <button type="button" class="sos37-choice"
                :class="{ 'sos37-selected': currentLanguage === 'en' }"
                :aria-pressed="currentLanguage === 'en'" title="English"
                @click.stop="setLanguage('en')">
          <span class="sos37-choice-full">English</span><span class="sos37-choice-short">EN</span>
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
