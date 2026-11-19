/* SERVICING OS 7.01: Components Received -> ERPNext-like one-record-per-line grid.
   No DOM reparenting and no changes to Vue state, events, APIs, or persistence.
   Keeps existing input elements in place. */
import './components-child-table-701.css';

const VERSION = '7.01';
const COLUMNS = [
  ['type', /^(?:type|ধরন)$/i],
  ['brand', /^(?:brand|ব্র্যান্ড)$/i],
  ['specification', /^(?:capacity\s*\/\s*specification|capacity|specification|স্পেসিফিকেশন|ক্ষমতা)$/i],
  ['quantity', /^(?:quantity|qty|পরিমাণ)$/i],
  ['model', /^(?:model|মডেল)$/i],
  ['serial', /^(?:serial\s*(?:number|no\.?|#)?|সিরিয়াল\s*(?:নম্বর)?)$/i],
  ['condition', /^(?:condition\s*(?:at\s*receive)?|receive\s*condition|অবস্থা)$/i],
  ['remarks', /^(?:remarks|notes|মন্তব্য)$/i],
];
const HEADER_RE = /(?:components?\s*received|received\s*components?|কম্পোনেন্ট.*(?:গ্রহণ|রিসিভ)|(?:গ্রহণ|রিসিভ).*কম্পোনেন্ট)/i;
const ADD_RE = /(?:add\s+component|কম্পোনেন্ট\s+যোগ)/i;
const REMOVE_RE = /(?:remove|মুছুন|সরান|বাদ\s*দিন)/i;
const CTRL = 'input:not([type="hidden"]),select,textarea,[role="combobox"]';
const VUE_LAYOUT = '[data-servicing-component-layout="vue"]';
const info = { version: VERSION, scans: 0, panels: 0, rows: 0, columns: COLUMNS.length, error: '', lastScan: null };
let timer = null;

function txt(node) { return (node?.textContent || '').replace(/\s+/g,' ').trim(); }
function visible(node) {
  if (!node || !node.isConnected || !node.getClientRects().length) return false;
  const style = getComputedStyle(node);
  return style.display !== 'none' && style.visibility !== 'hidden';
}
function controls(node) { return [...node.querySelectorAll(CTRL)].filter(el => !el.closest(VUE_LAYOUT) && visible(el)); }
function fieldIndex(name) {
  const value = (name || '').replace(/\s*[:：*]\s*$/, '').replace(/\s+/g,' ').trim();
  return COLUMNS.findIndex(([, regex]) => regex.test(value));
}
function labels(node) {
  return [...node.querySelectorAll('label, .field-label, .form-label')].filter(el => {
    // avoid duplicate nested label wrappers
    if (el.closest(VUE_LAYOUT) || !visible(el) || el.querySelector('label,.field-label,.form-label')) return false;
    return fieldIndex(labelText(el)) >= 0;
  });
}
function labelText(node) {
  const clone = node.cloneNode(true);
  for (const control of clone.querySelectorAll(CTRL)) control.remove();
  return txt(clone);
}
function headerNode(node) {
  const value = txt(node);
  if (!value || value.length > 100) return false;
  return HEADER_RE.test(value);
}
function findPanels() {
  const result = new Set();
  for (const heading of document.querySelectorAll('h1,h2,h3,h4,h5,h6,legend,strong,b,span,.section-title,.panel-title')) {
    if (heading.closest(VUE_LAYOUT) || !visible(heading) || !headerNode(heading)) continue;
    let node = heading;
    for (let level=0; level<9 && node && node!==document.body; level++, node=node.parentElement) {
      const n = controls(node).length;
      const hasAdd = [...node.querySelectorAll('button')].some(b => ADD_RE.test(txt(b)));
      if (n >= 7 && n <= 130 && hasAdd) { result.add(node); break; }
    }
  }
  return [...result].filter(node => visible(node));
}
function nearestFieldRow(typeLabel, panel) {
  let node = typeLabel.parentElement;
  let inner = null;
  for (let i=0; i<10 && node && node!==panel && node!==document.body; i++, node=node.parentElement) {
    const counts = controls(node).length;
    if (counts > 14) break;
    const found = new Set(labels(node).map(label => fieldIndex(labelText(label))));
    if (counts >= 7 && found.size >= 7 && ![...node.querySelectorAll('button')].some(b => ADD_RE.test(txt(b)))) {
      inner = node;
      break;
    }
  }
  if (!inner) return null;
  let outer = inner;
  for (let i=0; i<4 && outer.parentElement && outer.parentElement!==panel; i++) {
    const p = outer.parentElement;
    if (controls(p).length > 12 || labels(p).filter(l=>fieldIndex(labelText(l))===0).length!==1) break;
    if ([...p.querySelectorAll('button')].some(b => ADD_RE.test(txt(b)))) break;
    if ([...p.querySelectorAll('button')].some(b => REMOVE_RE.test(txt(b)))) { outer=p; break; }
    outer=p;
  }
  return outer;
}
function fieldWrapper(label, row) {
  let node = label;
  while (node && node!==row) {
    if (controls(node).length===1 && (node.matches('label') || node.querySelector(CTRL))) return node;
    node=node.parentElement;
  }
  return null;
}
function flattenBetween(wrapper, row) {
  let parent = wrapper.parentElement;
  while (parent && parent!==row) {
    parent.classList.add('sos701-flatten');
    parent = parent.parentElement;
  }
}
function metaWrapper(row, button) {
  if (!button) return null;
  let node=button;
  while (node.parentElement && node.parentElement!==row && controls(node.parentElement).length===0) node=node.parentElement;
  return node;
}
function prepareRow(row, panel, index) {
  const byField = new Map();
  for (const label of labels(row)) {
    const col = fieldIndex(labelText(label));
    if (col<0 || byField.has(col)) continue;
    const field = fieldWrapper(label, row);
    if (field) byField.set(col,field);
  }
  if (byField.size < 7) return false;
  row.classList.add('sos701-row');
  row.dataset.sos701Number = String(index+1).padStart(2,'0');
  row.classList.toggle('sos701-first', index===0);
  for (const [idx, field] of byField) {
    field.classList.add('sos701-cell');
    field.dataset.sos701Heading = ['Type','Brand','Capacity / Specification','Quantity','Model','Serial Number','Condition at Receive','Remarks'][idx];
    field.style.setProperty('--sos701-column', String(idx+2));
    flattenBetween(field, row);
    // Covers labels implemented as sibling elements as well as wrapping labels.
    const label = labels(field).find(l=>fieldIndex(labelText(l))===idx);
    if (label) label.classList.add('sos701-cell-label');
  }
  const remove = [...row.querySelectorAll('button')].find(button => REMOVE_RE.test(txt(button)));
  if (remove) {
    const meta=metaWrapper(row,remove);
    if (meta) {
      meta.classList.add('sos701-meta');
      remove.classList.add('sos701-delete');
    }
  }
  const scroll = row.parentElement;
  if (scroll && scroll!==panel) scroll.classList.add('sos701-scroll');
  panel.classList.add('sos701-root');
  return true;
}
function scan() {
  info.scans++;
  info.lastScan=new Date().toISOString();
  let rows=0;
  const panels=findPanels();
  for (const panel of panels) {
    const found=[];
    const seen=new Set();
    for (const label of labels(panel)) {
      if (fieldIndex(labelText(label))!==0) continue;
      const row=nearestFieldRow(label,panel);
      if (row && !seen.has(row)) { seen.add(row); found.push(row); }
    }
    // Avoid partially styling a grid if one or more rows could not be mapped.
    const valid=found.filter(row => labels(row).map(l=>fieldIndex(labelText(l))).filter(x=>x>=0).length>=7);
    if (valid.length) valid.forEach((row,i)=>{ if(prepareRow(row,panel,i)) rows++; });
  }
  info.panels=panels.length;
  info.rows=rows;
  info.error=panels.length && !rows ? 'Panel detected, but row/field structure is not supported. No controls were moved.' : '';
}
function schedule() { if (timer!==null) return; timer=requestAnimationFrame(()=>{timer=null;try{scan()}catch(e){info.error=String(e)}}); }
function start() {
  schedule();
  const observer=new MutationObserver(schedule);
  observer.observe(document.body,{childList:true,subtree:true});
  document.addEventListener('click',schedule,true);
  window.addEventListener('popstate',schedule);
  window.__sosComponentsChildTable701=info;
}
if (typeof document!=='undefined') {
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
}
