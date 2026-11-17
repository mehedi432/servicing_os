/* SERVICING OS • Components Receive compact form • V6.95
 * Visual-only enhancement: no changes to Vue models, validation, data, or APIs.
 * Classifies visible field grids in the active Components Receive panel.
 */
import './servicing-receive-compact-695.css';

const VERSION = '6.95';
const ROOT_CLASS = 'sos-component-receive-compact-695';
const GRID_CLASS = 'sos-component-receive-grid-695';
const FIELD_CLASS = 'sos-component-receive-wide-695';
const phrase = /(?:component(?:s)?\s*(?:receive|received|receiving)|(?:receive|received|receiving)\s*component(?:s)?|receive\s*parts|parts\s*receive|কম্পোনেন্ট.{0,16}(?:রিসিভ|গ্রহণ)|(?:রিসিভ|গ্রহণ).{0,16}কম্পোনেন্ট)/i;
const componentWord = /(?:components?|parts|কম্পোনেন্ট|যন্ত্রাংশ)/i;
const receiveWord = /(?:receive|received|receiving|রিসিভ|গ্রহণ)/i;
const controlsSelector = 'input:not([type="hidden"]), select, textarea, [role="combobox"]';
const state = { version: VERSION, scans: 0, panels: 0, grids: 0, lastScan: null };

function visible(el) {
  if (!el || !el.isConnected || !el.getClientRects().length) return false;
  const cs = window.getComputedStyle(el);
  return cs.display !== 'none' && cs.visibility !== 'hidden';
}
function formControls(el) {
  return [...el.querySelectorAll(controlsSelector)].filter(visible);
}
function textOf(el) { return (el.textContent || '').replace(/\s+/g, ' ').trim(); }
function supportedAnchor(el) {
  if (!visible(el)) return false;
  const value = textOf(el);
  return value.length > 0 && value.length < 105 && phrase.test(value);
}
function outerPanel(anchor) {
  const dialog = anchor.closest('dialog, [role="dialog"], [aria-modal="true"], .modal-dialog, .modal-content');
  if (dialog && visible(dialog) && formControls(dialog).length >= 3) return dialog;
  let el = anchor;
  for (let i = 0; i < 12 && el && el !== document.body; i++, el = el.parentElement) {
    const count = formControls(el).length;
    if (count >= 3 && count <= 50 && !el.matches('#app, main, body')) return el;
  }
  return null;
}
function panelCandidates() {
  const roots = new Set();
  const anchorSelector = 'h1,h2,h3,h4,h5,h6,legend,[role="tab"],button,strong,span,.modal-title,.section-title,.panel-title';
  for (const anchor of document.querySelectorAll(anchorSelector)) {
    if (!supportedAnchor(anchor)) continue;
    const root = outerPanel(anchor);
    if (root) roots.add(root);
  }
  // Also handles a dialog headed "Receive Device" with a selected "Components" tab.
  const modals = document.querySelectorAll('dialog,[role="dialog"],[aria-modal="true"],.modal-dialog,.modal-content');
  for (const modal of modals) {
    if (!visible(modal) || formControls(modal).length < 3) continue;
    const titleText = [...modal.querySelectorAll('h1,h2,h3,h4,h5,h6,legend,[role="tab"],button')]
      .filter(visible).map(textOf).filter(x => x.length < 90).join(' ');
    if (phrase.test(titleText)) roots.add(modal);
    else if (receiveWord.test(titleText) && componentWord.test(titleText)) {
      // Only treat it as Components when its tab is selected (if tabs exist).
      const tabs = [...modal.querySelectorAll('[role="tab"], button')].filter(visible);
      const selected = tabs.some(t => componentWord.test(textOf(t)) &&
        (t.getAttribute('aria-selected') === 'true' ||
         t.getAttribute('data-state') === 'active' ||
         /(?:^|\s)(?:active|selected)(?:\s|$)/.test(t.className || '')));
      if (selected) roots.add(modal);
    }
  }
  return [...roots];
}
function fieldGridCandidates(root) {
  const candidates = [];
  for (const el of root.querySelectorAll('div, section, fieldset')) {
    if (!visible(el) || el.children.length < 3 || el.children.length > 20) continue;
    const children = [...el.children].filter(visible);
    if (children.length < 3) continue;
    const counts = children.map(child => formControls(child).length);
    const fieldChildren = counts.filter(c => c >= 1 && c <= 2).length;
    const allControlCount = counts.reduce((sum, n) => sum + n, 0);
    if (allControlCount < 3 || allControlCount > 18) continue;
    if (fieldChildren < 3 || fieldChildren / children.length < 0.7) continue;
    const cs = getComputedStyle(el);
    if (cs.display !== 'grid' && cs.display !== 'flex' &&
        !/(?:grid|fields|form-row)/i.test(el.className || '')) continue;
    // A field grid should not be a major panel with large nested cards.
    if (children.some(c => formControls(c).length > 2)) continue;
    candidates.push(el);
  }
  return candidates;
}
function processPanel(root) {
  root.classList.add(ROOT_CLASS);
  let n = 0;
  for (const grid of fieldGridCandidates(root)) {
    grid.classList.add(GRID_CLASS);
    n++;
    for (const item of grid.children) {
      if (item.querySelector('textarea') || /(?:description|problem|notes|remarks|issue|সমস্যা|বিবরণ)/i.test(
        [...item.querySelectorAll('label')].map(textOf).join(' '))) {
        item.classList.add(FIELD_CLASS);
      }
    }
  }
  return n;
}
function scan() {
  state.scans++;
  state.lastScan = new Date().toISOString();
  const panels = panelCandidates();
  let grids = 0;
  for (const panel of panels) grids += processPanel(panel);
  state.panels = panels.length;
  state.grids = grids;
}
let pending = false;
function scheduleScan() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => { pending = false; scan(); });
}
function initialize() {
  scheduleScan();
  const observer = new MutationObserver(scheduleScan);
  observer.observe(document.body, { childList: true, subtree: true });
  document.addEventListener('click', scheduleScan, true);
  document.addEventListener('focusin', scheduleScan, true);
  window.addEventListener('popstate', scheduleScan);
  window.__sosReceiveCompact695 = state;
}
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}
