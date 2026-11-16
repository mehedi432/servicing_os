/* SERVICING OS — QR LABEL PRINT V11 (standalone enhancement, no Vue/route changes)
   Version marker: SOS_QR_LABEL_PRINT_V11
   Works with the existing QR sticker modal's rendered QR <svg>, <canvas>, or <img>.
   It cannot generate QR codes when the existing modal did not render one.
*/
(function () {
  'use strict';
  if (window.__SOS_QR_LABEL_PRINT_V11__) return;
  window.__SOS_QR_LABEL_PRINT_V11__ = true;

  const VERSION = 'SOS_QR_LABEL_PRINT_V11';
  const TOOLBAR_ID = 'sos-qr-label-print-v11';
  const STYLE_ID = 'sos-qr-label-print-v11-styles';
  const SIZES = [
    ['50x30', '50 × 30 mm · Device'],
    ['60x40', '60 × 40 mm · Standard'],
    ['40x30', '40 × 30 mm · Compact'],
    ['40x25', '40 × 25 mm · Compact'],
    ['50x25', '50 × 25 mm · Compact'],
    ['30x30', '30 × 30 mm · QR mini'],
    ['30x20', '30 × 20 mm · QR mini'],
    ['25x25', '25 × 25 mm · QR only'],
    ['50x50', '50 × 50 mm · Square'],
    ['70x40', '70 × 40 mm'],
    ['70x50', '70 × 50 mm'],
    ['80x50', '80 × 50 mm'],
    ['100x50', '100 × 50 mm'],
    ['100x75', '100 × 75 mm'],
    ['100x100', '100 × 100 mm'],
    ['100x150', '100 × 150 mm · 4×6 in approx.'],
    ['custom', 'Custom / কাস্টম মাপ']
  ];
  const escapeHtml = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean = s => String(s || '').replace(/[\r\t]/g, ' ').trim();
  const visible = el => Boolean(el && el.isConnected && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden');

  function styleToolbar() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      #${TOOLBAR_ID}{box-sizing:border-box;display:block;clear:both;margin:12px 0;padding:12px;border:1px solid #d8c7b3;border-radius:12px;background:#faf5ed;color:#3d2b1e;font:13px/1.4 system-ui,-apple-system,BlinkMacSystemFont,"Noto Sans Bengali",sans-serif;position:relative;z-index:1}
      #${TOOLBAR_ID} *,#${TOOLBAR_ID} *::before,#${TOOLBAR_ID} *::after{box-sizing:border-box}
      #${TOOLBAR_ID} .sos-v11-title{font-weight:800;font-size:13px;margin:0 0 8px}
      #${TOOLBAR_ID} .sos-v11-fields{display:flex;align-items:flex-end;flex-wrap:wrap;gap:8px}
      #${TOOLBAR_ID} label{font-size:11px;font-weight:750;color:#5c4430;display:flex;flex-direction:column;gap:4px}
      #${TOOLBAR_ID} select,#${TOOLBAR_ID} input{max-width:100%;background:#fff;color:#302117;border:1px solid #cbb8a1;border-radius:7px;padding:8px;min-height:36px;font:inherit}
      #${TOOLBAR_ID} select{width:225px}
      #${TOOLBAR_ID} input[type=number]{width:70px}
      #${TOOLBAR_ID} .sos-v11-custom{display:none;align-items:end;gap:8px}
      #${TOOLBAR_ID} .sos-v11-custom.sos-v11-on{display:flex}
      #${TOOLBAR_ID} .sos-v11-print{appearance:none;background:#483526;color:#fff;font-weight:800;border:0;border-radius:8px;padding:9px 15px;min-height:36px;cursor:pointer}
      #${TOOLBAR_ID} .sos-v11-print:hover{background:#2f2119}
      #${TOOLBAR_ID} .sos-v11-help{display:block;margin-top:7px;color:#6d5a48;font-size:11px}
      #${TOOLBAR_ID} .sos-v11-status{margin-top:6px;font-weight:700;color:#8c321f;min-height:0}
    `;
    document.head.appendChild(style);
  }

  function findHeading() {
    const nodes = document.querySelectorAll('h1,h2,h3,h4,h5,[role="heading"],strong,b,span,div');
    for (const el of nodes) {
      if (!visible(el) || el.closest('#' + TOOLBAR_ID)) continue;
      const t = clean(el.textContent);
      if (t.length > 100 || t.length < 7) continue;
      if (/কিউআর স্টিকার প্রিন্ট|QR Sticker Print|QR Label Print/i.test(t)) return el;
    }
    return null;
  }

  function findModal(heading) {
    let el = heading.closest('[role="dialog"],dialog,[aria-modal="true"],.modal,.modal-content');
    if (el && visible(el)) return el;
    el = heading;
    for (let i = 0; i < 9 && el && el !== document.body; i++, el = el.parentElement) {
      if (!visible(el)) continue;
      const t = clean(el.innerText);
      if (t.length < 18000 && /(?:স্টিকারের মাপ|Sticker Size|Device Identification|সার্ভিস জব নম্বর)/i.test(t) &&
          /(?:SRV-\d{4}-\d+|service_job=|সার্ভিস জব খুঁজুন|Find Service Job)/i.test(t)) return el;
    }
    return null;
  }

  function readLine(text, labels, limit) {
    const re = new RegExp('(?:^|\\n)\\s*(?:' + labels + ')\\s*[:：]\\s*([^\\n]{1,' + (limit || 150) + '})', 'im');
    const m = text.match(re);
    if (!m) return '';
    return clean(m[1].split(/\s+(?:Mobile|Phone|Problem|Customer|Device S\/N|মোবাইল|সমস্যা|ক্রেতা|কিউআর লিংক)\s*[:：]/i)[0]);
  }

  function extractData(modal) {
    const text = clean(modal.innerText).replace(/\u00a0/g, ' ');
    const a = [...modal.querySelectorAll('a[href]')].find(a => /[?&]service_job=/.test(a.getAttribute('href') || ''));
    let qrUrl = a ? a.href : '';
    if (!qrUrl) {
      const m = text.match(/https?:\/\/[^\s<>"']+[?&]service_job=[A-Za-z0-9_.-]+/i);
      if (m) qrUrl = m[0];
    }
    let job = '';
    if (qrUrl) {
      try { const u = new URL(qrUrl, location.href); job = u.searchParams.get('service_job') || ''; }
      catch (_) { /* use text fallback */ }
    }
    if (!job) job = (text.match(/SRV-\d{4}-\d+/i) || [''])[0];

    const customer = readLine(text, 'ক্রেতা|গ্রাহক|Customer|Client', 110);
    const mobile = readLine(text, 'মোবাইল|Mobile|Phone|Contact', 35);
    const problem = readLine(text, 'Problem|সমস্যা|অভিযোগ|Reported Problem', 300);
    const serial = readLine(text, 'Device S\\/N|S\\/N|Serial Number|সিরিয়াল', 100);
    let device = readLine(text, 'Device|ডিভাইস', 110);
    if (!device) {
      const lines = text.split(/\n+/).map(clean);
      const pos = lines.findIndex(l => job && l.includes(job));
      const afterJob = (pos >= 0 ? lines.slice(pos + 1) : lines);
      device = afterJob.find(l => l && l.length < 100 && /(?:APPLE|MACBOOK|DELL|HP\b|LENOVO|ASUS|ACER|SAMSUNG|LAPTOP|DESKTOP|MSI\b)/i.test(l) && !/http|serial|Device S\/N/i.test(l)) || '';
    }
    if (!device) {
      const pattern = new RegExp(escapeRegExp(job) + '\\s*([^\\n]{3,95}?)(?:Device S\\/N|Serial|ক্রেতা|Customer)', 'i');
      const m = job && text.match(pattern);
      if (m) device = clean(m[1]);
    }
    return {job, customer, mobile, problem, serial, device, qrUrl, brand:'AL MODINA COMPUTERS LIMITED'};
  }
  function escapeRegExp(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  function findQrGraphic(modal) {
    const nodes = [...modal.querySelectorAll('canvas,svg,img')].filter(el => !el.closest('#' + TOOLBAR_ID));
    const ranks = [];
    for (const el of nodes) {
      if (!visible(el)) continue;
      const box = el.getBoundingClientRect();
      const tag = el.tagName.toLowerCase();
      const w = tag === 'canvas' ? el.width : tag === 'img' ? el.naturalWidth : box.width;
      const h = tag === 'canvas' ? el.height : tag === 'img' ? el.naturalHeight : box.height;
      if (!w || !h || Math.min(box.width, box.height) < 55) continue;
      if (Math.abs(w / h - 1) > .35) continue;
      let score = Math.min(box.width, box.height);
      if (tag === 'canvas') score += 120;
      if (tag === 'svg') score += el.outerHTML.length > 900 ? 170 : 0;
      if (tag === 'img' && /qr/i.test(el.alt + ' ' + el.className)) score += 160;
      ranks.push({el, score});
    }
    ranks.sort((a,b) => b.score - a.score);
    for (const {el} of ranks) {
      try {
        if (el.tagName.toLowerCase() === 'canvas') {
          return '<img class="qr-art" alt="QR" src="' + escapeHtml(el.toDataURL('image/png')) + '">';
        }
        if (el.tagName.toLowerCase() === 'img') {
          if (/^(?:data:image\/(?:png|svg\+xml|jpeg|webp)|https?:\/\/|\/)/i.test(el.src))
            return '<img class="qr-art" alt="QR" src="' + escapeHtml(el.src) + '">';
        }
        if (el.tagName.toLowerCase() === 'svg') {
          const clone = el.cloneNode(true);
          clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
          clone.removeAttribute('style');
          clone.setAttribute('class', 'qr-art');
          return new XMLSerializer().serializeToString(clone);
        }
      } catch (_) { /* Try another visible QR representation */ }
    }
    return '';
  }

  function makePrintHtml(data, qrHtml, width, height, copies, labelLang) {
    const mini = width < 40 || height < 25;
    const compact = !mini && (width <= 50 || height <= 30);
    const cls = mini ? 'mini' : compact ? 'compact' : 'roomy';
    const pad = mini ? 0.75 : 1.1;
    const qrMm = mini ? Math.min(width - 2 * pad, height - 8, 21) : Math.min(width * .35, height * .55, 24);
    const brand = escapeHtml(data.brand);
    const job = escapeHtml(data.job);
    const customer = escapeHtml(data.customer || '—');
    const phone = escapeHtml(data.mobile || '—');
    const device = escapeHtml(data.device || '—');
    const serial = escapeHtml(data.serial || '—');
    const fault = escapeHtml(data.problem || '—');
    const page = `<section class="label ${cls}">
      <div class="top"><div class="qr-holder">${qrHtml}</div>
      <div class="meta"><div class="brand">${brand}</div><div class="job">${job}</div>
      <div class="device">${device}</div><div class="customer">${customer}</div>
      <div class="mobile">${phone}</div></div></div>
      <div class="problem">${labelLang === 'bn' ? 'সমস্যা' : 'PROBLEM'}: ${fault}</div>
      <div class="serial">S/N: ${serial}</div>
    </section>`;
    return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Device label ${job} · ${width} × ${height} mm</title>
<style>
  @page{size:${width}mm ${height}mm;margin:0}
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:#fff;color:#161210;font-family:Arial,"Noto Sans Bengali","Hind Siliguri",sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .label{width:${width}mm;height:${height}mm;overflow:hidden;page-break-after:always;break-after:page;display:flex;flex-direction:column;padding:${pad}mm;gap:.3mm;background:#fff}
  .label:last-of-type{page-break-after:auto;break-after:auto}
  .top{display:flex;gap:1mm;min-height:0;flex:1;align-items:flex-start}
  .qr-holder{width:${qrMm.toFixed(1)}mm;height:${qrMm.toFixed(1)}mm;flex:0 0 ${qrMm.toFixed(1)}mm;display:flex;align-items:center;justify-content:center;overflow:hidden;background:#fff}
  .qr-art{display:block;width:100%!important;height:100%!important;max-height:100%!important;max-width:100%!important;object-fit:contain;image-rendering:pixelated}
  .meta{display:flex;min-width:0;flex:1;flex-direction:column;gap:.2mm;overflow:hidden}
  .brand{font-size:6.2pt;line-height:1.07;font-weight:900;overflow-wrap:anywhere;max-height:5mm;overflow:hidden}
  .job{font-size:8pt;font-weight:900;line-height:1.1;overflow-wrap:anywhere}
  .device{font-size:7.4pt;font-weight:700;line-height:1.15;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
  .customer{font-size:10.4pt;font-weight:900;line-height:1.1;overflow-wrap:anywhere;max-height:7.5mm;overflow:hidden}
  .mobile{font-size:8.5pt;font-weight:800;line-height:1.1;white-space:nowrap}
  .problem{font-weight:900;border-top:.18mm solid #25201d;padding-top:.4mm;min-height:0;max-height:30%;font-size:9pt;line-height:1.13;overflow-wrap:anywhere;overflow:hidden}
  .serial{font-size:6.2pt;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .compact .brand{font-size:5pt;max-height:3.8mm}.compact .job{font-size:7pt}.compact .device{font-size:6.1pt}.compact .customer{font-size:9pt;max-height:5.3mm}.compact .mobile{font-size:7.6pt}.compact .problem{font-size:8.2pt;max-height:30%}.compact .serial{display:none}
  .mini .top{display:flex;flex-direction:column;align-items:center;justify-content:space-between;gap:.5mm}
  .mini .meta{flex:none;width:100%;text-align:center}.mini .meta>*:not(.job){display:none}.mini .job{font-size:6.2pt;white-space:nowrap}
  .mini .problem,.mini .serial{display:none}
  .roomy .problem{max-height:40%;font-size:11pt}.roomy .brand{font-size:8pt}.roomy .job{font-size:10pt}.roomy .device{font-size:9pt}.roomy .customer{font-size:14pt}.roomy .mobile{font-size:11pt}
  .noprint{display:none}
  @media screen{body{background:#f3eee7;padding:18px}.label{box-shadow:0 3px 12px #0002;margin:0 auto 14px}.noprint{display:flex;position:sticky;top:0;background:#f9f3e9;border:1px solid #d3c0a8;border-radius:8px;padding:12px;margin:0 auto 14px;max-width:650px;align-items:center;gap:12px;z-index:3;font:13px system-ui}.noprint button{padding:8px 14px;background:#493526;color:white;border:0;border-radius:7px;cursor:pointer}}
  @media print{html,body{width:${width}mm;margin:0!important;padding:0!important;background:#fff}.noprint{display:none!important}}
</style></head><body>
<div class="noprint"><button type="button" onclick="window.print()">🖨 Print / প্রিন্ট</button><span>${width} × ${height} mm · ${copies} ${copies === 1 ? 'label' : 'labels'} · Set scale 100%, margins none</span></div>
${Array(copies).fill(page).join('\n')}
</body></html>`;
  }

  function injectToolbar(modal, heading) {
    if (modal.querySelector('#' + TOOLBAR_ID)) return;
    styleToolbar();
    const bn = /[\u0980-\u09FF]/.test(heading.textContent || '');
    const bar = document.createElement('div');
    bar.id = TOOLBAR_ID;
    bar.setAttribute('data-version', VERSION);
    const opts = SIZES.map(([v, label]) => `<option value="${v}"${v==='60x40'?' selected':''}>${escapeHtml(label)}</option>`).join('');
    bar.innerHTML = `
      <div class="sos-v11-title">🖨 ${bn ? 'কিউআর স্টিকার প্রিন্ট · প্রিন্টার সেটআপ' : 'QR Label Printing · Printer Setup'}</div>
      <div class="sos-v11-fields">
        <label>${bn ? 'লেবেলের মাপ' : 'Label size'}<select class="sos-v11-size" aria-label="Label size">${opts}</select></label>
        <div class="sos-v11-custom">
          <label>${bn ? 'প্রস্থ (মিমি)' : 'Width (mm)'}<input class="sos-v11-width" type="number" min="20" max="150" step="1" value="50"></label>
          <label>${bn ? 'উচ্চতা (মিমি)' : 'Height (mm)'}<input class="sos-v11-height" type="number" min="20" max="200" step="1" value="30"></label>
        </div>
        <label>${bn ? 'কপি' : 'Copies'}<input class="sos-v11-copies" type="number" min="1" max="20" value="1"></label>
        <button class="sos-v11-print" type="button">🖨 ${bn ? 'স্টিকার প্রিন্ট করুন' : 'Print Sticker'}</button>
      </div>
      <small class="sos-v11-help">${bn ? 'থার্মাল/লেবেল প্রিন্টারে 100% স্কেল, মার্জিন 0 এবং একই পেপার সাইজ নির্বাচন করুন।' : 'For thermal/label printers, use 100% scale, zero margins, and the same paper size in printer settings.'}</small>
      <div class="sos-v11-status" role="status" aria-live="polite"></div>`;
    const header = heading.closest('header') || heading.parentElement;
    if (header && header !== modal && modal.contains(header)) header.insertAdjacentElement('afterend', bar);
    else modal.insertBefore(bar, modal.firstChild);
    const select = bar.querySelector('.sos-v11-size');
    const custom = bar.querySelector('.sos-v11-custom');
    const status = bar.querySelector('.sos-v11-status');
    select.addEventListener('change', () => {
      custom.classList.toggle('sos-v11-on', select.value === 'custom');
      status.textContent = '';
    });
    bar.querySelector('.sos-v11-print').addEventListener('click', () => {
      const dims = select.value === 'custom' ? [Number(bar.querySelector('.sos-v11-width').value), Number(bar.querySelector('.sos-v11-height').value)] : select.value.split('x').map(Number);
      const [width, height] = dims;
      const copies = Number(bar.querySelector('.sos-v11-copies').value);
      status.textContent = '';
      if (!Number.isFinite(width) || !Number.isFinite(height) || width < 20 || width > 150 || height < 20 || height > 200) {
        status.textContent = bn ? 'প্রস্থ 20–150 মিমি ও উচ্চতা 20–200 মিমি দিন।' : 'Width must be 20–150 mm and height 20–200 mm.';
        return;
      }
      if (!Number.isInteger(copies) || copies < 1 || copies > 20) {
        status.textContent = bn ? 'কপি 1–20 হতে হবে।' : 'Copies must be 1–20.';
        return;
      }
      const data = extractData(modal);
      const qr = findQrGraphic(modal);
      if (!data.job) {
        status.textContent = bn ? 'আগে একটি সার্ভিস জব নির্বাচন করুন।' : 'Select a service job first.';
        return;
      }
      if (!qr) {
        status.textContent = bn ? 'কিউআর কোডটি লোড হয়নি। আগে কিউআর প্রিভিউ দেখা যাচ্ছে কি না নিশ্চিত করুন।' : 'QR code is not rendered yet. Open the job and wait for its QR preview.';
        return;
      }
      const win = window.open('', '_blank', 'width=760,height=650');
      if (!win) {
        status.textContent = bn ? 'পপ-আপ ব্লক করা হয়েছে। এই সাইটের জন্য পপ-আপ অনুমতি দিন।' : 'Pop-up blocked. Allow pop-ups for this site and retry.';
        return;
      }
      const html = makePrintHtml(data, qr, width, height, copies, bn ? 'bn' : 'en');
      win.document.open();
      win.document.write(html);
      win.document.close();
      try { win.opener = null; } catch (_) { /* browser may restrict this */ }
      // The print-preview page always includes a manual Print button, even if automatic printing is prevented.
      const doPrint = () => { try { win.focus(); win.print(); } catch (_) { /* user can press Print in the opened window */ } };
      if (win.document.readyState === 'complete') setTimeout(doPrint, 250);
      else win.addEventListener('load', () => setTimeout(doPrint, 250), {once:true});
    });
  }

  let queued = false;
  function scan() {
    queued = false;
    const heading = findHeading();
    if (!heading) return;
    const modal = findModal(heading);
    if (modal) injectToolbar(modal, heading);
  }
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(scan);
  }
  function boot() {
    schedule();
    new MutationObserver(schedule).observe(document.body, {subtree:true, childList:true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
