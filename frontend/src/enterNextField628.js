// SERVICING_ENTER_NEXT_628
// Keyboard-only enhancement for SERVICING OS forms.
// Regular single-line fields: Enter = next, Shift+Enter = previous.
// Safe exits: barcode scanners, search/filter controls, comboboxes, textareas,
// passwords, submit/buttons, native date pickers, modifier shortcuts and IME.
// This never clicks buttons, submits forms or triggers accounting transactions.

const FEATURE_KEY = '__servicingEnterNext628Installed'

function formField(node) {
  if (!node || !node.tagName) return false
  const tag = node.tagName.toLowerCase()
  if (tag === 'select' || tag === 'textarea') return true
  if (tag !== 'input') return false
  const kind = String(node.type || 'text').toLowerCase()
  return !['button', 'submit', 'reset', 'checkbox', 'radio', 'file',
    'hidden', 'image', 'color', 'range'].includes(kind)
}

function activeField(node) {
  if (!formField(node) || node.disabled || node.readOnly) return false
  if (node.tabIndex < 0) return false
  if (node.closest?.('[inert], [aria-hidden="true"], [data-enter-next="off"]')) return false
  if (!node.isConnected) return false
  // Exclude CSS-hidden fields, including inactive v-show tabs.
  if (typeof node.getClientRects === 'function' && node.getClientRects().length === 0) return false
  return true
}

function nativeEnter(node) {
  if (!node || !node.tagName) return true
  const tag = node.tagName.toLowerCase()
  if (tag === 'textarea') return true  // Enter creates a newline.
  if (tag === 'select') return false  // Select Enter handled *after* native selection.
  if (tag !== 'input') return true
  const kind = String(node.type || 'text').toLowerCase()
  if (['password', 'search', 'file', 'submit', 'button', 'reset', 'radio',
    'checkbox', 'hidden', 'color', 'range', 'date', 'time',
    'datetime-local', 'month', 'week'].includes(kind)) return true
  if (node.hasAttribute?.('list')) return true
  if (node.getAttribute?.('role') === 'combobox') return true
  if (node.hasAttribute?.('aria-autocomplete')) return true
  if (node.getAttribute?.('aria-expanded') === 'true') return true
  if (node.closest?.('[data-native-enter], [data-enter-next="off"]')) return true
  // Search and scanner fields need Enter for lookup/scan; don't steal it.
  const text = [node.id, node.name, node.getAttribute?.('placeholder'),
    node.getAttribute?.('aria-label')].filter(Boolean).join(' ').toLowerCase()
  if (/\b(search|filter|lookup|scan|find)\b/.test(text) ||
      /(?:^|[_-])(search|filter|scan|lookup|find)(?:$|[_-])/.test(text)) return true
  return false
}

const SCOPE = [
  '[data-enter-next-scope]', 'form', '[role="dialog"]', 'dialog',
  '[aria-modal="true"]', '.modal', '.sos627-panel', '.cc-checkout',
  '.cc-root', '.sos-stock-modal', '.stock-quick-modal',
  '.used-laptop-modal', 'main'
].join(', ')

function containingScope(node) {
  // Use the nearest real form or dialog. This avoids navigating into the
  // sidebar or a different (possibly hidden) counter tab.
  return node.closest?.(SCOPE) || document.querySelector('#app') || null
}

function move(node, reverse = false) {
  const scope = containingScope(node)
  if (!scope || !scope.querySelectorAll) return false
  const candidates = Array.from(scope.querySelectorAll('input, select, textarea'))
    .filter(activeField)
  const index = candidates.indexOf(node)
  if (index < 0) return false
  const next = candidates[index + (reverse ? -1 : 1)]
  if (!next) return false
  next.focus({ preventScroll: true })
  if (next.tagName?.toLowerCase() === 'input' &&
      !['number', 'date', 'time'].includes(String(next.type).toLowerCase()) &&
      typeof next.select === 'function' && next.getAttribute?.('data-enter-next-select') === 'all') {
    next.select()
  }
  next.scrollIntoView?.({ block: 'nearest', inline: 'nearest' })
  return true
}

function permittedKey(e) {
  return e.key === 'Enter' && !e.defaultPrevented && !e.isComposing &&
    e.keyCode !== 229 && !e.ctrlKey && !e.metaKey && !e.altKey && !e.repeat
}

function onKeydown(e) {
  if (!permittedKey(e)) return
  const field = e.target
  if (!activeField(field)) return
  // Native select menus require their own Enter; handled on keyup.
  if (field.tagName.toLowerCase() === 'select' || nativeEnter(field)) return
  // Prevent accidental implicit form submission, even on the final field.
  e.preventDefault()
  move(field, Boolean(e.shiftKey))
}

function onKeyup(e) {
  if (!permittedKey(e)) return
  const field = e.target
  if (!activeField(field) || field.tagName.toLowerCase() !== 'select') return
  if (field.closest?.('[data-native-enter], [data-enter-next="off"]')) return
  // On native <select>, wait until Enter has accepted the option.
  move(field, Boolean(e.shiftKey))
}

if (typeof document !== 'undefined' && typeof window !== 'undefined' &&
    !window[FEATURE_KEY]) {
  window[FEATURE_KEY] = true
  // Bubble phase: component-level Enter handlers run first. Respect preventDefault.
  document.addEventListener('keydown', onKeydown, false)
  document.addEventListener('keyup', onKeyup, false)
}
