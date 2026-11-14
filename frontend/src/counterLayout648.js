/* SERVICING COUNTER 6.48 — progressively enhance existing active tiles.
 * Does not replace buttons, emit synthetic transactions, or mutate Vue state.
 */
const FEATURES = [
  ['receive', /^(receive device|service receive|ডিভাইস গ্রহণ|সার্ভিস গ্রহণ)/i],
  ['sale', /^(new sale|new product sale|নতুন বিক্রয়|নতুন বিক্রয়)/i],
  ['repair', /^(repair jobs?|service jobs?|মেরামত)/i],
  ['billing', /^(billing\s*(?:&|and)\s*delivery|service delivery|repair billing|বিল)/i],
  ['used', /^(used laptops?|পুরাতন ল্যাপটপ)/i],
  ['stock', /^(stock\s*(?:&|and)\s*items|inventory|স্টক)/i],
];

function textOf(el) {
  return (el?.textContent || '').replace(/\s+/g, ' ').trim();
}

function actionableFor(node, root) {
  let el = node.parentElement;
  while (el && el !== root) {
    if (el.matches('button,a,[role="button"],[role="link"],.cursor-pointer')) return el;
    el = el.parentElement;
  }
  return null;
}

function findTileCandidates(root) {
  const found = new Map();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const txt = (node.nodeValue || '').replace(/\s+/g, ' ').trim();
    if (!txt || txt.length > 85) continue;
    for (const [id, pattern] of FEATURES) {
      if (found.has(id) || !pattern.test(txt)) continue;
      const clickable = actionableFor(node, root);
      if (clickable && textOf(clickable).length < 320) found.set(id, clickable);
    }
  }
  return found;
}

// Find the nearest common container whose six DIRECT children each own exactly
// one unique actionable tile. Works for existing native buttons and card wrappers.
function findGrid(found, root) {
  const cards = [...found.values()];
  if (cards.length !== 6 || new Set(cards).size !== 6) return null;
  let current = cards[0].parentElement;
  while (current && current !== root) {
    const children = [...current.children];
    const owners = cards.map(el => children.find(child => child === el || child.contains(el)));
    if (owners.every(Boolean) && new Set(owners).size === 6) {
      return {grid: current, owners};
    }
    current = current.parentElement;
  }
  return null;
}

function enhance() {
  const root = document.querySelector('.servicing-counter-647');
  if (!root) return false;
  const found = findTileCandidates(root);
  const group = findGrid(found, root);
  if (!group) return false;
  group.grid.classList.add('sos648-grid');
  group.owners.forEach((card, i) => {
    card.classList.add('sos648-tile');
    card.dataset.sos648 = FEATURES[i][0];
  });
  root.classList.add('sos648-ready');
  return true;
}

export function installCounter648() {
  if (window.__servicingCounter648Installed) return;
  window.__servicingCounter648Installed = true;
  let busy = false;
  let enhanced = false;
  const run = () => {
    if (busy) return;
    busy = true;
    try {
      enhanced = enhance();
    } finally {
      busy = false;
    }
  };
  run();
  // The Counter workspace can mount after API load, tab navigation or login.
  const observer = new MutationObserver(() => {
    if (!enhanced || !document.querySelector('.sos648-grid')) run();
  });
  observer.observe(document.getElementById('app') || document.body, {childList:true, subtree:true});
  return () => { observer.disconnect(); window.__servicingCounter648Installed = false; };
}
