/* SERVICING OS — Sticker Focus / Print v2
   Non-invasive enhancement: no ERPNext APIs, DB writes or component replacement.
   Activates only when the existing "Print QR Sticker" modal is visible. */
const PRINT_ROOT_ID = 'sos-sticker-v2-print-root';
const STYLE_ID = 'sos-sticker-v2-style';
const PAGE_STYLE_ID = 'sos-sticker-v2-page';
const JOB_PATTERN = /\b(?:SRV|SERVICE)[-_][A-Z0-9-]+\b/i;
let scanning = false;

const styleText = `
/* Readable print button - warm ivory / espresso styling */
.sos-sticker-v2-actions {
  display:flex!important; gap:10px!important; flex-wrap:wrap!important;
  align-items:center!important; justify-content:flex-end!important;
  position:sticky!important; top:0!important; z-index:20!important;
  padding:9px 12px!important; margin:6px 0!important;
  background:#f8f3ea!important; border:1px solid #e4d6c2!important;
  border-radius:11px!important; box-shadow:0 2px 8px #29180c15!important;
}
.sos-sticker-v2-print {
  display:inline-flex!important; align-items:center!important; justify-content:center!important;
  gap:9px!important; min-height:42px!important; padding:10px 18px!important;
  background:#503727!important; color:#fffaf1!important; border:1px solid #503727!important;
  border-radius:9px!important; font:700 14px/1.2 system-ui,sans-serif!important;
  cursor:pointer!important; opacity:1!important; visibility:visible!important;
}
.sos-sticker-v2-print:hover { background:#38261c!important; }
.sos-sticker-v2-print:focus-visible { outline:3px solid #bd9467!important; outline-offset:2px!important; }
.sos-sticker-v2-hint { font:500 12px/1.3 system-ui,sans-serif!important; color:#725a46!important; }
/* Only the QR-sticker preview, never the separate receipt or navigation. */
.sos-focused-sticker.sos-focused-sticker { font-family:Arial,sans-serif!important; letter-spacing:0!important; }
.sos-focused-sticker.sos-focused-sticker .sos-focus-device {
  font-size:13px!important; line-height:1.12!important; font-weight:900!important;
  color:#16110d!important; letter-spacing:-.1px!important; overflow-wrap:anywhere!important;
}
.sos-focused-sticker.sos-focused-sticker .sos-focus-problem {
  font-size:12px!important; line-height:1.14!important; font-weight:900!important;
  color:#17110d!important; overflow-wrap:anywhere!important;
}
.sos-focused-sticker.sos-focused-sticker .sos-focus-customer,
.sos-focused-sticker.sos-focused-sticker .sos-focus-mobile {
  font-size:12.5px!important; line-height:1.14!important; font-weight:850!important;
  color:#17110d!important; overflow-wrap:anywhere!important;
}
.sos-focused-sticker.sos-focused-sticker .sos-focus-serial {
  font-size:9px!important; line-height:1.1!important; font-weight:650!important;
  color:#483c34!important;
}
.sos-focused-sticker.sos-focused-sticker .sos-focus-job {
  font-size:9px!important; line-height:1.06!important; font-weight:750!important;
}
.sos-focused-sticker.sos-focused-sticker .sos-focus-company {
  font-size:8.5px!important; line-height:1.08!important; font-weight:850!important;
}
.sos-focused-sticker.sos-focused-sticker.sos-focused-sticker-compact .sos-focus-device {font-size:11px!important;}
.sos-focused-sticker.sos-focused-sticker.sos-focused-sticker-compact .sos-focus-problem {font-size:10.5px!important;}
.sos-focused-sticker.sos-focused-sticker.sos-focused-sticker-compact .sos-focus-customer,
.sos-focused-sticker.sos-focused-sticker.sos-focused-sticker-compact .sos-focus-mobile {font-size:10.5px!important;}
.sos-focused-sticker.sos-focused-sticker.sos-focused-sticker-compact .sos-focus-serial {font-size:8px!important;}
/* Print ONLY the physical label. Print container is created when user clicks. */
@media print {
  html:has(body[data-sos-sticker-v2-printing="1"]) body > :not(#${PRINT_ROOT_ID}) {display:none!important;}
  html body[data-sos-sticker-v2-printing="1"] #${PRINT_ROOT_ID},
  html body[data-sos-sticker-v2-printing="1"] #${PRINT_ROOT_ID} * {
    visibility:visible!important; opacity:1!important;
  }
  html body[data-sos-sticker-v2-printing="1"] #${PRINT_ROOT_ID} {
    display:block!important;position:absolute!important;top:0!important;left:0!important;
    width:100%!important;height:auto!important;margin:0!important;padding:0!important;
    color:#000!important;background:#fff!important;overflow:hidden!important;
  }
}
#${PRINT_ROOT_ID} {display:none;}
#${PRINT_ROOT_ID} .sos-v2-paper {
  display:flex;flex-direction:column; box-sizing:border-box; overflow:hidden;
  background:#fff; color:#111; padding:1.15mm; margin:0;
  font-family:Arial,Helvetica,sans-serif; letter-spacing:0; word-break:normal;
}
#${PRINT_ROOT_ID} .sos-v2-paper * {box-sizing:border-box;}
#${PRINT_ROOT_ID} .sos-v2-head {border-bottom:.18mm solid #111; padding-bottom:.35mm; margin-bottom:.6mm; flex-shrink:0;}
#${PRINT_ROOT_ID} .sos-v2-shop {font-size:7.7pt;line-height:1.0;font-weight:900;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
#${PRINT_ROOT_ID} .sos-v2-job {font-size:7.1pt;line-height:1.03;font-weight:800;margin-top:.25mm;}
#${PRINT_ROOT_ID} .sos-v2-main {display:grid;grid-template-columns:14mm minmax(0,1fr);gap:.8mm;align-items:start;flex-shrink:0;}
#${PRINT_ROOT_ID} .sos-v2-qrbox {width:13.8mm;height:13.8mm;display:flex;flex-direction:column;justify-content:center;align-items:center;overflow:hidden;}
#${PRINT_ROOT_ID} .sos-v2-qrbox img, #${PRINT_ROOT_ID} .sos-v2-qrbox canvas, #${PRINT_ROOT_ID} .sos-v2-qrbox svg {display:block;max-width:100%;max-height:100%;width:100%;height:100%;object-fit:contain;}
#${PRINT_ROOT_ID} .sos-v2-device {font-size:10.3pt;line-height:1.09;font-weight:900;overflow-wrap:anywhere;}
#${PRINT_ROOT_ID} .sos-v2-problem {font-size:9.5pt;line-height:1.12;font-weight:900;margin-top:.6mm;overflow-wrap:anywhere;}
#${PRINT_ROOT_ID} .sos-v2-row {display:flex;gap:1mm;align-items:baseline;font-size:9pt;line-height:1.08;font-weight:850;overflow-wrap:anywhere;margin-top:.45mm;}
#${PRINT_ROOT_ID} .sos-v2-row b {font-size:7pt;font-weight:700;flex-shrink:0;}
#${PRINT_ROOT_ID} .sos-v2-row.sos-v2-phone {font-size:10.1pt;}
#${PRINT_ROOT_ID} .sos-v2-row.sos-v2-serial {font-size:7pt;line-height:1.05;font-weight:650;color:#333;margin-top:.3mm;}
#${PRINT_ROOT_ID} .sos-v2-compact {padding:.85mm;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-shop {font-size:6.3pt;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-job {font-size:6.5pt;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-head {margin-bottom:.3mm;padding-bottom:.2mm;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-main {grid-template-columns:10.7mm minmax(0,1fr);gap:.7mm;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-qrbox {width:10.5mm;height:10.5mm;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-device {font-size:8.35pt;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-problem {font-size:8.3pt;margin-top:.25mm;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-row {font-size:7.9pt;line-height:1.05;margin-top:.22mm;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-row b {font-size:6.1pt;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-row.sos-v2-phone {font-size:8.7pt;}
#${PRINT_ROOT_ID} .sos-v2-compact .sos-v2-row.sos-v2-serial {font-size:6.2pt;line-height:1.0;}
`;

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = styleText;
  document.head.appendChild(style);
}
function normalized(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
function isVisible(el) { return !!(el && el.getClientRects && el.getClientRects().length); }

function findModal() {
  // If multiple modals are present, choose the smallest *visible* one with this exact title.
  const titles = [...document.querySelectorAll('h1,h2,h3,h4,[role="heading"]')]
    .filter(e => isVisible(e) && /print qr sticker/i.test(normalized(e.textContent)));
  for (const heading of titles.reverse()) {
    let e = heading;
    for (let i = 0; e && e !== document.body && i < 11; i++, e = e.parentElement) {
      const txt = normalized(e.textContent);
      if (txt.length > 25000) break;
      if (/sticker size/i.test(txt) && (/scan job/i.test(txt) || /qr link/i.test(txt))) {
        // Continue to role dialog if present, but avoid grabbing the SPA root.
        const dialog = heading.closest('[role="dialog"],[aria-modal="true"]');
        if (dialog && dialog.contains(e) && dialog !== document.body) return dialog;
        if (txt.length < 6500) return e;
      }
    }
  }
  return null;
}

function chooseSticker(modal) {
  const explicit = [...modal.querySelectorAll('.sr-sticker,[id*="sticker" i],[class*="sticker" i]')]
    .filter(e => isVisible(e) && JOB_PATTERN.test(e.innerText || e.textContent || '') && /mobile\s*:/i.test(e.innerText || e.textContent || '')
      && !/print qr sticker/i.test(e.textContent || ''));
  if (explicit.length) return explicit.sort((a,b) => normalized(a.textContent).length - normalized(b.textContent).length)[0];
  const candidates = [...modal.querySelectorAll('article,section,div')]
    .filter(e => isVisible(e) && JOB_PATTERN.test(e.innerText || e.textContent || '') && /mobile\s*:/i.test(e.innerText || e.textContent || '')
      && /problem\s*:/i.test(e.textContent || '')
      && e.querySelector('img,svg,canvas') && !e.querySelector('input,select,textarea,button'));
  candidates.sort((a,b) => normalized(a.textContent).length - normalized(b.textContent).length);
  return candidates[0] || null;
}

function rowCandidates(label) {
  return [...label.querySelectorAll('p,div,span,strong,b,small,section,header,footer')]
    .filter(e => normalized(e.textContent).length > 0 && normalized(e.textContent).length < 180);
}
function bestRow(label, test) {
  const found = rowCandidates(label).filter(e => test(normalized(e.textContent)));
  found.sort((a,b) => normalized(a.textContent).length - normalized(b.textContent).length);
  return found[0] || null;
}
function focusPreview(label, compact) {
  label.classList.add('sos-focused-sticker');
  label.classList.toggle('sos-focused-sticker-compact',compact);
  const patterns = [
    ['sos-focus-device', s => /\b(macbook|laptop|desktop|imac|thinkpad|dell|hp|lenovo|asus|acer|printer|monitor)\b/i.test(s) && !/s\/n\s*:/i.test(s) && !/customer\s*:/i.test(s)],
    ['sos-focus-problem', s => /^\s*(problem|issue|fault)\s*:/i.test(s)],
    ['sos-focus-customer', s => /^\s*(customer|name)\s*:/i.test(s)],
    ['sos-focus-mobile', s => /^\s*(mobile|phone)\s*:/i.test(s)],
    ['sos-focus-serial', s => /\b(s\/n|serial)\s*:/i.test(s)],
    ['sos-focus-job', s => JOB_PATTERN.test(s) && s.length < 60],
    ['sos-focus-company', s => /AL MODINA COMPUTERS LIMITED/i.test(s) && s.length < 80],
  ];
  for (const [className, test] of patterns) {
    const row = bestRow(label,test);
    if (row) row.classList.add(className);
  }
}

function stickerSize(modal) {
  const selects = [...modal.querySelectorAll('select')];
  for (const select of selects) {
    const opts = [...select.options].map(o => normalized(o.textContent)).join(' ');
    if (!/(?:50\s*[×x]\s*30|60\s*[×x]\s*40)/i.test(opts)) continue;
    const chosen = normalized(select.selectedOptions?.[0]?.textContent || select.value);
    return /50\s*[×x]\s*30|50\s*[_-]?\s*30/i.test(chosen) ? '50x30' : '60x40';
  }
  const checked = modal.querySelector('input[type="radio"]:checked');
  if (checked) {
    const text = normalized(checked.closest('label')?.textContent || checked.value);
    if (/50\s*[×x]\s*30/i.test(text)) return '50x30';
  }
  const active = [...modal.querySelectorAll('[aria-pressed="true"],[data-state="active"],button[class*="active"],button[class*="selected"]')];
  if (active.some(el => /50\s*[×x]\s*30/i.test(el.textContent || ''))) return '50x30';
  if (active.some(el => /60\s*[×x]\s*40/i.test(el.textContent || ''))) return '60x40';
  // Segmented controls can style the chosen option without exposing pressed state.
  // If the preview has a physical-paper ratio, use it as a secondary hint.
  const preview = chooseSticker(modal);
  const rect = preview?.getBoundingClientRect();
  if (rect && rect.width >= 130 && rect.height >= 65) {
    const ratio = rect.width / rect.height;
    if (ratio >= 1.60 && ratio <= 1.95) return '50x30';
    if (ratio >= 1.37 && ratio < 1.60) return '60x40';
  }
  return '60x40';
}
function getText(row, prefixes) {
  if (!row) return '';
  const escaped = prefixes.map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  return normalized(row.textContent).replace(new RegExp('^\\s*(?:'+escaped+')\\s*:\\s*','i'), '').trim();
}
function readData(label) {
  const txt = normalized(label.innerText || label.textContent);
  const job = (txt.match(JOB_PATTERN) || [''])[0];
  const device = bestRow(label, s => /\b(macbook|laptop|desktop|imac|thinkpad|dell|hp|lenovo|asus|acer|printer|monitor)\b/i.test(s) && !/\bs\/n\s*:/i.test(s) && !/customer\s*:/i.test(s));
  const customer = bestRow(label, s => /^\s*(customer|name)\s*:/i.test(s));
  const mobile = bestRow(label, s => /^\s*(mobile|phone)\s*:/i.test(s));
  const problem = bestRow(label, s => /^\s*(problem|issue|fault)\s*:/i.test(s));
  const serial = bestRow(label, s => /^(?:device\s*)?(?:s\/n|serial(?: number)?)\s*:/i.test(s));
  return {
    job,
    device: getText(device,['Device']) || normalized(device?.textContent) || 'Device not recorded',
    customer: getText(customer,['Customer','Name']) || 'Not recorded',
    mobile: getText(mobile,['Mobile','Phone']) || 'Not recorded',
    problem: getText(problem,['Problem','Issue','Fault']) || 'Not recorded',
    serial: getText(serial,['Device S/N','S/N','Serial','Serial Number']) || 'Not recorded',
    shop: normalized(bestRow(label,s => /AL MODINA COMPUTERS LIMITED/i.test(s) && s.length < 100)?.textContent) || 'AL MODINA COMPUTERS LIMITED',
  };
}
function copyQr(label) {
  // The original sticker's QR already contains the job URL. Do not change its payload.
  const imgs = [...label.querySelectorAll('img')].filter(e => e.currentSrc || e.src);
  const qrImg = imgs.find(e => /qr|data:image|qrcode/i.test((e.src||'')+' '+(e.alt||'')+' '+(e.className||''))) || imgs[0];
  if (qrImg) {
    const out = document.createElement('img');
    out.alt = 'Service job QR code';
    out.src = qrImg.currentSrc || qrImg.src;
    return out;
  }
  const canvas = label.querySelector('canvas');
  if (canvas) {
    try { const img = document.createElement('img');img.src=canvas.toDataURL('image/png');img.alt='Service job QR code';return img; }
    catch (err) { console.warn('SERVICING OS sticker: unable to copy QR canvas',err); }
  }
  const svg = label.querySelector('svg');
  return svg ? svg.cloneNode(true) : null;
}
function addText(el, cls, content) { const p=document.createElement('div');p.className=cls;p.textContent=content;el.appendChild(p);return p; }
function addRow(el, label, value, cls='') {
  const row=document.createElement('div'); row.className='sos-v2-row '+cls;
  const key=document.createElement('b');key.textContent=label;
  const val=document.createElement('span');val.textContent=value;
  row.append(key,val);el.appendChild(row);
}
function removePreviousPrint() {
  document.getElementById(PRINT_ROOT_ID)?.remove();
  document.getElementById(PAGE_STYLE_ID)?.remove();
  document.body?.removeAttribute('data-sos-sticker-v2-printing');
}
async function printSticker(modal, label, button) {
  const data = readData(label);
  if (!data.job) { window.alert('The sticker has no Service Job ID. Find a Service Job first.'); return; }
  const qr = copyQr(label);
  if (!qr) { window.alert('QR code is not ready. Find the Service Job and allow the QR to load before printing.'); return; }
  const size=stickerSize(modal), compact=size==='50x30';
  removePreviousPrint();
  const root=document.createElement('div');root.id=PRINT_ROOT_ID;
  const paper=document.createElement('section');paper.className='sos-v2-paper'+(compact?' sos-v2-compact':'');
  paper.style.width=compact?'50mm':'60mm';paper.style.height=compact?'30mm':'40mm';
  root.appendChild(paper);
  const head=document.createElement('div');head.className='sos-v2-head';paper.appendChild(head);
  addText(head,'sos-v2-shop',data.shop);
  addText(head,'sos-v2-job',data.job);
  const main=document.createElement('div');main.className='sos-v2-main';paper.appendChild(main);
  const qrBox=document.createElement('div');qrBox.className='sos-v2-qrbox';qrBox.appendChild(qr);main.appendChild(qrBox);
  const summary=document.createElement('div');main.appendChild(summary);
  addText(summary,'sos-v2-device',data.device);
  addText(summary,'sos-v2-problem',data.problem);
  addRow(paper,'NAME',data.customer);
  addRow(paper,'MOBILE',data.mobile,'sos-v2-phone');
  addRow(paper,'S/N',data.serial,'sos-v2-serial');
  document.body.appendChild(root);
  const pg=document.createElement('style');pg.id=PAGE_STYLE_ID;
  pg.textContent=`@page { size:${compact?'50mm 30mm':'60mm 40mm'}; margin:0; }`;
  document.head.appendChild(pg);
  button.disabled=true;
  const originalText=button.querySelector('span')?.textContent;
  if (button.querySelector('span')) button.querySelector('span').textContent='Opening print…';
  document.body.setAttribute('data-sos-sticker-v2-printing','1');
  // Do not call window.open(): popup blockers are avoided. Print only our print-root.
  const cleanup=()=>{removePreviousPrint();button.disabled=false;if(originalText && button.querySelector('span')) button.querySelector('span').textContent=originalText;};
  window.addEventListener('afterprint',cleanup,{once:true});
  try {
    if (document.fonts?.ready) await document.fonts.ready;
    if (qr.tagName==='IMG' && !qr.complete) {
      await Promise.race([new Promise(resolve=>{qr.addEventListener('load',resolve,{once:true});qr.addEventListener('error',resolve,{once:true});}),new Promise(resolve=>setTimeout(resolve,1600))]);
    }
    window.print();
  } catch (err) {cleanup();console.error('SERVICING OS: sticker print failed',err);window.alert('Could not open printer. Check browser print permissions.');}
}
function installModal(modal) {
  const label=chooseSticker(modal);
  if (!label) return;
  const compact=stickerSize(modal)==='50x30';
  focusPreview(label,compact);
  if (modal.querySelector('.sos-sticker-v2-actions')) return;
  const title=[...modal.querySelectorAll('h1,h2,h3,h4,[role="heading"]')]
    .find(el=>/print qr sticker/i.test(normalized(el.textContent)));
  if (!title) return;
  const actions=document.createElement('div');actions.className='sos-sticker-v2-actions';
  const hint=document.createElement('span');hint.className='sos-sticker-v2-hint';hint.textContent='Print the label only';
  const btn=document.createElement('button');btn.type='button';btn.className='sos-sticker-v2-print';
  btn.setAttribute('aria-label','Print selected QR sticker');
  btn.innerHTML='<svg aria-hidden="true" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a3 3 0 0 1 3-3h14a3 3 0 0 1 3 3v5a2 2 0 0 1-2 2h-2M6 14h12v8H6zM18 12h.01"/></svg><span>Print Sticker</span>';
  btn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();printSticker(modal,chooseSticker(modal)||label,btn);});
  actions.append(hint,btn);
  // Place next to heading, keeping the close icon and the sticker controls intact.
  title.insertAdjacentElement('afterend',actions);
  modal.addEventListener('change',()=>{
    const l=chooseSticker(modal);if(l) focusPreview(l,stickerSize(modal)==='50x30');
  });
}
function scan() {
  if (scanning) return;
  scanning=true;
  try {
    const modal=findModal();
    if (modal) {
      installModal(modal);
    }
  } finally {scanning=false;}
}
function boot() {
  ensureStyle();
  scan();
  const observer=new MutationObserver(records=>{
    // Only react when the component opens/closes or rerenders, not to style changes.
    if (records.some(r=>r.type==='childList')) scan();
  });
  observer.observe(document.body,{childList:true,subtree:true});
}
if (typeof document!=='undefined') {
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
}
