
/* SERVICING OS — Premium Sticker V4
   Safe modal enhancer for the existing Print QR Sticker workflow.
   - keeps original preview DOM untouched (hidden, not destroyed)
   - renders a premium custom preview beside it
   - prints only the selected label size (60x40 or 50x30)
   - removes Customer:/Mobile: labels in printed sticker
   - customer name becomes the biggest line; mobile separate bold; problem below bold
*/
const STYLE_ID = 'sos-v4-sticker-style';
const PRINT_ROOT_ID = 'sos-v4-sticker-print-root';
const PAGE_STYLE_ID = 'sos-v4-sticker-page-style';
const JOB_PATTERN = /\b(?:SRV|SERVICE)[-_][A-Z0-9-]+\b/i;
let busy = false;

const css = `
.sos-v4-actions {
  display:flex!important; align-items:center!important; justify-content:flex-end!important; gap:10px!important;
  flex-wrap:wrap!important; margin:8px 0!important; padding:10px 12px!important;
  background:#f8f3ea!important; border:1px solid #e4d6c2!important; border-radius:12px!important;
  box-shadow:0 2px 10px rgba(41,24,12,.08)!important; position:sticky!important; top:0!important; z-index:15!important;
}
.sos-v4-hint { font:500 12px/1.25 system-ui,sans-serif!important; color:#725a46!important; }
.sos-v4-print {
  display:inline-flex!important; align-items:center!important; justify-content:center!important; gap:8px!important;
  min-height:42px!important; padding:10px 18px!important; border-radius:10px!important;
  border:1px solid #4a3326!important; background:#4a3326!important; color:#fffaf1!important;
  font:700 14px/1.2 system-ui,sans-serif!important; cursor:pointer!important;
}
.sos-v4-print:hover { background:#38261c!important; }
.sos-v4-print:disabled { opacity:.65!important; cursor:wait!important; }
.sos-v4-hide-original { display:none!important; }
.sos-v4-preview-wrap { margin-top:8px!important; }
.sos-v4-preview-paper {
  width:100%!important; box-sizing:border-box!important; overflow:hidden!important; background:#fff!important; color:#111!important;
  border:1px solid #d8cfc0!important; border-radius:10px!important; padding:1.4mm!important;
  font-family:Arial,Helvetica,sans-serif!important; box-shadow:0 4px 14px rgba(41,24,12,.06)!important;
}
.sos-v4-preview-paper * { box-sizing:border-box!important; }
.sos-v4-head { border-bottom:1px solid #111!important; padding-bottom:.9mm!important; margin-bottom:1mm!important; }
.sos-v4-shop { font-size:8px!important; font-weight:900!important; line-height:1.04!important; text-transform:uppercase!important; white-space:nowrap!important; overflow:hidden!important; text-overflow:ellipsis!important; }
.sos-v4-job { font-size:7px!important; font-weight:800!important; line-height:1.03!important; margin-top:.3mm!important; }
.sos-v4-main { display:grid!important; grid-template-columns:12.5mm minmax(0,1fr)!important; gap:1mm!important; align-items:start!important; }
.sos-v4-main.compact { grid-template-columns:9.5mm minmax(0,1fr)!important; gap:.7mm!important; }
.sos-v4-qr { width:12.2mm!important; height:12.2mm!important; display:flex!important; align-items:center!important; justify-content:center!important; overflow:hidden!important; }
.sos-v4-main.compact .sos-v4-qr { width:8.8mm!important; height:8.8mm!important; }
.sos-v4-qr img,.sos-v4-qr canvas,.sos-v4-qr svg { width:100%!important; height:100%!important; max-width:100%!important; max-height:100%!important; object-fit:contain!important; display:block!important; }
.sos-v4-device { font-size:10.8px!important; line-height:1.04!important; font-weight:900!important; letter-spacing:-.1px!important; overflow-wrap:anywhere!important; }
.sos-v4-main.compact .sos-v4-device { font-size:8.0px!important; }
.sos-v4-serial { font-size:7px!important; line-height:1!important; font-weight:650!important; color:#4b5563!important; margin-top:.35mm!important; overflow-wrap:anywhere!important; }
.sos-v4-main.compact .sos-v4-serial { font-size:5.6px!important; margin-top:.15mm!important; }
.sos-v4-customer { font-size:13.4px!important; line-height:1.03!important; font-weight:900!important; color:#16110d!important; margin-top:.6mm!important; overflow-wrap:anywhere!important; }
.sos-v4-main.compact .sos-v4-customer { font-size:9.6px!important; margin-top:.3mm!important; }
.sos-v4-mobile { font-size:11.2px!important; line-height:1.02!important; font-weight:900!important; color:#1f2937!important; margin-top:.45mm!important; overflow-wrap:anywhere!important; }
.sos-v4-main.compact .sos-v4-mobile { font-size:8.0px!important; margin-top:.18mm!important; }
.sos-v4-problem { font-size:10.6px!important; line-height:1.06!important; font-weight:900!important; color:#111827!important; margin-top:.55mm!important; overflow-wrap:anywhere!important; }
.sos-v4-main.compact .sos-v4-problem { font-size:7.6px!important; margin-top:.25mm!important; }
@media print {
  html:has(body[data-sos-v4-printing="1"]) body > :not(#${PRINT_ROOT_ID}) { display:none!important; }
  html body[data-sos-v4-printing="1"] #${PRINT_ROOT_ID},
  html body[data-sos-v4-printing="1"] #${PRINT_ROOT_ID} * { visibility:visible!important; opacity:1!important; }
  html body[data-sos-v4-printing="1"] #${PRINT_ROOT_ID} {
    display:block!important; position:absolute!important; top:0!important; left:0!important;
    width:100%!important; margin:0!important; padding:0!important; background:#fff!important; overflow:hidden!important;
  }
}
#${PRINT_ROOT_ID} { display:none; }
#${PRINT_ROOT_ID} .sos-v4-paper {
  display:flex; flex-direction:column; box-sizing:border-box; overflow:hidden; background:#fff; color:#111;
  padding:1mm; margin:0; font-family:Arial,Helvetica,sans-serif;
}
#${PRINT_ROOT_ID} .sos-v4-paper * { box-sizing:border-box; }
#${PRINT_ROOT_ID} .sos-v4-head { border-bottom:.18mm solid #111; padding-bottom:.22mm; margin-bottom:.45mm; }
#${PRINT_ROOT_ID} .sos-v4-shop { font-size:6.4pt; line-height:1; font-weight:900; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
#${PRINT_ROOT_ID} .sos-v4-job { font-size:5.8pt; line-height:1.01; font-weight:800; margin-top:.15mm; }
#${PRINT_ROOT_ID} .sos-v4-main { display:grid; grid-template-columns:12.2mm minmax(0,1fr); gap:.7mm; align-items:start; }
#${PRINT_ROOT_ID} .sos-v4-qrbox { width:11.8mm; height:11.8mm; display:flex; align-items:center; justify-content:center; overflow:hidden; }
#${PRINT_ROOT_ID} .sos-v4-qrbox img,#${PRINT_ROOT_ID} .sos-v4-qrbox canvas,#${PRINT_ROOT_ID} .sos-v4-qrbox svg { width:100%; height:100%; max-width:100%; max-height:100%; object-fit:contain; display:block; }
#${PRINT_ROOT_ID} .sos-v4-device { font-size:8.5pt; line-height:1.02; font-weight:900; overflow-wrap:anywhere; }
#${PRINT_ROOT_ID} .sos-v4-serial { font-size:5.1pt; line-height:1; font-weight:650; color:#374151; margin-top:.18mm; overflow-wrap:anywhere; }
#${PRINT_ROOT_ID} .sos-v4-customer { font-size:10.8pt; line-height:1.01; font-weight:900; margin-top:.3mm; overflow-wrap:anywhere; }
#${PRINT_ROOT_ID} .sos-v4-mobile { font-size:9.3pt; line-height:1.01; font-weight:900; margin-top:.18mm; overflow-wrap:anywhere; }
#${PRINT_ROOT_ID} .sos-v4-problem { font-size:8.4pt; line-height:1.03; font-weight:900; margin-top:.26mm; overflow-wrap:anywhere; }
#${PRINT_ROOT_ID} .sos-v4-compact { padding:.72mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-head { padding-bottom:.14mm; margin-bottom:.24mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-shop { font-size:5.1pt; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-job { font-size:5.0pt; margin-top:.08mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-main { grid-template-columns:8.9mm minmax(0,1fr); gap:.45mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-qrbox { width:8.5mm; height:8.5mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-device { font-size:6.6pt; line-height:1; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-serial { font-size:4.4pt; line-height:1; margin-top:.08mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-customer { font-size:8.2pt; line-height:1; margin-top:.14mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-mobile { font-size:7.2pt; line-height:1; margin-top:.08mm; }
#${PRINT_ROOT_ID} .sos-v4-compact .sos-v4-problem { font-size:6.8pt; line-height:1.02; margin-top:.12mm; }
`;

function n(v){ return String(v || '').replace(/\s+/g,' ').trim(); }
function visible(el){ return !!(el && el.getClientRects && el.getClientRects().length); }
function ensureStyle(){ if(document.getElementById(STYLE_ID)) return; const s=document.createElement('style'); s.id=STYLE_ID; s.textContent=css; document.head.appendChild(s); }
function escapeRe(x){ return x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }

function findModal(){
  const heads=[...document.querySelectorAll('h1,h2,h3,h4,[role="heading"]')].filter(el=>visible(el) && /print qr sticker/i.test(n(el.textContent)));
  for(const head of heads.reverse()){
    const dialog=head.closest('[role="dialog"],[aria-modal="true"]');
    if(dialog && /sticker size/i.test(n(dialog.textContent || ''))) return dialog;
    let p=head;
    for(let i=0;p && p!==document.body && i<10;i++,p=p.parentElement){
      const txt=n(p.textContent || '');
      if(/sticker size/i.test(txt) && /service job/i.test(txt)) return p;
    }
  }
  return null;
}

function stickerSize(modal){
  const select=[...modal.querySelectorAll('select')].find(s=>/(50\s*[×x]\s*30|60\s*[×x]\s*40)/i.test([...s.options].map(o=>n(o.textContent)).join(' ')));
  if(select){ const chosen=n(select.selectedOptions?.[0]?.textContent || select.value); return /50\s*[×x]\s*30/i.test(chosen) ? '50x30' : '60x40'; }
  const checked=modal.querySelector('input[type="radio"]:checked');
  if(checked){ const txt=n(checked.closest('label')?.textContent || checked.value); if(/50\s*[×x]\s*30/i.test(txt)) return '50x30'; }
  const active=[...modal.querySelectorAll('[aria-pressed="true"],[data-state="active"],button[class*="active"],button[class*="selected"]')];
  if(active.some(el=>/50\s*[×x]\s*30/i.test(el.textContent || ''))) return '50x30';
  return '60x40';
}

function chooseOriginalSticker(modal){
  const prior=modal.querySelector('[data-sos-v4-original="1"]');
  if(prior) return prior;
  const candidates=[...modal.querySelectorAll('article,section,div')].filter(el => visible(el)
    && JOB_PATTERN.test(el.innerText || el.textContent || '')
    && /problem|issue|fault/i.test(el.textContent || '')
    && el.querySelector('img,canvas,svg')
    && !el.querySelector('input,select,textarea,button'));
  candidates.sort((a,b)=>n(a.textContent).length - n(b.textContent).length);
  const best=candidates[0] || null;
  if(best) best.setAttribute('data-sos-v4-original','1');
  return best;
}

function sourceRoot(original){ return original.__sosV4Source || original; }
function getParts(root){ return [...root.querySelectorAll('p,div,span,strong,b,small,section,header,footer')].filter(el=>{ const t=n(el.textContent); return t && t.length < 220; }); }
function best(root, test){ const rows=getParts(root).filter(el=>test(n(el.textContent))); rows.sort((a,b)=>n(a.textContent).length - n(b.textContent).length); return rows[0] || null; }
function stripPrefix(text, prefixes){ const re='^\\s*(?:'+prefixes.map(escapeRe).join('|')+')\\s*:?\\s*'; return n(text).replace(new RegExp(re,'i'),'').trim(); }
function parseData(original){
  const root=sourceRoot(original);
  const txt=n(root.innerText || root.textContent || '');
  const job=(txt.match(JOB_PATTERN) || [''])[0];
  const device=best(root, s=>/\b(macbook|laptop|desktop|imac|thinkpad|dell|hp|lenovo|asus|acer|printer|monitor)\b/i.test(s) && !/^\s*(customer|name|mobile|phone|problem|issue|fault|s\/?n|serial)\s*:?/i.test(s));
  const customer=best(root, s=>/^\s*(customer|name)\s*:?/i.test(s));
  const mobile=best(root, s=>/^\s*(mobile|phone)\s*:?/i.test(s));
  const problem=best(root, s=>/^\s*(problem|issue|fault)\s*:?/i.test(s));
  const serial=best(root, s=>/^(?:device\s*)?(?:s\/?n|serial(?: number)?)\s*:?/i.test(s));
  const shop=best(root, s=>/AL MODINA COMPUTERS LIMITED/i.test(s));
  return {
    shop: n(shop?.textContent) || 'AL MODINA COMPUTERS LIMITED',
    job,
    device: stripPrefix(device?.textContent || 'Device not recorded', ['Device']),
    customer: stripPrefix(customer?.textContent || 'Not recorded', ['Customer','Name']),
    mobile: stripPrefix(mobile?.textContent || 'Not recorded', ['Mobile','Phone']),
    problem: stripPrefix(problem?.textContent || 'Not recorded', ['Problem','Issue','Fault']),
    serial: stripPrefix(serial?.textContent || '—', ['Device S/N','S/N','Serial','Serial Number']) || '—'
  };
}
function cloneQr(original){
  const root=sourceRoot(original);
  const imgs=[...root.querySelectorAll('img')].filter(img=>img.currentSrc || img.src);
  const qr=imgs.find(img=>/qr|qrcode|data:image/i.test((img.src||'')+' '+(img.alt||'')+' '+(img.className||''))) || imgs[0];
  if(qr){ const img=document.createElement('img'); img.alt='Service job QR code'; img.src=qr.currentSrc || qr.src; return img; }
  const canvas=root.querySelector('canvas');
  if(canvas){ try { const img=document.createElement('img'); img.alt='Service job QR code'; img.src=canvas.toDataURL('image/png'); return img; } catch(_){} }
  const svg=root.querySelector('svg');
  return svg ? svg.cloneNode(true) : null;
}
function make(tag, cls, txt){ const el=document.createElement(tag); if(cls) el.className=cls; if(txt!=null) el.textContent=txt; return el; }

function renderPremiumPreview(original, size){
  if(!original) return;
  const data=parseData(original);
  const qr=cloneQr(original);
  if(!qr) return;
  if(!original.__sosV4Source){ original.__sosV4Source = original.cloneNode(true); }
  original.classList.add('sos-v4-hide-original');
  let wrap=original.nextElementSibling;
  if(!wrap || !wrap.classList.contains('sos-v4-preview-wrap')){
    wrap=document.createElement('div'); wrap.className='sos-v4-preview-wrap'; original.insertAdjacentElement('afterend', wrap);
  }
  wrap.innerHTML='';
  const compact=size==='50x30';
  const paper=make('div','sos-v4-preview-paper');
  const head=make('div','sos-v4-head');
  head.append(make('div','sos-v4-shop',data.shop), make('div','sos-v4-job',data.job));
  const main=make('div','sos-v4-main'+(compact?' compact':''));
  const qrBox=make('div','sos-v4-qr'); qrBox.appendChild(qr);
  const text=make('div','');
  text.append(
    make('div','sos-v4-device',data.device),
    make('div','sos-v4-serial','S/N: ' + (data.serial || '—')),
    make('div','sos-v4-customer',data.customer),
    make('div','sos-v4-mobile',data.mobile),
    make('div','sos-v4-problem',data.problem)
  );
  main.append(qrBox, text);
  paper.append(head, main);
  wrap.appendChild(paper);
}

function removePrintArtifacts(){
  document.getElementById(PRINT_ROOT_ID)?.remove();
  document.getElementById(PAGE_STYLE_ID)?.remove();
  document.body?.removeAttribute('data-sos-v4-printing');
}
async function printSticker(modal, original, button){
  const data=parseData(original);
  const qr=cloneQr(original);
  if(!data.job){ alert('Service Job number not found.'); return; }
  if(!qr){ alert('QR code is not ready yet.'); return; }
  const compact=stickerSize(modal)==='50x30';
  removePrintArtifacts();
  const root=document.createElement('div'); root.id=PRINT_ROOT_ID;
  const paper=make('section','sos-v4-paper'+(compact?' sos-v4-compact':''));
  paper.style.width=compact?'50mm':'60mm'; paper.style.height=compact?'30mm':'40mm';
  const head=make('div','sos-v4-head');
  head.append(make('div','sos-v4-shop',data.shop), make('div','sos-v4-job',data.job));
  const main=make('div','sos-v4-main');
  const qrBox=make('div','sos-v4-qrbox'); qrBox.appendChild(qr);
  const text=make('div','');
  text.append(
    make('div','sos-v4-device',data.device),
    make('div','sos-v4-serial','S/N: ' + (data.serial || '—')),
    make('div','sos-v4-customer',data.customer),
    make('div','sos-v4-mobile',data.mobile),
    make('div','sos-v4-problem',data.problem)
  );
  main.append(qrBox,text);
  paper.append(head,main);
  root.appendChild(paper);
  document.body.appendChild(root);
  const ps=document.createElement('style'); ps.id=PAGE_STYLE_ID; ps.textContent=`@page { size:${compact?'50mm 30mm':'60mm 40mm'}; margin:0; }`; document.head.appendChild(ps);
  const old=button.querySelector('span')?.textContent || 'Print Sticker'; button.disabled=true; if(button.querySelector('span')) button.querySelector('span').textContent='Opening print…';
  const cleanup=()=>{ removePrintArtifacts(); button.disabled=false; if(button.querySelector('span')) button.querySelector('span').textContent=old; };
  window.addEventListener('afterprint', cleanup, {once:true});
  document.body.setAttribute('data-sos-v4-printing','1');
  try {
    if(document.fonts?.ready) await document.fonts.ready;
    if(qr.tagName==='IMG' && !qr.complete){ await Promise.race([new Promise(resolve=>{qr.addEventListener('load',resolve,{once:true});qr.addEventListener('error',resolve,{once:true});}), new Promise(resolve=>setTimeout(resolve,1400))]); }
    window.print();
  } catch(e){ cleanup(); alert('Unable to open printer dialog.'); }
}

function installModal(modal){
  if(modal.dataset.sosV4Installed !== '1'){
    modal.dataset.sosV4Installed = '1';
    const head=[...modal.querySelectorAll('h1,h2,h3,h4,[role="heading"]')].find(el=>/print qr sticker/i.test(n(el.textContent)));
    if(head){
      const bar=make('div','sos-v4-actions');
      bar.append(make('span','sos-v4-hint','Premium sticker print for 60×40 and 50×30 mm'));
      const btn=make('button','sos-v4-print'); btn.type='button'; btn.innerHTML='<svg aria-hidden="true" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a3 3 0 0 1 3-3h14a3 3 0 0 1 3 3v5a2 2 0 0 1-2 2h-2M6 14h12v8H6zM18 12h.01"/></svg><span>Print Sticker</span>';
      btn.addEventListener('click', ev=>{ ev.preventDefault(); ev.stopPropagation(); const original=chooseOriginalSticker(modal); if(original) printSticker(modal, original, btn); });
      bar.appendChild(btn); head.insertAdjacentElement('afterend', bar);
    }
    modal.addEventListener('change', ()=>setTimeout(()=>refreshModal(modal), 80));
    modal.addEventListener('input', ()=>setTimeout(()=>refreshModal(modal), 80));
  }
  refreshModal(modal);
}
function refreshModal(modal){
  const original=chooseOriginalSticker(modal);
  if(!original) return;
  renderPremiumPreview(original, stickerSize(modal));
}
function scan(){
  if(busy) return; busy=true;
  try { const modal=findModal(); if(modal) installModal(modal); } finally { busy=false; }
}
function boot(){ ensureStyle(); scan(); const obs=new MutationObserver(recs=>{ if(recs.some(r=>r.type==='childList')) scan(); }); obs.observe(document.body,{childList:true,subtree:true}); }
if(typeof document!=='undefined'){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot, {once:true}); else boot(); }
